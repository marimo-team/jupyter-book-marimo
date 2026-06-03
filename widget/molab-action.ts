import lzString from "lz-string";
import type { Release } from "./model.ts";

const { compressToEncodedURIComponent } = lzString;

const MOLAB_BASE_URL = "https://molab.new/";
const ACTION_SELECTOR = 'a[data-jupyter-book-marimo-molab-action="true"]';
const ACTION_STYLE_ID = "jupyter-book-marimo-molab-action-style";
const BADGES_SELECTOR = "div.myst-fm-block-badges";
const molabPageActions = new WeakMap<Document, MolabPageAction>();

export const MOLAB_ICON_SVG =
  `<svg id="Layer_2" data-name="Layer 2" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 283.84 283.84">
  <g id="Layer_1-2" data-name="Layer 1">
    <path fill="currentColor" d="M268.19,213.42C180.77,355.27-46.67,255.18,11.06,93.21c2.56-7.15,9.38-20.96,14.72-26.21,2.23-2.19,6.1-3.7,8.52-5.86,1.19-1.06,8.21-9.19,7.18-10.24l-6.63,1.94,26.55-24.09-1.41-3.86c70.14-56.43,196.79-7.4,217.03,78.46,8.57,35.74,8.07,77.05-8.83,110.06ZM203.06,38.72c-6.26-5.48-14.77-9.55-22.68-12.16l22.68,12.16ZM92.94,62.53l-6.99-1.09c-52.44,28.96-43.39,99.3-14.71,142.57,23.72,39.33,72.55,36.89,113.02,35.87,96.13-21.43,78.26-139.18,15.4-188.09-35.3-26.62-89.99-29.22-127.17-5.01-6.82,12.35-8.08,10.87-18.02,17.95-16.04,17.53-24.93,41.7-26.26,65.3l2.86-13.46,4.26-1.55c3.17-21.33,17.45-50.87,39.05-57.49,1.63.04,9.8,2.6,10.26,2.23-1.93-3.76,1.76-6.21,4.74-7.74l-.31-2.77c3.19,1.58,4.8.07,7.93-.5,2.93,2.72,2.36,6.23,1.85,9.76-1.86,2.51-5.88.31-5.92,4.02ZM58.64,210.25l-10.98-20.83c-3.5-5.81-3.96-13.89-7.82-19.01,1.34,14.83,5.97,31.05,18.8,39.84ZM117.29,251.75c-10.17-1.6-18.69-8.01-28.21-11.07,6.3,4.59,20.87,13.91,28.21,11.07ZM182.03,258.39l-22.68,6.08c7.76,1,15.65-3.1,22.68-6.08Z"/>
    <path fill="currentColor" d="M203.06,38.72l-22.68-12.16c7.91,2.61,16.43,6.69,22.68,12.16Z"/>
    <path fill="currentColor" d="M117.3,116.19c2.28.53,2.42-2.7,3.63-4.39,7.73-10.78,27.34-12.07,35.93-1.7,1.38,1.67,3.61,7,4.96,7.22,1.03.21.72-.28.98-.72,5.48-14.59,26.87-17.14,38.77-9.15,19.1,15.12,8.13,53.55,10.89,75.7h-30.98v-47.31c-1.18-6.4-10.82-7.87-14.86-3.24-3.12-1.76-1.31,49.74-1.74,50.54h-30.43c-.28-1.54,1.02-50.48-1.42-49.76-4.12-6.46-15.18-3.41-15.73,4.11,0,0,0,45.65,0,45.65h-30.43v-78.01h30.43v11.07Z"/>
  </g>
</svg>`;

type MolabActionTarget = Document | DocumentFragment | HTMLElement;
type MolabPageAction = {
  href: string;
  link: HTMLAnchorElement;
  uses: number;
};
type MolabSourceStatus = "complete" | `fallback:${string}`;

type ExportContextWindow = Window & {
  __MARIMO_EXPORT_CONTEXT__?: {
    notebookCode?: string;
    trusted?: boolean;
  };
};

export type NotebookCodeSource = () => string | null | undefined;

export const notebookCodeFromValue = (
  notebookCode: string,
): NotebookCodeSource => {
  return () => notebookCode;
};

export const notebookCodeFromExportContext = (): NotebookCodeSource => {
  return () => (window as ExportContextWindow).__MARIMO_EXPORT_CONTEXT__?.notebookCode;
};

export const notebookCodeFromDom = (
  appId?: string,
  target: ParentNode = document,
): NotebookCodeSource => {
  return () => {
    const nodes = Array.from(target.querySelectorAll("marimo-code"));
    const node = appId
      ? nodes.find((candidate) => candidate.getAttribute("data-app-id") === appId)
      : nodes[0];
    const encoded = node?.textContent?.trim();
    if (!encoded) return "";
    try {
      return decodeURIComponent(encoded);
    } catch {
      return encoded;
    }
  };
};

export const firstNotebookCodeSource = (
  ...sources: NotebookCodeSource[]
): NotebookCodeSource => {
  return () => {
    for (const source of sources) {
      const notebookCode = source();
      if (notebookCode && notebookCode.trim()) return notebookCode;
    }
    return "";
  };
};

