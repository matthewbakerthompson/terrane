// Two things a person lost on every page, walked the way a person loses
// them: the sidebar hidden and looked for again, and the page reloaded.
//
//   node 80_APP/tools/dev/place_probe.mjs out/place http://127.0.0.1:8020
//
// For each page: hide the sidebar, capture the window (<page>-hidden.png),
// and say whether a "Show the sidebar" control is on screen and brings it
// back. Then, with the sidebar open, reload the page and say whether it came
// back to the same place: the same page and what was chosen on it, the
// drawing's zoom and pan, how far down the page was scrolled.
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { launch } from "../capture.mjs";

const OUT = process.argv[2];
const url = process.argv[3];
await mkdir(OUT, { recursive: true });
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

// Every page is reached by pressing what a person presses, so the walk means
// the same before a page had an address of its own as after.
const PAGES = [
  ["home", []],
  ["diagrams", ["#btnDiagrams"]],
  ["drawing", ["#btnDiagrams", "VIEW"]],
  ["model", ["#btnData", "TABLE"]],
  ["library", ["#btnComponents"]],
  ["checks", ["#btnChecks", "TAB:Coverage"]],
  ["flows", ["#btnFlows"]],
  ["settings", ["#btnSettings"]],
  ["help", ["#btnHelp"]],
];

async function press(page, step) {
  if (step === "VIEW") {
    await page.evaluate(() => { window.location.hash = "view=system-context"; });
    await page.waitForFunction(() => /\d+%/.test((document.getElementById("zoomPct") || {}).textContent || ""), { timeout: 30000 });
  } else if (step === "TABLE") {
    // The third table, not the one the page opens on by itself.
    await page.waitForSelector(".data-type", { timeout: 15000 });
    await page.evaluate(() => document.querySelectorAll(".data-type")[2].click());
  } else if (step.startsWith("TAB:")) {
    const label = step.slice(4);
    await page.waitForSelector(".page-tab", { timeout: 15000 });
    await page.evaluate((l) => {
      Array.prototype.find.call(document.querySelectorAll(".page-tab"), (b) => b.textContent.indexOf(l) === 0).click();
    }, label);
  } else {
    await page.waitForSelector(step, { timeout: 15000 });
    await page.click(step);
  }
  await wait(1500);
}

// Where a person is: the address, the page's heading, what is chosen on it,
// the drawing's viewport, the scroll.
function where(page) {
  return page.evaluate(() => {
    const vis = (n) => n && n.offsetParent !== null && !n.closest("[hidden]");
    const h1 = Array.prototype.find.call(document.querySelectorAll("h1"), vis);
    const chosen = document.querySelector(".data-type.is-on, .page-tab.is-on");
    const reg = document.getElementById("cy")._cyreg;
    const cy = reg && reg.cy && vis(document.getElementById("cy")) ? reg.cy : null;
    const panel = document.getElementById("dataPanel");
    return {
      hash: window.location.hash,
      heading: h1 ? h1.textContent.trim() : "",
      chosen: chosen ? (chosen.dataset.id || chosen.textContent.trim().split("\n")[0]).slice(0, 40) : "",
      zoom: cy ? Math.round(cy.zoom() * 1000) / 1000 : null,
      pan: cy ? [Math.round(cy.pan().x), Math.round(cy.pan().y)] : null,
      scroll: panel && !panel.hidden ? Math.round(panel.scrollTop) : null,
    };
  });
}

const browser = await launch();
const lines = [];
try {
  for (const [name, steps] of PAGES) {
    // ---- the sidebar, hidden here ------------------------------------
    const page = await browser.newPage();
    await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1 });
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.evaluateOnNewDocument(() => {
      try { if (!sessionStorage.getItem("probe.started")) { localStorage.setItem("aac.rail.shut", "0"); sessionStorage.setItem("probe.started", "1"); } } catch (e) { /* none */ }
    });
    await page.goto(url + "/#home", { waitUntil: "networkidle0", timeout: 60000 });
    await wait(1200);
    for (const step of steps) await press(page, step);
    await page.click("#btnRail");
    await wait(700);
    await writeFile(resolve(OUT, name + "-hidden.png"), await page.screenshot());
    const back = await page.evaluate(() => {
      const shown = Array.prototype.filter.call(document.querySelectorAll('[aria-label="Show the sidebar"]'), (n) => {
        const r = n.getBoundingClientRect();
        return n.offsetParent !== null && r.width > 0 && r.right > 0 && r.left < window.innerWidth && r.top < window.innerHeight;
      });
      if (!shown.length) return "no way back on screen";
      shown[0].click();
      const rail = document.getElementById("rail");
      return rail.offsetWidth > 100 ? "way back works" : "a button, but the sidebar stays hidden";
    });

    // ---- the place, across a reload ----------------------------------
    if (name === "drawing") {
      await page.evaluate(() => {
        const cy = document.getElementById("cy")._cyreg.cy;
        cy.zoom({ level: cy.zoom() * 1.8, renderedPosition: { x: 300, y: 260 } });
        cy.panBy({ x: -140, y: -90 });
      });
      await wait(600);
    }
    if (name === "diagrams" || name === "library") {
      await page.evaluate(() => { document.getElementById("dataPanel").scrollTop = 700; });
      await wait(600);
    }
    const before = await where(page);
    await page.reload({ waitUntil: "networkidle0", timeout: 60000 });
    await wait(2500);
    const after = await where(page);
    const lost = ["hash", "heading", "chosen", "zoom", "pan", "scroll"].filter((k) => JSON.stringify(before[k]) !== JSON.stringify(after[k]));
    lines.push({ page: name, sidebar: back, reload: lost.length ? "lost " + lost.join(", ") : "same place", before, after, errors });
    console.log(name.padEnd(9), back.padEnd(40), lost.length ? "reload lost: " + lost.join(", ") : "reload: same place",
      errors.length ? " ERRORS: " + errors.join(" | ") : "");
    await page.close();
  }
} finally {
  await browser.close();
}
await writeFile(resolve(OUT, "place.json"), JSON.stringify(lines, null, 2));
