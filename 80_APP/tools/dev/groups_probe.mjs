// Do several of the diagram's own group, as V16 draws it? On a new diagram
// with four shapes of its own: three picked offer Group them on the bar and
// in the panel, and grouped, the file keeps the group and each says it is
// in it; a click on one picks all three, its outline and name shown, and a
// drag moves the three as one; a double-click goes inside to pick one and
// Esc comes back out; the name typed in the panel is kept; the group and
// the fourth grouped again nest, a click picking the outer and each
// double-click going a level in; Ctrl+Shift+U ungroups, and one Undo
// puts it back; Shift-click takes a group out of a pick whole; a look
// painted with a click goes onto the whole group; Ctrl+D copies a group as
// a group of its own, and a copy left with one in it lets it go; Ctrl+C
// and Ctrl+V paste one as a group of its own; the picture draws no group;
// leaving the canvas takes the outline with it.
//
//   node 80_APP/tools/dev/groups_probe.mjs out/ URL
//
// It makes a diagram, so run it on a copy of the repository. Exits 1 if a
// step does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node groups_probe.mjs OUT URL");
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
const picked = () => page.evaluate(() => {
  const s = window.TerraneApp.Canvas.cv.sel;
  return s && s.keys ? s.keys.slice().sort() : [];
});
const groups = () => page.evaluate(() => JSON.parse(JSON.stringify(window.TerraneApp.Canvas.cv.data.groups || [])));
const file = () => page.evaluate(() => fetch("/api/view?id=" + window.TerraneApp.Canvas.cv.id).then((r) => r.json()))
  .then((f) => f.data || {});
const same = (a, b) => JSON.stringify(a.slice().sort()) === JSON.stringify(b.slice().sort());
// Where one of its own is on the screen: its box through the sheet's zoom
// and pan, which the drawing over it follows.
const at = (k) => page.evaluate((key) => {
  const app = window.TerraneApp, b = app.Canvas.engine.boxOf(key), cy = document.getElementById("cy")._cyreg.cy;
  const r = document.getElementById("cy").getBoundingClientRect(), z = cy.zoom(), p = cy.pan();
  return { x: r.left + (b.x1 + b.x2) / 2 * z + p.x, y: r.top + (b.y1 + b.y2) / 2 * z + p.y, box: b };
}, k);
async function click(k, opts) {
  const p = await at(k);
  if (opts && opts.shift) await page.keyboard.down("Shift");
  await page.mouse.click(p.x, p.y);
  if (opts && opts.shift) await page.keyboard.up("Shift");
  await pause(450);
}
async function dblclick(k) {
  const p = await at(k);
  await page.mouse.click(p.x, p.y, { count: 2 });
  await pause(500);
}
async function chord(...combo) {
  await page.focus("#cy");
  for (const k of combo.slice(0, -1)) await page.keyboard.down(k);
  await page.keyboard.press(combo[combo.length - 1]);
  for (const k of combo.slice(0, -1).reverse()) await page.keyboard.up(k);
  await pause(500);
}
const outline = () => page.evaluate(() => {
  const o = document.getElementById("cvGroup");
  return o && !o.hidden ? o.querySelector(".cv-gathered-tag").innerText.trim() : null;
});
const panel = () => page.evaluate(() => document.getElementById("cvDetails").innerText);
async function button(words) {
  const b = await page.evaluateHandle((w) => Array.prototype.find.call(
    document.querySelectorAll("#cvDetails button"), (x) => x.innerText.trim() === w) || null, words);
  return b.asElement();
}

const keys = await page.evaluate(() => {
  const e = window.TerraneApp.Canvas.engine;
  const add = (label, x, y) => e.add({ role: "shape", shape: "rounded", label: label, box: { x: x, y: y, w: 150, h: 64 } });
  const out = { a: add("Gateway", 80, 140), b: add("Payments", 280, 140), c: add("Ledger", 480, 140),
    d: add("Fraud check", 280, 320) };
  e.select([]);
  return out;
});
await saved();
const three = [keys.a, keys.b, keys.c];

