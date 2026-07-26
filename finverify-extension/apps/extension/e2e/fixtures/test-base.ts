import { test as base, chromium, type BrowserContext } from "@playwright/test";
import { fileURLToPath } from "node:url";

const EXTENSION_PATH = fileURLToPath(new URL("../.test-extension", import.meta.url));

export const test = base.extend<{
  context: BrowserContext;
  extensionId: string;
}>({
  // eslint-disable-next-line no-empty-pattern
  context: async ({}, use) => {
    const context = await chromium.launchPersistentContext("", {
      headless: false, // MV3 extensions are unreliable under classic headless; CI uses xvfb (see ci.yml)
      args: [
        `--disable-extensions-except=${EXTENSION_PATH}`,
        `--load-extension=${EXTENSION_PATH}`,
        "--no-sandbox", // required in most CI containers
      ],
    });
    await use(context);
    await context.close();
  },

  extensionId: async ({ context }, use) => {
    // MV3 service workers register asynchronously; wait for it rather
    // than assuming it's already there when the context opens.
    let [worker] = context.serviceWorkers();
    if (!worker) {
      worker = await context.waitForEvent("serviceworker");
    }
    const extensionId = worker.url().split("/")[2];
    await use(extensionId);
  },
});

export const expect = test.expect;
