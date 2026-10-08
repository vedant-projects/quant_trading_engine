"""Shared environment isolation for unit tests."""

import os
from collections.abc import Iterator

import pytest

from app.config import Settings, get_settings


@pytest.fixture(autouse=True)
def isolate_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[None]:
    """Prevent inherited application variables from contaminating tests."""
    names = {name.casefold() for name in Settings.model_fields}

    for key in list(os.environ):
        if key.casefold() in names:
            monkeypatch.delenv(key, raising=False)

    get_settings.cache_clear()

    yield

    get_settings.cache_clear()
