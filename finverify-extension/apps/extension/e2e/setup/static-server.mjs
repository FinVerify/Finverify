import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL("../fixtures", import.meta.url));
const PORT = Number(process.env.FV_FIXTURE_PORT ?? 8973);

const MIME = {
  ".html": "text/html",
  ".js": "text/javascript",
  ".css": "text/css",
};

const server = createServer(async (req, res) => {
  const urlPath = (req.url ?? "/").split("?")[0];
  const safePath = normalize(urlPath === "/" ? "/chatgpt-fixture.html" : urlPath).replace(/^(\.\.[/\\])+/, "");
  const filePath = join(ROOT, safePath);

  try {
    const body = await readFile(filePath);
    res.writeHead(200, { "Content-Type": MIME[extname(filePath)] ?? "application/octet-stream" });
    res.end(body);
  } catch {
    res.writeHead(404);
    res.end("Not found");
  }
});

server.listen(PORT, () => {
  console.log(`[e2e] fixture server listening on http://127.0.0.1:${PORT}`);
});
