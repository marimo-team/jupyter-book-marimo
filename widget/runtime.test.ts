/// <reference lib="deno.ns" />

import { parseHTML } from "linkedom";
import { appRecord, retainApp } from "./runtime.ts";

const assertEquals = <T>(actual: T, expected: T): void => {
  if (actual !== expected) {
    throw new Error(
      `expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`,
    );
  }
};

type LinkedomWindow = Window & typeof globalThis & {
  __MARIMO_EXPORT_CONTEXT__?: { notebookCode: string; trusted: boolean };
  __MARIMO_MOUNT_CONFIG__?: { version: string };
};

const installDomGlobals = (window: LinkedomWindow): void => {
  delete (globalThis as LinkedomWindow).__MARIMO_MOUNT_CONFIG__;
  delete window.__MARIMO_MOUNT_CONFIG__;
  Object.assign(globalThis, {
    document: window.document,
    HTMLLinkElement: window.HTMLLinkElement,
    window,
  });
};

Deno.test("retainApp publishes the latest export context across app remounts", () => {
  const { window } = parseHTML("<html><head></head><body></body></html>");
  installDomGlobals(window as LinkedomWindow);

  const releaseFirst = retainApp("first", "x = 1", {
    links: [],
    moduleScripts: [],
  });
  assertEquals(
    (window as LinkedomWindow).__MARIMO_EXPORT_CONTEXT__?.notebookCode,
    "x = 1",
  );
  releaseFirst();

  const releaseSecond = retainApp("second", "y = 2", {
    links: [],
    moduleScripts: [],
  });
  assertEquals(
    (window as LinkedomWindow).__MARIMO_EXPORT_CONTEXT__?.notebookCode,
    "y = 2",
  );
  releaseSecond();
});

Deno.test("retainApp installs marimo version before loading island assets", async () => {
  const { window } = parseHTML("<html><head></head><body></body></html>");
  installDomGlobals(window as LinkedomWindow);
  const observedConfig = "data:text/javascript," +
    encodeURIComponent(`
      if (globalThis.window.__MARIMO_MOUNT_CONFIG__?.version !== "0.23.8") {
        throw new Error("mount config missing before asset import");
      }
    `);

  const release = retainApp("first", "x = 1", {
    links: [],
    moduleScripts: [observedConfig],
    version: "0.23.8",
  });

  assertEquals(
    (window as LinkedomWindow).__MARIMO_MOUNT_CONFIG__?.version,
    "0.23.8",
  );
  await appRecord("first").promise;
  release();
});

Deno.test("retainApp derives marimo version from legacy island asset URLs", async () => {
  const { window } = parseHTML("<html><head></head><body></body></html>");
  installDomGlobals(window as LinkedomWindow);
  const moduleHref =
    "data:text/javascript;path=/@marimo-team/islands@0.24.0/dist/main.js,export%20{}";

  const release = retainApp("first", "x = 1", {
    links: [],
    moduleScripts: [moduleHref],
  });

  assertEquals(
    (window as LinkedomWindow).__MARIMO_MOUNT_CONFIG__?.version,
    "0.24.0",
  );
  await appRecord("first").promise;
  release();
});
