import os
from openai import OpenAI
from models.listing import Listing

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def generar_contenido(listing: Listing) -> tuple[str, str]:
    amenidades_str = ", ".join(listing.amenidades) if listing.amenidades else "sin amenidades especificadas"

    prompt = f"""Eres experto en bienes raíces en México. Genera contenido profesional para esta propiedad de Inmersiva Grupo Inmobiliario.

Propiedad:
- Tipo: {listing.tipo} en {listing.operacion}
- Ubicación: {listing.direccion}, {listing.ciudad}, {listing.estado}
- Precio: {listing.precio_str}
- Recámaras: {listing.recamaras or 'N/A'} | Baños: {listing.banos or 'N/A'}
- M² construidos: {listing.m2_construidos or 'N/A'} | M² terreno: {listing.m2_terreno or 'N/A'}
- Estacionamientos: {listing.estacionamientos or 'N/A'}
- Amenidades: {amenidades_str}
- Notas del agente: {listing.descripcion_agente}

Genera exactamente en este formato:

[DESCRIPCIÓN]
(150-200 palabras, tono profesional y aspiracional, resalta beneficios clave)

---INSTAGRAM---
[INSTAGRAM]
(100-150 palabras para Instagram, emojis estratégicos, 15-20 hashtags relevantes del mercado inmobiliario mexicano)"""

    response = _get_client().chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.75,
        max_tokens=900,
    )

    content = response.choices[0].message.content.strip()
    parts = content.split("---INSTAGRAM---")

    descripcion = parts[0].replace("[DESCRIPCIÓN]", "").strip()
    copy_ig = parts[1].replace("[INSTAGRAM]", "").strip() if len(parts) > 1 else ""

    return descripcion, copy_ig
