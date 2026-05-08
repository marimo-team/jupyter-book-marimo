/**
 * anywidget container for exported marimo islands.
 *
 * MyST renders anywidgets inside a shadow root. marimo islands expect normal
 * light DOM, a hidden notebook source node, and same-origin runtime assets.
 * This adapter keeps that boundary explicit.
 *
 * The Python plugin copies this file into the generated .jupyter-book-marimo/
 * directory during a book build. That copy is the served ESM asset; this
 * packaged file is the source of truth.
 */

const outputClass = "marimo-jupyter-book-output";
const loadingClass = "marimo-jupyter-book-loading";
const themeStyleId = "marimo-jupyter-book-theme";
const shadowThemeStyleId = "marimo-jupyter-book-shadow-theme";

const loadedModules = new Map();
const notebookCodeNodes = new Map();
const appRecords = new Map();
const observedShadowRoots = new WeakSet();

let themeObserverStarted = false;
let documentNavigationStarted = false;

const globalThemeCss = `
:root {
  --jbm-code-bg: #f6f8fa;
  --jbm-code-fg: #24292f;
  --jbm-code-border: #d8dee4;
}

html.dark {
  --jbm-code-bg: #10151f;
  --jbm-code-fg: #e6edf3;
  --jbm-code-border: #303846;
}

pre,
pre code {
  background: var(--jbm-code-bg) !important;
  color: var(--jbm-code-fg) !important;
}

pre {
  border: 0 !important;
  box-shadow: none !important;
}

.myst-code {
  background: var(--jbm-code-bg) !important;
  border: 1px solid var(--jbm-code-border);
  box-shadow: none !important;
}

.myst-code:hover {
  box-shadow: none !important;
}

.myst-code-body,
.myst-code .myst-code-body,
.myst-code .myst-code-body.hljs,
.myst-code pre,
.myst-code .hljs {
  background: transparent !important;
  background-color: transparent !important;
}

.highlight,
.cell,
.code-cell {
  box-shadow: none !important;
}

html.dark code:not(pre code) {
  background: rgba(148, 163, 184, 0.16);
  color: #f0abfc;
}

.${outputClass} pre {
  background: var(--jbm-code-bg) !important;
  color: var(--jbm-code-fg) !important;
  border: 0 !important;
  box-shadow: none !important;
}

html.dark .${outputClass} :where(marimo-island, marimo-island *) {
  color: inherit !important;
}

html.dark .${outputClass} :where(a) {
  color: #93c5fd !important;
}

html.dark .${outputClass} :where(code:not(pre code)) {
  background: rgba(255, 255, 255, 0.08);
  color: #f9a8d4 !important;
}

html.dark .${outputClass} :where(hr) {
  border-color: rgba(214, 211, 209, 0.24);
}
`;

const shadowThemeCss = `
:host([data-jb-theme="dark"]) :where(
  .marimo,
  .marimo *,
  .markdown,
  .markdown *,
  .text-muted-foreground,
  h1,
  h2,
  h3,
  h4,
  h5,
  h6,
  p,
  li,
  summary,
  button,
  label
) {
  color: rgb(214, 211, 209) !important;
}

:host([data-jb-theme="dark"]) :where(a) {
  color: #93c5fd !important;
}

:host([data-jb-theme="dark"]) :where(code:not(pre code)) {
  background: rgba(255, 255, 255, 0.08);
  color: #f9a8d4 !important;
}
`;

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

function installExportContext(notebookCode) {
  if (!notebookCode) return;
  Object.defineProperty(window, "__MARIMO_EXPORT_CONTEXT__", {
    value: Object.freeze({ trusted: true, notebookCode }),
    writable: false,
    configurable: true,
  });
}

function retainNotebookCode(appId, notebookCode) {
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
  const assets = getModelValue(model, "assets", {});
  const record = assets && typeof assets === "object" ? assets : {};
  return {
    links: Array.isArray(record.links) ? record.links : linksFromFragment(head),
    moduleScripts: Array.isArray(record.moduleScripts)
      ? record.moduleScripts.filter((src) => typeof src === "string")
      : modulesFromFragment(head),
  };
}

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

