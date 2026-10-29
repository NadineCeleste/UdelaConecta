from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser, exigir_mismo_usuario, get_current_user, normalizar_email
from app.models import Contrato, Gerente, Proyecto
from app.schemas.serializacion import a_dict, aplicar_cambios

router = APIRouter(prefix="/api", tags=["proyectos"], dependencies=[Depends(get_current_user)])

NO_EDITABLES = {"id", "email_gerente", "id_gerente", "created_at"}


async def proyecto_a_dict(db: AsyncSession, proyecto: Proyecto) -> dict:
    # El modelo del front tipa "contratos" como string[]: se devuelven los ids
    ids = (await db.scalars(select(Contrato.id).where(Contrato.proyecto_id == proyecto.id))).all()
    return {**a_dict(proyecto), "contratos": [str(i) for i in ids]}


async def buscar_proyecto_de(db: AsyncSession, email: str) -> Proyecto | None:
    return await db.scalar(select(Proyecto).where(Proyecto.email_gerente == normalizar_email(email)))


@router.get("/proyecto/{email}")
async def get_proyecto(email: str, db: AsyncSession = Depends(get_db)):
    proyecto = await buscar_proyecto_de(db, email)
    data = [await proyecto_a_dict(db, proyecto)] if proyecto else []
    return {"message": "Proyecto encontrado" if data else "Sin proyecto", "count": len(data), "data": data}


@router.post("/proyecto", status_code=status.HTTP_201_CREATED)
async def crear_proyecto(
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    # El dueño sale del token; si viene en el body tiene que coincidir
    if body.get("email_gerente"):
        exigir_mismo_usuario(body["email_gerente"], user)
    gerente = await db.scalar(select(Gerente).where(Gerente.email == user.email))
    if gerente is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo un gerente puede crear un proyecto")
    if await buscar_proyecto_de(db, user.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "El gerente ya tiene un proyecto")

    proyecto = Proyecto(email_gerente=user.email, id_gerente=str(gerente.id))
    aplicar_cambios(proyecto, body, NO_EDITABLES)
    db.add(proyecto)
    await db.flush()
    gerente.id_proyecto = proyecto.id
    await db.flush()
    return {"message": "Proyecto creado", "count": 1, "data": [await proyecto_a_dict(db, proyecto)]}


@router.put("/proyecto/{email_gerente}")
async def editar_proyecto(
    email_gerente: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    exigir_mismo_usuario(email_gerente, user)
    proyecto = await buscar_proyecto_de(db, email_gerente)
    if proyecto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proyecto no encontrado")
    aplicar_cambios(proyecto, body, NO_EDITABLES | {"contratos"})
    await db.flush()
    return {"message": "Proyecto actualizado", "count": 1, "data": [await proyecto_a_dict(db, proyecto)]}
