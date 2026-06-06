export const outputClass = "marimo-jupyter-book-output";

export const themeStyleId = "marimo-jupyter-book-theme";
export const shadowThemeStyleId = "marimo-jupyter-book-shadow-theme";
export const customStyleAttribute = "data-jupyter-book-marimo-custom-style";
export const scratchpadTipAttribute = "data-jupyter-book-marimo-scratchpad-tip";
export const codeEditorThemeAttribute = "data-jupyter-book-marimo-code-editor-theme";
export const editorRunControlAttribute = "data-jupyter-book-marimo-editor-run-control";

/*
 * Styling contract:
 * - the bridge owns light-DOM mounting and shadow-root style transport
 * - book themes own color by setting --jbm-* variables with normal CSS
 * - custom stylesheets carry widget-specific shadow DOM overrides.
 */
export const globalThemeCss = `
.${outputClass} {
  box-sizing: border-box;
  color: inherit;
  color-scheme: inherit;
  max-width: 100%;
  min-width: 0;
  overflow-x: auto;
  --jbm-error-editor-gap: 0.5rem;
  --jbm-output-margin-block: 1rem;
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
  --jbm-error-bg: transparent;
  --jbm-error-border: #e5e7eb;
  --jbm-error-title: #ea5d5d;
  --jbm-error-text: #64748b;
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
  --jbm-error-bg: color-mix(in srgb, #f87171 6%, var(--jbm-background));
  --jbm-error-border: color-mix(in srgb, #f87171 42%, var(--jbm-border));
  --jbm-error-title: #fca5a5;
  --jbm-error-text: #d6d3d1;
}

.${outputClass}[data-jb-theme="light"] {
  color-scheme: light;
}

.${outputClass}:where(
  :has(> marimo-island:not([hidden]):not([data-jupyter-book-marimo-hide-output="true"]) > :not(span:empty)),
  :has(marimo-cell-output > :not(span:empty)),
  :has(marimo-ui-element)
) {
  margin-block: var(--jbm-output-margin-block, 1rem);
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

/*
 * Jupyter Book supplies the page surface. Keep marimo island variables and
 * runtime ownership, but let each component draw its own visible box.
 */
.${outputClass} > marimo-island.marimo {
  display: contents;
}

.${outputClass} :where([${scratchpadTipAttribute}="true"]) {
  display: none !important;
}

.${outputClass} :where(marimo-ui-element:has(> marimo-code-editor)) {
  display: block !important;
  max-width: 100%;
  position: relative !important;
}

.${outputClass} :where([${editorRunControlAttribute}="true"]) {
  align-items: center;
  background: var(--jbm-surface, Field);
  border: 1px solid var(--jbm-border, ButtonBorder);
  border-radius: 0.375rem;
  color: var(--jbm-foreground, ButtonText);
  cursor: pointer;
  display: inline-flex;
  height: 1.5rem;
  justify-content: center;
  margin: 0;
  padding: 0;
  position: absolute;
  right: 0.35rem;
  top: 0.35rem;
  width: 1.5rem;
  z-index: 20;
}

.${outputClass} :where([${editorRunControlAttribute}="true"])::before {
  border-block: 0.28rem solid transparent;
  border-inline-start: 0.45rem solid currentColor;
  content: "";
  display: block;
  margin-inline-start: 0.08rem;
}

.${outputClass} :where([${editorRunControlAttribute}="true"]:hover) {
  background: var(--jbm-hover-bg, ButtonFace);
}

.${outputClass} :where([${editorRunControlAttribute}="true"]:focus-visible) {
  outline: 2px solid var(--jbm-focus-ring, Highlight);
  outline-offset: 2px;
}

.${outputClass} :where([${editorRunControlAttribute}="true"]:disabled) {
  cursor: wait;
  opacity: 0.65;
}

/*
 * Exported editor errors do not include the full notebook cell output-area
 * wrapper. Restore the padding at the alert boundary so intentional error
 * examples keep the same readable inset in static books.
 */
.${outputClass}
  :where(
    marimo-island.marimo > [role="alert"],
    marimo-island.marimo > :has(> [role="alert"]) > [role="alert"],
    marimo-island.marimo [role="alert"]
  ) {
  background: var(--jbm-error-bg, Canvas) !important;
  border-color: var(--jbm-error-border, ButtonBorder) !important;
  box-sizing: border-box;
  color: var(--jbm-error-text, CanvasText) !important;
  padding: 1rem !important;
}

.${outputClass}
  :where(marimo-island.marimo [role="alert"])
  :where(h1, h2, h3, h4, h5, h6, .text-destructive) {
  color: var(--jbm-error-title, #dc2626) !important;
}

.${outputClass}
  :where(marimo-island.marimo [role="alert"])
  :where([data-orientation="vertical"]) {
  border-color: var(--jbm-error-border, ButtonBorder) !important;
}

.${outputClass}
  :where(marimo-island.marimo [role="alert"])
  :where(a) {
  color: var(--jbm-link, LinkText) !important;
}

/*
 * marimo renders visible source editors as siblings of the server output. Keep
 * an intentional gap when an error display is followed by that source editor.
 */
.${outputClass}
  :where(
    marimo-island.marimo > [role="alert"] + marimo-ui-element > marimo-code-editor,
    marimo-island.marimo > :has(> [role="alert"]) + marimo-ui-element > marimo-code-editor
  ) {
  margin-block-start: var(--jbm-error-editor-gap, 0.5rem);
}

.${outputClass}
  :where(
    marimo-accordion,
    marimo-array,
    marimo-button,
    marimo-checkbox,
    marimo-code-editor,
    marimo-date,
    marimo-dict,
    marimo-dropdown,
    marimo-file,
    marimo-number,
    marimo-radio,
    marimo-range-slider,
    marimo-slider,
    marimo-switch,
    marimo-table,
    marimo-tabs,
    marimo-text,
    marimo-text-area
  ) {
  display: inline-block;
  line-height: normal;
  max-width: 100%;
  vertical-align: middle;
}

.${outputClass}
  :where(
    marimo-accordion,
    marimo-array,
    marimo-code-editor,
    marimo-dict,
    marimo-file,
    marimo-table,
    marimo-tabs,
    marimo-text-area
  ) {
  display: block;
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
  --jbm-error-bg: color-mix(in srgb, #f87171 6%, var(--jbm-background, #1c1917));
  --jbm-error-border: color-mix(in srgb, #f87171 42%, var(--jbm-border, rgba(168, 162, 158, 0.36)));
  --jbm-error-title: #fca5a5;
  --jbm-error-text: #d6d3d1;
}

:host([data-jb-theme="light"]) {
  color-scheme: light;
}

:host :where([${scratchpadTipAttribute}="true"]) {
  display: none !important;
}

:host
  :where(
    .marimo > [role="alert"],
    .marimo > :has(> [role="alert"]) > [role="alert"],
    .marimo [role="alert"],
    [role="alert"]
  ) {
  background: var(--jbm-error-bg, Canvas) !important;
  border-color: var(--jbm-error-border, ButtonBorder) !important;
  box-sizing: border-box;
  color: var(--jbm-error-text, CanvasText) !important;
  padding: 1rem !important;
}

:host
  :where(.marimo [role="alert"], [role="alert"])
  :where(h1, h2, h3, h4, h5, h6, .text-destructive) {
  color: var(--jbm-error-title, #dc2626) !important;
}

:host
  :where(.marimo [role="alert"], [role="alert"])
  :where([data-orientation="vertical"]) {
  border-color: var(--jbm-error-border, ButtonBorder) !important;
}

:host :where(.marimo [role="alert"], [role="alert"]) :where(a) {
  color: var(--jbm-link, LinkText) !important;
}

:host(:not([data-min-height])) :where(.cm-editor) {
  min-height: 0 !important;
}

/* marimo's UI utilities are layered. Some notebook widget stylesheets inject
   unlayered Tailwind resets into component shadow roots, so keep the UI control
   contract explicit at this bridge boundary. */
:host :where(.marimo .h-3) {
  height: calc(var(--spacing, 0.25rem) * 3) !important;
}

:host :where(.marimo .w-3) {
  width: calc(var(--spacing, 0.25rem) * 3) !important;
}

:host :where(.marimo .h-4) {
  height: calc(var(--spacing, 0.25rem) * 4) !important;
  min-height: calc(var(--spacing, 0.25rem) * 4) !important;
}

:host :where(.marimo .w-4) {
  width: calc(var(--spacing, 0.25rem) * 4) !important;
}

:host :where(.marimo .h-6) {
  height: calc(var(--spacing, 0.25rem) * 6) !important;
  min-height: calc(var(--spacing, 0.25rem) * 6) !important;
}

:host :where(.marimo .h-px) {
  height: 1px !important;
}

:host :where(.marimo .px-0\\.5) {
  padding-inline: calc(var(--spacing, 0.25rem) * 0.5) !important;
}

:host :where(.marimo .px-1\\.5) {
  padding-inline: calc(var(--spacing, 0.25rem) * 1.5) !important;
}

:host :where(.marimo .px-2) {
  padding-inline: calc(var(--spacing, 0.25rem) * 2) !important;
}

:host :where(.marimo .py-1) {
  padding-block: calc(var(--spacing, 0.25rem) * 1) !important;
}

:host :where(.marimo .border-input) {
  border-color: var(--input, ButtonBorder) !important;
}

:host :where(.marimo .border-primary) {
  border-color: var(--primary, Highlight) !important;
}

:host :where(.marimo .border-s-2) {
  border-inline-start-color: var(--border, ButtonBorder) !important;
  border-inline-start-style: solid !important;
  border-inline-start-width: 2px !important;
}

:host :where(.marimo .bg-background) {
  background-color: var(--background, Field) !important;
}

:host :where(.marimo .bg-border) {
  background-color: var(--border, ButtonBorder) !important;
}

:host :where(.marimo .text-muted-foreground) {
  color: var(--muted-foreground, GrayText) !important;
}

:host :where(.marimo .placeholder\\:text-muted-foreground)::placeholder {
  color: var(--muted-foreground, GrayText) !important;
}

:host :where(.marimo .shadow-xs-solid) {
  box-shadow:
    1px 1px 0 0 var(--base-shadow-darker, rgba(128, 128, 128, 0.4)),
    0 0 2px 0 rgba(128, 128, 128, 0.2) !important;
}

:host :where(.marimo [data-testid="marimo-plugin-number-input"] input) {
  min-height: calc(var(--spacing, 0.25rem) * 6) !important;
}

:host :where(.marimo [data-testid="marimo-plugin-number-input"] button) {
  align-items: center !important;
  display: flex !important;
  height: auto !important;
  justify-content: center !important;
  min-height: 0 !important;
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
    .marimo *:not(.cm-editor):not(.cm-editor *),
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
:host([data-jb-theme="dark"])
  .marimo
  .contents.light
  *:not(.cm-editor):not(.cm-editor *),
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

:host([data-jb-theme="dark"]) :where(.marimo [role="alert"], [role="alert"]) {
  background: var(--jbm-error-bg, #241b1b) !important;
  border-color: var(--jbm-error-border, rgba(248, 113, 113, 0.42)) !important;
  color: var(--jbm-error-text, #d6d3d1) !important;
}

:host([data-jb-theme="dark"])
  :where(.marimo [role="alert"], [role="alert"])
  :where(h1, h2, h3, h4, h5, h6, .text-destructive) {
  color: var(--jbm-error-title, #fca5a5) !important;
}

:host([data-jb-theme="dark"])
  :where(.marimo [role="alert"], [role="alert"])
  :where([data-orientation="vertical"]) {
  border-color: var(--jbm-error-border, rgba(248, 113, 113, 0.42)) !important;
}

:host([data-jb-theme="dark"])
  :where(.marimo [role="alert"], [role="alert"])
  :where(a) {
  color: var(--jbm-link, #93c5fd) !important;
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
