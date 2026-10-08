"""Strict helpers for strategy configuration."""

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation


def integer_parameter(
    parameters: Mapping[str, object],
    name: str,
    default: int,
) -> int:
    """Read a strictly positive integer parameter."""
    value = parameters.get(name, default)

    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer.")

    if value <= 0:
        raise ValueError(f"{name} must be positive.")

    return value


def decimal_parameter(
    parameters: Mapping[str, object],
    name: str,
    default: str,
) -> Decimal:
    """Read a positive finite decimal parameter."""
    value = parameters.get(name, default)

    if isinstance(value, bool):
        raise TypeError(f"{name} cannot be a boolean.")

    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{name} is not a valid decimal.") from exc

    if not result.is_finite() or result <= 0:
        raise ValueError(f"{name} must be finite and positive.")

    return result


def text_parameter(
    parameters: Mapping[str, object],
    name: str,
    default: str,
) -> str:
    """Read a nonempty string without surrounding whitespace."""
    value = parameters.get(name, default)

    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")

    if not value or value != value.strip():
        raise ValueError(f"{name} must be nonempty and trimmed.")

    return value


def reject_unknown_parameters(
    parameters: Mapping[str, object],
    allowed: set[str],
) -> None:
    """Reject misspelled or unsupported parameter names."""
    unknown = set(parameters) - allowed

    if unknown:
        raise ValueError(f"Unknown strategy parameters: {sorted(unknown)}")
