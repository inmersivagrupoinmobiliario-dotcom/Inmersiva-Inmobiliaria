import os
import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, Form, File, UploadFile, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

from models.listing import Listing
from services.ai_service import generar_contenido
from auth import hash_password, verify_password, create_token, get_empresa_session, get_corredor_session, get_usuario_session, oauth
from database import engine, SessionLocal, Base
from typing import Optional as Opt

load_dotenv()

# DB init
from models.db_models import Corredor as CorredorModel, PropiedadPublica, UsuarioPublico

def _init_db():
    try:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            if db.query(CorredorModel).count() == 0:
                db.add(CorredorModel(
                    nombre="Corredor Demo", email="corredor@inmersiva.com",
                    username="corredor1", hashed_password=hash_password("corredor123"),
                ))
                db.commit()
        finally:
            db.close()
    except Exception as e:
        print(f"[WARN] DB init: {e}")

_init_db()

EMPRESA_USER = os.getenv("EMPRESA_USER", "admin")
EMPRESA_PASS = os.getenv("EMPRESA_PASS", "Inmersiva2025")

app = FastAPI(title="Inmersiva Grupo Inmobiliario")
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "inmersiva-session-secret-2025"))
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/generated", StaticFiles(directory="generated"), name="generated")
templates = Jinja2Templates(directory="templates")

UPLOADS = Path("uploads")
GENERATED = Path("generated")


# ── Helpers ───────────────────────────────────────────────────────────────────
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


