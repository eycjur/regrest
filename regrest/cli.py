"""Command-line interface for regrest."""

from typing import Annotated, Any, Optional

import typer

from .config import Config, set_config
from .storage import Storage

app = typer.Typer(
    name="regrest",
    help="Regression testing tool for Python",
    no_args_is_help=True,
)


@app.callback(invoke_without_command=True)
def callback(
    ctx: typer.Context,
    storage_dir: Annotated[
        str, typer.Option(help="Directory to store test records")
    ] = ".regrest",
) -> None:
    """Regrest CLI - Regression testing tool for Python."""
    # Store storage_dir in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["storage_dir"] = storage_dir


@app.command()
def list(
    ctx: typer.Context,
    k: Annotated[
        Optional[str],
        typer.Option(
            "-k", help="Keyword to filter records (matches module or function name)"
        ),
    ] = None,
) -> None:
    """List all test records.

    Examples:
        regrest list                # Show all records
        regrest list -k calculate   # Show records with 'calculate' in module
                                    # or function name
        regrest list -k __main__    # Show records from __main__ module
    """
    storage_dir = ctx.obj["storage_dir"]
    _setup_config(storage_dir)

    storage = Storage()
    records = storage.list_all()

    if not records:
        typer.echo("No test records found.")
        return

    # Filter records by keyword
    if k:
        keyword_lower = k.lower()
        records = [
            r
            for r in records
            if keyword_lower in r.module.lower() or keyword_lower in r.function.lower()
        ]

    if not records:
        typer.echo("No test records found matching the filter.")
        return

    # Sort by module, function, timestamp
    records.sort(key=lambda r: (r.module, r.function, r.timestamp))

    typer.echo(f"Found {len(records)} test record(s):\n")

    current_module = None
    current_function = None

    for record in records:
        # Print module header if changed
        if record.module != current_module:
            if current_module is not None:
                typer.echo()  # Blank line between modules
            typer.secho(f"{record.module}:", fg=typer.colors.CYAN, bold=True)
            current_module = record.module
            current_function = None

        # Print function header if changed
        if record.function != current_function:
            typer.secho(f"  {record.function}()", fg=typer.colors.YELLOW)
            current_function = record.function

        # Print ID
        typer.echo(f"    ID: {record.record_id}")

        # Print arguments
        typer.echo("    Arguments:")
        if record.args:
            for i, arg in enumerate(record.args):
                typer.echo(f"      args[{i}]: {_format_value(arg)}")
        if record.kwargs:
            for key, value in record.kwargs.items():
                typer.echo(f"      {key}: {_format_value(value)}")
        if not record.args and not record.kwargs:
            typer.echo("      (no arguments)")

        # Print result
        typer.echo("    Result:")
        typer.echo(f"      {_format_value(record.result)}")

        typer.echo(f"    Recorded: {record.timestamp}")
        typer.echo()  # Blank line between records


