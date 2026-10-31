from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.config import settings
from app.core.security import AUDIENCIA_CHAT, create_chat_token, decode_access_token

GERENTE = "empresa@udela.edu.ar"
OTRO_GERENTE = "otra@udela.edu.ar"
DEV = "dev@udela.edu.ar"
DEV2 = "dev2@udela.edu.ar"


def token_chat(headers: dict) -> dict:
    """Convierte los headers de sesión en los del token del asistente del mismo usuario."""
    payload = decode_access_token(headers["Authorization"].removeprefix("Bearer "))
    return {"Authorization": f"Bearer {create_chat_token(payload['sub'], payload['email'])}"}


async def crear_oferta(client, headers, proyecto_id, titulo, **extra):
    res = await client.post(
        "/api/contrato", json={"titulo": titulo, "proyecto_id": proyecto_id, **extra}, headers=headers
    )
    assert res.status_code == 201, res.text
    return res.json()["data"][0]


@pytest.fixture
async def escenario(client, registrar_usuario):
    """Empresa con dos ofertas (una con postulante), otra empresa y dos estudiantes."""
    hg = await registrar_usuario(GERENTE, "gerente")
    hg2 = await registrar_usuario(OTRO_GERENTE, "gerente")
    hd = await registrar_usuario(DEV, "estudiante")
    hd2 = await registrar_usuario(DEV2, "estudiante")

    await client.put(
        f"/api/usuario/{DEV}",
        json={
            "nombre": "Valentina",
            "apellido": "Gómez",
            "telefono": "1155550101",
            "fecha_nacimiento": "2001-04-12",
            "habilidades": [{"nombre": "Angular", "nivel": "intermedio"}],
            "idiomas": [{"nombre": "Inglés", "nivel": "B2"}],
        },
        headers=hd,
    )
    await client.put(f"/api/usuario/{DEV2}", json={"habilidades": [{"nombre": "Python", "nivel": "alto"}]}, headers=hd2)

    proyecto = (await client.post("/api/proyecto", json={"nombre": "FinTech"}, headers=hg)).json()["data"][0]
    otro = (await client.post("/api/proyecto", json={"nombre": "Otra"}, headers=hg2)).json()["data"][0]
    frontend = await crear_oferta(
        client, hg, proyecto["id"], "Frontend Angular", modalidad="remoto", descripcion="x" * 500
    )
    backend = await crear_oferta(client, hg, proyecto["id"], "Backend Python", modalidad="presencial")
    ajena = await crear_oferta(client, hg2, otro["id"], "QA")

    res = await client.put(f"/api/contrato/{frontend['id']}", json={"postulaciones": DEV}, headers=hd)
    assert res.status_code == 200, res.text
    res = await client.put(f"/api/contrato/{ajena['id']}", json={"postulaciones": DEV}, headers=hd)
    assert res.status_code == 200, res.text
    res = await client.put(f"/api/contrato/asignar/{ajena['id']}", json={"pasante_email": DEV}, headers=hg2)
    assert res.status_code == 200, res.text

    return {
        "gerente": token_chat(hg),
        "otro_gerente": token_chat(hg2),
        "dev": token_chat(hd),
        "frontend": frontend,
        "backend": backend,
        "ajena": ajena,
    }


async def test_ofertas_es_publica_y_filtra(client, escenario):
    res = await client.get("/api/chat/datos/ofertas")
    assert res.status_code == 200
    titulos = {o["titulo"] for o in res.json()["data"]}
    # La oferta asignada ya no está libre
    assert titulos == {"Frontend Angular", "Backend Python"}

    oferta = next(o for o in res.json()["data"] if o["titulo"] == "Frontend Angular")
    assert "postulaciones" not in oferta and "pasante_email" not in oferta
    assert len(oferta["descripcion"]) <= 300
    assert oferta["proyecto"] == "FinTech"

    res = await client.get("/api/chat/datos/ofertas", params={"texto": "python"})
    assert [o["titulo"] for o in res.json()["data"]] == ["Backend Python"]
    res = await client.get("/api/chat/datos/ofertas", params={"modalidad": "remoto"})
    assert [o["titulo"] for o in res.json()["data"]] == ["Frontend Angular"]


