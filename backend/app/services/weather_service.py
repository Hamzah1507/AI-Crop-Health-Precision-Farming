"""
Weather Service

Fetches live weather through Open-Meteo (https://open-meteo.com, no API key
required). Both the geocoding and forecast calls are made from the backend.

Every result carries an explicit ``is_live`` flag:
- ``is_live=True``  -> real data returned by Open-Meteo.
- ``is_live=False`` -> clearly labelled fallback values, used ONLY when the
  external service is unreachable. Fallback data is never stored as a record.

An unknown location is reported as ``LocationNotFoundError`` rather than being
papered over with fallback values.

Weather data by Open-Meteo.com (CC BY 4.0).
"""

import httpx
import logging
from typing import Optional, Dict, Any, List
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ATTRIBUTION = "Weather data by Open-Meteo.com (CC BY 4.0)"
ATTRIBUTION_URL = "https://open-meteo.com/"
TIMEOUT_SECONDS = 10.0

# WMO weather interpretation codes -> (description, broad condition)
WMO_CODES = {
    0: ("Clear sky", "Clear"),
    1: ("Mainly clear", "Clear"),
    2: ("Partly cloudy", "Clouds"),
    3: ("Overcast", "Clouds"),
    45: ("Fog", "Fog"),
    48: ("Depositing rime fog", "Fog"),
    51: ("Light drizzle", "Drizzle"),
    53: ("Moderate drizzle", "Drizzle"),
    55: ("Dense drizzle", "Drizzle"),
    56: ("Light freezing drizzle", "Drizzle"),
    57: ("Dense freezing drizzle", "Drizzle"),
    61: ("Slight rain", "Rain"),
    63: ("Moderate rain", "Rain"),
    65: ("Heavy rain", "Rain"),
    66: ("Light freezing rain", "Rain"),
    67: ("Heavy freezing rain", "Rain"),
    71: ("Slight snow", "Snow"),
    73: ("Moderate snow", "Snow"),
    75: ("Heavy snow", "Snow"),
    77: ("Snow grains", "Snow"),
    80: ("Slight rain showers", "Rain"),
    81: ("Moderate rain showers", "Rain"),
    82: ("Violent rain showers", "Rain"),
    85: ("Slight snow showers", "Snow"),
    86: ("Heavy snow showers", "Snow"),
    95: ("Thunderstorm", "Thunderstorm"),
    96: ("Thunderstorm with slight hail", "Thunderstorm"),
    99: ("Thunderstorm with heavy hail", "Thunderstorm"),
}


class LocationNotFoundError(Exception):
    """The entered location could not be resolved to coordinates."""


class WeatherUnavailableError(Exception):
    """Open-Meteo could not be reached or returned unusable data."""


def _describe(code: Optional[int]) -> tuple:
    return WMO_CODES.get(code, ("Unknown conditions", "Unknown"))


def _num(value) -> Optional[float]:
    """Return value as float, or None if it is missing or not numeric."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


async def geocode(client: httpx.AsyncClient, location: str) -> Dict[str, Any]:
    """
    Resolve a free-text location such as "Pune" or "Mumbai, India" to coordinates.

    Open-Meteo geocoding matches on place name only, so "City, Region, Country"
    is searched by its first part and the remaining parts are used to pick the
    best match (country, country code or region).
    """
    parts = [p.strip() for p in location.split(",") if p.strip()]
    if not parts:
        raise LocationNotFoundError(location)

    response = await client.get(
        GEOCODING_URL,
        params={"name": parts[0], "count": 10, "language": "en", "format": "json"},
    )
    response.raise_for_status()
    results = response.json().get("results") or []
    if not results:
        raise LocationNotFoundError(location)

    wanted = [p.lower() for p in parts[1:]]
    best = results[0]
    if wanted:
        for item in results:
            haystack = {
                str(item.get(k, "")).lower()
                for k in ("country", "country_code", "admin1", "admin2")
            }
            if any(w in haystack for w in wanted):
                best = item
                break

    lat, lon = _num(best.get("latitude")), _num(best.get("longitude"))
    if lat is None or lon is None:
        raise LocationNotFoundError(location)

    label = ", ".join(str(best[k]) for k in ("name", "admin1", "country") if best.get(k))
    return {"latitude": lat, "longitude": lon, "name": label or parts[0]}


def _parse_forecast(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Turn Open-Meteo's column-oriented daily block into a list of day dicts."""
    daily = payload.get("daily") or {}
    dates = daily.get("time") or []
    days = []
    for i, date in enumerate(dates):
        def pick(key):
            values = daily.get(key) or []
            return _num(values[i]) if i < len(values) else None

        code = pick("weather_code")
        days.append({
            "date": date,
            "temp_max": pick("temperature_2m_max"),
            "temp_min": pick("temperature_2m_min"),
            "precipitation_sum": pick("precipitation_sum"),
            "precipitation_probability": pick("precipitation_probability_max"),
            "description": _describe(int(code) if code is not None else None)[0],
        })
    return days