export const createMolabUrl = (
  notebookCode: string,
  baseUrl = MOLAB_BASE_URL,
): string => {
  const url = new URL(baseUrl);
  url.hash = `#code/${compressToEncodedURIComponent(notebookCode)}`;
  return url.href;
};

const ownerDocumentFor = (target: MolabActionTarget): Document => {
  return target instanceof Document ? target : target.ownerDocument;
};

const findFrontmatterHeader = (
  target: MolabActionTarget,
): HTMLElement | null => {
  return target.querySelector(".myst-fm-block-header");
};

const ensureMolabActionStyle = (doc: Document): void => {
  if (doc.getElementById(ACTION_STYLE_ID)) return;

  const style = doc.createElement("style");
  style.id = ACTION_STYLE_ID;
  style.textContent = `
.myst-fm-molab-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.125rem;
  height: 1.125rem;
  margin: 0 0.375rem 0 0;
  color: inherit;
  line-height: 1;
  vertical-align: middle;
}

.myst-fm-molab-icon {
  display: block;
  width: 1.125rem;
  height: 1.125rem;
  margin: 0;
  color: currentColor;
  opacity: 0.6;
  transition: opacity 120ms ease;
}

.myst-fm-molab-link:hover .myst-fm-molab-icon,
.myst-fm-molab-link:focus-visible .myst-fm-molab-icon {
  opacity: 1;
}

.myst-fm-molab-icon svg {
  display: block;
  width: 100%;
  height: 100%;
}
`;
  doc.head.appendChild(style);
};

const renderIcon = (link: HTMLAnchorElement, doc: Document): void => {
  let icon = link.querySelector<HTMLElement>(".myst-fm-molab-icon");
  if (!icon) {
    icon = doc.createElement("span");
    icon.className = "myst-fm-molab-icon";
    icon.setAttribute("aria-hidden", "true");
    link.replaceChildren(icon);
  }

  icon.innerHTML = MOLAB_ICON_SVG;
  const svg = icon.querySelector("svg");
  svg?.setAttribute("aria-hidden", "true");
  svg?.setAttribute("focusable", "false");
};

const insertMolabAction = (
  badges: HTMLElement,
  link: HTMLAnchorElement,
): void => {
  badges.insertBefore(link, badges.firstChild);
};

const upsertMolabAction = (
  header: HTMLElement,
  href: string,
  sourceStatus: MolabSourceStatus,
): HTMLAnchorElement => {
  const doc = header.ownerDocument;
  const link = header.querySelector<HTMLAnchorElement>(ACTION_SELECTOR) ??
    doc.createElement("a");

  link.href = href;
  link.dataset.jupyterBookMarimoMolabAction = "true";
  link.dataset.jupyterBookMarimoMolabHref = href;
  link.dataset.jupyterBookMarimoMolabSource = sourceStatus;
  link.title = sourceStatus === "complete"
    ? "Open in molab"
    : "Open in molab (cell-only fallback)";
  link.ariaLabel = link.title;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.className = "myst-fm-molab-link text-inherit hover:text-inherit";
  renderIcon(link, doc);

  const badges = header.querySelector<HTMLElement>(BADGES_SELECTOR);
  if (!badges) return link;
  if (link.parentElement !== badges || badges.firstElementChild !== link) {
    insertMolabAction(badges, link);
  }
  return link;
};

export function ensureMolabPageAction({
  notebookCodeSource,
  fallbackReason = "",
  target = document,
  baseUrl = MOLAB_BASE_URL,
}: {
  notebookCodeSource: NotebookCodeSource;
  fallbackReason?: string;
  target?: MolabActionTarget;
  baseUrl?: string;
}): Release {
  const notebookCode = notebookCodeSource();
  if (!notebookCode || !notebookCode.trim()) return () => {};

  const header = findFrontmatterHeader(target);
  if (!header) return () => {};

  const doc = ownerDocumentFor(target);
  ensureMolabActionStyle(doc);
  const href = createMolabUrl(notebookCode, baseUrl);
  const sourceStatus: MolabSourceStatus = fallbackReason
    ? `fallback:${fallbackReason}`
    : "complete";
  const existing = molabPageActions.get(doc);
  if (existing?.link.isConnected) {
    existing.uses += 1;
    if (existing.href !== href) {
      existing.link = upsertMolabAction(header, href, sourceStatus);
      existing.href = href;
    }
    return () => {
      existing.uses -= 1;
      if (existing.uses === 0 && molabPageActions.get(doc) === existing) {
        existing.link.remove();
        molabPageActions.delete(doc);
      }
    };
  }

  const link = upsertMolabAction(header, href, sourceStatus);
  const action: MolabPageAction = { href, link, uses: 1 };
  molabPageActions.set(doc, action);

  return () => {
    action.uses -= 1;
    if (action.uses === 0 && molabPageActions.get(doc) === action) {
      action.link.remove();
      molabPageActions.delete(doc);
    }
  };
}
