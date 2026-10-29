import pytest

GERENTE = "empresa@udela.edu.ar"
DEV = "dev@udela.edu.ar"


@pytest.fixture
async def escenario(client, registrar_usuario):
    """Gerente con proyecto y un contrato libre, más un estudiante."""
    hg = await registrar_usuario(GERENTE, "gerente")
    hd = await registrar_usuario(DEV, "estudiante")
    res = await client.post(
        "/api/proyecto",
        json={"nombre": "FinTech", "description": "d", "buscando_devs": "true", "email_gerente": GERENTE},
        headers=hg,
    )
    assert res.status_code == 201, res.text
    proyecto = res.json()["data"][0]
    res = await client.post(
        "/api/contrato",
        json={
            "titulo": "Frontend",
            "proyecto_id": proyecto["id"],
            "seniority_deseado": ["Junior"],
            "pasante_email": "",
            "esta_ocupado": True,
        },
        headers=hg,
    )
    assert res.status_code == 201, res.text
    contrato = res.json()["data"][0]
    return {"hg": hg, "hd": hd, "proyecto": proyecto, "contrato": contrato}


async def test_proyecto_crud(client, escenario):
    hg = escenario["hg"]
    res = await client.get(f"/api/proyecto/{GERENTE}", headers=hg)
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["contratos"] == [str(escenario["contrato"]["id"])]

    res = await client.put(f"/api/proyecto/{GERENTE}", json={"nombre": "Nuevo", "buscando_devs": "false"}, headers=hg)
    assert res.status_code == 200
    assert res.json()["data"][0]["nombre"] == "Nuevo"
    assert res.json()["data"][0]["buscando_devs"] is False

    res = await client.get(f"/api/usuario/{GERENTE}/gerente", headers=hg)
    assert res.json()["data"]["id_proyecto"] == escenario["proyecto"]["id"]

    assert (await client.post("/api/proyecto", json={"nombre": "Otro"}, headers=hg)).status_code == 409
    assert (await client.get("/api/proyecto/nadie@udela.edu.ar", headers=hg)).json()["data"] == []


async def test_solo_gerentes_crean_proyecto_propio(client, escenario):
    hd = escenario["hd"]
    assert (await client.post("/api/proyecto", json={"nombre": "X"}, headers=hd)).status_code == 403
    assert (await client.put(f"/api/proyecto/{GERENTE}", json={"nombre": "X"}, headers=hd)).status_code == 403


async def test_contrato_se_crea_libre(client, escenario):
    contrato = escenario["contrato"]
    assert contrato["esta_ocupado"] is False
    assert contrato["postulaciones"] == []
    assert contrato["seniority_deseado"] == ["Junior"]


async def test_crear_contrato_en_proyecto_ajeno(client, escenario):
    res = await client.post(
        "/api/contrato", json={"titulo": "X", "proyecto_id": escenario["proyecto"]["id"]}, headers=escenario["hd"]
    )
    assert res.status_code == 403
    sin_proyecto = await client.post("/api/contrato", json={"titulo": "X"}, headers=escenario["hg"])
    assert sin_proyecto.status_code == 400


async def test_listados_de_contratos(client, escenario):
    hd = escenario["hd"]
    assert (await client.get("/api/contratos", headers=hd)).json()["count"] == 1
    assert (await client.get("/api/contratoslibres", headers=hd)).json()["count"] == 1
    assert (await client.get(f"/api/contratos/{GERENTE}", headers=hd)).json()["count"] == 1
    assert (await client.get("/api/contratos/nadie@udela.edu.ar", headers=hd)).json()["count"] == 0


async def test_flujo_postulacion_y_asignacion(client, escenario):
    hg, hd = escenario["hg"], escenario["hd"]
    cid = escenario["contrato"]["id"]

    # Paso 1 del front: postularse con el propio email
    res = await client.put(f"/api/contrato/{cid}", json={"postulaciones": DEV}, headers=hd)
    assert res.status_code == 200, res.text
    assert res.json()["data"]["postulaciones"] == [DEV]
    assert res.json()["data"]["tiene_postulaciones"] is True

    # Paso 2 del front: marcar tiene_postulaciones (el servidor lo deriva)
    res = await client.put(f"/api/contrato/{cid}", json={"id": cid, "tiene_postulaciones": True}, headers=hd)
    assert res.status_code == 200
    assert res.json()["data"]["tiene_postulaciones"] is True

    duplicada = await client.put(f"/api/contrato/{cid}", json={"postulaciones": DEV}, headers=hd)
    assert duplicada.status_code == 409

    ajena = await client.put(f"/api/contrato/{cid}", json={"postulaciones": "otro@udela.edu.ar"}, headers=hd)
    assert ajena.status_code == 403

    # El estudiante no puede editar otros campos ni asignar
    assert (await client.put(f"/api/contrato/{cid}", json={"titulo": "X"}, headers=hd)).status_code == 403
    asignar = {"pasante_email": DEV}
    assert (await client.put(f"/api/contrato/asignar/{cid}", json=asignar, headers=hd)).status_code == 403

    no_postulado = await client.put(
        f"/api/contrato/asignar/{cid}", json={"pasante_email": "otro@udela.edu.ar"}, headers=hg
    )
    assert no_postulado.status_code == 400

    res = await client.put(f"/api/contrato/asignar/{cid}", json=asignar, headers=hg)
    assert res.status_code == 200
    data = res.json()["data"][0]
    assert data["esta_ocupado"] is True
    assert data["pasante_email"] == DEV

    assert (await client.get("/api/contratoslibres", headers=hd)).json()["count"] == 0
    tarde = await client.put(f"/api/contrato/{cid}", json={"postulaciones": DEV}, headers=hd)
    assert tarde.status_code == 409


async def test_solo_estudiantes_se_postulan(client, escenario):
    cid = escenario["contrato"]["id"]
    res = await client.put(f"/api/contrato/{cid}", json={"postulaciones": GERENTE}, headers=escenario["hg"])
    assert res.status_code == 403


async def test_gerente_edita_y_borra_contrato(client, escenario):
    hg, hd = escenario["hg"], escenario["hd"]
    cid = escenario["contrato"]["id"]
    res = await client.put(f"/api/contrato/{cid}", json={"titulo": "Editado", "modalidad": "hibrido"}, headers=hg)
    assert res.status_code == 200
    assert res.json()["data"]["titulo"] == "Editado"

    assert (await client.delete(f"/api/contrato/{cid}", headers=hd)).status_code == 403
    assert (await client.delete(f"/api/contrato/{cid}", headers=hg)).status_code == 200
    assert (await client.delete(f"/api/contrato/{cid}", headers=hg)).status_code == 404
