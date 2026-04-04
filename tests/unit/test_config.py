"""Unit tests for config module."""

import shutil
import tempfile
from pathlib import Path

import pytest

from regrest.config import Config, _get_env_bool, _get_env_float, get_config, set_config


class TestEnvHelpers:
    """Test environment variable helper functions."""

    def test_get_env_bool_true_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _get_env_bool with various true values."""
        for value in ["true", "True", "TRUE", "1", "yes", "YES", "on", "ON"]:
            monkeypatch.setenv("TEST_BOOL", value)
            assert _get_env_bool("TEST_BOOL", False) is True

    def test_get_env_bool_false_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _get_env_bool with various false values."""
        for value in ["false", "False", "FALSE", "0", "no", "NO", "off", "OFF"]:
            monkeypatch.setenv("TEST_BOOL", value)
            assert _get_env_bool("TEST_BOOL", True) is False

    def test_get_env_bool_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _get_env_bool returns default when not set."""
        monkeypatch.delenv("TEST_BOOL", raising=False)
        assert _get_env_bool("TEST_BOOL", True) is True
        assert _get_env_bool("TEST_BOOL", False) is False

    def test_get_env_float_valid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _get_env_float with valid float values."""
        monkeypatch.setenv("TEST_FLOAT", "1.5")
        assert _get_env_float("TEST_FLOAT", 0.0) == 1.5

        monkeypatch.setenv("TEST_FLOAT", "1e-9")
        assert _get_env_float("TEST_FLOAT", 0.0) == 1e-9

    def test_get_env_float_invalid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _get_env_float returns default for invalid values."""
        monkeypatch.setenv("TEST_FLOAT", "not_a_float")
        assert _get_env_float("TEST_FLOAT", 2.5) == 2.5

    def test_get_env_float_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _get_env_float returns default when not set."""
        monkeypatch.delenv("TEST_FLOAT", raising=False)
        assert _get_env_float("TEST_FLOAT", 3.14) == 3.14


class TestConfig:
    """Test Config class."""

    def test_default_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Config with default values."""
        # Clear environment variables
        for key in [
            "REGREST_STORAGE_DIR",
            "REGREST_RAISE_ON_ERROR",
            "REGREST_UPDATE_MODE",
            "REGREST_FLOAT_TOLERANCE",
        ]:
            monkeypatch.delenv(key, raising=False)

        config = Config()
        assert config.storage_dir == Path(".regrest")
        assert config.raise_on_error is False
        assert config.update_mode is False
        assert config.float_tolerance == 1e-9

    def test_constructor_arguments(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Config with constructor arguments."""
        # Set env vars to different values
        monkeypatch.setenv("REGREST_STORAGE_DIR", "/some/path")
        monkeypatch.setenv("REGREST_RAISE_ON_ERROR", "false")
        monkeypatch.setenv("REGREST_UPDATE_MODE", "false")
        monkeypatch.setenv("REGREST_FLOAT_TOLERANCE", "1e-6")

        # Constructor args should override env vars
        config = Config(
            storage_dir="/custom/path",
            raise_on_error=True,
            update_mode=True,
            float_tolerance=1e-12,
        )

        assert config.storage_dir == Path("/custom/path")
        assert config.raise_on_error is True
        assert config.update_mode is True
        assert config.float_tolerance == 1e-12

    def test_env_variables(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Config reads from environment variables."""
        monkeypatch.setenv("REGREST_STORAGE_DIR", "/env/path")
        monkeypatch.setenv("REGREST_RAISE_ON_ERROR", "true")
        monkeypatch.setenv("REGREST_UPDATE_MODE", "1")
        monkeypatch.setenv("REGREST_FLOAT_TOLERANCE", "1e-6")

        config = Config()
        assert config.storage_dir == Path("/env/path")
        assert config.raise_on_error is True
        assert config.update_mode is True
        assert config.float_tolerance == 1e-6

    def test_partial_constructor_args(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Config with partial constructor arguments."""
        monkeypatch.setenv("REGREST_STORAGE_DIR", "/env/path")
        monkeypatch.setenv("REGREST_FLOAT_TOLERANCE", "1e-6")

        # Only override some values
        config = Config(raise_on_error=True, update_mode=True)

        # Should use env vars for unspecified args
        assert config.storage_dir == Path("/env/path")
        assert config.float_tolerance == 1e-6

        # Should use constructor args for specified args
        assert config.raise_on_error is True
        assert config.update_mode is True

    def test_ensure_storage_dir_creates_directory(self) -> None:
        """Test ensure_storage_dir creates the directory."""
        temp_dir = tempfile.mkdtemp()
        try:
            storage_path = Path(temp_dir) / "nested" / "storage"
            config = Config(storage_dir=str(storage_path))

            assert not storage_path.exists()
            config.ensure_storage_dir()
            assert storage_path.exists()
            assert storage_path.is_dir()
        finally:
            shutil.rmtree(temp_dir)

    def test_ensure_storage_dir_creates_gitignore(self) -> None:
        """Test ensure_storage_dir creates .gitignore."""
        temp_dir = tempfile.mkdtemp()
        try:
            storage_path = Path(temp_dir) / "storage"
            config = Config(storage_dir=str(storage_path))

            config.ensure_storage_dir()

            gitignore_path = storage_path / ".gitignore"
            assert gitignore_path.exists()

            content = gitignore_path.read_text()
            assert "*" in content
        finally:
            shutil.rmtree(temp_dir)

    def test_ensure_gitignore_not_overwritten(self) -> None:
        """Test that existing .gitignore is not overwritten."""
        temp_dir = tempfile.mkdtemp()
        try:
            storage_path = Path(temp_dir) / "storage"
            storage_path.mkdir()

            # Create custom .gitignore
            gitignore_path = storage_path / ".gitignore"
            custom_content = "# Custom content\n*.tmp\n"
            gitignore_path.write_text(custom_content)

            config = Config(storage_dir=str(storage_path))
            config.ensure_storage_dir()

            # Should not be overwritten
            assert gitignore_path.read_text() == custom_content
        finally:
            shutil.rmtree(temp_dir)


class TestGlobalConfig:
    """Test global config functions."""

    def test_get_config_returns_instance(self) -> None:
        """Test get_config returns a Config instance."""
        config = get_config()
        assert isinstance(config, Config)

    def test_set_config_changes_global(self) -> None:
        """Test set_config changes the global config."""
        original = get_config()

        # Create and set new config
        custom_config = Config(
            storage_dir="/custom",
            raise_on_error=True,
            update_mode=True,
            float_tolerance=1e-12,
        )
        set_config(custom_config)

        # Get config should return the new one
        current = get_config()
        assert current is custom_config
        assert current.storage_dir == Path("/custom")
        assert current.raise_on_error is True
        assert current.update_mode is True
        assert current.float_tolerance == 1e-12

        # Restore original
        set_config(original)

    def test_get_config_is_singleton(self) -> None:
        """Test get_config returns the same instance."""
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2
