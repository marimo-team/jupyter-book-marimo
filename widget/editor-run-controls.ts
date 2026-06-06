import type { Release } from "./model.ts";
import { editorRunControlAttribute } from "./styles.ts";

type SendRunRequest = {
  cellIds: string[];
  codes: string[];
};

type MarimoRequestClient = {
  sendRun: (request: SendRunRequest) => Promise<unknown>;
};

type MarimoRequestClientGetter = () => unknown;

type MarimoWindow = Window & typeof globalThis & {
  _marimo_private_UIElementRegistry?: {
    lookupValue?: (objectId: string) => unknown;
  };
};

const editorSelector = "marimo-code-editor";
const controlSelector = `[${editorRunControlAttribute}="true"]`;

let requestClientGetterPromise: Promise<MarimoRequestClientGetter> | null = null;

type OptionalEditor = {
  parent: HTMLElement;
  editor: HTMLElement;
};

const rootIsConnected = (root: ParentNode): boolean => {
  if (root instanceof Document) return true;
  if (root instanceof ShadowRoot) return root.host.isConnected;
  return root instanceof Node ? root.isConnected : true;
};

const cellIdFromIsland = (island: Element): string => {
  try {
    const runtimeIsland = island as Element & { cellId?: unknown };
    return typeof runtimeIsland.cellId === "string" ? runtimeIsland.cellId : "";
  } catch {
    return island.getAttribute("data-cell-id") ?? "";
  }
};

const codeFromJsonAttribute = (value: string | null): string => {
  if (!value) return "";
  try {
    const parsed = JSON.parse(value);
    return typeof parsed === "string" ? parsed : String(parsed);
  } catch {
    return value;
  }
};

const currentEditorCode = (editor: HTMLElement): string => {
  const objectId = editor.parentElement?.getAttribute("object-id");
  const registry = (window as MarimoWindow)._marimo_private_UIElementRegistry;
  if (objectId && typeof registry?.lookupValue === "function") {
    const value = registry.lookupValue(objectId);
    if (value !== undefined) return String(value);
  }

  const shadowCode = editor.shadowRoot?.querySelector(".cm-content")
    ?.textContent;
  if (shadowCode) return shadowCode;
  return codeFromJsonAttribute(editor.getAttribute("data-initial-value"));
};

const moduleUrlCandidates = (): string[] => {
  const urls = new Set<string>();
  for (const entry of performance.getEntriesByType("resource")) {
    if (entry.name.endsWith(".js")) urls.add(entry.name);
  }
  for (const node of document.querySelectorAll("script[src], link[href]")) {
    const url = node instanceof HTMLScriptElement
      ? node.src
      : node instanceof HTMLLinkElement
      ? node.href
      : "";
    if (url.endsWith(".js")) urls.add(url);
  }
  return Array.from(urls).filter((url) =>
    url.includes("@marimo-team/islands") || url.includes("/marimo/")
  );
};

const isRequestClientGetter = (
  value: unknown,
): value is MarimoRequestClientGetter => {
  if (typeof value !== "function") return false;
  const source = Function.prototype.toString.call(value);
  return source.includes(
    "getRequestClient() requires requestClientAtom to be set.",
  );
};

const discoverRequestClientGetter = async (): Promise<
  MarimoRequestClientGetter
> => {
  for (const url of moduleUrlCandidates()) {
    const moduleExports = await import(url);
    for (const value of Object.values(moduleExports)) {
      if (isRequestClientGetter(value)) return value;
    }
  }
  throw new Error("Could not find marimo request client");
};

const requestClient = async (): Promise<MarimoRequestClient> => {
  requestClientGetterPromise ??= discoverRequestClientGetter();
  const client = await requestClientGetterPromise.then((getter) => getter());
  if (
    !client || typeof client !== "object" ||
    typeof (client as Partial<MarimoRequestClient>).sendRun !== "function"
  ) {
    throw new Error("marimo request client cannot run cells");
  }
  return client as MarimoRequestClient;
};

