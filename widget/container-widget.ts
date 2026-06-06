import { hasRuntimePayload, isOutputBodyEmpty, readOutputModel } from "./model.ts";
import {
  appRecord,
  ensureDocumentNavigation,
  retainApp,
  retainNotebookCode,
} from "./runtime.ts";
import {
  createLightDomMount,
  deferRuntimeOwnedOutput,
  observeSuppressedMimeRenderers,
  runtimeError,
  scheduleIslandCellContainers,
  stripHeadOnlyNodes,
  suppressMimeRenderers,
} from "./output-dom.ts";
import { scheduleEditorRunControls } from "./editor-run-controls.ts";
import {
  ensureCustomStyleBlocks,
  ensureCustomStylesheets,
  ensureThemeStyle,
  scheduleShadowTheme,
} from "./theme.ts";
import {
  ensureMolabPageAction,
  firstNotebookCodeSource,
  notebookCodeFromDom,
  notebookCodeFromExportContext,
  notebookCodeFromValue,
} from "./molab-action.ts";
import type { AnyWidgetModel, Release } from "./model.ts";

type RenderContext = {
  model: unknown;
  el: HTMLElement;
};

const appIslandCount = (appId: string): number => {
  return Array.from(
    document.querySelectorAll("marimo-island[data-reactive='true']"),
  ).filter((island) => island.getAttribute("data-app-id") === appId).length;
};

const waitForAppIslands = (
  appId: string,
  expectedCount: number,
): Promise<void> => {
  if (!appId || expectedCount <= 0 || appIslandCount(appId) >= expectedCount) {
    return Promise.resolve();
  }

  return new Promise((resolve) => {
    let settled = false;
    const finish = (): void => {
      if (settled) return;
      settled = true;
      observer.disconnect();
      timeouts.forEach(clearTimeout);
      resolve();
    };
    const check = (): void => {
      if (appIslandCount(appId) >= expectedCount) finish();
    };

    const observer = new MutationObserver(check);
    observer.observe(document.body, { childList: true, subtree: true });
    const timeouts = [0, 16, 50, 100, 250, 500, 1000, 3000].map((delay) =>
      setTimeout(delay === 3000 ? finish : check, delay)
    );
  });
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
  let releaseEditorRunControls: Release = () => {};
  let releaseMolabAction: Release = () => {};

  stripHeadOnlyNodes(output.body);
  suppressMimeRenderers(output.body, output.suppressMimetypes);
  deferRuntimeOwnedOutput(output.body);
  ensureThemeStyle();
  ensureCustomStyleBlocks(document, output.customStyleBlocks);
  ensureCustomStylesheets(document, output.customStylesheets);
  ensureDocumentNavigation();

  const hasPayload = hasRuntimePayload(output);
  const bodyIsEmpty = isOutputBodyEmpty(output);
  const notebookCodeSource = firstNotebookCodeSource(
    notebookCodeFromValue(output.molabNotebookCode),
    notebookCodeFromValue(output.notebookCode),
    notebookCodeFromExportContext(),
    notebookCodeFromDom(output.appId),
  );

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
    releaseEditorRunControls = scheduleEditorRunControls(mount);
  } else {
    mount.replaceChildren();
  }

  const hydrate = async (): Promise<void> => {
    try {
      if (hasPayload) {
        if (output.widgetConfig.molab.enabled) {
          releaseMolabAction = ensureMolabPageAction({
            notebookCodeSource,
            fallbackReason: output.molabSourceFallbackReason,
            baseUrl: output.widgetConfig.molab.baseUrl,
          });
        }
        releaseCode = retainNotebookCode(output.appId, output.notebookCode);
      }

      if (output.appId && hasPayload) {
        await waitForAppIslands(output.appId, output.runtimeCellCount);
        if (cancelled) return;
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
    releaseEditorRunControls();
    releaseMolabAction();
    mount.remove();
  };
};

const containerWidget = {
  render({ model, el }: RenderContext) {
    return mountMarimo(model, el);
  },
};

export default containerWidget;
