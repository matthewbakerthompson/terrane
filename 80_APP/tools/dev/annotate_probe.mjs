// Does the canvas draw from scratch? On a new diagram's empty sheet, with a
// real pointer: a frame dragged out, a note clicked in and typed in, a
// diamond from the Shapes menu, words with the Text tool, and a line from
// the note to the diamond. Then the note restyled from its panel, moved,
// undone and redone, deleted and brought back; the page opened again on
// the diagram, the diagram opened as a diagram (read only), and the engine's
// own picture of it (/api/svg), each holding the same shapes.
//
//   node 80_APP/tools/dev/annotate_probe.mjs out/ URL
//
// It makes a diagram, so run it on a copy of the repository, never on the
// one you commit from. Exits 1 if a step does not do what it says.
import { mkdir, writeFile } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node annotate_probe.mjs OUT URL");
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
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  await page.evaluateOnNewDocument(() => {
    localStorage.setItem("aac.rail.shut", "1");
    localStorage.setItem("aac.insp.shut", "0");
    localStorage.setItem("aac.tour", "taken");
  });
  await page.goto(URL + "/#" + hash, { waitUntil: "networkidle0", timeout: 60000 });
  await page.waitForSelector(".mg-surface.takes-pointer svg", { timeout: 30000 });
  await pause(400);
  return page;
}

const own = (page) => page.evaluate(() => (window.TerraneApp.Canvas.cv.data.annotations || []).map((a) => Object.assign({}, a)));
const drawn = (page) => page.evaluate(() => window.TerraneApp.Canvas.engine.ownBoxes() || {});
async function sheetAt(page, fx, fy) {
  const r = await page.evaluate(() => { const b = document.querySelector(".mg-surface").getBoundingClientRect(); return { x: b.left, y: b.top, w: b.width, h: b.height }; });
  return { x: r.x + r.w * fx, y: r.y + r.h * fy };
}
async function drag(page, a, b) {
  await page.mouse.move(a.x, a.y);
  await page.mouse.down();
  for (let i = 1; i <= 12; i += 1) await page.mouse.move(a.x + (b.x - a.x) * i / 12, a.y + (b.y - a.y) * i / 12);
  await page.mouse.up();
  await pause(250);
}
// The Line tool, by its menu: a route chosen arms it.
async function lineTool(page, route = "Straight") {
  await page.click("#cvLine");
  await page.waitForSelector("#cvShapeMenu.is-lines:not([hidden])");
  const at = await page.$$eval(".cv-shape-item", (bs, r) => bs.findIndex((b) => b.textContent.trim() === r), route);
  await (await page.$$(".cv-shape-item"))[at].click();
}
// The save that is under way, not the one before it: a refused save once
// passed here on the last one's "Saved as you draw".
async function saved(page) {
  await pause(400);
  await page.waitForFunction(() => /^(saved|failed)$/.test(window.TerraneApp.Canvas.cv.status), { timeout: 15000 });
  const status = await page.evaluate(() => window.TerraneApp.Canvas.cv.status + " " + ((document.querySelector("#viewMeta .cv-status") || {}).title || ""));
  if (!/^saved/.test(status)) check("saved", false, status);
}

// ---- drawn from scratch
const page = await open("draw");
check("a new diagram's sheet takes the tools", await page.evaluate(() => !document.getElementById("cvShapes").hidden
  && !document.getElementById("cvTools").classList.contains("no-own")));

await page.click("#cvFrame");
const f1 = await sheetAt(page, 0.18, 0.2), f2 = await sheetAt(page, 0.62, 0.78);
await drag(page, f1, f2);
let list = await own(page);
check("a frame dragged out", list.length === 1 && list[0].role === "frame", JSON.stringify(list[0]));

