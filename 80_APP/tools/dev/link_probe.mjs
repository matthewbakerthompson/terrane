// Does the words' toolbar's last button link a shape somewhere? On a new
// diagram with two shapes of its own: the first picked, Link clicked shows
// where to type; an address with no https://, http:// or mailto: is
// refused saying so; one that has it is the shape's link, marked at its
// corner, and the mark clicked opens it in a new tab; the file keeps it and
// the engine's picture makes the shape a link; Copy the look painted onto
// the second carries no link; Remove takes it off, and one Undo puts it back.
//
//   node 80_APP/tools/dev/link_probe.mjs out/ URL
//
// The link is the app's own address, so nothing leaves the machine. It
// makes a diagram, so run it on a copy of the repository. Exits 1 if a step
// does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node link_probe.mjs OUT URL");
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
const pick = (k) => page.evaluate((key) => window.TerraneApp.Canvas.picked([], [key]), k).then(() => pause(400));
const file = () => page.evaluate(() => fetch("/api/view?id=" + window.TerraneApp.Canvas.cv.id).then((r) => r.json()))
  .then((f) => (f.data && f.data.annotations) || []);
const marks = () => page.evaluate(() => Array.from(document.querySelectorAll(".mg-surface svg image"))
  .filter((i) => /%3Ccircle/.test(i.getAttribute("href") || i.getAttributeNS("http://www.w3.org/1999/xlink", "href") || ""))
  .map((i) => { const r = i.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; }));
async function typeLink(value) {
  await page.click("#cvDetails .cv-link-in");
  await page.keyboard.down("Control");
  await page.keyboard.press("a");
  await page.keyboard.up("Control");
  await page.keyboard.type(value);
  await page.keyboard.press("Enter");
  await pause(600);
}
async function chord(...combo) {
  for (const k of combo.slice(0, -1)) await page.keyboard.down(k);
  await page.keyboard.press(combo[combo.length - 1]);
  for (const k of combo.slice(0, -1).reverse()) await page.keyboard.up(k);
  await pause(500);
}

const keys = await page.evaluate(() => {
  const e = window.TerraneApp.Canvas.engine;
  const a = e.add({ role: "shape", shape: "rounded", label: "Runbook", box: { x: 80, y: 120, w: 150, h: 64 } });
  const b = e.add({ role: "shape", shape: "rounded", label: "Ledger", box: { x: 320, y: 120, w: 150, h: 64 } });
  e.select([]);
  return { a, b };
});
await saved();
await pick(keys.a);
await page.click('#cvDetails .cv-tool-b[aria-label="Link"]');
await pause(400);
check("Link clicked shows where to type it", await page.evaluate(() => !!document.querySelector("#cvDetails .cv-link-in")));
await typeLink("www.example.com");
check("an address with no https:// is refused, saying so", !(await item(keys.a)).link && await page.evaluate(() =>
  /starts with https:\/\/, http:\/\/ or mailto:/.test(document.getElementById("cvDetails").innerText)));
const link = URL + "/#home";
await typeLink(link);
check("one with it is the shape's link", (await item(keys.a)).link === link, (await item(keys.a)).link);
let shown = await marks();
check("marked at its corner", shown.length === 1, JSON.stringify(shown));
await saved();
check("and the file keeps it", ((await file()).find((x) => x.key === keys.a) || {}).link === link);
const svg = await page.evaluate(() => fetch("/api/svg?view=" + window.TerraneApp.Canvas.cv.id).then((r) => r.text()));
check("the engine's picture makes the shape a link", svg.indexOf('<a href="' + link + '" target="_blank"') !== -1);

if (shown.length) {
  const opened = browser.waitForTarget((t) => t.url() === link, { timeout: 10000 }).then(() => true, () => false);
  await page.mouse.click(shown[0].x, shown[0].y);
  check("the mark clicked opens it in a new tab", await opened);
  await page.bringToFront();
}
await page.screenshot({ path: OUT + "/link.png" });

await pick(keys.a);
await page.focus("#cy");
await chord("Control", "Alt", "KeyC");
await pick(keys.b);
await page.focus("#cy");
await chord("Control", "Alt", "KeyV");
check("Copy the look carries no link", !(await item(keys.b)).link);

await pick(keys.a);
const remove = await page.evaluateHandle(() => Array.prototype.find.call(
  document.querySelectorAll("#cvDetails .cv-link-row button"), (b) => b.textContent === "Remove"));
await remove.asElement().click();
await pause(500);
check("Remove takes it off, and its mark", !(await item(keys.a)).link && (await marks()).length === 0);
await page.focus("#cy");
await chord("Control", "z");
check("one Undo puts it back, marked", (await item(keys.a)).link === link && (await marks()).length === 1);
check("no page errors", errors.length === 0, errors.join(" / "));
await browser.close();
process.exit(failed ? 1 : 0);
