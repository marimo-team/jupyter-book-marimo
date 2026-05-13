---
title: Layout
---

```{marimo-config}
:header: # Copyright 2026 Marimo. All rights reserved
```

`marimo` provides functions to help you lay out your output, such as in rows and
columns, accordions, tabs, and callouts.

<!---->

## Rows and columns

Arrange objects into rows and columns with `mo.hstack` and `mo.vstack`.

```{marimo} python
mo.hstack(
    [mo.ui.text(label="hello"), mo.ui.slider(1, 10, label="slider")],
    justify="start",
)
```

```{marimo} python
mo.vstack([mo.ui.text(label="world"), mo.ui.number(1, 10, label="number")])
```

```{marimo} python
grid = mo.vstack(
    [
        mo.hstack(
            [mo.ui.text(label="hello"), mo.ui.slider(1, 10, label="slider")],
        ),
        mo.hstack(
            [mo.ui.text(label="world"), mo.ui.number(1, 10, label="number")],
        ),
    ],
).center()

mo.md(
    f"""
    Combine `mo.hstack` with `mo.vstack` to make grids:

    {grid}

    You can pass anything to `mo.hstack` to `mo.vstack` (including
    plots!).
    """
)
```

**Customization.** The presentation of stacked elements can be customized with some
arguments that are best understood by example.

```{marimo} python
justify = mo.ui.dropdown(
    ["start", "center", "end", "space-between", "space-around"],
    value="space-between",
    label="justify",
)
align = mo.ui.dropdown(
    ["start", "center", "end", "stretch"], value="center", label="align"
)
gap = mo.ui.number(start=0, step=0.25, stop=2, value=0.5, label="gap")
wrap = mo.ui.checkbox(label="wrap")

mo.hstack([justify, align, gap, wrap], justify="center")
```

```{marimo} python
size = mo.ui.slider(label="box size", start=60, stop=500)
mo.hstack([size], justify="center")
```

```{marimo} python
mo.hstack(
    boxes,
    align=align.value,
    justify=justify.value,
    gap=gap.value,
    wrap=wrap.value,
)
```

```{marimo} python
mo.vstack(
    boxes,
    align=align.value,
    gap=gap.value,
)
```

```{marimo} python
def create_box(num=1):
    box_size = size.value + num * 10
    return mo.Html(
        f"<div style='min-width: {box_size}px; min-height: {box_size}px; background-color: orange; text-align: center; line-height: {box_size}px'>{str(num)}</div>"
    )

boxes = [create_box(i) for i in range(1, 5)]
```

```{marimo} python
:hide-code: true

mo.accordion(
    {
        "Documentation: `mo.hstack`": mo.doc(mo.hstack),
        "Documentation: `mo.vstack`": mo.doc(mo.vstack),
    }
)
```

**Justifying `Html`.** While you can center or right-justify any object using
`mo.hstack`, `Html` objects (returned by most marimo functions, and subclassed by most
marimo classes) have a shortcut using via their `center`, `right`, and `left` methods.

<!---->

This markdown is left-justified.

```{marimo} python
mo.md("This markdown is centered.").center()
```

```{marimo} python
mo.md("This markdown is right-justified.").right()
```

```{marimo} python
:hide-code: true

mo.accordion(
    {
        "Documentation: `Html.center`": mo.doc(mo.Html.center),
        "Documentation: `Html.right`": mo.doc(mo.Html.right),
        "Documentation: `Html.left`": mo.doc(mo.Html.left),
    }
)
```

## Accordion

Create expandable shelves of content using `mo.accordion`:

<!---->

An accordion can contain multiple items:

```{marimo} python
mo.accordion(
    {
        "Multiple items": "By default, only one item can be open at a time",
        "Allow multiple items to be open": (
            """
            Use the keyword argument `multiple=True` to allow multiple items
            to be open at the same time
            """
        ),
    }
)
```

## Tabs

Use `mo.ui.tabs` to display multiple objects in a single tabbed output:

```{marimo} python
_settings = mo.vstack(
    [
        mo.md("**Edit User**"),
        mo.ui.text(label="First Name"),
        mo.ui.text(label="Last Name"),
    ]
)

_organization = mo.vstack(
    [
        mo.md("**Edit Organization**"),
        mo.ui.text(label="Organization Name"),
        mo.ui.number(label="Number of employees", start=0, stop=1000),
    ]
)

mo.ui.tabs(
    {
        "🧙‍♀ User": _settings,
        "🏢 Organization": _organization,
    }
)
```

```{marimo} python
:hide-code: true

mo.accordion({"Documentation: `mo.ui.tabs`": mo.doc(mo.ui.tabs)})
```

```{marimo} python
_t = [
    mo.md("**Hello!**"),
    mo.md(r"$f(x)$"),
    {"c": mo.ui.slider(1, 10), "d": (mo.ui.checkbox(), mo.ui.switch())},
]

mo.md(
    f"""
    ## Tree

    Display a nested structure of lists, dictionaries, and tuples with
    `mo.tree`:

    {mo.tree(_t)}
    """
)
```

```{marimo} python
:hide-code: true

mo.accordion({"Documentation: `mo.tree`": mo.doc(mo.tree)})
```

## Callout

Turn any markdown or HTML into an emphasized callout with the `callout` method:

```{marimo} python
callout_kind = mo.ui.dropdown(
    ["neutral", "warn", "success", "info", "danger"], value="neutral"
)
```

```{marimo} python
mo.md(
    f"""
    **This is a callout!**

    You can turn any HTML or markdown into an emphasized callout.
    You can choose from a variety of different callout kind. This one is:
    {callout_kind}
    """
).callout(kind=callout_kind.value)
```

```{marimo} python
:hide-code: true

mo.accordion({"Documentation: `mo.callout`": mo.doc(mo.callout)})
```

```{marimo} python
import marimo as mo
```