await page.click("#cvNote");
const n = await sheetAt(page, 0.3, 0.42);
await page.mouse.click(n.x, n.y);
await page.waitForSelector(".mg-edit", { timeout: 5000 });
await page.keyboard.type("Guardrails: every account is denied the regions but eu-west-2");
await page.keyboard.down("Control");
await page.keyboard.press("Enter");
await page.keyboard.up("Control");
await pause(300);
list = await own(page);
const note = list.find((a) => a.role === "note");
check("a note clicked in, and typed in where it is", !!note && /Guardrails/.test(note.label || ""), note && note.label);
check("drawn inside the frame, it sits in it", !!note && (note.in || []).join() === list[0].key, note && JSON.stringify(note.in));

await page.click("#cvShapes");
await page.waitForSelector("#cvShapeMenu:not([hidden])");
const diamond = await page.$$eval(".cv-shape-item", (bs) => bs.findIndex((b) => /Diamond/.test(b.textContent)));
await (await page.$$(".cv-shape-item"))[diamond].click();
const d = await sheetAt(page, 0.78, 0.4);
await page.mouse.click(d.x, d.y);
await pause(300);
list = await own(page);
const shape = list.find((a) => a.role === "shape");
check("a diamond from the Shapes menu", !!shape && shape.shape === "diamond", shape && JSON.stringify(shape));
check("the tool is Select again after one shape", await page.evaluate(() => window.TerraneApp.Canvas.cv.tool === "select"));
check("and what it drew is picked, its panel beside it", await page.evaluate((k) => {
  const sel = window.TerraneApp.Canvas.cv.sel;
  return !!sel && sel.kind === "own" && sel.keys.join() === k && /Diamond/.test(document.querySelector("#cvDetails .cv-h").textContent);
}, shape && shape.key));

await page.click("#cvText");
const t = await sheetAt(page, 0.3, 0.88);
await page.mouse.click(t.x, t.y);
await page.waitForSelector(".mg-edit", { timeout: 5000 });
await page.keyboard.type("For the platform review");
await page.keyboard.down("Control");
await page.keyboard.press("Enter");
await page.keyboard.up("Control");
await pause(300);

await lineTool(page);
await drag(page, await sheetAt(page, 0.3, 0.42), await sheetAt(page, 0.78, 0.4));
list = await own(page);
const line = list.find((a) => a.role === "line");
check("a line from the note to the diamond, joined to both", !!line && line.from === note.key && line.to === shape.key,
  line && JSON.stringify(line));
await saved(page);
const id = await page.evaluate(() => window.TerraneApp.Canvas.cv.id);
check("saved as a diagram of its own", !!id, id);
await page.mouse.click((await sheetAt(page, 0.95, 0.1)).x, (await sheetAt(page, 0.95, 0.1)).y);
await pause(200);
await page.screenshot({ path: `${OUT}/annotate-drawn.png` });

// ---- the note's panel, a move, Undo and Redo, Delete and back
const nb = (await drawn(page))[note.key];
const sr = await page.evaluate(() => { const b = document.querySelector(".mg-surface").getBoundingClientRect(); return { x: b.left, y: b.top }; });
// Its middle: near an edge, a press is on a handle and resizes it.
const noteAt = { x: sr.x + nb.x + nb.w / 2, y: sr.y + nb.y + nb.h / 2 };
await page.mouse.click(noteAt.x, noteAt.y);
await pause(300);
check("a press on the note selects it, and its panel says so",
  /Note/.test(await page.$eval("#cvDetails .cv-h", (h) => h.textContent)));
await page.click('#cvDetails .cv-swatch[aria-label="Mint"]');
await page.click('#cvDetails .cv-seg-b:nth-child(2)');
await pause(300);
list = await own(page);
let look = (list.find((a) => a.key === note.key) || {}).look || {};
check("restyled from the panel: mint, dashed", look.fill === "mint" && look.line === "dashed", JSON.stringify(look));
await page.screenshot({ path: `${OUT}/annotate-selected.png` });

