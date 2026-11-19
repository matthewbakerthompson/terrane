// Does a kit place whole (V17)? On the canvas of lending-onboarding
// (arrange_probe.mjs makes it): Add's search for "ai assistant" lists the
// kit first, its systems named, and the one-box kind after it on Business
// systems (V18), the foot saying what the kit places; the kit
// dragged into prod-lending's region asks its name, says it lands in the
// account it was dropped in, offers the owner every system there has, takes
// the systems it answers from, and says what each part runs on there; Place
// writes one product and draws its six systems with their lines. Then the
// kit clicked rather than dropped waits for an account, and Just one box is
// the part's own question.
//
//   node 80_APP/tools/dev/kit_probe.mjs out/ URL
//
// It makes a product, so run it on a copy of the repository, never on the
// one you commit from. Exits 1 if a step does not do what it says.
import { mkdir } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
if (!OUT || !URL) {
  console.error("usage: node kit_probe.mjs OUT URL");
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
});
await page.goto(URL + "/#draw=lending-onboarding", { waitUntil: "networkidle0", timeout: 60000 });
await settled(page);
await pause(600);

async function search(q) {
  await page.evaluate(() => { const s = document.querySelector("#cvPicker .cv-search"); if (s) s.value = ""; });
  if (await page.$eval("#cvPicker", (p) => p.hidden)) await page.click("#cvAdd");
  await page.waitForSelector("#cvPicker .cv-search");
  await page.type("#cvPicker .cv-search", q);
  await pause(250);
  return page.$$eval("#cvPicker .cv-row", (rows) => rows.slice(0, 3).map((r) => ({
    name: r.querySelector(".cv-row-text b").textContent,
    sub: (r.querySelector(".cv-row-text span") || {}).textContent || "",
    tag: r.querySelector(".cv-tag").textContent })));
}

let rows = await search("ai assistant");
check("the kit is first, its systems named", rows[0] && rows[0].tag === "Kit" && rows[0].name === "AI assistant"
  && rows[0].sub === "6 systems: Service · Chat · Inference service · Document ingestion · Retrieval index · Conversation history",
  JSON.stringify(rows[0]));
check("the one-box kind after it", rows[1] && rows[1].tag === "Box" && rows[1].name === "AI assistant", JSON.stringify(rows[1]));
const foot = await page.$eval("#cvPicker .cv-detail", (d) => d.innerText);
check("the foot says what the kit places", /Whole applications · Application/.test(foot)
  && /It places service, chat, inference service, document ingestion, retrieval index and conversation history\./.test(foot),
  JSON.stringify(foot));
await page.screenshot({ path: `${OUT}/kit-picker.png` });

// Dropped as the list drops it, at a clear spot in the account's region.
async function spotIn(groupId) {
  return page.evaluate((gid) => {
    const cy = document.getElementById("cy")._cyreg.cy, sheet = document.getElementById("cy").getBoundingClientRect();
    const g = cy.getElementById(gid);
    if (g.empty()) return null;
    const bb = g.boundingBox({ includeLabels: false });
    const inner = g.descendants().map((d) => d.boundingBox({ includeLabels: false }));
    const gap = (x, y) => Math.min(...inner.map((b) => Math.max(b.x1 - x, x - b.x2, b.y1 - y, y - b.y2, 0)), 1e9);
    let best = null;
    for (let i = 1; i < 32; i += 1) for (let j = 1; j < 32; j += 1) {
      const x = bb.x1 + (bb.w * i) / 32, y = bb.y1 + 30 + ((bb.h - 30) * j) / 32;
      const sx = sheet.left + x * cy.zoom() + cy.pan().x, sy = sheet.top + y * cy.zoom() + cy.pan().y;
      if (sx < sheet.left + 20 || sx > sheet.right - 460 || sy < sheet.top + 70 || sy > sheet.bottom - 60) continue;
      const room = Math.min(gap(x, y), x - bb.x1, bb.x2 - x, y - bb.y1, bb.y2 - y);
      if (room > 0 && (!best || room > best.room)) best = { room, x: sx, y: sy };
    }
    return best;
  }, groupId);
}
const spot = await spotIn("grp::AWS::prod-lending::eu-west-2");
check("a clear spot in prod-lending's region", !!spot, JSON.stringify(spot));
await page.evaluate((at) => {
  const row = document.querySelector("#cvPicker .cv-row"), sheet = document.getElementById("mapSheet");
  const dt = new DataTransfer();
  row.dispatchEvent(new DragEvent("dragstart", { bubbles: true, dataTransfer: dt }));
  sheet.dispatchEvent(new DragEvent("dragover", { bubbles: true, cancelable: true, dataTransfer: dt, clientX: at.x, clientY: at.y }));
  sheet.dispatchEvent(new DragEvent("drop", { bubbles: true, cancelable: true, dataTransfer: dt, clientX: at.x, clientY: at.y }));
  row.dispatchEvent(new DragEvent("dragend", { bubbles: true, dataTransfer: dt }));
}, spot);
await page.waitForSelector("#cvKit .cv-kit-zone", { timeout: 15000 });

