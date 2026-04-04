"""Unit tests for server module."""

import json
import shutil
import tempfile
from collections.abc import Generator
from typing import Any, Union

import pytest

from regrest.config import Config
from regrest.server import _serialize_value
from regrest.storage import Storage, TestRecord

# Try to import Flask for Flask-specific tests
try:
    from flask import Flask

    from regrest.server import _create_flask_app

    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False


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


class TestSerializeValue:
    """Test _serialize_value function."""

    def test_serialize_none(self) -> None:
        """Test serializing None."""
        result = _serialize_value(None)
        assert result is None

    def test_serialize_bool(self) -> None:
        """Test serializing boolean."""
        assert _serialize_value(True) is True
        assert _serialize_value(False) is False

    def test_serialize_int(self) -> None:
        """Test serializing integer."""
        assert _serialize_value(42) == 42

    def test_serialize_float(self) -> None:
        """Test serializing float."""
        assert _serialize_value(3.14) == 3.14

    def test_serialize_string(self) -> None:
        """Test serializing string."""
        assert _serialize_value("hello") == "hello"

    def test_serialize_list(self) -> None:
        """Test serializing list."""
        result = _serialize_value([1, 2, 3])
        assert result == [1, 2, 3]

    def test_serialize_tuple(self) -> None:
        """Test serializing tuple."""
        result = _serialize_value((1, 2, 3))
        assert result == [1, 2, 3]

    def test_serialize_dict(self) -> None:
        """Test serializing dictionary."""
        result = _serialize_value({"a": 1, "b": 2})
        assert result == {"a": 1, "b": 2}

    def test_serialize_set(self) -> None:
        """Test serializing set."""
        result = _serialize_value({1, 2, 3})
        assert isinstance(result, list)
        assert set(result) == {1, 2, 3}

    def test_serialize_nested_list(self) -> None:
        """Test serializing nested list."""
        result = _serialize_value([[1, 2], [3, 4]])
        assert result == [[1, 2], [3, 4]]

    def test_serialize_nested_dict(self) -> None:
        """Test serializing nested dictionary."""
        result = _serialize_value({"user": {"name": "Alice", "age": 30}})
        assert result == {"user": {"name": "Alice", "age": 30}}

    def test_serialize_custom_class(self) -> None:
        """Test serializing custom class."""

        class Point:
            def __init__(self, x: int, y: int) -> None:
                self.x = x
                self.y = y

        point = Point(10, 20)
        result = _serialize_value(point)

        assert isinstance(result, dict)
        assert result["__class__"] == "Point"
        assert result["__module__"] in [
            "test_server",
            "tests.test_server",
            "tests.unit.test_server",
        ]
        assert result["x"] == 10
        assert result["y"] == 20

    def test_serialize_nested_custom_class(self) -> None:
        """Test serializing nested custom classes."""

        class Address:
            def __init__(self, city: str) -> None:
                self.city = city

        class Person:
            def __init__(self, name: str, address: Address) -> None:
                self.name = name
                self.address = address

        person = Person("Alice", Address("Tokyo"))
        result = _serialize_value(person)

        assert result["__class__"] == "Person"
        assert result["name"] == "Alice"
        assert result["address"]["__class__"] == "Address"
        assert result["address"]["city"] == "Tokyo"

    def test_serialize_max_depth(self) -> None:
        """Test max depth protection."""

        # Create deeply nested structure
        def create_nested(depth: int) -> Union[str, dict[str, Any]]:
            if depth == 0:
                return "leaf"
            return {"nested": create_nested(depth - 1)}

        deep = create_nested(15)
        result = _serialize_value(deep, max_depth=10)

        # Should reach max depth and return error string
        def check_depth(obj: Any, current: int = 0) -> int:
            if isinstance(obj, str) and obj.startswith("<max depth reached"):
                return current
            if isinstance(obj, dict) and "nested" in obj:
                return check_depth(obj["nested"], current + 1)
            return current

        # Should hit max depth
        assert "<max depth reached" in str(result)

    def test_serialize_complex_structure(self) -> None:
        """Test serializing complex structure."""
        data = {
            "users": [
                {"name": "Alice", "scores": [95, 87, 92]},
                {"name": "Bob", "scores": [88, 91, 85]},
            ],
            "metadata": {"version": "1.0", "count": 2},
        }

        result = _serialize_value(data)
        assert result == data


