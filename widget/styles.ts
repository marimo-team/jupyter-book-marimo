export const outputClass = "marimo-jupyter-book-output";

export const themeStyleId = "marimo-jupyter-book-theme";
export const shadowThemeStyleId = "marimo-jupyter-book-shadow-theme";
export const customStyleAttribute = "data-jupyter-book-marimo-custom-style";

/*
 * Styling contract:
 * - the bridge owns light-DOM mounting and shadow-root style transport
 * - book themes own color by setting --jbm-* variables with normal CSS
 * - custom stylesheets carry widget-specific shadow DOM overrides.
 */
export const globalThemeCss = `
.${outputClass} {
  color: inherit;
  color-scheme: inherit;
  max-width: 100%;
  min-width: 0;
  overflow-x: auto;
  --jbm-background: var(--myst-color-background, var(--pst-color-background, Canvas));
  --jbm-foreground: var(--myst-color-text, var(--pst-color-text-base, CanvasText));
  --jbm-surface: var(--myst-color-surface, var(--pst-color-surface, Field));
  --jbm-muted-surface: color-mix(in srgb, var(--jbm-foreground) 6%, var(--jbm-background));
  --jbm-raised-surface: color-mix(in srgb, var(--jbm-foreground) 3%, var(--jbm-background));
  --jbm-border: var(--myst-color-border, var(--pst-color-border, color-mix(in srgb, var(--jbm-foreground) 24%, transparent)));
  --jbm-muted-foreground: var(--myst-color-text-muted, var(--pst-color-text-muted, color-mix(in srgb, var(--jbm-foreground) 68%, transparent)));
  --jbm-link: var(--myst-color-link, var(--pst-color-link, LinkText));
  --jbm-accent: var(--myst-color-primary, var(--pst-color-primary, Highlight));
  --jbm-accent-foreground: var(--myst-color-on-primary, HighlightText);
  --jbm-focus-ring: var(--myst-color-primary, var(--pst-color-primary, Highlight));
  --jbm-code-bg: var(--myst-color-code-background, var(--pst-color-on-background, var(--jbm-muted-surface)));
  --jbm-code-fg: var(--jbm-foreground);
  --jbm-code-border: var(--jbm-border);
  --jbm-inline-code-bg: color-mix(in srgb, var(--jbm-accent) 10%, transparent);
  --jbm-inline-code-fg: var(--jbm-foreground);
  --jbm-hover-bg: color-mix(in srgb, var(--jbm-foreground) 8%, transparent);
  --jbm-selection-bg: color-mix(in srgb, var(--jbm-accent) 28%, transparent);
}

.${outputClass}[data-jb-theme="dark"] {
  color-scheme: dark;
  --jbm-background: var(--myst-color-background, var(--pst-color-background, #1c1917));
  --jbm-foreground: var(--myst-color-text, var(--pst-color-text-base, #e7e5e4));
  --jbm-surface: var(--myst-color-surface, var(--pst-color-surface, #292524));
  --jbm-muted-surface: color-mix(in srgb, var(--jbm-foreground) 9%, var(--jbm-background));
  --jbm-raised-surface: color-mix(in srgb, var(--jbm-foreground) 6%, var(--jbm-background));
  --jbm-border: var(--myst-color-border, var(--pst-color-border, rgba(168, 162, 158, 0.36)));
  --jbm-muted-foreground: var(--myst-color-text-muted, var(--pst-color-text-muted, #a8a29e));
  --jbm-code-bg: var(--myst-color-code-background, var(--pst-color-on-background, #292524));
  --jbm-code-fg: var(--jbm-foreground);
}

.${outputClass}[data-jb-theme="light"] {
  color-scheme: light;
}

.${outputClass}[data-jb-theme="dark"]
  :where(
    .admonition,
    [class*="admonition"],
    .callout,
    .markdown.prose,
    .markdown.prose *,
    .codehilite,
    .codehilite *,
    .highlight,
    .highlight *,
    pre,
    pre *,
    code,
    code *,
    marimo-accordion,
    marimo-accordion *,
    table,
    thead,
    tbody,
    tr,
    th,
    td,
    .marimo-json-output,
    .marimo-json-output *,
    .json-viewer-theme-light,
    .json-viewer-theme-light *,
    label,
    input,
    output,
    [role="cell"],
    [role="columnheader"],
    [role="rowheader"]
  ) {
  color: var(--jbm-foreground, #e7e5e4) !important;
}

.${outputClass}[data-jb-theme="dark"]
  :where(.admonition, [class*="admonition"], .callout) {
  background: var(--jbm-muted-surface, #292524) !important;
  border-color: var(--jbm-border, rgba(168, 162, 158, 0.36)) !important;
}

.${outputClass}[data-jb-theme="dark"] .marimo .markdown.prose .admonition,
.${outputClass}[data-jb-theme="dark"]
  .marimo
  .markdown.prose
  [class*="admonition"],
.${outputClass}[data-jb-theme="dark"] .marimo .markdown.prose .callout {
  background: var(--jbm-muted-surface, #292524) !important;
  border-color: var(--jbm-border, rgba(168, 162, 158, 0.36)) !important;
  color: var(--jbm-foreground, #e7e5e4) !important;
}

.${outputClass}[data-jb-theme="dark"] .marimo .markdown.prose .admonition *,
.${outputClass}[data-jb-theme="dark"]
  .marimo
  .markdown.prose
  [class*="admonition"]
  *,
.${outputClass}[data-jb-theme="dark"] .marimo .markdown.prose .callout * {
  color: var(--jbm-foreground, #e7e5e4) !important;
}

.${outputClass}[data-jb-theme="dark"]
  :where([style*="background-color: orange"], [style*="background: orange"]) {
  color: #111827 !important;
}

.${outputClass} :where(marimo-island, marimo-cell-output) {
  max-width: 100%;
  min-width: 0;
  overflow-x: auto;
}

.${outputClass} :where(p, li) code,
.${outputClass} :where(p, li) code * {
  white-space: normal !important;
  overflow-wrap: anywhere;
  word-break: break-word;
}

@media (max-width: 48rem) {
  .${outputClass} :where(.myst-code pre, .myst-code code, .myst-code code *) {
    white-space: pre-wrap !important;
    overflow-wrap: anywhere;
    word-break: break-word;
  }
}

.${outputClass} :where(pre) {
  background: var(--jbm-code-bg, #292524) !important;
  color: var(--jbm-code-fg, #e7e5e4) !important;
  border: 0 !important;
  box-shadow: none !important;
}

.${outputClass} :where(.myst-code) {
  background: var(--jbm-code-bg, #292524) !important;
  border: 1px solid var(--jbm-code-border, rgba(168, 162, 158, 0.36));
  box-shadow: none !important;
}

.${outputClass} :where(.codehilite, .highlight) {
  background: var(--jbm-code-bg, #292524) !important;
  box-shadow: none !important;
}

.${outputClass} :where(.myst-code:hover) {
  box-shadow: none !important;
}

.${outputClass} :where(
  .codehilite pre,
  .highlight pre,
  .myst-code-body,
  .myst-code .myst-code-body,
  .myst-code .myst-code-body.hljs,
  .myst-code pre,
  .myst-code .hljs
) {
  background: transparent !important;
  background-color: transparent !important;
}

.${outputClass} :where(.highlight, .cell, .code-cell) {
  box-shadow: none !important;
}

.${outputClass} pre {
  background: var(--jbm-code-bg, #292524) !important;
  color: var(--jbm-code-fg, #e7e5e4) !important;
  border: 0 !important;
  box-shadow: none !important;
}

.${outputClass} :where(
  marimo-island[data-jupyter-book-marimo-hide-output="true"] > marimo-cell-output,
  marimo-island[data-jupyter-book-marimo-hide-output="true"] > :first-child:not(marimo-ui-element)
) {
  display: none !important;
}
`;

