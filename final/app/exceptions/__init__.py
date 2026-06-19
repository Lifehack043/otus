"""Application-level exceptions."""

from app.models import WeatherResponse


class AllProvidersFailed(Exception):
    def __init__(self, city: str, response: WeatherResponse):
        self.city = city
        self.response = response
        super().__init__(f"All providers failed for city={city}")


class GeocodingFailed(Exception):
    def __init__(self, city: str, message: str):
        self.city = city
        self.message = message
        super().__init__(f"Geocoding failed for {city}: {message}")
