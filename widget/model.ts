export type Release = () => void;

export type AnyWidgetModel = {
  get?: (key: string) => unknown;
  [key: string]: unknown;
};

export type LinkAttributes = Record<string, string>;

export type RuntimeAssets = {
  links: LinkAttributes[];
  moduleScripts: string[];
  version?: string;
};

export type StyleBlock = {
  id: string;
  css: string;
};

export type OutputModel = {
  body: DocumentFragment;
  notebookCode: string;
  molabNotebookCode: string;
  molabSourceFallbackReason: string;
  appId: string;
  assets: RuntimeAssets;
  customStylesheets: string[];
  customStyleBlocks: StyleBlock[];
  suppressMimetypes: string[];
  runtimeCellCount: number;
  widgetConfig: WidgetConfig;
};

export type AppRecord = {
  ready: boolean;
  started: boolean;
  uses: number;
  promise: Promise<void>;
  resolve: () => void;
  reject: (error: unknown) => void;
};

export type ShadowStyleSet = {
  stylesheets: string[];
  styleBlocks: StyleBlock[];
};

export type MolabActionConfig = {
  enabled: boolean;
  baseUrl?: string;
};

export type WidgetConfig = {
  molab: MolabActionConfig;
};

type ModelGetter = {
  get: (key: string) => unknown;
};

const parseHtml = (html: unknown): DocumentFragment => {
  const template = document.createElement("template");
  template.innerHTML = typeof html === "string" ? html : "";
  return template.content;
};

const stringHash = (value: string): string => {
  let hash = 5381;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 33) ^ value.charCodeAt(index);
  }
  return (hash >>> 0).toString(36);
};

const decodeMarimoCode = (fragment: ParentNode): string => {
  const node = fragment.querySelector("marimo-code");
  const encoded = node?.textContent?.trim();
  if (!encoded) return "";
  try {
    return decodeURIComponent(encoded);
  } catch {
    return encoded;
  }
};

const appIdFrom = (
  fragment: ParentNode,
  notebookCode: string,
): string => {
  const island = fragment.querySelector("marimo-island[data-app-id]");
  if (island) return island.getAttribute("data-app-id") ?? "";
  return notebookCode ? `marimo-${stringHash(notebookCode)}` : "";
};

const hasModelGetter = (model: unknown): model is ModelGetter => {
  return typeof (model as { get?: unknown } | null)?.get === "function";
};

const getModelValue = (
  model: AnyWidgetModel | unknown,
  key: string,
  fallback: unknown = "",
): unknown => {
  if (hasModelGetter(model)) {
    const value = model.get(key);
    return value == null ? fallback : value;
  }

  const value = (model as Record<string, unknown> | null)?.[key];
  return value == null ? fallback : value;
};

const getModelString = (model: AnyWidgetModel | unknown, key: string): string => {
  const value = getModelValue(model, key);
  return typeof value === "string" ? value : "";
};

const getBoolean = (value: unknown, fallback: boolean): boolean => {
  if (typeof value === "boolean") return value;
  if (typeof value === "string") return value.toLowerCase() === "true";
  return fallback;
};

const getModelNumber = (
  model: AnyWidgetModel | unknown,
  key: string,
): number => {
  const value = getModelValue(model, key, 0);
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number.parseInt(value, 10);
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
};

const recordFrom = (value: unknown): Record<string, unknown> => {
  return value && typeof value === "object" ? value as Record<string, unknown> : {};
};

const getModelStringList = (
  model: AnyWidgetModel | unknown,
  key: string,
): string[] => {
  const value = getModelValue(model, key, []);
  if (Array.isArray(value)) {
    return value.filter((item): item is string => typeof item === "string");
  }
  return typeof value === "string" ? [value] : [];
};

