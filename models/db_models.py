from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey
from datetime import datetime
import json as _json
from database import Base


class Contacto(Base):
    __tablename__ = "contactos"
    id = Column(Integer, primary_key=True)
    corredor_id = Column(Integer, ForeignKey("corredores.id"), nullable=False)
    nombre = Column(String(100), nullable=False)
    email = Column(String(100), default="")
    telefono = Column(String(30), default="")
    origen = Column(String(50), default="Web")        # Web, WhatsApp, Referido, Portal, Otro
    estado = Column(String(30), default="Nuevo")      # Nuevo, Contactado, Negociacion, Ganado, Perdido
    interes = Column(String(300), default="")
    notas = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Cita(Base):
    __tablename__ = "citas"
    id = Column(Integer, primary_key=True)
    corredor_id = Column(Integer, ForeignKey("corredores.id"), nullable=False)
    contacto_id = Column(Integer, ForeignKey("contactos.id"), nullable=True)
    titulo = Column(String(200), nullable=False)
    descripcion = Column(Text, default="")
    fecha = Column(DateTime, nullable=False)
    lugar = Column(String(200), default="")
    estado = Column(String(20), default="Pendiente")  # Pendiente, Completada, Cancelada
    created_at = Column(DateTime, default=datetime.utcnow)


class DocumentoCorredor(Base):
    __tablename__ = "documentos_corredor"
    id = Column(Integer, primary_key=True)
    corredor_id = Column(Integer, ForeignKey("corredores.id"), nullable=False)
    nombre = Column(String(200), nullable=False)
    tipo = Column(String(50), default="Otro")         # Contrato, Tasación, Plano, Fotos, Otro
    archivo = Column(String(300), default="")
    notas = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class PostRRSS(Base):
    __tablename__ = "posts_rrss"
    id = Column(Integer, primary_key=True)
    corredor_id = Column(Integer, ForeignKey("corredores.id"), nullable=False)
    red = Column(String(30), nullable=False)          # Instagram, Facebook, WhatsApp, TikTok
    contenido = Column(Text, default="")
    url = Column(String(500), default="")
    fecha_publicacion = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class Corredor(Base):
    __tablename__ = "corredores"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    telefono = Column(String(20), default="")
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class UsuarioPublico(Base):
    __tablename__ = "usuarios_publicos"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(200), nullable=True)
    google_id = Column(String(100), nullable=True)
    telefono = Column(String(20), default="")
    activo = Column(Boolean, default=True)
    favoritos = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)


class PropiedadPublica(Base):
    __tablename__ = "propiedades_publicas"
    id = Column(Integer, primary_key=True)
    listing_id = Column(String(36), unique=True, nullable=False)
    titulo = Column(String(200), nullable=False)
    tipo = Column(String(50), nullable=False)
    operacion = Column(String(20), nullable=False)
    precio = Column(Integer, nullable=False)
    moneda = Column(String(10), default="PEN")
    ciudad = Column(String(100), nullable=False)
    estado = Column(String(100), nullable=False)
    direccion = Column(String(200), nullable=False)
    descripcion = Column(Text, default="")
    habitaciones = Column(Integer, nullable=True)
    banos = Column(Float, nullable=True)
    m2_construidos = Column(Integer, nullable=True)
    m2_terreno = Column(Integer, nullable=True)
    estacionamientos = Column(Integer, nullable=True)
    foto_portada = Column(String(300), default="")
    fotos_extras = Column(Text, default="[]")
    tour_360_url = Column(String(500), default="")
    corredor_id = Column(Integer, ForeignKey("corredores.id"), nullable=True)
    publicado = Column(Boolean, default=True)
    destacado = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def fotos_list(self):
        try:
            return _json.loads(self.fotos_extras or "[]")
        except Exception:
            return []

    @property
    def precio_fmt(self):
        sym = "S/." if self.moneda == "PEN" else ("USD" if self.moneda == "USD" else self.moneda)
        return f"{sym} {self.precio:,}"
