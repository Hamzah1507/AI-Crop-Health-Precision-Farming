from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, insert, select, exists, literal
from sqlalchemy.orm import Session
from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.models.farm import Farm
from app.schemas.farm import FarmCreate, FarmUpdate, FarmResponse, DefaultFarmResponse
from app.utils.deps import get_current_user
from typing import List

router = APIRouter(prefix="/api/farms", tags=["Farms"])


@router.post("/default", response_model=DefaultFarmResponse)
def ensure_default_farm(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Make sure the current user has a farm, creating the default one only if they have none.

    - Idempotent: a user who already has any farm is left exactly as they are, and a farm's
      location is never overwritten.
    - Race-safe: the insert is a single `INSERT ... SELECT ... WHERE NOT EXISTS` statement, so
      simultaneous calls (for example React StrictMode's double effect) cannot both insert.
    - Only the user's own rows are read or written. No area is set (it would be an invented value).
    """
    settings = get_settings()

    def first_farm():
        return db.query(Farm).filter(Farm.farmer_id == current_user.id).order_by(Farm.id).first()

    farm = first_farm()
    created = False
    if farm is None:
        statement = insert(Farm).from_select(
            ["farmer_id", "name", "location", "area_unit"],
            select(
                literal(current_user.id), literal(settings.DEFAULT_FARM_NAME),
                literal(settings.DEFAULT_FARM_LOCATION), literal("acres"),
            ).where(~exists().where(Farm.farmer_id == current_user.id)),
        )
        result = db.execute(statement)
        db.commit()
        created = result.rowcount == 1          # 0 means a concurrent call inserted it first
        farm = first_farm()

    return DefaultFarmResponse(
        farm=farm, created=created,
        default_farm_name=settings.DEFAULT_FARM_NAME,
        default_location=settings.DEFAULT_FARM_LOCATION,
    )


@router.post("/", response_model=FarmResponse)
def create_farm(
    farm_data: FarmCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new farm. If the user already has a farm with the same name
    (case-insensitive), that farm is updated and returned instead of creating a duplicate.
    """
    name = farm_data.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Farm name is required")

    existing = db.query(Farm).filter(
        Farm.farmer_id == current_user.id,
        func.lower(Farm.name) == name.lower()
    ).first()
    if existing:
        if farm_data.location:
            existing.location = farm_data.location
        if farm_data.area is not None:
            existing.area = farm_data.area
        if farm_data.area_unit:
            existing.area_unit = farm_data.area_unit
        db.commit()
        db.refresh(existing)
        return existing

    farm = Farm(
        farmer_id=current_user.id,
        name=name,
        location=farm_data.location,
        area=farm_data.area,
        area_unit=farm_data.area_unit
    )
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm


@router.get("/", response_model=List[FarmResponse])
def get_farms(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all farms for the current user."""
    farms = db.query(Farm).filter(Farm.farmer_id == current_user.id).all()
    return farms


@router.get("/{farm_id}", response_model=FarmResponse)
def get_farm(farm_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get a specific farm."""
    farm = db.query(Farm).filter(Farm.id == farm_id, Farm.farmer_id == current_user.id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    return farm


@router.put("/{farm_id}", response_model=FarmResponse)
def update_farm(
    farm_id: int,
    farm_data: FarmUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a farm."""
    farm = db.query(Farm).filter(Farm.id == farm_id, Farm.farmer_id == current_user.id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")

    for field, value in farm_data.model_dump(exclude_unset=True).items():
        setattr(farm, field, value)

    db.commit()
    db.refresh(farm)
    return farm


@router.delete("/{farm_id}")
def delete_farm(farm_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a farm."""
    farm = db.query(Farm).filter(Farm.id == farm_id, Farm.farmer_id == current_user.id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    db.delete(farm)
    db.commit()
    return {"message": "Farm deleted successfully"}
