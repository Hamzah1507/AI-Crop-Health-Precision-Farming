from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime


class SoilRecordCreate(BaseModel):
    farm_id: Optional[int] = None
    crop_id: Optional[int] = None
    ph: Optional[float] = Field(None, ge=0.0, le=14.0, description="Soil pH (0.0 to 14.0)")
    nitrogen: Optional[float] = Field(None, ge=0.0, le=1000.0, description="Available Nitrogen in kg/ha")
    phosphorus: Optional[float] = Field(None, ge=0.0, le=1000.0, description="Available Phosphorus in kg/ha")
    potassium: Optional[float] = Field(None, ge=0.0, le=1000.0, description="Available Potassium in kg/ha")
    moisture: Optional[float] = Field(None, ge=0.0, le=100.0, description="Soil Moisture percentage (0.0% to 100.0%)")


class SoilRecordResponse(BaseModel):
    id: int
    farm_id: Optional[int] = None
    crop_id: Optional[int] = None
    farmer_id: int
    ph: Optional[float] = None
    nitrogen: Optional[float] = None
    phosphorus: Optional[float] = None
    potassium: Optional[float] = None
    moisture: Optional[float] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SoilAnalysisRequest(BaseModel):
    ph: Optional[float] = Field(None, ge=0.0, le=14.0, description="Soil pH (0.0 to 14.0)")
    nitrogen: Optional[float] = Field(None, ge=0.0, le=1000.0, description="Available Nitrogen in kg/ha")
    phosphorus: Optional[float] = Field(None, ge=0.0, le=1000.0, description="Available Phosphorus in kg/ha")
    potassium: Optional[float] = Field(None, ge=0.0, le=1000.0, description="Available Potassium in kg/ha")
    moisture: Optional[float] = Field(None, ge=0.0, le=100.0, description="Soil Moisture percentage (0.0% to 100.0%)")
    crop_name: Optional[str] = None
    crop_id: Optional[int] = None
    location: Optional[str] = None
    farm_id: Optional[int] = None


class SoilLatestResponse(BaseModel):
    """Latest saved soil record plus its rule-based assessment (computed on the fly, never stored)."""
    total_records: int = 0
    record: Optional[SoilRecordResponse] = None
    analysis: Optional[dict] = None


class SoilHealthResult(BaseModel):
    soil_health_status: str
    soil_health_score: float
    health_summary: Optional[str] = None
    is_sufficient: bool = True
    measured_parameters_count: int = 5
    fertilizer_recommendations: List[dict]
    crop_recommendations: List[str]
    irrigation_recommendation: dict
    weather_alerts: List[str]
    detailed_analysis: dict
    weather_used: Optional[dict] = None
    recommendations_created: int = 0      # new recommendations stored by this analysis
    repeat_analysis: bool = False         # True if identical measurements were analysed before