export const shadowThemeCss = `
:host {
  color-scheme: inherit;
  --background: var(--jbm-background, Canvas);
  --foreground: var(--jbm-foreground, CanvasText);
  --card: var(--jbm-surface, Field);
  --card-foreground: var(--jbm-foreground, FieldText);
  --popover: var(--jbm-surface, Field);
  --popover-foreground: var(--jbm-foreground, FieldText);
  --primary: var(--jbm-accent, Highlight);
  --primary-foreground: var(--jbm-accent-foreground, HighlightText);
  --secondary: var(--jbm-muted-surface, ButtonFace);
  --secondary-foreground: var(--jbm-foreground, ButtonText);
  --muted: var(--jbm-muted-surface, ButtonFace);
  --muted-foreground: var(--jbm-muted-foreground, GrayText);
  --accent: var(--jbm-accent, Highlight);
  --accent-foreground: var(--jbm-accent-foreground, HighlightText);
  --border: var(--jbm-border, ButtonBorder);
  --input: var(--jbm-border, ButtonBorder);
  --ring: var(--jbm-focus-ring, Highlight);
  --cm-background: var(--jbm-code-bg, var(--background));
  --cm-foreground: var(--jbm-code-fg, var(--foreground));
  --cm-comment: var(--jbm-muted-foreground, GrayText);
}

:host([data-jb-theme="dark"]) {
  color-scheme: dark;
  --background: var(--jbm-background, #1c1917);
  --foreground: var(--jbm-foreground, #d6d3d1);
  --card: var(--jbm-surface, #292524);
  --card-foreground: var(--jbm-foreground, #d6d3d1);
  --popover: var(--jbm-surface, #292524);
  --popover-foreground: var(--jbm-foreground, #d6d3d1);
  --secondary: var(--jbm-muted-surface, #44403c);
  --secondary-foreground: var(--jbm-foreground, #f5f5f4);
  --muted: var(--jbm-muted-surface, #292524);
  --muted-foreground: var(--jbm-muted-foreground, #a8a29e);
  --border: var(--jbm-border, rgba(168, 162, 158, 0.36));
  --input: var(--jbm-border, rgba(168, 162, 158, 0.4));
  --cm-background: var(--jbm-code-bg, #292524);
  --cm-foreground: var(--jbm-code-fg, #e7e5e4);
  --cm-comment: var(--jbm-muted-foreground, #a8a29e);
}

:host([data-jb-theme="light"]) {
  color-scheme: light;
}

:host([data-jb-theme="dark"]) :where(.marimo) {
  background: transparent !important;
  color: var(--jbm-foreground, #e7e5e4) !important;
}

:host([data-jb-theme="dark"])
  :where(
    .admonition,
    [class*="admonition"],
    .callout,
    .marimo *,
    .markdown.prose,
    .markdown.prose *,
    .codehilite,
    .codehilite *,
    .highlight,
    .highlight *,
    pre,
    pre *,
    code,
    code *,
    marimo-accordion,
    marimo-accordion *,
    table,
    thead,
    tbody,
    tr,
    th,
    td,
    .marimo-json-output,
    .marimo-json-output *,
    .json-viewer-theme-light,
    .json-viewer-theme-light *,
    label,
    input,
    output,
    [role="cell"],
    [role="columnheader"],
    [role="rowheader"]
  ) {
  color: var(--jbm-foreground, #e7e5e4) !important;
}

:host([data-jb-theme="dark"])
  :where(.admonition, [class*="admonition"], .callout) {
  background: var(--muted, #292524) !important;
  border-color: var(--jbm-border, rgba(168, 162, 158, 0.36)) !important;
}

:host([data-jb-theme="dark"])
  :where([style*="background-color: orange"], [style*="background: orange"]) {
  color: #111827 !important;
}

:host :where(input, button, select, textarea, [role="button"], [role="combobox"]) {
  min-height: 1.75rem;
}

:host :where(table) {
  max-width: 100%;
}

:host([data-jb-theme="dark"])
  :where(
    .bg-background,
    .bg-card,
    .bg-white,
    [class*="bg-background"],
    [class*="bg-card"],
    [class*="bg-white"]
  ) {
  background: var(--jbm-surface, #292524) !important;
  color: var(--jbm-foreground, #e7e5e4) !important;
}

:host([data-jb-theme="dark"])
  :where(.cm-editor, .cm-scroller, .cm-content) {
  background: #292524 !important;
  color: #e7e5e4 !important;
  --cm-background: #292524 !important;
  --cm-foreground: #e7e5e4 !important;
}

:host([data-jb-theme="dark"]) :where(.cm-gutters) {
  background: #1c1917 !important;
  border-color: rgba(168, 162, 158, 0.36) !important;
  color: #a8a29e !important;
}

:host([data-jb-theme="dark"]) :where(.cm-activeLine, .cm-activeLineGutter) {
  background: var(--jbm-hover-bg, rgba(255, 255, 255, 0.08)) !important;
}

:host([data-jb-theme="dark"]) .marimo,
:host([data-jb-theme="dark"]) .marimo :is(
  .admonition,
  [class*="admonition"],
  .callout,
  .contents.light,
  .font-prose,
  .mo-label,
  .mo-label *,
  .markdown,
  .markdown *,
  .codehilite,
  .codehilite *,
  .highlight,
  .highlight *,
  pre,
  pre *,
  code,
  code *,
  marimo-accordion,
  marimo-accordion *,
  table,
  thead,
  tbody,
  tr,
  th,
  td,
  .marimo-json-output,
  .marimo-json-output *,
  .json-viewer-theme-light,
  .json-viewer-theme-light *,
  label,
  output,
  [id="sliderValues"],
  [role="cell"],
  [role="columnheader"],
  [role="rowheader"]
) {
  color: var(--jbm-foreground, #e7e5e4) !important;
}

:host([data-jb-theme="dark"]) .marimo
  :is(.codehilite, .highlight, pre) {
  background: var(--jbm-code-bg, #292524) !important;
  border-color: var(--jbm-border, rgba(168, 162, 158, 0.36)) !important;
}

:host([data-jb-theme="dark"]) .marimo :is(
  .bg-background,
  .bg-card,
  .bg-muted,
  .bg-secondary,
  .bg-white,
  [class*="bg-background"],
  [class*="bg-card"],
  [class*="bg-muted"],
  [class*="bg-secondary"],
  [class*="bg-white"]
) {
  background: var(--jbm-surface, #292524) !important;
  color: var(--jbm-foreground, #e7e5e4) !important;
}

:host([data-jb-theme="dark"]) .marimo :is(input, textarea, select) {
  background: var(--jbm-surface, #292524) !important;
  border-color: var(--jbm-border, rgba(168, 162, 158, 0.36)) !important;
  color: var(--jbm-foreground, #e7e5e4) !important;
  color-scheme: dark !important;
}

:host([data-jb-theme="dark"]) .marimo :is(input, textarea)::placeholder {
  color: var(--jbm-muted-foreground, #a8a29e) !important;
}

:host([data-jb-theme="dark"]) .marimo .contents.light,
:host([data-jb-theme="dark"]) .marimo .contents.light *,
:host([data-jb-theme="dark"]) .marimo .contents.light .font-prose,
:host([data-jb-theme="dark"]) .marimo .contents.light .font-prose *,
:host([data-jb-theme="dark"]) .marimo .contents.light .markdown,
:host([data-jb-theme="dark"]) .marimo .contents.light .markdown *,
:host([data-jb-theme="dark"]) .marimo .contents.light .mo-label,
:host([data-jb-theme="dark"]) .marimo .contents.light .mo-label *,
:host([data-jb-theme="dark"]) .marimo .contents.light .text-muted-foreground,
:host([data-jb-theme="dark"])
  .marimo
  .contents.light
  .text-muted-foreground
  * {
  color: var(--jbm-foreground, #e7e5e4) !important;
}

:host([data-jb-theme="dark"]) .marimo .contents.light :is(
  input,
  textarea,
  select
) {
  background: var(--jbm-surface, #292524) !important;
  border-color: var(--jbm-border, rgba(168, 162, 158, 0.36)) !important;
  color: var(--jbm-foreground, #e7e5e4) !important;
  color-scheme: dark !important;
}

:host([data-jb-theme="dark"]) .marimo .contents.light option {
  background: var(--jbm-surface, #292524) !important;
  color: var(--jbm-foreground, #e7e5e4) !important;
  color-scheme: dark !important;
}

:host([data-jb-theme="dark"])
  .marimo
  .contents.light
  :is(input, textarea)::placeholder {
  color: var(--jbm-muted-foreground, #a8a29e) !important;
}

:host([data-jb-theme="dark"]) .marimo .contents.light input.bg-background,
:host([data-jb-theme="dark"]) .marimo .contents.light input.flex-1,
:host([data-jb-theme="dark"]) .marimo .contents.light input.w-full,
:host([data-jb-theme="dark"]) .marimo .contents.light input[class*="placeholder"],
:host([data-jb-theme="dark"]) .marimo .contents.light textarea.bg-background,
:host([data-jb-theme="dark"]) .marimo .contents.light select.bg-background {
  background: var(--jbm-surface, #292524) !important;
  border-color: var(--jbm-border, rgba(168, 162, 158, 0.36)) !important;
  color: var(--jbm-foreground, #e7e5e4) !important;
  color-scheme: dark !important;
}

:host([data-jb-theme="dark"]) .marimo .contents.light .bg-muted,
:host([data-jb-theme="dark"]) .marimo .contents.light .bg-secondary,
:host([data-jb-theme="dark"]) .marimo .contents.light [class*="bg-muted"],
:host([data-jb-theme="dark"]) .marimo .contents.light [class*="bg-secondary"] {
  background: var(--jbm-surface, #292524) !important;
  color: var(--jbm-foreground, #e7e5e4) !important;
}

/* The generated external-dependencies page imports Slider2D from the upstream
   tutorial source, which is not pinned in this repo. Keep this override tied to
   the rendered canvas contract and rerun that page's browser smoke when the
   dependency changes. */
:host([data-jb-theme="dark"]) .marimo canvas[id="sliderCanvas"] {
  background: var(--jbm-surface, #292524) !important;
  border: 1px solid var(--jbm-border, rgba(168, 162, 158, 0.36)) !important;
}
`;
