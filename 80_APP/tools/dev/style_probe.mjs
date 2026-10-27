// Does the Style tab do what V16 draws, and does Copy the look paint? On a
// new diagram with three shapes and a note of its own: the first picked
// opens on Style; Rose clicked, Opacity typed as 60, L clicked for its
// edge, its corners dragged to about 16 and its shadow set to None each
// land in its look, are drawn by maxGraph, kept in the file and drawn by
// the engine's picture; Copy the look clicked, the next shape and the note
// clicked take that look, a click on the one copied from paints nothing,
// Esc stops it, and one Undo takes the note's back; Ctrl+Alt+C on the
// first and Ctrl+Alt+V on the third paint by keys; the Arrange tab takes a
// width typed in and brings it forward.
//
//   node 80_APP/tools/dev/style_probe.mjs out/ URL
//
// It makes a diagram, so run it on a copy of the repository. Exits 1 if a
// step does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node style_probe.mjs OUT URL");
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
page.on("pageerror", (e) => errors.push(String(e) + " " + String(e.stack || "").split(String.fromCharCode(10))
  .slice(1, 4).join(" | ")));
page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
await page.evaluateOnNewDocument(() => {
  localStorage.setItem("aac.rail.shut", "1");
  localStorage.setItem("aac.insp.shut", "0");
  localStorage.setItem("aac.tour", "taken");
});
await page.goto(URL + "/#draw", { waitUntil: "networkidle0", timeout: 60000 });
await page.waitForFunction(() => window.TerraneApp.Canvas.engine && window.TerraneApp.Canvas.engine.live(), { timeout: 30000 });
await settled(page);
await pause(700);
await page.bringToFront();

async function saved() {
  await pause(400);
  await page.waitForFunction(() => /^(saved|failed)$/.test(window.TerraneApp.Canvas.cv.status), { timeout: 15000 });
}
const look = (k) => page.evaluate((key) => Object.assign({}, (window.TerraneApp.Canvas.engine.item(key) || {}).look), k);
const item = (k) => page.evaluate((key) => window.TerraneApp.Canvas.engine.item(key), k);
const pick = (k) => page.evaluate((key) => window.TerraneApp.Canvas.picked([], [key]), k).then(() => pause(400));
async function screenBox(k) {
  return page.evaluate((key) => {
    const b = window.TerraneApp.Canvas.engine.ownBoxes()[key], s = document.querySelector(".mg-surface").getBoundingClientRect();
    return { cx: s.left + b.x + b.w / 2, cy: s.top + b.y + b.h / 2 };
  }, k);
}
async function clickOn(k) {
  const b = await screenBox(k);
  await page.mouse.click(b.cx, b.cy);
  await pause(500);
}
async function press(group, word) {
  const b = await page.evaluateHandle((g, w) => Array.prototype.find.call(
    document.querySelectorAll('#cvDetails [aria-label="' + g + '"] button'), (x) => x.textContent === w), group, word);
  await b.asElement().click();
  await pause(500);
}
async function typeInto(selector, value) {
  // A number box's digits are not picked by a triple click: Ctrl+A.
  await page.click(selector);
  await page.keyboard.down("Control");
  await page.keyboard.press("a");
  await page.keyboard.up("Control");
  await page.keyboard.type(String(value));
  await page.keyboard.press("Tab");
  await pause(500);
}
const styleOf = (k) => page.evaluate((key) => {
  const e = window.TerraneApp.Canvas.engine, s = e._style ? e._style(key) : null;
  return s;
}, k);

const keys = await page.evaluate(() => {
  const e = window.TerraneApp.Canvas.engine;
  const a = e.add({ role: "shape", shape: "rounded", label: "Payments API", box: { x: 80, y: 120, w: 150, h: 64 } });
  const b = e.add({ role: "shape", shape: "rectangle", label: "Ledger", box: { x: 300, y: 120, w: 150, h: 64 } });
  const c = e.add({ role: "note", label: "Moves in Q2", box: { x: 80, y: 260, w: 170, h: 80 } });
  const d = e.add({ role: "shape", shape: "rounded", label: "Fraud scoring", box: { x: 300, y: 260, w: 150, h: 64 } });
  e.select([]);
  return { a, b, c, d };
});
await saved();
await pick(keys.a);
check("picked, a shape opens on Style", await page.evaluate(() => {
  const on = document.querySelector('#cvDetails .cv-tabs [aria-checked="true"]');
  return !!on && on.textContent === "Style";
}));
check("with the diagram's look, words and size, shape, fill and opacity, edge and corners, and shadow",
  await page.evaluate(() => ["Look of this diagram", "Words", "Shape", "Fill", "Edge and corners", "Shadow"].every((t) =>
    Array.prototype.some.call(document.querySelectorAll("#cvDetails .cv-sec-h .cv-label"), (n) => n.textContent === t))));

await page.click('#cvDetails .cv-swatch[aria-label="Rose"]');
await pause(500);
await typeInto("#cvDetails .cv-opacity", 60);
await press("How heavy the edge is", "L");
// The corners' slider dragged by its knob, to about half way: 16 of 32.
const range = await page.evaluate(() => {
  const r = document.querySelector("#cvDetails .cv-range").getBoundingClientRect();
  return { x: r.left, y: r.top + r.height / 2, w: r.width, v: Number(document.querySelector("#cvDetails .cv-range").value) };
});
await page.mouse.move(range.x + range.w * range.v / 32, range.y);
await page.mouse.down();
for (let i = 1; i <= 8; i += 1) await page.mouse.move(range.x + range.w * (range.v + (16 - range.v) * i / 8) / 32, range.y);
await page.mouse.up();
await pause(500);
await press("Shadow", "None");
let mine = await look(keys.a);
check("Rose, 60, L, corners about 16 and no shadow land in its look", mine.fill === "rose" && mine.opacity === 60
  && mine.weight === "l" && Math.abs((mine.corners || 0) - 16) <= 1 && mine.shadow === "none", JSON.stringify(mine));
