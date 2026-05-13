---
title: Runtime assets
---

# Runtime assets

During a static build, three asset paths matter:

| Path                                        | What happens                                           |
| ------------------------------------------- | ------------------------------------------------------ |
| `.jupyter-book-marimo/container-widget.mjs` | generated in the book source tree during the build     |
| generated Jupyter Book assets               | Jupyter Book serves the fingerprinted anywidget bridge |
| marimo island runtime URLs                  | load the marimo runtime assets emitted by marimo       |

The generated `.jupyter-book-marimo/` directory gives Jupyter Book a same-origin ESM
bridge that it can fingerprint and publish with the site.

## Source files

Do not edit `.jupyter-book-marimo/`; it is generated output.

The maintained TypeScript source lives in the top-level Deno project:

```text
widget/
```

The packaged runtime bundle is:

```text
src/jupyter_book_marimo/assets/container-widget.mjs
```

Rebuild the packaged bundle with:

```bash
make widget-build
```

The package build checks that the generated bundle is current.
