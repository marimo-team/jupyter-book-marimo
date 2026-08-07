---
title: Authoring cells
---

# Authoring cells

Use the `marimo` MyST directive with an explicit language argument. The language must be
exactly `python`, `sql`, or `markdown`.

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

Python cells can read names defined by earlier cells and by the page header. SQL and
Markdown cells are converted to Python before execution and import marimo internally.

## Cell Options

Write options with standard MyST directive syntax:

````markdown
```{marimo} python
:echo: true
:output: true

import marimo as mo
mo.md("show source and output")
```
````

| Option            | Type    | Default | Behavior                                                           |
| ----------------- | ------- | ------- | ------------------------------------------------------------------ |
| `:eval:`          | boolean | `true`  | Execute the cell during the build                                  |
| `:echo:`          | boolean | `false` | Render source as static code                                       |
| `:editor:`        | boolean | `false` | Render source in a marimo code editor                              |
| `:output:`        | boolean | `true`  | Render the browser output island                                   |
| `:server-output:` | boolean | `true`  | Include build-time preview HTML in the output island               |
| `:error:`         | boolean | `true`  | Render marimo error output instead of failing on error MIME output |
| `:include:`       | boolean | `true`  | Keep this cell's visible node in the page                          |
| `:hide-code:`     | boolean | `false` | Hide rendered source when page defaults would show it              |
| `:hide-output:`   | boolean | `false` | Hide rendered output when page defaults would show it              |
| `:disabled:`      | boolean | `false` | Skip execution and keep optional visible source                    |
| `:unparsable:`    | boolean | `false` | Skip parsing intentionally invalid code                            |
| `:name:`          | string  | none    | Set the marimo cell name                                           |
| `:column:`        | number  | none    | Set the marimo column index                                        |

Unsupported options fail the build before execution. The plugin also rejects a single
directive that explicitly sets both sides of these option pairs:

- `:echo: true` and `:hide-code: true`
- `:output: true` and `:hide-output: true`
- `:eval: true` and `:disabled: true`

Visibility options are presentational. Executed cells are serialized into the static
page so marimo can hydrate islands in the browser. Do not put credentials, private
logic, or untrusted input in cells that ship with a public book.

## Execution And Visibility

`include` controls the visible node, not execution. Use `:include: false` when a cell
should run for downstream cells but should not render code or output in the page. Use
`:eval: false`, `:disabled: true`, or `:unparsable: true` when the cell should not run.

Use `:server-output: false` when a cell should execute and hydrate in the browser with
an empty build-time preview. The page keeps the shared notebook source and runtime
payload. That cell's `<marimo-cell-output>` starts empty.

Use `:error: false` for strict builds. If marimo execution produces an error MIME
renderer, the build fails at that cell. Successful output keeps text, HTML, and other
non-error MIME renderers.

## SQL cells

SQL cells use the same directive with the `sql` language argument:

````markdown
```{marimo} sql
:query: result

SELECT *
FROM my_table
WHERE value > 10
```
````

SQL options:

| Option     | Type   | Default | Behavior                                         |
| ---------- | ------ | ------- | ------------------------------------------------ |
| `:query:`  | string | `_df`   | Python variable name for the SQL result          |
| `:engine:` | string | none    | Python identifier bound to the marimo SQL engine |

`query` and `engine` are SQL-only options. If `query` is missing or is not a valid
Python identifier, the plugin uses `_df`.

## Markdown cells

Markdown cells join the page-level marimo execution graph:

````markdown
```{marimo} markdown
# A marimo-rendered heading

The Markdown block executes as a marimo Markdown cell.
```
````

Use ordinary MyST outside marimo cells for static book content.

## Page Defaults

Use `{marimo-config}` once per page when cells should share defaults, header code, or
dependencies:

````markdown
```{marimo-config}
:header: |
  import marimo as mo
:echo: true
```
````

Cell options override page defaults. See [Page configuration](configuration.md).
