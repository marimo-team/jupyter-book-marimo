# jupyter-book-marimo

`jupyter-book-marimo` turns MyST-native `{marimo}` directives into hydrated marimo
islands in a Jupyter Book site.

Authors write Python, SQL, or Markdown cells in normal MyST pages. During the book
build, the executable plugin runs those cells and emits static HTML. In the browser,
marimo hydrates the outputs so controls, tables, plots, SQL results, and dependent cells
stay reactive.

Requires Python 3.10+. The package installs marimo for page execution.

## Quick Start

Install the plugin in the same environment as Jupyter Book:

```bash
pip install jupyter-book-marimo
```

For uv-managed projects, use:

```bash
uv add jupyter-book-marimo
```

Register the executable plugin in `myst.yml`:

```yaml
project:
  plugins:
    - type: executable
      path: .venv/bin/jupyter-book-marimo
```

Use the executable path that matches your environment. In this repo's docs site, the
docs live in `docs/`, so the path is `../.venv/bin/jupyter-book-marimo`.

Write marimo cells as MyST directives:

````markdown
```{marimo} python
import marimo as mo

slider = mo.ui.slider(start=1, stop=10, label="islands")
slider
```

```{marimo} python
"🏝️" * slider.value
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

Build the book:

```bash
jupyter-book build --html
```

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