const panel = () => page.evaluate(() => {
  const box = document.getElementById("cvKit");
  const selects = box.querySelectorAll("select");
  return {
    head: box.querySelector(".cv-kit-head h2").textContent,
    sub: box.querySelector(".cv-kit-sub").textContent,
    name: box.querySelector(".cv-kit-body input").value,
    hints: Array.from(box.querySelectorAll(".cv-kit-hint")).map((p) => p.textContent),
    lands: selects[0].value, owner: selects[1].value,
    owned: box.querySelector(".cv-kit-owned").hidden ? "" : box.querySelector(".cv-kit-owned").textContent,
    chips: Array.from(box.querySelectorAll(".cv-kit-chip > span")).map((s) => s.textContent),
    zones: Array.from(box.querySelectorAll(".cv-kit-zone")).map((p) => p.textContent),
    made: Array.from(box.querySelectorAll(".cv-kit-made")).map((p) => p.querySelector("b").textContent + ": " + p.querySelector("span").textContent),
    waits: box.querySelector(".cv-kit-waits").hidden ? "" : box.querySelector(".cv-kit-waits").textContent,
    place: box.querySelector(".cv-kit-acts .btn.primary").textContent,
    placeOn: !box.querySelector(".cv-kit-acts .btn.primary").disabled,
    one: Array.from(box.querySelectorAll(".cv-kit-acts .btn")).map((b) => b.textContent).join(" | "),
    mark: document.getElementById("cvKitMark").hidden ? "" : document.getElementById("cvKitMark").textContent,
  };
});
let p = await panel();
check("asked where it was dropped", p.head === "Place the AI assistant kit"
  && p.sub === "Six systems on the AWS landing zone of prod-lending, where you dropped it. They land in its subnets by zone.",
  p.head + " / " + p.sub);
check("it lands in the account it was dropped in", p.lands === "AWS|prod-lending|eu-west-2"
  && p.hints.includes("The account you dropped it in, in the Lending domain."), p.lands + " / " + p.hints.join(" | "));
check("the owner every system there has, said why", p.owner === "ORG-PRODUCT"
  && p.owned === "Owned by Product Management, as every system already in prod-lending that has an owner. Change",
  p.owner + " / " + p.owned);
check("the drop is marked", /AI assistantKit · 6 systems/.test(p.mark), p.mark);

await page.evaluate(() => { const i = document.querySelector("#cvKit .cv-kit-body input"); i.focus(); i.select(); });
await page.keyboard.type("Lending assistant");
await page.waitForFunction(() => /PRD-LENDING-ASSISTANT,/.test(document.querySelector("#cvKit .cv-kit-hint").textContent), { timeout: 10000 })
  .then(() => check("the name makes the product's id", true), () => check("the name makes the product's id", false));

async function answer(q) {
  await page.click("#cvKit .cv-kit-add");
  await page.type("#cvKit .cv-kit-find input", q);
  await pause(150);
  await page.keyboard.press("Enter");
  await pause(500);
}
await answer("Installment Lending Service");
await answer("Core Card Ledger");
await page.waitForFunction(() => document.querySelectorAll("#cvKit .cv-kit-chip").length === 2, { timeout: 5000 }).catch(() => {});
await pause(800);
p = await panel();
check("still where it was dropped, named", /^Six systems on the AWS landing zone of prod-lending, where you dropped it\./.test(p.sub)
  && p.hints.includes("The account you dropped it in, in the Lending domain."), p.sub);
check("it answers from the two systems chosen", p.chips.join() === "Installment Lending Service,Core Card Ledger", p.chips.join());
check("the app subnets, on what they share", p.zones[0] === "In the app subnets, on Amazon EKS and Amazon CloudWatch"
  && p.zones[1] === "In the data subnets", JSON.stringify(p.zones));
check("each part with what it runs on there", p.made.join(" | ") === [
  "Service: its own Amazon ElastiCache", "Chat: Microsoft Entra ID",
  "Inference service: Amazon Bedrock and Amazon Bedrock Guardrails", "Document ingestion: Amazon Bedrock",
  "Retrieval index: Amazon OpenSearch Service", "Conversation history: Amazon RDS for PostgreSQL, its own AWS Backup and AWS KMS",
].join(" | "), p.made.join(" | "));
check("Place 6 systems, or Just one box", p.placeOn && p.one === "Place 6 systems | Just one box" && !p.waits, p.one + " / " + p.waits);
await page.screenshot({ path: `${OUT}/kit-place.png` });

