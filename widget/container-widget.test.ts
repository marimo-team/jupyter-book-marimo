/// <reference lib="deno.ns" />

import { parseHTML } from "linkedom";
import lzString from "lz-string";
import containerWidget from "./container-widget.ts";

const { decompressFromEncodedURIComponent } = lzString;

const assert: (condition: unknown, message?: string) => asserts condition = (
  condition: unknown,
  message = "assertion failed",
) => {
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
    MutationObserver: TestMutationObserver,
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

const molabNotebookCode = (link: HTMLAnchorElement): string | null => {
  let encodedCode = "";
  try {
    const hash = new URL(link.href).hash;
    if (!hash.startsWith("#code/")) return null;
    encodedCode = hash.replace(/^#code\//, "");
  } catch {
    return null;
  }
  return decompressFromEncodedURIComponent(encodedCode);
};

const molabAction = (target: ParentNode): HTMLAnchorElement | null => {
  const badges = target.querySelector(".myst-fm-block-badges");
  if (!badges) return null;
  return Array.from(badges.querySelectorAll<HTMLAnchorElement>("a")).find(
    (link) => molabNotebookCode(link) !== null,
  ) ?? null;
};

const ownedMolabActions = (target: ParentNode): HTMLAnchorElement[] => {
  const badges = target.querySelector(".myst-fm-block-badges");
  if (!badges) return [];
  return Array.from(
    badges.querySelectorAll<HTMLAnchorElement>(
      'a[data-jupyter-book-marimo-molab-action="true"]',
    ),
  );
};

const assertNamedActionLink = (link: HTMLAnchorElement): void => {
  const accessibleName = link.ariaLabel?.trim() || link.title.trim();
  assert(accessibleName);
  assertEquals(link.target, "_blank");
  assert(link.rel.split(/\s+/).includes("noopener"));
};

Deno.test("container widget owns output, runtime source, and Molab action for one render", () => {
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

  const molab = molabAction(document);
  assert(molab, "expected Molab action link");
  assertEquals(molabNotebookCode(molab), "x = 1");
  assertNamedActionLink(molab);

  release();
  assertEquals(host.querySelector("marimo-island"), null);
  assertEquals(host.textContent?.trim() ?? "", "");
  assertEquals(document.querySelector("marimo-code[data-app-id='jb-test']"), null);
  assertEquals(molabAction(document), null);
  assertEquals(ownedMolabActions(document).length, 0);
});

Deno.test("container widget falls back to exported notebook code for Molab action", () => {
  const document = testDocument();
  const host = document.getElementById("host") as HTMLElement | null;
  if (!host) throw new Error("expected host element");

  const notebookCode = "import marimo as mo\n\napp = mo.App()\n";
  const release = containerWidget.render({
    el: host,
    model: {
      appId: "jb-fallback",
      assets: { links: [], moduleScripts: [] },
      html:
        '<marimo-island data-app-id="jb-fallback" data-cell-idx="0" data-reactive="true"><div>Static output</div></marimo-island>',
      molabNotebookCode: "",
      notebookCode,
      widgetConfig: { molab: { enabled: true } },
    },
  });

  const molab = molabAction(document);
  assert(molab, "expected Molab action link");
  assertEquals(molabNotebookCode(molab), notebookCode);
  assertNamedActionLink(molab);

  release();
});

Deno.test("container widget defers runtime-owned marimo output while preserving static output", () => {
  const document = testDocument();
  const host = document.getElementById("host") as HTMLElement | null;
  if (!host) throw new Error("expected host element");

  const release = containerWidget.render({
    el: host,
    model: {
      appId: "jb-static",
      assets: { links: [], moduleScripts: [] },
      html:
        '<marimo-island data-app-id="jb-static" data-cell-idx="0" data-reactive="true">' +
        "<marimo-cell-output>" +
        "<p>Static text</p>" +
        '<marimo-mime-renderer data-mime="&quot;text/plain&quot;">Renderer</marimo-mime-renderer>' +
        "<marimo-ui-element>Inline</marimo-ui-element>" +
        "</marimo-cell-output>" +
        "</marimo-island>",
      notebookCode: "import marimo as mo\n\napp = mo.App()\n",
    },
  });

  const text = host.textContent ?? "";
  assert(text.includes("Static text"));
  assert(text.includes("Renderer"));
  assert(!text.includes("Inline"));

  release();
});

Deno.test("container widget leaves empty runtime outputs blank", () => {
  const document = testDocument();
  const host = document.getElementById("host") as HTMLElement | null;
  if (!host) throw new Error("expected host element");

  const release = containerWidget.render({
    el: host,
    model: {
      appId: "jb-empty",
      assets: { links: [], moduleScripts: [] },
      html: "",
      notebookCode: "import marimo as mo\n\napp = mo.App()\n",
    },
  });

  assertEquals(host.textContent?.trim() ?? "", "");

  release();
});
