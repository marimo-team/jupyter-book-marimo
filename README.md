# marimo + jupyter-book = 🌴 📖 ❤️

`jupyter-book-marimo` is a Jupyter Book executable plugin that renders
MyST-native marimo directives for Python, SQL, and Markdown as hydrated marimo
islands.

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

**3.** Author marimo cells as MyST directives.

````markdown
```{marimo} python
import marimo as mo

slider = mo.ui.slider(start=1, stop=10, label="count")
slider
```

```{marimo} python
"*" * slider.value
```
````

**4.** Build the book.

```bash
jupyter-book build --html
```

## Authoring Options

The plugin keeps the authoring surface close to MyST:

| Feature             | How                              |
| ------------------- | -------------------------------- |
| Python cells        | `` ```{marimo} python ``         |
| SQL cells           | `` ```{marimo} sql ``            |
| Markdown cells      | `` ```{marimo} markdown ``       |
| Show code/editor    | `:editor: true`                  |
| Show source         | `:echo: true`                    |
| Hide source         | `:hide-code: true`               |
| Hide output         | `:hide-output: true`             |
| Skip execution      | `:eval: false`                   |
| Fail on cell errors | `:error: false`                  |
| Disable execution   | `:disabled: true`                |
| Mark bad syntax     | `:unparseable: true`             |
| Omit rendered cell  | `:include: false`                |
| SQL result name     | `:query: result`                 |
| SQL engine object   | `:engine: engine`                |

Cells render output only by default.
Use one spelling for each option; multiword options use kebab case.

The same execution options can be set as page defaults under
`{marimo-config}`. Cell directive options override page defaults.

## Page Metadata

Add a `{marimo-config}` directive to declare page-local dependencies.
The plugin converts this metadata into `uv run` arguments using marimo's
sandbox logic. Add `header` when a page needs Python inserted before the
exported notebook code.

````markdown
```{marimo-config}
---
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
````

Pages without `pyproject` execute in-process. Use `external-env: true` to
make in-process execution explicit; `external-env` and `pyproject` are mutually
exclusive.

Cell options use the same directive option syntax:

````markdown
```{marimo} sql
:query: result
:hide-output: true

SELECT * FROM table
```
````

Old `.marimo` fence classes and `options.marimo` frontmatter are not parsed by
this API.

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
while the maintained source stays in the top-level `widget/` Deno project. The
packaged `src/jupyter_book_marimo/assets/container-widget.mjs` file is a
checked-in Deno bundle generated from that TypeScript source.

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
make widget-build # rebuild packaged container-widget.mjs from TypeScript
make book-build  # strict static HTML Jupyter Book build
```

Please see `CONTRIBUTING.md` for the full local workflow.
