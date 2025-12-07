"""Local development settings"""

from app.core.settings.base import BaseAppSettings


class LocalSettings(BaseAppSettings):
    """Settings for local development environment"""

    ENVIRONMENT: str = "local"
    DEBUG: bool = True
    RELOAD: bool = True
    LOG_LEVEL: str = "DEBUG"
    LOG_FORMAT: str = "console"  # Human-readable for local development

    # Local defaults (can be overridden by .env)
    SECRET_KEY: str = "local-secret-key-change-in-production"
    HMAC_SECRET_KEY: str = "local-hmac-secret-key-change-in-production"
    POSTGRES_PASSWORD: str = "postgres"
