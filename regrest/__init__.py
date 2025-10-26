"""Regrest - Regression testing tool for Python."""

try:
    from importlib.metadata import version

    __version__ = version("regrest")
except Exception:
    # Fallback for development mode or if package is not installed
    __version__ = "unknown"

from .config import Config, get_config, set_config
from .decorator import regrest
from .exceptions import RecordLoadError, RegressError, RegressionTestError, StorageError
from .matcher import Matcher, MatchResult
from .storage import Storage, TestRecord

__all__ = [
    "regrest",
    "RegressionTestError",
    "RecordLoadError",
    "RegressError",
    "StorageError",
    "Config",
    "get_config",
    "set_config",
    "Storage",
    "TestRecord",
    "Matcher",
    "MatchResult",
]
