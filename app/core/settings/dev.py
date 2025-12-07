"""Development environment settings"""

from app.core.settings.base import BaseAppSettings


class DevSettings(BaseAppSettings):
    """Settings for development environment"""

    ENVIRONMENT: str = "dev"
    DEBUG: bool = True
    RELOAD: bool = False
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
