---
title: Page configuration
---

# Page configuration

Use one `{marimo-config}` directive per page to set defaults for the page execution
graph.

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

| Option            | Type    | Default | Behavior                                              |
| ----------------- | ------- | ------- | ----------------------------------------------------- |
| `:eval:`          | boolean | `true`  | Default build-time execution for cells                |
| `:echo:`          | boolean | `false` | Default static source rendering                       |
| `:editor:`        | boolean | `false` | Default marimo editor rendering                       |
| `:output:`        | boolean | `true`  | Default browser output island rendering               |
| `:server-output:` | boolean | `true`  | Default build-time preview HTML rendering             |
| `:error:`         | boolean | `true`  | Default build behavior for marimo error output        |
| `:include:`       | boolean | `true`  | Default visible node inclusion                        |
| `:header:`        | string  | none    | Python source prepended to the generated notebook     |
| `:molab:`         | boolean | `true`  | Enable the page-level Molab launcher                  |
| `:pyproject:`     | string  | none    | Page-local dependency metadata for `uv run`           |
| `:external-env:`  | boolean | `false` | Run extraction in the Jupyter Book Python environment |

Unsupported config options fail the build before execution. `hide-code`, `hide-output`,
`disabled`, `unparsable`, `name`, and `column` are cell options. Set them on `{marimo}`
directives, not on `{marimo-config}`.

## Header Code

`header` is Python source inserted before the generated marimo cells. Use it for shared
imports, helper functions, or setup that every cell on the page can read.

````markdown
```{marimo-config}
:header: |
  import marimo as mo
  from pathlib import Path
```
````

Header code executes during the build and is included in the browser hydration source.
Treat it like public page source when publishing a static book.

## Molab Launcher

Pages show a Molab launcher by default when they contain included marimo output. The
launcher opens generated notebook source for the current page.

When the plugin can match the MyST source page and directive line ranges, the Molab
notebook includes surrounding Markdown plus executable `{marimo}` cells. When the source
page cannot be matched safely, the launcher still opens the executable marimo cells and
records a fallback reason in the widget model for debugging.

Set `:molab: false` to hide the launcher for a page:

````markdown
```{marimo-config}
:molab: false
```
````

The Molab notebook source is separate from the in-page hydration source. It is attached
to the first included marimo output on the page.

## Page-Local Dependencies

Declare page dependencies with `pyproject` metadata:

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
metadata parser. The plugin adds `marimo>=0.23.8` to the `uv run` invocation, so page
metadata only needs the dependencies used by that page.

`pyproject` isolates dependency resolution. It is not a security sandbox for filesystem,
process, or network access.

Use `:external-env: true` when the page should execute in the Python environment that
runs Jupyter Book:

````markdown
```{marimo-config}
:external-env: true
```
````

`:pyproject:` and `:external-env: true` are mutually exclusive.
