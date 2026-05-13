---
title: Authoring cells
---

# Authoring cells

Use the MyST directive name `marimo` and pass the cell language as the required
argument.

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

Use one of three language arguments:

| Language | Directive                  | Use for                           |
| -------- | -------------------------- | --------------------------------- |
| Python   | `` ```{marimo} python ``   | normal marimo Python cells        |
| SQL      | `` ```{marimo} sql ``      | marimo SQL cells                  |
| Markdown | `` ```{marimo} markdown `` | Markdown cells rendered by marimo |

Write the language name as shown: `python`, `sql`, or `markdown`.

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

| Option          | Default | Meaning                                       |
| --------------- | ------- | --------------------------------------------- |
| `:eval:`        | `true`  | execute the cell during the book build        |
| `:echo:`        | `false` | show the source code                          |
| `:editor:`      | `false` | show the source in a marimo editor            |
| `:output:`      | `true`  | include rendered output                       |
| `:error:`       | `true`  | render marimo error output instead of failing |
| `:warning:`     | `true`  | keep warning output                           |
| `:include:`     | `true`  | include this cell in the page                 |
| `:hide-code:`   | `false` | force source code hidden                      |
| `:hide-output:` | `false` | force output hidden                           |
| `:disabled:`    | `false` | skip execution                                |
| `:unparseable:` | `false` | mark intentionally invalid source             |
| `:name:`        | none    | optional cell name metadata                   |
| `:column:`      | none    | optional column metadata                      |

Conflicting options fail the build. Do not combine `:echo: true` with
`:hide-code: true`, `:output: true` with `:hide-output: true`, or `:eval: true` with
`:disabled: true`.

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

| Option     | Meaning                                 |
| ---------- | --------------------------------------- |
| `:query:`  | Python variable name for the SQL result |
| `:engine:` | Python expression naming the SQL engine |

`query` and `engine` are only valid on SQL cells.

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
