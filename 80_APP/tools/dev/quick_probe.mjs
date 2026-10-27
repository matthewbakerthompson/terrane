// Does quick connect draw the next box? With a real pointer: on a new
// diagram, a shape hovered shows four arrows off its sides, which stay as
// the pointer goes out to one; the right one pressed draws the same shape
// 60 units to the right, joined by a line, open to type in, and one Undo
// takes both away; pressed again and typed in, it keeps the words; the
// arrow below carried to empty sheet draws the next shape there, and the
// right one carried onto the shape beside it draws only a line. Then on
// lending-onboarding (arrange_probe.mjs makes it), the Lending portal's
// right arrow opens Add asking what comes next; a record of the estate
// chosen, a line joins the two and asks "What is this line?".
//
//   node 80_APP/tools/dev/quick_probe.mjs out/ URL
//
// It draws and makes a diagram, so run it on a copy of the repository.
// Exits 1 if a step does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node quick_probe.mjs OUT URL");
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
const own = (page) => page.evaluate(() => (window.TerraneApp.Canvas.cv.data.annotations || []).map((a) => Object.assign({}, a)));
const arrows = (page) => page.evaluate(() => Array.from(document.querySelectorAll(".mg-qc-set:not([hidden]) .mg-qc")).map((b) => {
  const r = b.getBoundingClientRect();
  return { dir: b.dataset.dir, x: r.left + r.width / 2, y: r.top + r.height / 2 };
}));
async function screenBox(page, key) {
  return page.evaluate((k) => {
    const b = window.TerraneApp.Canvas.engine.ownBoxes()[k], s = document.querySelector(".mg-surface").getBoundingClientRect();
    return { x1: s.left + b.x, y1: s.top + b.y, x2: s.left + b.x + b.w, y2: s.top + b.y + b.h, cx: s.left + b.x + b.w / 2, cy: s.top + b.y + b.h / 2 };
  }, key);
}
async function glide(page, a, b, steps = 10) {
  for (let i = 1; i <= steps; i += 1) await page.mouse.move(a.x + (b.x - a.x) * i / steps, a.y + (b.y - a.y) * i / steps);
}
async function keys(page, ...combo) {
  for (const k of combo.slice(0, -1)) await page.keyboard.down(k);
  await page.keyboard.press(combo[combo.length - 1]);
  for (const k of combo.slice(0, -1).reverse()) await page.keyboard.up(k);
  await pause(400);
}

// ---- the diagram's own, on a new diagram
const page = await open("draw");
const first = await page.evaluate(() => {
  const e = window.TerraneApp.Canvas.engine;
  const k = e.add({ role: "shape", shape: "rounded", label: "Intake", box: { x: 200, y: 200, w: 120, h: 64 } });
  e.select([]);
  return k;
});
await pause(500);
const A = await screenBox(page, first);
await page.mouse.move(A.cx - 200, A.cy);
await glide(page, { x: A.cx - 200, y: A.cy }, { x: A.cx, y: A.cy });
await pause(200);
let shown = await arrows(page);
const east = shown.find((b) => b.dir === "e");
check("hovered, a shape shows four arrows off its sides", shown.length === 4 && !!east && Math.abs(east.x - (A.x2 + 14)) < 1.5
  && Math.abs(east.y - A.cy) < 1.5, JSON.stringify(shown.map((b) => b.dir + "@" + Math.round(b.x) + "," + Math.round(b.y))));
await glide(page, { x: A.cx, y: A.cy }, east, 8);
await pause(150);
check("and they stay as the pointer goes out to one", (await arrows(page)).length === 4);
await page.screenshot({ path: `${OUT}/quick-hover.png` });
const before = await own(page);
await page.mouse.down();
await page.mouse.up();
await pause(500);
let after = await own(page);
const made = after.find((a) => !before.some((b) => b.key === a.key) && a.role === "shape");
const joined = after.find((a) => a.role === "line" && a.from === first && made && a.to === made.key);
const was = before.find((a) => a.key === first);
check("pressed, the right arrow draws the same shape 60 to the right", !!made && made.shape === "rounded"
  && made.at[0] === was.at[0] + 180 && made.at[1] === was.at[1], made && JSON.stringify(made));
check("joined to it by a line", !!joined);
check("and open to type in", await page.evaluate(() => !!document.querySelector(".mg-edit")));
await page.keyboard.press("Escape");
await pause(300);
await keys(page, "Control", "z");
after = await own(page);
check("one Undo takes the shape and the line away", after.length === before.length, after.length + " for " + before.length);

await page.mouse.move(A.cx, A.cy);
await pause(200);
shown = await arrows(page);
await glide(page, { x: A.cx, y: A.cy }, shown.find((b) => b.dir === "e"), 8);
await page.mouse.down();
await page.mouse.up();
await pause(400);
await page.keyboard.type("Review");
await keys(page, "Control", "Enter");
after = await own(page);
const second = after.find((a) => a.label === "Review");
check("pressed again and typed in, the next shape keeps the words", !!second && second.role === "shape");

