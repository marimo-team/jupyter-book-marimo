/// <reference lib="deno.ns" />

import { parseHTML } from "linkedom";
import lzString from "lz-string";
import { ensureMolabPageAction } from "./molab-action.ts";

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
  return molabActions(target)[0] ?? null;
};

const molabActions = (target: ParentNode): HTMLAnchorElement[] => {
  const badges = target.querySelector(".myst-fm-block-badges");
  if (!badges) return [];
  return Array.from(badges.querySelectorAll<HTMLAnchorElement>("a")).filter(
    (link) => molabNotebookCode(link) !== null,
  );
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

const existingBadge = (document: Document): HTMLElement => {
  const badge = document.getElementById("existing-badge");
  if (!badge) throw new Error("expected existing badge");
  return badge;
};

const frontmatterBadges = (document: Document): HTMLElement => {
  const badges = document.querySelector<HTMLElement>(".myst-fm-block-badges");
  if (!badges) throw new Error("expected frontmatter badge container");
  return badges;
};

const assertNamedActionLink = (link: HTMLAnchorElement): void => {
  const accessibleName = link.ariaLabel?.trim() || link.title.trim();
  assert(accessibleName);
  assertEquals(link.target, "_blank");
  assert(link.rel.split(/\s+/).includes("noopener"));
};

Deno.test("ensureMolabPageAction uses the configured Molab base URL", () => {
  const document = testDocument();
  const notebookCode = "x = 1\nx";
  const release = ensureMolabPageAction({
    target: document,
    notebookCodeSource: () => notebookCode,
    baseUrl: "https://example.test/open",
  });
  const link = molabAction(document);
  assert(link, "expected a Molab action link");

  const url = new URL(link.href);
  assertEquals(url.origin, "https://example.test");
  assertEquals(url.pathname, "/open");
  assertEquals(molabNotebookCode(link), notebookCode);

  release();
});

Deno.test("ensureMolabPageAction retains one action with the latest notebook code", () => {
  const document = testDocument();
  const badges = frontmatterBadges(document);

  const releaseFirst = ensureMolabPageAction({
    target: document,
    notebookCodeSource: () => "x = 1",
  });
  const firstLink = molabAction(document);

  assert(firstLink, "expected a Molab action link");
  assertEquals(molabNotebookCode(firstLink), "x = 1");
  assertNamedActionLink(firstLink);
  assert(badges.contains(existingBadge(document)));

  const releaseSecond = ensureMolabPageAction({
    target: document,
    notebookCodeSource: () => "x = 2",
  });
  const linksAfterSecondRetain = molabActions(document);

  assertEquals(linksAfterSecondRetain.length, 1);
  assertEquals(molabNotebookCode(linksAfterSecondRetain[0]), "x = 2");

  releaseFirst();
  const retainedLink = molabAction(document);
  assert(retainedLink, "expected the second render to keep the action mounted");
  assertEquals(molabNotebookCode(retainedLink), "x = 2");

  releaseSecond();
  assertEquals(molabAction(document), null);
  assertEquals(ownedMolabActions(document).length, 0);
  assert(badges.contains(existingBadge(document)));
  assert(existingBadge(document).isConnected);
});

Deno.test("ensureMolabPageAction keeps the page header unchanged without notebook code", () => {
  const document = testDocument();
  const badges = frontmatterBadges(document);

  ensureMolabPageAction({
    target: document,
    notebookCodeSource: () => "",
  })();

  assertEquals(molabAction(document), null);
  assertEquals(ownedMolabActions(document).length, 0);
  assert(badges.contains(existingBadge(document)));
  assert(existingBadge(document).isConnected);
});

Deno.test("ensureMolabPageAction skips pages without frontmatter headers", () => {
  const { document: headerlessDocument, window } = parseHTML(
    "<html><head></head><body></body></html>",
  );
  installDomGlobals(window as LinkedomWindow);
  ensureMolabPageAction({
    target: headerlessDocument,
    notebookCodeSource: () => "x = 1",
  })();

  assertEquals(molabAction(headerlessDocument), null);
  assertEquals(ownedMolabActions(headerlessDocument).length, 0);
});
