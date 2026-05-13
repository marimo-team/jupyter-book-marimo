---
title: Jupyter Book + marimo = 🏝️❤️📖
---

```{marimo-config}
:header: # Copyright 2026 Marimo. All rights reserved
```

# jupyter-book-marimo

Reactive marimo cells in Jupyter Book.

```bash
pip install jupyter-book-marimo
```

Add the executable plugin to `myst.yml`, write `{marimo}` cells in MyST Markdown, and
build your book as usual. At build time, `jupyter-book-marimo` executes the marimo cells
and emits static HTML. In the browser, marimo hydrates those islands so sliders, tables,
plots, SQL results, and dependent outputs stay reactive.

## Quickstart

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

## Try it

This page was built the same way. The Python cell ran during the book build; the slider
and output still update after the page is served as static HTML.

```{marimo} python
:editor: true

import marimo as mo

demo_count = mo.ui.slider(start=1, stop=10, label="islands")
demo_count
```

```{marimo} python
mo.md(f"Static HTML, live islands: {'🏝️' * demo_count.value}")
```

## Next steps

- [Get started](api/install.md) with installation and `myst.yml` setup.
- Use the [reference](api/index.md) for cell syntax, page configuration, styling, and
  runtime assets.
- Open the [tutorials](tutorials/index.md) for marimo examples in a Jupyter Book.

## Use it for

- runnable examples in normal `.md` docs;
- reactive UI controls in static sites;
- plots, tables, SQL results, and Markdown output inside Jupyter Book pages;
- page-local dependencies for examples that need extra packages; and
- Jupyter Book navigation, search, and publishing around marimo outputs.
