# Sistema Corredores, Ficha y Publicación RRSS — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir que corredores reales se registren, llenen fichas, generen imágenes verticales profesionales y soliciten publicación en RRSS; el admin aprueba y UploadPost publica automáticamente en Instagram, Facebook, WhatsApp y TikTok.

**Architecture:** Monolítico mejorado — todas las rutas nuevas se agregan a `main.py` en secciones bien delimitadas. Los servicios (`image_service`, `uploadpost_service`) son módulos independientes. La BD usa SQLAlchemy `create_all` sin Alembic — los campos nuevos se agregan con `nullable=True` para no romper datos existentes.

**Tech Stack:** FastAPI · SQLAlchemy · PostgreSQL · Pillow (imágenes) · httpx (UploadPost API) · Jinja2 · pytest

---

## File Map

| Archivo | Acción | Responsabilidad |
|---|---|---|
| `models/db_models.py` | Modificar | + `SolicitudCorredor`, + campos a `Corredor` y `PostRRSS` |
| `services/image_service.py` | Modificar | + función `generar_imagen_vertical` (1080×1920) |
| `services/uploadpost_service.py` | Crear | Cliente HTTP para UploadPost API |
| `main.py` | Modificar | + ~15 rutas nuevas en secciones organizadas |
| `templates/registro_corredor.html` | Crear | Formulario auto-registro corredor |
| `templates/results.html` | Modificar | + botón imagen vertical + botón solicitar publicación |
| `templates/dashboard_corredor.html` | Modificar | + sección "Mis publicaciones" + "Mi perfil" |
| `templates/dashboard_empresa.html` | Modificar | + cola aprobación + actividad corredores + solicitudes |
| `tests/test_image_service.py` | Modificar | + test imagen vertical |
| `tests/test_uploadpost_service.py` | Crear | Tests del cliente UploadPost |

---

## Task 1: Actualizar modelos de BD

**Files:**
- Modify: `models/db_models.py`

- [ ] **Step 1: Agregar `SolicitudCorredor` y campos nuevos a `Corredor` y `PostRRSS`**

Reemplazar el contenido completo de `models/db_models.py`:

```python
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey
from datetime import datetime
import json as _json
from database import Base


class SolicitudCorredor(Base):
    __tablename__ = "solicitudes_corredor"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    telefono = Column(String(30), default="")
    mensaje = Column(Text, default="")
    estado = Column(String(20), default="Pendiente")  # Pendiente / Aprobado / Rechazado
    created_at = Column(DateTime, default=datetime.utcnow)


class Contacto(Base):
    __tablename__ = "contactos"
    id = Column(Integer, primary_key=True)
    corredor_id = Column(Integer, ForeignKey("corredores.id"), nullable=False)
    nombre = Column(String(100), nullable=False)
    email = Column(String(100), default="")
    telefono = Column(String(30), default="")
    origen = Column(String(50), default="Web")
    estado = Column(String(30), default="Nuevo")
    interes = Column(String(300), default="")
    notas = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Cita(Base):
    __tablename__ = "citas"
    id = Column(Integer, primary_key=True)
    corredor_id = Column(Integer, ForeignKey("corredores.id"), nullable=False)
    contacto_id = Column(Integer, ForeignKey("contactos.id"), nullable=True)
    titulo = Column(String(200), nullable=False)
    descripcion = Column(Text, default="")
    fecha = Column(DateTime, nullable=False)
    lugar = Column(String(200), default="")
    estado = Column(String(20), default="Pendiente")
    created_at = Column(DateTime, default=datetime.utcnow)


class DocumentoCorredor(Base):
    __tablename__ = "documentos_corredor"
    id = Column(Integer, primary_key=True)
    corredor_id = Column(Integer, ForeignKey("corredores.id"), nullable=False)
    nombre = Column(String(200), nullable=False)
    tipo = Column(String(50), default="Otro")
    archivo = Column(String(300), default="")
    notas = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class PostRRSS(Base):
    __tablename__ = "posts_rrss"
    id = Column(Integer, primary_key=True)
    corredor_id = Column(Integer, ForeignKey("corredores.id"), nullable=False)
    # Campos originales
    red = Column(String(30), nullable=False)
    contenido = Column(Text, default="")
    url = Column(String(500), default="")
    fecha_publicacion = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    # Campos nuevos para flujo de aprobación
    listing_id = Column(String(36), nullable=True)
    titulo = Column(String(200), nullable=True)
    imagen_url = Column(String(500), nullable=True)
    estado = Column(String(20), default="Pendiente")   # Pendiente/Aprobado/Rechazado/Publicado
    comentario_admin = Column(Text, nullable=True)
    redes = Column(String(200), nullable=True)          # CSV: instagram,facebook,whatsapp,tiktok
    upload_post_id = Column(String(100), nullable=True)
    publicado_at = Column(DateTime, nullable=True)
    caption = Column(Text, nullable=True)

    @property
    def redes_list(self):
        return [r.strip() for r in (self.redes or "").split(",") if r.strip()]


class Corredor(Base):
    __tablename__ = "corredores"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    telefono = Column(String(20), default="")
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    # Campos nuevos de perfil
    foto_perfil = Column(String(300), nullable=True)
    bio = Column(Text, nullable=True)
    instagram = Column(String(100), nullable=True)
    whatsapp = Column(String(30), nullable=True)


class UsuarioPublico(Base):
    __tablename__ = "usuarios_publicos"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(200), nullable=True)
    google_id = Column(String(100), nullable=True)
    telefono = Column(String(20), default="")
    activo = Column(Boolean, default=True)
    favoritos = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)


class PropiedadPublica(Base):
    __tablename__ = "propiedades_publicas"
    id = Column(Integer, primary_key=True)
    listing_id = Column(String(36), unique=True, nullable=False)
    titulo = Column(String(200), nullable=False)
    tipo = Column(String(50), nullable=False)
    operacion = Column(String(20), nullable=False)
    precio = Column(Integer, nullable=False)
    moneda = Column(String(10), default="PEN")
    ciudad = Column(String(100), nullable=False)
    estado = Column(String(100), nullable=False)
    direccion = Column(String(200), nullable=False)
    descripcion = Column(Text, default="")
    habitaciones = Column(Integer, nullable=True)
    banos = Column(Float, nullable=True)
    m2_construidos = Column(Integer, nullable=True)
    m2_terreno = Column(Integer, nullable=True)
    estacionamientos = Column(Integer, nullable=True)
    foto_portada = Column(String(300), default="")
    fotos_extras = Column(Text, default="[]")
    tour_360_url = Column(String(500), default="")
    corredor_id = Column(Integer, ForeignKey("corredores.id"), nullable=True)
    publicado = Column(Boolean, default=True)
    destacado = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def fotos_list(self):
        try:
            return _json.loads(self.fotos_extras or "[]")
        except Exception:
            return []

    @property
    def precio_fmt(self):
        sym = "S/." if self.moneda == "PEN" else ("USD" if self.moneda == "USD" else self.moneda)
        return f"{sym} {self.precio:,}"
```

- [ ] **Step 2: Verificar que Python parsea el archivo sin errores**

```bash
python -c "import models.db_models; print('OK')"
```

Resultado esperado: `OK`

- [ ] **Step 3: Commit**

```bash
git add models/db_models.py
git commit -m "feat: expandir modelos BD — SolicitudCorredor, perfil corredor, campos aprobación PostRRSS"
```

---

## Task 2: Imagen vertical profesional 1080×1920

**Files:**
- Modify: `services/image_service.py`
- Modify: `tests/test_image_service.py`

- [ ] **Step 1: Descargar fuente Inter para imagen profesional**

