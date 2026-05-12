# marimo + jupyter-book = 🌴 📖 ❤️

`jupyter-book-marimo` is a Jupyter Book executable plugin that renders
marimo-marked Python, SQL, and Markdown fences as hydrated marimo islands.

Use it when you want normal MyST pages with reactive marimo cells embedded
inside the Jupyter Book site.

> [!NOTE]
> This plugin requires `marimo>=0.23.5` and Python 3.10+.

## Quick Start

**1.** Install the plugin in the same environment as Jupyter Book.

```bash
uv add jupyter-book-marimo
```

For local development from this repo:

```bash
uv sync --dev
```

**2.** Register the executable plugin in `myst.yml`.

```yaml
project:
  plugins:
    - type: executable
      path: .venv/bin/jupyter-book-marimo
```

Use the path that matches your environment. In this repo's docs site, the docs
live in `docs/`, so the path is `../.venv/bin/jupyter-book-marimo`.

**3.** Author marimo cells as ordinary MyST language fences.

````markdown
```python {.marimo}
import marimo as mo

slider = mo.ui.slider(start=1, stop=10, label="count")
slider
```

```python {.marimo}
"*" * slider.value
```
````

**4.** Build the book.

```bash
jupyter-book build --html
```

## Authoring Options

The plugin keeps the authoring surface close to MyST:

| Feature             | How                                                        |
| ------------------- | ---------------------------------------------------------- |
| Python cells        | ` ```python {.marimo} `                                    |
| SQL cells           | ` ```sql {.marimo query="result"} `                        |
| Markdown cells      | ` ```markdown {.marimo} `                                  |
| Show code/editor    | `editor="true"`                                            |
| Show source         | `echo="true"`                                              |
| Hide source         | `hide_code="true"`                                         |
| Hide output         | `hide_output="true"` or `output="false"`                   |
| Skip execution      | `eval="false"`                                             |
| Fail on cell errors | `error="false"`                                            |
| Disable execution   | `disabled="true"`                                          |
| Mark bad syntax     | `unparseable="true"` or the accepted alias `unparsable`    |
| Omit rendered cell  | `include="false"`                                          |
| SQL result name     | `query="result"`                                           |
| SQL engine object   | `engine="engine"`                                          |

Cells render output only by default.
The parser also accepts `warning` for Quarto-style option compatibility.

The same execution options can be set as page defaults under
`options.marimo` frontmatter. Cell attributes override page defaults.

## Page Metadata

Add `options.marimo.pyproject` frontmatter to declare page-local dependencies.
The plugin converts this metadata into `uv run` arguments using marimo's
sandbox logic. Add `options.marimo.header` when a page needs Python inserted
before the exported notebook code.

```yaml
---
options:
  marimo:
    header: |
      import marimo as mo
    pyproject: |
      requires-python = ">=3.10"
      dependencies = [
          "pandas",
          "marimo>=0.23.5",
      ]
---
```

Pages without `options.marimo.pyproject` execute in-process.

## Styling

The packaged bridge owns structure, not your palette. It mounts marimo output,
shows the disabled preview/skeleton while the runtime is starting, and maps a
small set of `--jbm-*` variables into marimo-owned shadow roots.

For normal theme integration, use your book's CSS and override the public
variables:

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

.your-dark-theme-selector .marimo-jupyter-book-output {
  --jbm-code-bg: var(--myst-color-surface);
  --jbm-code-fg: var(--myst-color-text);
}
```

If you need to style elements inside marimo's shadow DOM, pass a custom
stylesheet at build time:

```bash
JUPYTER_BOOK_MARIMO_STYLESHEETS=styles/jupyter-book-marimo.css \
  jupyter-book build --html
```

Local stylesheets are embedded into the widget model and injected into both the
document and marimo-owned shadow roots. External `https://...` and site-root
`/...` stylesheets are linked as-is. The executable also accepts repeated
`--style` flags, which is useful if your Jupyter Book plugin path points at a
small wrapper script.

The docs site uses this hook for
`docs/styles/jupyter-book-marimo.css`. That stylesheet is intentionally
site-specific; internal marimo selectors in custom CSS are an escape hatch, not
the plugin's public styling API.

## Docs Site

This repo includes a small Jupyter Book in `docs/`. It is an integration
fixture for `jupyter-book-marimo`, not a general Jupyter Book publishing guide.

```bash
make book-build
make book-start
```

For subpath deployments, pass the public path through `BASE_URL`:

```bash
BASE_URL=/projects/marimo/jupyter-book-marimo/docs make book-build
```

During a book build, the plugin writes
`docs/.jupyter-book-marimo/container-widget.mjs`. That directory is generated
output: it gives Jupyter Book a same-origin ESM file for the anywidget bridge,
while the source of truth stays in
`src/jupyter_book_marimo/assets/container-widget.mjs`.

For Jupyter Book build, hosting, and publishing details outside this plugin's
integration surface, use the official Jupyter Book docs:
https://jupyterbook.org/stable/build-and-publish/

The docs are intentionally an application surface for the plugin: the root page
shows the basic setup, and the tutorial pages exercise marimo output,
reactivity, layouts, SQL, Markdown, and page-local dependencies.

## Development

```bash
make check       # format check, lint, typecheck, tests, build
make test        # tests only
make book-build  # strict static HTML Jupyter Book build
```

Please see `CONTRIBUTING.md` for the full local workflow.
