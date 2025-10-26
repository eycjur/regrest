"""Web server for visualizing test records.

Supports both Flask (if installed) and standard library HTTP server.
"""

import json
import os
import re
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Optional, Union
from urllib.parse import urlparse

from .storage import Storage, TestRecord

# Try to import Flask
try:
    from flask import Flask, jsonify, send_from_directory

    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False


# ============================================================================
# Flask-based server (if Flask is available)
# ============================================================================


def _create_flask_app(storage_dir: str) -> Any:
    """Create Flask application.

    Args:
        storage_dir: Directory containing test records

    Returns:
        Flask application instance
    """
    from .config import Config, set_config

    # Set up config
    config = Config(storage_dir=storage_dir)
    set_config(config)

    # Create storage instance
    storage = Storage()

    # Create Flask app
    app = Flask(__name__)
    app.config["storage"] = storage

    @app.route("/")
    def index() -> Any:
        """Serve index.html."""
        static_dir = Path(__file__).parent / "static"
        return send_from_directory(static_dir, "index.html")

    @app.route("/static/<path:filename>")
    def static_files(filename: str) -> Any:
        """Serve static files (CSS, JS, images)."""
        static_dir = Path(__file__).parent / "static"
        return send_from_directory(static_dir, filename)

    @app.route("/api/records", methods=["GET"])
    def get_records() -> Any:
        """Get all records as JSON."""
        try:
            # Get all record files
            record_files = list(storage.config.storage_dir.glob("*.json"))

            records_data = []
            error_records = []

            for filepath in record_files:
                try:
                    # Read the JSON file to get basic info
                    with open(filepath, encoding="utf-8") as f:
                        data = json.load(f)

                    # Try to load the full record
                    record = TestRecord.from_dict(data)

                    record_dict = {
                        "module": record.module,
                        "function": record.function,
                        "args": _serialize_value(record.args),
                        "kwargs": _serialize_value(record.kwargs),
                        "result": _serialize_value(record.result),
                        "timestamp": record.timestamp,
                        "record_id": record.record_id,
                    }
                    records_data.append(record_dict)

                except AttributeError as e:
                    # Class not found error - extract useful information
                    error_msg = str(e)
                    match = re.search(r"Class '(\w+)' not found", error_msg)
                    class_name = match.group(1) if match else "Unknown"

                    error_records.append(
                        {
                            "record_id": data.get("record_id", filepath.stem),
                            "module": data.get("module", "unknown"),
                            "function": data.get("function", "unknown"),
                            "timestamp": data.get("timestamp", ""),
                            "error_type": "MissingClass",
                            "error_message": (
                                f"Class '{class_name}' not found in module"
                            ),
                            "details": (
                                f"The class '{class_name}' has been deleted or renamed."
                            ),
                            "suggested_fixes": [
                                f"Restore the '{class_name}' class",
                                "Delete this record",
                                "Update all records with REGREST_UPDATE_MODE=1",
                            ],
                        }
                    )

                except Exception as e:
                    # Generic error
                    has_data = "data" in locals()
                    error_records.append(
                        {
                            "record_id": (
                                data.get("record_id", filepath.stem)
                                if has_data
                                else filepath.stem
                            ),
                            "module": (
                                data.get("module", "unknown") if has_data else "unknown"
                            ),
                            "function": (
                                data.get("function", "unknown")
                                if has_data
                                else "unknown"
                            ),
                            "timestamp": (
                                data.get("timestamp", "") if has_data else ""
                            ),
                            "error_type": type(e).__name__,
                            "error_message": str(e)[:200],
                            "details": "Failed to load this record",
                            "suggested_fixes": [
                                "Delete this record",
                                "Check the record file for corruption",
                            ],
                        }
                    )

            # Sort by timestamp (newest first)
            records_data.sort(key=lambda r: r["timestamp"], reverse=True)

            response: Union[dict[str, Any], list[dict[str, Any]]] = {
                "records": records_data,
                "error_records": error_records,
                "total_errors": len(error_records),
            }

            # For backward compatibility, return just the array if no errors
            if len(error_records) == 0:
                response = records_data

            return jsonify(response)

        except Exception as e:
            return jsonify({"error": f"Error loading records: {str(e)}"}), 500

    @app.route("/api/stats", methods=["GET"])
    def get_stats() -> Any:
        """Get statistics as JSON."""
        try:
            records = storage.list_all()

            # Calculate statistics
            total_records = len(records)
            modules = {r.module for r in records}
            functions = {f"{r.module}.{r.function}" for r in records}

            # Group by module and function
            by_module: dict[str, int] = {}
            by_function: dict[str, int] = {}

            for record in records:
                # By module
                if record.module not in by_module:
                    by_module[record.module] = 0
                by_module[record.module] += 1

                # By function
                func_key = f"{record.module}.{record.function}"
                if func_key not in by_function:
                    by_function[func_key] = 0
                by_function[func_key] += 1

            stats = {
                "total_records": total_records,
                "total_modules": len(modules),
                "total_functions": len(functions),
                "by_module": by_module,
                "by_function": by_function,
            }

            return jsonify(stats)

        except Exception as e:
            return jsonify({"error": f"Error calculating stats: {str(e)}"}), 500

    @app.route("/api/records/<record_id>", methods=["DELETE"])
    def delete_record(record_id: str) -> Any:
        """Delete a single record."""
        try:
            success = storage.delete(record_id)

            if success:
                return jsonify(
                    {"success": True, "message": f"Deleted record {record_id}"}
                )
            else:
                return jsonify({"error": f"Record {record_id} not found"}), 404

        except Exception as e:
            return jsonify({"error": f"Error deleting record: {str(e)}"}), 500

    @app.route("/api/records", methods=["DELETE"])
    def delete_all_records() -> Any:
        """Delete all records."""
        try:
            count = storage.clear_all()

            return jsonify(
                {
                    "success": True,
                    "count": count,
                    "message": f"Deleted {count} records",
                }
            )

        except Exception as e:
            return jsonify({"error": f"Error deleting records: {str(e)}"}), 500

    return app


