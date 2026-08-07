---
title: Runtime assets
---

# Runtime assets

Each MyST page compiles into one versioned marimo page:

```text
{marimo} directives
  -> MarimoPageRequest
  -> marimo compiler
  -> CompiledMarimoPage
  -> MyST anywidgets
  -> marimo islands
```

`MarimoPageRequest` contains the ordered cells, page defaults, setup cells, dependency
metadata, and a content-based identity. The compiler returns one app and one compiled
cell for each authored cell.

The document transform collects every marimo directive before compilation. Compiling
directives separately would create independent apps, so reactive dependencies could not
span cells and navigation could not replace the page as one lifecycle unit.

The first included anywidget carries the app payload. Sibling widgets carry the app ID
and their compiled cell. This keeps the page payload singular while allowing MyST to
place cells between ordinary document sections.

## Browser lifecycle

The anywidget adapter creates a marimo custom element in light DOM and assigns its page
payload. The `@marimo-team/mdx-marimo/bridge/*` modules then:

1. renders the static cell HTML
2. loads the marimo assets declared by the compiled app
3. starts or reuses the page app
4. hydrates each cell against that app
5. stops the outgoing app when client-side navigation replaces the page
6. retains the worker and Pyodide environment for the next page

Theme state and app transitions stay in the shared bridge so each static-site host uses
the same lifecycle.

App replacement requires marimo 0.23.16 or newer. Earlier runtime versions use
full-document navigation and reload the browser runtime with the next page.

## Static previews

`:server-output: true` includes build-time HTML while the runtime loads.
`:server-output: false` leaves the preview empty and still hydrates the cell.
`:output: false` keeps the output out of the rendered cell.

Executed source is part of the runtime payload even when `:echo: false`.

## Published files

The wheel contains:

```text
jupyter_book_marimo/assets/container-widget.mjs
jupyter_book_marimo/assets/islands-bridge.css
```

During the document transform, both files are copied into:

```text
.jupyter-book-marimo/
```

MyST fingerprints those files and publishes them as same-origin assets. The adapter
installs the fingerprinted stylesheet at document scope because the custom element
mounts in light DOM.

The marimo compiler supplies its runtime scripts, links, head tags, and notebook source
through the app payload. Asset URLs follow the installed marimo export runtime.

Upstream contracts:

- [MyST executable plugins](https://mystmd.org/guide/executable-plugins)
- [MyST widgets](https://mystmd.org/guide/widgets)
- [Anywidget Front-End Module specification](https://anywidget.dev/en/afm/)
