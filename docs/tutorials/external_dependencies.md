---
title: External dependencies
---

```{marimo-config}
---
header: |
  # Copyright 2026 Marimo. All rights reserved
pyproject: |
  requires-python = ">=3.11"
  dependencies = [
      "marimo>=0.23.5",
      "wigglystuff",
  ]
---
```

# Loading Custom Packages

By default, `jupyter-book-marimo` creates a sandboxed Python environment with `uv`. To
add a package for one document, declare it in a `{marimo-config}` directive with
`pyproject`.

````markdown
```{marimo-config}
---
pyproject: |
  requires-python = ">=3.11"
  dependencies = [
      "marimo>=0.23.5",
      "wigglystuff",
  ]
---
```
````

After that, you can import the package normally inside marimo cells. If the package
exposes an anywidget, wrap it with `mo.ui.anywidget` so marimo can keep the UI reactive
in Jupyter Book output.

## Example: `wigglystuff.Slider2D`

```{marimo} python
import marimo as mo
from wigglystuff import Slider2D

widget = mo.ui.anywidget(
    Slider2D(
        width=320,
        height=320,
        x_bounds=(-2.0, 2.0),
        y_bounds=(-1.0, 1.5),
    )
)

widget
```

```{marimo} python
mo.callout(
    f"x = {widget.x:.3f}, y = {widget.y:.3f}; bounds {widget.x_bounds} / {widget.y_bounds}"
)
```
