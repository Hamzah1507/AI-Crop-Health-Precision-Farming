"""
Seed an ISOLATED demonstration database for CropHealth AI.

    cd backend
    python scripts/seed_demo_data.py --db demo_data/demo.db --uploads demo_data/uploads

Safety rules (enforced here, not just documented):
  * --db is REQUIRED. There is no default and no way to point this script at the real database:
    the real `backend/app.db` is refused outright.
  * Nothing is ever deleted, reset or overwritten. Re-running adds only what is missing (idempotent).
  * It is a command-line tool only; no HTTP endpoint can trigger it.
  * The demo user's password comes from the DEMO_PASSWORD environment variable; if that is unset a random one is
    generated and saved to <db folder>/demo_credentials.txt. It is never printed.
  * The JWT secret and every other .env value are untouched (only DATABASE_URL / UPLOAD_DIR are overridden for this process).

Everything seeded is FICTIONAL DEMONSTRATION DATA (measurements, areas, dates). Leaf scans use images from the
sample library, and their results come from the app's existing SIMULATED detector, so they are flagged is_demo.
Recommendations are produced by the app's own rule-based services. Weather comes from Open-Meteo when reachable.
"""
import argparse
import asyncio
import json
import os
import random
import secrets
import shutil
import sys
from datetime import date, datetime, timedelta, timezone

BACKEND = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
REAL_DB = os.path.normcase(os.path.realpath(os.path.join(BACKEND, "app.db")))


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", required=True, help="path of the isolated demo SQLite file (created if missing)")
    ap.add_argument("--uploads", default=None, help="upload folder for the demo scan images (default: <db folder>/uploads)")
    ap.add_argument("--username", default="demo_farmer")
    ap.add_argument("--no-weather", action="store_true", help="do not call Open-Meteo")
    return ap.parse_args()


