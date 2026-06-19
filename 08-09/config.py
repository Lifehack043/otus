"""Конфигурация приложения из переменных окружения."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Настройки приложения."""

    # JWT
    jwt_secret_key: str = "super-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    # Роли
    default_role: str = "user"

    # Админ-сидирование
    admin_password: str = "admin123"
    admin_username: str = "admin"
    admin_email: str = "admin@admin.com"

    # База данных
    database_url: str = "sqlite:///./users.db"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    """Получить кэшированные настройки."""
    return Settings()