const before = (list.find((a) => a.key === note.key) || {}).at;
await drag(page, noteAt, { x: noteAt.x + 60, y: noteAt.y + 30 });
list = await own(page);
const after = (list.find((a) => a.key === note.key) || {}).at;
check("moved by the pointer", !!after && (after[0] !== before[0] || after[1] !== before[1]), JSON.stringify([before, after]));
await page.keyboard.down("Control");
await page.keyboard.press("z");
await page.keyboard.up("Control");
await pause(300);
list = await own(page);
check("Ctrl+Z puts it back", JSON.stringify((list.find((a) => a.key === note.key) || {}).at) === JSON.stringify(before));
await page.keyboard.down("Control");
await page.keyboard.down("Shift");
await page.keyboard.press("z");
await page.keyboard.up("Shift");
await page.keyboard.up("Control");
await pause(300);
list = await own(page);
check("Ctrl+Shift+Z moves it again", JSON.stringify((list.find((a) => a.key === note.key) || {}).at) === JSON.stringify(after));

await page.evaluate((k) => window.TerraneApp.Canvas.engine.select([k]), shape.key);
await pause(100);
await page.keyboard.press("Delete");
await pause(300);
list = await own(page);
check("Delete removes the diamond, and the line that ended on it", !list.find((a) => a.key === shape.key)
  && !list.find((a) => a.key === line.key), list.map((a) => a.key).join(" "));
await page.keyboard.down("Control");
await page.keyboard.press("z");
await page.keyboard.up("Control");
await pause(300);
list = await own(page);
check("and Undo brings both back", !!list.find((a) => a.key === shape.key) && !!list.find((a) => a.key === line.key));
await saved(page);
const file = await page.evaluate((v) => fetch("/api/view?id=" + encodeURIComponent(v)).then((r) => r.json()), id);
const kept = (file.data && file.data.annotations) || [];
check("the file holds what the sheet does", kept.length === list.length, kept.length + " of " + list.length);
console.log(JSON.stringify(kept));
await page.close();

// ---- opened again, then opened as a diagram, then the engine's picture
const again = await open("draw=" + encodeURIComponent(id));
const boxes = await drawn(again);
check("opened again, every shape is drawn", Object.keys(boxes).length === kept.length, Object.keys(boxes).length + " of " + kept.length);
await again.screenshot({ path: `${OUT}/annotate-again.png` });
await again.close();

const read = await open("view=" + encodeURIComponent(id));
const shown = await read.evaluate(() => window.TerraneApp.Canvas.engine.ownBoxes() || {});
check("opened as a diagram, read only, its shapes are there", Object.keys(shown).length === kept.length,
  Object.keys(shown).length + " of " + kept.length);
check("and none of them can be picked up there", await read.evaluate(() => {
  const e = window.TerraneApp.Canvas.engine;
  return e.selected().length === 0;
}));
await read.screenshot({ path: `${OUT}/annotate-read.png` });
await read.close();

const svg = await (await fetch(URL + "/api/svg?view=" + encodeURIComponent(id))).text();
const painted = (svg.match(/class="own"/g) || []).length;
check("the engine's picture draws them all", painted === kept.length, painted + " of " + kept.length);
await writeFile(`${OUT}/annotate.svg`, svg);

