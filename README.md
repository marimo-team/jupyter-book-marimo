# marimo + Jupyter Book

marimo is a reactive Python notebook that can be embedded in static documents. This repo
is a Jupyter Book executable plugin that lets you write marimo cells in MyST pages and
publish a static book whose controls, tables, plots, SQL results, and dependent cells
still respond in the browser.

Requires Python 3.10+. The package installs marimo for page execution.

## Quick Start

**1.** Install the plugin in the same environment as Jupyter Book:

```bash
pip install jupyter-book-marimo
```

For uv-managed projects, use:

```bash
uv add jupyter-book-marimo
```

**2.** Register the executable plugin in `myst.yml`:

```yaml
project:
  plugins:
    - type: executable
      path: .venv/bin/jupyter-book-marimo
```

Use the executable path that matches your environment. In this repo's docs site, the
docs live in `docs/`, so the path is `../.venv/bin/jupyter-book-marimo`.

**3.** Edit a MyST page:

````markdown
---
title: My reactive page
---

# A reactive page

```{marimo} python
import marimo as mo

slider = mo.ui.slider(start=1, stop=10, step=1, label="items")
slider
```

```{marimo} python
mo.md(f"The slider is set to **{slider.value}**.")
```
````

Set page defaults or page-local dependencies with `{marimo-config}`:

````markdown
```{marimo-config}
:echo: true
:pyproject: |
  requires-python = ">=3.10"
  dependencies = ["pandas"]
```
````

**4.** Build the book:

```bash
jupyter-book build --html
```

## Features

`jupyter-book-marimo` uses
[marimo islands](https://docs.marimo.io/guides/exporting/#islands-in-action) so reactive
notebook content can live between ordinary book sections. The plugin supports Python,
SQL, and Markdown cells, page-level execution defaults, page-local dependencies, custom
styling hooks, and static HTML output that hydrates into interactive marimo components
on load.

## Docs

- [Live docs index](docs/index.md): quick proof that static pages hydrate into reactive
  marimo islands.
- [Installation](docs/api/install.md): install the package and register the executable
  plugin.
- [Authoring](docs/api/authoring.md): full `{marimo}` directive option list.
- [Page configuration](docs/api/configuration.md): defaults, headers, and page-local
  dependencies.
- [Styling](docs/api/styling.md): public CSS hooks for book themes.
- [Runtime assets](docs/api/runtime-assets.md): bridge assets, hydration payloads, and
  publishing constraints.

For the full local workflow, see [CONTRIBUTING.md](CONTRIBUTING.md).
