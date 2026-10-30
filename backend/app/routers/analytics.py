"""
Farm Analytics and Report Data Router.
Provides farmer-scoped, strongly-typed analytics endpoints for dashboards,
trend analysis, and PDF report generation.
"""

from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.user import User
from app.models.farmer_profile import FarmerProfile
from app.models.farm import Farm
from app.models.crop import Crop
from app.models.prediction import Prediction
from app.models.soil_record import SoilRecord
from app.models.yield_prediction import YieldPrediction
from app.models.recommendation import Recommendation
from app.services.soil_service import soil_analysis_service
from app.utils.deps import get_current_user
from app.schemas.analytics import (
    AnalyticsSummaryResponse,
    AnalyticsTrendsResponse,
    AnalyticsReportDataResponse,
    ScansSummary,
    SoilSummary,
    YieldSummary,
    RecommendationSummary,
    SoilTrendPoint,
    ScanTrendPoint,
    YieldTrendPoint,
    ReportFarmerInfo,
    ReportFarmInfo,
    ReportCropInfo,
    ReportPredictionItem,
    ReportSoilItem,
    ReportYieldItem,
    ReportRecommendationItem,
)

router = APIRouter(prefix="/api/analytics", tags=["Farm Analytics & Reports"])


def _verify_farm_ownership(db: Session, user_id: int, farm_id: Optional[int]) -> Optional[Farm]:
    """Ensure farm belongs to the authenticated user. Raises 404 if not found."""
    if farm_id is None:
        return None
    farm = db.query(Farm).filter(Farm.id == farm_id, Farm.farmer_id == user_id).first()
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found or not owned by user")
    return farm


def _parse_iso_date(date_str: Optional[str], param_name: str) -> Optional[datetime]:
    """Safely parse ISO date strings with clear validation error handling."""
    if not date_str or not date_str.strip():
        return None
    try:
        # Accepts YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS
        clean_str = date_str.strip()
        if len(clean_str) == 10:
            return datetime.strptime(clean_str, "%Y-%m-%d")
        return datetime.fromisoformat(clean_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {param_name} format. Expected ISO-8601 format (e.g. '2026-10-29' or '2026-10-29T00:00:00')."
        )


