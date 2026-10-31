import time
from collections import defaultdict, deque

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import CurrentUser, create_chat_token, get_current_user_optional
from app.routers.usuarios import buscar_perfil

router = APIRouter(prefix="/api", tags=["chat"])

HEADER_SECRETO = "X-Udela-Secret"
VENTANA_SEGUNDOS = 60

# Mensajes recientes por usuario o IP. Vive en memoria de cada worker, así que el límite
# real es CHAT_MENSAJES_POR_MINUTO por worker; alcanza para frenar abusos del asistente.
_mensajes_recientes: dict[str, deque[float]] = defaultdict(deque)

# Los tests lo reemplazan por un httpx.MockTransport para no llamar a n8n
_transporte: httpx.AsyncBaseTransport | None = None


class ChatRequest(BaseModel):
    mensaje: str = Field(min_length=1, max_length=1000)
    session_id: str = Field(min_length=1, max_length=100)


def _exigir_limite(clave: str) -> None:
    ahora = time.monotonic()
    recientes = _mensajes_recientes[clave]
    while recientes and ahora - recientes[0] > VENTANA_SEGUNDOS:
        recientes.popleft()
    if len(recientes) >= settings.CHAT_MENSAJES_POR_MINUTO:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Enviaste muchos mensajes seguidos. Esperá un minuto y probá de nuevo.",
        )
    recientes.append(ahora)


@router.post("/chat")
async def chat(
    datos: ChatRequest,
    request: Request,
    user: CurrentUser | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    if not settings.N8N_CHAT_WEBHOOK_URL or not settings.N8N_CHAT_SECRET:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "El asistente no está disponible")

    mensaje = datos.mensaje.strip()
    if not mensaje:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El mensaje está vacío")

    ip = request.client.host if request.client else "desconocida"
    _exigir_limite(f"usuario:{user.id}" if user else f"ip:{ip}")

    # El modo lo decide el token, nunca el navegador: n8n elige el agente con este dato
    usuario = None
    if user:
        tabla, _ = await buscar_perfil(db, user.email)
        usuario = {"email": user.email, "rol": tabla or ""}

    payload = {
        "mensaje": mensaje,
        "session_id": datos.session_id,
        "modo": "usuario" if user else "invitado",
        "usuario": usuario,
        # Para las herramientas de n8n: dónde leer datos y con qué token (solo del usuario, minutos)
        "datos_url": settings.CHAT_DATOS_URL.rstrip("/"),
        "token_herramientas": create_chat_token(user.id, user.email) if user else None,
    }

    try:
        async with httpx.AsyncClient(
            timeout=settings.N8N_CHAT_TIMEOUT_SEGUNDOS, transport=_transporte
        ) as cliente:
            res = await cliente.post(
                settings.N8N_CHAT_WEBHOOK_URL,
                json=payload,
                headers={HEADER_SECRETO: settings.N8N_CHAT_SECRET},
            )
        res.raise_for_status()
        respuesta = str(res.json().get("respuesta") or "").strip()
    except (httpx.HTTPError, ValueError, AttributeError):
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "El asistente no pudo responder. Probá de nuevo en unos minutos."
        )
    if not respuesta:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "El asistente no pudo responder. Probá de nuevo en unos minutos."
        )

    return {"message": "Respuesta del asistente", "data": {"respuesta": respuesta}}