check("the panel says a see-through fill casts no shadow", await page.evaluate(() =>
  /none under a see-through fill/.test(document.getElementById("cvDetails").innerText)));
const drawn = await page.evaluate((key) => {
  const s = document.querySelector('.mg-surface svg');
  const shapes = Array.from(s.querySelectorAll("rect, path")).filter((n) => (n.getAttribute("fill-opacity") || "") === "0.6");
  return shapes.length;
}, keys.a);
check("maxGraph draws its fill at 60", drawn >= 1, String(drawn));
await saved();
const filed = ((await page.evaluate(() => fetch("/api/view?id=" + window.TerraneApp.Canvas.cv.id).then((r) => r.json())))
  .data.annotations || []).find((x) => x.key === keys.a) || {};
check("and the file keeps it", JSON.stringify(filed.look) === JSON.stringify(mine), JSON.stringify(filed.look));
const svg = await page.evaluate(() => fetch("/api/svg?view=" + window.TerraneApp.Canvas.cv.id).then((r) => r.text()));
const ownA = (svg.split('data-key="' + keys.a + '"')[1] || "").split("</g>")[0];
check("and the engine's picture draws it so", /fill-opacity="0.6"/.test(ownA) && /stroke-width="2"/.test(ownA)
  && /rx="1[5-7]"/.test(ownA) && !/class="shadow"/.test(ownA), ownA.slice(0, 160));

// Copy the look, and paint it on with clicks.
const copyButton = async () => page.evaluateHandle(() => Array.prototype.find.call(
  document.querySelectorAll("#cvDetails .cv-acts button"), (b) => /Copy the look|Stop painting/.test(b.textContent)));
await (await copyButton()).asElement().click();
await pause(400);
check("Copy the look starts painting", await page.evaluate(() => document.body.classList.contains("cv-painting")));
await clickOn(keys.b);
await clickOn(keys.c);
const lb = await look(keys.b), lc = await look(keys.c);
check("the next shape clicked takes the look", lb.fill === "rose" && lb.opacity === 60 && lb.weight === "l"
  && lb.corners === mine.corners && lb.shadow === "none", JSON.stringify(lb));
check("and the note too", lc.fill === "rose" && lc.opacity === 60 && lc.corners === mine.corners && lc.shadow === "none",
  JSON.stringify(lc));
await clickOn(keys.a);
check("the one copied from is left as it was", JSON.stringify(await look(keys.a)) === JSON.stringify(mine));
await page.keyboard.press("Escape");
await pause(400);
check("Esc stops painting", await page.evaluate(() => !document.body.classList.contains("cv-painting")
  && !window.TerraneApp.Canvas.painting));
await clickOn(keys.d);
check("and the next click paints nothing", !(await look(keys.d)).opacity, JSON.stringify(await look(keys.d)));
await page.focus("#cy");
await page.keyboard.down("Control");
await page.keyboard.press("z");
await page.keyboard.up("Control");
await pause(600);
check("one Undo takes the note's look back", !(await look(keys.c)).opacity, JSON.stringify(await look(keys.c)));

// By keys: Ctrl+Alt+C on the first, Ctrl+Alt+V on the fourth.
await pick(keys.a);
await page.focus("#cy");
await page.keyboard.down("Control");
await page.keyboard.down("Alt");
await page.keyboard.press("KeyC");
await page.keyboard.up("Alt");
await page.keyboard.up("Control");
await pick(keys.d);
await page.focus("#cy");
await page.keyboard.down("Control");
await page.keyboard.down("Alt");
await page.keyboard.press("KeyV");
await page.keyboard.up("Alt");
await page.keyboard.up("Control");
await pause(500);
const ld = await look(keys.d);
check("Ctrl+Alt+C and Ctrl+Alt+V paint by keys", ld.fill === "rose" && ld.opacity === 60 && ld.weight === "l",
  JSON.stringify(ld));
await page.screenshot({ path: OUT + "/style.png" });

// Arrange: a width typed in, and forward.
await pick(keys.a);
await press("Style or arrange", "Arrange");
check("Arrange shows its size, how far it is turned, and its order", await page.evaluate(() =>
  ["Size", "Turned", "Order"].every((t) => Array.prototype.some.call(
    document.querySelectorAll("#cvDetails .cv-sec-h .cv-label"), (n) => n.textContent === t))));
await typeInto("#cvDetails .cv-width", 200);
await saved();
const sized = await item(keys.a);
check("a width typed in is its width, in the file too", sized.size && sized.size[0] === 200, JSON.stringify(sized.size));
const order = () => page.evaluate(() => (window.TerraneApp.Canvas.cv.data.annotations || []).map((x) => x.key));
const before = (await order()).indexOf(keys.a);
const forward = await page.evaluateHandle(() => Array.prototype.find.call(
  document.querySelectorAll("#cvDetails button"), (b) => b.textContent === "Bring forward"));
await forward.asElement().click();
await saved();
check("Bring forward moves it up the order", (await order()).indexOf(keys.a) > before, before + " -> "
  + (await order()).indexOf(keys.a));
await page.screenshot({ path: OUT + "/arrange.png" });
await page.evaluate(() => { window.TerraneApp.Canvas.ownTab = "style"; });
check("no page errors", errors.length === 0, errors.join(" / "));
await browser.close();
process.exit(failed ? 1 : 0);
