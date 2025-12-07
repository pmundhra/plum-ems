"""Application settings and configuration"""

import os
from typing import Type

from app.core.settings.base import BaseAppSettings
from app.core.settings.local import LocalSettings
from app.core.settings.dev import DevSettings
from app.core.settings.staging import StagingSettings
from app.core.settings.production import ProductionSettings


def get_settings() -> BaseAppSettings:
    """
    Get settings instance based on ENVIRONMENT variable.

    Returns:
        BaseAppSettings: Settings instance for the current environment
    """
    environment = os.getenv("ENVIRONMENT", "local").lower()

    settings_map: dict[str, Type[BaseAppSettings]] = {
        "local": LocalSettings,
        "dev": DevSettings,
        "staging": StagingSettings,
        "production": ProductionSettings,
    }

    settings_class = settings_map.get(environment, LocalSettings)
    return settings_class()


# Global settings instance
settings = get_settings()

__all__ = ["settings", "get_settings", "BaseAppSettings"]