// Three picked: Group them, on the bar and in the panel.
await page.evaluate((list) => window.TerraneApp.Canvas.picked([], list), three);
await pause(500);
check("three picked offer Group them on the bar", await page.evaluate(() => {
  const b = document.querySelector('#cvBar [data-do="group"]');
  return !!b && !b.disabled && !document.getElementById("cvBar").hidden;
}));
check("and in the panel, first", await page.evaluate(() => {
  const b = document.querySelector("#cvDetails .cv-acts button");
  return !!b && b.innerText.trim() === "Group them" && b.classList.contains("primary");
}));
await page.screenshot({ path: OUT + "/several.png" });
await (await button("Group them")).click();
await pause(600);
let g = await groups();
check("grouped, the diagram has one group", g.length === 1 && g[0].key === "group-1", JSON.stringify(g));
check("and each of the three is in it", (await Promise.all(three.map(item))).every((x) => x.group === "group-1"));
check("the group picked shows its outline and its name", (await outline()) === "Group 1 · 3", await outline());
check("and its panel", /Group · on this diagram only/.test(await panel()) && /In it/.test(await panel()));
check("the bar is not shown over a group", await page.evaluate(() => document.getElementById("cvBar").hidden));
await saved();
let f = await file();
check("the file keeps it", (f.groups || []).length === 1 &&
  (f.annotations || []).filter((x) => x.group === "group-1").length === 3, JSON.stringify(f.groups));

// A click on one picks all three; a drag moves them as one.
await chord("Escape");
check("Esc lets go", (await picked()).length === 0);
await click(keys.b);
check("a click on one picks the whole group", same(await picked(), three), JSON.stringify(await picked()));
const before = await Promise.all([keys.a, keys.b, keys.c, keys.d].map(at));
const p = await at(keys.b);
await page.mouse.move(p.x, p.y);
await page.mouse.down();
for (let i = 1; i <= 10; i += 1) await page.mouse.move(p.x + 6 * i, p.y + 4 * i);
await page.mouse.up();
await pause(700);
const after = await Promise.all([keys.a, keys.b, keys.c, keys.d].map(at));
const moved = after.map((q, i) => Math.round(q.box.x1 - before[i].box.x1));
check("a drag on one moves the three as one, and not the fourth",
  moved[0] > 30 && moved[0] === moved[1] && moved[1] === moved[2] && moved[3] === 0, JSON.stringify(moved));

// A double-click goes inside; Esc comes out.
await dblclick(keys.b);
check("a double-click goes inside, picking the one", same(await picked(), [keys.b]), JSON.stringify(await picked()));
check("and no words were opened to edit", await page.evaluate(() => !document.querySelector(".mg-edit")));
await click(keys.c);
check("inside, a click picks another of it alone", same(await picked(), [keys.c]), JSON.stringify(await picked()));
await chord("Escape");
check("Esc comes out, the group picked whole", same(await picked(), three), JSON.stringify(await picked()));

// Its name, typed in the panel.
await page.click("#cvDetails input.cv-input");
await page.keyboard.down("Control");
await page.keyboard.press("a");
await page.keyboard.up("Control");
await page.keyboard.type("Front of payments");
await page.keyboard.press("Tab");
await pause(500);
check("the name typed is the group's", (await groups())[0].name === "Front of payments");
check("and the outline says it", (await outline()) === "Front of payments · 3", await outline());
await page.screenshot({ path: OUT + "/group.png" });

// The group and the fourth, grouped again.
await click(keys.d, { shift: true });
check("Shift-click adds the fourth to the group picked", same(await picked(), three.concat([keys.d])));
await chord("Control", "Shift", "KeyG");
g = await groups();
const outer = g.find((x) => x.key !== "group-1");
check("Ctrl+Shift+G groups the group and the fourth", !!outer && g.find((x) => x.key === "group-1").group === outer.key &&
  (await item(keys.d)).group === outer.key, JSON.stringify(g));
await chord("Escape");
await chord("Escape");
await click(keys.a);
check("a click picks the outer group, four", same(await picked(), three.concat([keys.d])), JSON.stringify(await picked()));
await dblclick(keys.a);
check("a double-click goes into it, picking the inner group", same(await picked(), three), JSON.stringify(await picked()));
await dblclick(keys.a);
check("and another, the one", same(await picked(), [keys.a]), JSON.stringify(await picked()));
await chord("Escape");
await chord("Escape");
check("Esc twice comes out to the outer group", same(await picked(), three.concat([keys.d])), JSON.stringify(await picked()));

