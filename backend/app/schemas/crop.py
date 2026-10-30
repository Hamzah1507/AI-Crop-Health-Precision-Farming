from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime, date


class CropCreate(BaseModel):
    farm_id: int
    name: str
    variety: Optional[str] = None
    planting_date: Optional[date] = None
    status: Optional[str] = "active"


class CropUpdate(BaseModel):
    name: Optional[str] = None
    variety: Optional[str] = None
    planting_date: Optional[date] = None
    status: Optional[str] = None


class CropResponse(BaseModel):
    id: int
    farm_id: int
    name: str
    variety: Optional[str] = None
    planting_date: Optional[date] = None
    status: Optional[str] = "active"
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
