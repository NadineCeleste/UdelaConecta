"""Tests del comparador determinista. No necesitan base de datos ni FastAPI."""

from app.dominio.compatibilidad import comparar, sanitizar_requisitos, texto_fallback


def req(nombre, nivel="principiante", exigencia="deseable", tipo="tecnica"):
    return {"nombre": nombre, "nivel_minimo": nivel, "exigencia": exigencia, "tipo": tipo}


def perfil(*habilidades):
    return {"email": "ana@udela.edu.ar", "habilidades": list(habilidades)}


def test_perfil_sin_habilidades_todo_a_capacitar():
    resultado = comparar(perfil(), [req("Angular", "intermedio", "excluyente"), req("SQL")])

    assert resultado["coincidencia"] == 0
    assert resultado["nivel"] == "baja"
    assert resultado["total_requisitos"] == 2
    assert resultado["total_compatibles"] == 0
    assert [i["nombre"] for i in resultado["a_capacitar"]] == ["Angular", "SQL"]
    assert {i["motivo"] for i in resultado["a_capacitar"]} == {"no_declarada"}
    assert [i["estado"] for i in resultado["checklist"]] == ["falta", "falta"]


def test_perfil_completo_da_cien_y_nivel_alta():
    habilidades = [
        {"nombre_habilidad": "Angular", "nivel_habilidad": "intermedio"},
        {"nombre_habilidad": "SQL", "nivel_habilidad": "avanzado"},
    ]
    resultado = comparar(
        perfil(*habilidades),
        [req("Angular", "intermedio", "excluyente"), req("SQL", "intermedio")],
    )

    assert resultado["coincidencia"] == 100
    assert resultado["nivel"] == "alta"
    assert resultado["total_requisitos"] == 2
    assert resultado["total_compatibles"] == 2
    assert resultado["a_capacitar"] == []
    assert {i["estado"] for i in resultado["checklist"]} == {"cumple"}


def test_nivel_menor_es_parcial():
    habilidades = [{"nombre_habilidad": "Angular", "nivel_habilidad": "principiante"}]
    resultado = comparar(perfil(*habilidades), [req("Angular", "avanzado", "excluyente")])

    assert resultado["coincidencia"] == 0
    assert len(resultado["a_capacitar"]) == 1
    assert resultado["a_capacitar"][0]["motivo"] == "nivel_menor"
    assert resultado["checklist"][0]["estado"] == "parcial"
    assert resultado["checklist"][0]["nivel_declarado"] == "principiante"


def test_sinonimos_y_tildes():
    habilidades = [
        {"nombre_habilidad": "TS", "nivel_habilidad": "intermedio"},
        {"nombre_habilidad": "Postgres", "nivel_habilidad": "intermedio"},
    ]
    resultado = comparar(
        perfil(*habilidades),
        [req("TypeScript", "intermedio"), req("PostgreSQL", "intermedio")],
    )

    assert resultado["coincidencia"] == 100
    assert {i["nombre"] for i in resultado["compatibles"]} == {"TypeScript", "PostgreSQL"}


def test_sinonimo_de_js_y_powerbi():
    habilidades = [{"nombre": "JS", "nivel": "avanzado"}, {"nombre": "PowerBI", "nivel": "intermedio"}]
    resultado = comparar(
        {"habilidades": habilidades},
        [req("JavaScript", "intermedio", "excluyente"), req("Power BI", "principiante")],
    )
    assert resultado["coincidencia"] == 100


def test_se_aprende_no_cuenta_en_el_total():
    resultado = comparar(
        perfil(),
        [req("Docker", "intermedio", "se_aprende"), req("Angular", "intermedio", "excluyente")],
    )

    assert resultado["total_requisitos"] == 1
    assert resultado["se_aprenden"] == ["Docker"]
    assert [i["nombre"] for i in resultado["a_capacitar"]] == ["Angular"]
    assert resultado["checklist"][0]["estado"] == "se_aprende"


def test_blanda_no_cuenta_en_el_total():
    resultado = comparar(
        perfil(),
        [req("Comunicación", tipo="blanda"), req("Angular", "intermedio", "excluyente")],
    )

    assert resultado["total_requisitos"] == 1
    assert resultado["blandas"] == ["Comunicación"]
    assert [i["nombre"] for i in resultado["a_capacitar"]] == ["Angular"]
    assert resultado["checklist"][0]["estado"] == "blanda"


def test_oferta_sin_requisitos_no_divide_por_cero():
    resultado = comparar(perfil(), [])

    assert resultado["sin_requisitos"] is True
    assert resultado["coincidencia"] == 0
    assert resultado["nivel"] == "sin_requisitos"
    assert resultado["total_requisitos"] == 0
    assert resultado["checklist"] == []


def test_requisito_sin_nombre_no_rompe_y_se_registra():
    resultado = comparar(perfil(), [{"nivel_minimo": "avanzado"}, req("Angular")])

    assert resultado["total_requisitos"] == 1
    assert len(resultado["requisitos_invalidos"]) == 1
    assert resultado["requisitos_invalidos"][0]["motivo"] == "sin_nombre"


def test_requisitos_y_habilidades_duplicadas_no_duplican():
    habilidades = [
        {"nombre_habilidad": "Angular", "nivel_habilidad": "intermedio"},
        {"nombre_habilidad": "angular", "nivel_habilidad": "avanzado"},
    ]
    resultado = comparar(
        perfil(*habilidades),
        [req("Angular", "intermedio"), req("ANGULAR", "avanzado", "excluyente")],
    )

    assert resultado["total_requisitos"] == 1
    assert resultado["total_compatibles"] == 1
    assert len(resultado["checklist"]) == 1
    # Se queda con el nivel más alto declarado.
    assert resultado["compatibles"][0]["nivel"] == "avanzado"


def test_sanitizar_requisitos_aplica_defaults_y_descarta_vacios():
    limpios = sanitizar_requisitos([
        {"nombre": " Angular "},
        {"nombre": ""},
        "no-es-un-dict",
        {"nombre": "angular", "nivel_minimo": "raro", "exigencia": "otra", "tipo": "x"},
    ])

    assert limpios == [
        {
            "nombre": "Angular",
            "nivel_minimo": "principiante",
            "exigencia": "deseable",
            "tipo": "tecnica",
        }
    ]


def test_fallback_sin_y_con_brechas():
    assert "no una evaluación" in texto_fallback([]).lower()
    assert "TypeScript" in texto_fallback([{"nombre": "TypeScript"}])
