# Demo environment and sample image library

Everything here is **development / demonstration only**. The demo data is fictional, lives in its own SQLite file,
and never touches the real database (`backend/app.db`), its uploads, `.env` or the JWT secret.

## Start the demo environment

```powershell
cd backend
# 1. Seed (first time) and serve the isolated demo database on port 8000
powershell -ExecutionPolicy Bypass -File scripts\start_demo_backend.ps1 -Seed

# 2. In another terminal, the normal frontend
cd frontend
npm run dev
```

Sign in as `demo_farmer`. The password is generated on first seeding and saved to
`backend/demo_data/demo_credentials.txt` (it is never printed). To choose your own, set `DEMO_PASSWORD`
(8+ characters) before the first seed.

## Go back to the real data

Stop the demo server (Ctrl+C) and start the normal one:

```powershell
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Only `DATABASE_URL` and `UPLOAD_DIR` are overridden, and only inside the demo process, so nothing else changes.

## Seeder

```powershell
cd backend
python scripts\seed_demo_data.py --db demo_data\demo.db --uploads demo_data\uploads
```

* `--db` is required; `backend/app.db` (or any file called `app.db`) is refused.
* Idempotent: running it again adds only what is missing and never deletes or overwrites anything.
* Seeds an Ahmedabad farm, four crops, soil records over time, one Open-Meteo weather record (skipped with
  `--no-weather` or when offline), eight leaf scans that use real sample-library photos, rule-based
  recommendations, and yield estimates.
* Leaf-scan results come from the app's **simulated** detector and are flagged as such. The sample photos'
  dataset labels are the sources' labels, not predictions.
* There is no HTTP endpoint that seeds data.

## Sample image library

`backend/uploads/sample_images/` holds 75 real, openly licensed photographs with `manifest.json`
(path, crop, source, licence, source label) and `README.md` (attribution). It is read-only reference material,
kept separate from user uploads.

* Rebuild or extend it: `python scripts\fetch_sample_images.py` (`--dry-run` lists what it would fetch).
* In the app, **Disease & pest detection -> Choose from sample library** opens a picker with crop and condition
  filters. A chosen image goes through the same upload API and byte-level validation as a user's own photo.
* Turn the selector off with `ENABLE_SAMPLE_LIBRARY=false` (for example in production).

## Tests on isolated storage

`python -m unittest discover -s tests -t .` runs against a temporary database and upload folder and removes them afterwards.
