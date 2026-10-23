// Drag a box on a drawing the way a person would -- mouse down on it, a
// few moves, mouse up -- onto another box or into a boundary, and capture
// what the drop opened, and the moment before it, held over the target:
//
//   node 80_APP/tools/dev/drag_probe.mjs out/ http://127.0.0.1:8020 \
//        regroup="view=integration-architecture|SYS-AUTH-SWITCH>grp::Application" \
//        connect="view=integration-architecture|SYS-AUTH-SWITCH>SYS-CORE-LEDGER"
//
// Each argument is name=hash|BOX>TARGET[|steps]. TARGET is a box's
// id, dropped on its middle, or a boundary's (`grp::` and its path joined by
// `::`), dropped on a spot inside it clear of every box and of the
// boundaries inside it -- its middle is often a box, which would be a
// connect. Steps, comma-separated: `layout=packed` picks a layout first (a
// map drawn as tiles has no drag), `confirm` presses the chooser's last
// button (Move it) and waits for the drawing, and `undo` then presses the
// toast's Undo. A PNG of the window
// per step (`-held`, the drop, `-moved`) lands in the folder given first,
// and a line per step says what the chooser said and where the box is
// drawn. Confirm writes to the model the app is serving; undo puts it back.
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { launch } from "../capture.mjs";

const OUT = process.argv[2];
const url = process.argv[3];
const shots = process.argv.slice(4).map((a) => { const i = a.indexOf("="); return [a.slice(0, i), a.slice(i + 1)]; });
if (!OUT || !url || !shots.length) {
  console.error("usage: node drag_probe.mjs OUT URL name=hash|BOX>TARGET[|layout=X,confirm,undo] ...");
  process.exit(2);
}
await mkdir(OUT, { recursive: true });
const pause = (ms) => new Promise((r) => setTimeout(r, ms));

// Where on the screen to let go: a box's middle, or the emptiest-looking
// spot in a boundary, found on a grid in the drawing's own coordinates.
function dropPoint(target) {
  const cy = document.getElementById("cy")._cyreg.cy;
  const sheet = document.getElementById("cy").getBoundingClientRect();
  const n = cy.getElementById(target);
  if (!n.length) return null;
  const toScreen = (p) => ({
    x: sheet.left + p.x * cy.zoom() + cy.pan().x,
    y: sheet.top + p.y * cy.zoom() + cy.pan().y,
  });
  if (!n.data("isGroup")) return window.__aacNodeAt(target);
  const bb = n.boundingBox({ includeLabels: false });
  const inner = n.descendants().map((d) => d.boundingBox({ includeLabels: false }));
  // How far a point is from the nearest box or boundary inside, 0 within one.
  const gap = (x, y) => Math.min(...inner.map((b) => Math.max(b.x1 - x, x - b.x2, b.y1 - y, y - b.y2, 0)), 1e9);
  let best = null;
  for (let i = 1; i < 32; i += 1) {
    for (let j = 1; j < 32; j += 1) {
      const x = bb.x1 + (bb.w * i) / 32, y = bb.y1 + 30 + ((bb.h - 30) * j) / 32;
      const s = toScreen({ x, y });
      if (s.x < sheet.left + 4 || s.x > sheet.right - 4 || s.y < sheet.top + 4 || s.y > sheet.bottom - 4) continue;
      // Clear of everything inside and of the boundary's own edges, by as
      // much as the boundary allows, so the drop plainly means the boundary.
      const room = Math.min(gap(x, y), x - bb.x1, bb.x2 - x, y - bb.y1, bb.y2 - y);
      if (room > 0 && (!best || room > best.room)) best = { room, ...s };
    }
  }
  return best && { x: best.x, y: best.y };
}

function drawnIn(id) {
  const cy = document.getElementById("cy")._cyreg.cy;
  const n = cy.getElementById(id);
  return n.length ? (n.parent().length ? n.parent().id() : "(no boundary)") : "(not drawn)";
}

const browser = await launch();
try {
  for (const [name, spec] of shots) {
    const [hash, move, after = ""] = spec.split("|");
    const [box, target] = move.split(">");
    const steps = after.split(",").filter(Boolean);
    const page = await browser.newPage();
    await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1 });
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
    // Past the first visit: the coach strip would push the drawing down.
    await page.evaluateOnNewDocument(() => localStorage.setItem("aac.coach", "done"));
    await page.goto(url + "/#" + hash, { waitUntil: "networkidle0" });
    await page.waitForFunction(() => /\d+%/.test((document.getElementById("zoomPct") || {}).textContent || ""), { timeout: 30000 });
    await pause(1200);
    const layout = steps.find((s) => s.startsWith("layout="));
    if (layout) {
      await page.evaluate((v) => {
        const pick = document.getElementById("layoutPicker");
        pick.value = v;
        pick.dispatchEvent(new Event("change", { bubbles: true }));
      }, layout.slice(7));
      await page.waitForFunction(() => document.getElementById("cy")._cyreg, { timeout: 30000 });
      await pause(2500);
    }

    const from = await page.evaluate((id) => window.__aacNodeAt(id), box);
    const to = await page.evaluate(dropPoint, target);
    if (!from || !to) {
      console.log(name, "cannot find", !from ? box : target, "on the drawing");
      await page.close();
      continue;
    }
    const before = await page.evaluate(drawnIn, box);
    await page.mouse.move(from.x, from.y);
    await page.mouse.down();
    for (let i = 1; i <= 14; i += 1) {
      await page.mouse.move(from.x + ((to.x - from.x) * i) / 14, from.y + ((to.y - from.y) * i) / 14);
      await pause(16);
    }
    // Held over the target, so the highlight it would land in shows.
    await pause(150);
    await writeFile(resolve(OUT, name + "-held.png"), await page.screenshot({ type: "png" }));
    await page.mouse.up();
    const opened = await page.waitForSelector("#ctxMenu", { timeout: 6000 }).then(() => true, () => false);
    await pause(400);
    const said = opened ? await page.$eval("#ctxMenu", (m) => m.innerText.replace(/\s*\n\s*/g, " / ")) : "(nothing opened)";
    await writeFile(resolve(OUT, name + ".png"), await page.screenshot({ type: "png" }));
    console.log(name, "in", before, "->", said);

    if (opened && steps.includes("confirm")) {
      await page.evaluate(() => { const b = [...document.querySelectorAll("#ctxMenu .connect-acts button")].pop(); b.click(); });
      await page.waitForSelector(".toast.ok", { timeout: 10000 });
      await pause(2500);
      const toast = await page.$eval(".toast.ok", (t) => t.innerText.replace(/\s*\n\s*/g, " / "));
      console.log(name, "moved:", toast, "| now in", await page.evaluate(drawnIn, box));
      await writeFile(resolve(OUT, name + "-moved.png"), await page.screenshot({ type: "png" }));
      if (steps.includes("undo")) {
        await page.click(".toast.ok .toast-act");
        await page.waitForFunction(() => [...document.querySelectorAll(".toast.ok .t")].some((t) => t.textContent === "Undone"), { timeout: 10000 });
        await pause(2500);
        console.log(name, "undone | now in", await page.evaluate(drawnIn, box));
      }
    }
    console.log(name, errors.length ? "ERRORS: " + errors.join(" | ") : "no page errors");
    await page.close();
  }
} finally {
  await browser.close();
}