// Ungroup, and Undo.
await chord("Control", "Shift", "KeyU");
g = await groups();
check("Ctrl+Shift+U ungroups the outer", g.length === 1 && g[0].key === "group-1" && !g[0].group &&
  !(await item(keys.d)).group, JSON.stringify(g));
await chord("Control", "z");
g = await groups();
check("one Undo puts it back", g.length === 2 && (await item(keys.d)).group === outer.key, JSON.stringify(g));
await chord("Escape");
await click(keys.d);
await chord("Control", "Shift", "KeyU");
check("and the outer, picked again, ungroups again", (await groups()).length === 1);
await chord("Escape");

// Shift-click takes a group out whole.
await click(keys.d);
await click(keys.b, { shift: true });
check("Shift-click on one of a group adds the group", same(await picked(), three.concat([keys.d])), JSON.stringify(await picked()));
await click(keys.a, { shift: true });
check("and again takes the group out whole", same(await picked(), [keys.d]), JSON.stringify(await picked()));

// A look painted with a click goes onto the whole group.
await chord("Escape");
await page.evaluate((k) => window.TerraneApp.Canvas.engine.update(k, { look: { fill: "rose" } }), keys.d);
await click(keys.d);
await (await button("Copy the look")).click();
await pause(300);
await click(keys.b);
check("a look painted with a click goes onto the whole group",
  (await Promise.all(three.map(item))).every((x) => x.look && x.look.fill === "rose"),
  JSON.stringify((await Promise.all(three.map(item))).map((x) => x.look)));
await chord("Escape");
await chord("Escape");

// A copy of a group is a group of its own; one left alone lets it go.
await chord("Escape");
await click(keys.a);
await chord("Control", "KeyD");
g = await groups();
const copied = await picked();
const copy = g.find((x) => x.key !== "group-1");
check("Ctrl+D copies the group as a group of its own, named as it", g.length === 2 && copy && copy.name === "Front of payments" &&
  copied.length === 3 && !copied.some((k) => three.includes(k)), JSON.stringify(g));
check("the copies are in the copy", (await Promise.all(copied.map(item))).every((x) => x.group === copy.key));
check("and the first three are not", (await Promise.all(three.map(item))).every((x) => x.group === "group-1"));
await page.evaluate((list) => window.TerraneApp.Canvas.engine.remove(list), copied.slice(0, 2));
await pause(600);
g = await groups();
check("a group left with one lets it go", g.length === 1 && !(await item(copied[2])).group, JSON.stringify(g));
await chord("Control", "z");
g = await groups();
check("and one Undo has the copy's group back whole", g.length === 2 && !!(await item(copied[0])), JSON.stringify(g));

// A paste of a group is a group of its own too; it lands over the
// first, so nothing after it clicks there.
await chord("Escape");
await click(keys.a);
await chord("Control", "KeyC");
await chord("Control", "KeyV");
g = await groups();
const pasted = await picked();
const third = g.find((x) => x.key !== "group-1" && x.key !== copy.key);
check("Ctrl+C and Ctrl+V paste the group as a group of its own", !!third && third.name === "Front of payments" &&
  pasted.length === 3 && (await Promise.all(pasted.map(item))).every((x) => x.group === third.key), JSON.stringify(g));


await saved();
f = await file();
const svg = await page.evaluate(() => fetch("/api/svg?view=" + window.TerraneApp.Canvas.cv.id).then((r) => r.text()));
check("the picture draws its shapes and no group", svg.indexOf("Gateway") !== -1 && svg.indexOf("Front of payments") === -1);
check("the file reads back", (f.groups || []).length === 3, JSON.stringify(f.groups));
// Leaving the canvas takes the outline with it: the sheet is the next
// view's too.
await click(keys.d);
await click(keys.a);
check("a group picked before leaving shows its outline", (await outline()) !== null);
await page.evaluate(() => { location.hash = "#home"; });
await pause(1500);
check("leaving the canvas takes the outline with it",
  await page.evaluate(() => { const o = document.getElementById("cvGroup"); return !o || o.hidden; }));
check("no page errors", errors.length === 0, errors.join(" / "));
await browser.close();
process.exit(failed ? 1 : 0);
