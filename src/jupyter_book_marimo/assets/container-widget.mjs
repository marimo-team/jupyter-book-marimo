/**
 * anywidget container for exported marimo islands.
 *
 * MyST renders anywidgets inside a shadow root. marimo islands expect normal
 * light DOM, a hidden notebook source node, and a same-origin bridge asset.
 * This adapter keeps that boundary explicit.
 *
 * The Python plugin copies this file into the generated .jupyter-book-marimo/
 * directory during a book build. That copy is the served ESM asset; this
 * packaged file is the source of truth.
 */

const outputClass = "marimo-jupyter-book-output";
const loadingClass = "marimo-jupyter-book-loading";
const pendingClass = "marimo-jupyter-book-pending";
const previewClass = "marimo-jupyter-book-preview";
const runtimeElementSelector =
  "marimo-anywidget, marimo-ui-element, marimo-mime-renderer, " +
  "marimo-json-output, marimo-table";
const nestedRuntimeContainerSelector =
  "marimo-accordion, marimo-tabs, marimo-carousel";
const themeStyleId = "marimo-jupyter-book-theme";
const shadowThemeStyleId = "marimo-jupyter-book-shadow-theme";
const customStyleAttribute = "data-jupyter-book-marimo-custom-style";

/*
 * One marimo app can be split across many anywidget outputs. Keep page-global
 * runtime state here, then release mount-owned observers and shared nodes when
 * each anywidget unmounts.
 */
const loadedModules = new Map();
const notebookCodeNodes = new Map();
const appRecords = new Map();
const observedShadowRoots = new WeakMap();
const observedShadowRootStyles = new WeakMap();
const shadowRootsByMount = new Map();
const themedRoots = new Map();

let themeObserverStarted = false;
let documentNavigationStarted = false;

/*
 * Styling contract:
 * - the bridge owns structure: mounting, pending previews, skeletons, and
 *   shadow-root style transport;
 * - book themes own color: they can set --jbm-* variables with normal CSS;
 * - custom stylesheets are the escape hatch for widget-specific shadow DOM.
 */
const globalThemeCss = `
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
.${pendingClass}[data-has-preview="true"] > .${loadingClass} {
  display: none;
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

const shadowThemeCss = `
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

// Read anywidget models without assuming the host uses Backbone-style .get().
function getModelValue(model, key, fallback = "") {
  if (model && typeof model.get === "function") {
    const value = model.get(key);
    return value == null ? fallback : value;
  }
  const value = model?.[key];
  return value == null ? fallback : value;
}

function getModelString(model, key) {
  const value = getModelValue(model, key);
  return typeof value === "string" ? value : "";
}

function getModelStringList(model, key) {
  const value = getModelValue(model, key, []);
  if (Array.isArray(value)) {
    return value.filter((item) => typeof item === "string");
  }
  return typeof value === "string" ? [value] : [];
}

function getModelStyleBlocks(model) {
  const value = getModelValue(model, "customStyleBlocks", []);
  if (!Array.isArray(value)) return [];
  return value
    .filter(
      (item) =>
        item &&
        typeof item === "object" &&
        typeof item.id === "string" &&
        typeof item.css === "string",
    )
    .map((item) => ({ id: item.id, css: item.css }));
}

// Normalize exported island fragments before mounting them into light DOM.
function parseHtml(html) {
  const template = document.createElement("template");
  template.innerHTML = typeof html === "string" ? html : "";
  return template.content;
}

function stringHash(value) {
  let hash = 5381;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 33) ^ value.charCodeAt(index);
  }
  return (hash >>> 0).toString(36);
}

function decodeMarimoCode(fragment) {
  const node = fragment.querySelector("marimo-code");
  const encoded = node?.textContent?.trim();
  if (!encoded) return "";
  try {
    return decodeURIComponent(encoded);
  } catch {
    return encoded;
  }
}

function appIdFrom(fragment, notebookCode) {
  const island = fragment.querySelector("marimo-island[data-app-id]");
  if (island) return island.getAttribute("data-app-id") ?? "";
  return notebookCode ? `marimo-${stringHash(notebookCode)}` : "";
}

// marimo's runtime reads this global while its module evaluates.
function installExportContext(notebookCode) {
  if (!notebookCode) return;
  Object.defineProperty(window, "__MARIMO_EXPORT_CONTEXT__", {
    value: Object.freeze({ trusted: true, notebookCode }),
    writable: false,
    configurable: true,
  });
}

