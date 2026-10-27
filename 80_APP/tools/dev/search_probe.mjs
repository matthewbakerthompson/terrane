// Does the search box find what a person means? On the card issuer, typed
// into Ctrl+K's palette with the keyboard: "core ledger" puts the Core Card
// Ledger first among the model's things, ahead of the interfaces named for
// it; "ledgr", misspelled, still finds a ledger; "rdbms", an alias of the
// relational database kind, finds the SQL databases; "led", half typed,
// finds ledgers; and Enter on the first opens it. A PNG of the palette for
// each. Point it at a baked static copy too: the index comes from a file
// there, and the answers are the same.
//
//   node 80_APP/tools/dev/search_probe.mjs out/ URL
//
// It writes nothing. Exits 1 if a step does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node search_probe.mjs OUT URL");
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
await page.evaluateOnNewDocument(() => { localStorage.setItem("aac.tour", "taken"); });
await page.goto(URL + "/#view=capability-map", { waitUntil: "networkidle0", timeout: 60000 });
await settled(page);
await page.waitForFunction(() => window.TerraneSearch && document.querySelector("#btnJump"), { timeout: 30000 });
// The index rides beside the list: wait until the page has it.
await page.waitForFunction(() => {
  const app = window.TerraneApp;
  return app && app.state && app.state.search && app.state.search.version === window.TerraneSearch.VERSION;
}, { timeout: 30000 }).catch(() => {});
check("the page has the engine's index",
  await page.evaluate(() => !!(window.TerraneApp && window.TerraneApp.state && window.TerraneApp.state.search)));

async function ask(query, name) {
  if (!(await page.$("#palette:not([hidden])"))) {
    await page.keyboard.down("Control");
    await page.keyboard.press("k");
    await page.keyboard.up("Control");
    await page.waitForSelector("#palette:not([hidden])", { timeout: 5000 });
  }
  await page.focus("#paletteBox");
  await page.keyboard.down("Control");
  await page.keyboard.press("a");
  await page.keyboard.up("Control");
  await page.keyboard.press("Backspace");
  await page.keyboard.type(query, { delay: 30 });
  await pause(250);
  const things = await page.evaluate(() => {
    const out = [];
    let group = "";
    for (const node of document.querySelectorAll("#paletteList > *")) {
      if (node.classList.contains("pal-group")) { group = node.textContent; continue; }
      if (group === "In the model") {
        out.push({ name: node.querySelector(".pr-name").textContent,
          hint: (node.querySelector(".pr-hint") || {}).textContent || "" });
      }
    }
    return out;
  });
  await page.screenshot({ path: OUT + "/" + name + ".png" });
  console.log("     " + JSON.stringify(query) + " -> " + things.slice(0, 4).map((t) => t.name).join(" | "));
  return things;
}

let got = await ask("core ledger", "core-ledger");
check("core ledger: the ledger itself first", got.length && got[0].name === "Core Card Ledger", got[0] && got[0].name);
got = await ask("ledgr", "misspelled");
check("ledgr: a ledger, misspelled", got.length && /ledger/i.test(got[0].name), got[0] && got[0].name);
got = await ask("rdbms", "alias");
check("rdbms: a relational database by its kind's alias",
  got.some((t) => /SQL|RDS/.test(t.name)), got.map((t) => t.name).slice(0, 3).join(", "));
got = await ask("led", "half-typed");
check("led: ledgers while it is typed", got.length && got.every((t) => /ledger/i.test(t.name) || /LEDGER|GL/.test(t.hint)),
  got.map((t) => t.name).slice(0, 3).join(", "));
got = await ask("core ledger", "open");
await page.keyboard.press("Enter");
await pause(1500);
const opened = await page.evaluate(() => window.location.hash);
check("Enter on the first opens it", /SYS-CORE-LEDGER/.test(decodeURIComponent(opened)), opened);
await page.screenshot({ path: OUT + "/opened.png" });

check("no page errors", errors.length === 0, errors.slice(0, 3).join(" / "));
await browser.close();
process.exit(failed ? 1 : 0);
