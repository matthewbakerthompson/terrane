// Parses every generated .mmd file with the real Mermaid parser.
//
// Optional: the engine itself has no dependencies, this check does. The Python
// test suite checks structure — balanced subgraphs, every edge endpoint
// declared, no comment marker eaten by string formatting — but it is not a
// Mermaid grammar, and only the real parser proves the output renders.
//
//   npm install mermaid jsdom
//   node 50_ENGINE/tools/mermaid_parse_check.mjs 70_ARTIFACTS/mermaid

import fs from "node:fs";
import path from "node:path";

const MISSING_DEPS =
  "This check needs mermaid and jsdom:\n\n  npm install mermaid jsdom\n";

let JSDOM;
try {
  ({ JSDOM } = await import("jsdom"));
} catch {
  console.error(MISSING_DEPS);
  process.exit(2);
}

const dir = process.argv[2];
if (!dir || !fs.existsSync(dir)) {
  console.error("Usage: node mermaid_parse_check.mjs <directory of .mmd files>");
  process.exit(2);
}

// Mermaid expects a browser. jsdom is enough for parsing, which is all we want.
// These globals must exist BEFORE mermaid is imported: it binds DOMPurify to
// whatever window it finds at import time, and with no window it binds a stub
// whose sanitize() does not exist.
const dom = new JSDOM("<!doctype html><html><body></body></html>", {
  pretendToBeVisual: true,
});
global.window = dom.window;
global.document = dom.window.document;
Object.defineProperty(global, "navigator", {
  value: dom.window.navigator,
  configurable: true,
});

let mermaid;
try {
  mermaid = (await import("mermaid")).default;
} catch {
  console.error(MISSING_DEPS);
  process.exit(2);
}

mermaid.initialize({ startOnLoad: false, securityLevel: "loose" });

let failures = 0;
// Recursive on purpose. Flows render to their own folder, and a check that
// only reads one directory silently stops covering whatever is added next.
function collect(from) {
  return fs
    .readdirSync(from, { withFileTypes: true })
    .flatMap((entry) => {
      const full = path.join(from, entry.name);
      if (entry.isDirectory()) return collect(full);
      return entry.name.endsWith(".mmd") ? [full] : [];
    });
}

const files = collect(dir).sort();

if (files.length === 0) {
  console.error(`No .mmd files in ${dir}. Run 'python -m terrane render' first.`);
  process.exit(2);
}

for (const full of files) {
  const file = path.relative(dir, full);
  const text = fs.readFileSync(full, "utf8");
  try {
    await mermaid.parse(text);
    console.log("PASS  " + file);
  } catch (err) {
    failures++;
    const detail = String(err && err.message)
      .split("\n")
      .slice(0, 4)
      .join("\n      ");
    console.log("FAIL  " + file + "\n      " + detail);
  }
}

console.log(
  failures === 0
    ? `\nAll ${files.length} diagrams parse.`
    : `\n${failures} of ${files.length} diagram(s) failed.`
);
process.exit(failures === 0 ? 0 : 1);
