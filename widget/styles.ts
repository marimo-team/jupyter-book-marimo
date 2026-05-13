export const outputClass = "marimo-jupyter-book-output";
export const loadingClass = "marimo-jupyter-book-loading";
export const pendingClass = "marimo-jupyter-book-pending";
export const previewClass = "marimo-jupyter-book-preview";
export const pendingStatusClass = "marimo-jupyter-book-pending-status";

export const runtimeElementSelector =
  "marimo-anywidget, marimo-ui-element, marimo-mime-renderer, " +
  "marimo-json-output, marimo-table";

export const nestedRuntimeContainerSelector =
  "marimo-accordion, marimo-tabs, marimo-carousel";

export const themeStyleId = "marimo-jupyter-book-theme";
export const shadowThemeStyleId = "marimo-jupyter-book-shadow-theme";
export const customStyleAttribute = "data-jupyter-book-marimo-custom-style";

/*
 * Styling contract:
 * - the bridge owns structure: mounting, pending previews, skeletons, and
 *   shadow-root style transport;
 * - book themes own color: they can set --jbm-* variables with normal CSS;
 * - custom stylesheets are the escape hatch for widget-specific shadow DOM.
 */
export const globalThemeCss = `
.${outputClass} {
  color: inherit;
  color-scheme: inherit;
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
  --jbm-pending-bg: color-mix(in srgb, var(--jbm-surface) 78%, transparent);
  --jbm-pending-border: var(--jbm-border);
  --jbm-pending-status-bg: color-mix(in srgb, var(--jbm-background) 86%, transparent);
  --jbm-pending-status-fg: var(--jbm-muted-foreground);
  --jbm-skeleton-bg: color-mix(in srgb, var(--jbm-surface) 86%, transparent);
  --jbm-skeleton-line: color-mix(in srgb, var(--jbm-foreground) 14%, transparent);
  --jbm-skeleton-line-strong: color-mix(in srgb, var(--jbm-foreground) 24%, transparent);
  --jbm-hover-bg: color-mix(in srgb, var(--jbm-foreground) 8%, transparent);
  --jbm-selection-bg: color-mix(in srgb, var(--jbm-accent) 28%, transparent);
}

.${outputClass}[data-jb-theme="dark"] {
  color-scheme: dark;
}

.${outputClass}[data-jb-theme="light"] {
  color-scheme: light;
}

.${outputClass} :where(pre) {
  background: var(--jbm-code-bg) !important;
  color: var(--jbm-code-fg) !important;
  border: 0 !important;
  box-shadow: none !important;
}

.${outputClass} :where(.myst-code) {
  background: var(--jbm-code-bg) !important;
  border: 1px solid var(--jbm-code-border);
  box-shadow: none !important;
}

.${outputClass} :where(.myst-code:hover) {
  box-shadow: none !important;
}

.${outputClass} :where(
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
  background: var(--jbm-code-bg) !important;
  color: var(--jbm-code-fg) !important;
  border: 0 !important;
  box-shadow: none !important;
}

.${pendingClass} {
  position: relative;
  max-width: 100%;
}

.${pendingClass}[data-has-preview="true"] {
  width: fit-content;
  max-width: 100%;
  padding: 0.5rem;
  border: 1px dashed var(--jbm-pending-border);
  border-radius: 0.5rem;
  background: var(--jbm-pending-bg);
}

.${pendingClass}[data-has-preview="true"] > .${previewClass} {
  opacity: 0.58;
  filter: grayscale(0.32) saturate(0.82);
  pointer-events: none;
  user-select: none;
}

.${pendingClass}:not([data-has-preview="true"]) > .${previewClass},
.${pendingClass}:not([data-has-preview="true"]) > .${pendingStatusClass},
.${pendingClass}[data-has-preview="true"] > .${loadingClass} {
  display: none;
}

.${pendingStatusClass} {
  display: inline-flex;
  width: fit-content;
  align-items: center;
  gap: 0.375rem;
  margin-top: 0.375rem;
  padding: 0.125rem 0.5rem;
  border: 1px solid var(--jbm-pending-border);
  border-radius: 999px;
  background: var(--jbm-pending-status-bg);
  color: var(--jbm-pending-status-fg);
  font-size: 0.75rem;
  line-height: 1.25;
  font-weight: 500;
}

.${pendingStatusClass}::before {
  content: "";
  width: 0.375rem;
  height: 0.375rem;
  border-radius: 999px;
  background: currentColor;
  opacity: 0.7;
}

.${loadingClass} {
  display: grid;
  gap: 0.625rem;
  width: min(100%, 34rem);
  min-height: 5.25rem;
  padding: 0.875rem;
  border: 1px solid var(--jbm-pending-border);
  border-radius: 0.5rem;
  background: var(--jbm-skeleton-bg);
}

.${loadingClass} > span {
  display: block;
  height: 0.75rem;
  border-radius: 999px;
  background: var(--jbm-skeleton-line);
}

.${loadingClass} > span:first-child {
  width: 62%;
  background: var(--jbm-skeleton-line-strong);
}

.${loadingClass} > span:nth-child(2) {
  width: 92%;
}

.${loadingClass} > span:last-child {
  width: 44%;
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
}

:host([data-jb-theme="light"]) {
  color-scheme: light;
}
`;
