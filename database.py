from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

_url = os.getenv("DATABASE_URL", "sqlite:///./inmersiva.db")
engine = create_engine(_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
