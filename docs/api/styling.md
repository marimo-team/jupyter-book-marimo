---
title: Styling hooks
---

# Styling hooks

The wrapper class around each rendered island is the public CSS contract:

```css
.marimo-jupyter-book-output {
  --jbm-background: var(--myst-color-background);
  --jbm-foreground: var(--myst-color-text);
  --jbm-surface: var(--myst-color-surface);
  --jbm-border: var(--myst-color-border);
  --jbm-link: var(--myst-color-link);
  --jbm-accent: var(--myst-color-primary);
  --jbm-code-bg: var(--myst-color-surface);
  --jbm-code-fg: var(--myst-color-text);
  --jbm-code-border: var(--myst-color-border);
}
```

Set those variables from your book theme. Selectors that reach into marimo internals are
outside the public contract.

## Custom stylesheets

The executable accepts custom stylesheet paths through the
`JUPYTER_BOOK_MARIMO_STYLESHEETS` environment variable or repeated `--style` arguments.
Values may be:

- absolute `http://` or `https://` URLs
- root-relative paths served by the built book
- relative local files or `file://` URLs, which are embedded into the widget model and
  injected into marimo shadow roots

Set the environment variable when you want to test a book stylesheet:

```bash
cd docs
JUPYTER_BOOK_MARIMO_STYLESHEETS="styles/jupyter-book-marimo.css" uv run jupyter-book build --html --strict
```
