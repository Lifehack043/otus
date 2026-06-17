"""
Настройки для разработки.
"""

import os

from .base import *  # noqa: F401, F403

DEBUG = True

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-dev-key-change-in-production-!@#$%^&*()",
)

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "::1"]

# Development email backend
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# CSRF trusted origins for development
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Static files serving in development
MIDDLEWARE.insert(1, "django.contrib.staticfiles.middleware.StaticFilesMiddleware")  # noqa: F405
