import {
  codeEditorThemeAttribute,
  customStyleAttribute,
  globalThemeCss,
  scratchpadTipAttribute,
  shadowThemeCss,
  shadowThemeStyleId,
  themeStyleId,
} from "./styles.ts";
import type { Release, ShadowStyleSet, StyleBlock } from "./model.ts";

type ObservedShadowRoot = {
  observer: MutationObserver;
  owners: Set<HTMLElement>;
};

const observedShadowRoots = new WeakMap<ShadowRoot, ObservedShadowRoot>();
const observedShadowRootStyles = new WeakMap<ShadowRoot, ShadowStyleSet>();
const shadowRootsByMount = new Map<HTMLElement, Set<ShadowRoot>>();
const themedRoots = new Map<HTMLElement, ShadowStyleSet>();

let themeObserverStarted = false;
let managedBodyTheme: {
  classes: Set<string>;
  datasetMode: boolean;
  datasetTheme: boolean;
  theme: string;
} = {
  classes: new Set(),
  datasetMode: false,
  datasetTheme: false,
  theme: "",
};

export const ensureThemeStyle = (): void => {
  if (document.getElementById(themeStyleId)) return;

  const style = document.createElement("style");
  style.id = themeStyleId;
  style.textContent = globalThemeCss;
  document.head.appendChild(style);
};

export const normalizedStylesheetHrefs = (stylesheets: string[]): string[] => {
  return Array.from(
    new Set(
      stylesheets
        .filter((stylesheet) => typeof stylesheet === "string")
        .map((stylesheet) => stylesheet.trim())
        .filter(Boolean)
        .map((stylesheet) => new URL(stylesheet, document.baseURI).href),
    ),
  );
};

const hasCustomStylesheet = (parent: ParentNode, href: string): boolean => {
  return Array.from(parent.querySelectorAll(`link[${customStyleAttribute}]`))
    .some((link) =>
      link instanceof HTMLLinkElement &&
      new URL(link.href, document.baseURI).href === href
    );
};

export const ensureCustomStylesheets = (
  root: Document | ShadowRoot,
  stylesheets: string[],
): void => {
  const parent = root instanceof ShadowRoot ? root : document.head;
  for (const href of normalizedStylesheetHrefs(stylesheets)) {
    if (hasCustomStylesheet(parent, href)) continue;

    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = href;
    link.setAttribute(customStyleAttribute, "true");
    parent.appendChild(link);
  }
};

export const normalizedStyleBlocks = (styleBlocks: StyleBlock[]): StyleBlock[] => {
  const seen = new Set<string>();
  const normalized: StyleBlock[] = [];
  for (const block of styleBlocks) {
    if (!block.id || seen.has(block.id)) continue;
    seen.add(block.id);
    normalized.push(block);
  }
  return normalized;
};

export const ensureCustomStyleBlocks = (
  root: Document | ShadowRoot,
  styleBlocks: StyleBlock[],
): void => {
  const parent = root instanceof ShadowRoot ? root : document.head;
  for (const block of normalizedStyleBlocks(styleBlocks)) {
    const existing = Array.from(
      parent.querySelectorAll(`style[${customStyleAttribute}]`),
    ).find((node) =>
      node instanceof HTMLStyleElement && node.dataset.styleId === block.id
    );
    if (existing) continue;

    const style = document.createElement("style");
    style.setAttribute(customStyleAttribute, "true");
    style.dataset.styleId = block.id;
    style.textContent = block.css;
    parent.appendChild(style);
  }
};

const themeFromToken = (value: unknown): string => {
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
};

const explicitThemeFromElement = (element: Element): string => {
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
};