function retainNotebookCode(appId, notebookCode) {
  /*
   * marimo discovers exported notebook source from light-DOM marimo-code nodes.
   * anywidget renders in a shadow root, so the bridge hoists one hidden shared
   * source node per app and reference-counts it across outputs.
   */
  if (!appId || !notebookCode) return () => {};

  const existing = notebookCodeNodes.get(appId);
  if (existing) {
    existing.uses += 1;
    return () => releaseNotebookCode(appId);
  }

  const node = document.createElement("marimo-code");
  node.hidden = true;
  node.dataset.appId = appId;
  node.dataset.jupyterBookMarimo = "true";
  node.textContent = encodeURIComponent(notebookCode);
  document.body.appendChild(node);

  notebookCodeNodes.set(appId, { node, uses: 1 });
  return () => releaseNotebookCode(appId);
}

function releaseNotebookCode(appId) {
  const record = notebookCodeNodes.get(appId);
  if (!record) return;

  record.uses -= 1;
  if (record.uses > 0) return;

  record.node.remove();
  notebookCodeNodes.delete(appId);
}

function linksFromFragment(fragment) {
  return Array.from(
    fragment.querySelectorAll("link[href]"),
    (link) =>
      Object.fromEntries(
        Array.from(link.attributes, (attribute) => [
          attribute.name,
          attribute.value,
        ]),
      ),
  );
}

function modulesFromFragment(fragment) {
  return Array.from(
    fragment.querySelectorAll('script[type="module"][src]'),
    (script) => script.getAttribute("src"),
  ).filter((src) => typeof src === "string" && src.length > 0);
}

function assetsFromModel(model, head) {
  // Prefer structured assets from Python; fall back to old head HTML payloads.
  const assets = getModelValue(model, "assets", {});
  const record = assets && typeof assets === "object" ? assets : {};
  return {
    links: Array.isArray(record.links) ? record.links : linksFromFragment(head),
    moduleScripts: Array.isArray(record.moduleScripts)
      ? record.moduleScripts.filter((src) => typeof src === "string")
      : modulesFromFragment(head),
  };
}

// Load marimo runtime assets once while preserving same-origin bridge loading.
function ensureLinks(links) {
  for (const attrs of links) {
    if (!attrs?.href) continue;

    const href = new URL(attrs.href, document.baseURI).href;
    const rel = typeof attrs.rel === "string" ? attrs.rel : "";
    const existing = Array.from(document.head.querySelectorAll("link[href]"))
      .find(
        (link) =>
          link instanceof HTMLLinkElement &&
          link.href === href &&
          (link.getAttribute("rel") || "") === rel,
      );
    if (existing) continue;

    const link = document.createElement("link");
    for (const [key, value] of Object.entries(attrs)) {
      if (value == null) continue;
      link.setAttribute(key, String(value));
    }
    link.href = href;
    document.head.appendChild(link);
  }
}

function normalizedStylesheetHrefs(stylesheets) {
  return Array.from(
    new Set(
      stylesheets
        .filter((stylesheet) => typeof stylesheet === "string")
        .map((stylesheet) => stylesheet.trim())
        .filter(Boolean)
        .map((stylesheet) => new URL(stylesheet, document.baseURI).href),
    ),
  );
}

function hasCustomStylesheet(parent, href) {
  return Array.from(parent.querySelectorAll(`link[${customStyleAttribute}]`))
    .some(
      (link) =>
        link instanceof HTMLLinkElement &&
        new URL(link.href, document.baseURI).href === href,
    );
}

function ensureCustomStylesheets(root, stylesheets) {
  const parent = root instanceof ShadowRoot ? root : document.head;
  for (const href of normalizedStylesheetHrefs(stylesheets)) {
    if (hasCustomStylesheet(parent, href)) continue;

    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = href;
    link.setAttribute(customStyleAttribute, "true");
    parent.appendChild(link);
  }
}

function normalizedStyleBlocks(styleBlocks) {
  const seen = new Set();
  const normalized = [];
  for (const block of styleBlocks) {
    if (!block?.id || seen.has(block.id)) continue;
    seen.add(block.id);
    normalized.push(block);
  }
  return normalized;
}

