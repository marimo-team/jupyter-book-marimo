---
title: Reference
---

# Reference

`jupyter-book-marimo` exposes two MyST directives and one document transform.

| Surface           | Contract                                                           |
| ----------------- | ------------------------------------------------------------------ |
| `{marimo}`        | Add one Python, SQL, or Markdown cell to the page app              |
| `{marimo-config}` | Set page defaults, setup code, and Python dependencies             |
| `marimo-islands`  | Compile the page and project its cells as hydrated MyST anywidgets |

The build executes authored code. Build pages you trust. Executed source is serialized
into the published page for browser hydration, including source hidden from the rendered
article.

## Pages

- [Getting started](install.md) covers installation and plugin registration.
- [Authoring cells](authoring.md) defines cell languages and options.
- [Page configuration](configuration.md) defines defaults, setup code, and execution
  environments.
- [Styling](styling.md) lists the public island theme tokens.
- [Runtime assets](runtime-assets.md) describes page compilation and browser hydration.
