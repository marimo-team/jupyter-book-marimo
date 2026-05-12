JBM_STYLESHEETS ?= styles/jupyter-book-marimo.css

.PHONY: format format-check lint typecheck test check build book-build book-start clean

format:
	uv run ruff format src tests

format-check:
	uv run ruff format --check src tests

lint:
	uv run ruff check src tests

typecheck:
	uv run ty check src

test:
	uv run pytest tests

check: format-check lint typecheck test build

build:
	uv build

book-build:
	cd docs && JUPYTER_BOOK_MARIMO_STYLESHEETS="$(JBM_STYLESHEETS)" uv run jupyter-book build --html --strict

book-start:
	cd docs && JUPYTER_BOOK_MARIMO_STYLESHEETS="$(JBM_STYLESHEETS)" uv run jupyter-book start --port 3102 --server-port 4102

clean:
	rm -rf dist _build _site .jupyter-book-marimo docs/_build docs/_site docs/.jupyter-book-marimo
	find src tests -type d -name __pycache__ -prune -exec rm -rf {} +
