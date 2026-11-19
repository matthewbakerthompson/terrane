// Does the Sources Words step say which names the model does not hold, as
// V15 draws it? The card issuer's quick inventory brought in through
// Settings > Sources: on Words, the owners' card above the word cards, 6
// of its 7 names lacking, Partnerships already an org unit, Finance offered
// for Finance operations and nothing for the rest; the side counting the
// names left and the rows that wait. Finance used, and an org unit chosen
// for Payments platform: two fewer left, and Review writes the systems with
// those owners. The card's foot goes back to Columns. Nothing is written.
//
//   node 80_APP/tools/dev/source_names_probe.mjs out/ URL
//
// Run it on a copy of the repository all the same. Exits 1 if a step does
// not do what it says.
import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import { launch } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node source_names_probe.mjs OUT URL");
  process.exit(2);
}
await mkdir(OUT, { recursive: true });
const FILE = resolve(process.cwd(), "../../../90_EXAMPLE/quick/sample-inventory.csv");
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
  localStorage.setItem("aac.rail.shut", "0");
  localStorage.setItem("aac.tour", "taken");
});
await page.goto(URL + "/#settings&tab=sources", { waitUntil: "networkidle0", timeout: 60000 });
await pause(800);
const input = await page.waitForSelector(".drop input[type=file]", { timeout: 20000 });
await input.uploadFile(FILE);
await page.waitForFunction(() => document.querySelector(".src-bar") && /Columns/.test(document.body.innerText), { timeout: 60000 });
await pause(600);
const bar = (re) => page.evaluate((src) => {
  const b = Array.from(document.querySelectorAll(".src-bar button")).find((x) => new RegExp(src).test(x.innerText));
  return b ? b.innerText : "";
}, re.source);
const press = (re) => page.evaluate((src) => Array.from(document.querySelectorAll(".src-bar button")).find((x) => new RegExp(src).test(x.innerText)).click(), re.source);
check("Columns goes on to the words", /Next: match the words/.test(await bar(/Next/)));
// The file says no status: one for every row, as a person would choose.
await page.evaluate(() => {
  const sel = Array.from(document.querySelectorAll(".st-side select")).find((x) => /Not in this file/.test(x.options[0].text));
  sel.value = "Active";
  sel.dispatchEvent(new Event("change"));
});
await pause(500);
await press(/Next/);
await page.waitForSelector(".names-card", { timeout: 60000 });
await pause(500);
const read = () => page.evaluate(() => {
  const card = document.querySelector(".names-card");
  return {
    first: document.querySelector(".st-main").firstElementChild === card,
    head: card.querySelector(".word-head").innerText.replace(/\s+/g, " "),
    rows: Array.from(card.querySelectorAll(".word-row")).map((r) => ({
      name: r.querySelector(".word").innerText, rows: r.querySelector(".rows").innerText, open: r.classList.contains("open"),
      chosen: (r.querySelector("select") || {}).value || "", said: ((r.querySelector(".same") || r.querySelector(".nearest") || {}).innerText || "").replace(/\s+/g, " ") })),
    left: document.querySelector(".st-side h2").innerText,
    side: document.querySelector(".st-side").innerText.replace(/\s+/g, " "),
  };
});
let s = await read();
const row = (n) => s.rows.find((r) => r.name === n) || {};
check("the owners' card comes first, saying how many are lacking", s.first && /^Owner from Owner 6 of its 7 names are not org units in the model$/.test(s.head), s.head);
check("Partnerships is already an org unit", row("Partnerships").said === "Already an org unit" && !row("Partnerships").open);
check("Finance is offered for Finance operations, with why", /^Reads like Finance Use Finance ORG-FINANCE · 0\.81 · shares finance$/.test(row("Finance operations").said), row("Finance operations").said);
check("and nothing for the rest", ["Payments platform", "Risk engineering", "Data office", "Merchant experience", "Platform engineering"]
  .every((n) => row(n).said === "No org unit reads like it" && row(n).open && row(n).chosen === "@none"), JSON.stringify(s.rows));
check("the side counts the names left and the rows that wait", s.left === "6 names left" &&
  /7 rows wait until those names have an org unit/.test(s.side), s.left + " | " + s.side);
await page.screenshot({ path: OUT + "/source-names.png" });

// Finance used; an org unit chosen for Payments platform.
await page.evaluate(() => Array.from(document.querySelectorAll(".names-card .nearest .linkish")).find((b) => b.innerText === "Use Finance").click());
await pause(300);
await page.evaluate(() => {
  const r = Array.from(document.querySelectorAll(".names-card .word-row")).find((x) => x.querySelector(".word").innerText === "Payments platform");
  const sel = r.querySelector("select");
  sel.value = "ORG-PAYMENTS";
  sel.dispatchEvent(new Event("change"));
});
await pause(400);
s = await read();
check("used, Finance is chosen and the row no longer waits", row("Finance operations").chosen === "ORG-FINANCE" && !row("Finance operations").open);
check("two fewer names left, three fewer rows waiting", s.left === "4 names left" && /4 rows wait/.test(s.side), s.left + " | " + s.side);

// Review: the two systems written with those owners.
await press(/Next: review/);
await page.waitForFunction(() => /Review/.test(document.body.innerText) && !/Reading/.test(document.querySelector(".st-main") ? document.querySelector(".st-main").innerText : "x"), { timeout: 60000 });
await pause(1500);
const review = await page.evaluate(() => document.querySelector(".st-body").innerText.replace(/\s+/g, " "));
check("Review writes the two Payments platform systems with the org unit chosen",
  /Authorization switch Active · High · On-prem Payments Operations/.test(review) &&
  /Card ledger Active · High · On-prem Payments Operations/.test(review), review.slice(0, 300));
const heldFor = (n) => review.includes("owner_org_id: '" + n + "' is no org unit");
check("and holds back for their owner only the four left unchosen",
  ["Data office", "Merchant experience", "Platform engineering", "Risk engineering"].every(heldFor) &&
  !heldFor("Payments platform") && !heldFor("Finance operations"), review.slice(0, 1200));
await page.screenshot({ path: OUT + "/source-names-review.png" });

// Back on Words, the card's foot goes to Columns.
await press(/Back/);
await page.waitForSelector(".names-card", { timeout: 30000 });
await page.evaluate(() => document.querySelector(".names-foot .linkish").click());
await pause(500);
check("the card's foot goes back to Columns", await page.evaluate(() => !!document.getElementById("srcUnits")));
check("no page errors", errors.length === 0, errors.join(" / "));
await browser.close();
process.exit(failed ? 1 : 0);
