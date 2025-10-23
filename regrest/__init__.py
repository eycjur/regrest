"""Regrest - Regression testing tool for Python."""

__version__ = "0.1.0"

from .config import Config, get_config, set_config
from .decorator import RegressionTestError, regrest
from .matcher import Matcher, MatchResult
from .storage import Storage, TestRecord

__all__ = [
    "regrest",
    "RegressionTestError",
    "Config",
    "get_config",
    "set_config",
    "Storage",
    "TestRecord",
    "Matcher",
    "MatchResult",
]
