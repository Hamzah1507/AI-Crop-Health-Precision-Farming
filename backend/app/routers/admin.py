from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.user import User
from app.models.farmer_profile import FarmerProfile
from app.models.prediction import Prediction
from app.models.yield_prediction import YieldPrediction
from app.models.recommendation import Recommendation
from app.models.farm import Farm
from app.models.crop import Crop
from app.models.soil_record import SoilRecord
from app.utils.deps import get_current_admin
from typing import List

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/stats")
def get_admin_stats(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get system-wide statistics for admin dashboard."""
    total_users = db.query(User).count()
    total_farmers = db.query(User).filter(User.role == "farmer").count()
    total_predictions = db.query(Prediction).count()
    total_yield_predictions = db.query(YieldPrediction).count()
    total_farms = db.query(Farm).count()
    total_crops = db.query(Crop).count()
    total_soil_records = db.query(SoilRecord).count()
    total_recommendations = db.query(Recommendation).count()
    active_users = db.query(User).filter(User.is_active == True).count()

    # Disease distribution
    disease_stats = (
        db.query(Prediction.disease_name, func.count(Prediction.id))
        .filter(Prediction.disease_name.isnot(None))
        .group_by(Prediction.disease_name)
        .all()
    )

    # Crop distribution
    crop_stats = (
        db.query(Prediction.crop_name, func.count(Prediction.id))
        .filter(Prediction.crop_name.isnot(None))
        .group_by(Prediction.crop_name)
        .all()
    )

    # Recent predictions
    recent_predictions = (
        db.query(Prediction)
        .order_by(Prediction.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "total_users": total_users,
        "total_farmers": total_farmers,
        "active_users": active_users,
        "total_predictions": total_predictions,
        "total_yield_predictions": total_yield_predictions,
        "total_farms": total_farms,
        "total_crops": total_crops,
        "total_soil_records": total_soil_records,
        "total_recommendations": total_recommendations,
        "disease_distribution": [{"name": name, "count": count} for name, count in disease_stats],
        "crop_distribution": [{"name": name, "count": count} for name, count in crop_stats],
        "recent_predictions": [
            {
                "id": p.id,
                "farmer_id": p.farmer_id,
                "crop_name": p.crop_name,
                "disease_name": p.disease_name,
                "pest_name": p.pest_name,
                "confidence": p.confidence,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in recent_predictions
        ]
    }


@router.get("/users")
def get_all_users(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all users."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    result = []
    for user in users:
        profile = db.query(FarmerProfile).filter(FarmerProfile.user_id == user.id).first()
        farm_count = db.query(Farm).filter(Farm.farmer_id == user.id).count()
        prediction_count = db.query(Prediction).filter(Prediction.farmer_id == user.id).count()
        result.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "full_name": profile.full_name if profile else None,
            "phone": profile.phone if profile else None,
            "farm_count": farm_count,
            "prediction_count": prediction_count,
        })
    return result


@router.get("/predictions")
def get_all_predictions(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all predictions system-wide."""
    predictions = (
        db.query(Prediction)
        .order_by(Prediction.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": p.id,
            "farmer_id": p.farmer_id,
            "crop_name": p.crop_name,
            "disease_name": p.disease_name,
            "pest_name": p.pest_name,
            "prediction_type": p.prediction_type,
            "confidence": p.confidence,
            "status": p.status,
            "is_demo": p.is_demo,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in predictions
    ]


@router.put("/users/{user_id}/toggle-active")
def toggle_user_active(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Toggle user active status."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    user.is_active = not user.is_active
    db.commit()
    return {"message": f"User {'activated' if user.is_active else 'deactivated'} successfully", "is_active": user.is_active}
