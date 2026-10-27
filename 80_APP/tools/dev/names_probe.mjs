// Do the names on maxGraph's canvas sit where Cytoscape set them? A
// canvas diagram opened twice at two pixels to the CSS pixel, as maxGraph
// draws it and as the old canvas does (`?canvas=cytoscape`), which opens
// at the same zoom on the same place; in each box, the rows and columns
// the name's ink takes up (pixels near the name's own color, so not the
// border, the lines or the technology line), and how far maxGraph's are
// from Cytoscape's. A line per box, the worst at the end; exits 1 past a
// pixel either way, or with the names leaning, in CSS pixels. NAMES_ZOOM
// sets the zoom both are read at, 2 by default.
//
//   node 80_APP/tools/dev/names_probe.mjs out/ URL [view]
//
// Reads lending-onboarding by default (arrange_probe.mjs makes it) and
// writes nothing.
import { mkdir, writeFile } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
const VIEW = process.argv[4] || "lending-onboarding";
if (!OUT || !URL) {
  console.error("usage: node names_probe.mjs OUT URL [view]");
  process.exit(2);
}
await mkdir(OUT, { recursive: true });
const pause = (ms) => new Promise((r) => setTimeout(r, ms));
const browser = await launch();
const errors = [];

async function open(engine) {
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 2 });
  page.on("pageerror", (e) => errors.push(engine + ": " + String(e)));
  await page.evaluateOnNewDocument(() => {
    localStorage.setItem("aac.rail.shut", "1");
    localStorage.setItem("aac.insp.shut", "1");
    localStorage.setItem("aac.tour", "taken");
  });
  const query = engine === "cytoscape" ? "?canvas=cytoscape" : "";
  await page.goto(URL + "/" + query + "#draw=" + encodeURIComponent(VIEW), { waitUntil: "networkidle0", timeout: 60000 });
  if (engine !== "cytoscape") await page.waitForSelector(".mg-surface svg", { timeout: 30000 });
  await settled(page);
  await pause(800);
  return page;
}

// Every box with a name, in CSS pixels on the page, and its name's color.
const boxesOf = (page) => page.evaluate(() => {
  const cy = document.getElementById("cy")._cyreg.cy;
  const at = document.getElementById("cy").getBoundingClientRect();
  return cy.nodes().filter((n) => !n.isParent() && n.data("label")).map((n) => {
    const b = n.renderedBoundingBox({ includeLabels: false });
    return { id: n.id(), x: at.left + b.x1, y: at.top + b.y1, w: b.w, h: b.h, zoom: cy.zoom(), ink: n.style("color") };
  });
});

// The ink of the name in each box: rows and columns with a pixel within a
// short distance of the name's color.
const inkOf = (page, url, list) => page.evaluate((u, boxes) => new Promise((resolve) => {
  const image = new Image();
  image.onload = () => {
    const c = document.createElement("canvas");
    c.width = image.width; c.height = image.height;
    const g = c.getContext("2d");
    g.drawImage(image, 0, 0);
    const d = g.getImageData(0, 0, c.width, c.height).data;
    const k = image.width / window.innerWidth;
    const rgb = (s) => (s.match(/\d+/g) || [0, 0, 0]).slice(0, 3).map(Number);
    resolve(boxes.map((b) => {
      const want = rgb(b.ink);
      const x1 = Math.ceil((b.x + 3) * k), x2 = Math.floor((b.x + b.w - 3) * k);
      const y1 = Math.ceil((b.y + 3) * k), y2 = Math.floor((b.y + b.h - 3) * k);
      let top = null, bottom = null, left = null, right = null;
      for (let y = y1; y < y2; y += 1) {
        for (let x = x1; x < x2; x += 1) {
          const i = (y * c.width + x) * 4;
          if (Math.hypot(d[i] - want[0], d[i + 1] - want[1], d[i + 2] - want[2]) < 48) {
            if (top === null) top = y;
            bottom = y;
            left = left === null ? x : Math.min(left, x);
            right = right === null ? x : Math.max(right, x);
          }
        }
      }
      return top === null ? null : { top: top / k, bottom: bottom / k, left: left / k, right: right / k };
    }));
  };
  image.src = u;
}), url, list);

