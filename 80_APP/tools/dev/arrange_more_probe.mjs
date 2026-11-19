// Does what M2 left work? On a new diagram with three shapes of its own:
// two grouped and turned right a quarter as one, each turned by as much and
// carried round their middle, and one Undo puts them back; a shape's place
// typed in Arrange puts its corner there, as the file then says; a style
// saved for every diagram is kept in model.yaml, offered on another
// diagram, painted from there, and removed.
//
//   node 80_APP/tools/dev/arrange_more_probe.mjs out/ URL
//
// It makes diagrams and writes model.yaml, so run it on a copy of the
// repository. Exits 1 if a step does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node arrange_more_probe.mjs OUT URL");
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
async function open(hash) {
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  await page.evaluateOnNewDocument(() => {
    localStorage.setItem("aac.rail.shut", "1");
    localStorage.setItem("aac.insp.shut", "0");
    localStorage.setItem("aac.tour", "taken");
  });
  await page.goto(URL + "/" + hash, { waitUntil: "networkidle0", timeout: 60000 });
  await page.waitForFunction(() => window.TerraneApp.Canvas.engine && window.TerraneApp.Canvas.engine.live(), { timeout: 30000 });
  await settled(page);
  await pause(700);
  await page.bringToFront();
  return page;
}
async function saved(page) {
  await pause(500);
  await page.waitForFunction(() => /^(saved|failed)$/.test(window.TerraneApp.Canvas.cv.status), { timeout: 15000 });
}
const item = (page, k) => page.evaluate((key) => window.TerraneApp.Canvas.engine.item(key), k);
const middle = (page, k) => page.evaluate((key) => {
  const b = window.TerraneApp.Canvas.engine.boxOf(key);
  return [Math.round((b.x1 + b.x2) / 2), Math.round((b.y1 + b.y2) / 2)];
}, k);
async function button(page, words) {
  return (await page.evaluateHandle((w) => Array.from(document.querySelectorAll("#cvDetails button"))
    .find((b) => b.innerText.trim() === w) || null, words)).asElement();
}

const page = await open("#draw");
const keys = await page.evaluate(() => {
  const e = window.TerraneApp.Canvas.engine;
  const add = (label, x, y) => e.add({ role: "shape", shape: "rounded", label: label, box: { x: x, y: y, w: 120, h: 60 } });
  const out = { a: add("Gateway", 100, 200), b: add("Ledger", 300, 200), c: add("Fraud check", 600, 400) };
  e.select([]);
  return out;
});
await saved(page);

// Two grouped, then turned right a quarter as one.
await page.evaluate((k) => window.TerraneApp.Canvas.picked([], [k.a, k.b]), keys);
await pause(300);
await (await button(page, "Group them")).click();
await pause(500);
const before = [await middle(page, keys.a), await middle(page, keys.b)];
check("a group picked offers to turn it", !!(await button(page, "Turn right")));
await (await button(page, "Turn right")).click();
await pause(500);
const after = [await middle(page, keys.a), await middle(page, keys.b)];
// Their middle was (260, 230): (160, 230) and (360, 230) go to (260, 130)
// and (260, 330).
check("turned right a quarter, each is carried round their middle",
  JSON.stringify(after) === JSON.stringify([[260, 130], [260, 330]]), JSON.stringify([before, after]));
check("and each is turned by as much", (await item(page, keys.a)).rotate === 90 && (await item(page, keys.b)).rotate === 90,
  JSON.stringify([(await item(page, keys.a)).rotate, (await item(page, keys.b)).rotate]));
await page.focus("#cy");
await page.keyboard.down("Control");
await page.keyboard.press("z");
await page.keyboard.up("Control");
await pause(500);
check("one Undo puts them back", JSON.stringify([await middle(page, keys.a), await middle(page, keys.b)]) ===
  JSON.stringify(before) && !(await item(page, keys.a)).rotate);

// A place typed in Arrange.
await page.evaluate((k) => { window.TerraneApp.Canvas.ownTab = "arrange"; window.TerraneApp.Canvas.picked([], [k]); }, keys.c);
await pause(400);
const x = await page.$("#cvDetails .cv-x"), y = await page.$("#cvDetails .cv-y");
check("Arrange says where it sits", !!x && !!y && await page.evaluate(() =>
  document.querySelector("#cvDetails .cv-x").value === "600" && document.querySelector("#cvDetails .cv-y").value === "400"));
await x.click({ count: 3 });
await page.keyboard.down("Control");
await page.keyboard.press("a");
await page.keyboard.up("Control");
await page.keyboard.type("320");
await y.click({ count: 3 });
await page.keyboard.down("Control");
await page.keyboard.press("a");
await page.keyboard.up("Control");
await page.keyboard.type("440");
await page.keyboard.press("Tab");
await pause(500);
check("a place typed puts its corner there", JSON.stringify((await item(page, keys.c)).at) === JSON.stringify([320, 440]),
  JSON.stringify((await item(page, keys.c)).at));
await page.evaluate(() => { window.TerraneApp.Canvas.ownTab = "style"; });

// A style saved for every diagram.
await page.evaluate((k) => window.TerraneApp.Canvas.engine.update(k, { look: { fill: "rose", weight: "l" } }), keys.c);
await page.evaluate((k) => window.TerraneApp.Canvas.picked([], [k]), keys.c);
await pause(400);
await page.evaluate(() => Array.from(document.querySelectorAll("#cvDetails button")).find((b) => b.innerText.trim() === "Save this as a style").click());
await pause(300);
await page.evaluate(() => Array.from(document.querySelectorAll("#cvDetails .cv-style-form .cv-seg-b")).find((b) => b.innerText.trim() === "Every diagram").click());
await page.type("#cvDetails .cv-style-form input", "Hot path");
await page.keyboard.press("Enter");
await pause(800);
const parts = await page.evaluate(() => fetch("/api/canvas/parts").then((r) => r.json()));
check("a style saved for every diagram is kept for the estate", (parts.styles || []).some((s) => s.name === "Hot path" &&
  s.look.fill === "rose" && s.look.weight === "l"), JSON.stringify(parts.styles));
check("and not in this diagram's file", !(await page.evaluate(() => window.TerraneApp.Canvas.cv.data.saved_styles)));
await saved(page);
await page.close();

const other = await open("#draw");
const shape = await other.evaluate(() => {
  const k = window.TerraneApp.Canvas.engine.add({ role: "shape", shape: "rounded", label: "Elsewhere", box: { x: 200, y: 200, w: 120, h: 60 } });
  window.TerraneApp.Canvas.picked([], [k]);
  return k;
});
await pause(500);
const chip = await other.evaluateHandle(() => Array.from(document.querySelectorAll("#cvDetails .cv-style-wrap.is-estate .cv-style"))
  .find((b) => b.innerText.trim() === "Hot path") || null);
check("another diagram offers it", !!chip.asElement());
if (chip.asElement()) await chip.asElement().click();
await pause(400);
check("and paints it", (await item(other, shape)).look && (await item(other, shape)).look.fill === "rose");
await other.screenshot({ path: OUT + "/estate-style.png" });
await other.evaluate(() => document.querySelector('#cvDetails .cv-style-wrap.is-estate .cv-style-x').click());
await pause(800);
const left = await other.evaluate(() => fetch("/api/canvas/parts").then((r) => r.json()));
check("removed, it is no longer kept", !(left.styles || []).length, JSON.stringify(left.styles));
check("no page errors", errors.length === 0, errors.join(" / "));
await browser.close();
process.exit(failed ? 1 : 0);
