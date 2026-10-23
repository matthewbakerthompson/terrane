// Any drawing to a PNG, through the app's own export, for judging a layout
// or style change by looking at it:
//
//   node 80_APP/tools/dev/shots.mjs network=view=network-topology \
//        card=view=product-architecture&p_product=PRD-CARD-SERVICING
//
// Each argument is name=hash; the PNG lands in 80_APP/tools/dev/out/<name>.png
// (not committed) and a line says its size and the zoom the app chose. The
// app must be listening (python 80_APP/app/server.py); --url changes where.
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { drawingPng, launch, openView } from "../capture.mjs";

const OUT = resolve(dirname(fileURLToPath(import.meta.url)), "out");
let url = "http://127.0.0.1:8020";
const shots = [];
for (let i = 2; i < process.argv.length; i += 1) {
  if (process.argv[i] === "--url") { url = process.argv[++i]; continue; }
  const arg = process.argv[i];
  const at = arg.indexOf("=");
  shots.push([arg.slice(0, at), arg.slice(at + 1)]);
}
if (!shots.length) {
  console.error("usage: node shots.mjs [--url URL] name=hash ...");
  process.exit(2);
}
await mkdir(OUT, { recursive: true });
const browser = await launch();
try {
  for (const [name, hash] of shots) {
    const page = await openView(browser, url, hash);
    page.on("pageerror", (e) => console.log(name, "pageerror:", e.message));
    await writeFile(resolve(OUT, name + ".png"), await drawingPng(page));
    const facts = await page.evaluate(() => {
      const cy = document.getElementById("cy")._cyreg.cy;
      const bb = cy.elements().boundingBox({ includeLabels: false });
      return { w: Math.round(bb.w), h: Math.round(bb.h), zoom: (document.getElementById("zoomPct") || {}).textContent || "" };
    });
    console.log(name.padEnd(24), JSON.stringify(facts), "->", resolve(OUT, name + ".png"));
    await page.close();
  }
} finally {
  await browser.close();
}
