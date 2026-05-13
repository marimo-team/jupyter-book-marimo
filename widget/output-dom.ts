import {
  loadingClass,
  nestedRuntimeContainerSelector,
  outputClass,
  pendingClass,
  pendingStatusClass,
  previewClass,
  runtimeElementSelector,
} from "./styles.ts";
import type { Release } from "./model.ts";

const firstElementChild = (node: Element): HTMLElement | null => {
  const child = node.firstElementChild;
  return child instanceof HTMLElement ? child : null;
};

export const stripHeadOnlyNodes = (fragment: ParentNode): void => {
  fragment
    .querySelectorAll("script, link, marimo-code, marimo-filename")
    .forEach((node) => node.remove());
};

export const suppressMimeRenderers = (
  root: ParentNode,
  mimetypes: string[],
): void => {
  // Used after `error: false`: keep successful output, remove error renderers.
  if (mimetypes.length === 0) return;

  root.querySelectorAll("marimo-mime-renderer").forEach((node) => {
    const mime = (node.getAttribute("data-mime") ?? "").trim().replace(
      /^["']|["']$/g,
      "",
    );
    if (mimetypes.includes(mime)) {
      node.remove();
    }
  });
};

export const observeSuppressedMimeRenderers = (
  root: ParentNode,
  mimetypes: string[],
): Release => {
  suppressMimeRenderers(root, mimetypes);
  if (mimetypes.length === 0) return () => {};

  const observer = new MutationObserver(() => {
    suppressMimeRenderers(root, mimetypes);
  });
  observer.observe(root, { childList: true, subtree: true });
  return () => observer.disconnect();
};

const containsMarimoUiElement = (node: Element): boolean => {
  return ["data-data", "data-json-data"]
    .map((name) => node.getAttribute(name) ?? "")
    .some((value) => value.includes("marimo-ui-element"));
};

const displayRuntimeSelector = "marimo-table, marimo-json-output, marimo-mime-renderer";

const isDisplayCodeEditor = (node: Element): boolean => {
  return node.matches("marimo-ui-element") &&
    Boolean(node.querySelector("marimo-code-editor"));
};

const shouldDeferServerRuntimeElement = (node: Element): boolean => {
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
};

const hasDeferredRuntimeAncestor = (node: Element): boolean => {
  return Boolean(
    node.parentElement?.closest(
      `${runtimeElementSelector}, ${nestedRuntimeContainerSelector}`,
    ),
  );
};

const staticTextWithoutRuntimeElements = (node: Element): string => {
  const clone = node.cloneNode(true);
  if (!(clone instanceof Element)) return "";
  clone
    .querySelectorAll(`${runtimeElementSelector}, ${nestedRuntimeContainerSelector}`)
    .forEach((child) => child.remove());
  return clone.textContent.trim();
};

const hasDisplayRuntimeElement = (node: Element): boolean => {
  if (node.matches(displayRuntimeSelector)) return true;
  return Boolean(node.querySelector(displayRuntimeSelector));
};

const hasOnlyDisplayRuntimeElements = (node: Element): boolean => {
  const runtimeElements = Array.from(node.querySelectorAll(runtimeElementSelector));
  if (node.matches(runtimeElementSelector)) {
    runtimeElements.unshift(node);
  }
  return runtimeElements.length > 0 &&
    runtimeElements.every((element) =>
      element.matches(displayRuntimeSelector) ||
      Boolean(element.querySelector(displayRuntimeSelector))
    );
};

const canUsePendingPreview = (node: Element): boolean => {
  /*
   * Keep useful server-rendered output visible while browser hydration catches
   * up. Pure inputs and anywidgets still use the skeleton, because their stale
   * server DOM is not meaningful until marimo recreates it.
   */
  if (node.matches("marimo-anywidget")) return false;
  if (!node.matches(`${runtimeElementSelector}, ${nestedRuntimeContainerSelector}`)) {
    return !node.querySelector(runtimeElementSelector);
  }
  if (staticTextWithoutRuntimeElements(node)) return true;
  if (hasOnlyDisplayRuntimeElements(node)) return true;
  return hasDisplayRuntimeElement(node) && !node.matches("marimo-ui-element");
};

const pendingStatusNode = (): HTMLElement => {
  const node = document.createElement("div");
  node.className = pendingStatusClass;
  node.setAttribute("role", "status");
  node.textContent = "Preparing live output";
  return node;
};

const replaceWithPendingPreview = (node: Element): HTMLElement => {
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

    wrapper.append(preview, pendingStatusNode(), loadingNode());
    node.replaceWith(wrapper);
    preview.append(node);
  } else {
    wrapper.append(loadingNode());
    node.replaceWith(wrapper);
  }
  return wrapper;
};

