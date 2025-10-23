"""Logging configuration for regrest."""

import logging
import os


def _get_log_level_from_env() -> int:
    """Get log level from environment variable.

    Environment variable:
        REGREST_LOG_LEVEL: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Logging level constant
    """
    level_str = os.getenv("REGREST_LOG_LEVEL", "INFO").upper()
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return level_map.get(level_str, logging.INFO)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Get a logger for regrest.

    Args:
        name: Logger name
        level: Logging level (default: INFO)

    Returns:
        Configured logger
    """
    formatter = logging.Formatter(
        "\033[92m%(levelname)-8s [%(asctime)s] %(name)s\033[0m: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.addHandler(handler)
    logger.setLevel(_get_log_level_from_env() or level)
    logger.propagate = False
    return logger


regrest_logger = get_logger("regrest")
