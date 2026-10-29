async def test_registro_login_y_errores(client):
    res = await client.post("/api/auth/register", json={"email": "Ana@Udela.edu.ar", "password": "Secreta123"})
    assert res.status_code == 201
    cuerpo = res.json()
    assert cuerpo["error"] is None
    assert cuerpo["data"]["user"]["email"] == "ana@udela.edu.ar"
    assert cuerpo["data"]["session"]["access_token"]

    duplicado = await client.post("/api/auth/register", json={"email": "ana@udela.edu.ar", "password": "Secreta123"})
    assert duplicado.status_code == 409

    corta = await client.post("/api/auth/register", json={"email": "otro@udela.edu.ar", "password": "123"})
    assert corta.status_code == 400

    invalido = await client.post("/api/auth/register", json={"email": "no-es-email", "password": "Secreta123"})
    assert invalido.status_code == 400

    ok = await client.post("/api/auth/login", json={"email": "ana@udela.edu.ar", "password": "Secreta123"})
    assert ok.status_code == 200
    assert ok.json()["data"]["session"]["access_token"]

    mal = await client.post("/api/auth/login", json={"email": "ana@udela.edu.ar", "password": "incorrecta"})
    assert mal.status_code == 401


async def test_social_y_reset(client):
    assert (await client.post("/api/auth/social", json={"provider": "google"})).status_code == 501
    assert (await client.post("/api/auth/reset-password", json={"email": "x@y.com"})).status_code == 200


async def test_api_exige_token(client):
    assert (await client.get("/api/usuario/ana@udela.edu.ar")).status_code == 401
    malo = {"Authorization": "Bearer token-falso"}
    assert (await client.get("/api/contratos", headers=malo)).status_code == 401


async def test_alta_y_consulta_de_perfil(client, registrar_usuario):
    h = await registrar_usuario("dev@udela.edu.ar")

    res = await client.get("/api/usuario/dev@udela.edu.ar", headers=h)
    assert res.status_code == 404
    assert res.json()["data"] == {"existe": 0, "tabla": None}

    res = await client.post("/api/estudiante", json={"email": "dev@udela.edu.ar"}, headers=h)
    assert res.status_code == 201
    assert (await client.post("/api/gerente", json={"email": "dev@udela.edu.ar"}, headers=h)).status_code == 409

    res = await client.get("/api/usuario/dev@udela.edu.ar", headers=h)
    assert res.json()["data"] == {"existe": 1, "tabla": "estudiante"}

    res = await client.get("/api/usuario/dev@udela.edu.ar/estudiante", headers=h)
    assert res.status_code == 200
    assert res.json()["data"]["email"] == "dev@udela.edu.ar"
    assert (await client.get("/api/usuario/dev@udela.edu.ar/inexistente", headers=h)).status_code == 400

    res = await client.get("/api/estudiantes", headers=h)
    assert res.json()["count"] == 1


async def test_no_se_crea_perfil_de_otro(client, registrar_usuario):
    h = await registrar_usuario("dev@udela.edu.ar")
    res = await client.post("/api/estudiante", json={"email": "otro@udela.edu.ar"}, headers=h)
    assert res.status_code == 403


async def test_actualizar_perfil_ignora_campos_extra(client, registrar_usuario):
    h = await registrar_usuario("dev@udela.edu.ar", "estudiante")
    payload = {
        "email": "dev@udela.edu.ar",
        "nombre": "Valen",
        "posicion": "Trainee",
        "is_disponible": "false",
        "verificado": True,
        "rol": "gerente",
        "proyecto": {"nombre": "no es columna"},
        "habilidades": [{"nombre": "Angular", "nivel": "avanzado"}],
        "idiomas": [{"nombre_idioma": "Inglés", "nivel_idioma": "B2"}],
    }
    res = await client.put("/api/usuario/dev@udela.edu.ar", json=payload, headers=h)
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["nombre"] == "Valen"
    assert data["puesto_actual"] == "Trainee"
    assert data["is_disponible"] is False
    assert data["verificado"] is False
    assert data["rol"] == "estudiante"
    assert data["habilidades"] == [{"nombre_habilidad": "Angular", "nivel_habilidad": "avanzado"}]
    assert data["idiomas"] == [{"nombre_idioma": "Inglés", "nivel_idioma": "B2"}]


async def test_no_se_edita_perfil_ajeno(client, registrar_usuario):
    await registrar_usuario("dev@udela.edu.ar", "estudiante")
    h_otro = await registrar_usuario("otro@udela.edu.ar", "estudiante")
    res = await client.put("/api/usuario/dev@udela.edu.ar", json={"nombre": "X"}, headers=h_otro)
    assert res.status_code == 403


def test_jwt_secret_de_ejemplo_se_rechaza():
    import pytest
    from pydantic import ValidationError

    from app.core.config import Settings

    for secreto in ("CAMBIAR_CLAVE_JWT_64_BYTES_ALEATORIA_AQUI", "corta"):
        with pytest.raises(ValidationError):
            Settings(JWT_SECRET_KEY=secreto)


async def test_login_se_bloquea_tras_intentos_fallidos(client):
    cred = {"email": "bloqueo@udela.edu.ar", "password": "Secreta123"}
    assert (await client.post("/api/auth/register", json=cred)).status_code == 201
    mala = {**cred, "password": "incorrecta"}

    for _ in range(4):
        assert (await client.post("/api/auth/login", json=mala)).status_code == 401
    # Un login correcto antes del límite reinicia el contador
    assert (await client.post("/api/auth/login", json=cred)).status_code == 200

    for _ in range(5):
        assert (await client.post("/api/auth/login", json=mala)).status_code == 401
    res = await client.post("/api/auth/login", json=cred)
    assert res.status_code == 429
    assert "intentos" in res.json()["detail"]


async def test_registrarse_con_email_de_admin_no_da_permisos(client):
    res = await client.post(
        "/api/auth/register", json={"email": "admin@udelaconecta.edu.ar", "password": "Secreta123"}
    )
    assert res.json()["data"]["user"]["is_admin"] is False


async def test_datos_personales_solo_para_el_dueno(client, registrar_usuario):
    h_dev = await registrar_usuario("dev@udela.edu.ar", "estudiante")
    h_otro = await registrar_usuario("empresa@udela.edu.ar", "gerente")
    await client.put(
        "/api/usuario/dev@udela.edu.ar",
        json={"telefono": "1155550101", "fecha_nacimiento": "2001-04-12"},
        headers=h_dev,
    )

    propio = (await client.get("/api/usuario/dev@udela.edu.ar/estudiante", headers=h_dev)).json()["data"]
    assert propio["telefono"] == "1155550101"

    ajeno = (await client.get("/api/usuario/dev@udela.edu.ar/estudiante", headers=h_otro)).json()["data"]
    assert "telefono" not in ajeno and "fecha_nacimiento" not in ajeno
    assert ajeno["email"] == "dev@udela.edu.ar"

    listado = (await client.get("/api/estudiantes", headers=h_otro)).json()["data"]
    assert all("telefono" not in d for d in listado)
