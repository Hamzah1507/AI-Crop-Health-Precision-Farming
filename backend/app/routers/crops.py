from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.crop import Crop
from app.models.farm import Farm
from app.schemas.crop import CropCreate, CropUpdate, CropResponse
from app.utils.deps import get_current_user
from typing import List

router = APIRouter(prefix="/api/crops", tags=["Crops"])


@router.post("/", response_model=CropResponse)
def create_crop(
    crop_data: CropCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new crop record."""
    # Verify farm belongs to user
    farm = db.query(Farm).filter(Farm.id == crop_data.farm_id, Farm.farmer_id == current_user.id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")

    # Same crop name on the same farm (case-insensitive) is returned, not duplicated
    existing = db.query(Crop).filter(
        Crop.farm_id == crop_data.farm_id,
        func.lower(Crop.name) == crop_data.name.strip().lower()
    ).first()
    if existing:
        return existing

    crop = Crop(
        farm_id=crop_data.farm_id,
        name=crop_data.name.strip(),
        variety=crop_data.variety,
        planting_date=crop_data.planting_date,
        status=crop_data.status
    )
    db.add(crop)
    db.commit()
    db.refresh(crop)
    return crop


@router.get("/", response_model=List[CropResponse])
def get_crops(
    farm_id: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all crops, optionally filtered by farm."""
    query = db.query(Crop).join(Farm).filter(Farm.farmer_id == current_user.id)
    if farm_id:
        query = query.filter(Crop.farm_id == farm_id)
    return query.all()


@router.get("/{crop_id}", response_model=CropResponse)
def get_crop(crop_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get a specific crop."""
    crop = db.query(Crop).join(Farm).filter(Crop.id == crop_id, Farm.farmer_id == current_user.id).first()
    if not crop:
        raise HTTPException(status_code=404, detail="Crop not found")
    return crop


@router.delete("/{crop_id}")
def delete_crop(crop_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a crop."""
    crop = db.query(Crop).join(Farm).filter(Crop.id == crop_id, Farm.farmer_id == current_user.id).first()
    if not crop:
        raise HTTPException(status_code=404, detail="Crop not found")
    db.delete(crop)
    db.commit()
    return {"message": "Crop deleted successfully"}
