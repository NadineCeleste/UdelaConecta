"""Conversión entre filas ORM y los diccionarios que espera el frontend.

El frontend manda objetos con campos de más (por ejemplo el perfil completo con
`proyecto`, `rol` o `posicion`), así que las escrituras aplican solo las columnas
conocidas de cada tabla y convierten los tipos que llegan como string desde los
<select> ("true"/"false").
"""

import json
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import JSON, Boolean, Integer, String, Text, inspect

VERDADEROS = {"true", "1", "si", "sí", "yes", "on"}
FALSOS = {"false", "0", "no", "off", ""}


def a_dict(obj: Any) -> dict[str, Any]:
    datos: dict[str, Any] = {}
    for col in inspect(obj).mapper.column_attrs:
        valor = getattr(obj, col.key)
        if isinstance(valor, datetime):
            valor = valor.isoformat()
        datos[col.key] = valor
    return datos


def _a_bool(clave: str, valor: Any) -> bool:
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, (int, float)):
        return bool(valor)
    texto = str(valor).strip().lower()
    if texto in VERDADEROS:
        return True
    if texto in FALSOS:
        return False
    raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Valor inválido para '{clave}'")


def _a_lista(valor: Any) -> list:
    if isinstance(valor, list):
        return valor
    if valor is None:
        return []
    if isinstance(valor, str):
        texto = valor.strip()
        if texto.startswith("["):
            try:
                cargado = json.loads(texto)
                if isinstance(cargado, list):
                    return cargado
            except ValueError:
                pass
        return [s.strip() for s in texto.split(",") if s.strip()]
    return [valor]


def aplicar_cambios(obj: Any, datos: dict[str, Any], excluir: set[str]) -> None:
    columnas = {c.key: c for c in inspect(obj).mapper.columns}
    for clave, valor in datos.items():
        col = columnas.get(clave)
        if col is None or clave in excluir or col.primary_key:
            continue
        tipo = col.type
        if valor is None:
            if col.nullable:
                setattr(obj, clave, None)
            continue
        if isinstance(tipo, Boolean):
            valor = _a_bool(clave, valor)
        elif isinstance(tipo, Integer):
            try:
                valor = int(valor)
            except (TypeError, ValueError):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Valor inválido para '{clave}'")
        elif isinstance(tipo, JSON):
            valor = _a_lista(valor)
        elif isinstance(tipo, (String, Text)):
            valor = valor if isinstance(valor, str) else str(valor)
            largo = getattr(tipo, "length", None)
            if largo:
                valor = valor[:largo]
        setattr(obj, clave, valor)
