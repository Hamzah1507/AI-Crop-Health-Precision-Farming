import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.models.prediction import Prediction
from app.models.recommendation import Recommendation
from app.schemas.prediction import PredictionResponse, PredictionListResponse
from app.schemas.recommendation import RecommendationResponse
from app.utils.deps import get_current_user
from app.utils.file_handler import delete_file

settings = get_settings()
router = APIRouter(prefix="/api/predictions", tags=["Predictions"])


@router.get("/", response_model=PredictionListResponse)
def get_predictions(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get prediction history for the current user."""
    total = db.query(Prediction).filter(Prediction.farmer_id == current_user.id).count()
    predictions = (
        db.query(Prediction)
        .filter(Prediction.farmer_id == current_user.id)
        .order_by(Prediction.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return PredictionListResponse(predictions=predictions, total=total)


@router.get("/{prediction_id}", response_model=PredictionResponse)
def get_prediction(
    prediction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific prediction."""
    prediction = db.query(Prediction).filter(
        Prediction.id == prediction_id,
        Prediction.farmer_id == current_user.id
    ).first()
    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return prediction


@router.get("/{prediction_id}/recommendations", response_model=List[RecommendationResponse])
def get_prediction_recommendations(
    prediction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recommendations for a specific prediction."""
    recs = db.query(Recommendation).filter(
        Recommendation.prediction_id == prediction_id,
        Recommendation.farmer_id == current_user.id
    ).all()
    return recs


@router.delete("/{prediction_id}")
def delete_prediction(
    prediction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a prediction and its associated uploaded image."""
    prediction = db.query(Prediction).filter(
        Prediction.id == prediction_id,
        Prediction.farmer_id == current_user.id
    ).first()
    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")

    image_path = prediction.image_path
    db.delete(prediction)
    db.commit()

    if image_path:
        sample_dir = os.path.abspath(settings.SAMPLE_LIBRARY_DIR)
        abs_img = os.path.abspath(image_path)
        # Only delete if file is not part of the read-only sample library
        if not (os.path.exists(sample_dir) and os.path.commonpath([sample_dir, abs_img]) == sample_dir):
            delete_file(image_path)

    return {"message": "Prediction deleted successfully"}
