DEV = "dev@udela.edu.ar"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


async def _subir(client, nombre, headers, contenido=PNG, tipo="image/png"):
    return await client.put(
        f"/storage/portfolios/{nombre}", content=contenido, headers={**headers, "Content-Type": tipo}
    )


async def test_portfolio_crud(client, registrar_usuario):
    h = await registrar_usuario(DEV, "estudiante")
    assert (await client.get(f"/api/portfolio/{DEV}", headers=h)).status_code == 404

    res = await client.post(
        f"/api/createportfolio/{DEV}", json={"titulo1": "Proyecto 1", "imagenes1": ["a"]}, headers=h
    )
    assert res.status_code == 201, res.text
    assert res.json()["data"]["imagenes1"] == ["a", "", ""]
    assert res.json()["data"]["imagenes2"] == ["", "", ""]

    assert (await client.post(f"/api/createportfolio/{DEV}", json={}, headers=h)).status_code == 409

    res = await client.put(f"/api/updateportfolio/{DEV}", json={"titulo2": "Proyecto 2", "id": 999}, headers=h)
    assert res.status_code == 200
    assert res.json()["data"]["titulo2"] == "Proyecto 2"

    res = await client.get(f"/api/portfolio/{DEV}", headers=h)
    assert res.json()["data"]["titulo1"] == "Proyecto 1"

    assert (await client.delete(f"/api/deleteportfolio/{DEV}", headers=h)).status_code == 200
    assert (await client.get(f"/api/portfolio/{DEV}", headers=h)).status_code == 404


async def test_portfolio_ajeno(client, registrar_usuario):
    await registrar_usuario(DEV, "estudiante")
    h_otro = await registrar_usuario("otro@udela.edu.ar", "estudiante")
    assert (await client.post(f"/api/createportfolio/{DEV}", json={}, headers=h_otro)).status_code == 403


async def test_subir_ver_y_borrar_imagen(client, registrar_usuario):
    h = await registrar_usuario(DEV)
    assert (await _subir(client, "foto.png", {})).status_code == 401

    res = await _subir(client, "123_foto.png", h)
    assert res.status_code == 201, res.text
    assert res.json()["data"]["url"].endswith("/portfolios/123_foto.png")

    res = await client.get("/storage/portfolios/123_foto.png")
    assert res.status_code == 200
    assert res.content == PNG
    assert res.headers["content-type"] == "image/png"

    h_otro = await registrar_usuario("otro@udela.edu.ar")
    assert (await client.delete("/storage/portfolios/123_foto.png", headers=h_otro)).status_code == 403
    assert (await _subir(client, "123_foto.png", h_otro)).status_code == 403

    assert (await client.delete("/storage/portfolios/123_foto.png", headers=h)).status_code == 200
    assert (await client.get("/storage/portfolios/123_foto.png")).status_code == 404


async def test_validaciones_de_imagen(client, registrar_usuario):
    h = await registrar_usuario(DEV)
    assert (await _subir(client, "a.txt", h, b"hola", "text/plain")).status_code == 415
    assert (await _subir(client, ".oculto.png", h)).status_code == 400
    assert (await _subir(client, "%2e%2e%2fsalida.png", h)).status_code in (400, 404)
    assert (await _subir(client, "grande.png", h, b"0" * (5 * 1024 * 1024 + 1))).status_code == 413
    assert (await client.get("/storage/portfolios/.123_foto.png.owner")).status_code == 400


async def test_no_se_pueden_subir_archivos_ejecutables(client, registrar_usuario):
    h = await registrar_usuario(DEV)
    html = b"<script>alert(1)</script>"
    # El Content-Type lo elige el cliente: no alcanza para aceptar el archivo
    assert (await _subir(client, "x.html", h, html, "image/png")).status_code == 415
    assert (await _subir(client, "x.svg", h, b"<svg onload=alert(1)>", "image/svg+xml")).status_code == 415
    assert (await _subir(client, "x.png", h, html, "image/png")).status_code == 415


async def test_imagen_se_sirve_con_headers_seguros(client, registrar_usuario):
    h = await registrar_usuario(DEV)
    assert (await _subir(client, "foto.PNG", h)).status_code == 201
    res = await client.get("/storage/portfolios/foto.PNG")
    assert res.headers["content-type"] == "image/png"
    assert res.headers["x-content-type-options"] == "nosniff"
    assert "sandbox" in res.headers["content-security-policy"]


async def test_borrar_portfolio_limpia_imagenes(client, registrar_usuario):
    h = await registrar_usuario(DEV, "estudiante")
    url_a = (await _subir(client, "a.png", h)).json()["data"]["url"]
    url_b = (await _subir(client, "b.png", h)).json()["data"]["url"]
    await client.post(f"/api/createportfolio/{DEV}", json={"imagenes1": [url_a, url_b]}, headers=h)

    # Al quitar una imagen del portfolio se borra del storage
    await client.put(f"/api/updateportfolio/{DEV}", json={"imagenes1": [url_a]}, headers=h)
    assert (await client.get("/storage/portfolios/b.png")).status_code == 404
    assert (await client.get("/storage/portfolios/a.png")).status_code == 200

    await client.delete(f"/api/deleteportfolio/{DEV}", headers=h)
    assert (await client.get("/storage/portfolios/a.png")).status_code == 404
