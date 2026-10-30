from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.farm import Farm
from app.models.weather_record import WeatherRecord
from app.schemas.weather import WeatherRequest, WeatherResponse
from app.services.weather_service import fetch_weather, LocationNotFoundError
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api/weather", tags=["Weather"])


@router.get("/current", response_model=WeatherResponse)
async def current_weather(
    location: str,
    current_user: User = Depends(get_current_user),
):
    """
    Read-only weather lookup for the dashboard summary. Same data as /fetch
    (live Open-Meteo values, or clearly flagged fallback placeholders), but nothing is stored.
    """
    location = location.strip()
    if not location:
        raise HTTPException(status_code=400, detail="Enter a location")
    try:
        return await fetch_weather(location)
    except LocationNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Could not find a place called '{location}'. Try a nearby city, e.g. 'Pune' or 'Pune, India'."
        )


@router.post("/fetch", response_model=WeatherResponse)
async def get_weather(
    data: WeatherRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fetch current weather and a short forecast for a location (Open-Meteo).

    Live results are stored as a weather record. Fallback placeholder values
    (returned only when the external service is unreachable) are never stored.
    """
    location = data.location.strip()
    if not location:
        raise HTTPException(status_code=400, detail="Enter a location")

    if data.farm_id is not None:
        farm = db.query(Farm).filter(Farm.id == data.farm_id, Farm.farmer_id == current_user.id).first()
        if not farm:
            raise HTTPException(status_code=404, detail="Farm not found")

    try:
        weather_data = await fetch_weather(location)
    except LocationNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Could not find a place called '{location}'. Try a nearby city, e.g. 'Pune' or 'Pune, India'."
        )

    response = dict(weather_data)
    if weather_data["is_live"]:
        record = WeatherRecord(
            farmer_id=current_user.id,
            farm_id=data.farm_id,
            location=location,
            temperature=weather_data.get("temperature"),
            humidity=weather_data.get("humidity"),
            rainfall=weather_data.get("rainfall"),
            wind_speed=weather_data.get("wind_speed"),
            description=weather_data.get("description"),
            condition=weather_data.get("condition")
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        response["id"] = record.id
        response["recorded_at"] = record.recorded_at

    return response