```bash
mkdir -p static/fonts
curl -L "https://github.com/rsms/inter/releases/download/v3.19/Inter-3.19.zip" -o /tmp/inter.zip
unzip -j /tmp/inter.zip "Inter Desktop/Inter-Regular.otf" -d static/fonts/
unzip -j /tmp/inter.zip "Inter Desktop/Inter-Bold.otf" -d static/fonts/
ls static/fonts/
```

Resultado esperado: `Inter-Bold.otf  Inter-Regular.otf`

- [ ] **Step 2: Agregar función `generar_imagen_vertical` a `services/image_service.py`**

Agregar al final del archivo existente (NO reemplazar la función `generar_imagen_instagram`):

```python
W_VERT, H_VERT = 1080, 1920
GOLD = (212, 175, 55)
WHITE_FULL = (255, 255, 255)
DARK_BG = (15, 15, 20)
FONTS_DIR = Path(__file__).parent.parent / "static" / "fonts"
LOGO_PATH = Path(__file__).parent.parent / "static" / "img" / "logo.jpeg"


def _load_inter(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = ["Inter-Bold.otf", "Inter-Bold.ttf"] if bold else ["Inter-Regular.otf", "Inter-Regular.ttf"]
    system_fallbacks = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for name in names:
        p = FONTS_DIR / name
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                pass
    for p in system_fallbacks:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _crop_to_fit(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    src_w, src_h = img.size
    ratio = max(target_w / src_w, target_h / src_h)
    new_w, new_h = int(src_w * ratio), int(src_h * ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def _draw_text_wrapped(draw: ImageDraw.ImageDraw, text: str, x: int, y: int,
                       max_width: int, font, fill, line_spacing: int = 8) -> int:
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        bbox = draw.textbbox((x, y), line, font=font)
        y += (bbox[3] - bbox[1]) + line_spacing
    return y


def generar_imagen_vertical(listing, portada_path: str | None, output_path: str) -> str:
    """Genera imagen 1080×1920 (formato stories/reels) profesional para RRSS."""
    # ── 1. Base: foto de portada en top 58% ──────────────────────────────────
    photo_h = int(H_VERT * 0.58)
    if portada_path and Path(portada_path).exists():
        photo = Image.open(portada_path).convert("RGB")
        photo = _crop_to_fit(photo, W_VERT, photo_h)
    else:
        photo = Image.new("RGB", (W_VERT, photo_h), (30, 45, 80))
    base = Image.new("RGB", (W_VERT, H_VERT), DARK_BG)
    base.paste(photo, (0, 0))

    # ── 2. Gradiente de transición foto→fondo ────────────────────────────────
    grad = Image.new("RGBA", (W_VERT, H_VERT), (0, 0, 0, 0))
    grad_draw = ImageDraw.Draw(grad)
    fade_start = int(photo_h * 0.55)
    for y in range(fade_start, photo_h + 80):
        alpha = min(255, int(255 * (y - fade_start) / (photo_h - fade_start + 80)))
        grad_draw.line([(0, y), (W_VERT, y)], fill=(DARK_BG[0], DARK_BG[1], DARK_BG[2], alpha))
    base = Image.alpha_composite(base.convert("RGBA"), grad).convert("RGB")

    draw = ImageDraw.Draw(base)

    # ── 3. Logo Inmersiva top-left ────────────────────────────────────────────
    if LOGO_PATH.exists():
        try:
            logo = Image.open(LOGO_PATH).convert("RGBA")
            logo.thumbnail((220, 88), Image.LANCZOS)
            # Fondo blanco semitransparente detrás del logo
            lw, lh = logo.size
            bg_logo = Image.new("RGBA", (lw + 20, lh + 16), (255, 255, 255, 200))
            base_rgba = base.convert("RGBA")
            base_rgba.paste(bg_logo, (30, 30), bg_logo)
            base_rgba.paste(logo, (40, 38), logo)
            base = base_rgba.convert("RGB")
            draw = ImageDraw.Draw(base)
        except Exception:
            pass

    # ── 4. Tipo + operación ───────────────────────────────────────────────────
    y = photo_h - 30
    tipo_text = f"{listing.tipo.upper()} EN {listing.operacion.upper()}"
    font_tipo = _load_inter(40)
    draw.text((60, y), tipo_text, font=font_tipo, fill=(200, 200, 200))

    # ── 5. Precio (dorado, grande) ────────────────────────────────────────────
    y += 58
    moneda = getattr(listing, "moneda", "PEN")
    sym = "S/." if moneda == "PEN" else "USD"
    precio_text = f"{sym} {listing.precio:,}"
    font_precio = _load_inter(88, bold=True)
    draw.text((60, y), precio_text, font=font_precio, fill=GOLD)

    # ── 6. Ubicación ──────────────────────────────────────────────────────────
    y += 115
    font_ubi = _load_inter(38)
    ubi_text = f"📍 {listing.ciudad}, {listing.estado}"
    draw.text((60, y), ubi_text, font=font_ubi, fill=WHITE_FULL)

    # ── 7. Specs (recámaras, baños, m²) ──────────────────────────────────────
    y += 62
    font_specs = _load_inter(34)
    specs = []
    if listing.recamaras:       specs.append(f"🛏  {listing.recamaras} rec.")
    if listing.banos:           specs.append(f"🚿  {listing.banos} baños")
    if listing.m2_construidos:  specs.append(f"📐  {listing.m2_construidos} m²")
    if specs:
        draw.text((60, y), "    ".join(specs), font=font_specs, fill=(220, 220, 220))
        y += 55

    # ── 8. Línea dorada divisoria ─────────────────────────────────────────────
    y += 10
    draw.rectangle([(60, y), (W_VERT - 60, y + 3)], fill=GOLD)
    y += 22

    # ── 9. Descripción breve (2 líneas máx) ──────────────────────────────────
    desc_raw = (listing.descripcion_generada or getattr(listing, "descripcion_agente", "") or "")
    desc = desc_raw[:160]
    font_desc = _load_inter(30)
    _draw_text_wrapped(draw, desc, 60, y, W_VERT - 120, font_desc,
                       fill=(210, 210, 210), line_spacing=10)

    # ── 10. Footer corredor ───────────────────────────────────────────────────
    footer_y = H_VERT - 160
    draw.rectangle([(0, footer_y - 10), (W_VERT, H_VERT)], fill=(10, 10, 15))
    draw.line([(0, footer_y - 10), (W_VERT, footer_y - 10)], fill=GOLD, width=2)

    agente = getattr(listing, "agente_nombre", "") or "Inmersiva"
    font_agente = _load_inter(36, bold=True)
    font_handle = _load_inter(30)
    draw.text((60, footer_y + 10), agente, font=font_agente, fill=WHITE_FULL)
    draw.text((60, footer_y + 60), "@inmersivainmobiliaria", font=font_handle, fill=GOLD)

    # Logo pequeño en footer derecho
    if LOGO_PATH.exists():
        try:
            logo_sm = Image.open(LOGO_PATH).convert("RGBA")
            logo_sm.thumbnail((120, 50), Image.LANCZOS)
            lw, lh = logo_sm.size
            base_rgba2 = base.convert("RGBA")
            base_rgba2.paste(logo_sm, (W_VERT - lw - 40, footer_y + 20), logo_sm)
            base = base_rgba2.convert("RGB")
        except Exception:
            pass

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    base.save(output_path, "JPEG", quality=92, optimize=True)
    return output_path
```

- [ ] **Step 3: Escribir test para imagen vertical**

Agregar al final de `tests/test_image_service.py`:

```python
from services.image_service import generar_imagen_vertical
import tempfile, os
from unittest.mock import MagicMock

def test_generar_imagen_vertical_sin_foto():
    listing = MagicMock()
    listing.tipo = "Departamento"
    listing.operacion = "Venta"
    listing.precio = 450000
    listing.moneda = "PEN"
    listing.ciudad = "Miraflores"
    listing.estado = "Lima"
    listing.recamaras = 3
    listing.banos = 2.0
    listing.m2_construidos = 120
    listing.descripcion_generada = "Hermoso departamento con vista al mar en Miraflores."
    listing.agente_nombre = "Juan Pérez"

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        out = tmp.name

    try:
        generar_imagen_vertical(listing, None, out)
        assert os.path.exists(out)
        assert os.path.getsize(out) > 10_000  # al menos 10KB
    finally:
        os.unlink(out)
```

