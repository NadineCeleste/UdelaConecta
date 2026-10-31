import json

import httpx
import pytest

from app.core.config import settings
from app.routers import chat as chat_router

WEBHOOK = "https://n8n.test/webhook/udela-chat"
SECRETO = "secreto-de-prueba"


@pytest.fixture
def n8n(monkeypatch):
    """Simula el webhook de n8n y guarda los pedidos que recibe."""
    estado = {"pedidos": [], "respuesta": httpx.Response(200, json={"respuesta": "Hola, soy el asistente"})}

    def responder(request: httpx.Request) -> httpx.Response:
        estado["pedidos"].append(request)
        return estado["respuesta"]

    monkeypatch.setattr(settings, "N8N_CHAT_WEBHOOK_URL", WEBHOOK)
    monkeypatch.setattr(settings, "N8N_CHAT_SECRET", SECRETO)
    monkeypatch.setattr(settings, "CHAT_DATOS_URL", "https://udela.test/api/chat/datos/")
    monkeypatch.setattr(chat_router, "_transporte", httpx.MockTransport(responder))
    chat_router._mensajes_recientes.clear()
    return estado


def cuerpo(pedido: httpx.Request) -> dict:
    return json.loads(pedido.content)


async def test_sin_configuracion_responde_503(client, monkeypatch):
    monkeypatch.setattr(settings, "N8N_CHAT_WEBHOOK_URL", "")
    res = await client.post("/api/chat", json={"mensaje": "hola", "session_id": "s1"})
    assert res.status_code == 503


async def test_invitado_va_a_n8n_con_el_secreto(client, n8n):
    res = await client.post("/api/chat", json={"mensaje": " ¿Cómo me registro? ", "session_id": "s1"})
    assert res.status_code == 200, res.text
    assert res.json()["data"]["respuesta"] == "Hola, soy el asistente"

    pedido = n8n["pedidos"][0]
    assert str(pedido.url) == WEBHOOK
    assert pedido.headers["X-Udela-Secret"] == SECRETO
    assert cuerpo(pedido) == {
        "mensaje": "¿Cómo me registro?",
        "session_id": "s1",
        "modo": "invitado",
        "usuario": None,
        "datos_url": "https://udela.test/api/chat/datos",
        "token_herramientas": None,
    }


async def test_usuario_logueado_manda_email_y_rol_del_token(client, n8n, registrar_usuario):
    headers = await registrar_usuario("ana@udela.edu.ar", "estudiante")
    res = await client.post(
        "/api/chat",
        json={"mensaje": "¿En qué me postulé?", "session_id": "s2", "modo": "invitado", "usuario": {"email": "otro@x.com"}},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    # Lo que mande el navegador en el body no cambia el modo ni el usuario
    enviado = cuerpo(n8n["pedidos"][0])
    assert enviado["modo"] == "usuario"
    assert enviado["usuario"] == {"email": "ana@udela.edu.ar", "rol": "estudiante"}

    # El token para las herramientas sirve en /api/chat/datos pero no en el resto de la API
    token = {"Authorization": f"Bearer {enviado['token_herramientas']}"}
    assert (await client.get("/api/chat/datos/mi-perfil", headers=token)).status_code == 200
    assert (await client.get("/api/usuario/ana@udela.edu.ar", headers=token)).status_code == 401
    # y el token de sesión normal no sirve para las herramientas
    assert (await client.get("/api/chat/datos/mi-perfil", headers=headers)).status_code == 401


async def test_usuario_sin_perfil_va_con_rol_vacio(client, n8n, registrar_usuario):
    headers = await registrar_usuario("nuevo@udela.edu.ar")
    res = await client.post("/api/chat", json={"mensaje": "hola", "session_id": "s3"}, headers=headers)
    assert res.status_code == 200
    assert cuerpo(n8n["pedidos"][0])["usuario"] == {"email": "nuevo@udela.edu.ar", "rol": ""}


async def test_token_invalido_responde_401(client, n8n):
    res = await client.post(
        "/api/chat",
        json={"mensaje": "hola", "session_id": "s1"},
        headers={"Authorization": "Bearer no-es-un-token"},
    )
    assert res.status_code == 401
    assert n8n["pedidos"] == []


@pytest.mark.parametrize(
    "cuerpo_invalido",
    [{"mensaje": "", "session_id": "s1"}, {"mensaje": "x" * 1001, "session_id": "s1"}, {"mensaje": "hola"}],
)
async def test_valida_el_mensaje(client, n8n, cuerpo_invalido):
    res = await client.post("/api/chat", json=cuerpo_invalido)
    assert res.status_code == 422
    assert n8n["pedidos"] == []


async def test_mensaje_solo_con_espacios_responde_422(client, n8n):
    res = await client.post("/api/chat", json={"mensaje": "   ", "session_id": "s1"})
    assert res.status_code == 422
    assert n8n["pedidos"] == []


@pytest.mark.parametrize(
    "respuesta_n8n",
    [
        httpx.Response(500, json={"message": "Error in workflow"}),
        httpx.Response(200, text="no es json"),
        httpx.Response(200, json={"respuesta": ""}),
        httpx.Response(200, json=["lista"]),
    ],
)
async def test_falla_de_n8n_responde_502(client, n8n, respuesta_n8n):
    n8n["respuesta"] = respuesta_n8n
    res = await client.post("/api/chat", json={"mensaje": "hola", "session_id": "s1"})
    assert res.status_code == 502


async def test_limite_de_mensajes_por_minuto(client, n8n, monkeypatch):
    monkeypatch.setattr(settings, "CHAT_MENSAJES_POR_MINUTO", 2)
    for _ in range(2):
        res = await client.post("/api/chat", json={"mensaje": "hola", "session_id": "s1"})
        assert res.status_code == 200
    res = await client.post("/api/chat", json={"mensaje": "hola", "session_id": "s1"})
    assert res.status_code == 429
    assert len(n8n["pedidos"]) == 2