# ============================================================================
# Standard library HTTP server (fallback)
# ============================================================================


class RecordHandler(BaseHTTPRequestHandler):
    """HTTP request handler for test records visualization."""

    storage: Optional[Storage] = None

    def do_GET(self) -> None:
        """Handle GET requests."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == "/":
            self._serve_static_file("index.html")
        elif path == "/api/records":
            self._serve_records_api()
        elif path == "/api/stats":
            self._serve_stats_api()
        else:
            self._serve_404()

    def do_DELETE(self) -> None:
        """Handle DELETE requests."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == "/api/records":
            self._delete_all_records()
        elif path.startswith("/api/records/"):
            record_id = path.split("/")[-1]
            self._delete_record(record_id)
        else:
            self._serve_404()

    def _serve_static_file(self, filename: str) -> None:
        """Serve static files."""
        try:
            static_dir = Path(__file__).parent / "static"
            file_path = static_dir / filename

            if not file_path.exists():
                self._serve_404()
                return

            with open(file_path, "rb") as f:
                content = f.read()

            self.send_response(200)
            if filename.endswith(".html"):
                self.send_header("Content-type", "text/html; charset=utf-8")
            elif filename.endswith(".css"):
                self.send_header("Content-type", "text/css")
            elif filename.endswith(".js"):
                self.send_header("Content-type", "application/javascript")
            self.end_headers()
            self.wfile.write(content)

        except Exception as e:
            self._serve_error(500, f"Error serving file: {str(e)}")

    def _serve_records_api(self) -> None:
        """Serve records as JSON API."""
        if not self.storage:
            self._serve_error(500, "Storage not initialized")
            return

        try:
            # Get all record files
            record_files = list(self.storage.config.storage_dir.glob("*.json"))

            records_data = []
            error_records = []

            for filepath in record_files:
                try:
                    # Read the JSON file to get basic info
                    with open(filepath, encoding="utf-8") as f:
                        data = json.load(f)

                    # Try to load the full record
                    record = TestRecord.from_dict(data)

                    record_dict = {
                        "module": record.module,
                        "function": record.function,
                        "args": self._serialize_value(record.args),
                        "kwargs": self._serialize_value(record.kwargs),
                        "result": self._serialize_value(record.result),
                        "timestamp": record.timestamp,
                        "record_id": record.record_id,
                    }
                    records_data.append(record_dict)

                except AttributeError as e:
                    # Class not found error - extract useful information
                    error_msg = str(e)
                    # Extract class name from error message
                    match = re.search(r"Class '(\w+)' not found", error_msg)
                    class_name = match.group(1) if match else "Unknown"

                    error_records.append(
                        {
                            "record_id": data.get("record_id", filepath.stem),
                            "module": data.get("module", "unknown"),
                            "function": data.get("function", "unknown"),
                            "timestamp": data.get("timestamp", ""),
                            "error_type": "MissingClass",
                            "error_message": (
                                f"Class '{class_name}' not found in module"
                            ),
                            "details": (
                                f"The class '{class_name}' has been deleted or renamed."
                            ),
                            "suggested_fixes": [
                                f"Restore the '{class_name}' class",
                                "Delete this record",
                                "Update all records with REGREST_UPDATE_MODE=1",
                            ],
                        }
                    )

                except Exception as e:
                    # Generic error
                    has_data = "data" in locals()
                    error_records.append(
                        {
                            "record_id": (
                                data.get("record_id", filepath.stem)
                                if has_data
                                else filepath.stem
                            ),
                            "module": (
                                data.get("module", "unknown") if has_data else "unknown"
                            ),
                            "function": (
                                data.get("function", "unknown")
                                if has_data
                                else "unknown"
                            ),
                            "timestamp": (
                                data.get("timestamp", "") if has_data else ""
                            ),
                            "error_type": type(e).__name__,
                            "error_message": str(e)[:200],
                            "details": "Failed to load this record",
                            "suggested_fixes": [
                                "Delete this record",
                                "Check the record file for corruption",
                            ],
                        }
                    )

            # Sort by timestamp (newest first)
            records_data.sort(key=lambda r: r["timestamp"], reverse=True)

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            response: Union[dict[str, Any], list[dict[str, Any]]] = {
                "records": records_data,
                "error_records": error_records,
                "total_errors": len(error_records),
            }

            # For backward compatibility, return just the array if no errors
            if len(error_records) == 0:
                response = records_data

            self.wfile.write(json.dumps(response, indent=2).encode("utf-8"))

        except Exception as e:
            self._serve_error(500, f"Error loading records: {str(e)}")

    def _serve_stats_api(self) -> None:
        """Serve statistics as JSON API."""
        if not self.storage:
            self._serve_error(500, "Storage not initialized")
            return

        try:
            records = self.storage.list_all()

            # Calculate statistics
            total_records = len(records)
            modules = {r.module for r in records}
            functions = {f"{r.module}.{r.function}" for r in records}

            # Group by module and function
            by_module = {}
            by_function = {}

            for record in records:
                # By module
                if record.module not in by_module:
                    by_module[record.module] = 0
                by_module[record.module] += 1

                # By function
                func_key = f"{record.module}.{record.function}"
                if func_key not in by_function:
                    by_function[func_key] = 0
                by_function[func_key] += 1

            stats = {
                "total_records": total_records,
                "total_modules": len(modules),
                "total_functions": len(functions),
                "by_module": by_module,
                "by_function": by_function,
            }

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(stats, indent=2).encode("utf-8"))

        except Exception as e:
            self._serve_error(500, f"Error calculating stats: {str(e)}")

    def _serialize_value(self, value: Any, depth: int = 0, max_depth: int = 10) -> Any:
        """Serialize a value for JSON response.

        Args:
            value: Value to serialize
            depth: Current recursion depth
            max_depth: Maximum recursion depth

        Returns:
            JSON-serializable value
        """
        # Prevent infinite recursion
        if depth > max_depth:
            return f"<max depth reached: {type(value).__name__}>"

        # Handle JSON-serializable primitives
        if value is None or isinstance(value, (bool, int, float, str)):
            return value

        # Handle lists and tuples
        if isinstance(value, (list, tuple)):
            return [self._serialize_value(item, depth + 1, max_depth) for item in value]

        # Handle dicts
        if isinstance(value, dict):
            return {
                str(k): self._serialize_value(v, depth + 1, max_depth)
                for k, v in value.items()
            }

        # Handle sets
        if isinstance(value, set):
            return list(value)

        # Handle custom objects with __dict__
        if hasattr(value, "__dict__"):
            result = {
                "__class__": type(value).__name__,
                "__module__": type(value).__module__,
            }
            for key, val in value.__dict__.items():
                result[key] = self._serialize_value(val, depth + 1, max_depth)
            return result

        # Fallback to string representation
        return repr(value)

    def _serve_404(self) -> None:
        """Serve 404 error."""
        self.send_response(404)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        html = "<html><body><h1>404 Not Found</h1></body></html>"
        self.wfile.write(html.encode("utf-8"))

    def _serve_error(self, code: int, message: str) -> None:
        """Serve error response."""
        self.send_response(code)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        error = {"error": message}
        self.wfile.write(json.dumps(error).encode("utf-8"))

    def _delete_record(self, record_id: str) -> None:
        """Delete a single record."""
        if not self.storage:
            self._serve_error(500, "Storage not initialized")
            return

        try:
            success = self.storage.delete(record_id)

            if success:
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                result = {"success": True, "message": f"Deleted record {record_id}"}
                self.wfile.write(json.dumps(result).encode("utf-8"))
            else:
                self._serve_error(404, f"Record {record_id} not found")

        except Exception as e:
            self._serve_error(500, f"Error deleting record: {str(e)}")

    def _delete_all_records(self) -> None:
        """Delete all records."""
        if not self.storage:
            self._serve_error(500, "Storage not initialized")
            return

        try:
            count = self.storage.clear_all()

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            result = {
                "success": True,
                "count": count,
                "message": f"Deleted {count} records",
            }
            self.wfile.write(json.dumps(result).encode("utf-8"))

        except Exception as e:
            self._serve_error(500, f"Error deleting records: {str(e)}")

    def log_message(self, format: str, *args: Any) -> None:
        """Override to customize logging."""
        # Simple log format
        print(f"[{self.log_date_time_string()}] {format % args}")


