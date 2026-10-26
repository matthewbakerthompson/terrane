// Driving the running app in a headless Chrome, for the tools that need a
// picture of it: the README's screenshots and the review pack. One place for
// the browser, the wide-sheet setup, the wait for a finished layout, and the
// two ways a view is captured -- a drawing through the app's own PNG export,
// a report or timeline as its stage.

import { existsSync } from "node:fs";

import puppeteer from "puppeteer-core";

const CHROMES = [
  process.env.TERRANE_CHROME,
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/usr/bin/google-chrome",
  "/usr/bin/google-chrome-stable",
  "/usr/bin/chromium",
  "/usr/bin/chromium-browser",
].filter(Boolean);

export function findChrome() {
  const chrome = CHROMES.find((p) => existsSync(p));
  if (!chrome) throw new Error("no Chrome found; set TERRANE_CHROME to a chrome.exe or msedge.exe");
  return chrome;
}

export async function launch() {
  return puppeteer.launch({
    executablePath: findChrome(),
    headless: true,
    defaultViewport: { width: 1600, height: 1000, deviceScaleFactor: 1 },
    args: ["--window-size=1600,1000", "--hide-scrollbars", "--no-sandbox"],
  });
}

// A page on the app with the rail folded before its own script runs, so the
// first layout is the wide one rather than a narrow one refitted.
// The canvas is maxGraph's (canvas/engine.js); TERRANE_CANVAS_ENGINE=cytoscape
// opens it as it was before, for a probe's output on the old canvas.
export async function openView(browser, url, hash) {
  const page = await browser.newPage();
  await page.evaluateOnNewDocument((engine) => {
    localStorage.setItem("aac.rail.shut", "1");
    localStorage.setItem("aac.insp.shut", "0");
    localStorage.setItem("aac.tour", "taken");
    if (engine) localStorage.setItem("aac.canvas.engine", engine);
  }, process.env.TERRANE_CANVAS_ENGINE || "");
  await page.goto(url + "/#" + hash, { waitUntil: "networkidle0", timeout: 60000 });
  return page;
}

// The zoom readout is the last thing `drawGraph` writes, after the fit.
export async function settled(page) {
  await page.waitForFunction(
    () => /\d+%/.test((document.getElementById("zoomPct") || {}).textContent || ""),
    { timeout: 30000 },
  );
  await new Promise((r) => setTimeout(r, 600));
}

// The picture the PNG button exports, composed by the app itself: Cytoscape's
// own PNG with the technology lines painted on. A page without that hook
// gives the bare PNG off the drawing cytoscape registers on its container.
export async function drawingPng(page) {
  await settled(page);
  const dataUrl = await page.evaluate(() => {
    if (typeof window.__aacDrawingPng === "function") return window.__aacDrawingPng(2);
    const reg = document.getElementById("cy")._cyreg;
    if (!reg || !reg.cy) throw new Error("no drawing on the page");
    return reg.cy.png({ full: true, scale: 2, bg: "#ffffff" });
  });
  return Buffer.from(dataUrl.split(",")[1], "base64");
}

// A report or a timeline is not a drawing: capture its stage, title and all,
// once its rows or bars are on the page.
export async function stagePng(page, readySelector) {
  await page.waitForSelector(readySelector, { timeout: 30000 });
  await new Promise((r) => setTimeout(r, 400));
  const stage = await page.$("main.stage");
  return Buffer.from(await stage.screenshot({ encoding: "base64" }), "base64");
}

// What a view of a given kind is captured as.
export async function capture(page, kind) {
  if (kind === "report") return stagePng(page, "#dataPanel table tbody tr");
  if (kind === "timeline") return stagePng(page, ".tl-bar");
  if (kind === "assemble") return stagePng(page, ".asm-edit");
  return drawingPng(page);
}
