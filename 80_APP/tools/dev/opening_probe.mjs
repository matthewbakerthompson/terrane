// What every drawing opens at, as a person sees it: the window at a laptop's
// 1440 by 900 with the sidebar as the app leaves it, each view of the estate
// opened in turn in the tone asked for, and for each a line saying the zoom it
// opened at, the zoom the whole drawing fits at, how large a box's name is on
// the screen, how much of the drawing is in view, and how far the drawing's
// middle sits from the sheet's; with a screenshot of the window as it opened.
//
//   node 80_APP/tools/dev/opening_probe.mjs out/opening http://127.0.0.1:8020 [stone|graphite] [view ...]
//
// With no views it takes every view the overview lists, each drawn for the
// subject the app picks first. A line per view lands in <out>/<tone>.jsonl
// too, so a run before a change and one after can be compared. A report and
// the timeline have no drawing and say so.
import { mkdir, writeFile, appendFile } from "node:fs/promises";
import { resolve } from "node:path";
import { launch } from "../capture.mjs";

const OUT = process.argv[2];
const url = process.argv[3] || "http://127.0.0.1:8020";
const tone = process.argv[4] || "stone";
let views = process.argv.slice(5);
await mkdir(resolve(OUT, tone), { recursive: true });
if (!views.length) {
  const res = await fetch(url + "/api/overview?tone=" + tone);
  views = (await res.json()).views.map((v) => v.viewId);
}
const log = resolve(OUT, tone + ".jsonl");
await writeFile(log, "");

const browser = await launch();
try {
  for (const v of views) {
    const page = await browser.newPage();
    await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1 });
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(url + "/#view=" + v + "&tone=" + tone, { waitUntil: "networkidle0", timeout: 60000 });
    try {
      await page.waitForFunction(() => {
        const pct = (document.getElementById("zoomPct") || {}).textContent || "";
        return /\d+%/.test(pct) || document.querySelector("#dataPanel table tbody tr, .tl-bar");
      }, { timeout: 30000 });
    } catch (e) {
      errors.push("nothing settled");
    }
    await new Promise((r) => setTimeout(r, 900));
    const facts = await page.evaluate(() => {
      const tiles = document.getElementById("tiles");
      if (tiles && !tiles.hidden && tiles.querySelector(".tile")) {
        const z = parseFloat(tiles.style.zoom || "1");
        return { kind: "tiles", zoom: Math.round(z * 100), scrolls: tiles.scrollHeight > tiles.clientHeight + 2,
          namePx: +(12 * z).toFixed(1) };
      }
      if (document.querySelector("#dataPanel table tbody tr")) return { kind: "report" };
      if (document.querySelector(".tl-bar")) return { kind: "timeline" };
      const host = document.getElementById("cy");
      const reg = host && host._cyreg;
      if (!reg || !reg.cy) return { kind: "none" };
      const cy = reg.cy;
      const bb = cy.elements().boundingBox({ includeLabels: false });
      const all = cy.elements().boundingBox({ includeLabels: true });
      const z = cy.zoom(), pan = cy.pan();
      const w = cy.width(), h = cy.height();
      // The part of the sheet the key and the controls leave clear, as
      // fitSheet measures it.
      let footH = 0;
      const foot = document.getElementById("mapSheet").querySelector(".sheet-foot");
      if (foot) for (const c of foot.children) {
        if (c.offsetHeight && getComputedStyle(c).display !== "none") footH = Math.max(footH, c.offsetHeight);
      }
      if (footH) footH += 14;
      const availW = w - 48, availH = h - 48 - footH;
      const fit = Math.min(availW / bb.w, availH / bb.h);
      // In view: the share of the drawing's box on the sheet at the opening.
      const sx1 = Math.max(0, bb.x1 * z + pan.x), sx2 = Math.min(w, bb.x2 * z + pan.x);
      const sy1 = Math.max(0, bb.y1 * z + pan.y), sy2 = Math.min(h - footH, bb.y2 * z + pan.y);
      const seen = Math.max(0, sx2 - sx1) * Math.max(0, sy2 - sy1) / (bb.w * z * bb.h * z);
      // Off-center: where the middle of everything drawn, labels and all,
      // lands against the middle of the clear sheet, at the fit, as a share
      // of the sheet.
      const cx = ((all.x1 + all.x2) / 2 - (bb.x1 + bb.x2) / 2) * fit / availW;
      const cyo = ((all.y1 + all.y2) / 2 - (bb.y1 + bb.y2) / 2) * fit / availH;
      const leaves = cy.nodes().filter((n) => !n.isParent());
      const ws = leaves.map((n) => n.width()), hs = leaves.map((n) => n.height());
      return {
        kind: "cy", w: Math.round(bb.w), h: Math.round(bb.h), ratio: +(bb.w / bb.h).toFixed(2),
        zoom: Math.round(z * 100), fit: Math.round(fit * 100), namePx: +(12 * z).toFixed(1),
        seen: Math.round(seen * 100), offX: Math.round(cx * 100), offY: Math.round(cyo * 100),
        leaves: leaves.length, groups: cy.nodes().filter((n) => n.isParent()).length,
        boxW: [Math.round(Math.min(...ws)), Math.round(Math.max(...ws))],
        boxH: [Math.round(Math.min(...hs)), Math.round(Math.max(...hs))],
        sheet: [Math.round(w), Math.round(h - footH)],
      };
    });
    facts.view = v;
    if (errors.length) facts.errors = errors;
    await writeFile(resolve(OUT, tone, v.replace(/[^a-z0-9-]/gi, "_") + ".png"), await page.screenshot({ type: "png" }));
    await appendFile(log, JSON.stringify(facts) + "\n");
    console.log(v.padEnd(30), JSON.stringify(facts));
    await page.close();
  }
} finally {
  await browser.close();
}
