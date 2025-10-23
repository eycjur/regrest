.DEFAULT_GOAL := help

.PHONY: help
help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install:  ## Install the package in development mode
	uv sync --all-extras

.PHONY: format
format:  ## Format code with ruff
	uv run python -m ruff format .

.PHONY: lint
lint:  ## Run linters (ruff check + mypy)
	uv run python -m ruff check .
	uv run python -m mypy .

.PHONY: lint-fix
lint-fix:  ## Run linters and fix issues
	uv run python -m ruff check --fix .
	uv run python -m mypy .

.PHONY: test
test:  ## Run tests with pytest
	uv run python -m pytest tests

.PHONY: check
check: format lint test  ## Run all checks (format, lint, test)

.PHONY: build
build: clean  ## Build distribution packages
	uv run python -m build

.PHONY: clean
clean:  ## Clean up generated files
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf .pytest_cache/
	rm -rf **/__pycache__/
	rm -rf *.egg-info/
	rm -rf dist/
	rm -rf build/

.PHONY: list
list:  ## List all regrest records
	uv run python -m regrest list

.PHONY: example
example:  ## Run example.py
	uv run python example.py
