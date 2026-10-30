from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class YieldPredictionRequest(BaseModel):
    crop_name: str
    farm_id: Optional[int] = None
    area: Optional[float] = None
    soil_ph: Optional[float] = None
    soil_nitrogen: Optional[float] = None
    soil_phosphorus: Optional[float] = None
    soil_potassium: Optional[float] = None
    soil_moisture: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    rainfall: Optional[float] = None
    season: Optional[str] = None


class YieldPredictionResponse(BaseModel):
    id: int
    farmer_id: int
    farm_id: Optional[int] = None
    crop_name: str
    predicted_yield: Optional[float] = None
    yield_unit: Optional[str] = "tons/hectare"
    confidence: Optional[float] = None
    area: Optional[float] = None
    soil_ph: Optional[float] = None
    soil_nitrogen: Optional[float] = None
    soil_phosphorus: Optional[float] = None
    soil_potassium: Optional[float] = None
    soil_moisture: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    rainfall: Optional[float] = None
    season: Optional[str] = None
    is_demo: Optional[str] = "false"
    created_at: Optional[datetime] = None
    # Only filled in when an estimate is just calculated (not stored in the database)
    factors: List[dict] = []
    model_note: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
