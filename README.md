# 🏠 INMERSIVA — Sistema de Publicación Inmobiliaria

**INMERSIVA GRUPO INMOBILIARIO**  
Sistema web privado para gestión y publicación automática de propiedades inmobiliarias.

---

## ¿Qué hace este sistema?

Permite a los agentes de INMERSIVA:

1. **Iniciar sesión** desde cualquier PC
2. **Crear una propiedad** llenando un formulario
3. **Subir fotografías** de la propiedad
4. **Generar automáticamente** con IA:
   - Descripción profesional inmobiliaria
   - Copy optimizado para Instagram/Facebook
5. **Generar imagen** 1080x1080 lista para redes sociales
6. **Generar PDF** ficha inmobiliaria descargable
7. **Publicar** directamente en Instagram y Facebook corporativo

---

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.12 + FastAPI |
| Frontend | Jinja2 + TailwindCSS |
| Base de datos | PostgreSQL |
| IA | OpenAI API |
| Imágenes | Pillow |
| PDFs | ReportLab |
| Publicación redes | Upload Post API |
| Infraestructura | Docker + EasyPanel + VPS |

---

## Instalación local

### 1. Clonar el repositorio

```bash
git clone https://github.com/inmersivagrupoinmobiliario-dotcom/Inmersiva-Inmobiliaria.git
cd Inmersiva-Inmobiliaria
```

### 2. Crear entorno virtual

```bash
python -m venv venv

# Mac/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
cp .env.example .env
# Edita .env con tus valores reales
```

### 5. Iniciar el servidor

```bash
uvicorn app.main:app --reload
```

Abrir en el navegador: [http://localhost:8000](http://localhost:8000)

---

## Despliegue en EasyPanel

### Servicios necesarios en EasyPanel:

**1. inmersiva-python** (App Service)
- Source: GitHub → `Inmersiva-Inmobiliaria`
- Branch: `main`
- Build: Dockerfile
- Port: `8000`

**2. inmersiva-db** (PostgreSQL)
- Crear base de datos: `inmersiva_db`

### Variables de entorno en EasyPanel:

```
DATABASE_URL=postgresql://usuario:password@inmersiva-db:5432/inmersiva_db
SECRET_KEY=tu-clave-secreta
OPENAI_API_KEY=sk-...
UPLOADPOST_API_KEY=tu-key
UPLOADPOST_USER=tu-usuario
BASE_URL=https://panel.inmobiliariainmersiva.com
```

---

## Estructura del proyecto

```
Inmersiva-Inmobiliaria/
│
├── app/
│   ├── main.py              # Entrada principal de la app
│   ├── config.py            # Configuración y variables de entorno
│   ├── database.py          # Conexión a PostgreSQL
│   │
│   ├── models/              # Estructura de tablas en la DB
│   ├── schemas/             # Validación de datos (Pydantic)
│   ├── routers/             # Rutas de la API
│   ├── services/            # Lógica de negocio (IA, PDF, redes)
│   │
│   ├── templates/           # HTML con Jinja2
│   ├── static/              # CSS, JS, imágenes del sistema
│   ├── uploads/             # Fotos subidas por agentes
│   └── generated/           # PDFs e imágenes generadas
│
├── requirements.txt
├── Dockerfile
├── .env.example
└── README.md
```

---

## Roadmap

- [x] Fase 1 — Estructura base + Auth + Propiedades
- [ ] Fase 2 — IA + PDF + Imagen social
- [ ] Fase 3 — Publicación Instagram/Facebook
- [ ] Fase 4 — CRM + Leads
- [ ] Fase 5 — Analytics + Dashboard gerencial
- [ ] Fase 6 — Video reels automáticos

---

**INMERSIVA GRUPO INMOBILIARIO** © 2025
