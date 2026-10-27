// Does a square line go around the boxes in its way? On a new diagram: two
// shapes, a note between them and a square line from one shape to the
// other: no piece of the line runs through the note, and its turns are the
// ones the engine's own picture draws; the note moved out of the way, the
// line takes its plain turns again, straight across; one Undo puts the
// note back and the line goes around it again. Then on lending-onboarding
// (arrange_probe.mjs makes it), a square line between two notes either
// side of the Lending portal goes around the portal's box.
//
//   node 80_APP/tools/dev/around_probe.mjs out/ URL
//
// It makes a diagram and draws on one, so run it on a copy of the
// repository. Exits 1 if a step does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node around_probe.mjs OUT URL");
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
    localStorage.removeItem("aac.canvas.snap");
  });
  await page.goto(URL + "/#" + hash, { waitUntil: "networkidle0", timeout: 60000 });
  await page.waitForFunction(() => window.TerraneApp.Canvas.engine && window.TerraneApp.Canvas.engine.live(), { timeout: 30000 });
  await settled(page);
  await pause(700);
  await page.bringToFront();
  return page;
}
// Whether a run across or down goes through a box's inside.
function cuts(p, q, o) {
  if (Math.abs(p[0] - q[0]) < 1e-6) {
    return o[0] < p[0] && p[0] < o[2] && Math.max(Math.min(p[1], q[1]), o[1]) < Math.min(Math.max(p[1], q[1]), o[3]);
  }
  return o[1] < p[1] && p[1] < o[3] && Math.max(Math.min(p[0], q[0]), o[0]) < Math.min(Math.max(p[0], q[0]), o[2]);
}
const through = (pts, o) => pts.some((p, i) => i > 0 && cuts(pts[i - 1], p, o));
const square = (pts) => pts.every((p, i) => i === 0 || Math.abs(p[0] - pts[i - 1][0]) < 0.01 || Math.abs(p[1] - pts[i - 1][1]) < 0.01);
const fmt = (pts) => pts.map((p) => p.map((v) => Math.round(v * 10) / 10).join(",")).join(" ");
async function saved(page) {
  await pause(400);
  await page.waitForFunction(() => /^(saved|failed)$/.test(window.TerraneApp.Canvas.cv.status), { timeout: 15000 });
}

const page = await open("draw");
const made = await page.evaluate(() => {
  const e = window.TerraneApp.Canvas.engine;
  const a = e.add({ role: "shape", shape: "rounded", label: "From", box: { x: 100, y: 200, w: 120, h: 64 } });
  const b = e.add({ role: "shape", shape: "rounded", label: "To", box: { x: 520, y: 200, w: 120, h: 64 } });
  const n = e.add({ role: "note", label: "In the way", box: { x: 300, y: 170, w: 100, h: 130 } });
  const l = e.add({ role: "line", from: a, to: b, route: "square" });
  e.select([]);
  return { a, b, n, l };
});
await pause(600);
const NOTE = [300, 170, 400, 300];
const route = () => page.evaluate((k) => window.TerraneApp.Canvas.engine.route(k), made.l);
const around = await route();
// The plain line would run straight across through the note.
check("a square line goes around the note in its way, squarely", !!around && around.length >= 4 && !through(around, NOTE)
  && square(around) && around.some((p) => Math.abs(p[1] - 232) > 1), around && fmt(around));
await saved(page);
const id = await page.evaluate(() => window.TerraneApp.Canvas.cv.id);
const svg = await (await fetch(URL + "/api/svg?view=" + encodeURIComponent(id))).text();
const d = (svg.match(new RegExp('data-key="' + made.l + '" data-role="line">\\s*<path d="([^"]+)"')) || [])[1] || "";
const drawn = (d.match(/-?[\d.]+ -?[\d.]+/g) || []).map((s) => s.split(" ").map(Number));
const inner = (pts) => pts.slice(1, -1);
const same = drawn.length === around.length
  && inner(drawn).every((p, i) => Math.abs(p[0] - inner(around)[i][0]) < 0.5 && Math.abs(p[1] - inner(around)[i][1]) < 0.5);
check("and turns where the engine's own picture turns it", same, fmt(drawn) + " for " + fmt(around));
await page.screenshot({ path: `${OUT}/around.png` });
await page.evaluate((k) => window.TerraneApp.Canvas.engine.nudge([k], 0, 300), made.n);
await pause(600);
const clear = await route();
check("the note moved away, the line takes its plain turns, straight across", !!clear && clear.every((p) => Math.abs(p[1] - 232) < 0.01),
  clear && fmt(clear));
await page.keyboard.down("Control");
await page.keyboard.press("z");
await page.keyboard.up("Control");
await pause(600);
const back = await route();
check("one Undo puts the note back, and the line goes around it again", !!back && fmt(back) === fmt(around), back && fmt(back));
await page.close();

if (!(await fetch(URL + "/api/view?id=lending-onboarding")).ok) {
  console.log("skip  no lending-onboarding here (arrange_probe.mjs makes it)");
} else {
  const lend = await open("draw=lending-onboarding");
  const portal = await lend.evaluate(() => {
    const n = document.getElementById("cy")._cyreg.cy.getElementById("SYS-LENDING-PORTAL"), p = n.position();
    return [p.x - n.width() / 2, p.y - n.height() / 2, p.x + n.width() / 2, p.y + n.height() / 2];
  });
  const line = await lend.evaluate((o) => {
    const e = window.TerraneApp.Canvas.engine, cy = (o[1] + o[3]) / 2;
    const left = e.add({ role: "note", label: "Before", box: { x: o[0] - 170, y: cy - 30, w: 110, h: 60 } });
    const right = e.add({ role: "note", label: "After", box: { x: o[2] + 60, y: cy - 30, w: 110, h: 60 } });
    // Level with the portal, so the plain line runs straight through it.
    const l = e.add({ role: "line", from: left, to: right, route: "square" });
    e.select([]);
    return l;
  }, portal);
  await pause(700);
  const pts = await lend.evaluate((k) => window.TerraneApp.Canvas.engine.route(k), line);
  check("on lending-onboarding a square line goes around the Lending portal", !!pts && pts.length >= 4 && !through(pts, portal)
    && square(pts),
    pts && fmt(pts) + " round " + fmt([portal.slice(0, 2), portal.slice(2)]));
  await lend.screenshot({ path: `${OUT}/around-lending.png` });
  await lend.close();
}
check("no page errors", !errors.length, errors.join(" | "));
await browser.close();
process.exit(failed ? 1 : 0);
