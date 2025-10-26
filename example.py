"""Example usage of regrest.

Run this script twice:
- First run: Records function outputs
- Second run: Validates outputs against recorded values

Environment variables:
    REGREST_LOG_LEVEL=DEBUG          # Set log level
    REGREST_UPDATE_MODE=1            # Update all records
    REGREST_RAISE_ON_ERROR=true      # Raise exceptions on test failure
"""

from dataclasses import dataclass

from regrest import regrest


# Example 1: Basic usage with dict
@regrest
def process_data(data):
    """Process data and return statistics."""
    return {
        "mean": sum(data) / len(data),
        "max": max(data),
        "min": min(data),
        "count": len(data),
    }


# Example 2: Custom tolerance for floating-point
@regrest(tolerance=1e-10)
def calculate_pi():
    """Calculate pi approximation with high precision."""
    pi = 0
    for i in range(1000000):
        pi += ((-1) ** i) / (2 * i + 1)
    return 4 * pi


# Example 3: Custom class with dataclass
@dataclass
class Address:
    """Simple address class."""

    street: str
    city: str
    country: str


class Company:
    """Simple company class."""

    def __init__(self, name: str, founded_year: int, headquarters: Address):
        self.name = name
        self.founded_year = founded_year
        self.headquarters = headquarters


@regrest
def create_company_structure():
    """Create a nested company structure.

    Demonstrates regrest's ability to handle custom classes with Pickle.
    """
    hq_address = Address(
        street="123 Tech Street",
        city="San Francisco",
        country="USA",
    )

    company = Company(
        name="TechCorp Inc.",
        founded_year=2015,
        headquarters=hq_address,
    )

    return company


def main():
    """Run examples."""
    print("=== Regrest Examples ===\n")

    # Example 1: Data processing
    print("Example 1: Process data")
    data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    stats = process_data(data)
    print(f"Result: {stats}\n")

    # Example 2: High precision calculation
    print("Example 2: Calculate pi")
    pi = calculate_pi()
    print(f"Result: {pi}\n")

    # Example 3: Custom class
    print("Example 3: Custom class with nested structure")
    company = create_company_structure()
    print(f"Company: {company.name}")
    print(f"Founded: {company.founded_year}")
    print(f"HQ: {company.headquarters.city}, {company.headquarters.country}\n")

    print("=== All examples completed ===")


if __name__ == "__main__":
    main()