export const deferServerRuntimeElements = (fragment: ParentNode): void => {
  fragment
    .querySelectorAll(runtimeElementSelector)
    .forEach((node) => {
      if (hasDeferredRuntimeAncestor(node)) return;
      if (!shouldDeferServerRuntimeElement(node)) return;
      replaceWithPendingPreview(node);
    });
};

export const deferNestedServerRuntimeElements = (fragment: ParentNode): void => {
  fragment
    .querySelectorAll(nestedRuntimeContainerSelector)
    .forEach((node) => {
      if (hasDeferredRuntimeAncestor(node)) return;
      if (!node.innerHTML.includes("marimo-ui-element")) return;
      replaceWithPendingPreview(node);
    });
};

const hasVisiblePreview = (wrapper: HTMLElement): boolean => {
  const preview = wrapper.querySelector(`:scope > .${previewClass}`);
  if (!(preview instanceof HTMLElement)) return false;
  if (preview.textContent.trim()) return true;

  const rect = preview.getBoundingClientRect();
  return rect.width > 1 && rect.height > 1;
};

const refreshPendingPreviews = (root: ParentNode): void => {
  root.querySelectorAll(`.${pendingClass}`).forEach((wrapper) => {
    if (!(wrapper instanceof HTMLElement)) return;
    if (hasVisiblePreview(wrapper)) {
      wrapper.dataset.hasPreview = "true";
    } else {
      delete wrapper.dataset.hasPreview;
    }
  });
};

export const schedulePendingPreviews = (root: ParentNode): void => {
  // Preview visibility can change after fonts, custom elements, or layout settle.
  refreshPendingPreviews(root);
  requestAnimationFrame(() => refreshPendingPreviews(root));
  for (const delay of [100, 500, 1500, 3000]) {
    setTimeout(() => refreshPendingPreviews(root), delay);
  }
};

const cellIdFromIsland = (island: Element): string => {
  try {
    const runtimeIsland = island as Element & { cellId?: unknown };
    return typeof runtimeIsland.cellId === "string" ? runtimeIsland.cellId : "";
  } catch {
    return island.getAttribute("data-cell-id") ?? "";
  }
};

const syncIslandCellContainers = (root: ParentNode): void => {
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
};

export const scheduleIslandCellContainers = (root: ParentNode): Release => {
  /*
   * The browser runtime resolves `data-cell-idx` to `cellId` asynchronously.
   * Retry and observe so plugin-facing div#cell-* wrappers appear once IDs land.
   */
  syncIslandCellContainers(root);

  const frame = requestAnimationFrame(() => syncIslandCellContainers(root));
  const timeouts = [100, 500, 1500, 3000, 5000].map((delay) =>
    setTimeout(() => syncIslandCellContainers(root), delay)
  );
  const observer = new MutationObserver(() => syncIslandCellContainers(root));
  observer.observe(root, { childList: true, subtree: true });

  return () => {
    cancelAnimationFrame(frame);
    timeouts.forEach(clearTimeout);
    observer.disconnect();
  };
};

const clearHost = (host: Element): void => {
  host
    .querySelectorAll(`:scope > .${outputClass}`)
    .forEach((node) => node.remove());
};

export const createLightDomMount = (el: HTMLElement): HTMLElement => {
  /*
   * anywidget gives us a shadow host, but marimo's runtime queries light DOM.
   * Slot the host's shadow contents and mount beside the host so marimo's DOM
   * walks can find notebook source, islands, and cell wrappers.
   */
  const root = el.getRootNode();
  const host = root instanceof ShadowRoot && root.host instanceof HTMLElement
    ? root.host
    : el;

  if (root instanceof ShadowRoot) {
    root.replaceChildren(document.createElement("slot"));
  }

  clearHost(host);

  const mount = document.createElement("div");
  mount.className = outputClass;
  host.appendChild(mount);
  return mount;
};

export const loadingNode = (): HTMLElement => {
  const node = document.createElement("div");
  node.className = loadingClass;
  node.setAttribute("role", "status");
  node.setAttribute("aria-label", "Loading marimo output");
  for (let index = 0; index < 3; index += 1) {
    node.appendChild(document.createElement("span"));
  }
  return node;
};

export const runtimeError = (error: unknown): HTMLDetailsElement => {
  const details = document.createElement("details");
  details.className = "marimo-plugin-fallback";
  details.open = true;

  const summary = document.createElement("summary");
  summary.textContent = "Failed to load marimo output";

  const pre = document.createElement("pre");
  pre.textContent = error instanceof Error ? error.message : String(error);

  details.append(summary, pre);
  return details;
};