const getModelStyleBlocks = (model: AnyWidgetModel | unknown): StyleBlock[] => {
  const value = getModelValue(model, "customStyleBlocks", []);
  if (!Array.isArray(value)) return [];
  return value
    .filter((item): item is StyleBlock => {
      return Boolean(
        item &&
          typeof item === "object" &&
          typeof (item as StyleBlock).id === "string" &&
          typeof (item as StyleBlock).css === "string",
      );
    })
    .map((item) => ({ id: item.id, css: item.css }));
};

const attributesFromElement = (element: Element): LinkAttributes => {
  return Object.fromEntries(
    Array.from(element.attributes, (attribute) => [
      attribute.name,
      attribute.value,
    ]),
  );
};

const linksFromFragment = (fragment: ParentNode): LinkAttributes[] => {
  return Array.from(
    fragment.querySelectorAll("link[href]"),
    attributesFromElement,
  );
};

const modulesFromFragment = (fragment: ParentNode): string[] => {
  return Array.from(
    fragment.querySelectorAll('script[type="module"][src]'),
    (script) => script.getAttribute("src"),
  ).filter((src): src is string => typeof src === "string" && src.length > 0);
};

const validLinkList = (value: unknown): value is LinkAttributes[] => {
  return Array.isArray(value) &&
    value.every((item) => item && typeof item === "object");
};

const validModuleScriptList = (value: unknown): value is string[] => {
  return Array.isArray(value) &&
    value.every((item) => typeof item === "string");
};

const assetsFromModel = (
  model: AnyWidgetModel | unknown,
  head: ParentNode,
): RuntimeAssets => {
  // Prefer structured assets from Python. Accept head HTML from earlier models.
  const assets = getModelValue(model, "assets", {});
  const record = assets && typeof assets === "object"
    ? assets as Record<string, unknown>
    : {};
  return {
    links: validLinkList(record.links) ? record.links : linksFromFragment(head),
    moduleScripts: validModuleScriptList(record.moduleScripts)
      ? record.moduleScripts
      : modulesFromFragment(head),
    version: typeof record.version === "string" ? record.version : undefined,
  };
};

const molabActionConfigFromWidgetConfig = (
  config: Record<string, unknown>,
): MolabActionConfig => {
  const molabConfig = recordFrom(config.molab);
  const baseUrl = molabConfig.baseUrl;

  return {
    enabled: getBoolean(molabConfig.enabled, false),
    ...(typeof baseUrl === "string" && baseUrl.trim() ? { baseUrl } : {}),
  };
};

const widgetConfigFromModel = (model: AnyWidgetModel | unknown): WidgetConfig => {
  const config = recordFrom(getModelValue(model, "widgetConfig", {}));
  return {
    molab: molabActionConfigFromWidgetConfig(config),
  };
};

export const readOutputModel = (model: AnyWidgetModel | unknown): OutputModel => {
  const head = parseHtml(getModelValue(model, "head"));
  const body = parseHtml(getModelValue(model, "html"));
  const notebookCode = getModelString(model, "notebookCode") ||
    decodeMarimoCode(head) ||
    decodeMarimoCode(body);

  return {
    body,
    notebookCode,
    molabNotebookCode: getModelString(model, "molabNotebookCode"),
    molabSourceFallbackReason: getModelString(
      model,
      "molabSourceFallbackReason",
    ),
    appId: getModelString(model, "appId") || appIdFrom(body, notebookCode),
    assets: assetsFromModel(model, head),
    customStylesheets: getModelStringList(model, "customStylesheets"),
    customStyleBlocks: getModelStyleBlocks(model),
    suppressMimetypes: getModelStringList(model, "suppressMimetypes"),
    runtimeCellCount: getModelNumber(model, "runtimeCellCount"),
    widgetConfig: widgetConfigFromModel(model),
  };
};

export const hasRuntimePayload = (output: OutputModel): boolean => {
  return Boolean(
    output.notebookCode ||
      output.assets.moduleScripts.length > 0 ||
      output.assets.links.length > 0,
  );
};

export const isOutputBodyEmpty = (output: OutputModel): boolean => {
  return output.body.childNodes.length === 0;
};
