from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.security import CurrentUser, get_current_user
from app.core.storage import contenido_coincide, dueno_de, ruta_dueno, ruta_segura, tipo_por_extension

# Reemplaza al bucket S3: el front hace PUT/DELETE directo sobre la URL de la imagen
router = APIRouter(prefix="/storage/portfolios", tags=["storage"])

# El navegador no adivina el tipo ni ejecuta nada aunque el archivo se abra directo
HEADERS_SEGUROS = {
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'none'; sandbox",
}


@router.get("/{nombre}")
async def ver_imagen(nombre: str):
    ruta = ruta_segura(nombre)
    if not ruta.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Imagen no encontrada")
    return FileResponse(ruta, media_type=tipo_por_extension(ruta), headers=HEADERS_SEGUROS)


@router.put("/{nombre}", status_code=status.HTTP_201_CREATED)
async def subir_imagen(nombre: str, request: Request, user: CurrentUser = Depends(get_current_user)):
    ruta = ruta_segura(nombre)
    # El tipo sale de la extensión (lista blanca); el Content-Type del cliente no alcanza
    tipo = tipo_por_extension(ruta)
    if ruta.exists() and dueno_de(ruta) not in (None, user.email):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "La imagen pertenece a otro usuario")

    contenido = bytearray()
    async for parte in request.stream():
        contenido.extend(parte)
        if len(contenido) > settings.MAX_IMAGE_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "La imagen supera el tamaño máximo")
    if not contenido:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La imagen está vacía")
    if not contenido_coincide(tipo, bytes(contenido)):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "El contenido no es una imagen válida")

    ruta.write_bytes(bytes(contenido))
    ruta_dueno(ruta).write_text(user.email)
    url = f"{settings.PUBLIC_STORAGE_BASE_URL.rstrip('/')}/portfolios/{ruta.name}"
    return {"message": "Imagen subida", "data": {"url": url}}


@router.delete("/{nombre}")
async def borrar_imagen(nombre: str, user: CurrentUser = Depends(get_current_user)):
    ruta = ruta_segura(nombre)
    if not ruta.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Imagen no encontrada")
    if dueno_de(ruta) not in (None, user.email):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "La imagen pertenece a otro usuario")
    ruta.unlink()
    ruta_dueno(ruta).unlink(missing_ok=True)
    return {"message": "Imagen eliminada"}
