"""Domain layer — abstract interfaces."""

from abc import ABC, abstractmethod
from typing import Any


class WeatherProvider(ABC):
    """Abstract weather data provider."""

    @abstractmethod
    async def fetch(
        self,
        lat: float | None = None,
        lon: float | None = None,
        city: str | None = None,
    ) -> dict[str, Any]:
        """Fetch weather data. Accepts coordinates OR city name."""
        ...

    @abstractmethod
    def extract_temperature(self, data: dict[str, Any]) -> float | None:
        """Extract temperature in Celsius from raw API response."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        ...

    @property
    @abstractmethod
    def field_name(self) -> str:
        """Response JSON key, e.g. 'open_meteo', 'yandex'."""
        ...


class GeocodingProvider(ABC):
    """Abstract geocoding provider — resolves city name to coordinates."""

    @abstractmethod
    async def resolve(self, city: str) -> tuple[float, float]:
        """Return (lat, lon). Raises ValueError if not found."""
        ...
