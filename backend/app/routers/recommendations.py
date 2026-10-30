from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models.user import User
from app.models.recommendation import Recommendation
from app.models.soil_record import SoilRecord
from app.schemas.recommendation import RecommendationResponse
from app.services.recommendation_service import parse_description
from app.utils.deps import get_current_user
from typing import List

router = APIRouter(prefix="/api/recommendations", tags=["Recommendations"])


def to_response(rec: Recommendation) -> RecommendationResponse:
    """Add the derived display fields (reason, action, crop, source, simulated flag) to a stored recommendation."""
    reason, action, crop = parse_description(rec.description)
    if not crop and rec.soil_record is not None and rec.soil_record.crop is not None:
        crop = rec.soil_record.crop.name
    if not crop and rec.prediction is not None:
        crop = rec.prediction.crop_name
    response = RecommendationResponse.model_validate(rec)
    response.reason, response.action, response.crop_name = reason, action, crop
    if rec.prediction_id is not None:
        response.source_type, response.source_id = "prediction", rec.prediction_id
        response.is_simulated = bool(rec.prediction is not None and rec.prediction.is_demo == "true")
    elif rec.soil_record_id is not None:
        response.source_type, response.source_id = "soil_record", rec.soil_record_id
    return response


def _query(db: Session, user: User):
    return (db.query(Recommendation)
            .options(joinedload(Recommendation.prediction), joinedload(Recommendation.soil_record).joinedload(SoilRecord.crop))
            .filter(Recommendation.farmer_id == user.id))


@router.get("/", response_model=List[RecommendationResponse])
def get_recommendations(
    type: str = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the current user's recommendations, newest first, optionally filtered by category."""
    query = _query(db, current_user)
    if type:
        query = query.filter(Recommendation.type == type)
    rows = query.order_by(Recommendation.created_at.desc(), Recommendation.id.desc()).limit(max(1, min(limit, 200))).all()
    return [to_response(r) for r in rows]


@router.get("/recent", response_model=List[RecommendationResponse])
def get_recent_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recent recommendations."""
    rows = _query(db, current_user).order_by(Recommendation.created_at.desc(), Recommendation.id.desc()).limit(10).all()
    return [to_response(r) for r in rows]
