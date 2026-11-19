// Does a swimlane draw as V16 draws it? On a new diagram, with a real
// pointer: Swimlane, the last of Shapes, dragged out on the sheet makes a
// swimlane of three lanes; a lane is picked by its name, its panel says so
// and its tab says it is the second of three; it stands for Payments
// Operations, chosen by name, and is named as it is; a shape drawn inside
// it sits in it, and goes with the swimlane when the swimlane is carried by
// its name; the lane made deeper by its handle pushes the lanes under it
// down; a lane added, and put first from the panel by its grip; the lane
// deleted keeps its shape, now in the lane above, where it was; the lanes
// turned to run down and their names put at the top; one Undo puts them
// back across; the file keeps it all, the picture draws it, and the org
// unit's page lists the diagram it has a lane on.
//
//   node 80_APP/tools/dev/swimlane_probe.mjs out/ URL
//
// It makes a diagram, so run it on a copy of the repository. Exits 1 if a
// step does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node swimlane_probe.mjs OUT URL");
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
const own = () => page.evaluate(() => window.TerraneApp.Canvas.engine.own ? null : null)
  .then(() => page.evaluate(() => JSON.parse(JSON.stringify(window.TerraneApp.Canvas.cv.data.annotations || []))));
const lanes = (pool) => page.evaluate((k) => window.TerraneApp.Canvas.engine.lanes(k), pool);
const picked = () => page.evaluate(() => { const s = window.TerraneApp.Canvas.cv.sel; return s && s.keys ? s.keys.slice() : []; });
const panel = () => page.evaluate(() => document.getElementById("cvDetails").innerText);
const file = () => page.evaluate(() => fetch("/api/view?id=" + window.TerraneApp.Canvas.cv.id).then((r) => r.json()))
  .then((f) => f.data || {});
// A point of one of its own on the screen: `fx`, `fy` shares of its box.
const at = (k, fx, fy) => page.evaluate((key, ax, ay) => {
  const b = window.TerraneApp.Canvas.engine.boxOf(key), cy = document.getElementById("cy")._cyreg.cy;
  const r = document.getElementById("cy").getBoundingClientRect(), z = cy.zoom(), p = cy.pan();
  return { x: r.left + (b.x1 + (b.x2 - b.x1) * ax) * z + p.x, y: r.top + (b.y1 + (b.y2 - b.y1) * ay) * z + p.y, box: b };
}, k, fx, fy);
async function drag(from, dx, dy) {
  await page.mouse.move(from.x, from.y);
  await page.mouse.down();
  for (let i = 1; i <= 10; i += 1) await page.mouse.move(from.x + dx * i / 10, from.y + dy * i / 10);
  await page.mouse.up();
  await pause(700);
}
async function button(words, scope) {
  const b = await page.evaluateHandle((w, sc) => Array.prototype.find.call(
    document.querySelectorAll((sc || "#cvDetails") + " button"), (x) => x.innerText.trim() === w) || null, words, scope);
  return b.asElement();
}
async function chord(...combo) {
  await page.focus("#cy");
  for (const k of combo.slice(0, -1)) await page.keyboard.down(k);
  await page.keyboard.press(combo[combo.length - 1]);
  for (const k of combo.slice(0, -1).reverse()) await page.keyboard.up(k);
  await pause(500);
}

// Swimlane, the last of Shapes, dragged out on the sheet.
await page.click("#cvShapes");
await pause(300);
const last = await page.evaluate(() => {
  const items = Array.from(document.querySelectorAll("#cvShapeMenu .cv-shape-item"));
  return items.length ? items[items.length - 1].innerText.trim() : "";
});
check("Swimlane is the last of Shapes", last === "Swimlane", last);
await (await button("Swimlane", "#cvShapeMenu")).click();
await pause(300);
// Dragged out from the sheet's corner: a new diagram's empty sheet has
// its offer to start from the estate in the middle, and the tool's hint
// under the tools.
const spot = await page.evaluate(() => {
  const b = document.querySelector(".mg-surface").getBoundingClientRect();
  return { x: b.left + b.width * 0.04, y: b.top + b.height * 0.3, w: b.width, h: b.height };
});
await drag(spot, spot.w * 0.66, spot.h * 0.66);
await pause(700);
let list = await own();
const pool = (list.find((a) => a.role === "pool") || {}).key;
let ls = pool ? await lanes(pool) : [];
check("dragged out on the sheet, it is a swimlane of three lanes", !!pool && ls.length === 3 &&
  list.filter((a) => a.role === "lane").every((a) => JSON.stringify(a.in) === JSON.stringify([pool])), JSON.stringify(list));
check("and the swimlane is picked, its panel saying so", JSON.stringify(await picked()) === JSON.stringify([pool]) &&
  /Swimlane · on this diagram only/.test(await panel()));
await page.screenshot({ path: OUT + "/swimlane.png" });

