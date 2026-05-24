---
title: Page configuration
---

# Page configuration

Use one `{marimo-config}` directive per page to set page-level defaults, dependency
metadata, and Molab export behavior.

````markdown
```{marimo-config}
:header: |
  import marimo as mo
:echo: true
:output: true
```
````

Cell options override page defaults. A page may contain at most one `{marimo-config}`
directive; unknown options fail the build.

| Option           | Type    | Default | Behavior                                       |
| ---------------- | ------- | ------- | ---------------------------------------------- |
| `:eval:`         | boolean | `true`  | default cell execution behavior                |
| `:echo:`         | boolean | `false` | default source visibility                      |
| `:editor:`       | boolean | `false` | default editor visibility                      |
| `:output:`       | boolean | `true`  | default output visibility                      |
| `:error:`        | boolean | `true`  | default build behavior for marimo errors       |
| `:include:`      | boolean | `true`  | default page inclusion                         |
| `:header:`       | string  | none    | Python inserted before exported notebook code  |
| `:molab:`        | boolean | `true`  | page-level Molab launch behavior               |
| `:pyproject:`    | string  | none    | dependencies for `uv run`                      |
| `:external-env:` | boolean | `false` | declare the default current Python environment |

Cell-only options such as `:hide-code:`, `:hide-output:`, `:disabled:`, `:unparsable:`,
`:query:`, and `:engine:` are not accepted in `{marimo-config}`. Put those on individual
`{marimo}` cells.

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
without `:pyproject:` execute in the current Python process.

Use `:external-env: true` only when you want to declare that default explicitly.
`:external-env:` and `:pyproject:` are mutually exclusive.
