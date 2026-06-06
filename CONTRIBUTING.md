# Contributing to jupyter-book-marimo

Work from the repository root. `uv` installs the package, the development tools, Jupyter
Book, and the Deno runtime used by the widget project.

## Prerequisites

| Tool                             | Purpose                                         |
| -------------------------------- | ----------------------------------------------- |
| [uv](https://docs.astral.sh/uv/) | Manages Python, dependencies, tests, and builds |
| Python 3.10+                     | Required by the package                         |

Install dependencies from the repo root:

```bash
uv python install "$(cat .python-version)"
uv sync --dev
```

`uv` creates and maintains `.venv/`.

## Development Workflow

### Make targets

| Command             | What it does                                                |
| ------------------- | ----------------------------------------------------------- |
| `make format`       | Format Python, widget TypeScript, and maintained Markdown   |
| `make lint`         | Check formatting, lint Python and TypeScript, and typecheck |
| `make test`         | Run Python and widget tests                                 |
| `make build`        | Regenerate the widget bundle and build wheel and sdist      |
| `make book-build`   | Build docs as strict static HTML                            |
| `make check`        | Run lint, tests, build, and strict docs build               |
| `make widget-build` | Regenerate only the packaged widget bundle                  |
| `make book-start`   | Serve docs locally                                          |
| `make clean`        | Delete build artifacts                                      |

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

### Building docs

```bash
make book-build
```

For subpath deployments, set `BASE_URL` to the public path before building:

```bash
BASE_URL=/your/deployment/path make book-build
```

The GitHub Pages workflow uses `BASE_URL=/jupyter-book-marimo`.

The docs in `docs/` are the application surface for this plugin. Keep them small and
exercise the real Jupyter Book executable plugin path.

`docs/tutorials/` is generated from upstream marimo tutorials. Do not edit those files
by hand in this repository. Change the upstream source or the export script instead.
Keep repo-owned documentation changes in `docs/api/`, `docs/index.md`, `docs/myst.yml`,
and `docs/styles/`.

Keep this repo focused on the marimo + Jupyter Book integration. For general Jupyter
Book build, hosting, and publishing mechanics, point contributors to the official docs:
https://jupyterbook.org/stable/build-and-publish/

The widget source of truth is `widget/`. `make build` regenerates the packaged bundle
before building the Python artifacts. Use `make widget-build` when you only need to
refresh `src/jupyter_book_marimo/assets/container-widget.mjs`.

Do not manually edit generated widget copies:
`src/jupyter_book_marimo/assets/container-widget.mjs` or
`docs/.jupyter-book-marimo/container-widget.mjs`.

## Project Structure

```text
jupyter-book-marimo/
├── src/jupyter_book_marimo/
│   ├── plugin.py                 # MyST executable plugin entrypoint
│   ├── authoring.py              # directive validation and execution options
│   ├── extract.py                # marimo execution and island export
│   ├── runtime.py                # subprocess extraction and uv sandbox execution
│   └── assets/container-widget.mjs # generated Deno bundle packaged at runtime
├── widget/                       # TypeScript source for the anywidget bridge
├── scripts/bundle_widget.py      # Deno bundle writer for the packaged bridge
├── tests/                        # pytest unit tests
├── docs/                         # Jupyter Book docs application surface
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

## Releases

Releases are cut from a clean `main` branch with an explicit final version such as
`./scripts/release.sh 0.1.0`, or with `./scripts/release.sh patch` or
`./scripts/release.sh minor` after the package is on a final version. The script bumps
`pyproject.toml`, refreshes `uv.lock`, runs `make check`, commits the version, and
creates a semver tag. See `releasing.md` for the full release gate and workflow.

Pushing the tag starts `.github/workflows/publish.yml`. The workflow builds the package,
uploads `dist`, publishes with `uv publish --trusted-publishing always`, and creates
GitHub release notes. PyPI Trusted Publishing is configured for the `pypi` GitHub
environment.

## Submitting a Pull Request

1. Fork the repo and create a branch from `main`.
2. Make your changes and add tests for new behavior.
3. Run `make check`.
4. Run a browser check for docs, plugin, runtime, widget, styling, or navigation
   changes.
5. Open a PR. The template lists the expected checks.

Every bug fix should include a regression test when unit tests can cover the behavior.
Browser-only regressions should include a clear manual validation note.
