# Contributing to jupyter-book-marimo

Work from the repository root. The Deno import map pins the published
`@marimo-team/mdx-marimo` package used for browser bridge imports and generated styles.

Install the Python environment:

```bash
uv python install "$(cat .python-version)"
uv sync --dev
```

The development environment includes the Deno runtime used for TypeScript checks, tests,
and browser bundles.

## Commands

| Command             | Contract                                                      |
| ------------------- | ------------------------------------------------------------- |
| `make format`       | Format Python, TypeScript, Markdown, YAML, and JSON           |
| `make lint`         | Check formatting, lint, and static types                      |
| `make test`         | Run Python protocol tests and browser-adapter tests           |
| `make widget-build` | Bundle local browser assets for tests and documentation       |
| `make build`        | Build the wheel and source distribution                       |
| `make book-build`   | Build the documentation as strict static HTML                 |
| `make book-start`   | Serve the documentation on `http://localhost:3102`            |
| `make check`        | Run lint, tests, package builds, and the strict documentation |

Run one Python test with:

```bash
uv run pytest tests/test_compiler.py::test_compile_page_emits_protocol_runtime_and_static_output
```

## Repository map

```text
jupyter-book-marimo/
├── src/jupyter_book_marimo/
│   ├── authoring.py       # MyST directive normalization
│   ├── document.py        # document collection and page identity
│   ├── protocol.py        # page request and compiled page types
│   ├── compiler.py        # vendored host-neutral page compiler
│   ├── runner.py          # Python environment selection
│   ├── projection.py      # compiled page to MyST anywidget nodes
│   ├── plugin.py          # executable plugin protocol
│   └── assets/            # package resource namespace
├── widget/                # anywidget adapter for the mdx-marimo bridge
├── scripts/
│   ├── bundle_widget.py   # browser asset bundler
│   └── hatch_build.py     # wheel asset build hook
├── tests/
└── docs/
```

The widget source lives in `widget/`. `make widget-build` writes ignored local copies at
`src/jupyter_book_marimo/assets/container-widget.mjs` and
`src/jupyter_book_marimo/assets/islands-bridge.css`. Hatch runs the same bundler while
building a wheel and includes both files as package resources.

`src/jupyter_book_marimo/compiler.py` is copied unchanged from mdx-marimo's
[`packages/islands-compiler/compiler.py`](https://github.com/marimo-team/mdx-marimo/blob/main/packages/islands-compiler/compiler.py).
Jupyter Book owns directive collection, environment selection, MyST projection, and
widget integration around that compiler.

The generated `.jupyter-book-marimo/` directory is MyST staging output. Edit `widget/`
or the shared bridge stylesheet, then rebuild.

`docs/tutorials/` is generated from upstream marimo tutorials. Keep repository-owned
documentation changes in `docs/api/`, `docs/index.md`, `docs/myst.yml`, and
`docs/styles/`.

## Browser validation

Changes to compilation, projection, browser mounting, styling, packaging, or navigation
require a built-book browser check:

```bash
make book-build
make book-start
```

Open `http://localhost:3102`, interact with the index slider, toggle light and dark
themes, and navigate between pages containing marimo cells. Confirm that the next page
hydrates from the retained runtime and that back navigation restores an interactive
page.

## Releases

Run `./scripts/release.sh 0.1.0` for an explicit release or use `patch` and `minor`
after the first final version. The script updates the version, runs `make check`,
creates the release commit, and creates the tag. See [releasing.md](releasing.md).
