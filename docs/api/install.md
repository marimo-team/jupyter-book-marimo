---
title: Getting started
---

# Getting started

Install `jupyter-book-marimo` into the same Python environment as Jupyter Book.

```bash
pip install jupyter-book-marimo
```

For local development from this repository:

```bash
uv sync --dev
```

Register the executable plugin in `myst.yml`:

```yaml
project:
  plugins:
    - type: executable
      path: .venv/bin/jupyter-book-marimo
```

Use the executable path for your environment. In this repository, the docs app lives in
`docs/`, so `docs/myst.yml` points at:

```yaml
project:
  plugins:
    - type: executable
      path: ../.venv/bin/jupyter-book-marimo
```

Build the book normally:

```bash
jupyter-book build --html
```

In this repository:

```bash
make book-build
make book-start
```
