---
title: Styling hooks
---

# Styling hooks

The plugin wraps each rendered island in `.marimo-jupyter-book-output`. That class is
the public CSS contract for book themes.

```css
.marimo-jupyter-book-output {
  --jbm-background: var(--myst-color-background);
  --jbm-foreground: var(--myst-color-text);
  --jbm-surface: var(--myst-color-surface);
  --jbm-muted-surface: color-mix(
    in srgb,
    var(--jbm-foreground) 6%,
    var(--jbm-background)
  );
  --jbm-raised-surface: color-mix(
    in srgb,
    var(--jbm-foreground) 3%,
    var(--jbm-background)
  );
  --jbm-border: var(--myst-color-border);
  --jbm-muted-foreground: var(--myst-color-text-muted);
  --jbm-link: var(--myst-color-link);
  --jbm-accent: var(--myst-color-primary);
  --jbm-accent-foreground: var(--myst-color-on-primary);
  --jbm-focus-ring: var(--myst-color-primary);
  --jbm-code-bg: var(--myst-color-code-background);
  --jbm-code-fg: var(--myst-color-text);
  --jbm-code-border: var(--myst-color-border);
  --jbm-inline-code-bg: color-mix(in srgb, var(--jbm-accent) 10%, transparent);
  --jbm-inline-code-fg: var(--myst-color-text);
  --jbm-hover-bg: color-mix(in srgb, var(--jbm-foreground) 8%, transparent);
  --jbm-selection-bg: color-mix(in srgb, var(--jbm-accent) 28%, transparent);
}
```

Set those variables from your book theme. Selectors that depend on marimo's internal DOM
are outside the public contract and may break when marimo changes its island markup.

## Custom Stylesheets

The executable accepts custom stylesheets through the `JUPYTER_BOOK_MARIMO_STYLESHEETS`
environment variable or repeated `--style` arguments. Use custom stylesheets when a book
needs marimo-specific styling inside nested shadow roots.

Accepted values:

| Value                            | Behavior                                                   |
| -------------------------------- | ---------------------------------------------------------- |
| `https://example.com/marimo.css` | Kept as an external stylesheet URL                         |
| `/assets/marimo.css`             | Kept as a root-relative book URL when no local file exists |
| `styles/jupyter-book-marimo.css` | Read from the build directory and embedded in the model    |
| `file:///path/to/marimo.css`     | Read from the filesystem and embedded in the model         |
| `/absolute/path/to/marimo.css`   | Embedded when the file exists on the build machine         |

Embedded stylesheets are copied into the anywidget model and injected into marimo shadow
roots by the bridge.

Set a comma-separated environment variable for one or more stylesheets:

```bash
JUPYTER_BOOK_MARIMO_STYLESHEETS="styles/jupyter-book-marimo.css,https://example.com/marimo.css" \
  jupyter-book build --html
```

The environment variable also accepts a JSON string list:

```bash
JUPYTER_BOOK_MARIMO_STYLESHEETS='["styles/jupyter-book-marimo.css"]' \
  jupyter-book build --html
```

In this repository, the Makefile forwards `JBM_STYLESHEETS` to the docs build:

```bash
JBM_STYLESHEETS="styles/jupyter-book-marimo.css" make book-build
```
