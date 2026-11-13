"""Comparador determinista entre el perfil declarado y los requisitos de una oferta.

Este módulo es Python puro: no importa FastAPI, SQLAlchemy, n8n ni ningún servicio de IA.
Recibe diccionarios u objetos simples y devuelve un informe reproducible.

Reglas centrales:
- Solo puntúan los requisitos técnicos con exigencia ``excluyente`` o ``deseable``.
- Las habilidades blandas no se puntúan: se listan para evaluar en entrevista.
- Lo que "se aprende en el puesto" no cuenta como brecha: se lista como oportunidad.
- El resultado nunca bloquea una postulación; es una orientación.
"""

from __future__ import annotations

import unicodedata
from typing import Any

NIVELES: dict[str, int] = {
    "principiante": 1,
    "basico": 1,
    "intermedio": 2,
    "avanzado": 3,
    "experto": 4,
}

NIVELES_VALIDOS = ("principiante", "intermedio", "avanzado")
EXIGENCIAS_VALIDAS = ("excluyente", "deseable", "se_aprende")
TIPOS_VALIDOS = ("tecnica", "blanda")

# Sinónimos: la clave es el nombre normalizado y el valor el nombre canónico.
SINONIMOS: dict[str, str] = {
    "js": "javascript",
    "ts": "typescript",
    "postgres": "postgresql",
    "node": "nodejs",
    "node js": "nodejs",
    "nodejs": "nodejs",
    "powerbi": "power bi",
    "gh actions": "github actions",
}

# Estados posibles del checklist que consume el frontend.
ESTADO_CUMPLE = "cumple"
ESTADO_FALTA = "falta"
ESTADO_PARCIAL = "parcial"
ESTADO_SE_APRENDE = "se_aprende"
ESTADO_BLANDA = "blanda"


def normalizar_nombre(texto: Any) -> str:
    """Minúsculas, sin tildes, sin puntuación y con espacios simples."""
    sin_tildes = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    limpio = sin_tildes.lower().replace(".", " ").replace("_", " ").replace("-", " ")
    return " ".join(limpio.split())


def _clave_habilidad(nombre: Any) -> str:
    normalizado = normalizar_nombre(nombre)
    return SINONIMOS.get(normalizado, normalizado)


def _nivel_numerico(valor: Any) -> int | None:
    """Nivel declarado o mínimo. Devuelve None si no se puede interpretar."""
    normalizado = normalizar_nombre(valor)
    if not normalizado:
        return None
    if normalizado in NIVELES:
        return NIVELES[normalizado]
    # Acepta textos como "B2 - Intermedio alto" o "Nivel avanzado".
    for palabra in ("experto", "avanzado", "intermedio", "principiante", "basico"):
        if palabra in normalizado:
            return NIVELES[palabra]
    return None


def _nivel_minimo_texto(valor: Any) -> str:
    normalizado = normalizar_nombre(valor)
    if normalizado in NIVELES_VALIDOS:
        return normalizado
    return "principiante"


def _exigencia_texto(valor: Any) -> str:
    normalizado = normalizar_nombre(valor).replace(" ", "_")
    return normalizado if normalizado in EXIGENCIAS_VALIDAS else "deseable"


def _tipo_texto(valor: Any) -> str:
    normalizado = normalizar_nombre(valor)
    return normalizado if normalizado in TIPOS_VALIDOS else "tecnica"


def _campo(origen: Any, clave: str, default: Any = None) -> Any:
    if isinstance(origen, dict):
        return origen.get(clave, default)
    return getattr(origen, clave, default)


def _items_habilidades(perfil: Any) -> list[Any]:
    """Junta ``skills`` y ``habilidades`` del perfil, sin importar el formato."""
    items: list[Any] = []
    for clave in ("habilidades", "skills"):
        valor = _campo(perfil, clave, [])
        if isinstance(valor, list):
            items.extend(valor)
        elif isinstance(valor, str) and valor.strip():
            items.append(valor)
    return items


def _habilidades_declaradas(perfil: Any) -> dict[str, dict[str, Any]]:
    """Mapa clave normalizada → {nombre, nivel, nivel_texto}. Se queda con el nivel más alto."""
    declaradas: dict[str, dict[str, Any]] = {}
    for item in _items_habilidades(perfil):
        if isinstance(item, dict):
            nombre = item.get("nombre_habilidad") or item.get("nombre") or item.get("skill") or ""
            nivel = item.get("nivel_habilidad") or item.get("nivel") or ""
        else:
            nombre, nivel = item, ""
        clave = _clave_habilidad(nombre)
        if not clave:
            continue
        valor = _nivel_numerico(nivel)
        # Sin nivel declarado se toma el mínimo: no se sobrevalora una habilidad.
        valor = 1 if valor is None else valor
        previa = declaradas.get(clave)
        if previa is None or valor > previa["nivel"]:
            declaradas[clave] = {
                "nombre": str(nombre).strip(),
                "nivel": valor,
                "nivel_texto": str(nivel).strip() if nivel else None,
            }
    return declaradas


def sanitizar_requisitos(requisitos: Any) -> list[dict[str, Any]]:
    """Normaliza los requisitos que manda la empresa y descarta los que no tienen nombre."""
    if not isinstance(requisitos, list):
        return []
    limpios: list[dict[str, Any]] = []
    vistos: set[str] = set()
    for item in requisitos:
        if not isinstance(item, dict):
            continue
        nombre = str(item.get("nombre") or "").strip()[:120]
        clave = _clave_habilidad(nombre)
        if not clave or clave in vistos:
            continue
        vistos.add(clave)
        limpios.append({
            "nombre": nombre,
            "nivel_minimo": _nivel_minimo_texto(item.get("nivel_minimo")),
            "exigencia": _exigencia_texto(item.get("exigencia")),
            "tipo": _tipo_texto(item.get("tipo")),
        })
    return limpios


