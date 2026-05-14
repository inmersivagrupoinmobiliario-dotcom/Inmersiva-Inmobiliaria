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
from models.db_models import (
    Corredor as CorredorModel, PropiedadPublica, UsuarioPublico,
    Contacto, Cita, DocumentoCorredor, PostRRSS,
)

def _run_migrations():
    """Add new columns to existing tables without breaking existing data."""
    from sqlalchemy import text
    db = SessionLocal()
    try:
        is_pg = "postgresql" in str(engine.url)
        migrations = [
            # posts_rrss new columns
            ("posts_rrss", "listing_id", "VARCHAR(36)"),
            ("posts_rrss", "titulo", "VARCHAR(200)"),
            ("posts_rrss", "imagen_url", "VARCHAR(500)"),
            ("posts_rrss", "estado", "VARCHAR(20) DEFAULT 'Pendiente'"),
            ("posts_rrss", "comentario_admin", "TEXT"),
            ("posts_rrss", "redes", "VARCHAR(200)"),
            ("posts_rrss", "upload_post_id", "VARCHAR(100)"),
            ("posts_rrss", "publicado_at", "TIMESTAMP"),
            ("posts_rrss", "caption", "TEXT"),
            # corredores new columns
            ("corredores", "foto_perfil", "VARCHAR(300)"),
            ("corredores", "bio", "TEXT"),
            ("corredores", "instagram", "VARCHAR(100)"),
            ("corredores", "whatsapp", "VARCHAR(30)"),
            ("corredores", "dni", "VARCHAR(20)"),
            ("corredores", "direccion", "VARCHAR(200)"),
            ("corredores", "email_personal", "VARCHAR(100)"),
            # solicitudes_corredor new columns
            ("solicitudes_corredor", "dni", "VARCHAR(20)"),
            ("solicitudes_corredor", "cv_archivo", "VARCHAR(300)"),
        ]
        for table, col, col_type in migrations:
            try:
                if is_pg:
                    db.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_type}"))
                else:
                    db.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                db.commit()
            except Exception:
                db.rollback()  # column already exists on SQLite
        print("[DB] Migraciones aplicadas OK")
    except Exception as e:
        print(f"[ERROR] Migraciones: {e}")
    finally:
        db.close()


def _init_db():
    try:
        Base.metadata.create_all(bind=engine)
        print("[DB] Tablas verificadas/creadas OK")
    except Exception as e:
        import traceback
        print(f"[ERROR] create_all falló: {e}")
        traceback.print_exc()
        return

    # Add new columns to existing tables (non-breaking — IF NOT EXISTS)
    _run_migrations()

    db = SessionLocal()
    try:
        if db.query(CorredorModel).count() == 0:
            db.add(CorredorModel(
                nombre="Corredor Demo", email="corredor1@inmersiva.com",
                username="corredor1", hashed_password=hash_password("corredor123"),
            ))
            db.commit()
            print("[DB] Corredor demo creado: corredor1 / corredor123")
        else:
            print(f"[DB] {db.query(CorredorModel).count()} corredor(es) existentes")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Seed corredor: {e}")
    finally:
        db.close()

_init_db()

EMPRESA_USER = os.getenv("EMPRESA_USER", "admin")
EMPRESA_PASS = os.getenv("EMPRESA_PASS", "Inmersiva2025")
ADMIN_EMAIL  = os.getenv("ADMIN_EMAIL", "inmersivagrupoinmobiliario@gmail.com")

app = FastAPI(title="Inmersiva Grupo Inmobiliario")
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "inmersiva-session-secret-2025"))
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/generated", StaticFiles(directory="generated"), name="generated")
Path("DOC").mkdir(exist_ok=True)
app.mount("/doc", StaticFiles(directory="DOC"), name="doc")
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


