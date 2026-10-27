// Does a box carried in its boundary find the equal gap? On lending-onboarding
// (arrange_probe.mjs makes it), three subnets in a row in zone eu-west-2b,
// with a real pointer: the last carried off to the right and brought back
// to three pixels short of the gap the first two have, and held there; the
// red measures of the two gaps must be on the sheet, saying its size, and
// let go, the box must stand at that gap. Then Undo puts it back. Then the
// diagram's own, which maxGraph carries: on a new diagram three notes in a
// row, 40 units between the first two, the third carried to three pixels
// short of that, two measures saying 40, let go 40 from the second, and
// Undo.
//
//   node 80_APP/tools/dev/spacing_probe.mjs out/ URL
//
// It moves a box and makes a diagram, so run it on a copy of the repository. Exits 1 if a step
// does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node spacing_probe.mjs OUT URL");
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
const page = await browser.newPage();
await page.setViewport({ width: 1440, height: 900 });
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
await page.evaluateOnNewDocument(() => {
  localStorage.setItem("aac.rail.shut", "1");
  localStorage.setItem("aac.insp.shut", "0");
  localStorage.setItem("aac.tour", "taken");
});
const VIEW = "lending-onboarding";
const ROW = ["TS-NET-SUB-LEND-APP-B", "TS-NET-SUB-LEND-DATA-B", "TS-NET-SUB-LEND-PUB-B"];
if (!(await fetch(URL + "/api/view?id=" + VIEW)).ok) {
  console.log("skip  no " + VIEW + " here (arrange_probe.mjs makes it)");
  await browser.close();
  process.exit(0);
}
await page.goto(URL + "/#draw=" + VIEW, { waitUntil: "networkidle0", timeout: 60000 });
await page.waitForSelector(".mg-surface.takes-pointer svg", { timeout: 30000 });
await settled(page);
await pause(800);

// Each box in the drawing's units and on the screen.
const boxes = () => page.evaluate((ids) => {
  const cy = document.getElementById("cy")._cyreg.cy, r = document.getElementById("cy").getBoundingClientRect();
  return ids.map((id) => {
    // Its body, which the canvas measures by: a box picked is drawn with a
    // wider outline, and its bounding box with it.
    const n = cy.getElementById(id), p = n.position(), w = n.width(), h = n.height(), rp = n.renderedPosition();
    return { id, x1: p.x - w / 2, x2: p.x + w / 2, y1: p.y - h / 2, y2: p.y + h / 2, sx: r.left + rp.x, sy: r.top + rp.y,
      zoom: cy.zoom() };
  });
}, ROW);
const before = await boxes();
const [a, b, c] = before;
const gap = b.x1 - a.x2, z = a.zoom;
check("three subnets in a row", Math.abs(a.y1 - c.y1) < 30 && a.x2 < b.x1 && b.x2 < c.x1,
  before.map((q) => Math.round(q.x1) + "-" + Math.round(q.x2)).join(" "));
// Where the last stands when its gap is the first two's, three pixels to the right of that.
const target = { x: c.sx + (b.x2 + gap - c.x1) * z + 3, y: c.sy };
await page.mouse.move(c.sx, c.sy);
await page.mouse.down();
for (let i = 1; i <= 10; i += 1) await page.mouse.move(c.sx + 6 * i, c.sy + (i % 2));
for (let i = 1; i <= 12; i += 1) await page.mouse.move(c.sx + 60 + (target.x - c.sx - 60) * i / 12, target.y);
await pause(300);
const marks = await page.evaluate(() => Array.from(document.querySelectorAll(".cv-gap")).map((m) => ({
  axis: m.classList.contains("is-x") ? "x" : "y", said: m.textContent, w: m.offsetWidth })));
await page.screenshot({ path: `${OUT}/spacing-held.png` });
check("held near the equal gap, two red measures are on the sheet", marks.length === 2 && marks.every((m) => m.axis === "x"),
  JSON.stringify(marks));
