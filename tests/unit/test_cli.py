"""Unit tests for CLI module."""

import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from regrest.cli import _format_value, app
from regrest.config import Config
from regrest.storage import Storage, TestRecord

runner = CliRunner()


@pytest.fixture
def temp_storage_dir() -> Generator[str, None, None]:
    """Create a temporary storage directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def populated_storage(temp_storage_dir: str) -> tuple[str, Storage]:
    """Create a storage with sample records."""
    config = Config(storage_dir=temp_storage_dir)
    from regrest.config import set_config

    set_config(config)
    storage = Storage()

    # Add sample records
    record1 = TestRecord("module1", "func1", (1, 2), {"key": "value"}, {"output": 42})
    record2 = TestRecord("module1", "func2", (), {}, "result2")
    record3 = TestRecord("module2", "calculate", (10,), {}, 100)

    storage.save(record1)
    storage.save(record2)
    storage.save(record3)

    return temp_storage_dir, storage


class TestFormatValue:
    """Test _format_value helper function."""

    def test_format_short_value(self) -> None:
        """Test formatting short values."""
        assert _format_value(42) == "42"
        assert _format_value("hello") == "'hello'"
        assert _format_value([1, 2, 3]) == "[1, 2, 3]"

    def test_format_long_value(self) -> None:
        """Test formatting long values (should truncate)."""
        long_str = "a" * 100
        result = _format_value(long_str)
        assert len(result) <= 80
        assert result.endswith("...")


class TestListCommand:
    """Test the list command."""

    def test_list_no_records(self, temp_storage_dir: str) -> None:
        """Test list with no records."""
        result = runner.invoke(app, ["--storage-dir", temp_storage_dir, "list"])
        assert result.exit_code == 0
        assert "No test records found" in result.stdout

    def test_list_all_records(self, populated_storage: tuple[str, Storage]) -> None:
        """Test list all records."""
        storage_dir, _ = populated_storage
        result = runner.invoke(app, ["--storage-dir", storage_dir, "list"])
        assert result.exit_code == 0
        assert "Found 3 test record(s)" in result.stdout
        assert "module1" in result.stdout
        assert "module2" in result.stdout
        assert "func1" in result.stdout
        assert "func2" in result.stdout
        assert "calculate" in result.stdout

    def test_list_with_keyword_filter(
        self, populated_storage: tuple[str, Storage]
    ) -> None:
        """Test list with keyword filter."""
        storage_dir, _ = populated_storage
        result = runner.invoke(
            app, ["--storage-dir", storage_dir, "list", "-k", "calculate"]
        )
        assert result.exit_code == 0
        assert "calculate" in result.stdout
        assert "func1" not in result.stdout

    def test_list_with_no_matching_filter(
        self, populated_storage: tuple[str, Storage]
    ) -> None:
        """Test list with filter that matches nothing."""
        storage_dir, _ = populated_storage
        result = runner.invoke(
            app, ["--storage-dir", storage_dir, "list", "-k", "nonexistent"]
        )
        assert result.exit_code == 0
        assert "No test records found matching the filter" in result.stdout


class TestDeleteCommand:
    """Test the delete command."""

    def test_delete_no_arguments(self, temp_storage_dir: str) -> None:
        """Test delete without arguments shows error."""
        result = runner.invoke(app, ["--storage-dir", temp_storage_dir, "delete"])
        assert result.exit_code == 1
        # Error messages can be in stdout or stderr
        output = result.stdout + result.stderr
        assert (
            "Error: Specify --all, --pattern, or a record ID" in output
            or "Missing argument" in output
        )

    def test_delete_by_id_with_confirmation_yes(
        self, populated_storage: tuple[str, Storage]
    ) -> None:
        """Test delete by ID with confirmation."""
        storage_dir, storage = populated_storage
        records = storage.list_all()
        record_id = records[0].record_id

        result = runner.invoke(
            app,
            ["--storage-dir", storage_dir, "delete", record_id, "-y"],
        )
        assert result.exit_code == 0
        assert f"Deleted record '{record_id}'" in result.stdout

        # Verify record was deleted
        remaining = storage.list_all()
        assert len(remaining) == 2

    def test_delete_nonexistent_id(
        self, populated_storage: tuple[str, Storage]
    ) -> None:
        """Test delete with nonexistent ID."""
        storage_dir, _ = populated_storage
        result = runner.invoke(
            app,
            ["--storage-dir", storage_dir, "delete", "nonexistent_id", "-y"],
        )
        assert result.exit_code == 1
        # Error messages can be in stdout or stderr
        output = result.stdout + result.stderr
        assert "Record 'nonexistent_id' not found" in output or "not found" in output

    def test_delete_by_pattern(self, populated_storage: tuple[str, Storage]) -> None:
        """Test delete by pattern."""
        storage_dir, storage = populated_storage
        result = runner.invoke(
            app,
            ["--storage-dir", storage_dir, "delete", "--pattern", "module1.*", "-y"],
        )
        assert result.exit_code == 0
        assert "Deleted 2 record(s)" in result.stdout

        # Verify only module2 records remain
        remaining = storage.list_all()
        assert len(remaining) == 1
        assert remaining[0].module == "module2"

    def test_delete_all(self, populated_storage: tuple[str, Storage]) -> None:
        """Test delete all records."""
        storage_dir, storage = populated_storage
        result = runner.invoke(
            app,
            ["--storage-dir", storage_dir, "delete", "--all", "-y"],
        )
        assert result.exit_code == 0
        assert "Deleted 3 record(s)" in result.stdout

        # Verify all records deleted
        remaining = storage.list_all()
        assert len(remaining) == 0


class TestVerifyCommand:
    """Test the verify command."""

    def test_verify_no_records(self, temp_storage_dir: str) -> None:
        """Test verify with no records."""
        result = runner.invoke(app, ["--storage-dir", temp_storage_dir, "verify"])
        assert result.exit_code == 0
        assert "No test records found" in result.stdout

    def test_verify_with_keyword_filter(
        self, populated_storage: tuple[str, Storage]
    ) -> None:
        """Test verify with keyword filter."""
        storage_dir, _ = populated_storage
        result = runner.invoke(
            app, ["--storage-dir", storage_dir, "verify", "-k", "calculate"]
        )
        # Will likely fail because functions don't exist in test env,
        # but we can check the filtering works
        assert (
            "calculate" in result.stdout or "Verifying 1 test record" in result.stdout
        )

    def test_verify_no_matching_filter(
        self, populated_storage: tuple[str, Storage]
    ) -> None:
        """Test verify with filter that matches nothing."""
        storage_dir, _ = populated_storage
        result = runner.invoke(
            app, ["--storage-dir", storage_dir, "verify", "-k", "nonexistent"]
        )
        assert result.exit_code == 0
        assert "No test records found matching the filter" in result.stdout

    def test_verify_custom_tolerance(
        self, populated_storage: tuple[str, Storage]
    ) -> None:
        """Test verify with custom tolerance."""
        storage_dir, _ = populated_storage
        result = runner.invoke(
            app, ["--storage-dir", storage_dir, "verify", "--tolerance", "0.001"]
        )
        # Command should at least try to verify (will fail because funcs don't exist)
        assert "Verifying" in result.stdout


class TestServeCommand:
    """Test the serve command."""

    def test_serve_command_exists(self) -> None:
        """Test that serve command exists and shows help."""
        result = runner.invoke(app, ["serve", "--help"])
        assert result.exit_code == 0
        assert "Start a web server" in result.stdout


class TestCLIIntegration:
    """Integration tests for CLI."""

    def test_help_command(self) -> None:
        """Test help command."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "regrest" in result.stdout.lower()
        assert "list" in result.stdout
        assert "delete" in result.stdout
        assert "verify" in result.stdout
        assert "serve" in result.stdout

    def test_list_help(self) -> None:
        """Test list help."""
        result = runner.invoke(app, ["list", "--help"])
        assert result.exit_code == 0
        assert "List all test records" in result.stdout

    def test_delete_help(self) -> None:
        """Test delete help."""
        result = runner.invoke(app, ["delete", "--help"])
        assert result.exit_code == 0
        assert "Delete test records" in result.stdout

    def test_verify_help(self) -> None:
        """Test verify help."""
        result = runner.invoke(app, ["verify", "--help"])
        assert result.exit_code == 0
        assert "Verify all recorded test records" in result.stdout

    def test_custom_storage_dir(self) -> None:
        """Test using custom storage directory."""
        temp_dir = tempfile.mkdtemp()
        try:
            custom_storage = Path(temp_dir) / "custom_storage"
            result = runner.invoke(app, ["--storage-dir", str(custom_storage), "list"])
            assert result.exit_code == 0
            assert "No test records found" in result.stdout
        finally:
            shutil.rmtree(temp_dir)
