"""
Cliente para UploadPost API (https://uploadpost.co)
Requiere: UPLOADPOST_API_KEY en variables de entorno
Plataformas soportadas: instagram, facebook, tiktok, whatsapp
"""
import os
import httpx
from pathlib import Path

UPLOADPOST_BASE = os.getenv("UPLOADPOST_BASE_URL", "https://api.uploadpost.co/v1")
API_KEY = os.getenv("UPLOADPOST_API_KEY", "")

PLATFORMS_MAP = {
    "instagram": "instagram",
    "facebook": "facebook",
    "tiktok": "tiktok",
    "whatsapp": "whatsapp",
}


class UploadPostError(Exception):
    pass


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json",
    }


def publicar_en_redes(caption: str, imagen_path: str, redes: list[str]) -> dict:
    """
    Publica imagen + caption en las redes especificadas via UploadPost.

    Args:
        caption: Texto del post con hashtags incluidos
        imagen_path: Path a la imagen JPEG
        redes: Lista de plataformas, ej. ["instagram", "facebook"]

    Returns:
        dict con: post_id, status, urls (por plataforma)

    Raises:
        UploadPostError: si la API retorna error o faltan credenciales
    """
    if not API_KEY:
        raise UploadPostError("UPLOADPOST_API_KEY no configurada en variables de entorno")

    plataformas = [PLATFORMS_MAP[r] for r in redes if r in PLATFORMS_MAP]
    if not plataformas:
        raise UploadPostError(f"Ninguna plataforma válida en: {redes}")

    imagen_path = Path(imagen_path)
    if not imagen_path.exists():
        raise UploadPostError(f"Imagen no encontrada: {imagen_path}")

    with httpx.Client(timeout=60) as client:
        # Paso 1: subir imagen
        with open(imagen_path, "rb") as f:
            upload_resp = client.post(
                f"{UPLOADPOST_BASE}/media",
                headers=_headers(),
                files={"file": ("post.jpg", f, "image/jpeg")},
            )
        if upload_resp.status_code not in (200, 201):
            raise UploadPostError(
                f"Error subiendo imagen: {upload_resp.status_code} — {upload_resp.text[:300]}"
            )
        media_data = upload_resp.json()
        media_id = media_data.get("id") or media_data.get("media_id")
        if not media_id:
            raise UploadPostError(f"UploadPost no retornó media_id: {media_data}")

        # Paso 2: crear post
        post_resp = client.post(
            f"{UPLOADPOST_BASE}/posts",
            headers=_headers(),
            json={
                "caption": caption,
                "media_ids": [media_id],
                "platforms": plataformas,
            },
        )
        if post_resp.status_code not in (200, 201):
            raise UploadPostError(
                f"Error creando post: {post_resp.status_code} — {post_resp.text[:300]}"
            )
        result = post_resp.json()
        return {
            "post_id": result.get("id") or result.get("post_id", ""),
            "status": result.get("status", "published"),
            "urls": result.get("urls", {}),
            "raw": result,
        }
