---
title: jupyter-book-marimo
---

```{marimo-config}
:header: # Copyright 2026 Marimo. All rights reserved
```

Reactive marimo cells for Jupyter Book.

## Example

Static HTML, live marimo islands. The build executes the Python cells below, and the
browser hydrates the same output so the slider can update dependent Markdown.

```{marimo} python
:editor: true

import marimo as mo

demo_count = mo.ui.slider(start=1, stop=10, label="islands")
demo_count
```

```{marimo} python
mo.md(f"Static HTML, live islands: {'🏝️' * demo_count.value}")
```

## Build and hydration

The two cells above are ordinary MyST `{marimo}` directives. At build time,
`jupyter-book-marimo` executes them with marimo and writes the rendered output into the
book. In the browser, marimo hydrates the same islands so the slider can still update
the dependent Markdown output.

## Quickstart

Install the package:

```bash
pip install jupyter-book-marimo
```

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

## Reference

- [Get started](api/install.md) with installation and `myst.yml` setup.
- Use the [reference](api/index.md) for directive syntax, page configuration, styling,
  and runtime assets.
- Open the [tutorials](tutorials/index.md) for marimo examples rendered through the
  plugin. Tutorial pages are separate from the API reference.