- [ ] **Step 4: Correr test**

```bash
pytest tests/test_image_service.py -v
```

Resultado esperado: todos los tests pasan (incluyendo el nuevo).

- [ ] **Step 5: Agregar ruta `/imagen-vertical/{listing_id}` a `main.py`**

Buscar la sección `# ── Instagram Image ───` en `main.py` y agregar después del bloque existente:

```python
@app.get("/imagen-vertical/{listing_id}")
async def descargar_imagen_vertical(listing_id: str):
    listing = load_listing(listing_id)
    img_path = GENERATED / "images" / f"{listing_id}_vertical.jpg"
    img_path.parent.mkdir(parents=True, exist_ok=True)
    portada_path = (UPLOADS / listing.foto_portada) if listing.foto_portada else None
    generar_imagen_vertical(listing, str(portada_path) if portada_path else None, str(img_path))
    filename = f"inmersiva_rrss_{listing.tipo.lower()}_{listing.ciudad.lower()}.jpg"
    return FileResponse(str(img_path), media_type="image/jpeg", filename=filename)
```

- [ ] **Step 6: Commit**

```bash
git add services/image_service.py tests/test_image_service.py main.py static/fonts/
git commit -m "feat: imagen vertical 1080x1920 profesional para RRSS + ruta /imagen-vertical"
```

---

## Task 3: Servicio UploadPost

**Files:**
- Create: `services/uploadpost_service.py`
- Create: `tests/test_uploadpost_service.py`

- [ ] **Step 1: Crear `services/uploadpost_service.py`**

```python
"""
Cliente para UploadPost API (https://uploadpost.co)
Documentación: https://docs.uploadpost.co
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
        imagen_path: Path absoluto o relativo a la imagen JPEG
        redes: Lista de plataformas, ej. ["instagram", "facebook"]

    Returns:
        dict con: post_id, status, urls (por plataforma)

    Raises:
        UploadPostError: si la API retorna error
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
```

- [ ] **Step 2: Crear `tests/test_uploadpost_service.py`**

```python
from unittest.mock import patch, MagicMock
import pytest
from services.uploadpost_service import publicar_en_redes, UploadPostError
import tempfile, os


@pytest.fixture
def dummy_image():
    from PIL import Image
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        img = Image.new("RGB", (100, 100), (255, 0, 0))
        img.save(f.name)
        yield f.name
    os.unlink(f.name)


def test_publicar_sin_api_key(dummy_image):
    with patch.dict(os.environ, {"UPLOADPOST_API_KEY": ""}):
        import importlib
        import services.uploadpost_service as svc
        svc.API_KEY = ""
        with pytest.raises(UploadPostError, match="UPLOADPOST_API_KEY"):
            publicar_en_redes("test caption", dummy_image, ["instagram"])


def test_publicar_plataforma_invalida(dummy_image):
    with patch.dict(os.environ, {"UPLOADPOST_API_KEY": "test-key"}):
        import services.uploadpost_service as svc
        svc.API_KEY = "test-key"
        with pytest.raises(UploadPostError, match="plataforma"):
            publicar_en_redes("caption", dummy_image, ["twitter_x_invalid"])


def test_publicar_imagen_no_existe():
    import services.uploadpost_service as svc
    svc.API_KEY = "test-key"
    with pytest.raises(UploadPostError, match="no encontrada"):
        publicar_en_redes("caption", "/tmp/no_existe_12345.jpg", ["instagram"])


def test_publicar_mock_exitoso(dummy_image):
    import services.uploadpost_service as svc
    svc.API_KEY = "test-key"
    mock_upload = MagicMock()
    mock_upload.status_code = 201
    mock_upload.json.return_value = {"id": "media-abc-123"}
    mock_post = MagicMock()
    mock_post.status_code = 201
    mock_post.json.return_value = {"id": "post-xyz-456", "status": "published", "urls": {}}

    with patch("services.uploadpost_service.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = [mock_upload, mock_post]
        mock_client_cls.return_value = mock_client

        result = publicar_en_redes("Test caption #inmersiva", dummy_image, ["instagram", "facebook"])

    assert result["post_id"] == "post-xyz-456"
    assert result["status"] == "published"
```

- [ ] **Step 3: Correr tests del servicio**

```bash
pytest tests/test_uploadpost_service.py -v
```

Resultado esperado: 4/4 tests pasan.

- [ ] **Step 4: Commit**

```bash
git add services/uploadpost_service.py tests/test_uploadpost_service.py
git commit -m "feat: servicio UploadPost para publicación multi-red + tests"
```

---

## Task 4: Auto-registro de corredor

**Files:**
- Create: `templates/registro_corredor.html`
- Modify: `main.py`

- [ ] **Step 1: Crear `templates/registro_corredor.html`**

```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Únete como Corredor — Inmersiva</title>
  <link rel="stylesheet" href="/static/css/style.css">
  <style>
    body { background: #0f1623; min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; }
    .reg-card { background: #1B2A4A; border-radius: 16px; padding: 48px 40px; width: 100%; max-width: 520px; box-shadow: 0 8px 40px rgba(0,0,0,.5); }
    .reg-logo { text-align: center; margin-bottom: 32px; }
    .reg-logo img { height: 72px; }
    h2 { color: #fff; font-size: 1.5rem; font-weight: 800; margin: 0 0 4px; }
    .subtitle { color: #C9A84C; font-size: .8rem; letter-spacing: 3px; text-transform: uppercase; margin-bottom: 32px; display: block; }
    label { color: #ccc; font-size: .85rem; display: block; margin-bottom: 6px; margin-top: 18px; }
    input, textarea { width: 100%; padding: 12px 14px; border-radius: 8px; border: 1.5px solid #2d4070; background: #111d30; color: #fff; font-size: .95rem; box-sizing: border-box; }
    input:focus, textarea:focus { border-color: #C9A84C; outline: none; }
    textarea { height: 90px; resize: vertical; }
    .btn-submit { width: 100%; padding: 14px; background: #C9A84C; color: #1B2A4A; font-weight: 800; font-size: 1rem; border: none; border-radius: 8px; cursor: pointer; margin-top: 28px; letter-spacing: 1px; }
    .btn-submit:hover { background: #e0c060; }
    .success-box { background: #0d3d2a; border: 1.5px solid #2ecc71; border-radius: 10px; padding: 20px 24px; color: #2ecc71; text-align: center; margin-top: 16px; }
    .error-box { background: #3d0d0d; border: 1.5px solid #e74c3c; border-radius: 10px; padding: 14px 18px; color: #e74c3c; margin-bottom: 20px; }
    .login-link { text-align: center; margin-top: 24px; color: #888; font-size: .85rem; }
    .login-link a { color: #C9A84C; text-decoration: none; }
  </style>
</head>
<body>
  <div class="reg-card">
    <div class="reg-logo">
      <img src="/static/img/logo.jpeg" alt="Inmersiva">
    </div>
    <h2>Únete como Corredor</h2>
    <span class="subtitle">Inmersiva Grupo Inmobiliario</span>

    {% if success %}
    <div class="success-box">
      <strong>✅ Solicitud enviada</strong><br>
      Tu solicitud fue recibida. Te contactaremos pronto para activar tu cuenta.
    </div>
    {% else %}
      {% if error %}<div class="error-box">{{ error }}</div>{% endif %}
      <form method="post" action="/corredor/registro">
        <label>Nombre completo *</label>
        <input type="text" name="nombre" required placeholder="Juan Pérez">

        <label>Email *</label>
        <input type="email" name="email" required placeholder="juan@ejemplo.com">

        <label>Teléfono</label>
        <input type="tel" name="telefono" placeholder="+51 999 999 999">

        <label>¿Por qué quieres unirte a Inmersiva?</label>
        <textarea name="mensaje" placeholder="Cuéntanos un poco sobre ti y tu experiencia en bienes raíces..."></textarea>

        <button type="submit" class="btn-submit">ENVIAR SOLICITUD</button>
      </form>
    {% endif %}

    <div class="login-link">
      ¿Ya tienes cuenta? <a href="/login?tab=corredor">Inicia sesión</a>
    </div>
  </div>
</body>
</html>
```

