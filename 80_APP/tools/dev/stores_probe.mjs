// Does What is this line? offer a database's ways in and out? On a new
// diagram, a line from the installment lending web front end to its
// database: the front end reading and writing it first, by its own
// datastore as the estate's six are, the chips its two ways in; the
// database feeding the front end second, by a change data capture feed or
// a scheduled extract, where it proposed an API call. A line from another
// product's pipeline: the database feeding it first and likeliest, the two
// ways out its only chips, and the pipeline reaching in last, said to be
// the shared database the library deprecates. A chip fills the form for
// its kind, CDC and all; nothing is written. Two databases: a replica and
// a backup lead.
//
//   node 80_APP/tools/dev/stores_probe.mjs out/ URL
//
// It writes nothing; run it on a copy of the repository all the same.
// Exits 1 if a step does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node stores_probe.mjs OUT URL");
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
  localStorage.setItem("aac.rail.shut", "1");
  localStorage.setItem("aac.insp.shut", "0");
  localStorage.setItem("aac.tour", "taken");
});
await page.goto(URL + "/#draw", { waitUntil: "networkidle0", timeout: 60000 });
await page.waitForFunction(() => window.TerraneApp.Canvas.engine && window.TerraneApp.Canvas.engine.live(), { timeout: 30000 });
await pause(800);
// The chooser as the canvas opens it when a line is drawn between two records.
const ask = async (a, b) => {
  await page.evaluate(() => { const m = document.getElementById("ctxMenu"); if (m) m.remove(); });
  await page.evaluate((a, b) => window.TerraneApp.openConnectChooser(a, b, 420, 200, {
    head: "What is this line?", keep: "Just a line, on this diagram only",
    why: "Kept in this diagram's file. The estate has no connection between them, and no other diagram shows it.",
    chose: function () {},
  }), a, b);
  await page.waitForSelector("#ctxMenu .connect-opt", { timeout: 20000 });
  await pause(300);
};
const read = () => page.evaluate(() => {
  const m = document.getElementById("ctxMenu");
  return Array.from(m.querySelectorAll(".connect-opt")).map((o) => ({
    said: ((o.querySelector(".co-s") || {}).innerText || "").replace(/\s+/g, " "), why: (o.querySelector(".co-h") || {}).innerText || "",
    likeliest: o.classList.contains("is-likeliest"), chips: Array.from(o.querySelectorAll(".co-kind")).map((c) => c.innerText),
    likely: (o.querySelector(".co-kind.is-likely") || {}).innerText || "", more: (o.querySelector(".co-more") || {}).innerText || "" }));
});

await ask("SYS-LENDING-WEB", "SYS-LENDING-DB");
let [first, second] = await read();
check("the front end reading and writing its database comes first",
  /^Installment Lending Web reads and writes Installment Lending Database\s*likeliest$/.test(first.said) && first.likeliest, JSON.stringify(first));
check("by its own datastore, as the estate's six are", first.why === "Installment Lending Database is a relational database; " +
  "the estate makes its 6 connections into one by its own datastore." && first.likely === "Its own datastore", first.why);
check("its chips its two ways in", JSON.stringify(first.chips) === JSON.stringify(["Its own datastore", "Pipeline load"]) &&
  /^and 14 more kinds$/.test(first.more), JSON.stringify(first.chips) + " " + first.more);
check("the database feeding the front end second, by its ways out", second.said === "Installment Lending Database feeds Installment Lending Web" &&
  second.why === "Installment Lending Database is a relational database, and the estate has no connection out of one yet: " +
  "a change data capture feed or a scheduled extract.", JSON.stringify(second));
await page.screenshot({ path: OUT + "/into.png" });

await ask("SYS-LENDPERF-PIPELINE", "SYS-LENDING-DB");
const menu = await read();
const out = menu[0], shared = menu.find((o) => /reads and writes/.test(o.said));
check("from another product's pipeline, the database feeding it is first and likeliest",
  /^Installment Lending Database feeds Lending Portfolio Performance Pipeline\s*likeliest$/.test(out.said) && out.likeliest, JSON.stringify(out));
check("its two ways out its only chips, neither said likeliest", JSON.stringify(out.chips) ===
  JSON.stringify(["Change data capture feed", "Scheduled extract"]) && !out.likely, JSON.stringify(out.chips));
check("the pipeline reaching in is last of the two, said to be the shared database",
  menu.indexOf(shared) === 1 && !shared.likeliest && / It is already Installment Lending Service's own datastore; a second system reaching into it is the shared database the library deprecates\.$/.test(shared.why),
  JSON.stringify(shared));
await page.screenshot({ path: OUT + "/out.png" });

// A chip fills the form for its kind; nothing is written.
const before = await page.evaluate(() => fetch("/api/list?type=interfaces").then((r) => r.text()));
await page.evaluate(() => Array.from(document.querySelectorAll("#ctxMenu .co-kind")).find((c) => c.innerText === "Change data capture feed").click());
await page.waitForFunction(() => !document.getElementById("drawer").hidden && document.querySelector("#drawerBody input"), { timeout: 20000 });
await pause(400);
const form = await page.evaluate(() => {
  const v = (name) => { const f = document.querySelector('#drawerBody [name="' + name + '"]'); return f ? f.value : null; };
  return { style: v("integration_style"), protocol: v("protocol"), auth: v("auth_method"), from: v("source_system_id"), to: v("target_system_id") };
});
check("the chip fills the form: an event over CDC, from the database to the pipeline",
  form.style === "Event" && form.protocol === "CDC" && form.auth === "IAM" && form.from === "SYS-LENDING-DB" &&
  form.to === "SYS-LENDPERF-PIPELINE", JSON.stringify(form));
await page.keyboard.press("Escape");
await pause(400);
check("and nothing is written", (await page.evaluate(() => fetch("/api/list?type=interfaces").then((r) => r.text()))) === before);
await page.evaluate(() => { const d = document.getElementById("drawerClose"); if (d && !document.getElementById("drawer").hidden) d.click(); });
await pause(300);

await ask("SYS-LENDING-DB", "SYS-REWARDS-STORE");
const two = (await read())[0];
check("between two databases, a replica and a backup lead", /^Installment Lending Database feeds Rewards Redemption Database/.test(two.said) &&
  /no connection from one relational database to another yet: a database replica, a backup, a change data capture feed or a scheduled extract\.$/.test(two.why),
  JSON.stringify(two));
check("no page errors", errors.length === 0, errors.join(" / "));
await browser.close();
process.exit(failed ? 1 : 0);
