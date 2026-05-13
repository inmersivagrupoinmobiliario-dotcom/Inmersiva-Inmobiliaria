"""
INMERSIVA — Modelo de Imágenes de Propiedad
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PropertyImage(Base):
    """
    Tabla de imágenes asociadas a una propiedad.
    Una propiedad puede tener múltiples imágenes; una de ellas es la portada.
    """
    __tablename__ = "property_images"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    image_url = Column(String(500), nullable=False)
    is_cover = Column(Boolean, default=False)  # Solo una imagen puede ser portada
    original_filename = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    property = relationship("Property", back_populates="images")

    def __repr__(self):
        return f"<PropertyImage id={self.id} property_id={self.property_id} cover={self.is_cover}>"
