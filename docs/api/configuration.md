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
directive.

| Option            | Type    | Default | Behavior                                         |
| ----------------- | ------- | ------- | ------------------------------------------------ |
| `:eval:`          | boolean | `true`  | default build-time execution                     |
| `:echo:`          | boolean | `false` | default source code rendering                    |
| `:editor:`        | boolean | `false` | default marimo editor rendering                  |
| `:output:`        | boolean | `true`  | default browser output island rendering          |
| `:server-output:` | boolean | `true`  | default build-time preview HTML rendering        |
| `:error:`         | boolean | `true`  | default build behavior for marimo errors         |
| `:include:`       | boolean | `true`  | default page node inclusion                      |
| `:header:`        | string  | none    | Python prepended to generated notebook code      |
| `:molab:`         | boolean | `true`  | page-level Molab launcher                        |
| `:pyproject:`     | string  | none    | page-local dependency metadata for `uv run`      |
| `:external-env:`  | boolean | `false` | use the Jupyter Book Python environment directly |

Set `:server-output: false` at the page level to keep marimo execution and browser
hydration with empty build-time preview HTML for every cell. Individual cells can set
`:server-output: true` when they should keep their static preview.

## Molab launcher

Pages show a Molab launcher by default when they contain included marimo output. The
launcher opens an external Molab page with notebook source generated from the current
page, including surrounding Markdown and executable `{marimo}` directive source when the
plugin can identify and align the source page unambiguously. If Jupyter Book does not
expose a unique source page, or if source line ranges cannot be aligned safely, the
launcher still opens the executable marimo cells. The widget model records the fallback
reason for debugging.

Set `:molab: false` to hide the launcher for a page:

````markdown
```{marimo-config}
:molab: false
```
````

The generated Molab notebook source is separate from the in-page output source. It is
attached to the first included marimo output on the page so the external launcher can
open the authored page content and the rendered cell result.

## Page-local dependencies

Declare dependencies with `:pyproject:`:

````markdown
```{marimo-config}
:pyproject: |
  requires-python = ">=3.10"
  dependencies = [
      "pandas",
  ]
```
````

When `:pyproject:` is present, the page runs through `uv` using marimo's sandbox
metadata parser. The plugin adds marimo to the `uv run` invocation, so page metadata
only needs the dependencies used by that page. `:pyproject:` isolates dependency
resolution. It is not a security sandbox for filesystem, process, or network access.

Use `:external-env: true` to execute with the Python environment that runs Jupyter Book.
`:pyproject:` and `:external-env: true` are mutually exclusive.
