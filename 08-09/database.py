"""Настройка подключения к базе данных."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # Для SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency для получения DB-сессии."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