await page.click("#cvKit .cv-kit-acts .btn.primary");
await page.waitForFunction(() => Object.keys(window.TerraneApp.Canvas.cv.made || {}).length >= 6, { timeout: 30000 })
  .then(() => check("placed, its six systems made here", true), () => check("placed, its six systems made here", false));
const product = await page.evaluate(() => fetch("/api/entity?id=PRD-LENDING-ASSISTANT").then((r) => r.json()));
const pr = product.record || {};
check("one product, assembled from the kit, owned and in its domain", pr.owner_org_id === "ORG-PRODUCT"
  && pr.company_domain === "Lending" && pr.build_type === "ai-assistant" && pr.archetype === "compose:PRD-LENDING-ASSISTANT",
  JSON.stringify({ owner: pr.owner_org_id, domain: pr.company_domain, type: pr.build_type, shape: pr.archetype }));
await page.waitForFunction(() => {
  const cy = document.getElementById("cy")._cyreg.cy;
  return ["CHAT", "API", "INFERENCE", "INGEST", "INDEX", "HISTORY"].every((s) => cy.getElementById("SYS-LENDING-ASSISTANT-" + s).nonempty());
}, { timeout: 20000 }).then(() => check("the six drawn", true), () => check("the six drawn", false));
await pause(1200);
const lines = await page.evaluate(() => {
  const cy = document.getElementById("cy")._cyreg.cy;
  return cy.edges().filter((e) => /^SYS-LENDING-ASSISTANT-/.test(e.source().id()) || /^SYS-LENDING-ASSISTANT-/.test(e.target().id())).length;
});
check("with their lines", lines >= 6, lines);
const toastSaid = await page.evaluate(() => Array.from(document.querySelectorAll(".toast")).map((t) => t.textContent).join(" | "));
check("and said where it is saved", /Placed Lending assistant/.test(toastSaid) && /PRD-LENDING-ASSISTANT\.yaml/.test(toastSaid), toastSaid);
await page.screenshot({ path: `${OUT}/kit-placed.png` });

// Clicked rather than dropped: no account, so Place waits and says for what.
rows = await search("ai agent");
await page.click("#cvPicker .cv-row");
await page.waitForSelector("#cvKit .cv-kit-makes-h", { timeout: 10000 });
await pause(300);
p = await panel();
check("clicked, it waits for an account and an owner", p.head === "Place the AI agent kit" && !p.placeOn && p.lands === ""
  && p.waits === "Place waits for where it lands and who owns it.", p.head + " / " + p.waits + " / " + p.lands);
await page.select("#cvKit select", "Azure|azure-payments-prod|uksouth");
await page.waitForFunction(() => document.querySelectorAll("#cvKit .cv-kit-zone").length > 0, { timeout: 10000 });
await pause(300);
p = await panel();
check("an account chosen, the owner is offered and Place is open", p.owner === "ORG-MERCHANT" && p.placeOn
  && /^Owned by .*, as every system already in azure-payments-prod\. Change$/.test(p.owned)
  && /Azure landing zone of azure-payments-prod\./.test(p.sub), p.owner + " / " + p.sub);
await page.screenshot({ path: `${OUT}/kit-clicked.png` });
await page.click("#cvKit .cv-kit-x");

// Just one box: the part's own question, where the kit was dropped.
await search("ai assistant");
const spot2 = await spotIn("grp::AWS::prod-lending::eu-west-2");
await page.evaluate((at) => {
  const row = document.querySelector("#cvPicker .cv-row"), sheet = document.getElementById("mapSheet");
  const dt = new DataTransfer();
  row.dispatchEvent(new DragEvent("dragstart", { bubbles: true, dataTransfer: dt }));
  sheet.dispatchEvent(new DragEvent("drop", { bubbles: true, cancelable: true, dataTransfer: dt, clientX: at.x, clientY: at.y }));
  row.dispatchEvent(new DragEvent("dragend", { bubbles: true, dataTransfer: dt }));
}, spot2);
await page.waitForSelector("#cvKit .cv-kit-zone", { timeout: 15000 });
await page.evaluate(() => Array.from(document.querySelectorAll("#cvKit .cv-kit-acts .btn")).find((b) => b.textContent === "Just one box").click());
await page.waitForSelector("#ctxMenu .connect-input", { timeout: 5000 })
  .then(() => check("Just one box asks the part's name", true), () => check("Just one box asks the part's name", false));
const one = await page.evaluate(() => ({ head: document.querySelector("#ctxMenu .ctx-head").textContent,
  kit: !document.getElementById("cvKit").hidden }));
check("and the kit's panel is gone", !one.kit && /AI assistant/.test(one.head), JSON.stringify(one));
await page.keyboard.press("Escape");
check("no page errors", !errors.length, errors.join(" | "));
await browser.close();
process.exit(failed ? 1 : 0);
