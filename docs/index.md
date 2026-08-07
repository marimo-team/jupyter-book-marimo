---
title: Make Jupyter Book pages reactive with marimo.
---

[Jupyter Book](https://jupyterbook.org/) builds books and documentation sites from MyST
Markdown and notebooks. `jupyter-book-marimo` adds reactive Python, SQL, and Markdown
cells to its MyST pages.

The plugin compiles every `{marimo}` directive on a page into one marimo app. Jupyter
Book publishes the authored content and initial cell output as static HTML, then
hydrates the app in the browser.

Move the slider. The page has already been built, served, and loaded as static HTML. The
Markdown below still updates because marimo hydrates the cells after the page loads.

```{marimo} python
:editor: true

import marimo as mo

demo_count = mo.ui.slider(
    start=1,
    stop=10,
    step=1,
    label="exclamation points"
)
demo_count
```

```{marimo} python
mo.md(
    f"""
    ## Hello from marimo{"!" * demo_count.value}

    This Markdown came from a Python cell. Change the slider and the output changes
    in place.
    """
).callout('info')
```

## How it works

The [executable plugin](https://mystmd.org/guide/executable-plugins) collects every
`{marimo}` directive before the page compiles. Jupyter Book keeps MyST navigation,
cross-references, and layout around each projected cell. A shared browser runtime
restores marimo dataflow after the static page loads, so dependencies can cross ordinary
MyST sections.

## Quickstart

Write a MyST page with `{marimo}` cells.

For instance, this cell:

````markdown
```{marimo} python
result = "Only the cell output is shown."
result
```
````

produces this output:

```{marimo} python
result = "Only the cell output is shown."
result
```

You can make a cell editable:

````markdown
```{marimo} python
:editor: true

editor_result = "Change me" + ("!" * 3)
editor_result
```
````

```{marimo} python
:editor: true

editor_result = "Change me" + ("!" * 3)
editor_result
```

And another cell can read its value:

```{marimo} python
mo.md(f"The value of `editor_result` is **{editor_result}**.")
```

### But how do I run this?

Install the plugin in the same environment as Jupyter Book.

```bash
pip install jupyter-book-marimo
```

Register the executable plugin in `myst.yml`.

```yaml
project:
  plugins:
    - type: executable
      path: .venv/bin/jupyter-book-marimo
```

Use the executable path for your book environment. When `myst.yml` lives in `docs/` and
the virtual environment lives at the repository root, use
`../.venv/bin/jupyter-book-marimo`. On Windows, use
`.venv/Scripts/jupyter-book-marimo.exe`, or `../.venv/Scripts/jupyter-book-marimo.exe`
for the same nested layout.

Then write cells in any MyST page:

````markdown
```{marimo} python
import marimo as mo

slider = mo.ui.slider(start=1, stop=10, step=1, label="islands")
slider
```

```{marimo} python
"🏝️" * round(slider.value)
```
````

Build the book:

```bash
jupyter-book build --html
```

The tutorials in the sidebar are marimo notebooks rendered through this plugin. Open
them to see larger examples with UI, data flow, SQL, layouts, Markdown, and plots.

## Reference

- [Getting started](api/install.md): install the package and register the executable
  plugin.
- [Authoring cells](api/authoring.md): write Python, SQL, and Markdown cells.
- [Page configuration](api/configuration.md): set defaults, header code, and page-local
  dependencies.
- [Styling](api/styling.md): map book theme variables into marimo output.
- [Runtime assets](api/runtime-assets.md): understand the anywidget bridge and marimo
  page lifecycle.
- [Tutorials](tutorials/index.md): read marimo examples rendered through the plugin.
