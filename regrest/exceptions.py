"""Custom exceptions for regrest."""


class RegressError(Exception):
    """Base exception for regrest."""


class RegressionTestError(RegressError, AssertionError):
    """Exception raised when regression test fails."""


class RecordLoadError(RegressError):
    """Exception raised when record cannot be loaded."""


class StorageError(RegressError):
    """Exception raised when storage operation fails."""