check("each saying the gap", marks.every((m) => m.said === String(Math.round(gap))), Math.round(gap) + " units");
await page.mouse.up();
await pause(900);
const after = await boxes();
const gap2 = after[2].x1 - after[1].x2;
check("let go, it stands at the gap the first two have", Math.abs(gap2 - gap) < 0.5, gap2.toFixed(2) + " for " + gap.toFixed(2));
check("and the measures are gone", await page.evaluate(() => !document.querySelector(".cv-gap")));
await page.screenshot({ path: `${OUT}/spacing-let-go.png` });
await page.keyboard.down("Control");
await page.keyboard.press("z");
await page.keyboard.up("Control");
await pause(1500);
const back = await boxes();
check("Undo puts it back", Math.abs(back[2].x1 - c.x1) < 0.5 && Math.abs(back[2].y1 - c.y1) < 0.5,
  Math.round(back[2].x1) + " for " + Math.round(c.x1));

// The diagram's own, on a new diagram: three notes in a row, 40 units
// between the first two, the third carried to three pixels short of that.
const own = await browser.newPage();
await own.setViewport({ width: 1440, height: 900 });
own.on("pageerror", (e) => errors.push(String(e)));
own.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
await own.goto(URL + "/#draw", { waitUntil: "networkidle0", timeout: 60000 });
await own.waitForFunction(() => window.TerraneApp.Canvas.engine && window.TerraneApp.Canvas.engine.live(), { timeout: 30000 });
await pause(800);
await own.bringToFront();
const made = await own.evaluate(() => {
  const e = window.TerraneApp.Canvas.engine;
  return [e.add({ role: "note", label: "One", box: { x: 100, y: 200, w: 120, h: 60 } }),
    e.add({ role: "note", label: "Two", box: { x: 260, y: 200, w: 120, h: 60 } }),
    e.add({ role: "note", label: "Three", box: { x: 520, y: 210, w: 120, h: 60 } })];
});
await pause(600);
const notes = () => own.evaluate((keys) => {
  const list = window.TerraneApp.Canvas.cv.data.annotations || [];
  return keys.map((k) => list.find((a) => a.key === k));
}, made);
const n0 = await notes();
const screen = await own.evaluate((k) => {
  const b = window.TerraneApp.Canvas.engine.ownBoxes()[k], s = document.querySelector(".mg-surface").getBoundingClientRect();
  return { x: s.left + b.x + b.w / 2, y: s.top + b.y + b.h / 2, k: b.w / 120 };
}, made[2]);
const to = screen.x + (n0[1].at[0] + 160 - n0[2].at[0]) * screen.k + 3;
await own.mouse.move(screen.x, screen.y);
await own.mouse.down();
for (let i = 1; i <= 10; i += 1) await own.mouse.move(screen.x + 4 * i, screen.y);
for (let i = 1; i <= 14; i += 1) await own.mouse.move(screen.x + 40 + (to - screen.x - 40) * i / 14, screen.y);
await pause(300);
const ownMarks = await own.evaluate(() => Array.from(document.querySelectorAll(".cv-gap")).map((m) => ({
  axis: m.classList.contains("is-x") ? "x" : "y", said: m.textContent })));
await own.screenshot({ path: `${OUT}/spacing-own-held.png` });
check("a note of the diagram's own held near the gap, two measures saying 40",
  ownMarks.length === 2 && ownMarks.every((m) => m.axis === "x" && m.said === "40"), JSON.stringify(ownMarks));
await own.mouse.up();
await pause(800);
const n1 = await notes();
check("let go, it stands 40 from the second", n1[2].at[0] - n1[1].at[0] === 160, (n1[2].at[0] - n1[1].at[0] - 120) + " units");
check("and the measures are gone", await own.evaluate(() => !document.querySelector(".cv-gap")));
await own.keyboard.down("Control");
await own.keyboard.press("z");
await own.keyboard.up("Control");
await pause(800);
const n2 = await notes();
check("Undo puts it back", n2[2].at[0] === n0[2].at[0], n2[2].at[0] + " for " + n0[2].at[0]);
check("no page errors", !errors.length, errors.join(" | "));
await browser.close();
process.exit(failed ? 1 : 0);
