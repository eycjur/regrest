"""Test regrest with custom classes."""

from regrest import regrest


class Point:
    """Simple point class without __eq__.

    WARNING: This will NOT work correctly with regrest!
    Without __eq__, comparison uses object identity.
    """

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __repr__(self):
        return f"Point({self.x}, {self.y})"


class PointWithEq:
    """Point class with __eq__ defined.

    This WILL work correctly with regrest.
    The class is pickle-serializable and has __eq__ for comparison.
    """

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __eq__(self, other):
        if not isinstance(other, PointWithEq):
            return False
        return self.x == other.x and self.y == other.y

    def __repr__(self):
        return f"PointWithEq({self.x}, {self.y})"


@regrest
def calculate_midpoint_dict(p1, p2):
    """Return dict - should work fine."""
    return {
        "x": (p1["x"] + p2["x"]) / 2,
        "y": (p1["y"] + p2["y"]) / 2,
    }


@regrest
def calculate_midpoint_class(p1, p2):
    """Return custom class - will this work?"""
    return PointWithEq(
        (p1.x + p2.x) / 2,
        (p1.y + p2.y) / 2,
    )


def test_dict_version():
    """Test with dict - should work."""
    result = calculate_midpoint_dict({"x": 0, "y": 0}, {"x": 10, "y": 10})
    assert result == {"x": 5.0, "y": 5.0}


def test_class_version():
    """Test with custom class - should work with pickle."""
    p1 = PointWithEq(0, 0)
    p2 = PointWithEq(10, 10)
    result = calculate_midpoint_class(p1, p2)
    assert result == PointWithEq(5.0, 5.0)
