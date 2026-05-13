"""
INMERSIVA — Modelo de Usuario
Define la estructura de la tabla 'users' en la base de datos.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class UserRole(str, enum.Enum):
    """Roles disponibles en el sistema."""
    ADMIN = "admin"        # Acceso total
    AGENT = "agent"        # Acceso a sus propias publicaciones


class User(Base):
    """
    Tabla de usuarios del sistema.
    Cada agente de INMERSIVA tendrá un registro aquí.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.AGENT, nullable=False)
    is_active = Column(Boolean, default=True)
    avatar_url = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relación con propiedades (un usuario puede tener muchas propiedades)
    properties = relationship("Property", back_populates="agent")

    def __repr__(self):
        return f"<User id={self.id} email={self.email} role={self.role}>"
