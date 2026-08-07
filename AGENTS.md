# AGENTS.md

`jupyter-book-marimo` is a MyST publishing adapter for the marimo page protocol. Read
the current phase owners before changing behavior.

## Commands

```bash
make check
make lint
make test
make build
make book-build
make book-start
```

Deno pins the published `@marimo-team/mdx-marimo` package used by the browser adapter
and generated styles. The Python development environment supplies the Deno runtime used
for checks, tests, and browser bundles.

## Architecture

One page follows one directional pipeline:

```text
MyST directives
  -> authoring.py
  -> document.py
  -> MarimoPageRequest
  -> runner.py
  -> compiler.py
  -> CompiledMarimoPage
  -> projection.py
  -> MyST anywidgets
  -> widget/index.ts
  -> @marimo-team/mdx-marimo/bridge/*
```

- `authoring.py` validates directive options and maps them to protocol option patches.
- `document.py` collects one document, assigns authored cell indexes, and computes a
  content-based page identity.
- `protocol.py` mirrors version 2 of the shared TypeScript page protocol.
- `runner.py` selects the current Python environment, an external environment, or a
  page-local uv environment.
- `compiler.py` is vendored unchanged from mdx-marimo's
  [`packages/islands-compiler/compiler.py`](https://github.com/marimo-team/mdx-marimo/blob/main/packages/islands-compiler/compiler.py).
  It converts languages, executes one marimo app, and returns one compiled cell per
  authored cell.
- `projection.py` stages browser assets and emits anywidgets. The first included cell
  carries the app payload. Sibling cells carry app references.
- `widget/index.ts` adapts the anywidget shadow host to a light-DOM custom element.
- `@marimo-team/mdx-marimo/bridge/*` owns asset loading, app retention, theme
  synchronization, static rendering, hydration, and teardown.

Keep bridge changes host-neutral. Its source, API, tests, and metadata must describe
dynamic hosts and the marimo page contract. Jupyter Book behavior stays in this
repository.

## Invariants

- One document produces one `MarimoPageRequest`, one `CompiledMarimoPage`, and one
  marimo app. The document transform collects every directive before invoking the
  compiler.
- Authored cell indexes remain ordered and unchanged across the compiler boundary.
- Page identity depends on executable content and options, not MyST source positions.
- Header cells participate in execution and browser hydration but have no projected
  node.
- Exactly one included cell owns the full app payload when a page has a runtime.
- Generated browser assets are copied from the package into `.jupyter-book-marimo/`
  for MyST to fingerprint and publish.
- The custom element mounts in light DOM because the marimo runtime queries the
  document. The anywidget shadow root contains a slot.
- The bridge stylesheet is published through the anywidget CSS field, then installed
  at document scope before the island mounts.

## Authoring

`{marimo}` accepts `python`, `sql`, and `markdown`. Its options are `eval`, `echo`,
`editor`, `output`, `server-output`, `error`, `include`, `hide-code`, `hide-output`,
`disabled`, `unparsable`, `name`, `column`, `query`, and `engine`.

`{marimo-config}` accepts execution defaults plus `header`, `pyproject`, and
`external-env`. A page may contain one config directive.

## Generated files

`widget/` and the mdx-marimo bridge stylesheet are the browser asset sources.
`make widget-build` writes local assets for tests and documentation builds. The Hatch
wheel hook runs the same bundler and packages both assets under
`jupyter_book_marimo/assets/`. Generated browser assets stay ignored by Git.

`src/jupyter_book_marimo/compiler.py` remains byte-for-byte identical to mdx-marimo's
islands compiler. Environment selection and subprocess handling stay in `runner.py`.

`docs/tutorials/` comes from upstream marimo tutorials. Edit repository documentation
under `docs/api/`, `docs/index.md`, `docs/myst.yml`, and `docs/styles/`.

## Validation

Run `make check` for every implementation change. Browser-facing changes also require
a real browser pass over the index interaction, theme toggle, forward navigation,
back navigation, and a tutorial page.
