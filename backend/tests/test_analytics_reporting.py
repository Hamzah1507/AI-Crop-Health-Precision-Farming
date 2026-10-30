"""
Automated Unit and Integration Test Suite for Farm Analytics and Reporting.
Covers:
1. Summary metric aggregations (farms, crops, scans, soil, yields, recommendations).
2. Trend ordering, calculations, date range filtering, and farm filtering.
3. Multi-tenant isolation between different farmers.
4. Access control: rejection of unauthorized farm IDs (HTTP 404).
5. Safe handling of empty accounts with 0 records.
6. Separation of genuine vs demo scan counts.
7. Yield predictions represented as estimates.
8. Error handling on invalid date parameters (HTTP 400).
"""

import os
import shutil
import tempfile
import unittest
import warnings

# Suppress harmless testclient deprecation warning and resource warnings during test runs
warnings.filterwarnings("ignore", message=r".*httpx.*", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=ResourceWarning)

from datetime import datetime, timezone, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models.user import User
from app.models.farmer_profile import FarmerProfile
from app.models.farm import Farm
from app.models.crop import Crop
from app.models.prediction import Prediction
from app.models.soil_record import SoilRecord
from app.models.yield_prediction import YieldPrediction
from app.models.recommendation import Recommendation
from app.utils.auth import get_password_hash, create_access_token


class AnalyticsReportingTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp(prefix="cp_analytics_test_")
        cls.db_path = os.path.join(cls.temp_dir, "test_analytics.db").replace("\\", "/")
        cls.engine = create_engine(
            f"sqlite:///{cls.db_path}",
            connect_args={"check_same_thread": False}
        )
        cls.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        Base.metadata.create_all(bind=cls.engine)

        def override_get_db():
            db = cls.TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

        # Seed Farmer A (with full rich data)
        db = cls.TestingSessionLocal()
        cls.farmer_a = User(
            username="farmer_a",
            email="farmer_a@example.com",
            hashed_password=get_password_hash("Secret123!"),
            role="farmer"
        )
        db.add(cls.farmer_a)
        db.commit()
        cls.farmer_a_id = cls.farmer_a.id

        cls.profile_a = FarmerProfile(user_id=cls.farmer_a_id, full_name="Farmer Alpha")
        db.add(cls.profile_a)

        cls.farm_a1 = Farm(farmer_id=cls.farmer_a_id, name="Green Valley Farm", location="Ahmedabad", area=10.5, area_unit="acres")
        cls.farm_a2 = Farm(farmer_id=cls.farmer_a_id, name="Highland Fields", location="Gandhinagar", area=5.0, area_unit="acres")
        db.add_all([cls.farm_a1, cls.farm_a2])
        db.commit()
        cls.farm_a1_id = cls.farm_a1.id
        cls.farm_a2_id = cls.farm_a2.id

        cls.crop_wheat = Crop(farm_id=cls.farm_a1_id, name="Wheat", variety="Sharbati")
        cls.crop_cotton = Crop(farm_id=cls.farm_a1_id, name="Cotton", variety="Bt Cotton")
        cls.crop_tomato = Crop(farm_id=cls.farm_a2_id, name="Tomato", variety="Hybrid")
        db.add_all([cls.crop_wheat, cls.crop_cotton, cls.crop_tomato])
        db.commit()
        cls.crop_wheat_id = cls.crop_wheat.id

        now = datetime.now(timezone.utc)

        # Predictions for Farmer A: 1 healthy, 1 genuine diseased, 1 demo diseased, 1 pest
        cls.pred1 = Prediction(farmer_id=cls.farmer_a_id, crop_id=cls.crop_wheat_id, crop_name="Wheat",
                               disease_name="Healthy Plant", prediction_type="disease", confidence=96.5, is_demo="false",
                               created_at=now - timedelta(days=3))
        cls.pred2 = Prediction(farmer_id=cls.farmer_a_id, crop_id=cls.crop_wheat_id, crop_name="Wheat",
                               disease_name="Leaf Rust", prediction_type="disease", confidence=88.2, is_demo="false",
                               created_at=now - timedelta(days=2))
        cls.pred3 = Prediction(farmer_id=cls.farmer_a_id, crop_name="Tomato",
                               disease_name="Early Blight", prediction_type="disease", confidence=None, is_demo="true",
                               created_at=now - timedelta(days=1))
        cls.pred4 = Prediction(farmer_id=cls.farmer_a_id, crop_name="Cotton",
                               pest_name="Whitefly", prediction_type="pest", confidence=91.0, is_demo="false",
                               created_at=now)
        db.add_all([cls.pred1, cls.pred2, cls.pred3, cls.pred4])

        # Soil records for Farmer A
        cls.soil1 = SoilRecord(farmer_id=cls.farmer_a_id, farm_id=cls.farm_a1_id, crop_id=cls.crop_wheat_id,
                               ph=6.5, nitrogen=35.0, phosphorus=25.0, potassium=30.0, moisture=55.0,
                               created_at=now - timedelta(days=5))
        cls.soil2 = SoilRecord(farmer_id=cls.farmer_a_id, farm_id=cls.farm_a1_id, crop_id=cls.crop_wheat_id,
                               ph=6.8, nitrogen=40.0, phosphorus=28.0, potassium=32.0, moisture=60.0,
                               created_at=now - timedelta(days=1))
        db.add_all([cls.soil1, cls.soil2])

        # Yield predictions for Farmer A
        cls.yield1 = YieldPrediction(farmer_id=cls.farmer_a_id, farm_id=cls.farm_a1_id, crop_name="Wheat",
                                     predicted_yield=4.5, yield_unit="tons/hectare", area=10.5, season="Rabi (Winter)",
                                     is_demo="true", created_at=now - timedelta(days=4))
        cls.yield2 = YieldPrediction(farmer_id=cls.farmer_a_id, farm_id=cls.farm_a1_id, crop_name="Wheat",
                                     predicted_yield=5.5, yield_unit="tons/hectare", area=10.5, season="Rabi (Winter)",
                                     is_demo="true", created_at=now - timedelta(days=2))
        db.add_all([cls.yield1, cls.yield2])

        # Recommendations for Farmer A
        cls.rec1 = Recommendation(farmer_id=cls.farmer_a_id, type="fertilizer", title="Add Nitrogen", priority="high",
                                  created_at=now - timedelta(days=2))
        cls.rec2 = Recommendation(farmer_id=cls.farmer_a_id, type="irrigation", title="Morning Watering", priority="medium",
                                  created_at=now - timedelta(days=1))
        db.add_all([cls.rec1, cls.rec2])

        # Seed Farmer B (isolated user with 1 farm, to test isolation)
        cls.farmer_b = User(
            username="farmer_b",
            email="farmer_b@example.com",
            hashed_password=get_password_hash("Secret123!"),
            role="farmer"
        )
        db.add(cls.farmer_b)
        db.commit()
        cls.farmer_b_id = cls.farmer_b.id

        cls.farm_b = Farm(farmer_id=cls.farmer_b_id, name="Farmer B Private Farm", location="Surat", area=20.0, area_unit="acres")
        db.add(cls.farm_b)
        db.commit()
        cls.farm_b_id = cls.farm_b.id

        # Seed Farmer C (completely empty account)
        cls.farmer_c = User(
            username="farmer_empty",
            email="farmer_empty@example.com",
            hashed_password=get_password_hash("Secret123!"),
            role="farmer"
        )
        db.add(cls.farmer_c)
        db.commit()
        cls.farmer_c_id = cls.farmer_c.id

        db.close()

        # Auth tokens
        cls.token_a = create_access_token(data={"user_id": cls.farmer_a_id, "username": "farmer_a", "role": "farmer"})
        cls.headers_a = {"Authorization": f"Bearer {cls.token_a}"}

        cls.token_b = create_access_token(data={"user_id": cls.farmer_b_id, "username": "farmer_b", "role": "farmer"})
        cls.headers_b = {"Authorization": f"Bearer {cls.token_b}"}

        cls.token_c = create_access_token(data={"user_id": cls.farmer_c_id, "username": "farmer_empty", "role": "farmer"})
        cls.headers_c = {"Authorization": f"Bearer {cls.token_c}"}

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        cls.engine.dispose()
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # Authentication & Access Control
    # -------------------------------------------------------------------------

    def test_analytics_endpoints_require_authentication(self):
        """Endpoints must return 401 Unauthorized when called without JWT."""
        for path in ["/api/analytics/summary", "/api/analytics/trends", "/api/analytics/report-data"]:
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 401, f"{path} should require auth")

    def test_rejection_of_unauthorized_farm_access(self):
        """Farmer A attempting to access Farmer B's farm must receive HTTP 404."""
        resp = self.client.get(f"/api/analytics/summary?farm_id={self.farm_b_id}", headers=self.headers_a)
        self.assertEqual(resp.status_code, 404)
        self.assertIn("detail", resp.json())

    # -------------------------------------------------------------------------
    # Summary Metrics Aggregation
    # -------------------------------------------------------------------------

    def test_summary_aggregations_for_farmer_a(self):
        """Verify summary accurately aggregates Farmer A's farms, crops, scans, soil, and yields."""
        resp = self.client.get("/api/analytics/summary", headers=self.headers_a)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["total_farms"], 2)
        self.assertEqual(data["total_crops"], 3)
        self.assertEqual(data["total_farm_area"], 15.5)  # 10.5 + 5.0
        self.assertEqual(data["area_unit"], "acres")

        scans = data["scans"]
        self.assertEqual(scans["total_scans"], 4)
        self.assertEqual(scans["healthy_count"], 1)
        self.assertEqual(scans["diseased_count"], 2)
        self.assertEqual(scans["pest_count"], 1)
        self.assertEqual(scans["demo_scans"], 1)
        self.assertEqual(scans["genuine_scans"], 3)

        soil = data["soil"]
        self.assertIsNotNone(soil)
        self.assertEqual(soil["ph"], 6.8)
        self.assertEqual(soil["nitrogen"], 40.0)
        self.assertIsInstance(soil["soil_health_score"], int)
        self.assertIsNotNone(soil["soil_health_status"])

        yields = data["yields"]
        self.assertEqual(yields["total_estimates"], 2)
        self.assertEqual(yields["min_yield"], 4.5)
        self.assertEqual(yields["max_yield"], 5.5)
        self.assertEqual(yields["avg_yield"], 5.0)

        recs = data["recommendations"]
        self.assertEqual(recs["total"], 2)
        self.assertEqual(recs["by_priority"].get("high"), 1)
        self.assertEqual(recs["by_priority"].get("medium"), 1)

    def test_summary_with_farm_filter(self):
        """Farmer A querying with farm_a1 should filter out farm_a2's crops."""
        resp = self.client.get(f"/api/analytics/summary?farm_id={self.farm_a1_id}", headers=self.headers_a)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total_farms"], 1)
        self.assertEqual(data["total_crops"], 2)  # Wheat & Cotton on farm_a1
        self.assertEqual(data["total_farm_area"], 10.5)

    # -------------------------------------------------------------------------
    # Trends
    # -------------------------------------------------------------------------

    def test_trends_chronological_ordering(self):
        """Trends endpoint must return records in ascending chronological order."""
        resp = self.client.get("/api/analytics/trends", headers=self.headers_a)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        # Soil trends ordering
        soil_dates = [t["date"] for t in data["soil_trends"]]
        self.assertEqual(soil_dates, sorted(soil_dates))

        # Scan trends ordering
        scan_dates = [t["date"] for t in data["scan_trends"]]
        self.assertEqual(scan_dates, sorted(scan_dates))

        # Yield trends ordering
        yield_dates = [t["date"] for t in data["yield_trends"]]
        self.assertEqual(yield_dates, sorted(yield_dates))

    def test_trends_date_range_filtering(self):
        """Ensure start_date and end_date filter records properly."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        resp = self.client.get(f"/api/analytics/trends?start_date={today}", headers=self.headers_a)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # Older records should be filtered out
        self.assertTrue(all(t["date"] >= today for t in data["scan_trends"]))

    def test_trends_invalid_date_format_handling(self):
        """Invalid date string must return HTTP 400 with a descriptive error."""
        resp = self.client.get("/api/analytics/trends?start_date=not-a-date", headers=self.headers_a)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Invalid start_date format", resp.json()["detail"])

    # -------------------------------------------------------------------------
    # Report Data
    # -------------------------------------------------------------------------

    def test_report_data_payload_structure(self):
        """Report data endpoint must return complete typed structure for PDF compilation."""
        resp = self.client.get("/api/analytics/report-data", headers=self.headers_a)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertIn("generated_at", data)
        self.assertEqual(data["farmer"]["username"], "farmer_a")
        self.assertEqual(data["farmer"]["full_name"], "Farmer Alpha")
        self.assertEqual(len(data["farms"]), 2)
        self.assertEqual(len(data["crops"]), 3)
        self.assertGreater(len(data["predictions"]), 0)
        self.assertGreater(len(data["soil_records"]), 0)
        self.assertGreater(len(data["yield_estimates"]), 0)
        self.assertGreater(len(data["recommendations"]), 0)

    # -------------------------------------------------------------------------
    # Farmer Multi-Tenant Isolation
    # -------------------------------------------------------------------------

    def test_farmer_isolation(self):
        """Farmer B must see only their own data (0 scans, 0 crops, 1 farm)."""
        resp = self.client.get("/api/analytics/summary", headers=self.headers_b)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total_farms"], 1)
        self.assertEqual(data["total_crops"], 0)
        self.assertEqual(data["scans"]["total_scans"], 0)
        self.assertIsNone(data["soil"])
        self.assertEqual(data["yields"]["total_estimates"], 0)

    # -------------------------------------------------------------------------
    # Empty Account Safe Handling
    # -------------------------------------------------------------------------

    def test_empty_farmer_account_handling(self):
        """A farmer with zero farms, crops, scans, and soil records must return clean zero/null responses without crashing."""
        resp_sum = self.client.get("/api/analytics/summary", headers=self.headers_c)
        self.assertEqual(resp_sum.status_code, 200)
        sum_data = resp_sum.json()
        self.assertEqual(sum_data["total_farms"], 0)
        self.assertEqual(sum_data["total_crops"], 0)
        self.assertIsNone(sum_data["total_farm_area"])
        self.assertEqual(sum_data["scans"]["total_scans"], 0)
        self.assertIsNone(sum_data["soil"])
        self.assertEqual(sum_data["yields"]["total_estimates"], 0)

        resp_rep = self.client.get("/api/analytics/report-data", headers=self.headers_c)
        self.assertEqual(resp_rep.status_code, 200)
        rep_data = resp_rep.json()
        self.assertEqual(len(rep_data["farms"]), 0)
        self.assertEqual(len(rep_data["crops"]), 0)
        self.assertEqual(len(rep_data["predictions"]), 0)
        self.assertEqual(len(rep_data["soil_records"]), 0)
        self.assertEqual(len(rep_data["yield_estimates"]), 0)

    # -------------------------------------------------------------------------
    # Sole-Farm and Cross-Farm Scoping Tests
    # -------------------------------------------------------------------------

    def test_sole_farm_unassigned_scans_associated_with_sole_farm(self):
        """A farmer with exactly 1 farm and scans without crop_id must associate scans with that farm."""
        db = self.TestingSessionLocal()
        farmer_d = User(username="farmer_d", email="farmer_d@example.com", hashed_password=get_password_hash("Secret123!"), role="farmer")
        db.add(farmer_d)
        db.commit()
        farm_d = Farm(farmer_id=farmer_d.id, name="Sole Valley Holding", location="Mehsana", area=8.0)
        db.add(farm_d)
        db.commit()
        # 2 scans with crop_id=None
        pred1 = Prediction(farmer_id=farmer_d.id, crop_id=None, crop_name="Wheat", disease_name="Leaf Blight", is_demo="true")
        pred2 = Prediction(farmer_id=farmer_d.id, crop_id=None, crop_name="Wheat", disease_name="Healthy Plant", is_demo="false")
        db.add_all([pred1, pred2])
        db.commit()
        token_d = create_access_token(data={"user_id": farmer_d.id, "username": "farmer_d", "role": "farmer"})
        headers_d = {"Authorization": f"Bearer {token_d}"}

        # Query report-data passing farm_id
        resp = self.client.get(f"/api/analytics/report-data?farm_id={farm_d.id}", headers=headers_d)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["predictions"]), 2)
        self.assertEqual(data["predictions"][0]["scope"], "Sole Farm")
        self.assertEqual(data["summary"]["scans"]["total_scans"], 2)
        db.close()


if __name__ == "__main__":
    unittest.main()

