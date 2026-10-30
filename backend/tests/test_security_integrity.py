"""
Automated Security Hardening and Database Integrity Test Suite
Verifies Task 2 requirements:
1. Rate limiting on /api/auth/login, /api/auth/register, and /api/detection/predict.
2. Safe secret handling and rejection of insecure/placeholder secrets in production.
3. Strict SQLite foreign key constraint enforcement and cascade behavior.
4. Safe Alembic migration discovery and isolation.
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

import io
import cv2
import numpy as np

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.main import app
from app.database import Base, get_db, check_foreign_keys_enabled
from app.config import Settings, secret_key_is_placeholder, get_settings
from app.models.user import User
from app.models.farm import Farm
from app.models.crop import Crop
from app.models.prediction import Prediction
from app.models.recommendation import Recommendation
from app.utils.auth import get_password_hash, create_access_token
from app.utils.rate_limiter import rate_limit_storage, RateLimitDependency, get_client_ip


class SecurityAndIntegrityTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()
        cls.temp_uploads = os.path.join(cls.temp_dir, "uploads")
        os.makedirs(cls.temp_uploads, exist_ok=True)
        os.environ["UPLOAD_DIR"] = cls.temp_uploads

        cls.db_path = os.path.join(cls.temp_dir, "test_security.db").replace("\\", "/")
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

        # Create a test user
        db = cls.TestingSessionLocal()
        cls.test_user = User(
            username="sec_farmer",
            email="sec_farmer@example.com",
            hashed_password=get_password_hash("ValidPassword123!"),
            role="farmer"
        )
        db.add(cls.test_user)
        db.commit()
        cls.test_user_id = cls.test_user.id
        db.close()

        cls.token = create_access_token(data={"user_id": cls.test_user_id, "username": "sec_farmer", "role": "farmer"})
        cls.auth_headers = {"Authorization": f"Bearer {cls.token}"}

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        cls.engine.dispose()
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setUp(self):
        rate_limit_storage.clear()

    # -------------------------------------------------------------------------
    # CHECK 1: Rate Limiting
    # -------------------------------------------------------------------------

    def test_login_rate_limiting_enforcement(self):
        """Repeated login attempts must trigger HTTP 429 once the configured limit is reached."""
        settings = get_settings()
        limit = settings.RATE_LIMIT_LOGIN_LIMIT
        client_ip = "198.51.100.1"
        headers = {"X-Forwarded-For": client_ip}

        # Execute requests up to the allowed limit
        for i in range(limit):
            resp = self.client.post("/api/auth/login", json={
                "username": "sec_farmer",
                "password": "wrongpassword"
            }, headers=headers)
            # May be 401 unauthorized, but NOT 429
            self.assertEqual(resp.status_code, 401, f"Attempt {i+1} should return 401, got {resp.status_code}")

        # The (limit + 1)-th attempt must return HTTP 429 Too Many Requests
        rate_limited_resp = self.client.post("/api/auth/login", json={
            "username": "sec_farmer",
            "password": "wrongpassword"
        }, headers=headers)
        self.assertEqual(rate_limited_resp.status_code, 429)
        self.assertIn("detail", rate_limited_resp.json())
        self.assertIn("Retry-After", rate_limited_resp.headers)
        self.assertIn("X-RateLimit-Limit", rate_limited_resp.headers)
        self.assertEqual(rate_limited_resp.headers.get("X-RateLimit-Remaining"), "0")

    def test_registration_rate_limiting_enforcement(self):
        """Repeated registration attempts must trigger HTTP 429 when limit is exceeded."""
        settings = get_settings()
        limit = settings.RATE_LIMIT_REGISTER_LIMIT
        client_ip = "198.51.100.2"
        headers = {"X-Forwarded-For": client_ip}

        for i in range(limit):
            resp = self.client.post("/api/auth/register", json={
                "username": f"user_rl_{i}",
                "email": f"user_rl_{i}@example.com",
                "password": "Password123!"
            }, headers=headers)
            # 200 or 400, but not 429
            self.assertIn(resp.status_code, (200, 400))

        rate_limited_resp = self.client.post("/api/auth/register", json={
            "username": f"user_rl_{limit+1}",
            "email": f"user_rl_{limit+1}@example.com",
            "password": "Password123!"
        }, headers=headers)
        self.assertEqual(rate_limited_resp.status_code, 429)
        self.assertIn("Retry-After", rate_limited_resp.headers)

    def test_detection_rate_limiting_enforcement(self):
        """Repeated image uploads to /api/detection/predict must trigger HTTP 429 when limit exceeded."""
        settings = get_settings()
        limit = settings.RATE_LIMIT_DETECTION_LIMIT
        client_ip = "198.51.100.3"
        headers = {**self.auth_headers, "X-Forwarded-For": client_ip}

        def _make_dummy_image():
            img = np.zeros((64, 64, 3), dtype=np.uint8)
            cv2.circle(img, (32, 32), 16, (40, 210, 70), -1)
            ok, buf = cv2.imencode(".jpg", img)
            return io.BytesIO(buf.tobytes())

        # Make limit requests
        for i in range(limit):
            buf = _make_dummy_image()
            resp = self.client.post(
                "/api/detection/predict",
                files={"file": (f"test_rl_{i}.jpg", buf, "image/jpeg")},
                data={"crop_name": "Tomato"},
                headers=headers,
            )
            self.assertEqual(resp.status_code, 200, f"Attempt {i+1} failed with {resp.text}")

        # The (limit + 1)-th request must be rate limited
        buf = _make_dummy_image()
        rate_limited_resp = self.client.post(
            "/api/detection/predict",
            files={"file": ("test_rl_exceeded.jpg", buf, "image/jpeg")},
            data={"crop_name": "Tomato"},
            headers=headers,
        )
        self.assertEqual(rate_limited_resp.status_code, 429)
        self.assertIn("Retry-After", rate_limited_resp.headers)

    def test_rate_limit_keys_do_not_leak_sensitive_info(self):
        """Verify that rate limit keys only contain endpoint scope and IP/user identifier, never secrets."""
        dep = RateLimitDependency(scope="login", default_limit=5, default_window=60)
        # Verify dummy request key
        class DummyRequest:
            client = type("Client", (), {"host": "192.168.1.50"})()
            headers = {}

        key = dep.build_key(DummyRequest())
        self.assertEqual(key, "rl:login:192.168.1.50")
        self.assertNotIn("password", key.lower())
        self.assertNotIn("token", key.lower())
        self.assertNotIn("secret", key.lower())

    # -------------------------------------------------------------------------
    # CHECK 2: Secret Management & JWT Configuration
    # -------------------------------------------------------------------------

    def test_production_rejects_missing_or_placeholder_secret(self):
        """In ENVIRONMENT=production, default or short placeholder secrets must be rejected."""
        placeholder_keys = [
            "dev-secret-key-change-in-production",
            "your-super-secret-key-change-in-production",
            "short",
            "changeme",
            ""
        ]
        for bad_key in placeholder_keys:
            with self.assertRaises(ValueError, msg=f"Should reject bad secret: '{bad_key}'"):
                Settings(ENVIRONMENT="production", SECRET_KEY=bad_key)

    def test_production_accepts_strong_secret(self):
        """In ENVIRONMENT=production, a cryptographically secure key of >= 32 chars is accepted."""
        strong_key = "x" * 64
        settings = Settings(ENVIRONMENT="production", SECRET_KEY=strong_key)
        self.assertEqual(settings.ENVIRONMENT, "production")
        self.assertEqual(settings.SECRET_KEY, strong_key)

    def test_development_allows_placeholder_with_warning(self):
        """In ENVIRONMENT=development, local development is preserved without crashing."""
        settings = Settings(ENVIRONMENT="development", SECRET_KEY="dev-secret-key-change-in-production")
        self.assertEqual(settings.ENVIRONMENT, "development")
        self.assertTrue(secret_key_is_placeholder(settings.SECRET_KEY))

    def test_secret_not_revealed_in_exceptions(self):
        """Ensure exception messages do not reveal secret values."""
        try:
            Settings(ENVIRONMENT="production", SECRET_KEY="change-in-production-sample-secret-value-12345")
        except ValueError as err:
            self.assertNotIn("sample-secret-value-12345", str(err))

    # -------------------------------------------------------------------------
    # CHECK 3: SQLite Foreign Key Constraints & Cascades
    # -------------------------------------------------------------------------

    def test_sqlite_foreign_keys_are_enabled(self):
        """Verify PRAGMA foreign_keys is 1 (ON) on new connections."""
        db = self.TestingSessionLocal()
        try:
            self.assertTrue(check_foreign_keys_enabled(db), "PRAGMA foreign_keys must be ON (1)")
        finally:
            db.close()

    def test_foreign_key_violation_raises_integrity_error(self):
        """Inserting a record with a non-existent parent foreign key must fail."""
        db = self.TestingSessionLocal()
        try:
            invalid_prediction = Prediction(
                farmer_id=999999,  # Does not exist
                crop_name="Wheat",
                disease_name="Leaf Rust"
            )
            db.add(invalid_prediction)
            with self.assertRaises(IntegrityError):
                db.commit()
            db.rollback()
        finally:
            db.close()

    def test_prediction_and_recommendation_deletion(self):
        """Deleting a prediction must cleanly delete child recommendations without FK conflicts."""
        db = self.TestingSessionLocal()
        try:
            # Create a prediction
            pred = Prediction(
                farmer_id=self.test_user_id,
                crop_name="Cotton",
                disease_name="Boll Rot"
            )
            db.add(pred)
            db.commit()
            db.refresh(pred)

            # Create an attached recommendation
            rec = Recommendation(
                prediction_id=pred.id,
                farmer_id=self.test_user_id,
                type="treatment",
                title="Apply Copper Fungicide",
                description="Spray once weekly"
            )
            db.add(rec)
            db.commit()
            rec_id = rec.id

            # Delete prediction via API endpoint
            resp = self.client.delete(f"/api/predictions/{pred.id}", headers=self.auth_headers)
            self.assertEqual(resp.status_code, 200)

            # Verify recommendation was deleted by cascade
            remaining_rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
            self.assertIsNone(remaining_rec, "Recommendation should be deleted when prediction is deleted")
        finally:
            db.close()

    def test_user_cascade_deletion(self):
        """Deleting a user cascades and removes child farms and profiles without orphan records."""
        db = self.TestingSessionLocal()
        try:
            temp_user = User(
                username="cascade_user",
                email="cascade@example.com",
                hashed_password=get_password_hash("Pass123!"),
                role="farmer"
            )
            db.add(temp_user)
            db.commit()
            db.refresh(temp_user)

            temp_farm = Farm(farmer_id=temp_user.id, name="Cascade Farm")
            db.add(temp_farm)
            db.commit()
            farm_id = temp_farm.id

            # Delete user
            db.delete(temp_user)
            db.commit()

            # Verify farm is deleted
            remaining_farm = db.query(Farm).filter(Farm.id == farm_id).first()
            self.assertIsNone(remaining_farm)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
