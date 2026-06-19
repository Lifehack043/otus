"""Open-Meteo weather provider (no API key required)."""

from app.config import settings
from app.domain import WeatherProvider
from app.services.client import create_client


class OpenMeteoProvider(WeatherProvider):
    """Open-Meteo current weather by coordinates."""

    @property
    def display_name(self) -> str:
        return "Open-Meteo"

    @property
    def field_name(self) -> str:
        return "open_meteo"

    def extract_temperature(self, data: dict) -> float | None:
        cw = data.get("current_weather")
        if cw:
            return cw.get("temperature")
        return None

    async def fetch(
        self,
        lat: float | None = None,
        lon: float | None = None,
        city: str | None = None,
    ) -> dict:
        if lat is None or lon is None:
            raise ValueError("Open-Meteo requires coordinates")

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": True,
            "timezone": "auto",
        }

        async with create_client(settings.request_timeout) as client:
            resp = await client.get(url, params=params)

        resp.raise_for_status()
        return resp.json()
