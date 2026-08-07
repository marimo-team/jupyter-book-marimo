---
title: Styling
---

# Styling

The browser bridge marks every mounted output with `.marimo-island-host` and
`data-marimo-host="jupyter-book"`. Set the public island tokens in the stylesheet
configured by your Jupyter Book theme:

```css
.marimo-island-host[data-marimo-host="jupyter-book"] {
  --marimo-island-background: var(--myst-color-background);
  --marimo-island-foreground: var(--myst-color-text);
  --marimo-island-surface: var(--myst-color-background);
  --marimo-island-muted-surface: var(--myst-color-background-muted);
  --marimo-island-muted-foreground: var(--myst-color-text-muted);
  --marimo-island-border: var(--myst-color-border);
  --marimo-island-accent: var(--myst-color-primary);
  --marimo-island-code-background: var(--myst-color-code-background);
  --marimo-island-margin-block: 1rem;
}
```

Available tokens:

| Token                               | Controls                     |
| ----------------------------------- | ---------------------------- |
| `--marimo-island-background`        | Page-level island background |
| `--marimo-island-foreground`        | Primary text                 |
| `--marimo-island-surface`           | Inputs and raised surfaces   |
| `--marimo-island-muted-surface`     | Muted containers             |
| `--marimo-island-muted-foreground`  | Secondary text               |
| `--marimo-island-border`            | Borders                      |
| `--marimo-island-accent`            | Links and active controls    |
| `--marimo-island-accent-foreground` | Text on accent surfaces      |
| `--marimo-island-focus-ring`        | Keyboard focus               |
| `--marimo-island-code-background`   | Code blocks                  |
| `--marimo-island-code-foreground`   | Code text                    |
| `--marimo-island-error-background`  | Error surfaces               |
| `--marimo-island-error-border`      | Error borders                |
| `--marimo-island-error-foreground`  | Error text                   |
| `--marimo-island-error-accent`      | Error summaries              |
| `--marimo-island-radius`            | Island corners               |
| `--marimo-island-margin-block`      | Vertical spacing             |

Theme mode follows the active book theme. Token overrides cascade into the island host
and the bridge propagates the resolved theme to marimo shadow roots.
