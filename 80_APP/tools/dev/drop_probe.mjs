// A drawing dropped on the canvas and adopted, walked the way a person
// would: New diagram, a file from the desktop dragged over the sheet, let
// go, the page that says what adopting it would add, an owner chosen, the
// corrections ticked when the drawing says something differently, Adopt,
// and the canvas the first page opens on. A PNG per step into OUT, and a
// line per step saying what the page said.
//
//   node 80_APP/tools/dev/drop_probe.mjs out/ http://127.0.0.1:8020 FILE [OWNER] [correct] [graphite] [name=prefix] [review-only]
//
// `review-only` stops before Adopt, so a clone can be pictured in the other
// tone before it is written to; `from=home` drops the file on an empty
// estate's first page instead of the canvas.
// The drop is the browser's own: a DataTransfer holding the file's bytes,
// dispatched on the sheet as a desktop drag would be. It writes the
// drawing's records into the model: run it on a copy of the repository,
// never on the one you commit from.
import { readFile, mkdir } from "node:fs/promises";
import { basename, resolve } from "node:path";
import { launch } from "../capture.mjs";

const [OUT, URL, FILE, ...rest] = process.argv.slice(2);
if (!OUT || !URL || !FILE) {
  console.error("usage: node drop_probe.mjs OUT URL FILE [OWNER] [correct] [graphite] [name=prefix]");
  process.exit(2);
}
const OWNER = rest.find((a) => /^ORG-/.test(a)) || "";
const CORRECT = rest.includes("correct");
const TONE = rest.includes("graphite") ? "graphite" : "stone";
const PREFIX = (rest.find((a) => a.startsWith("name=")) || "name=drop").slice(5);
const REVIEW_ONLY = rest.includes("review-only");
const HOME = rest.includes("from=home");
const suffix = TONE === "graphite" ? "-graphite" : "";
await mkdir(OUT, { recursive: true });
const pause = (ms) => new Promise((r) => setTimeout(r, ms));
const bytes = (await readFile(FILE)).toString("base64");
const name = basename(FILE);

const browser = await launch();
try {
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1 });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  const shot = async (step) => {
    await page.screenshot({ path: resolve(OUT, PREFIX + "-" + step + suffix + ".png") });
    console.log(step, errors.length ? "ERRORS: " + errors.splice(0).join(" | ") : "ok");
  };
  const say = async (sel) => page.$eval(sel, (n) => n.innerText.replace(/\s+/g, " ").trim()).catch(() => "(none)");

  await page.goto(URL + (HOME ? "/#home&tone=" : "/#draw&tone=") + TONE, { waitUntil: "networkidle0" });
  await pause(1500);
  await shot("new");

  // The file over the sheet, then let go on it.
  const drag = (type) => page.evaluate((type, b64, name, home) => {
    const data = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
    const dt = new DataTransfer();
    dt.items.add(new File([data], name));
    const sheet = home ? document.querySelector(".drop") : document.getElementById("mapSheet");
    const r = sheet.getBoundingClientRect();
    sheet.dispatchEvent(new DragEvent(type, { bubbles: true, cancelable: true, dataTransfer: dt,
      clientX: r.left + r.width / 2, clientY: r.top + r.height / 2 }));
  }, type, bytes, name, HOME);
  await drag("dragenter");
  await drag("dragover");
  await pause(300);
  await shot("dragged-over");
  await drag("drop");
  await page.waitForSelector(".adopt-drawing img, .adopt-nothing", { timeout: 120000 });
  await pause(800);
  await shot("review");
  console.log("  head:", await say(".adopt .st-head"));
  console.log("  side:", await say(".adopt .st-side"));
  console.log("  button:", await say("#adoptGo"));

  if (OWNER) {
    await page.select(".adopt .st-side select", OWNER);
    await pause(300);
  }
  if (CORRECT && (await page.$("#adoptCorrect"))) {
    await page.click("#adoptCorrect");
    await page.waitForFunction(() => !document.querySelector(".adopt-picture.is-busy"), { timeout: 120000 });
    await pause(800);
    await shot("review-corrected");
    console.log("  button:", await say("#adoptGo"));
  }
  if (!REVIEW_ONLY) {
    await page.click("#adoptGo");
    await page.waitForFunction(() => /#draw/.test(location.hash) || /#settings/.test(location.hash), { timeout: 120000 });
    await page.waitForFunction(() => !!document.querySelector(".toast"), { timeout: 30000 });
    // The canvas shows once it has its diagram and has drawn it.
    await page.waitForFunction(() => !document.getElementById("mapSheet").hidden && !!document.querySelector("#cy canvas"),
      { timeout: 120000 });
    await pause(2500);
    await shot("adopted");
    console.log("  toast:", await say(".toast"));
    console.log("  at:", await page.evaluate(() => location.hash));
  }
} finally { await browser.close(); }