const luminanceFromColor = (value: string): number | null => {
  const match = value.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
  if (!match) return null;
  const [, red, green, blue] = match.map(Number);
  return (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255;
};

const colorSchemeFromDocument = (): string => {
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

  return globalThis.matchMedia?.("(prefers-color-scheme: dark)")?.matches
    ? "dark"
    : "light";
};

const bodyThemeClasses = (theme: string): string[] => [theme, `${theme}-theme`];

const syncDocumentMarimoTheme = (theme: string): void => {
  const body = document.body;
  if (!(body instanceof HTMLElement)) return;

  const desiredClasses = new Set(bodyThemeClasses(theme));
  const nextManagedClasses = new Set<string>();

  for (const className of managedBodyTheme.classes) {
    if (!desiredClasses.has(className) && body.classList.contains(className)) {
      body.classList.remove(className);
    }
  }

  for (const className of desiredClasses) {
    if (body.classList.contains(className)) {
      if (managedBodyTheme.classes.has(className)) {
        nextManagedClasses.add(className);
      }
      continue;
    }
    body.classList.add(className);
    nextManagedClasses.add(className);
  }

  if (managedBodyTheme.datasetTheme || !body.hasAttribute("data-theme")) {
    if (body.dataset.theme !== theme) body.dataset.theme = theme;
    managedBodyTheme.datasetTheme = true;
  }
  if (managedBodyTheme.datasetMode || !body.hasAttribute("data-mode")) {
    if (body.dataset.mode !== theme) body.dataset.mode = theme;
    managedBodyTheme.datasetMode = true;
  }

  managedBodyTheme = {
    classes: nextManagedClasses,
    datasetMode: managedBodyTheme.datasetMode,
    datasetTheme: managedBodyTheme.datasetTheme,
    theme,
  };
};

const releaseDocumentMarimoTheme = (): void => {
  const body = document.body;
  if (!(body instanceof HTMLElement)) return;

  for (const className of managedBodyTheme.classes) {
    if (body.classList.contains(className)) body.classList.remove(className);
  }
  if (
    managedBodyTheme.datasetTheme &&
    body.dataset.theme === managedBodyTheme.theme
  ) {
    delete body.dataset.theme;
  }
  if (
    managedBodyTheme.datasetMode &&
    body.dataset.mode === managedBodyTheme.theme
  ) {
    delete body.dataset.mode;
  }
  managedBodyTheme = {
    classes: new Set(),
    datasetMode: false,
    datasetTheme: false,
    theme: "",
  };
};

const syncMarimoContentsTheme = (
  root: ParentNode,
  theme: string,
): void => {
  const opposite = theme === "dark" ? "light" : "dark";
  for (
    const node of root.querySelectorAll(
      ".marimo .contents.light, .marimo .contents.dark",
    )
  ) {
    if (!(node instanceof HTMLElement)) continue;
    node.classList.remove(opposite);
    node.classList.add(theme);
  }
};

const syncCodeEditorTheme = (
  root: ParentNode,
  theme: string,
): void => {
  const editors = root instanceof HTMLElement &&
      root.localName === "marimo-code-editor"
    ? [root, ...root.querySelectorAll("marimo-code-editor")]
    : Array.from(root.querySelectorAll("marimo-code-editor"));

  for (const node of editors) {
    if (!(node instanceof HTMLElement)) continue;
    const managed = node.getAttribute(codeEditorThemeAttribute) === "true";
    if (!managed && node.hasAttribute("data-theme")) continue;

    const encodedTheme = JSON.stringify(theme);
    if (node.getAttribute("data-theme") !== encodedTheme) {
      node.setAttribute("data-theme", encodedTheme);
    }
    node.setAttribute(codeEditorThemeAttribute, "true");
  }
};

const scratchpadTipTitle = "Need a scratchpad?";

const normalizedElementText = (element: Element): string =>
  (element.textContent ?? "").replace(/\s+/g, " ").trim();

const scratchpadTipContainer = (trigger: HTMLElement): HTMLElement => {
  let target = trigger;
  while (
    target.parentElement instanceof HTMLElement &&
    normalizedElementText(target.parentElement) === scratchpadTipTitle
  ) {
    target = target.parentElement;
  }
  return target;
};

const syncScratchpadTips = (root: ParentNode): void => {
  for (const node of root.querySelectorAll("button")) {
    if (!(node instanceof HTMLElement)) continue;
    if (normalizedElementText(node) !== scratchpadTipTitle) continue;
    scratchpadTipContainer(node).setAttribute(scratchpadTipAttribute, "true");
  }
};

const syncHostTheme = (host: Element, theme: string): void => {
  if (!(host instanceof HTMLElement)) return;
  host.dataset.jbTheme = theme;
  host.dataset.jbColorScheme = theme;
};

const installShadowTheme = (
  root: Document | ShadowRoot | HTMLElement,
  stylesheets: string[] = [],
  styleBlocks: StyleBlock[] = [],
  owner: HTMLElement | null = null,
): void => {
  ensureThemeObserver();
  const theme = colorSchemeFromDocument();
  syncDocumentMarimoTheme(theme);
  if (root instanceof HTMLElement) syncHostTheme(root, theme);
  syncMarimoContentsTheme(root, theme);
  syncScratchpadTips(root);
  syncCodeEditorTheme(root, theme);
  for (const node of root.querySelectorAll("*")) {
    const shadow = node.shadowRoot;
    if (!shadow) continue;

    syncHostTheme(node, theme);
    syncMarimoContentsTheme(shadow, theme);
    syncScratchpadTips(shadow);
    syncCodeEditorTheme(shadow, theme);
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
};

const refreshThemedRoots = (): void => {
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
  if (themedRoots.size === 0) releaseDocumentMarimoTheme();
};

const ensureThemeObserver = (): void => {
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
};

const rememberShadowStyles = (
  shadow: ShadowRoot,
  stylesheets: string[],
  styleBlocks: StyleBlock[],
): void => {
  // A shadow root can be discovered by multiple mounts. Merge style state.
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
};

const observeShadowRoot = (
  shadow: ShadowRoot,
  stylesheets: string[],
  styleBlocks: StyleBlock[],
  owner: HTMLElement | null,
): void => {
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
};

const releaseShadowObservers = (owner: HTMLElement): void => {
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
};

export const scheduleShadowTheme = (
  mount: HTMLElement,
  stylesheets: string[] = [],
  styleBlocks: StyleBlock[] = [],
): Release => {
  /*
   * marimo UI creates shadow roots asynchronously. The timed passes catch roots
   * attached after React/custom-element hydration, and the observer handles
   * later nested UI changes.
   */
  ensureThemeObserver();
  const normalized = normalizedStylesheetHrefs(stylesheets);
  const blocks = normalizedStyleBlocks(styleBlocks);
  themedRoots.set(mount, { stylesheets: normalized, styleBlocks: blocks });

  let released = false;
  const installIfConnected = (): void => {
    if (released || !mount.isConnected) return;
    installShadowTheme(mount, normalized, blocks, mount);
  };

  installIfConnected();
  const frame = requestAnimationFrame(installIfConnected);
  const timeouts = [100, 500, 2000, 5000].map((delay) =>
    setTimeout(installIfConnected, delay)
  );
  const observer = new MutationObserver(installIfConnected);
  observer.observe(mount, { childList: true, subtree: true });
  return () => {
    released = true;
    cancelAnimationFrame(frame);
    timeouts.forEach(clearTimeout);
    observer.disconnect();
    releaseShadowObservers(mount);
    themedRoots.delete(mount);
    if (themedRoots.size === 0) releaseDocumentMarimoTheme();
  };
};
