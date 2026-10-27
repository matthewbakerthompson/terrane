// Does a line's end stay where it is put on a box? With a real pointer, on
// a new diagram: two shapes and a straight line between them; the line
// picked, its end carried over the second shape shows the points it can be
// held at, and let go on the top middle it is held there, which the file
// keeps as to_at [0.5, 0]; made square, it comes into that point from
// above, square, as the engine's own picture draws it; the shape moved,
// the end moves with it; carried off the shape to empty sheet the end
// stays at a point there, held nowhere; one Undo puts it back on the box.
//
//   node 80_APP/tools/dev/pins_probe.mjs out/ URL
//
// It makes a diagram, so run it on a copy of the repository. Exits 1 if a
// step does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node pins_probe.mjs OUT URL");
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
page.on("requestfailed", (r) => errors.push("request failed: " + r.url()));
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
const fmt = (pts) => pts.map((p) => p.map((v) => Math.round(v * 10) / 10).join(",")).join(" ");
const made = await page.evaluate(() => {
  const e = window.TerraneApp.Canvas.engine;
  const a = e.add({ role: "shape", shape: "rounded", label: "From", box: { x: 100, y: 200, w: 120, h: 64 } });
  const b = e.add({ role: "shape", shape: "rounded", label: "To", box: { x: 520, y: 300, w: 120, h: 64 } });
  const l = e.add({ role: "line", from: a, to: b });
  e.select([l]);
  return { a, b, l };
});
await pause(500);
const item = () => page.evaluate((k) => (window.TerraneApp.Canvas.cv.data.annotations || []).find((x) => x.key === k), made.l);
const route = () => page.evaluate((k) => window.TerraneApp.Canvas.engine.route(k), made.l);
// The drawing's units on the screen, read off the first shape, whose box
// is known: the sheet is moved and scaled to fit what is on it.
const map = await page.evaluate((k) => {
  const r = document.querySelector(".mg-surface").getBoundingClientRect(), b = window.TerraneApp.Canvas.engine.ownBoxes()[k];
  const z = b.w / 120;
  return { z, x: r.left + b.x - 100 * z, y: r.top + b.y - 200 * z };
}, made.a);
const scr = (p) => ({ x: map.x + p[0] * map.z, y: map.y + p[1] * map.z });
// The end's handle: the one with the terminal's pointer nearest the end.
const end = (await route()).slice(-1)[0];
const handle = await page.evaluate((e) => {
  const hs = Array.from(document.querySelectorAll(".mg-surface svg *")).filter((n) => n.style && n.style.cursor === "pointer")
    .map((n) => { const r = n.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2, w: r.width }; })
    .filter((r) => r.w > 0);
  hs.sort((p, q) => Math.hypot(p.x - e.x, p.y - e.y) - Math.hypot(q.x - e.x, q.y - e.y));
  return hs[0] || null;
}, scr(end));
check("the line picked shows its end's handle", !!handle && Math.hypot(handle.x - scr(end).x, handle.y - scr(end).y) < 3,
  handle && Math.round(handle.x - scr(end).x) + "," + Math.round(handle.y - scr(end).y));
const top = scr([580, 300]);
await page.mouse.move(handle.x, handle.y);
await page.mouse.down();
for (let i = 1; i <= 16; i += 1) await page.mouse.move(handle.x + (top.x - handle.x) * i / 16, handle.y + (top.y + 18 - handle.y) * i / 16);
await pause(200);
const points = await page.evaluate(() => Array.from(document.querySelectorAll(".mg-surface svg image")).filter((n) => /circle/.test(decodeURIComponent(n.getAttribute("href") || n.getAttribute("xlink:href") || ""))).length);
check("carried over the shape, the points it can be held at show", points === 12, points + " points");
await page.mouse.move(top.x, top.y + 1);
await pause(150);
await page.mouse.move(top.x, top.y);
await pause(150);
await page.mouse.up();
await pause(600);
let it = await item();
check("let go on the top middle, it is held there, the file says to_at [0.5, 0]", it.to === made.b
  && JSON.stringify(it.to_at) === "[0.5,0]", JSON.stringify(it));
let r = await route();
check("and the line ends there", Math.abs(r.slice(-1)[0][0] - 580) < 0.5 && Math.abs(r.slice(-1)[0][1] - 300) < 0.5, fmt(r));
await page.evaluate((k) => window.TerraneApp.Canvas.picked([], [k]), made.l);
await pause(300);
await page.evaluate(() => Array.from(document.querySelectorAll("#cvDetails button")).find((x) => x.innerText.trim() === "Square").click());
await pause(600);
r = await route();
const last = r.slice(-2);
check("made square, it comes into that point from above, square", Math.abs(last[0][0] - 580) < 0.5
  && Math.abs(last[0][1] - 290) < 0.5 && r.every((p, i) => i === 0 || Math.abs(p[0] - r[i - 1][0]) < 0.01
  || Math.abs(p[1] - r[i - 1][1]) < 0.01), fmt(r));
await pause(500);
await page.waitForFunction(() => /^(saved|failed)$/.test(window.TerraneApp.Canvas.cv.status), { timeout: 15000 });
const id = await page.evaluate(() => window.TerraneApp.Canvas.cv.id);
const svg = await (await fetch(URL + "/api/svg?view=" + encodeURIComponent(id))).text();
const d = (svg.match(new RegExp('data-key="' + made.l + '" data-role="line">\\s*<path d="([^"]+)"')) || [])[1] || "";
const drawn = (d.match(/-?[\d.]+ -?[\d.]+/g) || []).map((s) => s.split(" ").map(Number));
const inner = (pts) => pts.slice(1, -1);
check("as the engine's own picture draws it", drawn.length === r.length
  && inner(drawn).every((p, i) => Math.abs(p[0] - inner(r)[i][0]) < 0.5 && Math.abs(p[1] - inner(r)[i][1]) < 0.5),
  fmt(drawn) + " for " + fmt(r));
await page.screenshot({ path: `${OUT}/pins.png` });
await page.evaluate((k) => window.TerraneApp.Canvas.engine.nudge([k], 40, 60), made.b);
await pause(600);
r = await route();
check("the shape moved, the end moves with it", Math.abs(r.slice(-1)[0][0] - 620) < 0.5 && Math.abs(r.slice(-1)[0][1] - 360) < 0.5,
  fmt(r));
// Carried off the shape to empty sheet.
await page.evaluate((k) => window.TerraneApp.Canvas.engine.select([k]), made.l);
await pause(300);
const now = scr(r.slice(-1)[0]);
await page.mouse.move(now.x, now.y);
await page.mouse.down();
for (let i = 1; i <= 12; i += 1) await page.mouse.move(now.x + 160 * i / 12, now.y + 140 * i / 12);
await page.mouse.up();
await pause(600);
it = await item();
check("carried off to empty sheet, the end stays at a point there, held nowhere", Array.isArray(it.to) && !it.to_at,
  JSON.stringify(it));
await page.keyboard.down("Control");
await page.keyboard.press("z");
await page.keyboard.up("Control");
await pause(600);
it = await item();
check("one Undo puts it back on the shape, held at its top", it.to === made.b && JSON.stringify(it.to_at) === "[0.5,0]",
  JSON.stringify(it));
check("no page errors", !errors.length, errors.join(" | "));
await browser.close();
process.exit(failed ? 1 : 0);
