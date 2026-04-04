"""Unit tests for decorator module."""

import shutil
import tempfile
from collections.abc import Generator
from typing import Any

import pytest

from regrest import regrest
from regrest.config import Config, set_config
from regrest.exceptions import RegressionTestError
from regrest.storage import Storage


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


class TestBasicRecording:
    """Test basic recording and verification."""

    def test_first_call_records(self, clean_config: Config) -> None:
        """Test that first call records the result."""

        @regrest
        def add(a: int, b: int) -> int:
            return a + b

        result = add(2, 3)
        assert result == 5

        # Verify record was created
        storage = Storage()
        records = storage.find(add.__module__, "add", (2, 3), {})
        assert records is not None
        assert records.result == 5

    def test_second_call_verifies(self, clean_config: Config) -> None:
        """Test that second call verifies against recorded result."""

        @regrest
        def multiply(a: int, b: int) -> int:
            return a * b

        # First call - record
        result1 = multiply(3, 4)
        assert result1 == 12

        # Second call - verify
        result2 = multiply(3, 4)
        assert result2 == 12

    def test_different_arguments_create_different_records(
        self, clean_config: Config
    ) -> None:
        """Test that different arguments create separate records."""

        @regrest
        def square(x: int) -> int:
            return x * x

        result1 = square(2)
        result2 = square(3)

        assert result1 == 4
        assert result2 == 9

        # Verify both records exist
        storage = Storage()
        record1 = storage.find(square.__module__, "square", (2,), {})
        record2 = storage.find(square.__module__, "square", (3,), {})

        assert record1 is not None
        assert record2 is not None
        assert record1.result == 4
        assert record2.result == 9

    def test_with_kwargs(self, clean_config: Config) -> None:
        """Test decorator with keyword arguments."""

        @regrest
        def greet(name: str, greeting: str = "Hello") -> str:
            return f"{greeting}, {name}!"

        result1 = greet("Alice")
        assert result1 == "Hello, Alice!"

        result2 = greet("Bob", greeting="Hi")
        assert result2 == "Hi, Bob!"

        # Verify both records exist
        storage = Storage()
        record1 = storage.find(greet.__module__, "greet", ("Alice",), {})
        record2 = storage.find(greet.__module__, "greet", ("Bob",), {"greeting": "Hi"})

        assert record1 is not None
        assert record2 is not None


class TestUpdateMode:
    """Test update mode."""

    def test_update_mode_overwrites_record(self, clean_config: Config) -> None:
        """Test that update mode overwrites existing record."""
        call_count = 0

        @regrest(update=True)
        def changing_function() -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        # First call
        result1 = changing_function()
        assert result1 == 1

        # Second call with update mode - should overwrite
        result2 = changing_function()
        assert result2 == 2

        # Verify record has latest value
        storage = Storage()
        record = storage.find(changing_function.__module__, "changing_function", (), {})
        assert record is not None
        assert record.result == 2

    def test_config_update_mode(self, temp_storage_dir: str) -> None:
        """Test update mode via config."""
        config = Config(storage_dir=temp_storage_dir, update_mode=True)
        set_config(config)

        call_count = 0

        @regrest
        def counter() -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        result1 = counter()
        result2 = counter()

        assert result1 == 1
        assert result2 == 2

        # Verify record has latest value
        storage = Storage()
        record = storage.find(counter.__module__, "counter", (), {})
        assert record is not None
        assert record.result == 2

        # Restore default config
        set_config(Config())


class TestTolerance:
    """Test float tolerance."""

    def test_float_within_tolerance(self, clean_config: Config) -> None:
        """Test that floats within tolerance pass."""

        @regrest(tolerance=1e-9)
        def calculate() -> float:
            return 0.1 + 0.2

        # First call - record
        result1 = calculate()

        # Second call - should pass despite floating point precision
        result2 = calculate()

        assert result1 == result2

    def test_float_outside_tolerance_raises(self, clean_config: Config) -> None:
        """Test that floats outside tolerance fail."""
        first_call = True

        @regrest(tolerance=1e-10, raise_on_error=True)
        def changing_calculation() -> float:
            nonlocal first_call
            if first_call:
                first_call = False
                return 1.0
            else:
                return 1.1

        # First call - record
        result1 = changing_calculation()
        assert result1 == 1.0

        # Second call - should fail
        with pytest.raises(RegressionTestError):
            changing_calculation()