- [ ] **Step 2: Agregar rutas de auto-registro a `main.py`**

Agregar después del bloque `# ── Registro usuario público ───`:

```python
# ── Registro corredor (auto-registro) ─────────────────────────────────────────
@app.get("/corredor/registro", response_class=HTMLResponse)
async def registro_corredor_page(request: Request):
    if get_corredor_session(request):
        return RedirectResponse("/corredor/dashboard", status_code=302)
    return templates.TemplateResponse(request, "registro_corredor.html",
                                      {"error": "", "success": False})


@app.post("/corredor/registro")
async def registro_corredor_submit(
    request: Request,
    nombre: str = Form(...),
    email: str = Form(...),
    telefono: str = Form(default=""),
    mensaje: str = Form(default=""),
):
    db = SessionLocal()
    try:
        from models.db_models import SolicitudCorredor
        existe = db.query(SolicitudCorredor).filter(SolicitudCorredor.email == email).first()
        existe_corredor = db.query(CorredorModel).filter(CorredorModel.email == email).first()
        if existe or existe_corredor:
            return templates.TemplateResponse(
                request, "registro_corredor.html",
                {"error": "Ya existe una solicitud o cuenta con ese email.", "success": False}
            )
        solicitud = SolicitudCorredor(nombre=nombre, email=email,
                                      telefono=telefono, mensaje=mensaje)
        db.add(solicitud)
        db.commit()
    except Exception as e:
        db.rollback()
        return templates.TemplateResponse(
            request, "registro_corredor.html",
            {"error": f"Error al enviar solicitud: {e}", "success": False}
        )
    finally:
        db.close()
    return templates.TemplateResponse(request, "registro_corredor.html",
                                      {"error": "", "success": True})
```

- [ ] **Step 3: Verificar que el servidor arranca sin errores**

```bash
python -c "import main; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add templates/registro_corredor.html main.py
git commit -m "feat: auto-registro de corredor con cola de aprobación"
```

---

## Task 5: Solicitar publicación desde results.html

**Files:**
- Modify: `templates/results.html`
- Modify: `main.py`

- [ ] **Step 1: Agregar ruta `POST /corredor/solicitar-publicacion/{listing_id}` a `main.py`**

Agregar después de la sección `# ── Instagram Publishing ───`:

```python
# ── Solicitud de publicación en RRSS ──────────────────────────────────────────
@app.post("/corredor/solicitar-publicacion/{listing_id}")
async def solicitar_publicacion(
    request: Request,
    listing_id: str,
    redes: List[str] = Form(default=["instagram", "facebook", "whatsapp", "tiktok"]),
):
    corredor_session = get_corredor_session(request)
    empresa_session = get_empresa_session(request)
    if not corredor_session and not empresa_session:
        return RedirectResponse("/login", status_code=302)

    try:
        listing = load_listing(listing_id)
    except Exception:
        return RedirectResponse("/corredor/dashboard?error=Ficha+no+encontrada", status_code=302)

    # Generar imagen vertical si no existe
    img_path = GENERATED / "images" / f"{listing_id}_vertical.jpg"
    if not img_path.exists():
        img_path.parent.mkdir(parents=True, exist_ok=True)
        portada_path = (UPLOADS / listing.foto_portada) if listing.foto_portada else None
        from services.image_service import generar_imagen_vertical
        generar_imagen_vertical(
            listing,
            str(portada_path) if portada_path and portada_path.exists() else None,
            str(img_path),
        )

    # Armar caption
    moneda = getattr(listing, "moneda", "PEN")
    sym = "S/." if moneda == "PEN" else "USD"
    caption = (
        f"{listing.tipo} en {listing.operacion} | {sym} {listing.precio:,}\n"
        f"📍 {listing.ciudad}, {listing.estado}\n\n"
        f"{listing.copy_instagram or listing.descripcion_generada or ''}\n\n"
        f"#InmersivaInmobiliaria #BienesRaices #Inmuebles"
    )

    db = SessionLocal()
    try:
        corredor_obj = None
        if corredor_session:
            corredor_obj = db.query(CorredorModel).filter(
                CorredorModel.username == corredor_session["sub"]
            ).first()

        # Verificar que no haya solicitud pendiente para este listing
        existing = db.query(PostRRSS).filter(
            PostRRSS.listing_id == listing_id,
            PostRRSS.estado.in_(["Pendiente", "Aprobado", "Publicado"]),
        ).first()
        if existing:
            return RedirectResponse(
                f"/corredor/dashboard?error=Ya+existe+solicitud+para+esta+ficha",
                status_code=302,
            )

        post = PostRRSS(
            corredor_id=corredor_obj.id if corredor_obj else 1,
            red=",".join(redes),
            contenido=caption,
            listing_id=listing_id,
            titulo=f"{listing.tipo} en {listing.operacion} — {listing.ciudad}",
            imagen_url=str(img_path),
            estado="Pendiente",
            redes=",".join(redes),
            caption=caption,
        )
        db.add(post)
        db.commit()
    finally:
        db.close()

    return RedirectResponse("/corredor/dashboard?seccion=publicaciones&ok=Solicitud+enviada", status_code=302)
```

- [ ] **Step 2: Actualizar la sección de acciones de `templates/results.html`**

Reemplazar el bloque `<!-- Acciones -->` existente con:

```html
  <!-- Acciones -->
  <div class="card">
    <div class="card-title">Descargas y Publicación</div>
    <div class="actions-row">
      <a href="/pdf/{{ listing.id }}" class="btn btn-primary" target="_blank">📄 Descargar PDF</a>
      <a href="/imagen/{{ listing.id }}" class="btn btn-gold" download>🖼 Imagen Cuadrada</a>
      <a href="/imagen-vertical/{{ listing.id }}" class="btn btn-gold" download id="btn-vertical">📱 Imagen Stories</a>
      <button onclick="publicarInstagram('{{ listing.id }}')" class="btn btn-outline">📲 Test Instagram</button>
      <button onclick="generarVideo('{{ listing.id }}')" class="btn btn-outline" id="btn-video">🎬 Generar Video</button>
    </div>

    <!-- Preview imagen vertical -->
    <div id="preview-vertical" style="display:none;margin-top:20px;text-align:center">
      <img id="img-vertical-preview" src="/imagen-vertical/{{ listing.id }}"
           style="max-height:400px;border-radius:12px;box-shadow:0 4px 24px rgba(0,0,0,.3)" alt="Preview">
      <p style="color:var(--gray-600);font-size:.85rem;margin-top:8px">Imagen 1080×1920 para Stories/Reels</p>
    </div>

    <!-- Solicitar publicación -->
    <div style="margin-top:28px;padding:20px;background:#f8f9fa;border-radius:10px;border:1.5px solid #e0e0e0">
      <h3 style="margin:0 0 12px;font-size:1rem;color:#1B2A4A">📢 Solicitar publicación en redes sociales</h3>
      <form method="post" action="/corredor/solicitar-publicacion/{{ listing.id }}" id="form-publicar">
        <div style="display:flex;flex-wrap:wrap;gap:12px;margin-bottom:16px">
          <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
            <input type="checkbox" name="redes" value="instagram" checked> Instagram
          </label>
          <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
            <input type="checkbox" name="redes" value="facebook" checked> Facebook
          </label>
          <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
            <input type="checkbox" name="redes" value="whatsapp" checked> WhatsApp
          </label>
          <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
            <input type="checkbox" name="redes" value="tiktok"> TikTok
          </label>
        </div>
        <p style="color:#666;font-size:.85rem;margin:0 0 12px">
          El admin revisará tu solicitud y publicará en las redes seleccionadas. Recibirás una notificación en tu dashboard.
        </p>
        <button type="submit" class="btn btn-primary" style="width:100%">
          🚀 Solicitar publicación
        </button>
      </form>
    </div>
  </div>
```

