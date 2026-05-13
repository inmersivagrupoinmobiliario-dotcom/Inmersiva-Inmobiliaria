"""
INMERSIVA — Configuración de base de datos
Maneja la conexión a PostgreSQL usando SQLAlchemy.
SQLAlchemy actúa como intérprete entre Python y la base de datos.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
import logging

from app.config import settings

logger = logging.getLogger("inmersiva.database")

# Motor de conexión a PostgreSQL
# pool_pre_ping=True verifica que la conexión esté viva antes de usarla
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG,  # Muestra queries SQL solo en modo debug
)

# Fábrica de sesiones — cada request obtiene su propia sesión
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Clase base para todos los modelos de la base de datos
Base = declarative_base()


def create_tables() -> None:
    """
    Crea todas las tablas en la base de datos si no existen.
    Se ejecuta automáticamente al iniciar la aplicación.
    """
    try:
        # Verificar conexión antes de crear tablas
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("📦 Conexión a PostgreSQL establecida.")

        # Importar modelos para que SQLAlchemy los registre
        from app.models import user, property, property_image, publication  # noqa

        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tablas creadas/verificadas correctamente.")

    except OperationalError as e:
        logger.error(f"❌ Error conectando a la base de datos: {e}")
        logger.error("Verifica que DATABASE_URL en tu .env sea correcto.")
        raise


def get_db():
    """
    Generador de sesión de base de datos.
    FastAPI lo usa como dependencia inyectable en cada endpoint.

    Uso en un router:
        @router.get("/algo")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()  # Siempre cierra la sesión, incluso si hay un error
