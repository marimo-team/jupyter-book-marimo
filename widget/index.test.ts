/// <reference lib="deno.ns" />

import { parseHTML } from "linkedom";

const assert: (condition: unknown, message?: string) => asserts condition = (
  condition: unknown,
  message = "assertion failed",
) => {
  if (!condition) throw new Error(message);
};

const assertEquals = <T>(actual: T, expected: T): void => {
  if (actual !== expected) {
    throw new Error(
      `expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`,
    );
  }
};

type LinkedomWindow = Window & typeof globalThis;

function installDom(): {
  document: Document;
  host: HTMLElement;
  renderTarget: HTMLElement;
} {
  const { document, window } = parseHTML(
    "<html><head></head><body><main id='host'></main></body></html>",
  );
  const linkedom = window as LinkedomWindow;
  linkedom.matchMedia = () =>
    ({
      addEventListener: () => {},
      matches: false,
      removeEventListener: () => {},
    }) as unknown as MediaQueryList;
  Object.assign(globalThis, {
    cancelAnimationFrame: (handle: number) => clearTimeout(handle),
    customElements: linkedom.customElements,
    document,
    getComputedStyle: () => ({ colorScheme: "light" }),
    HTMLElement: linkedom.HTMLElement,
    HTMLTemplateElement: linkedom.HTMLTemplateElement,
    MutationObserver: linkedom.MutationObserver,
    Node: linkedom.Node,
    NodeFilter: { SHOW_ELEMENT: 1 },
    requestAnimationFrame: (callback: FrameRequestCallback) =>
      setTimeout(() => callback(performance.now()), 0),
    ShadowRoot: linkedom.ShadowRoot,
    window: linkedom,
  });

  const host = document.getElementById("host");
  assert(host instanceof linkedom.HTMLElement);
  const renderTarget = prepareWidgetHost(document, host);
  return { document, host, renderTarget };
}

function prepareWidgetHost(document: Document, host: HTMLElement): HTMLElement {
  const shadow = host.attachShadow({ mode: "open" });
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = "https://example.test/assets/islands-bridge.css";
  const renderTarget = document.createElement("div");
  shadow.append(link, renderTarget);
  return renderTarget;
}

function staticPayload(html = "<p>Static output</p>") {
  return {
    protocolVersion: 2,
    app: null,
    cell: {
      index: 0,
      html,
      options: {
        language: "python",
        render: {
          source: false,
          output: true,
          include: true,
          editor: false,
          error: true,
          serverOutput: true,
        },
        execution: { enabled: true },
        marimo: { disabled: false, unparsable: false },
      },
    },
  };
}

Deno.test("widget mounts a programmatic page payload in host light DOM", async () => {
  const { default: widget } = await import("./index.ts");
  const { document, host, renderTarget } = installDom();

  const release = widget.render({
    el: renderTarget,
    model: { get: (key: string) => key === "payload" ? staticPayload() : null },
  });
  await Promise.resolve();

  const island = host.querySelector("marimo-jupyter-book-island");
  assert(island);
  assertEquals(island.textContent?.trim(), "Static output");
  assertEquals(host.shadowRoot?.firstElementChild?.tagName, "SLOT");

  const styles = document.head.querySelectorAll('link[rel="stylesheet"]');
  assertEquals(styles.length, 1);
  assertEquals(
    styles[0]?.getAttribute("href"),
    "https://example.test/assets/islands-bridge.css",
  );

  release();
  await waitForRemoval();
  assertEquals(host.querySelector("marimo-jupyter-book-island"), null);
});

Deno.test("widget rejects models outside the page protocol", async () => {
  const { default: widget } = await import("./index.ts");
  const { renderTarget } = installDom();

  let error: unknown;
  try {
    widget.render({ el: renderTarget, model: { payload: { html: "legacy" } } });
  } catch (caught) {
    error = caught;
  }
  assert(error instanceof TypeError);
});

async function waitForRemoval(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 0));
  await new Promise((resolve) => setTimeout(resolve, 0));
}
