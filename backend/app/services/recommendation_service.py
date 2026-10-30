"""
Builds and stores recommendations from the app's rule-based assessments.

Every recommendation carries:
  - a title,
  - the REASON it appears (which measurement or condition triggered it, against which reference range),
  - a SUGGESTED ACTION (general guidance; never an exact chemical dosage),
  - optionally the crop it concerns,
  - a priority.

These are stored in the existing `recommendations` table. The reason/action/crop are kept in `description`
as labelled lines so no schema change is needed; `parse_description` reads them back.

Types: fertilizer, irrigation, soil, weather (from the soil analysis), treatment (from a leaf scan).
Treatments from the simulated detector are always labelled as such.
"""
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.recommendation import Recommendation
from app.models.soil_record import SoilRecord
from app.services.soil_service import soil_analysis_service

REASON, ACTION, CROP = "Reason:", "Suggested action:", "Crop:"
NUTRIENTS = ("nitrogen", "phosphorus", "potassium")
LABELS = {"ph": "Soil pH", "nitrogen": "Nitrogen", "phosphorus": "Phosphorus", "potassium": "Potassium", "moisture": "Soil moisture"}
UNITS = {"ph": "", "nitrogen": " kg/ha", "phosphorus": " kg/ha", "potassium": " kg/ha", "moisture": "%"}
CONFIRM = "Confirm products and quantities with a soil test or your local agronomist."


def compose(reason: str, action: str, crop: Optional[str] = None) -> str:
    text = f"{REASON} {reason}\n{ACTION} {action}"
    return f"{text}\n{CROP} {crop}" if crop else text


