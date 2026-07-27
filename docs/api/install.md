---
title: Getting started
---

# Getting started

Install `jupyter-book-marimo` into the same Python environment that builds your Jupyter
Book.

```bash
pip install jupyter-book-marimo
```

For a uv-managed book project, add it as a dependency:

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

Set `path` to the plugin executable for the environment that runs `jupyter-book build`.
The path is resolved from the book source directory. In this repository, `myst.yml`
lives in `docs/` and the virtual environment lives one directory up:

```yaml
project:
  plugins:
    - type: executable
      path: ../.venv/bin/jupyter-book-marimo
```

On Windows, use the executable under `Scripts`:

```yaml
project:
  plugins:
    - type: executable
      path: .venv/Scripts/jupyter-book-marimo.exe
```

Build the book normally:

```bash
jupyter-book build --html
```

In this repository, run the docs build through the Makefile:

```bash
make book-build
make book-start
```

`make book-build` runs Jupyter Book with `--strict`. `make book-start` serves the built
site on `http://localhost:3102`.

## First Page

Add a marimo cell to any MyST Markdown page:

````markdown
```{marimo} python
import marimo as mo

slider = mo.ui.slider(start=1, stop=10, label="islands")
slider
```

```{marimo} python
mo.md(f"The slider is set to **{slider.value}**.")
```
````

The build executes the page and writes a static preview. The browser hydrates the same
cells so the slider can update the Markdown output.
