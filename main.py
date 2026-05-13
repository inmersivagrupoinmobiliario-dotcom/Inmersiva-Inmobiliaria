import os
import json
import shutil
import uuid
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, Form, File, UploadFile, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from models.listing import Listing
from services.ai_service import generar_contenido

load_dotenv()

app = FastAPI(title="Inmersiva Grupo Inmobiliario — Generador de Contenido")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/generated", StaticFiles(directory="generated"), name="generated")
templates = Jinja2Templates(directory="templates")

UPLOADS = Path("uploads")
GENERATED = Path("generated")


def save_listing(listing: Listing):
    folder = GENERATED / listing.id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "data.json").write_text(listing.model_dump_json(), encoding="utf-8")


def load_listing(listing_id: str) -> Listing:
    data = (GENERATED / listing_id / "data.json").read_text(encoding="utf-8")
    return Listing.model_validate_json(data)


def save_upload(upload: UploadFile, dest: Path) -> None:
    with open(dest, "wb") as f:
        shutil.copyfileobj(upload.file, f)


@app.get("/", response_class=HTMLResponse)
async def form(request: Request):
    return templates.TemplateResponse(request, "form.html")


@app.post("/generar", response_class=HTMLResponse)
async def generar(
    request: Request,
    # ── Corredor ─────────────────────────────────────────────────────────────
    agente_nombre: str = Form(...),
    agente_telefono: str = Form(...),
    agente_email: str = Form(...),
    origen_contacto: str = Form(default=""),
    resultado_llamada: List[str] = Form(default=[]),
    # ── Propietario ───────────────────────────────────────────────────────────
    propietario_nombre: str = Form(default=""),
    propietario_dni: str = Form(default=""),
    propietario_telefono: str = Form(default=""),
    propietario_email: str = Form(default=""),
    propietario_estado_civil: str = Form(default=""),
    propietario_regimen: str = Form(default=""),
    propietario_relacion: str = Form(default=""),
    propietario_otros_titulares: str = Form(default=""),
    # ── Inmueble ──────────────────────────────────────────────────────────────
    tipo: str = Form(...),
    operacion: str = Form(...),
    direccion: str = Form(...),
    ciudad: str = Form(...),
    estado: str = Form(...),
    moneda: str = Form(default="PEN"),
    precio: int = Form(...),
    precio_minimo: Optional[int] = Form(None),
    recamaras: Optional[int] = Form(None),
    banos: Optional[float] = Form(None),
    m2_construidos: Optional[int] = Form(None),
    m2_terreno: Optional[int] = Form(None),
    estacionamientos: Optional[int] = Form(None),
    pisos: Optional[int] = Form(None),
    antiguedad: Optional[int] = Form(None),
    vista: str = Form(default=""),
    estado_inmueble: str = Form(default=""),
    mantenimiento_mensual: Optional[int] = Form(None),
    cuotas_pendientes: str = Form(default=""),
    servicios: List[str] = Form(default=[]),
    amenidades: List[str] = Form(default=[]),
    equipamiento: List[str] = Form(default=[]),
    # ── Documentación ─────────────────────────────────────────────────────────
    tenencia: str = Form(default=""),
    partida_registral: str = Form(default=""),
    oficina_registral: str = Form(default=""),
    declaratoria_fabrica: str = Form(default=""),
    independizacion: str = Form(default=""),
    predial_al_dia: str = Form(default=""),
    arbitrios_al_dia: str = Form(default=""),
    hipoteca: str = Form(default=""),
    hipoteca_entidad: str = Form(default=""),
    hipoteca_saldo: str = Form(default=""),
    litigios: str = Form(default=""),
    # ── Comercial ─────────────────────────────────────────────────────────────
    modalidad: str = Form(default=""),
    forma_pago: List[str] = Form(default=[]),
    comision: str = Form(default=""),
    comision_paga: str = Form(default=""),
    fotos_profesionales: str = Form(default=""),
    # ── Historial ─────────────────────────────────────────────────────────────
    tiempo_publicada: Optional[int] = Form(None),
    num_visitas: Optional[int] = Form(None),
    num_ofertas: Optional[int] = Form(None),
    oferta_mas_alta: Optional[int] = Form(None),
    portales: List[str] = Form(default=[]),
    otros_corredores: str = Form(default=""),
    exclusividad: str = Form(default=""),
    # ── Motivación ────────────────────────────────────────────────────────────
    motivo_venta: str = Form(default=""),
    plazo_venta: str = Form(default=""),
    urgencia: Optional[int] = Form(None),
    dinero_comprometido: str = Form(default=""),
    # ── Ocupación ─────────────────────────────────────────────────────────────
    estado_ocupacion: str = Form(default=""),
    disponibilidad_visitas: str = Form(default=""),
    llaves_tercero: str = Form(default=""),
    # ── Siguiente paso ────────────────────────────────────────────────────────
    proximo_contacto_fecha: str = Form(default=""),
    proximo_contacto_hora: str = Form(default=""),
    proximo_contacto_canal: str = Form(default=""),
    acuerdo_concreto: str = Form(default=""),
    # ── Observaciones ─────────────────────────────────────────────────────────
    interes_percibido: Optional[int] = Form(None),
    decisor_unico: str = Form(default=""),
    tono_actitud: str = Form(default=""),
    descripcion_agente: str = Form(...),
    # ── Archivos ──────────────────────────────────────────────────────────────
    foto_portada: UploadFile = File(...),
    fotos_extras: List[UploadFile] = File(default=[]),
    video_propiedad: Optional[UploadFile] = File(None),
    tour_360_url: str = Form(default=""),
):
    listing_id = str(uuid.uuid4())
    upload_dir = UPLOADS / listing_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    portada_name = f"portada_{foto_portada.filename}"
    save_upload(foto_portada, upload_dir / portada_name)

    extras_names = []
    for extra in fotos_extras:
        if extra.filename:
            name = f"extra_{extra.filename}"
            save_upload(extra, upload_dir / name)
            extras_names.append(f"{listing_id}/{name}")

    video_rel = ""
    if video_propiedad and video_propiedad.filename:
        vname = f"video_{video_propiedad.filename}"
        save_upload(video_propiedad, upload_dir / vname)
        video_rel = f"{listing_id}/{vname}"

    listing = Listing(
        id=listing_id,
        agente_nombre=agente_nombre, agente_telefono=agente_telefono,
        agente_email=agente_email, origen_contacto=origen_contacto,
        resultado_llamada=resultado_llamada,
        propietario_nombre=propietario_nombre, propietario_dni=propietario_dni,
        propietario_telefono=propietario_telefono, propietario_email=propietario_email,
        propietario_estado_civil=propietario_estado_civil,
        propietario_regimen=propietario_regimen, propietario_relacion=propietario_relacion,
        propietario_otros_titulares=propietario_otros_titulares,
        tipo=tipo, operacion=operacion, direccion=direccion,
        ciudad=ciudad, estado=estado, moneda=moneda, precio=precio,
        precio_minimo=precio_minimo, recamaras=recamaras, banos=banos,
        m2_construidos=m2_construidos, m2_terreno=m2_terreno,
        estacionamientos=estacionamientos, pisos=pisos,
        antiguedad=antiguedad, vista=vista, estado_inmueble=estado_inmueble,
        mantenimiento_mensual=mantenimiento_mensual, cuotas_pendientes=cuotas_pendientes,
        servicios=servicios, amenidades=amenidades, equipamiento=equipamiento,
        tenencia=tenencia, partida_registral=partida_registral,
        oficina_registral=oficina_registral, declaratoria_fabrica=declaratoria_fabrica,
        independizacion=independizacion, predial_al_dia=predial_al_dia,
        arbitrios_al_dia=arbitrios_al_dia, hipoteca=hipoteca,
        hipoteca_entidad=hipoteca_entidad, hipoteca_saldo=hipoteca_saldo,
        litigios=litigios, modalidad=modalidad, forma_pago=forma_pago,
        comision=comision, comision_paga=comision_paga,
        fotos_profesionales=fotos_profesionales,
        tiempo_publicada=tiempo_publicada, num_visitas=num_visitas,
        num_ofertas=num_ofertas, oferta_mas_alta=oferta_mas_alta,
        portales=portales, otros_corredores=otros_corredores, exclusividad=exclusividad,
        motivo_venta=motivo_venta, plazo_venta=plazo_venta,
        urgencia=urgencia, dinero_comprometido=dinero_comprometido,
        estado_ocupacion=estado_ocupacion, disponibilidad_visitas=disponibilidad_visitas,
        llaves_tercero=llaves_tercero,
        proximo_contacto_fecha=proximo_contacto_fecha,
        proximo_contacto_hora=proximo_contacto_hora,
        proximo_contacto_canal=proximo_contacto_canal,
        acuerdo_concreto=acuerdo_concreto,
        interes_percibido=interes_percibido, decisor_unico=decisor_unico,
        tono_actitud=tono_actitud, descripcion_agente=descripcion_agente,
        foto_portada=f"{listing_id}/{portada_name}",
        fotos_extras=extras_names, video_propiedad=video_rel,
        tour_360_url=tour_360_url,
    )

    try:
        descripcion, copy_ig = generar_contenido(listing)
    except Exception as e:
        return templates.TemplateResponse(
            request, "form.html", {"error": f"Error al generar contenido: {e}"}
        )

    listing.descripcion_generada = descripcion
    listing.copy_instagram = copy_ig
    save_listing(listing)

    return templates.TemplateResponse(request, "results.html", {"listing": listing})


