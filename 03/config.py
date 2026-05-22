"""Конфигурация сервера."""

import sys

# Настройки HTTP сервера
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8080

# Настройки логирования
LOG_FORMAT = "[%(asctime)s] %(levelname).1s %(message)s"
LOG_DATE_FORMAT = "%Y.%m.%d %H:%M:%S"
LOG_DEFAULT_STREAM = sys.stdout


def get_log_config(log_file: str = None) -> dict:
    """Возвращает конфигурацию для logging.basicConfig."""
    config = {
        "level": "INFO",
        "format": LOG_FORMAT,
        "datefmt": LOG_DATE_FORMAT,
    }
    if log_file:
        config["filename"] = log_file
    else:
        config["stream"] = LOG_DEFAULT_STREAM
    return config
