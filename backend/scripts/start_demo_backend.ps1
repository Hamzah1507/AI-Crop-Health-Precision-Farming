<#
  Start the CropHealth AI backend against the ISOLATED demo database (backend\demo_data\demo.db).

      cd backend
      powershell -ExecutionPolicy Bypass -File scripts\start_demo_backend.ps1            # serve the demo data
      powershell -ExecutionPolicy Bypass -File scripts\start_demo_backend.ps1 -Seed      # (re)seed first, then serve

  Only DATABASE_URL and UPLOAD_DIR are overridden, and only for this process. The real database (app.db), its uploads,
  .env and the JWT secret are not touched. To go back to the real data, stop this server (Ctrl+C) and start the
  normal one:   python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
#>
param(
  [switch]$Seed,
  [int]$Port = 8000
)

$backend = Split-Path -Parent $PSScriptRoot
$demo    = Join-Path $backend 'demo_data'
$db      = Join-Path $demo 'demo.db'
$uploads = Join-Path $demo 'uploads'

Set-Location $backend

if ($Seed -or -not (Test-Path $db)) {
  python scripts\seed_demo_data.py --db $db --uploads $uploads
  if ($LASTEXITCODE -ne 0) { Write-Error 'Seeding failed; not starting the server.'; exit 1 }
}

$env:DATABASE_URL = 'sqlite:///' + ($db -replace '\\', '/')
$env:UPLOAD_DIR   = $uploads
Write-Host "Demo mode: database $db"
Write-Host 'The demo login is in demo_data\demo_credentials.txt (never printed here).'
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port $Port
