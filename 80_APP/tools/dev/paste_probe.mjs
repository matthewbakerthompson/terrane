// Does copy and paste carry what is picked across diagrams? On
// lending-onboarding (arrange_probe.mjs makes it, annotate_probe.mjs puts a
// note by the Lending portal and a line from the portal to it): the portal,
// the note and the line picked and copied with Ctrl+C; Ctrl+V on the same
// diagram draws the note and the line again a step on, the portal already
// there; Ctrl+V on a new diagram places the portal and draws the note and
// the line joined to it, which the new diagram's file holds; and one Undo
// takes what was pasted of its own away.
//
//   node 80_APP/tools/dev/paste_probe.mjs out/ URL
//
// It draws on a diagram and makes another, so run it on a copy of the
// repository. Exits 1 if a step does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node paste_probe.mjs OUT URL");
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
const VIEW = "lending-onboarding", RECORD = "SYS-LENDING-PORTAL";
if (!(await fetch(URL + "/api/view?id=" + VIEW)).ok) {
  console.log("skip  no " + VIEW + " here (arrange_probe.mjs makes it)");
  await browser.close();
  process.exit(0);
}
async function open(hash) {
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  await page.evaluateOnNewDocument(() => {
    localStorage.setItem("aac.rail.shut", "1");
    localStorage.setItem("aac.insp.shut", "0");
    localStorage.setItem("aac.tour", "taken");
  });
  await page.goto(URL + "/#" + hash, { waitUntil: "networkidle0", timeout: 60000 });
  await page.waitForSelector(".mg-surface.takes-pointer svg", { timeout: 30000 });
  await settled(page);
  await pause(600);
  await page.focus("#cy");
  return page;
}
const own = (page) => page.evaluate(() => (window.TerraneApp.Canvas.cv.data.annotations || []).map((a) => Object.assign({}, a)));
async function key(page, k) {
  await page.keyboard.down("Control");
  await page.keyboard.press(k);
  await page.keyboard.up("Control");
  await pause(500);
}
async function saved(page) {
  await pause(400);
  await page.waitForFunction(() => /^(saved|failed)$/.test(window.TerraneApp.Canvas.cv.status), { timeout: 15000 });
}

const page = await open("draw=" + VIEW);
const before = await own(page);
const line = before.find((a) => a.role === "line" && a.from === RECORD && before.some((n) => n.key === a.to && n.role === "note"));
const note = line && before.find((a) => a.key === line.to);
check("the portal has its note and a line to it", !!line && !!note, line && JSON.stringify(line));
if (!line) { await browser.close(); process.exit(1); }
await page.evaluate((r, keys) => window.TerraneApp.Canvas.picked([r], keys), RECORD, [note.key, line.key]);
await pause(300);
await key(page, "c");
const clip = await page.evaluate(() => JSON.parse(localStorage.getItem("aac.canvas.clip") || "null"));
check("Ctrl+C keeps the portal, the note and the line in the browser",
  !!clip && clip.records.join() === RECORD && clip.own.map((a) => a.role).sort().join() === "line,note",
  clip && JSON.stringify({ records: clip.records, own: clip.own.map((a) => a.role) }));

await key(page, "v");
let after = await own(page);
const notes = (list) => list.filter((a) => a.role === "note" && a.label === note.label);
// The note whose key is new: an earlier walk can leave another with the
// same words on a well-used copy.
const copyNote = notes(after).find((a) => !before.some((b) => b.key === a.key));
check("Ctrl+V on the same diagram draws the note again, a step on", notes(after).length === notes(before).length + 1
  && !!copyNote && copyNote.at[0] === note.at[0] + 24 && copyNote.at[1] === note.at[1] + 24,
  copyNote && JSON.stringify(copyNote.at) + " from " + JSON.stringify(note.at));
const copyLine = after.find((a) => a.role === "line" && copyNote && a.to === copyNote.key);
check("and the line, from the portal to the new note", !!copyLine && copyLine.from === RECORD, copyLine && JSON.stringify(copyLine));
await key(page, "z");
check("one Undo takes what was pasted away", (await own(page)).length === before.length);
await saved(page);
await page.close();

const fresh = await open("draw");
await key(fresh, "v");
await fresh.waitForFunction((r) => (window.TerraneApp.Canvas.cv.data.annotations || []).length > 0
  && !!document.getElementById("cy")._cyreg.cy.getElementById(r).length, { timeout: 20000 }, RECORD);
await pause(600);
const there = await own(fresh);
const n2 = there.find((a) => a.role === "note"), l2 = there.find((a) => a.role === "line");
check("Ctrl+V on a new diagram places the portal", await fresh.evaluate((r) => !!document.getElementById("cy")._cyreg.cy.getElementById(r).length, RECORD));
check("and draws the note and the line joined to the portal", !!n2 && n2.label === note.label && !!l2 && l2.from === RECORD && l2.to === n2.key,
  JSON.stringify(there.map((a) => a.role + ":" + (a.from || "") + ">" + (a.to || ""))));
await saved(fresh);
const id = await fresh.evaluate(() => window.TerraneApp.Canvas.cv.id);
const file = await fresh.evaluate((v) => fetch("/api/view?id=" + encodeURIComponent(v)).then((r) => r.json()), id);
const pins = ((file.data || {}).scope || {}).pin || [];
check("which its file holds", pins.indexOf(RECORD) !== -1 && ((file.data || {}).annotations || []).length === 2,
  JSON.stringify({ pins, own: ((file.data || {}).annotations || []).length }));
await fresh.screenshot({ path: `${OUT}/paste-new.png` });
check("no page errors", !errors.length, errors.join(" | "));
await browser.close();
process.exit(failed ? 1 : 0);
