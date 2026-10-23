// The onboarding tour, walked as a first visit walks it: the offer on Home,
// Start the tour, then each step done the way the card asks (half by the
// person's own press, half by Show me), to the end card.
//
//   node 80_APP/tools/dev/tour_probe.mjs out/tour http://127.0.0.1:8020 [graphite]
//
// A PNG of the window per step (`tour-<n>.png`), and a line each: what the
// card says, where the ring is, whether the pointer rests inside it, and
// what moved the tour on. Then the ways out: Esc, the close button, Not now
// and Don't offer this again, and whether the offer comes back after each.
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { launch } from "../capture.mjs";

const OUT = process.argv[2];
const url = process.argv[3];
const tone = process.argv[4] === "graphite" ? "graphite" : "stone";
await mkdir(OUT, { recursive: true });
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const browser = await launch();
const errors = [];

async function fresh(keep) {
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1 });
  page.on("pageerror", (e) => errors.push(e.message));
  await page.evaluateOnNewDocument((t, k) => {
    if (sessionStorage.getItem("probe")) return;
    sessionStorage.setItem("probe", "1");
    localStorage.clear();
    localStorage.setItem("terrane.tone", t);
    for (const [key, value] of Object.entries(k || {})) localStorage.setItem(key, value);
  }, tone, keep || {});
  await page.goto(url + "/#home", { waitUntil: "networkidle0", timeout: 60000 });
  await wait(1500);
  return page;
}

const state = (page) => page.evaluate(() => {
  const card = document.querySelector(".tour-card:not(.tour-offer)");
  const ring = document.querySelector(".tour-ring");
  const ptr = document.querySelector(".tour-pointer");
  const r = ring && !ring.hidden ? ring.getBoundingClientRect() : null;
  const m = ptr ? new DOMMatrix(getComputedStyle(ptr).transform) : null;
  const tip = m ? { x: m.m41 + 1.5, y: m.m42 + 1.5 } : null;
  return {
    step: card ? card.querySelector(".tc-step").textContent : "",
    title: card ? card.querySelector(".tc-title").textContent : "",
    ring: r ? [r.left, r.top, r.width, r.height].map(Math.round) : null,
    inside: !!(r && tip && tip.x >= r.left && tip.x <= r.right && tip.y >= r.top && tip.y <= r.bottom),
    away: card ? !card.querySelector(".tc-away").hidden : false,
    hash: window.location.hash,
  };
});

async function settle(page, title) {
  await page.waitForFunction((t) => {
    const c = document.querySelector(".tour-card:not(.tour-offer) .tc-title");
    return c && c.textContent === t && !document.querySelector(".tour-ring").hidden;
  }, { timeout: 20000 }, title);
  await wait(1100);
}

const STEPS = [
  ["Every diagram, by layer", "press", "#btnDiagrams"],
  ["Open one", "showme"],
  ["Press a box", "press-box"],
  ["What depends on it", "showme"],
  ["Move around", "next"],
  ["The model underneath", "press", "#btnData"],
  ["Draw your own", "showme"],
  ["That is the tour", "end"],
];

try {
  let page = await fresh();
  const offered = await page.$(".tour-offer");
  console.log("offer on Home:", !!offered);
  await writeFile(resolve(OUT, "tour-offer.png"), await page.screenshot());
  await page.evaluate(() => Array.prototype.find.call(document.querySelectorAll(".tour-offer .btn"), (b) => b.textContent === "Start the tour").click());
  for (const [i, [title, how, sel]] of STEPS.entries()) {
    await settle(page, title);
    const s = await state(page);
    await writeFile(resolve(OUT, "tour-" + (i + 1) + ".png"), await page.screenshot());
    console.log(String(i + 1).padEnd(3), s.step.padEnd(12), title.padEnd(24), "ring", JSON.stringify(s.ring), s.inside ? "pointer in ring" : "POINTER OUTSIDE",
      s.away ? "AWAY" : "", "|", how, s.hash);
    if (how === "press") await page.click(sel);
    else if (how === "press-box") {
      await page.evaluate(() => {
        const r = document.querySelector(".tour-ring").getBoundingClientRect();
        const el = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
        el.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, clientX: r.left + r.width / 2, clientY: r.top + r.height / 2 }));
        el.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, clientX: r.left + r.width / 2, clientY: r.top + r.height / 2 }));
      });
      await page.mouse.click(...(await page.evaluate(() => { const r = document.querySelector(".tour-ring").getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; })));
    } else if (how === "showme" || how === "next") {
      const label = how === "showme" ? "Show me" : "Next";
      await page.evaluate((l) => Array.prototype.find.call(document.querySelectorAll(".tour-card .btn"), (b) => b.textContent === l).click(), label);
    }
  }
  console.log("the offer after taking the tour:", await page.evaluate(() => { window.location.hash = "home"; return true; }) && (await wait(1200), !!(await page.$(".tour-offer"))));
  await page.close();

  // Back, and the ways out.
  page = await fresh();
  await page.evaluate(() => Array.prototype.find.call(document.querySelectorAll(".tour-offer .btn"), (b) => b.textContent === "Start the tour").click());
  await settle(page, "Every diagram, by layer");
  await page.evaluate(() => Array.prototype.find.call(document.querySelectorAll(".tour-card .btn"), (b) => b.textContent === "Next").click());
  await settle(page, "Open one");
  await page.evaluate(() => Array.prototype.find.call(document.querySelectorAll(".tour-card .btn"), (b) => b.textContent === "Next").click());
  await settle(page, "Press a box");
  console.log("Next, Next lands on:", (await state(page)).title, (await state(page)).hash);
  await page.evaluate(() => Array.prototype.find.call(document.querySelectorAll(".tour-card .btn"), (b) => b.textContent === "Back").click());
  await settle(page, "Open one");
  console.log("Back lands on:", (await state(page)).title, (await state(page)).hash);
  await page.keyboard.press("Escape");
  await wait(400);
  console.log("Esc ends it:", !(await page.$(".tour-card")), "and leaves", await page.evaluate(() => document.querySelectorAll(".tour-ring, .tour-pointer").length), "pieces behind");
  await page.close();

  page = await fresh();
  await page.evaluate(() => Array.prototype.find.call(document.querySelectorAll(".tour-offer .btn"), (b) => b.textContent === "Not now").click());
  await page.reload({ waitUntil: "networkidle0" }); await wait(1200);
  console.log("Not now, then a reload in the same visit, offer:", !!(await page.$(".tour-offer")));
  await page.close();

  page = await fresh();
  await page.evaluate(() => Array.prototype.find.call(document.querySelectorAll(".tour-offer .tc-link"), (b) => /offer this again/.test(b.textContent)).click());
  await wait(500);
  console.log("Don't offer this again, stored:", await page.evaluate(() => localStorage.getItem("aac.tour")));
  await page.evaluate(() => { window.location.hash = "guide"; });
  await wait(1200);
  const help = await page.evaluate(() => !!Array.prototype.find.call(document.querySelectorAll("#dataPanel .btn"), (b) => b.textContent === "Take the tour"));
  console.log("Help offers Take the tour:", help);
  await page.evaluate(() => Array.prototype.find.call(document.querySelectorAll("#dataPanel .btn"), (b) => b.textContent === "Take the tour").click());
  await settle(page, "Every diagram, by layer");
  console.log("Take the tour from Help starts on:", (await state(page)).hash);
  await page.close();
} finally {
  await browser.close();
}
console.log("page errors:", errors.length ? errors : "none");