def forecast_alerts(forecast: List[Dict[str, Any]]) -> List[str]:
    """Simple rule-based farming alerts derived from the daily forecast."""
    alerts = []
    for day in forecast:
        date = day["date"]
        if day["precipitation_sum"] is not None and day["precipitation_sum"] >= 20:
            alerts.append(f"Heavy rain expected on {date} ({day['precipitation_sum']} mm): check drainage and delay spraying.")
        if day["temp_min"] is not None and day["temp_min"] <= 4:
            alerts.append(f"Frost risk on {date} (low {day['temp_min']}°C): protect sensitive crops.")
        if day["temp_max"] is not None and day["temp_max"] >= 38:
            alerts.append(f"Extreme heat expected on {date} (high {day['temp_max']}°C): plan extra irrigation.")
    return alerts


async def fetch_weather(location: str) -> Dict[str, Any]:
    """
    Fetch current weather and a 5-day forecast for ``location``.

    Raises LocationNotFoundError for an unknown location. If Open-Meteo is
    unreachable, returns labelled fallback values with ``is_live=False``.
    """
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            place = await geocode(client, location)
            response = await client.get(
                FORECAST_URL,
                params={
                    "latitude": place["latitude"],
                    "longitude": place["longitude"],
                    "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code",
                    "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max",
                    "forecast_days": 5,
                    "timezone": "auto",
                    "wind_speed_unit": "kmh",
                },
            )
            response.raise_for_status()
            payload = response.json()

        current = payload.get("current")
        if not isinstance(current, dict) or _num(current.get("temperature_2m")) is None:
            raise WeatherUnavailableError("Open-Meteo response did not contain current weather")

        description, condition = _describe(
            int(current["weather_code"]) if _num(current.get("weather_code")) is not None else None
        )
        forecast = _parse_forecast(payload)
        return {
            "location": location,
            "resolved_location": place["name"],
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "temperature": _num(current.get("temperature_2m")),
            "humidity": _num(current.get("relative_humidity_2m")),
            "rainfall": _num(current.get("precipitation")) or 0.0,
            "wind_speed": _num(current.get("wind_speed_10m")),
            "description": description,
            "condition": condition,
            "forecast": forecast,
            "forecast_alerts": forecast_alerts(forecast),
            "is_live": True,
            "source": "Open-Meteo (live)",
            "attribution": ATTRIBUTION,
            "attribution_url": ATTRIBUTION_URL,
        }

    except LocationNotFoundError:
        raise
    except (httpx.HTTPError, ValueError, KeyError, WeatherUnavailableError) as e:
        logger.error(f"Open-Meteo unavailable for '{location}': {e}")
        return _get_fallback_weather(location)


def _get_fallback_weather(location: str) -> Dict[str, Any]:
    """Clearly labelled placeholder values used only when Open-Meteo is unreachable."""
    return {
        "location": location,
        "resolved_location": None,
        "latitude": None,
        "longitude": None,
        "temperature": 28.5,
        "humidity": 65.0,
        "rainfall": 2.5,
        "wind_speed": 12.0,
        "description": "Placeholder values - live weather service unavailable",
        "condition": "Unavailable",
        "forecast": [],
        "forecast_alerts": [],
        "is_live": False,
        "source": "Fallback placeholder (NOT live weather)",
        "attribution": None,
        "attribution_url": None,
    }
