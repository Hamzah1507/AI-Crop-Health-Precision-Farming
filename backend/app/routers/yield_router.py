from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.yield_prediction import YieldPrediction
from app.schemas.yield_prediction import YieldPredictionRequest, YieldPredictionResponse
from app.services.yield_service import yield_prediction_service
from app.utils.deps import get_current_user
from typing import List

router = APIRouter(prefix="/api/yield", tags=["Crop Yield Prediction"])


@router.post("/predict", response_model=YieldPredictionResponse)
def predict_yield(
    data: YieldPredictionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Predict crop yield based on parameters."""
    result = yield_prediction_service.predict(
        crop_name=data.crop_name,
        area=data.area,
        soil_ph=data.soil_ph,
        soil_nitrogen=data.soil_nitrogen,
        soil_phosphorus=data.soil_phosphorus,
        soil_potassium=data.soil_potassium,
        soil_moisture=data.soil_moisture,
        temperature=data.temperature,
        humidity=data.humidity,
        rainfall=data.rainfall,
        season=data.season
    )

    # Store prediction
    yield_pred = YieldPrediction(
        farmer_id=current_user.id,
        farm_id=data.farm_id,
        crop_name=data.crop_name,
        predicted_yield=result["predicted_yield"],
        yield_unit=result["yield_unit"],
        confidence=result["confidence"],
        area=data.area,
        soil_ph=data.soil_ph,
        soil_nitrogen=data.soil_nitrogen,
        soil_phosphorus=data.soil_phosphorus,
        soil_potassium=data.soil_potassium,
        soil_moisture=data.soil_moisture,
        temperature=data.temperature,
        humidity=data.humidity,
        rainfall=data.rainfall,
        season=data.season,
        is_demo=result.get("is_demo", "true")
    )
    db.add(yield_pred)
    db.commit()
    db.refresh(yield_pred)

    response = YieldPredictionResponse.model_validate(yield_pred)
    response.factors = result.get("factors", [])
    response.model_note = result.get("model_note")
    return response


@router.get("/history", response_model=List[YieldPredictionResponse])
def get_yield_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get yield prediction history."""
    return (
        db.query(YieldPrediction)
        .filter(YieldPrediction.farmer_id == current_user.id)
        .order_by(YieldPrediction.created_at.desc())
        .limit(50)
        .all()
    )
