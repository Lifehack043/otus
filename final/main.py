"""
FastAPI Weather Aggregator

GET /weather?city={city}
Параллельный запрос к OpenWeatherMap + WeatherAPI.

Запуск:
    pip3 install -r requirements.txt
    python3 -m uvicorn main:app --reload
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
