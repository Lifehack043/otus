"""WeatherAPI.com provider — by city name or coordinates."""

from app.config import settings
from app.domain import WeatherProvider
from app.services.client import create_client


class WeatherApiProvider(WeatherProvider):
    @property
    def display_name(self) -> str:
        return "WeatherAPI"

    @property
    def field_name(self) -> str:
        return "weatherapi"

    def extract_temperature(self, data: dict) -> float | None:
        current = data.get("current")
        if current:
            return current.get("temp_c")
        return None

    async def fetch(
        self,
        lat: float | None = None,
        lon: float | None = None,
        city: str | None = None,
    ) -> dict:
        if not settings.weatherapi_key:
            raise ValueError("WEATHERAPI_KEY not set")

        url = "https://api.weatherapi.com/v1/current.json"
        params = {"key": settings.weatherapi_key}

        if lat is not None and lon is not None:
            params["q"] = f"{lat},{lon}"
        elif city:
            params["q"] = city
        else:
            raise ValueError("Provide city name or coordinates")

        async with create_client(settings.request_timeout) as client:
            resp = await client.get(url, params=params)

        if resp.status_code == 401:
            raise ValueError("WeatherAPI key is invalid")
        if resp.status_code == 400:
            raise ValueError(f"City '{city}' not found")
        resp.raise_for_status()

        data = resp.json()
        if "error" in data:
            raise ValueError(f"API error: {data['error'].get('message', data['error'])}")
        return data
