from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser, get_current_user, normalizar_email
from app.dominio.compatibilidad import comparar, sanitizar_requisitos
from app.models import Contrato, Estudiante, Proyecto
from app.schemas.auth import AsignarRequest
from app.schemas.serializacion import a_dict, aplicar_cambios

router = APIRouter(prefix="/api", tags=["contratos"], dependencies=[Depends(get_current_user)])

# Estos campos solo cambian por postulación/asignación, nunca con un PUT genérico
CAMPOS_DE_ESTADO = {"id", "created_at", "proyecto_id", "postulaciones", "tiene_postulaciones",
                    "esta_ocupado", "pasante_email"}


def _respuesta_lista(mensaje: str, contratos: list[Contrato]) -> dict:
    return {"message": mensaje, "count": len(contratos), "data": [a_dict(c) for c in contratos]}


async def _obtener(db: AsyncSession, contrato_id: int, bloquear: bool = False) -> Contrato:
    # Con bloquear, SELECT ... FOR UPDATE: dos postulaciones simultáneas no se pisan la lista
    contrato = await db.get(Contrato, contrato_id, with_for_update=bloquear)
    if contrato is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contrato no encontrado")
    return contrato


async def _es_dueno(db: AsyncSession, contrato: Contrato, user: CurrentUser) -> bool:
    if not contrato.proyecto_id:
        return False
    proyecto = await db.get(Proyecto, contrato.proyecto_id)
    return proyecto is not None and proyecto.email_gerente == user.email


