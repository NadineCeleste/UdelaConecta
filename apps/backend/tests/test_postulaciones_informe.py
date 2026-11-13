"""Tests de los endpoints de informe, orientación y automatización."""

import json

import httpx
import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.models import InformePostulacion
from app.routers import postulaciones as postulaciones_router

GERENTE = "empresa@udela.edu.ar"
OTRO_GERENTE = "otra@udela.edu.ar"
DEV = "dev@udela.edu.ar"
OTRO_DEV = "otro@udela.edu.ar"
WEBHOOK = "https://n8n.test/webhook/udela-orientacion"
SECRETO = "secreto-automatizacion"


def requisito(nombre, nivel="intermedio", exigencia="excluyente", tipo="tecnica"):
    return {"nombre": nombre, "nivel_minimo": nivel, "exigencia": exigencia, "tipo": tipo}


async def crear_contrato(client, headers, proyecto_id, titulo, requisitos, ocupado=False):
    res = await client.post(
        "/api/contrato",
        json={
            "titulo": titulo,
            "proyecto_id": proyecto_id,
            "seniority_deseado": ["Junior"],
            "esta_ocupado": ocupado,
            "requisitos": requisitos,
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()["data"][0]


async def definir_habilidades(client, headers, email, habilidades):
    res = await client.put(
        f"/api/usuario/{email}", json={"habilidades": habilidades}, headers=headers
    )
    assert res.status_code == 200, res.text


async def postularse(client, headers, contrato_id, email):
    res = await client.put(
        f"/api/contrato/{contrato_id}", json={"postulaciones": email}, headers=headers
    )
    assert res.status_code == 200, res.text


@pytest.fixture
async def escenario(client, registrar_usuario):
    hg = await registrar_usuario(GERENTE, "gerente")
    hd = await registrar_usuario(DEV, "estudiante")
    res = await client.post(
        "/api/proyecto",
        json={"nombre": "FinTech", "description": "d", "buscando_devs": "true", "email_gerente": GERENTE},
        headers=hg,
    )
    assert res.status_code == 201, res.text
    proyecto = res.json()["data"][0]
    contrato = await crear_contrato(
        client,
        hg,
        proyecto["id"],
        "Frontend Angular",
        [requisito("Angular"), requisito("TypeScript")],
    )
    await definir_habilidades(
        client, hd, DEV, [{"nombre": "Angular", "nivel": "intermedio"}]
    )
    await postularse(client, hd, contrato["id"], DEV)
    return {"hg": hg, "hd": hd, "proyecto": proyecto, "contrato": contrato}


@pytest.fixture
def n8n(monkeypatch):
    estado = {
        "pedidos": [],
        "respuesta": httpx.Response(
            200, json={"texto": "Reforzás TypeScript con un proyecto chico.", "modelo": "deepseek-flash"}
        ),
    }

    def responder(request: httpx.Request) -> httpx.Response:
        estado["pedidos"].append(request)
        return estado["respuesta"]

    monkeypatch.setattr(settings, "N8N_ORIENTACION_WEBHOOK_URL", WEBHOOK)
    monkeypatch.setattr(settings, "N8N_AUTOMATION_SECRET", SECRETO)
    monkeypatch.setattr(postulaciones_router, "_transporte", httpx.MockTransport(responder))
    return estado


async def test_mis_postulaciones_devuelve_resultado_determinista(client, escenario):
    res = await client.get("/api/mis-postulaciones", headers=escenario["hd"])
    assert res.status_code == 200, res.text
    data = res.json()["data"]

    assert len(data) == 1
    assert data[0]["contrato"]["titulo"] == "Frontend Angular"
    resultado = data[0]["resultado"]
    assert resultado["coincidencia"] == 50
    assert resultado["nivel"] == "media"
    assert resultado["total_requisitos"] == 2
    assert resultado["total_compatibles"] == 1
    assert [i["nombre"] for i in resultado["compatibles"]] == ["Angular"]
    assert [i["nombre"] for i in resultado["a_capacitar"]] == ["TypeScript"]
    assert data[0]["orientacion"] is None


async def test_orientacion_sin_n8n_guarda_fallback(client, escenario, monkeypatch):
    monkeypatch.setattr(settings, "N8N_ORIENTACION_WEBHOOK_URL", "")
    monkeypatch.setattr(settings, "N8N_AUTOMATION_SECRET", "")

    res = await client.post(
        f"/api/postulaciones/{escenario['contrato']['id']}/orientacion", headers=escenario["hd"]
    )
    assert res.status_code == 200, res.text
    orientacion = res.json()["data"]
    assert orientacion["estado"] == "fallback"
    assert "TypeScript" in orientacion["texto"]
    assert "no una evaluación" in orientacion["texto"].lower()

    # Se guardó y se puede leer
    res = await client.get(
        f"/api/postulaciones/{escenario['contrato']['id']}/orientacion", headers=escenario["hd"]
    )
    assert res.status_code == 200
    assert res.json()["data"]["estado"] == "fallback"


async def test_orientacion_con_n8n_guarda_generado(client, escenario, n8n):
    cid = escenario["contrato"]["id"]
    res = await client.post(
        f"/api/postulaciones/{cid}/orientacion", headers=escenario["hd"]
    )
    assert res.status_code == 200, res.text
    orientacion = res.json()["data"]
    assert orientacion["estado"] == "generado"
    assert orientacion["modelo"] == "deepseek-flash"
    assert orientacion["texto"] == "Reforzás TypeScript con un proyecto chico."

    pedido = n8n["pedidos"][0]
    assert str(pedido.url) == WEBHOOK
    assert pedido.headers["X-Udela-Secret"] == SECRETO
    enviado = json.loads(pedido.content)
    assert enviado == {
        "contrato_id": cid,
        "email": DEV,
        "oferta": "Frontend Angular",
        "compatibles": ["Angular"],
        "a_capacitar": ["TypeScript"],
        "se_aprenden": [],
        "blandas": [],
        "coincidencia": 50,
    }


async def test_regenerar_actualiza_el_mismo_informe(client, escenario, n8n, sesiones):
    cid = escenario["contrato"]["id"]
    assert (
        await client.post(f"/api/postulaciones/{cid}/orientacion", headers=escenario["hd"])
    ).status_code == 200
    n8n["respuesta"] = httpx.Response(
        200, json={"texto": "Otra orientación breve.", "modelo": "deepseek-flash"}
    )
    res = await client.post(f"/api/postulaciones/{cid}/orientacion", headers=escenario["hd"])
    assert res.status_code == 200
    assert res.json()["data"]["texto"] == "Otra orientación breve."

    async with sesiones() as db:
        total = await db.scalar(select(func.count()).select_from(InformePostulacion))
    assert total == 1


async def test_respuesta_invalida_de_ia_usa_fallback(client, escenario, n8n, sesiones):
    n8n["respuesta"] = httpx.Response(200, json={"texto": "No calificás para este puesto."})
    res = await client.post(
        f"/api/postulaciones/{escenario['contrato']['id']}/orientacion", headers=escenario["hd"]
    )
    assert res.status_code == 200
    assert res.json()["data"]["estado"] == "fallback"
    assert "no calificás" not in res.json()["data"]["texto"].lower()

    async with sesiones() as db:
        informe = await db.scalar(select(InformePostulacion))
    assert informe.estado == "fallback"


async def test_texto_demasiado_largo_usa_fallback(client, escenario, n8n):
    n8n["respuesta"] = httpx.Response(200, json={"texto": "x" * 601})
    res = await client.post(
        f"/api/postulaciones/{escenario['contrato']['id']}/orientacion", headers=escenario["hd"]
    )
    assert res.status_code == 200
    assert res.json()["data"]["estado"] == "fallback"


async def test_texto_cortado_usa_fallback(client, escenario, n8n):
    # El modelo se quedó sin tokens a mitad de frase (finish_reason: length)
    n8n["respuesta"] = httpx.Response(
        200, json={"texto": "La brecha principal para la", "modelo": "deepseek-flash"}
    )
    res = await client.post(
        f"/api/postulaciones/{escenario['contrato']['id']}/orientacion", headers=escenario["hd"]
    )
    assert res.status_code == 200
    orientacion = res.json()["data"]
    assert orientacion["estado"] == "fallback"
    assert orientacion["texto"] != "La brecha principal para la"
    assert "TypeScript" in orientacion["texto"]


async def test_texto_que_cierra_con_comillas_o_parentesis_es_valido(client, escenario, n8n):
    for texto in ('Reforzá TypeScript. Es "una orientación, no una evaluación."',
                  "Reforzá TypeScript con práctica (un proyecto chico)."):
        n8n["respuesta"] = httpx.Response(200, json={"texto": texto, "modelo": "deepseek-flash"})
        res = await client.post(
            f"/api/postulaciones/{escenario['contrato']['id']}/orientacion",
            headers=escenario["hd"],
        )
        assert res.status_code == 200
        assert res.json()["data"]["estado"] == "generado", texto
        assert res.json()["data"]["texto"] == texto


@pytest.mark.parametrize("modelo", ["fallback", "sin-brechas"])
async def test_respuesta_sin_ia_de_n8n_queda_como_fallback(client, escenario, n8n, modelo):
    # n8n respondió su propio texto determinista: se conserva, pero no se marca como IA
    texto = "Te falta TypeScript. Podés reforzarlo con un curso corto. Esto es una orientación."
    n8n["respuesta"] = httpx.Response(200, json={"texto": texto, "modelo": modelo})
    res = await client.post(
        f"/api/postulaciones/{escenario['contrato']['id']}/orientacion", headers=escenario["hd"]
    )
    assert res.status_code == 200
    orientacion = res.json()["data"]
    assert orientacion["estado"] == "fallback"
    assert orientacion["modelo"] == modelo
    assert orientacion["texto"] == texto


async def test_estudiante_no_ve_orientacion_ajena(client, escenario, registrar_usuario):
    ho = await registrar_usuario(OTRO_DEV, "estudiante")
    res = await client.get(
        f"/api/postulaciones/{escenario['contrato']['id']}/orientacion", headers=ho
    )
    assert res.status_code == 403
    res = await client.post(
        f"/api/postulaciones/{escenario['contrato']['id']}/orientacion", headers=ho
    )
    assert res.status_code == 403


async def test_gerente_no_ve_orientacion_de_estudiante(client, escenario):
    res = await client.get(
        f"/api/postulaciones/{escenario['contrato']['id']}/orientacion", headers=escenario["hg"]
    )
    assert res.status_code == 403
    res = await client.post(
        f"/api/postulaciones/{escenario['contrato']['id']}/orientacion", headers=escenario["hg"]
    )
    assert res.status_code == 403


async def test_empresa_ve_resultados_solo_en_sus_contratos(client, escenario, registrar_usuario):
    hg = escenario["hg"]
    res = await client.get(f"/api/contratos/{GERENTE}", headers=hg)
    assert res.status_code == 200
    contrato = res.json()["data"][0]
    assert contrato["resultados_postulantes"] == [
        {
            "email": DEV,
            "nombre": "",
            "resultado": {
                "coincidencia": 50,
                "nivel": "media",
                "total_requisitos": 2,
                "total_compatibles": 1,
                "sin_requisitos": False,
                "compatibles": [{"nombre": "Angular", "nivel": "intermedio"}],
                "a_capacitar": [
                    {"nombre": "TypeScript", "nivel_minimo": "intermedio", "motivo": "no_declarada"}
                ],
                "se_aprenden": [],
                "blandas": [],
                "checklist": [
                    {
                        "nombre": "Angular",
                        "estado": "cumple",
                        "nivel_minimo": "intermedio",
                        "nivel_declarado": "intermedio",
                    },
                    {
                        "nombre": "TypeScript",
                        "estado": "falta",
                        "nivel_minimo": "intermedio",
                        "nivel_declarado": None,
                    },
                ],
                "requisitos_invalidos": [],
            },
        }
    ]

    ho = await registrar_usuario(OTRO_GERENTE, "gerente")
    res = await client.get(f"/api/contratos/{GERENTE}", headers=ho)
    assert res.status_code == 200
    assert "resultados_postulantes" not in res.json()["data"][0]


async def test_contratoslibres_trae_mi_resultado(client, escenario):
    res = await client.get("/api/contratoslibres", headers=escenario["hd"])
    assert res.status_code == 200
    contrato = res.json()["data"][0]
    assert contrato["mi_resultado"]["coincidencia"] == 50

    # El gerente no recibe el campo de resultado propio
    res = await client.get("/api/contratoslibres", headers=escenario["hg"])
    assert "mi_resultado" not in res.json()["data"][0]


async def test_oferta_sin_requisitos_no_rompe_ni_genera_orientacion(client, escenario):
    hg, hd = escenario["hg"], escenario["hd"]
    contrato = await crear_contrato(client, hg, escenario["proyecto"]["id"], "Sin requisitos", [])
    await postularse(client, hd, contrato["id"], DEV)

    res = await client.get("/api/mis-postulaciones", headers=hd)
    fila = next(d for d in res.json()["data"] if d["contrato"]["id"] == contrato["id"])
    assert fila["resultado"]["sin_requisitos"] is True
    assert fila["resultado"]["coincidencia"] == 0

    res = await client.post(f"/api/postulaciones/{contrato['id']}/orientacion", headers=hd)
    assert res.status_code == 400
    assert "no tiene requisitos" in res.json()["detail"]


async def test_estudiante_sin_postulaciones_recibe_lista_vacia(client, registrar_usuario):
    hd = await registrar_usuario(OTRO_DEV, "estudiante")
    res = await client.get("/api/mis-postulaciones", headers=hd)
    assert res.status_code == 200
    assert res.json()["data"] == []
    assert res.json()["count"] == 0


async def test_informe_no_incluye_datos_sensibles(client, escenario):
    hd = escenario["hd"]
    res = await client.put(
        f"/api/usuario/{DEV}",
        json={"telefono": "1155550000", "fecha_nacimiento": "2000-01-01"},
        headers=hd,
    )
    assert res.status_code == 200

    res = await client.get("/api/mis-postulaciones", headers=hd)
    texto = json.dumps(res.json())
    assert "telefono" not in texto
    assert "fecha_nacimiento" not in texto
    assert "1155550000" not in texto


async def test_automatizacion_exige_secreto(client, escenario, monkeypatch):
    monkeypatch.setattr(settings, "N8N_AUTOMATION_SECRET", SECRETO)
    assert (await client.get("/api/automatizacion/digests")).status_code == 403
    assert (
        await client.get("/api/automatizacion/digests", headers={"X-Udela-Secret": "otro"})
    ).status_code == 403

    monkeypatch.setattr(settings, "N8N_AUTOMATION_SECRET", "")
    assert (await client.get("/api/automatizacion/digests")).status_code == 503


async def test_digests_devuelve_oportunidades_por_estudiante(client, escenario, monkeypatch):
    monkeypatch.setattr(settings, "N8N_AUTOMATION_SECRET", SECRETO)
    hg, hd = escenario["hg"], escenario["hd"]

    # Oferta libre que el estudiante todavía no pidió; coincide al 100 %.
    libre = await crear_contrato(
        client, hg, escenario["proyecto"]["id"], "Backend Python", [requisito("Angular")]
    )

    res = await client.get(
        "/api/automatizacion/digests", headers={"X-Udela-Secret": SECRETO}
    )
    assert res.status_code == 200, res.text
    datos = res.json()["data"]
    fila = next(d for d in datos if d["email"] == DEV)
    assert fila["nombre"] == ""
    assert fila["ofertas"] == [
        {"contrato_id": libre["id"], "titulo": "Backend Python", "coincidencia": 100, "faltantes": []}
    ]


async def test_automatizacion_guarda_orientacion_con_secreto(client, escenario, monkeypatch):
    monkeypatch.setattr(settings, "N8N_AUTOMATION_SECRET", SECRETO)
    cid = escenario["contrato"]["id"]
    url = f"/api/automatizacion/postulaciones/{cid}/{DEV}/orientacion"

    assert (await client.post(url, json={"texto": "x"})).status_code == 403
    res = await client.post(
        url,
        json={"texto": "Reforzás TypeScript con práctica.", "modelo": "deepseek-flash"},
        headers={"X-Udela-Secret": SECRETO},
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["estado"] == "generado"

    invalida = await client.post(
        url,
        json={"texto": "No calificás para la búsqueda."},
        headers={"X-Udela-Secret": SECRETO},
    )
    assert invalida.status_code == 400

    cortada = await client.post(
        url,
        json={"texto": "La brecha principal para la", "modelo": "deepseek-flash"},
        headers={"X-Udela-Secret": SECRETO},
    )
    assert cortada.status_code == 400

    sin_ia = await client.post(
        url,
        json={"texto": "Te falta TypeScript. Esto es una orientación.", "modelo": "fallback"},
        headers={"X-Udela-Secret": SECRETO},
    )
    assert sin_ia.status_code == 200, sin_ia.text
    assert sin_ia.json()["data"]["estado"] == "fallback"
