// Page and console errors while a hash loads, caught from before the first
// script runs, for the drawing that comes up blank:
//
//   node 80_APP/tools/dev/err_probe.mjs "view=onboarding&p_product=PRD-INSTALLMENT-LENDING"
//   node 80_APP/tools/dev/err_probe.mjs "assemble&open=PRD-REWARDS"
//
// Prints each error with the top of its stack, then whether a drawing is on
// the page and what the zoom readout says. The app must be listening.
import { launch } from "../capture.mjs";

const settle = (ms) => new Promise((r) => setTimeout(r, ms));
let url = "http://127.0.0.1:8020";
let hash = "";
for (let i = 2; i < process.argv.length; i += 1) {
  if (process.argv[i] === "--url") { url = process.argv[++i]; continue; }
  hash = process.argv[i];
}
if (!hash) {
  console.error("usage: node err_probe.mjs [--url URL] <hash>");
  process.exit(2);
}

const browser = await launch();
try {
  const page = await browser.newPage();
  page.on("pageerror", (e) => console.log("pageerror:", (e.stack || e.message || String(e)).split("\n").slice(0, 4).join(" | ")));
  page.on("console", (m) => { if (m.type() === "error" || m.type() === "warning") console.log("console", m.type() + ":", m.text().slice(0, 300)); });
  await page.evaluateOnNewDocument(() => { localStorage.setItem("aac.rail.shut", "1"); });
  await page.goto(url + "/#" + hash, { waitUntil: "networkidle0", timeout: 60000 });
  await settle(3000);
  const state = await page.evaluate(() => ({
    zoom: (document.getElementById("zoomPct") || {}).textContent || "",
    hasDrawing: !!(document.getElementById("cy") && document.getElementById("cy")._cyreg && document.getElementById("cy")._cyreg.cy),
    stage: ((document.querySelector("main.stage") || {}).textContent || "").replace(/\s+/g, " ").trim().slice(0, 160),
  }));
  console.log(JSON.stringify(state));
  await page.close();
} finally {
  await browser.close();
}
