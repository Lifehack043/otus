"""FastAPI-сервис для инференса модели диагностики диабета с JWT-аутентификацией и RBAC."""

import logging
import time
from contextlib import asynccontextmanager
from datetime import timedelta

import numpy as np
import onnxruntime as ort
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2
from sqlalchemy.orm import Session

from config import get_settings
from database import Base, engine, get_db
from models import User
from schemas import (
    AdminMetrics,
    PatientData,
    PredictionResponse,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from auth import (
    create_access_token,
    get_current_user,
    hash_password,
    require_admin,
    require_user,
    verify_password,
)

# ---------------------------------------------------------------------------
# Логирование
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Глобальные метрики
# ---------------------------------------------------------------------------
start_time = time.time()
prediction_counter = 0

# ---------------------------------------------------------------------------
# Загрузка ONNX-модели
# ---------------------------------------------------------------------------
MODEL_PATH = "diabetes_model.onnx"
session = ort.InferenceSession(MODEL_PATH, providers=["CPUExecutionProvider"])
input_name = session.get_inputs()[0].name

# ---------------------------------------------------------------------------
# OAuth2 декоратор для OpenAPI-документации
# ---------------------------------------------------------------------------
oauth2_scheme_docs = OAuth2(
    flows={
        "password": {
            "tokenUrl": "/auth/login",
            "scopes": {
                "read:profile": "Чтение профиля пользователя",
                "predict": "Доступ к инференсу модели",
                "admin": "Доступ к административным функциям",
            },
        }
    }
)

# ---------------------------------------------------------------------------
# Лайфсап приложения
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Создание таблиц БД и сидирование админа при старте."""
    global start_time
    start_time = time.time()

    # Создаём таблицы
    Base.metadata.create_all(bind=engine)
    logger.info("Таблицы БД созданы")

    # Сидирование админа
    settings = get_settings()
    db = next(get_db())
    try:
        admin = db.query(User).filter(User.username == settings.admin_username).first()
        if not admin:
            admin = User(
                username=settings.admin_username,
                email=settings.admin_email,
                hashed_password=hash_password(settings.admin_password),
                role="admin",
                is_active=True,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            logger.info("Админ-пользователь %s создан", settings.admin_username)
        else:
            logger.info("Админ-пользователь %s уже существует", settings.admin_username)
    finally:
        db.close()

    yield


# ---------------------------------------------------------------------------
# Приложение
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Diabetes Prediction API",
    description="API для предсказания диабета с JWT-аутентификацией и RBAC",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ---------------------------------------------------------------------------
# Корневой эндпоинт
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    """Корневой эндпоинт — приветственное сообщение."""
    return {
        "message": "Добро пожаловать в Diabetes Prediction API",
        "endpoints": {
            "/": "Приветственное сообщение",
            "/auth/register": "Регистрация пользователя",
            "/auth/login": "Вход и получение JWT-токена",
            "/me": "Профиль текущего пользователя (требуется Bearer-токен)",
            "/predict": "Предсказание наличия диабета (требуется Bearer-токен)",
            "/admin/metrics": "Метрики системы (только admin)",
            "/docs": "Интерактивная документация OpenAPI",
        },
    }


# ===================================================================
# Эндпоинты аутентификации
# ===================================================================

@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Регистрация нового пользователя.

    По умолчанию присваивается роль **user**.
    При попытке зарегистрировать существующий логин или e-mail возвращается 409.
    """
    settings = get_settings()

    # Проверка на дубликаты
    existing = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким логином или e-mail уже существует",
        )

    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        role=settings.default_role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("Пользователь %s зарегистрирован", user.username)
    return user


@app.post("/auth/login", response_model=TokenResponse)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """
    Вход в систему.

    Принимает логин (или e-mail) и пароль, возвращает JWT access-token.
    """
    settings = get_settings()

    # Поиск пользователя по username или email
    user = db.query(User).filter(
        (User.username == login_data.username) | (User.email == login_data.username)
    ).first()

    if not user or not verify_password(login_data.password, user.hashed_password):
        logger.warning("Неудачная попытка входа: %s", login_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин/e-mail или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт деактивирован",
        )

    # Создание токена
    access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    token_data = {
        "sub": user.username,
        "role": user.role,
    }
    access_token = create_access_token(token_data, expires_delta=access_token_expires)

    expires_in_seconds = int(access_token_expires.total_seconds())

    logger.info("Пользователь %s вошёл в систему", user.username)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in_seconds,
    )


# ===================================================================
# Эндпоинт профиля
# ===================================================================

@app.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Вернуть профиль текущего пользователя.

    Требует **Bearer-токен**.
    """
    return current_user


# ===================================================================
# Эндпоинт инференса
# ===================================================================

@app.post("/predict", response_model=PredictionResponse)
def predict(
    patient: PatientData,
    current_user: User = Depends(require_user),
):
    """
    Предсказание наличия диабета.

    Требует **Bearer-токен** с ролью **user** или **admin**.

    Входные данные:
    - **Pregnancies**: количество беременностей (0–60)
    - **Glucose**: уровень глюкозы в мг/дл (0–500)
    - **BMI**: индекс массы тела (0–100)
    - **Age**: возраст (0–120)
    """
    global prediction_counter
    prediction_counter += 1

    logger.info(
        "Запрос на предсказание от пользователя %s (роль=%s): %s",
        current_user.username,
        current_user.role,
        patient.model_dump(),
    )

    try:
        # Подготовка входных данных
        data = np.array(
            [[patient.Pregnancies, patient.Glucose, patient.BMI, patient.Age]],
            dtype=np.float32,
        )

        # Инференс
        output = session.run(None, {input_name: data})
        probability = float(output[0][0])
        prediction = 1 if probability > 0.5 else 0

        response = PredictionResponse(prediction=prediction, probability=probability)
        logger.info(
            "Результат предсказания #%d: prediction=%d, probability=%.4f",
            prediction_counter,
            prediction,
            probability,
        )
        return response

    except Exception as e:
        logger.error("Ошибка инференса: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при выполнении инференса модели",
        )


# ===================================================================
# Админ-эндпоинты
# ===================================================================

@app.get("/admin/metrics", response_model=AdminMetrics)
def admin_metrics(current_user: User = Depends(require_admin)):
    """
    Метрики системы.

    Доступен только пользователям с ролью **admin**.
    """
    uptime = time.time() - start_time
    return AdminMetrics(
        total_predictions=prediction_counter,
        uptime_seconds=round(uptime, 2),
        app_version="1.0.0",
        model_name=MODEL_PATH,
    )


# ---------------------------------------------------------------------------
# Запуск (для uvicorn)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