def main():
    args = parse_args()
    db_path = os.path.abspath(os.path.join(BACKEND, args.db)) if not os.path.isabs(args.db) else os.path.abspath(args.db)
    if os.path.normcase(os.path.realpath(db_path)) == REAL_DB or os.path.basename(db_path).lower() == "app.db":
        sys.exit("REFUSED: this script never writes to the real database (backend/app.db). Choose an isolated path such as demo_data/demo.db.")
    uploads = os.path.abspath(os.path.join(BACKEND, args.uploads)) if args.uploads and not os.path.isabs(args.uploads) \
        else os.path.abspath(args.uploads) if args.uploads else os.path.join(os.path.dirname(db_path), "uploads")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    os.makedirs(uploads, exist_ok=True)

    # Point the app at the isolated storage BEFORE any app module is imported.
    os.environ["DATABASE_URL"] = "sqlite:///" + db_path.replace("\\", "/")
    os.environ["UPLOAD_DIR"] = uploads
    sys.path.insert(0, BACKEND)

    from app.config import get_settings
    from app.database import Base, SessionLocal, engine
    import app.models  # noqa: F401  (registers every table)
    from app.models.user import User
    from app.models.farmer_profile import FarmerProfile
    from app.models.farm import Farm
    from app.models.crop import Crop
    from app.models.soil_record import SoilRecord
    from app.models.weather_record import WeatherRecord
    from app.models.prediction import Prediction
    from app.models.yield_prediction import YieldPrediction
    from app.services.soil_service import soil_analysis_service
    from app.services.yield_service import yield_prediction_service
    from app.services.weather_service import fetch_weather, LocationNotFoundError
    from app.services.recommendation_service import save_soil_recommendations, save_treatment_recommendation
    from app.ml.model_service import model_service
    from app.utils.auth import get_password_hash

    # Final guard: the engine really points at the isolated file.
    target = os.path.normcase(os.path.realpath(engine.url.database))
    if target == REAL_DB or target != os.path.normcase(os.path.realpath(db_path)):
        sys.exit("REFUSED: the database engine does not point at the requested isolated file.")

    settings = get_settings()
    Base.metadata.create_all(bind=engine)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    ago = lambda days, hour=9: (now - timedelta(days=days)).replace(hour=hour, minute=0, second=0)
    report = {}

    def bump(key, created):
        counts = report.setdefault(key, [0, 0])      # [newly created, already present]
        counts[0 if created else 1] += 1

    db = SessionLocal()
    try:
        # ---- user (never overwritten; password never printed) ----------------------------------------
        user = db.query(User).filter(User.username == args.username).first()
        if user is None:
            password = os.environ.get("DEMO_PASSWORD") or None      # an empty value counts as "not set"
            if password is not None and len(password) < 8:
                sys.exit("REFUSED: DEMO_PASSWORD must be at least 8 characters (or leave it unset to generate one).")
            generated = password is None
            if generated:
                password = secrets.token_urlsafe(12)
            user = User(username=args.username, email=f"{args.username}@example.com", hashed_password=get_password_hash(password), role="farmer")
            db.add(user)
            db.commit()
            db.refresh(user)
            db.add(FarmerProfile(user_id=user.id, full_name="Demo Farmer", phone=None, address="Ahmedabad, Gujarat, India", experience_years=8))
            db.commit()
            bump("user", True)
            if generated:
                cred = os.path.join(os.path.dirname(db_path), "demo_credentials.txt")
                with open(cred, "w", encoding="utf-8") as f:
                    f.write(f"username: {args.username}\npassword: {password}\n(demo database only)\n")
                print(f"Demo login saved to {cred} (not printed).")
            else:
                print("Demo user created with the password from DEMO_PASSWORD.")
        else:
            bump("user", False)

        # ---- farm and crops -------------------------------------------------------------------------
        farm = db.query(Farm).filter(Farm.farmer_id == user.id, Farm.name == "Ahmedabad Demonstration Farm").first()
        bump("farm", farm is None)
        if farm is None:
            farm = Farm(farmer_id=user.id, name="Ahmedabad Demonstration Farm", location=settings.DEFAULT_FARM_LOCATION, area=12.5, area_unit="acres")
            db.add(farm)
            db.commit()
            db.refresh(farm)

        crops = {}
        for name, planted_days_ago in (("Wheat", 110), ("Cotton", 150), ("Tomato", 60), ("Groundnut", 90)):
            crop = db.query(Crop).filter(Crop.farm_id == farm.id, Crop.name == name).first()
            bump("crops", crop is None)
            if crop is None:
                crop = Crop(farm_id=farm.id, name=name, planting_date=date.today() - timedelta(days=planted_days_ago), status="active")
                db.add(crop)
                db.commit()
                db.refresh(crop)
            crops[name] = crop

        # ---- weather (live Open-Meteo only; nothing is stored if it is unreachable) ---------------------
        weather = None
        if not args.no_weather:
            try:
                fetched = asyncio.run(fetch_weather(settings.DEFAULT_FARM_LOCATION))
                weather = fetched if fetched.get("is_live") else None
            except LocationNotFoundError:
                weather = None
            if weather is None:
                print("Weather: Open-Meteo unreachable, so no weather record was stored.")
            elif db.query(WeatherRecord).filter(WeatherRecord.farm_id == farm.id).first() is None:
                db.add(WeatherRecord(farmer_id=user.id, farm_id=farm.id, location=settings.DEFAULT_FARM_LOCATION,
                                     temperature=weather["temperature"], humidity=weather["humidity"], rainfall=weather["rainfall"],
                                     wind_speed=weather["wind_speed"], description=weather["description"], condition=weather["condition"],
                                     recorded_at=now))
                db.commit()
                bump("weather", True)
            else:
                bump("weather", False)

        # ---- soil measurements over ~10 weeks (fictional values) + rule-based recommendations ----------
        soil_plan = [  # days ago, crop, pH, N, P, K, moisture
            (70, "Wheat", 7.2, 38, 27, 33, 52), (56, "Wheat", 6.8, 24, 18, 26, 41), (42, "Cotton", 5.4, 14, 11, 17, 33),
            (28, "Cotton", 6.3, 19, 22, 24, 26), (14, "Tomato", 6.6, 33, 26, 31, 48), (3, "Groundnut", 7.9, 27, 16, 21, 58),
        ]
        for i, (days, crop_name, ph, n, p, k, moist) in enumerate(soil_plan):
            record = db.query(SoilRecord).filter(SoilRecord.farmer_id == user.id, SoilRecord.farm_id == farm.id, SoilRecord.ph == ph,
                                                 SoilRecord.nitrogen == n, SoilRecord.phosphorus == p, SoilRecord.potassium == k,
                                                 SoilRecord.moisture == moist).first()
            bump("soil_records", record is None)
            if record is not None:
                continue
            stamp = ago(days)
            record = SoilRecord(farmer_id=user.id, farm_id=farm.id, crop_id=crops[crop_name].id, ph=ph, nitrogen=n, phosphorus=p,
                                potassium=k, moisture=moist, created_at=stamp, updated_at=stamp)
            db.add(record)
            db.commit()
            db.refresh(record)
            is_latest = i == len(soil_plan) - 1
            wx = weather if is_latest else None
            result = soil_analysis_service.analyze(ph=ph, nitrogen=n, phosphorus=p, potassium=k, moisture=moist, crop_name=crop_name, weather=wx)
            made, _ = save_soil_recommendations(db, user.id, record, result, crop_name, wx, created_at=stamp)
            report.setdefault("soil_recommendations", [0, 0])[0] += made

        # ---- leaf scans from the sample library (results are SIMULATED by the existing detector) --------
        lib = os.path.abspath(os.path.join(BACKEND, settings.SAMPLE_LIBRARY_DIR))
        manifest_path = os.path.join(lib, "manifest.json")
        if not os.path.isfile(manifest_path):
            print("Sample library not found; leaf scans skipped (run scripts/fetch_sample_images.py first).")
        else:
            library = {e["id"]: e for e in json.load(open(manifest_path, encoding="utf-8"))["images"]}
            crop_names = {"tomato": "Tomato", "wheat": "Wheat", "cotton": "Cotton", "maize": "Corn", "potato": "Potato"}
            scan_plan = [(2, "tomato_late-blight_001"), (5, "tomato_healthy_001"), (9, "wheat_leaf-rust_001"), (15, "pest_whitefly-eggplant_001"),
                         (22, "potato_early-blight_001"), (30, "cotton_boll_001"), (41, "maize_common-rust_001"), (55, "pest_thrips-basil_001")]
            random.seed(20261027)  # the simulated detector is random; fixed seed -> the demo DB is reproducible
            for days, image_id in scan_plan:
                entry = library.get(image_id)
                if entry is None:
                    print(f"Sample image {image_id} not in the manifest; skipped.")
                    continue
                ext = os.path.splitext(entry["filename"])[1]
                stored = os.path.join(uploads, f"demo_{image_id}{ext}")
                existing = db.query(Prediction).filter(Prediction.farmer_id == user.id, Prediction.image_path == stored).first()
                bump("leaf_scans", existing is None)
                if existing is not None:
                    continue
                shutil.copy2(os.path.join(lib, entry["path"]), stored)
                crop_label = crop_names.get(entry["crop"])
                crop_row = crops.get(crop_label) if crop_label else None
                result = model_service.predict(stored, crop_label)
                stamp = ago(days, 14)
                prediction = Prediction(farmer_id=user.id, crop_id=crop_row.id if crop_row else None, image_path=stored,
                                        original_filename=entry["filename"], crop_name=crop_label, disease_name=result.get("disease_name"),
                                        pest_name=result.get("pest_name"), prediction_type=result.get("prediction_type", "disease"),
                                        confidence=result.get("confidence"), bbox_data=result.get("bbox_data"), status="completed",
                                        is_demo=result.get("is_demo", "true"), created_at=stamp)
                db.add(prediction)
                db.commit()
                db.refresh(prediction)
                save_treatment_recommendation(db, user.id, prediction, result, created_at=stamp)

        # ---- yield estimates (rule-based, deterministic) -----------------------------------------------
        yield_plan = [  # days ago, crop, area, season, pH, N, P, K, moisture, temp, humidity, rain
            (60, "Wheat", 4.0, "Rabi (Winter)", 7.0, 35, 25, 30, 48, 22, 55, 3), (45, "Cotton", 5.0, "Kharif (Monsoon)", 6.2, 22, 20, 24, 36, 31, 62, 9),
            (30, "Tomato", 1.5, "Zaid (Summer)", 6.5, 32, 24, 28, 52, 29, 60, 6), (21, "Groundnut", 2.0, "Kharif (Monsoon)", 6.0, 18, 17, 22, 30, 33, 58, 12),
            (14, "Wheat", 3.0, "Rabi (Winter)", 5.4, 14, 11, 17, 33, 20, 50, 2), (7, "Corn", 2.5, "Kharif (Monsoon)", 6.8, 30, 22, 27, 45, 28, 65, 8),
            (2, "Cotton", 5.0, "Kharif (Monsoon)", 7.4, 36, 28, 31, 50, 30, 60, 7),
        ]
        for days, crop, area, season, ph, n, p, k, moist, temp, hum, rain in yield_plan:
            existing = db.query(YieldPrediction).filter(YieldPrediction.farmer_id == user.id, YieldPrediction.crop_name == crop, YieldPrediction.area == area,
                                                        YieldPrediction.season == season, YieldPrediction.soil_ph == ph, YieldPrediction.soil_nitrogen == n,
                                                        YieldPrediction.temperature == temp, YieldPrediction.rainfall == rain).first()
            bump("yield_estimates", existing is None)
            if existing is not None:
                continue
            est = yield_prediction_service.predict(crop_name=crop, area=area, soil_ph=ph, soil_nitrogen=n, soil_phosphorus=p, soil_potassium=k,
                                                   soil_moisture=moist, temperature=temp, humidity=hum, rainfall=rain, season=season)
            db.add(YieldPrediction(farmer_id=user.id, farm_id=farm.id, crop_name=crop, predicted_yield=est["predicted_yield"], yield_unit=est["yield_unit"],
                                   confidence=est["confidence"], area=area, soil_ph=ph, soil_nitrogen=n, soil_phosphorus=p, soil_potassium=k,
                                   soil_moisture=moist, temperature=temp, humidity=hum, rainfall=rain, season=season,
                                   is_demo=est.get("is_demo", "true"), created_at=ago(days, 11)))
            db.commit()
    finally:
        db.close()

    print("\nSeeded the isolated demo database (new / already present):")
    for key, (new, old) in report.items():
        print(f"  {key:<22} {new:>3} new  {old:>3} already there")
    print(f"\nDatabase : {db_path}\nUploads  : {uploads}\nUser     : {args.username}  (password: see above; never printed)")


if __name__ == "__main__":
    main()
