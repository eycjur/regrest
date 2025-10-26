"""Regression test decorator."""

import functools
import logging
import os
import sys
from typing import Any, Callable, Optional

from ._logging import regrest_logger
from .config import get_config
from .exceptions import RegressionTestError
from .matcher import Matcher
from .storage import Storage, TestRecord


def regrest(
    func: Optional[Callable] = None,
    *,
    tolerance: Optional[float] = None,
    update: bool = False,
    raise_on_error: Optional[bool] = None,
) -> Callable:
    """Decorator for regression testing.

    On first call, records the function's arguments and return value.
    On subsequent calls, compares the return value with the recorded value.

    Args:
        func: Function to decorate
        tolerance: Float comparison tolerance (overrides config)
        update: If True, update the record instead of testing
        raise_on_error: If True, raise exception on test failure.
                       If False, log error and continue.
                       If None (default), use config value (default: False).

    Returns:
        Decorated function

    Example:
        @regrest
        def calculate(x, y):
            return x + y

        # First call: records result
        result = calculate(2, 3)  # Returns 5, records it

        # Second call: tests against record
        result = calculate(2, 3)  # Returns 5, compares with record

        # Non-strict mode: logs error but doesn't raise exception
        @regrest(raise_on_error=False)
        def maybe_failing():
            return some_value()
    """

    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get function metadata
            module = f.__module__
            function = f.__name__

            # Convert __main__ to actual script filename
            if module == "__main__":
                main_module = sys.modules.get("__main__")
                if main_module and hasattr(main_module, "__file__"):
                    main_file = main_module.__file__
                    if main_file:
                        # Get filename without extension
                        module = os.path.splitext(os.path.basename(main_file))[0]

                        # Register __main__ as the actual module name in sys.modules
                        # This allows pickle to find classes when unpickling
                        if module not in sys.modules:
                            sys.modules[module] = main_module

            # Debug logging: log function call with arguments
            if regrest_logger.isEnabledFor(logging.DEBUG):
                regrest_logger.debug(
                    "Calling %s.%s with args=%s, kwargs=%s",
                    module,
                    function,
                    args,
                    kwargs,
                )

            # Get config
            config = get_config()
            should_update = update or config.update_mode
            should_raise_on_error = (
                raise_on_error if raise_on_error is not None else config.raise_on_error
            )

            # Initialize storage and matcher
            storage = Storage()
            matcher = Matcher(tolerance=tolerance)

            # Execute function
            result = f(*args, **kwargs)

            # Debug logging: log return value
            if regrest_logger.isEnabledFor(logging.DEBUG):
                regrest_logger.debug(
                    "Function %s.%s returned: %s", module, function, result
                )

            # Try to find existing record
            record_load_failed = False
            try:
                existing_record = storage.find(module, function, args, kwargs)
            except (AttributeError, ImportError) as e:
                # Failed to load record due to missing class or module
                error_message = (
                    f"Failed to load existing record for {module}.{function}\n{str(e)}"
                )

                if should_raise_on_error:
                    raise RegressionTestError(error_message) from e
                else:
                    # Log error but don't overwrite the corrupted record
                    for line in error_message.split("\n"):
                        if line:
                            regrest_logger.error(line)
                    record_load_failed = True
                    existing_record = None

            # Don't save if record load failed (to avoid overwriting corrupted records)
            if record_load_failed:
                regrest_logger.warning(
                    "Skipping save for %s.%s due to record load error", module, function
                )
                return result

            if existing_record is None or should_update:
                # Record mode: save the result
                record = TestRecord(
                    module=module,
                    function=function,
                    args=args,
                    kwargs=kwargs,
                    result=result,
                )
                storage.save(record)

                if existing_record is None:
                    regrest_logger.info("Recorded: %s.%s", module, function)
                else:
                    regrest_logger.info("Updated: %s.%s", module, function)
            else:
                # Test mode: compare with recorded result
                match_result = matcher.match(existing_record.result, result)

                if not match_result:
                    error_message = (
                        f"Regression test failed for {module}.{function}\n"
                        f"{match_result.message}"
                    )

                    if should_raise_on_error:
                        raise RegressionTestError(error_message)
                    else:
                        # Log each line separately so formatter is applied to each line
                        for line in error_message.split("\n"):
                            if line:  # Skip empty lines
                                regrest_logger.error(line)
                else:
                    regrest_logger.info("Passed: %s.%s", module, function)

            return result

        return wrapper

    # Handle both @regrest and @regrest() syntax
    if func is None:
        # Called with arguments: @regrest()
        return decorator
    else:
        # Called without arguments: @regrest
        return decorator(func)
