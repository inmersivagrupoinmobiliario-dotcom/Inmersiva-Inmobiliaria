# ListaPro Inmersiva — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 5-phase web tool for Inmersiva real estate agents to generate AI descriptions, PDFs, Instagram images, social posts, and video reels from a property form.

**Architecture:** FastAPI serves a single-page form that collects property data and photos, stores each submission as a JSON file under `generated/{listing_id}/`, and exposes endpoints for content generation (OpenAI), PDF (WeasyPrint), Instagram image (Pillow), social publishing (Upload Post API), and video reel (Remotion CLI subprocess).

**Tech Stack:** Python 3.11, FastAPI, Jinja2, OpenAI GPT-4o, WeasyPrint, Pillow, Remotion, httpx, python-dotenv

---

## File Map

| File | Responsibility |
|------|----------------|
| `main.py` | FastAPI app, all routes |
| `models/listing.py` | Pydantic `Listing` model |
| `services/ai_service.py` | OpenAI GPT-4o calls |
| `services/pdf_service.py` | WeasyPrint PDF generation |
| `services/image_service.py` | Pillow 1080×1080 image |
| `services/social_service.py` | Upload Post API HTTP call |
| `services/video_service.py` | Remotion CLI subprocess |
| `templates/form.html` | Property input form |
| `templates/results.html` | Results page with all download buttons |
| `templates/pdf_template.html` | WeasyPrint HTML template |
| `static/css/style.css` | Inmersiva brand styles (navy + gold) |
| `static/js/main.js` | Copy-to-clipboard, video polling |
| `video/src/PropertyReel.tsx` | Remotion React component |
| `video/src/Root.tsx` | Remotion composition root |
| `.env` | API keys |
| `requirements.txt` | Python dependencies |

---

## Task 1: Project Setup & Environment

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.env` (not committed)
- Create: `static/css/style.css` (empty placeholder)
- Create: `static/js/main.js` (empty placeholder)
- Create: `uploads/.gitkeep`
- Create: `generated/.gitkeep`

- [ ] **Step 1: Create requirements.txt**

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
python-multipart==0.0.9
python-dotenv==1.0.1
openai==1.30.1
weasyprint==62.3
Pillow==10.3.0
jinja2==3.1.4
httpx==0.27.0
aiofiles==23.2.1
pytest==8.2.1
pytest-asyncio==0.23.7
httpx==0.27.0
```

- [ ] **Step 2: Create .env.example**

```
OPENAI_API_KEY=sk-...
UPLOADPOST_API_KEY=...
UPLOADPOST_USER=...
```

- [ ] **Step 3: Create .env with real keys (do not commit)**

```
OPENAI_API_KEY=<tu-clave-openai>
UPLOADPOST_API_KEY=<tu-clave-uploadpost>
UPLOADPOST_USER=<tu-usuario-uploadpost>
```

- [ ] **Step 4: Install dependencies**

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Expected: all packages install without errors.

- [ ] **Step 5: Create directory structure**

```bash
mkdir -p models services templates static/css static/js uploads generated/pdfs generated/images generated/videos tests
touch uploads/.gitkeep generated/.gitkeep static/css/style.css static/js/main.js
```

- [ ] **Step 6: Create .gitignore**

```
.env
venv/
uploads/
generated/
__pycache__/
*.pyc
.DS_Store
node_modules/
```

- [ ] **Step 7: Commit**

```bash
git add requirements.txt .env.example .gitignore static/ models/ services/ templates/ tests/ uploads/.gitkeep generated/.gitkeep
git commit -m "chore: project scaffold and dependencies"
```

---

## Task 2: Listing Model

**Files:**
- Create: `models/__init__.py`
- Create: `models/listing.py`
- Create: `tests/test_listing.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_listing.py
from models.listing import Listing

def test_listing_defaults():
    l = Listing(
        tipo="Casa",
        operacion="Venta",
        direccion="Av. Reforma 100",
        ciudad="CDMX",
        estado="CDMX",
        precio=3500000,
        descripcion_agente="Amplia y luminosa",
        agente_nombre="Carlos López",
        agente_telefono="5512345678",
        agente_email="carlos@inmersiva.com",
    )
    assert l.id != ""
    assert l.amenidades == []
    assert l.fotos_extras == []

def test_listing_precio_formateado():
    l = Listing(
        tipo="Departamento", operacion="Renta",
        direccion="Nápoles 45", ciudad="CDMX", estado="CDMX",
        precio=25000,
        descripcion_agente="Moderno y bien ubicado",
        agente_nombre="Ana M", agente_telefono="55999", agente_email="a@b.com",
    )
    assert l.precio_str == "$25,000 MXN"
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_listing.py -v
```

Expected: `ImportError` or `AttributeError`.

- [ ] **Step 3: Implement model**

```python
# models/__init__.py
# (empty)
```

```python
# models/listing.py
from pydantic import BaseModel, Field, computed_field
from typing import Optional, List
import uuid
from datetime import datetime

class Listing(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tipo: str
    operacion: str
    direccion: str
    ciudad: str
    estado: str
    precio: int
    recamaras: Optional[int] = None
    banos: Optional[float] = None
    m2_construidos: Optional[int] = None
    m2_terreno: Optional[int] = None
    estacionamientos: Optional[int] = None
    amenidades: List[str] = []
    descripcion_agente: str
    agente_nombre: str
    agente_telefono: str
    agente_email: str
    foto_portada: str = ""
    fotos_extras: List[str] = []
    descripcion_generada: str = ""
    copy_instagram: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    @computed_field
    @property
    def precio_str(self) -> str:
        return f"${self.precio:,} MXN"
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_listing.py -v
```

Expected: 2 PASSED.

- [ ] **Step 5: Commit**

```bash
git add models/ tests/test_listing.py
git commit -m "feat: Listing Pydantic model with computed precio_str"
```

---

## Task 3: AI Service

**Files:**
- Create: `services/__init__.py`
- Create: `services/ai_service.py`
- Create: `tests/test_ai_service.py`

- [ ] **Step 1: Write failing test (with OpenAI mock)**

