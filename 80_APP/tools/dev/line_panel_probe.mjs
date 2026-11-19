// Does a line picked offer what V16's line panel draws, its first part? On
// a new diagram, two shapes joined by a square line: + Add a label gives
// the line words at its middle, then at its start and its end, each drawn
// where it sits; a place changed carries the words there; Dotted and L draw
// it dotted and heavy, and Rounded turns rounds its turns; the file keeps
// it all, the picture draws it, and one Undo takes the last change back.
//
//   node 80_APP/tools/dev/line_panel_probe.mjs out/ URL
//
// It makes a diagram, so run it on a copy of the repository. Exits 1 if a
// step does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node line_panel_probe.mjs OUT URL");
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
const drawn = () => page.evaluate(() => document.querySelector(".mg-surface").innerText);
async function button(words) {
  return (await page.evaluateHandle((w) => Array.from(document.querySelectorAll("#cvDetails button"))
    .find((b) => b.innerText.trim() === w) || null, words)).asElement();
}
async function addLabel(words) {
  await (await button("+ Add a label")).click();
  await pause(300);
  await page.keyboard.type(words);
  await page.keyboard.press("Enter");
  await pause(500);
}

const keys = await page.evaluate(() => {
  const e = window.TerraneApp.Canvas.engine;
  const a = e.add({ role: "shape", shape: "rounded", label: "Checkout web", box: { x: 80, y: 120, w: 150, h: 64 } });
  const b = e.add({ role: "shape", shape: "rounded", label: "Card ledger", box: { x: 420, y: 380, w: 150, h: 64 } });
  const l = e.add({ role: "line", from: a, to: b, route: "square" });
  e.select([]);
  window.TerraneApp.Canvas.picked([], [l]);
  return { a, b, l };
});
await pause(500);
check("a line picked shows Labels with + Add a label", /Labels/.test(await page.evaluate(() => document.getElementById("cvDetails").innerText)) &&
  !!(await button("+ Add a label")));
await addLabel("reads balances");
check("the first label is its middle's", (await item(keys.l)).label === "reads balances", JSON.stringify(await item(keys.l)));
await addLabel("every five minutes");
await addLabel("read only");
let l = await item(keys.l);
check("the next two are its start's and its end's", l.labels && l.labels.start === "every five minutes" && l.labels.end === "read only",
  JSON.stringify(l.labels));
check("each drawn on the line", await page.evaluate(() => {
  const t = document.querySelector(".mg-surface").innerText;
  return ["reads balances", "every five minutes", "read only"].every((w) => t.indexOf(w) !== -1);
}));
check("and no more labels to add", !(await button("+ Add a label")));
// The end's words carried to the middle's place, freed by emptying it.
await page.evaluate(() => {
  const row = document.querySelector('#cvDetails .cv-label-row[data-at="middle"] input');
  row.value = "";
  row.dispatchEvent(new Event("change"));
});
await pause(400);
await page.evaluate(() => {
  const at = document.querySelector('#cvDetails .cv-label-row[data-at="end"] select');
  at.value = "middle";
  at.dispatchEvent(new Event("change"));
});
await pause(400);
l = await item(keys.l);
check("a place changed carries the words there", l.label === "read only" && !(l.labels || {}).end, JSON.stringify(l));

// Dotted, heavy, and its turns rounded.
async function seg(group, words) {
  await page.evaluate((g, w) => Array.from(document.querySelectorAll('#cvDetails [aria-label="' + g + '"] .cv-seg-b'))
    .find((b) => b.innerText.trim() === w).click(), group, words);
  await pause(400);
}
await seg("Outline", "Dotted");
await seg("How heavy it is", "L");
await seg("Turns", "Rounded turns");
l = await item(keys.l);
check("Dotted, L and Rounded turns", l.look && l.look.line === "dotted" && l.look.weight === "l" && l.turns === "rounded",
  JSON.stringify(l));
check("drawn so on the canvas", await page.evaluate(() => {
  const p = Array.from(document.querySelectorAll(".mg-surface svg path")).find((x) => (x.getAttribute("stroke-dasharray") || "") !== "" &&
    Number(x.getAttribute("stroke-width")) >= 2.4);
  return !!p;
}));
await saved();
const f = await page.evaluate(() => fetch("/api/view?id=" + window.TerraneApp.Canvas.cv.id).then((r) => r.json())).then((x) => x.data);
const line = (f.annotations || []).find((x) => x.key === keys.l) || {};
check("the file keeps it", line.turns === "rounded" && line.labels && line.labels.start === "every five minutes" &&
  line.label === "read only" && line.look.line === "dotted", JSON.stringify(line));
const svg = await page.evaluate(() => fetch("/api/svg?view=" + window.TerraneApp.Canvas.cv.id).then((r) => r.text()));
check("the picture draws it: dotted, heavy, rounded, its words", /stroke-width="2.5" stroke-dasharray="2 3"/.test(svg) &&
  /Q\d/.test(svg) && />every five minutes</.test(svg) && />read only</.test(svg));
await page.screenshot({ path: OUT + "/line-panel.png" });
await page.focus("#cy");
await page.keyboard.down("Control");
await page.keyboard.press("z");
await page.keyboard.up("Control");
await pause(500);
check("one Undo takes the rounded turns back", !(await item(keys.l)).turns);
check("no page errors", errors.length === 0, errors.join(" / "));
await browser.close();
process.exit(failed ? 1 : 0);
