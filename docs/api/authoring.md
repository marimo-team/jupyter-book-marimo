---
title: Authoring cells
---

# Authoring cells

Use the MyST directive name `marimo` and pass the cell language as the required
argument. The language must be exactly `python`, `sql`, or `markdown`.

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

| Option          | Type    | Default | Behavior                                      |
| --------------- | ------- | ------- | --------------------------------------------- |
| `:eval:`        | boolean | `true`  | execute the cell during the book build        |
| `:echo:`        | boolean | `false` | show the source code                          |
| `:editor:`      | boolean | `false` | show the source in a marimo editor            |
| `:output:`      | boolean | `true`  | include rendered output                       |
| `:error:`       | boolean | `true`  | render marimo error output instead of failing |
| `:include:`     | boolean | `true`  | include this cell in the page                 |
| `:hide-code:`   | boolean | `false` | force source code hidden                      |
| `:hide-output:` | boolean | `false` | force output hidden                           |
| `:disabled:`    | boolean | `false` | skip execution                                |
| `:unparsable:`  | boolean | `false` | mark intentionally invalid source             |
| `:name:`        | string  | none    | store marimo cell name metadata               |
| `:column:`      | number  | none    | store marimo column metadata                  |

Unsupported options fail the build. Conflicting options also fail the build: do not
combine `:echo: true` with `:hide-code: true`, `:output: true` with
`:hide-output: true`, or `:eval: true` with `:disabled: true`.

`:error: false` is build-strict. If marimo execution produces an error MIME renderer,
the build fails at that cell; otherwise any allowed error MIME nodes are stripped from
the rendered output.

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

SQL-only options:

| Option     | Type   | Default | Behavior                                       |
| ---------- | ------ | ------- | ---------------------------------------------- |
| `:query:`  | string | `_df`   | Python variable name for the SQL result        |
| `:engine:` | string | none    | Python expression naming the marimo SQL engine |

`query` and `engine` are only valid on SQL cells. Invalid `query` names fall back to
`_df`, matching the plugin's safe default for SQL output.

## Markdown cells

Markdown cells let Markdown syntax join the page-level marimo execution graph.

````markdown
```{marimo} markdown
# A marimo-rendered heading

This Markdown is executed as a marimo Markdown cell.
```
````

Use ordinary MyST outside marimo cells when the content does not need marimo execution
or reactivity.

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