@router.get("/summary", response_model=AnalyticsSummaryResponse)
def get_farmer_analytics_summary(
    farm_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get aggregated overview metrics scoped strictly to the authenticated farmer.
    Returns counts, ratios, soil health score, and yield summary.
    """
    _verify_farm_ownership(db, current_user.id, farm_id)

    # 1. Farms and crops count
    if farm_id is not None:
        total_farms = 1
        total_crops = db.query(Crop).filter(Crop.farm_id == farm_id).count()
        farm = db.query(Farm).filter(Farm.id == farm_id).first()
        total_area = farm.area if farm else None
        area_unit = (farm.area_unit if farm and farm.area_unit else "acres")
    else:
        total_farms = db.query(Farm).filter(Farm.farmer_id == current_user.id).count()
        total_crops = db.query(Crop).join(Farm).filter(Farm.farmer_id == current_user.id).count()
        area_sum = db.query(func.sum(Farm.area)).filter(Farm.farmer_id == current_user.id).scalar()
        total_area = round(float(area_sum), 2) if area_sum is not None else None
        area_unit = "acres"

    # 2. Scans breakdown
    user_farms = db.query(Farm).filter(Farm.farmer_id == current_user.id).all()
    total_user_farms = len(user_farms)
    farm_scans_count = 0
    unassigned_scans_count = 0

    if farm_id is not None:
        farm_crop_ids = [c.id for c in db.query(Crop.id).filter(Crop.farm_id == farm_id).all()]
        other_farm_crop_ids = [
            c.id for c in db.query(Crop.id).join(Farm).filter(Farm.farmer_id == current_user.id, Farm.id != farm_id).all()
        ]

        if total_user_farms <= 1:
            # Sole farm holding: all predictions of this farmer belong to this sole farm
            pred_query = db.query(Prediction).filter(Prediction.farmer_id == current_user.id)
            farm_scans_count = pred_query.count()
            unassigned_scans_count = 0
        else:
            # Multi-farm:
            # Farm-specific scans (linked to crops on this farm)
            farm_pred_q = db.query(Prediction).filter(
                Prediction.farmer_id == current_user.id,
                Prediction.crop_id.in_(farm_crop_ids) if farm_crop_ids else False
            )
            farm_scans_count = farm_pred_q.count()

            unassigned_q = db.query(Prediction).filter(
                Prediction.farmer_id == current_user.id,
                Prediction.crop_id.is_(None)
            )
            unassigned_scans_count = unassigned_q.count()

            if farm_scans_count > 0:
                pred_query = farm_pred_q
            else:
                pred_query = db.query(Prediction).filter(
                    Prediction.farmer_id == current_user.id,
                    ~Prediction.crop_id.in_(other_farm_crop_ids) if other_farm_crop_ids else True
                )
    else:
        pred_query = db.query(Prediction).filter(Prediction.farmer_id == current_user.id)
        farm_scans_count = pred_query.filter(Prediction.crop_id.isnot(None)).count()
        unassigned_scans_count = pred_query.filter(Prediction.crop_id.is_(None)).count()

    total_scans = pred_query.count()
    healthy_count = pred_query.filter(Prediction.disease_name == "Healthy Plant").count()
    pest_count = pred_query.filter(Prediction.prediction_type == "pest").count()
    diseased_count = pred_query.filter(
        Prediction.disease_name.isnot(None),
        Prediction.disease_name != "Healthy Plant",
        Prediction.prediction_type != "uncertain",
        Prediction.status != "uncertain",
        ~Prediction.disease_name.like("%Unable to Identify%")
    ).count()
    demo_scans = pred_query.filter(Prediction.is_demo == "true").count()
    genuine_scans = max(0, total_scans - demo_scans)

    scans_summary = ScansSummary(
        total_scans=total_scans,
        healthy_count=healthy_count,
        diseased_count=diseased_count,
        pest_count=pest_count,
        demo_scans=demo_scans,
        genuine_scans=genuine_scans,
        farm_scans=farm_scans_count,
        unassigned_scans=unassigned_scans_count,
    )

    # 3. Latest soil measurement & assessment
    soil_query = db.query(SoilRecord).filter(SoilRecord.farmer_id == current_user.id)
    if farm_id is not None:
        soil_query = soil_query.filter(SoilRecord.farm_id == farm_id)

    latest_soil = soil_query.order_by(SoilRecord.created_at.desc(), SoilRecord.id.desc()).first()
    soil_summary = None
    if latest_soil:
        parameters = {
            "ph": latest_soil.ph,
            "nitrogen": latest_soil.nitrogen,
            "phosphorus": latest_soil.phosphorus,
            "potassium": latest_soil.potassium,
            "moisture": latest_soil.moisture,
        }
        provided_count = sum(1 for v in parameters.values() if v is not None)
        is_sufficient = provided_count >= 3

        analysis = soil_analysis_service.analyze(
            ph=latest_soil.ph,
            nitrogen=latest_soil.nitrogen,
            phosphorus=latest_soil.phosphorus,
            potassium=latest_soil.potassium,
            moisture=latest_soil.moisture,
        )
        soil_health_score_val = None
        if is_sufficient and analysis.get("soil_health_score") is not None:
            soil_health_score_val = int(round(analysis.get("soil_health_score")))

        soil_summary = SoilSummary(
            record_id=latest_soil.id,
            recorded_at=latest_soil.created_at.isoformat() if latest_soil.created_at else None,
            ph=latest_soil.ph,
            nitrogen=latest_soil.nitrogen,
            phosphorus=latest_soil.phosphorus,
            potassium=latest_soil.potassium,
            moisture=latest_soil.moisture,
            soil_health_score=soil_health_score_val,
            soil_health_status=analysis.get("soil_health_status") if is_sufficient else "Insufficient Data",
            measured_parameters_count=provided_count,
            is_sufficient=is_sufficient,
        )

    # 4. Yield estimate aggregations
    yield_query = db.query(YieldPrediction).filter(YieldPrediction.farmer_id == current_user.id)
    if farm_id is not None:
        yield_query = yield_query.filter(YieldPrediction.farm_id == farm_id)

    yield_stats = yield_query.with_entities(
        func.count(YieldPrediction.id),
        func.min(YieldPrediction.predicted_yield),
        func.max(YieldPrediction.predicted_yield),
        func.avg(YieldPrediction.predicted_yield),
    ).first()

    total_yield_estimates = yield_stats[0] if yield_stats else 0
    min_yield = round(float(yield_stats[1]), 2) if yield_stats and yield_stats[1] is not None else None
    max_yield = round(float(yield_stats[2]), 2) if yield_stats and yield_stats[2] is not None else None
    avg_yield = round(float(yield_stats[3]), 2) if yield_stats and yield_stats[3] is not None else None

    # Determine predominant yield unit
    latest_yield = yield_query.order_by(YieldPrediction.created_at.desc()).first()
    yield_unit = latest_yield.yield_unit if latest_yield and latest_yield.yield_unit else "tons/hectare"

    yields_summary = YieldSummary(
        total_estimates=total_yield_estimates,
        min_yield=min_yield,
        max_yield=max_yield,
        avg_yield=avg_yield,
        yield_unit=yield_unit,
    )

    # 5. Recommendations counts
    rec_query = db.query(Recommendation).filter(Recommendation.farmer_id == current_user.id)
    if farm_id is not None and total_user_farms > 1:
        other_farm_soil_ids = [
            s.id for s in db.query(SoilRecord.id).filter(
                SoilRecord.farmer_id == current_user.id, SoilRecord.farm_id != farm_id
            ).all()
        ]
        other_farm_crop_ids = [
            c.id for c in db.query(Crop.id).join(Farm).filter(
                Farm.farmer_id == current_user.id, Farm.id != farm_id
            ).all()
        ]
        other_pred_ids = (
            [p.id for p in db.query(Prediction.id).filter(
                Prediction.farmer_id == current_user.id, Prediction.crop_id.in_(other_farm_crop_ids)
            ).all()]
            if other_farm_crop_ids
            else []
        )
        if other_farm_soil_ids:
            rec_query = rec_query.filter(~Recommendation.soil_record_id.in_(other_farm_soil_ids))
        if other_pred_ids:
            rec_query = rec_query.filter(~Recommendation.prediction_id.in_(other_pred_ids))

    total_recs = rec_query.count()

    priority_rows = (
        rec_query.with_entities(Recommendation.priority, func.count(Recommendation.id))
        .group_by(Recommendation.priority)
        .all()
    )
    by_priority = {p or "medium": c for p, c in priority_rows}

    type_rows = (
        rec_query.with_entities(Recommendation.type, func.count(Recommendation.id))
        .group_by(Recommendation.type)
        .all()
    )
    by_type = {t or "general": c for t, c in type_rows}

    recs_summary = RecommendationSummary(
        total=total_recs,
        by_priority=by_priority,
        by_type=by_type,
    )

    return AnalyticsSummaryResponse(
        total_farms=total_farms,
        total_crops=total_crops,
        total_farm_area=total_area,
        area_unit=area_unit,
        scans=scans_summary,
        soil=soil_summary,
        yields=yields_summary,
        recommendations=recs_summary,
    )


@router.get("/trends", response_model=AnalyticsTrendsResponse)
def get_farmer_analytics_trends(
    farm_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get chronological trend series for soil parameters, disease scans, and yield estimates.
    Scoped strictly to the authenticated user with optional farm and date filters.
    """
    _verify_farm_ownership(db, current_user.id, farm_id)
    start_dt = _parse_iso_date(start_date, "start_date")
    end_dt = _parse_iso_date(end_date, "end_date")

    # 1. Soil trends
    soil_q = db.query(SoilRecord).filter(SoilRecord.farmer_id == current_user.id)
    if farm_id is not None:
        soil_q = soil_q.filter(SoilRecord.farm_id == farm_id)
    if start_dt:
        soil_q = soil_q.filter(SoilRecord.created_at >= start_dt)
    if end_dt:
        soil_q = soil_q.filter(SoilRecord.created_at <= end_dt)
    soil_rows = soil_q.order_by(SoilRecord.created_at.asc()).limit(limit).all()

    soil_trends = [
        SoilTrendPoint(
            id=r.id,
            date=r.created_at.isoformat() if r.created_at else "",
            ph=r.ph,
            nitrogen=r.nitrogen,
            phosphorus=r.phosphorus,
            potassium=r.potassium,
            moisture=r.moisture,
            farm_id=r.farm_id,
        )
        for r in soil_rows
    ]

    # 2. Scan trends
    user_farms = db.query(Farm).filter(Farm.farmer_id == current_user.id).all()
    total_user_farms = len(user_farms)

    scan_q = db.query(Prediction).filter(Prediction.farmer_id == current_user.id)
    if farm_id is not None:
        if total_user_farms <= 1:
            pass  # Sole farm holding: all predictions of this farmer belong to this sole farm
        else:
            farm_crop_ids = [c.id for c in db.query(Crop.id).filter(Crop.farm_id == farm_id).all()]
            other_farm_crop_ids = [
                c.id for c in db.query(Crop.id).join(Farm).filter(Farm.farmer_id == current_user.id, Farm.id != farm_id).all()
            ]
            farm_pred_count = scan_q.filter(Prediction.crop_id.in_(farm_crop_ids)).count() if farm_crop_ids else 0
            if farm_pred_count > 0:
                scan_q = scan_q.filter(Prediction.crop_id.in_(farm_crop_ids))
            else:
                scan_q = scan_q.filter(~Prediction.crop_id.in_(other_farm_crop_ids) if other_farm_crop_ids else True)

    if start_dt:
        scan_q = scan_q.filter(Prediction.created_at >= start_dt)
    if end_dt:
        scan_q = scan_q.filter(Prediction.created_at <= end_dt)
    scan_rows = scan_q.order_by(Prediction.created_at.asc()).limit(limit).all()

    scan_trends = [
        ScanTrendPoint(
            id=p.id,
            date=p.created_at.isoformat() if p.created_at else "",
            crop_name=p.crop_name,
            disease_name=p.disease_name,
            pest_name=p.pest_name,
            prediction_type=p.prediction_type or "disease",
            confidence=p.confidence,
            is_demo=p.is_demo or "false",
        )
        for p in scan_rows
    ]

    # 3. Yield trends
    yield_q = db.query(YieldPrediction).filter(YieldPrediction.farmer_id == current_user.id)
    if farm_id is not None:
        yield_q = yield_q.filter(YieldPrediction.farm_id == farm_id)
    if start_dt:
        yield_q = yield_q.filter(YieldPrediction.created_at >= start_dt)
    if end_dt:
        yield_q = yield_q.filter(YieldPrediction.created_at <= end_dt)
    yield_rows = yield_q.order_by(YieldPrediction.created_at.asc()).limit(limit).all()

    yield_trends = [
        YieldTrendPoint(
            id=y.id,
            date=y.created_at.isoformat() if y.created_at else "",
            crop_name=y.crop_name,
            predicted_yield=y.predicted_yield,
            yield_unit=y.yield_unit or "tons/hectare",
            season=y.season,
            is_demo=y.is_demo or "false",
        )
        for y in yield_rows
    ]

    return AnalyticsTrendsResponse(
        soil_trends=soil_trends,
        scan_trends=scan_trends,
        yield_trends=yield_trends,
    )


@router.get("/report-data", response_model=AnalyticsReportDataResponse)
def get_farmer_report_data(
    farm_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get consolidated, verified data payload specifically formatted for PDF report compilation.
    Contains farmer profile, selected farm/crops, diagnostic history, soil tests,
    yield estimates, and prioritized recommendations.
    """
    selected_farm_obj = _verify_farm_ownership(db, current_user.id, farm_id)

    # Farmer profile info
    profile = db.query(FarmerProfile).filter(FarmerProfile.user_id == current_user.id).first()
    farmer_info = ReportFarmerInfo(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=profile.full_name if profile and profile.full_name else current_user.username,
    )

    # Farms
    farm_rows = db.query(Farm).filter(Farm.farmer_id == current_user.id).order_by(Farm.name.asc()).all()
    farms_list = [
        ReportFarmInfo(
            id=f.id,
            name=f.name,
            location=f.location,
            area=f.area,
            area_unit=f.area_unit or "acres",
        )
        for f in farm_rows
    ]

    selected_farm_info = None
    if selected_farm_obj:
        selected_farm_info = ReportFarmInfo(
            id=selected_farm_obj.id,
            name=selected_farm_obj.name,
            location=selected_farm_obj.location,
            area=selected_farm_obj.area,
            area_unit=selected_farm_obj.area_unit or "acres",
        )

    # Crops
    crop_q = db.query(Crop).join(Farm).filter(Farm.farmer_id == current_user.id)
    if farm_id is not None:
        crop_q = crop_q.filter(Crop.farm_id == farm_id)
    crop_rows = crop_q.order_by(Crop.name.asc()).all()

    crops_list = [
        ReportCropInfo(
            id=c.id,
            farm_id=c.farm_id,
            name=c.name,
            variety=c.variety,
            status=c.status or "active",
            planting_date=c.planting_date.isoformat() if c.planting_date else None,
        )
        for c in crop_rows
    ]

    # Summary
    summary_data = get_farmer_analytics_summary(farm_id=farm_id, current_user=current_user, db=db)

    # Recent bounded predictions (up to 100 for report)
    user_farms = db.query(Farm).filter(Farm.farmer_id == current_user.id).all()
    total_user_farms = len(user_farms)

    farm_crop_ids = [c.id for c in db.query(Crop.id).filter(Crop.farm_id == farm_id).all()] if farm_id is not None else []
    other_farm_crop_ids = [
        c.id for c in db.query(Crop.id).join(Farm).filter(Farm.farmer_id == current_user.id, Farm.id != farm_id).all()
    ] if farm_id is not None else []

    pred_q = db.query(Prediction).filter(Prediction.farmer_id == current_user.id)
    if farm_id is not None:
        if total_user_farms <= 1:
            pass  # Sole farm holding: all predictions belong to this farm
        else:
            if other_farm_crop_ids:
                pred_q = pred_q.filter(~Prediction.crop_id.in_(other_farm_crop_ids))

    pred_rows = pred_q.order_by(Prediction.created_at.desc()).limit(100).all()

    farm_crop_set = set(farm_crop_ids)
    selected_farm_name = selected_farm_obj.name if selected_farm_obj else "Registered Holdings"
    predictions_list = []

    for p in pred_rows:
        if farm_id is None:
            scope_desc = "All Farms"
            assoc_farm = "Account-wide"
        elif total_user_farms <= 1:
            scope_desc = "Sole Farm"
            assoc_farm = selected_farm_name
        elif p.crop_id in farm_crop_set:
            scope_desc = "Farm-Specific"
            assoc_farm = selected_farm_name
        else:
            scope_desc = "Farmer-wide (General)"
            assoc_farm = "General Holding"

        # Identify historical cross-crop simulation anomalies honestly
        if p.crop_name and p.disease_name:
            c_low = p.crop_name.lower().strip()
            d_low = p.disease_name.lower().strip()
            for host in ["potato", "tomato", "corn", "rice", "wheat", "apple", "grape", "cotton", "soybean", "sugarcane"]:
                if host != c_low and host in d_low:
                    scope_desc = f"{scope_desc} (Historical Demo Mismatch)"
                    break

        if p.prediction_type == "uncertain" or (p.disease_name and "unable to identify" in p.disease_name.lower()):
            scope_desc = f"{scope_desc} (Uncertain Identification)"

        predictions_list.append(
            ReportPredictionItem(
                id=p.id,
                date=p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else "—",
                crop_name=p.crop_name or "Unspecified",
                disease_name=p.disease_name,
                pest_name=p.pest_name,
                prediction_type=p.prediction_type or "disease",
                confidence=p.confidence,
                status=p.status or "completed",
                is_demo=p.is_demo or "false",
                scope=scope_desc,
                farm_name=assoc_farm,
            )
        )

    # Soil records (up to 30 for report)
    soil_q = db.query(SoilRecord).filter(SoilRecord.farmer_id == current_user.id)
    if farm_id is not None:
        soil_q = soil_q.filter(SoilRecord.farm_id == farm_id)
    soil_rows = soil_q.order_by(SoilRecord.created_at.desc()).limit(30).all()

    soil_list = [
        ReportSoilItem(
            id=s.id,
            date=s.created_at.strftime("%Y-%m-%d") if s.created_at else "—",
            farm_id=s.farm_id,
            ph=s.ph,
            nitrogen=s.nitrogen,
            phosphorus=s.phosphorus,
            potassium=s.potassium,
            moisture=s.moisture,
        )
        for s in soil_rows
    ]

    # Yield estimates (up to 30 for report)
    yield_q = db.query(YieldPrediction).filter(YieldPrediction.farmer_id == current_user.id)
    if farm_id is not None:
        yield_q = yield_q.filter(YieldPrediction.farm_id == farm_id)
    yield_rows = yield_q.order_by(YieldPrediction.created_at.desc()).limit(30).all()

    yield_list = [
        ReportYieldItem(
            id=y.id,
            date=y.created_at.strftime("%Y-%m-%d") if y.created_at else "—",
            crop_name=y.crop_name,
            predicted_yield=y.predicted_yield,
            yield_unit=y.yield_unit or "tons/hectare",
            area=y.area,
            season=y.season,
            is_demo=y.is_demo or "false",
        )
        for y in yield_rows
    ]

    # Recommendations (up to 40 distinct items for report, farm-scoped)
    rec_q = db.query(Recommendation).filter(Recommendation.farmer_id == current_user.id)
    if farm_id is not None and total_user_farms > 1:
        other_farm_soil_ids = [
            s.id for s in db.query(SoilRecord.id).filter(
                SoilRecord.farmer_id == current_user.id, SoilRecord.farm_id != farm_id
            ).all()
        ]
        other_farm_crop_ids = [
            c.id for c in db.query(Crop.id).join(Farm).filter(
                Farm.farmer_id == current_user.id, Farm.id != farm_id
            ).all()
        ]
        other_pred_ids = (
            [p.id for p in db.query(Prediction.id).filter(
                Prediction.farmer_id == current_user.id, Prediction.crop_id.in_(other_farm_crop_ids)
            ).all()]
            if other_farm_crop_ids
            else []
        )
        if other_farm_soil_ids:
            rec_q = rec_q.filter(~Recommendation.soil_record_id.in_(other_farm_soil_ids))
        if other_pred_ids:
            rec_q = rec_q.filter(~Recommendation.prediction_id.in_(other_pred_ids))

    rec_rows = rec_q.order_by(Recommendation.created_at.desc(), Recommendation.id.desc()).limit(60).all()

    seen_rec_keys = set()
    distinct_rec_rows = []
    for r in rec_rows:
        key = (r.type or "", (r.title or "").strip().lower(), (r.description or "").strip().lower())
        if key in seen_rec_keys:
            continue
        seen_rec_keys.add(key)
        distinct_rec_rows.append(r)
        if len(distinct_rec_rows) >= 40:
            break

    recs_list = [
        ReportRecommendationItem(
            id=r.id,
            type=r.type or "general",
            title=r.title or "Advice",
            description=r.description,
            priority=r.priority or "medium",
            date=r.created_at.strftime("%Y-%m-%d") if r.created_at else "—",
        )
        for r in distinct_rec_rows
    ]

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    report_scope = (
        f"Selected Farm: {selected_farm_obj.name}" if selected_farm_obj else "All Registered Holdings (Farmer-wide)"
    )

    return AnalyticsReportDataResponse(
        generated_at=now_iso,
        report_scope=report_scope,
        farmer=farmer_info,
        selected_farm=selected_farm_info,
        farms=farms_list,
        crops=crops_list,
        summary=summary_data,
        predictions=predictions_list,
        soil_records=soil_list,
        yield_estimates=yield_list,
        recommendations=recs_list,
    )

