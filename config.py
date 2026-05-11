"""Configuration management with validation and environment variable support."""

import os
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class SecurityConfig(BaseModel):
    """Security configuration."""

    secret_key: str = Field(default="change-me-in-production")
    api_key_header: str = Field(default="X-API-Key")
    allowed_origins: List[str] = Field(default=["*"])
    enable_cors: bool = Field(default=True)
    require_api_key: bool = Field(default=False)
    api_keys: List[str] = Field(default=[])

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v):
        if v == "change-me-in-production" and os.getenv("APP_ENV") == "production":
            raise ValueError("SECRET_KEY must be changed in production")
        return v


class APIConfig(BaseModel):
    """API server configuration."""

    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1, le=65535)
    workers: int = Field(default=4, ge=1, le=32)
    reload: bool = Field(default=False)
    timeout: int = Field(default=60, ge=1)


class ModelConfig(BaseModel):
    """Model configuration."""

    model_path: str = Field(default="models/nids_model.pkl")
    model_version: str = Field(default="1.0.0")
    inference_timeout_ms: int = Field(default=100, ge=1)
    max_batch_size: int = Field(default=1000, ge=1)
    enable_shap: bool = Field(default=True)


class AlertConfig(BaseModel):
    """Alert configuration."""

    queue_size: int = Field(default=10000, ge=100)
    retention_hours: int = Field(default=24, ge=1)
    high_severity_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    medium_severity_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default="INFO")
    format: str = Field(default="json")
    log_file: str = Field(default="logs/nids.log")
    max_bytes: int = Field(default=10485760)
    backup_count: int = Field(default=5)

    @field_validator("level")
    @classmethod
    def validate_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()


class DatabaseConfig(BaseModel):
    """Database configuration."""

    db_type: str = Field(default="sqlite")
    db_path: str = Field(default="data/nids.db")
    db_host: Optional[str] = None
    db_port: Optional[int] = None
    db_name: Optional[str] = None
    db_user: Optional[str] = None
    db_password: Optional[str] = None


class Config(BaseModel):
    """Main application configuration."""
    
    model_config = ConfigDict(
        env_file=".env",
        env_nested_delimiter="__"
    )

    app_env: str = Field(default="development")
    app_name: str = Field(default="NIDS")
    app_version: str = Field(default="1.0.0")
    debug: bool = Field(default=False)

    security: SecurityConfig = Field(default_factory=SecurityConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    alert: AlertConfig = Field(default_factory=AlertConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)

    # Paths
    data_dir: str = Field(default="data")
    model_dir: str = Field(default="models")
    log_dir: str = Field(default="logs")


def load_config() -> Config:
    """Load configuration from environment variables."""
    return Config(
        app_env=os.getenv("APP_ENV", "development"),
        app_name=os.getenv("APP_NAME", "NIDS"),
        app_version=os.getenv("APP_VERSION", "1.0.0"),
        debug=os.getenv("DEBUG", "false").lower() == "true",
        security=SecurityConfig(
            secret_key=os.getenv("SECRET_KEY", "change-me-in-production"),
            api_key_header=os.getenv("API_KEY_HEADER", "X-API-Key"),
            allowed_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
            require_api_key=os.getenv("REQUIRE_API_KEY", "false").lower() == "true",
            api_keys=os.getenv("API_KEYS", "").split(",") if os.getenv("API_KEYS") else [],
        ),
        api=APIConfig(
            host=os.getenv("API_HOST", "0.0.0.0"),
            port=int(os.getenv("API_PORT", "8000")),
            workers=int(os.getenv("API_WORKERS", "4")),
            reload=os.getenv("API_RELOAD", "false").lower() == "true",
        ),
        model=ModelConfig(
            model_path=os.getenv("MODEL_PATH", "models/nids_model.pkl"),
            model_version=os.getenv("MODEL_VERSION", "1.0.0"),
            inference_timeout_ms=int(os.getenv("INFERENCE_TIMEOUT_MS", "100")),
            max_batch_size=int(os.getenv("MAX_BATCH_SIZE", "1000")),
        ),
        alert=AlertConfig(
            queue_size=int(os.getenv("ALERT_QUEUE_SIZE", "10000")),
            retention_hours=int(os.getenv("ALERT_RETENTION_HOURS", "24")),
            high_severity_threshold=float(os.getenv("HIGH_SEVERITY_THRESHOLD", "0.8")),
            medium_severity_threshold=float(os.getenv("MEDIUM_SEVERITY_THRESHOLD", "0.5")),
        ),
        logging=LoggingConfig(
            level=os.getenv("LOG_LEVEL", "INFO"),
            format=os.getenv("LOG_FORMAT", "json"),
            log_file=os.getenv("LOG_FILE", "logs/nids.log"),
            max_bytes=int(os.getenv("LOG_MAX_BYTES", "10485760")),
            backup_count=int(os.getenv("LOG_BACKUP_COUNT", "5")),
        ),
        database=DatabaseConfig(
            db_type=os.getenv("DB_TYPE", "sqlite"),
            db_path=os.getenv("DB_PATH", "data/nids.db"),
            db_host=os.getenv("DB_HOST"),
            db_port=int(os.getenv("DB_PORT")) if os.getenv("DB_PORT") else None,
            db_name=os.getenv("DB_NAME"),
            db_user=os.getenv("DB_USER"),
            db_password=os.getenv("DB_PASSWORD"),
        ),
        data_dir=os.getenv("DATA_DIR", "data"),
        model_dir=os.getenv("MODEL_DIR", "models"),
        log_dir=os.getenv("LOG_DIR", "logs"),
    )


# Global config instance
config = load_config()


def ensure_directories():
    """Ensure required directories exist."""
    Path(config.data_dir).mkdir(parents=True, exist_ok=True)
    Path(config.model_dir).mkdir(parents=True, exist_ok=True)
    Path(config.log_dir).mkdir(parents=True, exist_ok=True)
