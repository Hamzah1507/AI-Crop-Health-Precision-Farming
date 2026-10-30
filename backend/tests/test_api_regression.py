"""
API regression tests. They run against a TEMPORARY database and upload folder;
your real app.db and uploads/ are never touched (a guard below enforces that).

Run from the backend folder:  python -m unittest tests.test_api_regression -v

Weather tests call the live Open-Meteo service and are skipped if it is unreachable.
"""
import os
import shutil
import struct
import tempfile
import unittest
import warnings

# Suppress harmless testclient deprecation warning and resource warnings during test runs
warnings.filterwarnings("ignore", message=r".*httpx.*", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=ResourceWarning)

import zlib
from datetime import datetime, timedelta, timezone

# --- Point the app at temporary storage BEFORE it is imported -----------------
_TMP = tempfile.mkdtemp(prefix="cp_tests_")
_UPLOADS = os.path.join(_TMP, "uploads")
_DB_PATH = os.path.join(_TMP, "test.db")
os.environ["DATABASE_URL"] = "sqlite:///" + _DB_PATH.replace("\\", "/")
os.environ["UPLOAD_DIR"] = _UPLOADS
os.makedirs(_UPLOADS, exist_ok=True)

import numpy as np                      # noqa: E402
import cv2                              # noqa: E402
from fastapi.testclient import TestClient   # noqa: E402
from jose import jwt                    # noqa: E402
from sqlalchemy import create_engine    # noqa: E402
from sqlalchemy.orm import sessionmaker # noqa: E402

from app.config import get_settings, secret_key_is_placeholder   # noqa: E402
from app.database import Base, get_db   # noqa: E402
from app.main import app                # noqa: E402

settings = get_settings()
client = None
_references = 0     # several test modules share this fixture; it is torn down when the last one finishes
_engine = None
_SessionLocal = None
_orig_upload_dir = None


def acquire():
    """Set up the shared temporary DB + client (first caller only)."""
    global client, _references, _TMP, _UPLOADS, _DB_PATH, _engine, _SessionLocal, _orig_upload_dir
    if _references == 0:
        if _TMP is None or not os.path.isdir(_TMP):
            _TMP = tempfile.mkdtemp(prefix="cp_tests_")
            _UPLOADS = os.path.join(_TMP, "uploads")
            _DB_PATH = os.path.join(_TMP, "test.db")
            os.makedirs(_UPLOADS, exist_ok=True)

        _engine = create_engine(
            f"sqlite:///{_DB_PATH.replace('\\', '/')}",
            connect_args={"check_same_thread": False}
        )
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        Base.metadata.create_all(bind=_engine)

        def override_get_db():
            db = _SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db

        _orig_upload_dir = settings.UPLOAD_DIR
        settings.UPLOAD_DIR = _UPLOADS

        # Safety guard: refuse to run if the engine is not pointing to the temporary storage.
        if os.path.normcase(os.path.abspath(_engine.url.database or "")).startswith(os.path.normcase(_TMP)) is False:
            raise RuntimeError("Tests are not using the temporary database; refusing to run.")
        if os.path.normcase(os.path.abspath(settings.UPLOAD_DIR)) != os.path.normcase(os.path.abspath(_UPLOADS)):
            raise RuntimeError("Tests are not using the temporary upload folder; refusing to run.")

        client = TestClient(app)
        client.__enter__()   # runs the startup hook that creates the tables
    _references += 1


def release():
    """Tear the shared fixture down when the last module has finished."""
    global client, _references, _TMP, _UPLOADS, _DB_PATH, _engine, _SessionLocal, _orig_upload_dir
    _references -= 1
    if _references == 0:
        if client:
            client.__exit__(None, None, None)
            client = None
        app.dependency_overrides.pop(get_db, None)
        if _orig_upload_dir is not None:
            settings.UPLOAD_DIR = _orig_upload_dir
            _orig_upload_dir = None
        if _engine:
            _engine.dispose()
            _engine = None
        _SessionLocal = None
        if _TMP and os.path.isdir(_TMP):
            shutil.rmtree(_TMP, ignore_errors=True)
            _TMP = None
            _UPLOADS = None
            _DB_PATH = None


setUpModule, tearDownModule = acquire, release


