"""Structured JSON logging configuration."""

import logging
import sys

import structlog
from structlog.typing import Processor


def configure_logging(level: str = "INFO") -> None:
    """Configure standard-library and structlog output as JSON."""
    normalized_level = level.upper()

    level_number = getattr(
        logging,
        normalized_level,
        None,
    )

    if not isinstance(level_number, int):
        raise ValueError(f"Unsupported logging level: {level}")

    shared_processors: list[Processor] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(
            fmt="iso",
            utc=True,
        ),
    ]

    formatter_processors: list[Processor] = [
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ]

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=formatter_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level_number)

    application_processors: list[Processor] = [
        structlog.stdlib.filter_by_level,
        *shared_processors,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ]

    structlog.configure(
        processors=application_processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
