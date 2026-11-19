// Does a line's end take a head from four notations, as V16 draws it? On
// a new diagram, two shapes joined by a line: picked, its panel names each
// end, "At Customer" and "At Order", with the head it has; the end's picker
// opens "The end at Order", its heads by notation, the one it has marked;
// Many at one end and One at the other are in the file, the picture and
// the pickers; Flow dashes the line and Triggering gives it back; Assignment
// puts a dot at an end with nothing; Escape shuts the heads with nothing
// changed; and one Undo takes the last head back.
//
//   node 80_APP/tools/dev/heads_probe.mjs out/ URL
//
// It makes a diagram, so run it on a copy of the repository. Exits 1 if a
// step does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node heads_probe.mjs OUT URL");
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
const ends = () => page.evaluate(() => Array.from(document.querySelectorAll("#cvDetails .cv-end-row")).map((r) => ({
  at: r.querySelector(".cv-end-at").innerText, head: r.querySelector(".cv-head-name").innerText })));
async function choose(place, head) {
  await page.click('#cvDetails .cv-end-row[data-at="' + place + '"] .cv-head-pick');
  await pause(300);
  await page.click('#cvHeads .cv-head-opt[data-head="' + head + '"]');
  await pause(500);
}
async function picture() {
  return page.evaluate(() => fetch("/api/svg?view=" + window.TerraneApp.Canvas.cv.id).then((r) => r.text()));
}

const keys = await page.evaluate(() => {
  const e = window.TerraneApp.Canvas.engine;
  const a = e.add({ role: "shape", shape: "rounded", label: "Customer", box: { x: 80, y: 120, w: 150, h: 64 } });
  const b = e.add({ role: "shape", shape: "rounded", label: "Order", box: { x: 420, y: 120, w: 150, h: 64 } });
  const l = e.add({ role: "line", from: a, to: b });
  e.select([]);
  return { a, b, l };
});
await saved();
await page.evaluate((k) => window.TerraneApp.Canvas.picked([], [k]), keys.l);
await pause(500);
check("a line picked names each end with the head it has", JSON.stringify(await ends()) ===
  JSON.stringify([{ at: "At Customer", head: "Nothing" }, { at: "At Order", head: "Arrow" }]), JSON.stringify(await ends()));

// The end at Order's heads.
await page.click('#cvDetails .cv-end-row[data-at="end"] .cv-head-pick');
await pause(400);
const pop = await page.evaluate(() => {
  const p = document.getElementById("cvHeads");
  if (!p) return null;
  return { title: p.querySelector(".cv-heads-h").innerText, groups: Array.from(p.querySelectorAll(".cv-label")).map((g) => g.innerText),
    count: p.querySelectorAll(".cv-head-opt").length,
    marked: Array.from(p.querySelectorAll('.cv-head-opt[aria-pressed="true"]')).map((b) => b.dataset.head) };
});
check("its picker opens the end's heads by notation, the one it has marked", pop && pop.title === "The end at Order" &&
  pop.groups.join(",") === "Plain,UML,Crow's foot,ArchiMate" && pop.count === 19 && pop.marked.join() === "arrow",
  JSON.stringify(pop));
await page.screenshot({ path: OUT + "/heads-open.png" });
await page.keyboard.press("Escape");
await pause(300);
check("Escape shuts it with nothing changed", !(await page.$("#cvHeads")) && !(await item(keys.l)).heads);

// Crow's foot: Many at Order, One at Customer.
await choose("end", "many");
await choose("start", "one");
let l = await item(keys.l);
check("Many at one end and One at the other are in the file", JSON.stringify(l.heads) === '{"start":"one","end":"many"}' &&
  !l.ends, JSON.stringify(l));
check("and the pickers say them", JSON.stringify((await ends()).map((e) => e.head)) === '["One","Many"]');
await saved();
let svg = await picture();
check("the picture draws the crow's foot and the bars", svg.includes('d="M420 147.5 L412 152 L420 156.5"') &&
  svg.includes('d="M234 156.5 L234 147.5"') && svg.includes('d="M238 156.5 L238 147.5"'),
  (svg.match(/<g class="own" data-key="line-1"[\s\S]*?<\/g>/) || [""])[0].slice(0, 600));

// ArchiMate: Flow dashes the line, Triggering gives it back.
await choose("end", "flow");
l = await item(keys.l);
check("Flow dashes the line, as ArchiMate draws it", l.heads.end === "flow" && (l.look || {}).line === "dashed", JSON.stringify(l));
check("and the panel's look says so", await page.evaluate(() => {
  const b = Array.from(document.querySelectorAll('#cvDetails [aria-label="Outline"] .cv-seg-b')).find((x) => x.getAttribute("aria-checked") === "true");
  return b && b.innerText === "Dashed";
}));
await choose("end", "triggering");
l = await item(keys.l);
check("Triggering gives it its plain line back", l.heads.end === "triggering" && !(l.look || {}).line, JSON.stringify(l));

// Assignment puts a dot at an end with nothing.
await choose("start", "none");
await choose("end", "assignment");
l = await item(keys.l);
check("Assignment puts a dot at the other end", JSON.stringify(l.heads) === '{"start":"dot","end":"assignment"}', JSON.stringify(l.heads));
await saved();
svg = await picture();
check("and the picture draws the dot", /<circle cx="233" cy="152" r="3" fill=/.test(svg), (svg.match(/<circle[^>]*>/g) || []).join(" "));
await page.screenshot({ path: OUT + "/heads.png" });

// A click elsewhere shuts the heads; one Undo takes the last head back.
await page.click('#cvDetails .cv-end-row[data-at="end"] .cv-head-pick');
await pause(300);
await page.mouse.click(700, 700);
await pause(300);
check("a click elsewhere shuts them", !(await page.$("#cvHeads")));
await page.focus("#cy");
await page.keyboard.down("Control");
await page.keyboard.press("z");
await page.keyboard.up("Control");
await pause(500);
l = await item(keys.l);
check("one Undo takes the last head back", JSON.stringify(l.heads) === '{"start":"none","end":"triggering"}', JSON.stringify(l.heads));
check("no page errors", errors.length === 0, errors.join(" / "));
await browser.close();
process.exit(failed ? 1 : 0);