async def _exigir_dueno(db: AsyncSession, contrato: Contrato, user: CurrentUser) -> None:
    if not await _es_dueno(db, contrato, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el gerente del proyecto puede hacer esto")


def _nombre_estudiante(estudiante: Estudiante) -> str:
    return f"{estudiante.nombre or ''} {estudiante.apellido or ''}".strip() or estudiante.name or ""


def _normalizar_requisitos(body: dict) -> dict:
    """Copia el body con los requisitos validados (sin tocar el diccionario original)."""
    if "requisitos" not in body:
        return body
    return {**body, "requisitos": sanitizar_requisitos(body.get("requisitos"))}


@router.get("/contratos")
async def get_contratos(db: AsyncSession = Depends(get_db)):
    contratos = (await db.scalars(select(Contrato).order_by(Contrato.id))).all()
    return _respuesta_lista("Contratos", list(contratos))


@router.get("/contratoslibres")
async def get_contratos_libres(
    db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(get_current_user)
):
    consulta = select(Contrato).where(Contrato.esta_ocupado.is_(False)).order_by(Contrato.id)
    contratos = list((await db.scalars(consulta)).all())
    perfil = await db.scalar(select(Estudiante).where(Estudiante.email == user.email))
    datos = []
    for contrato in contratos:
        fila = a_dict(contrato)
        if perfil is not None:
            # Cada estudiante ve su propio resultado calculado al vuelo con su perfil actual.
            fila["mi_resultado"] = comparar(perfil, contrato.requisitos)
        datos.append(fila)
    return {"message": "Contratos libres", "count": len(datos), "data": datos}


@router.get("/contratos/{email_gerente}")
async def get_contratos_de_gerente(
    email_gerente: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    email_gerente = normalizar_email(email_gerente)
    consulta = (
        select(Contrato)
        .join(Proyecto, Contrato.proyecto_id == Proyecto.id)
        .where(Proyecto.email_gerente == email_gerente)
        .order_by(Contrato.id)
    )
    contratos = list((await db.scalars(consulta)).all())
    datos = [a_dict(c) for c in contratos]

    # El informe determinista de postulantes solo lo ve la empresa dueña de la oferta.
    if user.email == email_gerente:
        emails = {e for c in contratos for e in (c.postulaciones or []) if e}
        estudiantes: dict[str, Estudiante] = {}
        if emails:
            filas = (await db.scalars(select(Estudiante).where(Estudiante.email.in_(emails)))).all()
            estudiantes = {e.email: e for e in filas}
        for contrato, fila in zip(contratos, datos):
            resultados = []
            for email in contrato.postulaciones or []:
                estudiante = estudiantes.get(email)
                if estudiante is None:
                    continue
                resultados.append({
                    "email": email,
                    "nombre": _nombre_estudiante(estudiante),
                    "resultado": comparar(estudiante, contrato.requisitos),
                })
            fila["resultados_postulantes"] = resultados

    return {"message": "Contratos del gerente", "count": len(datos), "data": datos}


@router.post("/contrato", status_code=status.HTTP_201_CREATED)
async def crear_contrato(
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    proyecto_id = str(body.get("proyecto_id") or "").strip()
    if not proyecto_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Falta el proyecto del contrato")
    proyecto = await db.get(Proyecto, proyecto_id)
    if proyecto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proyecto no encontrado")
    if proyecto.email_gerente != user.email:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No podés crear contratos en un proyecto ajeno")
    if not str(body.get("titulo") or "").strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El contrato necesita un título")

    contrato = Contrato(
        proyecto_id=proyecto.id, titulo="", postulaciones=[], seniority_deseado=[], requisitos=[]
    )
    aplicar_cambios(contrato, _normalizar_requisitos(body), CAMPOS_DE_ESTADO)
    db.add(contrato)
    await db.flush()
    return _respuesta_lista("Contrato creado", [contrato])


@router.put("/contrato/asignar/{contrato_id}")
async def asignar_postulante(
    contrato_id: int,
    body: AsignarRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    contrato = await _obtener(db, contrato_id, bloquear=True)
    await _exigir_dueno(db, contrato, user)
    email = normalizar_email(body.pasante_email)
    if contrato.esta_ocupado:
        raise HTTPException(status.HTTP_409_CONFLICT, "El contrato ya tiene un pasante asignado")
    if email not in (contrato.postulaciones or []):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ese email no se postuló a este contrato")
    contrato.pasante_email = email
    contrato.esta_ocupado = True
    await db.flush()
    # El front lee data[0] en esta respuesta
    return _respuesta_lista("Postulante asignado", [contrato])


@router.put("/contrato/{contrato_id}")
async def actualizar_contrato(
    contrato_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    contrato = await _obtener(db, contrato_id, bloquear=True)
    mensaje = "Contrato actualizado"

    if "postulaciones" in body:
        # Postulación: solo con el propio email, sin duplicados y si el contrato está libre
        pedidos = body["postulaciones"]
        pedidos = pedidos if isinstance(pedidos, list) else [pedidos]
        emails = {normalizar_email(str(e)) for e in pedidos if str(e).strip()}
        if emails != {user.email}:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo podés postularte con tu propio email")
        if not await db.scalar(select(Estudiante.id).where(Estudiante.email == user.email)):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo los estudiantes y graduados pueden postularse")
        if contrato.esta_ocupado:
            raise HTTPException(status.HTTP_409_CONFLICT, "El contrato ya está ocupado")
        actuales = list(contrato.postulaciones or [])
        if user.email in actuales:
            raise HTTPException(status.HTTP_409_CONFLICT, "Ya te postulaste a este contrato")
        contrato.postulaciones = [*actuales, user.email]  # lista nueva para que se detecte el cambio
        mensaje = "Postulación registrada"

    # tiene_postulaciones lo deriva el servidor; el resto de los campos es del gerente dueño
    otros = {k: v for k, v in body.items() if k not in CAMPOS_DE_ESTADO}
    if otros:
        await _exigir_dueno(db, contrato, user)
        aplicar_cambios(contrato, _normalizar_requisitos(otros), CAMPOS_DE_ESTADO)
    contrato.tiene_postulaciones = bool(contrato.postulaciones)
    await db.flush()
    return {"message": mensaje, "data": a_dict(contrato)}


@router.delete("/contrato/{contrato_id}")
async def borrar_contrato(
    contrato_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    contrato = await _obtener(db, contrato_id)
    await _exigir_dueno(db, contrato, user)
    await db.delete(contrato)
    await db.flush()
    return {"message": "Contrato eliminado"}
