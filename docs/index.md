---
title: Jupyter Book + marimo = 🏝️❤️📖
---

```{marimo-config}
:header: # Copyright 2026 Marimo. All rights reserved
```

`jupyter-book-marimo` adds reactive marimo cells to Jupyter Book.

## Try it

This page is static HTML with live marimo islands. The Python cell ran during the book
build; the slider and output still update after the page is served.

```{marimo} python
:editor: true

import marimo as mo

demo_count = mo.ui.slider(start=1, stop=10, label="islands")
demo_count
```

```{marimo} python
mo.md(f"Static HTML, live islands: {'🏝️' * demo_count.value}")
```

## Quickstart

Install the package:

```bash
pip install jupyter-book-marimo
```

Add the executable plugin to `myst.yml`, write `{marimo}` cells in MyST Markdown, and
build your book as usual. At build time, `jupyter-book-marimo` executes the marimo cells
and emits static HTML. In the browser, marimo hydrates those islands so sliders, tables,
plots, SQL results, and dependent outputs stay reactive.

Register the plugin:

```yaml
project:
  plugins:
    - type: executable
      path: .venv/bin/jupyter-book-marimo
```

Write marimo cells in a Markdown page:

````markdown
```{marimo} python
:editor: true

import marimo as mo

slider = mo.ui.slider(start=1, stop=10, label="islands")
slider
```

```{marimo} python
"🏝️" * slider.value
```
````

Build the book:

```bash
jupyter-book build --html
```

## Next steps

- [Get started](api/install.md) with installation and `myst.yml` setup.
- Use the [reference](api/index.md) for cell syntax, page configuration, styling, and
  runtime assets.
- Open the [tutorials](tutorials/index.md) for marimo examples in a Jupyter Book.

Use this for runnable documentation examples, reactive controls, plots, SQL results, and
page-local dependencies inside Jupyter Book.
