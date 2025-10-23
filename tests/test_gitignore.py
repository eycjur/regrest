"""Test auto-gitignore functionality."""

import shutil
import time
from pathlib import Path

import pytest


@pytest.fixture(scope="module", autouse=True)
def clean_regrest_dir():
    """Clean up .regrest directory before and after tests."""
    regrest_dir = Path(".regrest")
    if regrest_dir.exists():
        shutil.rmtree(regrest_dir)
    yield
    # Keep the directory for inspection, but you can uncomment to clean up
    # if regrest_dir.exists():
    #     shutil.rmtree(regrest_dir)


def test_gitignore_auto_creation():
    """Test that .regrest/.gitignore is created automatically on first run."""
    from regrest import regrest

    @regrest
    def simple_function():
        return 42

    result = simple_function()
    assert result == 42

    gitignore_path = Path(".regrest/.gitignore")
    assert gitignore_path.exists(), (
        ".regrest/.gitignore should be created automatically"
    )

    content = gitignore_path.read_text()
    assert "*" in content, ".regrest/.gitignore should contain '*' to ignore all files"


def test_gitignore_not_overwritten():
    """Test that .regrest/.gitignore is not overwritten on subsequent runs."""
    from regrest import regrest

    gitignore_path = Path(".regrest/.gitignore")
    assert gitignore_path.exists(), (
        ".regrest/.gitignore should exist from previous test"
    )

    original_mtime = gitignore_path.stat().st_mtime
    time.sleep(0.1)

    @regrest
    def another_function():
        return "hello"

    result = another_function()
    assert result == "hello"

    new_mtime = gitignore_path.stat().st_mtime
    assert original_mtime == new_mtime, (
        ".regrest/.gitignore should not be overwritten on subsequent runs"
    )
