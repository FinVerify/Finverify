import { statSync, readFileSync } from "node:fs";
import { gzipSync } from "node:zlib";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const DIST = fileURLToPath(new URL("../../apps/extension/dist", import.meta.url));

function fmtKB(bytes) {
  return `${(bytes / 1024).toFixed(2)} KB`;
}

const targets = [
  "src/content/index.js",
  "src/content/index.css",
  "src/background/index.js",
  "src/popup/index.js",
  "src/popup/popup.css",
];

console.log("FinVerify extension — bundle size report");
console.log("(measured against apps/extension/dist — run `npm run build` first)\n");
console.log(["File", "Raw", "Gzipped"].join("\t"));

let totalRaw = 0;
let totalGz = 0;
for (const rel of targets) {
  const full = join(DIST, rel);
  let size;
  try {
    size = statSync(full).size;
  } catch {
    console.log(`${rel}\t(not found — build may not have run)`);
    continue;
  }
  const gz = gzipSync(readFileSync(full)).length;
  totalRaw += size;
  totalGz += gz;
  console.log(`${rel}\t${fmtKB(size)}\t${fmtKB(gz)}`);
}

console.log(`\nTotal (all entries)\t${fmtKB(totalRaw)}\t${fmtKB(totalGz)}`);
console.log("\nFor context: content/index.js is the one loaded on every ChatGPT page view —");
console.log("its gzipped size is the number that actually matters for page-load overhead.");
