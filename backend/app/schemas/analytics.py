"""
Pydantic schemas for Farm Analytics and Reporting APIs.
Ensures strong typing, input validation, and clean serialization for farmer analytics.
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field


# ----------------- Summary Schemas -----------------

class ScansSummary(BaseModel):
    total_scans: int = 0
    healthy_count: int = 0
    diseased_count: int = 0
    pest_count: int = 0
    demo_scans: int = 0
    genuine_scans: int = 0
    farm_scans: int = 0
    unassigned_scans: int = 0


class SoilSummary(BaseModel):
    record_id: Optional[int] = None
    recorded_at: Optional[str] = None
    ph: Optional[float] = None
    nitrogen: Optional[float] = None
    phosphorus: Optional[float] = None
    potassium: Optional[float] = None
    moisture: Optional[float] = None
    soil_health_score: Optional[int] = None
    soil_health_status: Optional[str] = None
    measured_parameters_count: int = 0
    is_sufficient: bool = True


class YieldSummary(BaseModel):
    total_estimates: int = 0
    min_yield: Optional[float] = None
    max_yield: Optional[float] = None
    avg_yield: Optional[float] = None
    yield_unit: str = "tons/hectare"


class RecommendationSummary(BaseModel):
    total: int = 0
    by_priority: Dict[str, int] = Field(default_factory=dict)
    by_type: Dict[str, int] = Field(default_factory=dict)


class AnalyticsSummaryResponse(BaseModel):
    total_farms: int = 0
    total_crops: int = 0
    total_farm_area: Optional[float] = None
    area_unit: str = "acres"
    scans: ScansSummary
    soil: Optional[SoilSummary] = None
    yields: YieldSummary
    recommendations: RecommendationSummary


# ----------------- Trend Schemas -----------------

class SoilTrendPoint(BaseModel):
    id: int
    date: str
    ph: Optional[float] = None
    nitrogen: Optional[float] = None
    phosphorus: Optional[float] = None
    potassium: Optional[float] = None
    moisture: Optional[float] = None
    farm_id: Optional[int] = None


class ScanTrendPoint(BaseModel):
    id: int
    date: str
    crop_name: Optional[str] = None
    disease_name: Optional[str] = None
    pest_name: Optional[str] = None
    prediction_type: str = "disease"
    confidence: Optional[float] = None
    is_demo: str = "false"


class YieldTrendPoint(BaseModel):
    id: int
    date: str
    crop_name: str
    predicted_yield: Optional[float] = None
    yield_unit: str = "tons/hectare"
    season: Optional[str] = None
    is_demo: str = "false"


class AnalyticsTrendsResponse(BaseModel):
    soil_trends: List[SoilTrendPoint] = Field(default_factory=list)
    scan_trends: List[ScanTrendPoint] = Field(default_factory=list)
    yield_trends: List[YieldTrendPoint] = Field(default_factory=list)


# ----------------- Consolidated Report Data Schemas -----------------

class ReportFarmerInfo(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None


class ReportFarmInfo(BaseModel):
    id: int
    name: str
    location: Optional[str] = None
    area: Optional[float] = None
    area_unit: Optional[str] = "acres"


class ReportCropInfo(BaseModel):
    id: int
    farm_id: int
    name: str
    variety: Optional[str] = None
    status: Optional[str] = "active"
    planting_date: Optional[str] = None


class ReportPredictionItem(BaseModel):
    id: int
    date: str
    crop_name: Optional[str] = None
    disease_name: Optional[str] = None
    pest_name: Optional[str] = None
    prediction_type: str = "disease"
    confidence: Optional[float] = None
    status: str = "completed"
    is_demo: str = "false"
    scope: Optional[str] = "Sole Farm Holding"
    farm_name: Optional[str] = None


class ReportSoilItem(BaseModel):
    id: int
    date: str
    farm_id: Optional[int] = None
    ph: Optional[float] = None
    nitrogen: Optional[float] = None
    phosphorus: Optional[float] = None
    potassium: Optional[float] = None
    moisture: Optional[float] = None


class ReportYieldItem(BaseModel):
    id: int
    date: str
    crop_name: str
    predicted_yield: Optional[float] = None
    yield_unit: str = "tons/hectare"
    area: Optional[float] = None
    season: Optional[str] = None
    is_demo: str = "false"


class ReportRecommendationItem(BaseModel):
    id: int
    type: str
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    date: str


class AnalyticsReportDataResponse(BaseModel):
    generated_at: str
    report_scope: Optional[str] = "Selected Farm"
    farmer: ReportFarmerInfo
    selected_farm: Optional[ReportFarmInfo] = None
    farms: List[ReportFarmInfo] = Field(default_factory=list)
    crops: List[ReportCropInfo] = Field(default_factory=list)
    summary: AnalyticsSummaryResponse
    predictions: List[ReportPredictionItem] = Field(default_factory=list)
    soil_records: List[ReportSoilItem] = Field(default_factory=list)
    yield_estimates: List[ReportYieldItem] = Field(default_factory=list)
    recommendations: List[ReportRecommendationItem] = Field(default_factory=list)