@pytest.mark.skipif(not HAS_FLASK, reason="Flask not installed")
class TestFlaskApp:
    """Test Flask application (requires Flask)."""

    def test_create_flask_app(self, temp_storage_dir: str) -> None:
        """Test creating Flask app."""
        app = _create_flask_app(temp_storage_dir)
        assert isinstance(app, Flask)
        assert "storage" in app.config

    def test_index_route(self, populated_storage: tuple[str, Storage]) -> None:
        """Test index route."""
        storage_dir, _ = populated_storage
        app = _create_flask_app(storage_dir)
        client = app.test_client()

        response = client.get("/")
        assert response.status_code == 200
        assert b"html" in response.data or b"HTML" in response.data

    def test_api_records_route(self, populated_storage: tuple[str, Storage]) -> None:
        """Test /api/records route."""
        storage_dir, _ = populated_storage
        app = _create_flask_app(storage_dir)
        client = app.test_client()

        response = client.get("/api/records")
        assert response.status_code == 200

        data = json.loads(response.data)
        # Should be a list or dict with "records" key
        if isinstance(data, list):
            assert len(data) == 3
        else:
            assert "records" in data
            assert len(data["records"]) == 3

    def test_api_stats_route(self, populated_storage: tuple[str, Storage]) -> None:
        """Test /api/stats route."""
        storage_dir, _ = populated_storage
        app = _create_flask_app(storage_dir)
        client = app.test_client()

        response = client.get("/api/stats")
        assert response.status_code == 200

        stats = json.loads(response.data)
        assert stats["total_records"] == 3
        assert stats["total_modules"] == 2
        assert "by_module" in stats
        assert "by_function" in stats

    def test_delete_record_route(self, populated_storage: tuple[str, Storage]) -> None:
        """Test DELETE /api/records/<record_id> route."""
        storage_dir, storage = populated_storage
        app = _create_flask_app(storage_dir)
        client = app.test_client()

        # Get a record ID
        records = storage.list_all()
        record_id = records[0].record_id

        # Delete the record
        response = client.delete(f"/api/records/{record_id}")
        assert response.status_code == 200

        result = json.loads(response.data)
        assert result["success"] is True

        # Verify record was deleted
        remaining = storage.list_all()
        assert len(remaining) == 2

    def test_delete_nonexistent_record(
        self, populated_storage: tuple[str, Storage]
    ) -> None:
        """Test deleting nonexistent record."""
        storage_dir, _ = populated_storage
        app = _create_flask_app(storage_dir)
        client = app.test_client()

        response = client.delete("/api/records/nonexistent_id")
        assert response.status_code == 404

    def test_delete_all_records_route(
        self, populated_storage: tuple[str, Storage]
    ) -> None:
        """Test DELETE /api/records route."""
        storage_dir, storage = populated_storage
        app = _create_flask_app(storage_dir)
        client = app.test_client()

        response = client.delete("/api/records")
        assert response.status_code == 200

        result = json.loads(response.data)
        assert result["success"] is True
        assert result["count"] == 3

        # Verify all records were deleted
        remaining = storage.list_all()
        assert len(remaining) == 0

    def test_api_records_empty(self, temp_storage_dir: str) -> None:
        """Test /api/records with no records."""
        app = _create_flask_app(temp_storage_dir)
        client = app.test_client()

        response = client.get("/api/records")
        assert response.status_code == 200

        data = json.loads(response.data)
        if isinstance(data, list):
            assert len(data) == 0
        else:
            assert len(data.get("records", [])) == 0

    def test_api_stats_empty(self, temp_storage_dir: str) -> None:
        """Test /api/stats with no records."""
        app = _create_flask_app(temp_storage_dir)
        client = app.test_client()

        response = client.get("/api/stats")
        assert response.status_code == 200

        stats = json.loads(response.data)
        assert stats["total_records"] == 0
        assert stats["total_modules"] == 0
        assert stats["total_functions"] == 0


class TestServerIntegration:
    """Integration tests for server."""

    @pytest.mark.skip(
        reason="Custom classes defined in test functions cannot be pickled"
    )
    def test_server_can_load_records_with_custom_classes(
        self, temp_storage_dir: str
    ) -> None:
        """Test server can serialize records with custom classes."""

        class CustomClass:
            def __init__(self, value: int) -> None:
                self.value = value

        config = Config(storage_dir=temp_storage_dir)
        from regrest.config import set_config

        set_config(config)
        storage = Storage()

        record = TestRecord(
            "test_module", "test_func", (CustomClass(42),), {}, CustomClass(100)
        )
        storage.save(record)

        # Serialize the args and result
        serialized_args = _serialize_value(record.args)
        serialized_result = _serialize_value(record.result)

        assert serialized_args[0]["__class__"] == "CustomClass"
        assert serialized_args[0]["value"] == 42
        assert serialized_result["__class__"] == "CustomClass"
        assert serialized_result["value"] == 100

    @pytest.mark.skipif(not HAS_FLASK, reason="Flask not installed")
    def test_flask_app_handles_record_with_custom_class(
        self, temp_storage_dir: str
    ) -> None:
        """Test Flask app can handle records with custom classes."""

        class Point:
            def __init__(self, x: int, y: int) -> None:
                self.x = x
                self.y = y

        config = Config(storage_dir=temp_storage_dir)
        from regrest.config import set_config

        set_config(config)
        storage = Storage()

        record = TestRecord("test_module", "test_func", (Point(1, 2),), {}, Point(3, 4))
        storage.save(record)

        app = _create_flask_app(temp_storage_dir)
        client = app.test_client()

        response = client.get("/api/records")
        assert response.status_code == 200

        data = json.loads(response.data)
        if isinstance(data, list):
            records = data
        else:
            records = data["records"]

        assert len(records) == 1
        record_data = records[0]

        # Check args serialization
        assert record_data["args"][0]["__class__"] == "Point"
        assert record_data["args"][0]["x"] == 1
        assert record_data["args"][0]["y"] == 2

        # Check result serialization
        assert record_data["result"]["__class__"] == "Point"
        assert record_data["result"]["x"] == 3
        assert record_data["result"]["y"] == 4
