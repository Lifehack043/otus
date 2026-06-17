"""
Настройки для тестирования.
"""

from .base import *  # noqa: F401, F403

DEBUG = False
TEST_RUNNER = "django.test.runner.DiscoverRunner"

# Use in-memory database for tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Faster password hashing for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable email sending in tests
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Silence specific logs during tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
}
