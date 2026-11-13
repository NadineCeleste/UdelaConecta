"""Postulaciones: informe determinista, orientación con IA/fallback y datos para n8n.

El indicador de compatibilidad siempre lo calcula ``app.dominio.compatibilidad`` en Python.
La IA (a través de n8n) solo redacta una orientación a partir de ese resultado: nunca lo
modifica ni evalúa habilidades blandas. Si n8n no está configurado o falla, se guarda un
fallback determinista para que la postulación y la app sigan funcionando.
"""

import re
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import CurrentUser, get_current_user, normalizar_email
from app.dominio.compatibilidad import comparar, normalizar_nombre, texto_fallback
from app.models import Contrato, Estudiante, InformePostulacion
from app.schemas.serializacion import a_dict

router = APIRouter(prefix="/api", tags=["postulaciones"])

HEADER_SECRETO = "X-Udela-Secret"
MAX_TEXTO_ORIENTACION = 600
ESTADOS_INFORME = {"pendiente", "generado", "fallback"}
# Frases que nunca debería devolver la IA: se comparan sin tildes ni mayúsculas.
FRASES_RECHAZO = ("no calificas", "rechazado", "no sos apto", "no cumple", "no sirve")
MODELO_POR_DEFECTO = "n8n"
# Respuestas de n8n que no redactó la IA: su respaldo y el mensaje fijo cuando no hay brechas.
# Se guardan con estado "fallback" para que el front no las muestre como "generada por IA".
MODELOS_SIN_IA = {"fallback", "sin-brechas"}
# Un texto completo termina en signo de cierre, opcionalmente seguido de comillas o paréntesis.
# Si el modelo se queda sin tokens, el texto se corta a mitad de frase y no lo cumple.
_CIERRE_DE_FRASE = re.compile(r"[.!?…][\"'»)\]]*$")

# Los tests lo reemplazan por un httpx.MockTransport para no llamar a n8n.
_transporte: httpx.AsyncBaseTransport | None = None


def _orientacion_dict(informe: InformePostulacion | None) -> dict | None:
    if informe is None:
        return None
    return {
        "texto": informe.texto,
        "estado": informe.estado,
        "modelo": informe.modelo,
        "actualizado_en": informe.actualizado_en.isoformat() if informe.actualizado_en else None,
    }


def _texto_orientacion_valido(texto: str) -> bool:
    if not texto or not texto.strip():
        return False
    if len(texto) > MAX_TEXTO_ORIENTACION:
        return False
    if not _CIERRE_DE_FRASE.search(texto.strip()):
        return False
    normalizado = normalizar_nombre(texto)
    return not any(frase in normalizado for frase in FRASES_RECHAZO)


def _estado_para(modelo: str) -> str:
    """Estado del informe según quién escribió el texto: la IA o un mensaje determinista."""
    return "fallback" if modelo in MODELOS_SIN_IA else "generado"


def _texto_por_defecto(resultado: dict) -> str:
    """Fallback determinista; nunca deja a la persona sin orientación."""
    if resultado.get("sin_requisitos"):
        return (
            "Esta oferta todavía no tiene requisitos cargados. Podés postularte igual y "
            "contar tu experiencia en la entrevista. Esto es una orientación para prepararte, "
            "no una evaluación."
        )
    return texto_fallback(resultado.get("a_capacitar") or [])


async def _pedir_a_n8n(payload: dict, resultado: dict) -> tuple[str, str, str]:
    """Devuelve (texto, modelo, estado). Ante cualquier falla usa el fallback."""
    fallback = _texto_por_defecto(resultado)
    if not settings.N8N_ORIENTACION_WEBHOOK_URL or not settings.N8N_AUTOMATION_SECRET:
        return fallback, "", "fallback"
    try:
        async with httpx.AsyncClient(
            timeout=settings.N8N_ORIENTACION_TIMEOUT_SEGUNDOS, transport=_transporte
        ) as cliente:
            res = await cliente.post(
                settings.N8N_ORIENTACION_WEBHOOK_URL,
                json=payload,
                headers={HEADER_SECRETO: settings.N8N_AUTOMATION_SECRET},
            )
        res.raise_for_status()
        cuerpo = res.json()
        texto = str(cuerpo.get("texto") or "").strip()
        modelo = str(cuerpo.get("modelo") or MODELO_POR_DEFECTO).strip()
    except (httpx.HTTPError, ValueError, AttributeError, TypeError):
        return fallback, "", "fallback"
    if not _texto_orientacion_valido(texto):
        return fallback, "", "fallback"
    return texto, modelo, _estado_para(modelo)


async def _guardar_informe(
    db: AsyncSession, contrato_id: int, email: str, texto: str, modelo: str, estado: str
) -> InformePostulacion:
    informe = await db.scalar(
        select(InformePostulacion).where(
            InformePostulacion.contrato_id == contrato_id,
            InformePostulacion.estudiante_email == email,
        )
    )
    if informe is None:
        informe = InformePostulacion(contrato_id=contrato_id, estudiante_email=email)
        db.add(informe)
    informe.texto = texto
    informe.modelo = modelo
    informe.estado = estado if estado in ESTADOS_INFORME else "fallback"
    informe.actualizado_en = datetime.now(timezone.utc)
    await db.flush()
    return informe


async def _contrato_postulado(
    db: AsyncSession, contrato_id: int, user: CurrentUser
) -> tuple[Contrato, Estudiante]:
    """Contrato y perfil del estudiante autenticado, exigiendo que sea su postulación."""
    contrato = await db.get(Contrato, contrato_id)
    if contrato is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contrato no encontrado")
    if user.email not in (contrato.postulaciones or []):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Solo podés ver la orientación de tus propias postulaciones"
        )
    estudiante = await db.scalar(select(Estudiante).where(Estudiante.email == user.email))
    if estudiante is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo estudiantes y graduados pueden postularse")
    return contrato, estudiante


