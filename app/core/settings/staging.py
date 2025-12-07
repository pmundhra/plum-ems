"""Staging environment settings"""

from app.core.settings.base import BaseAppSettings


class StagingSettings(BaseAppSettings):
    """Settings for staging environment"""

    ENVIRONMENT: str = "staging"
    DEBUG: bool = False
    RELOAD: bool = False
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Staging-specific overrides
    CORS_ORIGINS: list[str] = [
        "https://staging.ems.example.com",
        "https://staging-portal.ems.example.com",
    ]
