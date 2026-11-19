// Does a square line's stretch move by hand, as V16 draws it? On a new
// diagram, two shapes joined by a square line: picked, it has a handle on
// each of its three stretches, which says what it is for beside it under
// the pointer; the middle one carried across itself, the
// line keeps the turns it then has, in the file and the picture; the box at
// its end carried down, the line stays square; Remove the bends gives it back
// its own turns, and one Undo keeps them again.
//
//   node 80_APP/tools/dev/stretch_probe.mjs out/ URL
//
// It makes a diagram, so run it on a copy of the repository. Exits 1 if a
// step does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node stretch_probe.mjs OUT URL");
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
  await pause(500);
  await page.waitForFunction(() => /^(saved|failed)$/.test(window.TerraneApp.Canvas.cv.status), { timeout: 15000 });
}
const item = (k) => page.evaluate((key) => window.TerraneApp.Canvas.engine.item(key), k);
const handles = () => page.evaluate(() => Array.from(document.querySelectorAll(".mg-surface .mg-stretch")).map((h) => {
  const b = h.getBoundingClientRect();
  return { x: b.left + b.width / 2, y: b.top + b.height / 2, upright: h.classList.contains("is-upright") };
}));
// The line's points in the picture, and whether each piece of it is square.
async function picture() {
  const svg = await page.evaluate(() => fetch("/api/svg?view=" + window.TerraneApp.Canvas.cv.id).then((r) => r.text()));
  const d = (svg.match(/<g class="own" data-key="line-1" data-role="line">\s*<path d="([^"]+)"/) || [])[1] || "";
  const pts = (d.match(/-?[\d.]+ -?[\d.]+/g) || []).map((p) => p.split(" ").map(Number));
  return { d, pts, square: pts.length > 1 && pts.every((p, i) => i === 0 || p[0] === pts[i - 1][0] || p[1] === pts[i - 1][1]) };
}

const keys = await page.evaluate(() => {
  const e = window.TerraneApp.Canvas.engine;
  const a = e.add({ role: "shape", shape: "rounded", label: "Checkout web", box: { x: 80, y: 120, w: 150, h: 64 } });
  const b = e.add({ role: "shape", shape: "rounded", label: "Card ledger", box: { x: 420, y: 380, w: 150, h: 64 } });
  const l = e.add({ role: "line", from: a, to: b, route: "square" });
  e.select([]);
  return { a, b, l };
});
await saved();
await page.evaluate((k) => window.TerraneApp.Canvas.picked([], [k]), keys.l);
await pause(500);
let hs = await handles();
// Three stretches, the middle one across the other two, whichever way the
// line runs between these two boxes.
check("a square line picked has a handle on each of its three stretches", hs.length === 3 &&
  hs[0].upright === hs[2].upright && hs[1].upright !== hs[0].upright, JSON.stringify(hs));
check("and its panel says how to move them", /Drag a stretch to move it/.test(await page.evaluate(() =>
  document.getElementById("cvDetails").innerText)));

// The middle stretch carried 60 across itself: right if it stands, down
// if it lies.
const mid = hs[1], axis = mid.upright ? 0 : 1, before = (await item(keys.l)).via;
await page.mouse.move(mid.x, mid.y);
await pause(200);
const tip = await page.evaluate(() => {
  const t = document.getElementById("cvTip"), b = t.getBoundingClientRect();
  return { shown: !t.hidden, text: t.textContent, left: b.left, middle: b.top + b.height / 2 };
});
check("under the pointer, a handle says what it is for beside it", tip.shown && tip.text === "Drag a stretch to move it" &&
  tip.left > mid.x && tip.left - mid.x < 24 && Math.abs(tip.middle - mid.y) < 3, JSON.stringify(tip));
await page.mouse.down();
check("and says no more once it is taken", await page.evaluate(() => document.getElementById("cvTip").hidden));
for (let i = 1; i <= 10; i += 1) await page.mouse.move(mid.x + (axis ? 0 : 6 * i), mid.y + (axis ? 6 * i : 0));
await page.mouse.up();
await pause(600);
let l = await item(keys.l);
const at = Array.isArray(l.via) && l.via.length === 2 && l.via[0][axis] === l.via[1][axis] ? l.via[0][axis] : null;
check("carried across itself, it keeps the two turns it then has", !before && at !== null, JSON.stringify(l.via));
hs = await handles();
check("and its handle is where the stretch now is", hs.length === 3 &&
  Math.abs((axis ? hs[1].y - mid.y : hs[1].x - mid.x) - 60) < 2, JSON.stringify(hs));
await saved();
let pic = await picture();
check("the picture runs it there, square", pic.square && pic.pts.some((p) => p[axis] === at), pic.d);
check("and the panel can take the bends out", /Remove the bends/.test(await page.evaluate(() => document.getElementById("cvDetails").innerText)));

// The box at its end carried down: the line stays square.
await page.evaluate((k) => window.TerraneApp.Canvas.engine.update(k, { at: [420, 470] }), keys.b);
await saved();
pic = await picture();
check("its box carried down, it stays square through its turns", pic.square && pic.pts.some((p) => p[axis] === at), pic.d);

// Remove the bends, and one Undo.
await page.evaluate((k) => window.TerraneApp.Canvas.picked([], [k]), keys.l);
await pause(400);
await page.evaluate(() => Array.from(document.querySelectorAll("#cvDetails button")).find((b) => b.innerText.trim() === "Remove the bends").click());
await pause(500);
check("Remove the bends gives it back its own turns", !(await item(keys.l)).via);
await page.screenshot({ path: OUT + "/stretch.png" });
await page.focus("#cy");
await page.keyboard.down("Control");
await page.keyboard.press("z");
await page.keyboard.up("Control");
await pause(500);
check("one Undo keeps them again", ((await item(keys.l)).via || []).length === 2, JSON.stringify((await item(keys.l)).via));

// The line given words at its middle: no handle sits over them.
await page.evaluate((k) => window.TerraneApp.Canvas.engine.update(k, { label: "reads balances" }), keys.l);
await page.evaluate((k) => window.TerraneApp.Canvas.picked([], [k]), keys.l);
await pause(500);
const over = await page.evaluate(() => {
  const words = Array.from(document.querySelectorAll(".mg-surface *")).filter((e) => e.textContent === "reads balances")
    // The words' own box: maxGraph's groups and its foreignObject hold
    // them too, as tall as the sheet, and a holder a pixel wide.
    .map((e) => e.getBoundingClientRect()).filter((b) => b.width > 8 && b.height > 6 && b.height < 40)
    .sort((a, b) => a.width * a.height - b.width * b.height)[0];
  if (!words) return { words: null };
  const hs = Array.from(document.querySelectorAll(".mg-surface .mg-stretch")).map((h) => h.getBoundingClientRect());
  return { words: [words.left, words.top, words.right, words.bottom], handles: hs.length,
    over: hs.filter((h) => h.left < words.right && h.right > words.left && h.top < words.bottom && h.bottom > words.top).length };
});
check("with words at its middle, no handle sits over them", over.words && over.handles === 3 && over.over === 0, JSON.stringify(over));
check("no page errors", errors.length === 0, errors.join(" / "));
await browser.close();
process.exit(failed ? 1 : 0);
