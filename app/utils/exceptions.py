"""Application-domain exception hierarchy."""


class EngineError(Exception):
    """Base exception for trading-engine domain failures."""


class ConfigurationError(EngineError):
    """Indicate an invalid or unsupported engine configuration."""


class DataValidationError(EngineError):
    """Indicate unusable market data or an invalid data sequence."""


class RiskRejected(EngineError):
    """Indicate that an intended order failed a risk check."""


class CircuitBreakerTripped(RiskRejected):
    """Indicate that trading is blocked by a latched circuit breaker."""


class BrokerError(EngineError):
    """Indicate a broker communication or execution failure."""


class ReconciliationError(EngineError):
    """Indicate a disagreement between local and broker account state."""
