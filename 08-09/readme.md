# Diabetes Prediction API

JSON API-сервис для инференса модели машинного обучения (диагностика диабета) с JWT-аутентификацией и RBAC-авторизацией.

## Цель задания

Закрепить навыки работы с:

- библиотекой FastAPI для создания JSON API,
- JWT-аутентификацией (выпуск, проверка, валидация токенов),
- RBAC-авторизацией (роли `user` и `admin`),
- выполнением инференса с использованием onnxruntime,
- хранением паролей в виде хэшей (bcrypt),
- SQLite + SQLAlchemy для хранения учётных данных.

## Модель

Модель `diabetes_model.onnx` принимает на вход признаки пациента:

- `Pregnancies` — количество беременностей (0–60),
- `Glucose` — уровень глюкозы, мг/дл (0–500),
- `BMI` — индекс массы тела (0–100),
- `Age` — возраст (0–120).

На выходе модель возвращает вероятность наличия диабета:

- вероятность > 0.5 → предсказание `1` (есть диабет),
- иначе → `0` (нет диабета).

## Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Конфигурация (.env)

Создайте файл `.env` в корне проекта:

```env
# JWT конфигурация
JWT_SECRET_KEY=super-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Дефолтная роль при регистрации
DEFAULT_ROLE=user

# Пароль админ-пользователя (для сидирования)
ADMIN_PASSWORD=admin123
```

### 3. Запуск

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Или напрямую:

```bash
python main.py
```

### 4. Документация OpenAPI

После запуска откройте в браузере:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Эндпоинты

### Аутентификация

| Метод | Путь | Описание | Авторизация |
|-------|------|----------|-------------|
| `POST` | `/auth/register` | Регистрация пользователя | Нет |
| `POST` | `/auth/login` | Вход и получение JWT-токена | Нет |

### Профиль

| Метод | Путь | Описание | Авторизация |
|-------|------|----------|-------------|
| `GET` | `/me` | Профиль текущего пользователя | Bearer-токен |

### Инференс

| Метод | Путь | Описание | Авторизация |
|-------|------|----------|-------------|
| `POST` | `/predict` | Предсказание наличия диабета | Bearer-токен (user/admin) |

### Администрирование

| Метод | Путь | Описание | Авторизация |
|-------|------|----------|-------------|
| `GET` | `/admin/metrics` | Метрики системы | Bearer-токен (admin) |

### Прочее

| Метод | Путь | Описание | Авторизация |
|-------|------|----------|-------------|
| `GET` | `/` | Приветственное сообщение | Нет |
| `GET` | `/docs` | Swagger UI | Нет |

## Примеры запросов

### Регистрация

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "password123"}'
```

**Ответ (201 Created):**

```json
{
  "id": 2,
  "username": "testuser",
  "email": "test@example.com",
  "role": "user"
}
```

### Вход

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "password123"}'
```

**Ответ (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Профиль пользователя

```bash
curl http://localhost:8000/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

**Ответ (200 OK):**

```json
{
  "id": 2,
  "username": "testuser",
  "email": "test@example.com",
  "role": "user"
}
```

### Предсказание

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -d '{"Pregnancies": 2, "Glucose": 140, "BMI": 35.5, "Age": 32}'
```

**Ответ (200 OK):**

```json
{
  "prediction": 1,
  "probability": 0.7832
}
```

### Админ-метрики

```bash
curl http://localhost:8000/admin/metrics \
  -H "Authorization: Bearer <admin-token>"
```

**Ответ (200 OK):**

```json
{
  "total_predictions": 42,
  "uptime_seconds": 3600.5,
  "app_version": "1.0.0",
  "model_name": "diabetes_model.onnx"
}
```

## Коды ответов

| Код | Описание |
|-----|----------|
| `200 OK` | Успешный запрос |
| `201 Created` | Пользователь создан |
| `400 Bad Request` | Некорректные входные данные |
| `401 Unauthorized` | Отсутствует/невалидный/просроченный токен |
| `403 Forbidden` | Недостаточно прав (роль) |
| `409 Conflict` | Пользователь уже существует |
| `500 Internal Server Error` | Ошибка сервера (инференс) |

## Роли и права доступа

| Роль | `/predict` | `/me` | `/admin/metrics` |
|------|-----------|-------|------------------|
| `user` | ✅ | ✅ | ❌ (403) |
| `admin` | ✅ | ✅ | ✅ |

## Структура проекта

```
.
├── .env                  # Переменные окружения
├── auth.py               # JWT-аутентификация и RBAC
├── config.py             # Конфигурация из .env
├── database.py           # Подключение к БД (SQLite)
├── diabetes_model.onnx   # ONNX-модель
├── infer.py              # Скрипт для тестового инференса
├── main.py               # FastAPI-приложение и эндпоинты
├── models.py             # SQLAlchemy-модели
├── readme.md             # Документация
├── requirements.txt      # Зависимости Python
├── schemas.py            # Pydantic-схемы
└── users.db              # SQLite-база (создаётся автоматически)
```

## Админ-пользователь

При первом запуске автоматически создаётся админ-пользователь:

- **Логин:** `admin`
- **Пароль:** значение из `ADMIN_PASSWORD` в `.env` (по умолчанию `admin123`)

## Безопасность

- Пароли хэшируются с помощью `bcrypt` (через `passlib`).
- JWT-токены подписываются секретным ключом из `.env`.
- Параметры безопасности (секрет, алгоритм, TTL) настраиваются через переменные окружения.
- Логирование ключевых событий: аутентификация, отказ в доступе, ошибки инференса.
