"""Unit tests for matcher module."""

import math

from regrest.matcher import Matcher, MatchResult


class TestMatchResult:
    """Test MatchResult class."""

    def test_success_result(self) -> None:
        """Test creating a success result."""
        result = MatchResult(matches=True)
        assert result.matches is True
        assert result.message is None

    def test_failure_result(self) -> None:
        """Test creating a failure result."""
        result = MatchResult(matches=False, message="Values don't match")
        assert result.matches is False
        assert result.message == "Values don't match"


class TestMatcherPrimitives:
    """Test Matcher with primitive types."""

    def test_match_int_equal(self) -> None:
        """Test matching equal integers."""
        matcher = Matcher()
        result = matcher.match(42, 42)
        assert result.matches is True

    def test_match_int_not_equal(self) -> None:
        """Test matching unequal integers."""
        matcher = Matcher()
        result = matcher.match(42, 43)
        assert result.matches is False
        assert result.message is not None
        assert "42" in result.message
        assert "43" in result.message

    def test_match_float_within_tolerance(self) -> None:
        """Test matching floats within tolerance."""
        matcher = Matcher(tolerance=1e-9)
        result = matcher.match(0.3, 0.1 + 0.2)
        assert result.matches is True

    def test_match_float_outside_tolerance(self) -> None:
        """Test matching floats outside tolerance."""
        matcher = Matcher(tolerance=1e-10)
        result = matcher.match(1.0, 1.1)
        assert result.matches is False

    def test_match_float_infinity(self) -> None:
        """Test matching infinity."""
        matcher = Matcher()
        result = matcher.match(math.inf, math.inf)
        assert result.matches is True

        result = matcher.match(-math.inf, -math.inf)
        assert result.matches is True

        result = matcher.match(math.inf, -math.inf)
        assert result.matches is False

    def test_match_float_nan(self) -> None:
        """Test matching NaN (both NaN should match)."""
        matcher = Matcher()
        result = matcher.match(math.nan, math.nan)
        assert result.matches is True

    def test_match_string_equal(self) -> None:
        """Test matching equal strings."""
        matcher = Matcher()
        result = matcher.match("hello", "hello")
        assert result.matches is True

    def test_match_string_not_equal(self) -> None:
        """Test matching unequal strings."""
        matcher = Matcher()
        result = matcher.match("hello", "world")
        assert result.matches is False

    def test_match_bool_equal(self) -> None:
        """Test matching equal booleans."""
        matcher = Matcher()
        result = matcher.match(True, True)
        assert result.matches is True
        result = matcher.match(False, False)
        assert result.matches is True

    def test_match_bool_not_equal(self) -> None:
        """Test matching unequal booleans."""
        matcher = Matcher()
        result = matcher.match(True, False)
        assert result.matches is False

    def test_match_none(self) -> None:
        """Test matching None."""
        matcher = Matcher()
        result = matcher.match(None, None)
        assert result.matches is True

    def test_match_none_vs_value(self) -> None:
        """Test matching None vs other value."""
        matcher = Matcher()
        result = matcher.match(None, 42)
        assert result.matches is False


class TestMatcherTypeChecking:
    """Test Matcher type checking."""

    def test_type_mismatch_int_float(self) -> None:
        """Test type mismatch between int and float."""
        matcher = Matcher()
        result = matcher.match(1, 1.0)
        assert result.matches is False
        assert result.message is not None
        assert "type" in result.message.lower()

    def test_type_mismatch_str_int(self) -> None:
        """Test type mismatch between str and int."""
        matcher = Matcher()
        result = matcher.match("42", 42)
        assert result.matches is False
        assert result.message is not None
        assert "type" in result.message.lower()

    def test_type_mismatch_list_tuple(self) -> None:
        """Test type mismatch between list and tuple."""
        matcher = Matcher()
        result = matcher.match([1, 2, 3], (1, 2, 3))
        assert result.matches is False
        assert result.message is not None
        assert "type" in result.message.lower()


