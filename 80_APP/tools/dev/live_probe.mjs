// The hosted demo as a reader sees it, after a Pages deploy: marks on the
// boundaries and nodes of one drawing, the review-pack line and the
// estates on the home page, each other estate's home as its own reader
// sees it, and any page error or missing icon file.
//
//   node 80_APP/tools/dev/live_probe.mjs
//   node 80_APP/tools/dev/live_probe.mjs http://127.0.0.1:8030/   # a site baked locally
//
// The site must be reachable; the default is the GitHub Pages address.
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { drawingPng, launch } from "../capture.mjs";

const OUT = resolve(dirname(fileURLToPath(import.meta.url)), "out");
const BASE = process.argv[2] || "https://matthewbakerthompson.github.io/terrane/";
const settle = (ms) => new Promise((r) => setTimeout(r, ms));

await mkdir(OUT, { recursive: true });
const browser = await launch();
try {
  const page = await browser.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("response", (r) => { if (r.status() >= 400 && /icons\//.test(r.url())) errors.push("HTTP " + r.status() + " " + r.url()); });
  await page.evaluateOnNewDocument(() => { localStorage.setItem("aac.rail.shut", "1"); });
  await page.goto(BASE + "#view=onboarding&p_product=PRD-INSTALLMENT-LENDING", { waitUntil: "networkidle0", timeout: 90000 });
  await writeFile(resolve(OUT, "live-onboarding.png"), await drawingPng(page));
  const facts = await page.evaluate(() => {
    const cy = document.getElementById("cy")._cyreg.cy;
    const groups = cy.nodes().filter((n) => n.isParent());
    return { nodes: cy.nodes().filter((n) => !n.isParent()).length,
      groupsWithMarks: groups.filter((n) => n.data("icon")).map((n) => n.data("label")).sort(),
      leavesWithMarks: cy.nodes().filter((n) => !n.isParent() && n.data("icon")).length,
      isStatic: !!window.__AAC_STATIC__ };
  });
  console.log("onboarding:", JSON.stringify(facts));
  const readHome = () => page.evaluate(() => {
    const deck = document.querySelector(".home-deck");
    return {
      title: document.title,
      deck: deck ? deck.textContent.slice(0, 160) : "(none)",
      estates: [...document.querySelectorAll(".home-estates .page-tab")].map((t) => ({
        name: t.querySelector(".pt-label").textContent,
        here: t.classList.contains("is-on"),
        href: t.getAttribute("href"),
      })),
    };
  });
  await page.goto(BASE + "#home", { waitUntil: "networkidle0", timeout: 90000 });
  await settle(2000);
  const home = await readHome();
  console.log("home:", JSON.stringify(home));
  // Every other estate the home page links, read the same way: its own
  // name in the tab, its own tab marked, and its own deck.
  for (const estate of home.estates.filter((e) => !e.here)) {
    await page.goto(new URL(estate.href, BASE).href + "#home", { waitUntil: "networkidle0", timeout: 90000 });
    await settle(2000);
    console.log(estate.name + ":", JSON.stringify(await readHome()));
  }
  console.log("errors:", JSON.stringify(errors.slice(0, 6)));
  await page.close();
} finally {
  await browser.close();
}