// The arrow below carried to empty sheet.
await page.mouse.move(A.cx, A.cy);
await pause(200);
shown = await arrows(page);
const south = shown.find((b) => b.dir === "s");
const count = (await own(page)).length;
await glide(page, { x: A.cx, y: A.cy }, south, 8);
await page.mouse.down();
const drop = { x: A.cx + 20, y: A.cy + 190 };
await glide(page, south, drop, 12);
await page.mouse.up();
await pause(500);
await page.keyboard.press("Escape");
await pause(300);
after = await own(page);
const third = after.find((a) => a.role === "shape" && a.key !== first && a.key !== second.key);
const sheetDrop = await page.evaluate((d) => {
  const s = document.querySelector(".mg-surface").getBoundingClientRect();
  return { x: d.x - s.left, y: d.y - s.top };
}, drop);
const thirdBox = third ? await screenBox(page, third.key) : null;
check("the arrow below carried to empty sheet draws the next shape there, joined",
  after.length === count + 2 && !!thirdBox && Math.abs(thirdBox.cx - drop.x) <= 1.5 && Math.abs(thirdBox.cy - drop.y) <= 1.5
  && after.some((a) => a.role === "line" && a.from === first && a.to === third.key),
  thirdBox && Math.round(thirdBox.cx - drop.x) + ", " + Math.round(thirdBox.cy - drop.y) + " from where it was let go");

// The right arrow carried onto the shape beside it.
await page.mouse.move(A.cx, A.cy);
await pause(200);
shown = await arrows(page);
const B = await screenBox(page, second.key);
const n0 = (await own(page)).length;
await glide(page, { x: A.cx, y: A.cy }, shown.find((b) => b.dir === "e"), 8);
await page.mouse.down();
await glide(page, shown.find((b) => b.dir === "e"), { x: B.cx, y: B.cy }, 12);
await page.mouse.up();
await pause(500);
after = await own(page);
check("carried onto the shape beside it, it draws only a line", after.length === n0 + 1
  && after.filter((a) => a.role === "line" && a.from === first && a.to === second.key).length === 2,
  (after.length - n0) + " added");
await page.screenshot({ path: `${OUT}/quick-own.png` });
await page.close();

// ---- from a record
const RECORD = "SYS-LENDING-PORTAL";
if (!(await fetch(URL + "/api/view?id=lending-onboarding")).ok) {
  console.log("skip  no lending-onboarding here (arrange_probe.mjs makes it)");
} else {
  const lend = await open("draw=lending-onboarding");
  const at = await lend.evaluate((id) => {
    const cy = document.getElementById("cy")._cyreg.cy, r = document.getElementById("cy").getBoundingClientRect();
    const rp = cy.getElementById(id).renderedPosition();
    return { x: r.left + rp.x, y: r.top + rp.y };
  }, RECORD);
  await lend.mouse.move(at.x - 3, at.y);
  await lend.mouse.move(at.x, at.y);
  await pause(250);
  const there = await arrows(lend);
  check("hovered, a record shows the arrows too", there.length === 4);
  const right = there.find((b) => b.dir === "e");
  const linesBefore = (await own(lend)).filter((a) => a.role === "line").map((a) => a.key);
  await glide(lend, at, right, 8);
  await lend.mouse.down();
  await lend.mouse.up();
  await pause(500);
  const asked = await lend.evaluate(() => {
    const p = document.getElementById("cvPicker"), l = p && p.querySelector(".cv-pick-link");
    return { open: !!p && !p.hidden, said: l ? l.innerText : "" };
  });
  check("pressed, its arrow opens Add asking what comes next", asked.open && /What comes next to Lending portal/.test(asked.said),
    asked.said);
  await lend.evaluate(() => Array.from(document.querySelectorAll("#cvPicker .cv-tab")).find((t) => t.innerText.trim() === "This estate").click());
  await pause(300);
  const chosen = await lend.evaluate(() => {
    const row = document.querySelector("#cvPicker .cv-row");
    const name = row.querySelector("b").innerText;
    row.click();
    return name;
  });
  await lend.waitForFunction(() => /What is this line\?/.test(document.body.innerText), { timeout: 20000 }).catch(() => {});
  const asks = await lend.evaluate(() => /What is this line\?/.test(document.body.innerText));
  const line = (await own(lend)).find((a) => a.role === "line" && linesBefore.indexOf(a.key) === -1);
  const drawn = line && await lend.evaluate((id) => document.getElementById("cy")._cyreg.cy.getElementById(id).nonempty(), line.to);
  check("a record of the estate chosen, a line joins the two and asks what it is",
    !!line && line.from === RECORD && drawn && asks, chosen + " (" + (line && line.to) + ")");
  await lend.screenshot({ path: `${OUT}/quick-record.png` });
  await lend.evaluate(() => {
    const b = Array.from(document.querySelectorAll("button")).find((x) => /Just a line/.test(x.innerText));
    if (b) b.click();
  });
  await pause(500);
  await lend.close();
}
check("no page errors", !errors.length, errors.join(" | "));
await browser.close();
process.exit(failed ? 1 : 0);
