from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Request
from authlib.integrations.starlette_client import OAuth
import os

SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv("SESSION_SECRET", "")
if not SECRET_KEY:
    import secrets as _auth_sec
    SECRET_KEY = _auth_sec.token_hex(32)
    print("[⚠️  SEGURIDAD] SECRET_KEY no configurado — generando clave aleatoria. Los tokens JWT expirarán al reiniciar.")
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(data: dict, hours: int = 8) -> str:
    payload = {**data, "exp": datetime.utcnow() + timedelta(hours=hours)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def get_empresa_session(request: Request) -> Optional[dict]:
    token = request.cookies.get("empresa_token")
    return decode_token(token) if token else None


def get_corredor_session(request: Request) -> Optional[dict]:
    token = request.cookies.get("corredor_token")
    return decode_token(token) if token else None


def get_usuario_session(request: Request) -> Optional[dict]:
    token = request.cookies.get("usuario_token")
    return decode_token(token) if token else None