# ============================================================================
# Shared helper function
# ============================================================================


def _serialize_value(value: Any, depth: int = 0, max_depth: int = 10) -> Any:
    """Serialize a value for JSON response.

    Args:
        value: Value to serialize
        depth: Current recursion depth
        max_depth: Maximum recursion depth

    Returns:
        JSON-serializable value
    """
    # Prevent infinite recursion
    if depth > max_depth:
        return f"<max depth reached: {type(value).__name__}>"

    # Handle JSON-serializable primitives
    if value is None or isinstance(value, (bool, int, float, str)):
        return value

    # Handle lists and tuples
    if isinstance(value, (list, tuple)):
        return [_serialize_value(item, depth + 1, max_depth) for item in value]

    # Handle dicts
    if isinstance(value, dict):
        return {
            str(k): _serialize_value(v, depth + 1, max_depth) for k, v in value.items()
        }

    # Handle sets
    if isinstance(value, set):
        return list(value)

    # Handle custom objects with __dict__
    if hasattr(value, "__dict__"):
        result = {
            "__class__": type(value).__name__,
            "__module__": type(value).__module__,
        }
        for key, val in value.__dict__.items():
            result[key] = _serialize_value(val, depth + 1, max_depth)
        return result

    # Fallback to string representation
    return repr(value)


