import { installMarimoIslandStyles } from "@marimo-team/mdx-marimo/bridge/browser";
import { mountMarimoIslandElement } from "@marimo-team/mdx-marimo/bridge/element";
import {
  isMarimoPageCellPayload,
  isMarimoPageCellReferencePayload,
  type MarimoPageSerializedCellPayload,
} from "@marimo-team/mdx-marimo/bridge/protocol";

const ELEMENT_NAME = "marimo-jupyter-book-island";
const mountHostSymbol = Symbol.for(
  "@marimo-team/jupyter-book-marimo/widget-host",
);

type AnyWidgetModel = {
  get?: (key: string) => unknown;
  [key: string]: unknown;
};

type RenderContext = {
  model: AnyWidgetModel | unknown;
  el: HTMLElement;
};

type WidgetRenderTarget = HTMLElement & {
  [mountHostSymbol]?: HTMLElement;
};

function modelValue(model: AnyWidgetModel | unknown, key: string): unknown {
  if (typeof (model as AnyWidgetModel | null)?.get === "function") {
    return (model as AnyWidgetModel).get?.(key);
  }
  return (model as Record<string, unknown> | null)?.[key];
}

function readPayload(model: AnyWidgetModel | unknown): MarimoPageSerializedCellPayload {
  const payload = modelValue(model, "payload");
  if (
    !isMarimoPageCellPayload(payload) &&
    !isMarimoPageCellReferencePayload(payload)
  ) {
    throw new TypeError("anywidget model contains an invalid marimo page payload");
  }
  return payload;
}

function widgetRoot(el: HTMLElement): {
  host: HTMLElement;
  shadow: ShadowRoot | undefined;
} {
  const renderTarget = el as WidgetRenderTarget;
  if (renderTarget[mountHostSymbol]) {
    const host = renderTarget[mountHostSymbol];
    return { host, shadow: host.shadowRoot ?? undefined };
  }
  const root = el.getRootNode();
  if ("host" in root) {
    const shadow = root as ShadowRoot;
    const host = shadow.host as HTMLElement;
    renderTarget[mountHostSymbol] = host;
    return { host, shadow };
  }
  renderTarget[mountHostSymbol] = el;
  return { host: el, shadow: el.shadowRoot ?? undefined };
}

function installWidgetStyles(
  el: HTMLElement,
  shadow: ShadowRoot | undefined,
): void {
  const link = (shadow ?? el).querySelector<HTMLLinkElement>(
    'link[rel="stylesheet"][href]',
  );
  if (link?.href) installMarimoIslandStyles(link.href, el.ownerDocument);
}

function mount({ model, el }: RenderContext): () => void {
  const payload = readPayload(model);

  const { host, shadow } = widgetRoot(el);
  installWidgetStyles(el, shadow);
  if (shadow) shadow.replaceChildren(el.ownerDocument.createElement("slot"));

  const mounted = mountMarimoIslandElement(host, payload, {
    name: ELEMENT_NAME,
    host: "jupyter-book",
    releaseDelayFrames: 2,
  });
  return mounted.release;
}

export default { render: mount };
