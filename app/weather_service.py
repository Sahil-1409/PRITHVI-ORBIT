import httpx
from datetime import datetime

async def get_weather_data(lat: float = 30.7046, lon: float = 76.7179):
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,wind_speed_10m,wind_direction_10m,weather_code"
        f"&hourly=temperature_2m,precipitation_probability,wind_speed_10m&timezone=auto"
    )
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            res = await client.get(url)
            res.raise_for_status()
            data = res.json()
            curr = data.get("current", {})
            return {
                "source": "Open-Meteo REST API",
                "provenance": "FORECAST",
                "is_offline": False,
                "fetched_at": datetime.utcnow().isoformat() + "Z",
                "temperature": curr.get("temperature_2m", 25.2),
                "apparent_temperature": curr.get("apparent_temperature", 26.4),
                "humidity": curr.get("relative_humidity_2m", 48),
                "precipitation": curr.get("precipitation", 0.0),
                "wind_speed": curr.get("wind_speed_10m", 8.4),
                "wind_direction": curr.get("wind_direction_10m", 345),
                "weather_code": curr.get("weather_code", 0)
            }
    except Exception:
        return {
            "source": "Local Seed Meteorological Cache",
            "provenance": "DEMO_OFFLINE_BUFFER",
            "is_offline": True,
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "temperature": 26.0,
            "apparent_temperature": 27.1,
            "humidity": 52,
            "precipitation": 0.0,
            "wind_speed": 8.0,
            "wind_direction": 340,
            "weather_code": 1
        }