const runEditorCell = async (
  island: Element,
  editor: HTMLElement,
  button: HTMLButtonElement,
): Promise<void> => {
  const cellId = cellIdFromIsland(island);
  if (!cellId) throw new Error("marimo editor cell id is not ready");

  button.disabled = true;
  button.dataset.state = "running";
  try {
    await (await requestClient()).sendRun({
      cellIds: [cellId],
      codes: [currentEditorCode(editor)],
    });
    button.removeAttribute("data-state");
  } catch (error) {
    button.dataset.state = "error";
    console.error("Failed to run marimo editor cell", error);
  } finally {
    button.disabled = false;
  }
};

const buttonElement = (node: Element | null): HTMLButtonElement | null => {
  if (!(node instanceof HTMLElement) || node.localName !== "button") return null;
  return node as HTMLButtonElement;
};

const directOptionalEditor = (island: Element): OptionalEditor | null => {
  for (const child of island.children) {
    if (!(child instanceof HTMLElement) || child.localName !== "marimo-ui-element") {
      continue;
    }
    const editor = Array.from(child.children).find((element) =>
      element.localName === editorSelector
    );
    if (editor instanceof HTMLElement) return { parent: child, editor };
  }
  return null;
};

const outputHost = (island: Element, editorParent: HTMLElement): Element | null => {
  return Array.from(island.children).find((child) => child !== editorParent) ?? null;
};

const isEmptyPlaceholder = (element: Element): boolean => {
  if (element.localName !== "span") return false;
  return element.children.length === 0 && (element.textContent ?? "").trim() === "";
};

const hasRenderedOutput = (element: Element | null): boolean => {
  if (!element) return false;
  if ((element.textContent ?? "").trim()) return true;

  for (const child of element.children) {
    if (child.matches(controlSelector)) continue;
    if (isEmptyPlaceholder(child)) continue;
    return true;
  }

  return false;
};

const removeRunControls = (island: Element): void => {
  for (const control of island.querySelectorAll(controlSelector)) {
    control.remove();
  }
};

const addRunControl = ({ parent }: OptionalEditor): void => {
  const existing = buttonElement(parent.querySelector(controlSelector));
  if (existing) return;

  const button = document.createElement("button");
  button.type = "button";
  button.title = "Run cell";
  button.setAttribute("aria-label", "Run cell");
  button.setAttribute(editorRunControlAttribute, "true");
  parent.append(button);
};

const syncEditorRunControls = (root: ParentNode): void => {
  for (const island of root.querySelectorAll("marimo-island")) {
    const optionalEditor = directOptionalEditor(island);
    if (
      !optionalEditor || hasRenderedOutput(outputHost(island, optionalEditor.parent))
    ) {
      removeRunControls(island);
      continue;
    }

    for (const control of island.querySelectorAll(controlSelector)) {
      if (control.parentElement !== optionalEditor.parent) control.remove();
    }
    addRunControl(optionalEditor);
  }
};

export const scheduleEditorRunControls = (root: ParentNode): Release => {
  let released = false;
  const run = (): void => {
    if (!released && rootIsConnected(root)) syncEditorRunControls(root);
  };
  const handleClick = (event: Event): void => {
    const target = event.target instanceof Element
      ? buttonElement(event.target.closest(controlSelector))
      : null;
    if (!target) return;

    const editor = target.parentElement?.querySelector(editorSelector);
    const island = target.closest("marimo-island");
    if (!(editor instanceof HTMLElement) || !island) return;

    event.preventDefault();
    event.stopPropagation();
    void runEditorCell(island, editor, target);
  };

  run();
  const frame = requestAnimationFrame(run);
  const timeouts = [100, 500, 1500, 3000, 5000].map((delay) => setTimeout(run, delay));
  const observer = new MutationObserver(run);
  observer.observe(root, { childList: true, subtree: true });
  const eventTarget = root as ParentNode & EventTarget;
  eventTarget.addEventListener("click", handleClick, true);

  return () => {
    released = true;
    cancelAnimationFrame(frame);
    timeouts.forEach(clearTimeout);
    observer.disconnect();
    eventTarget.removeEventListener("click", handleClick, true);
  };
};
