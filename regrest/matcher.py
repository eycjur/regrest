"""Comparison logic for test results."""

import math
from typing import Any, Optional

from .config import get_config


class MatchResult:
    """Result of a match operation."""

    def __init__(self, matches: bool, message: Optional[str] = None):
        """Initialize match result.

        Args:
            matches: Whether the values match
            message: Optional message describing the mismatch
        """
        self.matches = matches
        self.message = message

    def __bool__(self) -> bool:
        """Return whether the values match."""
        return self.matches


class Matcher:
    """Compares test results."""

    def __init__(self, tolerance: Optional[float] = None):
        """Initialize matcher.

        Args:
            tolerance: Floating point comparison tolerance
        """
        self.tolerance = tolerance or get_config().float_tolerance

    def match(self, expected: Any, actual: Any, path: str = "") -> MatchResult:
        """Compare two values.

        Args:
            expected: Expected value
            actual: Actual value
            path: Current path in the value tree (for error messages)

        Returns:
            MatchResult indicating whether values match
        """
        # Type check
        if type(expected) is not type(actual):
            return MatchResult(
                False,
                f"Type mismatch at {path or 'root'}: "
                f"expected {type(expected).__name__}, "
                f"got {type(actual).__name__}",
            )

        # None
        if expected is None:
            return MatchResult(True)

        # Boolean
        if isinstance(expected, bool):
            if expected != actual:
                return MatchResult(
                    False,
                    f"Value mismatch at {path or 'root'}: "
                    f"expected {expected}, got {actual}",
                )
            return MatchResult(True)

        # Numbers
        if isinstance(expected, (int, float)):
            return self._match_number(expected, actual, path)

        # Strings
        if isinstance(expected, str):
            if expected != actual:
                return MatchResult(
                    False,
                    f"Value mismatch at {path or 'root'}: "
                    f"expected '{expected}', got '{actual}'",
                )
            return MatchResult(True)

        # Lists
        if isinstance(expected, (list, tuple)):
            return self._match_sequence(expected, actual, path)

        # Dictionaries
        if isinstance(expected, dict):
            return self._match_dict(expected, actual, path)

        # Sets
        if isinstance(expected, set):
            return self._match_set(expected, actual, path)

        # Default: use equality
        if expected != actual:
            return MatchResult(
                False,
                f"Value mismatch at {path or 'root'}: "
                f"expected {expected}, got {actual}",
            )
        return MatchResult(True)

    def _match_number(self, expected: float, actual: float, path: str) -> MatchResult:
        """Compare two numbers with tolerance.

        Args:
            expected: Expected number
            actual: Actual number
            path: Current path

        Returns:
            MatchResult
        """
        # Handle special float values
        if math.isnan(expected) and math.isnan(actual):
            return MatchResult(True)

        if math.isinf(expected) and math.isinf(actual):
            if expected == actual:  # Both +inf or both -inf
                return MatchResult(True)

        # For integers, require exact match
        if isinstance(expected, int) and isinstance(actual, int):
            if expected != actual:
                return MatchResult(
                    False,
                    f"Value mismatch at {path or 'root'}: "
                    f"expected {expected}, got {actual}",
                )
            return MatchResult(True)

        # For floats, use tolerance
        if abs(expected - actual) > self.tolerance:
            return MatchResult(
                False,
                f"Value mismatch at {path or 'root'}: "
                f"expected {expected}, got {actual} "
                f"(diff: {abs(expected - actual)}, tolerance: {self.tolerance})",
            )

        return MatchResult(True)

    def _match_sequence(self, expected: Any, actual: Any, path: str) -> MatchResult:
        """Compare two sequences (lists or tuples).

        Args:
            expected: Expected sequence
            actual: Actual sequence
            path: Current path

        Returns:
            MatchResult
        """
        if len(expected) != len(actual):
            return MatchResult(
                False,
                f"Length mismatch at {path or 'root'}: "
                f"expected {len(expected)}, got {len(actual)}",
            )

        for i, (exp_item, act_item) in enumerate(zip(expected, actual)):
            item_path = f"{path}[{i}]" if path else f"[{i}]"
            result = self.match(exp_item, act_item, item_path)
            if not result:
                return result

        return MatchResult(True)

    def _match_dict(self, expected: dict, actual: dict, path: str) -> MatchResult:
        """Compare two dictionaries.

        Args:
            expected: Expected dictionary
            actual: Actual dictionary
            path: Current path

        Returns:
            MatchResult
        """
        # Check for missing keys
        expected_keys = set(expected.keys())
        actual_keys = set(actual.keys())

        if expected_keys != actual_keys:
            missing = expected_keys - actual_keys
            extra = actual_keys - expected_keys
            msg_parts = []
            if missing:
                msg_parts.append(f"missing keys: {missing}")
            if extra:
                msg_parts.append(f"extra keys: {extra}")
            return MatchResult(
                False, f"Key mismatch at {path or 'root'}: {', '.join(msg_parts)}"
            )

        # Compare values
        for key in expected_keys:
            key_path = f"{path}.{key}" if path else str(key)
            result = self.match(expected[key], actual[key], key_path)
            if not result:
                return result

        return MatchResult(True)

    def _match_set(self, expected: set, actual: set, path: str) -> MatchResult:
        """Compare two sets.

        Args:
            expected: Expected set
            actual: Actual set
            path: Current path

        Returns:
            MatchResult
        """
        if expected != actual:
            missing = expected - actual
            extra = actual - expected
            msg_parts = []
            if missing:
                msg_parts.append(f"missing: {missing}")
            if extra:
                msg_parts.append(f"extra: {extra}")
            return MatchResult(
                False, f"Set mismatch at {path or 'root'}: {', '.join(msg_parts)}"
            )

        return MatchResult(True)
