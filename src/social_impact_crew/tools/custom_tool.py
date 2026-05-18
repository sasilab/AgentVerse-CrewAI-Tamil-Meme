"""Custom CrewAI tools backed by Open-Meteo (no API key required).

Why Open-Meteo: it's free, key-less, and rate-limit friendly for learners.
Each tool subclasses crewai.tools.BaseTool with a Pydantic args_schema so the
LLM gets a typed contract instead of free-form strings.
"""

from typing import Type

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Short timeout so the agent fails fast on a flaky network instead of hanging.
HTTP_TIMEOUT = 15


# ---------- Geocode ----------

class GeocodeInput(BaseModel):
    city: str = Field(..., description="City name, e.g. 'Chennai' or 'Bengaluru'.")


class GeocodeTool(BaseTool):
    name: str = "geocode_city"
    description: str = (
        "Convert a city name into latitude/longitude using Open-Meteo's free "
        "geocoding API. Returns 'lat,lon,resolved_name,country' as a string."
    )
    args_schema: Type[BaseModel] = GeocodeInput

    def _run(self, city: str) -> str:
        url = "https://geocoding-api.open-meteo.com/v1/search"
        # count=1 keeps the response tiny; the first hit is almost always the
        # populated city the user meant.
        params = {"name": city, "count": 1, "language": "en", "format": "json"}
        r = requests.get(url, params=params, timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        results = r.json().get("results") or []
        if not results:
            return f"ERROR: no geocoding result for '{city}'."
        top = results[0]
        return (
            f"{top['latitude']},{top['longitude']},"
            f"{top.get('name', city)},{top.get('country', '')}"
        )


# ---------- Weather ----------

class WeatherInput(BaseModel):
    latitude: float = Field(..., description="Latitude in decimal degrees.")
    longitude: float = Field(..., description="Longitude in decimal degrees.")


class WeatherTool(BaseTool):
    name: str = "get_current_weather"
    description: str = (
        "Fetch current weather (temperature, humidity, wind, precipitation, "
        "weather code) for a lat/lon from Open-Meteo. No API key needed."
    )
    args_schema: Type[BaseModel] = WeatherInput

    def _run(self, latitude: float, longitude: float) -> str:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            # Bundling these in one call avoids multiple round-trips.
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,"
                       "precipitation,weather_code,wind_speed_10m",
            "timezone": "auto",
        }
        r = requests.get(url, params=params, timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        cur = r.json().get("current", {})
        if not cur:
            return "ERROR: weather API returned no 'current' block."
        return (
            f"temp_c={cur.get('temperature_2m')}, "
            f"feels_like_c={cur.get('apparent_temperature')}, "
            f"humidity_pct={cur.get('relative_humidity_2m')}, "
            f"wind_kmh={cur.get('wind_speed_10m')}, "
            f"precip_mm={cur.get('precipitation')}, "
            f"weather_code={cur.get('weather_code')}"
        )


# ---------- Pollution ----------

class PollutionInput(BaseModel):
    latitude: float = Field(..., description="Latitude in decimal degrees.")
    longitude: float = Field(..., description="Longitude in decimal degrees.")


class PollutionTool(BaseTool):
    name: str = "get_air_quality"
    description: str = (
        "Fetch current air quality (PM2.5, PM10, NO2, O3, CO, European AQI) "
        "for a lat/lon from Open-Meteo Air Quality API. No API key needed."
    )
    args_schema: Type[BaseModel] = PollutionInput

    def _run(self, latitude: float, longitude: float) -> str:
        url = "https://air-quality-api.open-meteo.com/v1/air-quality"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,ozone,"
                       "european_aqi",
            "timezone": "auto",
        }
        r = requests.get(url, params=params, timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        cur = r.json().get("current", {})
        if not cur:
            return "ERROR: air-quality API returned no 'current' block."
        return (
            f"european_aqi={cur.get('european_aqi')}, "
            f"pm2_5={cur.get('pm2_5')} ug/m3, "
            f"pm10={cur.get('pm10')} ug/m3, "
            f"no2={cur.get('nitrogen_dioxide')} ug/m3, "
            f"o3={cur.get('ozone')} ug/m3, "
            f"co={cur.get('carbon_monoxide')} ug/m3"
        )
