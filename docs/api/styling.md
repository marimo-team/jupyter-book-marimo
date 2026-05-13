---
title: Styling hooks
---

# Styling hooks

Style marimo outputs from your book CSS with the public wrapper class:

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

If a site needs CSS inside marimo-owned shadow roots, pass stylesheets at build time:

```bash
JUPYTER_BOOK_MARIMO_STYLESHEETS=styles/jupyter-book-marimo.css \
  jupyter-book build --html
```

Local stylesheet files are embedded into the widget model and injected into the page
plus nested marimo shadow roots. External `https://...` and site-root `/...` stylesheets
are linked as-is.

The executable also accepts repeated `--style` flags. This is useful when the Jupyter
Book plugin entry points at a wrapper script.

Use CSS variables for stable theme integration. Selectors that reach into marimo
internals should stay local to your site.
