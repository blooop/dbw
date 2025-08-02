"""Structured logging for dbw."""

import logging
import sys
from datetime import datetime

import structlog
from rich.console import Console
from rich.logging import RichHandler

from .config import get_logs_dir


def setup_logging(verbose: bool = False) -> structlog.BoundLogger:
    """Setup structured logging with file and console output."""

    # Ensure logs directory exists
    logs_dir = get_logs_dir()
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Configure standard library logging
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        handlers=[
            RichHandler(
                console=Console(stderr=True),
                show_time=False,
                show_path=False,
                markup=True,
            ),
            logging.FileHandler(
                logs_dir / f"dbw-{datetime.now().strftime('%Y%m%d')}.log",
                mode="a",
            ),
        ],
        format="%(message)s",
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
            if not sys.stderr.isatty()
            else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger("dbw")


def get_logger(name: str = "dbw") -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


# Global logger instance
logger = get_logger()