- [ ] **Step 3: Commit**

```bash
git add templates/results.html main.py
git commit -m "feat: solicitar publicación RRSS desde results.html + imagen vertical"
```

---

## Task 6: Dashboard corredor — Mis publicaciones y Mi perfil

**Files:**
- Modify: `templates/dashboard_corredor.html`
- Modify: `main.py`

- [ ] **Step 1: Agregar ruta de perfil del corredor a `main.py`**

Agregar después de la sección de registro corredor:

```python
# ── Perfil corredor ────────────────────────────────────────────────────────────
@app.get("/corredor/perfil", response_class=HTMLResponse)
async def perfil_corredor_page(request: Request):
    corredor, redir = _corredor_or_redirect(request)
    if redir:
        return redir
    db = SessionLocal()
    try:
        corredor_obj = db.query(CorredorModel).filter(CorredorModel.id == corredor.id).first()
    finally:
        db.close()
    return templates.TemplateResponse(request, "dashboard_corredor.html", {
        "corredor": corredor_obj,
        "seccion": "perfil",
    })


@app.post("/corredor/perfil")
async def actualizar_perfil(
    request: Request,
    bio: str = Form(default=""),
    instagram: str = Form(default=""),
    whatsapp: str = Form(default=""),
    foto_perfil: UploadFile = File(default=None),
):
    corredor, redir = _corredor_or_redirect(request)
    if redir:
        return redir
    db = SessionLocal()
    try:
        corredor_obj = db.query(CorredorModel).filter(CorredorModel.id == corredor.id).first()
        if corredor_obj:
            corredor_obj.bio = bio
            corredor_obj.instagram = instagram
            corredor_obj.whatsapp = whatsapp
            if foto_perfil and foto_perfil.filename:
                ext = Path(foto_perfil.filename).suffix
                fname = f"perfil_{corredor_obj.id}{ext}"
                dest = Path("uploads") / fname
                save_upload(foto_perfil, dest)
                corredor_obj.foto_perfil = fname
            db.commit()
    finally:
        db.close()
    return RedirectResponse("/corredor/dashboard?seccion=perfil&ok=Perfil+actualizado", status_code=302)
```

- [ ] **Step 2: Actualizar la ruta `/corredor/dashboard` para incluir publicaciones**

En `main.py`, buscar la ruta `@app.get("/corredor/dashboard"...)` y agregar la query de publicaciones:

```python
# En la ruta existente /corredor/dashboard, agregar dentro del bloque db:
posts_rrss = db.query(PostRRSS).filter(
    PostRRSS.corredor_id == corredor_obj.id,
    PostRRSS.listing_id != None,
).order_by(PostRRSS.created_at.desc()).limit(50).all()
```

Y pasar `posts_rrss=posts_rrss` al contexto del template.

- [ ] **Step 3: Agregar sección "Mis publicaciones" a `templates/dashboard_corredor.html`**

Agregar dentro del sistema de tabs existente. Buscar el bloque de tabs de navegación y agregar:

```html
<!-- En la barra de tabs del corredor -->
<button class="tab-btn {% if seccion == 'publicaciones' %}active{% endif %}"
        onclick="showTab('publicaciones')">📢 Publicaciones</button>
<button class="tab-btn {% if seccion == 'perfil' %}active{% endif %}"
        onclick="showTab('perfil')">👤 Mi Perfil</button>

<!-- Sección Publicaciones -->
<div id="tab-publicaciones" class="tab-content" style="display:{% if seccion == 'publicaciones' %}block{% else %}none{% endif %}">
  <div class="card">
    <div class="card-title">Mis Publicaciones en Redes Sociales</div>

    {% if not posts_rrss %}
    <p style="color:#888;text-align:center;padding:32px 0">
      Aún no tienes publicaciones. Llena una ficha y solicita publicación.
    </p>
    {% else %}
    <div style="overflow-x:auto">
      <table style="width:100%;border-collapse:collapse">
        <thead>
          <tr style="background:#f5f7fa;font-size:.8rem;color:#666;text-transform:uppercase;letter-spacing:1px">
            <th style="padding:12px 16px;text-align:left">Propiedad</th>
            <th style="padding:12px 16px;text-align:left">Redes</th>
            <th style="padding:12px 16px;text-align:center">Estado</th>
            <th style="padding:12px 16px;text-align:left">Fecha</th>
            <th style="padding:12px 16px;text-align:left">Comentario Admin</th>
          </tr>
        </thead>
        <tbody>
          {% for post in posts_rrss %}
          <tr style="border-bottom:1px solid #eee">
            <td style="padding:14px 16px">
              <div style="font-weight:600;font-size:.9rem">{{ post.titulo or '—' }}</div>
              {% if post.imagen_url %}
              <img src="/generated/images/{{ post.listing_id }}_vertical.jpg"
                   onerror="this.style.display='none'"
                   style="height:60px;border-radius:4px;margin-top:6px">
              {% endif %}
            </td>
            <td style="padding:14px 16px;font-size:.85rem;color:#555">
              {{ post.redes or post.red }}
            </td>
            <td style="padding:14px 16px;text-align:center">
              {% if post.estado == 'Publicado' %}
                <span style="background:#d4edda;color:#155724;padding:4px 10px;border-radius:20px;font-size:.8rem;font-weight:600">✅ Publicado</span>
              {% elif post.estado == 'Aprobado' %}
                <span style="background:#cce5ff;color:#004085;padding:4px 10px;border-radius:20px;font-size:.8rem;font-weight:600">🔄 Aprobado</span>
              {% elif post.estado == 'Rechazado' %}
                <span style="background:#f8d7da;color:#721c24;padding:4px 10px;border-radius:20px;font-size:.8rem;font-weight:600">❌ Rechazado</span>
              {% else %}
                <span style="background:#fff3cd;color:#856404;padding:4px 10px;border-radius:20px;font-size:.8rem;font-weight:600">⏳ Pendiente</span>
              {% endif %}
            </td>
            <td style="padding:14px 16px;font-size:.85rem;color:#666">
              {{ post.publicado_at.strftime('%d/%m/%Y') if post.publicado_at else post.created_at.strftime('%d/%m/%Y') }}
            </td>
            <td style="padding:14px 16px;font-size:.85rem;color:{% if post.estado == 'Rechazado' %}#721c24{% else %}#555{% endif %}">
              {{ post.comentario_admin or '—' }}
              {% if post.estado == 'Rechazado' and post.listing_id %}
              <br><a href="/nueva-ficha" style="color:#C9A84C;font-size:.8rem">Corregir ficha →</a>
              {% endif %}
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    {% endif %}
  </div>
</div>

<!-- Sección Mi Perfil -->
<div id="tab-perfil" class="tab-content" style="display:{% if seccion == 'perfil' %}block{% else %}none{% endif %}">
  <div class="card">
    <div class="card-title">Mi Perfil Profesional</div>
    <form method="post" action="/corredor/perfil" enctype="multipart/form-data">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
        <div>
          <label style="display:block;margin-bottom:6px;color:#666;font-size:.85rem">Foto de perfil</label>
          {% if corredor.foto_perfil %}
          <img src="/uploads/{{ corredor.foto_perfil }}" style="height:80px;border-radius:50%;margin-bottom:8px;display:block">
          {% endif %}
          <input type="file" name="foto_perfil" accept="image/*" style="font-size:.85rem">
        </div>
        <div>
          <label style="display:block;margin-bottom:6px;color:#666;font-size:.85rem">Instagram (@usuario)</label>
          <input type="text" name="instagram" value="{{ corredor.instagram or '' }}"
                 placeholder="@tususario" style="width:100%;padding:10px;border:1.5px solid #ddd;border-radius:6px;box-sizing:border-box">

          <label style="display:block;margin-top:14px;margin-bottom:6px;color:#666;font-size:.85rem">WhatsApp</label>
          <input type="tel" name="whatsapp" value="{{ corredor.whatsapp or '' }}"
                 placeholder="+51 999 999 999" style="width:100%;padding:10px;border:1.5px solid #ddd;border-radius:6px;box-sizing:border-box">
        </div>
      </div>
      <label style="display:block;margin-top:18px;margin-bottom:6px;color:#666;font-size:.85rem">Bio profesional</label>
      <textarea name="bio" rows="4"
                style="width:100%;padding:10px;border:1.5px solid #ddd;border-radius:6px;box-sizing:border-box;resize:vertical"
                placeholder="Cuéntanos sobre tu experiencia y especialidad...">{{ corredor.bio or '' }}</textarea>

      <button type="submit" class="btn btn-primary" style="margin-top:20px">Guardar perfil</button>
    </form>
  </div>
</div>
```