def _publicar_en_portal(db, listing_id: str, corredor_id):
    """Crea o actualiza PropiedadPublica cuando un post es aprobado y publicado."""
    try:
        listing = load_listing(listing_id)
    except Exception:
        return
    existing = db.query(PropiedadPublica).filter(PropiedadPublica.listing_id == listing_id).first()
    if existing:
        existing.publicado = True
        db.commit()
        return
    corredor_obj = db.query(CorredorModel).filter(CorredorModel.id == corredor_id).first() if corredor_id else None
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
        descripcion=listing.descripcion_generada or getattr(listing, "descripcion_agente", ""),
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
    tour: Opt[str] = None,
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
        if tour:
            q = q.filter(PropiedadPublica.tour_360_url != "")
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

    # Check if public user is also a registered corredor (for dual-access option)
    usuario_es_corredor = False
    if usuario and not corredor and not empresa:
        db2 = SessionLocal()
        try:
            _cor = db2.query(CorredorModel).filter(
                CorredorModel.email == usuario.get("sub", ""),
                CorredorModel.activo == True,
            ).first()
            usuario_es_corredor = _cor is not None
        finally:
            db2.close()

    portal_error = request.query_params.get("error", "")
    return templates.TemplateResponse(request, "portal.html", {
        "propiedades": propiedades,
        "filtros": {"tipo": tipo or "", "operacion": operacion or "", "ciudad": ciudad or "", "tour": tour or ""},
        "user": user,
        "usuario": usuario,
        "usuario_es_corredor": usuario_es_corredor,
        "portal_error": portal_error,
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
    # Legacy route — kept for backward compat
    if username == EMPRESA_USER and password == EMPRESA_PASS:
        token = create_token({"sub": username, "role": "empresa"})
        resp = RedirectResponse("/dashboard", status_code=302)
        resp.set_cookie("empresa_token", token, httponly=True, samesite="lax")
        return resp
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
    return templates.TemplateResponse(request, "login.html", {"error": "Usuario o contraseña incorrectos"}, status_code=401)


@app.post("/login/smart")
async def login_smart(request: Request, email: str = Form(...), password: str = Form(...)):
    """Unified login — detects role by email and routes accordingly."""
    email = email.strip().lower()

    # 1. Admin
    if email == ADMIN_EMAIL.lower():
        if password == EMPRESA_PASS:
            token = create_token({"sub": EMPRESA_USER, "role": "empresa"})
            resp = RedirectResponse("/dashboard", status_code=302)
            resp.set_cookie("empresa_token", token, httponly=True, samesite="lax")
            return resp
        return templates.TemplateResponse(request, "login.html", {"error": "Contraseña incorrecta."}, status_code=401)

    db = SessionLocal()
    try:
        # 2. Corredor (by email)
        corredor = db.query(CorredorModel).filter(
            CorredorModel.email == email, CorredorModel.activo == True
        ).first()
        if corredor:
            if corredor.hashed_password and verify_password(password, corredor.hashed_password):
                token = create_token({"sub": corredor.username, "email": corredor.email, "nombre": corredor.nombre})
                resp = RedirectResponse("/corredor/dashboard", status_code=302)
                resp.set_cookie("corredor_token", token, httponly=True, samesite="lax")
                return resp
            return templates.TemplateResponse(request, "login.html", {"error": "Contraseña incorrecta."}, status_code=401)

        # 3. Usuario público
        usuario = db.query(UsuarioPublico).filter(
            UsuarioPublico.email == email, UsuarioPublico.activo == True
        ).first()
        if usuario:
            if usuario.hashed_password and verify_password(password, usuario.hashed_password):
                token = create_token({"sub": email, "nombre": usuario.nombre, "role": "usuario"})
                resp = RedirectResponse("/", status_code=302)
                resp.set_cookie("usuario_token", token, httponly=True, samesite="lax")
                return resp
            return templates.TemplateResponse(request, "login.html", {"error": "Contraseña incorrecta."}, status_code=401)
    finally:
        db.close()

    # Not found
    return templates.TemplateResponse(request, "login.html",
        {"error": "No encontramos una cuenta con ese email.", "show_register": True}, status_code=401)


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


@app.post("/usuario/acceder-como-corredor")
async def acceder_como_corredor(request: Request, password: str = Form(...)):
    """Let a public user switch to their corredor session using just their password."""
    usuario = get_usuario_session(request)
    if not usuario:
        return RedirectResponse("/login", status_code=302)
    email = usuario.get("sub", "")
    db = SessionLocal()
    try:
        corredor = db.query(CorredorModel).filter(
            CorredorModel.email == email, CorredorModel.activo == True
        ).first()
        if corredor and corredor.hashed_password and verify_password(password, corredor.hashed_password):
            token = create_token({"sub": corredor.username, "email": corredor.email, "nombre": corredor.nombre})
            resp = RedirectResponse("/corredor/dashboard", status_code=302)
            resp.set_cookie("corredor_token", token, httponly=True, samesite="lax")
            return resp
    finally:
        db.close()
    return RedirectResponse("/?error=corredor_pass", status_code=302)


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

    # Corredores NUNCA acceden vía Google — solo con email corporativo + contraseña
    company_domain = os.getenv("COMPANY_EMAIL_DOMAIN", "inmersiva.com")
    if email.endswith(f"@{company_domain}"):
        return templates.TemplateResponse(
            request, "login.html",
            {"error": "Los corredores deben iniciar sesión con su email corporativo y contraseña, no con Google."},
            status_code=400,
        )

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

    db2 = SessionLocal()
    try:
        from models.db_models import SolicitudCorredor
        posts_pendientes = db2.query(PostRRSS).filter(
            PostRRSS.estado == "Pendiente",
            PostRRSS.listing_id != None,
        ).order_by(PostRRSS.created_at.asc()).all()
        solicitudes = db2.query(SolicitudCorredor).order_by(
            SolicitudCorredor.created_at.desc()
        ).limit(50).all()
        actividad_corredores = []
        for c in corredores:
            fichas_c = list_fichas(c.email)
            posts_c = db2.query(PostRRSS).filter(
                PostRRSS.corredor_id == c.id,
                PostRRSS.listing_id != None,
            ).all()
            actividad_corredores.append({
                "corredor": c,
                "fichas": len(fichas_c),
                "posts_pendientes": sum(1 for p in posts_c if p.estado == "Pendiente"),
                "posts_publicados": sum(1 for p in posts_c if p.estado == "Publicado"),
            })
    finally:
        db2.close()

    fichas = list_fichas()
    s = fichas_stats(fichas)
    ok_msg = request.query_params.get("ok", "")
    error_msg = request.query_params.get("error", "")
    return templates.TemplateResponse(request, "dashboard_empresa.html", {
        "empresa_user": empresa["sub"],
        "corredor": corredor_obj,
        "fichas": fichas,
        "corredores": corredores,
        "corredor_error": corredor_error,
        "ok_msg": ok_msg,
        "error_msg": error_msg,
        "posts_pendientes": posts_pendientes,
        "solicitudes": solicitudes,
        "actividad_corredores": actividad_corredores,
        "stats": {
            "total_fichas": s["total"],
            "fichas_mes": s["fichas_mes"],
            "corredores_activos": corredores_activos,
            "pdfs_generados": s["pdfs"],
            "posts_pendientes": len(posts_pendientes),
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


def _corredor_or_redirect(request: Request):
    """Returns (corredor_obj, None) or (None, RedirectResponse)."""
    session = get_corredor_session(request)
    if not session:
        if get_empresa_session(request):
            return None, RedirectResponse("/dashboard", status_code=302)
        return None, RedirectResponse("/login", status_code=302)
    db = SessionLocal()
    try:
        corredor = db.query(CorredorModel).filter(CorredorModel.username == session["sub"]).first()
    finally:
        db.close()
    if not corredor:
        resp = RedirectResponse("/login", status_code=302)
        resp.delete_cookie("corredor_token")
        return None, resp
    return corredor, None


_DOC_ICONS = {
    ".pdf": "📄", ".docx": "📝", ".doc": "📝",
    ".xlsx": "📊", ".xls": "📊", ".png": "🖼", ".jpg": "🖼",
}
_DOC_TIPO = {
    "contrato": "Contrato", "autorizacion": "Autorización",
    "ficha": "Ficha", "guion": "Guión", "protocolo": "Protocolo",
}

def _doc_empresa_list():
    doc_dir = Path("DOC")
    items = []
    for f in sorted(doc_dir.iterdir()):
        if f.is_file() and not f.name.startswith("."):
            ext = f.suffix.lower()
            nombre = f.stem.replace("_", " ").replace("inmersiva", "").strip().title()
            tipo = next((v for k, v in _DOC_TIPO.items() if k in f.name.lower()), "Documento")
            items.append({
                "nombre": nombre,
                "tipo": tipo,
                "ext": ext.lstrip(".").upper(),
                "icono": _DOC_ICONS.get(ext, "📎"),
                "url": f"/doc/{f.name}",
                "size_kb": round(f.stat().st_size / 1024),
            })
    return items


@app.get("/corredor/dashboard", response_class=HTMLResponse)
async def dashboard_corredor(request: Request, seccion: str = "resumen"):
    corredor, redir = _corredor_or_redirect(request)
    if redir:
        return redir

    db = SessionLocal()
    try:
        fichas = list_fichas(corredor_email=corredor.email)
        s = fichas_stats(fichas)
        contactos = db.query(Contacto).filter(Contacto.corredor_id == corredor.id)\
                      .order_by(Contacto.updated_at.desc()).all()
        citas = db.query(Cita).filter(Cita.corredor_id == corredor.id)\
                  .order_by(Cita.fecha.asc()).all()
        documentos = db.query(DocumentoCorredor).filter(DocumentoCorredor.corredor_id == corredor.id)\
                       .order_by(DocumentoCorredor.created_at.desc()).all()
        posts = db.query(PostRRSS).filter(PostRRSS.corredor_id == corredor.id)\
                  .order_by(PostRRSS.fecha_publicacion.desc()).all()
        posts_rrss = db.query(PostRRSS).filter(
            PostRRSS.corredor_id == corredor.id,
            PostRRSS.listing_id != None,
        ).order_by(PostRRSS.created_at.desc()).limit(50).all()
        contactos_map = {c.id: c for c in contactos}
    finally:
        db.close()

    docs_empresa = _doc_empresa_list()

    pipeline = {
        "Nuevo":        [c for c in contactos if c.estado == "Nuevo"],
        "Contactado":   [c for c in contactos if c.estado == "Contactado"],
        "Negociacion":  [c for c in contactos if c.estado == "Negociacion"],
        "Ganado":       [c for c in contactos if c.estado == "Ganado"],
        "Perdido":      [c for c in contactos if c.estado == "Perdido"],
    }

    return templates.TemplateResponse(request, "dashboard_corredor.html", {
        "corredor": corredor,
        "fichas": fichas,
        "seccion": seccion,
        "stats": {
            "mis_fichas": s["total"],
            "fichas_mes": s["fichas_mes"],
            "pdfs": s["pdfs"],
            "contactos": len(contactos),
            "citas_pendientes": sum(1 for c in citas if c.estado == "Pendiente"),
        },
        "contactos": contactos,
        "pipeline": pipeline,
        "citas": citas,
        "documentos": documentos,
        "docs_empresa": docs_empresa,
        "posts": posts,
        "posts_rrss": posts_rrss,
        "contactos_map": contactos_map,
        "ok_msg": request.query_params.get("ok", ""),
        "error_msg": request.query_params.get("error", ""),
    })


# ── CRM: Contactos ────────────────────────────────────────────────────────────
@app.post("/corredor/contacto/nuevo")
async def nuevo_contacto(
    request: Request,
    nombre: str = Form(...),
    email: str = Form(default=""),
    telefono: str = Form(default=""),
    origen: str = Form(default="Web"),
    interes: str = Form(default=""),
    notas: str = Form(default=""),
):
    corredor, redir = _corredor_or_redirect(request)
    if redir:
        return redir
    db = SessionLocal()
    try:
        c = Contacto(corredor_id=corredor.id, nombre=nombre, email=email,
                     telefono=telefono, origen=origen, interes=interes, notas=notas)
        db.add(c)
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/corredor/dashboard?seccion=contactos", status_code=302)


@app.post("/corredor/contacto/{cid}/estado")
async def actualizar_estado_contacto(request: Request, cid: int, estado: str = Form(...)):
    corredor, redir = _corredor_or_redirect(request)
    if redir:
        return redir
    db = SessionLocal()
    try:
        c = db.query(Contacto).filter(Contacto.id == cid, Contacto.corredor_id == corredor.id).first()
        if c:
            c.estado = estado
            c.updated_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()
    return RedirectResponse("/corredor/dashboard?seccion=pipeline", status_code=302)


@app.post("/corredor/contacto/{cid}/eliminar")
async def eliminar_contacto(request: Request, cid: int):
    corredor, redir = _corredor_or_redirect(request)
    if redir:
        return redir
    db = SessionLocal()
    try:
        c = db.query(Contacto).filter(Contacto.id == cid, Contacto.corredor_id == corredor.id).first()
        if c:
            db.delete(c)
            db.commit()
    finally:
        db.close()
    return RedirectResponse("/corredor/dashboard?seccion=contactos", status_code=302)


# ── CRM: Citas ────────────────────────────────────────────────────────────────
@app.post("/corredor/cita/nueva")
async def nueva_cita(
    request: Request,
    titulo: str = Form(...),
    fecha: str = Form(...),
    lugar: str = Form(default=""),
    descripcion: str = Form(default=""),
    contacto_id: str = Form(default=""),
):
    corredor, redir = _corredor_or_redirect(request)
    if redir:
        return redir
    db = SessionLocal()
    try:
        cid = int(contacto_id) if contacto_id.strip() else None
        fecha_dt = datetime.fromisoformat(fecha)
        cita = Cita(corredor_id=corredor.id, contacto_id=cid, titulo=titulo,
                    fecha=fecha_dt, lugar=lugar, descripcion=descripcion)
        db.add(cita)
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/corredor/dashboard?seccion=agenda", status_code=302)


@app.post("/corredor/cita/{cid}/estado")
async def actualizar_cita(request: Request, cid: int, estado: str = Form(...)):
    corredor, redir = _corredor_or_redirect(request)
    if redir:
        return redir
    db = SessionLocal()
    try:
        cita = db.query(Cita).filter(Cita.id == cid, Cita.corredor_id == corredor.id).first()
        if cita:
            cita.estado = estado
            db.commit()
    finally:
        db.close()
    return RedirectResponse("/corredor/dashboard?seccion=agenda", status_code=302)


@app.post("/corredor/cita/{cid}/eliminar")
async def eliminar_cita(request: Request, cid: int):
    corredor, redir = _corredor_or_redirect(request)
    if redir:
        return redir
    db = SessionLocal()
    try:
        cita = db.query(Cita).filter(Cita.id == cid, Cita.corredor_id == corredor.id).first()
        if cita:
            db.delete(cita)
            db.commit()
    finally:
        db.close()
    return RedirectResponse("/corredor/dashboard?seccion=agenda", status_code=302)


# ── CRM: Documentos ───────────────────────────────────────────────────────────
@app.post("/corredor/documento/subir")
async def subir_documento(
    request: Request,
    nombre: str = Form(...),
    tipo: str = Form(default="Otro"),
    notas: str = Form(default=""),
    archivo: UploadFile = File(default=None),
):
    corredor, redir = _corredor_or_redirect(request)
    if redir:
        return redir
    archivo_nombre = ""
    if archivo and archivo.filename:
        ext = Path(archivo.filename).suffix
        archivo_nombre = f"doc_{uuid.uuid4().hex}{ext}"
        dest = Path("uploads") / archivo_nombre
        dest.parent.mkdir(exist_ok=True)
        with open(dest, "wb") as f:
            shutil.copyfileobj(archivo.file, f)
    db = SessionLocal()
    try:
        doc = DocumentoCorredor(corredor_id=corredor.id, nombre=nombre,
                                tipo=tipo, archivo=archivo_nombre, notas=notas)
        db.add(doc)
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/corredor/dashboard?seccion=documentos", status_code=302)


@app.post("/corredor/documento/{did}/eliminar")
async def eliminar_documento(request: Request, did: int):
    corredor, redir = _corredor_or_redirect(request)
    if redir:
        return redir
    db = SessionLocal()
    try:
        doc = db.query(DocumentoCorredor).filter(
            DocumentoCorredor.id == did, DocumentoCorredor.corredor_id == corredor.id
        ).first()
        if doc:
            if doc.archivo:
                try:
                    Path("uploads", doc.archivo).unlink(missing_ok=True)
                except Exception:
                    pass
            db.delete(doc)
            db.commit()
    finally:
        db.close()
    return RedirectResponse("/corredor/dashboard?seccion=documentos", status_code=302)


# ── CRM: Posts RRSS ───────────────────────────────────────────────────────────
@app.post("/corredor/post/nuevo")
async def nuevo_post(
    request: Request,
    red: str = Form(...),
    contenido: str = Form(default=""),
    url: str = Form(default=""),
    fecha_publicacion: str = Form(default=""),
):
    corredor, redir = _corredor_or_redirect(request)
    if redir:
        return redir
    db = SessionLocal()
    try:
        fecha_dt = datetime.fromisoformat(fecha_publicacion) if fecha_publicacion else datetime.utcnow()
        post = PostRRSS(corredor_id=corredor.id, red=red, contenido=contenido,
                        url=url, fecha_publicacion=fecha_dt)
        db.add(post)
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/corredor/dashboard?seccion=rrss", status_code=302)


@app.post("/corredor/post/{pid}/eliminar")
async def eliminar_post(request: Request, pid: int):
    corredor, redir = _corredor_or_redirect(request)
    if redir:
        return redir
    db = SessionLocal()
    try:
        post = db.query(PostRRSS).filter(
            PostRRSS.id == pid, PostRRSS.corredor_id == corredor.id
        ).first()
        if post:
            db.delete(post)
            db.commit()
    finally:
        db.close()
    return RedirectResponse("/corredor/dashboard?seccion=rrss", status_code=302)


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
    password: str = Form(...),
    dni: str = Form(default=""),
    direccion: str = Form(default=""),
    email_personal: str = Form(default=""),
):
    username = email.split("@")[0]
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
            dni=dni or None, direccion=direccion or None,
            email_personal=email_personal or None,
        ))
        db.commit()
    except Exception as e:
        db.rollback()
        import traceback, urllib.parse
        traceback.print_exc()
        msg = urllib.parse.quote(str(e)[:200])
        return RedirectResponse(f"/dashboard?corredor_error={msg}", status_code=302)
    finally:
        db.close()
    # Cloudflare email routing + envío de credenciales si se proporcionó email personal
    if email_personal:
        from services.email_service import setup_cloudflare_email_routing, enviar_credenciales_corredor
        setup_cloudflare_email_routing(email, email_personal)
        enviar_credenciales_corredor(nombre, email, email_personal, username, password)
    return RedirectResponse("/dashboard?ok=Corredor+creado+exitosamente", status_code=302)


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
    listing.nombre_borrador = f"Generado {listing.tipo} · {listing.ciudad} · {datetime.now().strftime('%d/%m %H:%M')}"
    save_listing(listing)

    return RedirectResponse(f"/resultados/{listing.id}", status_code=302)


@app.get("/resultados/{listing_id}", response_class=HTMLResponse)
async def ver_resultados(request: Request, listing_id: str):
    try:
        listing = load_listing(listing_id)
    except Exception:
        return RedirectResponse("/", status_code=302)
    ok = request.query_params.get("ok", "")
    return templates.TemplateResponse(request, "results.html", {"listing": listing, "ok": ok})


@app.post("/resultados/{listing_id}/editar")
async def editar_resultados(
    request: Request,
    listing_id: str,
    descripcion: str = Form(...),
    copy_instagram: str = Form(...),
):
    try:
        listing = load_listing(listing_id)
    except Exception:
        return RedirectResponse("/", status_code=302)
    listing.descripcion_generada = descripcion
    listing.copy_instagram = copy_instagram
    save_listing(listing)
    return RedirectResponse(f"/resultados/{listing_id}?ok=1", status_code=302)


@app.post("/api/mejorar-texto")
async def mejorar_texto(
    request: Request,
    listing_id: str = Form(...),
    campo: str = Form(...),
    instruccion: str = Form(default=""),
):
    try:
        listing = load_listing(listing_id)
    except Exception:
        return JSONResponse({"error": "Ficha no encontrada"}, status_code=404)
    from services.ai_service import generar_contenido
    texto_actual = listing.descripcion_generada if campo == "descripcion" else listing.copy_instagram
    prompt_extra = f"\n\nInstrucción adicional: {instruccion}" if instruccion.strip() else ""
    try:
        if campo == "descripcion":
            desc, _ = generar_contenido(listing, hint=f"Reescribe y mejora esta descripción:{prompt_extra}\n\n{texto_actual}")
            return JSONResponse({"texto": desc})
        else:
            _, copy_ig = generar_contenido(listing, hint=f"Reescribe y mejora este copy de Instagram:{prompt_extra}\n\n{texto_actual}")
            return JSONResponse({"texto": copy_ig})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


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


@app.get("/imagen-vertical/{listing_id}")
async def descargar_imagen_vertical(listing_id: str):
    listing = load_listing(listing_id)
    img_path = GENERATED / "images" / f"{listing_id}_vertical.jpg"
    img_path.parent.mkdir(parents=True, exist_ok=True)
    portada_path = (UPLOADS / listing.foto_portada) if listing.foto_portada else None
    from services.image_service import generar_imagen_vertical
    generar_imagen_vertical(listing, str(portada_path) if portada_path and portada_path.exists() else None, str(img_path))
    filename = f"inmersiva_rrss_{listing.tipo.lower()}_{listing.ciudad.lower()}.jpg"
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


# ── Registro corredor (auto-registro público) ──────────────────────────────────
@app.get("/corredor/registro", response_class=HTMLResponse)
async def registro_corredor_page(request: Request):
    if get_corredor_session(request):
        return RedirectResponse("/corredor/dashboard", status_code=302)
    return templates.TemplateResponse(request, "registro_corredor.html",
                                      {"error": "", "success": False})


@app.post("/corredor/registro")
async def registro_corredor_submit(
    request: Request,
    nombre: str = Form(...),
    email: str = Form(...),
    telefono: str = Form(default=""),
    dni: str = Form(default=""),
    mensaje: str = Form(default=""),
    cv: UploadFile = File(default=None),
):
    from models.db_models import SolicitudCorredor
    db = SessionLocal()
    cv_path = None
    try:
        existe_sol = db.query(SolicitudCorredor).filter(SolicitudCorredor.email == email).first()
        existe_corredor = db.query(CorredorModel).filter(CorredorModel.email == email).first()
        if existe_sol or existe_corredor:
            return templates.TemplateResponse(
                request, "registro_corredor.html",
                {"error": "Ya existe una solicitud o cuenta con ese email.", "success": False}
            )
        if cv and cv.filename:
            ext = Path(cv.filename).suffix.lower()
            if ext not in (".pdf", ".doc", ".docx"):
                return templates.TemplateResponse(
                    request, "registro_corredor.html",
                    {"error": "El CV debe ser PDF, DOC o DOCX.", "success": False}
                )
            cv_name = f"{uuid.uuid4()}{ext}"
            cv_dest = Path("uploads/cvs") / cv_name
            with open(cv_dest, "wb") as f:
                f.write(await cv.read())
            cv_path = str(cv_dest)
        db.add(SolicitudCorredor(
            nombre=nombre, email=email, telefono=telefono,
            dni=dni or None, mensaje=mensaje, cv_archivo=cv_path,
        ))
        db.commit()
    except Exception as e:
        db.rollback()
        return templates.TemplateResponse(
            request, "registro_corredor.html",
            {"error": f"Error al enviar solicitud: {e}", "success": False}
        )
    finally:
        db.close()
    return templates.TemplateResponse(request, "registro_corredor.html",
                                      {"error": "", "success": True})


# ── Admin: aprobar / rechazar solicitud de corredor ───────────────────────────
@app.post("/admin/solicitud/{solicitud_id}/aprobar")
async def aprobar_solicitud_corredor(request: Request, solicitud_id: int):
    if not get_empresa_session(request):
        return RedirectResponse("/login", status_code=302)
    import unicodedata, secrets, string
    from models.db_models import SolicitudCorredor
    from services.email_service import setup_cloudflare_email_routing, enviar_credenciales_corredor

    company_domain = os.getenv("COMPANY_EMAIL_DOMAIN", "inmersiva.com")

    def normalizar(texto: str) -> str:
        sin_tildes = unicodedata.normalize("NFD", texto)
        sin_tildes = "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")
        return sin_tildes.lower().replace(" ", ".")

    db = SessionLocal()
    try:
        sol = db.query(SolicitudCorredor).filter(SolicitudCorredor.id == solicitud_id).first()
        if not sol:
            return RedirectResponse("/dashboard?error=Solicitud+no+encontrada", status_code=302)
        if sol.estado == "Aprobado":
            return RedirectResponse("/dashboard?error=Esta+solicitud+ya+fue+aprobada", status_code=302)

        # Generar email corporativo: primer_nombre.apellido@inmersiva.com
        partes = sol.nombre.strip().split()
        slug = normalizar(f"{partes[0]}.{partes[-1]}") if len(partes) > 1 else normalizar(partes[0])
        email_corp = f"{slug}@{company_domain}"
        username = slug

        base_slug = slug
        counter = 1
        while db.query(CorredorModel).filter(
            (CorredorModel.email == email_corp) | (CorredorModel.username == username)
        ).first():
            username = f"{base_slug}{counter}"
            email_corp = f"{username}@{company_domain}"
            counter += 1

        password = "Inm" + "".join(secrets.choice(string.digits) for _ in range(4)) + secrets.choice(string.ascii_uppercase)

        # Guardar valores antes de cerrar la sesión
        sol_nombre = sol.nombre
        sol_email  = sol.email
        sol_telefono = sol.telefono or ""
        sol_dni    = sol.dni

        db.add(CorredorModel(
            nombre=sol_nombre, email=email_corp, telefono=sol_telefono,
            username=username, hashed_password=hash_password(password),
            dni=sol_dni, email_personal=sol_email,
        ))
        sol.estado = "Aprobado"
        db.commit()
    except Exception as e:
        db.rollback()
        import traceback, urllib.parse
        traceback.print_exc()
        msg = urllib.parse.quote(str(e)[:200])
        return RedirectResponse(f"/dashboard?error={msg}", status_code=302)
    finally:
        db.close()

    setup_cloudflare_email_routing(email_corp, sol_email)
    enviar_credenciales_corredor(sol_nombre, email_corp, sol_email, username, password)
    import urllib.parse
    msg = urllib.parse.quote(f"Corredor aprobado: {email_corp} · credenciales enviadas a {sol_email}")
    return RedirectResponse(f"/dashboard?ok={msg}", status_code=302)


@app.post("/admin/solicitud/{solicitud_id}/rechazar")
async def rechazar_solicitud_corredor(request: Request, solicitud_id: int):
    if not get_empresa_session(request):
        return RedirectResponse("/login", status_code=302)
    from models.db_models import SolicitudCorredor
    db = SessionLocal()
    try:
        sol = db.query(SolicitudCorredor).filter(SolicitudCorredor.id == solicitud_id).first()
        if sol:
            sol.estado = "Rechazado"
            db.commit()
    finally:
        db.close()
    return RedirectResponse("/dashboard", status_code=302)


@app.get("/admin/solicitud/{solicitud_id}/cv")
async def descargar_cv_solicitud(request: Request, solicitud_id: int):
    if not get_empresa_session(request):
        return RedirectResponse("/login", status_code=302)
    from models.db_models import SolicitudCorredor
    db = SessionLocal()
    try:
        sol = db.query(SolicitudCorredor).filter(SolicitudCorredor.id == solicitud_id).first()
        if not sol or not sol.cv_archivo or not Path(sol.cv_archivo).exists():
            return HTMLResponse("<p>CV no disponible</p>", status_code=404)
        return FileResponse(sol.cv_archivo, filename=f"CV_{sol.nombre.replace(' ','_')}{Path(sol.cv_archivo).suffix}")
    finally:
        db.close()


@app.get("/admin/corredor/{corredor_id}", response_class=HTMLResponse)
async def admin_corredor_detalle(request: Request, corredor_id: int):
    if not get_empresa_session(request):
        return RedirectResponse("/login", status_code=302)
    db = SessionLocal()
    try:
        corredor = db.query(CorredorModel).filter(CorredorModel.id == corredor_id).first()
        if not corredor:
            return RedirectResponse("/dashboard?error=Corredor+no+encontrado", status_code=302)
        fichas = list_fichas(corredor.email)
        contactos = db.query(Contacto).filter(Contacto.corredor_id == corredor_id)\
                      .order_by(Contacto.updated_at.desc()).limit(20).all()
        citas = db.query(Cita).filter(Cita.corredor_id == corredor_id)\
                  .order_by(Cita.fecha.desc()).limit(20).all()
        posts = db.query(PostRRSS).filter(PostRRSS.corredor_id == corredor_id)\
                  .order_by(PostRRSS.created_at.desc()).limit(20).all()
        return templates.TemplateResponse(request, "admin_corredor_detalle.html", {
            "corredor": corredor,
            "fichas": fichas,
            "contactos": contactos,
            "citas": citas,
            "posts": posts,
        })
    finally:
        db.close()


@app.post("/admin/corredor/{corredor_id}/eliminar")
async def eliminar_corredor(request: Request, corredor_id: int, admin_password: str = Form(...)):
    if not get_empresa_session(request):
        return RedirectResponse("/login", status_code=302)
    if admin_password != EMPRESA_PASS:
        return RedirectResponse("/dashboard?error=Contraseña+de+administrador+incorrecta", status_code=302)
    db = SessionLocal()
    try:
        corredor = db.query(CorredorModel).filter(CorredorModel.id == corredor_id).first()
        if not corredor:
            return RedirectResponse("/dashboard?error=Corredor+no+encontrado", status_code=302)
        nombre = corredor.nombre
        db.delete(corredor)
        db.commit()
    except Exception as e:
        db.rollback()
        import urllib.parse
        return RedirectResponse(f"/dashboard?error={urllib.parse.quote(str(e)[:150])}", status_code=302)
    finally:
        db.close()
    import urllib.parse
    return RedirectResponse(f"/dashboard?ok={urllib.parse.quote(f'Corredor {nombre} eliminado')}", status_code=302)


# ── Solicitar publicación en RRSS (corredor) ──────────────────────────────────
@app.post("/corredor/solicitar-publicacion/{listing_id}")
async def solicitar_publicacion(
    request: Request,
    listing_id: str,
    redes: List[str] = Form(default=["instagram", "facebook", "whatsapp", "tiktok"]),
):
    corredor_session = get_corredor_session(request)
    empresa_session = get_empresa_session(request)
    if not corredor_session and not empresa_session:
        return RedirectResponse("/login", status_code=302)

    try:
        listing = load_listing(listing_id)
    except Exception:
        return RedirectResponse("/corredor/dashboard?error=Ficha+no+encontrada", status_code=302)

    img_path = GENERATED / "images" / f"{listing_id}_vertical.jpg"
    if not img_path.exists():
        img_path.parent.mkdir(parents=True, exist_ok=True)
        portada_path = (UPLOADS / listing.foto_portada) if listing.foto_portada else None
        from services.image_service import generar_imagen_vertical
        generar_imagen_vertical(
            listing,
            str(portada_path) if portada_path and portada_path.exists() else None,
            str(img_path),
        )

    moneda = getattr(listing, "moneda", "PEN")
    sym = "S/." if moneda == "PEN" else "USD"
    caption = (
        f"{listing.tipo} en {listing.operacion} | {sym} {listing.precio:,}\n"
        f"📍 {listing.ciudad}, {listing.estado}\n\n"
        f"{listing.copy_instagram or listing.descripcion_generada or ''}\n\n"
        f"#InmersivaInmobiliaria #BienesRaices #Inmuebles"
    )

    db = SessionLocal()
    try:
        corredor_obj = None
        if corredor_session:
            corredor_obj = db.query(CorredorModel).filter(
                CorredorModel.username == corredor_session["sub"]
            ).first()
        existing = db.query(PostRRSS).filter(
            PostRRSS.listing_id == listing_id,
            PostRRSS.estado.in_(["Pendiente", "Aprobado", "Publicado"]),
        ).first()
        if existing:
            return RedirectResponse(
                "/corredor/dashboard?error=Ya+existe+solicitud+para+esta+ficha",
                status_code=302,
            )
        post = PostRRSS(
            corredor_id=corredor_obj.id if corredor_obj else 1,
            red=",".join(redes),
            contenido=caption,
            listing_id=listing_id,
            titulo=f"{listing.tipo} en {listing.operacion} — {listing.ciudad}",
            imagen_url=str(img_path),
            estado="Pendiente",
            redes=",".join(redes),
            caption=caption,
        )
        db.add(post)
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/corredor/dashboard?seccion=publicaciones&ok=Solicitud+enviada+al+admin", status_code=302)


# ── Admin: aprobar / rechazar / reintentar post RRSS ──────────────────────────
@app.post("/admin/post/{post_id}/aprobar")
async def aprobar_post(
    request: Request,
    post_id: int,
    comentario: str = Form(default=""),
):
    if not get_empresa_session(request):
        return RedirectResponse("/login", status_code=302)
    db = SessionLocal()
    try:
        post = db.query(PostRRSS).filter(PostRRSS.id == post_id).first()
        if not post:
            return RedirectResponse("/dashboard?error=Post+no+encontrado", status_code=302)
        post.estado = "Aprobado"
        post.comentario_admin = comentario
        db.commit()

        from services.uploadpost_service import publicar_en_redes, UploadPostError
        redes = post.redes_list if post.redes_list else ["instagram"]
        try:
            resultado = publicar_en_redes(post.caption or post.contenido or "", post.imagen_url or "", redes)
            post.upload_post_id = resultado.get("post_id", "")
            post.estado = "Publicado"
            post.publicado_at = datetime.utcnow()
            db.commit()
            if post.listing_id:
                _publicar_en_portal(db, post.listing_id, post.corredor_id)
        except Exception as e:
            print(f"[UploadPost ERROR] post_id={post_id}: {e}")
    finally:
        db.close()
    return RedirectResponse("/dashboard?seccion=aprobacion&ok=Post+aprobado", status_code=302)


@app.post("/admin/post/{post_id}/rechazar")
async def rechazar_post(
    request: Request,
    post_id: int,
    comentario: str = Form(...),
):
    if not get_empresa_session(request):
        return RedirectResponse("/login", status_code=302)
    db = SessionLocal()
    try:
        post = db.query(PostRRSS).filter(PostRRSS.id == post_id).first()
        if post:
            post.estado = "Rechazado"
            post.comentario_admin = comentario
            db.commit()
    finally:
        db.close()
    return RedirectResponse("/dashboard?seccion=aprobacion", status_code=302)


@app.post("/admin/post/{post_id}/reintentar")
async def reintentar_post(request: Request, post_id: int):
    if not get_empresa_session(request):
        return RedirectResponse("/login", status_code=302)
    db = SessionLocal()
    try:
        post = db.query(PostRRSS).filter(PostRRSS.id == post_id).first()
        if not post or post.estado != "Aprobado":
            return RedirectResponse("/dashboard?error=Post+no+válido+para+reintento", status_code=302)
        from services.uploadpost_service import publicar_en_redes, UploadPostError
        redes = post.redes_list if post.redes_list else ["instagram"]
        try:
            resultado = publicar_en_redes(post.caption or post.contenido or "", post.imagen_url or "", redes)
            post.upload_post_id = resultado.get("post_id", "")
            post.estado = "Publicado"
            post.publicado_at = datetime.utcnow()
            db.commit()
            if post.listing_id:
                _publicar_en_portal(db, post.listing_id, post.corredor_id)
        except Exception as e:
            return RedirectResponse(f"/dashboard?error=UploadPost+error", status_code=302)
    finally:
        db.close()
    return RedirectResponse("/dashboard?ok=Post+publicado+exitosamente", status_code=302)


# ── Perfil corredor ────────────────────────────────────────────────────────────
@app.get("/corredor/perfil", response_class=HTMLResponse)
async def perfil_corredor_page(request: Request):
    corredor, redir = _corredor_or_redirect(request)
    if redir:
        return redir
    return RedirectResponse("/corredor/dashboard?seccion=perfil", status_code=302)


@app.post("/corredor/perfil")
async def actualizar_perfil(
    request: Request,
    bio: str = Form(default=""),
    instagram: str = Form(default=""),
    whatsapp: str = Form(default=""),
    foto_perfil: UploadFile = File(default=None),
):
    corredor, redir = _corredor_or_redirect(request)
    if redir:
        return redir
    db = SessionLocal()
    try:
        corredor_obj = db.query(CorredorModel).filter(CorredorModel.id == corredor.id).first()
        if corredor_obj:
            corredor_obj.bio = bio
            corredor_obj.instagram = instagram
            corredor_obj.whatsapp = whatsapp
            if foto_perfil and foto_perfil.filename:
                ext = Path(foto_perfil.filename).suffix
                fname = f"perfil_{corredor_obj.id}{ext}"
                dest = UPLOADS / fname
                save_upload(foto_perfil, dest)
                corredor_obj.foto_perfil = fname
            db.commit()
    finally:
        db.close()
    return RedirectResponse("/corredor/dashboard?seccion=perfil&ok=Perfil+actualizado", status_code=302)
