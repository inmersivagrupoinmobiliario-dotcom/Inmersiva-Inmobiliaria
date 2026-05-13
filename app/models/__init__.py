"""
INMERSIVA — Registro de modelos
Importar todos los modelos aquí garantiza que SQLAlchemy los detecte al crear tablas.
"""

from app.models.user import User, UserRole
from app.models.property import Property, PropertyType, OperationType, PropertyStatus
from app.models.property_image import PropertyImage
from app.models.publication import Publication

__all__ = [
    "User",
    "UserRole",
    "Property",
    "PropertyType",
    "OperationType",
    "PropertyStatus",
    "PropertyImage",
    "Publication",
]
