// Does Snap to grid put things on the grid? On lending-onboarding
// (arrange_probe.mjs makes it), with a real pointer: the status bar under
// the sheet says what is on the diagram; Snap to grid turned on there, and
// kept in the browser; a record carried an odd distance and let go, its
// corner on the ten-unit grid; a note drawn with the Note tool, its corner
// and size on the grid, and carried, still on it; Snap to grid turned off.
//
//   node 80_APP/tools/dev/snap_probe.mjs out/ URL
//
// It moves a record and draws a note, so run it on a copy of the
// repository. Exits 1 if a step does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node snap_probe.mjs OUT URL");
  process.exit(2);
}
await mkdir(OUT, { recursive: true });
const pause = (ms) => new Promise((r) => setTimeout(r, ms));
const browser = await launch();
const errors = [];
let failed = false;
function check(what, ok, said) {
  console.log((ok ? "ok   " : "FAIL ") + what + (said !== undefined ? ": " + said : ""));
  if (!ok) failed = true;
}
const VIEW = "lending-onboarding";
if (!(await fetch(URL + "/api/view?id=" + VIEW)).ok) {
  console.log("skip  no " + VIEW + " here (arrange_probe.mjs makes it)");
  await browser.close();
  process.exit(0);
}
const page = await browser.newPage();
await page.setViewport({ width: 1440, height: 900 });
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
await page.evaluateOnNewDocument(() => {
  localStorage.setItem("aac.rail.shut", "1");
  localStorage.setItem("aac.insp.shut", "0");
  localStorage.setItem("aac.tour", "taken");
  localStorage.removeItem("aac.canvas.snap");
});
await page.goto(URL + "/#draw=" + VIEW, { waitUntil: "networkidle0", timeout: 60000 });
await page.waitForSelector(".mg-surface.takes-pointer svg", { timeout: 30000 });
await settled(page);
await pause(800);
async function drag(a, b) {
  await page.mouse.move(a.x, a.y);
  await page.mouse.down();
  for (let i = 1; i <= 12; i += 1) await page.mouse.move(a.x + (b.x - a.x) * i / 12, a.y + (b.y - a.y) * i / 12);
  await page.mouse.up();
  await pause(600);
}
const onGrid = (v) => Math.abs(v / 10 - Math.round(v / 10)) < 0.001;

const status = await page.evaluate(() => {
  const bar = document.getElementById("cvStatus");
  return { shown: !bar.hidden && bar.offsetHeight > 0, words: bar.innerText.replace(/\s+/g, " ").trim(),
    under: bar.getBoundingClientRect().top >= document.getElementById("mapSheet").getBoundingClientRect().bottom - 1 };
});
check("the status bar is under the sheet", status.shown && status.under, status.words);
check("saying how it is laid out and what is on it", /Arranged by hand/.test(status.words) && /\d+ records/.test(status.words),
  status.words);
const pressed = () => page.evaluate(() => document.getElementById("cvSnap").getAttribute("aria-pressed"));
check("Snap to grid is off to begin with", (await pressed()) === "false");
await page.click("#cvSnap");
check("and on once pressed, kept in the browser", (await pressed()) === "true"
  && (await page.evaluate(() => localStorage.getItem("aac.canvas.snap"))) === "1");

// A record carried an odd distance.
const RECORD = "TS-NET-VPC-LENDING";
const at = await page.evaluate((id) => {
  const cy = document.getElementById("cy")._cyreg.cy, r = document.getElementById("cy").getBoundingClientRect();
  const rp = cy.getElementById(id).renderedPosition();
  return { x: r.left + rp.x, y: r.top + rp.y };
}, RECORD);
await page.mouse.move(at.x, at.y);
await page.mouse.down();
for (let i = 1; i <= 12; i += 1) await page.mouse.move(at.x + 37 * i / 12, at.y + 23 * i / 12);
// A guide's line or an equal gap takes its axis before the grid does, by
// design: what was showing as it was let go says which axes are the grid's.
const shown = await page.evaluate(() => ({
  x: !document.getElementById("cvGuideX").hidden || !!document.querySelector(".cv-gap.is-x"),
  y: !document.getElementById("cvGuideY").hidden || !!document.querySelector(".cv-gap.is-y") }));
await page.mouse.up();
await pause(600);
const corner = await page.evaluate((id) => {
  const n = document.getElementById("cy")._cyreg.cy.getElementById(id), p = n.position();
  return { x: p.x - n.width() / 2, y: p.y - n.height() / 2 };
}, RECORD);
check("a record let go has its corner on the grid, where no guide took the axis",
  (shown.x || onGrid(corner.x)) && (shown.y || onGrid(corner.y)) && !(shown.x && shown.y),
  corner.x.toFixed(2) + ", " + corner.y.toFixed(2) + (shown.x || shown.y ? " (a guide took " + (shown.x ? "x" : "y") + ")" : ""));

// A note drawn, then carried.
const sheet = await page.evaluate(() => { const b = document.querySelector(".mg-surface").getBoundingClientRect(); return { x: b.left, y: b.top, w: b.width, h: b.height }; });
const own = () => page.evaluate(() => (window.TerraneApp.Canvas.cv.data.annotations || []).map((a) => Object.assign({}, a)));
const had = new Set((await own()).map((a) => a.key));
await page.click("#cvNote");
await drag({ x: sheet.x + sheet.w * 0.86, y: sheet.y + sheet.h * 0.24 }, { x: sheet.x + sheet.w * 0.86 + 133, y: sheet.y + sheet.h * 0.24 + 71 });
await page.waitForSelector(".mg-edit", { timeout: 5000 });
await page.keyboard.type("On the grid");
await page.keyboard.down("Control");
await page.keyboard.press("Enter");
await page.keyboard.up("Control");
await pause(400);
let note = (await own()).find((a) => a.role === "note" && !had.has(a.key));
check("a note drawn has its corner and its size on the grid", !!note && note.at.every(onGrid) && note.size.every(onGrid),
  note && JSON.stringify({ at: note.at, size: note.size }));
const nb = (await page.evaluate(() => window.TerraneApp.Canvas.engine.ownBoxes()))[note.key];
await drag({ x: sheet.x + nb.x + nb.w / 2, y: sheet.y + nb.y + nb.h / 2 }, { x: sheet.x + nb.x + nb.w / 2 + 33, y: sheet.y + nb.y + nb.h / 2 + 17 });
const moved = (await own()).find((a) => a.key === note.key);
check("carried, it is still on the grid", moved.at.every(onGrid) && JSON.stringify(moved.at) !== JSON.stringify(note.at),
  JSON.stringify(note.at) + " to " + JSON.stringify(moved.at));
await page.screenshot({ path: `${OUT}/snap-on.png` });
await page.click("#cvSnap");
check("Snap to grid off again", (await pressed()) === "false"
  && (await page.evaluate(() => localStorage.getItem("aac.canvas.snap"))) === null);
check("no page errors", !errors.length, errors.join(" | "));
await browser.close();
process.exit(failed ? 1 : 0);
