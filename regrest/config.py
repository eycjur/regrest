"""Configuration management for regrest."""

import os
from pathlib import Path
from typing import Optional


def _get_env_bool(key: str, default: bool) -> bool:
    """Get boolean value from environment variable.

    Args:
        key: Environment variable name
        default: Default value if not set

    Returns:
        Boolean value
    """
    value = os.getenv(key)
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes", "on")


def _get_env_float(key: str, default: float) -> float:
    """Get float value from environment variable.

    Args:
        key: Environment variable name
        default: Default value if not set

    Returns:
        Float value
    """
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


class Config:
    """Configuration for regrest.

    Configuration can be set via:
    1. Constructor arguments (highest priority)
    2. Environment variables
    3. Default values (lowest priority)

    Environment variables:
        REGREST_STORAGE_DIR: Directory to store test records
        REGREST_RAISE_ON_ERROR: If true, raise exception on test failure
            (true/false, 1/0)
        REGREST_UPDATE_MODE: If true, update records instead of testing
            (true/false, 1/0)
        REGREST_FLOAT_TOLERANCE: Float comparison tolerance (e.g., 1e-9)
    """

    def __init__(
        self,
        storage_dir: Optional[str] = None,
        raise_on_error: Optional[bool] = None,
        update_mode: Optional[bool] = None,
        float_tolerance: Optional[float] = None,
    ):
        """Initialize configuration.

        Args:
            storage_dir: Directory to store test records
            raise_on_error: If True, raise exception on test failure
            update_mode: If True, update records instead of testing
            float_tolerance: Float comparison tolerance
        """
        # Storage directory: argument > env > default
        if storage_dir is not None:
            self.storage_dir = Path(storage_dir)
        else:
            env_dir = os.getenv("REGREST_STORAGE_DIR")
            self.storage_dir = Path(env_dir) if env_dir else Path(".regrest")

        # raise_on_error: argument > env > default (False)
        if raise_on_error is not None:
            self.raise_on_error = raise_on_error
        else:
            self.raise_on_error = _get_env_bool("REGREST_RAISE_ON_ERROR", False)

        # update_mode: argument > env > default (False)
        if update_mode is not None:
            self.update_mode = update_mode
        else:
            self.update_mode = _get_env_bool("REGREST_UPDATE_MODE", False)

        # float_tolerance: argument > env > default (1e-9)
        if float_tolerance is not None:
            self.float_tolerance = float_tolerance
        else:
            self.float_tolerance = _get_env_float("REGREST_FLOAT_TOLERANCE", 1e-9)

    def ensure_storage_dir(self) -> None:
        """Create storage directory if it doesn't exist.

        Also automatically adds the directory to .gitignore.
        """
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Automatically add to .gitignore
        self._ensure_gitignore()

    def _ensure_gitignore(self) -> None:
        """Create .gitignore inside storage directory to ignore all contents."""
        gitignore_path = self.storage_dir / ".gitignore"

        # If .gitignore already exists, don't overwrite
        if gitignore_path.exists():
            return

        # Create .gitignore to ignore all files
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write("# Ignore all files in this directory\n")
            f.write("*\n")


# Global config instance
_config = Config()


def get_config() -> Config:
    """Get the global configuration instance."""
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config