def make_image(fmt: str, width=64, height=48) -> bytes:
    img = np.zeros((height, width, 3), np.uint8)
    img[:] = (40, 140, 50)
    cv2.circle(img, (width // 2, height // 2), min(width, height) // 3, (30, 200, 60), -1)
    ok, buf = cv2.imencode("." + fmt, img)
    assert ok
    return buf.tobytes()


def png_claiming(width, height) -> bytes:
    """A tiny PNG whose header claims a huge canvas (decompression-bomb shape)."""
    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IEND", b"")


def register(username):
    r = client.post("/api/auth/register", json={"username": username, "email": f"{username}@example.com", "password": "secret12"})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def upload_files():
    return sorted(os.listdir(_UPLOADS)) if os.path.isdir(_UPLOADS) else []


class Security(unittest.TestCase):
    def test_registration_cannot_assign_admin(self):
        for i, role in enumerate(["admin", "ADMIN", "superuser", None]):
            body = {"username": f"sec_user{i}", "email": f"sec{i}@example.com", "password": "secret12"}
            if role:
                body["role"] = role
            r = client.post("/api/auth/register", json=body)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()["role"], "farmer")
            headers = {"Authorization": "Bearer " + r.json()["access_token"]}
            self.assertEqual(client.get("/api/auth/me", headers=headers).json()["role"], "farmer")
            self.assertEqual(client.get("/api/admin/stats", headers=headers).status_code, 403)
            self.assertEqual(client.get("/api/admin/users", headers=headers).status_code, 403)

    def test_wrong_password_returns_clear_401(self):
        register("sec_login")
        r = client.post("/api/auth/login", json={"username": "sec_login", "password": "WRONG"})
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()["detail"], "Invalid username or password")
        self.assertEqual(client.post("/api/auth/login", json={"username": "sec_login", "password": "secret12"}).status_code, 200)

    def test_jwt_secret_is_not_a_placeholder(self):
        self.assertFalse(secret_key_is_placeholder(settings.SECRET_KEY))
        self.assertGreaterEqual(len(settings.SECRET_KEY), 64)

    def test_tokens_signed_with_old_or_default_secrets_are_rejected(self):
        register("sec_forge")
        exp = datetime.now(timezone.utc) + timedelta(hours=1)
        for guessed in ("dev-secret-key-change-in-production", "your-super-secret-key-change-in-production"):
            token = jwt.encode({"user_id": 1, "username": "x", "role": "admin", "exp": exp}, guessed, algorithm="HS256")
            r = client.get("/api/admin/stats", headers={"Authorization": "Bearer " + token})
            self.assertEqual(r.status_code, 401, guessed)

    def test_protected_endpoints_need_a_token(self):
        for path in ("/api/predictions/", "/api/farms/", "/api/soil/records", "/api/recommendations/", "/api/users/profile"):
            self.assertIn(client.get(path).status_code, (401, 403), path)


