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
| `:warning:`      | default warning handling                       |
| `:include:`      | default page inclusion                         |
| `:header:`       | Python inserted before exported notebook code  |
| `:pyproject:`    | dependencies for `uv run`                      |
| `:external-env:` | declare the default current Python environment |

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
