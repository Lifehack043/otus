# Django Polls

Веб-приложение для проведения опросов, реализованное на основе официального туториала Django. Приложение позволяет создавать опросы, голосовать за варианты ответов и просматривать результаты.

## Функциональность

- **Главная страница** — список последних 5 опросов
- **Страница опроса** — просмотр вопроса и голосование
- **Страница результатов** — отображение результатов голосования с прогресс-барами
- **Админ-панель** — управление опросами и вариантами ответов

## Технологический стек

| Компонент | Технология |
|-----------|-----------|
| Framework | Django 5.x |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Server | Gunicorn + Whitenoise |
| Container | Docker + Docker Compose |
| Testing | Django TestCase + Coverage |
| Linting | Ruff |

## Быстрый старт

### Локальная разработка

```bash
# 1. Клонируйте репозиторий
git clone <repo-url>
cd 07

# 2. Создайте виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 3. Установите зависимости
pip install -r requirements.txt

# 4. Скопируйте файл окружения
cp .env.example .env

# 5. Выполните миграции
python manage.py migrate

# 6. Создайте суперпользователя
python manage.py createsuperuser

# 7. Запустите сервер разработки
python manage.py runserver
```

Откройте [http://localhost:8000](http://localhost) в браузере.

Админ-панель: [http://localhost:8000/admin](http://localhost/admin)

### Docker

```bash
# Запуск через Docker Compose
docker-compose up --build

# Остановка
docker-compose down
```

## Тестирование

```bash
# Запуск всех тестов
python manage.py test

# Запуск с покрытием кода
coverage run --source=polls manage.py test
coverage report -m
coverage html
```

## Структура проекта

```
├── config/                 # Настройки проекта
│   ├── settings/           # Модульные настройки
│   │   ├── base.py         # Базовые настройки
│   │   ├── development.py  # Настройки разработки
│   │   ├── production.py   # Настройки продакшена
│   │   └── test.py         # Настройки тестирования
│   ├── urls.py             # Главные URL-маршруты
│   ├── wsgi.py             # WSGI-конфигурация
│   └── asgi.py             # ASGI-конфигурация
├── polls/                  # Приложение опросов
│   ├── models.py           # Модели данных
│   ├── views.py            # Представления
│   ├── urls.py             # URL-маршруты приложения
│   ├── admin.py            # Регистрация в админке
│   └── tests.py            # Тесты
├── templates/              # Шаблоны
│   ├── base.html           # Базовый шаблон
│   └── polls/              # Шаблоны приложения
│       ├── index.html
│       ├── detail.html
│       └── results.html
├── static/                 # Статические файлы
│   └── css/
│       └── base.css
├── manage.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── gunicorn.conf.py
└── README.md
```

## Настройка окружения

Скопируйте `.env.example` в `.env` и настройте переменные:

| Переменная | Описание | По умолчанию |
|------------|----------|:-----------:|
| `DJANGO_SETTINGS_MODULE` | Модуль настроек Django | `config.settings.development` |
| `DJANGO_SECRET_KEY` | Секретный ключ Django | — |
| `DJANGO_DEBUG` | Режим отладки | `True` |
| `ALLOWED_HOSTS` | Разрешённые хосты (через запятую) | `localhost` |
| `DB_ENGINE` | Драйвер базы данных | `django.db.backends.sqlite3` |
| `DB_NAME` | Имя базы данных | `polls_db` |
| `DB_USER` | Пользователь БД | — |
| `DB_PASSWORD` | Пароль БД | — |
| `DB_HOST` | Хост БД | `localhost` |
| `DB_PORT` | Порт БД | `5432` |

## Развёртывание

### Production Checklist

1. Установите `DJANGO_SETTINGS_MODULE=config.settings.production`
2. Установите надёжный `SECRET_KEY`
3. Настройте PostgreSQL (`DB_ENGINE=django.db.backends.postgresql`)
4. Настройте SMTP для отправки email
5. Включите HTTPS (`SECURE_SSL_REDIRECT=True`)
6. Соберите статические файлы: `python manage.py collectstatic`
7. Выполните миграции: `python manage.py migrate`
8. Запустите Gunicorn: `gunicorn config.wsgi:application --config gunicorn.conf.py`

### Heroku

```bash
heroku create your-app-name
heroku config:set DJANGO_SETTINGS_MODULE=config.settings.production
heroku config:set SECRET_KEY=$(openssl rand -base64 32)
git push heroku main
heroku run python manage.py migrate
heroku run python manage.py createsuperuser
```

## Безопасность

- CSRF-защита на всех формах
- XSS-фильтрация через автоэкранирование Django
- Защита от кликджекинга (`X-Frame-Options: DENY`)
- Безопасные куки в production (`Secure`, `HttpOnly`)
- Rate limiting через django-axes (защита брутфорса)
- Валидация паролей

## Лицензия

MIT License
