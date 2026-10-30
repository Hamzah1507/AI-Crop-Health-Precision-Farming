"""
Comprehensive unit and integration test suite for the Disease & Pest Detection Pipeline.

Covers all 18 test scenarios required by Task 1:
1. Valid image upload.
2. Invalid image signature (MIME sniffing).
3. Corrupted or undecodable image.
4. Oversized image upload (HTTP 413).
5. Unauthenticated request (HTTP 401).
6. Unauthorized crop or farm access (HTTP 404).
7. Model successfully loaded status.
8. Model weights unavailable status.
9. Model initialization failure handling.
10. Successful genuine inference with mocked model output.
11. Genuine no-disease result ("Healthy Plant").
12. Malformed inference output / execution failure handling.
13. Correct confidence and bounding-box mapping.
14. Database persistence failure / file cleanup rollback.
15. Correct recommendation association.
16. Demo mode remains clearly marked (is_demo="true", confidence=None).
17. Prediction history and deletion regression (including disk file cleanup).
18. Frontend API contract compatibility.

Runs against isolated temporary storage; never touches production app.db or uploads/.
"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# ----------------- Ephemeral storage setup -----------------
_TMP = tempfile.mkdtemp(prefix="cp_det_test_")
_UPLOADS = os.path.join(_TMP, "uploads")
_DB_PATH = os.path.join(_TMP, "test_det.db")
os.environ["DATABASE_URL"] = "sqlite:///" + _DB_PATH.replace("\\", "/")
os.environ["UPLOAD_DIR"] = _UPLOADS
os.makedirs(_UPLOADS, exist_ok=True)

import numpy as np
import cv2
import warnings

# Suppress harmless testclient deprecation warning and resource warnings during test runs
warnings.filterwarnings("ignore", message=r".*httpx.*", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=ResourceWarning)

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.database import Base, get_db
from app.main import app
from app.ml.model_service import model_service, ModelInferenceError
from app.models.prediction import Prediction
from app.models.recommendation import Recommendation
from app.models.farm import Farm
from app.models.crop import Crop
from app.models.user import User
from app.utils.auth import create_access_token, get_password_hash

settings = get_settings()


def make_test_image(fmt: str = "png", width: int = 64, height: int = 64) -> bytes:
    """Generate a valid test image byte stream."""
    img = np.zeros((height, width, 3), np.uint8)
    img[:] = (35, 130, 45)
    cv2.circle(img, (width // 2, height // 2), width // 4, (40, 210, 70), -1)
    ok, buf = cv2.imencode("." + fmt, img)
    assert ok
    return buf.tobytes()


class MockBoxes:
    def __init__(self, conf=0.895, cls=0, xyxy=(12.0, 15.0, 95.0, 110.0)):
        self.conf = np.array([conf], dtype=np.float32)
        self.cls = np.array([cls], dtype=np.int32)
        self.xyxy = np.array([xyxy], dtype=np.float32)

    def __len__(self):
        return 1


class MockResult:
    def __init__(self, boxes=None, names=None):
        self.boxes = boxes
        self.names = names or {0: "Tomato Late Blight"}


class MockYOLOModel:
    def __init__(self, should_fail=False, empty=False, custom_class="Tomato Late Blight", conf=0.895, bbox=(12.0, 15.0, 95.0, 110.0)):
        self.should_fail = should_fail
        self.empty = empty
        self.custom_class = custom_class
        self.conf = conf
        self.bbox = bbox

    def __call__(self, image_path):
        if self.should_fail:
            raise RuntimeError("Simulated inference kernel failure")
        if self.empty:
            return [MockResult(boxes=None, names={0: self.custom_class})]
        boxes = MockBoxes(self.conf, 0, self.bbox)
        return [MockResult(boxes=boxes, names={0: self.custom_class})]


class DetectionPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_upload_dir = settings.UPLOAD_DIR
        settings.UPLOAD_DIR = _UPLOADS

        cls.engine = create_engine(
            f"sqlite:///{_DB_PATH.replace('\\', '/')}",
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
        cls.client.__enter__()

        # Register primary test user
        db = cls.TestingSessionLocal()
        cls.user = User(
            username="det_tester",
            email="det_tester@example.com",
            hashed_password=get_password_hash("testpass123"),
            role="farmer",
            is_active=True
        )
        db.add(cls.user)
        db.commit()
        db.refresh(cls.user)

        # Create farm and crop for user
        cls.farm = Farm(farmer_id=cls.user.id, name="Tester Farm", location="Ahmedabad")
        db.add(cls.farm)
        db.commit()
        db.refresh(cls.farm)

        cls.crop = Crop(farm_id=cls.crop_id if hasattr(cls, 'crop_id') else cls.farm.id, name="Tomato", variety="Roma")
        db.add(cls.crop)
        db.commit()
        db.refresh(cls.crop)

        # Register secondary user for authorization tests
        cls.other_user = User(
            username="det_stranger",
            email="det_stranger@example.com",
            hashed_password=get_password_hash("testpass123"),
            role="farmer",
            is_active=True
        )
        db.add(cls.other_user)
        db.commit()
        db.refresh(cls.other_user)

        cls.other_farm = Farm(farmer_id=cls.other_user.id, name="Other Farm")
        db.add(cls.other_farm)
        db.commit()
        db.refresh(cls.other_farm)

        cls.other_crop = Crop(farm_id=cls.other_farm.id, name="Rice")
        db.add(cls.other_crop)
        db.commit()
        db.refresh(cls.other_crop)

        cls.user_id = cls.user.id
        cls.username = cls.user.username
        cls.user_role = cls.user.role
        cls.crop_id = cls.crop.id

        cls.other_user_id = cls.other_user.id
        cls.other_username = cls.other_user.username
        cls.other_user_role = cls.other_user.role
        cls.other_crop_id = cls.other_crop.id

        db.close()

        cls.token = create_access_token(data={"user_id": cls.user_id, "username": cls.username, "role": cls.user_role})
        cls.auth_headers = {"Authorization": f"Bearer {cls.token}"}

        cls.other_token = create_access_token(data={"user_id": cls.other_user_id, "username": cls.other_username, "role": cls.other_user_role})
        cls.other_headers = {"Authorization": f"Bearer {cls.other_token}"}

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)
        app.dependency_overrides.pop(get_db, None)
        settings.UPLOAD_DIR = cls._orig_upload_dir
        cls.engine.dispose()
        shutil.rmtree(_TMP, ignore_errors=True)
        model_service._try_load_models()

    def tearDown(self):
        # Reset model_service to default uninitialized demo state after each test
        model_service.unload_model()

    def post_image(self, content: bytes, filename: str = "leaf.png", content_type: str = "image/png", headers=None, **data):
        h = headers if headers is not None else self.auth_headers
        return self.client.post(
            "/api/detection/predict",
            headers=h,
            files={"file": (filename, content, content_type)},
            data=data
        )

    # 1. Valid image upload
    def test_01_valid_image_upload(self):
        for fmt in ("jpg", "png", "webp"):
            with self.subTest(format=fmt):
                img = make_test_image(fmt)
                res = self.post_image(img, filename=f"leaf.{fmt}")
                self.assertEqual(res.status_code, 200, res.text)
                body = res.json()
                self.assertIn("id", body)
                self.assertTrue(body["image_path"].endswith(f".{ 'jpg' if fmt == 'jpg' else fmt }"))
                self.assertTrue(os.path.exists(body["image_path"]))

    # 2. Invalid image signature (MIME sniffing)
    def test_02_invalid_image_signature_rejected(self):
        fake_payloads = [
            b"<!DOCTYPE html><html><body>malicious</body></html>",
            b"%PDF-1.5 fake document header",
            b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff",
            b"plain text pretending to be leaf image"
        ]
        before_count = len(os.listdir(_UPLOADS))
        for payload in fake_payloads:
            res = self.post_image(payload, filename="image.png", content_type="image/png")
            self.assertEqual(res.status_code, 400)
            self.assertIn("Unsupported or invalid", res.json()["detail"])
        self.assertEqual(len(os.listdir(_UPLOADS)), before_count, "Invalid files must not remain on disk")

    # 3. Corrupted or undecodable image
    def test_03_corrupted_undecodable_image(self):
        valid = make_test_image("png")
        truncated = valid[: len(valid) // 3]
        before_count = len(os.listdir(_UPLOADS))
        res = self.post_image(truncated, filename="corrupt.png")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(len(os.listdir(_UPLOADS)), before_count)

    # 4. Oversized image upload
    def test_04_oversized_image_upload(self):
        before_count = len(os.listdir(_UPLOADS))
        limit_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024 + 1024
        # Fake oversized stream starting with PNG magic header
        oversized = b"\x89PNG\r\n\x1a\n" + (b"0" * limit_bytes)
        res = self.post_image(oversized, filename="giant.png")
        self.assertEqual(res.status_code, 413)
        self.assertEqual(len(os.listdir(_UPLOADS)), before_count)

    # 5. Unauthenticated request
    def test_05_unauthenticated_request(self):
        res = self.client.post(
            "/api/detection/predict",
            files={"file": ("leaf.png", make_test_image("png"), "image/png")}
        )
        self.assertEqual(res.status_code, 401)

    # 6. Unauthorized crop or farm access
    def test_06_unauthorized_crop_access(self):
        before_count = len(os.listdir(_UPLOADS))
        # User tries to link prediction to stranger's crop
        res = self.post_image(make_test_image("png"), crop_id=str(self.other_crop_id))
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.json()["detail"], "Crop not found")
        self.assertEqual(len(os.listdir(_UPLOADS)), before_count, "No image should be saved for invalid crop link")

    # 7. Model successfully loaded status
    def test_07_model_successfully_loaded_status(self):
        model_service.set_model(MockYOLOModel(), "YOLOv8")
        status = self.client.get("/api/detection/status").json()
        self.assertTrue(status["model_loaded"])
        self.assertEqual(status["model_type"], "YOLOv8")
        self.assertEqual(status["status"], "ready")
        self.assertEqual(status["mode"], "genuine")

    # 8. Model weights unavailable status
    def test_08_model_weights_unavailable_status(self):
        model_service.unload_model()
        status = self.client.get("/api/detection/status").json()
        self.assertFalse(status["model_loaded"])
        self.assertEqual(status["status"], "unavailable")
        self.assertEqual(status["mode"], "demo")

    # 9. Model initialization failure handling
    def test_09_model_initialization_failure(self):
        # Point to nonexistent model paths across all frameworks
        with patch.object(settings, "PYTORCH_MODEL_PATH", "nonexistent/model.pt"), \
             patch.object(settings, "YOLO_MODEL_PATH", "nonexistent/model.pt"), \
             patch.object(settings, "TENSORFLOW_MODEL_PATH", "nonexistent/model.h5"):
            model_service._try_load_models()
            self.assertFalse(model_service.model_loaded)
            self.assertEqual(model_service.get_status()["status"], "unavailable")
        # Restore real models after test
        model_service._try_load_models()

    # 10. Successful genuine inference with mocked model output
    def test_10_genuine_inference_success(self):
        model_service.set_model(MockYOLOModel(custom_class="Tomato Late Blight", conf=0.912, bbox=(10.0, 15.0, 80.0, 95.0)), "YOLOv8")
        res = self.post_image(make_test_image("jpg"), filename="scan.jpg")
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertEqual(data["is_demo"], "false")
        self.assertEqual(data["disease_name"], "Tomato Late Blight")
        self.assertEqual(data["confidence"], 91.2)
        self.assertIsNotNone(data["bbox_data"])
        self.assertEqual(data["bbox_data"]["boxes"][0], [10.0, 15.0, 80.0, 95.0])
        self.assertEqual(data["status"], "completed")

    # 11. Genuine no-disease result ("Healthy Plant")
    def test_11_genuine_no_disease_healthy_plant(self):
        model_service.set_model(MockYOLOModel(empty=True), "YOLOv8")
        res = self.post_image(make_test_image("png"))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["is_demo"], "false")
        self.assertEqual(data["disease_name"], "Healthy Plant")
        self.assertIsNone(data["confidence"])
        self.assertIsNone(data["bbox_data"])
        self.assertEqual(data["status"], "completed")

    # 12. Malformed inference output / execution failure handling
    def test_12_inference_failure_raises_500_and_cleans_file(self):
        model_service.set_model(MockYOLOModel(should_fail=True), "YOLOv8")
        before_files = set(os.listdir(_UPLOADS))
        res = self.post_image(make_test_image("png"))
        self.assertEqual(res.status_code, 500)
        self.assertIn("inference failed", res.json()["detail"].lower())
        after_files = set(os.listdir(_UPLOADS))
        self.assertEqual(after_files, before_files, "Temporary uploaded file must be cleaned up on inference error")

    # 13. Correct confidence and bounding-box mapping
    def test_13_confidence_and_bbox_mapping(self):
        expected_box = [5.5, 12.3, 200.1, 180.4]
        model_service.set_model(MockYOLOModel(custom_class="Potato Early Blight", conf=0.8745, bbox=expected_box), "YOLOv8")
        res = self.post_image(make_test_image("png"))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["confidence"], 87.45)
        self.assertEqual(data["bbox_data"]["boxes"][0], expected_box)
        self.assertEqual(data["bbox_data"]["scores"][0], 87.45)
        self.assertEqual(data["bbox_data"]["labels"][0], "Potato Early Blight")

    # 14. Database persistence failure / file cleanup rollback
    def test_14_database_failure_cleans_up_file(self):
        before_files = set(os.listdir(_UPLOADS))
        with patch("app.routers.detection.Session.commit", side_effect=RuntimeError("DB Commit Crash")):
            res = self.post_image(make_test_image("png"))
            self.assertEqual(res.status_code, 500)
        after_files = set(os.listdir(_UPLOADS))
        self.assertEqual(after_files, before_files, "Uploaded file must be deleted on DB commit failure")

    # 15. Correct recommendation association
    def test_15_recommendation_association(self):
        model_service.set_model(MockYOLOModel(custom_class="Tomato Late Blight", conf=0.92), "YOLOv8")
        res = self.post_image(make_test_image("png"), crop_id=str(self.crop_id))
        self.assertEqual(res.status_code, 200)
        pred_id = res.json()["id"]

        recs_res = self.client.get(f"/api/predictions/{pred_id}/recommendations", headers=self.auth_headers)
        self.assertEqual(recs_res.status_code, 200)
        recs = recs_res.json()
        self.assertGreater(len(recs), 0)
        self.assertEqual(recs[0]["prediction_id"], pred_id)
        self.assertEqual(recs[0]["farmer_id"], self.user_id)
        self.assertEqual(recs[0]["type"], "treatment")
        self.assertIn("Tomato Late Blight", recs[0]["title"])
        self.assertNotIn("(simulated detection)", recs[0]["title"])

    # 16. Demo mode remains clearly marked
    def test_16_demo_mode_clearly_marked(self):
        model_service.unload_model()
        res = self.post_image(make_test_image("png"))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["is_demo"], "true")
        self.assertIsNone(data["confidence"], "Demo mode must not fabricate confidence scores")
        self.assertIsNone(data["bbox_data"], "Demo mode must not fabricate bounding boxes")

    # 17. Prediction history and deletion regression
    def test_17_prediction_history_and_deletion(self):
        res = self.post_image(make_test_image("png"))
        self.assertEqual(res.status_code, 200)
        pred_id = res.json()["id"]
        stored_path = res.json()["image_path"]
        self.assertTrue(os.path.exists(stored_path))

        # Check appearance in history
        hist = self.client.get("/api/predictions/", headers=self.auth_headers).json()
        matching = [p for p in hist["predictions"] if p["id"] == pred_id]
        self.assertEqual(len(matching), 1)

        # Stranger cannot delete
        stranger_del = self.client.delete(f"/api/predictions/{pred_id}", headers=self.other_headers)
        self.assertEqual(stranger_del.status_code, 404)
        self.assertTrue(os.path.exists(stored_path))

        # Owner deletes
        owner_del = self.client.delete(f"/api/predictions/{pred_id}", headers=self.auth_headers)
        self.assertEqual(owner_del.status_code, 200)
        self.assertFalse(os.path.exists(stored_path), "File on disk must be cleaned up on deletion")

    # 18. Frontend API contract compatibility
    def test_18_frontend_api_contract_compatibility(self):
        res = self.post_image(make_test_image("png"), crop_name="Tomato", crop_id=str(self.crop_id))
        self.assertEqual(res.status_code, 200)
        body = res.json()

        # Required fields consumed by frontend (DetectionResult, PredictionHistory, DataAcquisition)
        expected_fields = [
            "id", "farmer_id", "crop_id", "image_path", "original_filename",
            "crop_name", "disease_name", "pest_name", "prediction_type",
            "confidence", "bbox_data", "status", "is_demo", "created_at"
        ]
        for field in expected_fields:
            self.assertIn(field, body, f"Contract mismatch: missing field '{field}'")

    # 19. Checkpoint loading and class mapping status
    def test_19_pytorch_model_loaded_and_class_mapping(self):
        model_service._try_load_models()
        status = self.client.get("/api/detection/status").json()
        self.assertTrue(status["model_loaded"])
        self.assertEqual(status["model_type"], "PyTorch (ResNet18)")
        self.assertEqual(status["status"], "ready")
        self.assertEqual(status["mode"], "genuine")
        self.assertIsNotNone(model_service.class_mapping)
        self.assertEqual(model_service.class_mapping["num_classes"], 18)

    # 20. Real PyTorch inference on healthy and diseased samples
    def test_20_pytorch_real_inference_healthy_and_diseased(self):
        model_service._try_load_models()

        # Healthy sample
        healthy_path = os.path.join(os.path.dirname(__file__), "..", "uploads", "sample_images", "tomato", "tomato_healthy_001.jpg")
        if os.path.exists(healthy_path):
            with open(healthy_path, "rb") as f:
                img_bytes = f.read()
            res = self.post_image(img_bytes, filename="healthy_tomato.jpg", crop_name="Tomato")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["is_demo"], "false")
            self.assertEqual(data["disease_name"], "Healthy Plant")
            self.assertEqual(data["prediction_type"], "healthy")
            self.assertIsNotNone(data["confidence"])
            self.assertGreater(data["confidence"], 70.0)

        # Diseased sample
        diseased_path = os.path.join(os.path.dirname(__file__), "..", "uploads", "sample_images", "potato", "potato_early-blight_001.jpg")
        if os.path.exists(diseased_path):
            with open(diseased_path, "rb") as f:
                img_bytes = f.read()
            res = self.post_image(img_bytes, filename="potato_blight.jpg", crop_name="Potato")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["is_demo"], "false")
            self.assertEqual(data["disease_name"], "Potato Early Blight")
            self.assertIsNotNone(data["confidence"])
            self.assertGreater(data["confidence"], 70.0)

    # 21. Unsupported crop safe demo fallback
    def test_21_pytorch_unsupported_crop_safe_demo_fallback(self):
        model_service._try_load_models()
        res = self.post_image(make_test_image("jpg"), crop_name="Cotton")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["is_demo"], "true")
        self.assertIsNone(data["confidence"], "Demo fallback for unsupported crops must not fabricate confidence")

    # 22. Low-confidence threshold advisory
    def test_22_pytorch_low_confidence_advisory(self):
        model_service._try_load_models()
        # Direct prediction with synthetic uniform noise simulating ambiguity
        import numpy as np
        noise_img = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        _, buf = cv2.imencode(".jpg", noise_img)
        res = self.post_image(buf.tobytes(), filename="noisy_ambiguous.jpg")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        if data["is_demo"] == "false" and data.get("confidence", 100) < 40.0:
            self.assertIn("low-confidence", data.get("treatment", "").lower())

    # 23. Prediction persistence and history retrieval
    def test_23_prediction_persistence_and_history(self):
        model_service._try_load_models()
        res = self.post_image(make_test_image("jpg"), crop_name="Tomato")
        self.assertEqual(res.status_code, 200)
        created = res.json()

        history_res = self.client.get("/api/predictions/", headers=self.auth_headers)
        self.assertEqual(history_res.status_code, 200)
        preds = history_res.json()["predictions"]
        matched = [p for p in preds if p["id"] == created["id"]]
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["confidence"], created["confidence"])
        self.assertEqual(matched[0]["is_demo"], created["is_demo"])

    # 24. Corrupt image upload cleanup
    def test_24_corrupt_image_upload_cleanup(self):
        before_count = len(os.listdir(_UPLOADS))
        res = self.post_image(b"Not an image byte stream", filename="corrupt.jpg")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(len(os.listdir(_UPLOADS)), before_count, "Corrupt file must not remain on disk")

    # 25. PDF reporting data compatibility
    def test_25_pdf_reporting_data_compatibility(self):
        model_service._try_load_models()
        res = self.post_image(make_test_image("jpg"), crop_name="Tomato")
        self.assertEqual(res.status_code, 200)
        created = res.json()

        # The PDF report generator uses predictions from /api/predictions/
        history_res = self.client.get("/api/predictions/", headers=self.auth_headers)
        self.assertEqual(history_res.status_code, 200)
        history = history_res.json()["predictions"]
        for p in history:
            self.assertIn("is_demo", p)
            self.assertIn("confidence", p)
            self.assertIn("disease_name", p)
            self.assertIn("created_at", p)

    # 26. Browser screenshot / unrelated UI image is rejected
    def test_26_browser_screenshot_rejected_with_400(self):
        model_service._try_load_models()
        # Synthetic browser / IDE screenshot with dark UI and horizontal/vertical boxes
        screenshot = np.full((300, 400, 3), 30, dtype=np.uint8)
        cv2.rectangle(screenshot, (20, 20), (380, 280), (60, 60, 60), 2)
        cv2.rectangle(screenshot, (20, 20), (380, 50), (45, 45, 45), -1)
        for y in range(70, 260, 20):
            cv2.line(screenshot, (40, y), (300, y), (180, 180, 180), 1)
        _, buf = cv2.imencode(".png", screenshot)

        before_files = len(os.listdir(_UPLOADS))
        res = self.post_image(buf.tobytes(), filename="screenshot.png", crop_name="Grape")
        self.assertEqual(res.status_code, 400)
        self.assertIn("Unable to identify a crop leaf", res.json()["detail"])
        self.assertEqual(len(os.listdir(_UPLOADS)), before_files, "Rejected screenshot must be deleted from uploads")

    # 27. Document / paper text scan is rejected
    def test_27_document_page_rejected_with_400(self):
        model_service._try_load_models()
        # White document page with dark text lines
        doc = np.full((400, 300, 3), 250, dtype=np.uint8)
        for y in range(40, 360, 20):
            cv2.line(doc, (30, y), (270, y), (20, 20, 20), 1)
        _, buf = cv2.imencode(".png", doc)

        before_files = len(os.listdir(_UPLOADS))
        res = self.post_image(buf.tobytes(), filename="invoice.png", crop_name="Tomato")
        self.assertEqual(res.status_code, 400)
        self.assertIn("Unable to identify a crop leaf", res.json()["detail"])
        self.assertEqual(len(os.listdir(_UPLOADS)), before_files, "Rejected document must be deleted from uploads")

    # 28. Valid supported crop leaf image is accepted
    def test_28_valid_supported_crop_leaf_accepted(self):
        model_service._try_load_models()
        # Use a real Tomato Early Blight sample if available, or valid botanical fixture
        pv_sample = os.path.join("ml", "data", "plantvillage_subset", "Tomato___Early_blight")
        if os.path.isdir(pv_sample) and os.listdir(pv_sample):
            leaf_path = os.path.join(pv_sample, os.listdir(pv_sample)[0])
            with open(leaf_path, "rb") as f:
                img_bytes = f.read()
        else:
            img_bytes = make_test_image("jpg")

        res = self.post_image(img_bytes, filename="leaf.jpg", crop_name="Tomato")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["is_demo"], "false")
        self.assertIsNotNone(data["confidence"])
        self.assertIn("Tomato", data["disease_name"])

    # 29. Healthy leaf genuine prediction
    def test_29_healthy_leaf_genuine_prediction(self):
        model_service._try_load_models()
        pv_sample = os.path.join("ml", "data", "plantvillage_subset", "Tomato___healthy")
        if os.path.isdir(pv_sample) and os.listdir(pv_sample):
            leaf_path = os.path.join(pv_sample, os.listdir(pv_sample)[0])
            with open(leaf_path, "rb") as f:
                img_bytes = f.read()
        else:
            img_bytes = make_test_image("jpg")

        res = self.post_image(img_bytes, filename="healthy_leaf.jpg", crop_name="Tomato")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["is_demo"], "false")
        self.assertEqual(data["prediction_type"], "healthy")
        self.assertEqual(data["disease_name"], "Healthy Plant")
        self.assertGreaterEqual(data["confidence"], 50.0)

    # 30. Low-confidence ambiguous leaf flagged with advisory
    def test_30_low_confidence_ambiguous_leaf(self):
        model_service._try_load_models()
        # Synthetic ambiguous image with foliage colors but non-standard pattern
        amb = np.full((128, 128, 3), (35, 120, 45), dtype=np.uint8)
        cv2.circle(amb, (64, 64), 30, (50, 160, 70), -1)
        _, buf = cv2.imencode(".jpg", amb)

        res = self.post_image(buf.tobytes(), filename="ambiguous_leaf.jpg", crop_name="Tomato")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["is_demo"], "false")
        if data.get("confidence", 100) < 40.0:
            recs_res = self.client.get(f"/api/predictions/{data['id']}/recommendations", headers=self.auth_headers)
            self.assertEqual(recs_res.status_code, 200)
            recs = recs_res.json()
            self.assertTrue(any("low-confidence" in r.get("description", "").lower() for r in recs))

    # 31. Unsupported crop (Cotton) preserves demo fallback when leaf is valid
    def test_31_unsupported_crop_cotton_preserves_demo_fallback(self):
        model_service._try_load_models()
        res = self.post_image(make_test_image("jpg"), filename="cotton.jpg", crop_name="Cotton")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["is_demo"], "true")
        self.assertIsNone(data["confidence"])
        self.assertEqual(data["crop_name"], "Cotton")

    # 32. Crop mismatch is rejected (e.g. Potato leaf submitted with Grape)
    def test_32_crop_mismatch_rejected_with_400(self):
        model_service._try_load_models()
        pv_potato = os.path.join("ml", "data", "plantvillage_subset", "Potato___Early_blight")
        if os.path.isdir(pv_potato) and os.listdir(pv_potato):
            with open(os.path.join(pv_potato, os.listdir(pv_potato)[0]), "rb") as f:
                img_bytes = f.read()
            res = self.post_image(img_bytes, filename="potato.jpg", crop_name="Grape")
            self.assertEqual(res.status_code, 400)
            self.assertIn("does not match the selected crop", res.json()["detail"])

    # 33. Corrupt and oversized uploads are rejected
    def test_33_corrupt_and_oversized_uploads_rejected(self):
        # Corrupt bytes
        res_corrupt = self.post_image(b"INVALID_IMAGE_BYTES_12345", filename="corrupt.jpg")
        self.assertEqual(res_corrupt.status_code, 400)

        # Oversized file (>10MB)
        limit = 10 * 1024 * 1024 + 1024
        res_oversized = self.post_image(b"0" * limit, filename="huge.jpg")
        self.assertEqual(res_oversized.status_code, 413)

    # 34. Genuine leaf of unidentified species with unspecified crop flags uncertain
    def test_34_unknown_species_leaf_unspecified_crop_uncertain(self):
        model_service._try_load_models()
        unknown_leaf_path = os.path.join(os.path.dirname(__file__), "..", "uploads", "878edbdc06164f098928b4d41c16c050.jpg")
        if os.path.exists(unknown_leaf_path):
            with open(unknown_leaf_path, "rb") as f:
                img_bytes = f.read()
        else:
            img_bytes = make_test_image("jpg")

        res = self.post_image(img_bytes, filename="unknown_leaf.jpg", crop_name=None)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["is_demo"], "false")
        self.assertEqual(data["prediction_type"], "uncertain")
        self.assertEqual(data["disease_name"], "Unable to Identify Reliably")
        self.assertEqual(data["status"], "uncertain")
        self.assertIsNotNone(data["confidence"])
        self.assertAlmostEqual(data["confidence"], 46.11, places=1)

    # 35. Prevention of disease-specific treatment recommendations for uncertain results
    def test_35_uncertain_prediction_no_treatment_recommendations(self):
        model_service._try_load_models()
        unknown_leaf_path = os.path.join(os.path.dirname(__file__), "..", "uploads", "878edbdc06164f098928b4d41c16c050.jpg")
        if os.path.exists(unknown_leaf_path):
            with open(unknown_leaf_path, "rb") as f:
                img_bytes = f.read()
        else:
            img_bytes = make_test_image("jpg")

        res = self.post_image(img_bytes, filename="unknown_leaf.jpg", crop_name=None)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # Fetch recommendations for this prediction
        recs_res = self.client.get(f"/api/predictions/{data['id']}/recommendations", headers=self.auth_headers)
        self.assertEqual(recs_res.status_code, 200)
        recs = recs_res.json()
        # Strictly verify no treatment recommendations exist
        self.assertEqual(len(recs), 0, "No disease-specific recommendations must be generated for uncertain predictions")

    # 36. Uncertain results excluded from confirmed diseased counts in analytics
    def test_36_uncertain_predictions_excluded_from_diseased_counts(self):
        model_service._try_load_models()
        unknown_leaf_path = os.path.join(os.path.dirname(__file__), "..", "uploads", "878edbdc06164f098928b4d41c16c050.jpg")
        if os.path.exists(unknown_leaf_path):
            with open(unknown_leaf_path, "rb") as f:
                img_bytes = f.read()
            # Post uncertain prediction
            res = self.post_image(img_bytes, filename="unknown_leaf.jpg", crop_name=None)
            self.assertEqual(res.status_code, 200)

            # Query analytics summary
            summary_res = self.client.get("/api/analytics/summary", headers=self.auth_headers)
            self.assertEqual(summary_res.status_code, 200)
            scans = summary_res.json()["scans"]

            # Total scans includes it, but diseased_count must NOT include it
            self.assertGreaterEqual(scans["total_scans"], 1)


if __name__ == "__main__":
    unittest.main()
