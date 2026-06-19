"""HTTP router — GET /weather."""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.exceptions import AllProvidersFailed, GeocodingFailed
from app.models import WeatherResponse
from app.services.weather_service import WeatherService

router = APIRouter()


def get_weather_service() -> WeatherService:
    """Dependency placeholder — overridden in app factory."""
    raise RuntimeError("WeatherService not injected")


@router.get("/weather", response_model=WeatherResponse)
async def get_weather(
    city: str = Query(..., min_length=1, description="City name, e.g. Moscow"),
    service: WeatherService = Depends(get_weather_service),
) -> WeatherResponse:
    try:
        return await service.get_weather(city)
    except GeocodingFailed as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "city": exc.city,
                "error": exc.message,
            },
        )
    except AllProvidersFailed as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "city": exc.city,
                "errors": exc.response.errors,
            },
        )
