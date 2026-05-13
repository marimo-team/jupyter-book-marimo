JBM_STYLESHEETS ?= styles/jupyter-book-marimo.css
WIDGET_SRC_DIR := widget
WIDGET_ENTRY := $(WIDGET_SRC_DIR)/container-widget.ts
WIDGET_BUNDLE := src/jupyter_book_marimo/assets/container-widget.mjs

.PHONY: format format-check lint typecheck docs-format docs-format-check widget-format widget-format-check widget-lint widget-typecheck widget-build widget-build-check test check build book-build book-start clean

format:
	uv run ruff format src tests scripts
	uv run deno task docs:fmt
	uv run deno task widget:fmt

format-check:
	uv run ruff format --check src tests scripts
	uv run deno task docs:fmt-check
	uv run deno task widget:fmt-check

lint:
	uv run ruff check src tests scripts
	uv run deno task widget:lint

typecheck:
	uv run ty check src scripts
	uv run deno task widget:check

docs-format:
	uv run deno task docs:fmt

docs-format-check:
	uv run deno task docs:fmt-check

widget-format:
	uv run deno task widget:fmt

widget-format-check:
	uv run deno task widget:fmt-check

widget-lint:
	uv run deno task widget:lint

widget-typecheck:
	uv run deno task widget:check

widget-build:
	uv run python scripts/bundle_widget.py

widget-build-check:
	@tmp=$$(mktemp); \
	uv run python scripts/bundle_widget.py "$$tmp"; \
	if ! cmp -s "$$tmp" "$(WIDGET_BUNDLE)"; then \
		echo "$(WIDGET_BUNDLE) is out of date; run make widget-build"; \
		rm -f "$$tmp"; \
		exit 1; \
	fi; \
	rm -f "$$tmp"

test:
	uv run pytest tests

check: format-check lint typecheck test build

build: widget-build-check
	uv build

book-build:
	cd docs && JUPYTER_BOOK_MARIMO_STYLESHEETS="$(JBM_STYLESHEETS)" uv run jupyter-book build --html --strict

book-start:
	cd docs && JUPYTER_BOOK_MARIMO_STYLESHEETS="$(JBM_STYLESHEETS)" uv run jupyter-book start --port 3102 --server-port 4102

clean:
	rm -rf dist _build _site .jupyter-book-marimo docs/_build docs/_site docs/.jupyter-book-marimo
	find src tests -type d -name __pycache__ -prune -exec rm -rf {} +
