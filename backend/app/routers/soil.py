from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.farm import Farm
from app.models.crop import Crop
from app.models.soil_record import SoilRecord
from app.services.recommendation_service import save_soil_recommendations
from app.schemas.soil import SoilRecordCreate, SoilRecordResponse, SoilAnalysisRequest, SoilHealthResult, SoilLatestResponse
from app.services.soil_service import soil_analysis_service
from app.services.weather_service import fetch_weather, LocationNotFoundError
from app.utils.deps import get_current_user
from typing import List, Optional

router = APIRouter(prefix="/api/soil", tags=["Soil Analysis"])


def _check_ownership(db: Session, user: User, farm_id: Optional[int], crop_id: Optional[int] = None):
    """Reject farm/crop ids that do not belong to the current user."""
    if farm_id is not None:
        if not db.query(Farm).filter(Farm.id == farm_id, Farm.farmer_id == user.id).first():
            raise HTTPException(status_code=404, detail="Farm not found")
    if crop_id is not None:
        if not db.query(Crop).join(Farm).filter(Crop.id == crop_id, Farm.farmer_id == user.id).first():
            raise HTTPException(status_code=404, detail="Crop not found")


@router.post("/records", response_model=SoilRecordResponse)
def create_soil_record(
    data: SoilRecordCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Store a soil record."""
    _check_ownership(db, current_user, data.farm_id, data.crop_id)
    record = SoilRecord(
        farmer_id=current_user.id,
        farm_id=data.farm_id,
        crop_id=data.crop_id,
        ph=data.ph,
        nitrogen=data.nitrogen,
        phosphorus=data.phosphorus,
        potassium=data.potassium,
        moisture=data.moisture
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/records", response_model=List[SoilRecordResponse])
def get_soil_records(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all soil records for the current user."""
    records = db.query(SoilRecord).filter(SoilRecord.farmer_id == current_user.id).order_by(SoilRecord.created_at.desc()).all()
    return records


@router.get("/latest", response_model=SoilLatestResponse)
def get_latest_soil(record_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    A soil record with its rule-based assessment: the latest one (dashboard), or a specific saved
    record when `record_id` is given (used to open the record a recommendation came from).
    Read-only: the existing analysis service is run on the saved values and nothing is stored.
    Only the current user's own records are ever returned.
    """
    query = db.query(SoilRecord).filter(SoilRecord.farmer_id == current_user.id)
    total = query.count()
    if record_id is not None:
        record = query.filter(SoilRecord.id == record_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="Soil record not found")
    else:
        record = query.order_by(SoilRecord.created_at.desc(), SoilRecord.id.desc()).first()
    if not record:
        return SoilLatestResponse(total_records=0)

    result = soil_analysis_service.analyze(
        ph=record.ph, nitrogen=record.nitrogen, phosphorus=record.phosphorus,
        potassium=record.potassium, moisture=record.moisture,
    )
    analysis = {k: result[k] for k in (
        "soil_health_status", "soil_health_score", "health_summary", "detailed_analysis",
        "fertilizer_recommendations", "irrigation_recommendation",
    )}
    return SoilLatestResponse(total_records=total, record=record, analysis=analysis)


@router.post("/analyze", response_model=SoilHealthResult)
async def analyze_soil(
    data: SoilAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyze soil parameters and get rule-based recommendations."""
    _check_ownership(db, current_user, data.farm_id, data.crop_id)

    # Weather is used only when it is live. Fallback placeholder values are
    # ignored so they can never produce fabricated weather alerts.
    weather_data = None
    if data.location:
        try:
            fetched = await fetch_weather(data.location)
            if fetched.get("is_live"):
                weather_data = fetched
        except LocationNotFoundError:
            weather_data = None

    # Store the soil record
    record = SoilRecord(
        farmer_id=current_user.id,
        farm_id=data.farm_id,
        crop_id=data.crop_id,
        ph=data.ph,
        nitrogen=data.nitrogen,
        phosphorus=data.phosphorus,
        potassium=data.potassium,
        moisture=data.moisture
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # Run analysis
    result = soil_analysis_service.analyze(
        ph=data.ph,
        nitrogen=data.nitrogen,
        phosphorus=data.phosphorus,
        potassium=data.potassium,
        moisture=data.moisture,
        crop_name=data.crop_name,
        location=data.location,
        weather=weather_data
    )

    if weather_data:
        result["weather_used"] = {
            "location": weather_data.get("resolved_location") or data.location,
            "temperature": weather_data.get("temperature"),
            "humidity": weather_data.get("humidity"),
            "rainfall": weather_data.get("rainfall"),
            "wind_speed": weather_data.get("wind_speed"),
            "source": weather_data.get("source"),
            "attribution": weather_data.get("attribution"),
        }
        result["weather_alerts"] = result["weather_alerts"] + weather_data.get("forecast_alerts", [])

    # Store explained recommendations (an identical, repeated analysis does not duplicate them)
    created, repeat = save_soil_recommendations(db, current_user.id, record, result, data.crop_name, weather_data)
    result["recommendations_created"] = created
    result["repeat_analysis"] = repeat

    return result
