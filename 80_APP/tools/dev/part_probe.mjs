// Does Add find a part by what each cloud calls it, and does a part placed
// in an account of a cloud come out as that cloud's product? On the canvas
// of lending-onboarding (arrange_probe.mjs makes it): Add's search for
// "EC2", "Compute Engine" and a former name, each row named for what was
// asked; the EC2 row dragged into zone eu-west-2a, the AWS zone, and the
// name it is asked for given as Amazon EC2, with what AWS calls it offered;
// then placed, the record's product Amazon EC2 and its mark EC2's.
//
//   node 80_APP/tools/dev/part_probe.mjs out/ URL
//
// It makes a record, so run it on a copy of the repository, never on the
// one you commit from. Exits 1 if a step does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node part_probe.mjs OUT URL");
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
await page.evaluateOnNewDocument(() => {
  localStorage.setItem("aac.rail.shut", "1");
  localStorage.setItem("aac.insp.shut", "0");
  localStorage.setItem("aac.tour", "taken");
});
await page.goto(URL + "/#draw=lending-onboarding", { waitUntil: "networkidle0", timeout: 60000 });
await settled(page);
await pause(600);

// Each search, and the first row it gives: its name and the line under it.
async function search(q) {
  await page.evaluate(() => { const s = document.querySelector("#cvPicker .cv-search"); if (s) s.value = ""; });
  if (await page.$eval("#cvPicker", (p) => p.hidden)) await page.click("#cvAdd");
  await page.waitForSelector("#cvPicker .cv-search");
  await page.type("#cvPicker .cv-search", q);
  await pause(200);
  return page.$$eval("#cvPicker .cv-row", (rows) => rows.slice(0, 3).map((r) => ({
    name: r.querySelector(".cv-row-text b").textContent, sub: r.querySelector(".cv-row-text span").textContent })));
}
let rows = await search("EC2");
check("EC2 finds the virtual machine, named for what was asked", rows[0] && rows[0].name === "Amazon EC2"
  && /Virtual machine · AWS/.test(rows[0].sub), JSON.stringify(rows[0]));
rows = await search("Compute Engine");
check("Compute Engine finds it on Google Cloud", rows.some((r) => r.name === "Compute Engine" && /GCP/.test(r.sub)),
  JSON.stringify(rows));
rows = await search("Azure OpenAI");
check("a former name finds the product it is now", rows.some((r) => r.name === "Microsoft Foundry Models"),
  JSON.stringify(rows));
rows = await search("EC2");
await page.screenshot({ path: `${OUT}/part-search.png` });

// Dropped as a drag from the list would drop it: the browser's own drag
// events, at a clear spot in the AWS zone eu-west-2a.
const spot = await page.evaluate(() => {
  const cy = document.getElementById("cy")._cyreg.cy, sheet = document.getElementById("cy").getBoundingClientRect();
  const g = cy.getElementById("grp::AWS::prod-lending::eu-west-2::eu-west-2a");
  const bb = g.boundingBox({ includeLabels: false });
  const inner = g.descendants().map((d) => d.boundingBox({ includeLabels: false }));
  const gap = (x, y) => Math.min(...inner.map((b) => Math.max(b.x1 - x, x - b.x2, b.y1 - y, y - b.y2, 0)), 1e9);
  let best = null;
  for (let i = 1; i < 32; i += 1) for (let j = 1; j < 32; j += 1) {
    const x = bb.x1 + (bb.w * i) / 32, y = bb.y1 + 30 + ((bb.h - 30) * j) / 32;
    const room = Math.min(gap(x, y), x - bb.x1, bb.x2 - x, y - bb.y1, bb.y2 - y);
    if (room > 0 && (!best || room > best.room)) best = { room, x, y };
  }
  return best && { x: sheet.left + best.x * cy.zoom() + cy.pan().x, y: sheet.top + best.y * cy.zoom() + cy.pan().y };
});
await page.evaluate((at) => {
  const row = document.querySelector("#cvPicker .cv-row"), sheet = document.getElementById("mapSheet");
  const dt = new DataTransfer();
  row.dispatchEvent(new DragEvent("dragstart", { bubbles: true, dataTransfer: dt }));
  sheet.dispatchEvent(new DragEvent("dragover", { bubbles: true, cancelable: true, dataTransfer: dt, clientX: at.x, clientY: at.y }));
  sheet.dispatchEvent(new DragEvent("drop", { bubbles: true, cancelable: true, dataTransfer: dt, clientX: at.x, clientY: at.y }));
  row.dispatchEvent(new DragEvent("dragend", { bubbles: true, dataTransfer: dt }));
}, spot);
await page.waitForSelector("#ctxMenu .connect-input", { timeout: 5000 });
const asked = await page.evaluate(() => ({
  name: document.querySelector("#ctxMenu .connect-input").value,
  where: document.querySelector("#ctxMenu .connect-ask").textContent,
  offers: Array.from(document.querySelectorAll("#ctxMenu .cv-offer")).map((b) => b.textContent + (b.getAttribute("aria-checked") === "true" ? "*" : "")),
}));
check("dropped in the AWS zone, it is asked for as Amazon EC2", asked.name === "Amazon EC2" && /eu-west-2a/.test(asked.where),
  JSON.stringify(asked));
check("with what AWS calls it offered", asked.offers.join() === "Amazon EC2*", asked.offers.join());
await page.screenshot({ path: `${OUT}/part-asked.png` });
await page.click("#ctxMenu .connect-acts .btn.primary");
await page.waitForFunction(() => Object.keys(window.TerraneApp.Canvas.cv.made || {}).length > 0, { timeout: 15000 });
const id = await page.evaluate(() => Object.keys(window.TerraneApp.Canvas.cv.made)[0]);
const entity = await page.evaluate((i) => fetch("/api/entity?id=" + encodeURIComponent(i)).then((r) => r.json()), id);
const r = entity.record || {};
check("placed, its product is Amazon EC2 on AWS", r.product === "Amazon EC2" && r.cloud_provider === "AWS"
  && r.availability_zone === "eu-west-2a", JSON.stringify({ id, product: r.product, cloud: r.cloud_provider, az: r.availability_zone }));
await page.waitForFunction((i) => {
  const cy = document.getElementById("cy")._cyreg.cy, n = cy.getElementById(i);
  return n.nonempty() && /ec2/.test(String(n.data("icon") || ""));
}, { timeout: 15000 }, id).then(() => check("and it wears EC2's mark", true), () => check("and it wears EC2's mark", false));
await pause(800);
await page.screenshot({ path: `${OUT}/part-placed.png` });
check("no page errors", !errors.length, errors.join(" | "));
await browser.close();
process.exit(failed ? 1 : 0);
