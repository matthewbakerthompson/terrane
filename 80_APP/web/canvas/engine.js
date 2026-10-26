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
 * again), with `arrange_probe.mjs`, `drag_probe.mjs` and `drop_probe.mjs`
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
    // a lid and not as a pill.
    cylinder: [["M", 0, 0.12], ["C", 0, -0.04, 1, -0.04, 1, 0.12], ["L", 1, 0.88], ["C", 1, 1.04, 0, 1.04, 0, 0.88],
      ["Z"], ["M", 0, 0.12], ["C", 0, 0.28, 1, 0.28, 1, 0.12]],
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

  function registerShapes(mg) {
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
    Object.keys(OWN_PATHS).forEach(function (name) {
      var prog = OWN_PATHS[name];
      class Own extends mg.ActorShape {
        redrawPath(c, x, y, w, h) { runPath(c, prog, w, h); }
      }
      mg.ShapeRegistry.add("own-" + name, Own);
    });
    // A square line's turns, from its ends' boxes; a dangling end is the
    // point it was left at.
    mg.EdgeStyleRegistry.add("terrane-square", function (state, source, target, points, result) {
      var pts = state.absolutePoints || [];
      var box = function (st, at) {
        if (st) return { x1: st.x, y1: st.y, x2: st.x + st.width, y2: st.y + st.height };
        return at ? { x1: at.x, y1: at.y, x2: at.x, y2: at.y } : null;
      };
      var a = box(source, pts[0]), b = box(target, pts[pts.length - 1]);
      if (!a || !b) return;
      squareTurns(a, b).forEach(function (p) { result.push(new mg.Point(p.x, p.y)); });
    }, { isOrthogonal: true });
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
   * Six fills a person picks from, each with the edge it is drawn with; an
   * outline solid, dashed or none; and the words small, middling or large.
   * The same names are in terrane/draw/annotations.py. */
  var FILLS = {
    yellow: ["#fdf0b8", "#d9bd4f"], mint: ["#d9efe5", "#6fae92"], lavender: ["#e7e3f7", "#9289c9"],
    rose: ["#f9e1dc", "#d48f84"], white: ["#ffffff", "#a39c8d"], stone: ["#ece7dd", "#a39c8d"],
  };
  var FILL_ORDER = ["yellow", "mint", "lavender", "rose", "white", "stone"];
  var TEXT_SIZES = { s: 11, m: 13, l: 16 };
  var ROLE_FILL = { note: "yellow", shape: "white", frame: "white" };
  var INK = "#272b33";
  var LINE_INK = "#5b6577";
  //: The size a tool draws at when the sheet is clicked rather than dragged.
  var DEFAULT_SIZE = { shape: [120, 64], note: [184, 96], text: [200, 44], frame: [360, 240] };

  function ownStyle(item) {
    var look = item.look || {}, role = item.role;
    if (role === "line") {
      var routed = item.route === "square" || item.route === "curved";
      var line = {
        curved: item.route === "curved",
        strokeColor: LINE_INK, strokeWidth: 1.5, dashed: look.line === "dashed", dashPattern: "6 4",
        endArrow: item.ends === "none" ? "none" : "block", endSize: 7, endFill: true,
        startArrow: item.ends === "both" ? "block" : "none", startSize: 7, startFill: true,
        fontFamily: FACE, fontSize: TEXT_SIZES[look.text || "s"], fontColor: INK, html: true,
        labelBackgroundColor: "#ffffff", labelBorderColor: "#d8d2c6", spacing: 3,
        editable: false, rotatable: false, cloneable: false, bendable: false,
      };
      // A straight line has no edge style at all; maxGraph has none named so.
      if (routed) line.edgeStyle = "terrane-square";
      return line;
    }
    var fill = role === "text" ? null : (look.fill && FILLS[look.fill] ? look.fill : ROLE_FILL[role] || "white");
    var stroke = role === "text" || look.line === "none" ? "none" : FILLS[fill][1];
    var size = TEXT_SIZES[look.text] || (role === "frame" ? 12 : 13);
    var style = {
      fillColor: fill ? FILLS[fill][0] : "none", strokeColor: stroke, strokeWidth: role === "frame" ? 1.25 : 1.25,
      dashed: look.line === "dashed", dashPattern: "6 4",
      fontFamily: FACE, fontSize: size, fontColor: INK, html: true, whiteSpace: "wrap", overflow: "hidden",
      editable: false, rotatable: false, cloneable: false, foldable: false,
    };
    if (role === "frame") {
      // Its name twelve in and eight down. With overflow "width" maxGraph
      // left the name in the frame's very corner, spacing or none.
      Object.assign(style, { shape: "rectangle", rounded: true, absoluteArcSize: true, arcSize: 16,
        align: "left", verticalAlign: "top", spacing: 0, spacingLeft: 12, spacingTop: 8, spacingRight: 12 });
    } else if (role === "note") {
      Object.assign(style, { shape: "rectangle", align: "left", verticalAlign: "top", spacing: 10 });
    } else if (role === "text") {
      Object.assign(style, { shape: "rectangle", align: "left", verticalAlign: "top", spacing: 2, fontColor: "#3b4049" });
    } else {
      var shape = (OWN_PATHS[item.shape] || item.shape === "rounded") ? item.shape : "rectangle";
      if (shape === "rounded") Object.assign(style, { shape: "rectangle", rounded: true, absoluteArcSize: true, arcSize: 20 });
      else Object.assign(style, { shape: "own-" + shape });
      // A line joined to an ellipse or a diamond ends on its outline, not
      // on the box around it; the picture clips it the same way.
      if (shape === "ellipse") style.perimeter = "ellipsePerimeter";
      if (shape === "diamond") style.perimeter = "rhombusPerimeter";
      Object.assign(style, { align: "center", verticalAlign: "middle", spacing: 8 });
    }
    return style;
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
  function attach(cy, list) {
    if (!cy || !enabled()) return Promise.resolve(null);
    return load().then(function (mg) {
      if (cy.destroyed()) return null;
      if (!surface || surface.host !== cy.container()) open(mg, cy.container());
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
    graph.isCellSelectable = mine;
    graph.isCellMovable = mine;
    graph.isCellResizable = function (cell) { return mine(cell) && cell.isVertex(); };
    graph.isCellEditable = function () { return false; };
    graph.isCellFoldable = function () { return false; };
    graph.isCellDisconnectable = function () { return false; };
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
        if (!v) return "";
        var weight = cell.terraneOwn.role === "frame" ? 600 : 400;
        return '<div style="font-weight:' + weight + ';line-height:1.32">' + escapeText(v) + "</div>";
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
    graph.setGridEnabled(false);
    graph.foldingEnabled = false;
    // A line stays in the layer it was drawn in, whatever its ends sit in.
    model.maintainEdgeParent = false;
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
    }
    var accent = (app.DRAW && app.DRAW.accent) || "#0f766e";
    mg.VertexHandlerConfig.selectionColor = accent;
    mg.VertexHandlerConfig.selectionStrokeWidth = 1.5;
    mg.VertexHandlerConfig.selectionDashed = false;
    mg.VertexHandlerConfig.rotationEnabled = false;
    mg.EdgeHandlerConfig.selectionColor = accent;
    mg.EdgeHandlerConfig.selectionDashed = false;
    mg.HandleConfig.fillColor = "#ffffff";
    mg.HandleConfig.strokeColor = accent;
    mg.HandleConfig.size = 8;
    // Every change the person makes to the diagram's own, said once it is
    // made; the engine's own keeping in step is not one.
    model.addListener(mg.InternalEvent.CHANGE, function () {
      if (s.syncing || surface !== s) return;
      changed();
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
      var mx = num(n.style("text-margin-x"), 0), my = num(n.style("text-margin-y"), 0);
      var maxw = num(n.style("text-max-width"), w);
      parts.push(textPart(id + "#name", id, name, x + w / 2 + mx - maxw / 2, y + h / 2 + my - h / 2, maxw, h, {
        fontSize: num(n.style("font-size"), 12), fontStyle: 1, fontColor: n.style("color"),
        // Wrapped at Cytoscape's text-max-width exactly: without "width"
        // the label wrapped wider, and "Installment Lending" kept a line.
        align: "center", verticalAlign: "middle", whiteSpace: "wrap", overflow: "width",
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

  function textPart(id, node, value, x, y, w, h, style) {
    var div = document.createElement("div");
    div.textContent = value;
    // Weight and leading in the label itself: maxGraph's bold is 700 and its
    // line height 1.2, where Cytoscape draws these names at 600 and 1.
    var weight = style.fontStyle === 1 ? 600 : 500;
    var html = '<div style="font-weight:' + weight + ';line-height:1.05">' + div.innerHTML + "</div>";
    style = Object.assign({}, style, { fontStyle: 0 });
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
        s.model.setGeometry(edge, g);
        edge.terraneOwn = copy(a);
        byKey[a.key] = edge;
        placed.push(a.key);
      });
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
        } else {
          item.from = endOf(c, true, at);
          item.to = endOf(c, false, at);
          if (a.ends && a.ends !== "end") item.ends = a.ends;
          if (a.route && a.route !== "straight") item.route = a.route;
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
      if (patch.look || patch.shape || patch.ends || patch.route) s.model.setStyle(cell, ownStyle(a));
    });
  }

  function remove(keys) {
    var s = surface;
    if (!s) return;
    var cells = keys.map(function (k) { return s.model.getCell(idOf(k)); }).filter(Boolean);
    if (cells.length) s.graph.removeCells(cells, true);
  }

  // Brought forward or sent back among what shares its frame or layer.
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
        cell = graph.insertEdge({ parent: s.layers.over, id: idOf(a.key), value: a.label || "",
          source: src || null, target: tgt || null, style: ownStyle(a) });
        var g = cell.geometry.clone();
        if (!src) g.setTerminalPoint(new mg.Point(a.fromAt.x, a.fromAt.y), true);
        if (!tgt) g.setTerminalPoint(new mg.Point(a.toAt.x, a.toAt.y), false);
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
    div.addEventListener("pointerdown", function (ev) {
      if ((ev.button !== 0 && ev.button !== 1) || !cy()) return;
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
      if (s.drawing) { drawingTo(s, p); return; }
      if (!press) { hover(s.tool || (!s.readOnly && ownAt(p)) ? null : nodeAt(p)); return; }
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
    div.addEventListener("pointerleave", function () { if (!press) hover(null); });
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
      target.dispatchEvent(new WheelEvent("wheel", {
        clientX: ev.clientX, clientY: ev.clientY, screenX: ev.screenX, screenY: ev.screenY,
        deltaX: ev.deltaX, deltaY: ev.deltaY, deltaZ: ev.deltaZ, deltaMode: ev.deltaMode,
        ctrlKey: ev.ctrlKey, shiftKey: ev.shiftKey, altKey: ev.altKey, metaKey: ev.metaKey,
        bubbles: true, cancelable: true,
      }));
    }, { passive: false });
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

  Canvas.engine = {
    enabled: enabled, attach: attach, detach: detach, boxes: boxes, drawnBoxes: drawnBoxes, ownBoxes: ownBoxes,
    counts: counts, KEY: KEY, live: function () { return !!surface; },
    setTool: setTool, own: own, add: add, update: update, remove: remove, order: order, nudge: nudge,
    copy: copyOwn, rebase: rebase, where: where, moveEach: moveEach, boxOf: boxOf, frameAround: frameAround,
    select: select, selected: selected, item: item, edit: function (key) {
      if (surface) editText(surface.model.getCell(idOf(key)));
    },
    extent: extent, around: around, origin: origin,
    SHAPES: OWN_SHAPES, FILLS: FILLS, FILL_ORDER: FILL_ORDER, pathData: pathData, ROUTES: OWN_ROUTES,
  };
})(window.TerraneApp);