async def _exigir_secreto(x_udela_secret: str | None = Header(default=None, alias=HEADER_SECRETO)):
    """Autenticación de los endpoints que consume n8n, con comparación en tiempo constante."""
    import hmac

    if not settings.N8N_AUTOMATION_SECRET:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "La automatización no está configurada"
        )
    if not x_udela_secret or not hmac.compare_digest(
        x_udela_secret, settings.N8N_AUTOMATION_SECRET
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Secreto de automatización inválido")


@router.get("/mis-postulaciones")
async def mis_postulaciones(
    user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    estudiante = await db.scalar(select(Estudiante).where(Estudiante.email == user.email))
    if estudiante is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Esta vista es solo para estudiantes y graduados"
        )

    contratos = (
        await db.scalars(select(Contrato).order_by(Contrato.id.desc()))
    ).all()
    propios = [c for c in contratos if user.email in (c.postulaciones or [])]
    ids = [c.id for c in propios]
    informes: dict[int, InformePostulacion] = {}
    if ids:
        filas = (
            await db.scalars(
                select(InformePostulacion).where(
                    InformePostulacion.estudiante_email == user.email,
                    InformePostulacion.contrato_id.in_(ids),
                )
            )
        ).all()
        informes = {i.contrato_id: i for i in filas}

    datos = [
        {
            "contrato": a_dict(contrato),
            "resultado": comparar(estudiante, contrato.requisitos),
            "orientacion": _orientacion_dict(informes.get(contrato.id)),
        }
        for contrato in propios
    ]
    return {"message": "Mis postulaciones", "count": len(datos), "data": datos}


@router.get("/postulaciones/{contrato_id}/orientacion")
async def get_orientacion(
    contrato_id: int,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _contrato_postulado(db, contrato_id, user)
    informe = await db.scalar(
        select(InformePostulacion).where(
            InformePostulacion.contrato_id == contrato_id,
            InformePostulacion.estudiante_email == user.email,
        )
    )
    return {"message": "Orientación", "data": _orientacion_dict(informe)}


@router.post("/postulaciones/{contrato_id}/orientacion")
async def generar_orientacion(
    contrato_id: int,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    contrato, estudiante = await _contrato_postulado(db, contrato_id, user)
    resultado = comparar(estudiante, contrato.requisitos)
    if resultado["sin_requisitos"]:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "La oferta no tiene requisitos cargados; no se puede generar una orientación",
        )

    payload = {
        "contrato_id": contrato.id,
        "email": user.email,
        "oferta": contrato.titulo,
        "compatibles": [i["nombre"] for i in resultado["compatibles"]],
        "a_capacitar": [i["nombre"] for i in resultado["a_capacitar"]],
        "se_aprenden": list(resultado["se_aprenden"]),
        "blandas": list(resultado["blandas"]),
        "coincidencia": resultado["coincidencia"],
    }
    texto, modelo, estado = await _pedir_a_n8n(payload, resultado)
    informe = await _guardar_informe(db, contrato.id, user.email, texto, modelo, estado)
    return {"message": "Orientación generada", "data": _orientacion_dict(informe)}


@router.post("/automatizacion/postulaciones/{contrato_id}/{email}/orientacion")
async def guardar_orientacion_automatizacion(
    contrato_id: int,
    email: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_exigir_secreto),
):
    """Alternativa para que n8n guarde la orientación si se usa una llamada asíncrona."""
    email = normalizar_email(email)
    contrato = await db.get(Contrato, contrato_id)
    if contrato is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contrato no encontrado")
    if email not in (contrato.postulaciones or []):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ese email no se postuló a este contrato")

    texto = str(body.get("texto") or "").strip()
    if not _texto_orientacion_valido(texto):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "La orientación está vacía, incompleta, supera los 600 caracteres o contiene "
            "frases de rechazo",
        )
    modelo = str(body.get("modelo") or MODELO_POR_DEFECTO).strip()
    informe = await _guardar_informe(db, contrato.id, email, texto, modelo, _estado_para(modelo))
    return {"message": "Orientación guardada", "data": _orientacion_dict(informe)}


@router.get("/automatizacion/digests")
async def digests(
    db: AsyncSession = Depends(get_db), _: None = Depends(_exigir_secreto)
):
    """Oportunidades libres con mayor coincidencia por estudiante, para el digest semanal."""
    estudiantes = (await db.scalars(select(Estudiante).order_by(Estudiante.id))).all()
    ofertas = (
        await db.scalars(
            select(Contrato).where(Contrato.esta_ocupado.is_(False)).order_by(Contrato.id)
        )
    ).all()

    datos = []
    for estudiante in estudiantes:
        postuladas = set()
        opciones = []
        for oferta in ofertas:
            if estudiante.email in (oferta.postulaciones or []):
                postuladas.add(oferta.id)
                continue
            if oferta.pasante_email == estudiante.email:
                continue
            resultado = comparar(estudiante, oferta.requisitos)
            if resultado["coincidencia"] <= 60:
                continue
            opciones.append({
                "contrato_id": oferta.id,
                "titulo": oferta.titulo,
                "coincidencia": resultado["coincidencia"],
                "faltantes": [i["nombre"] for i in resultado["a_capacitar"]],
            })
        if not opciones:
            continue
        opciones.sort(key=lambda o: (-o["coincidencia"], o["contrato_id"]))
        datos.append({
            "email": estudiante.email,
            "nombre": f"{estudiante.nombre or ''} {estudiante.apellido or ''}".strip()
            or estudiante.name
            or "",
            "ofertas": opciones[:3],
        })

    return {"message": "Digests de oportunidades", "count": len(datos), "data": datos}
