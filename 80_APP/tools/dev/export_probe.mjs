// Do the export and the overview draw what the sheet draws? On a new
// diagram, a frame dragged out and a note typed into it; the PNG the export
// takes (window.__aacDrawingPng, what Export's PNG and the screenshot tool
// use) must hold the note's yellow and the frame, and the overview the note.
// Then, on lending-onboarding (arrange_probe.mjs makes it, annotate_probe.mjs
// puts a note by the Lending portal), the same with the estate's records:
// the picture is maxGraph's, holding the boxes and the note, and no smaller
// than Cytoscape's of the estate alone. Both pictures and the window land in
// OUT to be looked at.
//
//   node 80_APP/tools/dev/export_probe.mjs out/ URL
//
// It makes a diagram, so run it on a copy of the repository, never on the
// one you commit from. Exits 1 if a step does not do what it says.
import { mkdir, writeFile } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node export_probe.mjs OUT URL");
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
  });
  await page.goto(URL + "/#" + hash, { waitUntil: "networkidle0", timeout: 60000 });
  await page.waitForSelector(".mg-surface svg", { timeout: 30000 });
  await pause(500);
  return page;
}
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
async function saved(page) {
  await pause(400);
  await page.waitForFunction(() => /^(saved|failed)$/.test(window.TerraneApp.Canvas.cv.status), { timeout: 15000 });
}

// How many pixels of a PNG are each of these colors, to two levels either
// way: a picture is judged by what is in it, not by its bytes.
function counted(page, url, colors) {
  return page.evaluate((u, cs) => new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => {
      const c = document.createElement("canvas");
      c.width = image.width;
      c.height = image.height;
      const g = c.getContext("2d");
      g.drawImage(image, 0, 0);
      const d = g.getImageData(0, 0, c.width, c.height).data;
      const want = cs.map((h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16)));
      const n = want.map(() => 0);
      // And how much strong color: the marks are most of it, and a mark
      // that did not load is a gray square.
      let strong = 0;
      for (let i = 0; i < d.length; i += 4) {
        want.forEach((w, j) => {
          if (Math.abs(d[i] - w[0]) <= 2 && Math.abs(d[i + 1] - w[1]) <= 2 && Math.abs(d[i + 2] - w[2]) <= 2) n[j] += 1;
        });
        if (Math.max(d[i], d[i + 1], d[i + 2]) - Math.min(d[i], d[i + 1], d[i + 2]) > 140) strong += 1;
      }
      resolve({ w: image.width, h: image.height, n, strong });
    };
    image.onerror = () => reject(new Error("not a picture"));
    image.src = u;
  }), url, colors);
}
const png = (page) => page.evaluate(() => window.__aacDrawingPng(2));
const cyPng = (page) => page.evaluate(() => document.getElementById("cy")._cyreg.cy.png({ full: true, scale: 2, bg: "#ffffff" }));
const save = (name, url) => writeFile(`${OUT}/${name}.png`, Buffer.from(url.split(",")[1], "base64"));
const NOTE = "#fbefc6";

// The overview shows only while some of the drawing is off the sheet: in as
// far as the wheel goes, then the sheet carried by the Hand until it is.
async function overviewOn(page) {
  const shown = () => page.evaluate(() => !document.getElementById("overview").hidden);
  const mid = await sheetAt(page, 0.5, 0.5);
  await page.mouse.move(mid.x, mid.y);
  for (let i = 0; i < 8 && !(await shown()); i += 1) {
    await page.mouse.wheel({ deltaY: -240 });
    await pause(250);
  }
  for (let i = 0; i < 4 && !(await shown()); i += 1) {
    await page.keyboard.down("Space");
    await drag(page, await sheetAt(page, 0.2, 0.5), await sheetAt(page, 0.75, 0.5));
    await page.keyboard.up("Space");
    await pause(300);
  }
  return shown();
}
const overviewPic = (page) => page.evaluate(() => document.getElementById("overviewPic").toDataURL("image/png"));