async function shot(page, name) {
  // A page behind the other is not painted, and its screenshot waits on it.
  await page.bringToFront();
  await pause(300);
  const data = await page.screenshot({ encoding: "base64" });
  await writeFile(`${OUT}/${name}.png`, Buffer.from(data, "base64"));
  return "data:image/png;base64," + data;
}

const mine = await open("maxgraph");
const theirs = await open("cytoscape");
// Both at one zoom on one place, larger than the drawing opens, so a
// quarter of a unit is a pixel of the screenshot: the drawing's corner
// near the sheet's.
const ZOOM = Number(process.env.NAMES_ZOOM || 2);
for (const page of [mine, theirs]) {
  await page.evaluate((z) => {
    const cy = document.getElementById("cy")._cyreg.cy;
    const bb = cy.elements().boundingBox({ includeLabels: false });
    cy.viewport({ zoom: z, pan: { x: 40 - bb.x1 * z, y: 120 - bb.y1 * z } });
  }, ZOOM);
  await pause(600);
}
const boxes = (await boxesOf(mine)).filter((b) => b.x > 30 && b.y > 120 && b.x + b.w < 1400 && b.y + b.h < 860);
const other = Object.fromEntries((await boxesOf(theirs)).map((b) => [b.id, b]));
const placed = boxes.filter((b) => other[b.id] && Math.abs(other[b.id].x - b.x) < 0.5 && Math.abs(other[b.id].y - b.y) < 0.5);
console.log("boxes " + boxes.length + ", at the same place on both " + placed.length);
const a = await inkOf(mine, await shot(mine, "names-maxgraph"), placed);
const b = await inkOf(theirs, await shot(theirs, "names-cytoscape"), placed);
let worst = 0;
const rows = [];
placed.forEach((box, i) => {
  if (!a[i] || !b[i]) {
    console.log(JSON.stringify({ id: box.id, inked: [!!a[i], !!b[i]] }));
    return;
  }
  const dTop = a[i].top - b[i].top, dBottom = a[i].bottom - b[i].bottom;
  const dMid = (a[i].left + a[i].right) / 2 - (b[i].left + b[i].right) / 2;
  worst = Math.max(worst, Math.abs(dTop), Math.abs(dBottom));
  rows.push({ id: box.id, dTop: +dTop.toFixed(2), dBottom: +dBottom.toFixed(2), dMid: +dMid.toFixed(2),
    height: +(b[i].bottom - b[i].top).toFixed(1), at: [box.x, box.y, box.w, box.h].map(Math.round) });
});
rows.forEach((r) => console.log(JSON.stringify(r)));
const mean = (key) => rows.reduce((s, r) => s + r[key], 0) / (rows.length || 1);
console.log("measured " + rows.length + " | zoom " + (boxes[0] ? boxes[0].zoom.toFixed(2) : "?") + " | mean top "
  + mean("dTop").toFixed(2) + " | mean bottom " + mean("dBottom").toFixed(2) + " | mean middle "
  + mean("dMid").toFixed(2) + " | worst " + worst.toFixed(2)
  + " (CSS pixels, maxGraph less Cytoscape, down and right positive)");
console.log("page errors: " + (errors.length ? errors.join(" | ") : "none"));
await browser.close();
// maxGraph puts an HTML label at a whole unit of the drawing before it
// scales it (`Math.round` in its SVG canvas), so a name can land up to half
// a unit off wherever the sheet is panned; with the screenshot's own half
// pixel, one pixel is as near as a name is held. What is held tighter is
// the mean: no lean either way.
const leaning = Math.abs(mean("dTop")) > 0.5 || Math.abs(mean("dBottom")) > 0.5 || Math.abs(mean("dMid")) > 1;
process.exit(worst > 1 || leaning || errors.length || !rows.length ? 1 : 0);
