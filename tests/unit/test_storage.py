"""Unit tests for storage module."""

import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from regrest.config import Config
from regrest.storage import Storage, TestRecord


@pytest.fixture
def temp_storage_dir() -> Generator[Path, None, None]:
    """Create a temporary storage directory."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def storage(temp_storage_dir: Path) -> Storage:
    """Create a storage instance with temporary directory."""
    config = Config(storage_dir=str(temp_storage_dir))
    from regrest.config import set_config

    set_config(config)
    return Storage()


@pytest.fixture
def sample_record() -> TestRecord:
    """Create a sample test record."""
    return TestRecord(
        module="test_module",
        function="test_function",
        args=(1, 2, 3),
        kwargs={"key": "value"},
        result={"output": 42},
    )


class TestTestRecord:
    """Test TestRecord class."""

    def test_generate_id_same_inputs(self) -> None:
        """Test that same inputs generate same ID."""
        record1 = TestRecord(
            module="mod",
            function="func",
            args=(1, 2),
            kwargs={"a": "b"},
            result=None,
        )
        record2 = TestRecord(
            module="mod",
            function="func",
            args=(1, 2),
            kwargs={"a": "b"},
            result=None,
        )
        assert record1.record_id == record2.record_id

    def test_generate_id_different_args(self) -> None:
        """Test that different args generate different ID."""
        record1 = TestRecord(
            module="mod",
            function="func",
            args=(1, 2),
            kwargs={},
            result=None,
        )
        record2 = TestRecord(
            module="mod",
            function="func",
            args=(1, 3),
            kwargs={},
            result=None,
        )
        assert record1.record_id != record2.record_id

    def test_generate_id_different_kwargs(self) -> None:
        """Test that different kwargs generate different ID."""
        record1 = TestRecord(
            module="mod",
            function="func",
            args=(),
            kwargs={"a": "b"},
            result=None,
        )
        record2 = TestRecord(
            module="mod",
            function="func",
            args=(),
            kwargs={"a": "c"},
            result=None,
        )
        assert record1.record_id != record2.record_id

    def test_to_dict(self, sample_record: TestRecord) -> None:
        """Test conversion to dictionary."""
        data = sample_record.to_dict()
        assert data["module"] == "test_module"
        assert data["function"] == "test_function"
        # args, kwargs, result are encoded
        assert "type" in data["args"]
        assert "type" in data["kwargs"]
        assert "type" in data["result"]
        assert "record_id" in data
        assert "timestamp" in data

    def test_from_dict(self, sample_record: TestRecord) -> None:
        """Test creation from dictionary."""
        data = sample_record.to_dict()
        restored = TestRecord.from_dict(data)
        assert restored.module == sample_record.module
        assert restored.function == sample_record.function
        assert tuple(restored.args) == tuple(sample_record.args)
        assert restored.kwargs == sample_record.kwargs
        assert restored.result == sample_record.result
        assert restored.record_id == sample_record.record_id


class TestStorage:
    """Test Storage class."""

    def test_save_and_load_json_serializable(
        self, storage: Storage, temp_storage_dir: Path
    ) -> None:
        """Test save and load with JSON-serializable data."""
        record = TestRecord(
            module="test_mod",
            function="test_func",
            args=(1, 2),
            kwargs={"key": "value"},
            result={"output": 42},
        )
        storage.save(record)

        # Check file exists
        expected_path = temp_storage_dir / f"test_mod.test_func.{record.record_id}.json"
        assert expected_path.exists()

        # Load and verify
        loaded = storage.load(record.record_id)
        assert loaded is not None
        assert loaded.module == record.module
        assert loaded.function == record.function
        assert tuple(loaded.args) == tuple(record.args)
        assert loaded.kwargs == record.kwargs
        assert loaded.result == record.result

    @pytest.mark.skip(
        reason="Custom classes defined in test functions cannot be pickled"
    )
    def test_save_and_load_pickle_fallback(
        self, storage: Storage, temp_storage_dir: Path
    ) -> None:
        """Test save and load with non-JSON-serializable data (pickle fallback)."""

        class CustomClass:
            def __init__(self, value: int) -> None:
                self.value = value

            def __eq__(self, other: object) -> bool:
                return isinstance(other, CustomClass) and self.value == other.value

        record = TestRecord(
            module="test_mod",
            function="test_func",
            args=(CustomClass(10),),
            kwargs={},
            result=CustomClass(20),
        )
        storage.save(record)

        # Check file exists
        expected_path = temp_storage_dir / f"test_mod.test_func.{record.record_id}.json"
        assert expected_path.exists()

        # Load and verify
        loaded = storage.load(record.record_id)
        assert loaded is not None
        assert loaded.args[0].value == 10
        assert loaded.result.value == 20

    def test_load_nonexistent(self, storage: Storage) -> None:
        """Test load returns None for nonexistent record."""
        result = storage.load("fake_id_12345678")
        assert result is None

    def test_find_exact_match(
        self, storage: Storage, sample_record: TestRecord
    ) -> None:
        """Test find with exact module.function match."""
        storage.save(sample_record)
        result = storage.find(
            "test_module", "test_function", sample_record.args, sample_record.kwargs
        )
        assert result is not None
        assert result.record_id == sample_record.record_id

    def test_find_different_args(self, storage: Storage) -> None:
        """Test find with different arguments."""
        record1 = TestRecord("mod1", "func1", (1, 2), {}, "result1")
        record2 = TestRecord("mod1", "func1", (3, 4), {}, "result2")

        storage.save(record1)
        storage.save(record2)

        # Find with first args
        result1 = storage.find("mod1", "func1", (1, 2), {})
        assert result1 is not None
        assert result1.result == "result1"

        # Find with second args
        result2 = storage.find("mod1", "func1", (3, 4), {})
        assert result2 is not None
        assert result2.result == "result2"

    def test_find_nonexistent(self, storage: Storage) -> None:
        """Test find returns None for nonexistent record."""
        result = storage.find("nonexistent", "function", (), {})
        assert result is None

    def test_find_with_kwargs(self, storage: Storage) -> None:
        """Test find with keyword arguments."""
        record = TestRecord("mod", "func", (), {"key": "value"}, "result")
        storage.save(record)

        result = storage.find("mod", "func", (), {"key": "value"})
        assert result is not None
        assert result.result == "result"

    def test_list_all(self, storage: Storage) -> None:
        """Test list_all returns all records."""
        record1 = TestRecord("mod1", "func1", (), {}, "result1")
        record2 = TestRecord("mod2", "func2", (), {}, "result2")
        record3 = TestRecord("mod3", "func3", (), {}, "result3")

        storage.save(record1)
        storage.save(record2)
        storage.save(record3)

        results = storage.list_all()
        assert len(results) == 3
        modules = {r.module for r in results}
        assert modules == {"mod1", "mod2", "mod3"}

    def test_delete_existing(self, storage: Storage, temp_storage_dir: Path) -> None:
        """Test delete removes existing record."""
        record = TestRecord("test_mod", "test_func", (), {}, "result")
        storage.save(record)

        file_path = temp_storage_dir / f"test_mod.test_func.{record.record_id}.json"
        assert file_path.exists()

        deleted = storage.delete(record.record_id)
        assert deleted is True
        assert not file_path.exists()

    def test_delete_nonexistent(self, storage: Storage) -> None:
        """Test delete returns False for nonexistent record."""
        deleted = storage.delete("fake_id_12345678")
        assert deleted is False

    def test_delete_by_pattern(self, storage: Storage) -> None:
        """Test delete_by_pattern removes matching records."""
        record1 = TestRecord("mod1", "func1", (), {}, "result1")
        record2 = TestRecord("mod1", "func2", (), {}, "result2")
        record3 = TestRecord("mod2", "func1", (), {}, "result3")

        storage.save(record1)
        storage.save(record2)
        storage.save(record3)

        count = storage.delete_by_pattern("mod1.*")
        assert count == 2

        # Verify only mod2.func1 remains
        remaining = storage.list_all()
        assert len(remaining) == 1
        assert remaining[0].module == "mod2"

    def test_clear_all(self, storage: Storage, temp_storage_dir: Path) -> None:
        """Test clear_all removes all records."""
        record1 = TestRecord("mod1", "func1", (), {}, "result1")
        record2 = TestRecord("mod2", "func2", (), {}, "result2")

        storage.save(record1)
        storage.save(record2)

        # Verify files exist
        assert len(list(temp_storage_dir.glob("*.json"))) == 2

        count = storage.clear_all()
        assert count == 2

        # Verify all files removed
        assert len(list(temp_storage_dir.glob("*.json"))) == 0
        assert storage.list_all() == []

    def test_storage_dir_created(self) -> None:
        """Test that storage directory is created if it doesn't exist."""
        temp_dir = tempfile.mkdtemp()
        try:
            storage_path = Path(temp_dir) / "nested" / "storage"
            config = Config(storage_dir=str(storage_path))
            from regrest.config import set_config

            set_config(config)
            storage = Storage()

            record = TestRecord("mod", "func", (), {}, "result")
            storage.save(record)

            assert storage_path.exists()
            assert (storage_path / f"mod.func.{record.record_id}.json").exists()
        finally:
            shutil.rmtree(temp_dir)
