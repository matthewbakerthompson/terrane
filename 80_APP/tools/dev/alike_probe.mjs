// Does Checks list the names that read alike as V15 draws it? On the
// Validate tab, a card beside the rules with one row, its count the
// engine's and in neither box; chosen, the pairs grouped by why each is
// probably two things, the first group open, each pair's two names, type,
// score and shared words, and the side's note saying it is not a finding.
// The link holds the choice; a name opens its record; All findings goes
// back. Nothing is written.
//
//   node 80_APP/tools/dev/alike_probe.mjs out/ URL
//
// Reads the card issuer as committed (9 pairs in four groups). Exits 1 if
// a step does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node alike_probe.mjs OUT URL");
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
const engine = await (await fetch(URL + "/api/checks/alike")).json();
const validate = await (await fetch(URL + "/api/validate")).json();

await page.goto(URL + "/#checks", { waitUntil: "networkidle0", timeout: 60000 });
await page.waitForSelector(".checks-beside", { timeout: 60000 });
await pause(500);
const side = () => page.evaluate(() => {
  const row = document.querySelector(".checks-beside .hp-row");
  return {
    head: document.querySelector(".checks-beside .hp-title").innerText,
    row: row.innerText.replace(/\s+/g, " "), on: row.classList.contains("is-on"),
    tiles: Array.from(document.querySelectorAll(".checks-side .hero-fact .hf-n")).map((n) => n.innerText),
    note: Array.from(document.querySelectorAll(".checks-side .brief-hint")).map((p) => p.innerText).join(" "),
  };
});
let s = await side();
check("beside the rules, one row counting the engine's pairs",
  s.head === "Beside the rules" && s.row === "Names that read alike " + engine.pairs && engine.pairs === 9 && !s.on, s.row);
check("and counted in neither box", s.tiles[0] === String(validate.errors.length) &&
  s.tiles[1] === String(validate.warnings.length), s.tiles.join(" / "));

await page.evaluate(() => document.querySelector(".checks-beside .hp-row").click());
await page.waitForSelector(".alike-head", { timeout: 30000 });
await pause(400);
const read = () => page.evaluate(() => ({
  hash: location.hash,
  head: document.querySelector(".alike-head").innerText.replace(/\s+/g, " "),
  said: document.querySelector(".alike-said").innerText,
  groups: Array.from(document.querySelectorAll(".alike-group")).map((g) => ({
    title: g.querySelector(".fg-title").innerText, line: g.querySelector(".fg-code").innerText,
    n: g.querySelector(".alike-n").innerText, open: g.open,
    pairs: Array.from(g.querySelectorAll(".alike-pair")).map((p) => ({
      names: Array.from(p.querySelectorAll(".alike-name")).map((b) => b.textContent),
      why: p.querySelector(".alike-why").textContent })) })),
  findings: document.querySelectorAll(".checks-main .finding").length,
}));
let r = await read();
s = await side();
check("chosen, the row is on and the link holds it", s.on && /rule=alike/.test(r.hash), r.hash);
check("the head counts the pairs", r.head === "Names that read alike 9", r.head);
check("and says what they are", /scores 0\.85 or more against each other\. None is a finding/.test(r.said), r.said);
check("four groups, most first", JSON.stringify(r.groups.map((g) => [g.title, g.n])) === JSON.stringify([
  ["Another cloud", "3"], ["Interfaces named for their two systems", "3"],
  ["A and B, or a recovery copy", "2"], ["Elsewhere on the map", "1"]]), JSON.stringify(r.groups.map((g) => [g.title, g.n])));
check("each saying why", r.groups[0].line === "the same technology service in AWS and in GCP: Lending App Subnet A and Lending App Subnetwork" &&
  r.groups[1].line === "one end shared, or the same two the other way round: Collections Platform to Outbound Contact Platform, and back" &&
  r.groups[2].line === "technology services: one is the other's DR copy" &&
  r.groups[3].line === "capabilities in different domains: Application Capture and Payment Capture & Application",
  r.groups.map((g) => g.line).join(" | "));
check("the first open and the rest folded", r.groups.map((g) => g.open).join() === "true,false,false,false");
check("each pair's two names, type, score and shared words",
  JSON.stringify(r.groups[2].pairs[0]) === JSON.stringify({ names: ["Analytics Data Subnetwork", "Analytics Data Subnetwork (DR)"],
    why: "technology services · 0.88 · shares analytic, data and subnetwork" }) &&
  r.groups[0].pairs[0].why === "technology services · 0.92 · shares app, lending and subnetwork for subnet" &&
  // Elsewhere on the map, where each sits.
  r.groups[3].pairs[0].why === "capabilities · 0.85 · shares application and capture · in Originations and in Servicing",
  JSON.stringify(r.groups[2].pairs[0]) + " " + r.groups[0].pairs[0].why);
check("no findings beside them", r.findings === 0, String(r.findings));
check("the side says it is not a finding", /^Not a finding, and counted in neither box/.test(s.note), s.note);
await page.screenshot({ path: OUT + "/alike.png" });

// The link opened afresh shows the list.
await page.goto(URL + "/#checks&rule=alike", { waitUntil: "networkidle0", timeout: 60000 });
await page.waitForSelector(".alike-head", { timeout: 60000 });
check("the link opens the list", (await read()).groups.length === 4);

// A name opens its record.
await page.evaluate(() => {
  const g = Array.from(document.querySelectorAll(".alike-group")).find((x) => /Secret Manager/.test(x.textContent));
  g.open = true;
  Array.from(g.querySelectorAll(".alike-name")).find((b) => b.innerText === "Secret Manager").click();
});
await pause(1500);
const opened = await page.evaluate(() => ({ hash: location.hash, text: document.body.innerText }));
check("a name opens its record", /TS-GCP-SECRET-MANAGER/.test(opened.hash) || /TS-GCP-SECRET-MANAGER/.test(opened.text), opened.hash);

// All findings goes back to the rules' findings.
await page.goto(URL + "/#checks&rule=alike", { waitUntil: "networkidle0", timeout: 60000 });
await page.waitForSelector(".alike-head", { timeout: 60000 });
await page.evaluate(() => document.querySelector(".checks-rules:not(.checks-beside) .hp-row").click());
await page.waitForSelector(".checks-main .fgroup:not(.alike-group)", { timeout: 30000 });
r = await page.evaluate(() => ({ alike: !!document.querySelector(".alike-head"), hash: location.hash,
  note: document.querySelector(".checks-side .brief-hint").innerText }));
check("All findings goes back, the note the warnings' again", !r.alike && !/rule=alike/.test(r.hash) && /^Warnings do not block a merge/.test(r.note), JSON.stringify(r));
check("no page errors", errors.length === 0, errors.join(" / "));
await browser.close();
process.exit(failed ? 1 : 0);
