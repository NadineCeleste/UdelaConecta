from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser, exigir_mismo_usuario, get_current_user, normalizar_email
from app.models import TABLAS_PERFIL, Estudiante
from app.schemas.auth import EmailRequest
from app.schemas.serializacion import a_dict, aplicar_cambios

router = APIRouter(prefix="/api", tags=["usuarios"], dependencies=[Depends(get_current_user)])

# Campos que el usuario no puede cambiar desde PUT usuario/:email
NO_EDITABLES = {"id", "email", "created_at", "rol", "verificado", "id_proyecto"}

# Datos personales que solo ve el dueño del perfil; el contacto entre usuarios es por email
CAMPOS_PRIVADOS = {"telefono", "fecha_nacimiento"}


def perfil_visible(perfil, user: CurrentUser) -> dict:
    datos = a_dict(perfil)
    if datos.get("email") != user.email:
        for campo in CAMPOS_PRIVADOS:
            datos.pop(campo, None)
    return datos


async def buscar_perfil(db: AsyncSession, email: str):
    """Devuelve (tabla, perfil) del usuario o (None, None) si no está en ninguna tabla."""
    email = normalizar_email(email)
    for tabla, modelo in TABLAS_PERFIL.items():
        perfil = await db.scalar(select(modelo).where(modelo.email == email))
        if perfil is not None:
            return tabla, perfil
    return None, None


def _normalizar_items(items: list, nombre: str, nivel: str) -> list:
    """Acepta {nombre, nivel} (formato del front) y lo guarda como {nombre_x, nivel_x}."""
    normalizados = []
    for item in items:
        if not isinstance(item, dict):
            continue
        valor_nombre = str(item.get(nombre) or item.get("nombre") or "").strip()
        if not valor_nombre:
            continue
        normalizados.append({nombre: valor_nombre, nivel: item.get(nivel) or item.get("nivel") or ""})
    return normalizados


@router.get("/usuario/{email}")
async def check_user_exists(email: str, db: AsyncSession = Depends(get_db)):
    tabla, _ = await buscar_perfil(db, email)
    if tabla is None:
        # El front traduce este 404 a "todavía no tiene perfil"
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "El usuario no existe en la DB", "data": {"existe": 0, "tabla": None}},
        )
    return {"message": "Usuario encontrado", "data": {"existe": 1, "tabla": tabla}}


@router.get("/usuario/{email}/{tabla}")
async def get_usuario(
    email: str,
    tabla: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    modelo = TABLAS_PERFIL.get(tabla)
    if modelo is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Tabla de usuario inválida")
    perfil = await db.scalar(select(modelo).where(modelo.email == normalizar_email(email)))
    if perfil is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    return {"message": "Usuario encontrado", "data": perfil_visible(perfil, user)}


@router.put("/usuario/{email}")
async def update_usuario(
    email: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    exigir_mismo_usuario(email, user)
    tabla, perfil = await buscar_perfil(db, email)
    if perfil is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")

    datos = dict(body)
    # El perfil del front usa "posicion"; en la base es "puesto_actual"
    if "posicion" in datos:
        datos["puesto_actual"] = datos["posicion"]
    if isinstance(datos.get("habilidades"), list):
        datos["habilidades"] = _normalizar_items(datos["habilidades"], "nombre_habilidad", "nivel_habilidad")
    if isinstance(datos.get("idiomas"), list):
        datos["idiomas"] = _normalizar_items(datos["idiomas"], "nombre_idioma", "nivel_idioma")

    aplicar_cambios(perfil, datos, NO_EDITABLES)
    await db.flush()
    return {"message": "Usuario actualizado", "data": {**a_dict(perfil), "rol": tabla}}


def _crear_endpoint_alta(tabla: str):
    modelo = TABLAS_PERFIL[tabla]

    async def crear_usuario(
        body: EmailRequest,
        db: AsyncSession = Depends(get_db),
        user: CurrentUser = Depends(get_current_user),
    ):
        email = exigir_mismo_usuario(body.email, user)
        existente, _ = await buscar_perfil(db, email)
        if existente is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, f"El usuario ya tiene perfil de {existente}")
        perfil = modelo(email=email)
        db.add(perfil)
        await db.flush()
        return {"message": f"Perfil de {tabla} creado", "data": a_dict(perfil)}

    crear_usuario.__name__ = f"crear_{tabla}"
    return crear_usuario


# POST estudiante | gerente | institucion_educativa (rutas explícitas para no tapar otras rutas)
for _tabla in TABLAS_PERFIL:
    router.add_api_route(
        f"/{_tabla}", _crear_endpoint_alta(_tabla), methods=["POST"], status_code=status.HTTP_201_CREATED
    )


@router.get("/estudiantes")
async def get_estudiantes(
    db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(get_current_user)
):
    devs = (await db.scalars(select(Estudiante).order_by(Estudiante.id))).all()
    return {
        "message": "Estudiantes",
        "count": len(devs),
        "data": [perfil_visible(d, user) for d in devs],
    }
