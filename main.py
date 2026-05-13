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

app = FastAPI(title="ListaPro — Inmersiva")
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


@app.get("/", response_class=HTMLResponse)
async def form(request: Request):
    return templates.TemplateResponse(request, "form.html")


@app.post("/generar", response_class=HTMLResponse)
async def generar(
    request: Request,
    tipo: str = Form(...),
    operacion: str = Form(...),
    direccion: str = Form(...),
    ciudad: str = Form(...),
    estado: str = Form(...),
    precio: int = Form(...),
    recamaras: Optional[int] = Form(None),
    banos: Optional[float] = Form(None),
    m2_construidos: Optional[int] = Form(None),
    m2_terreno: Optional[int] = Form(None),
    estacionamientos: Optional[int] = Form(None),
    amenidades: List[str] = Form(default=[]),
    descripcion_agente: str = Form(...),
    agente_nombre: str = Form(...),
    agente_telefono: str = Form(...),
    agente_email: str = Form(...),
    foto_portada: UploadFile = File(...),
    fotos_extras: List[UploadFile] = File(default=[]),
):
    listing_id = str(uuid.uuid4())
    upload_dir = UPLOADS / listing_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    portada_name = f"portada_{foto_portada.filename}"
    with open(upload_dir / portada_name, "wb") as f:
        shutil.copyfileobj(foto_portada.file, f)

    extras_names = []
    for extra in fotos_extras:
        if extra.filename:
            name = f"extra_{extra.filename}"
            with open(upload_dir / name, "wb") as f:
                shutil.copyfileobj(extra.file, f)
            extras_names.append(f"{listing_id}/{name}")

    listing = Listing(
        id=listing_id, tipo=tipo, operacion=operacion,
        direccion=direccion, ciudad=ciudad, estado=estado, precio=precio,
        recamaras=recamaras, banos=banos, m2_construidos=m2_construidos,
        m2_terreno=m2_terreno, estacionamientos=estacionamientos,
        amenidades=amenidades, descripcion_agente=descripcion_agente,
        agente_nombre=agente_nombre, agente_telefono=agente_telefono,
        agente_email=agente_email,
        foto_portada=f"{listing_id}/{portada_name}",
        fotos_extras=extras_names,
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


# ── Phase 2: PDF ─────────────────────────────────────────────────────────────

from services.pdf_service import generar_pdf


@app.get("/pdf/{listing_id}")
async def descargar_pdf(listing_id: str):
    listing = load_listing(listing_id)
    pdf_path = GENERATED / "pdfs" / f"{listing_id}.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    generar_pdf(listing, str(pdf_path))
    filename = f"inmersiva_{listing.tipo.lower()}_{listing.ciudad.lower()}.pdf"
    return FileResponse(str(pdf_path), media_type="application/pdf", filename=filename)


# ── Phase 3: Instagram Image ──────────────────────────────────────────────────

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


# ── Phase 4: Instagram Publishing ────────────────────────────────────────────

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


# ── Phase 5: Video ────────────────────────────────────────────────────────────

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
    status = get_status(listing_id)
    return JSONResponse(content={"status": status})
