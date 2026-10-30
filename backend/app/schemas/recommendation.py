from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class RecommendationResponse(BaseModel):
    id: int
    prediction_id: Optional[int] = None
    soil_record_id: Optional[int] = None
    farmer_id: int
    type: str
    title: str
    description: Optional[str] = None
    priority: Optional[str] = "medium"
    created_at: Optional[datetime] = None
    # Derived for display (not stored separately): why it appears, what to do, which crop, where it came from
    reason: Optional[str] = None
    action: Optional[str] = None
    crop_name: Optional[str] = None
    source_type: Optional[str] = None      # "soil_record" or "prediction"
    source_id: Optional[int] = None
    is_simulated: bool = False             # True when it came from the simulated disease detector

    model_config = ConfigDict(from_attributes=True)
