from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class PredictionResponse(BaseModel):
    id: int
    farmer_id: int
    crop_id: Optional[int] = None
    image_path: Optional[str] = None
    original_filename: Optional[str] = None
    crop_name: Optional[str] = None
    disease_name: Optional[str] = None
    pest_name: Optional[str] = None
    prediction_type: str
    confidence: Optional[float] = None
    bbox_data: Optional[dict] = None
    status: Optional[str] = None
    is_demo: Optional[str] = "false"
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PredictionListResponse(BaseModel):
    predictions: List[PredictionResponse]
    total: int