function ensureCustomStyleBlocks(root, styleBlocks) {
  const parent = root instanceof ShadowRoot ? root : document.head;
  for (const block of normalizedStyleBlocks(styleBlocks)) {
    const existing = Array.from(
      parent.querySelectorAll(`style[${customStyleAttribute}]`),
    ).find((node) => node.dataset.styleId === block.id);
    if (existing) continue;

    const style = document.createElement("style");
    style.setAttribute(customStyleAttribute, "true");
    style.dataset.styleId = block.id;
    style.textContent = block.css;
    parent.appendChild(style);
  }
}

function ensureModule(src) {
  // Dynamic import is the browser-visible equivalent of loading marimo's head.
  const href = new URL(src, document.baseURI).href;
  if (loadedModules.has(href)) return loadedModules.get(href);

  const promise = import(href).then(
    () => undefined,
    () => {
      throw new Error(`Failed to load marimo runtime: ${href}`);
    },
  );

  loadedModules.set(href, promise);
  return promise;
}

function appRecord(appId) {
  /*
   * One payload-bearing island boots the marimo app. Sibling islands with the
   * same appId share this readiness promise instead of re-importing assets.
   */
  const existing = appRecords.get(appId);
  if (existing) return existing;

  const record = {
    ready: false,
    started: false,
    uses: 0,
    promise: null,
    resolve: () => {},
    reject: () => {},
  };

  record.promise = new Promise((resolve, reject) => {
    record.resolve = resolve;
    record.reject = reject;
  });

  appRecords.set(appId, record);
  return record;
}

function retainApp(appId, notebookCode, assets) {
  if (!appId) return () => {};

  const record = appRecord(appId);
  record.uses += 1;

  if (!record.started) {
    record.started = true;
    installExportContext(notebookCode);
    ensureLinks(assets.links);
    Promise.all(assets.moduleScripts.map(ensureModule)).then(
      () => {
        record.ready = true;
        record.resolve();
      },
      (error) => {
        record.reject(error);
        appRecords.delete(appId);
      },
    );
  }

  return () => releaseApp(appId);
}

function releaseApp(appId) {
  const record = appRecords.get(appId);
  if (!record) return;

  record.uses -= 1;
  if (record.uses > 0) return;

  appRecords.delete(appId);
}

// Mirror book theme and custom styles across marimo's nested shadow roots.
function ensureThemeStyle() {
  if (document.getElementById(themeStyleId)) return;

  const style = document.createElement("style");
  style.id = themeStyleId;
  style.textContent = globalThemeCss;
  document.head.appendChild(style);
}

function shouldUseDocumentNavigation(event, anchor) {
  if (event.defaultPrevented || event.button !== 0) return false;
  if (event.metaKey || event.altKey || event.ctrlKey || event.shiftKey) {
    return false;
  }
  if (anchor.target && anchor.target !== "_self") return false;
  if (anchor.hasAttribute("download")) return false;

  const url = new URL(anchor.href, document.baseURI);
  if (url.origin !== window.location.origin) return false;
  return url.pathname !== window.location.pathname ||
    url.search !== window.location.search;
}

function ensureDocumentNavigation() {
  if (documentNavigationStarted) return;
  documentNavigationStarted = true;

  // The marimo islands runtime is initialized per document. Jupyter Book's
  // client-side page swaps can otherwise keep a stale runtime bridge alive.
  document.addEventListener(
    "click",
    (event) => {
      const anchor = event.target?.closest?.("a[href]");
      if (!(anchor instanceof HTMLAnchorElement)) return;
      if (!shouldUseDocumentNavigation(event, anchor)) return;

      event.preventDefault();
      window.location.assign(anchor.href);
    },
    true,
  );
}

function themeFromToken(value) {
  if (typeof value !== "string") return "";
  const normalized = value.toLowerCase();
  for (const token of normalized.split(/[\s,]+/)) {
    if (token === "light" || token === "dark") return token;
  }
  const hasDark = normalized.includes("dark");
  const hasLight = normalized.includes("light");
  if (hasDark && !hasLight) return "dark";
  if (hasLight && !hasDark) return "light";
  return "";
}

function explicitThemeFromElement(element) {
  if (!(element instanceof HTMLElement)) return "";
  const attributes = [
    element.dataset.theme,
    element.dataset.mode,
    element.dataset.colorMode,
    element.dataset.bsTheme,
    element.getAttribute("theme"),
  ];
  for (const value of attributes) {
    const theme = themeFromToken(value);
    if (theme) return theme;
  }
  if (element.classList.contains("dark")) return "dark";
  if (element.classList.contains("light")) return "light";
  return "";
}