class TestMatcherSequences:
    """Test Matcher with sequences (list, tuple)."""

    def test_match_list_equal(self) -> None:
        """Test matching equal lists."""
        matcher = Matcher()
        result = matcher.match([1, 2, 3], [1, 2, 3])
        assert result.matches is True

    def test_match_list_different_length(self) -> None:
        """Test matching lists with different lengths."""
        matcher = Matcher()
        result = matcher.match([1, 2], [1, 2, 3])
        assert result.matches is False
        assert result.message is not None
        assert "length" in result.message.lower()

    def test_match_list_different_element(self) -> None:
        """Test matching lists with different elements."""
        matcher = Matcher()
        result = matcher.match([1, 2, 3], [1, 2, 4])
        assert result.matches is False
        assert result.message is not None
        assert "[2]" in result.message

    def test_match_tuple_equal(self) -> None:
        """Test matching equal tuples."""
        matcher = Matcher()
        result = matcher.match((1, 2, 3), (1, 2, 3))
        assert result.matches is True

    def test_match_nested_list(self) -> None:
        """Test matching nested lists."""
        matcher = Matcher()
        result = matcher.match([[1, 2], [3, 4]], [[1, 2], [3, 4]])
        assert result.matches is True

        result = matcher.match([[1, 2], [3, 4]], [[1, 2], [3, 5]])
        assert result.matches is False


class TestMatcherDict:
    """Test Matcher with dictionaries."""

    def test_match_dict_equal(self) -> None:
        """Test matching equal dictionaries."""
        matcher = Matcher()
        result = matcher.match({"a": 1, "b": 2}, {"a": 1, "b": 2})
        assert result.matches is True

    def test_match_dict_missing_key(self) -> None:
        """Test matching dicts with missing key."""
        matcher = Matcher()
        result = matcher.match({"a": 1, "b": 2}, {"a": 1})
        assert result.matches is False
        assert result.message is not None
        assert "key" in result.message.lower()

    def test_match_dict_extra_key(self) -> None:
        """Test matching dicts with extra key."""
        matcher = Matcher()
        result = matcher.match({"a": 1}, {"a": 1, "b": 2})
        assert result.matches is False
        assert result.message is not None
        assert "key" in result.message.lower()

    def test_match_dict_different_value(self) -> None:
        """Test matching dicts with different value."""
        matcher = Matcher()
        result = matcher.match({"a": 1, "b": 2}, {"a": 1, "b": 3})
        assert result.matches is False
        assert result.message is not None
        # Message format is like "Value mismatch at b: ..."
        assert "b" in result.message

    def test_match_nested_dict(self) -> None:
        """Test matching nested dictionaries."""
        matcher = Matcher()
        dict1 = {"user": {"name": "Alice", "age": 30}}
        dict2 = {"user": {"name": "Alice", "age": 30}}
        result = matcher.match(dict1, dict2)
        assert result.matches is True

        dict3 = {"user": {"name": "Alice", "age": 31}}
        result = matcher.match(dict1, dict3)
        assert result.matches is False
        assert result.message is not None
        # Message format is like "Value mismatch at user.age: ..."
        assert "age" in result.message


class TestMatcherSet:
    """Test Matcher with sets."""

    def test_match_set_equal(self) -> None:
        """Test matching equal sets."""
        matcher = Matcher()
        result = matcher.match({1, 2, 3}, {1, 2, 3})
        assert result.matches is True

    def test_match_set_different_size(self) -> None:
        """Test matching sets with different sizes."""
        matcher = Matcher()
        result = matcher.match({1, 2}, {1, 2, 3})
        assert result.matches is False
        assert result.message is not None
        # Message contains info about set difference
        assert (
            "set" in result.message.lower()
            or "extra" in result.message.lower()
            or "missing" in result.message.lower()
        )

    def test_match_set_missing_element(self) -> None:
        """Test matching sets with missing element."""
        matcher = Matcher()
        result = matcher.match({1, 2, 3}, {1, 2, 4})
        assert result.matches is False
        assert result.message is not None
        assert "missing" in result.message.lower() or "extra" in result.message.lower()


