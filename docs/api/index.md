---
title: Reference
---

# Reference

The public surface is two MyST directives:

- `{marimo}` turns one Python, SQL, or Markdown cell into a marimo island.
- `{marimo-config}` sets page defaults, dependency metadata, and Molab export behavior
  for the cells on that page.

During a build, Jupyter Book invokes the executable plugin, the plugin executes the
collected cells, emits MyST `anywidget` nodes, and copies
`.jupyter-book-marimo/container-widget.mjs` so the browser can hydrate the
server-rendered islands.

Directive options use standard MyST syntax, for example `:echo: true`. The v1 authoring
API accepts only the spellings documented here; unsupported options or conflicting
visibility/execution settings fail the build.

- [Getting started](install.md): install the package and register the executable plugin.
- [Authoring cells](authoring.md): write Python, SQL, and Markdown cells.
- [Page configuration](configuration.md): set defaults, headers, and page-local
  dependencies.
- [Styling hooks](styling.md): integrate marimo output with a book theme.
- [Runtime assets](runtime-assets.md): understand the bridge used for publishing and
  hydration.
