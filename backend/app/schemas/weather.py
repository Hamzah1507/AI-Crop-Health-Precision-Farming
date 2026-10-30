from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class WeatherRequest(BaseModel):
    location: str
    farm_id: Optional[int] = None


class ForecastDay(BaseModel):
    date: str
    temp_max: Optional[float] = None
    temp_min: Optional[float] = None
    precipitation_sum: Optional[float] = None
    precipitation_probability: Optional[float] = None
    description: Optional[str] = None


class WeatherResponse(BaseModel):
    id: Optional[int] = None
    location: Optional[str] = None
    resolved_location: Optional[str] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    rainfall: Optional[float] = None
    wind_speed: Optional[float] = None
    description: Optional[str] = None
    condition: Optional[str] = None
    recorded_at: Optional[datetime] = None
    # Live vs. fallback disclosure, forecast and attribution
    is_live: bool = False
    source: Optional[str] = None
    forecast: List[ForecastDay] = []
    forecast_alerts: List[str] = []
    attribution: Optional[str] = None
    attribution_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
