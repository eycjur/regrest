"""Example usage of regrest.

This example demonstrates:
1. Basic usage with @regrest decorator
2. Custom tolerance for floating-point calculations
3. Successful regression tests (results match recorded values)
4. Non-strict mode (default) - logs errors but continues execution
5. Strict mode (raise_on_error=True) - raises exceptions on test failure

Run this script twice:
- First run: Records all function outputs
- Second run: Validates outputs and demonstrates regression failures

Environment variables:
    REGREST_LOG_LEVEL=DEBUG          # Set log level (DEBUG, INFO, WARNING, ERROR)
    REGREST_RAISE_ON_ERROR=true      # Raise exceptions on test failure
    REGREST_UPDATE_MODE=true         # Update all records
    REGREST_STORAGE_DIR=.my_records  # Custom storage directory
    REGREST_FLOAT_TOLERANCE=1e-6     # Float comparison tolerance

Examples:
    # Run with debug logging
    REGREST_LOG_LEVEL=DEBUG python example.py

    # Update all records
    REGREST_UPDATE_MODE=1 python example.py

    # Strict mode (raise on error)
    REGREST_RAISE_ON_ERROR=true python example.py
"""

from regrest import regrest


@regrest
def calculate_price(items, discount=0):
    """Calculate total price with discount."""
    total = sum(item["price"] for item in items)
    return total * (1 - discount)


@regrest
def process_data(data):
    """Process data and return statistics."""
    return {
        "mean": sum(data) / len(data),
        "max": max(data),
        "min": min(data),
        "count": len(data),
    }


@regrest(tolerance=1e-10)
def calculate_pi():
    """Calculate pi approximation."""
    # Using Leibniz formula
    pi = 0
    for i in range(1000000):
        pi += ((-1) ** i) / (2 * i + 1)
    return 4 * pi


# Variable to demonstrate regression test failure
_calculation_version = 1


@regrest
def calculate_sum(numbers):
    """Calculate sum of numbers.

    This function uses raise_on_error=True to raise exceptions on test failure.
    This function's behavior changes based on _calculation_version
    to demonstrate regression test failure.
    """
    if _calculation_version == 1:
        return sum(numbers)
    else:
        # Changed behavior - will cause regression test to fail
        return sum(numbers) * 2


@regrest
def calculate_product(numbers):
    """Calculate product of numbers.

    This function uses default raise_on_error (False), so test failures
    will be logged as errors instead of raising exceptions.
    """
    result = 1
    for n in numbers:
        result *= n
    return result


def main():
    """Run examples."""
    print("=== Regrest Example ===\n")

    # Example 1: Simple calculation
    print("Example 1: Calculate price")
    items = [{"price": 100}, {"price": 200}, {"price": 300}]
    result = calculate_price(items, discount=0.1)
    print(f"Result: {result}\n")

    # Example 2: Data processing
    print("Example 2: Process data")
    data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    stats = process_data(data)
    print(f"Result: {stats}\n")

    # Example 2-1: Demonstrate regression test failure
    print("Example 2-1: Process data with changed behavior (to demonstrate failure)")
    # Changing data to trigger regression test failure
    data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 11]  # Changed last element from 10 to 11
    stats = process_data(data)
    print(f"Result: {stats}\n")

    # Example 3: High precision calculation
    print("Example 3: Calculate pi")
    pi = calculate_pi()
    print(f"Result: {pi}\n")

    # Example 4: Successful test (first run records, second run passes)
    print("Example 4: Calculate sum (should pass)")
    numbers = [1, 2, 3, 4, 5]
    result = calculate_sum(numbers)
    print(f"Result: {result}\n")

    # Example 5: Non-strict mode (default behavior - logs error but continues)
    print("Example 5: Non-strict mode (default)")
    print("First call: records the result")
    result = calculate_product([2, 3, 4])
    print(f"Result: {result}")
    print("Second call: if it fails, logs error but continues execution")
    # On second run, if you change the implementation, it will log an error
    # but won't raise an exception (default behavior)
    result = calculate_product([2, 3, 4])
    print(f"Result: {result}\n")

    # Example 6: Strict mode (raise_on_error=True - raises exception on failure)
    print("Example 6: Strict mode (raise_on_error=True)")
    print("Changing function behavior to trigger regression test failure...")
    global _calculation_version
    _calculation_version = 2  # Change behavior
    result = calculate_sum(
        numbers
    )  # Same arguments, but different behavior - will raise exception

    print("=== All examples completed ===")


if __name__ == "__main__":
    main()
