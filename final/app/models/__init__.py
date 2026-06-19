"""Pydantic models for the API layer."""

from pydantic import BaseModel


class Coordinates(BaseModel):
    lat: float
    lon: float


class ProviderTemp(BaseModel):
    """Temperature from a single provider."""
    temperature_celsius: float | None = None
    available: bool = True
    error: str | None = None


class WeatherResponse(BaseModel):
    city: str
    coordinates: Coordinates
    temperatures: dict[str, ProviderTemp]  # provider name → temp
    average_temperature_celsius: float | None = None
    errors: dict[str, str | None] = {}

    def has_any_data(self) -> bool:
        return self.average_temperature_celsius is not None