- [ ] **Step 4: Commit**

```bash
git add templates/dashboard_corredor.html main.py
git commit -m "feat: dashboard corredor — mis publicaciones con estado + perfil editable"
```

---

## Task 7: Flujo de aprobación admin

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Agregar rutas de aprobación de solicitudes de corredor a `main.py`**

Agregar después de `# ── Admin: nuevo corredor ───`:

```python
# ── Admin: aprobar / rechazar solicitud de corredor ───────────────────────────
@app.post("/admin/solicitud/{solicitud_id}/aprobar")
async def aprobar_solicitud_corredor(
    request: Request,
    solicitud_id: int,
    username: str = Form(...),
    password: str = Form(...),
):
    if not get_empresa_session(request):
        return RedirectResponse("/login", status_code=302)
    db = SessionLocal()
    try:
        from models.db_models import SolicitudCorredor
        sol = db.query(SolicitudCorredor).filter(SolicitudCorredor.id == solicitud_id).first()
        if not sol:
            return RedirectResponse("/dashboard?error=Solicitud+no+encontrada", status_code=302)
        existe = db.query(CorredorModel).filter(
            (CorredorModel.email == sol.email) | (CorredorModel.username == username)
        ).first()
        if existe:
            return RedirectResponse("/dashboard?error=Email+o+usuario+ya+existe", status_code=302)
        nuevo_corredor = CorredorModel(
            nombre=sol.nombre, email=sol.email, telefono=sol.telefono,
            username=username, hashed_password=hash_password(password),
        )
        db.add(nuevo_corredor)
        sol.estado = "Aprobado"
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/dashboard?ok=Corredor+creado+exitosamente", status_code=302)


@app.post("/admin/solicitud/{solicitud_id}/rechazar")
async def rechazar_solicitud_corredor(request: Request, solicitud_id: int):
    if not get_empresa_session(request):
        return RedirectResponse("/login", status_code=302)
    db = SessionLocal()
    try:
        from models.db_models import SolicitudCorredor
        sol = db.query(SolicitudCorredor).filter(SolicitudCorredor.id == solicitud_id).first()
        if sol:
            sol.estado = "Rechazado"
            db.commit()
    finally:
        db.close()
    return RedirectResponse("/dashboard", status_code=302)
```

- [ ] **Step 2: Agregar rutas de aprobación de posts a `main.py`**

```python
# ── Admin: aprobar / rechazar post RRSS ───────────────────────────────────────
@app.post("/admin/post/{post_id}/aprobar")
async def aprobar_post(
    request: Request,
    post_id: int,
    comentario: str = Form(default=""),
):
    if not get_empresa_session(request):
        return RedirectResponse("/login", status_code=302)
    db = SessionLocal()
    try:
        post = db.query(PostRRSS).filter(PostRRSS.id == post_id).first()
        if not post:
            return RedirectResponse("/dashboard?error=Post+no+encontrado", status_code=302)
        post.estado = "Aprobado"
        post.comentario_admin = comentario
        db.commit()

        # Publicar en UploadPost
        from services.uploadpost_service import publicar_en_redes, UploadPostError
        redes = post.redes_list if post.redes_list else ["instagram"]
        imagen = post.imagen_url or ""
        caption = post.caption or post.contenido or ""

        try:
            resultado = publicar_en_redes(caption, imagen, redes)
            post.upload_post_id = resultado.get("post_id", "")
            post.estado = "Publicado"
            post.publicado_at = datetime.utcnow()
            db.commit()

            # Publicar en portal si tiene listing_id
            if post.listing_id:
                _publicar_en_portal(db, post.listing_id, post.corredor_id)
        except UploadPostError as e:
            print(f"[UploadPost ERROR] post_id={post_id}: {e}")
            # El post queda en estado Aprobado — el admin puede reintentar
    finally:
        db.close()
    return RedirectResponse("/dashboard?seccion=aprobacion&ok=Post+aprobado+y+publicado", status_code=302)


@app.post("/admin/post/{post_id}/rechazar")
async def rechazar_post(
    request: Request,
    post_id: int,
    comentario: str = Form(...),
):
    if not get_empresa_session(request):
        return RedirectResponse("/login", status_code=302)
    db = SessionLocal()
    try:
        post = db.query(PostRRSS).filter(PostRRSS.id == post_id).first()
        if post:
            post.estado = "Rechazado"
            post.comentario_admin = comentario
            db.commit()
    finally:
        db.close()
    return RedirectResponse("/dashboard?seccion=aprobacion", status_code=302)


@app.post("/admin/post/{post_id}/reintentar")
async def reintentar_post(request: Request, post_id: int):
    if not get_empresa_session(request):
        return RedirectResponse("/login", status_code=302)
    db = SessionLocal()
    try:
        post = db.query(PostRRSS).filter(PostRRSS.id == post_id).first()
        if not post or post.estado != "Aprobado":
            return RedirectResponse("/dashboard?error=Post+no+válido+para+reintento", status_code=302)
        from services.uploadpost_service import publicar_en_redes, UploadPostError
        redes = post.redes_list if post.redes_list else ["instagram"]
        try:
            resultado = publicar_en_redes(post.caption or post.contenido or "", post.imagen_url or "", redes)
            post.upload_post_id = resultado.get("post_id", "")
            post.estado = "Publicado"
            post.publicado_at = datetime.utcnow()
            db.commit()
            if post.listing_id:
                _publicar_en_portal(db, post.listing_id, post.corredor_id)
        except UploadPostError as e:
            return RedirectResponse(f"/dashboard?error=UploadPost+error:+{str(e)[:80]}", status_code=302)
    finally:
        db.close()
    return RedirectResponse("/dashboard?ok=Post+publicado+exitosamente", status_code=302)
```

- [ ] **Step 3: Agregar función helper `_publicar_en_portal` a `main.py`**

Agregar después de la función `fichas_stats`:

