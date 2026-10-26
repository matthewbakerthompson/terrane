// Does maxGraph draw the canvas where Cytoscape laid it out? Opens a canvas
// diagram with the canvas drawn by maxGraph (canvas/engine.js) and, for every
// box, compares the rectangle maxGraph's shape takes on screen with the
// outline Cytoscape gives the same node; then every line's ends; then a PNG
// of each drawing, Cytoscape's own and maxGraph's, to look at side by side.
//
//   node 80_APP/tools/dev/mirror_probe.mjs out/ http://127.0.0.1:8020 [view]
//
// The view defaults to lending-onboarding, which arrange_probe.mjs makes; on
// a fresh copy this makes it the same way, so run it on a copy of the
// repository, never on the one you commit from. Exits 1 if a box is off by
// more than TOLERANCE pixels or a drawn box or line is missing.
import { mkdir } from "node:fs/promises";
import { launch, settled } from "../capture.mjs";

const OUT = process.argv[2];
const URL = process.argv[3];
const VIEW = process.argv[4] || "lending-onboarding";
const TOLERANCE = 1.5;
if (!OUT || !URL) {
  console.error("usage: node mirror_probe.mjs OUT URL [view]");
  process.exit(2);
}
await mkdir(OUT, { recursive: true });

async function post(path, body) {
  const r = await fetch(URL + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const d = await r.json();
  if (!r.ok) throw new Error(path + ": " + (d.error || r.status));
  return d;
}
if (VIEW === "lending-onboarding" && !(await fetch(URL + "/api/view?id=" + VIEW)).ok) {
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
async function open(engine) {
  const page = await browser.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("console", (m) => { if (m.type() === "error" || m.type() === "warning") errors.push(m.text()); });
  await page.evaluateOnNewDocument((e) => {
    localStorage.setItem("aac.rail.shut", "1");
    localStorage.setItem("aac.insp.shut", "0");
    localStorage.setItem("aac.tour", "taken");
    localStorage.setItem("aac.canvas.engine", e);
  }, engine);
  await page.goto(URL + "/#draw=" + VIEW, { waitUntil: "networkidle0", timeout: 60000 });
  await settled(page);
  return { page, errors };
}

let failed = false;
const plain = await open("cytoscape");
await plain.page.screenshot({ path: `${OUT}/mirror-cytoscape.png` });
const drawn = await open("maxgraph");
await drawn.page.waitForFunction(() => {
  const s = document.querySelector(".mg-surface svg");
  return s && s.querySelectorAll("g g").length > 0;
}, { timeout: 30000 });
await new Promise((r) => setTimeout(r, 400));
await drawn.page.screenshot({ path: `${OUT}/mirror-maxgraph.png` });

const report = await drawn.page.evaluate((tol) => {
  const cy = document.getElementById("cy")._cyreg.cy;
  const z = cy.zoom();
  const engine = window.TerraneApp.Canvas.engine;
  const boxes = engine.boxes() || {};
  const off = [], missing = [];
  let compared = 0;
  cy.nodes().forEach((n) => {
    if (!n.visible()) return;
    const border = parseFloat(n.style("border-width")) || 0;
    const w = (n.outerWidth() - border) * z, h = (n.outerHeight() - border) * z, p = n.renderedPosition();
    const want = { x: p.x - w / 2, y: p.y - h / 2, w, h };
    const got = boxes[n.id()];
    if (!got) { missing.push(n.id()); return; }
    compared += 1;
    const worst = Math.max(Math.abs(got.x - want.x), Math.abs(got.y - want.y), Math.abs(got.w - want.w), Math.abs(got.h - want.h));
    if (worst > tol) off.push({ id: n.id(), by: Math.round(worst * 10) / 10 });
  });
  const lines = cy.edges().filter((e) => e.visible()).length;
  return { compared, off, missing, lines, drawn: engine.counts(), zoom: Math.round(z * 1000) / 1000,
    hidden: getComputedStyle(cy.container().querySelector("canvas")).opacity };
}, TOLERANCE);

// The surface's own drawn rectangles, read from the DOM: does what is on
// screen match what maxGraph's view state says?
const dom = await drawn.page.evaluate(() => {
  const engine = window.TerraneApp.Canvas.engine;
  return engine.drawnBoxes ? engine.drawnBoxes() : null;
});
let domOff = [];
if (dom) {
  const boxes = await drawn.page.evaluate(() => window.TerraneApp.Canvas.engine.boxes());
  domOff = Object.keys(dom).filter((id) => {
    const a = dom[id], b = boxes[id];
    return !b || Math.max(Math.abs(a.x - b.x), Math.abs(a.y - b.y), Math.abs(a.w - b.w), Math.abs(a.h - b.h)) > TOLERANCE + 2;
  });
}

console.log("boxes compared:", report.compared, "| off by more than", TOLERANCE + "px:", report.off.length ? JSON.stringify(report.off) : "none");
console.log("boxes Cytoscape drew that maxGraph did not:", report.missing.length ? report.missing.join(", ") : "none");
console.log("shapes on screen away from their state:", dom ? (domOff.length ? domOff.join(", ") : "none") : "(not read)");
console.log("lines Cytoscape drew:", report.lines, "| maxGraph drew:", report.drawn.lines, "boxes,", report.drawn.boxes,
  "| zoom", report.zoom, "| Cytoscape's canvas opacity under it:", report.hidden);
if (report.drawn.lines !== report.lines) failed = true;
console.log("page errors, without the mirror:", plain.errors.length ? plain.errors.join(" | ") : "none");
console.log("page errors, with it:", drawn.errors.length ? drawn.errors.join(" | ") : "none");
if (report.off.length || report.missing.length || domOff.length || drawn.errors.length || report.hidden !== "0") failed = true;
await browser.close();
process.exit(failed ? 1 : 0);
