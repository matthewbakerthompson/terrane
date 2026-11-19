// Do drawing layers work as V16 draws them? On a new diagram with three
// shapes of its own: the toolbar's last button opens Drawing layers, the
// diagram's first layer marked to draw on and the estate's records under
// it; a new layer goes on top, marked, and what is drawn next goes on it;
// hidden, it is not drawn, the picture leaves it out and the file keeps
// it; a locked layer's shape is not picked; Ctrl+Alt+] takes a shape to
// the layer above; the estate carried to the top by its grip puts the
// first layer under the records, what named no layer kept on it by name;
// a layer renamed by a double-click, and deleted, what was on it going to
// the layer under it; one Undo puts it back; and the Arrange tab says the
// layer.
//
//   node 80_APP/tools/dev/layers_probe.mjs out/ URL
//
// It makes a diagram, so run it on a copy of the repository. Exits 1 if a
// step does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node layers_probe.mjs OUT URL");
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
await page.goto(URL + "/#draw", { waitUntil: "networkidle0", timeout: 60000 });
await page.waitForFunction(() => window.TerraneApp.Canvas.engine && window.TerraneApp.Canvas.engine.live(), { timeout: 30000 });
await settled(page);
await pause(700);
await page.bringToFront();

async function saved() {
  await pause(400);
  await page.waitForFunction(() => /^(saved|failed)$/.test(window.TerraneApp.Canvas.cv.status), { timeout: 15000 });
}
const item = (k) => page.evaluate((key) => window.TerraneApp.Canvas.engine.item(key), k);
const layerOf = (k) => page.evaluate((key) => window.TerraneApp.Canvas.engine.layerOf(key), k);
const layers = () => page.evaluate(() => JSON.parse(JSON.stringify(window.TerraneApp.Canvas.cv.data.layers || null)));
const rows = () => page.evaluate(() => Array.from(document.querySelectorAll("#cvLayers .cv-layer")).map((r) => ({
  key: r.dataset.key, text: r.innerText.replace(/\s+/g, " ").trim(), on: r.classList.contains("is-on") })));
const drawn = () => page.evaluate(() => document.querySelector(".mg-surface").innerText);
const file = () => page.evaluate(() => fetch("/api/view?id=" + window.TerraneApp.Canvas.cv.id).then((r) => r.json()))
  .then((f) => f.data || {});
const picked = () => page.evaluate(() => { const s = window.TerraneApp.Canvas.cv.sel; return s && s.keys ? s.keys.slice() : []; });
const at = (k) => page.evaluate((key) => {
  const b = window.TerraneApp.Canvas.engine.boxOf(key), cy = document.getElementById("cy")._cyreg.cy;
  const r = document.getElementById("cy").getBoundingClientRect(), z = cy.zoom(), p = cy.pan();
  return { x: r.left + (b.x1 + b.x2) / 2 * z + p.x, y: r.top + (b.y1 + b.y2) / 2 * z + p.y };
}, k);
async function rowButton(key, label) {
  const b = await page.evaluateHandle((k, l) => {
    const r = document.querySelector('#cvLayers .cv-layer[data-key="' + k + '"]');
    return r ? Array.from(r.querySelectorAll("button")).find((x) => x.getAttribute("aria-label") === l) || null : null;
  }, key, label);
  return b.asElement();
}
async function chord(...combo) {
  await page.focus("#cy");
  for (const k of combo.slice(0, -1)) await page.keyboard.down(k);
  await page.keyboard.press(combo[combo.length - 1]);
  for (const k of combo.slice(0, -1).reverse()) await page.keyboard.up(k);
  await pause(500);
}

const keys = await page.evaluate(() => {
  const e = window.TerraneApp.Canvas.engine;
  const add = (label, x, y) => e.add({ role: "shape", shape: "rounded", label: label, box: { x: x, y: y, w: 150, h: 64 } });
  const out = { a: add("Gateway", 80, 140), b: add("Ledger", 280, 140), c: add("Fraud check", 480, 140) };
  e.select([]);
  return out;
});
await saved();

await page.click("#cvLayersBtn");
await pause(400);
let r = await rows();
check("the toolbar's last button opens Drawing layers", await page.evaluate(() => !document.getElementById("cvLayers").hidden));
check("the diagram's first layer, marked to draw on, over the estate's records",
  r.length === 2 && r[0].key === "layer-1" && r[0].on && /drawing here/.test(r[0].text) && r[1].key === "estate" &&
  /Records from the estate/.test(r[1].text), JSON.stringify(r));
check("and it counts the three shapes on it", / 3$/.test(r[0].text), r[0].text);

// A new layer goes on top, marked, and what is drawn next goes on it.
await page.evaluate(() => Array.from(document.querySelectorAll("#cvLayers button")).find((b) => /New layer/.test(b.innerText)).click());
await pause(400);
r = await rows();
check("+ New layer puts a layer on top, marked to draw on", r.length === 3 && r[0].key === "layer-2" && r[0].on, JSON.stringify(r));
const note = await page.evaluate(() => window.TerraneApp.Canvas.engine.add({ role: "note", label: "Review: who signs off",
  box: { x: 680, y: 140, w: 184, h: 96 } }));
await pause(400);
check("what is drawn next goes on it", (await item(note)).layer === "layer-2", JSON.stringify(await item(note)));
check("and what named no layer stays on the first", (await layerOf(keys.a)) === "layer-1" && !(await item(keys.a)).layer);