```python
def _publicar_en_portal(db, listing_id: str, corredor_id: int | None):
    """Crea o actualiza PropiedadPublica cuando un post es aprobado."""
    try:
        listing = load_listing(listing_id)
    except Exception:
        return
    existing = db.query(PropiedadPublica).filter(PropiedadPublica.listing_id == listing_id).first()
    if existing:
        existing.publicado = True
        db.commit()
        return
    corredor_obj = db.query(CorredorModel).filter(CorredorModel.id == corredor_id).first() if corredor_id else None
    db.add(PropiedadPublica(
        listing_id=listing_id,
        titulo=f"{listing.tipo} en {listing.operacion} — {listing.ciudad}",
        tipo=listing.tipo,
        operacion=listing.operacion,
        precio=listing.precio,
        moneda=getattr(listing, "moneda", "PEN"),
        ciudad=listing.ciudad,
        estado=listing.estado,
        direccion=listing.direccion,
        descripcion=listing.descripcion_generada or getattr(listing, "descripcion_agente", ""),
        habitaciones=listing.recamaras,
        banos=listing.banos,
        m2_construidos=listing.m2_construidos,
        m2_terreno=listing.m2_terreno,
        estacionamientos=listing.estacionamientos,
        foto_portada=listing.foto_portada,
        fotos_extras=json.dumps(listing.fotos_extras or []),
        tour_360_url=getattr(listing, "tour_360_url", ""),
        corredor_id=corredor_obj.id if corredor_obj else None,
    ))
    db.commit()
```

- [ ] **Step 4: Verificar sintaxis**

```bash
python -c "import main; print('OK')"
```

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "feat: rutas admin para aprobar/rechazar solicitudes de corredor y posts RRSS"
```

---

## Task 8: Dashboard empresa — cola, actividad y solicitudes

**Files:**
- Modify: `templates/dashboard_empresa.html`
- Modify: `main.py` (ruta /dashboard)

- [ ] **Step 1: Actualizar ruta `/dashboard` para incluir datos de cola y actividad**

Dentro del bloque `@app.get("/dashboard"...)` existente, agregar queries adicionales:

```python
# Agregar dentro del bloque db del dashboard existente:
from models.db_models import SolicitudCorredor

# Cola de aprobación
posts_pendientes = db.query(PostRRSS).filter(
    PostRRSS.estado == "Pendiente",
    PostRRSS.listing_id != None,
).order_by(PostRRSS.created_at.asc()).all()

# Solicitudes de corredor pendientes
solicitudes = db.query(SolicitudCorredor).order_by(
    SolicitudCorredor.created_at.desc()
).limit(50).all()
solicitudes_pendientes = [s for s in solicitudes if s.estado == "Pendiente"]

# Actividad: fichas por corredor
corredores_list = db.query(CorredorModel).filter(CorredorModel.activo == True).all()
actividad_corredores = []
for c in corredores_list:
    fichas_c = list_fichas(c.email)
    posts_c = db.query(PostRRSS).filter(
        PostRRSS.corredor_id == c.id,
        PostRRSS.listing_id != None,
    ).all()
    actividad_corredores.append({
        "corredor": c,
        "fichas": len(fichas_c),
        "posts_pendientes": sum(1 for p in posts_c if p.estado == "Pendiente"),
        "posts_publicados": sum(1 for p in posts_c if p.estado == "Publicado"),
    })
```

Y agregar al contexto del template:
```python
"posts_pendientes": posts_pendientes,
"solicitudes": solicitudes,
"solicitudes_pendientes": solicitudes_pendientes,
"actividad_corredores": actividad_corredores,
```

- [ ] **Step 2: Agregar sección "Cola de Aprobación" a `dashboard_empresa.html`**

Agregar como primera sección prominente en el dashboard, antes de la lista de fichas:

```html
<!-- Badge de pendientes en la navegación -->
{% if posts_pendientes %}
<div style="background:#fff3cd;border:1.5px solid #ffc107;border-radius:10px;padding:14px 20px;margin-bottom:20px;display:flex;align-items:center;gap:12px">
  <span style="font-size:1.5rem">⏳</span>
  <span style="font-weight:600;color:#856404">
    Tienes <strong>{{ posts_pendientes|length }}</strong> publicación(es) esperando aprobación
  </span>
  <button onclick="showAdminTab('aprobacion')" class="btn btn-primary" style="margin-left:auto;padding:8px 16px;font-size:.85rem">
    Ver cola →
  </button>
</div>
{% endif %}

<!-- Tab: Cola de Aprobación -->
<div id="admin-tab-aprobacion" class="tab-content">
  <div class="card">
    <div class="card-title">📋 Cola de Aprobación</div>
    {% if not posts_pendientes %}
    <p style="color:#888;text-align:center;padding:32px 0">No hay publicaciones pendientes. ✅</p>
    {% else %}
    {% for post in posts_pendientes %}
    <div style="display:flex;gap:16px;padding:20px;border:1.5px solid #e0e0e0;border-radius:10px;margin-bottom:16px;align-items:flex-start">
      <!-- Miniatura imagen vertical -->
      <div style="flex-shrink:0">
        <img src="/generated/images/{{ post.listing_id }}_vertical.jpg"
             onerror="this.src='/static/img/logo.jpeg'"
             style="width:80px;height:140px;object-fit:cover;border-radius:8px">
      </div>
      <!-- Info -->
      <div style="flex:1">
        <div style="font-weight:700;font-size:1rem;margin-bottom:4px">{{ post.titulo or 'Propiedad' }}</div>
        <div style="font-size:.85rem;color:#666;margin-bottom:8px">
          Corredor ID: {{ post.corredor_id }} &nbsp;·&nbsp;
          Redes: {{ post.redes or post.red }} &nbsp;·&nbsp;
          {{ post.created_at.strftime('%d/%m/%Y %H:%M') }}
        </div>
        <div style="font-size:.82rem;color:#555;background:#f8f9fa;padding:8px 12px;border-radius:6px;max-height:60px;overflow:hidden">
          {{ (post.caption or post.contenido or '')[:200] }}
        </div>
      </div>
      <!-- Acciones -->
      <div style="display:flex;flex-direction:column;gap:8px;flex-shrink:0">
        <a href="/imagen-vertical/{{ post.listing_id }}" target="_blank"
           class="btn btn-outline" style="font-size:.8rem;padding:6px 12px;text-align:center">
          👁 Ver imagen
        </a>
        <!-- Aprobar -->
        <form method="post" action="/admin/post/{{ post.id }}/aprobar" style="margin:0">
          <input type="hidden" name="comentario" value="">
          <button type="submit" style="width:100%;padding:8px 14px;background:#28a745;color:white;border:none;border-radius:6px;cursor:pointer;font-size:.85rem;font-weight:600">
            ✅ Aprobar y publicar
          </button>
        </form>
        <!-- Rechazar con comentario -->
        <button onclick="toggleRechazar({{ post.id }})"
                style="padding:8px 14px;background:#dc3545;color:white;border:none;border-radius:6px;cursor:pointer;font-size:.85rem;font-weight:600">
          ❌ Rechazar
        </button>
        <div id="form-rechazar-{{ post.id }}" style="display:none">
          <form method="post" action="/admin/post/{{ post.id }}/rechazar">
            <textarea name="comentario" required placeholder="Motivo del rechazo..."
                      style="width:100%;padding:8px;border:1.5px solid #ddd;border-radius:6px;font-size:.82rem;box-sizing:border-box;height:70px"></textarea>
            <button type="submit" style="width:100%;padding:6px;background:#dc3545;color:white;border:none;border-radius:6px;cursor:pointer;font-size:.82rem;margin-top:4px">
              Confirmar rechazo
            </button>
          </form>
        </div>
      </div>
    </div>
    {% endfor %}
    {% endif %}
  </div>
</div>

