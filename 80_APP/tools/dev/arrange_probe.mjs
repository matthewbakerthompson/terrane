// The canvas arranged by hand, walked the way a person would: a box dragged
// within its zone (the guide and the note beside it), a system dragged in
// from the picker, a box carried into another zone and moved there, a
// boundary dragged, Lay out again and Undo. A PNG per step into OUT, and a
// line per step saying what the file and the drawing said: how many lines
// the file keeps, which boxes moved, how far a drop landed from where it
// was let go.
//
//   node 80_APP/tools/dev/arrange_probe.mjs out/ http://127.0.0.1:8020 [graphite]
//
// It writes: a Lending portal made from the Web application part, the
// diagram lending-onboarding (Network Topology kept to prod-lending, the
// portal and the lending API pinned), the moves, and the portal's zone.
// Run it on a copy of the repository, never on the one you commit from;
// on a copy already walked, delete the portal's record and the diagram's
// file first (10_MODEL/systems/SYS-LENDING-PORTAL.yaml,
// 30_VIEWS/lending-onboarding.view.yaml) and put the model back.
import { mkdir } from "node:fs/promises";
import { launch, openView, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
const TONE = process.argv[4] || "stone";
const VIEW = "lending-onboarding";
const suffix = TONE === "graphite" ? "-graphite" : "";
if (!OUT || !URL) {
  console.error("usage: node arrange_probe.mjs OUT URL [graphite]");
  process.exit(2);
}
await mkdir(OUT, { recursive: true });
const pause = (ms) => new Promise((r) => setTimeout(r, ms));

// The diagram the canvas would have made, through the canvas's own
// endpoints, unless a walk already made it.
async function post(path, body) {
  const r = await fetch(URL + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const d = await r.json();
  if (!r.ok) throw new Error(path + ": " + (d.error || r.status));
  return d;
}
if (!(await fetch(URL + "/api/view?id=" + VIEW)).ok) {
  const into = [["cloud_provider", "AWS"], ["cloud_account", "prod-lending"], ["region", "eu-west-2"],
    ["availability_zone", "eu-west-2a"]].map(([field, value]) => ({ field, value }));
  const made = await post("/api/canvas/record", { part: "web-app", into, name: "Lending portal" });
  await post("/api/canvas/save", { id: null, data: {
    title: "Lending onboarding", category: "Application", kind: "diagram",
    places: [{ view: "network-topology", only: { cloud_account: ["prod-lending"] } }],
    scope: { pin: [made.id, "SYS-LENDING-API"] }, edges: [{ via: "interfaces" }] } });
  console.log("made", made.id, "and the diagram", VIEW);
}

const browser = await launch();
const errors = [];
const page = await openView(browser, URL, "draw=" + VIEW + (TONE === "graphite" ? "&tone=graphite" : ""));
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
await settled(page);
await pause(900);

async function shot(name) {
  await page.screenshot({ path: `${OUT}/${name}${suffix}.png` });
  console.log("shot", name + suffix);
}
async function file() {
  return page.evaluate(async (id) => {
    const r = await fetch("/api/view?id=" + id);
    const d = await r.json();
    return { positions: (d.data || {}).positions || null, text: d.text };
  }, VIEW);
}
async function leaves() {
  return page.evaluate(() => {
    const cy = document.getElementById("cy")._cyreg.cy;
    const out = {};
    // Top-left corners, as positions are kept: a box grows with its
    // connections, and its middle moves when it does.
    cy.nodes().forEach((n) => { if (!n.data("isGroup")) out[n.id()] = [n.position("x") - n.width() / 2, n.position("y") - n.height() / 2]; });
    return out;
  });
}
async function centerOf(id) {
  return page.evaluate((nid) => { const n = document.getElementById("cy")._cyreg.cy.getElementById(nid); return [n.position("x"), n.position("y")]; }, id);
}
async function chip() {
  return page.evaluate(() => { const c = document.getElementById("cvLayout"); return c.hidden ? "(hidden)" : c.textContent; });
}
// A clear spot inside a boundary, in screen coordinates: drag_probe's search.
async function clearSpot(groupId, avoid) {
  return page.evaluate((gid, avoidId) => {
    const cy = document.getElementById("cy")._cyreg.cy;
    const sheet = document.getElementById("cy").getBoundingClientRect();
    const g = cy.getElementById(gid);
    const bb = g.boundingBox({ includeLabels: false });
    const inner = g.descendants().filter((d) => d.id() !== avoidId).map((d) => d.boundingBox({ includeLabels: false }));
    const gap = (x, y) => Math.min(...inner.map((b) => Math.max(b.x1 - x, x - b.x2, b.y1 - y, y - b.y2, 0)), 1e9);
    let best = null;
    for (let i = 1; i < 32; i += 1) for (let j = 1; j < 32; j += 1) {
      const x = bb.x1 + (bb.w * i) / 32, y = bb.y1 + 30 + ((bb.h - 30) * j) / 32;
      const room = Math.min(gap(x, y), x - bb.x1, bb.x2 - x, y - bb.y1, bb.y2 - y);
      if (room > 0 && (!best || room > best.room)) best = { room, x, y };
    }
    return best && { x: sheet.left + best.x * cy.zoom() + cy.pan().x, y: sheet.top + best.y * cy.zoom() + cy.pan().y,
      mx: best.x, my: best.y };
  }, groupId, avoid);
}
async function drag(from, to, hold) {
  await page.mouse.move(from.x, from.y);
  await page.mouse.down();
  const steps = 14;
  for (let i = 1; i <= steps; i += 1) {
    await page.mouse.move(from.x + ((to.x - from.x) * i) / steps, from.y + ((to.y - from.y) * i) / steps);
    await pause(30);
  }
  if (hold) await hold();
  await page.mouse.up();
  await pause(1200);
}

// 1. As placed: laid out.
console.log("chip:", await chip(), "| file positions:", (await file()).positions ? "yes" : "none");
await shot("positions-laid-out");

// 2. The portal carried within its zone, and put down.
const ZONE = "grp::AWS::prod-lending::eu-west-2::eu-west-2a";
const PORTAL = "SYS-LENDING-PORTAL";
const before = await leaves();
const from = await page.evaluate((id) => window.__aacNodeAt(id), PORTAL);
// Under Lending Public Subnet A, a few pixels off its middle: the guide
// should show and the box land on the line.
const to = await page.evaluate(() => {
  const cy = document.getElementById("cy")._cyreg.cy;
  const sheet = document.getElementById("cy").getBoundingClientRect();
  const a = cy.getElementById("TS-NET-SUB-LEND-PUB-A");
  const p = a.length ? a.position() : { x: 0, y: 0 };
  const m = { x: p.x + 3, y: p.y + 80 };
  return { x: sheet.left + m.x * cy.zoom() + cy.pan().x, y: sheet.top + m.y * cy.zoom() + cy.pan().y };
});
await drag(from, to, async () => {
  await pause(150);
  const guides = await page.evaluate(() => [!document.getElementById("cvGuideX").hidden, !document.getElementById("cvGuideY").hidden]);
  console.log("guides while carried (x, y):", guides);
  await shot("positions-moving");
});
await pause(800);
await shot("positions-arranged");
let f = await file();
const after = await leaves();
const moved = Object.keys(before).filter((k) => Math.abs(before[k][0] - after[k][0]) + Math.abs(before[k][1] - after[k][1]) > 1.5);
console.log("chip:", await chip(), "| kept lines:", f.positions && Object.keys(f.positions).length, "| boxes moved:", moved.join(", "));
console.log("portal line:", Object.entries(f.positions || {}).filter(([k]) => k.endsWith(PORTAL)).map(([k, v]) => k + ": " + JSON.stringify(v)).join("; "));

// 3. A system dragged in from the picker onto the region's own ground,
// where it sits already: it lands where it was dropped. Then the portal
// carried into zone eu-west-2b, which asks the move first and, once made,
// puts it where it was let go. Nothing else moves (measured against the
// lending API, since each drawing may put the sheet's corner elsewhere).
async function pickerDrop(query, name, target) {
  await page.click("#cvAdd");
  await pause(400);
  await page.type(".cv-search", query);
  await pause(500);
  await page.evaluate((nm, at) => {
    const row = Array.from(document.querySelectorAll(".cv-row")).filter((r) => r.textContent.indexOf(nm) !== -1)[0];
    const dt = new DataTransfer();
    row.dispatchEvent(new DragEvent("dragstart", { bubbles: true, dataTransfer: dt }));
    const sheet = document.getElementById("mapSheet");
    sheet.dispatchEvent(new DragEvent("dragover", { bubbles: true, cancelable: true, dataTransfer: dt, clientX: at.x, clientY: at.y }));
    sheet.dispatchEvent(new DragEvent("drop", { bubbles: true, cancelable: true, dataTransfer: dt, clientX: at.x, clientY: at.y }));
    row.dispatchEvent(new DragEvent("dragend", { bubbles: true, dataTransfer: dt }));
  }, name, target);
  await pause(2500);
  await settled(page);
  await pause(900);
}
async function modelOf(sx, sy) {
  return page.evaluate((x, y) => {
    const cy = document.getElementById("cy")._cyreg.cy;
    const sheet = document.getElementById("cy").getBoundingClientRect();
    return { x: (x - sheet.left - cy.pan().x) / cy.zoom(), y: (y - sheet.top - cy.pan().y) / cy.zoom() };
  }, sx, sy);
}
function against(all, ref) {
  const out = {};
  Object.keys(all).forEach((k) => { out[k] = [all[k][0] - all[ref][0], all[k][1] - all[ref][1]]; });
  return out;
}
// Moved by more than the whole-pixel rounding of the first freeze can
// account for (half a pixel a side, on the box and on the reference); the
// largest shift is said either way.
function movedAmong(a, b) {
  let most = 0;
  const out = Object.keys(a).filter((k) => {
    if (!b[k]) return false;
    const d = Math.max(Math.abs(a[k][0] - b[k][0]), Math.abs(a[k][1] - b[k][1]));
    most = Math.max(most, d);
    return d > 1.01;
  });
  out.push("(largest shift " + most.toFixed(2) + "px)");
  return out;
}
const REF = "SYS-LENDING-API";
const kept1 = await leaves();
const REGION = "grp::AWS::prod-lending::eu-west-2";
const spot = await clearSpot(REGION, null);
const spotModel = await modelOf(spot.x, spot.y);
const spotRel = [spotModel.x - kept1[REF][0], spotModel.y - kept1[REF][1]];
await pickerDrop("Async Worker", "Installment Lending Async Worker", spot);
const kept2 = await leaves();
const wc = await centerOf("SYS-LENDING-WORKER");
const w = [wc[0] - kept2[REF][0], wc[1] - kept2[REF][1]];
console.log("worker placed:", !!w, "| off its drop point by", w ? Math.round(Math.hypot(w[0] - spotRel[0], w[1] - spotRel[1])) : "-",
  "px | boxes that moved:", movedAmong(against(kept1, REF), against(kept2, REF)).join(", ") || "none");
await shot("positions-second");

const kept3 = await leaves();
const ZONE_B0 = "grp::AWS::prod-lending::eu-west-2::eu-west-2b";
const REF_B = "TS-NET-SUB-LEND-APP-B";
const spotB = await clearSpot(ZONE_B0, null);
const spotBModel = await modelOf(spotB.x, spotB.y);
const spotBRel = [spotBModel.x - kept3[REF_B][0], spotBModel.y - kept3[REF_B][1]];
const portalAt = await page.evaluate((id) => window.__aacNodeAt(id), PORTAL);
await drag(portalAt, spotB);
await pause(900);
const asked = await page.evaluate(() => { const m = document.getElementById("ctxMenu"); return m ? m.textContent.slice(0, 120) : ""; });
console.log("portal carried into zone eu-west-2b, the chooser says:", asked);
await shot("positions-third-asks");
const moveIt = await page.$("#ctxMenu .connect-acts .btn.primary");
if (moveIt) { await moveIt.click(); await pause(2500); await settled(page); await pause(1200); }
const kept4 = await leaves();
const portalParent = await page.evaluate((id) => { const cy = document.getElementById("cy")._cyreg.cy; return cy.getElementById(id).parent().id(); }, PORTAL);
const pc = await centerOf(PORTAL);
const pr = [pc[0] - kept4[REF_B][0], pc[1] - kept4[REF_B][1]];
const others3 = against(kept3, REF), others4 = against(kept4, REF);
delete others3[PORTAL]; delete others4[PORTAL];
console.log("portal now in", portalParent, "| off its drop point by", Math.round(Math.hypot(pr[0] - spotBRel[0], pr[1] - spotBRel[1])),
  "px | boxes that moved:", movedAmong(others3, others4).join(", ") || "none");
f = await file();
console.log("portal lines:", Object.keys(f.positions || {}).filter((k) => k.endsWith(PORTAL)).join("; "));
await shot("positions-third");
f = await file();
const lines1 = f.text.split(String.fromCharCode(10));

// 4. A boundary dragged: zone eu-west-2b by its own ground.
const ZONE_B = "grp::AWS::prod-lending::eu-west-2::eu-west-2b";
const grip = await page.evaluate((gid) => {
  const cy = document.getElementById("cy")._cyreg.cy;
  const sheet = document.getElementById("cy").getBoundingClientRect();
  const bb = cy.getElementById(gid).boundingBox({ includeLabels: false });
  return { x: sheet.left + (bb.x1 + 40) * cy.zoom() + cy.pan().x, y: sheet.top + (bb.y2 - 8) * cy.zoom() + cy.pan().y };
}, ZONE_B);
const inB = await leaves();
await drag(grip, { x: grip.x + 30, y: grip.y + 70 });
await pause(600);
await shot("positions-boundary-moved");
const afterB = await leaves();
f = await file();
const lines2 = f.text.split("\n");
const changedLines = lines2.filter((l, i) => l !== lines1[i]);
const movedB = Object.keys(inB).filter((k) => Math.abs(inB[k][0] - afterB[k][0]) + Math.abs(inB[k][1] - afterB[k][1]) > 1.5);
console.log("boundary moved:", movedB.length, "boxes went with it | file lines changed:", changedLines.join(" || "));

// 5. Lay out again, then Undo.
await page.click(".cv-again");
await pause(2500);
await settled(page);
await pause(900);
await shot("positions-laid-out-again");
f = await file();
console.log("after Lay out again: chip:", await chip(), "| file positions:", f.positions ? Object.keys(f.positions).length : "none");
const undo = await page.$(".toast .toast-act");
if (undo) { await undo.click(); await pause(2500); await settled(page); await pause(700); }
f = await file();
console.log("after Undo: chip:", await chip(), "| file positions:", f.positions ? Object.keys(f.positions).length : "none");
await shot("positions-undone");
console.log("page errors:", errors.length ? errors.join(" | ") : "none");
await browser.close();
