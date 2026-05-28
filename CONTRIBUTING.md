# Contributing to jupyter-book-marimo

Set up the development environment from the repository root.

## Prerequisites

| Tool                             | Purpose                                               |
| -------------------------------- | ----------------------------------------------------- |
| [uv](https://docs.astral.sh/uv/) | Manages Python, dependencies, tests, and builds       |
| Python 3.10+                     | Required by the package                               |
| Jupyter Book >=2.1.5             | Builds the docs site through the dev dependency group |

Install dependencies from the repo root:

```bash
uv sync --dev
```

`uv` creates and maintains `.venv/`.

## Development Workflow

### Make targets

| Command             | What it does                                                  |
| ------------------- | ------------------------------------------------------------- |
| `make format`       | Format Python, widget TypeScript, and docs Markdown           |
| `make lint`         | Check formatting, lint Python and TypeScript, and type-check  |
| `make test`         | Run Python and widget tests                                   |
| `make check`        | Run lint, tests, bundle freshness checks, and package build   |
| `make build`        | Check the widget bundle and build the package with `uv build` |
| `make widget-build` | Regenerate the packaged widget bundle after editing `widget/` |
| `make book-build`   | Build docs as strict static HTML                              |
| `make book-start`   | Serve docs locally                                            |
| `make clean`        | Delete build artifacts                                        |

### Linting and formatting

```bash
make lint

# Auto-format
make format
```

### Running tests

```bash
make test

# Run a single test
uv run pytest tests/test_extract.py::test_reactive_islands_use_browser_cell_indexes
```

### Building Docs

```bash
make book-build
```

For subpath deployments, set `BASE_URL` before building:

```bash
BASE_URL=/projects/marimo/jupyter-book-marimo/docs make book-build
```

The docs in `docs/` are the application surface for this plugin. Keep them small and
exercise the real Jupyter Book executable plugin path.

`docs/tutorials/` is generated from upstream marimo tutorials. Do not edit those files
by hand in this repository. Change the upstream source or the export script instead.

Keep this repo focused on the marimo + Jupyter Book integration. For general Jupyter
Book build, hosting, and publishing mechanics, point contributors to the official docs:
https://jupyterbook.org/stable/build-and-publish/

The widget source of truth is `widget/`. Run `make widget-build` after editing the
TypeScript source. Do not manually edit either generated copy:
`src/jupyter_book_marimo/assets/container-widget.mjs` or
`docs/.jupyter-book-marimo/container-widget.mjs`.

## Project Structure

```text
jupyter-book-marimo/
├── src/jupyter_book_marimo/
│   ├── plugin.py                 # MyST executable plugin entrypoint
│   ├── authoring.py              # frontmatter, fence parsing, execution options
│   ├── extract.py                # marimo execution and island export
│   ├── runtime.py                # sandbox dispatch
│   └── assets/container-widget.mjs # generated browser ESM bundle
├── widget/                       # TypeScript source for the bridge
├── tests/                        # pytest unit tests
├── docs/                         # Jupyter Book docs site
└── Makefile
```

## Browser Validation

Unit tests cover parsing and extraction contracts. They do not fully cover Jupyter Book
hydration, shadow-root rendering, theme behavior, or client-side navigation. For changes
touching `container-widget.mjs`, island output, docs styling, or page navigation, build
the book and check it in a browser.

Local browser check:

```bash
make book-build
make book-start
```

Then open `http://localhost:3102`, interact with the index slider, toggle light/dark
mode, and click through the tutorial pages.

## Submitting a Pull Request

1. Fork the repo and create a branch from `main`.
2. Make your changes and add tests for new behavior.
3. Run `make check`.
4. Run `make book-build` for docs, plugin, or runtime changes.
5. Open a PR. The template lists the expected checks.

Every bug fix should include a regression test when unit tests can cover the behavior.
Browser-only regressions should include a clear manual validation note.
