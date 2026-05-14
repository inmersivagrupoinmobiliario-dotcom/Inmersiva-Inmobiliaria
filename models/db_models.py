from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey
from datetime import datetime
import json as _json
from database import Base


class SolicitudCorredor(Base):
    __tablename__ = "solicitudes_corredor"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)  # email personal del solicitante
    telefono = Column(String(30), default="")
    dni = Column(String(20), nullable=True)
    mensaje = Column(Text, default="")
    cv_archivo = Column(String(300), nullable=True)  # ruta al CV subido
    estado = Column(String(20), default="Pendiente")  # Pendiente / Aprobado / Rechazado
    created_at = Column(DateTime, default=datetime.utcnow)


class Contacto(Base):
    __tablename__ = "contactos"
    id = Column(Integer, primary_key=True)
    corredor_id = Column(Integer, ForeignKey("corredores.id"), nullable=False)
    nombre = Column(String(100), nullable=False)
    email = Column(String(100), default="")
    telefono = Column(String(30), default="")
    origen = Column(String(50), default="Web")
    estado = Column(String(30), default="Nuevo")
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
    estado = Column(String(20), default="Pendiente")
    created_at = Column(DateTime, default=datetime.utcnow)


class DocumentoCorredor(Base):
    __tablename__ = "documentos_corredor"
    id = Column(Integer, primary_key=True)
    corredor_id = Column(Integer, ForeignKey("corredores.id"), nullable=False)
    nombre = Column(String(200), nullable=False)
    tipo = Column(String(50), default="Otro")
    archivo = Column(String(300), default="")
    notas = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class PostRRSS(Base):
    __tablename__ = "posts_rrss"
    id = Column(Integer, primary_key=True)
    corredor_id = Column(Integer, ForeignKey("corredores.id"), nullable=False)
    # Campos originales
    red = Column(String(30), nullable=False)
    contenido = Column(Text, default="")
    url = Column(String(500), default="")
    fecha_publicacion = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    # Campos nuevos para flujo de aprobación
    listing_id = Column(String(36), nullable=True)
    titulo = Column(String(200), nullable=True)
    imagen_url = Column(String(500), nullable=True)
    estado = Column(String(20), default="Pendiente")   # Pendiente/Aprobado/Rechazado/Publicado
    comentario_admin = Column(Text, nullable=True)
    redes = Column(String(200), nullable=True)          # CSV: instagram,facebook,whatsapp,tiktok
    upload_post_id = Column(String(100), nullable=True)
    publicado_at = Column(DateTime, nullable=True)
    caption = Column(Text, nullable=True)

    @property
    def redes_list(self):
        return [r.strip() for r in (self.redes or "").split(",") if r.strip()]


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
    # Campos nuevos de perfil
    foto_perfil = Column(String(300), nullable=True)
    bio = Column(Text, nullable=True)
    instagram = Column(String(100), nullable=True)
    whatsapp = Column(String(30), nullable=True)
    dni = Column(String(20), nullable=True)
    direccion = Column(String(200), nullable=True)
    email_personal = Column(String(100), nullable=True)  # Gmail personal para reenvío Cloudflare


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
    vistas = Column(Integer, default=0)
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


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id = Column(Integer, primary_key=True)
    email = Column(String(100), nullable=False, index=True)
    token = Column(String(64), unique=True, nullable=False)
    tipo = Column(String(20), default="corredor")  # corredor / usuario
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
