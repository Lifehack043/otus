"""Weather service — geocoding + parallel provider calls."""

import asyncio
import logging
import statistics
from typing import Any

import httpx

from app.domain import GeocodingProvider, WeatherProvider
from app.exceptions import AllProvidersFailed, GeocodingFailed
from app.models import Coordinates, ProviderTemp, WeatherResponse

logger = logging.getLogger(__name__)


def _format_error(exc: Exception) -> str:
    if isinstance(exc, httpx.TimeoutException):
        return "Request timed out (5s)"
    if isinstance(exc, httpx.ConnectError):
        return "Cannot connect to the API server"
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code}"
    return str(exc)


class WeatherService:
    def __init__(
        self,
        geocoder: GeocodingProvider,
        providers: list[WeatherProvider],
    ):
        self.geocoder = geocoder
        self.providers = providers

    async def get_weather(self, city: str) -> WeatherResponse:
        logger.info("Request: city=%s", city)

        lat, lon = await self._resolve_coordinates(city)
        results = await self._fetch_from_providers(lat, lon, city)
        resp = self._build_response(city, lat, lon, results)

        if not resp.has_any_data():
            raise AllProvidersFailed(city=city, response=resp)

        logger.info("Response for %s ready: avg=%.1f°C", city, resp.average_temperature_celsius)
        return resp

    async def _resolve_coordinates(self, city: str) -> tuple[float, float]:
        try:
            lat, lon = await self.geocoder.resolve(city)
            logger.info("Geocoded %s → lat=%.4f, lon=%.4f", city, lat, lon)
            return lat, lon
        except Exception as exc:
            msg = _format_error(exc)
            logger.error("Geocoding failed for %s: %s", city, msg)
            raise GeocodingFailed(city=city, message=msg)

    async def _fetch_from_providers(
        self, lat: float, lon: float, city: str
    ) -> list[dict[str, Any] | Exception]:
        return await asyncio.gather(
            *(provider.fetch(lat=lat, lon=lon, city=city) for provider in self.providers),
            return_exceptions=True,
        )

    def _build_response(
        self,
        city: str,
        lat: float,
        lon: float,
        results: list[dict[str, Any] | Exception],
    ) -> WeatherResponse:
        temperatures: dict[str, ProviderTemp] = {}
        temps_ok: list[float] = []

        for provider, result in zip(self.providers, results):
            key = provider.field_name

            if isinstance(result, Exception):
                msg = _format_error(result)
                temperatures[key] = ProviderTemp(
                    temperature_celsius=None,
                    available=False,
                    error=msg,
                )
                logger.warning("%s failed: %s", provider.display_name, msg)
            else:
                temp = provider.extract_temperature(result)
                temperatures[key] = ProviderTemp(
                    temperature_celsius=temp,
                    available=True,
                    error=None,
                )
                logger.info("%s OK, temp=%.1f°C", provider.display_name, temp)
                if temp is not None:
                    temps_ok.append(temp)

        avg_temp = round(statistics.mean(temps_ok), 1) if temps_ok else None

        return WeatherResponse(
            city=city,
            coordinates=Coordinates(lat=lat, lon=lon),
            temperatures=temperatures,
            average_temperature_celsius=avg_temp,
        )
