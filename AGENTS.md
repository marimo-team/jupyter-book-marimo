# AGENTS.md

This file gives coding agents the repo map and the commands that matter.

## Build & Test Commands

```bash
# Full local gate
make check

# Lint and type-check only
make format-check
make lint
make typecheck

# Tests only
make test

# Build the package
make build

# Build the example Jupyter Book as static HTML
make book-build

# Serve the example book locally
make book-start
```

## Architecture

This is a Jupyter Book executable plugin that turns MyST code fences marked
with `.marimo` into hydrated marimo islands.

### Plugin entrypoint (`src/jupyter_book_marimo/plugin.py`)

Jupyter Book invokes the `jupyter-book-marimo` console script as a MyST
executable plugin. The plugin advertises one document transform,
`marimo-code-fences`, and replaces supported code nodes with `anywidget` nodes.

The transform:

1. Scans the MyST document for Python, SQL, and Markdown fences marked
   `.marimo`.
2. Reads page-level metadata from the `options.marimo` YAML frontmatter
   namespace.
3. Executes the collected cells through `runtime.py`.
4. Copies `container-widget.mjs` into `.jupyter-book-marimo/` so Jupyter Book
   can serve the anywidget bridge as a same-origin ESM asset.
5. Emits a MyST `anywidget` node for each marimo output.

### Extractor (`src/jupyter_book_marimo/extract.py`)

The extractor owns marimo execution. It builds a `MarimoIslandGenerator`, runs
the page until completion, captures runtime assets, and returns one output model
per executable cell.

The browser runtime and the server export do not share generated cell IDs, so
the extractor rewrites islands to use browser cell indexes and injects a stable
page-local `CellManager` prefix into the exported notebook code.

### Runtime bridge (`src/jupyter_book_marimo/assets/container-widget.mjs`)

Jupyter Book renders anywidgets in a shadow root. marimo islands expect light
DOM and a hidden notebook source node. The container widget is the boundary
between those systems and is served as a same-origin bridge asset; marimo's
island runtime URLs still come from marimo's generated island head.

The generated `.jupyter-book-marimo/` directory is only the served copy of that
bridge; the maintained source is
`src/jupyter_book_marimo/assets/container-widget.mjs`.

It mounts the marimo output into light DOM, retains one notebook source node per
app, loads marimo island assets once, installs plugin styling, mirrors theme
state into nested shadow roots, and forces document navigation for same-origin
page changes so Jupyter Book does not reuse a stale marimo runtime bridge.

### Authoring parser (`src/jupyter_book_marimo/authoring.py`)

Authoring concerns live in one small parser module. It reads YAML frontmatter
with PyYAML, extracts `options.marimo`, parses `.marimo` fence attributes, and
normalizes execution options shared by the plugin and extractor.

Page-level dependencies live in `options.marimo.pyproject` YAML frontmatter.
`runtime.py` converts that TOML block into `uv run` arguments by reusing
marimo's sandbox parsing instead of maintaining a second dependency parser.

## Authoring Surface

Use ordinary MyST language fences with the `.marimo` class:

````markdown
```python {.marimo}
import marimo as mo

mo.md("hello")
```
````

Supported languages are `python`, `sql`, and `markdown`. Options live in the
same attribute block: `eval`, `echo`, `editor`, `hide_code`, `hide_output`,
`disabled`, `unparseable`, `include`, and SQL-specific options such as `query`.

Page-level metadata is written under the `options.marimo` YAML frontmatter key:

```yaml
---
options:
  marimo:
    header: |
      # Python inserted before exported notebook code
    pyproject: |
      requires-python = ">=3.10"
      dependencies = ["pandas", "marimo>=0.23.5"]
---
```

## Project Structure

```text
jupyter-book-marimo/
├── src/jupyter_book_marimo/
│   ├── plugin.py                 # MyST executable plugin entrypoint
│   ├── authoring.py              # fence, frontmatter, and execution options
│   ├── extract.py                # marimo execution and island export
│   ├── runtime.py                # in-process vs uv sandbox execution
│   └── assets/container-widget.mjs
├── tests/                        # pytest unit tests
├── docs/                         # example Jupyter Book application surface
├── Makefile
└── pyproject.toml
```

## Development Notes

- Keep generated output out of commits: `dist/`, `docs/_build/`,
  `docs/_site/`, and `docs/.jupyter-book-marimo/` are build artifacts.
- Prefer `make check` before handoff. It runs format check, lint, type-check,
  tests, and package build.
- Use `make book-build` after changes to docs, MyST parsing, runtime assets, or
  browser hydration behavior.
- If browser behavior changes, verify the built book with `agent-browser` or an
  equivalent real browser run. Static tests are not enough for the widget/theme
  boundary.
