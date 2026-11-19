// Do a diagram's pages work as V16 draws them? On a new diagram with a
// shape on it: the tabs at the sheet's foot show its one page and +; + adds
// a second page, empty, on the sheet, and what is drawn there is its own;
// the first page's tab brings the first back as it was; a double-click
// renames the page on the sheet; a page's menu duplicates it, what is on
// it and all, moves the copy left, and deletes it after asking; the file
// keeps each page in its place, the picture draws a page of its own, and
// the list of diagrams shows the diagram once.
//
//   node 80_APP/tools/dev/pages_probe.mjs out/ URL
//
// It makes a diagram, so run it on a copy of the repository. Exits 1 if a
// step does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node pages_probe.mjs OUT URL");
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
const tabs = () => page.evaluate(() => Array.from(document.querySelectorAll("#cvPages .cv-page"))
  .map((t) => (t.classList.contains("is-on") ? "*" : "") + t.innerText.trim()));
const drawn = () => page.evaluate(() => document.querySelector(".mg-surface").innerText);
const file = () => page.evaluate(() => fetch("/api/view?id=" + window.TerraneApp.Canvas.cv.id).then((r) => r.json()))
  .then((f) => f.data || {});
const add = (label, x) => page.evaluate((l, at) => window.TerraneApp.Canvas.engine.add({ role: "shape", shape: "rounded",
  label: l, box: { x: at, y: 160, w: 160, h: 64 } }), label, x);
async function tab(name) {
  return (await page.evaluateHandle((n) => Array.from(document.querySelectorAll("#cvPages .cv-page"))
    .find((t) => t.innerText.trim() === n) || null, name)).asElement();
}
async function menuItem(words) {
  return (await page.evaluateHandle((w) => Array.from(document.querySelectorAll("#cvPageMenu .cv-page-item"))
    .find((b) => b.innerText.trim().indexOf(w) === 0) || null, words)).asElement();
}

await add("Gateway", 120);
await saved();
check("the tabs show the diagram's one page and +", JSON.stringify(await tabs()) === JSON.stringify(["*Page 1"]) &&
  await page.evaluate(() => !!document.querySelector("#cvPages .cv-page-add")), JSON.stringify(await tabs()));

// + adds a second page, empty, on the sheet.
await page.click("#cvPages .cv-page-add");
await pause(900);
check("+ adds a second page, on the sheet", JSON.stringify(await tabs()) === JSON.stringify(["Page 1", "*Page 2"]), JSON.stringify(await tabs()));
check("and it is empty", !/Gateway/.test(await drawn()));
await add("Settle the batch", 160);
await saved();
let f = await file();
check("what is drawn there is its own, kept under pages", (f.pages || []).length === 1 && f.pages[0].key === "page-2" &&
  (f.pages[0].annotations || []).some((a) => a.label === "Settle the batch") &&
  (f.annotations || []).length === 1 && f.annotations[0].label === "Gateway", JSON.stringify(f.pages));

// The first page's tab brings it back as it was.
await (await tab("Page 1")).click();
await pause(900);
check("the first page's tab brings it back as it was", /Gateway/.test(await drawn()) && !/Settle the batch/.test(await drawn()));

// A double-click renames the page on the sheet.
await (await tab("Page 1")).click({ count: 2 });
await pause(300);
await page.keyboard.down("Control");
await page.keyboard.press("a");
await page.keyboard.up("Control");
await page.keyboard.type("Payments");
await page.keyboard.press("Enter");
await pause(500);
await saved();
check("a double-click renames it", JSON.stringify(await tabs()) === JSON.stringify(["*Payments", "Page 2"]) &&
  (await file()).page === "Payments", JSON.stringify(await tabs()));

// The second page's menu: duplicate it, move the copy left, delete it.
await (await tab("Page 2")).click({ button: "right" });
await pause(300);
check("a right-click opens the page's menu", await page.evaluate(() => !document.getElementById("cvPageMenu").hidden) &&
  JSON.stringify(await page.evaluate(() => Array.from(document.querySelectorAll("#cvPageMenu .cv-page-item"))
    .map((b) => b.querySelector("span").innerText))) ===
  JSON.stringify(["Open", "Rename", "Duplicate", "Move left", "Move right", "Delete the page"]));
await page.screenshot({ path: OUT + "/page-menu.png" });
await (await menuItem("Duplicate")).click();
await pause(900);
check("Duplicate copies the page, what is on it and all, onto the sheet",
  JSON.stringify(await tabs()) === JSON.stringify(["Payments", "Page 2", "*Copy of Page 2"]) && /Settle the batch/.test(await drawn()),
  JSON.stringify(await tabs()));
await (await tab("Copy of Page 2")).click({ button: "right" });
await pause(300);
await (await menuItem("Move left")).click();
await pause(900);
check("Move left puts it before the page it copied", JSON.stringify(await tabs()) ===
  JSON.stringify(["Payments", "*Copy of Page 2", "Page 2"]), JSON.stringify(await tabs()));
await (await tab("Copy of Page 2")).click({ button: "right" });
await pause(300);
await (await menuItem("Delete the page")).click();
await pause(300);
check("Delete asks first", (await tabs()).length === 3 && await page.evaluate(() =>
  /Delete it and all on it/.test(document.getElementById("cvPageMenu").innerText)));
await (await menuItem("Delete it and all on it")).click();
await pause(900);
check("and then deletes it", JSON.stringify(await tabs()) === JSON.stringify(["*Payments", "Page 2"]), JSON.stringify(await tabs()));

// The file, the picture of a page, and the list of diagrams.
await saved();
f = await file();
check("the file keeps each page in its place", f.page === "Payments" && (f.pages || []).length === 1 &&
  f.pages[0].name === "Page 2" && (f.annotations || [])[0].label === "Gateway", JSON.stringify([f.page, f.pages]));
const id = await page.evaluate(() => window.TerraneApp.Canvas.cv.id);
const svg = await page.evaluate((v) => fetch("/api/svg?view=" + v + "--page-2").then((r) => r.text()), id);
check("the picture draws a page of its own", /Settle the batch/.test(svg) && !/Gateway/.test(svg));
const overview = await page.evaluate(() => fetch("/api/overview").then((r) => r.json()));
const listed = (overview.views || []).filter((v) => v.viewId === id || v.viewId.indexOf(id + "--") === 0).map((v) => v.viewId);
check("the list of diagrams shows the diagram once", JSON.stringify(listed) === JSON.stringify([id]), JSON.stringify(listed));
await page.screenshot({ path: OUT + "/pages.png" });
check("no page errors", errors.length === 0, errors.join(" / "));
await browser.close();
process.exit(failed ? 1 : 0);