@app.command()
def delete(
    ctx: typer.Context,
    record_id: Annotated[
        Optional[str], typer.Argument(help="Record ID to delete")
    ] = None,
    all: Annotated[bool, typer.Option("--all", help="Delete all records")] = False,
    pattern: Annotated[
        Optional[str], typer.Option(help="Delete records matching pattern")
    ] = None,
    yes: Annotated[bool, typer.Option("-y", "--yes", help="Skip confirmation")] = False,
) -> None:
    """Delete test records."""
    storage_dir = ctx.obj["storage_dir"]
    _setup_config(storage_dir)

    storage = Storage()

    if all:
        # Delete all records
        if not yes:
            response = typer.confirm("Delete ALL test records?", default=False)
            if not response:
                typer.echo("Cancelled.")
                return

        count = storage.clear_all()
        typer.secho(f"Deleted {count} record(s).", fg=typer.colors.GREEN)

    elif pattern:
        # Delete by pattern
        if not yes:
            response = typer.confirm(
                f"Delete all records matching '{pattern}'?", default=False
            )
            if not response:
                typer.echo("Cancelled.")
                return

        count = storage.delete_by_pattern(pattern)
        typer.secho(f"Deleted {count} record(s).", fg=typer.colors.GREEN)

    elif record_id:
        # Delete by ID
        success = storage.delete(record_id)
        if success:
            typer.secho(f"Deleted record '{record_id}'.", fg=typer.colors.GREEN)
        else:
            typer.secho(
                f"Error: Record '{record_id}' not found.", fg=typer.colors.RED, err=True
            )
            raise typer.Exit(code=1)

    else:
        typer.secho(
            "Error: Specify --all, --pattern, or a record ID.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)


@app.command()
def verify(
    ctx: typer.Context,
    k: Annotated[
        Optional[str],
        typer.Option(
            "-k", help="Keyword to filter records (matches module or function name)"
        ),
    ] = None,
    tolerance: Annotated[
        Optional[float],
        typer.Option("--tolerance", help="Float comparison tolerance"),
    ] = None,
) -> None:
    """Verify all recorded test records by re-executing functions.

    This command:
    1. Loads all recorded test data
    2. Re-executes each function with recorded arguments
    3. Compares results with recorded values
    4. Reports pass/fail status

    Examples:
        regrest verify                      # Verify all records
        regrest verify -k calculate         # Verify only 'calculate' functions
        regrest verify --tolerance 0.001    # Custom float tolerance
    """
    storage_dir = ctx.obj["storage_dir"]
    _setup_config(storage_dir)

    storage = Storage()
    records = storage.list_all()

    if not records:
        typer.echo("No test records found.")
        return

    # Filter records by keyword
    if k:
        keyword_lower = k.lower()
        records = [
            r
            for r in records
            if keyword_lower in r.module.lower() or keyword_lower in r.function.lower()
        ]

    if not records:
        typer.echo("No test records found matching the filter.")
        return

    # Sort by module, function, timestamp
    records.sort(key=lambda r: (r.module, r.function, r.timestamp))

    typer.echo(f"Verifying {len(records)} test record(s)...\n")

    passed = 0
    failed = 0
    errors = 0
    failed_records = []

    # Import necessary modules
    import importlib
    import os
    import sys
    from .matcher import Matcher

    # Add current working directory to sys.path to allow importing user modules
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    matcher = Matcher(tolerance=tolerance)

    current_module = None
    for record in records:
        # Print module header if changed
        if record.module != current_module:
            if current_module is not None:
                typer.echo()
            typer.secho(f"{record.module}:", fg=typer.colors.CYAN, bold=True)
            current_module = record.module

        # Print function being tested
        typer.echo(f"  {record.function}() [ID: {record.record_id[:8]}]...", nl=False)

        try:
            # Import module and get function
            try:
                module = importlib.import_module(record.module)
            except ImportError as e:
                raise ImportError(
                    f"Cannot import module '{record.module}'. "
                    f"Make sure to run this command from the project root directory. "
                    f"Original error: {str(e)}"
                )

            func = getattr(module, record.function)

            # Get the original function if it's decorated
            if hasattr(func, "__wrapped__"):
                original_func = func.__wrapped__
            else:
                original_func = func

            # Execute function with recorded arguments
            result = original_func(*record.args, **record.kwargs)

            # Compare result with recorded value
            match_result = matcher.match(record.result, result)

            if match_result:
                typer.secho(" PASS", fg=typer.colors.GREEN)
                passed += 1
            else:
                typer.secho(" FAIL", fg=typer.colors.RED)
                failed += 1
                failed_records.append((record, match_result.message))

        except Exception as e:
            typer.secho(" ERROR", fg=typer.colors.RED)
            errors += 1
            failed_records.append((record, f"Exception: {str(e)}"))

    # Summary
    typer.echo()
    typer.secho("=" * 60, fg=typer.colors.BRIGHT_BLACK)
    typer.echo(f"Total: {len(records)} | ", nl=False)
    typer.secho(f"Passed: {passed}", fg=typer.colors.GREEN, nl=False)
    typer.echo(" | ", nl=False)
    if failed > 0:
        typer.secho(f"Failed: {failed}", fg=typer.colors.RED, nl=False)
        typer.echo(" | ", nl=False)
    if errors > 0:
        typer.secho(f"Errors: {errors}", fg=typer.colors.RED)
    else:
        typer.echo()

    # Show failed records details
    if failed_records:
        typer.echo()
        typer.secho("Failed Records:", fg=typer.colors.RED, bold=True)
        for record, error_msg in failed_records:
            typer.echo()
            typer.echo(f"  {record.module}.{record.function}() [ID: {record.record_id[:8]}]")
            typer.echo(f"    {error_msg}")

    # Exit with error code if any tests failed
    if failed + errors > 0:
        raise typer.Exit(code=1)


@app.command()
def serve(
    ctx: typer.Context,
    host: Annotated[str, typer.Option(help="Host to bind to")] = "localhost",
    port: Annotated[int, typer.Option(help="Port to bind to")] = 8000,
    reload: Annotated[
        bool, typer.Option("--reload", help="Enable auto-reload on file changes")
    ] = False,
) -> None:
    """Start a web server to visualize test records.

    Examples:
        regrest serve                    # Start server on localhost:8000
        regrest serve --port 8080        # Start server on port 8080
        regrest serve --host 0.0.0.0     # Allow external connections
        regrest serve --reload           # Enable hot reload for development

    Note:
        If Flask is installed (pip install regrest[server]), a Flask-based
        server will be used. Otherwise, falls back to the standard library
        HTTP server.
    """
    storage_dir = ctx.obj["storage_dir"]

    from .server import run_server

    run_server(host=host, port=port, storage_dir=storage_dir, reload=reload)


def _setup_config(storage_dir: str) -> None:
    """Set up configuration.

    Args:
        storage_dir: Directory to store test records
    """
    config = Config(storage_dir=storage_dir)
    set_config(config)


def _format_value(value: Any) -> str:
    """Format a value for display.

    Args:
        value: Value to format

    Returns:
        Formatted string
    """
    value_str = repr(value)
    if len(value_str) > 80:
        value_str = value_str[:77] + "..."
    return value_str


def main() -> None:
    """Main entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
