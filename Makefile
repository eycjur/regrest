.DEFAULT_GOAL := help

include .env

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
	uv build

.PHONY: publish
publish: check build  ## Publish to PyPI (production)
	@echo ""
	@echo "=========================================="
	@echo "  Publishing to PyPI"
	@echo "=========================================="
	@echo ""
	@echo "[1/6] Checking PyPI token..."
	@if [ -z "$(UV_PUBLISH_TOKEN)" ]; then \
		echo "❌ UV_PUBLISH_TOKEN is not set"; \
		echo "   Please set it in .env file or environment"; \
		exit 1; \
	fi
	@echo "      ✅ PyPI token is set"
	@echo ""
	@echo "[2/6] Reading version from pyproject.toml..."
	@VERSION=$$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/'); \
	if [ -z "$$VERSION" ]; then \
		echo "❌ Could not find version in pyproject.toml"; \
		exit 1; \
	fi; \
	echo "      Version: $$VERSION"; \
	echo ""; \
	echo "[3/6] Checking git status..."; \
	if ! git diff-index --quiet HEAD --; then \
		echo "❌ Uncommitted changes. Commit first."; \
		git status --short; \
		exit 1; \
	fi; \
	echo "      ✅ Working directory is clean"; \
	echo ""; \
	echo "[4/6] Checking git tags..."; \
	CURRENT_TAGS=$$(git tag --points-at HEAD); \
	if [ -n "$$CURRENT_TAGS" ]; then \
		for tag in $$CURRENT_TAGS; do \
			if [ "$$tag" = "v$$VERSION" ]; then \
				echo "❌ Version $$VERSION already published"; \
				echo "   Tag v$$VERSION exists on current commit"; \
				echo "   Update version in pyproject.toml and commit"; \
				exit 1; \
			fi; \
		done; \
	fi; \
	if git rev-parse "v$$VERSION" >/dev/null 2>&1; then \
		echo "❌ Tag v$$VERSION exists on a different commit"; \
		echo "   Update version in pyproject.toml"; \
		exit 1; \
	fi; \
	echo "      ✅ Ready to tag v$$VERSION"; \
	echo ""; \
	echo "[5/6] Creating and pushing git tag..."; \
	if git tag -a "v$$VERSION" -m "Release v$$VERSION"; then \
		if git push origin "v$$VERSION" 2>&1; then \
			echo "      ✅ Tagged and pushed v$$VERSION"; \
		else \
			echo ""; \
			echo "❌ Failed to push tag to remote"; \
			echo "   Removing local tag..."; \
			git tag -d "v$$VERSION"; \
			exit 1; \
		fi; \
	else \
		echo "❌ Failed to create tag"; \
		exit 1; \
	fi; \
	echo ""; \
	echo "[6/6] Publishing to PyPI..."; \
	UV_PUBLISH_TOKEN=$(UV_PUBLISH_TOKEN) uv publish; \
	echo ""; \
	echo "=========================================="
	@echo "  ✅ Successfully published v$$VERSION"
	@echo "=========================================="

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
