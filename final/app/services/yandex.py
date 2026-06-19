"""Yandex.Weather provider (requires API key)."""

from app.config import settings
from app.domain import WeatherProvider
from app.services.client import create_client


class YandexWeatherProvider(WeatherProvider):
    """Yandex.Weather by coordinates."""

    @property
    def display_name(self) -> str:
        return "Yandex.Weather"

    @property
    def field_name(self) -> str:
        return "yandex"

    def extract_temperature(self, data: dict) -> float | None:
        fact = data.get("fact")
        if fact:
            return fact.get("temp")
        return None

    async def fetch(
        self,
        lat: float | None = None,
        lon: float | None = None,
        city: str | None = None,
    ) -> dict:
        if not settings.yandex_weather_api_key:
            raise ValueError("YANDEX_WEATHER_API_KEY not set")
        if lat is None or lon is None:
            raise ValueError("Yandex.Weather requires coordinates")

        url = "https://api.weather.yandex.ru/v2/forecast"
        params = {"lat": lat, "lon": lon, "lang": "ru_RU"}
        headers = {"X-Yandex-API-Key": settings.yandex_weather_api_key}

        async with create_client(settings.request_timeout) as client:
            resp = await client.get(url, params=params, headers=headers)

        if resp.status_code == 401:
            raise ValueError("Yandex.Weather API key is invalid")
        resp.raise_for_status()
        return resp.json()
