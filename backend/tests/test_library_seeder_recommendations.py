"""
Sample library, demo seeder and recommendation tests.

Run from the backend folder:  python -m unittest tests.test_library_seeder_recommendations -v
Uses temporary storage only (the API tests reuse test_api_regression's temp DB/uploads; the seeder tests use their own temp folder).
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import warnings

# Suppress harmless testclient deprecation warning and resource warnings during test runs
warnings.filterwarnings("ignore", message=r".*httpx.*", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=ResourceWarning)

import cv2
import numpy as np

from tests import test_api_regression as base      # sets up the temporary DB/uploads and the shared TestClient
from app.config import get_settings
from app.services.recommendation_service import build_soil_recommendations, parse_description, compose
from app.services.soil_service import soil_analysis_service

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIBRARY = os.path.join(BACKEND, "uploads", "sample_images")


def setUpModule():
    base.acquire()


def tearDownModule():
    base.release()


def analyse(**values):
    return soil_analysis_service.analyze(**values)


SCENARIOS = {
    "suitable": dict(ph=6.5, nitrogen=35, phosphorus=25, potassium=30, moisture=50),
    "acidic": dict(ph=5.2, nitrogen=30, phosphorus=22, potassium=28, moisture=50),
    "deficient": dict(ph=6.4, nitrogen=10, phosphorus=8, potassium=12, moisture=45),
    "dry": dict(ph=6.6, nitrogen=32, phosphorus=24, potassium=29, moisture=14),
}


class RecommendationRules(unittest.TestCase):
    def types(self, recs):
        return {r["type"] for r in recs}

    def test_every_recommendation_explains_itself(self):
        for name, values in SCENARIOS.items():
            recs = build_soil_recommendations(analyse(**values), "Wheat")
            self.assertTrue(recs, name)
            for r in recs:
                with self.subTest(scenario=name, title=r["title"]):
                    self.assertTrue(r["reason"].strip(), "needs a reason")
                    self.assertTrue(r["action"].strip(), "needs a suggested action")
                    self.assertIn(r["priority"], ("low", "medium", "high", "critical"))

    def test_suitable_soil_is_explained_as_within_reference_ranges(self):
        recs = build_soil_recommendations(analyse(**SCENARIOS["suitable"]))
        within = [r for r in recs if r["title"].startswith("Measurements are within")]
        self.assertEqual(len(within), 1)
        for text in ("pH", "nitrogen", "phosphorus", "potassium", "soil moisture", "reference"):
            self.assertIn(text, within[0]["reason"])

    def test_deficient_soil_gets_fertilizer_guidance_for_each_low_nutrient(self):
        titles = " | ".join(r["title"] for r in build_soil_recommendations(analyse(**SCENARIOS["deficient"])) if r["type"] == "fertilizer")
        self.assertIn("Urea", titles)
        self.assertIn("DAP", titles)
        self.assertIn("Muriate of Potash", titles)

    def test_acidic_and_dry_soil(self):
        acidic = build_soil_recommendations(analyse(**SCENARIOS["acidic"]))
        self.assertTrue(any("Lime" in r["title"] for r in acidic), "very acidic soil gets the liming guidance")
        dry = build_soil_recommendations(analyse(**SCENARIOS["dry"]))
        irrigation = [r for r in dry if r["type"] == "irrigation"]
        self.assertEqual(len(irrigation), 1)
        self.assertIn(irrigation[0]["priority"], ("high", "critical"))

    def test_moderately_acidic_ph_gets_an_explanation_without_duplicating_the_lime_item(self):
        mild = build_soil_recommendations(analyse(ph=5.8, nitrogen=30, phosphorus=22, potassium=28, moisture=50))
        self.assertTrue(any(r["type"] == "soil" and "pH" in r["title"] for r in mild))
        severe = build_soil_recommendations(analyse(**SCENARIOS["acidic"]))
        self.assertFalse(any(r["type"] == "soil" and r["title"].startswith("Soil pH") for r in severe), "the liming item already covers it")

    def test_no_invented_precision_or_exact_chemical_dosages(self):
        banned = re.compile(r"\b\d+\s*[-–]?\s*\d*\s*(mm of water|mm\b|litres?|liters?|kg per|kg/acre|g/m|ml/)|guarantee|increase yield by", re.I)
        for name, values in SCENARIOS.items():
            for r in build_soil_recommendations(analyse(**values), "Rice"):
                with self.subTest(scenario=name, title=r["title"]):
                    self.assertIsNone(banned.search(r["reason"] + " " + r["action"]), r)

    def test_crop_context_is_added_for_nitrogen_guidance(self):
        recs = build_soil_recommendations(analyse(**SCENARIOS["deficient"]), "Rice")
        urea = next(r for r in recs if "Urea" in r["title"])
        self.assertIn("Rice", urea["reason"])
        self.assertIn("high nitrogen requirement", urea["reason"])

    def test_weather_advisories_only_come_from_live_forecast_data(self):
        live = {"is_live": True, "resolved_location": "Ahmedabad, Gujarat, India",
                "forecast_alerts": ["Heavy rain expected on 2026-10-30 (24 mm): check drainage and delay spraying."]}
        recs = build_soil_recommendations(analyse(**SCENARIOS["suitable"]), None, live)
        weather = [r for r in recs if r["type"] == "weather"]
        self.assertEqual(len(weather), 1)
        self.assertIn("Open-Meteo", weather[0]["reason"])
        self.assertIn("check drainage", weather[0]["action"])
        placeholder = dict(live, is_live=False)
        self.assertFalse([r for r in build_soil_recommendations(analyse(**SCENARIOS["suitable"]), None, placeholder) if r["type"] == "weather"])

    def test_description_round_trip_and_legacy_text(self):
        text = compose("Because X", "Do Y", "Rice")
        self.assertEqual(parse_description(text), ("Because X", "Do Y", "Rice"))
        self.assertEqual(parse_description("Plain legacy text"), ("Plain legacy text", None, None))


class RecommendationApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = base.register("rec_user")
        cls.client = base.client

    def analyze(self, **values):
        r = self.client.post("/api/soil/analyze", headers=self.h, json=values)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def recs(self, **params):
        r = self.client.get("/api/recommendations/", headers=self.h, params=params)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_repeated_identical_analysis_does_not_duplicate_recommendations(self):
        h = base.register("rec_repeat")
        body = {**SCENARIOS["deficient"], "crop_name": "Wheat"}
        first = self.client.post("/api/soil/analyze", headers=h, json=body).json()
        count = len(self.client.get("/api/recommendations/", headers=h).json())
        again = self.client.post("/api/soil/analyze", headers=h, json=body).json()
        self.assertGreater(first["recommendations_created"], 0)
        self.assertFalse(first["repeat_analysis"])
        self.assertTrue(again["repeat_analysis"])
        self.assertEqual(again["recommendations_created"], 0)
        self.assertEqual(len(self.client.get("/api/recommendations/", headers=h).json()), count)
        changed = self.client.post("/api/soil/analyze", headers=h, json={**body, "nitrogen": 12}).json()
        self.assertFalse(changed["repeat_analysis"])
        self.assertGreater(changed["recommendations_created"], 0, "different measurements are a new analysis")

    def test_response_carries_reason_action_crop_priority_source_and_date(self):
        h = base.register("rec_fields")
        self.client.post("/api/soil/analyze", headers=h, json={**SCENARIOS["deficient"], "crop_name": "Rice"})
        rows = self.client.get("/api/recommendations/", headers=h).json()
        self.assertTrue(rows)
        for r in rows:
            self.assertTrue(r["reason"] and r["action"], r)
            self.assertEqual(r["crop_name"], "Rice")
            self.assertEqual(r["source_type"], "soil_record")
            self.assertIsNotNone(r["source_id"])
            self.assertTrue(r["created_at"])
            self.assertFalse(r["is_simulated"])

    def test_categories_and_filtering(self):
        h = base.register("rec_filter")
        self.client.post("/api/soil/analyze", headers=h, json=SCENARIOS["dry"])
        self.client.post("/api/soil/analyze", headers=h, json=SCENARIOS["deficient"])
        kinds = {r["type"] for r in self.client.get("/api/recommendations/", headers=h).json()}
        self.assertTrue({"fertilizer", "irrigation"} <= kinds, kinds)
        for kind in ("fertilizer", "irrigation"):
            filtered = self.client.get("/api/recommendations/", headers=h, params={"type": kind}).json()
            self.assertTrue(filtered and all(r["type"] == kind for r in filtered))
        self.assertEqual(self.client.get("/api/recommendations/", headers=h, params={"type": "treatment"}).json(), [])

    def test_treatments_from_the_simulated_detector_are_flagged_and_link_to_the_scan(self):
        h = base.register("rec_treat")
        with open(os.path.join(LIBRARY, "healthy", "tomato_healthy_001.jpg"), "rb") as f:
            png = f.read()
        scan = self.client.post("/api/detection/predict", headers=h, files={"file": ("leaf.jpg", png, "image/jpeg")}, data={"crop_name": "Tomato"}).json()
        treatments = self.client.get("/api/recommendations/", headers=h, params={"type": "treatment"}).json()
        self.assertEqual(len(treatments), 1)
        t = treatments[0]
        # With active PyTorch ResNet-18 model, Tomato receives genuine AI care guidance
        self.assertFalse(t["is_simulated"])
        self.assertIn("genuine", t["reason"].lower())
        self.assertEqual((t["source_type"], t["source_id"], t["crop_name"]), ("prediction", scan["id"], "Tomato"))

        # Unsupported crops (e.g. Cotton) exercise the demo fallback with is_simulated=True
        with open(os.path.join(LIBRARY, "cotton", "cotton_plant_001.jpg"), "rb") as f:
            cotton_png = f.read()
        scan_demo = self.client.post("/api/detection/predict", headers=h, files={"file": ("cotton.jpg", cotton_png, "image/jpeg")}, data={"crop_name": "Cotton"}).json()
        self.assertEqual(scan_demo["is_demo"], "true")
        demo_treatments = [r for r in self.client.get("/api/recommendations/", headers=h, params={"type": "treatment"}).json() if r["source_id"] == scan_demo["id"]]
        if demo_treatments:
            self.assertTrue(demo_treatments[0]["is_simulated"])
            self.assertIn("simulated", demo_treatments[0]["title"].lower())

    def test_recommendations_are_private_to_their_owner(self):
        other = base.register("rec_other")
        self.assertEqual(self.client.get("/api/recommendations/", headers=other).json(), [])

    def test_a_saved_soil_record_can_be_reopened_but_only_by_its_owner(self):
        h = base.register("rec_reopen")
        self.client.post("/api/soil/analyze", headers=h, json=SCENARIOS["acidic"])
        self.client.post("/api/soil/analyze", headers=h, json=SCENARIOS["suitable"])
        rec = next(r for r in self.client.get("/api/recommendations/", headers=h).json() if r["source_type"] == "soil_record" and "Lime" in r["title"])
        opened = self.client.get("/api/soil/latest", headers=h, params={"record_id": rec["source_id"]}).json()
        self.assertEqual(opened["record"]["ph"], 5.2)
        self.assertIn(opened["analysis"]["soil_health_status"], ("Moderate", "Poor", "Critical", "Good"))
        self.assertEqual(self.client.get("/api/soil/latest", headers=h).json()["record"]["ph"], 6.5, "without record_id it is still the newest")
        stranger = base.register("rec_stranger")
        self.assertEqual(self.client.get("/api/soil/latest", headers=stranger, params={"record_id": rec["source_id"]}).status_code, 404)


class SampleLibrary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = base.register("lib_user")
        cls.client = base.client
        with open(os.path.join(LIBRARY, "manifest.json"), encoding="utf-8") as f:
            cls.manifest = json.load(f)["images"]

    def test_library_files_are_valid_images_that_match_the_manifest(self):
        self.assertGreaterEqual(len(self.manifest), 50)
        for e in self.manifest:
            with open(os.path.join(LIBRARY, e["path"]), "rb") as f:
                data = f.read()
            with self.subTest(path=e["path"]):
                self.assertEqual(hashlib.sha256(data).hexdigest(), e["sha256"])
                self.assertIsNotNone(cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR))
                self.assertTrue(os.path.exists(os.path.join(LIBRARY, e["crop_folder_path"])))
                for field in ("license", "license_url", "source_url", "author", "crop", "condition", "label"):
                    self.assertTrue(e.get(field), field)
        self.assertEqual(len({e["sha256"] for e in self.manifest}), len(self.manifest), "no duplicate images")

    def test_library_covers_the_required_folders_crops_and_conditions(self):
        for folder in ("healthy", "disease", "pests", "rice", "wheat", "tomato", "potato", "cotton", "maize", "other_crops"):
            self.assertTrue(os.listdir(os.path.join(LIBRARY, folder)), folder)
        self.assertTrue({"healthy", "disease", "pest"} <= {e["condition"] for e in self.manifest})
        self.assertTrue({"tomato", "potato", "maize", "rice", "wheat", "cotton"} <= {e["crop"] for e in self.manifest})

    def test_readme_exists_with_attribution_and_the_honesty_notes(self):
        with open(os.path.join(LIBRARY, "README.md"), encoding="utf-8") as f:
            text = f.read()
        for needle in ("CC BY-SA 3.0", "PlantVillage", "Wikimedia Commons", "simulated", "Salathé", "Not obtained"):
            self.assertIn(needle, text)

    def test_listing_requires_login_and_returns_every_image_with_attribution(self):
        self.assertIn(self.client.get("/api/samples/").status_code, (401, 403))
        body = self.client.get("/api/samples/", headers=self.h).json()
        self.assertTrue(body["enabled"])
        self.assertEqual(body["count"], len(self.manifest))
        for item in body["items"]:
            self.assertTrue(item["license"] and item["author"] and item["label"] and item["url"].startswith("/sample-images/"))

    def test_filtering_by_crop_and_condition(self):
        body = self.client.get("/api/samples/", headers=self.h, params={"crop": "tomato", "condition": "disease"}).json()
        self.assertTrue(body["items"])
        self.assertTrue(all(i["crop"] == "tomato" and i["condition"] == "disease" for i in body["items"]))

    def test_images_are_served_and_nothing_outside_the_library_is(self):
        item = self.client.get("/api/samples/", headers=self.h).json()["items"][0]
        r = self.client.get(item["url"])
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.headers["content-type"].startswith("image/"))
        for attack in ("/sample-images/../app.db", "/sample-images/..%2Fapp.db", "/sample-images/%2e%2e/%2e%2e/.env", "/sample-images/manifest.json/../../app.db"):
            self.assertIn(self.client.get(attack).status_code, (400, 404), attack)

    def test_library_can_be_switched_off(self):
        settings = get_settings()
        settings.ENABLE_SAMPLE_LIBRARY = False
        try:
            body = self.client.get("/api/samples/", headers=self.h).json()
            self.assertEqual((body["enabled"], body["count"], body["items"]), (False, 0, []))
        finally:
            settings.ENABLE_SAMPLE_LIBRARY = True

    def test_a_sample_goes_through_the_normal_upload_pipeline_and_stays_simulated(self):
        # Supported crop sample (Tomato) uses genuine AI inference when model is active
        entry = next(e for e in self.manifest if e["condition"] == "disease" and e["crop"] == "tomato")
        with open(os.path.join(LIBRARY, entry["path"]), "rb") as f:
            data = f.read()
        r = self.client.post("/api/detection/predict", headers=self.h, files={"file": (entry["filename"], data, "image/jpeg")}, data={"crop_name": "Tomato"})
        self.assertEqual(r.status_code, 200, r.text)
        scan = r.json()
        self.assertEqual(scan["is_demo"], "false")
        self.assertIsNotNone(scan["confidence"])
        self.assertGreater(scan["confidence"], 0)

        # Unsupported crop (Cotton) exercises demonstration fallback
        cotton_entry = next((e for e in self.manifest if e.get("crop") == "cotton"), None)
        if cotton_entry:
            with open(os.path.join(LIBRARY, cotton_entry["path"]), "rb") as f:
                cdata = f.read()
            r_demo = self.client.post("/api/detection/predict", headers=self.h, files={"file": (cotton_entry["filename"], cdata, "image/jpeg")}, data={"crop_name": "Cotton"})
            self.assertEqual(r_demo.status_code, 200)
            scan_demo = r_demo.json()
            self.assertEqual((scan_demo["is_demo"], scan_demo["confidence"], scan_demo["bbox_data"]), ("true", None, None))

        bad = self.client.post("/api/detection/predict", headers=self.h, files={"file": ("x.jpg", b"not an image", "image/jpeg")})
        self.assertEqual(bad.status_code, 400, "invalid uploads are still rejected")


class DemoSeeder(unittest.TestCase):
    def run_seeder(self, *args, env_extra=None):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", **(env_extra or {}))
        return subprocess.run([sys.executable, "-W", "ignore", os.path.join("scripts", "seed_demo_data.py"), *args],
                              cwd=BACKEND, capture_output=True, text=True, env=env, timeout=240)

    def counts(self, db):
        import sqlite3
        c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            return {t: c.execute(f"select count(*) from {t}").fetchone()[0] for t in
                    ("users", "farms", "crops", "soil_records", "predictions", "recommendations", "yield_predictions")}
        finally:
            c.close()

    def test_refuses_the_real_database_and_a_missing_target(self):
        real = os.path.join(BACKEND, "app.db")
        before = os.path.getmtime(real) if os.path.exists(real) else None
        for args in (["--db", "app.db"], ["--db", real], ["--db", os.path.join("demo_data", "..", "app.db")], []):
            r = self.run_seeder(*args)
            with self.subTest(args=args):
                self.assertNotEqual(r.returncode, 0)
        self.assertEqual(os.path.getmtime(real) if os.path.exists(real) else None, before, "the real database was not touched")

    def test_seeding_is_complete_idempotent_and_never_prints_the_password(self):
        tmp = tempfile.mkdtemp(prefix="cp_seed_")
        try:
            db = os.path.join(tmp, "demo.db")
            first = self.run_seeder("--db", db, "--no-weather", env_extra={"DEMO_PASSWORD": ""})
            self.assertEqual(first.returncode, 0, first.stderr[-600:])
            with open(os.path.join(tmp, "demo_credentials.txt"), encoding="utf-8") as f:
                cred = f.read()
            password = re.search(r"password: (\S+)", cred).group(1)
            self.assertNotIn(password, first.stdout + first.stderr, "the password must never be printed")
            c1 = self.counts(db)
            self.assertEqual((c1["users"], c1["farms"], c1["crops"], c1["soil_records"], c1["predictions"], c1["yield_predictions"]), (1, 1, 4, 6, 8, 7))
            self.assertGreater(c1["recommendations"], 10)

            second = self.run_seeder("--db", db, "--no-weather")
            self.assertEqual(second.returncode, 0, second.stderr[-600:])
            self.assertEqual(self.counts(db), c1, "re-running must not create anything")
            self.assertEqual(len(os.listdir(os.path.join(tmp, "uploads"))), 8, "scan images are copied once")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_demo_user_can_log_in_and_sees_only_its_own_seeded_history(self):
        tmp = tempfile.mkdtemp(prefix="cp_seed_login_")
        try:
            db = os.path.join(tmp, "demo.db")
            self.assertEqual(self.run_seeder("--db", db, "--no-weather", env_extra={"DEMO_PASSWORD": "demo-pass-123"}).returncode, 0)
            # Log in against the seeded database in a separate process (the test DB of this process is a different file)
            code = ("import os,sys; sys.path.insert(0,'.'); from fastapi.testclient import TestClient; import app.main as m\n"
                    "with TestClient(m.app) as c:\n"
                    "  t=c.post('/api/auth/login',json={'username':'demo_farmer','password':'demo-pass-123'}).json()['access_token']\n"
                    "  h={'Authorization':'Bearer '+t}\n"
                    "  print(len(c.get('/api/farms/',headers=h).json()), c.get('/api/predictions/',headers=h).json()['total'], len(c.get('/api/yield/history',headers=h).json()), len(c.get('/api/recommendations/',headers=h).json()))\n"
                    "  print(c.post('/api/auth/login',json={'username':'demo_farmer','password':'wrong'}).status_code)")
            env = dict(os.environ, DATABASE_URL="sqlite:///" + db.replace("\\", "/"), UPLOAD_DIR=os.path.join(tmp, "uploads"), PYTHONDONTWRITEBYTECODE="1")
            out = subprocess.run([sys.executable, "-W", "ignore", "-c", code], cwd=BACKEND, capture_output=True, text=True, env=env, timeout=120)
            lines = [l for l in out.stdout.splitlines() if l and not l.startswith("INFO")]
            self.assertEqual(lines[-2].split()[:3], ["1", "8", "7"], out.stdout + out.stderr[-500:])
            self.assertEqual(lines[-1], "401")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
