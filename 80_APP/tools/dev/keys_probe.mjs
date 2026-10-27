// Does every tool have its key, and does the canvas say them? On
// lending-onboarding (arrange_probe.mjs makes it): each tool's key chooses
// it, its button pressed; "?" opens the sheet of keys over the status bar
// and Esc closes it, as its button does; and Ctrl+K's palette lists the
// canvas's tools first, each with its key, a tool chosen from it by name.
//
//   node 80_APP/tools/dev/keys_probe.mjs out/ URL
//
// It writes nothing. Exits 1 if a step does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node keys_probe.mjs OUT URL");
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
// The sheet itself has the keyboard, as it has after a click on it.
await page.focus("#cy");

const tool = () => page.evaluate(() => window.TerraneApp.Canvas.cv.tool);
const pressed = (id) => page.evaluate((i) => document.getElementById(i).getAttribute("aria-pressed"), id);
for (const [key, name, button] of [["n", "note", "cvNote"], ["t", "text", "cvText"], ["f", "frame", "cvFrame"],
  ["l", "line", "cvLine"], ["r", "shape", "cvShapes"], ["h", "pan", "cvPan"], ["v", "select", "cvSelect"]]) {
  await page.keyboard.press(key);
  await pause(150);
  const now = await tool();
  check(key.toUpperCase() + " chooses " + name, now === name && (await pressed(button)) === "true", now);
}

// Boundary is Add's own tab now: B opens it there.
check("the toolbar has no Boundary of its own", await page.evaluate(() => !document.getElementById("cvBoundary")));
await page.keyboard.press("b");
await pause(300);
const bounds = await page.evaluate(() => ({ open: !document.getElementById("cvPicker").hidden,
  tab: (document.querySelector("#cvPicker .cv-tab[aria-selected=true]") || {}).textContent,
  tags: Array.from(new Set(Array.from(document.querySelectorAll("#cvPicker .cv-row .cv-tag")).map((t) => t.textContent))) }));
check("B opens Add on its Boundaries tab, every row a boundary", bounds.open && bounds.tab === "Boundaries"
  && bounds.tags.join() === "Boundary", JSON.stringify(bounds));
await page.click("#cvAdd");
await pause(200);
check("and Add closes it", await page.evaluate(() => document.getElementById("cvPicker").hidden));
await page.focus("#cy");

const sheet = () => page.evaluate(() => {
  const s = document.getElementById("cvKeys");
  return { open: !s.hidden && s.offsetHeight > 0, text: s.innerText.replace(/\s+/g, " ") };
});
await page.keyboard.press("?");
await pause(200);
let s = await sheet();
check("? opens the sheet of keys", s.open && /Ctrl\+K/.test(s.text) && /Frame/.test(s.text), s.text.slice(0, 80));
await page.screenshot({ path: `${OUT}/keys-sheet.png` });
await page.keyboard.press("Escape");
await pause(200);
check("Esc closes it", !(await sheet()).open);
await page.click("#cvKeysBtn");
await pause(200);
check("and its button opens it", (await sheet()).open
  && (await page.evaluate(() => document.getElementById("cvKeysBtn").getAttribute("aria-expanded"))) === "true");
await page.click("#cvKeysBtn");
await pause(200);
check("and closes it", !(await sheet()).open);

await page.keyboard.down("Control");
await page.keyboard.press("k");
await page.keyboard.up("Control");
await page.waitForSelector("#palette:not([hidden])", { timeout: 5000 });
const rows = await page.evaluate(() => Array.from(document.querySelectorAll("#paletteList .pal-row")).slice(0, 4)
  .map((r) => r.innerText.replace(/\s+/g, " ").trim()));
check("Ctrl+K lists the canvas's tools first, each with its key", /Select.*V/.test(rows[0] || "") && /Hand.*H/.test(rows[1] || ""),
  JSON.stringify(rows));
await page.keyboard.type("note");
await pause(200);
await page.keyboard.press("Enter");
await pause(300);
check("and a tool chosen from it by name", (await tool()) === "note");
await page.keyboard.press("Escape");
check("no page errors", !errors.length, errors.join(" | "));
await browser.close();
process.exit(failed ? 1 : 0);
