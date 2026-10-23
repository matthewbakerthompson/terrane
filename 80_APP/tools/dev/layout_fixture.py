"""The app's own layout of a view, read back as a test fixture.

The Python drawing in `terrane.draw` is held equal to the app, and the app is
the spec: this script opens a view in a headless Chrome, lets the page lay
it out, and writes what Cytoscape ended up with -- every node's center and
size, every boundary's box, the sheet the layout was fitted to -- beside the
payload the page drew from. `tests/test_draw_packed.py` lays the same
payload out in Python and compares.

    python 80_APP/app/server.py --port 8031
    python 80_APP/tools/dev/layout_fixture.py --url http://127.0.0.1:8031 \
        application-landscape hosting-estate

With no views named, every view the Python layout covers is captured: the
five packed maps into `fixtures/layout/`, the nine dagre-ranked diagrams
into `fixtures/layered/`, the latter with the direction the app chose, the
axis it ranked each edge along and the pieces of every routed edge, for
`tests/test_draw_layered.py`, and the eleven tile maps into
`fixtures/tiles/`. A tile map has no Cytoscape to read: its geometry is
the page's own, so the fixture holds every band, card, grid and tile as a
box relative to the host, with its class, its id, its text and the lines
the browser broke the text into, plus the host's width, for
`tests/test_draw_tiles.py`. The app's PNG of each lands in `out/` beside
the fixture, not committed, so the two pictures can be put side by side.

A fixture whose view is no longer in the estate -- one kept from a retired
view, or captured from a probe view that was deleted -- is taken again with
`--replay`: the page is handed the payload the fixture holds in place of
whatever `/api/graph` would answer, and the fixture is written back where it
was.

    python 80_APP/tools/dev/layout_fixture.py --url http://127.0.0.1:8031 --replay         50_ENGINE/tests/fixtures/organic/zz-flat-probe.json
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from chrome import Chrome  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
FIXTURES = REPO / "50_ENGINE" / "tests" / "fixtures" / "layout"
OUT = HERE / "out"

#: The maps the app packs rather than ranks: `kind: map` with edges.
PACKED = ["actor-channels", "application-landscape", "hosting-estate", "lifecycle-portfolio", "vendor-exposure"]
#: The diagrams the app ranks with dagre: laned, or past what `elkFits`
#: hands to ELK (thirty leaves, eight boundaries). Their fixtures carry the
#: routed edges too, and live in their own folder.
DAGRE = ["tiered-architecture", "product-architecture", "onboarding", "network-topology",
         "integration-architecture", "data-dissemination", "harvested-estate", "restricted-data-governance"]
#: `fixtures/layered/frameworks-landscape.json` is kept from a view retired
#: on 2026-10-20 (the frameworks are a grid now): a capture is its own
#: payload, so it still holds the Python layout equal to what the app drew.
LAYERED = REPO / "50_ENGINE" / "tests" / "fixtures" / "layered"
#: The maps with nothing connected, which the app draws as tiles: HTML in
#: a CSS grid, so their fixtures are the DOM's boxes, not Cytoscape's.
TILES = ["capability-map", "value-streams", "process-landscape", "data-landscape", "technology-stack",
         "framework-landscape"]
#: Kept from the views the one framework landscape replaced on 2026-10-20
#: (bian-, apqc-, cri-, dmbok-, itil-landscape, capability-domains): each
#: capture carries its own payload and still tests the tile layout.
TILE_FIXTURES = REPO / "50_ENGINE" / "tests" / "fixtures" / "tiles"
#: The view that asks for a wheel (`layout: concentric`): the app's own
#: `__aacLayout` says it was neither layered nor ELK, and `terrane.draw.wheel`
#: is held equal to it.
WHEEL_FIXTURES = REPO / "50_ENGINE" / "tests" / "fixtures" / "wheel"
#: A flat drawing past what ELK takes that dagre ranked into a ribbon, which
#: the app then laid out organically; `terrane.draw.organic` runs the same cose
#: through the browser and is held equal to it.
ORGANIC_FIXTURES = REPO / "50_ENGINE" / "tests" / "fixtures" / "organic"

INIT = 'localStorage.setItem("aac.rail.shut", "1"); localStorage.setItem("aac.insp.shut", "0");'

#: What the page knows once `drawGraph` has finished: the drawing's geometry
#: in model coordinates, the sheet it was fitted to, and the shapes Cytoscape
#: draws, so the painter can be checked against them too.
GEOMETRY = r"""
(function () {
  var host = document.getElementById("cy");
  var cy = host._cyreg.cy;
  var rect = host.getBoundingClientRect();
  var nodes = {};
  cy.nodes().forEach(function (n) {
    var p = n.position();
    var bb = n.boundingBox({ includeLabels: false, includeOverlays: false });
    nodes[n.id()] = {
      x: p.x, y: p.y, w: n.width(), h: n.height(), ow: n.outerWidth(), oh: n.outerHeight(),
      bb: [bb.x1, bb.y1, bb.x2, bb.y2],
      group: !!n.data("isGroup"), parent: n.parent().length ? n.parent().id() : null,
      degree: n.data("degree") || 0,
      corner: n.data("icon") ? "icon" : n.data("glyph") ? "glyph" : n.data("ticon") ? "ticon" : "",
    };
  });
  var edges = cy.edges().map(function (e) {
    var s = e.sourceEndpoint(), t = e.targetEndpoint(), m = e.midpoint();
    // The pieces as drawn: the router's segment points as it wrote them
    // and every point of the path Cytoscape laid down from them.
    var rs = e._private.rscratch || {};
    return { id: e.id(), s: [s.x, s.y], t: [t.x, t.y], mid: [m.x, m.y],
             shown: e.data("shown") || "", lx: e.data("lx") || 0, ly: e.data("ly") || 0,
             rot: e.hasClass("rot"), free: e.hasClass("free"),
             segw: e.data("segw") || "", segd: e.data("segd") || "",
             type: rs.edgeType || "", pts: (rs.allpts || []).slice() };
  });
  var all = cy.elements().boundingBox();
  var shapes = {};
  var ns = cy.renderer().nodeShapes;
  Object.keys(ns).forEach(function (k) { if (ns[k].points) shapes[k] = ns[k].points; });
  var radius = {};
  [[64, 36], [132, 52], [200, 100], [20, 20], [100, 16]].forEach(function (s) {
    radius[s.join("x")] = cy.renderer().getRoundRectangleRadius
      ? cy.renderer().getRoundRectangleRadius(s[0], s[1]) : null;
  });
  var tiles = !document.getElementById("tiles").hidden;
  return { container: { w: rect.width, h: rect.height }, zoom: cy.zoom(), tiles: tiles,
           labelsShown: (document.getElementById("btnLabels") || {}).getAttribute
             ? document.getElementById("btnLabels").getAttribute("aria-pressed") : null,
           // What the layout decided (`drawGraph` leaves it on the window):
           // the direction drawn, whether ELK or dagre drew it, the axis each
           // edge was ranked along.
           layout: window.__aacLayout || null,
           // The three pieces the fallback would draw, which the grid
           // router's drawing does not show.
           pieces: window.__aacLayout && window.__aacLayout.pieces && window.__aacLayout.layered
             && !window.__aacLayout.elk ? window.__aacLayout.pieces() : null,
           bounds: [all.x1, all.y1, all.x2, all.y2],
           nodes: nodes, edges: edges, shapes: shapes, roundRect: radius };
})()
"""

#: What the page knows once `drawTiles` has finished: every box of the tile
#: map as the browser laid it out, relative to the host's own top-left, with
#: the class that styled it, the id it stands for, its text and the lines
#: the browser broke that text into. The host's width is the one number the
#: layout depends on; its padding and the root font size are read back so
#: the fixture says which stylesheet it was laid out under.
TILE_GEOMETRY = r"""
(function () {
  var host = document.getElementById("tiles");
  var rect = host.getBoundingClientRect();
  var hs = getComputedStyle(host);
  function box(e) {
    var r = e.getBoundingClientRect();
    return [r.left - rect.left + host.scrollLeft, r.top - rect.top + host.scrollTop, r.width, r.height];
  }
  // The text as the browser broke it: one string per line box, found by
  // where each character's own rectangle sits.
  function lines(e) {
    var node = e.firstChild;
    if (!node || node.nodeType !== 3) return [e.textContent];
    var text = node.textContent, out = [], tops = [], range = document.createRange();
    for (var i = 0; i < text.length; i += 1) {
      range.setStart(node, i);
      range.setEnd(node, i + 1);
      var rs = range.getClientRects();
      if (!rs.length) { if (out.length) out[out.length - 1] += text[i]; continue; }
      var top = Math.round(rs[0].top * 4) / 4;
      if (!tops.length || Math.abs(top - tops[tops.length - 1]) > 1) { tops.push(top); out.push(""); }
      out[out.length - 1] += text[i];
    }
    return out.map(function (s) { return s.replace(/\s+$/, ""); });
  }
  var items = [];
  var wanted = ".tband, .tband-h, .tband-name, .tband-gloss, .tband-n, .tband-body, .tcards, .tcard, .tcard-h, "
    + ".tcard-h > span:first-child, .tcard-n, .tgrid, .tile, .tile-name, .tile-sub";
  host.querySelectorAll(wanted).forEach(function (e) {
    var s = getComputedStyle(e);
    var cls = e.className;
    if (e.parentElement && e.parentElement.classList.contains("tcard-h") && !cls) cls = "tcard-name";
    var textual = /tband-name|tband-gloss|tband-n|tcard-name|tcard-n|tile-name|tile-sub/.test(cls);
    items.push({
      cls: cls, id: e.getAttribute("data-id") || "", box: box(e),
      text: textual ? e.textContent : "",
      lines: /tband-name|tband-gloss|tcard-name|tile-name/.test(cls) ? lines(e) : undefined,
      border: [s.borderTopWidth, s.borderRightWidth, s.borderBottomWidth, s.borderLeftWidth].map(parseFloat),
      font: textual ? s.fontWeight + " " + s.fontSize + "/" + s.lineHeight + " " + s.fontFamily.split(",")[0] : "",
    });
  });
  return {
    host: { w: rect.width, h: rect.height, clientWidth: host.clientWidth, clientHeight: host.clientHeight,
            scrollHeight: host.scrollHeight,
            padding: [hs.paddingTop, hs.paddingRight, hs.paddingBottom, hs.paddingLeft].map(parseFloat) },
    rootFontSize: parseFloat(getComputedStyle(document.documentElement).fontSize),
    fonts: document.fonts.status,
    geist: document.fonts.check("12px Geist"),
    items: items,
  };
})()
"""


def fetch_json(url: str):
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


#: What the page is given in place of the server's answer, for `--replay`:
#: every `/api/graph` request answered with the fixture's own payload.
REPLAY = r"""
window.__aacReplay = %s;
(function () {
  var fetched = window.fetch;
  window.fetch = function (url) {
    if (typeof url === "string" && url.indexOf("/api/graph?") === 0) {
      return Promise.resolve(new Response(JSON.stringify(window.__aacReplay),
        { status: 200, headers: { "Content-Type": "application/json" } }));
    }
    return fetched.apply(this, arguments);
  };
})();
"""


def capture(browser: Chrome, base: str, view: str, hash_: str, png: bool, payload: dict = None) -> dict:
    query = dict(urllib.parse.parse_qsl(hash_))
    init = INIT
    if payload is None:
        payload = fetch_json(base + "/api/graph?" + urllib.parse.urlencode(query))
    else:
        init += REPLAY % json.dumps(payload)
    page = browser.page(base + "/#" + hash_, init_script=init)
    # The readout says 100% in the HTML before any drawing exists, so the
    # wait is for the drawing itself: Cytoscape registered on the sheet with
    # nodes in it and the laying-out class gone, or the tile map shown with
    # the faces it is set in loaded, since a tile wraps its name in Geist
    # and would wrap it elsewhere in the fallback face.
    page.wait_for(
        '(function () { var h = document.getElementById("cy"); var r = h && h._cyreg && h._cyreg.cy;'
        ' var tiles = document.getElementById("tiles");'
        ' if (tiles && !tiles.hidden && tiles.children.length) return document.fonts.status === "loaded";'
        ' return !!(r && r.nodes().length && !h.classList.contains("is-laying")'
        ' && /\\d+%/.test((document.getElementById("zoomPct") || {}).textContent || "")); })()',
        timeout=60, settle=0.8)
    tiles = page.evaluate('!document.getElementById("tiles").hidden')
    geometry = page.evaluate(TILE_GEOMETRY if tiles else GEOMETRY)
    if tiles:
        geometry["tiles"] = True
        if not geometry.get("geist"):
            raise SystemExit("%s was laid out before Geist loaded; the fixture would hold the fallback face" % view)
    if png:
        OUT.mkdir(parents=True, exist_ok=True)
        data_url = page.evaluate("window.__aacDrawingPng(2)", await_promise=True)
        (OUT / (view + ".app.png")).write_bytes(base64.b64decode(data_url.split(",", 1)[1]))
    page.close()
    return {
        "view": view,
        "hash": hash_,
        "viewport": [browser.width, browser.height],
        "payload": payload,
        **geometry,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--url", default="http://127.0.0.1:8020")
    parser.add_argument("--out", default="", help="one folder for every fixture; by default the packed maps go to "
                        "fixtures/layout, the layered diagrams to fixtures/layered and the tile maps to "
                        "fixtures/tiles")
    parser.add_argument("--no-png", action="store_true", help="skip the app's own PNG of each view")
    parser.add_argument("--replay", action="store_true", help="the arguments are fixture files: take each again "
                        "from the payload it holds and write it back in place")
    parser.add_argument("views", nargs="*", help="view ids, or name=hash for a subject")
    args = parser.parse_args(argv)
    wanted = args.views or PACKED + DAGRE + TILES
    with Chrome() as browser:
        for item in wanted:
            kept = None
            if args.replay:
                kept = Path(item)
                held = json.loads(kept.read_text(encoding="utf-8"))
                name, hash_ = held["view"], held["hash"]
                fixture = capture(browser, args.url.rstrip("/"), name, hash_, not args.no_png, held["payload"])
            else:
                name, _, hash_ = item.partition("=")
                if not hash_:
                    hash_ = "view=" + name
                fixture = capture(browser, args.url.rstrip("/"), name, hash_, not args.no_png)
            layout = fixture.get("layout") or {}
            out = (kept.parent if kept else Path(args.out) if args.out else FIXTURES if name in PACKED else
                   TILE_FIXTURES if fixture.get("tiles") else
                   (WHEEL_FIXTURES if str(fixture["payload"].get("layout") or "").lower() == "concentric"
                    else ORGANIC_FIXTURES) if layout.get("layered") is False and not layout.get("elk")
                   else LAYERED)
            out.mkdir(parents=True, exist_ok=True)
            path = out / (name + ".json")
            # LF on every platform: a fixture is compared by git as well as read.
            with path.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(fixture, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
            if fixture.get("tiles"):
                tiles = sum(1 for i in fixture["items"] if i["cls"].split()[0] == "tile")
                bands = sum(1 for i in fixture["items"] if i["cls"].split()[0] == "tband")
                cards = sum(1 for i in fixture["items"] if i["cls"].split()[0] == "tcard")
                print("%-24s %3d tiles %3d bands %3d cards  host %dx%d  -> %s" % (
                    name, tiles, bands, cards, fixture["host"]["clientWidth"], fixture["host"]["scrollHeight"],
                    path.resolve().relative_to(REPO)))
                continue
            leaves = sum(1 for n in fixture["nodes"].values() if not n["group"])
            groups = len(fixture["nodes"]) - leaves
            print("%-24s %3d nodes %3d boundaries  sheet %dx%d  zoom %.2f  -> %s" % (
                name, leaves, groups, fixture["container"]["w"], fixture["container"]["h"],
                fixture["zoom"], path.resolve().relative_to(REPO)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