def list_fichas(corredor_email: str = None) -> list:
    fichas = []
    for data_file in sorted(GENERATED.glob("*/data.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(data_file.read_text(encoding="utf-8"))
            if corredor_email and data.get("agente_email") != corredor_email:
                continue
            data["_mtime"] = data_file.stat().st_mtime
            fichas.append(data)
        except Exception:
            pass
    return fichas


def fichas_stats(fichas: list) -> dict:
    now = datetime.now()
    fichas_mes = sum(
        1 for f in fichas
        if datetime.fromtimestamp(f.get("_mtime", 0)).month == now.month
        and datetime.fromtimestamp(f.get("_mtime", 0)).year == now.year
    )
    pdfs = sum(1 for f in fichas if (GENERATED / "pdfs" / f"{f['id']}.pdf").exists())
    return {"total": len(fichas), "fichas_mes": fichas_mes, "pdfs": pdfs}


# ── Portal público ────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def portal(
    request: Request,
    tipo: Opt[str] = None,
    operacion: Opt[str] = None,
    ciudad: Opt[str] = None,
):
    db = SessionLocal()
    try:
        q = db.query(PropiedadPublica).filter(PropiedadPublica.publicado == True)
        if tipo:
            q = q.filter(PropiedadPublica.tipo == tipo)
        if operacion:
            q = q.filter(PropiedadPublica.operacion == operacion)
        if ciudad:
            q = q.filter(PropiedadPublica.ciudad.ilike(f"%{ciudad}%"))
        propiedades = q.order_by(
            PropiedadPublica.destacado.desc(),
            PropiedadPublica.created_at.desc()
        ).all()
    finally:
        db.close()

    empresa = get_empresa_session(request)
    corredor = get_corredor_session(request)
    usuario = get_usuario_session(request)
    user = empresa or corredor or usuario
    return templates.TemplateResponse(request, "portal.html", {
        "propiedades": propiedades,
        "filtros": {"tipo": tipo or "", "operacion": operacion or "", "ciudad": ciudad or ""},
        "user": user,
        "usuario": usuario,
    })


@app.get("/propiedad/{propiedad_id}", response_class=HTMLResponse)
async def detalle_propiedad(request: Request, propiedad_id: int):
    db = SessionLocal()
    try:
        propiedad = db.query(PropiedadPublica).filter(
            PropiedadPublica.id == propiedad_id,
            PropiedadPublica.publicado == True,
        ).first()
        if not propiedad:
            return RedirectResponse("/", status_code=302)
        corredor_obj = db.query(CorredorModel).filter(
            CorredorModel.id == propiedad.corredor_id
        ).first() if propiedad.corredor_id else None
    finally:
        db.close()

    empresa = get_empresa_session(request)
    corredor_session = get_corredor_session(request)
    return templates.TemplateResponse(request, "propiedad_detalle.html", {
        "p": propiedad,
        "corredor": corredor_obj,
        "user": empresa or corredor_session,
    })


# ── Admin: publicar ficha en portal ───────────────────────────────────────────
@app.post("/admin/publicar-ficha/{listing_id}")
async def publicar_ficha_portal(request: Request, listing_id: str):
    empresa = get_empresa_session(request)
    if not empresa:
        return RedirectResponse("/login", status_code=302)
    try:
        listing = load_listing(listing_id)
    except Exception:
        return RedirectResponse("/dashboard?error=Ficha+no+encontrada", status_code=302)

    db = SessionLocal()
    try:
        existing = db.query(PropiedadPublica).filter(
            PropiedadPublica.listing_id == listing_id
        ).first()
        if existing:
            existing.publicado = True
        else:
            corredor_obj = db.query(CorredorModel).filter(
                CorredorModel.email == listing.agente_email
            ).first()
            db.add(PropiedadPublica(
                listing_id=listing_id,
                titulo=f"{listing.tipo} en {listing.operacion} — {listing.ciudad}",
                tipo=listing.tipo,
                operacion=listing.operacion,
                precio=listing.precio,
                moneda=getattr(listing, "moneda", "PEN"),
                ciudad=listing.ciudad,
                estado=listing.estado,
                direccion=listing.direccion,
                descripcion=listing.descripcion_generada or listing.descripcion_agente,
                habitaciones=listing.recamaras,
                banos=listing.banos,
                m2_construidos=listing.m2_construidos,
                m2_terreno=listing.m2_terreno,
                estacionamientos=listing.estacionamientos,
                foto_portada=listing.foto_portada,
                fotos_extras=json.dumps(listing.fotos_extras or []),
                tour_360_url=getattr(listing, "tour_360_url", ""),
                corredor_id=corredor_obj.id if corredor_obj else None,
            ))
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/dashboard", status_code=302)


@app.post("/admin/propiedad/{propiedad_id}/despublicar")
async def despublicar_propiedad(request: Request, propiedad_id: int):
    empresa = get_empresa_session(request)
    if not empresa:
        return RedirectResponse("/login", status_code=302)
    db = SessionLocal()
    try:
        p = db.query(PropiedadPublica).filter(PropiedadPublica.id == propiedad_id).first()
        if p:
            p.publicado = False
            db.commit()
    finally:
        db.close()
    return RedirectResponse("/dashboard", status_code=302)


@app.post("/admin/propiedad/{propiedad_id}/destacar")
async def destacar_propiedad(request: Request, propiedad_id: int):
    empresa = get_empresa_session(request)
    if not empresa:
        return RedirectResponse("/login", status_code=302)
    db = SessionLocal()
    try:
        p = db.query(PropiedadPublica).filter(PropiedadPublica.id == propiedad_id).first()
        if p:
            p.destacado = not p.destacado
            db.commit()
    finally:
        db.close()
    return RedirectResponse("/dashboard", status_code=302)


# ── Auth routes ────────────────────────────────────────────────────────────────


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, tab: str = "usuario"):
    if get_empresa_session(request):
        return RedirectResponse("/dashboard", status_code=302)
    if get_corredor_session(request):
        return RedirectResponse("/corredor/dashboard", status_code=302)
    if get_usuario_session(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(request, "login.html", {"error": "", "tab": tab})


# ── Registro usuario público ───────────────────────────────────────────────────
@app.get("/registro", response_class=HTMLResponse)
async def registro_page(request: Request):
    if get_empresa_session(request) or get_corredor_session(request) or get_usuario_session(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(request, "registro.html", {"error": "", "success": ""})


@app.post("/registro")
async def registro_submit(
    request: Request,
    nombre: str = Form(...),
    email: str = Form(...),
    telefono: str = Form(default=""),
    password: str = Form(...),
    password2: str = Form(...),
):
    if password != password2:
        return templates.TemplateResponse(request, "registro.html",
                                          {"error": "Las contraseñas no coinciden.", "success": ""})
    if len(password) < 6:
        return templates.TemplateResponse(request, "registro.html",
                                          {"error": "La contraseña debe tener al menos 6 caracteres.", "success": ""})
    db = SessionLocal()
    try:
        if db.query(UsuarioPublico).filter(UsuarioPublico.email == email).first():
            return templates.TemplateResponse(request, "registro.html",
                                              {"error": "Ese email ya está registrado.", "success": ""})
        db.add(UsuarioPublico(
            nombre=nombre, email=email, telefono=telefono,
            hashed_password=hash_password(password),
        ))
        db.commit()
    finally:
        db.close()
    token = create_token({"sub": email, "nombre": nombre, "role": "usuario"})
    resp = RedirectResponse("/", status_code=302)
    resp.set_cookie("usuario_token", token, httponly=True, samesite="lax")
    return resp


@app.post("/login/usuario")
async def login_usuario(request: Request, email: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    try:
        usuario = db.query(UsuarioPublico).filter(
            UsuarioPublico.email == email, UsuarioPublico.activo == True
        ).first()
        if usuario and usuario.hashed_password and verify_password(password, usuario.hashed_password):
            token = create_token({"sub": email, "nombre": usuario.nombre, "role": "usuario"})
            resp = RedirectResponse("/", status_code=302)
            resp.set_cookie("usuario_token", token, httponly=True, samesite="lax")
            return resp
    finally:
        db.close()
    return templates.TemplateResponse(request, "login.html",
                                      {"error": "Email o contraseña incorrectos.", "tab": "usuario"})


@app.post("/login")
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    # Try empresa
    if username == EMPRESA_USER and password == EMPRESA_PASS:
        token = create_token({"sub": username, "role": "empresa"})
        resp = RedirectResponse("/dashboard", status_code=302)
        resp.set_cookie("empresa_token", token, httponly=True, samesite="lax")
        return resp
    # Try corredor
    db = SessionLocal()
    try:
        corredor = db.query(CorredorModel).filter(
            CorredorModel.username == username, CorredorModel.activo == True
        ).first()
        if corredor and verify_password(password, corredor.hashed_password):
            token = create_token({"sub": corredor.username, "email": corredor.email, "nombre": corredor.nombre})
            resp = RedirectResponse("/corredor/dashboard", status_code=302)
            resp.set_cookie("corredor_token", token, httponly=True, samesite="lax")
            return resp
    finally:
        db.close()
    return templates.TemplateResponse(request, "login.html", {"error": "Usuario o contraseña incorrectos", "tab": "admin"}, status_code=401)


@app.get("/logout")
async def logout():
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie("empresa_token")
    resp.delete_cookie("corredor_token")
    resp.delete_cookie("usuario_token")
    return resp


@app.get("/usuario/logout")
async def usuario_logout():
    resp = RedirectResponse("/", status_code=302)
    resp.delete_cookie("usuario_token")
    return resp


# ── Google OAuth ──────────────────────────────────────────────────────────────
@app.get("/auth/google")
async def google_login(request: Request):
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/google/callback", name="google_callback")
async def google_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception:
        return templates.TemplateResponse(
            request, "login.html",
            {"error": "Error al autenticar con Google. Intenta de nuevo."},
            status_code=400,
        )

    user_info = token.get("userinfo", {})
    email = user_info.get("email", "")
    nombre = user_info.get("name", email)

    if not email:
        return templates.TemplateResponse(
            request, "login.html",
            {"error": "No se pudo obtener el correo de Google."},
            status_code=400,
        )

    # ¿Es cuenta empresa?
    google_empresa_emails = [
        e.strip() for e in os.getenv("GOOGLE_EMPRESA_EMAIL", "").split(",") if e.strip()
    ]
    if email in google_empresa_emails:
        t = create_token({"sub": EMPRESA_USER, "role": "empresa"})
        resp = RedirectResponse("/dashboard", status_code=302)
        resp.set_cookie("empresa_token", t, httponly=True, samesite="lax")
        return resp

    # ¿Es corredor registrado?
    db = SessionLocal()
    try:
        corredor = db.query(CorredorModel).filter(
            CorredorModel.email == email, CorredorModel.activo == True
        ).first()
        if corredor:
            t = create_token({"sub": corredor.username, "email": corredor.email, "nombre": corredor.nombre})
            resp = RedirectResponse("/corredor/dashboard", status_code=302)
            resp.set_cookie("corredor_token", t, httponly=True, samesite="lax")
            return resp
    finally:
        db.close()

    # Auto-create or login as UsuarioPublico
    db2 = SessionLocal()
    try:
        google_id = user_info.get("sub", "")
        usuario = db2.query(UsuarioPublico).filter(UsuarioPublico.email == email).first()
        if not usuario:
            usuario = UsuarioPublico(
                nombre=nombre,
                email=email,
                google_id=google_id,
            )
            db2.add(usuario)
            db2.commit()
            db2.refresh(usuario)
        elif google_id and not usuario.google_id:
            usuario.google_id = google_id
            db2.commit()
        t = create_token({"sub": email, "nombre": usuario.nombre, "role": "usuario"})
        resp = RedirectResponse("/", status_code=302)
        resp.set_cookie("usuario_token", t, httponly=True, samesite="lax")
        return resp
    finally:
        db2.close()


# ── Empresa dashboard ─────────────────────────────────────────────────────────
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_empresa(request: Request):
    empresa = get_empresa_session(request)
    if not empresa:
        return RedirectResponse("/login", status_code=302)
    corredor_session = get_corredor_session(request)
    corredor_error = request.query_params.get("corredor_error", "")

    db = SessionLocal()
    try:
        corredores = db.query(CorredorModel).order_by(CorredorModel.created_at.desc()).all()
        corredores_activos = sum(1 for c in corredores if c.activo)
        corredor_obj = None
        if corredor_session:
            corredor_obj = db.query(CorredorModel).filter(CorredorModel.username == corredor_session["sub"]).first()
    finally:
        db.close()

    fichas = list_fichas()
    s = fichas_stats(fichas)
    return templates.TemplateResponse(request, "dashboard_empresa.html", {
        "empresa_user": empresa["sub"],
        "corredor": corredor_obj,
        "fichas": fichas,
        "corredores": corredores,
        "corredor_error": corredor_error,
        "stats": {
            "total_fichas": s["total"],
            "fichas_mes": s["fichas_mes"],
            "corredores_activos": corredores_activos,
            "pdfs_generados": s["pdfs"],
        },
    })


# ── Corredor auth ─────────────────────────────────────────────────────────────
@app.post("/corredor/login")
async def corredor_login(request: Request, username: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    try:
        corredor = db.query(CorredorModel).filter(
            CorredorModel.username == username, CorredorModel.activo == True
        ).first()
        if corredor and verify_password(password, corredor.hashed_password):
            token = create_token({"sub": corredor.username, "email": corredor.email, "nombre": corredor.nombre})
            resp = RedirectResponse("/corredor/dashboard", status_code=302)
            resp.set_cookie("corredor_token", token, httponly=True, samesite="lax")
            return resp
    finally:
        db.close()
    return templates.TemplateResponse(request, "login.html",
                                      {"error": "Usuario o contraseña incorrectos.", "tab": "corredor"},
                                      status_code=401)


@app.get("/corredor/logout")
async def corredor_logout():
    resp = RedirectResponse("/dashboard", status_code=302)
    resp.delete_cookie("corredor_token")
    return resp


@app.get("/corredor/dashboard", response_class=HTMLResponse)
async def dashboard_corredor(request: Request):
    corredor_session = get_corredor_session(request)
    if not corredor_session:
        if get_empresa_session(request):
            return RedirectResponse("/dashboard", status_code=302)
        return RedirectResponse("/login", status_code=302)

    db = SessionLocal()
    try:
        corredor = db.query(CorredorModel).filter(CorredorModel.username == corredor_session["sub"]).first()
    finally:
        db.close()

    if not corredor:
        resp = RedirectResponse("/login", status_code=302)
        resp.delete_cookie("corredor_token")
        return resp

    fichas = list_fichas(corredor_email=corredor.email)
    s = fichas_stats(fichas)
    return templates.TemplateResponse(request, "dashboard_corredor.html", {
        "corredor": corredor,
        "fichas": fichas,
        "stats": {"mis_fichas": s["total"], "fichas_mes": s["fichas_mes"], "pdfs": s["pdfs"]},
    })


# ── Nueva ficha (protected) ───────────────────────────────────────────────────
@app.get("/nueva-ficha", response_class=HTMLResponse)
async def nueva_ficha(request: Request):
    corredor_session = get_corredor_session(request)
    if not corredor_session:
        if get_empresa_session(request):
            return RedirectResponse("/dashboard", status_code=302)
        return RedirectResponse("/login", status_code=302)

    db = SessionLocal()
    try:
        corredor = db.query(CorredorModel).filter(CorredorModel.username == corredor_session["sub"]).first()
    finally:
        db.close()

    return templates.TemplateResponse(request, "form.html", {
        "agente_nombre_default": corredor.nombre if corredor else "",
        "agente_email_default": corredor.email if corredor else "",
        "agente_telefono_default": corredor.telefono if corredor else "",
    })


# ── Admin: nuevo corredor ─────────────────────────────────────────────────────
@app.post("/admin/corredor/nuevo")
async def crear_corredor(
    request: Request,
    nombre: str = Form(...),
    email: str = Form(...),
    telefono: str = Form(default=""),
    username: str = Form(...),
    password: str = Form(...),
):
    empresa = get_empresa_session(request)
    if not empresa:
        return RedirectResponse("/login", status_code=302)
    db = SessionLocal()
    try:
        exists = db.query(CorredorModel).filter(
            (CorredorModel.username == username) | (CorredorModel.email == email)
        ).first()
        if exists:
            return RedirectResponse("/dashboard?corredor_error=El+usuario+o+email+ya+existe", status_code=302)
        db.add(CorredorModel(
            nombre=nombre, email=email, telefono=telefono,
            username=username, hashed_password=hash_password(password),
        ))
        db.commit()
    except Exception:
        db.rollback()
        return RedirectResponse("/dashboard?corredor_error=Error+al+crear+corredor", status_code=302)
    finally:
        db.close()
    return RedirectResponse("/dashboard", status_code=302)


# ── Form submit (protected) ───────────────────────────────────────────────────
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
    corredor_session = get_corredor_session(request)
    if not corredor_session:
        if get_empresa_session(request):
            return RedirectResponse("/dashboard", status_code=302)
        return RedirectResponse("/login", status_code=302)

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
