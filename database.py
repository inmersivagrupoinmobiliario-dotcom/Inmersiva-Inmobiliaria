from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from urllib.parse import urlparse, urlunparse, quote
import os


def _safe_url(url: str) -> str:
    """Percent-encode special characters in the password part of a DB URL."""
    if not url or not url.startswith(("postgres", "postgresql")):
        return url
    try:
        p = urlparse(url)
        if p.password:
            pw = quote(p.password, safe="")
            host = p.hostname + (f":{p.port}" if p.port else "")
            netloc = f"{p.username}:{pw}@{host}"
            return urlunparse(p._replace(netloc=netloc))
    except Exception:
        pass
    return url


_url = _safe_url(os.getenv("DATABASE_URL", "sqlite:///./inmersiva.db"))
engine = create_engine(_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