def parse_description(text: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """(reason, action, crop). Older records without labels are returned whole as the reason."""
    if not text:
        return None, None, None
    reason = action = crop = None
    for line in text.splitlines():
        if line.startswith(REASON):
            reason = line[len(REASON):].strip()
        elif line.startswith(ACTION):
            action = line[len(ACTION):].strip()
        elif line.startswith(CROP):
            crop = line[len(CROP):].strip()
    if reason is None and action is None:
        return text, None, None
    return reason, action, crop


def _range_text(key: str) -> str:
    r = soil_analysis_service.OPTIMAL_RANGES[key]
    return f"{r['min']}-{r['max']}{UNITS[key]}"


def build_soil_recommendations(result: Dict, crop_name: Optional[str] = None, weather: Optional[Dict] = None) -> List[Dict]:
    """Turn one soil analysis result into explained recommendations (pure function)."""
    detail = result.get("detailed_analysis", {}) or {}
    crop = crop_name.strip() if crop_name and crop_name.strip() else None
    n_need = (soil_analysis_service.CROP_SUITABILITY.get(crop.lower(), {}) or {}).get("n_need") if crop else None
    recs: List[Dict] = []

    fertilizers = result.get("fertilizer_recommendations", []) or []
    for f in fertilizers:
        reason = f.get("reason", "")
        name = f.get("fertilizer", "Fertilizer recommendation")
        if crop and n_need and any(w in name for w in ("Urea", "Ammonium")):
            reason += f" {crop} generally has a {n_need} nitrogen requirement, so this matters for it."
        recs.append({"type": "fertilizer", "title": name, "reason": reason,
                     "action": f"{f.get('application', 'Apply according to crop requirements')}. {CONFIRM}",
                     "priority": f.get("priority", "medium")})

    irr = result.get("irrigation_recommendation") or {}
    if irr and irr.get("status") != "Unknown":
        recs.append({"type": "irrigation", "title": irr.get("status", "Irrigation guidance"), "reason": irr.get("recommendation", ""),
                     "action": irr.get("schedule", "Re-check soil moisture regularly."), "priority": irr.get("priority", "medium")})

    ph = detail.get("ph")
    amended = any(("Lime" in f.get("fertilizer", "") or "Gypsum" in f.get("fertilizer", "")) for f in fertilizers)
    if ph and ph["status"] != "Optimal" and not amended:
        recs.append({"type": "soil", "title": f"Soil pH is {ph['status'].lower()} ({ph['value']})",
                     "reason": f"Soil pH outside the {_range_text('ph')} reference range can reduce how well crops take up nutrients.",
                     "action": f"{ph['action']}. Confirm with a laboratory soil test before amending the soil.", "priority": "medium"})

    for key in NUTRIENTS:
        d = detail.get(key)
        if d and d["status"] == "High":
            recs.append({"type": "soil", "title": f"{LABELS[key]} is high ({d['value']}{UNITS[key]})",
                         "reason": f"{LABELS[key]} is above the {_range_text(key)} reference range.",
                         "action": f"{d['action']}. {CONFIRM}", "priority": "low"})

    if detail and all(d["status"] == "Optimal" for d in detail.values()):
        plain = {"ph": "pH", "nitrogen": "nitrogen", "phosphorus": "phosphorus", "potassium": "potassium", "moisture": "soil moisture"}
        parts = [f"{plain[k]} {d['value']}{UNITS[k]} (reference {_range_text(k)})" for k, d in detail.items()]
        recs.append({"type": "soil", "title": "Measurements are within the reference ranges",
                     "reason": "All provided measurements fall inside the ranges used by this app: " + "; ".join(parts) + ".",
                     "action": "Keep monitoring and re-test after the crop cycle or whenever conditions change.", "priority": "low"})

    if weather and weather.get("is_live"):
        place = weather.get("resolved_location") or weather.get("location")
        for alert in (weather.get("forecast_alerts") or [])[:3]:
            head, _, tail = alert.partition(":")
            recs.append({"type": "weather", "title": head.strip(), "reason": f"From the live Open-Meteo forecast for {place}.",
                         "action": tail.strip() or head.strip(), "priority": "medium"})
    return recs


def save_soil_recommendations(db: Session, farmer_id: int, record: SoilRecord, result: Dict,
                              crop_name: Optional[str] = None, weather: Optional[Dict] = None, created_at=None) -> Tuple[int, bool]:
    """
    Store the recommendations for a saved soil record. Returns (number created, is_repeat).

    If the same measurements (same farm, identical values) were analysed before, any recommendation
    already stored for that earlier analysis is not created again.
    """
    candidates = build_soil_recommendations(result, crop_name, weather)
    identical = db.query(SoilRecord.id).filter(
        SoilRecord.farmer_id == farmer_id, SoilRecord.id != record.id, SoilRecord.farm_id == record.farm_id,
        SoilRecord.ph == record.ph, SoilRecord.nitrogen == record.nitrogen, SoilRecord.phosphorus == record.phosphorus,
        SoilRecord.potassium == record.potassium, SoilRecord.moisture == record.moisture,
    ).all()
    earlier_ids = [row[0] for row in identical]
    seen = set()
    if earlier_ids:
        for r in db.query(Recommendation).filter(Recommendation.soil_record_id.in_(earlier_ids)):
            seen.add((r.type, r.title, r.description))

    created = 0
    for c in candidates:
        description = compose(c["reason"], c["action"], crop_name.strip() if crop_name and crop_name.strip() else None)
        key = (c["type"], c["title"], description)
        if key in seen:
            continue
        seen.add(key)
        extra = {"created_at": created_at} if created_at is not None else {}
        db.add(Recommendation(soil_record_id=record.id, farmer_id=farmer_id, type=c["type"], title=c["title"][:200],
                              description=description, priority=c["priority"], **extra))
        created += 1
    db.commit()
    return created, bool(earlier_ids)


def save_treatment_recommendation(db: Session, farmer_id: int, prediction, result: Dict, created_at=None) -> Optional[Recommendation]:
    """Store the treatment or care guidance for a leaf scan. Simulated-detector results are labelled as such."""
    treatment = result.get("treatment")
    target = result.get("disease_name") or result.get("pest_name") or "Unknown"
    pred_type = result.get("prediction_type") or getattr(prediction, "prediction_type", "")
    pred_status = result.get("status") or getattr(prediction, "status", "")

    # Strictly prevent disease-specific chemical treatment recommendations for uncertain or rejected predictions
    if (
        not treatment
        or pred_type in ("unable_to_identify", "uncertain")
        or pred_status == "uncertain"
        or "unable to identify" in target.lower()
    ):
        return None
    simulated = result.get("is_demo") == "true"
    is_healthy = target.lower() in ("healthy plant", "healthy")

    if is_healthy:
        title = f"Care Guidance for Healthy Plant{' (simulated detection)' if simulated else ''}"
        priority = "low"
        if simulated:
            from app.ml.model_service import model_service
            if model_service.model_loaded:
                crop_lbl = f"'{prediction.crop_name}'" if prediction.crop_name else "this crop"
                reason = f"Demonstration advisory: {crop_lbl} is not currently supported by the active ResNet-18 model; this confirms the simulated healthy condition."
            else:
                reason = "Simulated detection: no trained model is loaded, so this confirms the simulated healthy condition."
        else:
            reason = "Genuine AI model inference detected no symptoms of disease or pest infestation."
        action = treatment or "Continue standard crop care, balanced irrigation, and routine scouting."
    else:
        title = f"Treatment for {target}{' (simulated detection)' if simulated else ''}"[:200]
        priority = "medium" if simulated else "high"
        if simulated:
            from app.ml.model_service import model_service
            if model_service.model_loaded:
                crop_lbl = f"'{prediction.crop_name}'" if prediction.crop_name else "this crop"
                reason = f"Demonstration advisory: {crop_lbl} is not currently supported by the active ResNet-18 model; this is general guidance for the label shown, not a diagnosis."
            else:
                reason = "Simulated detection: no trained model is loaded, so this is general guidance for the label shown, not a diagnosis."
        else:
            reason = f"Based on the detection of {target} in the uploaded image."
        advisory_suffix = "Advisory: Confirm with a local agronomist before applying chemical treatments."
        action = f"{treatment.rstrip('.')}. {advisory_suffix}" if advisory_suffix not in treatment else treatment

    extra = {"created_at": created_at} if created_at is not None else {}
    rec = Recommendation(
        prediction_id=prediction.id,
        farmer_id=farmer_id,
        type="treatment",
        title=title,
        description=compose(reason, action, prediction.crop_name),
        priority=priority,
        **extra
    )
    db.add(rec)
    db.commit()
    return rec
