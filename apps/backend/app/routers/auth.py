import logging
from datetime import datetime, timedelta, timezone

from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    hash_password,
    normalizar_email,
    verify_password,
)
from app.models import AuthUser
from app.schemas.auth import Credenciales, ResetPasswordRequest, SocialRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])
log = logging.getLogger(__name__)

PASSWORD_MIN = 6
PASSWORD_MAX_BYTES = 72  # límite de bcrypt


def _respuesta_sesion(user: AuthUser) -> dict:
    """Mismo sobre que devolvía el cliente de auth original: { data: { user, session }, error }."""
    usuario = {"id": user.id, "email": user.email, "is_admin": bool(user.is_admin)}
    token = create_access_token(user.email, user.id)
    return {
        "data": {
            "user": usuario,
            "session": {"user": usuario, "access_token": token, "token_type": "bearer"},
        },
        "error": None,
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: Credenciales, db: AsyncSession = Depends(get_db)):
    try:
        email = normalizar_email(validate_email(body.email, check_deliverability=False).normalized)
    except EmailNotValidError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El email no es válido")
    if len(body.password) < PASSWORD_MIN:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"La contraseña debe tener al menos {PASSWORD_MIN} caracteres",
        )
    if len(body.password.encode("utf-8")) > PASSWORD_MAX_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La contraseña es demasiado larga")

    existente = await db.scalar(select(AuthUser).where(AuthUser.email == email))
    if existente:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe una cuenta con ese email")

    user = AuthUser(email=email, password_hash=hash_password(body.password))
    db.add(user)
    await db.flush()
    return _respuesta_sesion(user)


def _bloqueada_hasta(user: AuthUser) -> datetime | None:
    if user.locked_until is None:
        return None
    hasta = user.locked_until
    if hasta.tzinfo is None:  # SQLite devuelve fechas sin zona horaria
        hasta = hasta.replace(tzinfo=timezone.utc)
    return hasta if hasta > datetime.now(timezone.utc) else None


@router.post("/login")
async def login(body: Credenciales, db: AsyncSession = Depends(get_db)):
    email = normalizar_email(body.email)
    user = await db.scalar(select(AuthUser).where(AuthUser.email == email).with_for_update())
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email o contraseña incorrectos")

    hasta = _bloqueada_hasta(user)
    if hasta is not None:
        minutos = max(1, round((hasta - datetime.now(timezone.utc)).total_seconds() / 60))
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Demasiados intentos fallidos. Probá de nuevo en {minutos} minuto(s)",
        )

    if not verify_password(body.password, user.password_hash):
        user.failed_logins = (user.failed_logins or 0) + 1
        if user.failed_logins >= settings.LOGIN_MAX_INTENTOS:
            user.failed_logins = 0
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=settings.LOGIN_BLOQUEO_MINUTOS)
            log.warning("Cuenta %s bloqueada por intentos fallidos", email)
        # El HTTPException hace rollback en get_db: el contador se guarda antes
        await db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email o contraseña incorrectos")

    if user.failed_logins or user.locked_until:
        user.failed_logins = 0
        user.locked_until = None
    return _respuesta_sesion(user)


@router.post("/social", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def social(body: SocialRequest):
    raise HTTPException(
        status.HTTP_501_NOT_IMPLEMENTED,
        f"El inicio de sesión con {body.provider} todavía no está disponible",
    )


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest):
    # No hay servidor de correo configurado: se responde igual para no revelar qué emails existen
    log.info("Pedido de recuperación de contraseña para %s (sin SMTP configurado)", body.email)
    return {"message": "Si el email está registrado, vas a recibir instrucciones para recuperar la contraseña"}
