// Does the adopt page say what is probably here already, as V15 draws it?
// The sample ArchiMate model dropped on a new diagram: its switch and its
// ledger listed and ticked Same record, its two capabilities listed and
// not; the counts say two fewer added and two more here already, "which the
// drawing calls by other names"; the ledger unticked adds one back, ticked
// again takes it; a capability ticked too; Adopt writes the drawing with
// the three joined to the estate's, no second ledger, switch or capability,
// and the ledger keeps its name.
//
//   node 80_APP/tools/dev/same_probe.mjs out/ URL
//
// It writes the drawing's records into the model: run it on a copy of the
// repository. Exits 1 if a step does not do what it says.
import { mkdir, readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { launch } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node same_probe.mjs OUT URL");
  process.exit(2);
}
await mkdir(OUT, { recursive: true });
const FILE = resolve(process.cwd(), "../../../90_EXAMPLE/quick/sample.archimate");
const bytes = (await readFile(FILE)).toString("base64");
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
await page.goto(URL + "/#draw", { waitUntil: "networkidle0", timeout: 60000 });
await pause(1500);
const drop = (type) => page.evaluate((type, b64) => {
  const data = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
  const dt = new DataTransfer();
  dt.items.add(new File([data], "sample.archimate"));
  const sheet = document.getElementById("mapSheet");
  const r = sheet.getBoundingClientRect();
  sheet.dispatchEvent(new DragEvent(type, { bubbles: true, cancelable: true, dataTransfer: dt,
    clientX: r.left + r.width / 2, clientY: r.top + r.height / 2 }));
}, type, bytes);
await drop("dragenter");
await drop("dragover");
await drop("drop");
await page.waitForSelector(".adopt-drawing img, .adopt-nothing", { timeout: 120000 });
const settledPage = async () => {
  await page.waitForFunction(() => !document.querySelector(".adopt-picture.is-busy"), { timeout: 120000 });
  await pause(500);
};
await settledPage();
const read = () => page.evaluate(() => ({
  rows: Array.from(document.querySelectorAll(".adopt-same")).map((r) => ({
    name: r.querySelector(".adopt-same-pair strong").innerText, theirs: (r.querySelector(".adopt-same-theirs") || {}).innerText || "",
    ticked: r.querySelector("input").checked, same: r.classList.contains("is-same"), why: r.querySelector(".adopt-same-why").innerText })),
  added: Number((document.querySelector(".adopt-count.accent strong") || {}).innerText),
  here: Array.from(document.querySelectorAll(".adopt-count")).map((c) => c.innerText.replace(/\s+/g, " ")).find((t) => /here already/.test(t)) || "",
  button: (document.getElementById("adoptGo") || {}).innerText || "",
  said: (Array.from(document.querySelectorAll(".adopt-block")).find((b) => /Probably here already/.test(b.innerText)) || {}).innerText || "",
}));
const tick = (name) => page.evaluate((n) => Array.from(document.querySelectorAll(".adopt-same")).find((r) =>
  r.querySelector(".adopt-same-pair strong").innerText === n).querySelector("input").click(), name);

let s = await read();
const by = (n) => s.rows.find((r) => r.name === n) || {};
check("four records the drawing adds are listed as probably here", s.rows.length === 4 && /^Probably here already/.test(s.said) &&
  /4 records the drawing adds read like ones the estate has/.test(s.said), JSON.stringify(s.rows.map((r) => r.name)));
check("the switch and the ledger ticked, as the estate's", by("Authorization switch").ticked && by("Card ledger").ticked &&
  by("Card ledger").theirs === "Core Card Ledger" && /^SYS-CORE-LEDGER · 0\.74 · shares card and ledger$/.test(by("Card ledger").why),
  JSON.stringify(s.rows));
check("the two capabilities listed and left to a person", !by("Payment processing").ticked && !by("Fraud detection").ticked);
check("here already says which the drawing calls by other names", /Authorization Switch and Core Card Ledger, which the drawing calls by other names/.test(s.here), s.here);
const added = s.added;
await page.screenshot({ path: OUT + "/same.png" });

// The ledger unticked adds it back; ticked again takes it.
await tick("Card ledger");
await settledPage();
s = await read();
check("the ledger unticked is added again", s.added === added + 1 && !by("Card ledger").ticked, String(s.added));
await tick("Card ledger");
await settledPage();
s = await read();
check("ticked again it is the estate's", s.added === added && by("Card ledger").ticked, String(s.added));
await tick("Payment processing");
await settledPage();
s = await read();
check("a capability ticked by a person is the estate's too", s.added === added - 1 && by("Payment processing").ticked &&
  /Adopt \d+ records/.test(s.button), s.button);

// Adopt: the three joined to the estate's.
await page.click("#adoptGo");
await page.waitForFunction(() => !!document.querySelector(".toast"), { timeout: 120000 });
await pause(1500);
const estate = await page.evaluate(async () => {
  const names = async (t) => (await (await fetch("/api/list?type=" + t)).json());
  return { systems: JSON.stringify(await names("systems")), capabilities: JSON.stringify(await names("capabilities")),
    ledger: (await (await fetch("/api/entity?id=SYS-CORE-LEDGER")).json()).record.name };
});
check("no second ledger or switch was written", !/"Card ledger"/.test(estate.systems) && !/"Authorization switch"/.test(estate.systems) &&
  /Fraud scoring/.test(estate.systems));
check("no second payment processing capability", !/"Payment processing"/.test(estate.capabilities) && /Fraud detection/.test(estate.capabilities));
check("the ledger keeps the estate's name", estate.ledger === "Core Card Ledger", estate.ledger);
check("no page errors", errors.length === 0, errors.join(" / "));
await browser.close();
process.exit(failed ? 1 : 0);
