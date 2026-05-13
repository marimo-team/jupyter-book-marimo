import { hasRuntimePayload, isOutputBodyEmpty, readOutputModel } from "./model.ts";
import {
  appRecord,
  ensureDocumentNavigation,
  retainApp,
  retainNotebookCode,
} from "./runtime.ts";
import {
  createLightDomMount,
  deferNestedServerRuntimeElements,
  deferServerRuntimeElements,
  loadingNode,
  observeSuppressedMimeRenderers,
  runtimeError,
  scheduleIslandCellContainers,
  schedulePendingPreviews,
  stripHeadOnlyNodes,
  suppressMimeRenderers,
} from "./output-dom.ts";
import {
  ensureCustomStyleBlocks,
  ensureCustomStylesheets,
  ensureThemeStyle,
  scheduleShadowTheme,
} from "./theme.ts";
import type { AnyWidgetModel, Release } from "./model.ts";

type RenderContext = {
  model: unknown;
  el: HTMLElement;
};

const mountMarimo = (
  model: AnyWidgetModel | unknown,
  el: HTMLElement,
): Release => {
  /*
   * Mount static HTML immediately, then hydrate when the shared app runtime is
   * ready. Empty outputs can still carry the runtime payload for the whole page.
   */
  const output = readOutputModel(model);
  const mount = createLightDomMount(el);

  let cancelled = false;
  let releaseCode: Release = () => {};
  let releaseAppRecord: Release = () => {};
  let releaseMimeObserver: Release = () => {};
  let releaseTheme: Release = () => {};
  let releaseCellContainers: Release = () => {};

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

  const hydrate = async (): Promise<void> => {
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
};

const containerWidget = {
  render({ model, el }: RenderContext) {
    return mountMarimo(model, el);
  },
};

export default containerWidget;
