// Does a straight line bend where it is dragged? With a real pointer, on a
// new diagram: two shapes and a straight line between them; the line
// picked shows a handle halfway along it, which carried 80 down bends the
// line there; the diagram's file keeps the bend under `via`, and the
// engine's own picture draws the line through it; one Undo straightens it
// and Redo bends it again; the panel's Remove the bend takes it out; bent
// again and made square, the bend goes, since a square line turns by
// itself.
//
//   node 80_APP/tools/dev/bends_probe.mjs out/ URL
//
// It makes a diagram, so run it on a copy of the repository. Exits 1 if a
// step does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node bends_probe.mjs OUT URL");
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
  localStorage.removeItem("aac.canvas.snap");
});
await page.goto(URL + "/#draw", { waitUntil: "networkidle0", timeout: 60000 });
await page.waitForFunction(() => window.TerraneApp.Canvas.engine && window.TerraneApp.Canvas.engine.live(), { timeout: 30000 });
await settled(page);
await pause(700);
await page.bringToFront();
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
const line = () => page.evaluate((k) => (window.TerraneApp.Canvas.cv.data.annotations || []).find((a) => a.key === k), made.line);
const made = await page.evaluate(() => {
  const e = window.TerraneApp.Canvas.engine;
  const a = e.add({ role: "shape", shape: "rounded", label: "From", box: { x: 120, y: 200, w: 120, h: 64 } });
  const b = e.add({ role: "shape", shape: "rounded", label: "To", box: { x: 520, y: 200, w: 120, h: 64 } });
  const l = e.add({ role: "line", from: a, to: b });
  e.select([l]);
  return { a, b, line: l };
});
await pause(500);
const handle = await page.evaluate(() => {
  const h = Array.from(document.querySelectorAll(".mg-surface svg *")).filter((n) => n.style && n.style.cursor === "crosshair")
    .map((n) => { const r = n.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2, w: r.width }; })
    .filter((r) => r.w > 0);
  return h;
});
check("the line picked shows a handle halfway along it", handle.length === 1, JSON.stringify(handle));
const before = await line();
if (handle.length) {
  const h = handle[0];
  await page.mouse.move(h.x, h.y);
  await page.mouse.down();
  for (let i = 1; i <= 12; i += 1) await page.mouse.move(h.x, h.y + 80 * i / 12);
  await page.mouse.up();
  await pause(600);
}
let bent = await line();
check("carried 80 down, it bends the line there", !before.via && Array.isArray(bent.via) && bent.via.length === 1,
  JSON.stringify(bent.via));
await saved();
const id = await page.evaluate(() => window.TerraneApp.Canvas.cv.id);
const file = await page.evaluate((v) => fetch("/api/view?id=" + encodeURIComponent(v)).then((r) => r.json()), id);
const kept = ((file.data && file.data.annotations) || []).find((a) => a.key === made.line);
check("the diagram's file keeps the bend under via", !!kept && JSON.stringify(kept.via) === JSON.stringify(bent.via),
  kept && JSON.stringify(kept.via));
const svg = await (await fetch(URL + "/api/svg?view=" + encodeURIComponent(id))).text();
const path = (svg.match(new RegExp('data-key="' + made.line + '" data-role="line">\\s*<path d="([^"]+)"')) || [])[1] || "";
check("and the engine's own picture draws the line through it", (path.match(/L/g) || []).length === 2, path);
await page.screenshot({ path: `${OUT}/bends.png` });
await keys("Control", "z");
check("one Undo straightens it", !(await line()).via);
await keys("Control", "y");
check("and Redo bends it again", Array.isArray((await line()).via));
await page.evaluate((k) => window.TerraneApp.Canvas.picked([], [k]), made.line);
await pause(300);
const removed = await page.evaluate(() => {
  const b = Array.from(document.querySelectorAll("#cvDetails button")).find((x) => /Remove the bend/.test(x.innerText));
  if (!b) return false;
  b.click();
  return true;
});
await pause(400);
check("the panel's Remove the bend takes it out", removed && !(await line()).via);
await keys("Control", "z");
await page.evaluate((k) => window.TerraneApp.Canvas.picked([], [k]), made.line);
await pause(300);
await page.evaluate(() => Array.from(document.querySelectorAll("#cvDetails button")).find((x) => x.innerText.trim() === "Square").click());
await pause(400);
bent = await line();
check("bent again and made square, the bend goes", bent.route === "square" && !bent.via, JSON.stringify(bent));
check("no page errors", !errors.length, errors.join(" | "));
await browser.close();
process.exit(failed ? 1 : 0);
