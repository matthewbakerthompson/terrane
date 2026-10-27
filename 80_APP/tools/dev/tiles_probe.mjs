// Does a diagram draw its own as Icon tiles, and does a tile carry the
// providers' marks? On lending-onboarding (arrange_probe.mjs makes it): with
// nothing picked, the panel's Look turned to Icon tiles with a real pointer,
// the canvas draws tiles and the file says `look: tiles`; a shape added and
// picked offers its Icon field, the plain icons first; the AWS set chosen
// lists the AWS marks, and Lambda clicked is the shape's icon, drawn in the
// tile's place on the canvas, kept in the file, carried into the canvas's
// own export and drawn by the engine's picture; "kubernetes" typed in the
// field's box finds the three clouds' clusters, and a word nothing has says
// so; one Undo takes the mark off; and Illustrated chosen again, the file
// says nothing of its look.
//
//   node 80_APP/tools/dev/tiles_probe.mjs out/ URL
//
// It changes the diagram, so run it on a copy of the repository. Exits 1 if
// a step does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node tiles_probe.mjs OUT URL");
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
const VIEW = "lending-onboarding";
if (!(await fetch(URL + "/api/view?id=" + VIEW)).ok) {
  console.log("skip  no " + VIEW + " here (arrange_probe.mjs makes it)");
  await browser.close();
  process.exit(0);
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
await page.goto(URL + "/#draw=" + VIEW, { waitUntil: "networkidle0", timeout: 60000 });
await page.waitForSelector(".mg-surface.takes-pointer svg", { timeout: 30000 });
await settled(page);
await pause(600);
await page.bringToFront();
async function saved() {
  await pause(400);
  await page.waitForFunction(() => /^(saved|failed)$/.test(window.TerraneApp.Canvas.cv.status), { timeout: 15000 });
}
const file = () => page.evaluate((v) => fetch("/api/view?id=" + v).then((r) => r.json()), VIEW).then((f) => f.data || {});
const item = (k) => page.evaluate((key) => Object.assign({}, window.TerraneApp.Canvas.engine.item(key)), k);
const pick = (keys) => page.evaluate((ks) => window.TerraneApp.Canvas.picked([], ks), keys).then(() => pause(400));
async function lookTo(word) {
  await pick([]);
  const b = await page.evaluateHandle((w) => Array.prototype.find.call(
    document.querySelectorAll('#cvDetails .cv-seg[aria-label="Look"] .cv-seg-b'), (x) => x.textContent === w), word);
  await b.asElement().click();
  await pause(600);
}

// The look, from the diagram's own panel.
await lookTo("Icon tiles");
check("Icon tiles chosen, the canvas draws tiles", await page.evaluate(() => window.TerraneApp.Canvas.engine.look()) === "tiles");
await saved();
check("and the file says look: tiles", (await file()).look === "tiles", String((await file()).look));

// A shape, to the right of what is there, picked.
const key = await page.evaluate(() => {
  const e = window.TerraneApp.Canvas.engine, boxes = e.ownBoxes() || {};
  let right = 0, top = 0;
  Object.keys(boxes).forEach((k) => { right = Math.max(right, boxes[k].x + boxes[k].w); top = boxes[k].y; });
  return e.add({ role: "shape", shape: "rounded", label: "Fraud scoring\nUnder 50 ms", box: { x: right + 80, y: top, w: 150, h: 64 } });
});
await saved();
await pick([key]);
const field = () => page.evaluate(() => {
  const set = document.querySelector('#cvDetails select[aria-label="Icon set"]');
  const grid = document.querySelector('#cvDetails .cv-icons');
  return set && grid ? { set: set.value, buttons: grid.querySelectorAll(".cv-icon-b").length,
    ticked: (grid.querySelector('[aria-checked="true"]') || {}).title || "",
    titles: Array.prototype.map.call(grid.querySelectorAll(".cv-icon-b"), (b) => b.title),
    none: (grid.querySelector(".cv-icons-none") || {}).textContent || "" } : null;
});
let f = await field();
check("the shape offers its Icon field, the plain icons first", f && f.set === "plain" && f.buttons >= 24 && f.ticked === "box",
  JSON.stringify(f && { set: f.set, buttons: f.buttons, ticked: f.ticked }));

// The AWS set, and Lambda clicked.
await page.select('#cvDetails select[aria-label="Icon set"]', "aws");
await page.waitForFunction(() => document.querySelectorAll("#cvDetails .cv-icons img").length > 0, { timeout: 15000 });
f = await field();
check("the AWS set lists the AWS marks", f.buttons === 64 && f.titles.every((t) => t.indexOf("AWS: ") === 0), String(f.buttons));
const lambda = await page.$('#cvDetails .cv-icon-b[title="AWS: lambda"]');
await lambda.click();
await pause(600);
check("Lambda clicked is the shape's icon", ((await item(key)).look || {}).icon === "aws/lambda", JSON.stringify((await item(key)).look));
check("drawn in the tile's place on the canvas", await page.evaluate(() =>
  !!document.querySelector('.mg-surface img[src="icons/aws/lambda.svg"]')));
await saved();
const kept = ((await file()).annotations || []).find((a) => a.key === key) || {};
check("and kept in the file", (kept.look || {}).icon === "aws/lambda", JSON.stringify(kept.look));
f = await field();
check("the panel opens on its set with it ticked", f.set === "aws" && f.ticked === "AWS: lambda", f.set + " / " + f.ticked);

// The canvas's own export carries the mark: Lambda's orange is in the PNG.
const orange = await page.evaluate(async () => {
  const url = await window.__aacDrawingPng(1);
  const img = new Image();
  await new Promise((resolve, reject) => { img.onload = resolve; img.onerror = reject; img.src = url; });
  const c = document.createElement("canvas");
  c.width = img.width; c.height = img.height;
  const g = c.getContext("2d");
  g.drawImage(img, 0, 0);
  const d = g.getImageData(0, 0, c.width, c.height).data;
  let n = 0;
  for (let i = 0; i < d.length; i += 4) if (Math.abs(d[i] - 237) < 12 && Math.abs(d[i + 1] - 113) < 12 && d[i + 2] < 20) n += 1;
  return n;
});
check("the canvas's export carries the mark", orange > 200, orange + " orange pixels");
const svg = await page.evaluate((v) => fetch("/api/svg?view=" + v).then((r) => r.text()), VIEW);
check("and the engine's picture draws it", svg.indexOf('data-key="' + key + '" data-role="shape"') !== -1 &&
  /<image [^>]*href="data:image\/svg\+xml;base64,/.test(svg));

// A word finds a mark in every set.
await page.type('#cvDetails .cv-icon-find', "kubernetes");
await pause(500);
f = await field();
check("kubernetes finds the three clouds' clusters", ["AWS: eks", "Azure: aks", "Google Cloud: gke"].every((t) => f.titles.indexOf(t) !== -1),
  f.titles.join(", "));
await page.click('#cvDetails .cv-icon-find', { clickCount: 3 });
await page.keyboard.type("zzzz");
await pause(500);
f = await field();
check("a word nothing has says so", f.buttons === 0 && f.none === "No icon matches that.", f.none);

// One Undo takes the mark off.
await page.focus("#cy");
await page.keyboard.down("Control");
await page.keyboard.press("z");
await page.keyboard.up("Control");
await pause(600);
check("one Undo takes the mark off", !((await item(key)).look || {}).icon, JSON.stringify((await item(key)).look));
await page.screenshot({ path: OUT + "/tiles.png" });

// Put back as it was: the shape gone, Illustrated, and the file silent.
await page.evaluate((k) => window.TerraneApp.Canvas.engine.remove([k]), key);
await saved();
await lookTo("Illustrated");
await saved();
const back = await file();
check("Illustrated chosen again, the file says nothing of its look", back.look === undefined, String(back.look));
check("no page errors", errors.length === 0, errors.join(" / "));
await browser.close();
process.exit(failed ? 1 : 0);
