// Does Add place the rest of the estate (V19)? On the canvas of
// lending-onboarding (arrange_probe.mjs makes it): a data asset picked from
// the Data shelf is drawn with lines to the systems there that read or
// write it, and an actor with lines to the systems it uses; the Public web
// tier block dragged into prod-lending's region asks its name, says it
// lands in the account it was dropped in and who owns it, and lists its
// four services with AWS's products in the order a request meets them;
// Place writes them with the account's fields and draws them with their
// three lines. Takes block-place.png and block-placed.png.
//
//   node 80_APP/tools/dev/estate_probe.mjs out/ URL
//
// It makes records, so run it on a copy of the repository, never on the
// one you commit from. Exits 1 if a step does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node estate_probe.mjs OUT URL");
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
await page.setViewport({ width: 1440, height: 900 });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
await page.evaluateOnNewDocument(() => {
  localStorage.setItem("aac.rail.shut", "0");
  localStorage.setItem("aac.insp.shut", "1");
  localStorage.setItem("aac.tour", "taken");
  localStorage.setItem("aac.tone", "stone");
  localStorage.setItem("aac.add.shelf", "data");
});
await page.goto(URL + "/#draw=lending-onboarding", { waitUntil: "networkidle0", timeout: 60000 });
await settled(page);
await pause(600);

const openOn = async (shelf) => {
  if (await page.$eval("#cvPicker", (p) => p.hidden)) await page.click("#cvAdd");
  await page.waitForSelector("#cvPicker .cv-shelf");
  await page.evaluate((n) => Array.from(document.querySelectorAll("#cvPicker .cv-shelf"))
    .find((b) => b.firstChild.textContent === n).click(), shelf);
  await pause(300);
};
// What a record placed is joined to on the sheet, by the record's name.
const joined = (name) => page.evaluate((nm) => {
  const cy = document.getElementById("cy")._cyreg.cy;
  const n = cy.nodes().filter((x) => (x.data("label") || x.data("name") || "").replace(/\s+/g, " ") === nm)[0];
  if (!n) return null;
  return n.connectedEdges().map((e) => (e.source() === n ? e.target() : e.source()).data("label") || "").map((s) => s.replace(/\s+/g, " "));
}, name);
const place = async (shelf, name) => {
  await openOn(shelf);
  await page.evaluate((nm) => Array.from(document.querySelectorAll("#cvPicker .cv-row"))
    .find((r) => r.innerText.trim() === nm).click(), name);
  await page.waitForFunction((nm) => {
    const cy = document.getElementById("cy")._cyreg.cy;
    return cy.nodes().some((x) => (x.data("label") || "").replace(/\s+/g, " ") === nm);
  }, { timeout: 20000 }, name).catch(() => {});
  await pause(1500);
  return joined(name);
};

let ends = await place("Data", "Installment Lending operational data");
check("a data asset placed is joined to what writes and reads it here", Array.isArray(ends) && ends.length > 0, JSON.stringify(ends));
ends = await place("Actors", "Loan Applicant");
check("an actor placed is drawn", Array.isArray(ends), JSON.stringify(ends));

