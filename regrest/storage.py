"""Storage layer for test records."""

import base64
import hashlib
import json
import pickle
from datetime import datetime
from typing import Any, Optional

from .config import get_config


class TestRecord:
    """Represents a test record."""

    def __init__(
        self,
        module: str,
        function: str,
        args: tuple,
        kwargs: dict,
        result: Any,
        timestamp: Optional[str] = None,
        record_id: Optional[str] = None,
    ):
        """Initialize a test record.

        Args:
            module: Module name where the function is defined
            function: Function name
            args: Positional arguments
            kwargs: Keyword arguments
            result: Return value of the function
            timestamp: ISO format timestamp
            record_id: Unique identifier for this record
        """
        self.module = module
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.result = result
        self.timestamp = timestamp or datetime.now().isoformat()
        self.record_id = record_id or self._generate_id()

    def _generate_id(self) -> str:
        """Generate a unique ID based on module, function, and arguments."""
        # Serialize args and kwargs for hashing
        try:
            args_str = json.dumps(self.args, sort_keys=True, default=str)
            kwargs_str = json.dumps(self.kwargs, sort_keys=True, default=str)
        except (TypeError, ValueError):
            # Fallback to repr if JSON serialization fails
            args_str = repr(self.args)
            kwargs_str = repr(self.kwargs)

        data = f"{self.module}.{self.function}:{args_str}:{kwargs_str}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def _try_encode(self, value: Any) -> dict[str, Any]:
        """Try to encode value for JSON, fallback to pickle.

        Args:
            value: Value to encode

        Returns:
            Dict with 'type' and 'data' fields
        """
        try:
            # Try JSON serialization
            json.dumps(value)
            return {"type": "json", "data": value}
        except (TypeError, ValueError):
            # Fallback to pickle
            pickled = pickle.dumps(value)
            encoded = base64.b64encode(pickled).decode("ascii")
            return {"type": "pickle", "data": encoded}

    def _try_decode(self, encoded: dict[str, Any]) -> Any:
        """Decode value from encoded format.

        Args:
            encoded: Encoded value dict

        Returns:
            Decoded value
        """
        if isinstance(encoded, dict) and "type" in encoded:
            if encoded["type"] == "pickle":
                decoded = base64.b64decode(encoded["data"])
                return pickle.loads(decoded)
            else:  # json
                return encoded["data"]
        # Legacy format (plain value)
        return encoded

    def to_dict(self) -> dict[str, Any]:
        """Convert record to dictionary."""
        return {
            "module": self.module,
            "function": self.function,
            "args": self._try_encode(self.args),
            "kwargs": self._try_encode(self.kwargs),
            "result": self._try_encode(self.result),
            "timestamp": self.timestamp,
            "record_id": self.record_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TestRecord":
        """Create record from dictionary."""
        # Create a temporary instance to use _try_decode method
        temp = cls.__new__(cls)

        # Decode values
        args = temp._try_decode(data["args"])
        kwargs = temp._try_decode(data["kwargs"])
        result = temp._try_decode(data["result"])

        # Create actual instance with decoded values
        return cls(
            module=data["module"],
            function=data["function"],
            args=args if isinstance(args, tuple) else tuple(args),
            kwargs=kwargs,
            result=result,
            timestamp=data.get("timestamp"),
            record_id=data.get("record_id"),
        )

    def get_filename(self) -> str:
        """Get the filename for this record."""
        return f"{self.module}.{self.function}.{self.record_id}.json"


class Storage:
    """Manages storage of test records."""

    def __init__(self) -> None:
        """Initialize storage."""
        self.config = get_config()
        self.config.ensure_storage_dir()

    def save(self, record: TestRecord) -> None:
        """Save a test record.

        Args:
            record: Test record to save
        """
        filepath = self.config.storage_dir / record.get_filename()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(record.to_dict(), f, indent=2)

    def load(self, record_id: str) -> Optional[TestRecord]:
        """Load a test record by ID.

        Args:
            record_id: Record ID to load

        Returns:
            TestRecord if found, None otherwise
        """
        # Find file matching the record_id
        pattern = f"*.{record_id}.json"
        files = list(self.config.storage_dir.glob(pattern))

        if not files:
            return None

        with open(files[0], encoding="utf-8") as f:
            data = json.load(f)
            return TestRecord.from_dict(data)

    def find(
        self, module: str, function: str, args: tuple, kwargs: dict
    ) -> Optional[TestRecord]:
        """Find a test record matching the given function call.

        Args:
            module: Module name
            function: Function name
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            TestRecord if found, None otherwise
        """
        # Create a temporary record to get the ID
        temp_record = TestRecord(module, function, args, kwargs, None)
        return self.load(temp_record.record_id)

    def list_all(self) -> list[TestRecord]:
        """List all test records.

        Returns:
            List of all test records
        """
        records = []
        for filepath in self.config.storage_dir.glob("*.json"):
            try:
                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)
                    records.append(TestRecord.from_dict(data))
            except (json.JSONDecodeError, KeyError):
                # Skip invalid files
                continue
        return records

    def delete(self, record_id: str) -> bool:
        """Delete a test record by ID.

        Args:
            record_id: Record ID to delete

        Returns:
            True if deleted, False if not found
        """
        pattern = f"*.{record_id}.json"
        files = list(self.config.storage_dir.glob(pattern))

        if not files:
            return False

        for filepath in files:
            filepath.unlink()

        return True

    def delete_by_pattern(self, pattern: str) -> int:
        """Delete test records matching a pattern.

        Args:
            pattern: Pattern to match (e.g., 'mymodule.*', '*.calculate_*')

        Returns:
            Number of records deleted
        """
        deleted = 0
        for filepath in self.config.storage_dir.glob("*.json"):
            filename = filepath.stem  # Without .json extension
            if self._matches_pattern(filename, pattern):
                filepath.unlink()
                deleted += 1
        return deleted

    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """Check if filename matches the pattern.

        Args:
            filename: Filename to check
            pattern: Pattern (supports * wildcard)

        Returns:
            True if matches, False otherwise
        """
        import fnmatch

        return fnmatch.fnmatch(filename, pattern)

    def clear_all(self) -> int:
        """Delete all test records.

        Returns:
            Number of records deleted
        """
        deleted = 0
        for filepath in self.config.storage_dir.glob("*.json"):
            filepath.unlink()
            deleted += 1
        return deleted
