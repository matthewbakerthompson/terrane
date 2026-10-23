// The shape of each drawing against the sheet -- width, height, ratio and
// the zoom it fits at -- so a layout change is judged across the estate
// rather than on the one view it was made for:
//
//   node 80_APP/tools/dev/ratio_probe.mjs                 # a default set of views
//   node 80_APP/tools/dev/ratio_probe.mjs network-topology "onboarding&p_product=PRD-REWARDS"
//
// Run it before and after the change and compare. A report or a timeline
// has no drawing and says so. The app must be listening; --url changes where.
import { launch, openView, settled } from "../capture.mjs";

const DEFAULT = [
  "network-topology", "onboarding&p_product=PRD-INSTALLMENT-LENDING", "product-architecture&p_product=PRD-CARD-SERVICING",
  "product-architecture&p_product=PRD-IDV", "integration-architecture", "system-context", "dr-topology",
  "hosting-estate", "application-landscape", "system-governance&p_system=SYS-AUTH-SWITCH", "domain-servicing",
  "tiered-architecture", "technology-stack", "framework-landscape&p_framework=FW-BIAN", "capability-map",
];
let url = "http://127.0.0.1:8020";
const views = [];
for (let i = 2; i < process.argv.length; i += 1) {
  if (process.argv[i] === "--url") { url = process.argv[++i]; continue; }
  views.push(process.argv[i]);
}
const wanted = views.length ? views : DEFAULT;

const browser = await launch();
try {
  for (const v of wanted) {
    const page = await openView(browser, url, "view=" + v);
    try {
      await settled(page);
    } catch (e) {
      console.log(v.padEnd(52), "no drawing settled");
      await page.close();
      continue;
    }
    const facts = await page.evaluate(() => {
      const reg = document.getElementById("cy") && document.getElementById("cy")._cyreg;
      if (!reg || !reg.cy) return { noDrawing: true };
      const cy = reg.cy;
      const bb = cy.elements().boundingBox({ includeLabels: false });
      const box = cy.container().getBoundingClientRect();
      const fit = Math.min(box.width / Math.max(bb.w, 1), box.height / Math.max(bb.h, 1));
      return { w: Math.round(bb.w), h: Math.round(bb.h), ratio: (bb.w / Math.max(bb.h, 1)).toFixed(2), fit: fit.toFixed(2),
        zoom: (document.getElementById("zoomPct") || {}).textContent || "" };
    });
    console.log(v.padEnd(52), JSON.stringify(facts));
    await page.close();
  }
} finally {
  await browser.close();
}
