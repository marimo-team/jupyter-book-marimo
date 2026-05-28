import { outputClass } from "./styles.ts";
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
  // After `error: false`, keep successful output and remove error renderers.
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

const runtimeOwnedOutputSelector = [
  "marimo-anywidget",
  "marimo-json-output",
  "marimo-mime-renderer",
  "marimo-table",
  "marimo-ui-element",
].join(",");

const runtimeOwnedContainerSelector = [
  "marimo-accordion",
  "marimo-carousel",
  "marimo-tabs",
].join(",");

const runtimeOwnedOutputPattern =
  /marimo-(anywidget|json-output|table|ui-element)|\\u003cmarimo-(anywidget|json-output|table|ui-element)/i;

const hasRuntimeOwnedAttribute = (node: Element): boolean => {
  return Array.from(node.attributes).some((attribute) =>
    runtimeOwnedOutputPattern.test(attribute.value)
  );
};

const shouldDeferRuntimeOwnedNode = (node: Element): boolean => {
  if (node.tagName === "MARIMO-MIME-RENDERER") {
    return hasRuntimeOwnedAttribute(node);
  }
  if (node.tagName !== "MARIMO-UI-ELEMENT") return true;
  return node.querySelector("marimo-code-editor") === null;
};

const shouldDeferRuntimeOwnedContainer = (node: Element): boolean => {
  if (hasRuntimeOwnedAttribute(node)) return true;
  return Array.from(node.querySelectorAll(runtimeOwnedOutputSelector)).some(
    shouldDeferRuntimeOwnedNode,
  );
};

export const deferRuntimeOwnedOutput = (root: ParentNode): void => {
  /*
   * These custom elements are recreated by the browser runtime. Keeping the
   * build-time copies leaves inert controls and stale renderers in front of the
   * hydrated island.
   */
  root.querySelectorAll(runtimeOwnedContainerSelector).forEach((node) => {
    if (shouldDeferRuntimeOwnedContainer(node)) node.remove();
  });
  root.querySelectorAll(runtimeOwnedOutputSelector).forEach((node) => {
    if (shouldDeferRuntimeOwnedNode(node)) node.remove();
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

const rootIsConnected = (root: ParentNode): boolean => {
  if (root instanceof Document) return true;
  if (root instanceof ShadowRoot) return root.host.isConnected;
  return root instanceof Node ? root.isConnected : true;
};

const scheduleConnectedDomChecks = (
  root: ParentNode,
  callback: () => void,
  delays: number[],
): Release => {
  let released = false;
  const run = (): void => {
    if (released || !rootIsConnected(root)) return;
    callback();
  };

  run();
  const frame = requestAnimationFrame(run);
  const timeouts = delays.map((delay) => setTimeout(run, delay));

  return () => {
    released = true;
    cancelAnimationFrame(frame);
    timeouts.forEach(clearTimeout);
  };
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
  const releaseSchedule = scheduleConnectedDomChecks(
    root,
    () => syncIslandCellContainers(root),
    [100, 500, 1500, 3000, 5000],
  );
  const observer = new MutationObserver(() => {
    if (rootIsConnected(root)) syncIslandCellContainers(root);
  });
  observer.observe(root, { childList: true, subtree: true });

  return () => {
    releaseSchedule();
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
