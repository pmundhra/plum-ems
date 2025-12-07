"""Production environment settings"""

from pydantic import Field

from app.core.settings.base import BaseAppSettings


class ProductionSettings(BaseAppSettings):
    """Settings for production environment"""

    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    RELOAD: bool = False
    LOG_LEVEL: str = "WARNING"
    LOG_FORMAT: str = "json"

    # Production-specific overrides
    CORS_ORIGINS: list[str] = [
        "https://ems.example.com",
        "https://portal.ems.example.com",
    ]

    # Production requires secure settings (must be set via environment variables)
    SECRET_KEY: str = Field(..., description="MUST be set in production")
    HMAC_SECRET_KEY: str = Field(..., description="MUST be set in production")
    POSTGRES_PASSWORD: str = Field(..., description="MUST be set in production")
