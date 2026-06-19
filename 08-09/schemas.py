"""Pydantic-схемы для запросов и ответов."""

from pydantic import BaseModel, Field


# --- Схемы аутентификации ---

class UserRegister(BaseModel):
    """Запрос на регистрацию."""
    username: str = Field(..., min_length=3, max_length=50, description="Логин")
    email: str = Field(..., description="E-mail")
    password: str = Field(..., min_length=6, max_length=100, description="Пароль")


class UserLogin(BaseModel):
    """Запрос на вход."""
    username: str = Field(..., description="Логин или e-mail")
    password: str = Field(..., description="Пароль")


class TokenResponse(BaseModel):
    """Ответ с JWT-токеном."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # время жизни в секундах


class UserResponse(BaseModel):
    """Профиль пользователя."""
    id: int
    username: str
    email: str
    role: str

    class Config:
        from_attributes = True


# --- Схемы инференса ---

class PatientData(BaseModel):
    """Входные данные пациента."""
    Pregnancies: int = Field(..., ge=0, le=60, description="Количество беременностей")
    Glucose: int = Field(..., ge=0, le=500, description="Уровень глюкозы (мг/дл)")
    BMI: float = Field(..., ge=0, le=100, description="Индекс массы тела")
    Age: int = Field(..., ge=0, le=120, description="Возраст")


class PredictionResponse(BaseModel):
    """Ответ с предсказанием."""
    prediction: int  # 0 — нет диабета, 1 — есть диабет
    probability: float  # вероятность класса 1


# --- Схемы админки ---

class AdminMetrics(BaseModel):
    """Метрики админ-эндпоинта."""
    total_predictions: int
    uptime_seconds: float
    app_version: str
    model_name: str