// A lane picked by its name.
const second = ls[1].key;
let p = await at(second, 0.05, 0.3);
await page.mouse.click(p.x, p.y);
await pause(500);
check("a lane is picked by its name", JSON.stringify(await picked()) === JSON.stringify([second]), JSON.stringify(await picked()));
check("its tab says which of the lanes it is", await page.evaluate(() => {
  const o = document.getElementById("cvGroup");
  return !!o && !o.hidden && o.querySelector(".cv-gathered-name").innerText.trim() === "Lane 2 of 3";
}));
check("and its panel says it is a lane of the swimlane", /Lane · on this diagram only/.test(await panel()) &&
  /A lane of “Who does what”/.test(await panel()), (await panel()).slice(0, 200));

// It stands for Payments Operations, chosen by its name.
await (await button("Choose an actor or an org unit")).click();
await pause(300);
await page.type("#cvDetails .cv-stands-in", "Payments Oper");
await pause(400);
const choice = await page.evaluateHandle(() => Array.prototype.find.call(
  document.querySelectorAll("#cvDetails .cv-stands-list .cv-pick"), (b) => /ORG-PAYMENTS/.test(b.innerText)) || null);
check("Payments Operations is found by its name", !!choice.asElement());
if (choice.asElement()) await choice.asElement().click();
await pause(500);
let lane2 = await item(second);
check("the lane stands for it, and is named as it is", lane2.stands_for === "ORG-PAYMENTS" &&
  lane2.label === "Payments Operations", JSON.stringify(lane2));
check("its name and id are drawn in its column", await page.evaluate(() => {
  const t = document.querySelector(".mg-surface").innerText;
  return /Payments Operations/.test(t) && /ORG-PAYMENTS/.test(t);
}));
check("and the panel shows what it stands for", /Payments Operations/.test(await panel()) &&
  /ORG-PAYMENTS · an org unit/.test(await panel()), (await panel()).slice(0, 300));

// A shape drawn inside the lane sits in it.
await (await page.$("#cvShapes")).click();
await pause(300);
await (await button("Rounded box", "#cvShapeMenu")).click();
await pause(300);
p = await at(second, 0.45, 0.5);
await page.mouse.click(p.x, p.y);
await pause(600);
list = await own();
const shape = (list.find((a) => a.role === "shape") || {}).key;
check("a shape drawn inside the lane sits in it", !!shape && JSON.stringify((await item(shape)).in) === JSON.stringify([pool, second]),
  JSON.stringify(shape && (await item(shape)).in));

// The swimlane carried by its name takes the lane and the shape with it.
let s0 = (await at(shape, 0.5, 0.5)).box, l0 = (await at(second, 0.5, 0.5)).box;
p = await at(pool, 0.3, 0.02);
await drag(p, 60, 40);
let s1 = (await at(shape, 0.5, 0.5)).box, l1 = (await at(second, 0.5, 0.5)).box;
check("the swimlane carried by its name takes its lanes and what is in them",
  Math.round(s1.x1 - s0.x1) === 60 && Math.round(s1.y1 - s0.y1) === 40 && Math.round(l1.x1 - l0.x1) === 60,
  JSON.stringify([s1.x1 - s0.x1, s1.y1 - s0.y1, l1.x1 - l0.x1]));

// The lane made deeper by its handle pushes the lanes under it down.
p = await at(second, 0.05, 0.3);
await page.mouse.click(p.x, p.y);
await pause(400);
const third = ls[2].key;
const t0 = (await at(third, 0.5, 0.5)).box, d0 = (await at(second, 0.5, 0.5)).box;
// The handle as the page draws it: the lowest of the handles' squares.
p = await page.evaluate(() => {
  const hs = Array.from(document.querySelectorAll(".mg-surface svg rect")).map((r) => r.getBoundingClientRect())
    .filter((b) => b.width >= 6 && b.width <= 12 && Math.abs(b.width - b.height) < 1);
  const low = Math.max.apply(null, hs.map((b) => b.top));
  const row = hs.filter((b) => Math.abs(b.top - low) < 1).sort((m, n) => m.left - n.left);
  const b = row[Math.floor(row.length / 2)];
  return { x: b.left + b.width / 2, y: b.top + b.height / 2 };
});
await drag(p, 0, 60);
const t1 = (await at(third, 0.5, 0.5)).box, d1 = (await at(second, 0.5, 0.5)).box, pb = (await at(pool, 0.5, 0.5)).box;
check("the lane made deeper by its handle pushes the lane under it down",
  Math.round((d1.y2 - d1.y1) - (d0.y2 - d0.y1)) === 60 && Math.round(t1.y1 - t0.y1) === 60 && Math.round(pb.y2 - t1.y2) === 0,
  JSON.stringify([d1.y2 - d1.y1 - (d0.y2 - d0.y1), t1.y1 - t0.y1, pb.y2 - t1.y2]));
check("and keeps the swimlane's length", Math.round(d1.x2 - d1.x1) === Math.round(pb.x2 - pb.x1));

