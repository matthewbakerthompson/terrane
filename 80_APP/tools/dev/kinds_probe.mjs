// Does Checks say what kind each record probably is, as V15 draws it? On
// What the diagrams need: the kinds first, the records with no component
// type counted against the library's kinds; the first group opened, its
// rows ticked where the match is sure, a one-word group said to be one;
// a record a product's part makes shown and not offered; a tick taken off
// and put back; Set writes the kind on what is ticked and the group goes;
// Undo puts it back; and the rest of the kinds open on a click.
//
//   node 80_APP/tools/dev/kinds_probe.mjs out/ URL
//
// It writes the model and puts it back, so run it on a copy of the
// repository. Exits 1 if a step does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node kinds_probe.mjs OUT URL");
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
  localStorage.setItem("aac.rail.shut", "0");
  localStorage.setItem("aac.tour", "taken");
});
async function open() {
  await page.goto(URL + "/#needs", { waitUntil: "networkidle0", timeout: 60000 });
  await page.waitForFunction(() => document.querySelector(".nd-kinds .nd-kind"), { timeout: 30000 });
  await pause(300);
}
const groups = () => page.evaluate(() => Array.from(document.querySelectorAll(".nd-kinds .nd-kind")).map((g) => ({
  name: g.querySelector(".nd-kind-name").innerText, count: Number(g.querySelector(".nd-kind-count").innerText),
  open: g.classList.contains("is-open"), one: (g.querySelector(".nd-kind-one") || {}).innerText || "",
  set: (g.querySelector(".nd-kind-head .btn") || {}).innerText || "",
  rows: Array.from(g.querySelectorAll(".nd-kind-row")).map((r) => ({
    name: r.querySelector("strong").innerText, ticked: r.querySelector("input").checked, made: r.classList.contains("is-made"),
    words: r.querySelector(".nd-kind-said").innerText, also: r.querySelector(".nd-kind-else").innerText })),
})));
const kindOf = (id) => page.evaluate((i) => fetch("/api/entity?id=" + i).then((r) => r.json()).then((d) => (d.record || d.entity || d).component_type || ""), id);

await open();
const said = await page.evaluate(() => {
  const box = document.querySelector(".nd-kinds");
  const main = box.parentNode;
  return { text: box.querySelector(".nd-kinds-said").innerText, first: main.querySelector(".nd-kinds") === box &&
    main.querySelector("h2").innerText, foot: box.querySelector(".nd-kinds-more").innerText };
});
check("the kinds come first, said against the library's kinds", said.first === "What kind each record probably is" &&
  /^54 systems have no component type\. Each is read against the library's \d+ kinds/.test(said.text), JSON.stringify(said));
let gs = await groups();
check("the first group is open and only it", gs[0].open && gs.slice(1).every((g) => !g.open), JSON.stringify(gs.map((g) => [g.name, g.count, g.open])));
const crm = gs[0];
check("a sure match is ticked and a guess is not", crm.name === "Customer relationship management" &&
  crm.rows.find((r) => r.name === "Dynamics 365 Customer Service").ticked &&
  !crm.rows.find((r) => r.name === "Campaign management").ticked, JSON.stringify(crm.rows));
check("its button sets what is ticked", crm.set === "Set 1 to Customer relationship management", crm.set);
check("a record a part makes is shown and not offered", crm.rows.some((r) => r.made && !r.ticked) && await page.evaluate(() => {
  const row = Array.from(document.querySelectorAll(".nd-kind.is-open .nd-kind-row")).find((r) => r.classList.contains("is-made"));
  return row && row.querySelector("input").disabled && /made by PRD-/.test(row.querySelector(".nd-kind-rec span").innerText);
}));
const dns = gs.find((g) => g.name === "DNS");
check("a group read on one word says so", dns && dns.one === "each on one word: domain", JSON.stringify(dns));
check("the rest are counted, with what the library says nothing of", /^and \d+ more kinds holding \d+ records, and 2 that nothing in the library says · Undo/.test(said.foot), said.foot);
await page.screenshot({ path: OUT + "/kinds.png" });

// A tick taken off and put back.
await page.evaluate(() => Array.from(document.querySelectorAll(".nd-kind.is-open .nd-kind-row")).find((r) => /Dynamics/.test(r.innerText)).querySelector("input").click());
await pause(200);
gs = await groups();
check("a tick taken off says so on the button", gs[0].set === "Set 0 to Customer relationship management" &&
  await page.evaluate(() => document.querySelector(".nd-kind.is-open .nd-kind-head .btn").disabled), gs[0].set);
await page.evaluate(() => Array.from(document.querySelectorAll(".nd-kind.is-open .nd-kind-row")).find((r) => /Campaign/.test(r.innerText)).querySelector("input").click());
await page.evaluate(() => Array.from(document.querySelectorAll(".nd-kind.is-open .nd-kind-row")).find((r) => /Dynamics/.test(r.innerText)).querySelector("input").click());
await pause(200);
gs = await groups();
check("and two ticked set two", gs[0].set === "Set 2 to Customer relationship management", gs[0].set);

// Set, then Undo.
await page.evaluate(() => document.querySelector(".nd-kind.is-open .nd-kind-head .btn").click());
await page.waitForFunction(() => /^Set 2 systems to customer relationship management/.test((document.querySelector(".toast") || {}).innerText || ""), { timeout: 15000 }).catch(() => {});
const toastText = await page.evaluate(() => (document.querySelector(".toast") || {}).innerText || "");
check("Set says what it did", /^Set 2 systems to customer relationship management/.test(toastText), toastText);
await page.waitForFunction(() => /^52 systems/.test((document.querySelector(".nd-kinds-said") || {}).innerText || ""), { timeout: 30000 }).catch(() => {});
await pause(300);
check("the two have the kind in their files", (await kindOf("SYS-CRM")) === "crm" && (await kindOf("SYS-MARKETING")) === "crm");
gs = await groups();
check("and leave the list", !gs.some((g) => g.rows.some((r) => /Dynamics 365|Campaign management/.test(r.name))) &&
  /^52 systems/.test(await page.evaluate(() => document.querySelector(".nd-kinds-said").innerText)));
await page.screenshot({ path: OUT + "/kinds-set.png" });
await page.evaluate(() => Array.from(document.querySelectorAll(".toast button")).find((b) => b.innerText.trim() === "Undo").click());
await page.waitForFunction(() => /^54 systems/.test((document.querySelector(".nd-kinds-said") || {}).innerText || ""), { timeout: 20000 }).catch(() => {});
check("Undo puts them back", (await kindOf("SYS-CRM")) === "" && (await kindOf("SYS-MARKETING")) === "");

// The rest of the kinds.
await page.evaluate(() => document.querySelector(".nd-kinds-more .linkish").click());
await pause(300);
gs = await groups();
check("the rest of the kinds open on a click", gs.length > 5 && !(await page.$(".nd-kinds-more .linkish")), String(gs.length));
check("no page errors", errors.length === 0, errors.join(" / "));
await browser.close();
process.exit(failed ? 1 : 0);