def _resultado_vacio(requisitos_invalidos: list[dict]) -> dict[str, Any]:
    return {
        "coincidencia": 0,
        "nivel": "sin_requisitos",
        "total_requisitos": 0,
        "total_compatibles": 0,
        "sin_requisitos": True,
        "compatibles": [],
        "a_capacitar": [],
        "se_aprenden": [],
        "blandas": [],
        "checklist": [],
        "requisitos_invalidos": requisitos_invalidos,
    }


def comparar(perfil: Any, requisitos: Any) -> dict[str, Any]:
    """Compara el perfil declarado con los requisitos y devuelve el informe determinista.

    ``perfil`` puede ser un ``dict`` o un objeto con ``habilidades``/``skills``.
    ``requisitos`` es la lista guardada en ``contrato.requisitos``.
    """
    declaradas = _habilidades_declaradas(perfil)
    if not isinstance(requisitos, list) or not requisitos:
        return _resultado_vacio([])

    compatibles: list[dict[str, Any]] = []
    a_capacitar: list[dict[str, Any]] = []
    se_aprenden: list[str] = []
    blandas: list[str] = []
    checklist: list[dict[str, Any]] = []
    requisitos_invalidos: list[dict[str, Any]] = []
    vistos: set[str] = set()

    for indice, requisito in enumerate(requisitos):
        if not isinstance(requisito, dict):
            requisitos_invalidos.append({"indice": indice, "motivo": "formato_invalido"})
            continue

        nombre = str(requisito.get("nombre") or "").strip()
        clave = _clave_habilidad(nombre)
        if not clave:
            requisitos_invalidos.append({"indice": indice, "motivo": "sin_nombre"})
            continue
        if clave in vistos:
            # Requisito repetido: no duplica el total ni el checklist.
            continue
        vistos.add(clave)

        minimo_texto = _nivel_minimo_texto(requisito.get("nivel_minimo"))
        minimo = NIVELES[minimo_texto]
        exigencia = _exigencia_texto(requisito.get("exigencia"))
        tipo = _tipo_texto(requisito.get("tipo"))
        declarada = declaradas.get(clave)
        nivel_declarado_texto = declarada["nivel_texto"] if declarada else None

        if tipo == "blanda":
            blandas.append(nombre)
            checklist.append({
                "nombre": nombre,
                "estado": ESTADO_BLANDA,
                "nivel_minimo": minimo_texto,
                "nivel_declarado": nivel_declarado_texto,
            })
            continue

        if exigencia == "se_aprende":
            se_aprenden.append(nombre)
            checklist.append({
                "nombre": nombre,
                "estado": ESTADO_SE_APRENDE,
                "nivel_minimo": minimo_texto,
                "nivel_declarado": nivel_declarado_texto,
            })
            continue

        if declarada is None:
            a_capacitar.append({
                "nombre": nombre,
                "nivel_minimo": minimo_texto,
                "motivo": "no_declarada",
            })
            checklist.append({
                "nombre": nombre,
                "estado": ESTADO_FALTA,
                "nivel_minimo": minimo_texto,
                "nivel_declarado": None,
            })
        elif declarada["nivel"] < minimo:
            a_capacitar.append({
                "nombre": nombre,
                "nivel_minimo": minimo_texto,
                "motivo": "nivel_menor",
            })
            checklist.append({
                "nombre": nombre,
                "estado": ESTADO_PARCIAL,
                "nivel_minimo": minimo_texto,
                "nivel_declarado": nivel_declarado_texto,
            })
        else:
            compatibles.append({"nombre": nombre, "nivel": nivel_declarado_texto})
            checklist.append({
                "nombre": nombre,
                "estado": ESTADO_CUMPLE,
                "nivel_minimo": minimo_texto,
                "nivel_declarado": nivel_declarado_texto,
            })

    total = len(compatibles) + len(a_capacitar)
    coincidencia = round(100 * len(compatibles) / total) if total else 0
    if total == 0:
        nivel = "sin_requisitos"
    elif coincidencia >= 75:
        nivel = "alta"
    elif coincidencia >= 40:
        nivel = "media"
    else:
        nivel = "baja"

    return {
        "coincidencia": coincidencia,
        "nivel": nivel,
        "total_requisitos": total,
        "total_compatibles": len(compatibles),
        "sin_requisitos": total == 0,
        "compatibles": compatibles,
        "a_capacitar": a_capacitar,
        "se_aprenden": se_aprenden,
        "blandas": blandas,
        "checklist": checklist,
        "requisitos_invalidos": requisitos_invalidos,
    }


def texto_fallback(a_capacitar: list[dict[str, Any]] | list[str]) -> str:
    """Orientación determinista cuando n8n o la IA no están disponibles."""
    nombres = []
    for item in a_capacitar or []:
        nombre = item.get("nombre") if isinstance(item, dict) else item
        if nombre:
            nombres.append(str(nombre))
    if not nombres:
        return (
            "Cumplís todos los requisitos técnicos declarados para esta búsqueda. "
            "Podés reforzar tu perfil con proyectos pequeños y seguir postulándote. "
            "Esto es una orientación para prepararte, no una evaluación."
        )
    return (
        f"Te faltan {', '.join(nombres)}. Podés reforzarlos con cursos introductorios y "
        "proyectos pequeños. Esto es una orientación para prepararte, no una evaluación."
    )
