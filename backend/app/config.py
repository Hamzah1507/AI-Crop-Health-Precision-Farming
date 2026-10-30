from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


def secret_key_is_placeholder(secret: str) -> bool:
    """True for the built-in default or any value that still says 'change-in-production' or is insecurely short."""
    if not secret:
        return True
    s = secret.strip().lower()
    return (
        len(secret) < 32
        or "change-in-production" in s
        or s.startswith("dev-secret")
        or s in ("secret", "changeme", "password", "admin", "default", "12345678")
    )


class Settings(BaseSettings):
    # Application Environment: 'development', 'testing', or 'production'
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str = "sqlite:///./app.db"

    # JWT Authentication
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_STORAGE_URL: str = "memory://"
    RATE_LIMIT_LOGIN_LIMIT: int = 5
    RATE_LIMIT_LOGIN_WINDOW: int = 60
    RATE_LIMIT_REGISTER_LIMIT: int = 5
    RATE_LIMIT_REGISTER_WINDOW: int = 60
    RATE_LIMIT_DETECTION_LIMIT: int = 10
    RATE_LIMIT_DETECTION_WINDOW: int = 60

    # Weather API
    WEATHER_API_KEY: str = ""

    # File Upload
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE_MB: int = 10

    # Default farm created for a user who has none (see POST /api/farms/default).
    DEFAULT_FARM_NAME: str = "My Ahmedabad Farm"
    DEFAULT_FARM_LOCATION: str = "Ahmedabad, Gujarat, India"

    # Sample image library (development/demo aid). Set ENABLE_SAMPLE_LIBRARY=false in production.
    SAMPLE_LIBRARY_DIR: str = "uploads/sample_images"
    ENABLE_SAMPLE_LIBRARY: bool = True

    # CORS
    FRONTEND_URL: str = "http://localhost:5173"

    # ML Model Paths
    PYTORCH_MODEL_PATH: str = "ml/models/resnet18_plantvillage_best.pt"
    CLASS_MAPPING_PATH: str = "ml/models/class_mapping.json"
    YOLO_MODEL_PATH: str = "ml/models/yolov8_crop_disease.pt"
    TENSORFLOW_MODEL_PATH: str = "ml/models/crop_disease_model.h5"

    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    @model_validator(mode="after")
    def validate_security(self) -> "Settings":
        env = (self.ENVIRONMENT or "development").strip().lower()
        is_placeholder = secret_key_is_placeholder(self.SECRET_KEY)

        if env in ("production", "prod"):
            if not self.SECRET_KEY or is_placeholder:
                raise ValueError(
                    "In production (ENVIRONMENT='production'), SECRET_KEY must be a cryptographically "
                    "secure random string of at least 32 characters and cannot be a default or placeholder value. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
                )
        else:
            if is_placeholder:
                logger.warning(
                    "SECURITY WARNING: Using placeholder or development fallback SECRET_KEY (%s characters). "
                    "In production, a secure SECRET_KEY of at least 32 characters must be configured in .env.",
                    len(self.SECRET_KEY) if self.SECRET_KEY else 0
                )
        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()