# ============================================================================
# Hot reload support (standard library only)
# ============================================================================


def _get_file_mtimes(watch_paths: list[Path]) -> dict[Path, float]:
    """Get modification times for watched files.

    Args:
        watch_paths: List of paths to watch

    Returns:
        Dictionary mapping file paths to modification times
    """
    mtimes = {}
    for path in watch_paths:
        if path.is_file():
            mtimes[path] = path.stat().st_mtime
        elif path.is_dir():
            for file_path in path.rglob("*"):
                if file_path.is_file():
                    mtimes[file_path] = file_path.stat().st_mtime
    return mtimes


def _run_server_with_reload(host: str, port: int, storage_dir: str) -> None:
    """Run server with auto-reload on file changes.

    Args:
        host: Host to bind to
        port: Port to bind to
        storage_dir: Directory containing test records
    """
    # Watch regrest package directory and static files
    package_dir = Path(__file__).parent
    static_dir = package_dir / "static"
    watch_paths = [package_dir / "server.py", static_dir]

    print("\n" + "=" * 60)
    print("🧪 Regrest Visualization Server (Hot Reload Enabled)")
    print("=" * 60)
    print(f"\n📁 Storage directory: {storage_dir}")
    print(f"🌐 Server running at: http://{host}:{port}")
    print(f"👀 Watching: {package_dir / 'server.py'}, {static_dir}")
    print("\n💡 Press Ctrl+C to stop the server\n")
    print("=" * 60 + "\n")

    # Start server in subprocess
    # Note: --storage-dir is a global option, so it must come before 'serve'
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "regrest",
            "--storage-dir",
            storage_dir,
            "serve",
            "--host",
            host,
            "--port",
            str(port),
        ],
        env={**os.environ, "REGREST_NO_RELOAD": "1"},
    )

    # Get initial modification times
    mtimes = _get_file_mtimes(watch_paths)

    try:
        while True:
            time.sleep(1)

            # Check for file changes
            current_mtimes = _get_file_mtimes(watch_paths)

            if current_mtimes != mtimes:
                # Find changed files
                changed = []
                for path in set(mtimes.keys()) | set(current_mtimes.keys()):
                    old_mtime = mtimes.get(path, 0)
                    new_mtime = current_mtimes.get(path, 0)
                    if old_mtime != new_mtime:
                        changed.append(path.name)

                print(f"\n🔄 Detected changes in: {', '.join(changed)}")
                print("♻️  Restarting server...\n")

                # Kill old process
                process.terminate()
                process.wait(timeout=5)

                # Start new process
                process = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "regrest",
                        "--storage-dir",
                        storage_dir,
                        "serve",
                        "--host",
                        host,
                        "--port",
                        str(port),
                    ],
                    env={**os.environ, "REGREST_NO_RELOAD": "1"},
                )

                mtimes = current_mtimes

    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down server...")
        process.terminate()
        process.wait(timeout=5)
        print("✅ Server stopped.\n")