class ImageUploads(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = register("upload_user")

    def post(self, content, filename="leaf.png", content_type="image/png", **data):
        return client.post("/api/detection/predict", headers=self.h, files={"file": (filename, content, content_type)}, data=data)

    def test_valid_formats_are_accepted_and_extension_comes_from_the_bytes(self):
        status = client.get("/api/detection/status").json()
        expected_demo = "false" if status.get("model_loaded") else "true"
        for fmt, ext in (("jpg", ".jpg"), ("png", ".png"), ("webp", ".webp")):
            with self.subTest(fmt=fmt):
                r = self.post(make_image(fmt), filename=f"photo.{fmt}")
                self.assertEqual(r.status_code, 200, r.text)
                self.assertTrue(r.json()["image_path"].endswith(ext))
                self.assertEqual(r.json()["is_demo"], expected_demo)

    def test_real_bytes_win_over_filename_and_content_type(self):
        r = self.post(make_image("png"), filename="really_a_png.jpg", content_type="application/octet-stream")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json()["image_path"].endswith(".png"))

    def test_fake_image_with_image_content_type_is_rejected(self):
        before = upload_files()
        for payload in (b"<html><script>alert(1)</script></html>", b"just text", b"GIF89a\x01\x00\x01\x00\x00\x00\x00;", b"%PDF-1.4 fake"):
            with self.subTest(payload=payload[:12]):
                self.assertEqual(self.post(payload, content_type="image/png").status_code, 400)
        self.assertEqual(upload_files(), before, "rejected uploads must not be written to disk")

    def test_corrupt_and_truncated_images_are_rejected(self):
        before = upload_files()
        good = make_image("png")
        cases = {"truncated": good[: len(good) // 2], "garbage body": good[:33] + b"\x00" * 500, "empty": b""}
        for name, payload in cases.items():
            with self.subTest(case=name):
                self.assertEqual(self.post(payload).status_code, 400)
        self.assertEqual(upload_files(), before)

    def test_oversized_file_is_rejected_with_413(self):
        before = upload_files()
        limit = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        r = self.post(b"\x89PNG\r\n\x1a\n" + b"0" * limit)
        self.assertEqual(r.status_code, 413)
        self.assertIn("too large", r.json()["detail"].lower())
        self.assertEqual(upload_files(), before)

    def test_decompression_bomb_header_is_rejected_before_decoding(self):
        before = upload_files()
        r = self.post(png_claiming(60000, 60000))
        self.assertEqual(r.status_code, 400)
        self.assertIn("too large", r.json()["detail"].lower())
        self.assertEqual(upload_files(), before)

    def test_tiny_dimensions_are_rejected(self):
        self.assertEqual(self.post(make_image("png", width=4, height=4)).status_code, 400)

    def test_unsafe_filenames_cannot_escape_the_upload_folder(self):
        root = os.path.realpath(_UPLOADS)
        for name in ("../../evil.png", "..\\..\\evil.png", "/etc/passwd.png", "C:\\Windows\\evil.png", "a\x00b.png", "x.php.png", "..."):
            with self.subTest(filename=name):
                r = self.post(make_image("png"), filename=name)
                self.assertEqual(r.status_code, 200, r.text)
                body = r.json()
                stored = os.path.realpath(body["image_path"])
                self.assertEqual(os.path.commonpath([root, stored]), root)
                self.assertRegex(os.path.basename(stored), r"^[0-9a-f]{32}\.png$")
                shown = body["original_filename"] or ""
                self.assertNotRegex(shown, r"[\\/\x00]")
                self.assertNotIn("..", shown.replace("x.php.png", ""))

    def test_crop_link_must_belong_to_the_user(self):
        other = register("upload_other")
        farm = client.post("/api/farms/", headers=other, json={"name": "Other Farm"}).json()
        crop = client.post("/api/crops/", headers=other, json={"farm_id": farm["id"], "name": "Rice"}).json()
        before = upload_files()
        self.assertEqual(self.post(make_image("png"), crop_id=str(crop["id"])).status_code, 404)
        self.assertEqual(upload_files(), before)


class SoilApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = register("soil_user")

    def analyze(self, **kw):
        r = client.post("/api/soil/analyze", headers=self.h, json=kw)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_low_moderate_and_suitable_through_the_api(self):
        low = self.analyze(ph=5, nitrogen=10, phosphorus=10, potassium=15, moisture=25)
        self.assertIn(low["soil_health_status"], ("Poor", "Critical"))
        self.assertLess(low["soil_health_score"], 45)
        self.assertIn("5 of 5", low["health_summary"])
        moderate = self.analyze(ph=5.5, nitrogen=15, phosphorus=20, potassium=18, moisture=25)
        self.assertEqual(moderate["soil_health_status"], "Moderate")
        suitable = self.analyze(ph=6.5, nitrogen=35, phosphorus=25, potassium=30, moisture=50)
        self.assertEqual((suitable["soil_health_status"], suitable["soil_health_score"]), ("Excellent", 100.0))
        self.assertIsNone(suitable["weather_used"])

    def test_latest_soil_summary_is_read_only_and_matches_the_analysis(self):
        h = register("soil_latest")
        empty = client.get("/api/soil/latest", headers=h).json()
        self.assertEqual((empty["total_records"], empty["record"], empty["analysis"]), (0, None, None))

        client.post("/api/soil/records", headers=h, json={"ph": 6.5, "nitrogen": 35, "phosphorus": 25, "potassium": 30, "moisture": 50})
        client.post("/api/soil/records", headers=h, json={"ph": 5, "nitrogen": 10, "phosphorus": 10, "potassium": 15, "moisture": 25})
        before = len(client.get("/api/soil/records", headers=h).json())
        recs_before = len(client.get("/api/recommendations/", headers=h).json())

        latest = client.get("/api/soil/latest", headers=h).json()
        self.assertEqual(latest["total_records"], 2)
        self.assertEqual(latest["record"]["ph"], 5)                        # the newer record wins
        analysis = latest["analysis"]
        full = client.post("/api/soil/analyze", headers=h, json={"ph": 5, "nitrogen": 10, "phosphorus": 10, "potassium": 15, "moisture": 25}).json()
        self.assertEqual(analysis["soil_health_status"], full["soil_health_status"])
        self.assertEqual(analysis["soil_health_score"], full["soil_health_score"])
        self.assertIn(analysis["soil_health_status"], ("Poor", "Critical"))

        # Read-only: the lookups above stored nothing (only the explicit /analyze call added one record)
        self.assertEqual(len(client.get("/api/soil/records", headers=h).json()), before + 1)
        client.get("/api/soil/latest", headers=h)
        self.assertEqual(len(client.get("/api/soil/records", headers=h).json()), before + 1)
        self.assertGreaterEqual(len(client.get("/api/recommendations/", headers=h).json()), recs_before)

        self.assertIn(client.get("/api/soil/latest").status_code, (401, 403))
        other = register("soil_latest_other")
        self.assertIsNone(client.get("/api/soil/latest", headers=other).json()["record"], "records are per-user")

    def test_soil_record_ownership_and_zero_values(self):
        other = register("soil_other")
        farm = client.post("/api/farms/", headers=other, json={"name": "Not Yours"}).json()
        self.assertEqual(client.post("/api/soil/records", headers=self.h, json={"farm_id": farm["id"], "ph": 6}).status_code, 404)
        r = client.post("/api/soil/records", headers=self.h, json={"ph": 6.5, "nitrogen": 0})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["nitrogen"], 0)


class Workflows(unittest.TestCase):
    """Data acquisition -> detection -> history -> recommendations -> yield -> dashboard counts -> profile."""

    @classmethod
    def setUpClass(cls):
        cls.h = register("flow_user")

    def test_full_workflow(self):
        h = self.h
        # Data acquisition: farm + crop + soil, resubmitting the same farm must not duplicate it
        f1 = client.post("/api/farms/", headers=h, json={"name": "Green Valley Farm", "location": "Pune", "area": 10}).json()
        f2 = client.post("/api/farms/", headers=h, json={"name": " green valley farm ", "area": 12}).json()
        self.assertEqual(f1["id"], f2["id"])
        self.assertEqual(f2["area"], 12)
        self.assertEqual(f2["location"], "Pune", "location is kept when not re-sent")
        c1 = client.post("/api/crops/", headers=h, json={"farm_id": f1["id"], "name": "Tomato"}).json()
        c2 = client.post("/api/crops/", headers=h, json={"farm_id": f1["id"], "name": "tomato"}).json()
        self.assertEqual(c1["id"], c2["id"])
        soil = client.post("/api/soil/records", headers=h, json={"farm_id": f1["id"], "crop_id": c1["id"], "ph": 6.5, "nitrogen": 0}).json()
        self.assertEqual((soil["farm_id"], soil["crop_id"], soil["nitrogen"]), (f1["id"], c1["id"], 0))

        # Detection: genuine inference when model loaded, fallback to simulated if not
        r = client.post("/api/detection/predict", headers=h, files={"file": ("leaf.jpg", make_image("jpg"), "image/jpeg")},
                        data={"crop_name": "Tomato", "crop_id": str(c1["id"])})
        self.assertEqual(r.status_code, 200, r.text)
        pred = r.json()
        status = client.get("/api/detection/status").json()
        if status.get("model_loaded"):
            self.assertEqual(pred["is_demo"], "false")
            self.assertIsInstance(pred["confidence"], (int, float))
            self.assertIsNone(pred["bbox_data"])
            self.assertEqual(pred["crop_id"], c1["id"])
            recs = client.get(f"/api/predictions/{pred['id']}/recommendations", headers=h).json()
            self.assertTrue(len(recs) > 0)
        else:
            self.assertEqual((pred["is_demo"], pred["confidence"], pred["bbox_data"], pred["crop_id"]), ("true", None, None, c1["id"]))
            recs = client.get(f"/api/predictions/{pred['id']}/recommendations", headers=h).json()
            self.assertTrue(recs and "(simulated detection)" in recs[0]["title"])

        # History, ownership and deletion
        self.assertEqual(client.get("/api/predictions/", headers=h).json()["total"], 1)
        stranger = register("flow_stranger")
        self.assertEqual(client.get(f"/api/predictions/{pred['id']}", headers=stranger).status_code, 404)
        self.assertEqual(client.delete(f"/api/predictions/{pred['id']}", headers=stranger).status_code, 404)

        # Recommendations come from soil analysis; yield estimate is deterministic and flagged as an estimate
        client.post("/api/soil/analyze", headers=h, json={"ph": 5, "nitrogen": 10, "phosphorus": 10, "potassium": 15, "moisture": 25})
        all_recs = client.get("/api/recommendations/", headers=h).json()
        self.assertTrue(any(x["type"] == "fertilizer" for x in all_recs) and any(x["type"] == "irrigation" for x in all_recs))
        body = {"crop_name": "Rice", "area": 2, "soil_ph": 6.5, "soil_nitrogen": 30, "soil_moisture": 50, "temperature": 25, "rainfall": 8}
        y1 = client.post("/api/yield/predict", headers=h, json=body).json()
        y2 = client.post("/api/yield/predict", headers=h, json=body).json()
        self.assertEqual(y1["predicted_yield"], y2["predicted_yield"])
        self.assertEqual(y1["is_demo"], "true")
        self.assertTrue(y1["factors"] and all({"factor", "impact", "detail"} <= set(f) for f in y1["factors"]))
        self.assertIn("Not a trained ML model", y1["model_note"])
        history = client.get("/api/yield/history", headers=h).json()
        self.assertTrue(history and history[0]["factors"] == [], "stored history rows carry no calculated factors")

        # Dashboard counts (the same endpoints the dashboard calls)
        self.assertEqual(len(client.get("/api/farms/", headers=h).json()), 1)
        self.assertEqual(len(client.get("/api/crops/", headers=h).json()), 1)
        self.assertEqual(len(client.get("/api/soil/records", headers=h).json()), 2)   # data entry + analysis
        self.assertEqual(len(client.get("/api/yield/history", headers=h).json()), 2)
        self.assertEqual(client.get("/api/predictions/", headers=h).json()["total"], 1)

        # Delete the prediction
        self.assertEqual(client.delete(f"/api/predictions/{pred['id']}", headers=h).status_code, 200)
        self.assertEqual(client.get("/api/predictions/", headers=h).json()["total"], 0)

        # Profile persists
        client.put("/api/users/profile", headers=h, json={"full_name": "Asha Patil", "phone": "9876543210", "address": "Pune", "experience_years": 7})
        profile = client.get("/api/users/profile", headers=h).json()["profile"]
        self.assertEqual((profile["full_name"], profile["phone"], profile["experience_years"]), ("Asha Patil", "9876543210", 7))


class DefaultFarm(unittest.TestCase):
    """POST /api/farms/default: one default Ahmedabad farm per user, created only when they have none."""

    NAME, LOCATION = "My Ahmedabad Farm", "Ahmedabad, Gujarat, India"

    def ensure(self, h):
        r = client.post("/api/farms/default", headers=h)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def farms(self, h):
        return client.get("/api/farms/", headers=h).json()

    def test_new_user_gets_exactly_one_default_farm_with_no_invented_values(self):
        h = register("df_new")
        self.assertEqual(self.farms(h), [], "registration itself creates nothing")
        body = self.ensure(h)
        self.assertTrue(body["created"])
        self.assertEqual((body["farm"]["name"], body["farm"]["location"]), (self.NAME, self.LOCATION))
        self.assertIsNone(body["farm"]["area"], "no area is invented")
        self.assertEqual((body["default_farm_name"], body["default_location"]), (self.NAME, self.LOCATION))
        self.assertEqual(len(self.farms(h)), 1)
        # No crops, soil records or detections are fabricated for the default farm
        self.assertEqual(client.get("/api/crops/", headers=h).json(), [])
        self.assertEqual(client.get("/api/soil/latest", headers=h).json()["record"], None)
        self.assertEqual(client.get("/api/predictions/", headers=h).json()["total"], 0)

    def test_existing_user_with_data_but_no_farm_gets_one_farm(self):
        h = register("df_existing")
        client.post("/api/soil/records", headers=h, json={"ph": 6.5, "nitrogen": 30})   # farm-less data from before
        self.assertEqual(self.farms(h), [])
        body = self.ensure(h)
        self.assertTrue(body["created"])
        self.assertEqual(len(self.farms(h)), 1)
        self.assertEqual(len(client.get("/api/soil/records", headers=h).json()), 1, "existing data is untouched")

    def test_user_with_a_farm_never_receives_a_duplicate_and_keeps_their_location(self):
        h = register("df_has_farm")
        mine = client.post("/api/farms/", headers=h, json={"name": "Green Valley", "location": "Pune, India", "area": 10}).json()
        body = self.ensure(h)
        self.assertFalse(body["created"])
        self.assertEqual(body["farm"]["id"], mine["id"])
        farms = self.farms(h)
        self.assertEqual([(f["name"], f["location"], f["area"]) for f in farms], [("Green Valley", "Pune, India", 10)])

    def test_a_farm_without_a_location_is_not_modified_either(self):
        h = register("df_no_loc")
        mine = client.post("/api/farms/", headers=h, json={"name": "Bare Farm"}).json()
        body = self.ensure(h)
        self.assertFalse(body["created"])
        self.assertIsNone(self.farms(h)[0]["location"], "the default location is offered for weather, never written onto the user's farm")
        self.assertEqual(body["farm"]["id"], mine["id"])

    def test_repeated_dashboard_loads_create_nothing_more(self):
        h = register("df_repeat")
        results = [self.ensure(h) for _ in range(6)]
        self.assertEqual([r["created"] for r in results], [True] + [False] * 5)
        self.assertEqual(len({r["farm"]["id"] for r in results}), 1)
        self.assertEqual(len(self.farms(h)), 1)

    def test_simultaneous_first_loads_create_exactly_one_farm(self):
        import threading
        h = register("df_race")
        barrier = threading.Barrier(8)
        out, lock = [], threading.Lock()

        def worker():
            barrier.wait()
            r = client.post("/api/farms/default", headers=h)
            with lock:
                out.append((r.status_code, r.json().get("created")))

        threads = [threading.Thread(target=worker) for _ in range(8)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertTrue(all(code == 200 for code, _ in out), out)
        self.assertEqual(sum(1 for _, created in out if created), 1, "exactly one request inserted the farm")
        self.assertEqual(len(self.farms(h)), 1)

    def test_users_cannot_see_or_change_each_others_farms(self):
        a, b = register("df_iso_a"), register("df_iso_b")
        fa, fb = self.ensure(a)["farm"], self.ensure(b)["farm"]
        self.assertNotEqual(fa["id"], fb["id"], "each user gets their own farm, never a shared one")
        self.assertEqual([f["id"] for f in self.farms(a)], [fa["id"]])
        self.assertEqual([f["id"] for f in self.farms(b)], [fb["id"]])
        for call in (lambda: client.get(f"/api/farms/{fa['id']}", headers=b),
                     lambda: client.put(f"/api/farms/{fa['id']}", headers=b, json={"location": "Hacked"}),
                     lambda: client.delete(f"/api/farms/{fa['id']}", headers=b)):
            self.assertEqual(call().status_code, 404)
        self.assertEqual(self.farms(a)[0]["location"], self.LOCATION)

    def test_a_location_the_user_changes_is_not_overwritten_by_the_default(self):
        h = register("df_changed")
        farm = self.ensure(h)["farm"]
        r = client.put(f"/api/farms/{farm['id']}", headers=h, json={"location": "Surat, Gujarat, India", "area": 4.5})
        self.assertEqual(r.status_code, 200)
        body = self.ensure(h)
        self.assertFalse(body["created"])
        self.assertEqual((body["farm"]["location"], body["farm"]["area"]), ("Surat, Gujarat, India", 4.5))
        self.assertEqual(len(self.farms(h)), 1)

    def test_existing_farm_and_crop_creation_still_works_alongside_the_default(self):
        h = register("df_coexist")
        default = self.ensure(h)["farm"]
        mine = client.post("/api/farms/", headers=h, json={"name": "Green Valley", "location": "Pune, India"}).json()
        self.assertNotEqual(mine["id"], default["id"])
        again = client.post("/api/farms/", headers=h, json={"name": " green valley "}).json()
        self.assertEqual(again["id"], mine["id"], "the existing same-name de-duplication still applies")
        crop = client.post("/api/crops/", headers=h, json={"farm_id": default["id"], "name": "Rice"})
        self.assertEqual(crop.status_code, 200)
        self.assertEqual(len(self.farms(h)), 2)
        self.assertEqual(len(self.farms(h)), len({f["id"] for f in self.farms(h)}))
        self.assertFalse(self.ensure(h)["created"])

    def test_requires_authentication(self):
        self.assertIn(client.post("/api/farms/default").status_code, (401, 403))

    def test_default_location_resolves_to_ahmedabad_through_the_open_meteo_integration(self):
        h = register("df_weather")
        location = self.ensure(h)["default_location"]
        r = client.get("/api/weather/current", headers=h, params={"location": location})
        body = r.json()
        if r.status_code != 200 or not body.get("is_live"):
            self.skipTest("Open-Meteo is unreachable from this machine")
        self.assertIn("Ahmedabad", body["resolved_location"])
        self.assertIn("Gujarat", body["resolved_location"])
        self.assertEqual(len(body["forecast"]), 5)
        self.assertIn("Open-Meteo", body["attribution"])


class Weather(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = register("weather_user")

    def fetch(self, location):
        return client.post("/api/weather/fetch", headers=self.h, json={"location": location})

    def test_live_weather_forecast_and_attribution(self):
        r = self.fetch("Pune, India")
        body = r.json()
        if r.status_code != 200 or not body.get("is_live"):
            self.skipTest("Open-Meteo is unreachable from this machine")
        self.assertIn("India", body["resolved_location"])
        self.assertEqual(len(body["forecast"]), 5)
        self.assertIn("Open-Meteo", body["attribution"])
        self.assertIsNotNone(body["id"], "live results are stored")

    def test_unknown_location_is_404_not_invented_data(self):
        r = self.fetch("Zzxqwv Nowhereville")
        if r.status_code == 200 and not r.json().get("is_live"):
            self.skipTest("Open-Meteo is unreachable from this machine")
        self.assertEqual(r.status_code, 404)

    def test_dashboard_lookup_returns_live_data_without_storing_anything(self):
        from app.models.weather_record import WeatherRecord
        db = _SessionLocal()
        try:
            before = db.query(WeatherRecord).count()
            r = client.get("/api/weather/current", headers=self.h, params={"location": "Pune, India"})
            body = r.json()
            if r.status_code != 200 or not body.get("is_live"):
                self.skipTest("Open-Meteo is unreachable from this machine")
            self.assertEqual(len(body["forecast"]), 5)
            self.assertIsNone(body["id"])
            self.assertEqual(db.query(WeatherRecord).count(), before, "the read-only lookup must not store a record")
        finally:
            db.close()
        self.assertEqual(client.get("/api/weather/current", headers=self.h, params={"location": "  "}).status_code, 400)
        self.assertIn(client.get("/api/weather/current", params={"location": "Pune"}).status_code, (401, 403))

    def test_blank_location_is_rejected(self):
        self.assertEqual(self.fetch("   ").status_code, 400)

    def test_service_outage_returns_labelled_fallback_that_is_not_stored(self):
        from app.services import weather_service as ws
        original = (ws.GEOCODING_URL, ws.FORECAST_URL)
        ws.GEOCODING_URL = ws.FORECAST_URL = "http://127.0.0.1:9/unreachable"
        try:
            body = self.fetch("Pune").json()
        finally:
            ws.GEOCODING_URL, ws.FORECAST_URL = original
        self.assertIs(body["is_live"], False)
        self.assertIsNone(body["id"])
        self.assertIn("NOT live", body["source"])
        self.assertEqual(body["forecast"], [])


if __name__ == "__main__":
    unittest.main()