// A lane added, and the new one put first by its grip.
await (await button("+ Add a lane")).click();
await pause(500);
ls = await lanes(pool);
check("+ Add a lane adds a fourth, picked", ls.length === 4 && JSON.stringify(await picked()) === JSON.stringify([ls[3].key]));
const fourth = ls[3].key;
const grip = await page.evaluate((k) => {
  const row = document.querySelector('#cvDetails .cv-lane[data-key="' + k + '"] .cv-lane-grip').getBoundingClientRect();
  const top = document.querySelector("#cvDetails .cv-lane").getBoundingClientRect();
  return { x: row.left + row.width / 2, y: row.top + row.height / 2, top: top.top };
}, fourth);
await page.mouse.move(grip.x, grip.y);
await page.mouse.down();
for (let i = 1; i <= 8; i += 1) await page.mouse.move(grip.x, grip.y + (grip.top - 4 - grip.y) * i / 8);
await page.mouse.up();
await pause(600);
ls = await lanes(pool);
check("its grip dragged to the top puts it first", ls[0].key === fourth, JSON.stringify(ls.map((l) => l.key)));
const fb = (await at(fourth, 0.5, 0.5)).box, pb2 = (await at(pool, 0.5, 0.5)).box;
check("and it is drawn first, under the swimlane's name", Math.round(fb.y1 - pb2.y1) === 34, fb.y1 - pb2.y1);

// The lane deleted keeps its shape, in the lane above, where it was.
const before = (await at(shape, 0.5, 0.5)).box;
const above = ls[ls.findIndex((l) => l.key === second) - 1].key;
p = await at(second, 0.05, 0.3);
await page.mouse.click(p.x, p.y);
await pause(400);
await (await button("Delete the lane")).click();
await pause(600);
const after = (await at(shape, 0.5, 0.5)).box;
check("the lane deleted keeps its shape, now in the lane above",
  !(await item(second)) && JSON.stringify((await item(shape)).in) === JSON.stringify([pool, above]), JSON.stringify((await item(shape)).in));
check("where it was on the sheet", Math.round(after.x1 - before.x1) === 0 && Math.round(after.y1 - before.y1) === 0,
  JSON.stringify([after.x1 - before.x1, after.y1 - before.y1]));

// The lanes turned to run down, their names at the top; one Undo puts them back.
p = await at(pool, 0.3, 0.02);
await page.mouse.click(p.x, p.y);
await pause(400);
await (await button("Down")).click();
await pause(600);
ls = await lanes(pool);
const boxes = [];
for (const l of ls) boxes.push((await at(l.key, 0.5, 0.5)).box);
const pool1 = await item(pool);
check("turned to run down, the lanes stand side by side with their names at the top",
  pool1.runs === "down" && pool1.names === "top" && boxes.every((b) => Math.round(b.y1) === Math.round(boxes[0].y1)) &&
  boxes.every((b, i) => i === 0 || Math.round(b.x1) === Math.round(boxes[i - 1].x2)), JSON.stringify(pool1));
await page.screenshot({ path: OUT + "/swimlane-down.png" });
await chord("Control", "z");
const pool2 = await item(pool);
check("one Undo runs them across again", !pool2.runs && !pool2.names, JSON.stringify(pool2));

// The file, the picture and the org unit's page.
await saved();
const f = await file();
const pooled = (f.annotations || []).filter((a) => a.role === "lane");
check("the file keeps the swimlane, its lanes and what one stands for", pooled.length === 3 &&
  (f.annotations || []).some((a) => a.role === "pool") && !pooled.some((a) => a.stands_for), JSON.stringify(pooled));
await page.evaluate((k) => window.TerraneApp.Canvas.picked([], [k]), above);
await pause(300);
await (await button("Choose an actor or an org unit")).click();
await page.type("#cvDetails .cv-stands-in", "Payments Oper");
await pause(400);
await page.evaluate(() => Array.prototype.find.call(document.querySelectorAll("#cvDetails .cv-stands-list .cv-pick"),
  (b) => /ORG-PAYMENTS/.test(b.innerText)).click());
await saved();
const svg = await page.evaluate(() => fetch("/api/svg?view=" + window.TerraneApp.Canvas.cv.id).then((r) => r.text()));
// The lane's name wraps in its column, a line a word.
check("the picture draws the swimlane and the lane's record", /data-role="pool"/.test(svg) && />Payments</.test(svg) &&
  />Operations</.test(svg) && />ORG-PAYMENTS</.test(svg));
const entity = await page.evaluate(() => fetch("/api/entity?id=ORG-PAYMENTS").then((r) => r.json()));
const lanesOn = ((entity.diagrams || []).find((g) => g.kind === "lanes") || {}).items || [];
const id = await page.evaluate(() => window.TerraneApp.Canvas.cv.id);
check("the org unit's page lists the diagram it has a lane on", lanesOn.some((d) => d.viewId === id), JSON.stringify(lanesOn));
await page.evaluate((k) => window.TerraneApp.Canvas.picked([], [k]), above);
await pause(400);
await page.screenshot({ path: OUT + "/lane.png" });
check("no page errors", errors.length === 0, errors.join(" / "));
await browser.close();
process.exit(failed ? 1 : 0);