function ensureModule(src) {
  const href = new URL(src, document.baseURI).href;
  if (loadedModules.has(href)) return loadedModules.get(href);

  const promise = new Promise((resolve, reject) => {
    const existing = Array.from(
      document.head.querySelectorAll('script[type="module"][src]'),
    ).find(
      (script) => script instanceof HTMLScriptElement && script.src === href,
    );

    if (
      existing instanceof HTMLScriptElement &&
      existing.dataset.loaded === "true"
    ) {
      resolve();
      return;
    }

    const script = existing instanceof HTMLScriptElement
      ? existing
      : document.createElement("script");
    script.type = "module";
    script.src = href;
    script.dataset.marimo = "true";
    script.addEventListener(
      "load",
      () => {
        script.dataset.loaded = "true";
        resolve();
      },
      { once: true },
    );
    script.addEventListener(
      "error",
      () => reject(new Error(`Failed to load marimo runtime: ${href}`)),
      { once: true },
    );

    if (!existing) document.head.appendChild(script);
  });

  loadedModules.set(href, promise);
  return promise;
}

function appRecord(appId) {
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

function syncHostTheme(host) {
  host.dataset.jbTheme = document.documentElement.classList.contains("dark")
    ? "dark"
    : "light";
}

function ensureThemeObserver() {
  if (themeObserverStarted) return;
  themeObserverStarted = true;
  new MutationObserver(() => installShadowTheme(document)).observe(
    document.documentElement,
    {
      attributes: true,
      attributeFilter: ["class"],
    },
  );
}

function observeShadowRoot(shadow) {
  if (observedShadowRoots.has(shadow)) return;
  observedShadowRoots.add(shadow);
  new MutationObserver(() => installShadowTheme(shadow)).observe(shadow, {
    childList: true,
    subtree: true,
  });
}

function installShadowTheme(root) {
  ensureThemeObserver();
  for (const node of root.querySelectorAll("*")) {
    const shadow = node.shadowRoot;
    if (!shadow) continue;

    syncHostTheme(node);
    observeShadowRoot(shadow);

    if (!shadow.getElementById(shadowThemeStyleId)) {
      const style = document.createElement("style");
      style.id = shadowThemeStyleId;
      style.textContent = shadowThemeCss;
      shadow.appendChild(style);
    }

    installShadowTheme(shadow);
  }
}

function scheduleShadowTheme(mount) {
  installShadowTheme(mount);
  requestAnimationFrame(() => installShadowTheme(mount));
  for (const delay of [100, 500, 2000, 5000]) {
    setTimeout(() => installShadowTheme(mount), delay);
  }
}

function stripHeadOnlyNodes(fragment) {
  fragment
    .querySelectorAll("script, link, marimo-code, marimo-filename")
    .forEach((node) => node.remove());
}

function deferServerRuntimeElements(fragment) {
  fragment
    .querySelectorAll("marimo-anywidget, marimo-mime-renderer, marimo-table")
    .forEach((node) => {
      const placeholder = loadingNode();
      node.replaceWith(placeholder);
    });
}

function clearHost(host) {
  host
    .querySelectorAll(`:scope > .${outputClass}`)
    .forEach((node) => node.remove());
}

function createLightDomMount(el) {
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
  node.textContent = "Loading marimo output...";
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
  };
}

function mountMarimo(model, el) {
  const output = readOutputModel(model);
  const mount = createLightDomMount(el);

  let cancelled = false;
  let releaseCode = () => {};
  let releaseAppRecord = () => {};

  stripHeadOnlyNodes(output.body);
  deferServerRuntimeElements(output.body);
  ensureThemeStyle();
  ensureDocumentNavigation();
  mount.replaceChildren(loadingNode());

  const hydrate = async () => {
    try {
      if (
        output.notebookCode ||
        output.assets.moduleScripts.length > 0 ||
        output.assets.links.length > 0
      ) {
        releaseCode = retainNotebookCode(output.appId, output.notebookCode);
      }

      if (!cancelled) {
        mount.replaceChildren(output.body);
        scheduleShadowTheme(mount);
      }

      if (
        output.notebookCode ||
        output.assets.moduleScripts.length > 0 ||
        output.assets.links.length > 0
      ) {
        releaseAppRecord = retainApp(
          output.appId,
          output.notebookCode,
          output.assets,
        );
      }

      if (output.appId) {
        await appRecord(output.appId).promise;
        if (!cancelled) scheduleShadowTheme(mount);
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
    mount.remove();
  };
}

const containerWidget = {
  render({ model, el }) {
    return mountMarimo(model, el);
  },
};

export default containerWidget;