// ---- beside the estate's records: a note by a box, a line from the box
// to it, and both where they were, beside it, when the diagram is drawn
// again. On lending-onboarding, which arrange_probe.mjs makes; skipped
// without it.
const BESIDE = "lending-onboarding", RECORD = "SYS-LENDING-PORTAL";
if ((await fetch(URL + "/api/view?id=" + BESIDE)).ok) {
  const p2 = await open("draw=" + BESIDE);
  await settled(p2);
  await pause(600);
  const z0 = await p2.evaluate(() => window.TerraneApp.Canvas.engine && document.getElementById("cy")._cyreg.cy.zoom());
  const s2 = await p2.evaluate(() => { const b = document.querySelector(".mg-surface").getBoundingClientRect(); return { x: b.left, y: b.top }; });
  const rec = await p2.evaluate((r) => window.TerraneApp.Canvas.engine.boxes()[r], RECORD);
  // What this walk draws, told from what earlier walks left on the diagram.
  const had = new Set((await own(p2)).map((a) => a.key));
  await p2.click("#cvNote");
  await p2.mouse.click(s2.x + rec.x + rec.w + 140, s2.y + rec.y + rec.h / 2);
  await p2.waitForSelector(".mg-edit", { timeout: 5000 });
  await p2.keyboard.type("Goes live in the first quarter");
  await p2.keyboard.down("Control");
  await p2.keyboard.press("Enter");
  await p2.keyboard.up("Control");
  await pause(300);
  let l2 = await own(p2);
  const by = l2.find((a) => a.role === "note" && !had.has(a.key));
  const nb2 = (await drawn(p2))[by.key];
  await lineTool(p2, "Square");
  await drag(p2, { x: s2.x + rec.x + rec.w / 2, y: s2.y + rec.y + rec.h / 2 }, { x: s2.x + nb2.x + nb2.w / 2, y: s2.y + nb2.y + nb2.h / 2 });
  l2 = await own(p2);
  const tie = l2.find((a) => a.role === "line" && !had.has(a.key));
  check("a square line from a record to the note, joined to both", !!tie && tie.to === by.key && tie.route === "square",
    tie && JSON.stringify(tie));
  check("the diagram keeps where its boxes are, so the note stays by its box",
    await p2.evaluate(() => Object.keys(window.TerraneApp.Canvas.cv.data.positions || {}).length > 0));
  const gap = { x: (nb2.x - rec.x) / z0, y: (nb2.y - rec.y) / z0 };
  await saved(p2);
  await p2.close();
  const p3 = await open("draw=" + BESIDE);
  await settled(p3);
  await pause(600);
  const z1 = await p3.evaluate(() => document.getElementById("cy")._cyreg.cy.zoom());
  const rec1 = await p3.evaluate((r) => window.TerraneApp.Canvas.engine.boxes()[r], RECORD);
  const nb3 = (await drawn(p3))[by.key];
  const gap1 = nb3 && { x: (nb3.x - rec1.x) / z1, y: (nb3.y - rec1.y) / z1 };
  check("drawn again, the note is where it was beside the box",
    !!gap1 && Math.abs(gap1.x - gap.x) <= 1 && Math.abs(gap1.y - gap.y) <= 1, JSON.stringify([gap, gap1]));
  check("and the line is still joined to the record", await p3.evaluate((k) => {
    const l = (window.TerraneApp.Canvas.cv.data.annotations || []).find((a) => a.key === k);
    return !!l && !!window.TerraneApp.Canvas.engine.ownBoxes()[k];
  }, tie.key));
  // A line from one record to another asks what it is; "Just a line" keeps
  // it the diagram's own.
  const other = await p3.evaluate((r) => {
    const b = window.TerraneApp.Canvas.engine.boxes();
    return Object.keys(b).filter((k) => k !== r && /^SYS-/.test(k))[0] || null;
  }, RECORD);
  if (other) {
    const s3 = await p3.evaluate(() => { const b = document.querySelector(".mg-surface").getBoundingClientRect(); return { x: b.left, y: b.top }; });
    const ob = await p3.evaluate((k) => window.TerraneApp.Canvas.engine.boxes()[k], other);
    const between = async () => (await own(p3)).filter((a) => a.role === "line" && a.from === RECORD && a.to === other).length;
    const linesBefore = await between();
    await lineTool(p3);
    await drag(p3, { x: s3.x + rec1.x + rec1.w / 2, y: s3.y + rec1.y + rec1.h / 2 }, { x: s3.x + ob.x + ob.w / 2, y: s3.y + ob.y + ob.h / 2 });
    await p3.waitForSelector("#ctxMenu .connect-opt.is-line", { timeout: 10000 });
    const head = await p3.$eval("#ctxMenu .ctx-head", (h) => h.textContent);
    check("a line between two records asks what it is", head === "What is this line?", head);
    await p3.screenshot({ path: `${OUT}/annotate-asks.png` });
    await p3.click("#ctxMenu .connect-opt.is-line");
    await pause(300);
    check("and Just a line keeps it the diagram's own", (await between()) === linesBefore + 1 && !(await p3.$("#ctxMenu")));
  }
  await p3.screenshot({ path: `${OUT}/annotate-beside.png` });

  // Several picked: a drag from inside the account, where nothing is,
  // around zone eu-west-2b; lined up by their tops from the bar, and back
  // with Undo; then framed with Ctrl+G, and the frame undone.
  await p3.keyboard.press("Escape");
  const span = await p3.evaluate(() => {
    const cy = document.getElementById("cy")._cyreg.cy, r = document.getElementById("cy").getBoundingClientRect();
    const box = (id) => cy.getElementById(id).renderedBoundingBox({ includeLabels: false });
    const acct = box("grp::AWS::prod-lending"), zone = box("grp::AWS::prod-lending::eu-west-2::eu-west-2b");
    return { from: { x: r.left + acct.x1 + 30, y: r.top + acct.y2 - 30 }, to: { x: r.left + zone.x2 + 4, y: r.top + zone.y1 - 4 } };
  });
  const kept0 = await p3.evaluate(() => JSON.stringify(window.TerraneApp.Canvas.cv.data.positions));
  await drag(p3, span.from, span.to);
  const picked = await p3.evaluate(() => window.TerraneApp.Canvas.cv.sel);
  check("a drag across the account's inside picks what it goes around", !!picked && picked.kind === "several"
    && picked.ids.length >= 2, picked && (picked.kind + " " + (picked.ids || []).length));
  check("and the bar is over them", await p3.evaluate(() => !document.getElementById("cvBar").hidden));
  await p3.screenshot({ path: `${OUT}/annotate-several.png` });
  await p3.click('#cvBar [data-do="top"]');
  await pause(500);
  const tops = await p3.evaluate((ids) => {
    const cy = document.getElementById("cy")._cyreg.cy;
    return ids.map((id) => { const n = cy.getElementById(id); return n.position("y") - n.height() / 2; });
  }, picked.ids);
  check("lined up by their tops", Math.max(...tops) - Math.min(...tops) < 1, tops.map((v) => Math.round(v)).join(" "));
  await p3.keyboard.down("Control");
  await p3.keyboard.press("z");
  await p3.keyboard.up("Control");
  await pause(1500);
  check("and Undo puts every one back where it was kept",
    (await p3.evaluate(() => JSON.stringify(window.TerraneApp.Canvas.cv.data.positions))) === kept0);
  await drag(p3, span.from, span.to);
  const framesBefore = (await own(p3)).filter((a) => a.role === "frame").length;
  await p3.keyboard.down("Control");
  await p3.keyboard.press("g");
  await p3.keyboard.up("Control");
  await pause(400);
  const framesAfter = (await own(p3)).filter((a) => a.role === "frame").length;
  check("Ctrl+G frames what is picked", framesAfter === framesBefore + 1);
  await p3.screenshot({ path: `${OUT}/annotate-framed.png` });
  await p3.keyboard.press("Escape");
  await p3.keyboard.down("Control");
  await p3.keyboard.press("z");
  await p3.keyboard.up("Control");
  await pause(400);
  check("and Undo takes the frame away", (await own(p3)).filter((a) => a.role === "frame").length === framesBefore);
  await p3.close();
  const svg2 = await (await fetch(URL + "/api/svg?view=" + BESIDE)).text();
  check("the engine's picture draws them with the records", (svg2.match(/class="own"/g) || []).length >= 2);
  await writeFile(`${OUT}/annotate-beside.svg`, svg2);
} else {
  console.log("skip beside the records: no " + BESIDE + " here (arrange_probe.mjs makes it)");
}

check("no page errors", !errors.length, errors.join(" | "));
await browser.close();
process.exit(failed ? 1 : 0);