class TestMatcherCustomObjects:
    """Test Matcher with custom objects."""

    def test_match_object_with_eq(self) -> None:
        """Test matching objects with __eq__ defined."""

        class Point:
            def __init__(self, x: int, y: int) -> None:
                self.x = x
                self.y = y

            def __eq__(self, other: object) -> bool:
                return (
                    isinstance(other, Point) and self.x == other.x and self.y == other.y
                )

        matcher = Matcher()
        result = matcher.match(Point(1, 2), Point(1, 2))
        assert result.matches is True

        result = matcher.match(Point(1, 2), Point(1, 3))
        assert result.matches is False

    def test_match_object_with_dict(self) -> None:
        """Test matching objects using __dict__."""

        class Person:
            def __init__(self, name: str, age: int) -> None:
                self.name = name
                self.age = age

        matcher = Matcher()
        result = matcher.match(Person("Alice", 30), Person("Alice", 30))
        assert result.matches is True

        result = matcher.match(Person("Alice", 30), Person("Bob", 30))
        assert result.matches is False

    def test_match_object_nested(self) -> None:
        """Test matching nested custom objects."""

        class Address:
            def __init__(self, city: str, country: str) -> None:
                self.city = city
                self.country = country

        class Person:
            def __init__(self, name: str, address: Address) -> None:
                self.name = name
                self.address = address

        matcher = Matcher()
        p1 = Person("Alice", Address("Tokyo", "Japan"))
        p2 = Person("Alice", Address("Tokyo", "Japan"))
        result = matcher.match(p1, p2)
        assert result.matches is True

        p3 = Person("Alice", Address("Osaka", "Japan"))
        result = matcher.match(p1, p3)
        assert result.matches is False

    def test_match_object_type_mismatch(self) -> None:
        """Test type mismatch with custom objects."""

        class Point2D:
            def __init__(self, x: int, y: int) -> None:
                self.x = x
                self.y = y

        class Point3D:
            def __init__(self, x: int, y: int, z: int) -> None:
                self.x = x
                self.y = y
                self.z = z

        matcher = Matcher()
        result = matcher.match(Point2D(1, 2), Point3D(1, 2, 3))
        assert result.matches is False
        assert result.message is not None
        assert "type" in result.message.lower()


class TestMatcherComplexStructures:
    """Test Matcher with complex nested structures."""

    def test_match_complex_nested(self) -> None:
        """Test matching complex nested structure."""
        matcher = Matcher()

        data1 = {
            "users": [
                {"name": "Alice", "scores": [95, 87, 92]},
                {"name": "Bob", "scores": [88, 91, 85]},
            ],
            "metadata": {"version": "1.0", "count": 2},
        }

        data2 = {
            "users": [
                {"name": "Alice", "scores": [95, 87, 92]},
                {"name": "Bob", "scores": [88, 91, 85]},
            ],
            "metadata": {"version": "1.0", "count": 2},
        }

        result = matcher.match(data1, data2)
        assert result.matches is True

        # Change nested value
        data3 = {
            "users": [
                {"name": "Alice", "scores": [95, 87, 92]},
                {"name": "Bob", "scores": [88, 91, 99]},  # Changed
            ],
            "metadata": {"version": "1.0", "count": 2},
        }

        result = matcher.match(data1, data3)
        assert result.matches is False
        assert result.message is not None
        # Message shows the path to the mismatch
        assert "scores" in result.message

    def test_match_with_custom_tolerance(self) -> None:
        """Test matching with custom tolerance."""
        matcher = Matcher(tolerance=0.1)

        data1 = {"value": 1.0, "measurements": [1.0, 2.0, 3.0]}
        data2 = {"value": 1.05, "measurements": [1.02, 2.03, 3.01]}

        result = matcher.match(data1, data2)
        assert result.matches is True

        # Outside tolerance
        data3 = {"value": 1.2, "measurements": [1.0, 2.0, 3.0]}
        result = matcher.match(data1, data3)
        assert result.matches is False
