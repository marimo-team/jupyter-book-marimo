---
title: Reference
---

# Reference

`jupyter-book-marimo` exposes two MyST directives and one document transform. The
directives collect page-local marimo source and configuration. The transform executes
the collected cells, emits MyST `anywidget` nodes, and copies the bridge asset that
hydrates the page in the browser.

| Surface           | Contract                                                               |
| ----------------- | ---------------------------------------------------------------------- |
| `{marimo}`        | One Python, SQL, or Markdown cell in the page execution graph          |
| `{marimo-config}` | Page defaults, header code, Molab export, and dependency metadata      |
| `marimo-islands`  | Document transform that replaces marimo nodes with hydrated anywidgets |
| `--style`         | Optional stylesheet path or URL injected into marimo output            |

## Execution Contract

The build runs authored code. Build pages you trust. Page-local dependencies change the
Python environment used for that page, but they are not a security sandbox for
filesystem, process, or network access.

Executed source required for browser hydration is part of the published static page.
Visibility options change what readers see in the article, not what the browser can
download.

## Pages

- [Getting started](install.md): install the package and register the executable plugin.
- [Authoring cells](authoring.md): write Python, SQL, and Markdown cells with supported
  options.
- [Page configuration](configuration.md): set page defaults, header code, Molab export,
  and page-local dependencies.
- [Styling hooks](styling.md): integrate marimo output with a Jupyter Book theme.
- [Runtime assets](runtime-assets.md): publish the same-origin anywidget bridge and
  understand the marimo runtime payload.
