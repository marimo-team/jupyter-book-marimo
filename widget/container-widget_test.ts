/// <reference lib="deno.ns" />

import { parseHTML } from "linkedom";
import containerWidget from "./container-widget.ts";
import { createMolabUrl } from "./molab-action.ts";

const assert = (condition: unknown, message = "assertion failed"): void => {
  if (!condition) {
    throw new Error(message);
  }
};

const assertEquals = <T>(actual: T, expected: T): void => {
  if (actual !== expected) {
    throw new Error(
      `expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`,
    );
  }
};

type LinkedomWindow = Window & typeof globalThis;

class TestMutationObserver {
  observe(): void {}
  disconnect(): void {}
}

const installDomGlobals = (window: LinkedomWindow): void => {
  Object.assign(globalThis, {
    cancelAnimationFrame: (id: number) => clearTimeout(id),
    document: window.document,
    Document: window.Document,
    DocumentFragment: window.DocumentFragment,
    getComputedStyle: window.getComputedStyle ??
      (() => ({ colorScheme: "light", getPropertyValue: () => "" })),
    HTMLElement: window.HTMLElement,
    HTMLLinkElement: window.HTMLLinkElement,
    MouseEvent: window.MouseEvent ?? window.Event,
    MutationObserver: window.MutationObserver ?? TestMutationObserver,
    Node: window.Node,
    requestAnimationFrame: (callback: FrameRequestCallback) =>
      setTimeout(() => callback(performance.now()), 0),
    ShadowRoot: window.ShadowRoot,
    window,
  });
};

const testDocument = (): Document => {
  const { document, window } = parseHTML(`
    <html>
      <head></head>
      <body>
        <div class="myst-fm-block-header">
          <div class="myst-fm-block-badges"></div>
        </div>
        <main id="host"></main>
      </body>
    </html>
  `);
  installDomGlobals(window as LinkedomWindow);
  return document;
};

Deno.test("container widget mounts output, runtime source, and Molab action", () => {
  const document = testDocument();
  const host = document.getElementById("host") as HTMLElement | null;
  if (!host) throw new Error("expected host element");

  const release = containerWidget.render({
    el: host,
    model: {
      appId: "jb-test",
      assets: { links: [], moduleScripts: [] },
      html:
        '<marimo-island data-app-id="jb-test" data-cell-idx="0" data-reactive="true"><div>Static output</div></marimo-island>',
      molabNotebookCode: "x = 1",
      molabSourceFallbackReason: "empty_page_source",
      notebookCode: "import marimo as mo\n\napp = mo.App()\n",
      widgetConfig: { molab: { enabled: true } },
    },
  });

  assert(host.querySelector("marimo-island"), "expected mounted marimo island");
  const code = document.querySelector("marimo-code[data-app-id='jb-test']");
  assert(code, "expected shared notebook source node");
  assertEquals(
    decodeURIComponent(code?.textContent ?? ""),
    "import marimo as mo\n\napp = mo.App()\n",
  );

  const molab = document.querySelector<HTMLAnchorElement>(
    'a[data-jupyter-book-marimo-molab-action="true"]',
  );
  assert(molab, "expected Molab action link");
  assertEquals(molab?.href ?? "", createMolabUrl("x = 1"));
  assertEquals(
    molab?.dataset.jupyterBookMarimoMolabSource ?? "",
    "fallback:empty_page_source",
  );
  assertEquals(molab?.title ?? "", "Open in molab (cell-only fallback)");

  release();
  assertEquals(document.querySelector("marimo-code[data-app-id='jb-test']"), null);
  assertEquals(
    document.querySelector('a[data-jupyter-book-marimo-molab-action="true"]'),
    null,
  );
});
