"""Open-Meteo Geocoding provider."""

from app.config import settings
from app.domain import GeocodingProvider
from app.services.client import create_client


class OpenMeteoGeocoding(GeocodingProvider):
    """Resolve city name to (lat, lon) via Open-Meteo Geocoding API."""

    async def resolve(self, city: str) -> tuple[float, float]:
        url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {"name": city, "count": 1, "language": "ru", "format": "json"}

        async with create_client(settings.request_timeout) as client:
            resp = await client.get(url, params=params)

        resp.raise_for_status()
        data = resp.json()

        results = data.get("results")
        if not results:
            raise ValueError(f"City '{city}' not found in geocoding")

        return results[0]["latitude"], results[0]["longitude"]
