---
title: Runtime assets
---

# Runtime assets

`jupyter-book-marimo` connects three systems during a static build:

- MyST executes the Python plugin through the executable-plugin protocol.
- Jupyter Book publishes the anywidget bridge as a same-origin ESM asset.
- marimo provides the island runtime assets captured from cell execution.

The bridge exists because marimo islands expect light DOM and notebook source, while
MyST anywidgets render inside a widget host. Jupyter Book owns site publishing; marimo
owns island execution and hydration; this package owns the adapter between them.

For the upstream contracts, see
[MyST executable plugins](https://mystmd.org/guide/executable-plugins),
[MyST widgets](https://mystmd.org/guide/widgets), the
[anywidget front-end module specification](https://anywidget.dev/en/afm/), and
[Deno bundle](https://docs.deno.com/runtime/reference/cli/bundle/).

## Source

Edit the TypeScript source in `widget/`.

Run `make widget-build` to regenerate:

```text
src/jupyter_book_marimo/assets/container-widget.mjs
```

The checked-in bundle is generated. Package users do not need Deno during normal book
builds; Deno is the contributor toolchain for checking TypeScript and producing the
browser ESM bundle.
