"""
INMERSIVA — Modelo de Propiedad
Define la estructura de la tabla 'properties' en la base de datos.
"""

from sqlalchemy import (
    Column, Integer, String, Float, Text,
    Boolean, DateTime, Enum, ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class PropertyType(str, enum.Enum):
    CASA = "casa"
    DEPARTAMENTO = "departamento"
    TERRENO = "terreno"
    PENTHOUSE = "penthouse"


class OperationType(str, enum.Enum):
    VENTA = "venta"
    RENTA = "renta"


class PropertyStatus(str, enum.Enum):
    DISPONIBLE = "disponible"
    RESERVADO = "reservado"
    VENDIDO = "vendido"
    ALQUILADO = "alquilado"
    OCULTO = "oculto"


class Property(Base):
    """
    Tabla principal de propiedades inmobiliarias.
    Cada propiedad pertenece a un agente (usuario).
    """
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)

    # ─── Datos generales ──────────────────────────────────────────────────────
    title = Column(String(200), nullable=True)  # Generado por IA automáticamente
    property_type = Column(Enum(PropertyType), nullable=False)
    operation_type = Column(Enum(OperationType), nullable=False)
    status = Column(Enum(PropertyStatus), default=PropertyStatus.DISPONIBLE)

    # ─── Ubicación ────────────────────────────────────────────────────────────
    address = Column(String(300), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)

    # ─── Precio ───────────────────────────────────────────────────────────────
    price = Column(Float, nullable=False)
    currency = Column(String(10), default="PEN")  # Soles peruanos por defecto

    # ─── Características ──────────────────────────────────────────────────────
    bedrooms = Column(Integer, nullable=True)
    bathrooms = Column(Integer, nullable=True)
    parking_spaces = Column(Integer, nullable=True)
    construction_m2 = Column(Float, nullable=True)
    land_m2 = Column(Float, nullable=True)

    # ─── Amenidades (cada una es un boolean) ─────────────────────────────────
    has_pool = Column(Boolean, default=False)
    has_garden = Column(Boolean, default=False)
    has_security = Column(Boolean, default=False)
    has_gym = Column(Boolean, default=False)
    has_roof_garden = Column(Boolean, default=False)
    has_terrace = Column(Boolean, default=False)
    has_patio = Column(Boolean, default=False)
    has_playground = Column(Boolean, default=False)

    # ─── Contenido ────────────────────────────────────────────────────────────
    agent_description = Column(Text, nullable=True)   # Input manual del agente
    ai_description = Column(Text, nullable=True)       # Generada por OpenAI
    social_caption = Column(Text, nullable=True)       # Copy para redes sociales
    ai_title = Column(String(200), nullable=True)      # Título generado por IA

    # ─── Relaciones ───────────────────────────────────────────────────────────
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    agent = relationship("User", back_populates="properties")
    images = relationship("PropertyImage", back_populates="property", cascade="all, delete-orphan")
    publications = relationship("Publication", back_populates="property", cascade="all, delete-orphan")

    # ─── Timestamps ───────────────────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Property id={self.id} type={self.property_type} city={self.city}>"
