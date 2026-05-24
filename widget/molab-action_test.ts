/// <reference lib="deno.ns" />

import { parseHTML } from "linkedom";
import {
  createMolabUrl,
  ensureMolabPageAction,
  firstNotebookCodeSource,
  notebookCodeFromValue,
} from "./molab-action.ts";

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

const installDomGlobals = (window: LinkedomWindow): void => {
  Object.assign(globalThis, {
    Document: window.Document,
    DocumentFragment: window.DocumentFragment,
    HTMLElement: window.HTMLElement,
  });
};

const testDocument = (): Document => {
  const { document, window } = parseHTML(`
    <html>
      <head></head>
      <body>
        <div class="myst-fm-block-header">
          <div class="myst-fm-block-badges">
            <a id="existing-badge"></a>
          </div>
        </div>
      </body>
    </html>
  `);
  installDomGlobals(window as LinkedomWindow);
  return document;
};

Deno.test("createMolabUrl encodes notebook code into the hash payload", () => {
  const url = new URL(createMolabUrl("x = 1\nx", "https://example.test/open"));

  assertEquals(url.origin, "https://example.test");
  assertEquals(url.pathname, "/open");
  assert(url.hash.startsWith("#code/"));
  assert(!url.href.includes("x = 1"));
});

Deno.test("firstNotebookCodeSource uses the first non-empty code source", () => {
  const source = firstNotebookCodeSource(
    notebookCodeFromValue(""),
    notebookCodeFromValue("  "),
    notebookCodeFromValue("x = 1"),
    notebookCodeFromValue("y = 2"),
  );

  assertEquals(source(), "x = 1");
});

Deno.test("ensureMolabPageAction inserts and releases a retained page action", () => {
  const document = testDocument();

  const releaseFirst = ensureMolabPageAction({
    target: document,
    notebookCodeSource: notebookCodeFromValue("x = 1"),
  });
  const firstLink = document.querySelector<HTMLAnchorElement>(
    'a[data-jupyter-book-marimo-molab-action="true"]',
  );

  assert(firstLink, "expected a Molab action link");
  assertEquals(
    firstLink?.href ?? "",
    createMolabUrl("x = 1", "https://molab.new/"),
  );
  assertEquals(firstLink?.parentElement?.className ?? "", "myst-fm-block-badges");
  assertEquals(firstLink?.parentElement?.firstElementChild, firstLink);
  assert(document.getElementById("jupyter-book-marimo-molab-action-style"));

  const releaseSecond = ensureMolabPageAction({
    target: document,
    notebookCodeSource: notebookCodeFromValue("x = 2"),
  });
  const linksAfterSecondRetain = document.querySelectorAll(
    'a[data-jupyter-book-marimo-molab-action="true"]',
  );

  assertEquals(linksAfterSecondRetain.length, 1);
  assertEquals(
    linksAfterSecondRetain[0]?.getAttribute("href") ?? "",
    createMolabUrl("x = 2", "https://molab.new/"),
  );

  releaseFirst();
  assert(
    document.querySelector('a[data-jupyter-book-marimo-molab-action="true"]'),
    "second retain should keep the page action mounted",
  );

  releaseSecond();
  assertEquals(
    document.querySelector('a[data-jupyter-book-marimo-molab-action="true"]'),
    null,
  );
});

Deno.test("ensureMolabPageAction is a no-op without notebook code or a page header", () => {
  const document = testDocument();

  ensureMolabPageAction({
    target: document,
    notebookCodeSource: notebookCodeFromValue(""),
  })();

  assertEquals(
    document.querySelector('a[data-jupyter-book-marimo-molab-action="true"]'),
    null,
  );

  const { document: documentWithoutHeader, window } = parseHTML(
    "<html><head></head><body></body></html>",
  );
  installDomGlobals(window as LinkedomWindow);
  ensureMolabPageAction({
    target: documentWithoutHeader,
    notebookCodeSource: notebookCodeFromValue("x = 1"),
  })();

  assertEquals(
    documentWithoutHeader.querySelector(
      'a[data-jupyter-book-marimo-molab-action="true"]',
    ),
    null,
  );
});