// ---- a new diagram: a frame and a note in it
const page = await open("draw");
await page.click("#cvFrame");
await drag(page, await sheetAt(page, 0.3, 0.3), await sheetAt(page, 0.62, 0.7));
await page.click("#cvNote");
const at = await sheetAt(page, 0.4, 0.45);
await page.mouse.click(at.x, at.y);
await page.waitForSelector(".mg-edit", { timeout: 5000 });
await page.keyboard.type("Guardrails on every account");
await page.keyboard.down("Control");
await page.keyboard.press("Enter");
await page.keyboard.up("Control");
await pause(300);
await page.mouse.click(...Object.values(await sheetAt(page, 0.9, 0.9)));
await saved(page);
const roles = await page.evaluate(() => (window.TerraneApp.Canvas.cv.data.annotations || []).map((a) => a.role).sort().join(","));
check("a frame and a note on the sheet", roles === "frame,note", roles);
const boxes = await page.evaluate(() => window.TerraneApp.Canvas.engine.ownBoxes());
const zoom = await page.evaluate(() => document.getElementById("cy")._cyreg.cy.zoom());
const noteBox = Object.values(boxes).find((b) => b.role === "note");
const frameBox = Object.values(boxes).find((b) => b.role === "frame");
let pic = await png(page);
await save("export-new", pic);
let got = await counted(page, pic, [NOTE]);
// The note's own area at two pixels to the unit, less its words.
const noteArea = (noteBox.w / zoom) * (noteBox.h / zoom) * 4;
check("the export holds the note", got.n[0] > noteArea * 0.6, Math.round(got.n[0]) + " of about " + Math.round(noteArea));
// The frame's name sits on a tab half above its top edge (Illustrated),
// and the export holds it.
const TAB_ABOVE = (12 * 1.32 + 4) / 2;
check("and is the size of the frame around it and its tab, sixteen units of white each way",
  Math.abs(got.w - (frameBox.w / zoom + 32) * 2) <= 6 && Math.abs(got.h - (frameBox.h / zoom + TAB_ABOVE + 32) * 2) <= 6,
  got.w + " by " + got.h + " for a frame of " + Math.round(frameBox.w / zoom) + " by " + Math.round(frameBox.h / zoom));
check("the sheet is back at its own zoom after the picture",
  Math.abs((await page.evaluate(() => document.getElementById("cy")._cyreg.cy.zoom())) - zoom) < 1e-9
  && JSON.stringify(await page.evaluate(() => window.TerraneApp.Canvas.engine.ownBoxes())) === JSON.stringify(boxes));
if (await overviewOn(page)) {
  const ov = await overviewPic(page);
  await save("overview-new", ov);
  got = await counted(page, ov, [NOTE]);
  check("the overview draws the note", got.n[0] > 20, got.n[0] + " pixels");
} else {
  check("the overview shows once the drawing is larger than the sheet", false);
}
await page.screenshot({ path: `${OUT}/export-new-window.png` });
await page.close();

// ---- beside the estate's records
const BESIDE = "lending-onboarding";
if ((await fetch(URL + "/api/view?id=" + BESIDE)).ok) {
  const p2 = await open("draw=" + BESIDE);
  await settled(p2);
  await pause(800);
  const own = await p2.evaluate(() => (window.TerraneApp.Canvas.cv.data.annotations || []).filter((a) => a.role === "note").length);
  check("lending-onboarding has a note of its own", own > 0, own + " notes");
  const records = await p2.evaluate(() => Object.keys(window.TerraneApp.Canvas.engine.boxes() || {}).length);
  const ours = await png(p2);
  const theirs = await cyPng(p2);
  await save("export-beside", ours);
  await save("export-beside-cytoscape", theirs);
  const a = await counted(p2, ours, [NOTE]);
  const b = await counted(p2, theirs, [NOTE]);
  check("the export holds the note beside the records", a.n[0] > 200 && b.n[0] === 0, a.n[0] + " here, " + b.n[0] + " in Cytoscape's");
  check("and is no smaller than the estate's alone", a.w >= b.w - 4 && a.h >= b.h - 4, a.w + "x" + a.h + " against " + b.w + "x" + b.h);
  check("with the providers' marks drawn, not left out", a.strong > b.strong * 0.8,
    a.strong + " strongly colored pixels against " + b.strong + " in Cytoscape's");
  check("with every record on it", records > 10, records + " boxes");
  if (await overviewOn(p2)) {
    const ov = await overviewPic(p2);
    await save("overview-beside", ov);
    got = await counted(p2, ov, [NOTE]);
    check("the overview draws the note beside the records", got.n[0] > 4, got.n[0] + " pixels");
  } else {
    check("the overview shows on lending-onboarding zoomed in", false);
  }
  await p2.screenshot({ path: `${OUT}/export-beside-window.png` });
  await p2.close();
} else {
  console.log("skip  lending-onboarding is not here (arrange_probe.mjs makes it)");
}

check("no page errors", !errors.length, errors.join(" | "));
await browser.close();
process.exit(failed ? 1 : 0);
