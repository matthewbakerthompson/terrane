// Does a shape of the diagram's own turn? On lending-onboarding
// (arrange_probe.mjs makes it, annotate_probe.mjs puts a note on it): the
// note picked, its panel offers Turned; set to 30, maxGraph draws it turned
// and the diagram's file keeps `rotate: 30`, which the engine's own picture
// turns too; its handle above it, carried round with a real pointer, turns
// it on by whole steps; one Undo puts it back; a frame offers no Turned; a
// locked note shows no handle; and set to 0, the file says nothing of it.
//
//   node 80_APP/tools/dev/rotate_probe.mjs out/ URL
//
// It changes the diagram, so run it on a copy of the repository. Exits 1 if
// a step does not do what it says.
import { mkdir, writeFile } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node rotate_probe.mjs OUT URL");
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
});
await page.goto(URL + "/#draw=" + VIEW, { waitUntil: "networkidle0", timeout: 60000 });
await page.waitForSelector(".mg-surface.takes-pointer svg", { timeout: 30000 });
await settled(page);
await pause(600);
await page.bringToFront();
await page.focus("#cy");
async function keys(...combo) {
  for (const k of combo.slice(0, -1)) await page.keyboard.down(k);
  await page.keyboard.press(combo[combo.length - 1]);
  for (const k of combo.slice(0, -1).reverse()) await page.keyboard.up(k);
  await pause(400);
}
async function saved() {
  await pause(400);
  await page.waitForFunction(() => /^(saved|failed)$/.test(window.TerraneApp.Canvas.cv.status), { timeout: 15000 });
}
const own = () => page.evaluate(() => (window.TerraneApp.Canvas.cv.data.annotations || []).map((a) => Object.assign({}, a)));
const file = () => page.evaluate((v) => fetch("/api/view?id=" + v).then((r) => r.json()), VIEW)
  .then((f) => (f.data && f.data.annotations) || []);
const pick = (k) => page.evaluate((key) => window.TerraneApp.Canvas.picked([], [key]), k).then(() => pause(300));
async function turnTo(v) {
  await page.evaluate((value) => {
    const f = document.querySelector("#cvDetails .cv-turn");
    f.value = String(value);
    f.dispatchEvent(new Event("change", { bubbles: true }));
  }, v);
  await pause(400);
}
const turned = (k) => own().then((list) => (list.find((a) => a.key === k) || {}).rotate || 0);

const note = (await own()).find((a) => a.role === "note");
if (!note) {
  console.log("skip  no note on " + VIEW + " (annotate_probe.mjs puts one there)");
  await browser.close();
  process.exit(0);
}
await pick(note.key);
// Turned lives in the Arrange tab (V16), which stays open as the pick moves.
const arrange = await page.evaluateHandle(() => Array.prototype.find.call(
  document.querySelectorAll('#cvDetails .cv-tabs button'), (b) => b.textContent === "Arrange"));
await arrange.asElement().click();
await pause(400);
check("the note's panel offers Turned", await page.evaluate(() => !!document.querySelector("#cvDetails .cv-turn")));
if (note.rotate) { await turnTo(0); await saved(); }

await turnTo(30);
check("set to 30, the note is turned", (await turned(note.key)) === 30, String(await turned(note.key)));
check("and maxGraph draws it turned", await page.evaluate(() =>
  !!document.querySelector('.mg-surface svg [transform*="rotate(30"]')));
await saved();
check("the diagram's file keeps rotate: 30", ((await file()).find((a) => a.key === note.key) || {}).rotate === 30);
const svg = await (await fetch(URL + "/api/svg?view=" + VIEW)).text();
check("and the engine's own picture turns it about its middle", new RegExp('data-key="' + note.key
  + '" data-role="note" transform="rotate\\(30 ').test(svg));
await writeFile(`${OUT}/rotate.svg`, svg);
await page.screenshot({ path: `${OUT}/rotate.png` });

// The handle above it, carried round its middle by sixty degrees.
await pick(note.key);
const handle = await page.evaluate(() => {
  const h = Array.from(document.querySelectorAll(".mg-surface svg *")).find((n) => n.style && n.style.cursor === "crosshair");
  if (!h) return null;
  const b = h.getBoundingClientRect();
  return { x: b.left + b.width / 2, y: b.top + b.height / 2 };
});
check("picked, it shows the handle that turns it", !!handle);
if (handle) {
  const nb = (await page.evaluate(() => window.TerraneApp.Canvas.engine.ownBoxes()))[note.key];
  const sv = await page.evaluate(() => { const b = document.querySelector(".mg-surface").getBoundingClientRect(); return { x: b.left, y: b.top }; });
  const mid = { x: sv.x + nb.x + nb.w / 2, y: sv.y + nb.y + nb.h / 2 };
  const r = Math.hypot(handle.x - mid.x, handle.y - mid.y), from = Math.atan2(handle.y - mid.y, handle.x - mid.x);
  await page.mouse.move(handle.x, handle.y);
  await page.mouse.down();
  for (let i = 1; i <= 16; i += 1) {
    const a = from + (Math.PI / 3) * i / 16;
    await page.mouse.move(mid.x + r * Math.cos(a), mid.y + r * Math.sin(a));
  }
  await page.mouse.up();
  await pause(600);
  const now = await turned(note.key);
  check("carried round sixty degrees, it turns on by whole steps", now >= 75 && now <= 105 && now % 5 === 0, String(now));
  await keys("Control", "z");
  check("and one Undo puts it back at 30", (await turned(note.key)) === 30, String(await turned(note.key)));
}

// A frame, drawn for the asking where the diagram has none, and taken away.
let frame = (await own()).find((a) => a.role === "frame"), drew = null;
if (!frame) {
  const nb = (await page.evaluate(() => window.TerraneApp.Canvas.engine.ownBoxes()))[note.key];
  drew = await page.evaluate((b) => window.TerraneApp.Canvas.engine.add({ role: "frame", label: "Asked",
    box: { x: b.x + b.w + 40, y: b.y, w: 160, h: 100 } }), nb);
  await pause(400);
  frame = { key: drew };
}
await pick(frame.key);
check("a frame offers no Turned", await page.evaluate(() => !!document.getElementById("cvDetails").innerText
  && !document.querySelector("#cvDetails .cv-turn")));
check("nor a handle to turn it by", await page.evaluate(() =>
  !Array.from(document.querySelectorAll(".mg-surface svg *")).some((n) => n.style && n.style.cursor === "crosshair")));
if (drew) {
  await page.evaluate((k) => window.TerraneApp.Canvas.engine.remove([k]), drew);
  await pause(400);
}

await pick(note.key);
await keys("Control", "Shift", "l");
const shown = await page.evaluate(() =>
  Array.from(document.querySelectorAll(".mg-surface svg *")).some((n) => n.style && n.style.cursor === "crosshair"));
check("locked, the note shows no handle", !shown);
await keys("Control", "Shift", "l");

await pick(note.key);
await turnTo(0);
await saved();
check("set to 0, the file says nothing of turning", !("rotate" in ((await file()).find((a) => a.key === note.key) || {})));
check("no page errors", !errors.length, errors.join(" | "));
await browser.close();
process.exit(failed ? 1 : 0);
