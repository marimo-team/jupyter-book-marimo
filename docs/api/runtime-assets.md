---
title: Runtime assets
---

# Runtime assets

`jupyter-book-marimo` connects the MyST executable-plugin protocol, MyST anywidgets, and
marimo's island runtime during a static build.

## Build Flow

1. MyST parses `{marimo}` and `{marimo-config}` directives into internal document nodes.
2. The document transform collects the page cells and config, then runs the extractor
   once for that page.
3. The extractor executes the page with marimo and returns one output model for each
   authored cell.
4. The plugin replaces included marimo nodes with MyST `anywidget` nodes.
5. The plugin copies `container-widget.mjs` to `.jupyter-book-marimo/` in the book
   source directory.
6. The browser imports that bridge as a same-origin ESM asset and hydrates marimo
   islands with the shared runtime payload.

The bridge adapts MyST's anywidget host to marimo's island runtime. MyST renders
anywidgets in a widget host. marimo islands expect light DOM and one hidden notebook
source node per app. The bridge moves rendered output into light DOM, installs the
shared source node, loads marimo runtime assets once, and waits for the app to become
ready.

## Payload Placement

Only one included marimo model on a page carries the shared runtime payload. Later
islands and editor views share the same `appId` and wait for that app to hydrate.

The payload includes generated notebook source needed for browser hydration. Source
visibility options such as `:echo:` and `:hide-code:` affect the rendered article, not
the downloaded widget model. Treat executed cells as public in a published static book.

## Static Previews

By default, output islands include build-time HTML preview from marimo. Set
`:server-output: false` when a cell should execute and hydrate in the browser with an
empty build-time preview.

Use `:server-output: false` for output whose server-rendered HTML should not be
published in the static page. Use `:output: false` or `:hide-output: true` when the
output should not be visible in the article.

## Published Assets

The generated bridge is packaged with `jupyter-book-marimo`. During the plugin
transform, the bundle is copied into `.jupyter-book-marimo/` in the source tree so MyST
can ingest it:

```text
.jupyter-book-marimo/container-widget.mjs
```

The static HTML artifact fingerprints that source-side copy into the public build
directory. If the book is published under a base URL, verify that the hashed public
module resolves as a same-origin ESM asset:

```text
<base-url>/build/container-widget-<hash>.mjs
```

The marimo island runtime assets come from marimo's exported island head for the
installed marimo version. For the supported marimo range, those assets may include
external CDN URLs such as jsDelivr, Google Fonts, and KaTeX. A fully offline or
self-hosted export needs marimo support for rewriting those runtime asset bases. The
plugin preserves the URLs marimo emits.

Upstream contracts:

- [MyST executable plugins](https://mystmd.org/guide/executable-plugins)
- [MyST widgets](https://mystmd.org/guide/widgets)
- [Anywidget Front-End Module specification](https://anywidget.dev/en/afm/)
- [Deno bundle](https://docs.deno.com/runtime/reference/cli/bundle/)

## Source

Edit the TypeScript source in `widget/`.

Run `make widget-build` to regenerate the packaged bridge:

```text
src/jupyter_book_marimo/assets/container-widget.mjs
```

The checked-in bundle ships with the Python package. Deno is the contributor toolchain
for checking TypeScript and producing the browser ESM bundle.

In this repository's docs app, the plugin copies that bundle to:

```text
docs/.jupyter-book-marimo/container-widget.mjs
```

That copied file is a generated staging copy for MyST. Do not edit it directly.
