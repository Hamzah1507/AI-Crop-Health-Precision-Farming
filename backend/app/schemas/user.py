from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: Optional[str] = "farmer"


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class FarmerProfileBase(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    experience_years: Optional[int] = 0


class FarmerProfileCreate(FarmerProfileBase):
    pass


class FarmerProfileResponse(FarmerProfileBase):
    id: int
    user_id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserWithProfile(UserResponse):
    profile: Optional[FarmerProfileResponse] = None

    model_config = ConfigDict(from_attributes=True)
