JBM_STYLESHEETS ?=
PYTHON_PATHS := src tests scripts
DENO_FORMAT_PATHS := deno.json widget README.md CONTRIBUTING.md releasing.md .github/pull_request_template.md docs/index.md docs/api docs/myst.yml docs/styles/jupyter-book-marimo.css
WIDGET_ENTRY := widget/container-widget.ts
WIDGET_BUNDLE := src/jupyter_book_marimo/assets/container-widget.mjs

.PHONY: format lint test check release-check build package-smoke widget-build book-build book-start clean

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

test:
	uv run pytest tests
	uv run deno test widget

check: lint test build package-smoke book-build

release-check: check

build:
	rm -f dist/jupyter_book_marimo-*.whl dist/jupyter_book_marimo-*.tar.gz
	@tmp=$$(mktemp); \
	uv run python scripts/bundle_widget.py "$$tmp"; \
	if ! cmp -s "$$tmp" "$(WIDGET_BUNDLE)"; then \
		echo "$(WIDGET_BUNDLE) is out of date; run make widget-build"; \
		rm -f "$$tmp"; \
		exit 1; \
	fi; \
	rm -f "$$tmp"
	uv build

package-smoke: build
	uv run python scripts/smoke_package.py

book-build:
	cd docs && JUPYTER_BOOK_MARIMO_STYLESHEETS="$(JBM_STYLESHEETS)" uv run jupyter-book build --html --strict

book-start:
	cd docs && JUPYTER_BOOK_MARIMO_STYLESHEETS="$(JBM_STYLESHEETS)" uv run jupyter-book start --port 3102 --server-port 4102

clean:
	rm -rf dist _build _site .jupyter-book-marimo docs/_build docs/_site docs/.jupyter-book-marimo
	find $(PYTHON_PATHS) -type d -name __pycache__ -prune -exec rm -rf {} +
