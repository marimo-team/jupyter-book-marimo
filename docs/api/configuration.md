---
title: Page configuration
---

# Page configuration

Use one `{marimo-config}` directive per page to set page-level defaults and dependency
metadata.

````markdown
```{marimo-config}
:header: |
  import marimo as mo
:echo: true
:output: true
```
````

Cell options override page defaults.

| Option           | Meaning                                        |
| ---------------- | ---------------------------------------------- |
| `:eval:`         | default cell execution behavior                |
| `:echo:`         | default source visibility                      |
| `:editor:`       | default editor visibility                      |
| `:output:`       | default output visibility                      |
| `:error:`        | default error handling                         |
| `:include:`      | default page inclusion                         |
| `:header:`       | Python inserted before exported notebook code  |
| `:molab:`        | page-level Molab launch behavior               |
| `:pyproject:`    | dependencies for `uv run`                      |
| `:external-env:` | declare the default current Python environment |

## Molab launcher

Pages show a Molab launcher by default when they contain included marimo output. The
launcher opens an external Molab page with notebook source generated from the current
page, including surrounding Markdown and executable `{marimo}` directive source.

Set `:molab: false` to hide the launcher for a page:

````markdown
```{marimo-config}
:molab: false
```
````

The generated Molab notebook source is separate from the in-page output source. It is
attached to the first included marimo output on the page so the external launcher can
open the authored page content, not just the rendered cell result.

## Page-local dependencies

Declare dependencies with `:pyproject:`:

````markdown
```{marimo-config}
:pyproject: |
  requires-python = ">=3.10"
  dependencies = [
      "pandas",
      "marimo>=0.23.5",
  ]
```
````

Pages with `:pyproject:` run through `uv` using marimo's sandbox metadata parsing. Pages
without `:pyproject:` already execute in the current Python process.

Use `:external-env: true` only when you want to declare that default explicitly.
`:external-env:` and `:pyproject:` are mutually exclusive.
