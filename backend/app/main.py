"""
AI-Powered Intelligent Crop Health & Precision Farming Platform
Backend API - FastAPI Application
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import logging

from app.config import get_settings
from app.database import create_tables, SessionLocal, check_foreign_keys_enabled
from app.routers import auth, users, farms, crops, soil, weather, detection, predictions, recommendations, yield_router, chatbot, admin, samples, analytics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Create database tables and verify database integrity on startup."""
    logger.info("Creating database tables...")
    create_tables()
    logger.info("Database tables created successfully.")

    # Verify SQLite foreign key status
    if settings.DATABASE_URL.startswith("sqlite"):
        db = SessionLocal()
        try:
            fk_active = check_foreign_keys_enabled(db)
            if fk_active:
                logger.info("SQLite foreign key constraints are active and enforced.")
            else:
                logger.warning("SQLite foreign key constraints are NOT enabled.")
        finally:
            db.close()

    if settings.RATE_LIMIT_ENABLED:
        logger.info(
            "Rate limiting is enabled (storage: %s).",
            settings.RATE_LIMIT_STORAGE_URL
        )

    logger.info("AI-Powered Intelligent Crop Health & Precision Farming Platform API is running.")
    yield


# Create FastAPI app
app = FastAPI(
    title="AI-Powered Intelligent Crop Health & Precision Farming Platform",
    description="Backend API for precision agriculture with AI-powered crop health monitoring",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create upload directory
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Serve uploaded files
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(farms.router)
app.include_router(crops.router)
app.include_router(soil.router)
app.include_router(weather.router)
app.include_router(detection.router)
app.include_router(predictions.router)
app.include_router(recommendations.router)
app.include_router(yield_router.router)
app.include_router(chatbot.router)
app.include_router(admin.router)
app.include_router(samples.router)
app.include_router(analytics.router)

# Read-only sample image library for testing (development aid; disable with ENABLE_SAMPLE_LIBRARY=false).
# Kept apart from user uploads, and mounted only when the library actually exists.
if settings.ENABLE_SAMPLE_LIBRARY and os.path.isdir(settings.SAMPLE_LIBRARY_DIR):
    app.mount("/sample-images", StaticFiles(directory=settings.SAMPLE_LIBRARY_DIR), name="sample-images")


@app.get("/")
def root():
    return {
        "application": "AI-Powered Intelligent Crop Health & Precision Farming Platform",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "api_prefix": "/api"
    }


@app.get("/api/health")
def health_check():
    return {"status": "healthy"}
