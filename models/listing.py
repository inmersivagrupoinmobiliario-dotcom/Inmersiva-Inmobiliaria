from pydantic import BaseModel, Field, computed_field
from typing import Optional, List
import uuid
from datetime import datetime

MONEDA_SIMBOLO = {"PEN": "S/", "USD": "US$", "MXN": "$"}


class Listing(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    # ── Corredor ────────────────────────────────────────────────────────────
    agente_nombre: str
    agente_telefono: str
    agente_email: str
    origen_contacto: str = ""
    resultado_llamada: List[str] = []

    # ── Propietario ─────────────────────────────────────────────────────────
    propietario_nombre: str = ""
    propietario_dni: str = ""
    propietario_telefono: str = ""
    propietario_email: str = ""
    propietario_estado_civil: str = ""
    propietario_regimen: str = ""
    propietario_relacion: str = ""
    propietario_otros_titulares: str = ""

    # ── Inmueble ─────────────────────────────────────────────────────────────
    tipo: str
    operacion: str
    direccion: str
    ciudad: str
    estado: str
    moneda: str = "PEN"
    precio: int
    precio_minimo: Optional[int] = None
    recamaras: Optional[int] = None
    banos: Optional[float] = None
    m2_construidos: Optional[int] = None
    m2_terreno: Optional[int] = None
    estacionamientos: Optional[int] = None
    pisos: Optional[int] = None
    antiguedad: Optional[int] = None
    vista: str = ""
    estado_inmueble: str = ""
    mantenimiento_mensual: Optional[int] = None
    cuotas_pendientes: str = ""
    servicios: List[str] = []
    amenidades: List[str] = []
    equipamiento: List[str] = []

    # ── Documentación ────────────────────────────────────────────────────────
    tenencia: str = ""
    partida_registral: str = ""
    oficina_registral: str = ""
    declaratoria_fabrica: str = ""
    independizacion: str = ""
    predial_al_dia: str = ""
    arbitrios_al_dia: str = ""
    litigios: str = ""
    hipoteca: str = ""
    hipoteca_entidad: str = ""
    hipoteca_saldo: str = ""

    # ── Comercial ────────────────────────────────────────────────────────────
    modalidad: str = ""
    forma_pago: List[str] = []
    comision: str = ""
    comision_paga: str = ""
    fotos_profesionales: str = ""

    # ── Historial ────────────────────────────────────────────────────────────
    tiempo_publicada: Optional[int] = None
    num_visitas: Optional[int] = None
    num_ofertas: Optional[int] = None
    oferta_mas_alta: Optional[int] = None
    portales: List[str] = []
    otros_corredores: str = ""
    exclusividad: str = ""

    # ── Motivación y urgencia ─────────────────────────────────────────────────
    motivo_venta: str = ""
    plazo_venta: str = ""
    urgencia: Optional[int] = None
    dinero_comprometido: str = ""

    # ── Ocupación ────────────────────────────────────────────────────────────
    estado_ocupacion: str = ""
    disponibilidad_visitas: str = ""
    llaves_tercero: str = ""

    # ── Siguiente paso ────────────────────────────────────────────────────────
    proximo_contacto_fecha: str = ""
    proximo_contacto_hora: str = ""
    proximo_contacto_canal: str = ""
    acuerdo_concreto: str = ""

    # ── Observaciones del corredor ────────────────────────────────────────────
    interes_percibido: Optional[int] = None
    decisor_unico: str = ""
    tono_actitud: str = ""
    descripcion_agente: str = ""

    # ── Archivos ─────────────────────────────────────────────────────────────
    foto_portada: str = ""
    fotos_extras: List[str] = []
    video_propiedad: str = ""
    tour_360_url: str = ""

    # ── Generado por IA ───────────────────────────────────────────────────────
    descripcion_generada: str = ""
    copy_instagram: str = ""

    @computed_field
    @property
    def precio_str(self) -> str:
        simbolo = MONEDA_SIMBOLO.get(self.moneda, "S/")
        return f"{simbolo} {self.precio:,}"

    @computed_field
    @property
    def precio_minimo_str(self) -> str:
        if not self.precio_minimo:
            return ""
        simbolo = MONEDA_SIMBOLO.get(self.moneda, "S/")
        return f"{simbolo} {self.precio_minimo:,}"
