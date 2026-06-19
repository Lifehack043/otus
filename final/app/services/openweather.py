"""OpenWeatherMap provider — by city name or coordinates."""

from app.config import settings
from app.domain import WeatherProvider
from app.services.client import create_client


class OpenWeatherProvider(WeatherProvider):
    """OpenWeatherMap API client."""

    @property
    def display_name(self) -> str:
        return "OpenWeatherMap"

    @property
    def field_name(self) -> str:
        return "openweather"

    def extract_temperature(self, data: dict) -> float | None:
        main = data.get("main")
        if main:
            return main.get("temp")
        return None

    async def fetch(
        self,
        lat: float | None = None,
        lon: float | None = None,
        city: str | None = None,
    ) -> dict:
        if not settings.openweather_api_key:
            raise ValueError("OPENWEATHER_API_KEY not set")

        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"appid": settings.openweather_api_key, "units": "metric"}

        if lat is not None and lon is not None:
            params["lat"] = lat
            params["lon"] = lon
        elif city:
            params["q"] = city
        else:
            raise ValueError("Provide city name or coordinates")

        async with create_client(settings.request_timeout) as client:
            resp = await client.get(url, params=params)

        if resp.status_code == 404:
            raise ValueError(f"City '{city}' not found")
        resp.raise_for_status()
        return resp.json()