// Hidden, it is not drawn; the picture leaves it out; the file keeps it.
await (await rowButton("layer-2", "Hide it")).click();
await pause(500);
check("hidden, the layer's note is not drawn", !/Review: who signs off/.test(await drawn()) && /Gateway/.test(await drawn()));
check("and its row says so", /hidden/.test((await rows())[0].text));
await saved();
const svg = await page.evaluate(() => fetch("/api/svg?view=" + window.TerraneApp.Canvas.cv.id).then((r) => r.text()));
check("the picture leaves the hidden layer out", !/Review: who signs off/.test(svg) && /Gateway/.test(svg));
const f = await file();
check("the file keeps the layers, hidden and all, and the note", JSON.stringify(f.layers) ===
  JSON.stringify([{ key: "layer-2", name: "Layer 2", hidden: true }, { key: "layer-1", name: "Layer 1" }, { key: "estate" }]) &&
  (f.annotations || []).some((a) => a.key === note), JSON.stringify(f.layers));
await (await rowButton("layer-2", "Show it")).click();
await pause(400);
check("shown again, it is drawn", /Review: who signs off/.test(await drawn()));

// A locked layer's shape is not picked.
// The popover is closed to click on the sheet: it sits over the shapes.
const popover = async (open) => {
  if ((await page.evaluate(() => !document.getElementById("cvLayers").hidden)) !== open) await page.click("#cvLayersBtn");
  await pause(300);
};
await (await rowButton("layer-1", "Lock it")).click();
await pause(400);
await popover(false);
let p = await at(keys.b);
await page.mouse.click(p.x, p.y);
await pause(400);
check("a locked layer's shape is not picked", !(await picked()).includes(keys.b), JSON.stringify(await picked()));
await popover(true);
await (await rowButton("layer-1", "Unlock it")).click();
await pause(400);
await popover(false);
p = await at(keys.b);
await page.mouse.click(p.x, p.y);
await pause(400);
check("unlocked, it is", JSON.stringify(await picked()) === JSON.stringify([keys.b]), JSON.stringify(await picked()));

// Ctrl+Alt+] takes it to the layer above.
await chord("Control", "Alt", "BracketRight");
check("Ctrl+Alt+] takes it to the layer above", (await item(keys.b)).layer === "layer-2", JSON.stringify(await item(keys.b)));
check("and the Arrange tab says its layer", await page.evaluate(() => {
  window.TerraneApp.Canvas.ownTab = "arrange";
  window.TerraneApp.Canvas.picked([], [window.TerraneApp.Canvas.cv.sel.keys[0]]);
  const s = document.querySelector("#cvDetails .cv-layer");
  return !!s && s.value === "layer-2";
}));
await page.evaluate(() => { window.TerraneApp.Canvas.ownTab = "style"; });
await popover(true);

// The estate carried to the top by its grip.
const grip = await page.evaluate(() => {
  const row = document.querySelector('#cvLayers .cv-layer[data-key="estate"] .cv-lane-grip').getBoundingClientRect();
  const top = document.querySelector("#cvLayers .cv-layer").getBoundingClientRect();
  return { x: row.left + row.width / 2, y: row.top + row.height / 2, top: top.top };
});
await page.mouse.move(grip.x, grip.y);
await page.mouse.down();
for (let i = 1; i <= 8; i += 1) await page.mouse.move(grip.x, grip.y + (grip.top - 4 - grip.y) * i / 8);
await page.mouse.up();
await pause(600);
let L = await layers();
check("the estate carried to the top by its grip", L.map((l) => l.key).join() === "estate,layer-2,layer-1", JSON.stringify(L));
check("what named no layer kept on the first by name", (await item(keys.a)).layer === "layer-1" &&
  (await layerOf(keys.a)) === "layer-1", JSON.stringify(await item(keys.a)));
await saved();
const graph = await page.evaluate(() => fetch("/api/graph?view=" + window.TerraneApp.Canvas.cv.id).then((r) => r.json()));
const under = (graph.annotations || []).filter((a) => a._under).map((a) => a.key).sort();
check("so it is drawn under the estate's records, and the rest too", JSON.stringify(under) ===
  JSON.stringify([keys.a, keys.b, keys.c, note].sort()), JSON.stringify(under));
await page.screenshot({ path: OUT + "/layers.png" });

// Renamed by a double-click, then deleted; one Undo puts it back.
const name = await page.evaluate(() => {
  const n = document.querySelector('#cvLayers .cv-layer[data-key="layer-2"] .cv-layer-n').getBoundingClientRect();
  return { x: n.left + 10, y: n.top + n.height / 2 };
});
await page.mouse.click(name.x, name.y, { count: 2 });
await pause(300);
await page.keyboard.down("Control");
await page.keyboard.press("a");
await page.keyboard.up("Control");
await page.keyboard.type("Review notes");
await page.keyboard.press("Enter");
await pause(400);
check("a double-click renames a layer", ((await layers()).find((l) => l.key === "layer-2") || {}).name === "Review notes");
await page.evaluate(() => document.querySelector('#cvLayers .cv-layer[data-key="layer-2"] .cv-layer-x').click());
await pause(500);
L = await layers();
check("deleted, what was on it goes to the layer under it", L.map((l) => l.key).join() === "estate,layer-1" &&
  (await layerOf(note)) === "layer-1" && (await layerOf(keys.b)) === "layer-1", JSON.stringify([L, await item(note)]));
await page.focus("#cy");
await chord("Control", "z");
L = await layers();
check("one Undo puts it back, with what was on it", L.map((l) => l.key).join() === "estate,layer-2,layer-1" &&
  (await layerOf(note)) === "layer-2", JSON.stringify(L));
check("no page errors", errors.length === 0, errors.join(" / "));
await browser.close();
process.exit(failed ? 1 : 0);
