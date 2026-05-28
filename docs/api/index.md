---
title: Reference
---

# Reference

`jupyter-book-marimo` exposes two MyST directives:

- `{marimo}` turns one Python, SQL, or Markdown cell into a marimo island.
- `{marimo-config}` sets page defaults, dependency metadata, and Molab export behavior
  for the cells on that page.

## Build contract

Jupyter Book invokes the executable plugin during the document transform stage. The
plugin collects marimo cells, executes them once per page, emits MyST `anywidget` nodes,
and copies `.jupyter-book-marimo/container-widget.mjs` into the book source tree. The
copied bridge must be served as a same-origin ESM asset.

## Execution contract

Builds execute authored code. Only build pages you trust. Page-local dependencies change
dependency resolution for a page. They do not sandbox filesystem, process, or network
access.

Executed source required for hydration is part of the published static page. Code
visibility options change what readers see in the article, not what the browser can
download.

Directive options use standard MyST syntax, for example `:echo: true`. The plugin
normalizes the options it uses for execution, visibility, output, Molab export, and
dependency resolution.

Tutorial pages demonstrate marimo behavior through the plugin. The reference documents
plugin contracts.

- [Getting started](install.md): install the package and register the executable plugin.
- [Authoring cells](authoring.md): write Python, SQL, and Markdown cells.
- [Page configuration](configuration.md): set defaults, headers, and page-local
  dependencies.
- [Styling hooks](styling.md): integrate marimo output with a book theme.
- [Runtime assets](runtime-assets.md): understand the bridge used for publishing and
  hydration.
