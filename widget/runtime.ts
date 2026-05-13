import type { AppRecord, Release, RuntimeAssets } from "./model.ts";

type NotebookCodeRecord = {
  node: HTMLElement;
  uses: number;
};

const loadedModules = new Map<string, Promise<void>>();
const notebookCodeNodes = new Map<string, NotebookCodeRecord>();
const appRecords = new Map<string, AppRecord>();

const installExportContext = (notebookCode: string): void => {
  if (!notebookCode) return;
  Object.defineProperty(window, "__MARIMO_EXPORT_CONTEXT__", {
    value: Object.freeze({ trusted: true, notebookCode }),
    writable: false,
    configurable: true,
  });
};

const releaseNotebookCode = (appId: string): void => {
  const record = notebookCodeNodes.get(appId);
  if (!record) return;

  record.uses -= 1;
  if (record.uses > 0) return;

  record.node.remove();
  notebookCodeNodes.delete(appId);
};

export const retainNotebookCode = (
  appId: string,
  notebookCode: string,
): Release => {
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
};

const ensureLinks = (links: RuntimeAssets["links"]): void => {
  for (const attrs of links) {
    if (!attrs.href) continue;

    const href = new URL(attrs.href, document.baseURI).href;
    const rel = attrs.rel ?? "";
    const existing = Array.from(document.head.querySelectorAll("link[href]"))
      .find((link) =>
        link instanceof HTMLLinkElement &&
        link.href === href &&
        (link.getAttribute("rel") || "") === rel
      );
    if (existing) continue;

    const link = document.createElement("link");
    for (const [key, value] of Object.entries(attrs)) {
      link.setAttribute(key, value);
    }
    link.href = href;
    document.head.appendChild(link);
  }
};

const ensureModule = (src: string): Promise<void> => {
  // Dynamic import is the browser-visible equivalent of loading marimo's head.
  const href = new URL(src, document.baseURI).href;
  const existing = loadedModules.get(href);
  if (existing) return existing;

  const promise = import(href).then(
    () => undefined,
    () => {
      throw new Error(`Failed to load marimo runtime: ${href}`);
    },
  );

  loadedModules.set(href, promise);
  return promise;
};

export const appRecord = (appId: string): AppRecord => {
  /*
   * One payload-bearing island boots the marimo app. Sibling islands with the
   * same appId share this readiness promise instead of re-importing assets.
   */
  const existing = appRecords.get(appId);
  if (existing) return existing;

  let resolveReady: () => void = () => {};
  let rejectReady: (error: unknown) => void = () => {};
  const promise = new Promise<void>((resolve, reject) => {
    resolveReady = resolve;
    rejectReady = reject;
  });

  const record: AppRecord = {
    ready: false,
    started: false,
    uses: 0,
    promise,
    resolve: resolveReady,
    reject: rejectReady,
  };

  appRecords.set(appId, record);
  return record;
};

const releaseApp = (appId: string): void => {
  const record = appRecords.get(appId);
  if (!record) return;

  record.uses -= 1;
  if (record.uses > 0) return;

  appRecords.delete(appId);
};

export const retainApp = (
  appId: string,
  notebookCode: string,
  assets: RuntimeAssets,
): Release => {
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
};

let documentNavigationStarted = false;

const closestAnchor = (target: EventTarget | null): HTMLAnchorElement | null => {
  if (!(target instanceof Element)) return null;
  const anchor = target.closest("a[href]");
  return anchor instanceof HTMLAnchorElement ? anchor : null;
};

const shouldUseDocumentNavigation = (
  event: MouseEvent,
  anchor: HTMLAnchorElement,
): boolean => {
  if (event.defaultPrevented || event.button !== 0) return false;
  if (event.metaKey || event.altKey || event.ctrlKey || event.shiftKey) {
    return false;
  }
  if (anchor.target && anchor.target !== "_self") return false;
  if (anchor.hasAttribute("download")) return false;

  const url = new URL(anchor.href, document.baseURI);
  if (url.origin !== globalThis.location.origin) return false;
  return url.pathname !== globalThis.location.pathname ||
    url.search !== globalThis.location.search;
};

export const ensureDocumentNavigation = (): void => {
  if (documentNavigationStarted) return;
  documentNavigationStarted = true;

  // Jupyter Book page swaps can otherwise keep a stale marimo bridge alive.
  document.addEventListener(
    "click",
    (event) => {
      if (!(event instanceof MouseEvent)) return;
      const anchor = closestAnchor(event.target);
      if (!anchor) return;
      if (!shouldUseDocumentNavigation(event, anchor)) return;

      event.preventDefault();
      globalThis.location.assign(anchor.href);
    },
    true,
  );
};
