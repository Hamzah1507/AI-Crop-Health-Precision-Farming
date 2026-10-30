from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class FarmCreate(BaseModel):
    name: str
    location: Optional[str] = None
    area: Optional[float] = None
    area_unit: Optional[str] = "acres"


class FarmUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    area: Optional[float] = None
    area_unit: Optional[str] = None


class FarmResponse(BaseModel):
    id: int
    farmer_id: int
    name: str
    location: Optional[str] = None
    area: Optional[float] = None
    area_unit: Optional[str] = "acres"
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DefaultFarmResponse(BaseModel):
    """Result of ensuring the user has a farm. `farm` is the user's first farm."""
    farm: FarmResponse
    created: bool                 # True only for the call that actually inserted the default farm
    default_farm_name: str
    default_location: str         # also the weather location used when a farm has none
