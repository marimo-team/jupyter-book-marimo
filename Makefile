PYTHON_PATHS := src tests scripts
DENO_FORMAT_PATHS := deno.json widget docs/api docs/styles
DENO_FORMAT_PATHS += README.md CONTRIBUTING.md releasing.md
DENO_FORMAT_PATHS += .github/*.md docs/*.md docs/*.yml
WIDGET_ENTRY := widget/index.ts

.PHONY: format lint test check build widget-build book-build book-start clean

format:
	uv run ruff format $(PYTHON_PATHS)
	uv run deno fmt $(DENO_FORMAT_PATHS)

lint:
	uv run ruff format --check $(PYTHON_PATHS)
	uv run ruff check $(PYTHON_PATHS)
	uv run ty check src scripts
	uv run deno fmt --check $(DENO_FORMAT_PATHS)
	uv run deno lint widget
	uv run deno check $(WIDGET_ENTRY)

widget-build:
	uv run python scripts/bundle_widget.py

test: widget-build
	uv run pytest tests
	uv run deno test widget

check: lint test build book-build

build:
	rm -f dist/jupyter_book_marimo-*.whl dist/jupyter_book_marimo-*.tar.gz
	uv build

book-build: widget-build
	cd docs && uv run jupyter-book build --html --strict

book-start:
	cd docs && uv run jupyter-book start --port 3102 --server-port 4102

clean:
	rm -rf dist _build _site .jupyter-book-marimo docs/_build docs/_site docs/.jupyter-book-marimo
	rm -f src/jupyter_book_marimo/assets/container-widget.mjs src/jupyter_book_marimo/assets/islands-bridge.css
	find $(PYTHON_PATHS) -type d -name __pycache__ -prune -exec rm -rf {} +
