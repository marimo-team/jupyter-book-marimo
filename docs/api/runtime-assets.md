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

## Build flow

1. The executable plugin receives MyST `marimoCell` and `marimoConfig` nodes.
2. The extractor executes supported cells with marimo and captures the island HTML,
   notebook source, and runtime asset links.
3. The plugin emits one MyST `anywidget` node per included output.
4. The browser imports `.jupyter-book-marimo/container-widget.mjs`, moves the rendered
   output into light DOM, exposes one hidden notebook source node per app, and waits for
   the shared marimo runtime to hydrate the islands.

Only the first included output for a page carries the runtime payload. Later outputs
share the same `appId` and wait for that app to become ready.

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

In this repository's docs app, the plugin copies that bundle to:

```text
docs/.jupyter-book-marimo/container-widget.mjs
```

That copied file is a served build artifact. Do not edit it directly.
