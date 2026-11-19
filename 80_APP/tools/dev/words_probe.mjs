// Do the Style tab's Styles and the words' toolbar do what V16 draws? On a
// new diagram with a shape and a note of its own: the shape picked shows
// five styles, and Risk clicked is its look, its chip ticked; Italic and
// "To the left" clicked set its words, which maxGraph draws so, and one Undo
// takes the last back; "Save this as a style" and a name typed keep its look
// in the diagram's file; the note picked takes that style with a click, and
// "A list of its lines" makes its lines a list, drawn with bullets on the
// canvas and in the engine's picture; and the style's own button takes it
// out of the file again.
//
//   node 80_APP/tools/dev/words_probe.mjs out/ URL
//
// It makes a diagram, so run it on a copy of the repository. Exits 1 if a
// step does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node words_probe.mjs OUT URL");
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
const look = (k) => page.evaluate((key) => Object.assign({}, (window.TerraneApp.Canvas.engine.item(key) || {}).look), k);
const pick = (k) => page.evaluate((key) => window.TerraneApp.Canvas.picked([], [key]), k).then(() => pause(400));
const file = () => page.evaluate(() => fetch("/api/view?id=" + window.TerraneApp.Canvas.cv.id).then((r) => r.json()))
  .then((f) => f.data || {});
async function press(selector) {
  await page.click(selector);
  await pause(500);
}
const chip = (name) => '#cvDetails .cv-style[title="' + name + '"]';
const label = (k) => page.evaluate((key) => {
  const e = window.TerraneApp.Canvas.engine, b = e.ownBoxes()[key], s = document.querySelector(".mg-surface");
  const r = s.getBoundingClientRect(), x = r.left + b.x + b.w / 2, y = r.top + b.y + b.h / 2;
  const hit = Array.from(s.querySelectorAll("foreignObject div")).filter((d) => {
    const q = d.getBoundingClientRect();
    // The innermost only: maxGraph wraps a label in divs of its own, and
    // each would say its words again.
    return q.left <= x && x <= q.right && q.top <= y + b.h / 2 && y - b.h / 2 <= q.bottom && d.textContent.trim()
      && !d.querySelector("div");
  });
  return hit.map((d) => d.getAttribute("style") + " | " + d.textContent).join(" || ");
}, k);
async function undo() {
  await page.focus("#cy");
  await page.keyboard.down("Control");
  await page.keyboard.press("z");
  await page.keyboard.up("Control");
  await pause(600);
}

const keys = await page.evaluate(() => {
  const e = window.TerraneApp.Canvas.engine;
  const a = e.add({ role: "shape", shape: "rounded", label: "Payments API\nREST, three regions", box: { x: 80, y: 120, w: 150, h: 64 } });
  const n = e.add({ role: "note", label: "Moves in Q2\nKeeps its keys", box: { x: 300, y: 120, w: 170, h: 90 } });
  e.select([]);
  return { a, n };
});
await saved();
await pick(keys.a);
check("a shape picked shows the five styles", await page.evaluate(() =>
  Array.from(document.querySelectorAll("#cvDetails .cv-style")).map((b) => b.title).join(",") === "Service,Data,Outside,Risk,Quiet"));
await press(chip("Risk"));
let mine = await look(keys.a);
check("Risk clicked is its look", mine.fill === "rose" && mine.weight === "l" && mine.bold === true, JSON.stringify(mine));
check("and its chip is ticked", await page.evaluate((s) => document.querySelector(s).getAttribute("aria-pressed") === "true",
  chip("Risk")));

await press('#cvDetails .cv-tool-b[aria-label="Italic"]');
await press('#cvDetails .cv-tool-b[aria-label="To the left"]');
mine = await look(keys.a);
check("Italic and To the left set its words", mine.italic === true && mine.align === "left", JSON.stringify(mine));
check("which maxGraph draws so", /font-style:italic/.test(await label(keys.a)), await label(keys.a));
check("and the Risk chip is no longer ticked", await page.evaluate((s) => document.querySelector(s).getAttribute("aria-pressed") === "false",
  chip("Risk")));
await undo();
mine = await look(keys.a);
check("one Undo takes the last back", mine.italic === true && !mine.align, JSON.stringify(mine));

await pick(keys.a);
await press('#cvDetails .cv-link-b');
await page.type('#cvDetails .cv-style-form input', "Edge case");
await page.keyboard.press("Enter");
await pause(600);
await saved();
const kept = (await file()).saved_styles || [];
check("Save this as a style keeps its look in the file by name", kept.length === 1 && kept[0].name === "Edge case"
  && kept[0].look.fill === "rose" && kept[0].look.italic === true, JSON.stringify(kept));
check("and its chip joins the five", await page.evaluate((s) => !!document.querySelector(s), chip("Edge case")));

await pick(keys.n);
await press(chip("Edge case"));
const ln = await look(keys.n);
check("the note takes that style with a click", ln.fill === "rose" && ln.italic === true && ln.bold === true, JSON.stringify(ln));
await press('#cvDetails .cv-tool-b[aria-label="A list of its lines"]');
check("A list of its lines makes it a list", (await look(keys.n)).list === true);
check("drawn with bullets on the canvas", (await label(keys.n)).split("•").length - 1 === 2, await label(keys.n));
await saved();
const svg = await page.evaluate(() => fetch("/api/svg?view=" + window.TerraneApp.Canvas.cv.id).then((r) => r.text()));
const note = (svg.split('data-key="' + keys.n + '"')[1] || "").split("</g>")[0];
check("and in the engine's picture", (note.match(/>•<\/text>/g) || []).length === 2 && /font-style="italic"/.test(note),
  note.slice(0, 200));
await page.screenshot({ path: OUT + "/words.png" });

await page.hover('#cvDetails .cv-style-wrap:last-child');
await pause(200);
await press('#cvDetails .cv-style-x');
await saved();
check("its own button takes the style out of the file", !((await file()).saved_styles || []).length,
  JSON.stringify((await file()).saved_styles));
check("no page errors", errors.length === 0, errors.join(" / "));
await browser.close();
process.exit(failed ? 1 : 0);
