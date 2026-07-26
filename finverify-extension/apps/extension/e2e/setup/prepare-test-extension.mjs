import { cp, readFile, writeFile, rm } from "node:fs/promises";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";

const EXTENSION_ROOT = fileURLToPath(new URL("../..", import.meta.url));
const SRC_DIST = `${EXTENSION_ROOT}/dist`;
const TEST_EXTENSION_DIR = `${EXTENSION_ROOT}/e2e/.test-extension`;
const FIXTURE_ORIGIN = `http://127.0.0.1:${process.env.FV_FIXTURE_PORT ?? 8973}/*`;

async function main() {
  if (!existsSync(SRC_DIST)) {
    throw new Error(
      `${SRC_DIST} does not exist. Run "npm run build" in apps/extension first — E2E tests run against the real production build, not source.`,
    );
  }

  await rm(TEST_EXTENSION_DIR, { recursive: true, force: true });
  await cp(SRC_DIST, TEST_EXTENSION_DIR, { recursive: true });

  const manifestPath = `${TEST_EXTENSION_DIR}/manifest.json`;
  const manifest = JSON.parse(await readFile(manifestPath, "utf8"));

  // The only edit: let the real, unmodified content script also run on
  // our local fixture origin. Everything else about the extension —
  // the adapter, the engine, the UI, the background worker — is exactly
  // what ships to users.
  for (const entry of manifest.content_scripts) {
    if (!entry.matches.includes(FIXTURE_ORIGIN)) {
      entry.matches.push(FIXTURE_ORIGIN);
    }
  }

  await writeFile(manifestPath, JSON.stringify(manifest, null, 2));
  console.log(`[e2e] prepared test extension at ${TEST_EXTENSION_DIR} (added ${FIXTURE_ORIGIN} to content_scripts.matches)`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
