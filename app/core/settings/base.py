"""Base settings configuration"""

from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseAppSettings(BaseSettings):
    """Base application settings with common configuration"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Endorsement Management System"
    APP_VERSION: str = "0.1.0"
    API_VERSION: str = "v1"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    ENVIRONMENT: Literal["local", "dev", "staging", "production"] = "local"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = False

    # Security
    SECRET_KEY: str = Field(..., description="Secret key for JWT tokens")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    HMAC_SECRET_KEY: str = Field(..., description="Secret key for HMAC signatures")

    # PostgreSQL
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "plum"
    POSTGRES_PASSWORD: str = Field(..., description="PostgreSQL password")
    POSTGRES_DB: str = "plum-ems"
    POSTGRES_POOL_SIZE: int = 10
    POSTGRES_MAX_OVERFLOW: int = 20

    @property
    def postgres_url(self) -> str:
        """Construct PostgreSQL connection URL"""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def postgres_sync_url(self) -> str:
        """Construct synchronous PostgreSQL connection URL for Alembic"""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # MongoDB
    MONGO_HOST: str = "localhost"
    MONGO_PORT: int = 27017
    MONGO_USER: str = ""
    MONGO_PASSWORD: str = ""
    MONGO_DB: str = "ems_audit"
    MONGO_AUTH_SOURCE: str = "admin"

    @property
    def mongo_url(self) -> str:
        """Construct MongoDB connection URL"""
        if self.MONGO_USER and self.MONGO_PASSWORD:
            return (
                f"mongodb://{self.MONGO_USER}:{self.MONGO_PASSWORD}"
                f"@{self.MONGO_HOST}:{self.MONGO_PORT}/{self.MONGO_DB}"
                f"?authSource={self.MONGO_AUTH_SOURCE}"
            )
        return f"mongodb://{self.MONGO_HOST}:{self.MONGO_PORT}/{self.MONGO_DB}"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_DECODE_RESPONSES: bool = True

    @property
    def redis_url(self) -> str:
        """Construct Redis connection URL"""
        if self.REDIS_PASSWORD:
            return (
                f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
            )
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_CLIENT_ID: str = "ems-api"
    KAFKA_GROUP_ID: str = "ems-consumers"
    KAFKA_AUTO_OFFSET_RESET: str = "earliest"
    KAFKA_ENABLE_AUTO_COMMIT: bool = False

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: Literal["json", "console"] = "json"

    # Prometheus
    METRICS_ENABLED: bool = True
    METRICS_PATH: str = "/metrics"

    # CORS
    CORS_ORIGINS: list[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    # Endorsement Processing
    ENDORSEMENT_BATCH_WINDOW_MINUTES: int = 5
    ENDORSEMENT_MAX_RETRIES: int = 5
    ENDORSEMENT_RETRY_BACKOFF_BASE: int = 2  # Exponential backoff base

    # Ledger
    LEDGER_LOW_BALANCE_THRESHOLD: float = 1000.0
    LEDGER_LOCK_TIMEOUT_SECONDS: int = 300  # 5 minutes

    # Insurer Gateway
    INSURER_REQUEST_TIMEOUT_SECONDS: int = 30
    INSURER_MAX_RETRIES: int = 3

    # Analytics
    ANALYTICS_ANOMALY_THRESHOLD_MULTIPLIER: float = 3.0  # 3x standard deviation
    ANALYTICS_CIRCUIT_BREAKER_ENABLED: bool = True
