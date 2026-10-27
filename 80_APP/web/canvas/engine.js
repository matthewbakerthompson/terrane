/* The canvas drawn and handled by maxGraph: every call to maxGraph is in
 * this file.
 *
 * The canvas has a model of its own here (M2 of the canvas plan, HANDOVER
 * section 8): one maxGraph model that lives as long as the canvas is open,
 * in five layers. Two are the estate's, what Cytoscape laid out and routed:
 * its boundaries, and over them its boxes and lines -- each at its
 * geometry, in its computed colors and shape, with its name, technology
 * line and mark, each line along the points it was routed by -- kept in
 * step with Cytoscape cell by cell as it renders, never rebuilt for a
 * frame. Cytoscape is the layout and the router, its own drawing invisible
 * beneath. The diagram's own, drawn with the tools and saved under
 * `annotations:` in the diagram's file (canvas.js), goes around them: a
 * frame on the bare sheet, or around boundaries, in the layer under the
 * estate; a frame inside a boundary among the boundaries, just above the
 * innermost that holds it and under the ones inside it (restack); and
 * every other shape, note, text and line in the layer over everything.
 * Cytoscape never sees those.
 *
 * Records and boundaries keep the pointer they had (takePointer, below):
 * each gesture becomes the Cytoscape event the canvas has always handled,
 * so placing, moving into a boundary and connecting are what they were. The
 * diagram's own shapes are maxGraph's to select, move, resize and drop into
 * a frame, with its handles and its guides, and a drawing tool draws them.
 *
 * The probes that hold it: `80_APP/tools/dev/mirror_probe.mjs` (every box
 * where Cytoscape put it), `gesture_probe.mjs` (the plainer gestures, the
 * same as on Cytoscape), `annotate_probe.mjs` (every tool, saved and drawn
 * again), `export_probe.mjs` (the PNG export and the overview hold what the
 * sheet does), `names_probe.mjs` (every name where Cytoscape set it), with
 * `arrange_probe.mjs`, `drag_probe.mjs` and `drop_probe.mjs`
 * giving their output on it. On unless the old canvas is asked for:
 * `?canvas=cytoscape` in the address, or `localStorage["aac.canvas.engine"]
 * = "cytoscape"`; if the bundle fails to load, the canvas is the old one
 * and the diagram's own shapes wait in its file. The bundle
 * (`vendor/maxgraph.min.js`, 618 KB) is loaded the first time a canvas
 * draws, never with the page.
 *
 * maxGraph is pre-1.0 and pinned (vendor/README.md). Its shapes are ES
 * classes, which a plain function cannot extend, so the shapes below are
 * written as classes; the rest keeps the app's ES5.
 */

