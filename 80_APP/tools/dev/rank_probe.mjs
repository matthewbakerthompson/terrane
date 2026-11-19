// Does What is this line? rank its answers, as V15 draws it? A line drawn
// on a new diagram from the installment lending web front end to the
// application fraud screening: the front end calling the screening comes
// first, marked likeliest, with why in the estate's numbers and its
// likeliest kinds as chips, the likeliest kind first; the screening calling
// the front end second, with its own why; Just a line after. A chip opens
// the interface form filled in for that kind, and nothing is written. Where
// the one called offers interfaces of its own, the chooser asks through
// which first, so the card ledger's likeliest call has no chips.
//
//   node 80_APP/tools/dev/rank_probe.mjs out/ URL
//
// It writes nothing; run it on a copy of the repository all the same.
// Exits 1 if a step does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node rank_probe.mjs OUT URL");
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
const ask = (a, b) => page.evaluate((a, b) => window.TerraneApp.openConnectChooser(a, b, 420, 260, {
  head: "What is this line?", keep: "Just a line, on this diagram only",
  why: "Kept in this diagram's file. The estate has no connection between them, and no other diagram shows it.",
  chose: function () {},
}), a, b);
const read = () => page.evaluate(() => {
  const m = document.getElementById("ctxMenu");
  return {
    head: m.querySelector(".ctx-head").innerText,
    options: Array.from(m.querySelectorAll(".connect-opt")).map((o) => ({
      said: (o.querySelector(".co-s") || {}).innerText || "", why: (o.querySelector(".co-h") || {}).innerText || "",
      likeliest: o.classList.contains("is-likeliest"), chips: Array.from(o.querySelectorAll(".co-kind")).map((c) => c.innerText),
      likely: (o.querySelector(".co-kind.is-likely") || {}).innerText || "", more: (o.querySelector(".co-more") || {}).innerText || "" })),
  };
});
await ask("SYS-LENDING-WEB", "SYS-APPFRAUD");
await page.waitForSelector("#ctxMenu .connect-opt", { timeout: 20000 });
await pause(300);
let menu = await read();
const [first, second] = menu.options;
check("the front end calling the screening comes first, marked likeliest", menu.head === "What is this line?" &&
  /^Installment Lending Web calls Application fraud screening\s*likeliest$/.test(first.said) && first.likeliest, JSON.stringify(first));
check("with why, in the estate's numbers", /^Application fraud screening is called once in the estate, by an API call; the estate has 39 of those among its \d+ interfaces\.$/.test(first.why), first.why);
check("and its likeliest kinds as chips, the likeliest first", first.chips.length === 3 && first.likely === "API call" &&
  first.chips[0] === "API call" && /^and \d+ more kinds$/.test(first.more), JSON.stringify(first.chips) + " " + first.more);
check("the other way second, with its own why", /^Application fraud screening calls Installment Lending Web$/.test(second.said) &&
  !second.likeliest && /^Installment Lending Web is called once in the estate, by an API call;/.test(second.why), JSON.stringify(second));
check("just a line is still offered", menu.options.some((o) => o.said === "Just a line, on this diagram only"));
await page.screenshot({ path: OUT + "/rank.png" });

// A chip fills the form for its kind; nothing is written.
const before = await page.evaluate(() => fetch("/api/list?type=interfaces").then((r) => r.text()));
await page.evaluate(() => document.querySelector("#ctxMenu .co-kind.is-likely").click());
await page.waitForFunction(() => !document.getElementById("drawer").hidden && document.querySelector("#drawerBody input"), { timeout: 20000 });
await pause(400);
const form = await page.evaluate(() => {
  const v = (name) => { const f = document.querySelector('#drawerBody [name="' + name + '"]'); return f ? f.value : null; };
  return { auth: v("auth_method"), from: v("source_system_id"), to: v("target_system_id"), menu: !!document.getElementById("ctxMenu") };
});
// An API call fills OAuth2; the form's own default names no authentication.
check("a chip opens the form filled in for its kind", form.auth === "OAuth2", JSON.stringify(form));
check("from the front end to the screening, the menu gone", form.from === "SYS-LENDING-WEB" && form.to === "SYS-APPFRAUD" && !form.menu,
  JSON.stringify(form));
await page.keyboard.press("Escape");
await pause(400);
check("and nothing is written", (await page.evaluate(() => fetch("/api/list?type=interfaces").then((r) => r.text()))) === before);

// The ledger offers interfaces of its own: through which comes first.
await page.evaluate(() => { const d = document.getElementById("drawerClose"); if (d && !document.getElementById("drawer").hidden) d.click(); });
await pause(300);
await ask("SYS-CORE-LEDGER", "SYS-CARDSVC-WEB");
await page.waitForSelector("#ctxMenu .connect-opt", { timeout: 20000 });
await pause(300);
menu = await read();
check("a call to one that offers interfaces has no chips, and leans the right way", /^Card Servicing Web calls Core Card Ledger/.test(menu.options[0].said) &&
  menu.options[0].likeliest && !menu.options[0].chips.length, JSON.stringify(menu.options[0]));
check("no page errors", errors.length === 0, errors.join(" / "));
await browser.close();
process.exit(failed ? 1 : 0);
