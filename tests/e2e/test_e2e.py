"""End-to-end tests for complete workflows."""

import shutil
import tempfile
from collections.abc import Generator
from typing import Any, Union

import pytest
from typer.testing import CliRunner

from regrest import regrest
from regrest.cli import app
from regrest.config import Config, set_config
from regrest.exceptions import RegressionTestError
from regrest.storage import Storage

runner = CliRunner()


@pytest.fixture
def temp_storage_dir() -> Generator[str, None, None]:
    """Create a temporary storage directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def clean_config(temp_storage_dir: str) -> Generator[Config, None, None]:
    """Create a clean config for each test."""
    config = Config(storage_dir=temp_storage_dir)
    set_config(config)
    yield config
    # Restore default config
    set_config(Config())


class TestCompleteWorkflow:
    """Test complete end-to-end workflows."""

    def test_record_verify_workflow(self, clean_config: Config) -> None:
        """Test recording and verifying results."""

        @regrest
        def add(a: int, b: int) -> int:
            return a + b

        # First call - should record
        result1 = add(2, 3)
        assert result1 == 5

        # Second call - should verify
        result2 = add(2, 3)
        assert result2 == 5

        # Verify record was created
        storage = Storage()
        records = storage.list_all()
        assert len(records) == 1
        assert records[0].result == 5

    def test_multiple_functions_workflow(self, clean_config: Config) -> None:
        """Test workflow with multiple functions."""

        @regrest
        def multiply(a: int, b: int) -> int:
            return a * b

        @regrest
        def divide(a: int, b: int) -> float:
            return a / b

        @regrest
        def power(a: int, b: int) -> int:
            return a**b

        # Record multiple functions
        assert multiply(3, 4) == 12
        assert divide(10, 2) == 5.0
        assert power(2, 3) == 8

        # Verify all records
        assert multiply(3, 4) == 12
        assert divide(10, 2) == 5.0
        assert power(2, 3) == 8

        # Check storage
        storage = Storage()
        records = storage.list_all()
        assert len(records) == 3

    def test_update_workflow(self, clean_config: Config) -> None:
        """Test updating existing records."""
        call_count = 0

        @regrest
        def counter() -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        # First call - record
        result1 = counter()
        assert result1 == 1

        # Verify record
        storage = Storage()
        record = storage.find(counter.__module__, "counter", (), {})
        assert record is not None
        assert record.result == 1

        # Update the record
        @regrest(update=True)  # type: ignore[no-redef]
        def counter() -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        result2 = counter()
        assert result2 == 2

        # Verify record was updated
        record = storage.find(counter.__module__, "counter", (), {})
        assert record is not None
        assert record.result == 2

    def test_failure_detection_workflow(self, clean_config: Config) -> None:
        """Test detecting regression failures."""
        first_call = True

        @regrest(raise_on_error=True)
        def changing_function() -> str:
            nonlocal first_call
            if first_call:
                first_call = False
                return "original"
            else:
                return "changed"

        # First call - record
        result1 = changing_function()
        assert result1 == "original"

        # Second call - should fail
        with pytest.raises(RegressionTestError) as exc_info:
            changing_function()

        assert "Regression test failed" in str(exc_info.value)

    def test_float_tolerance_workflow(self, clean_config: Config) -> None:
        """Test float comparison with tolerance."""

        @regrest(tolerance=1e-9)
        def calculate_sum() -> float:
            return 0.1 + 0.2

        # First call - record
        result1 = calculate_sum()

        # Second call - should pass despite floating point precision
        result2 = calculate_sum()

        # Both should be equal within tolerance
        assert abs(result1 - 0.3) < 1e-9
        assert abs(result2 - 0.3) < 1e-9


class TestCLIWorkflow:
    """Test CLI workflows."""

    def test_list_delete_workflow(self, temp_storage_dir: str) -> None:
        """Test listing and deleting records via CLI."""
        # Set up config
        config = Config(storage_dir=temp_storage_dir)
        set_config(config)

        # Create some records
        @regrest
        def func1() -> int:
            return 1

        @regrest
        def func2() -> int:
            return 2

        func1()
        func2()

        # List records
        result = runner.invoke(app, ["--storage-dir", temp_storage_dir, "list"])
        assert result.exit_code == 0
        assert "Found 2 test record(s)" in result.stdout

        # Get record IDs
        storage = Storage()
        records = storage.list_all()
        record_id = records[0].record_id

        # Delete one record
        result = runner.invoke(
            app, ["--storage-dir", temp_storage_dir, "delete", record_id, "-y"]
        )
        assert result.exit_code == 0

        # Verify only one record remains
        result = runner.invoke(app, ["--storage-dir", temp_storage_dir, "list"])
        assert result.exit_code == 0
        assert "Found 1 test record(s)" in result.stdout

        # Delete all records
        result = runner.invoke(
            app, ["--storage-dir", temp_storage_dir, "delete", "--all", "-y"]
        )
        assert result.exit_code == 0

        # Verify no records remain
        result = runner.invoke(app, ["--storage-dir", temp_storage_dir, "list"])
        assert result.exit_code == 0
        assert "No test records found" in result.stdout

        # Restore default config
        set_config(Config())


class TestComplexDataWorkflow:
    """Test workflows with complex data structures."""

    def test_nested_structure_workflow(self, clean_config: Config) -> None:
        """Test with nested data structures."""

        @regrest
        def get_user_data() -> dict[str, Any]:
            return {
                "user": {
                    "name": "Alice",
                    "profile": {"age": 30, "city": "Tokyo"},
                    "scores": [95, 87, 92],
                },
                "metadata": {"version": "1.0"},
            }

        # First call - record
        result1 = get_user_data()
        assert result1["user"]["name"] == "Alice"

        # Second call - verify
        result2 = get_user_data()
        assert result2 == result1

    @pytest.mark.skip(
        reason="Custom classes defined in test functions cannot be pickled"
    )
    def test_custom_class_workflow(self, clean_config: Config) -> None:
        """Test with custom classes."""

        class User:
            def __init__(self, name: str, age: int) -> None:
                self.name = name
                self.age = age

            def __eq__(self, other: object) -> bool:
                return (
                    isinstance(other, User)
                    and self.name == other.name
                    and self.age == other.age
                )

        @regrest
        def create_user() -> User:
            return User("Alice", 30)

        # First call - record
        user1 = create_user()
        assert user1.name == "Alice"
        assert user1.age == 30

        # Second call - verify
        user2 = create_user()
        assert user2 == user1

    def test_mixed_types_workflow(self, clean_config: Config) -> None:
        """Test with mixed data types."""

        @regrest
        def get_mixed_data(x: int) -> dict[str, Any]:
            return {
                "int": x,
                "float": x * 1.5,
                "str": f"value_{x}",
                "list": [x, x + 1, x + 2],
                "tuple": (x, x * 2),
                "dict": {"key": x},
                "bool": x > 5,
                "none": None,
            }

        # First call - record
        result1 = get_mixed_data(10)

        # Second call - verify
        result2 = get_mixed_data(10)
        assert result2 == result1

        # Different argument - new record
        result3 = get_mixed_data(20)
        assert result3 != result1

        # Verify two records exist
        storage = Storage()
        records = storage.list_all()
        assert len(records) == 2


class TestMultiModuleWorkflow:
    """Test workflows across multiple modules."""

    def test_multiple_argument_combinations(self, clean_config: Config) -> None:
        """Test function with multiple argument combinations."""

        @regrest
        def calculate(operation: str, a: int, b: int) -> Union[int, float, None]:
            if operation == "add":
                return a + b
            elif operation == "subtract":
                return a - b
            elif operation == "multiply":
                return a * b
            elif operation == "divide":
                return a / b
            return None

        # Record multiple combinations
        assert calculate("add", 10, 5) == 15
        assert calculate("subtract", 10, 5) == 5
        assert calculate("multiply", 10, 5) == 50
        assert calculate("divide", 10, 5) == 2.0

        # Verify all combinations
        assert calculate("add", 10, 5) == 15
        assert calculate("subtract", 10, 5) == 5
        assert calculate("multiply", 10, 5) == 50
        assert calculate("divide", 10, 5) == 2.0

        # Verify 4 records exist
        storage = Storage()
        records = storage.list_all()
        assert len(records) == 4


class TestErrorHandlingWorkflow:
    """Test error handling workflows."""

    def test_non_strict_mode_continues_on_error(
        self, clean_config: Config, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that non-strict mode logs errors but continues."""
        import logging

        # Capture logs from the regrest logger
        caplog.set_level(logging.ERROR, logger="regrest")

        # Enable propagation so caplog can capture logs
        from regrest._logging import regrest_logger

        old_propagate = regrest_logger.propagate
        regrest_logger.propagate = True

        try:
            first_call = True

            @regrest(raise_on_error=False)
            def sometimes_fails() -> int:
                nonlocal first_call
                if first_call:
                    first_call = False
                    return 100
                else:
                    return 200

            # First call - record
            result1 = sometimes_fails()
            assert result1 == 100

            # Second call - should log error but not raise
            result2 = sometimes_fails()
            assert result2 == 200

            # Verify error was logged
            log_messages = " ".join(record.message for record in caplog.records)
            assert (
                "Regression test failed" in log_messages
                or "Value mismatch" in log_messages
            )
        finally:
            # Restore original propagate setting
            regrest_logger.propagate = old_propagate


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_data_processing_pipeline(self, clean_config: Config) -> None:
        """Test a data processing pipeline."""

        @regrest
        def load_data() -> list[int]:
            return [1, 2, 3, 4, 5]

        @regrest
        def process_data(data: list[int]) -> list[int]:
            return [x * 2 for x in data]

        @regrest
        def aggregate_data(data: list[int]) -> dict[str, Union[int, float]]:
            return {"sum": sum(data), "count": len(data), "avg": sum(data) / len(data)}

        # Pipeline execution
        raw_data = load_data()
        processed_data = process_data(raw_data)
        result = aggregate_data(processed_data)

        assert result["sum"] == 30
        assert result["count"] == 5
        assert result["avg"] == 6.0

        # Verify pipeline works on second run
        raw_data = load_data()
        processed_data = process_data(raw_data)
        result = aggregate_data(processed_data)

        assert result["sum"] == 30

        # Verify 3 records (one for each function)
        storage = Storage()
        records = storage.list_all()
        assert len(records) == 3

    def test_configuration_driven_behavior(
        self, temp_storage_dir: str, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test behavior changes based on configuration."""
        # Test with raise_on_error=False (default)
        config1 = Config(storage_dir=temp_storage_dir, raise_on_error=False)
        set_config(config1)

        first_call = True

        @regrest
        def func() -> str:
            nonlocal first_call
            if first_call:
                first_call = False
                return "first"
            return "second"

        func()  # Record
        func()  # Should log error but not raise

        # Test with raise_on_error=True
        config2 = Config(storage_dir=temp_storage_dir, raise_on_error=True)
        set_config(config2)

        first_call = True  # Reset for new function

        @regrest
        def func2() -> str:
            nonlocal first_call
            if first_call:
                first_call = False
                return "first"
            return "second"

        func2()  # Record

        with pytest.raises(RegressionTestError):
            func2()  # Should raise

        # Restore default config
        set_config(Config())