```python
# tests/test_ai_service.py
from unittest.mock import patch, MagicMock
from models.listing import Listing
from services.ai_service import generar_contenido

def _make_listing():
    return Listing(
        tipo="Casa", operacion="Venta",
        direccion="Calle Pino 12", ciudad="Guadalajara", estado="Jalisco",
        precio=4200000, recamaras=3, banos=2.5, m2_construidos=180,
        amenidades=["alberca", "jardín"],
        descripcion_agente="Excelente ubicación cerca de parques",
        agente_nombre="Luis R", agente_telefono="33112233", agente_email="luis@inmersiva.com",
    )

def test_generar_contenido_returns_two_strings():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = (
        "[DESCRIPCIÓN]\nDescripción profesional de prueba.\n\n"
        "---INSTAGRAM---\n[INSTAGRAM]\nCopy para Instagram. #BienesRaices"
    )
    with patch("services.ai_service.client.chat.completions.create", return_value=mock_response):
        desc, copy = generar_contenido(_make_listing())
    assert len(desc) > 10
    assert "#" in copy

def test_generar_contenido_strips_markers():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = (
        "[DESCRIPCIÓN]\nTexto limpio.\n\n---INSTAGRAM---\n[INSTAGRAM]\nCopy limpio. #mx"
    )
    with patch("services.ai_service.client.chat.completions.create", return_value=mock_response):
        desc, copy = generar_contenido(_make_listing())
    assert "[DESCRIPCIÓN]" not in desc
    assert "[INSTAGRAM]" not in copy
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_ai_service.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement AI service**

```python
# services/__init__.py
# (empty)
```

```python
# services/ai_service.py
import os
from openai import OpenAI
from models.listing import Listing

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

    response = client.chat.completions.create(
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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_ai_service.py -v
```

Expected: 2 PASSED.

- [ ] **Step 5: Commit**

```bash
git add services/ tests/test_ai_service.py
git commit -m "feat: AI content generation service with OpenAI GPT-4o"
```

---

## Task 4: CSS — Inmersiva Brand Styles

**Files:**
- Modify: `static/css/style.css`

- [ ] **Step 1: Write brand stylesheet**

```css
/* static/css/style.css */
:root {
  --navy: #1B2A4A;
  --gold: #C9A84C;
  --gold-light: #E8C96A;
  --white: #FFFFFF;
  --gray-50: #F8F9FA;
  --gray-100: #F1F3F5;
  --gray-300: #DEE2E6;
  --gray-600: #6C757D;
  --gray-800: #343A40;
  --shadow-sm: 0 1px 3px rgba(0,0,0,.08);
  --shadow-md: 0 4px 16px rgba(0,0,0,.12);
  --shadow-lg: 0 8px 32px rgba(0,0,0,.16);
  --radius: 10px;
  --radius-sm: 6px;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  background: var(--gray-50);
  color: var(--gray-800);
  line-height: 1.6;
}

/* ── Header ────────────────────────────────── */
.header {
  background: var(--navy);
  padding: 1rem 2rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  box-shadow: var(--shadow-md);
}
.header img { height: 52px; }
.header-text h1 { color: var(--white); font-size: 1.4rem; font-weight: 700; letter-spacing: .5px; }
.header-text p  { color: var(--gold); font-size: .82rem; letter-spacing: 1.5px; text-transform: uppercase; }

/* ── Container ─────────────────────────────── */
.container { max-width: 860px; margin: 2.5rem auto; padding: 0 1.5rem; }

/* ── Card ──────────────────────────────────── */
.card {
  background: var(--white);
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
  padding: 2rem;
  margin-bottom: 1.5rem;
}
.card-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--navy);
  text-transform: uppercase;
  letter-spacing: 1px;
  border-bottom: 2px solid var(--gold);
  padding-bottom: .5rem;
  margin-bottom: 1.5rem;
}

/* ── Form ──────────────────────────────────── */
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.form-grid.cols-3 { grid-template-columns: 1fr 1fr 1fr; }
.form-group { display: flex; flex-direction: column; gap: .4rem; }
.form-group.full { grid-column: 1 / -1; }

label { font-size: .82rem; font-weight: 600; color: var(--navy); text-transform: uppercase; letter-spacing: .5px; }

input[type="text"],
input[type="email"],
input[type="number"],
select,
textarea {
  border: 1.5px solid var(--gray-300);
  border-radius: var(--radius-sm);
  padding: .6rem .85rem;
  font-size: .95rem;
  color: var(--gray-800);
  background: var(--white);
  transition: border-color .2s;
  width: 100%;
}
input:focus, select:focus, textarea:focus {
  outline: none;
  border-color: var(--gold);
  box-shadow: 0 0 0 3px rgba(201,168,76,.15);
}
textarea { resize: vertical; min-height: 90px; }

/* Amenidades checkboxes */
.amenidades-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: .5rem; }
.amenidad-item { display: flex; align-items: center; gap: .5rem; font-size: .9rem; cursor: pointer; }
.amenidad-item input[type="checkbox"] { accent-color: var(--gold); width: 16px; height: 16px; }

/* File upload */
.file-upload-area {
  border: 2px dashed var(--gray-300);
  border-radius: var(--radius);
  padding: 1.5rem;
  text-align: center;
  cursor: pointer;
  transition: border-color .2s, background .2s;
}
.file-upload-area:hover { border-color: var(--gold); background: rgba(201,168,76,.04); }
.file-upload-area input[type="file"] { display: none; }
.file-upload-area .upload-label { color: var(--navy); font-weight: 600; }
.file-upload-area .upload-hint { font-size: .82rem; color: var(--gray-600); margin-top: .25rem; }
.preview-grid { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: 1rem; justify-content: center; }
.preview-grid img { width: 80px; height: 80px; object-fit: cover; border-radius: var(--radius-sm); border: 2px solid var(--gray-300); }

