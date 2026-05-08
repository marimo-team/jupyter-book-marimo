# marimo + jupyter-book = 🌴 📖 ❤️

`jupyter-book-marimo` is a Jupyter Book executable plugin that renders
marimo-marked Python, SQL, and Markdown fences as hydrated marimo islands.

Use it when you want normal MyST pages with reactive marimo cells embedded
inside the Jupyter Book site.

> [!NOTE]
> This plugin requires `marimo>=0.23.5` and Python 3.12+.

## Quick Start

**1.** Install the plugin in the same environment as Jupyter Book.

```bash
uv add jupyter-book-marimo
```

For local development from this repo:

```bash
uv sync --dev
```

**2.** Register the executable plugin in `myst.yml`.

```yaml
project:
  plugins:
    - type: executable
      path: .venv/bin/jupyter-book-marimo
```

Use the path that matches your environment. In this repo's example book, the
docs live in `docs/`, so the path is `../.venv/bin/jupyter-book-marimo`.

**3.** Author marimo cells as ordinary MyST language fences.

````markdown
```python {.marimo}
import marimo as mo

slider = mo.ui.slider(start=1, stop=10, label="count")
slider
```

```python {.marimo}
"*" * slider.value
```
````

**4.** Build the book.

```bash
jupyter-book build --html
```

## Features

The plugin keeps the authoring surface close to MyST:

| Feature           | How                                 |
| ----------------- | ----------------------------------- |
| Python cells      | ` ```python {.marimo} `             |
| SQL cells         | ` ```sql {.marimo query="result"} ` |
| Markdown cells    | ` ```markdown {.marimo} `           |
| Editable code     | `editor="true"`                     |
| Show source       | `echo="true"`                       |
| Hide source       | `hide_code="true"`                  |
| Hide output       | `hide_output="true"`                |
| Disable execution | `disabled="true"`                   |

Cells render output only by default.

## Page Dependencies

Add `options.marimo.pyproject` frontmatter to declare page-local dependencies.
The plugin converts this metadata into `uv run` arguments using marimo's
sandbox logic.

```yaml
---
options:
  marimo:
    pyproject: |
      requires-python = ">=3.12"
      dependencies = [
          "pandas",
          "marimo>=0.23.5",
      ]
---
```

Pages without `options.marimo.pyproject` execute in-process.

## Example Book

This repo includes a small Jupyter Book in `docs/`. It is an integration
fixture for `jupyter-book-marimo`, not a general Jupyter Book publishing guide.

```bash
make book-build
make book-start
```

For subpath deployments, pass the public path through `BASE_URL`:

```bash
BASE_URL=/projects/marimo/jupyter-book-marimo/docs make book-build
```

During a book build, the plugin writes
`docs/.jupyter-book-marimo/container-widget.mjs`. That directory is generated
output: it gives Jupyter Book a same-origin ESM file for the anywidget bridge,
while the source of truth stays in
`src/jupyter_book_marimo/assets/container-widget.mjs`.

For Jupyter Book build, hosting, and publishing details outside this plugin's
integration surface, use the official Jupyter Book docs:
https://jupyterbook.org/stable/build-and-publish/

The docs are intentionally an application surface for the plugin: the root page
shows the basic setup, and the tutorial pages exercise marimo output,
reactivity, layouts, SQL, Markdown, and page-local dependencies.

## Development

```bash
make check       # format check, lint, typecheck, tests, build
make test        # tests only
make book-build  # strict static HTML Jupyter Book build
```

Please see `CONTRIBUTING.md` for the full local workflow.
