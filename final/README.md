# Weather Aggregator

FastAPI-приложение параллельно запрашивает погоду из 4 источников и возвращает **температуру** от каждого провайдера + **среднее**.

## Установка

```bash
uv sync
```

## Конфигурация

```bash
cp .env.example .env
```

## Запуск

```bash
python3 -m uvicorn main:app --reload
```

Сервер на `http://localhost:8000`.

## API

### `GET /weather?city={city}`

```bash
curl 'http://localhost:8000/weather?city=Moscow'
```

**Успех:**

```json
{
  "city": "Moscow",
  "coordinates": { "lat": 55.752, "lon": 37.618 },
  "temperatures": {
    "open_meteo":  { "temperature_celsius": 14.0, "available": true },
    "yandex":      { "temperature_celsius": 14.0, "available": true },
    "openweather": { "temperature_celsius": 13.6, "available": true },
    "weatherapi":  { "temperature_celsius": 14.1, "available": true }
  },
  "average_temperature_celsius": 13.9,
  "errors": {},
  "elapsed_seconds": 0.847
}
```

**Частичный ответ (один провайдер упал):**

```json
{
  "temperatures": {
    "open_meteo": { "temperature_celsius": null, "available": false, "error": "Request timed out (5s)" },
    "yandex":     { "temperature_celsius": 14.0, "available": true }
  },
  "average_temperature_celsius": 13.9,
  "errors": { "open_meteo": "Request timed out (5s)" }
}
```

**HTTP 400 (город не найден):**

```json
{
  "detail": { "city": "НегСити999", "error": "City not found in geocoding" }
}
```

**HTTP 502 (все провайдеры упали):**

```json
{
  "detail": {
    "city": "Moscow",
    "errors": { "open_meteo": "...", "yandex": "...", "openweather": "...", "weatherapi": "..." }
  }
}
```

## Архитектура

```
GET /weather?city=Moscow
  │
  ├── Router          → HTTP-эндпоинт
  ├── WeatherService  → геокдинг → asyncio.gather(4 провайдера) → extract_temperature()
  │     ├── OpenMeteoGeocoding   → city → (lat, lon)
  │     ├── OpenMeteoProvider    → current_weather.temperature
  │     ├── YandexWeatherProvider → fact.temp
  │     ├── OpenWeatherProvider  → main.temp
  │     └── WeatherApiProvider   → current.temp_c
  ├── Domain          → WeatherProvider, GeocodingProvider (ABC)
  └── Models          → WeatherResponse, ProviderTemp, Coordinates (Pydantic)
```

## Структура проекта

```
app/
├── __init__.py              # экспорт create_app
├── config.py                # ключи API, timeout
├── main.py                  # Application factory
├── domain/
│   └── __init__.py          # WeatherProvider, GeocodingProvider (ABC)
├── models/
│   └── __init__.py          # WeatherResponse, ProviderTemp, Coordinates
├── services/
│   ├── __init__.py
│   ├── client.py            # httpx.AsyncClient с truststore (fix macOS SSL)
│   ├── geocoding.py         # OpenMeteo Geocoding
│   ├── openmeteo.py         # Open-Meteo Weather API
│   ├── openweather.py       # OpenWeatherMap API
│   ├── weatherapi.py        # WeatherAPI.com API
│   ├── yandex.py            # Yandex.Weather API
│   └── weather_service.py   # WeatherService + исключения
└── routers/
    └── __init__.py          # GET /weather
```
