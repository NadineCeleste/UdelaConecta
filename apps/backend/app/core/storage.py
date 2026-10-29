"""Archivos de imágenes de portfolio guardados en disco (STORAGE_DIR/portfolios).

El dueño de cada archivo se guarda en un archivo oculto al lado (".<nombre>.owner"),
así solo quien lo subió puede pisarlo o borrarlo.
"""

from pathlib import Path
from urllib.parse import unquote, urlparse

from fastapi import HTTPException, status

from app.core.config import settings

CARPETA = "portfolios"

# Solo formatos raster: un SVG o un HTML servido desde el mismo dominio ejecutaría scripts
EXTENSIONES: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def tipo_por_extension(ruta: Path) -> str:
    tipo = EXTENSIONES.get(ruta.suffix.lower())
    if tipo is None:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Solo se aceptan imágenes PNG, JPG, GIF o WEBP"
        )
    return tipo


def contenido_coincide(tipo: str, contenido: bytes) -> bool:
    """Compara los primeros bytes del archivo con la firma del formato declarado."""
    if tipo == "image/png":
        return contenido.startswith(b"\x89PNG\r\n\x1a\n")
    if tipo == "image/jpeg":
        return contenido.startswith(b"\xff\xd8\xff")
    if tipo == "image/gif":
        return contenido.startswith((b"GIF87a", b"GIF89a"))
    if tipo == "image/webp":
        return contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP"
    return False


def directorio() -> Path:
    carpeta = Path(settings.STORAGE_DIR) / CARPETA
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def ruta_segura(nombre: str) -> Path:
    nombre = unquote(nombre)
    if (
        not nombre
        or nombre.startswith(".")
        or any(c in nombre for c in ("/", "\\", "\0"))
        or len(nombre) > 200
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nombre de archivo inválido")
    base = directorio().resolve()
    ruta = (base / nombre).resolve()
    if ruta.parent != base:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nombre de archivo inválido")
    return ruta


def ruta_dueno(ruta: Path) -> Path:
    return ruta.with_name(f".{ruta.name}.owner")


def dueno_de(ruta: Path) -> str | None:
    marca = ruta_dueno(ruta)
    return marca.read_text().strip() if marca.exists() else None


def nombre_desde_url(url: str) -> str | None:
    """Extrae el nombre de archivo si la URL apunta a /storage/portfolios/<nombre>."""
    if not url:
        return None
    partes = Path(urlparse(url).path).parts
    for i in range(len(partes) - 2):
        if partes[i] == "storage" and partes[i + 1] == CARPETA:
            return partes[i + 2] if i + 3 == len(partes) else None
    return None


def borrar_por_url(url: str, email: str) -> None:
    """Borra un archivo propio referenciado por URL. Ignora URLs externas o ya borradas."""
    nombre = nombre_desde_url(url)
    if not nombre:
        return
    try:
        ruta = ruta_segura(nombre)
    except HTTPException:
        return
    if ruta.exists() and dueno_de(ruta) in (None, email):
        ruta.unlink(missing_ok=True)
        ruta_dueno(ruta).unlink(missing_ok=True)
