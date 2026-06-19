"""Application factory — assembles all layers."""

import logging

from fastapi import FastAPI

from app.routers import get_weather_service, router
from app.services.geocoding import OpenMeteoGeocoding
from app.services.openmeteo import OpenMeteoProvider
from app.services.openweather import OpenWeatherProvider
from app.services.weather_service import WeatherService
from app.services.weatherapi import WeatherApiProvider
from app.services.yandex import YandexWeatherProvider

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def create_app() -> FastAPI:
    geocoder = OpenMeteoGeocoding()
    providers = [
        OpenMeteoProvider(),
        YandexWeatherProvider(),
        OpenWeatherProvider(),
        WeatherApiProvider(),
    ]
    service = WeatherService(geocoder=geocoder, providers=providers)

    app = FastAPI(title="Weather Aggregator", version="2.0.0")

    app.dependency_overrides[get_weather_service] = lambda: service

    app.include_router(router)

    return app
