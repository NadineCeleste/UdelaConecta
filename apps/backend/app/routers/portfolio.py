from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser, exigir_mismo_usuario, get_current_user, normalizar_email
from app.core.storage import borrar_por_url
from app.models import Portfolio
from app.schemas.serializacion import a_dict, aplicar_cambios

router = APIRouter(prefix="/api", tags=["portfolio"], dependencies=[Depends(get_current_user)])

BLOQUES_IMAGENES = ("imagenes1", "imagenes2", "imagenes3")
NO_EDITABLES = {"id", "email"}


def _imagenes(portfolio: Portfolio) -> set[str]:
    return {u for b in BLOQUES_IMAGENES for u in (getattr(portfolio, b) or []) if u}


def _normalizar(datos: dict) -> dict:
    """Cada bloque de imágenes queda con exactamente 3 posiciones (strings vacíos si faltan)."""
    datos = dict(datos)
    for bloque in BLOQUES_IMAGENES:
        if bloque in datos:
            lista = [str(u or "") for u in (datos[bloque] or [])][:3]
            datos[bloque] = lista + [""] * (3 - len(lista))
    return datos


async def _buscar(db: AsyncSession, email: str) -> Portfolio | None:
    return await db.scalar(select(Portfolio).where(Portfolio.email == normalizar_email(email)))


@router.get("/portfolio/{email}")
async def get_portfolio(email: str, db: AsyncSession = Depends(get_db)):
    portfolio = await _buscar(db, email)
    if portfolio is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "El usuario no tiene portfolio", "data": None},
        )
    return {"message": "Portfolio encontrado", "data": a_dict(portfolio)}


@router.post("/createportfolio/{email}", status_code=status.HTTP_201_CREATED)
async def crear_portfolio(
    email: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    email = exigir_mismo_usuario(email, user)
    if await _buscar(db, email):
        raise HTTPException(status.HTTP_409_CONFLICT, "El usuario ya tiene portfolio")
    portfolio = Portfolio(email=email)
    aplicar_cambios(portfolio, _normalizar(body), NO_EDITABLES)
    db.add(portfolio)
    await db.flush()
    return {"message": "Portfolio creado", "data": a_dict(portfolio)}


@router.put("/updateportfolio/{email}")
async def actualizar_portfolio(
    email: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    email = exigir_mismo_usuario(email, user)
    portfolio = await _buscar(db, email)
    if portfolio is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Portfolio no encontrado")
    antes = _imagenes(portfolio)
    aplicar_cambios(portfolio, _normalizar(body), NO_EDITABLES)
    datos = a_dict(portfolio)
    # Commit antes de tocar el disco: si la base falla, las imágenes siguen ahí
    await db.commit()
    # Las imágenes que dejaron de usarse se borran del storage (E-28)
    for url in antes - _imagenes(portfolio):
        borrar_por_url(url, email)
    return {"message": "Portfolio actualizado", "data": datos}


@router.delete("/deleteportfolio/{email}")
async def borrar_portfolio(
    email: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    email = exigir_mismo_usuario(email, user)
    portfolio = await _buscar(db, email)
    if portfolio is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Portfolio no encontrado")
    imagenes = _imagenes(portfolio)
    await db.delete(portfolio)
    await db.commit()
    for url in imagenes:
        borrar_por_url(url, email)
    return {"message": "Portfolio eliminado"}
