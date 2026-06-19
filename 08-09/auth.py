"""Модуль аутентификации и авторизации (JWT + RBAC)."""

import logging
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from config import get_settings
from database import get_db
from models import User

logger = logging.getLogger(__name__)

# --- Константы ---
settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Матрица ролей: чем выше индекс — тем больше прав
ROLE_HIERARCHY = {
    "user": 0,
    "admin": 1,
}


# --- Утилиты для паролей ---

def hash_password(password: str) -> str:
    """Хеширует пароль с помощью bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет пароль по хэшу."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


# --- Утилиты для JWT ---

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Создаёт JWT access-token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """Декодирует и проверяет JWT-токен."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as e:
        logger.warning("Ошибка декодирования JWT: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный или просроченный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )


# --- Зависимости FastAPI ---

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency: извлекает текущего пользователя по JWT-токену.
    Поднимает 401 при невалидном/просроченном токене.
    """
    token_data = decode_access_token(token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный или просроченный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username: str = token_data.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректные данные токена",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден или деактивирован",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info("Пользователь %s успешно аутентифицирован", username)
    return user


def require_role(required_role: str):
    """
    Фабрика зависимостей RBAC.
    Проверяет, что роль текущего пользователя >= required_role по иерархии.
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_level = ROLE_HIERARCHY.get(current_user.role, -1)
        required_level = ROLE_HIERARCHY.get(required_role, -1)

        if user_level < required_level:
            logger.warning(
                "Отказ в доступе: пользователь %s (роль=%s) пытается получить доступ, "
                "требуется роль %s",
                current_user.username,
                current_user.role,
                required_role,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Доступ запрещён. Требуется роль '{required_role}' или выше",
            )

        return current_user

    return role_checker


# Готовые зависимости для удобства
require_user = require_role("user")
require_admin = require_role("admin")
