from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    id: str
    email: str


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(email: str, user_id: str) -> str:
    ahora = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "iat": ahora,
        "exp": ahora + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    # Un token del asistente (con "aud") falla acá: no sirve para el resto de la API
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


# Token corto que el backend le pasa a n8n para que el asistente lea datos del usuario
# en /api/chat/datos/*. Solo vale para esas rutas y vence en minutos.
AUDIENCIA_CHAT = "udela-chat"


def create_chat_token(user_id: str, email: str) -> str:
    ahora = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "aud": AUDIENCIA_CHAT,
        "iat": ahora,
        "exp": ahora + timedelta(minutes=settings.CHAT_TOKEN_MINUTOS),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _no_autenticado(detalle: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detalle,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser | None:
    if credentials is None:
        return None
    from app.models.entities import AuthUser  # import diferido para evitar ciclos

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise _no_autenticado("Token inválido o vencido")
    user = await db.get(AuthUser, payload.get("sub"))
    if user is None or not user.is_active:
        raise _no_autenticado("Usuario inexistente o inactivo")
    return CurrentUser(id=user.id, email=user.email)


async def get_current_user(
    user: CurrentUser | None = Depends(get_current_user_optional),
) -> CurrentUser:
    if user is None:
        raise _no_autenticado("No autenticado")
    return user


async def get_usuario_chat(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """Usuario de un token del asistente; el token de sesión normal no sirve acá."""
    if credentials is None:
        raise _no_autenticado("No autenticado")
    from app.models.entities import AuthUser  # import diferido para evitar ciclos

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            audience=AUDIENCIA_CHAT,
        )
    except jwt.PyJWTError:
        raise _no_autenticado("Token del asistente inválido o vencido")
    user = await db.get(AuthUser, payload.get("sub"))
    if user is None or not user.is_active:
        raise _no_autenticado("Usuario inexistente o inactivo")
    return CurrentUser(id=user.id, email=user.email)


def normalizar_email(email: str) -> str:
    return (email or "").strip().lower()


def exigir_mismo_usuario(email: str, user: CurrentUser) -> str:
    """El recurso identificado por email solo lo puede modificar su dueño."""
    email = normalizar_email(email)
    if email != user.email:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No podés modificar recursos de otro usuario")
    return email
