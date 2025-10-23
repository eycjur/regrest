# Regrest

[English](README.md) | [日本語](README_ja.md)

**Regrest** is a simple and powerful regression testing tool for Python. It automatically records function outputs on the first run and validates them on subsequent runs.

## Features

- 🎯 **Simple decorator-based API** - Just add `@regrest` to your functions
- 📝 **Automatic recording** - First run records outputs, subsequent runs validate
- 🔍 **Smart comparison** - Handles floats, dicts, lists, nested structures
- 🛠 **CLI tools** - List, view, and delete test records
- ⚙️ **Configurable** - Custom tolerance, storage location, and more
- 🔧 **Auto .gitignore** - Automatically creates `.regrest/.gitignore` to exclude test records on first run

## Requirements

- Python 3.9 or higher

## Installation

```bash
# Using uv (recommended)
uv sync --all-extras

# Or using pip
pip install -e .
```

## Development

This project uses `make` for common development tasks:

```bash
# Show all available commands
make help

# Install dependencies
make install

# Format code
make format

# Run linters
make lint

# Run linters with auto-fix
make lint-fix

# Run tests
make test

# Run all checks (format + lint + test)
make check

# Clean generated files
make clean

# Run example
make example
```

## Running Examples

```bash
# Basic usage example
python tests/example.py

# Custom class test
python tests/test_custom_class.py

# Auto .gitignore test
python tests/test_gitignore.py
```

## Quick Start

### Basic Usage

```python
from regrest import regrest

@regrest
def calculate_price(items, discount=0):
    total = sum(item['price'] for item in items)
    return total * (1 - discount)

# First run: records the result
items = [{'price': 100}, {'price': 200}]
result = calculate_price(items, discount=0.1)  # Returns 270.0, records it
# Output: [regrest] Recorded: __main__.calculate_price (id: abc123...)

# Second run: validates against recorded result
result = calculate_price(items, discount=0.1)  # Returns 270.0, compares with record
# Output: [regrest] Passed: __main__.calculate_price (id: abc123...)
```

### Custom Tolerance

```python
@regrest(tolerance=1e-6)
def calculate_pi():
    return 3.14159265359
```

### Update Mode

To update existing records instead of testing:

```python
@regrest(update=True)
def my_function():
    return "new result"
```

Or set the environment variable:

```bash
REGREST_UPDATE_MODE=1 python your_script.py
```

## Environment Variables

Regrest supports configuration via environment variables:

- `REGREST_LOG_LEVEL` - Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `REGREST_RAISE_ON_ERROR` - Raise exceptions on test failure (true/false, 1/0)
- `REGREST_UPDATE_MODE` - Update all records (true/false, 1/0)
- `REGREST_STORAGE_DIR` - Custom storage directory
- `REGREST_FLOAT_TOLERANCE` - Float comparison tolerance (e.g., 1e-6)

Examples:

```bash
# Run with debug logging
REGREST_LOG_LEVEL=DEBUG python your_script.py

# Update all records
REGREST_UPDATE_MODE=1 python your_script.py

# Strict mode (raise on error)
REGREST_RAISE_ON_ERROR=true python your_script.py

# Custom storage and tolerance
REGREST_STORAGE_DIR=.test_records REGREST_FLOAT_TOLERANCE=1e-6 python your_script.py
```

**Priority order**: Constructor arguments > Environment variables > Default values

## CLI Usage

The CLI can be invoked in multiple ways:

```bash
# After pip install -e .
regrest list

# Or using python -m
python -m regrest list

# Or directly
python regrest/cli.py list
```

### List all test records

```bash
# Show all records
regrest list

# Filter by keyword
regrest list -k calculate
regrest list -k __main__
```

Output:
```
Found 2 test record(s):

__main__:
  calculate_price()
    ID: abc123def456
    Arguments:
      args[0]: [{'price': 100}, {'price': 200}]
      discount: 0.1
    Result:
      270.0
    Recorded: 2024-01-15T10:30:00
```

### Delete records

```bash
# Delete by ID
regrest delete abc123

# Delete by pattern
regrest delete --pattern "mymodule.*"

# Delete all records
regrest delete --all
```

### Custom storage directory

```bash
regrest --storage-dir=.my_records list
```

## How It Works

1. **First Run**: When you call a function decorated with `@regrest`, it executes normally and saves:
   - Module and function name
   - Arguments (args and kwargs)
   - Return value
   - Timestamp

   The record is saved to `.regrest/` directory as a JSON file.

2. **Subsequent Runs**: On the next call with the same arguments:
   - The function executes
   - The result is compared with the recorded value
   - If they match → Test passes ✅
   - If they don't match → `RegressionTestError` is raised ❌

3. **Update Mode**: When you need to update the expected values:
   - Use `@regrest(update=True)` or `REGREST_UPDATE=1`
   - The old record is replaced with the new result

## Configuration

### Global Configuration

```python
from regrest import Config, set_config

config = Config(
    storage_dir='.my_records',
    float_tolerance=1e-6,
)
set_config(config)
```

### Per-function Configuration

```python
@regrest(tolerance=1e-9)
def precise_calculation():
    return 3.141592653589793
```

## Advanced Features

### Comparison Logic

The matcher intelligently compares:
- **Primitives**: Exact match for strings, booleans
- **Numbers**: Tolerance-based for floats, exact for integers
- **Collections**: Deep comparison for lists, dicts, sets
- **Nested structures**: Recursive comparison with detailed error messages

### Record Identification