function luminanceFromColor(value) {
  const match = value.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
  if (!match) return null;
  const [, red, green, blue] = match.map(Number);
  return (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255;
}

function colorSchemeFromDocument() {
  /*
   * Book themes expose dark/light state inconsistently, so prefer explicit
   * tokens and fall back to computed color before consulting OS preference.
   */
  for (const element of [document.documentElement, document.body]) {
    const explicit = explicitThemeFromElement(element);
    if (explicit) return explicit;
  }

  const colorScheme = getComputedStyle(document.documentElement).colorScheme;
  const explicitScheme = themeFromToken(colorScheme);
  if (explicitScheme) return explicitScheme;

  const background = getComputedStyle(document.body).backgroundColor ||
    getComputedStyle(document.documentElement).backgroundColor;
  const luminance = luminanceFromColor(background);
  if (luminance != null) return luminance < 0.5 ? "dark" : "light";

  return window.matchMedia?.("(prefers-color-scheme: dark)")?.matches
    ? "dark"
    : "light";
}

function syncHostTheme(host) {
  const theme = colorSchemeFromDocument();
  host.dataset.jbTheme = theme;
  host.dataset.jbColorScheme = theme;
}

function ensureThemeObserver() {
  if (themeObserverStarted) return;
  themeObserverStarted = true;
  const observer = new MutationObserver(() => refreshThemedRoots());
  const options = {
    attributes: true,
    attributeFilter: [
      "class",
      "data-theme",
      "data-mode",
      "data-color-mode",
      "data-bs-theme",
      "style",
      "theme",
    ],
  };
  observer.observe(document.documentElement, options);
  if (document.body) observer.observe(document.body, options);
}

function refreshThemedRoots() {
  for (const [root, customStyles] of Array.from(themedRoots.entries())) {
    if (!root.isConnected) {
      themedRoots.delete(root);
      continue;
    }
    installShadowTheme(
      root,
      customStyles.stylesheets,
      customStyles.styleBlocks,
      root,
    );
  }
}

function rememberShadowStyles(shadow, stylesheets, styleBlocks) {
  // A shadow root can be discovered by multiple mounts; merge style state.
  const existing = observedShadowRootStyles.get(shadow) ?? {
    stylesheets: [],
    styleBlocks: [],
  };
  observedShadowRootStyles.set(
    shadow,
    {
      stylesheets: normalizedStylesheetHrefs([
        ...existing.stylesheets,
        ...stylesheets,
      ]),
      styleBlocks: normalizedStyleBlocks([
        ...existing.styleBlocks,
        ...styleBlocks,
      ]),
    },
  );
}

function observeShadowRoot(shadow, stylesheets, styleBlocks, owner) {
  rememberShadowStyles(shadow, stylesheets, styleBlocks);
  let record = observedShadowRoots.get(shadow);
  if (!record) {
    // marimo components can attach deeper shadow roots after the first pass.
    const observer = new MutationObserver(() => {
      const customStyles = observedShadowRootStyles.get(shadow) ?? {
        stylesheets: [],
        styleBlocks: [],
      };
      installShadowTheme(
        shadow,
        customStyles.stylesheets,
        customStyles.styleBlocks,
        owner,
      );
    });
    observer.observe(shadow, { childList: true, subtree: true });
    record = { observer, owners: new Set() };
    observedShadowRoots.set(shadow, record);
  }
  if (owner) {
    record.owners.add(owner);
    const shadows = shadowRootsByMount.get(owner) ?? new Set();
    shadows.add(shadow);
    shadowRootsByMount.set(owner, shadows);
  }
}

function releaseShadowObservers(owner) {
  const shadows = shadowRootsByMount.get(owner);
  if (!shadows) return;

  for (const shadow of shadows) {
    const record = observedShadowRoots.get(shadow);
    if (!record) continue;
    record.owners.delete(owner);
    if (record.owners.size === 0) {
      record.observer.disconnect();
      observedShadowRoots.delete(shadow);
      observedShadowRootStyles.delete(shadow);
    }
  }
  shadowRootsByMount.delete(owner);
}

function installShadowTheme(root, stylesheets = [], styleBlocks = [], owner = null) {
  ensureThemeObserver();
  if (root instanceof HTMLElement) syncHostTheme(root);
  for (const node of root.querySelectorAll("*")) {
    const shadow = node.shadowRoot;
    if (!shadow) continue;

    syncHostTheme(node);
    observeShadowRoot(shadow, stylesheets, styleBlocks, owner);

    if (!shadow.getElementById(shadowThemeStyleId)) {
      const style = document.createElement("style");
      style.id = shadowThemeStyleId;
      style.textContent = shadowThemeCss;
      shadow.appendChild(style);
    }
    ensureCustomStyleBlocks(shadow, styleBlocks);
    ensureCustomStylesheets(shadow, stylesheets);

    installShadowTheme(shadow, stylesheets, styleBlocks, owner);
  }
}

function scheduleShadowTheme(mount, stylesheets = [], styleBlocks = []) {
  /*
   * marimo UI creates shadow roots asynchronously. The timed passes catch roots
   * attached after React/custom-element hydration, and the observer handles
   * later nested UI changes.
   */
  ensureThemeObserver();
  const normalized = normalizedStylesheetHrefs(stylesheets);
  const blocks = normalizedStyleBlocks(styleBlocks);
  themedRoots.set(mount, { stylesheets: normalized, styleBlocks: blocks });
  installShadowTheme(mount, normalized, blocks, mount);
  requestAnimationFrame(() => installShadowTheme(mount, normalized, blocks, mount));
  for (const delay of [100, 500, 2000, 5000]) {
    setTimeout(() => installShadowTheme(mount, normalized, blocks, mount), delay);
  }
  const observer = new MutationObserver(() =>
    installShadowTheme(mount, normalized, blocks, mount),
  );
  observer.observe(mount, { childList: true, subtree: true });
  return () => {
    observer.disconnect();
    releaseShadowObservers(mount);
    themedRoots.delete(mount);
  };
}

function stripHeadOnlyNodes(fragment) {
  fragment
    .querySelectorAll("script, link, marimo-code, marimo-filename")
    .forEach((node) => node.remove());
}

function suppressMimeRenderers(root, mimetypes) {
  // Used after `error: false`: keep successful output, remove error renderers.
  if (mimetypes.length === 0) return;

  root.querySelectorAll("marimo-mime-renderer").forEach((node) => {
    const mime = (node.getAttribute("data-mime") ?? "").trim().replace(/^["']|["']$/g, "");
    if (mimetypes.includes(mime)) {
      node.remove();
    }
  });
}

function observeSuppressedMimeRenderers(root, mimetypes) {
  suppressMimeRenderers(root, mimetypes);
  if (mimetypes.length === 0) return () => {};

  const observer = new MutationObserver(() => {
    suppressMimeRenderers(root, mimetypes);
  });
  observer.observe(root, { childList: true, subtree: true });
  return () => observer.disconnect();
}

function containsMarimoUiElement(node) {
  return ["data-data", "data-json-data"]
    .map((name) => node.getAttribute(name) ?? "")
    .some((value) => value.includes("marimo-ui-element"));
}

function isDisplayCodeEditor(node) {
  return node.matches("marimo-ui-element") &&
    node.querySelector("marimo-code-editor");
}

function shouldDeferServerRuntimeElement(node) {
  /*
   * Server-rendered interactive elements are stale placeholders until browser
   * marimo recreates them. Display-code editors are static source views, so
   * leave those in place.
   */
  if (isDisplayCodeEditor(node)) {
    return false;
  }
  if (node.matches("marimo-anywidget, marimo-ui-element, marimo-table")) {
    return true;
  }
  if (node.matches("marimo-mime-renderer, marimo-json-output")) {
    return containsMarimoUiElement(node);
  }
  return false;
}

function hasDeferredRuntimeAncestor(node) {
  return Boolean(
    node.parentElement?.closest(
      `${runtimeElementSelector}, ${nestedRuntimeContainerSelector}`,
    ),
  );
}

function canUsePendingPreview(node) {
  if (node.matches(`${runtimeElementSelector}, ${nestedRuntimeContainerSelector}`)) {
    return false;
  }
  return !node.querySelector(runtimeElementSelector);
}

function replaceWithPendingPreview(node) {
  /*
   * Preserve static HTML as a dimmed preview only when it does not itself contain
   * live marimo runtime elements that the browser will recreate.
   */
  const wrapper = document.createElement("div");
  wrapper.className = pendingClass;
  wrapper.setAttribute("aria-busy", "true");
  wrapper.setAttribute("aria-disabled", "true");
  wrapper.inert = true;

  if (canUsePendingPreview(node)) {
    const preview = document.createElement("div");
    preview.className = previewClass;

    wrapper.append(preview, loadingNode());
    node.replaceWith(wrapper);
    preview.append(node);
  } else {
    wrapper.append(loadingNode());
    node.replaceWith(wrapper);
  }
  return wrapper;
}

function deferServerRuntimeElements(fragment) {
  fragment
    .querySelectorAll(runtimeElementSelector)
    .forEach((node) => {
      if (hasDeferredRuntimeAncestor(node)) return;
      if (!shouldDeferServerRuntimeElement(node)) return;
      replaceWithPendingPreview(node);
    });
}

function deferNestedServerRuntimeElements(fragment) {
  fragment
    .querySelectorAll(nestedRuntimeContainerSelector)
    .forEach((node) => {
      if (hasDeferredRuntimeAncestor(node)) return;
      if (!node.innerHTML.includes("marimo-ui-element")) return;
      replaceWithPendingPreview(node);
    });
}

function hasVisiblePreview(wrapper) {
  const preview = wrapper.querySelector(`:scope > .${previewClass}`);
  if (!(preview instanceof HTMLElement)) return false;
  if (preview.textContent.trim()) return true;

  const rect = preview.getBoundingClientRect();
  return rect.width > 1 && rect.height > 1;
}

function refreshPendingPreviews(root) {
  root.querySelectorAll(`.${pendingClass}`).forEach((wrapper) => {
    if (!(wrapper instanceof HTMLElement)) return;
    if (hasVisiblePreview(wrapper)) {
      wrapper.dataset.hasPreview = "true";
    } else {
      delete wrapper.dataset.hasPreview;
    }
  });
}

function schedulePendingPreviews(root) {
  // Preview visibility can change after fonts, custom elements, or layout settle.
  refreshPendingPreviews(root);
  requestAnimationFrame(() => refreshPendingPreviews(root));
  for (const delay of [100, 500, 1500, 3000]) {
    setTimeout(() => refreshPendingPreviews(root), delay);
  }
}

function cellIdFromIsland(island) {
  try {
    return typeof island.cellId === "string" ? island.cellId : "";
  } catch {
    return island.getAttribute("data-cell-id") ?? "";
  }
}

function firstElementChild(node) {
  const child = node.firstElementChild;
  return child instanceof HTMLElement ? child : null;
}

function syncIslandCellContainers(root) {
  root.querySelectorAll("marimo-island").forEach((island) => {
    const cellId = cellIdFromIsland(island);
    const container = firstElementChild(island);
    if (!cellId || !container) return;

    /*
     * marimo plugins locate their owning cell by walking to the nearest
     * div#cell-*. Islands mount into a custom element, so expose the same
     * runtime cell id on the React output wrapper once the browser runtime has
     * resolved data-cell-idx to a concrete cell id.
     */
    if (container.tagName === "DIV") {
      container.id = `cell-${cellId}`;
    }
  });
}

function scheduleIslandCellContainers(root) {
  /*
   * The browser runtime resolves `data-cell-idx` to `cellId` asynchronously.
   * Retry and observe so plugin-facing div#cell-* wrappers appear once IDs land.
   */
  syncIslandCellContainers(root);

  const frame = requestAnimationFrame(() => syncIslandCellContainers(root));
  const timeouts = [100, 500, 1500, 3000, 5000].map((delay) =>
    setTimeout(() => syncIslandCellContainers(root), delay),
  );
  const observer = new MutationObserver(() => syncIslandCellContainers(root));
  observer.observe(root, { childList: true, subtree: true });

  return () => {
    cancelAnimationFrame(frame);
    timeouts.forEach(clearTimeout);
    observer.disconnect();
  };
}

function clearHost(host) {
  host
    .querySelectorAll(`:scope > .${outputClass}`)
    .forEach((node) => node.remove());
}

function createLightDomMount(el) {
  /*
   * anywidget gives us a shadow host, but marimo's runtime queries light DOM.
   * Slot the host's shadow contents and mount beside the host so marimo's DOM
   * walks can find notebook source, islands, and cell wrappers.
   */
  const root = el.getRootNode();
  const host = root instanceof ShadowRoot ? root.host : el;

  if (root instanceof ShadowRoot) {
    root.replaceChildren(document.createElement("slot"));
  }

  clearHost(host);

  const mount = document.createElement("div");
  mount.className = outputClass;
  host.appendChild(mount);
  return mount;
}

function loadingNode() {
  const node = document.createElement("div");
  node.className = loadingClass;
  node.setAttribute("role", "status");
  node.setAttribute("aria-label", "Loading marimo output");
  for (let index = 0; index < 3; index += 1) {
    node.appendChild(document.createElement("span"));
  }
  return node;
}

function runtimeError(error) {
  const details = document.createElement("details");
  details.className = "marimo-plugin-fallback";
  details.open = true;

  const summary = document.createElement("summary");
  summary.textContent = "Failed to load marimo output";

  const pre = document.createElement("pre");
  pre.textContent = error instanceof Error ? error.message : String(error);

  details.append(summary, pre);
  return details;
}

function readOutputModel(model) {
  const head = parseHtml(getModelValue(model, "head"));
  const body = parseHtml(getModelValue(model, "html"));
  const notebookCode = getModelString(model, "notebookCode") ||
    decodeMarimoCode(head) ||
    decodeMarimoCode(body);

  return {
    body,
    notebookCode,
    appId: getModelString(model, "appId") || appIdFrom(body, notebookCode),
    assets: assetsFromModel(model, head),
    customStylesheets: getModelStringList(model, "customStylesheets"),
    customStyleBlocks: getModelStyleBlocks(model),
    suppressMimetypes: getModelStringList(model, "suppressMimetypes"),
  };
}

function hasRuntimePayload(output) {
  return Boolean(
    output.notebookCode ||
      output.assets.moduleScripts.length > 0 ||
      output.assets.links.length > 0,
  );
}

function isOutputBodyEmpty(output) {
  return output.body.childNodes.length === 0;
}

function mountMarimo(model, el) {
  /*
   * Mount static HTML immediately, then hydrate when the shared app runtime is
   * ready. Empty outputs can still carry the runtime payload for the whole page.
   */
  const output = readOutputModel(model);
  const mount = createLightDomMount(el);

  let cancelled = false;
  let releaseCode = () => {};
  let releaseAppRecord = () => {};
  let releaseMimeObserver = () => {};
  let releaseTheme = () => {};
  let releaseCellContainers = () => {};

  stripHeadOnlyNodes(output.body);
  suppressMimeRenderers(output.body, output.suppressMimetypes);
  deferNestedServerRuntimeElements(output.body);
  deferServerRuntimeElements(output.body);
  ensureThemeStyle();
  ensureCustomStyleBlocks(document, output.customStyleBlocks);
  ensureCustomStylesheets(document, output.customStylesheets);
  ensureDocumentNavigation();

  const hasRuntime = Boolean(output.appId) || hasRuntimePayload(output);
  const hasPayload = hasRuntimePayload(output);
  const bodyIsEmpty = isOutputBodyEmpty(output);

  if (!bodyIsEmpty) {
    mount.replaceChildren(output.body);
    releaseMimeObserver = observeSuppressedMimeRenderers(
      mount,
      output.suppressMimetypes,
    );
    releaseTheme = scheduleShadowTheme(
      mount,
      output.customStylesheets,
      output.customStyleBlocks,
    );
    releaseCellContainers = scheduleIslandCellContainers(mount);
    schedulePendingPreviews(mount);
  } else if (hasRuntime) {
    mount.replaceChildren(loadingNode());
  } else {
    mount.replaceChildren();
  }

  const hydrate = async () => {
    try {
      if (hasPayload) {
        releaseCode = retainNotebookCode(output.appId, output.notebookCode);
      }

      if (output.appId && hasPayload) {
        releaseAppRecord = retainApp(
          output.appId,
          output.notebookCode,
          output.assets,
        );
      } else if (output.appId) {
        appRecord(output.appId);
      }

      if (output.appId) {
        await appRecord(output.appId).promise;
        if (!cancelled) {
          if (bodyIsEmpty) mount.replaceChildren();
          releaseTheme();
          releaseTheme = scheduleShadowTheme(
            mount,
            output.customStylesheets,
            output.customStyleBlocks,
          );
        }
      }
    } catch (error) {
      if (!cancelled) mount.replaceChildren(runtimeError(error));
    }
  };

  hydrate();

  return () => {
    cancelled = true;
    releaseCode();
    releaseAppRecord();
    releaseMimeObserver();
    releaseTheme();
    releaseCellContainers();
    mount.remove();
  };
}

const containerWidget = {
  render({ model, el }) {
    return mountMarimo(model, el);
  },
};

export default containerWidget;
