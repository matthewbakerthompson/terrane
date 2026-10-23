// A page of the app as a person sees it, window and all, for judging the
// shell rather than a drawing: name=hash, or name=hash|click:id,id to press
// buttons after the page has settled (the pages a hash cannot reach).
//
//   node 80_APP/tools/dev/pages.mjs out/ http://127.0.0.1:8020 home=home checks="home|click:btnChecks"
//
// A PNG per name lands in the folder given first; a line per page says
// whether the page threw.
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { launch } from "../capture.mjs";
const OUT = process.argv[2];
const url = process.argv[3];
const shots = process.argv.slice(4).map(a => { const i = a.indexOf("="); return [a.slice(0, i), a.slice(i + 1)]; });
await mkdir(OUT, { recursive: true });
const browser = await launch();
try {
  for (const [name, spec] of shots) {
    const [hash, extra] = spec.split("|");
    const page = await browser.newPage();
    await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1 });
    const errors = [];
    page.on("pageerror", e => errors.push(e.message));
    page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
    await page.goto(url + "/#" + hash, { waitUntil: "networkidle0" });
    await new Promise(r => setTimeout(r, 1800));
    if (extra && extra.startsWith("click:")) {
      for (const id of extra.slice(6).split(",")) {
        await page.click("#" + id);
        await new Promise(r => setTimeout(r, 1200));
      }
    }
    await writeFile(resolve(OUT, name + ".png"), await page.screenshot({ type: "png" }));
    console.log(name, errors.length ? "ERRORS: " + errors.join(" | ") : "ok");
    await page.close();
  }
} finally { await browser.close(); }