# ── PDF ───────────────────────────────────────────────────────────────────────
from services.pdf_service import generar_pdf

@app.get("/pdf/{listing_id}")
async def descargar_pdf(listing_id: str):
    listing = load_listing(listing_id)
    pdf_path = GENERATED / "pdfs" / f"{listing_id}.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    generar_pdf(listing, str(pdf_path))
    filename = f"inmersiva_{listing.tipo.lower()}_{listing.ciudad.lower()}.pdf"
    return FileResponse(str(pdf_path), media_type="application/pdf", filename=filename)


# ── Instagram Image ───────────────────────────────────────────────────────────
from services.image_service import generar_imagen_instagram

@app.get("/imagen/{listing_id}")
async def descargar_imagen(listing_id: str):
    listing = load_listing(listing_id)
    img_path = GENERATED / "images" / f"{listing_id}.jpg"
    img_path.parent.mkdir(parents=True, exist_ok=True)
    portada_path = (UPLOADS / listing.foto_portada) if listing.foto_portada else None
    generar_imagen_instagram(listing, str(portada_path) if portada_path else None, str(img_path))
    filename = f"inmersiva_instagram_{listing.tipo.lower()}.jpg"
    return FileResponse(str(img_path), media_type="image/jpeg", filename=filename)


# ── Instagram Publishing ──────────────────────────────────────────────────────
from services.social_service import publicar_instagram

@app.post("/publicar/{listing_id}")
async def publicar(listing_id: str):
    listing = load_listing(listing_id)
    img_path = GENERATED / "images" / f"{listing_id}.jpg"
    if not img_path.exists():
        portada_path = (UPLOADS / listing.foto_portada) if listing.foto_portada else None
        img_path.parent.mkdir(parents=True, exist_ok=True)
        generar_imagen_instagram(listing, str(portada_path) if portada_path else None, str(img_path))
    result = publicar_instagram(str(img_path), listing.copy_instagram)
    return JSONResponse(content=result)


# ── Video ─────────────────────────────────────────────────────────────────────
from services.video_service import iniciar_render, get_status

@app.post("/video/{listing_id}")
async def generar_video(listing_id: str):
    listing = load_listing(listing_id)
    video_path = GENERATED / "videos" / f"{listing_id}.mp4"
    video_path.parent.mkdir(parents=True, exist_ok=True)
    iniciar_render(listing, str(video_path))
    return JSONResponse(content={"ok": True, "status": "rendering"})

@app.get("/video/status/{listing_id}")
async def video_status(listing_id: str):
    return JSONResponse(content={"status": get_status(listing_id)})
