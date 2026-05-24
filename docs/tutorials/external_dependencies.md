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
      "marimo>=0.23.5,<0.24",
      "wigglystuff",
  ]
---
```

# Loading Custom Packages

This page uses a page-local dependency so the published example can import `wigglystuff`
without requiring it from every page in the book.

````markdown
```{marimo-config}
---
pyproject: |
  requires-python = ">=3.11"
  dependencies = [
      "marimo>=0.23.5,<0.24",
      "wigglystuff",
  ]
---
```
````

After the page declares the dependency, marimo cells can import it normally. If the
package exposes an anywidget, wrap it with `mo.ui.anywidget` so marimo can keep the UI
reactive in Jupyter Book output.

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