/* ── Buttons ───────────────────────────────── */
.btn {
  display: inline-flex; align-items: center; gap: .5rem;
  padding: .75rem 1.75rem;
  border: none; border-radius: var(--radius-sm);
  font-size: .95rem; font-weight: 700;
  cursor: pointer; transition: all .2s;
  text-decoration: none;
}
.btn-primary   { background: var(--navy); color: var(--white); }
.btn-primary:hover { background: #243660; box-shadow: var(--shadow-md); }
.btn-gold      { background: var(--gold); color: var(--navy); }
.btn-gold:hover { background: var(--gold-light); box-shadow: var(--shadow-md); }
.btn-outline   { background: transparent; color: var(--navy); border: 2px solid var(--navy); }
.btn-outline:hover { background: var(--navy); color: var(--white); }
.btn-sm        { padding: .45rem 1rem; font-size: .85rem; }
.btn-block     { width: 100%; justify-content: center; margin-top: 1.5rem; font-size: 1rem; padding: 1rem; }

/* ── Results ───────────────────────────────── */
.result-box {
  background: var(--gray-50);
  border: 1px solid var(--gray-300);
  border-radius: var(--radius-sm);
  padding: 1.25rem;
  font-size: .95rem;
  line-height: 1.7;
  white-space: pre-wrap;
  position: relative;
}
.copy-btn {
  position: absolute; top: .75rem; right: .75rem;
  background: var(--navy); color: var(--white);
  border: none; border-radius: var(--radius-sm);
  padding: .3rem .75rem; font-size: .8rem; font-weight: 600; cursor: pointer;
}
.copy-btn:hover { background: var(--gold); color: var(--navy); }

.actions-row { display: flex; flex-wrap: wrap; gap: .75rem; margin-top: 1rem; }

/* ── Alert ─────────────────────────────────── */
.alert { padding: .85rem 1.25rem; border-radius: var(--radius-sm); font-size: .9rem; margin-bottom: 1rem; }
.alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
.alert-error   { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }

/* ── Progress ──────────────────────────────── */
.progress-bar { height: 6px; background: var(--gray-100); border-radius: 99px; overflow: hidden; }
.progress-fill { height: 100%; background: linear-gradient(90deg, var(--navy), var(--gold)); transition: width .4s; }

/* ── Footer ────────────────────────────────── */
.footer { text-align: center; padding: 2rem; font-size: .8rem; color: var(--gray-600); }
.footer span { color: var(--gold); font-weight: 700; }

/* ── Responsive ────────────────────────────── */
@media (max-width: 640px) {
  .form-grid, .form-grid.cols-3 { grid-template-columns: 1fr; }
  .header { padding: 1rem; }
  .container { padding: 0 1rem; }
}
```

- [ ] **Step 2: Commit**

```bash
git add static/css/style.css
git commit -m "feat: Inmersiva brand CSS (navy + gold design system)"
```

---

## Task 5: Form HTML Template

**Files:**
- Create: `templates/form.html`

- [ ] **Step 1: Create form template**

```html
<!-- templates/form.html -->
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ListaPro — Inmersiva Grupo Inmobiliario</title>
  <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>

<header class="header">
  <div class="header-text">
    <h1>ListaPro</h1>
    <p>Inmersiva Grupo Inmobiliario</p>
  </div>
</header>

<div class="container">

  {% if error %}
  <div class="alert alert-error">{{ error }}</div>
  {% endif %}

  <form id="listingForm" action="/generar" method="post" enctype="multipart/form-data">

    <!-- Datos de la Propiedad -->
    <div class="card">
      <div class="card-title">Datos de la Propiedad</div>
      <div class="form-grid">
        <div class="form-group">
          <label for="tipo">Tipo de propiedad *</label>
          <select name="tipo" id="tipo" required>
            <option value="">Selecciona...</option>
            <option value="Casa">Casa</option>
            <option value="Departamento">Departamento</option>
            <option value="Terreno">Terreno</option>
            <option value="Penthouse">Penthouse</option>
          </select>
        </div>
        <div class="form-group">
          <label for="operacion">Operación *</label>
          <select name="operacion" id="operacion" required>
            <option value="">Selecciona...</option>
            <option value="Venta">Venta</option>
            <option value="Renta">Renta</option>
          </select>
        </div>
        <div class="form-group full">
          <label for="direccion">Dirección / Ubicación *</label>
          <input type="text" name="direccion" id="direccion" placeholder="Ej. Av. Insurgentes Sur 1234, Col. Del Valle" required>
        </div>
        <div class="form-group">
          <label for="ciudad">Ciudad *</label>
          <input type="text" name="ciudad" id="ciudad" placeholder="Ej. Ciudad de México" required>
        </div>
        <div class="form-group">
          <label for="estado">Estado *</label>
          <input type="text" name="estado" id="estado" placeholder="Ej. CDMX" required>
        </div>
        <div class="form-group">
          <label for="precio">Precio (MXN) *</label>
          <input type="number" name="precio" id="precio" placeholder="Ej. 3500000" min="0" required>
        </div>
      </div>
    </div>

    <!-- Características -->
    <div class="card">
      <div class="card-title">Características</div>
      <div class="form-grid cols-3">
        <div class="form-group">
          <label for="recamaras">Recámaras</label>
          <input type="number" name="recamaras" id="recamaras" placeholder="0" min="0">
        </div>
        <div class="form-group">
          <label for="banos">Baños</label>
          <input type="number" name="banos" id="banos" placeholder="0" min="0" step="0.5">
        </div>
        <div class="form-group">
          <label for="estacionamientos">Estacionamientos</label>
          <input type="number" name="estacionamientos" id="estacionamientos" placeholder="0" min="0">
        </div>
        <div class="form-group">
          <label for="m2_construidos">M² Construidos</label>
          <input type="number" name="m2_construidos" id="m2_construidos" placeholder="0" min="0">
        </div>
        <div class="form-group">
          <label for="m2_terreno">M² Terreno</label>
          <input type="number" name="m2_terreno" id="m2_terreno" placeholder="0" min="0">
        </div>
      </div>
    </div>

    <!-- Amenidades -->
    <div class="card">
      <div class="card-title">Amenidades</div>
      <div class="amenidades-grid">
        {% for amenidad in ["Alberca", "Jardín", "Seguridad 24h", "Gimnasio", "Salón de eventos", "Área de juegos", "Roof garden", "Elevador", "Bodega", "Cuarto de servicio", "Estudio", "Cisterna propia", "Paneles solares", "Vista al mar", "Frente a parque"] %}
        <label class="amenidad-item">
          <input type="checkbox" name="amenidades" value="{{ amenidad }}">
          {{ amenidad }}
        </label>
        {% endfor %}
      </div>
    </div>

    <!-- Notas del Agente -->
    <div class="card">
      <div class="card-title">Notas del Agente</div>
      <div class="form-group">
        <label for="descripcion_agente">¿Qué destaca de esta propiedad? (2-3 líneas) *</label>
        <textarea name="descripcion_agente" id="descripcion_agente" rows="3"
          placeholder="Ej. Ubicación privilegiada frente al parque, acabados de lujo, recién remodelada..." required></textarea>
      </div>
    </div>

    <!-- Fotos -->
    <div class="card">
      <div class="card-title">Fotos de la Propiedad</div>
      <div class="form-group" style="margin-bottom:1rem">
        <label>Foto de portada * (aparece grande en el PDF e imagen de Instagram)</label>
        <div class="file-upload-area" onclick="document.getElementById('foto_portada').click()">
          <input type="file" id="foto_portada" name="foto_portada" accept="image/*" required onchange="previewPortada(this)">
          <div class="upload-label">📷 Seleccionar foto de portada</div>
          <div class="upload-hint">JPG, PNG — recomendado mínimo 1200×800px</div>
          <div id="portada-preview" class="preview-grid"></div>
        </div>
      </div>
      <div class="form-group">
        <label>Fotos adicionales (opcional)</label>
        <div class="file-upload-area" onclick="document.getElementById('fotos_extras').click()">
          <input type="file" id="fotos_extras" name="fotos_extras" accept="image/*" multiple onchange="previewExtras(this)">
          <div class="upload-label">📷 Agregar más fotos</div>
          <div class="upload-hint">Puedes seleccionar varias a la vez</div>
          <div id="extras-preview" class="preview-grid"></div>
        </div>
      </div>
    </div>

    <!-- Datos del Agente -->
    <div class="card">
      <div class="card-title">Datos del Agente</div>
      <div class="form-grid">
        <div class="form-group">
          <label for="agente_nombre">Nombre completo *</label>
          <input type="text" name="agente_nombre" id="agente_nombre" placeholder="Ej. Carlos López" required>
        </div>
        <div class="form-group">
          <label for="agente_telefono">Teléfono / WhatsApp *</label>
          <input type="text" name="agente_telefono" id="agente_telefono" placeholder="Ej. 5512345678" required>
        </div>
        <div class="form-group full">
          <label for="agente_email">Email *</label>
          <input type="email" name="agente_email" id="agente_email" placeholder="carlos@inmersiva.com" required>
        </div>
      </div>
    </div>

    <button type="submit" class="btn btn-primary btn-block" id="submitBtn">
      ✨ Generar Contenido con IA
    </button>
  </form>

</div>

<footer class="footer">
  Powered by <span>Inmersiva Grupo Inmobiliario</span> · ListaPro v1.0
</footer>

<script src="/static/js/main.js"></script>
<script>
  document.getElementById('listingForm').addEventListener('submit', function() {
    const btn = document.getElementById('submitBtn');
    btn.disabled = true;
    btn.textContent = '⏳ Generando contenido...';
  });

  function previewPortada(input) {
    const preview = document.getElementById('portada-preview');
    preview.innerHTML = '';
    if (input.files && input.files[0]) {
      const img = document.createElement('img');
      img.src = URL.createObjectURL(input.files[0]);
      preview.appendChild(img);
    }
  }

  function previewExtras(input) {
    const preview = document.getElementById('extras-preview');
    preview.innerHTML = '';
    Array.from(input.files).forEach(file => {
      const img = document.createElement('img');
      img.src = URL.createObjectURL(file);
      preview.appendChild(img);
    });
  }
</script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add templates/form.html
git commit -m "feat: property input form with Inmersiva branding"
```

---

## Task 6: FastAPI App — Phase 1 Routes

**Files:**
- Create: `main.py`

- [ ] **Step 1: Create main.py**

```python
# main.py
import os
import json
import shutil
import uuid
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, Form, File, UploadFile, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from models.listing import Listing
from services.ai_service import generar_contenido

load_dotenv()

app = FastAPI(title="ListaPro — Inmersiva")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/generated", StaticFiles(directory="generated"), name="generated")
templates = Jinja2Templates(directory="templates")

UPLOADS = Path("uploads")
GENERATED = Path("generated")

def save_listing(listing: Listing):
    folder = GENERATED / listing.id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "data.json").write_text(listing.model_dump_json(), encoding="utf-8")

