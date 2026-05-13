# ListaPro para Inmersiva — Diseño del Sistema

**Fecha:** 2026-05-12  
**Empresa:** Inmersiva Grupo Inmobiliario  
**Dominio:** inmobiliariainmersiva.com | Servidor: 145.223.95.184  
**Propósito:** Herramienta interna para agentes de Inmersiva que genera contenido profesional de propiedades automáticamente con IA.

---

## Resumen

Web app que permite a un agente llenar un formulario con datos de una propiedad y obtener automáticamente: descripción profesional, copy de Instagram, PDF descargable, imagen cuadrada para redes, video reel y publicación directa a Instagram.

---

## Stack Técnico

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.11 + FastAPI |
| Frontend | HTML + CSS + Vanilla JS (sin framework) |
| IA | OpenAI GPT-4o (descripciones + copy) |
| PDF | WeasyPrint |
| Imagen | Pillow (1080×1080) |
| Video | Remotion (React, carpeta `video/`) |
| Social | Upload Post API (`api.upload-post.com`) |
| Config | `.env` con python-dotenv |

**Colores de marca Inmersiva:**
- Navy: `#1B2A4A`
- Dorado: `#C9A84C`
- Fondo: `#FFFFFF`

---

## Fases de Implementación

### Fase 1 — Formulario + Generación IA
**Entrada (formulario web):**
- Tipo de propiedad: Casa, Departamento, Terreno, Penthouse
- Operación: Venta / Renta
- Dirección, Ciudad, Estado
- Precio (MXN)
- Recámaras, baños, m² construidos, m² terreno, estacionamientos
- Amenidades (checkboxes): alberca, jardín, seguridad 24h, gimnasio, etc.
- Descripción breve del agente (2-3 líneas)
- Fotos: 1 portada + extras (upload)
- Datos del agente: nombre, teléfono, email

**Salida:**
- Descripción profesional generada por GPT-4o
- Copy optimizado para Instagram con hashtags del sector inmobiliario MX

**Endpoints FastAPI:**
- `GET /` → formulario HTML
- `POST /generar` → recibe form-data, llama OpenAI, retorna página de resultados
- `GET /static/*` → archivos estáticos (CSS, JS, imágenes subidas)

### Fase 2 — PDF Descargable
- Generado con WeasyPrint desde HTML template
- Contenido: foto portada (grande), fotos extras (grid), descripción IA, datos clave visuales (precio, recámaras, baños, m²), amenidades, contacto del agente
- Encabezado con colores Inmersiva (navy + dorado)
- Botón "Descargar PDF" en página de resultados
- Endpoint: `GET /pdf/{listing_id}`

### Fase 3 — Imagen Instagram (1080×1080)
- Generada con Pillow
- Foto de portada como fondo
- Gradiente oscuro overlay para legibilidad
- Badge "En Venta" / "En Renta"
- Precio destacado
- Ubicación
- Iconos con datos principales (recámaras 🛏, baños 🚿, m²)
- Botón "Descargar Imagen" en resultados
- Endpoint: `GET /imagen/{listing_id}`

### Fase 4 — Publicar en Instagram
- Botón "Publicar en Instagram" en página de resultados
- Llama Upload Post API (`POST https://api.upload-post.com/api/upload`)
- Parámetros: `user`, `platform[]=instagram`, imagen generada, `title` = copy Instagram
- Header: `Authorization: Apikey {UPLOADPOST_API_KEY}`
- Variable `UPLOADPOST_API_KEY` en `.env`
- Muestra mensaje de éxito o error
- Endpoint: `POST /publicar/{listing_id}`

### Fase 5 — Video Reel (1080×1920)
- Generado con Remotion en carpeta `video/`
- Especificaciones:
  - Fotos con transiciones fade + efecto Ken Burns (zoom lento)
  - Cada foto: 3-4 segundos
  - Texto animado: precio, ubicación, datos principales
  - Pantalla final: datos de contacto del agente
  - Duración: 20-30 segundos
  - Música de fondo (mp3 configurable)
- Backend pasa datos al componente React, renderiza con Remotion CLI, guarda `.mp4`
- Botón "Generar Video" con indicador de progreso (polling)
- Endpoints: `POST /video/{listing_id}` (inicia render), `GET /video/status/{listing_id}` (estado)

---

## Estructura de Archivos

```
Inmersiva-Inmobiliaria/
├── main.py                    # FastAPI app
├── .env                       # OPENAI_API_KEY, UPLOADPOST_API_KEY
├── requirements.txt
├── templates/
│   ├── form.html              # Formulario
│   ├── results.html           # Página de resultados
│   └── pdf_template.html      # Template para WeasyPrint
├── static/
│   ├── css/style.css          # Estilos Inmersiva (navy + dorado)
│   ├── js/main.js
│   └── logo.png               # Logo Inmersiva
├── uploads/                   # Fotos subidas por agentes
├── generated/                 # PDFs, imágenes y videos generados
│   ├── pdfs/
│   ├── images/
│   └── videos/
├── video/                     # Proyecto Remotion
│   ├── package.json
│   └── src/
│       └── PropertyReel.tsx
└── docs/
    └── superpowers/specs/
        └── 2026-05-12-listapro-inmersiva-design.md
```

---

## Variables de Entorno (.env)

```
OPENAI_API_KEY=sk-...
UPLOADPOST_API_KEY=...
```

---

## Flujo de Datos

```
Agente llena formulario
  → POST /generar (FastAPI)
    → Guarda fotos en uploads/
    → Crea listing_id (UUID)
    → Llama OpenAI → descripción + copy Instagram
    → Renderiza results.html con todos los datos
      → Botón PDF → GET /pdf/{id} (WeasyPrint)
      → Botón Imagen → GET /imagen/{id} (Pillow)
      → Botón Publicar → POST /publicar/{id} (Upload Post API)
      → Botón Video → POST /video/{id} (Remotion) + polling
```

---

## Criterios de Éxito

- Fase 1: El agente llena el formulario y ve descripción + copy en < 10 segundos
- Fase 2: PDF descargable con diseño limpio y logo Inmersiva
- Fase 3: Imagen 1080×1080 lista para subir a Instagram
- Fase 4: Publicación exitosa a Instagram en 1 clic
- Fase 5: Video reel `.mp4` generado y descargable
