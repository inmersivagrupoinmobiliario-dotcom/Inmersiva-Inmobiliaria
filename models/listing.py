from pydantic import BaseModel, Field, computed_field
from typing import Optional, List
import uuid
from datetime import datetime


class Listing(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tipo: str
    operacion: str
    direccion: str
    ciudad: str
    estado: str
    precio: int
    recamaras: Optional[int] = None
    banos: Optional[float] = None
    m2_construidos: Optional[int] = None
    m2_terreno: Optional[int] = None
    estacionamientos: Optional[int] = None
    amenidades: List[str] = []
    descripcion_agente: str
    agente_nombre: str
    agente_telefono: str
    agente_email: str
    antiguedad: Optional[int] = None
    vista: Optional[str] = None
    estado_inmueble: Optional[str] = None
    modalidad: Optional[str] = None
    forma_pago: List[str] = []
    servicios: List[str] = []
    foto_portada: str = ""
    fotos_extras: List[str] = []
    video_propiedad: str = ""
    tour_360_url: str = ""
    descripcion_generada: str = ""
    copy_instagram: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    @computed_field
    @property
    def precio_str(self) -> str:
        return f"${self.precio:,} MXN"
