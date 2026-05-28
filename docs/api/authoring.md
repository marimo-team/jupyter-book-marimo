---
title: Authoring cells
---

# Authoring cells

Use the MyST directive name `marimo` and pass the cell language as the required
argument. The language must be exactly `python`, `sql`, or `markdown`. Python cells use
the names defined by earlier cells or the page header. SQL and Markdown cells import
marimo internally, so they do not require a separate `import marimo as mo` cell.

````markdown
```{marimo} python
import marimo as mo

slider = mo.ui.slider(start=1, stop=10, label="islands")
slider
```

```{marimo} python
"🏝️" * slider.value
```
````

## Cell options

Write cell options as MyST directive options.

````markdown
```{marimo} python
:echo: true
:output: true

import marimo as mo
mo.md("show source and output")
```
````

| Option            | Type    | Default | Behavior                                |
| ----------------- | ------- | ------- | --------------------------------------- |
| `:eval:`          | boolean | `true`  | run the cell during the book build      |
| `:echo:`          | boolean | `false` | render source as a static code block    |
| `:editor:`        | boolean | `false` | render source in a marimo editor        |
| `:output:`        | boolean | `true`  | include the browser output island       |
| `:server-output:` | boolean | `true`  | include build-time preview HTML         |
| `:error:`         | boolean | `true`  | render marimo error output              |
| `:include:`       | boolean | `true`  | include this cell's node in the page    |
| `:hide-code:`     | boolean | `false` | hide rendered source code               |
| `:hide-output:`   | boolean | `false` | hide rendered output                    |
| `:disabled:`      | boolean | `false` | skip execution                          |
| `:unparsable:`    | boolean | `false` | skip parsing intentionally invalid code |
| `:name:`          | string  | none    | set the marimo cell name                |
| `:column:`        | number  | none    | set the marimo column index             |

Unsupported options fail the build before execution. Conflicting options also fail the
build: do not combine `:echo: true` with `:hide-code: true`, `:output: true` with
`:hide-output: true`, or `:eval: true` with `:disabled: true`.

Visibility options are presentational. Executed cells are serialized into the static
page so marimo can hydrate islands in the browser. Do not put credentials, private
logic, or untrusted input in cells that ship with a public book, even when `:echo:` is
false or `:hide-code:` is true.

`:error: false` is build-strict. If marimo execution produces an error MIME renderer,
the build fails at that cell. Successful output keeps text, HTML, and other non-error
MIME renderers.

Use `:server-output: false` when a cell should execute and hydrate as a marimo island
with an empty build-time preview. The page keeps the shared notebook source and runtime
payload. That cell's `<marimo-cell-output>` starts empty.

## SQL cells

SQL cells use the same directive and the `sql` language argument.

````markdown
```{marimo} sql
:query: result

SELECT *
FROM my_table
WHERE value > 10
```
````

SQL options:

| Option     | Type   | Default | Behavior                                       |
| ---------- | ------ | ------- | ---------------------------------------------- |
| `:query:`  | string | `_df`   | Python variable name for the SQL result        |
| `:engine:` | string | none    | Python expression naming the marimo SQL engine |

SQL cells read `query` and `engine` when building the generated marimo cell. Invalid
`query` names fall back to `_df`, matching the plugin's safe default for SQL output.

## Markdown cells

Markdown cells let Markdown syntax join the page-level marimo execution graph.

````markdown
```{marimo} markdown
# A marimo-rendered heading

The Markdown block executes as a marimo Markdown cell.
```
````

Use ordinary MyST outside marimo cells for static content.

## Page defaults

Use `{marimo-config}` once per page when cells should share defaults or dependencies:

````markdown
```{marimo-config}
:header: |
  import marimo as mo
:echo: true
```
````

See [Page configuration](configuration.md) for headers, defaults, and page-local
dependencies.