<!-- Tab: Actividad Corredores -->
<div id="admin-tab-actividad" class="tab-content" style="display:none">
  <div class="card">
    <div class="card-title">📊 Actividad de Corredores</div>
    <table style="width:100%;border-collapse:collapse">
      <thead>
        <tr style="background:#f5f7fa;font-size:.8rem;color:#666;text-transform:uppercase;letter-spacing:1px">
          <th style="padding:12px 16px;text-align:left">Corredor</th>
          <th style="padding:12px 16px;text-align:center">Fichas</th>
          <th style="padding:12px 16px;text-align:center">Posts pendientes</th>
          <th style="padding:12px 16px;text-align:center">Posts publicados</th>
        </tr>
      </thead>
      <tbody>
        {% for a in actividad_corredores %}
        <tr style="border-bottom:1px solid #eee">
          <td style="padding:14px 16px">
            <div style="font-weight:600">{{ a.corredor.nombre }}</div>
            <div style="font-size:.8rem;color:#888">{{ a.corredor.email }}</div>
          </td>
          <td style="padding:14px 16px;text-align:center;font-weight:700">{{ a.fichas }}</td>
          <td style="padding:14px 16px;text-align:center">
            {% if a.posts_pendientes > 0 %}
            <span style="background:#fff3cd;color:#856404;padding:3px 10px;border-radius:20px;font-size:.85rem;font-weight:600">
              {{ a.posts_pendientes }}
            </span>
            {% else %}0{% endif %}
          </td>
          <td style="padding:14px 16px;text-align:center">
            <span style="background:#d4edda;color:#155724;padding:3px 10px;border-radius:20px;font-size:.85rem;font-weight:600">
              {{ a.posts_publicados }}
            </span>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>

<!-- Tab: Solicitudes de Corredor -->
<div id="admin-tab-solicitudes" class="tab-content" style="display:none">
  <div class="card">
    <div class="card-title">🙋 Solicitudes de Registro</div>
    {% if not solicitudes %}
    <p style="color:#888;text-align:center;padding:32px 0">No hay solicitudes.</p>
    {% else %}
    {% for sol in solicitudes %}
    <div style="padding:16px;border:1.5px solid #e0e0e0;border-radius:8px;margin-bottom:12px">
      <div style="display:flex;justify-content:space-between;align-items:flex-start">
        <div>
          <div style="font-weight:700">{{ sol.nombre }}</div>
          <div style="font-size:.85rem;color:#666">{{ sol.email }} &nbsp;·&nbsp; {{ sol.telefono }}</div>
          {% if sol.mensaje %}
          <div style="font-size:.82rem;color:#555;margin-top:6px;font-style:italic">"{{ sol.mensaje }}"</div>
          {% endif %}
          <div style="font-size:.78rem;color:#999;margin-top:4px">{{ sol.created_at.strftime('%d/%m/%Y %H:%M') }}</div>
        </div>
        <div style="display:flex;flex-direction:column;gap:8px;align-items:flex-end">
          {% if sol.estado == 'Pendiente' %}
          <button onclick="toggleAprobarSol({{ sol.id }})"
                  style="padding:6px 14px;background:#28a745;color:white;border:none;border-radius:6px;cursor:pointer;font-size:.85rem">
            ✅ Aprobar
          </button>
          <div id="form-aprobar-sol-{{ sol.id }}" style="display:none">
            <form method="post" action="/admin/solicitud/{{ sol.id }}/aprobar">
              <input type="text" name="username" required placeholder="Username" style="padding:6px;border:1.5px solid #ddd;border-radius:4px;width:140px">
              <input type="password" name="password" required placeholder="Contraseña temporal" style="padding:6px;border:1.5px solid #ddd;border-radius:4px;width:140px;margin-top:4px">
              <button type="submit" style="display:block;width:100%;padding:6px;background:#1B2A4A;color:white;border:none;border-radius:4px;margin-top:4px;cursor:pointer">
                Crear cuenta
              </button>
            </form>
          </div>
          <form method="post" action="/admin/solicitud/{{ sol.id }}/rechazar" style="margin:0">
            <button type="submit" style="padding:6px 14px;background:#dc3545;color:white;border:none;border-radius:6px;cursor:pointer;font-size:.85rem">
              ❌ Rechazar
            </button>
          </form>
          {% else %}
          <span style="padding:4px 12px;border-radius:20px;font-size:.82rem;font-weight:600;
                {% if sol.estado == 'Aprobado' %}background:#d4edda;color:#155724{% else %}background:#f8d7da;color:#721c24{% endif %}">
            {{ sol.estado }}
          </span>
          {% endif %}
        </div>
      </div>
    </div>
    {% endfor %}
    {% endif %}
  </div>
</div>
```

- [ ] **Step 3: Agregar JS para toggles y tabs en dashboard_empresa.html**

```html
<script>
function toggleRechazar(id) {
  const el = document.getElementById('form-rechazar-' + id);
  el.style.display = el.style.display === 'none' ? 'block' : 'none';
}
function toggleAprobarSol(id) {
  const el = document.getElementById('form-aprobar-sol-' + id);
  el.style.display = el.style.display === 'none' ? 'block' : 'none';
}
function showAdminTab(tab) {
  document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
  const el = document.getElementById('admin-tab-' + tab);
  if (el) el.style.display = 'block';
}
// Auto-mostrar sección según query param
const urlParams = new URLSearchParams(window.location.search);
const seccion = urlParams.get('seccion');
if (seccion) showAdminTab(seccion);
</script>
```

- [ ] **Step 4: Commit**

```bash
git add templates/dashboard_empresa.html main.py
git commit -m "feat: dashboard admin — cola aprobación, actividad corredores, solicitudes registro"
```

---

## Task 9: Tests finales y verificación

**Files:**
- Modify: `tests/test_listing.py`

- [ ] **Step 1: Correr suite completa de tests**

```bash
pytest tests/ -v --tb=short
```

Resultado esperado: todos los tests pasan. Si alguno falla por el campo `estado` u otro campo nuevo en los modelos, ajustar el test.

- [ ] **Step 2: Verificar que Python carga todo sin errores**

```bash
python -c "
import main
from models.db_models import SolicitudCorredor, PostRRSS, Corredor
from services.image_service import generar_imagen_vertical
from services.uploadpost_service import publicar_en_redes
print('Todos los módulos OK')
"
```

Resultado esperado: `Todos los módulos OK`

- [ ] **Step 3: Verificar DB crea tablas nuevas**

```bash
python -c "
from database import engine, Base
from models.db_models import SolicitudCorredor
Base.metadata.create_all(bind=engine)
print('Tablas creadas OK')
"
```

- [ ] **Step 4: Commit final**

```bash
git add -A
git commit -m "test: verificación completa sistema corredores + publicación RRSS"
```

---

## Task 10: Deploy a producción

- [ ] **Step 1: Push a main**

```bash
git push origin main
```

- [ ] **Step 2: Verificar en Coolify**

En el panel de Coolify, verificar que el build inicia automáticamente. El Dockerfile ya tiene todas las dependencias.

- [ ] **Step 3: Configurar variable de entorno UPLOADPOST_API_KEY en Coolify**

En Coolify → Servicio → Environment Variables → Agregar:
```
UPLOADPOST_API_KEY=tu_api_key_real
```

Rearrancar el servicio después de agregar la variable.

- [ ] **Step 4: Smoke test en producción**

1. Ir a `https://inmobiliariainmersiva.com/corredor/registro` → verificar que el formulario carga
2. Ir a `https://inmobiliariainmersiva.com/login` → verificar login corredor funciona
3. Ir a `https://inmobiliariainmersiva.com/dashboard` → verificar sección "Cola de Aprobación" visible

---

## Notas de implementación

- **UploadPost API:** Verificar los endpoints exactos en https://docs.uploadpost.co — los paths `/v1/media` y `/v1/posts` pueden variar según la versión de su API.
- **Fuentes Inter:** Si `curl` falla por certificado, descargar manualmente de https://rsms.me/inter/ y colocar en `static/fonts/`.
- **DB en producción:** Las columnas nuevas son `nullable=True` — SQLAlchemy con `create_all` las agrega sin romper datos existentes en PostgreSQL solo si las tablas son nuevas. Para columnas en tablas existentes, ejecutar manualmente: `ALTER TABLE posts_rrss ADD COLUMN IF NOT EXISTS listing_id VARCHAR(36);` etc.
