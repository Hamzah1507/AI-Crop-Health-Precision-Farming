from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session
import logging
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.crop import Crop
from app.models.farm import Farm
from app.models.prediction import Prediction
from app.services.recommendation_service import save_treatment_recommendation
from app.schemas.prediction import PredictionResponse
from app.ml.model_service import model_service, ModelInferenceError
from app.ml.image_preprocessing import image_preprocessor, OPENCV_AVAILABLE
from app.utils.deps import get_current_user
from app.utils.file_handler import validate_and_save_image, delete_file, safe_display_name
from app.utils.rate_limiter import rate_limit_detection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/detection", tags=["Disease & Pest Detection"])


@router.post("/predict", response_model=PredictionResponse, dependencies=[Depends(rate_limit_detection)])
async def detect_disease(
    file: UploadFile = File(...),
    crop_name: Optional[str] = Form(None),
    crop_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a crop leaf image and detect diseases/pests.
    Uses YOLOv8/TensorFlow model if available. Otherwise the result is a
    clearly identified demonstration fallback (is_demo="true"), not a real detection.
    """
    # 1. Authorize crop ownership BEFORE touching file storage
    if crop_id is not None:
        owned = db.query(Crop).join(Farm).filter(Crop.id == crop_id, Farm.farmer_id == current_user.id).first()
        if not owned:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crop not found")
        crop_name = (crop_name.strip() if crop_name and crop_name.strip() else None) or owned.name
    elif crop_name:
        crop_name = crop_name.strip() if crop_name.strip() else None

    # 2. Validate and stream image to storage
    image_path = await validate_and_save_image(file)

    # 3. Verify decodability and validate that image contains crop leaf foliage
    if OPENCV_AVAILABLE:
        if image_preprocessor.preprocess(image_path) is None:
            delete_file(image_path)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not read the uploaded file as an image")

        is_leaf, leaf_reason = image_preprocessor.validate_crop_leaf(image_path)
        if not is_leaf:
            delete_file(image_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unable to identify a crop leaf in the uploaded image. {leaf_reason}"
            )

    # 4. Run prediction and persist to database safely
    try:
        result = model_service.predict(image_path, crop_name)

        # Reject out-of-distribution or crop mismatch results that could not be identified
        if result.get("prediction_type") == "unable_to_identify":
            delete_file(image_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("treatment", "Unable to identify a crop leaf in the uploaded image. Please upload a clear photo of a crop leaf.")
            )

        prediction = Prediction(
            farmer_id=current_user.id,
            crop_id=crop_id,
            image_path=image_path,
            original_filename=safe_display_name(file.filename),
            crop_name=crop_name,
            disease_name=result.get("disease_name"),
            pest_name=result.get("pest_name"),
            prediction_type=result.get("prediction_type", "disease"),
            confidence=result.get("confidence"),
            bbox_data=result.get("bbox_data"),
            status=result.get("status", "completed"),
            is_demo=result.get("is_demo", "true")
        )
        db.add(prediction)
        db.commit()
        db.refresh(prediction)

        # Store the treatment guidance (labelled as simulated when no trained model produced the result)
        try:
            save_treatment_recommendation(db, current_user.id, prediction, result)
        except Exception as rec_err:
            logger.warning(f"Failed to record treatment recommendation for prediction {prediction.id}: {rec_err}")

        return prediction
    except ModelInferenceError as err:
        db.rollback()
        delete_file(image_path)
        logger.error(f"Inference error during disease detection: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Detection model inference failed: {str(err)}"
        )
    except HTTPException:
        db.rollback()
        delete_file(image_path)
        raise
    except Exception as err:
        db.rollback()
        delete_file(image_path)
        logger.error(f"Unexpected error during disease detection: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process image prediction. Please try again."
        )


@router.get("/status")
def model_status():
    """Get the current ML model status."""
    return model_service.get_status()
