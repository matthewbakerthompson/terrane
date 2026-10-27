// Does Lock keep things where they are? On lending-onboarding
// (arrange_probe.mjs makes it, annotate_probe.mjs puts a note by the
// Lending portal): the portal picked and locked with Ctrl+Shift+L, kept in
// the diagram's file, its panel offering Unlock; carried with a real
// pointer and nudged beside another record, it does not move and the other
// does; the note locked, carried and nudged, does not move; one Undo
// unlocks the note; locked as it is picked, it has no handles left; opened
// again the portal is still locked; and Unlock in its panel lets it go.
//
//   node 80_APP/tools/dev/lock_probe.mjs out/ URL
//
// It changes the diagram, so run it on a copy of the repository. Exits 1 if
// a step does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node lock_probe.mjs OUT URL");
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
const VIEW = "lending-onboarding", RECORD = "SYS-LENDING-PORTAL", OTHER = "TS-NET-NAT-LEND-B";
if (!(await fetch(URL + "/api/view?id=" + VIEW)).ok) {
  console.log("skip  no " + VIEW + " here (arrange_probe.mjs makes it)");
  await browser.close();
  process.exit(0);
}
async function open() {
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
  await page.focus("#cy");
  return page;
}
async function keys(page, ...combo) {
  for (const k of combo.slice(0, -1)) await page.keyboard.down(k);
  await page.keyboard.press(combo[combo.length - 1]);
  for (const k of combo.slice(0, -1).reverse()) await page.keyboard.up(k);
  await pause(400);
}
async function saved(page) {
  await pause(400);
  await page.waitForFunction(() => /^(saved|failed)$/.test(window.TerraneApp.Canvas.cv.status), { timeout: 15000 });
}
const locked = (page) => page.evaluate(() => (window.TerraneApp.Canvas.cv.data.locked || []).slice());
const at = (page, id) => page.evaluate((i) => {
  const n = document.getElementById("cy")._cyreg.cy.getElementById(i), r = document.getElementById("cy").getBoundingClientRect();
  const p = n.position(), rp = n.renderedPosition();
  return { x: p.x, y: p.y, sx: r.left + rp.x, sy: r.top + rp.y };
}, id);
async function drag(page, a, dx, dy) {
  await page.mouse.move(a.sx, a.sy);
  await page.mouse.down();
  for (let i = 1; i <= 10; i += 1) await page.mouse.move(a.sx + dx * i / 10, a.sy + dy * i / 10);
  await page.mouse.up();
  await pause(700);
}

const page = await open();
// What an earlier walk left locked is unlocked first: Ctrl+Shift+L turns
// a lock off when everything picked has one.
const left = await locked(page);
if (left.length) {
  await page.evaluate((list) => window.TerraneApp.Canvas.picked(list.filter((x) => /^[A-Z]/.test(x)),
    list.filter((x) => !/^[A-Z]/.test(x))), left);
  await pause(300);
  await keys(page, "Control", "Shift", "l");
  check("what an earlier walk left locked is unlocked", (await locked(page)).length === 0, JSON.stringify(left));
}
await page.evaluate((r) => window.TerraneApp.Canvas.picked([r], []), RECORD);
await pause(300);
await keys(page, "Control", "Shift", "l");
check("Ctrl+Shift+L locks the portal on this diagram", (await locked(page)).indexOf(RECORD) !== -1, JSON.stringify(await locked(page)));
check("and its panel says so and offers Unlock", await page.evaluate(() => {
  const d = document.getElementById("cvDetails");
  return /Locked on this diagram/.test(d.innerText) && Array.from(d.querySelectorAll("button")).some((b) => b.innerText.trim() === "Unlock");
}));
await page.screenshot({ path: `${OUT}/lock.png` });
const p0 = await at(page, RECORD);
await drag(page, p0, 80, 40);
const p1 = await at(page, RECORD);
check("carried, it stays where it is", Math.abs(p1.x - p0.x) < 0.5 && Math.abs(p1.y - p0.y) < 0.5,
  [p1.x - p0.x, p1.y - p0.y].map((v) => v.toFixed(1)).join(", "));
const o0 = await at(page, OTHER);
await page.evaluate((ids) => window.TerraneApp.Canvas.picked(ids, []), [RECORD, OTHER]);
await pause(300);
await keys(page, "Shift", "ArrowRight");
const p2 = await at(page, RECORD), o1 = await at(page, OTHER);
check("nudged beside another record, it does not move and the other does",
  Math.abs(p2.x - p0.x) < 0.5 && Math.abs(o1.x - o0.x - 10) < 0.5, (p2.x - p0.x) + " and " + (o1.x - o0.x));

const own = await page.evaluate(() => (window.TerraneApp.Canvas.cv.data.annotations || []).filter((a) => a.role === "note"));
const note = own[0];
await page.evaluate((k) => window.TerraneApp.Canvas.picked([], [k]), note.key);
await pause(300);
await keys(page, "Control", "Shift", "l");
check("the note locked too", (await locked(page)).indexOf(note.key) !== -1);
// Locked as it is picked: the handles made before the lock went on
// resizing it until the engine made them again.
check("and its handles go, nothing left to resize it by", await page.evaluate(() =>
  !Array.from(document.querySelectorAll(".mg-surface svg *")).some((n) => n.style && /resize/.test(n.style.cursor))));
const nb = (await page.evaluate(() => window.TerraneApp.Canvas.engine.ownBoxes()))[note.key];
const sv = await page.evaluate(() => { const b = document.querySelector(".mg-surface").getBoundingClientRect(); return { x: b.left, y: b.top }; });
await drag(page, { sx: sv.x + nb.x + nb.w / 2, sy: sv.y + nb.y + nb.h / 2 }, 70, 30);
await keys(page, "ArrowDown");
const after = (await page.evaluate(() => window.TerraneApp.Canvas.cv.data.annotations || [])).find((a) => a.key === note.key);
check("carried and nudged, the note stays where it is", JSON.stringify(after.at) === JSON.stringify(note.at),
  JSON.stringify(after.at) + " for " + JSON.stringify(note.at));
await keys(page, "Control", "z");
check("one Undo unlocks the note, and leaves the portal locked", (await locked(page)).indexOf(note.key) === -1
  && (await locked(page)).indexOf(RECORD) !== -1, JSON.stringify(await locked(page)));
await saved(page);
await page.close();

const again = await open();
check("opened again, the portal is still locked", (await locked(again)).indexOf(RECORD) !== -1);
await again.evaluate((r) => window.TerraneApp.Canvas.picked([r], []), RECORD);
await pause(300);
await again.evaluate(() => Array.from(document.querySelectorAll("#cvDetails button")).find((b) => b.innerText.trim() === "Unlock").click());
await pause(300);
check("and Unlock in its panel lets it go", (await locked(again)).indexOf(RECORD) === -1);
await saved(again);
check("no page errors", !errors.length, errors.join(" | "));
await browser.close();
process.exit(failed ? 1 : 0);
