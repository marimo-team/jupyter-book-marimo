---
title: Runtime assets
---

# Runtime assets

`jupyter-book-marimo` connects three runtimes during a static build:

- MyST executes the Python plugin through the executable-plugin protocol.
- Jupyter Book publishes the anywidget bridge as a same-origin ESM asset.
- marimo provides the island runtime assets captured from cell execution.

The container widget adapts MyST's anywidget host to marimo's island runtime. marimo
islands expect light DOM and a hidden notebook source node. MyST anywidgets render in a
widget host.

## Build flow

1. The executable plugin receives MyST `marimoCell` and `marimoConfig` nodes.
2. The extractor executes supported cells with marimo and captures the island HTML,
   notebook source, and runtime asset links.
3. The plugin emits one MyST `anywidget` node per included output.
4. The browser imports `.jupyter-book-marimo/container-widget.mjs`, moves the rendered
   output into light DOM, exposes one hidden notebook source node per app, and waits for
   the shared marimo runtime to hydrate the islands.

Only one included marimo model for a page carries the runtime payload. Later islands and
source-editor views share the same `appId` and wait for that app to become ready.

The payload includes the generated notebook source required for browser hydration.
Source visibility options such as `:echo:` and `:hide-code:` affect the rendered
article, not the downloaded widget model. Treat executed cells as public in a published
static book.

## Static previews

By default, output islands include build-time HTML preview from marimo. One included
model on the page also carries the shared browser runtime payload.
`:server-output: false` gives that cell an empty `<marimo-cell-output>` preview. The
extractor still executes the cell and keeps it in the shared notebook source so the
browser can hydrate the island.

Set `:server-output: false` for cells whose server-rendered HTML cannot be published in
a static book. Use `:output: false` or `:hide-output: true` when the whole output should
be hidden.

## CDN assets

The generated bridge is packaged with `jupyter-book-marimo` and served from the book. If
the book is published under a base URL, verify that
`.jupyter-book-marimo/container-widget.mjs` resolves as a same-origin ESM asset.

The marimo island runtime assets come from marimo's exported island head for the
installed marimo version. For the supported marimo range, those assets may include
external CDN URLs such as jsDelivr, Google Fonts, and KaTeX. A fully offline or
self-hosted export needs marimo support for rewriting those runtime asset bases. The
plugin preserves the URLs marimo emits.

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

The checked-in bundle ships with the package. Deno is the contributor toolchain for
checking TypeScript and producing the browser ESM bundle.

In this repository's docs app, the plugin copies that bundle to:

```text
docs/.jupyter-book-marimo/container-widget.mjs
```

That copied file is a served build artifact. Do not edit it directly.
