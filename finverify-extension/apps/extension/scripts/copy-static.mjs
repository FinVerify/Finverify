import { copyFile, mkdir, cp } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const dist = resolve(root, "dist");

await mkdir(resolve(dist, "assets/icons"), { recursive: true });
await copyFile(resolve(root, "manifest.json"), resolve(dist, "manifest.json"));
await cp(resolve(root, "src/assets/icons"), resolve(dist, "assets/icons"), { recursive: true });

console.log("Copied manifest.json and icon assets into dist/");
