---
title: Page configuration
---

# Page configuration

Use one `{marimo-config}` directive to set defaults for every marimo cell on a page:

````markdown
```{marimo-config}
:header: |
  import marimo as mo
:echo: true
:output: true
```
````

Cell options override page defaults.

| Option            | Type    | Default | Behavior                                      |
| ----------------- | ------- | ------- | --------------------------------------------- |
| `:eval:`          | boolean | `true`  | Execute cells during the build                |
| `:echo:`          | boolean | `false` | Render cell source                            |
| `:editor:`        | boolean | `false` | Render a marimo editor                        |
| `:output:`        | boolean | `true`  | Render browser output                         |
| `:server-output:` | boolean | `true`  | Include the build-time HTML preview           |
| `:error:`         | boolean | `true`  | Render marimo error output                    |
| `:include:`       | boolean | `true`  | Project a visible node for the cell           |
| `:header:`        | string  | empty   | Execute shared Python setup before page cells |
| `:pyproject:`     | string  | empty   | Resolve a page-local Python environment       |
| `:external-env:`  | boolean | `false` | Use the Jupyter Book Python environment       |

## Header code

`header` joins the page app as a hidden setup cell. Page cells can read names it
defines. The browser receives the same setup source so reactive execution has the same
graph as the build.

````markdown
```{marimo-config}
:header: |
  import marimo as mo
  from pathlib import Path
```
````

## Page-local dependencies

Set `pyproject` to PEP 723-compatible TOML:

````markdown
```{marimo-config}
:pyproject: |
  requires-python = ">=3.10"
  dependencies = [
      "pandas",
  ]
```
````

The plugin runs that page with uv and `marimo>=0.23.15`. Dependency resolution changes
the Python environment. It does not restrict filesystem, process, or network access.

Use `:external-env: true` when the page imports packages already installed beside
Jupyter Book:

````markdown
```{marimo-config}
:external-env: true
```
````

`pyproject` and `external-env` select different execution environments, so one config
cannot combine them.
