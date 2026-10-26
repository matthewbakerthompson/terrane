// The canvas's plainer gestures, walked with a real pointer on the canvas as
// Cytoscape takes them and as maxGraph takes them (canvas/engine.js), and
// compared: a press on a box selects it and the panel names it, a press on
// the sheet lets it go, hovering marks the box, the wheel zooms by what it
// always zoomed by, and dragging the sheet pans it by what the pointer moved:
// on maxGraph with the Hand tool, since there a drag across the bare sheet
// picks what it goes around (annotate_probe.mjs walks that).
// With maxGraph on, Cytoscape must hear none of it: its own "tapstart", which
// only a press on its canvas fires, is counted and must stay at nothing.
//
//   node 80_APP/tools/dev/gesture_probe.mjs http://127.0.0.1:8020 [view]
//
// The view defaults to lending-onboarding (arrange_probe.mjs makes it); it
// reads and writes nothing else. Exits 1 if the two canvases differ.
import { launch, settled } from "../capture.mjs";

const URL = process.argv[2];
const VIEW = process.argv[3] || "lending-onboarding";
if (!URL) {
  console.error("usage: node gesture_probe.mjs URL [view]");
  process.exit(2);
}
const pause = (ms) => new Promise((r) => setTimeout(r, ms));
const browser = await launch();

async function walk(engine) {
  const page = await browser.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.evaluateOnNewDocument((e) => {
    localStorage.setItem("aac.rail.shut", "1");
    localStorage.setItem("aac.insp.shut", "0");
    localStorage.setItem("aac.tour", "taken");
    localStorage.setItem("aac.canvas.engine", e);
  }, engine);
  await page.goto(URL + "/#draw=" + VIEW, { waitUntil: "networkidle0", timeout: 60000 });
  await settled(page);
  if (engine === "maxgraph") await page.waitForSelector(".mg-surface.takes-pointer svg", { timeout: 30000 });
  await pause(500);
  await page.evaluate(() => {
    const cy = document.getElementById("cy")._cyreg.cy;
    window.__heard = 0;
    cy.on("tapstart", () => { window.__heard += 1; });
  });
  const cy = (fn, arg) => page.evaluate(fn, arg);
  // A leaf box clear of the toolbar, and a spot of empty sheet.
  // A leaf box clear of the toolbar, and a spot of bare sheet: inside the
  // canvas, under no box, line or label, and with nothing floating over it
  // (the overview, the chips and the tools all take the pointer).
  const pick = await cy(() => {
    const c = document.getElementById("cy")._cyreg.cy, r = c.container().getBoundingClientRect();
    const leaf = c.nodes().filter((n) => !n.isParent() && n.renderedPosition().y > 220).sort((a, b) => a.id() < b.id() ? -1 : 1)[0];
    const p = leaf.renderedPosition();
    let blank = null;
    for (let y = r.top + 60; y < r.bottom - 60 && !blank; y += 23) {
      for (let x = r.left + 60; x < r.right - 60 && !blank; x += 29) {
        const top = document.elementFromPoint(x, y);
        if (!top || !(top.closest("#cy") || top.closest(".mg-surface"))) continue;
        const m = { x: (x - r.left - c.pan().x) / c.zoom(), y: (y - r.top - c.pan().y) / c.zoom() };
        const over = c.elements().some((e) => { const b = e.boundingBox({ includeLabels: true }); return m.x >= b.x1 - 30 && m.x <= b.x2 + 30 && m.y >= b.y1 - 30 && m.y <= b.y2 + 30 && !e.isParent(); });
        if (!over) blank = { x, y };
      }
    }
    return { id: leaf.id(), label: leaf.data("label"), x: r.left + p.x, y: r.top + p.y, blank };
  });
  if (!pick.blank) throw new Error("no bare sheet found on " + VIEW);
  await cy((id) => {
    const n = document.getElementById("cy")._cyreg.cy.getElementById(id);
    window.__over = 0; window.__out = 0;
    n.on("mouseover", () => { window.__over += 1; });
    n.on("mouseout", () => { window.__out += 1; });
  }, pick.id);
  const out = { engine };
  await page.mouse.click(pick.x, pick.y);
  await pause(700);
  out.selected = await cy(() => (document.querySelector("#cvDetails .cv-h") || {}).textContent || "");
  out.selectedIsBox = out.selected.indexOf(pick.label) !== -1;
  await page.mouse.click(pick.blank.x, pick.blank.y);
  await pause(300);
  out.released = await cy(() => (document.querySelector("#cvDetails .cv-h") || {}).textContent || "");
  await page.mouse.move(pick.x, pick.y, { steps: 4 });
  await pause(150);
  out.hovered = await cy(() => window.__over > 0);
  await page.mouse.move(pick.blank.x, pick.blank.y, { steps: 4 });
  await pause(150);
  out.unhovered = await cy(() => window.__out > 0);
  const z0 = await cy(() => document.getElementById("cy")._cyreg.cy.zoom());
  await page.mouse.move(pick.blank.x, pick.blank.y);
  for (let i = 0; i < 3; i += 1) { await page.mouse.wheel({ deltaY: -100 }); await pause(60); }
  await pause(250);
  out.zoomedBy = Math.round(((await cy(() => document.getElementById("cy")._cyreg.cy.zoom())) / z0) * 1000) / 1000;
  const p0 = await cy(() => document.getElementById("cy")._cyreg.cy.pan());
  if (engine === "maxgraph") await page.click("#cvPan");
  await page.mouse.move(pick.blank.x, pick.blank.y);
  await page.mouse.down();
  for (let i = 1; i <= 10; i += 1) await page.mouse.move(pick.blank.x - 6 * i, pick.blank.y - 3 * i);
  await page.mouse.up();
  await pause(200);
  const p1 = await cy(() => document.getElementById("cy")._cyreg.cy.pan());
  out.pannedBy = [Math.round(p1.x - p0.x), Math.round(p1.y - p0.y)];
  out.cytoscapeHeard = await cy(() => window.__heard);
  out.errors = errors;
  await page.close();
  return out;
}

const plain = await walk("cytoscape");
const drawn = await walk("maxgraph");
for (const r of [plain, drawn]) console.log(JSON.stringify(r));
const same = (k) => JSON.stringify(plain[k]) === JSON.stringify(drawn[k]);
const checks = {
  "a press selects the box": drawn.selectedIsBox && plain.selectedIsBox,
  "a press on the sheet lets it go": same("released"),
  "hover marks the box, and lets it go": drawn.hovered && drawn.unhovered && same("hovered"),
  "the wheel zooms the same": same("zoomedBy"),
  "dragging the sheet pans the same": same("pannedBy"),
  "Cytoscape hears no press with maxGraph on": drawn.cytoscapeHeard === 0 && plain.cytoscapeHeard > 0,
  "no page errors": !plain.errors.length && !drawn.errors.length,
};
let ok = true;
for (const [k, v] of Object.entries(checks)) { console.log((v ? "ok   " : "FAIL ") + k); if (!v) ok = false; }
await browser.close();
process.exit(ok ? 0 : 1);
