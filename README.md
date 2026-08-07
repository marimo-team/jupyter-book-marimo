<p align="center">
  <a href="https://marimo-team.github.io/jupyter-book-marimo/">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://marimo-team.github.io/jupyter-book-marimo/assets/brand/jupyter-book-marimo-lockup-stacked-dark.svg">
      <img alt="jupyter-book-marimo" src="https://marimo-team.github.io/jupyter-book-marimo/assets/brand/jupyter-book-marimo-lockup-stacked-light.svg" width="320">
    </picture>
  </a>
</p>

<p align="center">
  <a href="https://github.com/marimo-team/jupyter-book-marimo/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/marimo-team/jupyter-book-marimo/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://pypi.org/project/jupyter-book-marimo/"><img alt="PyPI" src="https://img.shields.io/pypi/v/jupyter-book-marimo.svg"></a>
  <a href="https://spdx.org/licenses/Apache-2.0.html"><img alt="License: Apache 2.0" src="https://img.shields.io/badge/license-Apache%202.0-blue.svg"></a>
</p>

<p align="center"><strong>Make Jupyter Book pages reactive with marimo.</strong></p>

[Jupyter Book](https://jupyterbook.org/) builds books and documentation sites from MyST
Markdown and notebooks. `jupyter-book-marimo` adds reactive Python, SQL, and Markdown
cells to its MyST pages.

The plugin compiles each page's `{marimo}` cells into one marimo app. Jupyter Book
places each result at its authored position and publishes the surrounding book as static
HTML.

The browser runtime then hydrates the shared app so controls and dependent cells stay
interactive across ordinary MyST sections.

Requires Python 3.10 or newer.

## Quick start

Install the plugin in the environment that builds the book:

```bash
pip install jupyter-book-marimo
```

Register its executable in `myst.yml`:

```yaml
project:
  plugins:
    - type: executable
      path: .venv/bin/jupyter-book-marimo
```

Paths are resolved from `myst.yml`. On Windows, use
`.venv/Scripts/jupyter-book-marimo.exe`. A `myst.yml` in `docs/` uses a path beginning
with `../.venv/`.

Write reactive cells in a MyST page:

````markdown
```{marimo} python
import marimo as mo

slider = mo.ui.slider(start=1, stop=10, label="items")
slider
```

```{marimo} python
mo.md(f"The slider is set to **{slider.value}**.")
```
````

Build the book:

```bash
jupyter-book build --html
```

The plugin compiles every page into one marimo app. Each visible cell becomes an island
backed by that shared app, so dataflow continues across ordinary MyST sections. The
static output renders before the browser runtime starts.

Use `{marimo-config}` for page defaults, setup code, and dependencies:

````markdown
```{marimo-config}
:echo: true
:pyproject: |
  requires-python = ">=3.10"
  dependencies = ["pandas"]
```
````

## Documentation

Read the [user documentation](https://marimo-team.github.io/jupyter-book-marimo/) for
authoring options, page configuration, styling, and runtime assets.

See [CONTRIBUTING.md](CONTRIBUTING.md) for local development.
