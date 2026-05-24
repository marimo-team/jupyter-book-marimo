---
title: Styling hooks
---

# Styling hooks

The public CSS contract is the wrapper class around each rendered island:

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

Use those variables from your book theme. Selectors that reach into marimo internals are
not part of the public contract.

## Custom stylesheets

The executable accepts custom stylesheet paths through the
`JUPYTER_BOOK_MARIMO_STYLESHEETS` environment variable or repeated `--style` arguments.
Values may be:

- absolute `http://` or `https://` URLs;
- root-relative paths served by the built book;
- local files, which are embedded into the widget model and injected into marimo shadow
  roots.

This repository's book build runs from `docs/` and passes
`styles/jupyter-book-marimo.css` through `JUPYTER_BOOK_MARIMO_STYLESHEETS`.