def load_listing(listing_id: str) -> Listing:
    data = (GENERATED / listing_id / "data.json").read_text(encoding="utf-8")
    return Listing.model_validate_json(data)

@app.get("/", response_class=HTMLResponse)
async def form(request: Request):
    return templates.TemplateResponse("form.html", {"request": request})

@app.post("/generar", response_class=HTMLResponse)
async def generar(
    request: Request,
    tipo: str = Form(...),
    operacion: str = Form(...),
    direccion: str = Form(...),
    ciudad: str = Form(...),
    estado: str = Form(...),
    precio: int = Form(...),
    recamaras: Optional[int] = Form(None),
    banos: Optional[float] = Form(None),
    m2_construidos: Optional[int] = Form(None),
    m2_terreno: Optional[int] = Form(None),
    estacionamientos: Optional[int] = Form(None),
    amenidades: List[str] = Form(default=[]),
    descripcion_agente: str = Form(...),
    agente_nombre: str = Form(...),
    agente_telefono: str = Form(...),
    agente_email: str = Form(...),
    foto_portada: UploadFile = File(...),
    fotos_extras: List[UploadFile] = File(default=[]),
):
    listing_id = str(uuid.uuid4())
    upload_dir = UPLOADS / listing_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    portada_name = f"portada_{foto_portada.filename}"
    portada_path = upload_dir / portada_name
    with open(portada_path, "wb") as f:
        shutil.copyfileobj(foto_portada.file, f)

    extras_names = []
    for extra in fotos_extras:
        if extra.filename:
            name = f"extra_{extra.filename}"
            with open(upload_dir / name, "wb") as f:
                shutil.copyfileobj(extra.file, f)
            extras_names.append(f"{listing_id}/{name}")

    listing = Listing(
        id=listing_id, tipo=tipo, operacion=operacion,
        direccion=direccion, ciudad=ciudad, estado=estado, precio=precio,
        recamaras=recamaras, banos=banos, m2_construidos=m2_construidos,
        m2_terreno=m2_terreno, estacionamientos=estacionamientos,
        amenidades=amenidades, descripcion_agente=descripcion_agente,
        agente_nombre=agente_nombre, agente_telefono=agente_telefono,
        agente_email=agente_email,
        foto_portada=f"{listing_id}/{portada_name}",
        fotos_extras=extras_names,
    )

    try:
        descripcion, copy_ig = generar_contenido(listing)
    except Exception as e:
        return templates.TemplateResponse("form.html", {"request": request, "error": f"Error al generar contenido: {e}"})

    listing.descripcion_generada = descripcion
    listing.copy_instagram = copy_ig
    save_listing(listing)

    return templates.TemplateResponse("results.html", {"request": request, "listing": listing})
```

- [ ] **Step 2: Create results.html**

```html
<!-- templates/results.html -->
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Resultados — ListaPro Inmersiva</title>
  <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>

<header class="header">
  <div class="header-text">
    <h1>ListaPro — Resultados</h1>
    <p>Inmersiva Grupo Inmobiliario</p>
  </div>
</header>

<div class="container">

  <div id="alert-container"></div>

  <!-- Resumen de la propiedad -->
  <div class="card">
    <div class="card-title">{{ listing.tipo }} en {{ listing.operacion }} · {{ listing.ciudad }}, {{ listing.estado }}</div>
    <p style="font-size:1.5rem;font-weight:700;color:var(--gold)">{{ listing.precio_str }}</p>
    <p style="color:var(--gray-600);margin-top:.25rem">{{ listing.direccion }}</p>
    <div style="display:flex;gap:1.5rem;margin-top:1rem;flex-wrap:wrap;font-size:.9rem">
      {% if listing.recamaras %}<span>🛏 {{ listing.recamaras }} rec.</span>{% endif %}
      {% if listing.banos %}<span>🚿 {{ listing.banos }} baños</span>{% endif %}
      {% if listing.m2_construidos %}<span>📐 {{ listing.m2_construidos }} m² const.</span>{% endif %}
      {% if listing.estacionamientos %}<span>🚗 {{ listing.estacionamientos }} est.</span>{% endif %}
    </div>
  </div>

  <!-- Descripción IA -->
  <div class="card">
    <div class="card-title">Descripción Profesional</div>
    <div class="result-box" id="desc-box">{{ listing.descripcion_generada }}<button class="copy-btn" onclick="copyText('desc-box')">Copiar</button></div>
  </div>

  <!-- Copy Instagram -->
  <div class="card">
    <div class="card-title">Copy para Instagram</div>
    <div class="result-box" id="ig-box">{{ listing.copy_instagram }}<button class="copy-btn" onclick="copyText('ig-box')">Copiar</button></div>
  </div>

  <!-- Acciones -->
  <div class="card">
    <div class="card-title">Descargas y Publicación</div>
    <div class="actions-row">
      <a href="/pdf/{{ listing.id }}" class="btn btn-primary" target="_blank">📄 Descargar PDF</a>
      <a href="/imagen/{{ listing.id }}" class="btn btn-gold" download>🖼 Descargar Imagen Instagram</a>
      <button onclick="publicarInstagram('{{ listing.id }}')" class="btn btn-outline">📲 Publicar en Instagram</button>
      <button onclick="generarVideo('{{ listing.id }}')" class="btn btn-outline" id="btn-video">🎬 Generar Video Reel</button>
    </div>

    <!-- Video progress -->
    <div id="video-progress" style="display:none;margin-top:1rem">
      <p style="font-size:.9rem;color:var(--navy);margin-bottom:.5rem" id="video-status">Iniciando render...</p>
      <div class="progress-bar"><div class="progress-fill" id="progress-fill" style="width:5%"></div></div>
    </div>
    <div id="video-download" style="display:none;margin-top:1rem">
      <a id="video-link" href="#" class="btn btn-gold" download>⬇️ Descargar Video</a>
    </div>
  </div>

  <a href="/" class="btn btn-outline" style="margin-bottom:2rem">← Nueva Propiedad</a>

</div>

<footer class="footer">
  Powered by <span>Inmersiva Grupo Inmobiliario</span> · ListaPro v1.0
</footer>

<script src="/static/js/main.js"></script>
</body>
</html>
```

- [ ] **Step 3: Create main.js**

```javascript
// static/js/main.js

function copyText(elementId) {
  const box = document.getElementById(elementId);
  const text = box.innerText.replace('Copiar', '').trim();
  navigator.clipboard.writeText(text).then(() => {
    showAlert('✅ Copiado al portapapeles', 'success');
  });
}

function showAlert(msg, type) {
  const container = document.getElementById('alert-container');
  if (!container) return;
  container.innerHTML = `<div class="alert alert-${type}">${msg}</div>`;
  setTimeout(() => { container.innerHTML = ''; }, 3500);
}

