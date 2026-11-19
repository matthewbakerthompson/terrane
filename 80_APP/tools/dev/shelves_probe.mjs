// Is Add on shelves (V18)? On a new diagram at 1440 by 900: Add opens on
// the shelf picked last, its shelves counted; Parts of an application is
// its four headings, two to a row, and Background worker pointed at is
// described with the kit it is part of; every shelf opens under its
// headings; "pay" searches every shelf at once, Everything found first and
// Payment processing the first found, the arrow keys moving on; "ec2" is
// the virtual machine with Amazon EC2 beside it; and Add opens again on the
// shelf last picked. V19's four shelves open under their headings, and Card
// account master pointed at says who writes, keeps and reads it. Takes the
// pictures the design file's as-built frames are filled with
// (shelves-parts.png, shelves-pay.png, shelves-business.png, shelves-data.png).
//
//   node 80_APP/tools/dev/shelves_probe.mjs out/ URL
//
// Writes nothing to the estate. Exits 1 if a step does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch } from "../capture.mjs";

const [OUT, URL] = process.argv.slice(2);
if (!OUT || !URL) {
  console.error("usage: node shelves_probe.mjs OUT URL");
  process.exit(2);
}
await mkdir(OUT, { recursive: true });
const pause = (ms) => new Promise((r) => setTimeout(r, ms));
let failed = false;
function check(what, ok, said) {
  console.log((ok ? "ok   " : "FAIL ") + what + (said !== undefined ? ": " + said : ""));
  if (!ok) failed = true;
}

const browser = await launch();
const page = await browser.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
await page.setViewport({ width: 1440, height: 900 });
await page.evaluateOnNewDocument(() => {
  localStorage.setItem("aac.rail.shut", "0");
  localStorage.setItem("aac.insp.shut", "1");
  localStorage.setItem("aac.tour", "taken");
  localStorage.setItem("aac.tone", "stone");
  localStorage.setItem("aac.add.shelf", "parts");
});
await page.goto(URL + "/#draw", { waitUntil: "networkidle0", timeout: 60000 });
await pause(1200);
const openAdd = () => page.evaluate(() => Array.from(document.querySelectorAll("button")).find((b) => b.innerText.trim() === "Add").click());
const pick = (name) => page.evaluate((n) => Array.from(document.querySelectorAll("#cvPicker .cv-shelf"))
  .find((b) => b.firstChild.textContent === n).click(), name);
const say = () => page.evaluate(() => ({
  shelves: Array.from(document.querySelectorAll("#cvPicker .cv-shelf")).map((b) =>
    (b.getAttribute("aria-selected") === "true" ? "*" : "") + b.firstChild.textContent + " " + b.lastChild.textContent),
  groups: Array.from(document.querySelectorAll("#cvPicker .cv-group")).map((g) => g.firstChild.textContent),
  cells: document.querySelectorAll("#cvPicker .cv-row.is-cell").length,
  current: ((document.querySelector("#cvPicker .cv-row.is-current") || {}).innerText || "").trim().replace(/\s*\n+\s*/g, " | "),
  foot: (document.querySelector("#cvPicker .cv-detail") || {}).innerText || "",
}));

await openAdd();
await pause(700);
let got = await say();
check("Add opens on the shelf picked last, every shelf counted", got.shelves[1] === "*Parts of an application 19"
  && got.shelves.length === 10 && got.shelves.every((s) => / \d+$/.test(s)), JSON.stringify(got.shelves));
check("Parts of an application: four headings, two to a row", got.groups.join() === "Front ends,Services and workers,AI,Platforms"
  && got.cells === 19, JSON.stringify(got.groups));
check("nothing pointed at, the foot says so", /^Point at one to read what it is/.test(got.foot), got.foot);
const worker = await page.evaluateHandle(() => Array.from(document.querySelectorAll("#cvPicker .cv-row"))
  .find((r) => r.innerText.trim() === "Background worker"));
await worker.hover();
await pause(300);
got = await say();
check("Background worker pointed at, described with its kit", got.current === "Background worker"
  && /Also in the Event-driven service kit, as its async worker\./.test(got.foot), got.foot);
await page.screenshot({ path: OUT + "/shelves-parts.png" });

for (const [name, first] of [["Whole applications", "Application"], ["Business systems", "Finance"],
  ["Building blocks", "Data"], ["Cloud services", "AI"], ["Systems", ""], ["Data", "Restricted"],
  ["Actors", "Outside the company"], ["Teams", "At the top"], ["Boundaries", "Views"]]) {
  await pick(name);
  await pause(300);
  got = await say();
  check(name + " opens under its headings", got.groups.length > 0 && (!first || got.groups[0] === first), JSON.stringify(got.groups));
  if (name === "Business systems") await page.screenshot({ path: OUT + "/shelves-business.png" });
  if (name === "Data") {
    const asset = await page.evaluateHandle(() => Array.from(document.querySelectorAll("#cvPicker .cv-row"))
      .find((r) => r.innerText.trim() === "Card account master"));
    await asset.hover();
    await pause(300);
    got = await say();
    check("a data asset pointed at says who writes it, keeps it and reads it (V19)",
      /Core Card Ledger writes it and keeps the master; ten more systems read it\. Placed, a line joins it to each of them that is on the diagram\./.test(got.foot),
      got.foot);
    await page.screenshot({ path: OUT + "/shelves-data.png" });
  }
}

await pick("Parts of an application");
await page.type("#cvPicker .cv-search", "pay");
await pause(400);
got = await say();
check("found: Everything found first, each shelf counting its own", /^\*Everything found \d+$/.test(got.shelves[0])
  && got.shelves.some((s) => s === "Business systems 4"), JSON.stringify(got.shelves));
check("Payment processing found first, Enter's to place", got.current.indexOf("Payment processing") === 0
  && /Business systems · Finance/.test(got.foot) && /Enter places it/.test(got.foot), got.current);
await page.screenshot({ path: OUT + "/shelves-pay.png" });
await page.keyboard.press("ArrowDown");
await pause(200);
got = await say();
check("the arrow keys move through what was found", got.current && got.current.indexOf("Payment processing") !== 0, got.current);

await page.evaluate(() => { document.querySelector("#cvPicker .cv-search").value = ""; });
await page.type("#cvPicker .cv-search", "ec2");
await pause(300);
got = await say();
check("ec2 is the virtual machine, Amazon EC2 beside it", /^Virtual machine \| Amazon EC2 · AWS \| Box$/.test(got.current)
  && /Placed, it is named Amazon EC2\./.test(got.foot), got.current);

await page.keyboard.press("Escape");
await pause(200);
await openAdd();
await pause(400);
got = await say();
check("opened again, on the shelf picked last", got.shelves[1] === "*Parts of an application 19", JSON.stringify(got.shelves));
check("no page errors", !errors.length, errors.join(" | "));
await browser.close();
process.exit(failed ? 1 : 0);
