"""Settings loaded from environment variables."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    openweather_api_key: str
    weatherapi_key: str
    yandex_weather_api_key: str
    request_timeout: float = 5.0


settings = Settings(
    openweather_api_key=os.getenv("OPENWEATHER_API_KEY", ""),
    weatherapi_key=os.getenv("WEATHERAPI_KEY", ""),
    yandex_weather_api_key=os.getenv("YANDEX_WEATHER_API_KEY", ""),
)