function publicarInstagram(listingId) {
  fetch(`/publicar/${listingId}`, { method: 'POST' })
    .then(r => r.json())
    .then(data => {
      if (data.ok) showAlert('✅ Publicado en Instagram exitosamente', 'success');
      else showAlert('❌ Error al publicar: ' + data.error, 'error');
    })
    .catch(() => showAlert('❌ Error de conexión', 'error'));
}

function generarVideo(listingId) {
  const btn = document.getElementById('btn-video');
  btn.disabled = true;
  document.getElementById('video-progress').style.display = 'block';

  fetch(`/video/${listingId}`, { method: 'POST' })
    .then(r => r.json())
    .then(() => pollVideo(listingId));
}

function pollVideo(listingId) {
  const fill = document.getElementById('progress-fill');
  const status = document.getElementById('video-status');
  let progress = 5;

  const interval = setInterval(() => {
    fetch(`/video/status/${listingId}`)
      .then(r => r.json())
      .then(data => {
        if (data.status === 'done') {
          clearInterval(interval);
          fill.style.width = '100%';
          status.textContent = '✅ Video listo';
          document.getElementById('video-download').style.display = 'block';
          document.getElementById('video-link').href = `/generated/videos/${listingId}.mp4`;
        } else if (data.status === 'error') {
          clearInterval(interval);
          status.textContent = '❌ Error al generar video';
        } else {
          progress = Math.min(progress + 8, 90);
          fill.style.width = progress + '%';
          status.textContent = 'Renderizando video...';
        }
      });
  }, 2500);
}
```

- [ ] **Step 4: Start the server and test**

```bash
uvicorn main:app --reload --port 8000
```

Open `http://localhost:8000` — fill the form, submit, and verify the results page shows the AI-generated description and Instagram copy.

- [ ] **Step 5: Commit**

```bash
git add main.py templates/ static/js/main.js
git commit -m "feat: phase 1 — FastAPI form, AI generation, results page"
```

---

## Task 7: PDF Service (Phase 2)