class TestErrorHandling:
    """Test error handling."""

    def test_raise_on_error_true(self, clean_config: Config) -> None:
        """Test that raise_on_error=True raises exception."""
        first_call = True

        @regrest(raise_on_error=True)
        def inconsistent_function() -> str:
            nonlocal first_call
            if first_call:
                first_call = False
                return "first"
            else:
                return "second"

        # First call - record
        result1 = inconsistent_function()
        assert result1 == "first"

        # Second call - should raise
        with pytest.raises(RegressionTestError) as exc_info:
            inconsistent_function()

        assert "Regression test failed" in str(exc_info.value)

    def test_raise_on_error_false_logs(
        self, clean_config: Config, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that raise_on_error=False logs error."""
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
            def inconsistent_function() -> str:
                nonlocal first_call
                if first_call:
                    first_call = False
                    return "first"
                else:
                    return "second"

            # First call - record
            result1 = inconsistent_function()
            assert result1 == "first"

            # Second call - should log but not raise
            result2 = inconsistent_function()
            assert result2 == "second"

            # Check that error was logged
            log_messages = " ".join(record.message for record in caplog.records)
            assert (
                "Regression test failed" in log_messages
                or "Value mismatch" in log_messages
            )
        finally:
            # Restore original propagate setting
            regrest_logger.propagate = old_propagate

    def test_config_raise_on_error(self, temp_storage_dir: str) -> None:
        """Test raise_on_error via config."""
        config = Config(storage_dir=temp_storage_dir, raise_on_error=True)
        set_config(config)

        first_call = True

        @regrest
        def inconsistent_function() -> int:
            nonlocal first_call
            if first_call:
                first_call = False
                return 100
            else:
                return 200

        # First call - record
        result1 = inconsistent_function()
        assert result1 == 100

        # Second call - should raise due to config
        with pytest.raises(RegressionTestError):
            inconsistent_function()

        # Restore default config
        set_config(Config())


class TestComplexDataTypes:
    """Test with complex data types."""

    def test_with_list(self, clean_config: Config) -> None:
        """Test with list return value."""

        @regrest
        def get_list() -> list[int]:
            return [1, 2, 3, 4, 5]

        result1 = get_list()
        result2 = get_list()

        assert result1 == result2 == [1, 2, 3, 4, 5]

    def test_with_dict(self, clean_config: Config) -> None:
        """Test with dict return value."""

        @regrest
        def get_dict() -> dict[str, Any]:
            return {"name": "Alice", "age": 30, "scores": [95, 87, 92]}

        result1 = get_dict()
        result2 = get_dict()

        assert result1 == result2

    def test_with_nested_structure(self, clean_config: Config) -> None:
        """Test with nested data structure."""

        @regrest
        def get_nested() -> dict[str, Any]:
            return {
                "users": [
                    {"name": "Alice", "scores": [95, 87, 92]},
                    {"name": "Bob", "scores": [88, 91, 85]},
                ],
                "metadata": {"version": "1.0", "count": 2},
            }

        result1 = get_nested()
        result2 = get_nested()

        assert result1 == result2

    @pytest.mark.skip(
        reason="Custom classes defined in test functions cannot be pickled"
    )
    def test_with_custom_class(self, clean_config: Config) -> None:
        """Test with custom class."""

        class Point:
            def __init__(self, x: int, y: int) -> None:
                self.x = x
                self.y = y

            def __eq__(self, other: object) -> bool:
                return (
                    isinstance(other, Point) and self.x == other.x and self.y == other.y
                )

        @regrest
        def create_point() -> Point:
            return Point(10, 20)

        result1 = create_point()
        result2 = create_point()

        assert result1 == result2


class TestDecoratorSyntax:
    """Test different decorator syntax."""

    def test_decorator_without_parens(self, clean_config: Config) -> None:
        """Test @regrest syntax (without parentheses)."""

        @regrest
        def func1() -> int:
            return 42

        result = func1()
        assert result == 42

    def test_decorator_with_parens(self, clean_config: Config) -> None:
        """Test @regrest() syntax (with parentheses)."""

        @regrest()
        def func2() -> int:
            return 42

        result = func2()
        assert result == 42

    def test_decorator_with_kwargs(self, clean_config: Config) -> None:
        """Test @regrest(tolerance=...) syntax."""

        @regrest(tolerance=1e-6)
        def func3() -> float:
            return 3.14

        result = func3()
        assert result == 3.14


class TestFunctionMetadata:
    """Test that decorator preserves function metadata."""

    def test_preserves_name(self, clean_config: Config) -> None:
        """Test that function name is preserved."""

        @regrest
        def my_function() -> int:
            """Docstring."""
            return 42

        assert my_function.__name__ == "my_function"

    def test_preserves_docstring(self, clean_config: Config) -> None:
        """Test that docstring is preserved."""

        @regrest
        def documented_function() -> int:
            """This is a test function."""
            return 42

        assert documented_function.__doc__ == "This is a test function."

    def test_preserves_module(self, clean_config: Config) -> None:
        """Test that module is preserved."""

        @regrest
        def my_function() -> int:
            return 42

        # Module name depends on how pytest is run
        assert my_function.__module__ in (
            "test_decorator",
            "tests.test_decorator",
            "tests.unit.test_decorator",
        )


class TestMultipleCalls:
    """Test multiple calls with verification."""

    def test_multiple_verifications(self, clean_config: Config) -> None:
        """Test multiple calls verify correctly."""

        @regrest
        def constant_function() -> int:
            return 100

        # First call - record
        result1 = constant_function()
        assert result1 == 100

        # Multiple verifications
        for _ in range(5):
            result = constant_function()
            assert result == 100

    def test_different_args_multiple_times(self, clean_config: Config) -> None:
        """Test calling with different args multiple times."""

        @regrest
        def add(a: int, b: int) -> int:
            return a + b

        # First set of calls - record
        assert add(1, 2) == 3
        assert add(3, 4) == 7

        # Second set of calls - verify
        assert add(1, 2) == 3
        assert add(3, 4) == 7

        # Third set - verify again
        assert add(1, 2) == 3
        assert add(3, 4) == 7
