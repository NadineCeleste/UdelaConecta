"""Datos de solo lectura para las herramientas del asistente (workflow de n8n).

El usuario sale siempre del token del asistente (create_chat_token), nunca de un parámetro:
aunque alguien convenza al modelo de pedir datos de otro email, no hay forma de hacerlo.
Las respuestas son resúmenes cortos (sin teléfonos, fechas de nacimiento ni emails de
postulantes ajenos) para no mandarle al modelo más de lo necesario.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser, get_usuario_chat
from app.models import Contrato, Estudiante, Portfolio, Proyecto
from app.routers.usuarios import buscar_perfil

router = APIRouter(prefix="/api/chat/datos", tags=["chat"])

MAX_RESULTADOS = 10
MAX_TEXTO = 300


def _recortar(texto: str | None, largo: int = MAX_TEXTO) -> str:
    texto = (texto or "").strip()
    return texto if len(texto) <= largo else texto[: largo - 1].rstrip() + "…"


def _nombres(items: list | None, clave: str) -> list[str]:
    """Nombres de habilidades/idiomas: acepta strings o {clave: ...} (formato del front)."""
    nombres = []
    for item in items or []:
        valor = item.get(clave) or item.get("nombre") if isinstance(item, dict) else item
        if valor and str(valor).strip():
            nombres.append(str(valor).strip())
    return nombres


def _skills(estudiante: Estudiante) -> list[str]:
    vistas, resultado = set(), []
    for nombre in _nombres(estudiante.skills, "nombre_habilidad") + _nombres(
        estudiante.habilidades, "nombre_habilidad"
    ):
        if nombre.lower() not in vistas:
            vistas.add(nombre.lower())
            resultado.append(nombre)
    return resultado


def _proyectos_portfolio(portfolio: Portfolio | None) -> list[dict]:
    if portfolio is None:
        return []
    proyectos = []
    for i in (1, 2, 3):
        titulo = getattr(portfolio, f"titulo{i}")
        if titulo:
            proyectos.append({
                "titulo": titulo,
                "descripcion": _recortar(getattr(portfolio, f"descripcion{i}"), 200),
                "tiene_repositorio": bool(getattr(portfolio, f"repositorio{i}")),
            })
    return proyectos


def _oferta(contrato: Contrato, proyecto: Proyecto | None) -> dict:
    return {
        "id": contrato.id,
        "titulo": contrato.titulo,
        "tipo": contrato.tipo or "",
        "descripcion": _recortar(contrato.descripcion),
        "modalidad": contrato.modalidad or "",
        "seniority": contrato.seniority_deseado or [],
        "desde": contrato.start_date or "",
        "hasta": contrato.end_date or "",
        "proyecto": proyecto.nombre if proyecto else "",
    }


async def _candidato(db: AsyncSession, estudiante: Estudiante) -> dict:
    portfolio = await db.scalar(select(Portfolio).where(Portfolio.email == estudiante.email))
    return {
        "nombre": f"{estudiante.nombre or ''} {estudiante.apellido or ''}".strip() or estudiante.name or "",
        "email": estudiante.email,
        "puesto_actual": estudiante.puesto_actual or "",
        "descripcion": _recortar(estudiante.descripcion, 200),
        "skills": _skills(estudiante),
        "idiomas": _nombres(estudiante.idiomas, "nombre_idioma"),
        "disponible": bool(estudiante.is_disponible),
        "proyectos_portfolio": [p["titulo"] for p in _proyectos_portfolio(portfolio)],
    }


async def _exigir_rol(db: AsyncSession, user: CurrentUser, rol: str):
    tabla, perfil = await buscar_perfil(db, user.email)
    if tabla != rol:
        quien = "estudiantes" if rol == "estudiante" else "empresas"
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Esta consulta es solo para {quien}")
    return perfil


@router.get("/ofertas")
async def ofertas(
    texto: str = Query("", max_length=100),
    modalidad: str = Query("", max_length=30),
    db: AsyncSession = Depends(get_db),
):
    """Ofertas libres; pública, igual que lo que ve un invitado al registrarse."""
    filas = (
        await db.execute(
            select(Contrato, Proyecto)
            .outerjoin(Proyecto, Contrato.proyecto_id == Proyecto.id)
            .where(Contrato.esta_ocupado.is_(False))
            .order_by(Contrato.id.desc())
        )
    ).all()
    palabras = [p for p in texto.lower().split() if p]
    resultado = []
    for contrato, proyecto in filas:
        oferta = _oferta(contrato, proyecto)
        if modalidad and modalidad.lower() not in oferta["modalidad"].lower():
            continue
        buscable = " ".join(
            [contrato.titulo, contrato.tipo or "", contrato.descripcion or "", " ".join(oferta["seniority"])]
        ).lower()
        if palabras and not any(p in buscable for p in palabras):
            continue
        resultado.append(oferta)
    return {"message": "Ofertas libres", "count": len(resultado[:MAX_RESULTADOS]), "data": resultado[:MAX_RESULTADOS]}


@router.get("/mi-perfil")
async def mi_perfil(user: CurrentUser = Depends(get_usuario_chat), db: AsyncSession = Depends(get_db)):
    tabla, perfil = await buscar_perfil(db, user.email)
    if perfil is None:
        return {"message": "Sin perfil", "data": {"rol": "", "faltantes": ["elegir un rol"]}}

    datos = {
        "rol": tabla,
        "nombre": f"{perfil.nombre or ''} {perfil.apellido or ''}".strip(),
        "descripcion": _recortar(perfil.descripcion),
    }
    faltantes = []
    if not datos["nombre"]:
        faltantes.append("nombre y apellido")
    if not datos["descripcion"]:
        faltantes.append("descripción")

    if tabla == "estudiante":
        portfolio = await db.scalar(select(Portfolio).where(Portfolio.email == user.email))
        proyectos = _proyectos_portfolio(portfolio)
        datos |= {
            "puesto_actual": perfil.puesto_actual or "",
            "skills": _skills(perfil),
            "idiomas": _nombres(perfil.idiomas, "nombre_idioma"),
            "disponible": bool(perfil.is_disponible),
            "proyectos_portfolio": proyectos,
        }
        if not datos["skills"]:
            faltantes.append("skills")
        if not datos["idiomas"]:
            faltantes.append("idiomas")
        if not proyectos:
            faltantes.append("al menos un proyecto en el portfolio")
        elif len(proyectos) < 3:
            faltantes.append(f"más proyectos en el portfolio (tiene {len(proyectos)} de 3)")
        if any(not p["tiene_repositorio"] for p in proyectos):
            faltantes.append("link al repositorio en todos los proyectos")
    elif tabla == "gerente":
        proyecto = await db.scalar(select(Proyecto).where(Proyecto.email_gerente == user.email))
        datos["proyecto"] = proyecto.nombre if proyecto else ""
        if proyecto is None:
            faltantes.append("crear el proyecto en Mi proyecto")

    datos["faltantes"] = faltantes
    return {"message": "Mi perfil", "data": datos}


@router.get("/mis-postulaciones")
async def mis_postulaciones(user: CurrentUser = Depends(get_usuario_chat), db: AsyncSession = Depends(get_db)):
    await _exigir_rol(db, user, "estudiante")
    filas = (
        await db.execute(
            select(Contrato, Proyecto)
            .outerjoin(Proyecto, Contrato.proyecto_id == Proyecto.id)
            .order_by(Contrato.id.desc())
        )
    ).all()
    resultado = []
    for contrato, proyecto in filas:
        postulado = user.email in (contrato.postulaciones or [])
        asignado = contrato.pasante_email == user.email
        if not (postulado or asignado):
            continue
        if asignado:
            estado = "asignado a vos"
        elif contrato.esta_ocupado:
            estado = "cubierto por otra persona"
        else:
            estado = "en revisión"
        resultado.append({"titulo": contrato.titulo, "proyecto": proyecto.nombre if proyecto else "", "estado": estado})
    return {"message": "Mis postulaciones", "count": len(resultado), "data": resultado[:MAX_RESULTADOS]}


@router.get("/mis-ofertas")
async def mis_ofertas(user: CurrentUser = Depends(get_usuario_chat), db: AsyncSession = Depends(get_db)):
    await _exigir_rol(db, user, "gerente")
    contratos = (
        await db.scalars(
            select(Contrato)
            .join(Proyecto, Contrato.proyecto_id == Proyecto.id)
            .where(Proyecto.email_gerente == user.email)
            .order_by(Contrato.id.desc())
        )
    ).all()
    resultado = [
        {
            "id": c.id,
            "titulo": c.titulo,
            "estado": "asignada" if c.esta_ocupado else ("con postulantes" if c.postulaciones else "sin postulantes"),
            "postulantes": len(c.postulaciones or []),
            "pasante_asignado": c.pasante_email or "",
        }
        for c in contratos
    ]
    return {"message": "Mis ofertas", "count": len(resultado), "data": resultado[:MAX_RESULTADOS]}


@router.get("/postulantes/{contrato_id}")
async def postulantes(
    contrato_id: int, user: CurrentUser = Depends(get_usuario_chat), db: AsyncSession = Depends(get_db)
):
    await _exigir_rol(db, user, "gerente")
    contrato = await db.get(Contrato, contrato_id)
    proyecto = await db.get(Proyecto, contrato.proyecto_id) if contrato and contrato.proyecto_id else None
    # Misma respuesta si no existe o es de otra empresa: no se revela qué ofertas existen
    if contrato is None or proyecto is None or proyecto.email_gerente != user.email:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No encontré esa oferta entre las tuyas")
    resultado = []
    for email in (contrato.postulaciones or [])[:MAX_RESULTADOS]:
        estudiante = await db.scalar(select(Estudiante).where(Estudiante.email == email))
        if estudiante is not None:
            resultado.append(await _candidato(db, estudiante))
    return {"message": f"Postulantes de {contrato.titulo}", "count": len(resultado), "data": resultado}


@router.get("/candidatos")
async def candidatos(
    skills: str = Query("", max_length=200),
    user: CurrentUser = Depends(get_usuario_chat),
    db: AsyncSession = Depends(get_db),
):
    await _exigir_rol(db, user, "gerente")
    buscadas = [s.strip().lower() for s in skills.replace(",", " ").split() if s.strip()]
    estudiantes = (
        await db.scalars(select(Estudiante).where(Estudiante.is_disponible.is_(True)).order_by(Estudiante.id))
    ).all()
    puntuados = []
    for estudiante in estudiantes:
        propias = [s.lower() for s in _skills(estudiante)]
        coincidencias = sum(1 for b in buscadas if any(b in p for p in propias))
        if buscadas and not coincidencias:
            continue
        puntuados.append((coincidencias, estudiante))
    puntuados.sort(key=lambda par: -par[0])
    resultado = [await _candidato(db, e) for _, e in puntuados[:MAX_RESULTADOS]]
    return {"message": "Candidatos disponibles", "count": len(resultado), "data": resultado}
