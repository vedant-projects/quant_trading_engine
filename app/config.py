"""Validated application configuration.

Settings are loaded from environment variables and the local .env file.
Live trading is deliberately unsupported at this development stage.
"""

from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class Settings(BaseSettings):
    """Define application settings and startup safety constraints."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )

    data_directory: Path = Path("data")
    report_directory: Path = Path("reports")

    app_name: str = "Personal Quant Trading Engine"
    app_env: Literal["development", "test", "production"] = "development"

    is_paper: bool = True
    enable_live_trading: bool = False

    database_url: SecretStr = SecretStr(
        "postgresql+asyncpg://quant:CHANGE_ME@127.0.0.1:5432/quant_engine"
    )
    redis_url: SecretStr = SecretStr("redis://127.0.0.1:6379/0")

    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=5, ge=0, le=50)
    database_connect_timeout_seconds: float = Field(
        default=5.0,
        gt=0,
        le=60,
        allow_inf_nan=False,
    )
    database_health_timeout_seconds: float = Field(
        default=3.0,
        gt=0,
        le=30,
        allow_inf_nan=False,
    )

    alpaca_api_key: SecretStr = SecretStr("")
    alpaca_secret_key: SecretStr = SecretStr("")

    max_daily_loss_pct: Decimal = Field(
        default=Decimal("2.0"),
        gt=0,
        lt=100,
        allow_inf_nan=False,
    )
    max_position_pct: Decimal = Field(
        default=Decimal("10.0"),
        gt=0,
        le=100,
        allow_inf_nan=False,
    )

    log_level: Literal[
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ] = "INFO"

    @field_validator("app_name")
    @classmethod
    def validate_app_name(cls, value: str) -> str:
        """Reject an empty application name."""
        if not value.strip():
            raise ValueError("app_name cannot be empty.")

        return value.strip()

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: object) -> object:
        """Accept case-insensitive logging levels."""
        if isinstance(value, str):
            return value.strip().upper()

        return value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr) -> SecretStr:
        """Require a PostgreSQL URL using the asyncpg driver."""
        try:
            url = make_url(value.get_secret_value())
        except (ArgumentError, ValueError) as exc:
            raise ValueError("database_url is not a valid database URL.") from exc

        if url.drivername != "postgresql+asyncpg":
            raise ValueError("database_url must use the postgresql+asyncpg driver.")

        if not url.host or not url.database or not url.username:
            raise ValueError(
                "database_url must include a host, database, and username."
            )

        return value

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, value: SecretStr) -> SecretStr:
        """Require a Redis connection URL."""
        try:
            url = urlsplit(value.get_secret_value())
            hostname = url.hostname
            port = url.port
        except ValueError as exc:
            raise ValueError("redis_url is not a valid Redis URL.") from exc

        if url.scheme not in {"redis", "rediss"} or not hostname:
            raise ValueError(
                "redis_url must use redis:// or rediss:// and include a host."
            )

        if port is not None and not 1 <= port <= 65535:
            raise ValueError("redis_url contains an invalid port.")

        return value

    @model_validator(mode="after")
    def enforce_paper_only_stage(self) -> Self:
        """Reject live-mode settings until live execution is implemented."""
        if not self.is_paper or self.enable_live_trading:
            raise ValueError(
                "This development stage supports paper trading only. "
                "Set IS_PAPER=true and ENABLE_LIVE_TRADING=false."
            )

        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and cache the application's validated configuration."""
    return Settings()