Records are identified by:
- Module name
- Function name
- SHA256 hash of arguments (first 16 chars)

This means different argument combinations create different records.

## Examples

### Example 1: Data Processing

```python
from regrest import regrest

@regrest
def process_data(data):
    # Complex data transformation
    result = {
        'mean': sum(data) / len(data),
        'max': max(data),
        'min': min(data),
    }
    return result

# First run records the result
stats = process_data([1, 2, 3, 4, 5])

# Future runs validate the result hasn't changed
stats = process_data([1, 2, 3, 4, 5])  # Must match recorded values
```

### Example 2: API Response

```python
@regrest
def format_user_response(user):
    return {
        'id': user['id'],
        'name': f"{user['first_name']} {user['last_name']}",
        'email': user['email'].lower(),
    }

user_data = {
    'id': 123,
    'first_name': 'John',
    'last_name': 'Doe',
    'email': 'JOHN@EXAMPLE.COM',
}

# Records: {'id': 123, 'name': 'John Doe', 'email': 'john@example.com'}
response = format_user_response(user_data)
```

### Example 3: Numerical Computation

```python
import math

@regrest(tolerance=1e-10)
def calculate_distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

# Floating point calculations validated with tolerance
distance = calculate_distance(0, 0, 3, 4)  # Should be 5.0
```

### Example 4: Custom Classes

```python
class Point:
    """Custom class example."""
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __eq__(self, other):
        """Equality definition is required."""
        if not isinstance(other, Point):
            return False
        return self.x == other.x and self.y == other.y

    def __repr__(self):
        """For better error messages (recommended)."""
        return f"Point({self.x}, {self.y})"


@regrest
def calculate_midpoint(p1, p2):
    """Function returning custom class."""
    return Point(
        (p1.x + p2.x) / 2,
        (p1.y + p2.y) / 2,
    )

# Custom classes are saved using pickle
result = calculate_midpoint(Point(0, 0), Point(10, 10))
```

**Requirements for custom classes**:
- ✅ Must be pickle-serializable
- ✅ Must implement `__eq__` method (for comparison)
- ✅ Recommended to implement `__repr__` (for better error messages)

## Storage Format

Records are stored as JSON files in `.regrest/`:

```
.regrest/
├── mymodule.calculate_price.abc123def456.json
└── mymodule.process_data.789ghi012jkl.json
```

Each file contains (for JSON-serializable data):
```json
{
  "module": "mymodule",
  "function": "calculate_price",
  "args": {
    "type": "json",
    "data": [[{"price": 100}, {"price": 200}]]
  },
  "kwargs": {
    "type": "json",
    "data": {"discount": 0.1}
  },
  "result": {
    "type": "json",
    "data": 270.0
  },
  "timestamp": "2024-01-15T10:30:00.123456",
  "record_id": "abc123def456"
}
```

For custom classes (not JSON-serializable):
```json
{
  "module": "mymodule",
  "function": "calculate_midpoint",
  "args": {
    "type": "pickle",
    "data": "gASVNAAAAAAAAACMCF9fbWFpbl9flIwFUG9pbnSUk5QpgZR9lCiMAXiUSwCMAXmUSwB1Yi4="
  },
  "result": {
    "type": "pickle",
    "data": "gASVNgAAAAAAAACMCF9fbWFpbl9flIwFUG9pbnSUk5QpgZR9lCiMAXiURwAUAAAAAAAAjAF5l..."
  },
  "timestamp": "2024-01-15T10:30:00.123456",
  "record_id": "def456ghi789"
}
```

**Encoding methods**:
- JSON-serializable data → Stored directly as JSON
- Non-JSON-serializable data → Pickled + Base64 encoded

## Best Practices

1. **Version Control**:
   - **Auto-exclude**: `.regrest/.gitignore` is automatically created to exclude test records on first run
   - **Team sharing**: To share records with your team, delete `.regrest/.gitignore`
   - **Directory tracking**: The `.regrest/` directory itself is tracked, but files inside are ignored

2. **Deterministic Functions**: Use `@regrest` on functions with deterministic outputs (same input → same output)

3. **Update Workflow**: When intentionally changing behavior:
   ```bash
   # Review changes, then update records
   REGREST_UPDATE=1 python your_script.py
   ```

4. **Selective Testing**: Use patterns to test specific modules:
   ```bash
   regrest delete --pattern "old_module.*"  # Remove old tests
   ```

## Limitations

- **Non-deterministic functions**: Don't use `@regrest` on functions with random output, timestamps, etc.
- **Large outputs**: Very large return values may make storage files unwieldy
- **Python version**: Requires Python 3.9 or higher
- **Serialization**:
  - Arguments and return values must be JSON or pickle-serializable
  - Custom classes must implement `__eq__` method (for comparison)
  - Pickle usage may have compatibility issues across Python versions

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

Before submitting, please ensure:
1. Run `make check` to verify all tests and linters pass
2. Add tests for new features
3. Update documentation as needed

## License

MIT License

## Changelog

### 0.1.0 (Initial Release)
- Core decorator functionality (`@regrest`)
- Hybrid JSON/Pickle storage system
- Smart comparison with floating-point tolerance
- CLI tools (`regrest list`, `regrest delete`)
- Custom class support
- Auto `.gitignore` generation
- Environment variable configuration
- Colorful logging output
- Python 3.9+ support
- pyproject.toml-based build system
- ruff + mypy static analysis
- Makefile task automation
- GitHub Actions CI/CD