(function (app) {
  "use strict";

  var Canvas = app.Canvas;
  var KEY = "aac.canvas.engine";
  var FACE = "Geist, system-ui, sans-serif";

  // On unless the old canvas is asked for by name; a browser that cannot
  // read the address or its storage gets the canvas that draws, which is
  // this one.
  function enabled() {
    try {
      var asked = new URLSearchParams(window.location.search).get("canvas");
      if (asked) return asked !== "cytoscape";
      return window.localStorage.getItem(KEY) !== "cytoscape";
    } catch (e) {
      return true;
    }
  }

  // ---- loading the bundle once, on first use
  var loading = null;
  function load() {
    if (window.maxgraph) return Promise.resolve(window.maxgraph);
    if (loading) return loading;
    loading = new Promise(function (resolve, reject) {
      var css = document.createElement("link");
      css.rel = "stylesheet";
      css.href = "vendor/maxgraph.css";
      document.head.appendChild(css);
      var js = document.createElement("script");
      js.src = "vendor/maxgraph.min.js";
      js.onload = function () { registerShapes(window.maxgraph); resolve(window.maxgraph); };
      js.onerror = function () { loading = null; reject(new Error("vendor/maxgraph.min.js did not load")); };
      document.head.appendChild(js);
    });
    return loading;
  }

  /* Cytoscape's polygons, as its own source gives them: points in -1..1 of
   * the box. Drawn from the same numbers so a rhomboid is the same slant and
   * a hexagon the same width of point; maxGraph's own hexagon is another. */
  var POLYGONS = {
    rhomboid: [-1, -1, 0.333, -1, 1, 1, -0.333, 1],
    hexagon: [-1, 0, -0.5, -1, 0.5, -1, 1, 0, 0.5, 1, -0.5, 1],
    octagon: [-1, -0.4142, -0.4142, -1, 0.4142, -1, 1, -0.4142, 1, 0.4142, 0.4142, 1, -0.4142, 1, -1, 0.4142],
    "round-tag": [-1, -1, 0.5, -1, 1, 0, 0.5, 1, -1, 1],
    tag: [-1, -1, 0.5, -1, 1, 0, 0.5, 1, -1, 1],
    diamond: [0, -1, 1, 0, 0, 1, -1, 0],
    triangle: [-1, 1, 0, -1, 1, 1],
  };

  /* The diagram's own shapes, in the order the Shapes menu lists them, each
   * a path in fractions of its box: M and L a point, Q one control and a
   * point, C two and a point, Z the close. The engine's picture draws the
   * same numbers (terrane/draw/annotations.py), so a cloud drawn here is the
   * cloud in every export. A rounded box is a rectangle with corners, not a
   * path, in both. */
  var OWN_SHAPES = [
    ["rectangle", "Rectangle"], ["rounded", "Rounded box"], ["ellipse", "Ellipse"], ["diamond", "Diamond"],
    ["hexagon", "Hexagon"], ["cylinder", "Data store"], ["cloud", "Cloud"], ["document", "Document"],
    ["person", "Person"], ["callout", "Callout"],
  ];
  //: How a line of its own runs, as the Line menu offers it.
  var OWN_ROUTES = [["straight", "Straight"], ["square", "Square"], ["curved", "Curved"]];
  var K = 0.27614;
  var OWN_PATHS = {
    rectangle: [["M", 0, 0], ["L", 1, 0], ["L", 1, 1], ["L", 0, 1], ["Z"]],
    ellipse: [["M", 0.5, 0], ["C", 0.5 + K, 0, 1, 0.5 - K, 1, 0.5], ["C", 1, 0.5 + K, 0.5 + K, 1, 0.5, 1],
      ["C", 0.5 - K, 1, 0, 0.5 + K, 0, 0.5], ["C", 0, 0.5 - K, 0.5 - K, 0, 0.5, 0], ["Z"]],
    diamond: [["M", 0.5, 0], ["L", 1, 0.5], ["L", 0.5, 1], ["L", 0, 0.5], ["Z"]],
    hexagon: [["M", 0, 0.5], ["L", 0.25, 0], ["L", 0.75, 0], ["L", 1, 0.5], ["L", 0.75, 1], ["L", 0.25, 1], ["Z"]],
    // The cap's front edge drawn again after the body, so the top reads as
    // a lid and not as a pill; right to left, wound as the body is, or the
    // lid is a hole in the fill and the shadow shows through it.
    cylinder: [["M", 0, 0.12], ["C", 0, -0.04, 1, -0.04, 1, 0.12], ["L", 1, 0.88], ["C", 1, 1.04, 0, 1.04, 0, 0.88],
      ["Z"], ["M", 1, 0.12], ["C", 1, 0.28, 0, 0.28, 0, 0.12]],
    cloud: [["M", 0.25, 0.25], ["C", 0.05, 0.25, 0, 0.5, 0.16, 0.55], ["C", 0, 0.66, 0.18, 0.9, 0.31, 0.8],
      ["C", 0.4, 1, 0.7, 1, 0.8, 0.8], ["C", 1, 0.8, 1, 0.6, 0.875, 0.5], ["C", 1, 0.3, 0.8, 0.1, 0.625, 0.2],
      ["C", 0.5, 0.05, 0.3, 0.05, 0.25, 0.25], ["Z"]],
    document: [["M", 0, 0], ["L", 1, 0], ["L", 1, 0.85], ["Q", 0.75, 0.7, 0.5, 0.85], ["Q", 0.25, 1, 0, 0.85], ["Z"]],
    person: [["M", 0.5, 0.02], ["C", 0.6, 0.02, 0.68, 0.1, 0.68, 0.2], ["C", 0.68, 0.3, 0.6, 0.38, 0.5, 0.38],
      ["C", 0.4, 0.38, 0.32, 0.3, 0.32, 0.2], ["C", 0.32, 0.1, 0.4, 0.02, 0.5, 0.02], ["Z"],
      ["M", 0.12, 1], ["L", 0.12, 0.72], ["C", 0.12, 0.52, 0.3, 0.44, 0.5, 0.44], ["C", 0.7, 0.44, 0.88, 0.52, 0.88, 0.72],
      ["L", 0.88, 1], ["Z"]],
    callout: [["M", 0, 0], ["L", 1, 0], ["L", 1, 0.72], ["L", 0.42, 0.72], ["L", 0.22, 1], ["L", 0.26, 0.72],
      ["L", 0, 0.72], ["Z"]],
  };

  function runPath(c, prog, w, h) {
    prog.forEach(function (op) {
      if (op[0] === "M") c.moveTo(op[1] * w, op[2] * h);
      else if (op[0] === "L") c.lineTo(op[1] * w, op[2] * h);
      else if (op[0] === "Q") c.quadTo(op[1] * w, op[2] * h, op[3] * w, op[4] * h);
      else if (op[0] === "C") c.curveTo(op[1] * w, op[2] * h, op[3] * w, op[4] * h, op[5] * w, op[6] * h);
      else c.close();
    });
  }

  // The same path as SVG, for the Shapes menu's pictures.
  function pathData(name, w, h) {
    var prog = OWN_PATHS[name] || OWN_PATHS.rectangle;
    return prog.map(function (op) {
      if (op[0] === "Z") return "Z";
      var nums = op.slice(1).map(function (v, i) { return Math.round(v * (i % 2 ? h : w) * 10) / 10; });
      return op[0] + nums.join(" ");
    }).join(" ");
  }

  // The tile in the middle of a box, as tile_box in annotations.py.
  function tileBox(x, y, w, h) {
    var side = Math.min(w, h, TILE);
    return { x: x + (w - side) / 2, y: y + (h - side) / 2, side: side };
  }

  function registerShapes(mg) {
    // A shape as Icon tiles draw it: its glow, then the tile, the gradient
    // running from the style's fill at the top to its gradient at the foot.
    class Tile extends mg.ActorShape {
      paintVertexShape(c, x, y, w, h) {
        var t = tileBox(x, y, w, h), top = this.style.fillColor, foot = this.style.gradientColor;
        // A shape that carries a provider's mark has the mark for its tile.
        if (!top || top === "none") return;
        // Its corners and how much of it shows, as its look says (cornersOf).
        var r = Math.min(this.style.arcSize != null ? this.style.arcSize / 2 : TILE_ROUND, t.side / 2);
        var o = (this.style.fillOpacity != null ? this.style.fillOpacity : 100) / 100;
        c.setFillColor(foot);
        c.setFillAlpha(0.25 * o);
        c.roundrect(t.x, t.y + TILE_GLOW, t.side, t.side, r, r);
        c.fill();
        c.setFillAlpha(o);
        c.setGradient(top, foot, t.x, t.y, t.side, t.side, "south", 1, 1);
        c.roundrect(t.x, t.y, t.side, t.side, r, r);
        c.fill();
      }
    }
    mg.ShapeRegistry.add("own-tile", Tile);
    // A line joined to a tile ends on the tile, not on the box round it.
    mg.PerimeterRegistry.add("tilePerimeter", function (bounds, vertex, next, orthogonal) {
      var k = vertex && vertex.view ? vertex.view.scale : 1;
      var side = Math.min(bounds.width, bounds.height, TILE * k);
      var square = new mg.Rectangle(bounds.x + (bounds.width - side) / 2, bounds.y + (bounds.height - side) / 2, side, side);
      return mg.Perimeter.RectanglePerimeter(square, vertex, next, orthogonal);
    });
    // The hard shadow under a shape or a note of the diagram's own, as the
    // app's pictures cast one: ink, unblurred, down and right. Nothing else
    // on the canvas asks for a shadow, so the defaults are its alone.
    Object.assign(mg.StyleDefaultsConfig, { shadowColor: INK, shadowOffsetX: SHADOW, shadowOffsetY: SHADOW,
      shadowOpacity: 1 });
    Object.keys(POLYGONS).forEach(function (name) {
      var pts = POLYGONS[name];
      class Polygon extends mg.ActorShape {
        redrawPath(c, x, y, w, h) {
          for (var i = 0; i < pts.length; i += 2) {
            var px = (pts[i] + 1) / 2 * w, py = (pts[i + 1] + 1) / 2 * h;
            if (i === 0) c.moveTo(px, py); else c.lineTo(px, py);
          }
          c.close();
        }
      }
      mg.ShapeRegistry.add("terrane-" + name, Polygon);
    });
    // A data store: a box whose top and bottom bulge, as Cytoscape draws one.
    class Barrel extends mg.ActorShape {
      redrawPath(c, x, y, w, h) {
        var b = Math.min(h * 0.15, 10);
        c.moveTo(0, b);
        c.quadTo(w / 2, -b, w, b);
        c.lineTo(w, h - b);
        c.quadTo(w / 2, h + b, 0, h - b);
        c.close();
      }
    }
    mg.ShapeRegistry.add("terrane-barrel", Barrel);
    // Every line on the canvas, the estate's and the diagram's own: maxGraph's
    // connector, hopping the straight lines drawn under it where it crosses
    // them (V14's line jumps), its corners rounded as maxGraph rounds them.
    class Hopping extends mg.ConnectorShape {
      paintLine(c, pts, rounded) {
        var hops = jumpsOn && this.state ? hopsOf(this, pts) : null;
        this.hopsDrawn = 0;
        if (!hops) { super.paintLine(c, pts, rounded); return; }
        this.hopsDrawn = hopPath(c, pts, rounded ? this.getBaseArcSize() : 0, hops, HOP * this.state.view.scale);
        c.stroke();
      }
    }
    Hopping.prototype.hopping = true;
    mg.ShapeRegistry.add("terrane-line", Hopping);
    Object.keys(OWN_PATHS).forEach(function (name) {
      var prog = OWN_PATHS[name];
      class Own extends mg.ActorShape {
        redrawPath(c, x, y, w, h) { runPath(c, prog, w, h); }
      }
      mg.ShapeRegistry.add("own-" + name, Own);
    });
    // A square line's turns, from its ends' boxes; a dangling end is the
    // point it was left at.
    // ... around the boxes in its way, routed in the drawing's units as the
    // picture routes it (detour), then put back on the screen.
    mg.EdgeStyleRegistry.add("terrane-square", function (state, source, target, points, result) {
      var pts = state.absolutePoints || [], view = state.view, k = view.scale, tr = view.translate;
      var box = function (st, at) {
        if (st) return { x1: st.x / k - tr.x, y1: st.y / k - tr.y, x2: (st.x + st.width) / k - tr.x, y2: (st.y + st.height) / k - tr.y };
        return at ? { x1: at.x / k - tr.x, y1: at.y / k - tr.y, x2: at.x / k - tr.x, y2: at.y / k - tr.y } : null;
      };
      // An end held at a side of its box leaves it square, a margin out
      // first, and is routed on from there as a point (`_stub`).
      var style = state.style || {};
      var stub = function (at, fx, fy) {
        if (!at || typeof fx !== "number" || typeof fy !== "number") return null;
        var side = fx === 1 ? 0 : fy === 1 ? 1 : fx === 0 ? 2 : fy === 0 ? 3 : -1, p = [at.x / k - tr.x, at.y / k - tr.y];
        if (side < 0) return { pin: p, out: null };
        var step = [[1, 0], [0, 1], [-1, 0], [0, -1]][side];
        return { pin: p, out: [p[0] + step[0] * PIN_OUT, p[1] + step[1] * PIN_OUT] };
      };
      var dot = function (p) { return { x1: p[0], y1: p[1], x2: p[0], y2: p[1] }; };
      var sa = source ? stub(pts[0], style.exitX, style.exitY) : null;
      var sb = target ? stub(pts[pts.length - 1], style.entryX, style.entryY) : null;
      var a = sa ? dot(sa.out || sa.pin) : box(source, pts[0]), b = sb ? dot(sb.out || sb.pin) : box(target, pts[pts.length - 1]);
      if (!a || !b) return;
      var plain = squareTurns(a, b).map(function (p) { return [p.x, p.y]; });
      var turns = detour([a.x1, a.y1, a.x2, a.y2], [b.x1, b.y1, b.x2, b.y2], walls(view), plain);
      if (sa && sa.out) turns.unshift(sa.out);
      if (sb && sb.out) turns.push(sb.out);
      turns.forEach(function (p) { result.push(new mg.Point((p[0] + tr.x) * k, (p[1] + tr.y) * k)); });
    }, { isOrthogonal: true });
  }

  /* ---- line jumps
   * Where a line crosses a straight one drawn under it -- earlier in the
   * page, so the estate's under the diagram's own and an older line under a
   * newer -- it hops it with a half circle, bulging up, or to the left on a
   * line that runs up and down. Not within two hops of either line's ends,
   * where it meets a box or carries an arrow, nor over a curved line. */
  //: A hop's radius, in the drawing's units.
  var HOP = 6;
  var jumpsOn = true;
  try { jumpsOn = localStorage.getItem("aac.canvas.jumps") !== "0"; } catch (e) { /* on, as V14 draws it */ }

  function cross(a, b, c, d) {
    var rx = b.x - a.x, ry = b.y - a.y, sx = d.x - c.x, sy = d.y - c.y, den = rx * sy - ry * sx;
    if (Math.abs(den) < 1e-9) return null;
    var t = ((c.x - a.x) * sy - (c.y - a.y) * sx) / den, u = ((c.x - a.x) * ry - (c.y - a.y) * rx) / den;
    if (t <= 0 || t >= 1 || u <= 0 || u >= 1) return null;
    return { t: t, x: a.x + t * rx, y: a.y + t * ry };
  }

  function near(p, q, d) { return !!q && Math.abs(p.x - q.x) < d && Math.abs(p.y - q.y) < d; }

  // For each stretch of the line, how far along it each hop is; null when
  // it hops nothing.
  function hopsOf(shape, pts) {
    var st = shape.state, node = shape.node, r = HOP * st.view.scale, others = [], out = [], any = false;
    if (!node || !node.parentNode || !pts || pts.length < 2) return null;
    st.view.states.forEach(function (o) {
      if (o === st || !o.cell || !o.cell.isEdge() || !o.shape || !o.shape.node || !o.absolutePoints) return;
      if ((o.style && o.style.curved) || o.shape.node.style.visibility === "hidden") return;
      // Drawn under this one: before it in the page.
      if (!(o.shape.node.compareDocumentPosition(node) & 4)) return;
      var q = o.absolutePoints.filter(Boolean);
      if (q.length > 1) others.push(q);
    });
    if (!others.length) return null;
    var first = pts[0], last = pts[pts.length - 1];
    for (var i = 0; i < pts.length - 1; i += 1) {
      var a = pts[i], b = pts[i + 1], len = Math.hypot(b.x - a.x, b.y - a.y), list = [];
      others.forEach(function (q) {
        for (var j = 0; j < q.length - 1; j += 1) {
          var hit = cross(a, b, q[j], q[j + 1]);
          if (!hit || near(hit, first, 2 * r) || near(hit, last, 2 * r) || near(hit, q[0], 2 * r)
            || near(hit, q[q.length - 1], 2 * r)) continue;
          list.push(hit.t * len);
        }
      });
      list.sort(function (x, y) { return x - y; });
      if (list.length) any = true;
      out.push(list);
    }
    return any ? out : null;
  }

  // The line drawn with its hops, each corner rounded by `arc` as maxGraph
  // rounds it; how many hops it drew.
  function hopPath(c, pts, arc, hops, r) {
    var n = pts.length, cut = [0], drawn = 0;
    for (var i = 1; i < n - 1; i += 1) {
      cut.push(Math.min(arc, Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y) / 2,
        Math.hypot(pts[i + 1].x - pts[i].x, pts[i + 1].y - pts[i].y) / 2));
    }
    cut.push(0);
    c.begin();
    c.moveTo(pts[0].x, pts[0].y);
    for (var s = 0; s < n - 1; s += 1) {
      var a = pts[s], b = pts[s + 1], len = Math.hypot(b.x - a.x, b.y - a.y);
      if (!len) continue;
      var ux = (b.x - a.x) / len, uy = (b.y - a.y) / len, to = len - cut[s + 1], last = cut[s];
      var sweep = Math.abs(ux) >= Math.abs(uy) ? (ux > 0 ? 1 : 0) : (uy > 0 ? 0 : 1);
      (hops[s] || []).forEach(function (d) {
        // Not into a corner, nor into the hop before it.
        if (d - r < last + 1 || d + r > to - 1) return;
        c.lineTo(a.x + ux * (d - r), a.y + uy * (d - r));
        c.arcTo(r, r, 0, 0, sweep, a.x + ux * (d + r), a.y + uy * (d + r));
        last = d + r;
        drawn += 1;
      });
      c.lineTo(a.x + ux * to, a.y + uy * to);
      if (s < n - 2 && cut[s + 1] > 0) {
        var nb = pts[s + 2], l2 = Math.hypot(nb.x - b.x, nb.y - b.y);
        c.quadTo(b.x, b.y, b.x + (nb.x - b.x) / l2 * cut[s + 1], b.y + (nb.y - b.y) / l2 * cut[s + 1]);
      }
    }
    return drawn;
  }

  // A line's hops depend on the lines under it, which move without it:
  // each line is drawn again when what it would hop has changed.
  function rehop(s, all) {
    if (!s || !s.graph) return;
    s.graph.view.states.forEach(function (st) {
      if (!st.cell || !st.cell.isEdge() || !st.shape || !st.shape.hopping || !st.absolutePoints) return;
      var key = jumpsOn ? JSON.stringify(hopsOf(st.shape, st.absolutePoints.filter(Boolean))) : "off";
      if (all || key !== st.shape.hopKey) {
        st.shape.hopKey = key;
        st.shape.redraw();
      }
    });
  }

  // What the probe reads: a line of the diagram's own as the canvas routed
  // it, from end to end, in the drawing's units.
  function routeOf(key) {
    var s = surface, cell = s && s.model.getCell(idOf(key)), st = cell && s.graph.view.getState(cell);
    if (!st || !st.absolutePoints) return null;
    var v = s.graph.view;
    return st.absolutePoints.filter(Boolean).map(function (p) {
      return [p.x / v.scale - v.translate.x, p.y / v.scale - v.translate.y];
    });
  }

  // What the probe reads: how many hops each line drew, by its cell's id.
  function hops() {
    var out = {};
    if (surface) {
      surface.graph.view.states.forEach(function (st) {
        if (st.cell && st.cell.isEdge() && st.shape && st.shape.hopping) out[st.cell.id] = st.shape.hopsDrawn || 0;
      });
    }
    return out;
  }

  /* A square line's turns from box `a` to box `b`, [x1, y1, x2, y2] (a
   * point is a box of no size), around the boxes in `obstacles`: `plain`,
   * the turns squareTurns gives as [x, y], when the line through them runs
   * through none, or when it has no turns; else the cheapest way over a
   * grid of corridors a margin out from every box, a bend costing BEND,
   * leaving `a` and coming into `b` square from a side's middle; `plain`
   * again when the boxes leave no way. `detour` in
   * terrane/draw/annotations.py, step for step: the inputs snapped to a
   * 1024th, so every sum after is exact, and the queue's ties broken on the
   * order things went into it. Whole in itself, so the test runs it alone. */
  function detour(a, b, obstacles, plain) {
    var M = 10, BEND = 36, STEPS = [[1, 0], [0, 1], [-1, 0], [0, -1]];
    if (!plain.length) return plain.slice();
    function snap(v) { return Math.floor(v * 1024 + 0.5) / 1024; }
    function boxOf(o) { return [snap(o[0]), snap(o[1]), snap(o[2]), snap(o[3])]; }
    function same(p, q) { return p[0] === q[0] && p[1] === q[1] && p[2] === q[2] && p[3] === q[3]; }
    function cuts(p, q, o) {
      if (p[0] === q[0]) {
        return o[0] < p[0] && p[0] < o[2] && Math.max(Math.min(p[1], q[1]), o[1]) < Math.min(Math.max(p[1], q[1]), o[3]);
      }
      return o[1] < p[1] && p[1] < o[3] && Math.max(Math.min(p[0], q[0]), o[0]) < Math.min(Math.max(p[0], q[0]), o[2]);
    }
    function lineOf(values) {
      values.sort(function (p, q) { return p - q; });
      return values.filter(function (v, i) { return i === 0 || v !== values[i - 1]; });
    }
    var sa = boxOf(a), sb = boxOf(b);
    var walls = obstacles.map(boxOf).sort(function (p, q) { return p[0] - q[0] || p[1] - q[1] || p[2] - q[2] || p[3] - q[3]; })
      .filter(function (o, i, all) { return (i === 0 || !same(o, all[i - 1])) && !same(o, sa) && !same(o, sb); });
    var ca = [(sa[0] + sa[2]) / 2, (sa[1] + sa[3]) / 2], cb = [(sb[0] + sb[2]) / 2, (sb[1] + sb[3]) / 2];
    var run = [ca].concat(plain.map(function (p) { return [p[0], p[1]]; }), [cb]);
    var clear = true;
    for (var r = 0; r < run.length - 1 && clear; r += 1) {
      for (var w = 0; w < walls.length; w += 1) if (cuts(run[r], run[r + 1], walls[w])) { clear = false; break; }
    }
    if (clear) return plain.slice();
    var blocks = walls.concat([sa, sb].filter(function (o) { return o[0] < o[2] && o[1] < o[3]; }));
    function free(p) {
      return !blocks.some(function (o) { return o[0] < p[0] && p[0] < o[2] && o[1] < p[1] && p[1] < o[3]; });
    }
    function ports(o, c) {
      if (o[0] === o[2] && o[1] === o[3]) return [[c, -1, c]];
      return [[[o[2] + M, c[1]], 0, [o[2], c[1]]], [[c[0], o[3] + M], 1, [c[0], o[3]]],
        [[o[0] - M, c[1]], 2, [o[0], c[1]]], [[c[0], o[1] - M], 3, [c[0], o[1]]]].filter(function (port) {
        return free(port[0]) && !walls.some(function (o2) { return cuts(port[2], port[0], o2); });
      });
    }
    var xs = lineOf([sa[0] - M, sa[2] + M, ca[0], sb[0] - M, sb[2] + M, cb[0]]
      .concat(walls.map(function (o) { return o[0] - M; }), walls.map(function (o) { return o[2] + M; })));
    var ys = lineOf([sa[1] - M, sa[3] + M, ca[1], sb[1] - M, sb[3] + M, cb[1]]
      .concat(walls.map(function (o) { return o[1] - M; }), walls.map(function (o) { return o[3] + M; })));
    var xi = {}, yi = {};
    xs.forEach(function (x, i) { xi[x] = i; });
    ys.forEach(function (y, j) { yi[y] = j; });
    var goals = {}, targets = [];
    ports(sb, cb).forEach(function (port) {
      var d = port[1];
      goals[xi[port[0][0]] + "," + yi[port[0][1]]] = [d < 0 ? -1 : (d + 2) % 4, d < 0 ? 0 : M];
      targets.push(port[0]);
    });
    if (!targets.length) return plain.slice();
    function near(i, j) {
      return Math.min.apply(null, targets.map(function (t) { return Math.abs(xs[i] - t[0]) + Math.abs(ys[j] - t[1]); }));
    }
    function turn(d1, d2) {
      if (d1 < 0 || d2 < 0 || d1 === d2) return 0;
      return (d1 + 2) % 4 === d2 ? 2 * BEND : BEND;
    }
    // A queue by cost, then by the order things went in.
    var heap = [], count = 0, best = {}, parent = {};
    function before(p, q) { return p[0] < q[0] || (p[0] === q[0] && p[1] < q[1]); }
    function push(e) {
      heap.push(e);
      for (var i = heap.length - 1; i > 0;) {
        var up = (i - 1) >> 1;
        if (!before(heap[i], heap[up])) break;
        var t = heap[i]; heap[i] = heap[up]; heap[up] = t; i = up;
      }
    }
    function pop() {
      var top = heap[0], last = heap.pop();
      if (heap.length) {
        heap[0] = last;
        for (var i = 0; ;) {
          var l = 2 * i + 1, rr = l + 1, k = i;
          if (l < heap.length && before(heap[l], heap[k])) k = l;
          if (rr < heap.length && before(heap[rr], heap[k])) k = rr;
          if (k === i) break;
          var t = heap[i]; heap[i] = heap[k]; heap[k] = t; i = k;
        }
      }
      return top;
    }
    function key(s) { return s[0] + "," + s[1] + "," + s[2]; }
    ports(sa, ca).forEach(function (port) {
      var s = [xi[port[0][0]], yi[port[0][1]], port[1]], g = port[1] < 0 ? 0 : M;
      if (!(key(s) in best) || g < best[key(s)]) {
        best[key(s)] = g;
        parent[key(s)] = null;
        push([g + near(s[0], s[1]), count, 0, s, g]);
        count += 1;
      }
    });
    var end = null;
    while (heap.length) {
      var e = pop(), s = e[3], g = e[4];
      if (e[2]) { end = s; break; }
      if (g > best[key(s)]) continue;
      var i = s[0], j = s[1], d = s[2], goal = goals[i + "," + j];
      if (goal) {
        var total = g + turn(d, goal[0]) + goal[1];
        push([total, count, 1, s, total]);
        count += 1;
      }
      for (var k = 0; k < 4; k += 1) {
        if (d >= 0 && k === (d + 2) % 4) continue;
        var ni = i + STEPS[k][0], nj = j + STEPS[k][1];
        if (ni < 0 || ni >= xs.length || nj < 0 || nj >= ys.length) continue;
        var p = [xs[i], ys[j]], q = [xs[ni], ys[nj]];
        if (!free(q) || blocks.some(function (o) { return cuts(p, q, o); })) continue;
        var ng = g + Math.abs(q[0] - p[0]) + Math.abs(q[1] - p[1]) + (d >= 0 && k !== d ? BEND : 0);
        var t = [ni, nj, k];
        if (!(key(t) in best) || ng < best[key(t)]) {
          best[key(t)] = ng;
          parent[key(t)] = s;
          push([ng + near(ni, nj), count, 0, t, ng]);
          count += 1;
        }
      }
    }
    if (!end) return plain.slice();
    var nodes = [];
    for (var at = end; at; at = parent[key(at)]) nodes.push([xs[at[0]], ys[at[1]]]);
    var pts = [ca].concat(nodes.reverse(), [cb]), kept = [pts[0]];
    for (var n = 1; n < pts.length - 1; n += 1) {
      var pp = kept[kept.length - 1], qq = pts[n], rr2 = pts[n + 1];
      if ((pp[0] === qq[0] && qq[0] === rr2[0]) || (pp[1] === qq[1] && qq[1] === rr2[1])) continue;
      kept.push(qq);
    }
    kept.push(pts[pts.length - 1]);
    return kept.slice(1, -1);
  }

  /* What a square or curved line goes around, in the drawing's units:
   * every box of the estate and every shape, note and text of the
   * diagram's own, not a frame, which holds things rather than standing in
   * the way, nor a boundary. `_walls` in terrane/draw/annotations.py. */
  var WALLS = { shape: true, note: true, text: true };

  function walls(view) {
    var s = surface, out = [], k = view.scale, tr = view.translate;
    if (!s) return out;
    view.states.forEach(function (st) {
      var c = st.cell;
      if (!c || !c.isVertex()) return;
      var mine = c.terraneOwn;
      var record = !mine && c.terraneNode && c.id === "n:" + c.terraneNode && c.parent === s.layers.boxes;
      if (!(mine ? WALLS[mine.role] : record)) return;
      out.push([st.x / k - tr.x, st.y / k - tr.y, (st.x + st.width) / k - tr.x, (st.y + st.height) / k - tr.y]);
    });
    return out;
  }

  // A square or curved line is routed again when what it goes around
  // moves, which maxGraph does not know it depends on.
  function reroute(s) {
    if (!s || !s.graph) return;
    var lines = s.layers.over.getChildren().filter(function (c) {
      return c.isEdge() && c.terraneOwn && (c.terraneOwn.route === "square" || c.terraneOwn.route === "curved");
    });
    if (!lines.length) return;
    lines.forEach(function (c) { s.graph.view.invalidate(c, false, false); });
    s.graph.view.validate();
  }

  /* The turns of a square line between two boxes: across the middle of
   * the gap between them, or down it, whichever gap is the wider, and none
   * when they overlap both ways, which leaves it straight. The picture's
   * `square` in terrane/draw/annotations.py, the same arithmetic. */
  function squareTurns(a, b) {
    var ca = { x: (a.x1 + a.x2) / 2, y: (a.y1 + a.y2) / 2 }, cb = { x: (b.x1 + b.x2) / 2, y: (b.y1 + b.y2) / 2 };
    var gx = b.x1 >= a.x2 ? b.x1 - a.x2 : a.x1 >= b.x2 ? a.x1 - b.x2 : -1;
    var gy = b.y1 >= a.y2 ? b.y1 - a.y2 : a.y1 >= b.y2 ? a.y1 - b.y2 : -1;
    if (gx < 0 && gy < 0) return [];
    if (gx >= gy) {
      var x = b.x1 >= a.x2 ? (a.x2 + b.x1) / 2 : (b.x2 + a.x1) / 2;
      return [{ x: x, y: ca.y }, { x: x, y: cb.y }];
    }
    var y = b.y1 >= a.y2 ? (a.y2 + b.y1) / 2 : (b.y2 + a.y1) / 2;
    return [{ x: ca.x, y: y }, { x: cb.x, y: y }];
  }

  function shapeStyle(shape, w, h) {
    if (shape === "ellipse") return { shape: "ellipse" };
    if (shape === "rectangle") return { shape: "rectangle" };
    if (shape === "barrel") return { shape: "terrane-barrel" };
    if (POLYGONS[shape]) return { shape: "terrane-" + shape };
    // round-rectangle and anything not listed: Cytoscape rounds by a
    // quarter of the shorter side, at most eight pixels; maxGraph's arc is
    // the diameter.
    return { shape: "rectangle", rounded: true, absoluteArcSize: true, arcSize: 2 * Math.min(w / 4, h / 4, 8) };
  }

  /* ---- the diagram's own look
   * Illustrated (V16): the app's own picture language, the Diagrams page's.
   * Seven fills a person picks from, every one edged in ink, accent the one
   * strong color with its words in paper; a hard ink shadow under a shape
   * or a note; a shape's first line of words its name in the display face
   * and the rest a caption; a frame's name on an ink tab across its top
   * edge; lines in the pictures' line color, their words on paper tags. An
   * outline solid, dashed or none; the words small, middling or large. The
   * same names and colors are in terrane/annotations.py and
   * terrane/draw/annotations.py. */
  var FILLS = {
    yellow: "#fbefc6", mint: "#b7dad3", lavender: "#dcd7f0", rose: "#f2d2cb", white: "#fffdf8", stone: "#e1dacd",
    accent: "#0f766e",
  };
  var FILL_ORDER = ["yellow", "mint", "lavender", "rose", "white", "stone", "accent"];
  var WORDS_ON = { accent: "#fffdf8" };
  var TEXT_SIZES = { s: 11, m: 13, l: 16 };
  //: How heavy an edge is drawn, by a look's `weight` (WEIGHTS in
  //: terrane/annotations.py): M when it says nothing.
  var WEIGHTS = { s: 1, m: 1.25, l: 2 };
  //: The most a side of one of its own may be typed as, in the drawing's units.
  var MOST_SIZE = 4000;
  var ROLE_FILL = { note: "yellow", shape: "white" };
  var INK = "#2e2a25";
  var LINE_INK = "#6e655a";
  var CAPTION_INK = "#6e655a";
  var PAPER = "#fffdf8";
  //: How far down and right a shape's or a note's hard shadow falls.
  var SHADOW = 4;
  //: A rounded box's corner radius, and a frame's.
  var ROUND = 6;
  var NAME_FACE = "'Libre Franklin', Geist, system-ui, sans-serif";
  //: How much smaller a caption is than the name over it, and the room
  //: either side of a frame's name on its tab.
  var CAPTION_STEP = 2, TAB_PAD = 8;

  /* Icon tiles, a diagram's other look (V16): every shape a square tile in
   * the middle of its box, light at the top and deep at the foot, a soft
   * glow under it and its icon in white (own-icons.js); its words under the
   * box, a little wider than it; a note flat, a frame a pale panel with its
   * name inside, lines gray. The same numbers are in
   * terrane/draw/annotations.py. The look is the diagram's (`look:` in its
   * file), Illustrated when it says nothing. */
  var LOOK = "illustrated";
  var TILE = 48, TILE_ROUND = 12, TILE_GLOW = 4, TILE_ICON = 22, TILE_GAP = 6, TILE_WORDS_OVER = 16;
  var TILE_FILLS = {
    yellow: ["#f2c94c", "#c9a227"], mint: ["#36b096", "#1f7a68"], lavender: ["#8a84e6", "#5b54c6"],
    rose: ["#e27b6e", "#b54a3f"], white: ["#6e7683", "#3b4049"], stone: ["#a1937f", "#6e655a"],
    accent: ["#5c8fd6", "#3a62a8"],
  };
  var TILE_INK = "#1e2230";
  var TILE_CAPTION = "#6b7489";
  var TILE_LINE = "#8a92a0";
  var TILE_FRAME = "#f4f5f7";
  var TILE_FRAME_INK = "#5b6170";
  //: The sheet Icon tiles draw on, and how far a tile's words' patch
  //: reaches past the widest of them either side.
  var TILE_SHEET = "#ffffff", TILE_GROUND_PAD = 3;
  var KIND_ICONS = {
    rectangle: "box", rounded: "box", ellipse: "circle", diamond: "diamond", hexagon: "hexagon",
    cylinder: "database", cloud: "cloud", document: "file-text", person: "user", callout: "message-square",
  };
  //: The providers' and vendors' marks a tile can carry instead, by folder
  //: under icons/ and the name the panel lists them under (MARK_SETS in
  //: terrane/icons.py). A shape names one as `aws/lambda`.
  var MARK_SETS = [["aws", "AWS"], ["azure", "Azure"], ["gcp", "Google Cloud"], ["brands", "Vendors"]];
  var MARK = new RegExp("^(?:" + MARK_SETS.map(function (s) { return s[0]; }).join("|") + ")/[a-z0-9-]+$");
  //: The size a tool draws at when the sheet is clicked rather than dragged.
  var DEFAULT_SIZE = { shape: [120, 64], note: [184, 96], text: [200, 44], frame: [360, 240] };

  // What maxGraph's handle may turn: not a frame, since what sits in it
  // would turn too (terrane.annotations.TURNS).
  var TURNS = { shape: true, note: true, text: true };
  // What quick connect's arrows go about, of the diagram's own: not a frame,
  // which holds things rather than joining them, nor a line.
  var QUICK = { shape: true, note: true, text: true };
  //: How far off a box's side quick connect's arrows sit, in pixels on the
  //: screen, and the gap in the drawing's units to the next box it draws.
  var QUICK_OUT = 14, QUICK_GAP = 60;
  var QUICK_WORDS = { n: "Add the next box above, joined by a line. Drag to draw a line instead.",
    e: "Add the next box to the right, joined by a line. Drag to draw a line instead.",
    s: "Add the next box below, joined by a line. Drag to draw a line instead.",
    w: "Add the next box to the left, joined by a line. Drag to draw a line instead." };

  // The radius its corners are rounded by: its look's own, else its kind's;
  // 0 for square, null for what has no corners to round (corners_of).
  function cornersOf(item) {
    var role = item.role, kind = item.shape || "rectangle";
    if ((role !== "shape" && role !== "note" && role !== "frame") ||
        (role === "shape" && LOOK !== "tiles" && kind !== "rectangle" && kind !== "rounded")) return null;
    var mine = (item.look || {}).corners;
    if (mine !== undefined && mine !== null) return Number(mine);
    if (LOOK === "tiles") return { shape: TILE_ROUND, frame: 16, note: 4 }[role];
    return role === "frame" || kind === "rounded" ? ROUND : 0;
  }

  // How much of its fill shows, in percent, and how heavy its edge is.
  function fillOpacityOf(item) { return (item.look || {}).opacity || 100; }
  function weightOf(item) { return WEIGHTS[(item.look || {}).weight] || WEIGHTS.m; }

  function ownStyle(item) {
    var look = item.look || {}, role = item.role;
    if (role === "line") {
      var routed = item.route === "square" || item.route === "curved";
      var line = {
        curved: item.route === "curved",
        strokeColor: LOOK === "tiles" ? TILE_LINE : LINE_INK, strokeWidth: 1.5, dashed: look.line === "dashed", dashPattern: "6 4",
        endArrow: item.ends === "none" ? "none" : "block", endSize: 7, endFill: true,
        startArrow: item.ends === "both" ? "block" : "none", startSize: 7, startFill: true,
        fontFamily: FACE, fontSize: TEXT_SIZES[look.text || "s"], fontColor: LOOK === "tiles" ? TILE_CAPTION : INK, html: true,
        labelBackgroundColor: LOOK === "tiles" ? "#ffffff" : PAPER, labelBorderColor: LOOK === "tiles" ? "none" : INK,
        spacing: 3,
        // A straight line bends where a person drags it; the others turn
        // by themselves.
        editable: false, rotatable: false, cloneable: false, bendable: !routed,
      };
      // A straight line has no edge style at all; maxGraph has none named so.
      if (routed) line.edgeStyle = "terrane-square";
      // An end held at a point of its box, a share of it across and down.
      if (held(item.from_at)) Object.assign(line, { exitX: item.from_at[0], exitY: item.from_at[1], exitPerimeter: false });
      if (held(item.to_at)) Object.assign(line, { entryX: item.to_at[0], entryY: item.to_at[1], entryPerimeter: false });
      return line;
    }
    if (LOOK === "tiles") return tilesStyle(item);
    var fill = ownFill(item);
    var stroke = role === "text" || look.line === "none" ? "none" : INK;
    var size = TEXT_SIZES[look.text] || (role === "frame" ? 12 : 13);
    var style = {
      fillColor: fill ? FILLS[fill] : "none", strokeColor: stroke, strokeWidth: weightOf(item),
      fillOpacity: fillOpacityOf(item),
      dashed: look.line === "dashed", dashPattern: "6 4",
      fontFamily: FACE, fontSize: size, fontColor: WORDS_ON[fill] || INK, html: true, whiteSpace: "wrap",
      overflow: "hidden", shadow: castsShadow(item),
      editable: false, rotatable: TURNS[role] === true, cloneable: false, foldable: false,
    };
    if (item.rotate) style.rotation = item.rotate;
    if (role === "frame") {
      // Its name on a tab twelve in, across the top edge: the label hangs
      // half its height above the frame, unclipped, on one line.
      Object.assign(style, { shape: "rectangle", rounded: cornersOf(item) > 0, absoluteArcSize: true,
        arcSize: cornersOf(item) * 2,
        align: "left", verticalAlign: "top", spacing: 0, spacingLeft: 12, spacingTop: -tabHeight(size) / 2,
        spacingRight: 12, overflow: "visible", whiteSpace: "nowrap" });
    } else if (role === "note") {
      Object.assign(style, { shape: "rectangle", rounded: cornersOf(item) > 0, absoluteArcSize: true,
        arcSize: cornersOf(item) * 2, align: "left", verticalAlign: "top", spacing: 10 });
    } else if (role === "text") {
      Object.assign(style, { shape: "rectangle", align: "left", verticalAlign: "top", spacing: 2, fontColor: "#3b4049" });
    } else {
      var shape = (OWN_PATHS[item.shape] || item.shape === "rounded") ? item.shape : "rectangle";
      // A box with its corners rounded is maxGraph's own rounded rectangle,
      // its radius half the arc it is given.
      var round = cornersOf(item);
      if (shape === "rounded" || (shape === "rectangle" && round)) {
        Object.assign(style, { shape: "rectangle", rounded: round > 0, absoluteArcSize: true, arcSize: round * 2 });
      } else Object.assign(style, { shape: "own-" + shape });
      // A line joined to an ellipse or a diamond ends on its outline, not
      // on the box around it; the picture clips it the same way.
      if (shape === "ellipse") style.perimeter = "ellipsePerimeter";
      if (shape === "diamond") style.perimeter = "rhombusPerimeter";
      Object.assign(style, { align: "center", verticalAlign: "middle", spacing: 8 });
    }
    return style;
  }

  // The fill it is drawn in: its own, or the one its kind starts with; a
  // frame and text start with none.
  function ownFill(item) {
    if (item.role === "text") return null;
    var look = item.look || {};
    return look.fill && FILLS[look.fill] ? look.fill : ROLE_FILL[item.role] || null;
  }

  // A shape or a note stands on the sheet with a hard shadow under it; text,
  // a frame and what has no edge lie flat, as everything does as tiles.
  // casts_shadow in annotations.py.
  function castsShadow(item) {
    var look = item.look || {};
    // A see-through fill casts none: its ink would show through.
    return LOOK !== "tiles" && (item.role === "shape" || item.role === "note") && look.line !== "none" &&
      look.shadow !== "none" && !(look.opacity < 100);
  }

  // One of the diagram's own as Icon tiles draws it (_tiled in annotations.py).
  function tilesStyle(item) {
    var look = item.look || {}, role = item.role, fill = ownFill(item);
    var size = TEXT_SIZES[look.text] || (role === "frame" ? 12 : 13);
    var dashed = look.line === "dashed";
    var style = {
      fontFamily: FACE, fontSize: size, html: true, shadow: false, strokeWidth: weightOf(item), dashed: dashed,
      dashPattern: "6 4", fillOpacity: fillOpacityOf(item),
      editable: false, rotatable: TURNS[role] === true, cloneable: false, foldable: false,
    };
    if (item.rotate) style.rotation = item.rotate;
    if (role === "shape") {
      // A mark stands in the tile's place, so there is no tile to paint.
      var t = markOf(item) ? ["none", "none"] : TILE_FILLS[fill] || TILE_FILLS.white;
      return Object.assign(style, { shape: "own-tile", fillColor: t[0], gradientColor: t[1], strokeColor: "none",
        arcSize: cornersOf(item) * 2,
        perimeter: "tilePerimeter", align: "center", verticalAlign: "top", spacing: 0, overflow: "visible",
        whiteSpace: "wrap", fontColor: TILE_INK });
    }
    if (role === "frame") {
      return Object.assign(style, { shape: "rectangle", rounded: cornersOf(item) > 0, absoluteArcSize: true,
        arcSize: cornersOf(item) * 2, fillColor: fill ? FILLS[fill] : TILE_FRAME, strokeColor: dashed ? TILE_FRAME_INK : "none", align: "left",
        verticalAlign: "top", spacing: 0, spacingLeft: 14, spacingTop: 10, spacingRight: 14, overflow: "hidden",
        whiteSpace: "nowrap", fontColor: TILE_FRAME_INK });
    }
    if (role === "note") {
      return Object.assign(style, { shape: "rectangle", rounded: cornersOf(item) > 0, absoluteArcSize: true,
        arcSize: cornersOf(item) * 2, fillColor: FILLS[fill || "yellow"], strokeColor: dashed ? TILE_FRAME_INK : "none", align: "left",
        verticalAlign: "top", spacing: 10, overflow: "hidden", whiteSpace: "wrap", fontColor: WORDS_ON[fill] || INK });
    }
    return Object.assign(style, { shape: "rectangle", fillColor: "none", strokeColor: "none", align: "left",
      verticalAlign: "top", spacing: 2, overflow: "hidden", whiteSpace: "wrap", fontColor: INK });
  }

  // The icon a shape carries as a tile: its own, a provider's mark or one
  // of the plain icons, or its kind's (icon_of).
  function iconOf(item) {
    var icons = window.TerraneOwnIcons || {}, named = (item.look || {}).icon;
    return named && (icons[named] || MARK.test(named)) ? named : KIND_ICONS[item.shape || "rectangle"] || "box";
  }

  // The mark a shape carries, by its name under icons/, or nothing. The
  // server refuses a mark it does not ship, so the name is the file.
  function markOf(item) {
    var named = (item.look || {}).icon;
    return named && MARK.test(named) ? named : "";
  }

  // A tile's label: its icon in the middle of its box, and its name and
  // caption under the box, wrapped a little wider than it (tile_rows).
  function tileLabel(cell, value) {
    var item = cell.terraneOwn, look = item.look || {}, size = TEXT_SIZES[look.text] || 13;
    var w = cell.geometry ? cell.geometry.width : 120, h = cell.geometry ? cell.geometry.height : 64;
    var icon = (window.TerraneOwnIcons || {})[iconOf(item)] || "", mark = markOf(item);
    var side = Math.min(w, h, TILE);
    // A mark is the provider's own file, drawn whole in the tile's place;
    // the export carries it into the picture as data (carryMarks).
    var out = '<div style="height:' + h + 'px;display:flex;align-items:center;justify-content:center">' + (mark
      ? '<img src="icons/' + mark + '.svg" width="' + side + '" height="' + side + '" alt="" style="display:block">'
      : '<svg width="' + TILE_ICON + '" height="' + TILE_ICON + '" viewBox="0 0 24 24" fill="none" stroke="#ffffff" ' +
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + icon + "</svg>") + "</div>";
    var lines = String(value || "").split("\n"), words = "";
    if (lines[0].trim()) {
      words += '<div style="font-family:' + FACE + ";font-weight:600;font-size:" + size + "px;line-height:1.32;color:" +
        TILE_INK + '">' + escapeText(lines[0]) + "</div>";
    }
    lines.slice(1).forEach(function (p) {
      if (!p.trim()) return;
      words += '<div style="font-family:' + FACE + ";font-weight:400;font-size:" + (size - CAPTION_STEP) +
        "px;line-height:1.32;color:" + TILE_CAPTION + '">' + escapeText(p) + "</div>";
    });
    if (words) {
      // On a patch of what lies under them (tile_ground): a line leaving
      // the tile downward runs under its words, and not through them. The
      // patch's margin gives its padding back, so the words wrap where the
      // picture's do.
      out += '<div style="width:' + (w + 2 * TILE_WORDS_OVER) + "px;margin-left:-" + TILE_WORDS_OVER + "px;padding-top:" +
        TILE_GAP + 'px;text-align:center"><span style="display:inline-block;vertical-align:top;background:' +
        tileGround(cell) + ";padding:0 " + TILE_GROUND_PAD + "px;margin:0 -" + TILE_GROUND_PAD + 'px">' + words +
        "</span></div>";
    }
    return out;
  }

  // What lies under a tile's words: the frame it sits in, the innermost,
  // as Icon tiles fill one, else the sheet (tile_ground).
  function tileGround(cell) {
    for (var c = cell.parent; c && c.terraneOwn; c = c.parent) {
      if (c.terraneOwn.role === "frame") {
        var f = ownFill(c.terraneOwn);
        return f ? FILLS[f] : TILE_FRAME;
      }
    }
    return TILE_SHEET;
  }

  // How the diagram draws its own: Illustrated, or Icon tiles. Changed, the
  // diagram's own is drawn again in it.
  function setLook(look) {
    var next = look === "tiles" ? "tiles" : "illustrated";
    if (surface && surface.div) surface.div.classList.toggle("look-tiles", next === "tiles");
    if (next === LOOK) return;
    LOOK = next;
    if (surface && surface.cy) own(Canvas.cv ? Canvas.cv.data.annotations : surface.readOnlyOwn || [], true);
  }

  function tabHeight(size) { return size * 1.32 + 4; }

  // A shape's words: the first line its name in the display face, every
  // later one a caption two sizes down, each a block of its own so it wraps
  // to the box as the picture wraps it (named_rows). A blank line is none.
  function namedLabel(item, value) {
    var look = item.look || {}, size = TEXT_SIZES[look.text] || 13, fill = ownFill(item);
    var words = WORDS_ON[fill] || INK;
    var caption = WORDS_ON[fill] ? "color:" + words + ";opacity:.75" : "color:" + CAPTION_INK;
    var lines = value.split("\n"), out = "";
    if (lines[0].trim()) {
      out += '<div style="font-family:' + NAME_FACE + ";font-weight:700;font-size:" + size + "px;line-height:1.32;color:" +
        words + '">' + escapeText(lines[0]) + "</div>";
    }
    lines.slice(1).forEach(function (p) {
      if (!p.trim()) return;
      out += '<div style="font-family:' + FACE + ";font-weight:400;font-size:" + (size - CAPTION_STEP) +
        "px;line-height:1.32;" + caption + '">' + escapeText(p) + "</div>";
    });
    return out;
  }

  // A frame's name on its ink tab, cut short with an ellipsis where it would
  // run past the frame (_tab in annotations.py).
  function frameTab(cell, value) {
    var look = cell.terraneOwn.look || {}, size = TEXT_SIZES[look.text] || 12;
    var room = Math.max(1, (cell.geometry ? cell.geometry.width : 200) - 24);
    return '<span style="display:inline-block;box-sizing:border-box;max-width:' + room + "px;overflow:hidden;" +
      "text-overflow:ellipsis;white-space:nowrap;vertical-align:top;background:" + INK + ";color:" + PAPER +
      ";font-family:" + FACE + ";font-weight:600;font-size:" + size + "px;line-height:1.32;padding:2px " + TAB_PAD +
      'px;border-radius:3px">' + escapeText(value.split("\n")[0]) + "</span>";
  }

  function escapeText(value) {
    var div = document.createElement("div");
    div.textContent = value;
    return div.innerHTML.replace(/\n/g, "<br>");
  }

  // ---- the surface: one maxGraph model while the canvas is open
  var surface = null;

  /* Laid over the canvas's sheet the first time it draws, and kept while
   * the canvas is open: a new drawing of the estate (a placed view, a box
   * moved into another boundary) binds a new Cytoscape to the same model,
   * and the diagram's own layers and their selection stay. Given a list, it
   * is a drawing the canvas is not open on, read only: a diagram drawn on
   * the canvas and opened as a diagram shows its own shapes too. */
  function attach(cy, list, look) {
    if (!cy || !enabled()) return Promise.resolve(null);
    return load().then(function (mg) {
      if (cy.destroyed()) return null;
      if (!surface || surface.host !== cy.container()) open(mg, cy.container());
      // The look first, so the diagram's own is drawn once, in it: the
      // canvas's file says it, a diagram opened to read its payload.
      surface.readOnlyOwn = list;
      LOOK = (Canvas.cv ? Canvas.cv.data.look : look) === "tiles" ? "tiles" : "illustrated";
      surface.div.classList.toggle("look-tiles", LOOK === "tiles");
      bind(cy, list);
      return surface;
    }).catch(function (err) {
      // A canvas without the mirror is the canvas as it always was.
      if (window.console) console.warn("maxGraph canvas off:", err.message);
      return null;
    });
  }

  function open(mg, host) {
    detach();
    var div = document.createElement("div");
    div.className = "mg-surface";
    // #cy stays the element a screen reader and the keys know.
    div.setAttribute("aria-hidden", "true");
    // Beside #cy, laid over it, not inside it: Cytoscape listens on its
    // container in the capture phase, so inside it every press reached
    // Cytoscape before the surface could keep it.
    host.parentNode.insertBefore(div, host.nextSibling);
    var place = function () {
      div.style.left = host.offsetLeft + "px";
      div.style.top = host.offsetTop + "px";
      div.style.width = host.offsetWidth + "px";
      div.style.height = host.offsetHeight + "px";
    };
    place();
    var watch = window.ResizeObserver ? new ResizeObserver(place) : null;
    if (watch) watch.observe(host);
    host.classList.add("under-mirror");
    var graph = new mg.Graph(div, undefined, [mg.SelectionCellsHandler, mg.SelectionHandler]);
    graph.setHtmlLabels(true);
    graph.getStylesheet().getDefaultEdgeStyle().shape = "terrane-line";
    var model = graph.getDataModel();
    // The layers, from the bottom: the frames on the bare sheet, the
    // estate's boundaries with the frames inside them, the estate's boxes
    // and lines, and the rest of the diagram's own.
    var root = model.getRoot(), bounds = root.getChildAt(0);
    var under = new mg.Cell(), boxes = new mg.Cell(), over = new mg.Cell();
    model.add(root, under, 0);
    model.add(root, boxes);
    model.add(root, over);
    graph.setDefaultParent(over);
    surface = { mg: mg, cy: null, host: host, div: div, graph: graph, model: model, watch: watch, queued: false,
      layers: { under: under, bounds: bounds, boxes: boxes, over: over }, cells: {}, shape: "", own: [],
      orphans: [], syncing: 0, tool: null, toolShape: "rectangle", edit: null };
    behave(surface);
    takePointer(surface);
    if (wanted) { setTool(wanted[0], wanted[1]); wanted = null; }
    return surface;
  }

  function bind(cy, list) {
    var s = surface;
    if (s.cy === cy) return;
    unbind();
    s.cy = cy;
    s.readOnly = !Canvas.cv;
    s.schedule = function () {
      if (!surface || surface.queued) return;
      surface.queued = true;
      window.requestAnimationFrame(function () {
        if (!surface) return;
        surface.queued = false;
        paint();
      });
    };
    // Destroyed for a new drawing of the canvas, the estate's layer waits
    // for it; destroyed because the canvas closed, the surface goes too.
    s.unbind = function () { if (Canvas.cv) unbind(); else detach(); };
    cy.on("render", s.schedule);
    cy.on("viewport", syncView);
    cy.on("destroy", s.unbind);
    // The estate first, so a line of the diagram's own that ends on a
    // record has the record to end on.
    s.shape = null;
    s.drawnOwn = false;
    paint();
    own(list !== undefined ? list : Canvas.cv ? Canvas.cv.data.annotations : []);
  }

  // The drawing of the estate gone (a new one is on its way, or the canvas
  // closed): the estate's layer empty, the diagram's own kept.
  function unbind() {
    var s = surface;
    if (!s || !s.cy) return;
    var cy = s.cy;
    s.cy = null;
    if (!cy.destroyed()) {
      cy.off("render", s.schedule);
      cy.off("viewport", syncView);
      cy.off("destroy", s.unbind);
    }
    quiet(function () { s.graph.removeCells(estateCells(s), false); });
    s.cells = {};
    s.shape = "";
  }

  // The estate's cells, its boundaries' and its boxes', and not the frames
  // of its own that sit among the boundaries.
  function estateCells(s) {
    return s.layers.bounds.getChildren().filter(function (c) { return !c.terraneOwn; })
      .concat(s.layers.boxes.getChildren());
  }

  // The diagram's own at the top of each of the layers it is drawn in.
  function ownCells(s) {
    return s.layers.under.getChildren().concat(
      s.layers.bounds.getChildren().filter(function (c) { return !!c.terraneOwn; }), s.layers.over.getChildren());
  }

  function detach() {
    wanted = null;
    if (!surface) return;
    var s = surface;
    closeEditor(false);
    if (s.onSpace) {
      document.removeEventListener("keydown", s.onSpace);
      document.removeEventListener("keyup", s.onSpace);
    }
    unbind();
    surface = null;
    if (s.watch) s.watch.disconnect();
    s.graph.destroy();
    if (s.div.parentNode) s.div.parentNode.removeChild(s.div);
    s.host.classList.remove("under-mirror");
  }

  // Changes the engine makes to keep in step, which are not the person's.
  function quiet(fn) {
    var s = surface;
    s.syncing += 1;
    try { s.graph.batchUpdate(fn); } finally { s.syncing -= 1; }
  }

  /* What maxGraph may do to what: the diagram's own is selected, moved,
   * resized and dropped into a frame; the estate is none of those, since
   * every gesture on it is the canvas's own (takePointer). */
  function behave(s) {
    var mg = s.mg, graph = s.graph, model = s.model;
    // Not while a tool is chosen, since a press then draws, even over a
    // shape; and not on a drawing the canvas is not open on. A frame not
    // yet picked is picked up by its edge or its name, as a boundary is:
    // pressed inside, it is sheet to drag across (takePointer).
    var mine = function (cell) {
      if (!(cell && cell.terraneOwn) || s.tool || s.readOnly) return false;
      if (cell.terraneOwn.role === "frame" && s.pressAt && !graph.isCellSelected(cell) && !onFrameEdge(cell, s.pressAt)) return false;
      return true;
    };
    // A shape locked on this diagram is picked, to be unlocked, and not
    // carried or resized.
    var lockedCell = function (cell) { return !!(cell && cell.terraneOwn && s.locked && s.locked[cell.terraneOwn.key]); };
    graph.isCellSelectable = mine;
    graph.isCellMovable = function (cell) { return mine(cell) && !lockedCell(cell); };
    graph.isCellResizable = function (cell) { return mine(cell) && cell.isVertex() && !lockedCell(cell); };
    // Turned by its handle as it is resized: not a frame, nor what is locked.
    graph.isCellRotatable = function (cell) {
      return mine(cell) && cell.isVertex() && TURNS[cell.terraneOwn.role] === true && !lockedCell(cell);
    };
    graph.isCellEditable = function () { return false; };
    graph.isCellFoldable = function () { return false; };
    // A line's end can be carried to another box, or off one to a point;
    // the whole line moved stays joined (setDisconnectOnMove).
    graph.isCellDisconnectable = function (cell) { return mine(cell) && cell.isEdge() && !lockedCell(cell); };
    graph.setDisconnectOnMove(false);
    // The points of a box, the estate's or the diagram's own, an end
    // carried over it can be held at.
    graph.getAllConnectionConstraints = function (st) {
      var c = st && st.cell;
      if (!c || !c.isVertex() || s.readOnly) return null;
      var mine2 = c.terraneOwn;
      var record = !mine2 && c.terraneNode && c.id === "n:" + c.terraneNode && c.parent === s.layers.boxes;
      if (!mine2 && !record) return null;
      // As tiles every shape is a square tile, and its points are a square's.
      var round = LOOK !== "tiles" && mine2 && mine2.role === "shape" &&
        (mine2.shape === "ellipse" || mine2.shape === "diamond");
      return (round ? PINS_ROUND : PINS).map(function (f) { return new mg.ConnectionConstraint(new mg.Point(f[0], f[1]), false); });
    };
    // As tiles, an end held at a point of a shape is that point of its
    // tile, not of the box round it (_ends in the picture), turned with it.
    var connectionPoint = graph.getConnectionPoint;
    graph.getConnectionPoint = function (vertex, constraint, round) {
      var own = vertex && vertex.cell && vertex.cell.terraneOwn;
      if (LOOK !== "tiles" || !own || own.role !== "shape" || !constraint || !constraint.point || constraint.perimeter) {
        return connectionPoint.apply(this, arguments);
      }
      var side = Math.min(vertex.width, vertex.height, TILE * vertex.view.scale);
      var cx = vertex.getCenterX(), cy = vertex.getCenterY();
      var x = cx - side / 2 + constraint.point.x * side, y = cy - side / 2 + constraint.point.y * side;
      var turn = (Number(vertex.style && vertex.style.rotation) || 0) * Math.PI / 180;
      if (turn) {
        var dx = x - cx, dy = y - cy;
        x = cx + dx * Math.cos(turn) - dy * Math.sin(turn);
        y = cy + dx * Math.sin(turn) + dy * Math.cos(turn);
      }
      return round === false ? new mg.Point(x, y) : new mg.Point(Math.round(x), Math.round(y));
    };
    graph.isCellsCloneable = function () { return false; };
    graph.isValidDropTarget = function (cell, cells) {
      if (!cell || !cell.terraneOwn || cell.terraneOwn.role !== "frame" || !cells) return false;
      // Not into itself, nor into a frame it holds.
      for (var c = cell; c; c = c.parent) if (cells.indexOf(c) !== -1) return false;
      return cells.every(function (m) { return m.isVertex(); });
    };
    graph.getLabel = function (cell) {
      if (cell && cell.terraneOwn) {
        var v = String(cell.value || "");
        if (LOOK === "tiles" && cell.terraneOwn.role === "shape") return tileLabel(cell, v);
        if (!v.trim()) return "";
        if (LOOK === "tiles") {
          var weight = cell.terraneOwn.role === "frame" ? 600 : 400;
          return '<div style="font-weight:' + weight + ';line-height:1.32">' + escapeText(cell.terraneOwn.role === "frame"
            ? v.split("\n")[0] : v) + "</div>";
        }
        if (cell.terraneOwn.role === "frame") return frameTab(cell, v);
        if (cell.terraneOwn.role === "shape") return namedLabel(cell.terraneOwn, v);
        return '<div style="font-weight:400;line-height:1.32">' + escapeText(v) + "</div>";
      }
      return typeof cell.value === "string" ? cell.value : "";
    };
    // Shift adds one of its own to what is picked, or takes it out, as it
    // does a record; maxGraph's own toggle is Ctrl alone.
    graph.isToggleEvent = function (evt) { return !!(evt && (evt.shiftKey || evt.ctrlKey || evt.metaKey)); };
    graph.setDropEnabled(true);
    graph.setSplitEnabled(false);
    graph.setConstrainChildren(false);
    graph.setAllowDanglingEdges(true);
    graph.setDisconnectOnMove(false);
    // Off until Snap to grid is on (grid, below).
    graph.setGridEnabled(false);
    graph.foldingEnabled = false;
    // A line stays in the layer it was drawn in, whatever its ends sit in.
    model.maintainEdgeParent = false;
    // As tiles, a tile and its words are drawn over every line. A line is a
    // child of the top layer and a tile in a frame a child of the frame, in
    // the layer under it, so ordering the lines back left a framed tile's
    // name under them. maxGraph's own foreground sequence, the one
    // keepEdgesInBackground puts every box in, carries the tiles alone.
    graph.view.stateValidated = function (state) {
      var mine = state.cell && state.cell.terraneOwn;
      var fg = LOOK === "tiles" && !!mine && mine.role === "shape" && state.cell.isVertex();
      var html = fg ? this.lastForegroundHtmlNode || this.lastHtmlNode : this.lastHtmlNode;
      var node = fg ? this.lastForegroundNode || this.lastNode : this.lastNode;
      var put = this.graph.cellRenderer.insertStateAfter(state, node, html);
      if (fg) { this.lastForegroundHtmlNode = put[1]; this.lastForegroundNode = put[0]; }
      else { this.lastHtmlNode = put[1]; this.lastNode = put[0]; }
    };
    var move = graph.getPlugin("SelectionHandler");
    if (move) {
      move.guidesEnabled = true;
      move.livePreview = true;
      // A press on a note in a frame picks the note. maxGraph, as mxGraph
      // did, hands a click on what is in a group to the group, and the probe's
      // press on its note restyled and moved the frame around it.
      move.isPropagateSelectionCell = function () { return false; };
      // Guides against every box on the sheet, the estate's records among
      // them, not only the shapes of the layer the moved one is in.
      move.getGuideStates = function () {
        var out = [];
        [s.layers.under, s.layers.bounds, s.layers.boxes, s.layers.over].forEach(function (layer) {
          // A cell's own descendants in maxGraph 0.25, not the model's.
          layer.filterDescendants(function (c) {
            if (!c.isVertex() || !(c.terraneOwn || (c.id && c.id.indexOf("n:") === 0 && c.id.indexOf("#") === -1))) return false;
            var st = graph.view.getState(c);
            if (st) out.push(st);
            return false;
          });
        });
        return out;
      };
      // An equal gap beside the guide's lines, as a record carried in its
      // boundary finds one (the canvas's evenGap): measured in the drawing's
      // units against every box on the sheet that is not moving, the
      // boundaries aside, and taking an axis from the guide's line when it
      // is nearer, and from the grid always. maxGraph's own guide looks only
      // at the boxes beside the moved one in its layer.
      var inBounds = function (c) {
        for (var p = c && c.parent; p; p = p.parent) if (p === s.layers.bounds) return true;
        return false;
      };
      var gaps = function (evens) {
        if (!Canvas.measureGaps) return;
        if (!evens.length) { Canvas.measureGaps([]); return; }
        var v = graph.view, k = v.scale, tr = v.translate, sheet = document.getElementById("mapSheet");
        var cr = graph.container.getBoundingClientRect(), sr = sheet ? sheet.getBoundingClientRect() : cr;
        Canvas.measureGaps(evens, k, { x: tr.x * k, y: tr.y * k }, cr.left - sr.left, cr.top - sr.top);
      };
      var guideFor = move.createGuide.bind(move);
      move.createGuide = function () {
        var guide = guideFor();
        var plain = guide.move.bind(guide), drop = guide.destroy.bind(guide), show = guide.setVisible.bind(guide);
        guide.move = function (bounds, delta, grid, clone) {
          var raw = delta ? { x: delta.x, y: delta.y } : null;
          var d = plain(bounds, delta, grid, clone);
          if (!bounds || !raw || !Canvas.evenGap || surface !== s) return d;
          var v = graph.view, k = v.scale, tr = v.translate;
          var unit = function (b) {
            var x1 = b.x / k - tr.x, y1 = b.y / k - tr.y, w = b.width / k, h = b.height / k;
            return { x1: x1, y1: y1, x2: x1 + w, y2: y1 + h, w: w, h: h };
          };
          var nb = unit({ x: bounds.x + raw.x, y: bounds.y + raw.y, width: bounds.width, height: bounds.height });
          var boxes = guide.states.filter(function (st) {
            return st && st.cell && !move.isCellMoving(st.cell) && !inBounds(st.cell);
          }).map(unit);
          var evens = [];
          [["x", "guideX"], ["y", "guideY"]].forEach(function (pair) {
            var a = pair[0], line = guide[pair[1]];
            var lined = !!(line && line.node && line.node.style.visibility === "visible");
            var even = Canvas.evenGap(boxes, nb, a, 6 / k);
            if (!even || (lined && even.d * k >= Math.abs(d[a] - raw[a]))) return;
            d[a] = (even.start + tr[a]) * k - bounds[a];
            if (lined) line.node.style.visibility = "hidden";
            evens.push(even);
          });
          gaps(evens);
          return d;
        };
        guide.destroy = function () { drop(); gaps([]); };
        guide.setVisible = function (on) { show(on); if (!on) gaps([]); };
        return guide;
      };
    }
    var accent = (app.DRAW && app.DRAW.accent) || "#0f766e";
    mg.VertexHandlerConfig.selectionColor = accent;
    mg.VertexHandlerConfig.selectionStrokeWidth = 1.5;
    mg.VertexHandlerConfig.selectionDashed = false;
    // The handle that turns a shape, a note or text; a frame's style says
    // it does not turn.
    mg.VertexHandlerConfig.rotationEnabled = true;
    // Off the top right corner, as draw.io has it: above the middle is
    // where quick connect's arrow is.
    mg.VertexHandler.prototype.getRotationHandlePosition = function () {
      return new mg.Point(this.bounds.x + this.bounds.width + 12, this.bounds.y - 12);
    };
    mg.EdgeHandlerConfig.selectionColor = accent;
    mg.EdgeHandlerConfig.selectionDashed = false;
    // A handle halfway along each stretch of a picked straight line, dragged
    // to bend it there; Shift and a click on a bend take it out.
    mg.EdgeHandlerConfig.virtualBendsEnabled = true;
    mg.EdgeHandlerConfig.removeBendOnShiftClickEnabled = true;
    // maxGraph draws a box's points with an image from a folder this app
    // does not have; a ring in the accent instead.
    var pinImage = new mg.ImageBox("data:image/svg+xml," + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" '
      + 'width="9" height="9"><circle cx="4.5" cy="4.5" r="3.5" fill="#ffffff" stroke="' + accent + '" stroke-width="1.5"/>'
      + "</svg>"), 9, 9);
    mg.ConstraintHandler.prototype.getImageForConstraint = function () { return pinImage; };
    mg.HandleConfig.fillColor = "#ffffff";
    mg.HandleConfig.strokeColor = accent;
    mg.HandleConfig.size = 8;
    // Every change the person makes to the diagram's own, said once it is
    // made; the engine's own keeping in step is not one.
    model.addListener(mg.InternalEvent.CHANGE, function () {
      if (s.syncing || surface !== s) return;
      reroute(s);
      rehop(s);
      changed();
    });
    // A frame moved takes the records it was drawn round with it, as it
    // takes what of its own sits in it: each record wholly inside its box
    // before the move, and not one picked, which the drag moves itself.
    // The canvas moves them where it keeps them, once maxGraph's own change
    // has said itself as the step Undo takes back.
    graph.addListener(mg.InternalEvent.MOVE_CELLS, function (sender, evt) {
      if (s.syncing || surface !== s || !s.cy || s.readOnly || !Canvas.recordsMoved) return;
      var dx = evt.getProperty("dx") || 0, dy = evt.getProperty("dy") || 0;
      if (!dx && !dy) return;
      var held = [];
      (evt.getProperty("cells") || []).forEach(function (cell) {
        if (!cell.terraneOwn || cell.terraneOwn.role !== "frame" || !cell.geometry) return;
        var at = absolute(cell);
        held.push({ x1: at.x - dx, y1: at.y - dy, x2: at.x - dx + cell.geometry.width,
          y2: at.y - dy + cell.geometry.height });
      });
      if (!held.length) return;
      var picked = Canvas.pickedIds ? Canvas.pickedIds() : [];
      var ids = s.cy.nodes().filter(function (n) {
        if (n.isParent() || picked.indexOf(n.id()) !== -1) return false;
        var b = n.boundingBox({ includeLabels: false });
        return held.some(function (f) { return b.x1 >= f.x1 && b.y1 >= f.y1 && b.x2 <= f.x2 && b.y2 <= f.y2; });
      }).map(function (n) { return n.id(); });
      if (ids.length) window.setTimeout(function () { if (surface === s) Canvas.recordsMoved(ids, dx, dy); }, 0);
    });
    graph.getSelectionModel().addListener(mg.InternalEvent.CHANGE, function () {
      if (surface !== s || s.picking) return;
      // Whether the press that picked it held Shift, so the records picked
      // beside it stay picked.
      if (Canvas.ownSelected) Canvas.ownSelected(selected(), !!s.shiftPress);
    });
    s.div.addEventListener("dblclick", function (ev) {
      if (s.readOnly) return;
      var r = s.div.getBoundingClientRect();
      var cell = ownAt({ x: ev.clientX - r.left, y: ev.clientY - r.top });
      if (cell) { ev.preventDefault(); editText(cell); }
    });
  }

  // Cytoscape puts a model point at model * zoom + pan; maxGraph at
  // (model + translate) * scale.
  function syncView() {
    if (!surface || !surface.cy) return;
    var z = surface.cy.zoom(), p = surface.cy.pan();
    surface.graph.view.scaleAndTranslate(z, p.x / z, p.y / z);
    placeEditor();
  }

  function num(v, fallback) {
    var n = parseFloat(v);
    return isNaN(n) ? fallback : n;
  }

  /* ---- the estate, in step with Cytoscape
   * Every element becomes its parts -- a box, its name, its technology line
   * and its mark; a line and its label -- each a cell with an id of its
   * own. While the parts are the same parts in the same order, a render
   * moves and restyles the cells that changed and nothing else; a drawing
   * with other parts, which only a new drawing or a box shown or hidden
   * gives, is laid down again. */
  function paint() {
    var s = surface;
    if (!s || !s.cy || s.cy.destroyed()) return;
    var parts = estateParts(s.cy);
    var shape = parts.map(function (p) { return p.id; }).join("|");
    var laid = shape !== s.shape;
    quiet(function () {
      if (laid) {
        s.graph.removeCells(estateCells(s), false);
        s.cells = {};
        parts.forEach(function (p) { insertPart(s, p); });
        s.shape = shape;
      } else {
        parts.forEach(function (p) { updatePart(s, p); });
      }
    });
    // Laid down again, the estate's cells are new, and a line of the
    // diagram's own that ended on the old ones is joined to these; a
    // boundary moved may now hold a frame, or no longer.
    if (laid && s.drawnOwn) own(s.own, true);
    else restack();
    syncView();
    reroute(s);
    rehop(s);
    // The overview drew the drawing before this model held it, from
    // Cytoscape alone, and kept that; it is drawn again, once the diagram's
    // own (drawn after this, in the same task) is here too.
    if (laid) app.overviewStale();
  }

  function estateParts(cy) {
    var parts = [], techFont = app.TECH_FONT;
    // Boundaries first, outermost first, so what is in one is drawn over it.
    var nodes = cy.nodes().filter(function (n) { return n.visible(); }).sort(function (a, b) {
      return depth(a) - depth(b) || (b.isParent() ? 1 : 0) - (a.isParent() ? 1 : 0);
    });
    nodes.forEach(function (n) {
      var from = parts.length, d = depth(n);
      nodeParts(n, techFont, parts);
      for (var i = from; i < parts.length; i += 1) { parts[i].layer = n.isParent() ? "bounds" : "boxes"; parts[i].depth = d; }
    });
    cy.edges().forEach(function (e) {
      var from = parts.length;
      if (e.visible()) edgeParts(e, parts);
      for (var i = from; i < parts.length; i += 1) parts[i].layer = "boxes";
    });
    return parts;
  }

  function depth(n) {
    var d = 0, p = n.parent();
    while (p && p.nonempty()) { d += 1; p = p.parent(); }
    return d;
  }

  function opacityOf(el) {
    return Math.round(num(el.effectiveOpacity ? el.effectiveOpacity() : el.style("opacity"), 1) * 100);
  }

  function nodeParts(n, techFont, parts) {
    var border = num(n.style("border-width"), 1);
    // The drawn outline: the box and its padding, the border astride it, as
    // both libraries stroke an outline.
    var w = n.outerWidth() - border, h = n.outerHeight() - border, p = n.position();
    var x = p.x - w / 2, y = p.y - h / 2;
    if (!finite([{ x: x, y: y }, { x: w, y: h }])) return;
    var dash = n.style("border-style");
    var id = n.id();
    parts.push({ id: "n:" + id, node: id, vertex: true, geo: [x, y, w, h], value: "",
      style: Object.assign(shapeStyle(n.style("shape"), w, h), {
        fillColor: n.style("background-color"),
        fillOpacity: Math.round(num(n.style("background-opacity"), 1) * 100),
        strokeColor: border > 0 ? n.style("border-color") : "none",
        strokeWidth: border,
        dashed: dash === "dashed" || dash === "dotted",
        dashPattern: dash === "dotted" ? "1 3" : "6 4",
        opacity: opacityOf(n),
      }) });
    var name = String(n.data("label") || "");
    var group = !!n.data("isGroup");
    if (group) {
      if (name) parts.push(textPart(id + "#name", id, name, x + 12, y + 8, w - 24, 16, {
        fontSize: 11, fontStyle: 1, fontColor: n.style("color"), align: "left",
      }));
    } else if (name) {
      // Where Cytoscape sets the name: its label's box, a slot one font size
      // tall a line, the middle where the margins put it, each line on its
      // slot's "bottom". The cell's words start at the box's top, a line
      // height of one apart, moved by what the canvas's baseline and an
      // HTML line's differ by. Centered, at a line height of 1.05, every
      // name came out low, the last line most (names_probe.mjs).
      // The lines are Cytoscape's own, each set as it is, the space it
      // keeps at the end of a wrapped line included: Cytoscape centers
      // "Lending App " with its space, and HTML, which drops a wrapped
      // line's last space, set every such line half a space to the right.
      var size = num(n.style("font-size"), 12);
      var box = n.boundingBox({ includeNodes: false, includeEdges: false, includeLabels: true, includeOverlays: false });
      var wrapped = n._private && n._private.rscratch && n._private.rscratch.labelWrapCachedLines;
      var said = Array.isArray(wrapped) && wrapped.length ? wrapped : null;
      var lines = said ? said.length : Math.max(1, Math.round(box.h / size));
      var at = baselines(size, 600);
      var maxw = num(n.style("text-max-width"), w);
      parts.push(textPart(id + "#name", id, name, (box.x1 + box.x2) / 2 - maxw / 2,
        (box.y1 + box.y2) / 2 - lines * size / 2 + at.canvas - at.html, maxw, lines * size, said ? {
          fontSize: size, fontStyle: 1, fontColor: n.style("color"), leading: 1, lines: said,
          align: "center", verticalAlign: "top", whiteSpace: "nowrap",
        } : {
          fontSize: size, fontStyle: 1, fontColor: n.style("color"), leading: 1,
          // Wrapped at Cytoscape's text-max-width exactly: without "width"
          // the label wrapped wider, and "Installment Lending" kept a line.
          align: "center", verticalAlign: "top", whiteSpace: "wrap", overflow: "width",
        }));
    }
    // The technology line's baseline sits 5.5 above the box's foot, as
    // attachTechLayer paints it; the cell's top is one ascent above that.
    var tech = !group && n.data("tech");
    if (tech) parts.push(textPart(id + "#tech", id, String(tech), x + 5, y + h - 5.5 - techFont * 0.92, w - 10, techFont * 1.25, {
      fontSize: techFont, fontColor: "#5b6577", align: "center", verticalAlign: "top", whiteSpace: "nowrap",
    }));
    var mark = n.data("icon") || n.data("glyph") || n.data("ticon");
    if (mark) {
      // maxGraph, as mxGraph did, adds ";base64" to any image data URI that
      // lacks it, and the app's marks are "data:image/svg+xml;utf8,%3Csvg..."
      // made with encodeURIComponent: the result is no URL at all. The one
      // form it leaves alone is "data:image/svg+xml,%3C...", the same bytes.
      mark = String(mark).replace(/^data:image\/svg\+xml;(utf8|charset=utf-8),/, "data:image/svg+xml,");
      var size = group ? 20 : n.data("icon") ? 18 : n.data("glyph") ? 13 : 12;
      var ox = num(n.style("background-offset-x"), -4), oy = num(n.style("background-offset-y"), 4);
      parts.push({ id: "n:" + id + "#mark", node: id, vertex: true, geo: [x + w - size + ox, y + oy, size, size], value: "",
        style: { shape: "image", image: mark, opacity: opacityOf(n) } });
    }
  }

  /* Where a line's baseline falls below the top of its line, at a size and
   * a weight: as Cytoscape's canvas sets a name (each line a slot one font
   * size tall, on the slot's "bottom"), and as an HTML line one font size
   * tall does (half of what the face's ascent and descent exceed it by
   * above, then the ascent). Both are the browser's own numbers for the
   * face, which it rounds: at twelve, 9.28 and 10. Kept once the face has
   * loaded; before, the fallback's numbers would be kept for Geist's. */
  var baselineCache = {};
  function baselines(size, weight) {
    var key = size + "/" + weight;
    if (baselineCache[key]) return baselineCache[key];
    var c = document.createElement("canvas").getContext("2d");
    c.font = weight + " " + size + "px " + FACE;
    c.textBaseline = "bottom";
    var fromBottom = c.measureText("Hg").alphabeticBaseline;
    c.textBaseline = "alphabetic";
    var m = c.measureText("Hg");
    var out = { canvas: size - fromBottom, html: (size - m.fontBoundingBoxAscent - m.fontBoundingBoxDescent) / 2 + m.fontBoundingBoxAscent };
    if (!isFinite(out.canvas) || !isFinite(out.html)) out = { canvas: 0, html: 0 };
    else if (!document.fonts || document.fonts.check(weight + " " + size + "px Geist")) baselineCache[key] = out;
    return out;
  }

  function textPart(id, node, value, x, y, w, h, style) {
    var div = document.createElement("div");
    div.textContent = value;
    // Weight and leading in the label itself: maxGraph's bold is 700 and its
    // line height 1.2, where Cytoscape draws these names at 600 and 1.
    var weight = style.fontStyle === 1 ? 600 : 500;
    var inner = div.innerHTML;
    if (style.lines) {
      // Lines already broken, each kept whole and with its spaces.
      inner = style.lines.map(function (line) {
        div.textContent = line;
        return '<div style="white-space:pre">' + div.innerHTML + "</div>";
      }).join("");
    }
    var html = '<div style="font-weight:' + weight + ";line-height:" + (style.leading || 1.05) + '">' + inner + "</div>";
    style = Object.assign({}, style, { fontStyle: 0 });
    delete style.leading;
    delete style.lines;
    // maxGraph lays a wrapped HTML label out two pixels wider than its cell
    // (114 for 112), and "Installment Lending", 113 at this face, kept a line
    // Cytoscape breaks. The cell gives those two back.
    if (style.whiteSpace === "wrap") { x += 1; w -= 2; }
    // No spacing: maxGraph's default two pixels moved every name off
    // where Cytoscape centers it.
    return { id: "n:" + id, node: node, vertex: true, geo: [x, y, w, h], value: html,
      style: Object.assign({ shape: "label", fillColor: "none", strokeColor: "none", fontFamily: FACE,
        html: true, spacing: 0 }, style) };
  }

  function finite(points) {
    return points.every(function (q) { return q && isFinite(q.x) && isFinite(q.y); });
  }

  function edgeParts(e, parts) {
    var curve = e.style("curve-style");
    var src = e.sourceEndpoint(), tgt = e.targetEndpoint();
    var mid = (curve === "bezier" || curve === "unbundled-bezier") ? (e.controlPoints() || []) : (e.segmentPoints() || []);
    // Mid-gesture, while the boxes glide and the lines are routed again, a
    // line can have no ends for a frame, and maxGraph's Point throws on NaN
    // ("Invalid x supplied", four times in the arrange walk). That frame
    // keeps the line where it was; the next one draws it routed.
    var id = e.id(), ok = finite([src, tgt].concat(mid));
    var line = e.style("line-style");
    var arrow = e.style("target-arrow-shape");
    parts.push({ id: "e:" + id, vertex: false, ends: ok ? [src, tgt, mid] : null, value: "", style: {
      strokeColor: e.style("line-color"),
      strokeWidth: num(e.style("width"), 1.6),
      dashed: line === "dashed" || line === "dotted",
      dashPattern: line === "dotted" ? "1 3" : "6 4",
      endArrow: arrow && arrow !== "none" ? "block" : "none",
      endSize: 7,
      endFill: true,
      rounded: curve === "round-segments",
      curved: curve === "bezier",
      opacity: opacityOf(e),
    } });
    var shown = e.data("shown");
    if (shown && ok) {
      var m = e.midpoint();
      var lx = num(e.style("text-margin-x"), 0), ly = num(e.style("text-margin-y"), 0);
      var size = num(e.style("font-size"), 10);
      var tw = measure(String(shown), size) + 8, th = size + 6;
      var part = textPart(id + "#label", null, String(shown), m.x + lx - tw / 2, m.y + ly - th / 2, tw, th, {
        fontSize: size, fontColor: e.style("color"), align: "center", verticalAlign: "middle",
        fillColor: e.style("text-background-color"), strokeColor: e.style("text-border-color"), rounded: true,
        absoluteArcSize: true, arcSize: 6, opacity: opacityOf(e),
      });
      part.id = "e:" + id + "#label";
      parts.push(part);
    }
  }

  // A part's look, compared as a string: style objects are new each render.
  function said(style) { return JSON.stringify(style); }

  function insertPart(s, p) {
    var graph = s.graph, mg = s.mg, cell;
    var style = Object.assign({ editable: false, movable: false, resizable: false }, p.style);
    if (p.vertex) {
      cell = graph.insertVertex({ parent: s.layers[p.layer], id: p.id, value: p.value,
        position: [p.geo[0], p.geo[1]], size: [p.geo[2], p.geo[3]], style: style });
    } else {
      cell = graph.insertEdge({ parent: s.layers[p.layer], id: p.id, value: "", style: style });
      setEnds(s, cell, p.ends);
    }
    cell.terraneNode = p.node || null;
    cell.terraneDepth = p.depth || 0;
    cell.terraneSaid = said(style);
    cell.terraneEnds = p.ends ? said(p.ends) : "";
    s.cells[p.id] = cell;
  }

  function updatePart(s, p) {
    var cell = s.cells[p.id], model = s.model;
    if (!cell) return;
    var style = Object.assign({ editable: false, movable: false, resizable: false }, p.style);
    var look = said(style);
    if (look !== cell.terraneSaid) { model.setStyle(cell, style); cell.terraneSaid = look; }
    if (p.vertex) {
      var g = cell.geometry;
      if (g.x !== p.geo[0] || g.y !== p.geo[1] || g.width !== p.geo[2] || g.height !== p.geo[3]) {
        var ng = g.clone();
        ng.x = p.geo[0]; ng.y = p.geo[1]; ng.width = p.geo[2]; ng.height = p.geo[3];
        model.setGeometry(cell, ng);
      }
      if (cell.value !== p.value) model.setValue(cell, p.value);
    } else if (p.ends) {
      var ends = said(p.ends);
      if (ends !== cell.terraneEnds) { setEnds(s, cell, p.ends); cell.terraneEnds = ends; }
    }
  }

  function setEnds(s, cell, ends) {
    if (!ends) return;
    var mg = s.mg, g = cell.geometry.clone();
    g.setTerminalPoint(new mg.Point(ends[0].x, ends[0].y), true);
    g.setTerminalPoint(new mg.Point(ends[1].x, ends[1].y), false);
    g.points = ends[2].map(function (q) { return new mg.Point(q.x, q.y); });
    s.model.setGeometry(cell, g);
  }

  var measurer = null;
  function measure(value, size) {
    if (!measurer) measurer = document.createElement("canvas").getContext("2d");
    measurer.font = "500 " + size + "px " + FACE;
    return measurer.measureText(value).width;
  }

  /* ---- the diagram's own
   * Kept in the diagram's file as a list (canvas.js `annotations`): each
   * item a key that never changes, its role, its words, the frames it sits
   * in by key, its corner in the frame around it or on the sheet, and its
   * size; a line its two ends, each a record on the drawing, a key of the
   * file's own, or a point. The sheet's corner is where the drawing's
   * positions start, so a note beside a box stays beside it when the
   * diagram is drawn again. */

  // Where the drawing's positions start: the corner an arranged drawing is
  // laid from, or, for one the layout places, the least corner of its
  // boxes, as keepAll takes it the moment the drawing is first arranged --
  // taken once, when the diagram's own is drawn, so a box carried before
  // the drawing is arranged does not carry the shapes with it.
  function origin() {
    var s = surface, cy = s && s.cy;
    if (!cy || cy.destroyed()) return { x: 0, y: 0 };
    var frames = cy.scratch("_frames");
    if (frames && frames[""]) return frames[""];
    if (s.ownOrigin) return s.ownOrigin;
    var x = Infinity, y = Infinity;
    cy.nodes().forEach(function (n) {
      if (n.data("isGroup")) return;
      var p = n.position();
      x = Math.min(x, Math.round(p.x - n.width() / 2));
      y = Math.min(y, Math.round(p.y - n.height() / 2));
    });
    return isFinite(x) ? { x: x, y: y } : { x: 0, y: 0 };
  }

  function idOf(key) { return "a:" + key; }

  function held(v) { return Array.isArray(v) && v.length === 2 && typeof v[0] === "number" && typeof v[1] === "number"; }

  //: How far a square line held at a side of its box runs out from it
  //: before it turns: the router's margin (`_stub` in the picture).
  var PIN_OUT = 10;
  //: The points of a box a line's end can be held at, as shares of it:
  //: each side's quarters and middle; an ellipse's and a diamond's four
  //: middles, which are all of their outline a box's share can name.
  var PINS = [[0.25, 0], [0.5, 0], [0.75, 0], [1, 0.25], [1, 0.5], [1, 0.75], [0.75, 1], [0.5, 1], [0.25, 1],
    [0, 0.75], [0, 0.5], [0, 0.25]];
  var PINS_ROUND = [[0.5, 0], [1, 0.5], [0.5, 1], [0, 0.5]];

  // A straight line with bends: a square or curved one turns by itself.
  function bent(a) {
    return Array.isArray(a.via) && a.via.length > 0 && (!a.route || a.route === "straight");
  }

  /* The diagram's own drawn from its list, all of it, as the engine keeping
   * in step: on a new drawing, and for an Undo. Anything the list holds
   * that cannot be drawn -- a line whose record is not on the drawing now --
   * is kept as it is and written back with the rest. */
  function own(list, keepSelection) {
    var s = surface;
    if (!s) return;
    s.ownOrigin = null;
    var mg = s.mg, graph = s.graph, at = origin();
    s.ownOrigin = at;
    var keys = keepSelection ? selected() : [];
    closeEditor(true);
    list = Array.isArray(list) ? list : [];
    var byKey = {}, orphans = [], placed = [];
    quiet(function () {
      graph.removeCells(ownCells(s), true);
      var boxes = list.filter(function (a) { return a && a.role !== "line" && a.key; });
      // Outer frames before what is in them, whatever order the file has.
      boxes.sort(function (a, b) { return ((a.in || []).length) - ((b.in || []).length); });
      boxes.forEach(function (a) {
        var inside = (a.in || []).length ? byKey[a.in[a.in.length - 1]] : null;
        var parent = inside || (a.role === "frame" ? s.layers.under : s.layers.over);
        // A frame goes to the layer its place says once it is on the sheet.
        var p = a.at || [0, 0], z = a.size || DEFAULT_SIZE[a.role] || [120, 64];
        var x = Number(p[0]) + (inside ? 0 : at.x), y = Number(p[1]) + (inside ? 0 : at.y);
        var cell = graph.insertVertex({ parent: parent, id: idOf(a.key), value: a.label || "",
          position: [x, y], size: [Number(z[0]), Number(z[1])], style: ownStyle(a) });
        cell.terraneOwn = copy(a);
        byKey[a.key] = cell;
        placed.push(a.key);
      });
      list.filter(function (a) { return a && a.role === "line" && a.key; }).forEach(function (a) {
        var src = endCell(s, a.from, byKey), tgt = endCell(s, a.to, byKey);
        if (src === undefined || tgt === undefined) { orphans.push(copy(a)); return; }
        var edge = graph.insertEdge({ parent: s.layers.over, id: idOf(a.key), value: a.label || "",
          source: src, target: tgt, style: ownStyle(a) });
        var g = edge.geometry.clone();
        if (!src) g.setTerminalPoint(new mg.Point(Number(a.from[0]) + at.x, Number(a.from[1]) + at.y), true);
        if (!tgt) g.setTerminalPoint(new mg.Point(Number(a.to[0]) + at.x, Number(a.to[1]) + at.y), false);
        if (bent(a)) g.points = a.via.map(function (p) { return new mg.Point(Number(p[0]) + at.x, Number(p[1]) + at.y); });
        s.model.setGeometry(edge, g);
        edge.terraneOwn = copy(a);
        byKey[a.key] = edge;
        placed.push(a.key);
      });
      // As tiles, the lines go under the shapes, as the clouds draw them:
      // a line leaving a tile downward runs under its words.
      if (LOOK === "tiles") {
        graph.orderCells(true, list.filter(function (a) { return a && a.role === "line" && byKey[a.key]; })
          .map(function (a) { return byKey[a.key]; }));
      }
    });
    s.orphans = orphans;
    restack();
    s.own = serialize();
    s.drawnOwn = true;
    if (keys.length) select(keys.filter(function (k) { return placed.indexOf(k) !== -1; }));
  }

  /* A frame on the sheet is stacked by what holds it: inside a boundary,
   * among the boundaries just above the innermost that holds it and under
   * the ones inside it, so a frame drawn in an account is not hidden by the
   * account, nor a zone by a frame drawn round it; inside none -- on the
   * bare sheet, or around boundaries -- under all of the estate.
   * terrane.draw.annotations stacks the picture by the same rule. */
  function holderDepth(s, box) {
    var d = -1;
    s.layers.bounds.getChildren().forEach(function (c) {
      if (c.terraneOwn || !c.id || c.id.indexOf("#") !== -1 || !c.geometry) return;
      var g = c.geometry;
      if (box.x >= g.x && box.y >= g.y && box.x + box.width <= g.x + g.width && box.y + box.height <= g.y + g.height) {
        d = Math.max(d, c.terraneDepth);
      }
    });
    return d;
  }

  function restack() {
    var s = surface;
    if (!s) return;
    var frames = ownCells(s).filter(function (c) { return c.terraneOwn.role === "frame" && c.geometry && c.isVertex(); });
    var moves = [];
    frames.forEach(function (c) {
      var d = holderDepth(s, c.geometry);
      c.terraneHeld = d;
      if (d < 0) { if (c.parent !== s.layers.under) moves.push([c, s.layers.under, undefined]); return; }
      // Its place among the boundaries, the frame itself left out: after
      // every boundary, and every frame, held no deeper than it is.
      var rest = s.layers.bounds.getChildren().filter(function (o) { return o !== c; }), at = 0;
      rest.forEach(function (o, i) {
        var level = o.terraneOwn ? (o.terraneHeld === undefined ? -1 : o.terraneHeld) : o.terraneDepth;
        if (level <= d) at = i + 1;
      });
      if (c.parent !== s.layers.bounds || s.layers.bounds.getChildren().indexOf(c) !== at) moves.push([c, s.layers.bounds, at]);
    });
    if (!moves.length) return;
    var keys = selected();
    quiet(function () { moves.forEach(function (m) { s.model.add(m[1], m[0], m[2]); }); });
    if (keys.length) { s.picking = true; try { select(keys); } finally { s.picking = false; } }
  }

  // A line's end: a cell of the file's own by key, a record's box on the
  // drawing by id, null for a point, undefined for a record not drawn.
  function endCell(s, end, byKey) {
    if (Array.isArray(end)) return null;
    if (byKey[end]) return byKey[end];
    var box = s.cells["n:" + end];
    return box || undefined;
  }

  function copy(v) { return JSON.parse(JSON.stringify(v)); }

  /* The diagram's own as the file will say it: walked from the model, so
   * where a person left each thing is what is written. */
  function serialize() {
    var s = surface, at = origin(), out = [];
    function round(v) { return Math.round(v); }
    function walk(parent, path) {
      parent.getChildren().forEach(function (c) {
        if (!c.terraneOwn) return;
        var a = c.terraneOwn, item = { key: a.key, role: a.role };
        if (a.shape && a.role === "shape") item.shape = a.shape;
        var label = String(c.value || "");
        if (label) item.label = label;
        if (c.isVertex()) {
          var g = c.geometry, top = !path.length;
          if (!top) item.in = path.slice();
          item.at = [round(g.x - (top ? at.x : 0)), round(g.y - (top ? at.y : 0))];
          item.size = [round(g.width), round(g.height)];
          // maxGraph's handle turns the cell's style; the item keeps it,
          // whole degrees, a half turn either way.
          var turn = Math.round(Number(c.style && c.style.rotation) || 0) % 360;
          if (turn > 180) turn -= 360;
          if (turn <= -180) turn += 360;
          if (turn && TURNS[a.role]) { a.rotate = turn; item.rotate = turn; } else delete a.rotate;
        } else {
          item.from = endOf(c, true, at);
          item.to = endOf(c, false, at);
          if (a.ends && a.ends !== "end") item.ends = a.ends;
          if (a.route && a.route !== "straight") item.route = a.route;
          // Where maxGraph holds each end on its box, if it does: a share of
          // the box, to the hundredth.
          [["from_at", true, "exitX", "exitY"], ["to_at", false, "entryX", "entryY"]].forEach(function (e) {
            var fx = c.style && c.style[e[2]], fy = c.style && c.style[e[3]];
            if (c.getTerminal(e[1]) && typeof fx === "number" && typeof fy === "number") {
              item[e[0]] = [Math.round(fx * 100) / 100, Math.round(fy * 100) / 100];
              a[e[0]] = item[e[0]];
            } else delete a[e[0]];
          });
          // Where maxGraph's handles bent it, from the sheet's corner.
          var bends = (c.geometry.points || []).filter(Boolean);
          if (bends.length && (!a.route || a.route === "straight")) {
            item.via = bends.map(function (p) { return [round(p.x - at.x), round(p.y - at.y)]; });
            a.via = item.via;
          } else delete a.via;
        }
        if (a.look && Object.keys(a.look).length) item.look = copy(a.look);
        out.push(item);
        if (c.isVertex()) walk(c, path.concat([a.key]));
      });
    }
    walk(s.layers.under, []);
    walk(s.layers.bounds, []);
    walk(s.layers.over, []);
    return out.concat(s.orphans);
  }

  function endOf(edge, source, at) {
    var t = edge.getTerminal(source);
    if (t && t.terraneOwn) return t.terraneOwn.key;
    if (t && t.terraneNode) return t.terraneNode;
    var p = edge.geometry.getTerminalPoint(source) || { x: 0, y: 0 };
    return [Math.round(p.x - at.x), Math.round(p.y - at.y)];
  }

  /* Said again from the corner the drawing is laid from now, which keepAll
   * has just taken: nothing moves on the sheet. */
  function rebase() {
    var s = surface;
    if (!s) return [];
    s.own = serialize();
    return copy(s.own);
  }

  // Each a little below and right of the one it copies, in the same frame,
  // all of them one step for Undo; the copies are selected.
  function copyOwn(keys) {
    var s = surface;
    if (!s) return [];
    var made = [];
    s.graph.batchUpdate(function () {
      keys.forEach(function (k) {
        var cell = s.model.getCell(idOf(k));
        if (!cell || !cell.isVertex()) return;
        var a = copy(cell.terraneOwn), o = absolute(cell);
        delete a.key;
        delete a.in;
        a.label = String(cell.value || "");
        a.box = { x: o.x + 16, y: o.y + 16, w: cell.geometry.width, h: cell.geometry.height };
        made.push(add(a, cell.parent && cell.parent.terraneOwn ? cell.parent.terraneOwn.key : null));
      });
    });
    select(made);
    return made;
  }

  /* What is picked as a clipping another diagram can take: each shape at
   * its place on the sheet, with what sits in a frame that is picked, and
   * each line among them, a picked line's ends kept as they are and a
   * point end said as a point of the sheet. */
  function clipOwn(keys) {
    var s = surface;
    if (!s) return null;
    var taken = {}, cells = [];
    function take(cell) {
      if (!cell || !cell.terraneOwn || taken[cell.terraneOwn.key]) return;
      taken[cell.terraneOwn.key] = true;
      cells.push(cell);
      for (var i = 0; i < cell.getChildCount(); i += 1) take(cell.getChildAt(i));
    }
    keys.forEach(function (k) { take(s.model.getCell(idOf(k))); });
    var sheet = origin(), items = [];
    cells.forEach(function (cell) {
      var a = copy(cell.terraneOwn);
      a.label = String(cell.value || "");
      if (cell.isVertex()) {
        var o = absolute(cell);
        a.box = { x: o.x, y: o.y, w: cell.geometry.width, h: cell.geometry.height };
        a.within = cell.parent && cell.parent.terraneOwn && taken[cell.parent.terraneOwn.key]
          ? cell.parent.terraneOwn.key : null;
        delete a.in;
      } else {
        // A point end, from the drawing's corner, as a point of the sheet.
        ["from", "to"].forEach(function (end) {
          if (Array.isArray(a[end])) a[end] = { x: sheet.x + a[end][0], y: sheet.y + a[end][1] };
        });
        if (Array.isArray(a.via)) a.via = a.via.map(function (p) { return { x: sheet.x + p[0], y: sheet.y + p[1] }; });
      }
      delete a.at;
      delete a.size;
      items.push(a);
    });
    return items;
  }

  /* A clipping drawn on this diagram, `dx` and `dy` from where it was:
   * frames before what sits in them, then the rest, then the lines, each
   * with a new key; a line keeps an end on a record this diagram draws or
   * on what came with it, and a line with an end on neither is left out.
   * One step for Undo; what was drawn is picked. */
  function pasteOwn(items, dx, dy) {
    var s = surface;
    if (!s || !items || !items.length) return [];
    var sheet = origin(), keys = {}, made = [];
    var drawn = function (id) { return !!(s.cells && s.cells["n:" + id]); };
    var boxes = items.filter(function (a) { return a.role !== "line"; });
    var ordered = [], placed = {};
    while (ordered.length < boxes.length) {
      var before = ordered.length;
      boxes.forEach(function (a) {
        if (placed[a.key] || (a.within && !placed[a.within] && boxes.some(function (b) { return b.key === a.within; }))) return;
        placed[a.key] = true;
        ordered.push(a);
      });
      if (ordered.length === before) break;
    }
    s.graph.batchUpdate(function () {
      ordered.forEach(function (a) {
        var spec = copy(a);
        delete spec.key;
        delete spec.within;
        spec.box = { x: a.box.x + dx, y: a.box.y + dy, w: a.box.w, h: a.box.h };
        var key = add(spec, a.within ? keys[a.within] : null);
        keys[a.key] = key;
        made.push(key);
      });
      items.forEach(function (a) {
        if (a.role !== "line") return;
        var spec = copy(a), ok = true;
        delete spec.key;
        ["from", "to"].forEach(function (end) {
          var v = a[end];
          if (v && typeof v === "object" && !Array.isArray(v)) {
            var p = { x: v.x + dx, y: v.y + dy };
            spec[end] = [Math.round(p.x - sheet.x), Math.round(p.y - sheet.y)];
            spec[end + "At"] = p;
          } else if (keys[v]) spec[end] = keys[v];
          else if (!drawn(v)) ok = false;
        });
        if (Array.isArray(a.via)) {
          spec.via = a.via.map(function (p) { return [Math.round(p.x + dx - sheet.x), Math.round(p.y + dy - sheet.y)]; });
        }
        if (!ok) return;
        made.push(add(spec));
      });
    });
    select(made);
    return made;
  }

  function changed() {
    var s = surface;
    if (!s) return;
    // A frame moved into or out of a boundary goes on it or under it; that
    // is the engine's own keeping in step, after the person's change.
    if (!s.restacking) {
      s.restacking = true;
      window.setTimeout(function () { s.restacking = false; if (surface === s) restack(); }, 0);
    }
    s.own = serialize();
    if (Canvas.ownChanged) Canvas.ownChanged(copy(s.own));
    // The overview is drawn from this model too, and was kept as it was.
    app.overviewStale();
  }

  function selected() {
    var s = surface;
    if (!s) return [];
    return s.graph.getSelectionCells().filter(function (c) { return c.terraneOwn; })
      .map(function (c) { return c.terraneOwn.key; });
  }

  function select(keys) {
    var s = surface;
    if (!s) return;
    var cells = (keys || []).map(function (k) { return s.model.getCell(idOf(k)); }).filter(Boolean);
    s.graph.setSelectionCells(cells);
  }

  function item(key) {
    var s = surface;
    var cell = s && s.model.getCell(idOf(key));
    if (!cell || !cell.terraneOwn) return null;
    return copy(s.own.filter(function (a) { return a.key === key; })[0] || cell.terraneOwn);
  }

  // A change from the panel: its words, its look, its shape or its ends.
  function update(key, patch) {
    var s = surface;
    var cell = s && s.model.getCell(idOf(key));
    if (!cell) return;
    var a = cell.terraneOwn;
    s.graph.batchUpdate(function () {
      if (patch.label !== undefined && patch.label !== cell.value) s.model.setValue(cell, patch.label);
      if (patch.look) a.look = Object.assign({}, a.look || {}, patch.look);
      if (patch.look) Object.keys(a.look).forEach(function (k) { if (a.look[k] == null) delete a.look[k]; });
      if (patch.shape) a.shape = patch.shape;
      if (patch.ends) a.ends = patch.ends;
      if (patch.route) a.route = patch.route;
      // Its bends taken out, or a line made square or curved, which turns
      // by itself.
      if (patch.via === null || (patch.route && patch.route !== "straight")) {
        var bare = cell.geometry.clone();
        bare.points = [];
        s.model.setGeometry(cell, bare);
        delete a.via;
      }
      if (patch.rotate !== undefined) { if (patch.rotate) a.rotate = patch.rotate; else delete a.rotate; }
      // Its size, typed in the Arrange tab, as a corner dragged would set it,
      // held to what the sheet can draw: a box 150200 wide, a width typed
      // onto the one there, made the overview's canvas too big to paint.
      if (patch.size && cell.isVertex()) {
        var sized = cell.geometry.clone();
        sized.width = Math.min(MOST_SIZE, Math.max(8, Math.round(Number(patch.size[0]) || sized.width)));
        sized.height = Math.min(MOST_SIZE, Math.max(8, Math.round(Number(patch.size[1]) || sized.height)));
        s.model.setGeometry(cell, sized);
      }
      if (patch.look || patch.shape || patch.ends || patch.route || patch.rotate !== undefined) {
        s.model.setStyle(cell, ownStyle(a));
        // As tiles, what a frame holds sets its words on the frame's fill.
        if (LOOK === "tiles" && a.role === "frame" && patch.look) s.graph.refresh(cell);
      }
    });
  }

  function remove(keys) {
    var s = surface;
    if (!s) return;
    var cells = keys.map(function (k) { return s.model.getCell(idOf(k)); }).filter(Boolean);
    if (cells.length) s.graph.removeCells(cells, true);
  }

  // Brought forward or sent back among what shares its frame or layer.
  // Several changes as one step, for Undo: a look painted onto several.
  function together(fn) {
    var s = surface;
    if (s) s.graph.batchUpdate(fn); else fn();
  }

  function order(keys, back) {
    var s = surface;
    var cells = keys.map(function (k) { return s.model.getCell(idOf(k)); }).filter(Boolean);
    if (cells.length) s.graph.orderCells(!!back, cells);
  }

  function nudge(keys, dx, dy) {
    var s = surface;
    var cells = keys.map(function (k) { return s.model.getCell(idOf(k)); }).filter(Boolean);
    if (cells.length) s.graph.moveCells(cells, dx, dy, false);
  }

  function freeKey(role) {
    var s = surface, used = {};
    s.own.concat(s.orphans).forEach(function (a) { used[a.key] = true; });
    for (var n = 1; ; n += 1) if (!used[role + "-" + n]) return role + "-" + n;
  }

  /* A new item of the diagram's own, by a tool or a copy: put in the model
   * as the person's change, selected. `within` is a frame's key. */
  function add(spec, within) {
    var s = surface;
    if (!s) return null;
    var mg = s.mg, graph = s.graph, a = copy(spec), cell;
    a.key = a.key && !s.model.getCell(idOf(a.key)) ? a.key : freeKey(a.role);
    var frame = within ? s.model.getCell(idOf(within)) : null;
    graph.batchUpdate(function () {
      if (a.role === "line") {
        var src = endCell(s, a.from, {}), tgt = endCell(s, a.to, {});
        if (!Array.isArray(a.from) && src === undefined) src = s.model.getCell(idOf(a.from)) || null;
        if (!Array.isArray(a.to) && tgt === undefined) tgt = s.model.getCell(idOf(a.to)) || null;
        // An end it can hold, a box or a point: a cell left half made broke
        // the frames' stacking that runs once the change is done.
        if ((!src && !a.fromAt) || (!tgt && !a.toAt)) return;
        cell = graph.insertEdge({ parent: s.layers.over, id: idOf(a.key), value: a.label || "",
          source: src || null, target: tgt || null, style: ownStyle(a) });
        var g = cell.geometry.clone();
        if (!src) g.setTerminalPoint(new mg.Point(a.fromAt.x, a.fromAt.y), true);
        if (!tgt) g.setTerminalPoint(new mg.Point(a.toAt.x, a.toAt.y), false);
        if (bent(a)) {
          var o0 = origin();
          g.points = a.via.map(function (p) { return new mg.Point(o0.x + Number(p[0]), o0.y + Number(p[1])); });
        }
        s.model.setGeometry(cell, g);
        delete a.fromAt;
        delete a.toAt;
      } else {
        var parent = frame || (a.role === "frame" ? s.layers.under : s.layers.over);
        var x = a.box.x, y = a.box.y;
        if (frame) {
          var o = absolute(frame);
          x -= o.x;
          y -= o.y;
        }
        cell = graph.insertVertex({ parent: parent, id: idOf(a.key), value: a.label || "",
          position: [x, y], size: [a.box.w, a.box.h], style: ownStyle(a) });
        delete a.box;
      }
      cell.terraneOwn = a;
    });
    if (!cell) return null;
    graph.setSelectionCell(cell);
    return a.key;
  }

  // A cell's corner on the sheet, whatever frames it sits in.
  function absolute(cell) {
    var x = 0, y = 0;
    for (var c = cell; c && c.geometry && c.terraneOwn; c = c.parent) { x += c.geometry.x; y += c.geometry.y; }
    return { x: x, y: y };
  }

  // Where an item of the diagram's own is on the page, its middle, for a
  // menu that asks about it.
  function where(key) {
    var s = surface;
    var cell = s && s.model.getCell(idOf(key));
    var st = cell && s.graph.view.getState(cell);
    if (!st) return null;
    var r = s.div.getBoundingClientRect(), pts = st.absolutePoints;
    if (!cell.isVertex() && pts && pts.length) {
      var a = pts[0], b = pts[pts.length - 1];
      return { x: r.left + (a.x + b.x) / 2, y: r.top + (a.y + b.y) / 2 };
    }
    return { x: r.left + st.x + st.width / 2, y: r.top + st.y + st.height / 2 };
  }

  // Everything the diagram's own takes up, on the sheet, for a fit.
  function extent() {
    var s = surface;
    if (!s) return null;
    var box = null;
    [ownCells(s)].forEach(function (list) {
      list.forEach(function (c) {
        var st = s.graph.view.getState(c);
        if (!st) return;
        var scale = s.graph.view.scale, t = s.graph.view.translate;
        var b = { x1: st.x / scale - t.x, y1: st.y / scale - t.y, x2: (st.x + st.width) / scale - t.x, y2: (st.y + st.height) / scale - t.y };
        box = box ? { x1: Math.min(box.x1, b.x1), y1: Math.min(box.y1, b.y1), x2: Math.max(box.x2, b.x2), y2: Math.max(box.y2, b.y2) } : b;
      });
    });
    return box;
  }

  // A bounding box with the diagram's own around it, as Cytoscape gives one.
  function around(bb) {
    var o = extent();
    var real = bb && isFinite(bb.x1) && isFinite(bb.x2) && bb.w > 0;
    if (!o) return bb;
    var out = real ? { x1: Math.min(bb.x1, o.x1), y1: Math.min(bb.y1, o.y1), x2: Math.max(bb.x2, o.x2), y2: Math.max(bb.y2, o.y2) } : o;
    out.w = out.x2 - out.x1;
    out.h = out.y2 - out.y1;
    return out;
  }

  /* ---- the words, typed where they are drawn
   * A plain text box laid over the cell, outside maxGraph's container so a
   * press in it is not a press on the sheet. Plain text in, plain text out:
   * the HTML editor gave back no-break spaces for typed ones. */
  function editText(cell) {
    var s = surface;
    if (!s || !cell || !cell.terraneOwn) return;
    closeEditor(true);
    var box = document.createElement("textarea");
    box.className = "mg-edit is-" + cell.terraneOwn.role;
    box.value = String(cell.value || "");
    box.setAttribute("aria-label", "Words");
    s.div.parentNode.appendChild(box);
    s.edit = { cell: cell, box: box, was: box.value };
    placeEditor();
    box.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") { ev.preventDefault(); ev.stopPropagation(); closeEditor(false); }
      else if (ev.key === "Enter" && (ev.ctrlKey || ev.metaKey || cell.terraneOwn.role === "line")) {
        ev.preventDefault();
        closeEditor(true);
      }
      ev.stopPropagation();
    });
    box.addEventListener("blur", function () { closeEditor(true); });
    box.focus();
    box.select();
  }

  function placeEditor() {
    var s = surface;
    if (!s || !s.edit) return;
    var st = s.graph.view.getState(s.edit.cell), box = s.edit.box;
    if (!st) return;
    var scale = s.graph.view.scale, line = !s.edit.cell.isVertex();
    var x = st.x, y = st.y, w = st.width, h = st.height;
    if (line) {
      var m = st.absolutePoints && st.absolutePoints.length
        ? { x: (st.absolutePoints[0].x + st.absolutePoints[st.absolutePoints.length - 1].x) / 2,
            y: (st.absolutePoints[0].y + st.absolutePoints[st.absolutePoints.length - 1].y) / 2 } : { x: x, y: y };
      w = 160 * scale; h = 28 * scale; x = m.x - w / 2; y = m.y - h / 2;
    }
    var style = ownStyle(s.edit.cell.terraneOwn);
    box.style.left = (s.div.offsetLeft + x) + "px";
    box.style.top = (s.div.offsetTop + y) + "px";
    box.style.width = Math.max(40, w) + "px";
    box.style.height = Math.max(24, h) + "px";
    box.style.fontSize = (style.fontSize * scale) + "px";
    box.style.textAlign = style.align === "center" || line ? "center" : "left";
    box.style.padding = ((style.spacing || 2) * scale) + "px";
  }

  function closeEditor(keep) {
    var s = surface;
    if (!s || !s.edit) return;
    var e = s.edit;
    s.edit = null;
    if (e.box.parentNode) e.box.parentNode.removeChild(e.box);
    var text = e.box.value.replace(/ /g, " ").replace(/\s+$/, "");
    if (keep && text !== e.was && e.cell.parent) s.model.setValue(e.cell, text);
  }

  /* ---- the pointer
   * A press on the diagram's own is maxGraph's: it selects, moves, resizes
   * and drops into a frame. Everything else is answered here as it always
   * was, each gesture the event the canvas has always handled, on the
   * record the cell was drawn for: a press on a box is Cytoscape's "grab",
   * moving it is "drag" with the box carried that far, letting go is
   * "free", and a press that never moved past Cytoscape's own four pixels
   * is "tap"; pressing the sheet and moving pans it, hovering a box is
   * "mouseover" and "mouseout". The canvas's own code (canvas.js and the
   * app's drop handlers) is unchanged and cannot tell. The wheel is handed
   * to Cytoscape's own handler, which tells a mouse's notches from a
   * trackpad's glide and owns the viewport while the layout is still
   * Cytoscape's. With a drawing tool chosen, a press draws instead. */
  var TAP = 4;

  function ownAt(p) {
    var s = surface;
    var cell = s.graph.getCellAt(p.x, p.y, null, true, true);
    return cell && cell.terraneOwn ? cell : null;
  }

  // The frame a point on the sheet is in, innermost first: where a tool
  // drawing there puts what it draws.
  function frameAt(p) {
    var s = surface, skip = function (st) { return !st.cell.terraneOwn || st.cell.terraneOwn.role !== "frame"; };
    return s.graph.getCellAt(p.x, p.y, s.layers.bounds, true, false, skip)
      || s.graph.getCellAt(p.x, p.y, s.layers.under, true, false, skip) || null;
  }

  //: How near the edge of a boundary or a frame, in pixels on the screen,
  //: a press picks it up; and the strip its name sits in, at full size.
  var EDGE = 12, NAME = 26;

  function nearEdge(st, p) {
    if (!st) return true;
    var top = Math.max(EDGE, NAME * surface.graph.view.scale);
    return p.x - st.x < EDGE || st.x + st.width - p.x < EDGE || p.y - st.y < top || st.y + st.height - p.y < EDGE;
  }

  function onFrameEdge(cell, p) { return nearEdge(surface.graph.view.getState(cell), p); }

  function toModel(p) {
    var v = surface.graph.view;
    return { x: p.x / v.scale - v.translate.x, y: p.y / v.scale - v.translate.y };
  }

  function takePointer(s) {
    var div = s.div, press = null, hovered = null;
    div.classList.add("takes-pointer");
    // Space held is the hand for as long as it is held, as in every drawing
    // tool; not while something is being typed.
    function typing() {
      var t = document.activeElement;
      return !!t && (/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName) || t.isContentEditable);
    }
    s.onSpace = function (ev) {
      if (ev.key !== " " || typing() || surface !== s) return;
      var down = ev.type === "keydown";
      if (down) ev.preventDefault();
      if (s.spaceDown === down) return;
      s.spaceDown = down;
      div.classList.toggle("is-panning", down || s.tool === "pan");
    };
    document.addEventListener("keydown", s.onSpace);
    document.addEventListener("keyup", s.onSpace);
    // Where a press is, before maxGraph hears it: whether a frame is
    // picked up by it depends on where on the frame it lands (behave).
    div.addEventListener("pointerdown", function (ev) { s.pressAt = at(ev); }, true);
    function cy() { return s.cy && !s.cy.destroyed() ? s.cy : null; }
    function at(ev) {
      var r = div.getBoundingClientRect();
      return { x: ev.clientX - r.left, y: ev.clientY - r.top };
    }
    // The topmost cell drawn for a node, its name and mark included; lines
    // and their labels are not something the canvas picks up.
    function nodeAt(p) {
      var c = cy();
      if (!c) return null;
      var cell = s.graph.getCellAt(p.x, p.y, null, true, false, function (state) { return !state.cell.terraneNode; });
      var n = cell && cell.terraneNode ? c.getElementById(cell.terraneNode) : null;
      return n && n.nonempty() ? n : null;
    }
    function onEdge(n, p) { return nearEdge(s.graph.view.getState(s.cells["n:" + n.id()]), p); }
    function hover(n) {
      if (n === hovered || (n && hovered && n.same(hovered))) return;
      if (hovered && !hovered.removed()) hovered.emit("mouseout");
      hovered = n;
      if (n) n.emit("mouseover");
    }
    /* Quick connect (V14): four arrows about a hovered box, a record or a
     * shape, note or text of the diagram's own. Pressed, one draws the next
     * box that way, joined to this one by a line; carried, it draws a line
     * to the box it is let go on, or the next box there (quickNext). */
    var qc = { set: null, of: null, rect: null };
    function qcOf(p) {
      if (s.tool || s.readOnly || s.spaceDown || s.edit || !cy()) return null;
      var mine = ownAt(p);
      if (mine) return mine.isVertex() && QUICK[mine.terraneOwn.role] ? { key: mine.terraneOwn.key, cell: mine } : null;
      var n = nodeAt(p);
      if (!n || n.isParent() || n.data("isGroup")) return null;
      return { id: n.id(), cell: s.cells["n:" + n.id()] };
    }
    function qcHide() {
      if (qc.set) qc.set.hidden = true;
      qc.of = null;
      qc.rect = null;
    }
    function qcShow(of) {
      var st = of.cell && s.graph.view.getState(of.cell);
      if (!st) { qcHide(); return; }
      if (!qc.set) {
        qc.set = document.createElement("div");
        qc.set.className = "mg-qc-set";
        ["n", "e", "s", "w"].forEach(function (dir) {
          var b = document.createElement("button");
          b.type = "button";
          b.className = "mg-qc is-" + dir;
          b.dataset.dir = dir;
          b.title = QUICK_WORDS[dir];
          b.setAttribute("aria-label", QUICK_WORDS[dir]);
          b.innerHTML = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 12.5V3.5M4.5 7 8 3.5 11.5 7"/></svg>';
          b.addEventListener("pointerdown", function (ev) { qcPress(ev, dir); });
          qc.set.appendChild(b);
        });
        div.appendChild(qc.set);
      }
      var r = { x: st.x, y: st.y, w: st.width, h: st.height };
      qc.of = of;
      qc.rect = r;
      qc.set.hidden = false;
      var place = { n: [r.x + r.w / 2, r.y - QUICK_OUT], e: [r.x + r.w + QUICK_OUT, r.y + r.h / 2],
        s: [r.x + r.w / 2, r.y + r.h + QUICK_OUT], w: [r.x - QUICK_OUT, r.y + r.h / 2] };
      Array.prototype.forEach.call(qc.set.children, function (b) {
        b.style.left = place[b.dataset.dir][0] + "px";
        b.style.top = place[b.dataset.dir][1] + "px";
      });
    }
    // Within reach of its arrows, the box keeps them: the pointer has to
    // leave the box to get to one.
    function qcHover(p) {
      var of = qcOf(p), r = qc.rect, m = QUICK_OUT + 14;
      if (of) {
        if (!qc.of || (qc.of.key || qc.of.id) !== (of.key || of.id)) qcShow(of);
        return;
      }
      if (!r || p.x < r.x - m || p.x > r.x + r.w + m || p.y < r.y - m || p.y > r.y + r.h + m) qcHide();
    }
    function qcPress(ev, dir) {
      if (ev.button !== 0 || !qc.of) return;
      // maxGraph and the sheet's own press are not told: this press is the arrow's.
      ev.stopPropagation();
      ev.preventDefault();
      var r = qc.rect, of = qc.of;
      var start = { n: { x: r.x + r.w / 2, y: r.y }, e: { x: r.x + r.w, y: r.y + r.h / 2 },
        s: { x: r.x + r.w / 2, y: r.y + r.h }, w: { x: r.x, y: r.y + r.h / 2 } }[dir];
      qcHide();
      hover(null);
      var ghost = document.createElement("div");
      ghost.className = "mg-ghost is-line";
      div.appendChild(ghost);
      s.linking = { of: of, dir: dir, start: start, press: at(ev), ghost: ghost };
      div.setPointerCapture(ev.pointerId);
    }
    function linkTo(p) {
      var l = s.linking, dx = p.x - l.start.x, dy = p.y - l.start.y, g = l.ghost;
      g.style.left = l.start.x + "px";
      g.style.top = l.start.y + "px";
      g.style.width = Math.hypot(dx, dy) + "px";
      g.style.transform = "rotate(" + Math.atan2(dy, dx) + "rad)";
    }
    function linkEnd(p, kept) {
      var l = s.linking;
      s.linking = null;
      if (l.ghost.parentNode) l.ghost.parentNode.removeChild(l.ghost);
      if (!kept) return;
      if (Math.hypot(p.x - l.press.x, p.y - l.press.y) < TAP) { quickNext(l.of, l.dir, null); return; }
      var from = l.of.key || l.of.id, to = endAt(s, p), toRef = to ? to.key || to.record : null;
      if (toRef === from) return;
      if (!toRef) { quickNext(l.of, l.dir, p); return; }
      var key = add({ role: "line", from: from, to: toRef });
      if (Canvas.ownDrawn) Canvas.ownDrawn(key, "line");
    }
    div.addEventListener("pointerdown", function (ev) {
      if ((ev.button !== 0 && ev.button !== 1) || !cy()) return;
      qcHide();
      var p = at(ev);
      // A press on the sheet takes the keys from the panel, so Delete
      // deletes what is selected rather than a letter typed there.
      s.host.focus({ preventScroll: true });
      s.shiftPress = ev.shiftKey;
      // The hand: the Hand tool, Space held, or the middle button, which
      // pans from wherever it is pressed, over a box or not.
      if (s.tool === "pan" || s.spaceDown || ev.button === 1) {
        press = { start: p, last: p, pan: true, moved: false };
        div.setPointerCapture(ev.pointerId);
        div.classList.add("is-grabbing");
        ev.preventDefault();
        return;
      }
      if (s.tool) { startDrawing(s, p, ev); return; }
      // On a drawing only read, the diagram's own shapes are pictures, and
      // a press on one is a press on the sheet. A frame not yet picked,
      // pressed inside, is sheet to drag across, and a click there picks it.
      var mineAt = !s.readOnly ? ownAt(p) : null;
      if (mineAt && !(mineAt.terraneOwn.role === "frame" && !s.graph.isCellSelected(mineAt) && !onFrameEdge(mineAt, p))) {
        hover(null);
        return;
      }
      if (mineAt) {
        press = { start: p, last: p, node: null, frame: mineAt, moved: false, grabbed: false, shift: ev.shiftKey, marquee: true };
        div.setPointerCapture(ev.pointerId);
        ev.preventDefault();
        return;
      }
      var n = nodeAt(p);
      // On the canvas, the bare sheet dragged picks what the drag goes
      // around; on a drawing only read, it pans, as it always did. A
      // boundary is picked up by its edge or its name, and its inside is
      // sheet to drag across: the account around a whole drawing would
      // otherwise leave nowhere to start. A click inside it still selects it.
      var inside = !!n && n.isParent() && !s.readOnly && !onEdge(n, p);
      press = { start: p, last: p, node: n, moved: false, grabbed: !inside && !!(n && n.grabbable()), shift: ev.shiftKey,
        marquee: (!n || inside) && !s.readOnly };
      div.setPointerCapture(ev.pointerId);
      if (press.grabbed) n.emit("grab");
      ev.preventDefault();
    });
    div.addEventListener("pointermove", function (ev) {
      var c = cy();
      if (!c) return;
      var p = at(ev);
      if (s.linking) { linkTo(p); return; }
      if (s.drawing) { drawingTo(s, p); return; }
      if (!press) {
        hover(s.tool || (!s.readOnly && ownAt(p)) ? null : nodeAt(p));
        qcHover(p);
        return;
      }
      if (!press.moved && Math.hypot(p.x - press.start.x, p.y - press.start.y) < TAP) return;
      press.moved = true;
      var dx = p.x - press.last.x, dy = p.y - press.last.y;
      press.last = p;
      if (press.marquee) { marqueeTo(s, press, p); return; }
      if (press.pan) {
        if (c.panningEnabled()) { c.panBy({ x: dx, y: dy }); c.emit("dragpan"); }
        return;
      }
      if (press.node) {
        if (!press.grabbed) return;
        // Carried the way Cytoscape carries one: a boundary takes what is
        // in it, and a box's boundary grows to keep it inside.
        var z = c.zoom(), moving = press.node.isParent() ? press.node.descendants().filter(function (m) { return !m.isParent(); }) : press.node;
        moving.positions(function (m) { var q = m.position(); return { x: q.x + dx / z, y: q.y + dy / z }; });
        press.node.emit("drag");
      } else if (c.panningEnabled() && c.userPanningEnabled()) {
        c.panBy({ x: dx, y: dy });
        c.emit("dragpan");
      }
    });
    function release(ev) {
      s.pressAt = null;
      if (s.linking) {
        if (div.hasPointerCapture && div.hasPointerCapture(ev.pointerId)) div.releasePointerCapture(ev.pointerId);
        linkEnd(at(ev), ev.type === "pointerup");
        return;
      }
      if (s.drawing) { finishDrawing(s, at(ev), ev.type === "pointerup"); return; }
      if (!press) return;
      var pr = press;
      press = null;
      if (div.hasPointerCapture && div.hasPointerCapture(ev.pointerId)) div.releasePointerCapture(ev.pointerId);
      div.classList.remove("is-grabbing");
      var c = cy();
      if (!c || pr.pan) return;
      if (pr.marquee && pr.moved) { finishMarquee(s, pr, ev.type === "pointerup"); return; }
      if (pr.ghost && pr.ghost.parentNode) pr.ghost.parentNode.removeChild(pr.ghost);
      if (pr.grabbed) {
        pr.node.emit("free");
        if (pr.moved) pr.node.emit("dragfree");
      }
      if (pr.moved || ev.type !== "pointerup") return;
      if (pr.frame) {
        if (pr.shift) s.graph.addSelectionCell(pr.frame); else s.graph.setSelectionCell(pr.frame);
        return;
      }
      // Shift and a record: one more picked, or one taken out, and nothing
      // else changes. Shift on the bare sheet keeps what is picked.
      if (pr.shift && Canvas.pickAlso && Canvas.cv) {
        if (pr.node && !pr.node.isParent()) Canvas.pickAlso(pr.node.id());
        if (!pr.node) return;
        if (!pr.node.isParent()) return;
      }
      (pr.node || c).emit("tap");
    }
    div.addEventListener("pointerup", release);
    div.addEventListener("pointercancel", release);
    div.addEventListener("pointerleave", function () { if (!press) { hover(null); qcHide(); } });
    // The canvas has no menu of its own (the app returns early on cxttap);
    // the browser's would only be in the way, as it was not over Cytoscape.
    div.addEventListener("contextmenu", function (ev) { ev.preventDefault(); });
    div.addEventListener("wheel", function (ev) {
      // On one of Cytoscape's own canvases, so it reaches every listener
      // Cytoscape put above it, the capture-phase ones on its container too.
      var c = cy();
      var target = c && c.container().querySelector("canvas");
      if (!target) return;
      ev.preventDefault();
      qcHide();
      target.dispatchEvent(new WheelEvent("wheel", {
        clientX: ev.clientX, clientY: ev.clientY, screenX: ev.screenX, screenY: ev.screenY,
        deltaX: ev.deltaX, deltaY: ev.deltaY, deltaZ: ev.deltaZ, deltaMode: ev.deltaMode,
        ctrlKey: ev.ctrlKey, shiftKey: ev.shiftKey, altKey: ev.altKey, metaKey: ev.metaKey,
        bubbles: true, cancelable: true,
      }));
    }, { passive: false });
  }

  /* The next box, joined by a line to the one an arrow was on: a step
   * that way, or where the arrow was carried to. Of the diagram's own, a
   * copy of its shape and look, empty and open to type in, in the frame
   * its middle lands in; one step for Undo. From a record, the canvas asks
   * which record comes next (Canvas.quickConnect). */
  function quickNext(of, dir, p) {
    var s = surface;
    if (!s) return null;
    if (of.id) {
      var r = s.div.getBoundingClientRect();
      if (Canvas.quickConnect) Canvas.quickConnect(of.id, dir, p ? { x: r.left + p.x, y: r.top + p.y } : null);
      return null;
    }
    var cell = s.model.getCell(idOf(of.key));
    if (!cell) return null;
    var a = cell.terraneOwn, o = absolute(cell), w = cell.geometry.width, h = cell.geometry.height, box;
    if (p) {
      var m = toModel(p);
      box = { x: m.x - w / 2, y: m.y - h / 2, w: w, h: h };
    } else {
      box = { x: o.x + (dir === "e" ? w + QUICK_GAP : dir === "w" ? -(w + QUICK_GAP) : 0),
        y: o.y + (dir === "s" ? h + QUICK_GAP : dir === "n" ? -(h + QUICK_GAP) : 0), w: w, h: h };
    }
    var step = s.graph.isGridEnabled() ? s.graph.getGridSize() : 1;
    box.x = Math.round(box.x / step) * step;
    box.y = Math.round(box.y / step) * step;
    var spec = { role: a.role, box: box, label: "" };
    if (a.shape) spec.shape = a.shape;
    if (a.look) spec.look = copy(a.look);
    if (a.rotate) spec.rotate = a.rotate;
    var v = s.graph.view, holder = frameAt({ x: (box.x + w / 2 + v.translate.x) * v.scale,
      y: (box.y + h / 2 + v.translate.y) * v.scale });
    var made = null;
    s.graph.batchUpdate(function () {
      made = add(spec, holder ? holder.terraneOwn.key : null);
      add({ role: "line", from: of.key, to: made });
    });
    select([made]);
    var next = s.model.getCell(idOf(made));
    if (next) editText(next);
    return made;
  }

  /* ---- picking several
   * A drag across the bare sheet draws a box, and what is wholly inside it
   * when it is let go is picked: the estate's records by id and the
   * diagram's own by key, with Shift added to what was picked. A record's
   * boundary is not picked by it; the boundary is the place it sits. */
  function marqueeTo(s, pr, p) {
    if (!pr.ghost) {
      pr.ghost = document.createElement("div");
      pr.ghost.className = "mg-ghost is-marquee";
      s.div.appendChild(pr.ghost);
    }
    var g = pr.ghost;
    g.style.left = Math.min(pr.start.x, p.x) + "px";
    g.style.top = Math.min(pr.start.y, p.y) + "px";
    g.style.width = Math.abs(p.x - pr.start.x) + "px";
    g.style.height = Math.abs(p.y - pr.start.y) + "px";
  }

  function finishMarquee(s, pr, kept) {
    if (pr.ghost && pr.ghost.parentNode) pr.ghost.parentNode.removeChild(pr.ghost);
    if (!kept) return;
    var box = { x1: Math.min(pr.start.x, pr.last.x), y1: Math.min(pr.start.y, pr.last.y),
      x2: Math.max(pr.start.x, pr.last.x), y2: Math.max(pr.start.y, pr.last.y) };
    var inside = function (st) {
      return st && st.x >= box.x1 && st.y >= box.y1 && st.x + st.width <= box.x2 && st.y + st.height <= box.y2;
    };
    var view = s.graph.view, ids = [], keys = [];
    estateCells(s).forEach(function (c) {
      if (!c.terraneNode || c.id !== "n:" + c.terraneNode) return;
      var n = s.cy.getElementById(c.terraneNode);
      if (n.nonempty() && !n.isParent() && inside(view.getState(c))) ids.push(c.terraneNode);
    });
    s.model.getRoot().filterDescendants(function (c) {
      if (c.terraneOwn && inside(view.getState(c))) keys.push(c.terraneOwn.key);
      return false;
    });
    if (Canvas.picked) Canvas.picked(ids, keys, pr.shift);
  }

  // Each item of the diagram's own moved by its own distance, all of them
  // one change, as lining several up is one step for Undo.
  function moveEach(moves) {
    var s = surface;
    if (!s || !moves.length) return;
    s.graph.batchUpdate(function () {
      moves.forEach(function (m) {
        var cell = s.model.getCell(idOf(m.key));
        if (cell && (m.dx || m.dy)) s.graph.moveCells([cell], m.dx, m.dy, false);
      });
    });
  }

  // An item of the diagram's own as a box on the sheet, whatever frames it
  // is in; a line by the box its ends make.
  function boxOf(key) {
    var s = surface;
    var cell = s && s.model.getCell(idOf(key));
    if (!cell) return null;
    if (cell.isVertex()) {
      var o = absolute(cell), g = cell.geometry;
      return { x1: o.x, y1: o.y, x2: o.x + g.width, y2: o.y + g.height };
    }
    var st = s.graph.view.getState(cell), v = s.graph.view;
    if (!st) return null;
    return { x1: st.x / v.scale - v.translate.x, y1: st.y / v.scale - v.translate.y,
      x2: (st.x + st.width) / v.scale - v.translate.x, y2: (st.y + st.height) / v.scale - v.translate.y };
  }

  /* A frame drawn around a box on the sheet, under everything in it, and
   * what of the diagram's own sits loose inside it put in it, so it moves
   * with the frame. One change; the frame is selected. */
  function frameAround(box, keys) {
    var s = surface;
    if (!s) return null;
    var key = null;
    s.graph.batchUpdate(function () {
      key = add({ role: "frame", label: "Frame", box: box });
      var frame = s.model.getCell(idOf(key));
      (keys || []).forEach(function (k) {
        var cell = s.model.getCell(idOf(k));
        if (!cell || !cell.isVertex() || (cell.parent && cell.parent.terraneOwn)) return;
        var o = absolute(cell), g = cell.geometry.clone();
        g.x = o.x - box.x;
        g.y = o.y - box.y;
        s.model.add(frame, cell);
        s.model.setGeometry(cell, g);
      });
    });
    return key;
  }

  /* ---- drawing with a tool
   * A press and a drag draws the box from corner to corner; a click draws
   * it at the tool's own size about the point. A line runs from where it
   * was pressed to where it was let go, each end held by the box or shape
   * under it, or left at the point. What is drawn is selected, and the tool
   * goes back to Select (canvas.js). */
  // A tool chosen before the canvas's first drawing is on the page.
  var wanted = null;

  function setTool(tool, shape) {
    var s = surface;
    if (!s) { wanted = tool ? [tool, shape] : null; return; }
    s.tool = tool && tool !== "select" ? tool : null;
    if (shape) s.toolShape = shape;
    s.div.classList.toggle("is-drawing", !!s.tool && s.tool !== "pan");
    s.div.classList.toggle("is-panning", s.tool === "pan" || !!s.spaceDown);
    if (s.tool && s.tool !== "pan") s.graph.clearSelection();
  }

  function startDrawing(s, p, ev) {
    s.div.setPointerCapture(ev.pointerId);
    ev.preventDefault();
    var ghost = document.createElement("div");
    ghost.className = "mg-ghost" + (s.tool === "line" ? " is-line" : "");
    s.div.appendChild(ghost);
    s.drawing = { tool: s.tool, start: p, now: p, ghost: ghost, from: s.tool === "line" ? endAt(s, p) : null };
    drawingTo(s, p);
  }

  function drawingTo(s, p) {
    var d = s.drawing;
    d.now = p;
    var g = d.ghost;
    if (d.tool === "line") {
      var dx = p.x - d.start.x, dy = p.y - d.start.y, len = Math.hypot(dx, dy);
      g.style.left = d.start.x + "px";
      g.style.top = d.start.y + "px";
      g.style.width = len + "px";
      g.style.transform = "rotate(" + Math.atan2(dy, dx) + "rad)";
      return;
    }
    var x = Math.min(d.start.x, p.x), y = Math.min(d.start.y, p.y);
    g.style.left = x + "px";
    g.style.top = y + "px";
    g.style.width = Math.abs(p.x - d.start.x) + "px";
    g.style.height = Math.abs(p.y - d.start.y) + "px";
  }

  // What a line's end is held by at a point: the diagram's own shape under
  // it, a record's box, or nothing.
  function endAt(s, p) {
    var own = ownAt(p);
    if (own && own.isVertex()) return { key: own.terraneOwn.key };
    var cell = s.graph.getCellAt(p.x, p.y, null, true, false, function (st) { return !st.cell.terraneNode; });
    if (cell && cell.terraneNode) {
      var n = s.cy && s.cy.getElementById(cell.terraneNode);
      if (n && n.nonempty() && !n.data("isGroup")) return { record: cell.terraneNode };
    }
    return null;
  }

  function finishDrawing(s, p, kept) {
    var d = s.drawing;
    s.drawing = null;
    if (d.ghost.parentNode) d.ghost.parentNode.removeChild(d.ghost);
    if (!kept) return;
    // The tool steps back before what it drew is put in: while a tool is
    // chosen nothing of the diagram's own can be picked, and the new shape
    // was drawn unselected, its panel never shown.
    s.tool = null;
    s.div.classList.remove("is-drawing");
    var a = toModel(d.start), b = toModel(p), sheet = origin(), key;
    var moved = Math.hypot(p.x - d.start.x, p.y - d.start.y) >= TAP;
    if (d.tool === "line") {
      if (!moved) return;
      var to = endAt(s, p);
      var spec = { role: "line" };
      if (s.toolShape && s.toolShape !== "straight" && (s.toolShape === "square" || s.toolShape === "curved")) spec.route = s.toolShape;
      spec.from = d.from ? (d.from.key || d.from.record) : [Math.round(a.x - sheet.x), Math.round(a.y - sheet.y)];
      spec.to = to ? (to.key || to.record) : [Math.round(b.x - sheet.x), Math.round(b.y - sheet.y)];
      if (spec.from === spec.to) return;
      spec.fromAt = a;
      spec.toAt = b;
      key = add(spec);
    } else {
      var size = DEFAULT_SIZE[d.tool];
      var box = moved
        ? { x: Math.min(a.x, b.x), y: Math.min(a.y, b.y), w: Math.max(24, Math.abs(b.x - a.x)), h: Math.max(20, Math.abs(b.y - a.y)) }
        : { x: a.x - size[0] / 2, y: a.y - size[1] / 2, w: size[0], h: size[1] };
      box = { x: Math.round(box.x), y: Math.round(box.y), w: Math.round(box.w), h: Math.round(box.h) };
      // With Snap to grid on, its corner on a line of the grid and its
      // size whole squares of it.
      var step = s.graph.isGridEnabled() ? s.graph.getGridSize() : 0;
      if (step) {
        box = { x: Math.round(box.x / step) * step, y: Math.round(box.y / step) * step,
          w: Math.max(step, Math.round(box.w / step) * step), h: Math.max(step, Math.round(box.h / step) * step) };
      }
      var frame = d.tool === "frame" ? null : frameAt(d.start);
      var spec2 = { role: d.tool, box: box, label: d.tool === "frame" ? "Frame" : "" };
      if (d.tool === "shape") spec2.shape = s.toolShape;
      key = add(spec2, frame ? frame.terraneOwn.key : null);
    }
    if (Canvas.ownDrawn) Canvas.ownDrawn(key, d.tool);
    var cell = s.model.getCell(idOf(key));
    if (cell && (d.tool === "text" || d.tool === "note")) editText(cell);
  }

  // What the probe reads: every box's rectangle on screen, by element id.
  function boxes() {
    if (!surface) return null;
    var out = {}, view = surface.graph.view;
    estateCells(surface).forEach(function (c) {
      if (!c.id || c.id.indexOf("n:") !== 0 || c.id.indexOf("#") !== -1) return;
      var st = view.getState(c);
      if (st) out[c.id.slice(2)] = { x: st.x, y: st.y, w: st.width, h: st.height };
    });
    return out;
  }

  // And where each box's shape landed on the page, read off the SVG: what a
  // person sees, against what the view state above meant to draw.
  function drawnBoxes() {
    if (!surface) return null;
    var out = {}, view = surface.graph.view, at = surface.div.getBoundingClientRect();
    estateCells(surface).forEach(function (c) {
      if (!c.id || c.id.indexOf("n:") !== 0 || c.id.indexOf("#") !== -1) return;
      var st = view.getState(c);
      var node = st && st.shape && st.shape.node;
      if (!node || !node.getBBox) return;
      var r = node.getBoundingClientRect();
      out[c.id.slice(2)] = { x: r.left - at.left, y: r.top - at.top, w: r.width, h: r.height };
    });
    return out;
  }

  // And the diagram's own, each where it is drawn on the page.
  function ownBoxes() {
    if (!surface) return null;
    var out = {}, view = surface.graph.view;
    surface.model.getRoot().filterDescendants(function (c) {
      if (!c.terraneOwn) return false;
      var st = view.getState(c);
      if (st) out[c.terraneOwn.key] = { x: st.x, y: st.y, w: st.width, h: st.height, role: c.terraneOwn.role };
      return false;
    });
    return out;
  }

  function counts() {
    if (!surface) return { boxes: 0, lines: 0, own: 0 };
    var kids = estateCells(surface);
    return {
      boxes: kids.filter(function (c) { return c.id && c.id.indexOf("n:") === 0 && c.id.indexOf("#") === -1; }).length,
      lines: kids.filter(function (c) { return c.isEdge(); }).length,
      own: surface.own.length,
    };
  }

  /* ---- the drawing as a picture, and small
   * Cytoscape is beneath, and it draws the estate alone: while the export
   * and the overview took its drawing, a frame, a note or a line of the
   * diagram's own was in neither. Both are this model's now. */

  // Every box on the sheet in the order maxGraph paints it, the estate's
  // and the diagram's own, in the drawing's units: the overview's picture.
  // Names, technology lines and marks are words and images, not boxes.
  function sheet() {
    var s = surface;
    if (!s) return null;
    var view = s.graph.view, k = view.scale, t = view.translate, out = [];
    function walk(cell) {
      var st = cell.isVertex() ? view.getState(cell) : null;
      var style = st && st.style;
      if (style && style.shape !== "label" && style.shape !== "image") {
        var fill = style.fillColor && style.fillColor !== "none" ? style.fillColor : null;
        var stroke = style.strokeColor && style.strokeColor !== "none" ? style.strokeColor : null;
        if (fill || stroke) {
          out.push({ x: st.x / k - t.x, y: st.y / k - t.y, w: st.width / k, h: st.height / k,
            fill: fill, stroke: stroke, own: !!cell.terraneOwn });
        }
      }
      for (var i = 0; i < cell.getChildCount(); i += 1) walk(cell.getChildAt(i));
    }
    ["under", "bounds", "boxes", "over"].forEach(function (name) { walk(s.layers[name]); });
    return out;
  }

  // The faces the labels are set in, carried by the picture as data: an SVG
  // drawn as an image sees none of the page's fonts.
  var faces = null;
  function fontFaces() {
    if (faces) return faces;
    faces = Promise.all([400, 500, 600, 700].map(function (weight) {
      var url = "fonts/geist-latin-" + weight + "-normal.woff2";
      return fetch(url).then(function (r) {
        if (!r.ok) throw new Error(url + " answered " + r.status);
        return r.blob();
      }).then(function (blob) {
        return new Promise(function (resolve, reject) {
          var reader = new FileReader();
          reader.onload = function () {
            resolve('@font-face{font-family:"Geist";font-weight:' + weight + ";font-style:normal;src:url("
              + reader.result + ') format("woff2")}');
          };
          reader.onerror = function () { reject(reader.error); };
          reader.readAsDataURL(blob);
        });
      });
    })).then(function (rules) { return rules.join(""); }, function (err) { faces = null; throw err; });
    return faces;
  }

  // The marks too: a provider's is a file the app serves (`icons/...`), and
  // an SVG drawn as an image fetches nothing, so every mark came out as a
  // broken image. Each is fetched once and carried as data.
  var XLINK = "http://www.w3.org/1999/xlink";
  var marks = {};
  function asData(url) {
    if (!marks[url]) {
      marks[url] = fetch(url).then(function (r) {
        if (!r.ok) throw new Error(url + " answered " + r.status);
        return r.blob();
      }).then(function (blob) {
        return new Promise(function (resolve, reject) {
          var reader = new FileReader();
          reader.onload = function () { resolve(reader.result); };
          reader.onerror = function () { reject(reader.error); };
          reader.readAsDataURL(blob);
        });
      }, function (err) { delete marks[url]; throw err; });
    }
    return marks[url];
  }
  function carryMarks(svg) {
    // A tile's mark is an <img> in its label's HTML, which an SVG drawn as
    // an image would not fetch either.
    return Promise.all(Array.prototype.map.call(svg.querySelectorAll("image, img"), function (image) {
      var url = image.getAttributeNS(XLINK, "href") || image.getAttribute("href") || image.getAttribute("src") || "";
      if (!url || /^data:/.test(url)) return null;
      return asData(url).then(function (data) {
        if (image.hasAttributeNS(XLINK, "href")) image.setAttributeNS(XLINK, "href", data);
        if (image.hasAttribute("href")) image.setAttribute("href", data);
        if (image.hasAttribute("src")) image.setAttribute("src", data);
      });
    }));
  }

  function pathTo(root, node) {
    var path = [];
    while (node && node !== root) {
      path.unshift(Array.prototype.indexOf.call(node.parentNode.childNodes, node));
      node = node.parentNode;
    }
    return node === root ? path : null;
  }

  /* The drawing as the sheet shows it, the estate's and the diagram's own,
   * as a PNG at `scale` pixels to the drawing's unit, sixteen units of white
   * around it. The SVG maxGraph drew is copied at a scale of one, without
   * the handles and guides drawn over it, and drawn as an image: one task,
   * so the sheet is never seen at that scale. */
  var PICTURE_PAD = 16;
  function picture(cy, scale) {
    var s = surface;
    if (!s || s.cy !== cy) return Promise.reject(new Error("the canvas is not drawing this diagram"));
    var S = scale || 2;
    return fontFaces().then(function (css) {
      if (surface !== s || s.cy !== cy) throw new Error("the drawing changed while its picture was made");
      var view = s.graph.view, svg = s.div.querySelector("svg");
      var copyOf, b;
      view.scaleAndTranslate(1, 0, 0);
      try {
        b = s.graph.getGraphBounds();
        copyOf = svg.cloneNode(true);
        // What is drawn over the drawing for the person is not of it.
        [view.getBackgroundPane(), view.getOverlayPane(), view.getDecoratorPane()].forEach(function (pane) {
          var path = pane && pathTo(svg, pane);
          var mine = path && path.reduce(function (n, i) { return n && n.childNodes[i]; }, copyOf);
          while (mine && mine.firstChild) mine.removeChild(mine.firstChild);
        });
      } finally {
        syncView();
      }
      if (!(b.width > 0) || !(b.height > 0)) throw new Error("nothing on the sheet to draw");
      var x = b.x - PICTURE_PAD, y = b.y - PICTURE_PAD;
      var w = b.width + 2 * PICTURE_PAD, h = b.height + 2 * PICTURE_PAD;
      var W = Math.round(w * S), H = Math.round(h * S);
      copyOf.removeAttribute("style");
      copyOf.setAttribute("viewBox", [x, y, w, h].join(" "));
      copyOf.setAttribute("width", String(W));
      copyOf.setAttribute("height", String(H));
      var style = document.createElementNS("http://www.w3.org/2000/svg", "style");
      style.textContent = css;
      copyOf.insertBefore(style, copyOf.firstChild);
      return carryMarks(copyOf).then(function () { return raster(copyOf, W, H); });
    });
  }

  // An SVG, W by H, drawn on white as a PNG.
  function raster(svg, W, H) {
    var xml = new XMLSerializer().serializeToString(svg);
    return new Promise(function (resolve, reject) {
      var image = new Image();
      image.onload = function () {
        var canvas = document.createElement("canvas");
        canvas.width = W;
        canvas.height = H;
        var ctx = canvas.getContext("2d");
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, W, H);
        ctx.drawImage(image, 0, 0, W, H);
        try { resolve(canvas.toDataURL("image/png")); } catch (err) { reject(err); }
      };
      image.onerror = function () { reject(new Error("the drawing's SVG did not load as a picture")); };
      image.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(xml);
    });
  }

  /* What is locked on this diagram, the canvas's list: not carried or
   * resized here. A handler made before the lock keeps its handles, and its
   * sizers still resized what was locked, so when the list changes they are
   * made again, as the lock now says. */
  function lockOwn(list) {
    var s = surface;
    if (!s) return;
    var was = Object.keys(s.locked || {}).sort().join("\n");
    s.locked = {};
    (list || []).forEach(function (k) { s.locked[k] = true; });
    var cells = s.graph.getPlugin("SelectionCellsHandler");
    if (cells && cells.handlers && Object.keys(s.locked).sort().join("\n") !== was) {
      cells.handlers.forEach(function (h) { h.onDestroy(); });
      cells.handlers = new Map();
      cells.refresh();
    }
  }

  Canvas.engine = {
    enabled: enabled, attach: attach, detach: detach, boxes: boxes, drawnBoxes: drawnBoxes, ownBoxes: ownBoxes,
    counts: counts, KEY: KEY, live: function () { return !!surface; },
    draws: function (cy) { return !!surface && !!cy && surface.cy === cy; }, sheet: sheet, picture: picture,
    // The grid the diagram's own snaps to when moved, resized or drawn; 0,
    // none.
    grid: function (size) {
      if (!surface) return;
      surface.graph.setGridEnabled(size > 0);
      if (size > 0) surface.graph.setGridSize(size);
    },
    setTool: setTool, own: own, add: add, update: update, remove: remove, order: order, nudge: nudge,
    copy: copyOwn, clip: clipOwn, paste: pasteOwn, rebase: rebase, lock: lockOwn, hops: hops, route: routeOf,
    // Line jumps on or off, the status bar's toggle.
    jumps: function (on) {
      if (!!on === jumpsOn) return;
      jumpsOn = !!on;
      rehop(surface, true);
    },
    where: where, moveEach: moveEach, boxOf: boxOf, frameAround: frameAround,
    select: select, selected: selected, item: item, edit: function (key) {
      if (surface) editText(surface.model.getCell(idOf(key)));
    },
    extent: extent, around: around, origin: origin,
    SHAPES: OWN_SHAPES, FILLS: FILLS, FILL_ORDER: FILL_ORDER, INK: INK, TILE_FILLS: TILE_FILLS, KIND_ICONS: KIND_ICONS,
    MARK_SETS: MARK_SETS, WEIGHTS: WEIGHTS, cornersOf: cornersOf, together: together,
    setLook: setLook, look: function () { return LOOK; }, pathData: pathData, ROUTES: OWN_ROUTES,
  };
})(window.TerraneApp);