**Files:**
- Create: `services/pdf_service.py`
- Create: `templates/pdf_template.html`
- Create: `tests/test_pdf_service.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_pdf_service.py
from pathlib import Path
from models.listing import Listing
from services.pdf_service import generar_pdf

def _make_listing():
    return Listing(
        tipo="Casa", operacion="Venta",
        direccion="Calle Verde 10", ciudad="Monterrey", estado="NL",
        precio=5000000, recamaras=4, banos=3, m2_construidos=220,
        amenidades=["Alberca", "Jardín"],
        descripcion_agente="Propiedad única",
        agente_nombre="María G", agente_telefono="8112345678", agente_email="m@inmersiva.com",
        foto_portada="",
        descripcion_generada="Descripción profesional de prueba.",
        copy_instagram="Copy de instagram #test",
    )

def test_generar_pdf_creates_file(tmp_path):
    listing = _make_listing()
    out = tmp_path / "test.pdf"
    generar_pdf(listing, str(out))
    assert out.exists()
    assert out.stat().st_size > 1000  # PDF with content
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_pdf_service.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Create PDF HTML template**

```html
<!-- templates/pdf_template.html -->
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<style>
  @page { margin: 0; size: Letter; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Helvetica Neue', Arial, sans-serif; color: #1B2A4A; }

  .header {
    background: #1B2A4A;
    color: white;
    padding: 20px 32px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .header-brand { font-size: 22px; font-weight: 700; letter-spacing: 1px; }
  .header-sub { color: #C9A84C; font-size: 11px; letter-spacing: 2px; text-transform: uppercase; margin-top: 2px; }
  .header-badge {
    background: #C9A84C; color: #1B2A4A;
    font-size: 14px; font-weight: 700;
    padding: 6px 16px; border-radius: 4px;
    text-transform: uppercase; letter-spacing: 1px;
  }

  .portada { width: 100%; height: 320px; object-fit: cover; display: block; }
  .no-photo { height: 200px; background: #F1F3F5; display: flex; align-items: center; justify-content: center; color: #999; font-size: 14px; }

  .content { padding: 24px 32px; }

  .precio { font-size: 32px; font-weight: 700; color: #C9A84C; margin: 12px 0 4px; }
  .ubicacion { font-size: 13px; color: #6C757D; margin-bottom: 16px; }

  .stats-row {
    display: flex; gap: 16px; flex-wrap: wrap;
    background: #F8F9FA; border-radius: 8px;
    padding: 14px 20px; margin-bottom: 20px;
  }
  .stat { display: flex; flex-direction: column; align-items: center; min-width: 70px; }
  .stat-val { font-size: 18px; font-weight: 700; color: #1B2A4A; }
  .stat-label { font-size: 10px; color: #6C757D; text-transform: uppercase; letter-spacing: .5px; margin-top: 2px; }

  .section-title {
    font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1.5px; color: #1B2A4A;
    border-bottom: 2px solid #C9A84C; padding-bottom: 4px; margin-bottom: 10px;
  }
  .descripcion { font-size: 12px; line-height: 1.7; color: #343A40; margin-bottom: 20px; }

  .amenidades-grid { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }
  .amenidad-tag {
    background: #1B2A4A; color: white;
    font-size: 10px; padding: 4px 10px; border-radius: 99px;
  }

  .extras-grid { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }
  .extras-grid img { width: 130px; height: 90px; object-fit: cover; border-radius: 6px; }

  .agente-box {
    background: #1B2A4A; color: white;
    border-radius: 8px; padding: 16px 20px;
    display: flex; justify-content: space-between; align-items: center;
  }
  .agente-nombre { font-size: 15px; font-weight: 700; }
  .agente-info { font-size: 11px; color: #C9A84C; margin-top: 4px; }

  .footer-pdf { text-align: center; padding: 12px; font-size: 10px; color: #6C757D; }
</style>
</head>
<body>

<div class="header">
  <div>
    <div class="header-brand">INMERSIVA</div>
    <div class="header-sub">Grupo Inmobiliario</div>
  </div>
  <div class="header-badge">{{ listing.tipo }} en {{ listing.operacion }}</div>
</div>

{% if portada_b64 %}
<img class="portada" src="data:image/jpeg;base64,{{ portada_b64 }}">
{% else %}
<div class="no-photo">Sin foto de portada</div>
{% endif %}

<div class="content">

  <div class="precio">{{ listing.precio_str }}</div>
  <div class="ubicacion">📍 {{ listing.direccion }}, {{ listing.ciudad }}, {{ listing.estado }}</div>

  <div class="stats-row">
    {% if listing.recamaras %}<div class="stat"><div class="stat-val">{{ listing.recamaras }}</div><div class="stat-label">🛏 Rec.</div></div>{% endif %}
    {% if listing.banos %}<div class="stat"><div class="stat-val">{{ listing.banos }}</div><div class="stat-label">🚿 Baños</div></div>{% endif %}
    {% if listing.m2_construidos %}<div class="stat"><div class="stat-val">{{ listing.m2_construidos }}</div><div class="stat-label">📐 M² Const.</div></div>{% endif %}
    {% if listing.m2_terreno %}<div class="stat"><div class="stat-val">{{ listing.m2_terreno }}</div><div class="stat-label">🌳 M² Ter.</div></div>{% endif %}
    {% if listing.estacionamientos %}<div class="stat"><div class="stat-val">{{ listing.estacionamientos }}</div><div class="stat-label">🚗 Est.</div></div>{% endif %}
  </div>

  <div class="section-title">Descripción</div>
  <div class="descripcion">{{ listing.descripcion_generada }}</div>

  {% if listing.amenidades %}
  <div class="section-title">Amenidades</div>
  <div class="amenidades-grid">
    {% for a in listing.amenidades %}<span class="amenidad-tag">{{ a }}</span>{% endfor %}
  </div>
  {% endif %}

  {% if extras_b64_list %}
  <div class="section-title">Galería de Fotos</div>
  <div class="extras-grid">
    {% for img in extras_b64_list %}
    <img src="data:image/jpeg;base64,{{ img }}">
    {% endfor %}
  </div>
  {% endif %}

  <div class="agente-box">
    <div>
      <div class="agente-nombre">{{ listing.agente_nombre }}</div>
      <div class="agente-info">📱 {{ listing.agente_telefono }} &nbsp;·&nbsp; ✉️ {{ listing.agente_email }}</div>
    </div>
    <div style="color:#C9A84C;font-size:11px;text-align:right">Inmersiva<br>Grupo Inmobiliario</div>
  </div>

</div>

<div class="footer-pdf">inmobiliariainmersiva.com · Documento generado con ListaPro</div>

</body>
</html>
```

- [ ] **Step 4: Implement PDF service**

```python
# services/pdf_service.py
import base64
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
from models.listing import Listing

_jinja = Environment(loader=FileSystemLoader("templates"))

def _img_to_b64(path: str) -> str:
    p = Path("uploads") / path
    if not p.exists():
        return ""
    return base64.b64encode(p.read_bytes()).decode()

def generar_pdf(listing: Listing, output_path: str):
    portada_b64 = _img_to_b64(listing.foto_portada) if listing.foto_portada else ""
    extras_b64_list = [_img_to_b64(f) for f in listing.fotos_extras if _img_to_b64(f)]

    template = _jinja.get_template("pdf_template.html")
    html_str = template.render(
        listing=listing,
        portada_b64=portada_b64,
        extras_b64_list=extras_b64_list,
    )

    HTML(string=html_str, base_url=".").write_pdf(output_path)
```

- [ ] **Step 5: Add PDF route to main.py** (add after the existing imports and routes)

```python
# Add to main.py
from services.pdf_service import generar_pdf

@app.get("/pdf/{listing_id}")
async def descargar_pdf(listing_id: str):
    listing = load_listing(listing_id)
    pdf_path = GENERATED / "pdfs" / f"{listing_id}.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    generar_pdf(listing, str(pdf_path))
    filename = f"inmersiva_{listing.tipo.lower()}_{listing.ciudad.lower()}.pdf"
    return FileResponse(str(pdf_path), media_type="application/pdf", filename=filename)
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/test_pdf_service.py -v
```

Expected: 1 PASSED.

- [ ] **Step 7: Test in browser** — click "Descargar PDF" in the results page and verify the PDF opens correctly.

- [ ] **Step 8: Commit**

```bash
git add services/pdf_service.py templates/pdf_template.html tests/test_pdf_service.py main.py
git commit -m "feat: phase 2 — PDF generation with WeasyPrint and Inmersiva branding"
```

---

## Task 8: Image Service — Instagram 1080×1080 (Phase 3)

**Files:**
- Create: `services/image_service.py`
- Create: `tests/test_image_service.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_image_service.py
from PIL import Image
from pathlib import Path
from models.listing import Listing
from services.image_service import generar_imagen_instagram

def _make_listing():
    return Listing(
        tipo="Departamento", operacion="Renta",
        direccion="Polanco", ciudad="CDMX", estado="CDMX",
        precio=35000, recamaras=2, banos=2, m2_construidos=90,
        descripcion_agente="Lujoso depa",
        agente_nombre="Ana L", agente_telefono="5509876543", agente_email="ana@inmersiva.com",
        foto_portada="",
    )

def test_imagen_dimensions(tmp_path):
    listing = _make_listing()
    out = tmp_path / "test.jpg"
    generar_imagen_instagram(listing, None, str(out))
    img = Image.open(out)
    assert img.size == (1080, 1080)

def test_imagen_creates_file(tmp_path):
    listing = _make_listing()
    out = tmp_path / "test2.jpg"
    generar_imagen_instagram(listing, None, str(out))
    assert out.stat().st_size > 10000
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_image_service.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement image service**

```python
# services/image_service.py
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import os

NAVY = (27, 42, 74)
GOLD = (201, 168, 76)
WHITE = (255, 255, 255)
SIZE = 1080

def _load_font(size: int):
    font_paths = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    ]
    for p in font_paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def _gradient_overlay(img: Image.Image) -> Image.Image:
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for i in range(SIZE):
        alpha = int(200 * (i / SIZE) ** 1.2)
        draw.line([(0, i), (SIZE, i)], fill=(0, 0, 0, alpha))
    img = img.convert("RGBA")
    img.paste(overlay, (0, 0), overlay)
    return img

def generar_imagen_instagram(listing, portada_path: str | None, output_path: str):
    if portada_path and Path(portada_path).exists():
        base = Image.open(portada_path).convert("RGB")
        base = base.resize((SIZE, SIZE), Image.LANCZOS)
    else:
        base = Image.new("RGB", (SIZE, SIZE), NAVY)

    base = _gradient_overlay(base).convert("RGB")
    draw = ImageDraw.Draw(base)

    # Badge "En Venta / En Renta"
    badge_color = GOLD if listing.operacion == "Venta" else (60, 120, 200)
    badge_text = f"  EN {listing.operacion.upper()}  "
    font_badge = _load_font(32)
    bbox = draw.textbbox((0, 0), badge_text, font=font_badge)
    bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.rectangle([48, 60, 48 + bw + 16, 60 + bh + 12], fill=badge_color)
    draw.text((56, 66), badge_text, font=font_badge, fill=NAVY if listing.operacion == "Venta" else WHITE)

    # Precio
    font_precio = _load_font(72)
    draw.text((60, SIZE - 320), listing.precio_str, font=font_precio, fill=GOLD)

    # Ubicación
    font_ubicacion = _load_font(38)
    ubicacion = f"📍 {listing.ciudad}, {listing.estado}"
    draw.text((60, SIZE - 230), ubicacion, font=font_ubicacion, fill=WHITE)

    # Stats row
    font_stats = _load_font(36)
    stats = []
    if listing.recamaras:     stats.append(f"🛏 {listing.recamaras} rec")
    if listing.banos:         stats.append(f"🚿 {listing.banos} baños")
    if listing.m2_construidos: stats.append(f"📐 {listing.m2_construidos}m²")
    stats_text = "   ".join(stats)
    draw.text((60, SIZE - 160), stats_text, font=font_stats, fill=WHITE)

    # Inmersiva watermark (bottom right)
    font_wm = _load_font(26)
    wm = "INMERSIVA Grupo Inmobiliario"
    bbox_wm = draw.textbbox((0, 0), wm, font=font_wm)
    wm_w = bbox_wm[2] - bbox_wm[0]
    draw.text((SIZE - wm_w - 50, SIZE - 60), wm, font=font_wm, fill=GOLD)

    base.save(output_path, "JPEG", quality=95)
```

- [ ] **Step 4: Add image route to main.py**

```python
# Add to main.py
from services.image_service import generar_imagen_instagram

@app.get("/imagen/{listing_id}")
async def descargar_imagen(listing_id: str):
    listing = load_listing(listing_id)
    img_path = GENERATED / "images" / f"{listing_id}.jpg"
    img_path.parent.mkdir(parents=True, exist_ok=True)
    portada_path = (UPLOADS / listing.foto_portada) if listing.foto_portada else None
    generar_imagen_instagram(listing, str(portada_path) if portada_path else None, str(img_path))
    filename = f"inmersiva_instagram_{listing.tipo.lower()}.jpg"
    return FileResponse(str(img_path), media_type="image/jpeg", filename=filename)
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_image_service.py -v
```

Expected: 2 PASSED.

- [ ] **Step 6: Test in browser** — click "Descargar Imagen Instagram" and verify the 1080×1080 image looks correct.

- [ ] **Step 7: Commit**

```bash
git add services/image_service.py tests/test_image_service.py main.py
git commit -m "feat: phase 3 — Instagram image 1080x1080 with Pillow"
```

---

## Task 9: Social Publishing Service (Phase 4)

**Files:**
- Create: `services/social_service.py`
- Create: `tests/test_social_service.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_social_service.py
from unittest.mock import patch, MagicMock
from services.social_service import publicar_instagram

def test_publicar_instagram_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"success": True}
    with patch("services.social_service.httpx.post", return_value=mock_resp):
        result = publicar_instagram("path/to/img.jpg", "Copy de test #inmobiliaria")
    assert result["ok"] is True

def test_publicar_instagram_api_error():
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"
    with patch("services.social_service.httpx.post", return_value=mock_resp):
        result = publicar_instagram("path/to/img.jpg", "Copy")
    assert result["ok"] is False
    assert "error" in result
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_social_service.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement social service**

```python
# services/social_service.py
import os
import httpx

UPLOAD_POST_URL = "https://api.upload-post.com/api/upload"

def publicar_instagram(image_path: str, caption: str) -> dict:
    api_key = os.getenv("UPLOADPOST_API_KEY")
    user = os.getenv("UPLOADPOST_USER")

    if not api_key or not user:
        return {"ok": False, "error": "UPLOADPOST_API_KEY o UPLOADPOST_USER no configurados en .env"}

    try:
        with open(image_path, "rb") as f:
            response = httpx.post(
                UPLOAD_POST_URL,
                headers={"Authorization": f"Apikey {api_key}"},
                data={"user": user, "platform[]": "instagram", "title": caption},
                files={"image": (os.path.basename(image_path), f, "image/jpeg")},
                timeout=30.0,
            )

        if response.status_code == 200:
            return {"ok": True, "data": response.json()}
        else:
            return {"ok": False, "error": f"API respondió {response.status_code}: {response.text}"}

    except Exception as e:
        return {"ok": False, "error": str(e)}
```

- [ ] **Step 4: Add publish route to main.py**

```python
# Add to main.py
from services.social_service import publicar_instagram

@app.post("/publicar/{listing_id}")
async def publicar(listing_id: str):
    listing = load_listing(listing_id)
    img_path = GENERATED / "images" / f"{listing_id}.jpg"

    if not img_path.exists():
        portada_path = (UPLOADS / listing.foto_portada) if listing.foto_portada else None
        from services.image_service import generar_imagen_instagram
        img_path.parent.mkdir(parents=True, exist_ok=True)
        generar_imagen_instagram(listing, str(portada_path) if portada_path else None, str(img_path))

    result = publicar_instagram(str(img_path), listing.copy_instagram)
    return JSONResponse(content=result)
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_social_service.py -v
```

Expected: 2 PASSED.

- [ ] **Step 6: Test in browser** — click "Publicar en Instagram" and verify the success/error message appears correctly.

- [ ] **Step 7: Commit**

```bash
git add services/social_service.py tests/test_social_service.py main.py
git commit -m "feat: phase 4 — Instagram publishing via Upload Post API"
```

---

## Task 10: Remotion Video Project Setup (Phase 5)

**Files:**
- Create: `video/package.json`
- Create: `video/src/index.ts`
- Create: `video/src/Root.tsx`
- Create: `video/src/PropertyReel.tsx`

- [ ] **Step 1: Initialize Remotion project**

```bash
cd video
npm init -y
npm install remotion @remotion/cli react react-dom
npm install --save-dev typescript @types/react @types/react-dom
```

- [ ] **Step 2: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "lib": ["ES2020", "DOM"],
    "jsx": "react",
    "strict": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "noEmit": true
  },
  "include": ["src"]
}
```

- [ ] **Step 3: Create video/src/index.ts**

```typescript
// video/src/index.ts
import { registerRoot } from "remotion";
import { Root } from "./Root";

registerRoot(Root);
```

- [ ] **Step 4: Create video/src/Root.tsx**

```tsx
// video/src/Root.tsx
import { Composition } from "remotion";
import { PropertyReel } from "./PropertyReel";

export type ReelProps = {
  photos: string[];         // base64 encoded JPEGs
  precio: string;
  ubicacion: string;
  tipo: string;
  operacion: string;
  recamaras?: number;
  banos?: number;
  m2?: number;
  agenteNombre: string;
  agenteTelefono: string;
  agenteEmail: string;
};

const DURATION_PER_PHOTO = 90; // 3 seconds at 30fps

export const Root: React.FC = () => {
  const dummyProps: ReelProps = {
    photos: [],
    precio: "$5,000,000 MXN",
    ubicacion: "CDMX, México",
    tipo: "Casa",
    operacion: "Venta",
    recamaras: 3,
    banos: 2,
    m2: 180,
    agenteNombre: "Agente Inmersiva",
    agenteTelefono: "5512345678",
    agenteEmail: "agente@inmersiva.com",
  };

  const numPhotos = Math.max(dummyProps.photos.length, 3);
  const totalFrames = numPhotos * DURATION_PER_PHOTO + 90; // +3s contact screen

  return (
    <Composition
      id="PropertyReel"
      component={PropertyReel}
      durationInFrames={totalFrames}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={dummyProps}
    />
  );
};
```

- [ ] **Step 5: Create video/src/PropertyReel.tsx**

```tsx
// video/src/PropertyReel.tsx
import {
  AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig,
  interpolate, Easing, spring
} from "remotion";
import { ReelProps } from "./Root";

const NAVY = "#1B2A4A";
const GOLD = "#C9A84C";
const FRAMES_PER_PHOTO = 90;
const CONTACT_FRAMES = 90;

const KenBurnsPhoto: React.FC<{ src: string; startFrame: number }> = ({ src, startFrame }) => {
  const frame = useCurrentFrame();
  const local = frame - startFrame;
  const scale = interpolate(local, [0, FRAMES_PER_PHOTO], [1, 1.08], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.ease),
  });
  const opacity = interpolate(local, [0, 15, FRAMES_PER_PHOTO - 15, FRAMES_PER_PHOTO], [0, 1, 1, 0]);

  return (
    <AbsoluteFill style={{ opacity }}>
      <div style={{
        width: "100%", height: "100%",
        backgroundImage: `url(data:image/jpeg;base64,${src})`,
        backgroundSize: "cover", backgroundPosition: "center",
        transform: `scale(${scale})`,
      }} />
      <AbsoluteFill style={{
        background: "linear-gradient(to bottom, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0.7) 100%)"
      }} />
    </AbsoluteFill>
  );
};

const PhotoSlide: React.FC<{
  photo: string; index: number; props: ReelProps;
}> = ({ photo, index, props }) => {
  const frame = useCurrentFrame();
  const local = frame;
  const textOpacity = interpolate(local, [20, 40], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const textY = interpolate(local, [20, 40], [30, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill>
      <KenBurnsPhoto src={photo} startFrame={0} />
      {index === 0 && (
        <AbsoluteFill style={{ display: "flex", flexDirection: "column", justifyContent: "flex-end", padding: "80px 60px" }}>
          <div style={{ opacity: textOpacity, transform: `translateY(${textY}px)` }}>
            <div style={{
              background: GOLD, color: NAVY,
              display: "inline-block", padding: "8px 20px",
              borderRadius: 4, fontSize: 32, fontWeight: 700,
              letterSpacing: 2, marginBottom: 20,
            }}>
              EN {props.operacion.toUpperCase()}
            </div>
            <div style={{ color: GOLD, fontSize: 72, fontWeight: 700, lineHeight: 1 }}>
              {props.precio}
            </div>
            <div style={{ color: "white", fontSize: 38, marginTop: 12 }}>
              📍 {props.ubicacion}
            </div>
            <div style={{ display: "flex", gap: 30, marginTop: 20 }}>
              {props.recamaras && <span style={{ color: "white", fontSize: 34 }}>🛏 {props.recamaras} rec.</span>}
              {props.banos && <span style={{ color: "white", fontSize: 34 }}>🚿 {props.banos} baños</span>}
              {props.m2 && <span style={{ color: "white", fontSize: 34 }}>📐 {props.m2}m²</span>}
            </div>
          </div>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};

const ContactScreen: React.FC<{ p: ReelProps }> = ({ p }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 20], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: NAVY, opacity, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: 80 }}>
      <div style={{ color: GOLD, fontSize: 24, letterSpacing: 4, textTransform: "uppercase", marginBottom: 40 }}>
        INMERSIVA GRUPO INMOBILIARIO
      </div>
      <div style={{ color: "white", fontSize: 52, fontWeight: 700, textAlign: "center", marginBottom: 20 }}>
        {p.agenteNombre}
      </div>
      <div style={{ color: GOLD, fontSize: 38, marginBottom: 12 }}>📱 {p.agenteTelefono}</div>
      <div style={{ color: "white", fontSize: 32, opacity: 0.8 }}>✉️ {p.agenteEmail}</div>
      <div style={{ marginTop: 60, color: GOLD, fontSize: 26 }}>inmobiliariainmersiva.com</div>
    </AbsoluteFill>
  );
};

export const PropertyReel: React.FC<ReelProps> = (props) => {
  const photos = props.photos.length > 0 ? props.photos : [""];
  return (
    <AbsoluteFill style={{ background: "black", fontFamily: "'Helvetica Neue', Arial, sans-serif" }}>
      {photos.map((photo, i) => (
        <Sequence key={i} from={i * FRAMES_PER_PHOTO} durationInFrames={FRAMES_PER_PHOTO}>
          <PhotoSlide photo={photo} index={i} props={props} />
        </Sequence>
      ))}
      <Sequence from={photos.length * FRAMES_PER_PHOTO} durationInFrames={CONTACT_FRAMES}>
        <ContactScreen p={props} />
      </Sequence>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 6: Verify Remotion renders**

```bash
cd video
npx remotion preview src/index.ts
```

Expected: browser opens with Remotion Studio showing the composition.

- [ ] **Step 7: Commit**

```bash
cd ..
git add video/
git commit -m "feat: phase 5a — Remotion video project with PropertyReel component"
```

---

## Task 11: Video Service & Routes (Phase 5 cont.)

**Files:**
- Create: `services/video_service.py`
- Modify: `main.py`

- [ ] **Step 1: Implement video service**

```python
# services/video_service.py
import os
import base64
import json
import subprocess
import threading
from pathlib import Path
from models.listing import Listing

_video_status: dict[str, str] = {}

def _img_to_b64(path: Path) -> str:
    if path.exists():
        return base64.b64encode(path.read_bytes()).decode()
    return ""

def _render(listing: Listing, output_path: str, listing_id: str):
    _video_status[listing_id] = "rendering"
    try:
        uploads = Path("uploads")
        photos_b64 = []
        if listing.foto_portada:
            b64 = _img_to_b64(uploads / listing.foto_portada)
            if b64:
                photos_b64.append(b64)
        for extra in listing.fotos_extras:
            b64 = _img_to_b64(uploads / extra)
            if b64:
                photos_b64.append(b64)

        props = {
            "photos": photos_b64,
            "precio": listing.precio_str,
            "ubicacion": f"{listing.ciudad}, {listing.estado}",
            "tipo": listing.tipo,
            "operacion": listing.operacion,
            "recamaras": listing.recamaras,
            "banos": listing.banos,
            "m2": listing.m2_construidos,
            "agenteNombre": listing.agente_nombre,
            "agenteTelefono": listing.agente_telefono,
            "agenteEmail": listing.agente_email,
        }

        result = subprocess.run(
            [
                "npx", "remotion", "render",
                "src/index.ts",
                "PropertyReel",
                output_path,
                "--props", json.dumps(props),
            ],
            cwd="video",
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode == 0:
            _video_status[listing_id] = "done"
        else:
            _video_status[listing_id] = "error"
    except Exception:
        _video_status[listing_id] = "error"

def iniciar_render(listing: Listing, output_path: str) -> None:
    t = threading.Thread(target=_render, args=(listing, output_path, listing.id), daemon=True)
    t.start()

def get_status(listing_id: str) -> str:
    return _video_status.get(listing_id, "pending")
```

- [ ] **Step 2: Add video routes to main.py**

```python
# Add to main.py
from services.video_service import iniciar_render, get_status

@app.post("/video/{listing_id}")
async def generar_video(listing_id: str):
    listing = load_listing(listing_id)
    video_path = GENERATED / "videos" / f"{listing_id}.mp4"
    video_path.parent.mkdir(parents=True, exist_ok=True)
    iniciar_render(listing, str(video_path))
    return JSONResponse(content={"ok": True, "status": "rendering"})

@app.get("/video/status/{listing_id}")
async def video_status(listing_id: str):
    status = get_status(listing_id)
    return JSONResponse(content={"status": status})
```

- [ ] **Step 3: Test video rendering end-to-end**

Start the server and click "Generar Video Reel" on a listing result page. The progress bar should animate, and after ~30-60 seconds the download button should appear.

```bash
uvicorn main:app --reload --port 8000
```

- [ ] **Step 4: Commit**

```bash
git add services/video_service.py main.py
git commit -m "feat: phase 5b — video render service with Remotion subprocess and progress polling"
```

---

## Task 12: Full Test Suite & Run All Tests

**Files:**
- Create: `tests/__init__.py`

- [ ] **Step 1: Create tests/__init__.py**

```bash
touch tests/__init__.py
```

- [ ] **Step 2: Run full test suite**

```bash
pytest tests/ -v
```

Expected output:
```
tests/test_listing.py::test_listing_defaults PASSED
tests/test_listing.py::test_listing_precio_formateado PASSED
tests/test_ai_service.py::test_generar_contenido_returns_two_strings PASSED
tests/test_ai_service.py::test_generar_contenido_strips_markers PASSED
tests/test_pdf_service.py::test_generar_pdf_creates_file PASSED
tests/test_image_service.py::test_imagen_dimensions PASSED
tests/test_image_service.py::test_imagen_creates_file PASSED
tests/test_social_service.py::test_publicar_instagram_success PASSED
tests/test_social_service.py::test_publicar_instagram_api_error PASSED

9 passed
```

- [ ] **Step 3: Final commit**

```bash
git add tests/__init__.py
git commit -m "test: full test suite passing — all 9 tests green"
```