async def test_mi_perfil_de_estudiante_sin_datos_privados(client, escenario):
    res = await client.get("/api/chat/datos/mi-perfil", headers=escenario["dev"])
    assert res.status_code == 200
    datos = res.json()["data"]
    assert datos["rol"] == "estudiante"
    assert datos["skills"] == ["Angular"]
    assert datos["idiomas"] == ["Inglés"]
    assert "telefono" not in datos and "fecha_nacimiento" not in datos
    assert "descripción" in datos["faltantes"]
    assert "al menos un proyecto en el portfolio" in datos["faltantes"]


async def test_mi_perfil_de_gerente(client, escenario):
    datos = (await client.get("/api/chat/datos/mi-perfil", headers=escenario["gerente"])).json()["data"]
    assert datos["rol"] == "gerente"
    assert datos["proyecto"] == "FinTech"


async def test_mis_postulaciones(client, escenario):
    res = await client.get("/api/chat/datos/mis-postulaciones", headers=escenario["dev"])
    assert res.status_code == 200
    estados = {p["titulo"]: p["estado"] for p in res.json()["data"]}
    assert estados == {"Frontend Angular": "en revisión", "QA": "asignado a vos"}


async def test_mis_ofertas(client, escenario):
    res = await client.get("/api/chat/datos/mis-ofertas", headers=escenario["gerente"])
    assert res.status_code == 200
    ofertas = {o["titulo"]: o for o in res.json()["data"]}
    assert set(ofertas) == {"Frontend Angular", "Backend Python"}
    assert ofertas["Frontend Angular"]["postulantes"] == 1
    assert ofertas["Frontend Angular"]["estado"] == "con postulantes"
    assert ofertas["Backend Python"]["estado"] == "sin postulantes"


async def test_postulantes_solo_de_ofertas_propias(client, escenario):
    url = f"/api/chat/datos/postulantes/{escenario['frontend']['id']}"
    res = await client.get(url, headers=escenario["gerente"])
    assert res.status_code == 200
    [candidato] = res.json()["data"]
    assert candidato["email"] == DEV
    assert candidato["skills"] == ["Angular"]
    assert "telefono" not in candidato and "fecha_nacimiento" not in candidato

    assert (await client.get(url, headers=escenario["otro_gerente"])).status_code == 404
    assert (await client.get("/api/chat/datos/postulantes/9999", headers=escenario["gerente"])).status_code == 404


async def test_candidatos_por_skills(client, escenario):
    res = await client.get("/api/chat/datos/candidatos", params={"skills": "python"}, headers=escenario["gerente"])
    assert res.status_code == 200
    assert [c["email"] for c in res.json()["data"]] == [DEV2]

    todos = await client.get("/api/chat/datos/candidatos", headers=escenario["gerente"])
    assert {c["email"] for c in todos.json()["data"]} == {DEV, DEV2}


@pytest.mark.parametrize(
    "ruta,rol",
    [
        ("/api/chat/datos/mis-postulaciones", "gerente"),
        ("/api/chat/datos/mis-ofertas", "dev"),
        ("/api/chat/datos/candidatos", "dev"),
    ],
)
async def test_cada_rol_solo_ve_lo_suyo(client, escenario, ruta, rol):
    assert (await client.get(ruta, headers=escenario[rol])).status_code == 403


@pytest.mark.parametrize("ruta", ["mi-perfil", "mis-postulaciones", "mis-ofertas", "candidatos"])
async def test_rutas_privadas_exigen_token_del_asistente(client, escenario, ruta):
    assert (await client.get(f"/api/chat/datos/{ruta}")).status_code == 401


async def test_token_vencido_o_con_otra_audiencia(client, escenario):
    payload = decode_access_token(
        jwt.encode(
            {"sub": "x", "email": DEV, "exp": datetime.now(timezone.utc) + timedelta(minutes=1)},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
    )
    vencido = jwt.encode(
        {**payload, "aud": AUDIENCIA_CHAT, "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    otra_audiencia = jwt.encode(
        {**payload, "aud": "otra-cosa"}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    for token in (vencido, otra_audiencia):
        res = await client.get("/api/chat/datos/mi-perfil", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 401
