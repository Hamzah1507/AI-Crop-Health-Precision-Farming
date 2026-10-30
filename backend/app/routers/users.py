from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.farmer_profile import FarmerProfile
from app.schemas.user import UserResponse, UserWithProfile, FarmerProfileCreate, FarmerProfileResponse
from app.utils.deps import get_current_user
from typing import List

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("/profile", response_model=UserWithProfile)
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current user's profile."""
    return current_user


@router.put("/profile", response_model=FarmerProfileResponse)
def update_profile(
    profile_data: FarmerProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update the farmer profile."""
    profile = db.query(FarmerProfile).filter(FarmerProfile.user_id == current_user.id).first()
    if not profile:
        profile = FarmerProfile(user_id=current_user.id)
        db.add(profile)

    if profile_data.full_name is not None:
        profile.full_name = profile_data.full_name
    if profile_data.phone is not None:
        profile.phone = profile_data.phone
    if profile_data.address is not None:
        profile.address = profile_data.address
    if profile_data.experience_years is not None:
        profile.experience_years = profile_data.experience_years

    db.commit()
    db.refresh(profile)
    return profile