// The block, dropped as the list drops it, at a clear spot in the region.
await openOn("Building blocks");
const spot = await page.evaluate(() => {
  const cy = document.getElementById("cy")._cyreg.cy, sheet = document.getElementById("cy").getBoundingClientRect();
  const g = cy.getElementById("grp::AWS::prod-lending::eu-west-2");
  if (g.empty()) return null;
  const bb = g.renderedBoundingBox({ includeLabels: false });
  return { x: Math.min(sheet.left + bb.x2 - 40, sheet.right - 480), y: sheet.top + bb.y1 + 20 };
});
check("a spot in prod-lending's region", !!spot, JSON.stringify(spot));
await page.evaluate((at) => {
  const row = Array.from(document.querySelectorAll("#cvPicker .cv-row")).find((r) => r.innerText.indexOf("Public web tier") === 0);
  const sheet = document.getElementById("mapSheet"), dt = new DataTransfer();
  row.dispatchEvent(new DragEvent("dragstart", { bubbles: true, dataTransfer: dt }));
  sheet.dispatchEvent(new DragEvent("dragover", { bubbles: true, cancelable: true, dataTransfer: dt, clientX: at.x, clientY: at.y }));
  sheet.dispatchEvent(new DragEvent("drop", { bubbles: true, cancelable: true, dataTransfer: dt, clientX: at.x, clientY: at.y }));
  row.dispatchEvent(new DragEvent("dragend", { bubbles: true, dataTransfer: dt }));
}, spot);
await page.waitForSelector("#cvKit .cv-kit-made", { timeout: 15000 });
await page.evaluate(() => { const i = document.querySelector("#cvKit .cv-kit-body input"); i.focus(); i.select(); });
await page.keyboard.type("Lending portal");
await page.waitForFunction(() => /Lending portal DNS/.test(document.querySelector("#cvKit .cv-kit-hint").textContent), { timeout: 10000 }).catch(() => {});
await pause(400);
const p = await page.evaluate(() => {
  const box = document.getElementById("cvKit"), selects = box.querySelectorAll("select");
  return {
    head: box.querySelector(".cv-kit-head h2").textContent, sub: box.querySelector(".cv-kit-sub").textContent,
    hints: Array.from(box.querySelectorAll(".cv-kit-hint")).map((h) => h.textContent),
    lands: selects[0].value, owner: selects[1].value,
    made: Array.from(box.querySelectorAll(".cv-kit-made")).map((m) => m.querySelector("b").textContent + ": " + m.querySelector("span").textContent),
    acts: Array.from(box.querySelectorAll(".cv-kit-acts .btn")).map((b) => b.textContent + (b.disabled ? " (off)" : "")).join(" | "),
    mark: document.getElementById("cvKitMark").hidden ? "" : document.getElementById("cvKitMark").textContent,
  };
});
check("asked where it was dropped", p.head === "Place the Public web tier block"
  && p.sub === "Four cloud services on AWS in prod-lending, eu-west-2, where you dropped it, each joined to the next in the order below.",
  p.head + " / " + p.sub);
check("named for what it is for", p.hints[0] === "Each is named for it: Lending portal DNS, Lending portal Load balancer.", p.hints[0]);
check("it lands where it was dropped, owned as most there are", p.lands === "AWS|prod-lending|eu-west-2" && p.owner === "ORG-TECH"
  && p.hints.some((h) => /^As \d+ of the \d+ services already in prod-lending are\.$/.test(h)), p.lands + " / " + p.owner + " / " + p.hints.join(" | "));
check("its services in the order a request meets them, each AWS's", p.made.join(" | ") ===
  "DNS: Amazon Route 53 | Content delivery network: Amazon CloudFront | Web application firewall: AWS WAF | Load balancer: Application Load Balancer",
  p.made.join(" | "));
check("Place 4 services, or Cancel", p.acts === "Place 4 services | Cancel", p.acts);
check("the drop is marked", /Public web tierBlock · 4 services/.test(p.mark), p.mark);
await page.screenshot({ path: `${OUT}/block-place.png` });

await page.click("#cvKit .cv-kit-acts .btn.primary");
await page.waitForFunction(() => {
  const cy = document.getElementById("cy")._cyreg.cy;
  return ["DNS", "CDN", "WAF", "LOAD-BALANCER"].every((s) => cy.getElementById("TS-LENDING-PORTAL-" + s).nonempty());
}, { timeout: 30000 }).then(() => check("the four drawn", true), () => check("the four drawn", false));
await pause(1500);
const lines = await page.evaluate(() => {
  const cy = document.getElementById("cy")._cyreg.cy;
  return cy.edges().filter((e) => /^TS-LENDING-PORTAL-/.test(e.source().id()) && /^TS-LENDING-PORTAL-/.test(e.target().id())).length;
});
check("with their three lines", lines === 3, lines);
const rec = await page.evaluate(() => fetch("/api/entity?id=TS-LENDING-PORTAL-CDN").then((r) => r.json()));
const r = rec.record || {};
check("each in the account, owned, and the cloud's product", r.cloud_account === "prod-lending" && r.region === "eu-west-2"
  && r.cloud_provider === "AWS" && r.owner_org_id === "ORG-TECH" && r.product === "Amazon CloudFront",
  JSON.stringify({ account: r.cloud_account, region: r.region, cloud: r.cloud_provider, owner: r.owner_org_id, product: r.product }));
const toastSaid = await page.evaluate(() => Array.from(document.querySelectorAll(".toast")).map((t) => t.textContent).join(" | "));
check("and said where they are saved", /Placed Lending portal/.test(toastSaid) && /4 cloud services and their lines, in prod-lending/.test(toastSaid), toastSaid);
await page.screenshot({ path: `${OUT}/block-placed.png` });
check("no page errors", !errors.length, errors.join(" | "));
await browser.close();
process.exit(failed ? 1 : 0);
