// Do lines hop where they cross? On a new diagram, a line across and a line
// down through it, drawn after: the second hops the first once and the
// first hops nothing; Line jumps in the status bar turned off, nothing hops
// and the browser keeps it off; on again, the hop is back; the first line
// moved clear, the second is drawn straight again. Then on lending-
// onboarding (arrange_probe.mjs makes it), the estate's lines hop where
// they cross.
//
//   node 80_APP/tools/dev/jumps_probe.mjs out/ URL
//
// It makes a diagram, so run it on a copy of the repository. Exits 1 if a
// step does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node jumps_probe.mjs OUT URL");
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
    localStorage.removeItem("aac.canvas.jumps");
  });
  await page.goto(URL + "/#" + hash, { waitUntil: "networkidle0", timeout: 60000 });
  await page.waitForFunction(() => window.TerraneApp.Canvas.engine && window.TerraneApp.Canvas.engine.live(), { timeout: 30000 });
  await settled(page);
  await pause(700);
  await page.bringToFront();
  return page;
}
const hops = (page) => page.evaluate(() => window.TerraneApp.Canvas.engine.hops());
const pressed = (page) => page.evaluate(() => document.getElementById("cvJumps").getAttribute("aria-pressed"));

const page = await open("draw");
const keys = await page.evaluate(() => {
  const e = window.TerraneApp.Canvas.engine;
  const across = e.add({ role: "line", from: [100, 240], to: [460, 240], fromAt: { x: 100, y: 240 }, toAt: { x: 460, y: 240 } });
  const down = e.add({ role: "line", from: [280, 100], to: [280, 380], fromAt: { x: 280, y: 100 }, toAt: { x: 280, y: 380 } });
  e.select([]);
  return { across, down };
});
await pause(500);
let h = await hops(page);
check("Line jumps is on to begin with", (await pressed(page)) === "true");
check("the line drawn second hops the first once, the first hops nothing",
  h["a:" + keys.down] === 1 && h["a:" + keys.across] === 0, JSON.stringify(h));
await page.screenshot({ path: `${OUT}/jumps-own.png`, clip: { x: 60, y: 160, width: 600, height: 420 } });
await page.click("#cvJumps");
await pause(400);
h = await hops(page);
check("turned off, nothing hops, and the browser keeps it off", (await pressed(page)) === "false"
  && Object.values(h).every((n) => n === 0)
  && (await page.evaluate(() => localStorage.getItem("aac.canvas.jumps"))) === "0", JSON.stringify(h));
await page.click("#cvJumps");
await pause(400);
h = await hops(page);
check("on again, the hop is back", (await pressed(page)) === "true" && h["a:" + keys.down] === 1, JSON.stringify(h));
await page.evaluate((k) => window.TerraneApp.Canvas.engine.nudge([k], 0, 200), keys.across);
await pause(500);
h = await hops(page);
check("the first line moved clear, the second is drawn straight again", h["a:" + keys.down] === 0, JSON.stringify(h));
await page.close();

if (!(await fetch(URL + "/api/view?id=lending-onboarding")).ok) {
  console.log("skip  no lending-onboarding here (arrange_probe.mjs makes it)");
} else {
  const lend = await open("draw=lending-onboarding");
  const all = await hops(lend);
  const total = Object.values(all).reduce((a, b) => a + b, 0);
  const estate = Object.keys(all).filter((id) => id.indexOf("e:") === 0 && all[id] > 0).length;
  check("on lending-onboarding the estate's lines hop where they cross", total > 0 && estate > 0,
    total + " hops on " + estate + " of the estate's lines");
  await lend.screenshot({ path: `${OUT}/jumps-lending.png` });
  await lend.close();
}
check("no page errors", !errors.length, errors.join(" | "));
await browser.close();
process.exit(failed ? 1 : 0);
