"""
INMERSIVA - Sistema de Publicación Inmobiliaria
Punto de entrada principal de la aplicación FastAPI
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import create_tables

# Configurar logging profesional
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("inmersiva")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Ciclo de vida de la aplicación.
    Se ejecuta al iniciar y al cerrar el servidor.
    """
    logger.info("🏠 Iniciando INMERSIVA...")
    create_tables()
    logger.info("✅ Base de datos lista.")
    yield
    logger.info("🔒 Cerrando INMERSIVA.")


# Instancia principal de la app
app = FastAPI(
    title="INMERSIVA",
    description="Sistema de Publicación Inmobiliaria — INMERSIVA GRUPO INMOBILIARIO",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url=None,
)

# CORS — permite que el frontend se comunique con el backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Archivos estáticos (CSS, JS, imágenes del sistema)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/uploads", StaticFiles(directory="app/uploads"), name="uploads")
app.mount("/generated", StaticFiles(directory="app/generated"), name="generated")

# Templates Jinja2
templates = Jinja2Templates(directory="app/templates")


# ─── Rutas principales ────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Endpoint de salud — usado por EasyPanel para verificar que la app corre."""
    return {
        "status": "ok",
        "project": "INMERSIVA",
        "version": "1.0.0",
    }


@app.get("/")
async def root():
    """Ruta raíz — redirige al panel o al login."""
    return {
        "message": "INMERSIVA API funcionando correctamente",
        "docs": "/api/docs",
        "panel": "/panel",
    }


# ─── Registro de routers (se activarán en fases siguientes) ──────────────────
# from app.routers import auth, dashboard, properties, publications, uploads
# app.include_router(auth.router, prefix="/auth", tags=["Auth"])
# app.include_router(dashboard.router, prefix="/panel", tags=["Dashboard"])
# app.include_router(properties.router, prefix="/properties", tags=["Properties"])
# app.include_router(publications.router, prefix="/publications", tags=["Publications"])
# app.include_router(uploads.router, prefix="/uploads", tags=["Uploads"])
