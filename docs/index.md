---
title: marimo + jupyter-book
options:
  marimo:
    header: |
      # Copyright 2026 Marimo. All rights reserved
---

# marimo + jupyter-book = 🌴 📖 ❤️

Write normal MyST pages, mark selected code fences as marimo cells, and let
Jupyter Book build a static site with hydrated reactive output.

`jupyter-book-marimo` is a Jupyter Book executable plugin. During the book
build, Jupyter Book sends each page to the plugin; the plugin executes
`.marimo` fences, captures the marimo island runtime assets, and returns output
that the Jupyter Book theme can hydrate in the browser.

## What it gives you

- reactive Python cells inside regular `.md` source files
- browser-side marimo UI controls that keep working after the static build
- page-local Python dependencies through `uv` metadata
- the normal Jupyter Book surface: table of contents, search, and
  publication-ready MyST pages

## Authoring model

Author cells as ordinary MyST code fences with the `.marimo` class:

````markdown
```python {.marimo}
import marimo as mo

mo.md("Hello from marimo")
```
````

The output below is rendered by this book's own plugin configuration in
`docs/myst.yml`.

```python {.marimo}
import marimo as mo

demo_slider = mo.ui.slider(start=1, stop=10, label="island count")
demo_slider
```

```python {.marimo editor="true"}
demo_result = "🏝️" * demo_slider.value
demo_result
```

## Configuration

This docs site uses the plugin exactly as an application would:

```yaml
project:
  plugins:
    - type: executable
      path: ../.venv/bin/jupyter-book-marimo
```

Pages can opt into a sandbox by adding `options.marimo.pyproject` frontmatter
with dependencies. The plugin runs those pages with `uv`, then emits
same-origin runtime assets for the static site.

The build also creates `.jupyter-book-marimo/container-widget.mjs`. That file is
a generated same-origin copy of the packaged anywidget bridge; edit
`src/jupyter_book_marimo/assets/container-widget.mjs` instead.

For Jupyter Book build and publishing details beyond this plugin integration,
use the official Jupyter Book docs:
https://jupyterbook.org/stable/build-and-publish/

## Next

Open the [tutorials](tutorials/index.md) for the marimo examples.
