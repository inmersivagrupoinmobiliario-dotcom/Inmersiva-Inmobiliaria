"""
INMERSIVA — Modelo de Publicación
Registra cada vez que se publica una propiedad en redes sociales.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Publication(Base):
    """
    Historial de publicaciones por propiedad.
    Guarda qué se generó y en qué redes se publicó.
    """
    __tablename__ = "publications"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)

    # ─── Archivos generados ───────────────────────────────────────────────────
    social_image_url = Column(String(500), nullable=True)   # Imagen 1080x1080
    pdf_url = Column(String(500), nullable=True)             # Ficha PDF

    # ─── Estado de publicación ────────────────────────────────────────────────
    instagram_posted = Column(Boolean, default=False)
    facebook_posted = Column(Boolean, default=False)
    instagram_post_id = Column(String(100), nullable=True)  # ID retornado por la API
    facebook_post_id = Column(String(100), nullable=True)

    # ─── Metadata ─────────────────────────────────────────────────────────────
    error_log = Column(Text, nullable=True)  # Si algo falla, guardamos el error
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    property = relationship("Property", back_populates="publications")

    def __repr__(self):
        return f"<Publication id={self.id} property_id={self.property_id}>"
