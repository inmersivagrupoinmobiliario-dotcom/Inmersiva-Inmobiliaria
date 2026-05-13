from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Request
import os

SECRET_KEY = os.getenv("SECRET_KEY", "inmersiva-secret-2025")
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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