# ============================================================================
# Main entry point
# ============================================================================


def run_server(
    host: str = "localhost",
    port: int = 8000,
    storage_dir: str = ".regrest",
    reload: bool = False,
) -> None:
    """Run the web server.

    Args:
        host: Host to bind to
        port: Port to bind to
        storage_dir: Directory containing test records
        reload: Enable auto-reload on file changes
    """
    # Try to use Flask if available
    if HAS_FLASK:
        app = _create_flask_app(storage_dir)

        print("\n" + "=" * 60)
        print("🧪 Regrest Visualization Server (Flask)")
        print("=" * 60)
        print(f"\n📁 Storage directory: {storage_dir}")
        print(f"🌐 Server running at: http://{host}:{port}")
        if reload:
            print("🔄 Auto-reload: enabled")
        print("\n💡 Press Ctrl+C to stop the server\n")
        print("=" * 60 + "\n")

        app.run(host=host, port=port, debug=reload)

    else:
        # Fall back to standard library server
        # If reload is enabled and we're not in the child process, run with reload
        if reload and not os.environ.get("REGREST_NO_RELOAD"):
            _run_server_with_reload(host, port, storage_dir)
            return

        from .config import Config, set_config

        # Set up config
        config = Config(storage_dir=storage_dir)
        set_config(config)

        # Create storage instance
        storage = Storage()
        RecordHandler.storage = storage

        # Create and start server
        server = HTTPServer((host, port), RecordHandler)

        # Only print banner if not in reload mode
        if not os.environ.get("REGREST_NO_RELOAD"):
            print("\n" + "=" * 60)
            print("🧪 Regrest Visualization Server")
            print("=" * 60)
            print(f"\n📁 Storage directory: {storage_dir}")
            print(f"🌐 Server running at: http://{host}:{port}")
            print("\n💡 Press Ctrl+C to stop the server\n")
            print("=" * 60 + "\n")

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            if not os.environ.get("REGREST_NO_RELOAD"):
                print("\n\n🛑 Shutting down server...")
                server.shutdown()
                print("✅ Server stopped.\n")
