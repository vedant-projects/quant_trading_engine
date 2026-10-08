"""Unit tests for application settings and startup safety."""

import os
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings


@pytest.fixture(autouse=True)
def isolate_settings_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Remove inherited settings and prevent cached state leaking."""
    setting_names = {name.casefold() for name in Settings.model_fields}

    for environment_name in list(os.environ):
        if environment_name.casefold() in setting_names:
            monkeypatch.delenv(environment_name, raising=False)

    get_settings.cache_clear()


def test_defaults_are_paper_only() -> None:
    """The default configuration cannot enable live execution."""
    settings = Settings(_env_file=None)

    assert settings.is_paper is True
    assert settings.enable_live_trading is False


def test_percentage_defaults_use_percentage_points() -> None:
    """Two means two percent, not a fractional value of two."""
    settings = Settings(_env_file=None)

    assert settings.max_daily_loss_pct == Decimal("2.0")
    assert settings.max_position_pct == Decimal("10.0")


def test_environment_variables_are_loaded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Environment variables override configuration defaults."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("MAX_DAILY_LOSS_PCT", "1.5")

    settings = Settings(_env_file=None)

    assert settings.app_env == "test"
    assert settings.max_daily_loss_pct == Decimal("1.5")


def test_live_mode_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Setting paper mode false prevents startup."""
    monkeypatch.setenv("IS_PAPER", "false")

    with pytest.raises(ValidationError, match="paper trading only"):
        Settings(_env_file=None)


def test_live_enable_flag_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The live-enable flag is not supported at this development stage."""
    monkeypatch.setenv("ENABLE_LIVE_TRADING", "true")

    with pytest.raises(ValidationError, match="paper trading only"):
        Settings(_env_file=None)


@pytest.mark.parametrize(
    "value",
    ["0", "-1", "100", "NaN", "Infinity"],
)
def test_invalid_daily_loss_limit_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    """Daily loss limits must be finite and between zero and 100."""
    monkeypatch.setenv("MAX_DAILY_LOSS_PCT", value)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.mark.parametrize(
    "value",
    ["0", "-1", "101", "NaN", "Infinity"],
)
def test_invalid_position_limit_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    """Position caps must be finite, positive, and at most 100."""
    monkeypatch.setenv("MAX_POSITION_PCT", value)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_position_limit_accepts_one_hundred_percent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fully allocated position is a valid configuration boundary."""
    monkeypatch.setenv("MAX_POSITION_PCT", "100")

    settings = Settings(_env_file=None)

    assert settings.max_position_pct == Decimal("100")


def test_database_url_requires_asyncpg(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A synchronous database driver is rejected."""
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://quant:password@localhost:5432/quant_engine",
    )

    with pytest.raises(ValidationError, match="asyncpg"):
        Settings(_env_file=None)


def test_database_url_requires_database_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A connection URL must identify a database."""
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://quant:password@localhost:5432",
    )

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_redis_url_rejects_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HTTP is not a valid Redis connection scheme."""
    monkeypatch.setenv("REDIS_URL", "http://localhost:6379/0")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_log_level_is_normalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lowercase logging levels are accepted and normalized."""
    monkeypatch.setenv("LOG_LEVEL", "debug")

    settings = Settings(_env_file=None)

    assert settings.log_level == "DEBUG"


def test_secrets_are_masked_in_settings_repr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ordinary settings representations do not reveal stored secrets."""
    monkeypatch.setenv("ALPACA_API_KEY", "test-key-not-a-real-key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "test-secret-not-a-real-secret")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://quant:private-password@localhost:5432/quant_engine",
    )

    settings = Settings(_env_file=None)
    representation = repr(settings)

    assert "test-key-not-a-real-key" not in representation
    assert "test-secret-not-a-real-secret" not in representation
    assert "private-password" not in representation


def test_settings_are_frozen() -> None:
    """Validated settings cannot be reassigned in ordinary application code."""
    settings = Settings(_env_file=None)

    with pytest.raises(ValidationError):
        settings.is_paper = False
