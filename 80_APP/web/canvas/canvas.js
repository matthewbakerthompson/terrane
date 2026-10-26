/* The canvas: a diagram drawn by hand, as New diagram and Edit open it.
 *
 * Plain browser JS, no build step, loaded after app.js and before the page's
 * DOMContentLoaded boot. It was app.js's canvas section until 2026-10-24 and
 * moved out unchanged, as the first step of the canvas becoming a drawing
 * tool (HANDOVER section 8): the rest of the app reaches it only through the
 * `Canvas` object it fills at the foot of this file, and it reaches the rest
 * only through the names it takes from `window.TerraneApp` here.
 */

(function (app) {
  "use strict";

  var $ = app.$,
    api = app.api,
    capFirst = app.capFirst,
    closeContextMenu = app.closeContextMenu,
    DRAW = app.DRAW,
    drawGraph = app.drawGraph,
    drawnHere = app.drawnHere,
    el = app.el,
    fail = app.fail,
    fieldWord = app.fieldWord,
    fitSheet = app.fitSheet,
    frameKids = app.frameKids,
    IMPACT_CLASSES = app.IMPACT_CLASSES,
    keepAll = app.keepAll,
    keepGroupMove = app.keepGroupMove,
    keepLeaf = app.keepLeaf,
    loadIndex = app.loadIndex,
    openConnectChooser = app.openConnectChooser,
    openDiagrams = app.openDiagrams,
    openEntityEditor = app.openEntityEditor,
    openRegroupChooser = app.openRegroupChooser,
    placeChooser = app.placeChooser,
    positionKey = app.positionKey,
    REDUCED = app.REDUCED,
    renderFacts = app.renderFacts,
    renderFocusBar = app.renderFocusBar,
    renderViewList = app.renderViewList,
    rerouteInPlace = app.rerouteInPlace,
    selectView = app.selectView,
    showPanel = app.showPanel,
    state = app.state,
    svgIcon = app.svgIcon,
    syncUrl = app.syncUrl,
    toast = app.toast,
    typeWord = app.typeWord,
    updateZoomPct = app.updateZoomPct,
    VIEW_CATEGORIES = app.VIEW_CATEGORIES;
  /* ---- the canvas -----------------------------------------------------------
   * New diagram opens on a sheet to draw on, with whatever is selected in the
   * panel beside it, instead of on a form. Everything placed is something
   * the estate keeps: a library part becomes a new record where it was
   * dropped, with the fields of every boundary it landed in; a system already
   * recorded is drawn as it is; a view is placed as a boundary, and stays in
   * step with that view because the diagram's file names it rather than
   * copying what it draws (terrane.places). The diagram is a view file written
   * as it is drawn, and drawn by the same code as every other drawing: the
   * accounts, the marks and the routed lines are the ones the placed view
   * has on its own page.
   */
  var cv = null;
  var cvDrag = null;

  var CANVAS_HINT = "Draw it: press + or drag a part in, or draw shapes, notes and frames of its own. "
    + "Whatever is selected shows its details on the right.";

  //: How a boundary's field is said where something is dropped into it.
  var PLACE_WORDS = { cloud_provider: "cloud", cloud_account: "account", region: "region",
    availability_zone: "zone", network_zone: "network zone", company_domain: "domain" };

  //: The parts a new diagram is most often drawn from, first in the list.
  var FIRST_PARTS = ["web-app", "service-api", "batch-application", "mobile-app"];

  function openCanvas(viewId, layer) {
    if (window.__AAC_STATIC__) {
      toast("warn", "Drawing needs the local app", "The published copy is read-only.");
      return;
    }
    closeContextMenu();
    var loading = viewId ? api("/api/view?id=" + encodeURIComponent(viewId)) : Promise.resolve(null);
    Promise.all([loading, api("/api/canvas/parts")]).then(function (got) {
      var d = got[0];
      if (viewId && (!d || !d.data)) {
        throw new Error("The file of " + viewId + " does not parse, so it opens in the view editor instead.");
      }
      leaveCanvas();
      if (state.panel) showPanel(false);
      if (state.focus) { state.focus = null; renderFocusBar(); }
      // A layout chosen from the menu draws a diagram the automatic way;
      // the canvas draws it as it is arranged.
      $("layoutPicker").value = "auto";
      var data = d ? d.data : {
        title: "Untitled diagram", category: layer && VIEW_CATEGORIES.indexOf(layer) !== -1 ? layer : "Application",
        kind: "diagram", edges: [{ via: "interfaces" }],
      };
      cv = { id: viewId || null, data: data, parts: got[1], tool: "select", from: null, made: {}, sel: null,
        saving: Promise.resolve(), status: viewId ? "saved" : "fresh", timer: null, fieldTimers: {}, focus: null,
        undo: [], redo: [], toolShape: "rectangle" };
      if (viewId) state.viewId = viewId;
      state.selectedId = null;
      document.querySelector(".shell").classList.add("canvas-mode");
      $("cvTools").hidden = false;
      // The drawing tools are maxGraph's: the old canvas has none of them.
      $("cvTools").classList.toggle("no-own", !(Canvas.engine && Canvas.engine.enabled()));
      $("cvDetails").hidden = false;
      setCanvasTool("select");
      renderUndo();
      syncUrl();
      return canvasDraw();
    }).then(function () { if (cv) canvasSelect(null); }).catch(fail);
  }

  function leaveCanvas() {
    if (!cv) return;
    clearTimeout(cv.timer);
    cv = null;
    cvDrag = null;
    closeCanvasPicker();
    closeShapeMenu();
    // The canvas's own model goes with it; a view drawn next is Cytoscape's.
    if (Canvas.engine) Canvas.engine.detach();
    document.querySelector(".shell").classList.remove("canvas-mode");
    ["cvTools", "cvChips", "cvEmpty", "cvDetails", "cvFold", "cvTip", "cvLayout", "cvGuideX", "cvGuideY", "cvFileDrop", "cvHint", "cvBar"]
      .forEach(function (id) { $(id).hidden = true; });
    $("cvDetails").textContent = "";
  }

  function placesOf() {
    if (!Array.isArray(cv.data.places)) cv.data.places = [];
    return cv.data.places;
  }

  function pinsOf() {
    if (!cv.data.scope || typeof cv.data.scope !== "object") cv.data.scope = {};
    if (!Array.isArray(cv.data.scope.pin)) cv.data.scope.pin = [];
    return cv.data.scope.pin;
  }

  /* Nothing from the estate on it: no view placed, no record pinned. */
  function noRecords(c) {
    var s = (c || cv).data.scope || {};
    return !((c || cv).data.places || []).length && !(s.pin || []).length && !(s.include || []).length;
  }

  /* Nothing on it at all, the estate's or its own. */
  function canvasEmpty(c) {
    return noRecords(c) && !(((c || cv).data.annotations) || []).length;
  }

  /* The diagram as its file will say it, with nothing empty left in. */
  function canvasData(c) {
    var data = JSON.parse(JSON.stringify(c.data));
    data.view_id = c.id || "untitled-diagram";
    if (data.scope) {
      Object.keys(data.scope).forEach(function (k) {
        if (Array.isArray(data.scope[k]) && !data.scope[k].length) delete data.scope[k];
      });
      if (!Object.keys(data.scope).length) delete data.scope;
    }
    if (data.places && !data.places.length) delete data.places;
    if (data.annotations && !data.annotations.length) delete data.annotations;
    // Positions are where the estate's things on it sit; with none of them
    // on it there is nowhere, and an empty object is not written either.
    if (noRecords(c) || (data.positions && !Object.keys(data.positions).length)) delete data.positions;
    return data;
  }

  function viewInfo(viewId) {
    return (cv.parts.views || []).filter(function (v) { return v.id === viewId; })[0] || null;
  }

  function placeTitle(place) {
    var info = viewInfo(place.view);
    return info ? info.title : place.view;
  }

  function indexOfPlace(viewId) {
    var places = cv.data.places || [];
    for (var i = 0; i < places.length; i++) if (places[i].view === viewId) return i;
    return -1;
  }

  /* Saves one after another, so a name typed while a part was being placed
   * cannot be overwritten by the older file. */
  function canvasSave() {
    var mine = cv;
    clearTimeout(mine.timer);
    setCanvasStatus("saving");
    mine.saving = mine.saving.catch(function () {}).then(function () {
      return api("/api/canvas/save", { id: mine.id, data: canvasData(mine) });
    }).then(function (res) {
      var created = !mine.id;
      mine.id = res.id;
      mine.data.view_id = res.id;
      if (cv !== mine) return res;
      state.viewId = res.id;
      setCanvasStatus("saved");
      syncUrl();
      if (created) canvasRefreshList();
      return res;
    }, function (err) {
      if (cv === mine) setCanvasStatus("failed", err.message);
      throw err;
    });
    return mine.saving;
  }

  /* A name or a description, saved once the typing stops. Held until
   * something is on the sheet: an empty diagram is not worth a file. */
  function canvasSoon(delay) {
    if (!cv) return;
    clearTimeout(cv.timer);
    if (!cv.id && canvasEmpty()) return;
    var mine = cv;
    cv.timer = setTimeout(function () {
      if (cv === mine) canvasSave().catch(function () {});
    }, delay === undefined ? 600 : delay);
  }

  function canvasRefreshList() {
    api("/api/overview").then(function (o) {
      state.overview = o;
      renderViewList(o);
      renderFacts(o);
    }).catch(function () {});
  }

  var CANVAS_STATUS = {
    fresh: "Saved once something is on it", saving: "Saving…", saved: "Saved as you draw", failed: "Not saved",
  };

  function setCanvasStatus(kind, why) {
    if (!cv) return;
    cv.status = kind;
    var box = $("viewMeta");
    box.textContent = "";
    box.appendChild(el("span", { class: "cv-status is-" + kind, title: why || "" }, [
      kind === "saved" ? svgIcon("i-circle-check") : kind === "failed" ? svgIcon("i-circle-alert") : null,
      el("span", { text: CANVAS_STATUS[kind] || "" }),
    ]));
    if (kind === "failed" && why) toast("err", "The diagram was not saved", why);
  }

  function setCanvasHead() {
    var d = cv.data;
    $("viewTitle").textContent = d.title || "Untitled diagram";
    var desc = $("viewDesc");
    desc.textContent = CANVAS_HINT;
    desc.title = "";
    var tag = $("viewKind");
    tag.textContent = "Diagram";
    tag.hidden = false;
    var crumb = $("viewCrumb");
    crumb.textContent = "";
    crumb.appendChild(el("button", { type: "button", text: "Diagrams", onclick: function () { openDiagrams("All"); } }));
    crumb.appendChild(el("span", { class: "sep", text: "/" }));
    crumb.appendChild(cv.id
      ? el("button", { type: "button", text: d.category || "Application",
          onclick: function () { openDiagrams(d.category || "All"); } })
      : el("span", { text: "New diagram" }));
    setCanvasStatus(cv.status);
  }

  /* The sheet: the empty state until something is placed, then the
   * diagram drawn as every diagram is. */
  function canvasDraw() {
    if (!cv) return Promise.resolve();
    var mine = cv;
    setCanvasHead();
    renderCanvasChips();
    renderCanvasFold();
    $("cvEmpty").hidden = !canvasEmpty();
    if (noRecords()) {
      // Nothing from the estate on it, so no layout to run: a bare sheet,
      // for the diagram's own shapes and for the first thing placed.
      var bare = bareSheet();
      state.lastGraph = null;
      $("legend").textContent = "";
      $("stageEmpty").hidden = true;
      renderCanvasLayout();
      if (!Canvas.engine) return Promise.resolve();
      return Canvas.engine.attach(bare).then(function () {
        if (cv !== mine || state.cy !== bare || bare.scratch("_fitted")) return;
        bare.scratch("_fitted", true);
        fitOwn(bare);
      });
    }
    return api("/api/view/preview", { id: mine.id, data: canvasData(mine) }).then(function (payload) {
      if (cv !== mine) return;
      $("stageEmpty").hidden = true;
      drawGraph(payload);
      // Spent by the drawing when it is arranged; a drop on a drawing the
      // layout placed is the layout's, and is not carried to the next one.
      cv.dropAt = null;
      setCanvasHead();
      renderCanvasFold();
      renderCanvasLayout();
      canvasMark();
      // maxGraph draws the canvas over what Cytoscape laid out, with the
      // diagram's own shapes (canvas/engine.js); with the old canvas asked
      // for, this does nothing.
      if (Canvas.engine && state.cy) return Canvas.engine.attach(state.cy);
    }).catch(function (err) {
      if (cv === mine) setCanvasStatus("failed", err.message);
    });
  }

  /* A sheet with nothing from the estate on it: a Cytoscape with nothing in
   * it, so the wheel, the zoom buttons and Fit work as on any drawing, and
   * maxGraph draws the diagram's own shapes over it. */
  function bareSheet() {
    if (state.cy && !state.cy.destroyed() && state.cy.scratch("_bare")) return state.cy;
    if (state.cy) { state.cy.destroy(); state.cy = null; }
    $("tiles").hidden = true;
    $("cy").hidden = false;
    $("cy").classList.remove("is-laying");
    var cy = cytoscape({ container: $("cy"), elements: [] });
    cy.scratch("_bare", true);
    // The sheet's corner a little in from the tools, at full size.
    cy.pan({ x: 80, y: 110 });
    cy.on("zoom", updateZoomPct);
    state.cy = cy;
    updateZoomPct();
    return cy;
  }

  /* A sheet of the diagram's own shapes alone, opened on them: all of them
   * in view, at no more than full size. */
  function fitOwn(cy) {
    var bb = Canvas.engine && Canvas.engine.extent();
    if (!bb) return;
    var w = cy.width(), h = cy.height(), pad = 60, bw = Math.max(1, bb.x2 - bb.x1), bh = Math.max(1, bb.y2 - bb.y1);
    var z = Math.min(1, (w - 2 * pad) / bw, (h - 2 * pad - 60) / bh);
    cy.zoom(z);
    cy.pan({ x: (w - bw * z) / 2 - bb.x1 * z, y: (h - bh * z) / 2 - bb.y1 * z });
    updateZoomPct();
  }

  function canvasMark() {
    if (!cv || !state.cy) return;
    var cy = state.cy;
    if (!cy.scratch("_cvStyled")) {
      cy.scratch("_cvStyled", true);
      cy.style().selector("node[?isGroup].cv-on").style({
        "border-color": DRAW.accent, "border-width": 2.5, "border-style": "solid",
      }).update();
    }
    cy.elements().removeClass(IMPACT_CLASSES + " cv-on");
    var sel = cv.sel;
    // The box outlined, not the rest dimmed: on a sheet being drawn on, the
    // other boxes are where the next thing goes.
    if (sel && sel.kind === "record") cy.getElementById(sel.id).addClass("sel");
    if (sel && sel.kind === "several") sel.ids.forEach(function (id) { cy.getElementById(id).addClass("sel"); });
    // The bar over what is picked follows the sheet as it pans and zooms.
    if (!cy.scratch("_cvBar")) { cy.scratch("_cvBar", true); cy.on("viewport", renderBar); }
    renderBar();
    if (sel && sel.kind === "place") cy.nodes("[?isGroup]").filter(function (g) { return !g.parent().length; }).addClass("cv-on");
  }

  /* The sheet moved to what was placed or changed: its boundary filling the
   * sheet, at no more than full size and never further out than the whole
   * drawing; or, for a change to a box already in view, the same zoom with
   * the box in the middle. */
  function canvasFocus() {
    if (!cv || !state.cy || !cv.focus) return;
    var cy = state.cy, want = cv.focus;
    cv.focus = null;
    var n = cy.getElementById(want.id);
    if (!n.length) return;
    var w = cy.width(), h = cy.height(), z;
    var pair = want.also ? cy.getElementById(want.also) : null;
    if (pair && pair.length) {
      // A connection: both ends and the line between, filling the sheet.
      var both = n.union(pair).union(n.edgesWith(pair));
      var bb2 = both.boundingBox({ includeLabels: true });
      z = Math.max(Math.min((w - 160) / Math.max(bb2.w, 1), (h - 220) / Math.max(bb2.h, 1), 0.8), cy.zoom());
      var t2 = { zoom: z, pan: { x: w / 2 - (bb2.x1 + bb2.w / 2) * z, y: h / 2 + 20 - (bb2.y1 + bb2.h / 2) * z } };
      if (REDUCED.matches) { cy.viewport(t2); updateZoomPct(); }
      else cy.animate(t2, { duration: 320, easing: "ease-out-quart", complete: updateZoomPct });
      return;
    }
    if (want.keep && want.zoom) {
      z = want.zoom;
    } else {
      var around = n.parent().length ? n.parent() : n;
      var bb = around.boundingBox({ includeLabels: true });
      // A little under full size: the boundary around it, and the ones
      // beside, are where the next thing goes.
      z = Math.min((w - 140) / Math.max(bb.w, 1), (h - 200) / Math.max(bb.h, 1), 0.8);
      z = Math.max(z, cy.zoom());
    }
    var p = n.parent().length && !want.keep ? n.parent().boundingBox({ includeLabels: true }) : n.boundingBox();
    var target = { zoom: z, pan: { x: w / 2 - (p.x1 + p.w / 2) * z, y: h / 2 + 20 - (p.y1 + p.h / 2) * z } };
    if (REDUCED.matches) { cy.viewport(target); updateZoomPct(); }
    else cy.animate(target, { duration: 320, easing: "ease-out-quart", complete: updateZoomPct });
  }

  /* ---- arranged by hand ----
   * Laid out until a box is moved; from the first move the diagram keeps
   * where everything is (`positions` in its file), the layout places only
   * what is new, and Lay out again hands it back. The arranging itself is
   * arrangeKept(), beside the layout. */

  function canvasKept() {
    var p = cv && cv.data.positions;
    return p && typeof p === "object" && Object.keys(p).length ? p : null;
  }

  /* A box put down in its own boundary: kept where it is, lined up with
   * the one its guide showed. The first move keeps everything. */
  function canvasMovedBox(n, from) {
    var cy = state.cy;
    if (!cv || !cy) return;
    remember();
    if (from.snap) {
      n.position({ x: from.snap.x === null ? n.position("x") : from.snap.x,
                   y: from.snap.y === null ? n.position("y") : from.snap.y });
    }
    var first = !canvasKept();
    if (first) { cv.data.positions = keepAll(cy); rebaseOwn(); }
    else keepLeaf(cy, n, cv.data.positions);
    canvasArranged(first);
    canvasSelect({ kind: "record", id: n.id() });
  }

  /* A boundary put down somewhere else, with everything in it. */
  function canvasMovedGroup(g, dx, dy) {
    var cy = state.cy;
    if (!cv || !cy) return;
    remember();
    var first = !canvasKept();
    if (first) { cv.data.positions = keepAll(cy); rebaseOwn(); }
    else keepGroupMove(cy, g, dx, dy, cv.data.positions);
    canvasArranged(first);
  }

  /* After a move: the lines routed again where the boxes are, the file
   * saved, and on the first move a word that the diagram stays put now. */
  function canvasArranged(first) {
    rerouteInPlace(state.cy);
    renderCanvasLayout();
    if (!cv.sel) canvasSelect(null);
    var mine = cv;
    canvasSave().then(function (res) {
      if (!first || cv !== mine) return;
      toast("ok", "Kept where you put it", "This diagram is arranged by hand from now on: nothing moves on its "
        + "own, and what you place goes where there is room. Its positions are saved in " + res.path + ".",
        { label: "Undo", go: function () {
          if (cv !== mine) return;
          delete cv.data.positions;
          canvasSave().then(canvasDraw).then(function () { if (cv) canvasSelect(cv.sel); }).catch(fail);
        } });
    }).catch(function () {});
  }

  /* The diagram's own shapes said again against the corner the arranged
   * drawing is laid from, which keepAll has just taken: where each is on
   * the sheet does not change, only what that is measured from. */
  function rebaseOwn() {
    if (!Canvas.engine || !Canvas.engine.live() || !(cv.data.annotations || []).length) return;
    cv.data.annotations = Canvas.engine.rebase();
  }

  /* The first shape of its own on a drawing the layout places: the diagram
   * is arranged from then on, as on the first move, so what is drawn stays
   * beside the boxes it was drawn beside. */
  function arrangeForOwn() {
    var cy = state.cy;
    if (!cy || noRecords() || canvasKept() || !cy.nodes().length) return;
    cv.data.positions = keepAll(cy);
    rebaseOwn();
    renderCanvasLayout();
    toast("ok", "Kept where you put it", "This diagram is arranged by hand from now on, so what you draw stays "
      + "beside the boxes you drew it beside. Lay out again hands the boxes back to the layout.");
  }

  /* ---- undo ----
   * Back and forward through what was drawn and where things were put on
   * this diagram: its own shapes and its positions, each step the file as
   * it was. What was placed, made or taken off has its own Undo, in the
   * message that said it was done, since it writes to the model. */
  //: How many steps Undo goes back.
  var UNDO_DEPTH = 200;

  function snapshot() {
    return JSON.stringify({ annotations: cv.data.annotations || [], positions: cv.data.positions || null });
  }

  function remember() {
    if (!cv) return;
    cv.undo.push(snapshot());
    if (cv.undo.length > UNDO_DEPTH) cv.undo.shift();
    cv.redo = [];
    renderUndo();
  }

  function canvasUndo(back) {
    if (!cv) return;
    var from = back ? cv.undo : cv.redo, to = back ? cv.redo : cv.undo;
    if (!from.length) return;
    to.push(snapshot());
    var then = JSON.parse(from.pop());
    var moved = JSON.stringify(cv.data.positions || null) !== JSON.stringify(then.positions);
    if (then.annotations.length) cv.data.annotations = then.annotations; else delete cv.data.annotations;
    if (then.positions) cv.data.positions = then.positions; else delete cv.data.positions;
    renderUndo();
    canvasSelect(null);
    $("cvEmpty").hidden = !canvasEmpty();
    // Where boxes sit is the layout's to draw again; the diagram's own is
    // the engine's alone.
    if (moved) canvasDraw();
    else if (Canvas.engine && Canvas.engine.live()) Canvas.engine.own(cv.data.annotations || []);
    // A new diagram with nothing left on it is not saved at all.
    if (cv.id || !canvasEmpty()) canvasSave().catch(function () {});
  }

  function renderUndo() {
    $("cvUndo").disabled = !cv || !cv.undo.length;
    $("cvRedo").disabled = !cv || !cv.redo.length;
  }

  /* Where something was dropped into a boundary, kept for the drawing that
   * follows: once it sits in that boundary -- placed there, or moved there
   * after the question -- it goes where it was put rather than where there
   * is room. Only on an arranged diagram; a laid-out one is the layout's. */
  function canvasDropAt(id, groupId, at) {
    if (!cv || !canvasKept() || !groupId || !at || !state.cy) return;
    // Against the boundary's frame, not the sheet: the next drawing puts
    // the sheet's corner somewhere else, and the boundary where it was.
    var o = (state.cy.scratch("_frames") || {})[groupId];
    if (!o) return;
    cv.dropAt = { id: id, group: groupId, dx: at.x - o.x, dy: at.y - o.y };
  }

  /* An arranged drawing being drawn, its boxes where arrangeKept put them
   * and nothing yet routed, fitted or gliding: what is new keeps the place
   * it was given, so the next thing placed cannot move it; a box that moved
   * to another boundary loses the line it had in the old one; and what was
   * dropped at a spot goes there. Saved when anything changed. */
  function canvasSettle() {
    var kept = canvasKept(), cy = state.cy;
    var drop = cv ? cv.dropAt : null;
    if (cv) cv.dropAt = null;
    if (!kept || !cy || !cy.scratch("_frames")) return;
    var frames = cy.scratch("_frames"), changed = false;
    cy.nodes().forEach(function (n) {
      if (n.data("isGroup")) return;
      var key = positionKey(n), tail = " / " + n.id();
      Object.keys(kept).forEach(function (k) {
        if (k !== key && (k === n.id() || k.slice(-tail.length) === tail)) { delete kept[k]; changed = true; }
      });
    });
    if (drop && frames[drop.group]) {
      var d = cy.getElementById(drop.id);
      if (d.length && d.parent().length && d.parent().id() === drop.group) {
        d.position({ x: frames[drop.group].x + drop.dx, y: frames[drop.group].y + drop.dy });
        keepLeaf(cy, d, kept);
        changed = true;
      }
    }
    cy.nodes().forEach(function (n) {
      var key = positionKey(n);
      if (kept[key] !== undefined) return;
      var parent = n.parent(), o = frames[parent.length ? parent.id() : ""];
      if (!o) return;
      if (n.data("isGroup")) {
        var f = frames[n.id()];
        if (f) kept[key] = [Math.round(f.x - o.x), Math.round(f.y - o.y)];
      } else {
        keepLeaf(cy, n, kept);
      }
      changed = true;
    });
    if (changed) canvasSoon(0);
  }

  /* Back to the layout: the positions cleared from the file, with Undo. */
  function canvasLayOutAgain() {
    if (!cv || !canvasKept()) return;
    var mine = cv, before = cv.data.positions;
    delete cv.data.positions;
    canvasSave().then(function (res) {
      return canvasDraw().then(function () {
        if (cv !== mine) return;
        if (!cv.sel) canvasSelect(null);
        toast("ok", "Laid out again", "Every box is where the layout puts it, and the positions are cleared from "
          + res.path + ". Move a box to arrange it by hand again.", { label: "Undo", go: function () {
            if (cv !== mine) return;
            cv.data.positions = before;
            canvasSave().then(canvasDraw).then(function () { if (cv && !cv.sel) canvasSelect(null); }).catch(fail);
          } });
      });
    }).catch(fail);
  }

  /* Which of the two the diagram is, at the sheet's foot beside the zoom. */
  function renderCanvasLayout() {
    var box = $("cvLayout");
    box.textContent = "";
    if (!cv || noRecords()) { box.hidden = true; return; }
    box.hidden = false;
    if (!canvasKept()) {
      box.classList.remove("is-arranged");
      box.title = "Move a box and the diagram keeps your arrangement from then on.";
      box.appendChild(svgIcon("i-grid"));
      box.appendChild(el("span", { text: "Laid out automatically" }));
      return;
    }
    box.classList.add("is-arranged");
    box.title = "";
    box.appendChild(svgIcon("i-hand"));
    box.appendChild(el("span", { class: "k", text: "Arranged by hand" }));
    box.appendChild(el("span", { class: "sep", "aria-hidden": "true" }));
    box.appendChild(el("button", { type: "button", class: "cv-link cv-again", onclick: canvasLayOutAgain,
      title: "Clear the positions and let the layout place every box" },
      [svgIcon("i-rotate-ccw"), el("span", { text: "Lay out again" })]));
  }

  /* While a box is carried in its own boundary: a guide where its middle
   * lines up with a box beside it, within six pixels on the screen, and
   * the box put on that line when it is let go. */
  function canvasGuides(n, from) {
    var cy = state.cy;
    if (!cy || !from) return;
    var z = cy.zoom(), pan = cy.pan(), p = n.position(), reach = 6 / z;
    var parent = n.parent();
    var best = { x: null, y: null, dx: reach, dy: reach, sx: null, sy: null };
    frameKids(cy, parent.length ? parent : null).forEach(function (s) {
      if (s === n || s.data("isGroup")) return;
      var q = s.position();
      if (Math.abs(q.x - p.x) <= best.dx) { best.x = q.x; best.dx = Math.abs(q.x - p.x); best.sx = q; }
      if (Math.abs(q.y - p.y) <= best.dy) { best.y = q.y; best.dy = Math.abs(q.y - p.y); best.sy = q; }
    });
    from.snap = best.x === null && best.y === null ? null : { x: best.x, y: best.y };
    var cr = $("cy").getBoundingClientRect(), sr = $("mapSheet").getBoundingClientRect();
    var ox = cr.left - sr.left, oy = cr.top - sr.top;
    var gx = $("cvGuideX"), gy = $("cvGuideY");
    if (best.x !== null) {
      var y1 = Math.min(p.y, best.sx.y) - 30, y2 = Math.max(p.y, best.sx.y) + 30;
      gx.style.left = Math.round(ox + best.x * z + pan.x) + "px";
      gx.style.top = Math.round(oy + y1 * z + pan.y) + "px";
      gx.style.height = Math.round((y2 - y1) * z) + "px";
    }
    if (best.y !== null) {
      var x1 = Math.min(p.x, best.sy.x) - 60, x2 = Math.max(p.x, best.sy.x) + 60;
      gy.style.top = Math.round(oy + best.y * z + pan.y) + "px";
      gy.style.left = Math.round(ox + x1 * z + pan.x) + "px";
      gy.style.width = Math.round((x2 - x1) * z) + "px";
    }
    gx.hidden = best.x === null;
    gy.hidden = best.y === null;
    // What letting go does, beside the box, as the picker's drop says it:
    // the box changes nothing in the model, only where it is drawn.
    var home = parent.length ? parent : null;
    var where = !home ? "on the sheet"
      : "within " + (home.data("field") ? (PLACE_WORDS[home.data("field")] || fieldWord(home.data("field"))) + " "
        + home.data("value") : home.data("label"));
    var tip = $("cvTip"), rp = n.renderedPosition();
    tip.textContent = "Moves it " + where + ". It stays where you put it.";
    tip.hidden = false;
    tip.style.left = Math.min(cr.left + rp.x + n.renderedWidth() / 2 + 12, window.innerWidth - tip.offsetWidth - 8) + "px";
    tip.style.top = Math.min(cr.top + rp.y + 12, window.innerHeight - tip.offsetHeight - 8) + "px";
  }

  function canvasGuidesOff(from) {
    if (from) from.snap = null;
    ["cvGuideX", "cvGuideY", "cvTip"].forEach(function (id) { if ($(id)) $(id).hidden = true; });
  }

  /* ---- what is selected, in the panel beside the sheet ---- */

  function canvasSelect(sel, fromEngine) {
    if (!cv) return;
    cv.sel = sel;
    state.selectedId = sel && sel.kind === "record" ? sel.id : null;
    // A record, a boundary or the diagram itself chosen: none of its own
    // shapes stays selected beside it. Said by the engine, it knows already.
    if (!fromEngine && (!sel || (sel.kind !== "own" && sel.kind !== "several")) && Canvas.engine
        && Canvas.engine.live() && Canvas.engine.selected().length) Canvas.engine.select([]);
    canvasMark();
    renderCanvasChips();
    var box = $("cvDetails");
    box.textContent = "";
    if (!sel) canvasDiagramDetails(box);
    else if (sel.kind === "own" && sel.keys.length > 1) canvasSeveralDetails(box, { ids: [], keys: sel.keys });
    else if (sel.kind === "own") canvasOwnDetails(box, sel.keys);
    else if (sel.kind === "several") canvasSeveralDetails(box, sel);
    else if (sel.kind === "place") {
      canvasPlaceDetails(box, sel.index);
      // The boundary is the whole of it: shown whole, as Fit would.
      if (state.cy && !sel.stay) {
        var cy = state.cy, before = { zoom: cy.zoom(), pan: cy.pan() };
        fitSheet(cy, 24);
        var after = { zoom: cy.zoom(), pan: cy.pan() };
        if (!REDUCED.matches) {
          cy.viewport(before);
          cy.animate(after, { duration: 320, easing: "ease-out-quart", complete: updateZoomPct });
        } else updateZoomPct();
      }
    }
    else canvasRecordDetails(box, sel.id);
  }

  function canvasTap(node) {
    if (node.data("isGroup")) {
      // A boundary belongs to the view placed whole; with several placed,
      // their boundaries are one set, and the first stands for them.
      if ((cv.data.places || []).length) canvasSelect({ kind: "place", index: 0 });
      return;
    }
    canvasSelect({ kind: "record", id: node.id() });
  }

  //: The tools that draw the diagram's own shapes, rather than pick.
  var DRAWING_TOOLS = { shape: true, text: true, note: true, frame: true, line: true };
  var TOOL_BUTTONS = [["cvSelect", "select"], ["cvPan", "pan"], ["cvShapes", "shape"], ["cvText", "text"],
    ["cvNote", "note"], ["cvFrame", "frame"], ["cvLine", "line"]];

  function toolHint(tool, shape) {
    if (tool === "pan") return "Drag to move around the sheet; Space held does the same with any tool. V is Select again.";
    if (tool === "shape") return "Drag on the sheet to draw " + articled(shapeName(shape).toLowerCase())
      + ", or click for one at its own size. Esc stops.";
    if (tool === "text") return "Click where the words go, or drag the width they wrap at. Esc stops.";
    if (tool === "note") return "Click where the note goes, or drag its size. Esc stops.";
    if (tool === "frame") return "Drag the frame's size: what is drawn inside it moves with it. Esc stops.";
    if (tool === "line") return "Drag from where the " + (shape && shape !== "straight" ? shape + " " : "")
      + "line starts to where it ends; on a box or a shape it stays joined to it, and between two records it asks "
      + "whether it is a connection. Esc stops.";
    return "";
  }

  function setCanvasTool(tool, shape) {
    if (!cv) return;
    cv.tool = tool;
    if (shape && tool === "shape") cv.toolShape = shape;
    TOOL_BUTTONS.forEach(function (b) { if ($(b[0])) $(b[0]).setAttribute("aria-pressed", String(tool === b[1])); });
    if (shape && tool === "line") cv.lineRoute = shape;
    var what = tool === "line" ? cv.lineRoute || "straight" : cv.toolShape;
    canvasHint(toolHint(tool, what));
    if (Canvas.engine) Canvas.engine.setTool(DRAWING_TOOLS[tool] || tool === "pan" ? tool : null, what);
    canvasMark();
  }

  /* ---- the diagram's own shapes, as the engine says them ---- */

  /* Something of its own drawn, moved, resized, typed in or restyled: the
   * file's list as the engine has it now, one step for Undo, and saved. */
  function canvasOwnChanged(list) {
    if (!cv) return;
    // Lining several up says itself as one step, before it moves them.
    if (!cv.holdUndo) remember();
    if (list.length) cv.data.annotations = list; else delete cv.data.annotations;
    if (list.length) arrangeForOwn();
    $("cvEmpty").hidden = !canvasEmpty();
    canvasSoon(0);
    // The panel follows the change, unless the change is being typed in it.
    var typing = document.activeElement && /^(TEXTAREA|INPUT)$/.test(document.activeElement.tagName)
      && $("cvDetails").contains(document.activeElement);
    if (cv.sel && (cv.sel.kind === "own" || cv.sel.kind === "several") && !typing) canvasSelect(cv.sel, true);
    else renderBar();
  }

  function canvasOwnSelected(keys, additive) {
    if (!cv || cv.picking) return;
    if (!additive && !keys.length && (!cv.sel || (cv.sel.kind !== "own" && cv.sel.kind !== "several"))) return;
    canvasPick(additive ? pickedIds(cv.sel) : [], keys);
  }

  /* ---- several picked ----
   * What is picked, the estate's records and the diagram's own, said as one
   * selection: one record is that record's panel, its own alone the panel
   * for those, and more than one thing the panel for several, with the bar
   * over them that lines them up, spreads them and frames them. */
  function unique(list) {
    var seen = {};
    return list.filter(function (v) { if (seen[v]) return false; seen[v] = true; return true; });
  }

  function pickedIds(sel) {
    return !sel ? [] : sel.kind === "record" ? [sel.id] : sel.kind === "several" ? sel.ids.slice() : [];
  }

  function pickedKeys(sel) {
    return !sel ? [] : sel.kind === "own" || sel.kind === "several" ? sel.keys.slice() : [];
  }

  function canvasPick(ids, keys) {
    ids = unique(ids);
    keys = unique(keys);
    var sel = !ids.length && !keys.length ? null
      : ids.length === 1 && !keys.length ? { kind: "record", id: ids[0] }
      : !ids.length ? { kind: "own", keys: keys }
      : { kind: "several", ids: ids, keys: keys };
    // The engine's own selection made to match, without its answer coming
    // back to undo what was just picked.
    var eng = Canvas.engine && Canvas.engine.live() ? Canvas.engine : null;
    if (eng && eng.selected().slice().sort().join("|") !== keys.slice().sort().join("|")) {
      cv.picking = true;
      try { eng.select(keys); } finally { cv.picking = false; }
    }
    canvasSelect(sel, true);
  }

  // What the drag across the sheet went around, added to what was picked
  // when it was made with Shift.
  function canvasPicked(ids, keys, additive) {
    if (!cv) return;
    if (additive) { ids = pickedIds(cv.sel).concat(ids); keys = pickedKeys(cv.sel).concat(keys); }
    canvasPick(ids, keys);
  }

  // Shift and a record: one more, or one fewer.
  function canvasPickAlso(id) {
    if (!cv) return;
    var ids = pickedIds(cv.sel), at = ids.indexOf(id);
    if (at === -1) ids.push(id); else ids.splice(at, 1);
    canvasPick(ids, pickedKeys(cv.sel));
  }

  /* Each thing picked as a box on the sheet: a record its own box, not its
   * name's, and the diagram's own by its outline. */
  function pickedBoxes(sel) {
    var cy = state.cy, out = [];
    pickedIds(sel).forEach(function (id) {
      var n = cy && cy.getElementById(id);
      if (!n || n.empty()) return;
      var p = n.position(), w = n.width(), h = n.height();
      out.push({ id: id, box: { x1: p.x - w / 2, y1: p.y - h / 2, x2: p.x + w / 2, y2: p.y + h / 2 } });
    });
    pickedKeys(sel).forEach(function (key) {
      var b = Canvas.engine && Canvas.engine.live() ? Canvas.engine.boxOf(key) : null;
      if (b) out.push({ key: key, box: b });
    });
    return out;
  }

  function unionOf(items) {
    return items.reduce(function (u, it) {
      var b = it.box;
      return u ? { x1: Math.min(u.x1, b.x1), y1: Math.min(u.y1, b.y1), x2: Math.max(u.x2, b.x2), y2: Math.max(u.y2, b.y2) } : b;
    }, null);
  }

  //: The bar's buttons: what each does, its icon and its words.
  var BAR = [
    ["left", "i-align-left", "Line up their left edges"], ["center", "i-align-center", "Line up their middles, across"],
    ["right", "i-align-right", "Line up their right edges"], null,
    ["top", "i-align-top", "Line up their tops"], ["middle", "i-align-middle", "Line up their middles, down"],
    ["bottom", "i-align-bottom", "Line up their bottoms"], null,
    ["across", "i-spread-across", "Space them evenly across"], ["down", "i-spread-down", "Space them evenly down"], null,
    ["frame", "i-frame", "Put a frame around them (Ctrl+G)"],
  ];

  /* The bar, over what is picked when it is more than one thing: on the
   * sheet above them, where the eye already is. */
  function renderBar() {
    var bar = $("cvBar");
    if (!bar) return;
    var sel = cv && cv.sel, cy = state.cy;
    var items = sel && cy ? pickedBoxes(sel) : [];
    if (items.length < 2) { bar.hidden = true; return; }
    if (!bar.childNodes.length) {
      BAR.forEach(function (b) {
        if (!b) { bar.appendChild(el("span", { class: "sep", "aria-hidden": "true" })); return; }
        bar.appendChild(el("button", { type: "button", class: "cv-bar-b", "data-do": b[0], title: b[2], "aria-label": b[2],
          onclick: function () { arrangePicked(b[0]); } }, [svgIcon(b[1])]));
      });
    }
    // Spreading needs three to have a space between to even out.
    Array.prototype.forEach.call(bar.querySelectorAll('[data-do="across"], [data-do="down"]'), function (b) {
      b.disabled = items.length < 3;
    });
    var u = unionOf(items), z = cy.zoom(), pan = cy.pan();
    var cr = $("cy").getBoundingClientRect(), sr = $("mapSheet").getBoundingClientRect();
    bar.hidden = false;
    var left = cr.left - sr.left + (u.x1 + u.x2) / 2 * z + pan.x - bar.offsetWidth / 2;
    var top = cr.top - sr.top + u.y1 * z + pan.y - bar.offsetHeight - 14;
    bar.style.left = Math.round(Math.max(8, Math.min(left, sr.width - bar.offsetWidth - 8))) + "px";
    bar.style.top = Math.round(Math.max(62, top)) + "px";
  }

  /* Lined up, spread or framed: each record moved where it is kept, each
   * of the diagram's own by maxGraph, one step for Undo, and saved. */
  function arrangePicked(how) {
    if (!cv || !state.cy) return;
    var items = pickedBoxes(cv.sel);
    if (items.length < 2) return;
    if (how === "frame") { frameThem(); return; }
    var u = unionOf(items), moves = [];
    var across = how === "left" || how === "center" || how === "right" || how === "across";
    if (how === "across" || how === "down") {
      if (items.length < 3) return;
      var a = across ? "x" : "y";
      var sorted = items.slice().sort(function (p, q) {
        return (p.box[a + "1"] + p.box[a + "2"]) - (q.box[a + "1"] + q.box[a + "2"]);
      });
      var room = sorted[sorted.length - 1].box[a + "2"] - sorted[0].box[a + "1"];
      var used = sorted.reduce(function (t, it) { return t + it.box[a + "2"] - it.box[a + "1"]; }, 0);
      var gap = (room - used) / (sorted.length - 1), at = sorted[0].box[a + "1"];
      sorted.forEach(function (it) {
        var d = at - it.box[a + "1"];
        moves.push({ item: it, dx: across ? d : 0, dy: across ? 0 : d });
        at += it.box[a + "2"] - it.box[a + "1"] + gap;
      });
    } else {
      items.forEach(function (it) {
        var b = it.box, d;
        if (how === "left") d = u.x1 - b.x1;
        else if (how === "right") d = u.x2 - b.x2;
        else if (how === "center") d = (u.x1 + u.x2) / 2 - (b.x1 + b.x2) / 2;
        else if (how === "top") d = u.y1 - b.y1;
        else if (how === "bottom") d = u.y2 - b.y2;
        else d = (u.y1 + u.y2) / 2 - (b.y1 + b.y2) / 2;
        moves.push({ item: it, dx: across ? d : 0, dy: across ? 0 : d });
      });
    }
    movePicked(moves);
  }

  function movePicked(moves) {
    var cy = state.cy;
    moves = moves.filter(function (m) { return Math.abs(m.dx) >= 0.5 || Math.abs(m.dy) >= 0.5; });
    if (!moves.length) return;
    remember();
    cv.holdUndo = true;
    try {
      var records = moves.filter(function (m) { return m.item.id; });
      if (records.length) {
        records.forEach(function (m) {
          var n = cy.getElementById(m.item.id), p = n.position();
          n.position({ x: p.x + m.dx, y: p.y + m.dy });
        });
        if (!canvasKept()) { cv.data.positions = keepAll(cy); rebaseOwn(); }
        else records.forEach(function (m) { keepLeaf(cy, cy.getElementById(m.item.id), cv.data.positions); });
        rerouteInPlace(cy);
        renderCanvasLayout();
      }
      var own = moves.filter(function (m) { return m.item.key; });
      if (own.length) Canvas.engine.moveEach(own.map(function (m) { return { key: m.item.key, dx: m.dx, dy: m.dy }; }));
    } finally {
      cv.holdUndo = false;
    }
    canvasSoon(0);
    renderBar();
  }

  /* A frame drawn around what is picked, under it, with room for its name:
   * the diagram's own put in it, the records left where they are, since a
   * frame drawn by hand sets no field the way a boundary does. */
  function frameThem() {
    var items = pickedBoxes(cv.sel);
    if (!items.length || !Canvas.engine || !Canvas.engine.live()) return;
    var u = unionOf(items);
    Canvas.engine.frameAround({ x: Math.round(u.x1 - 24), y: Math.round(u.y1 - 44),
      w: Math.round(u.x2 - u.x1 + 48), h: Math.round(u.y2 - u.y1 + 68) }, pickedKeys(cv.sel));
  }

  function canvasSeveralDetails(box, sel) {
    var eng = Canvas.engine && Canvas.engine.live() ? Canvas.engine : null;
    var n = sel.ids.length + sel.keys.length;
    var words = [];
    if (sel.ids.length) words.push(sel.ids.length === 1 ? "a record" : sel.ids.length + " records");
    if (sel.keys.length) words.push(sel.keys.length === 1 ? "one of its own" : sel.keys.length + " of its own");
    box.appendChild(el("span", { class: "cv-badge is-link", text: n + " selected" }));
    box.appendChild(el("h2", { class: "cv-h", text: capFirst(spoken(words)) }));
    box.appendChild(el("p", { class: "cv-lede", text: "What the bar over them does, it does to all " + n
      + ": line them up, spread them, frame them." + (sel.ids.length ? " Their fields stay their own, each in its record's panel." : "") }));
    var list = el("div", { class: "cv-picks" });
    sel.ids.forEach(function (id) {
      var item = indexItem(id);
      list.appendChild(el("button", { type: "button", class: "cv-pick", onclick: function () { canvasPick([id], []); } }, [
        el("span", { class: "cv-pick-dot", "aria-hidden": "true" }),
        el("span", { class: "cv-pick-n", text: item ? item.name : id }),
        el("span", { class: "cv-pick-id", text: id }),
      ]));
    });
    sel.keys.forEach(function (key) {
      var a = eng ? eng.item(key) : null;
      if (!a) return;
      list.appendChild(el("button", { type: "button", class: "cv-pick is-own", onclick: function () { canvasPick([], [key]); } }, [
        el("span", { class: "cv-pick-dot", "aria-hidden": "true" }),
        el("span", { class: "cv-pick-n", text: a.label || (a.role === "shape" ? shapeName(a.shape) : ROLE_WORDS[a.role]) }),
        el("span", { class: "cv-pick-id", text: "its own " + a.role }),
      ]));
    });
    box.appendChild(list);
    var acts = [el("button", { type: "button", class: "btn small", onclick: frameThem },
      [svgIcon("i-frame"), el("span", { text: "Put a frame around them" })])];
    if (sel.keys.length) {
      acts.push(el("button", { type: "button", class: "btn small", onclick: function () { if (eng) eng.remove(sel.keys); } },
        [svgIcon("i-x"), el("span", { text: sel.ids.length ? "Delete its own" : "Delete them" })]));
    }
    box.appendChild(el("div", { class: "cv-acts" }, acts));
    box.appendChild(el("p", { class: "cv-small", text: "A frame is this diagram's own, drawn under what it is around. "
      + "What of its own is in it moves with it; the records keep their places, and a frame sets no field the way "
      + "dropping a box into a boundary does." }));
    box.appendChild(el("p", { class: "cv-small cv-keys", text: "Drag across the sheet to pick several \u00b7 Shift-click "
      + "adds or takes one \u00b7 the arrows nudge them, Shift by ten \u00b7 Ctrl+G frames them \u00b7 Space and drag, "
      + "or H, moves the sheet" }));
  }

  /* A tool draws one thing, and the pointer is a pointer again. A line
   * drawn from one record to another asks what it is (V13): a connection
   * the metamodel allows between them, saved with the two records, which
   * takes the line's place; or just a line, which Esc leaves it. */
  function canvasOwnDrawn(key, tool) {
    if (!cv) return;
    setCanvasTool("select");
    var a = tool === "line" ? Canvas.engine.item(key) : null;
    if (!a || !recordEnd(a.from) || !recordEnd(a.to)) return;
    var at = Canvas.engine.where(key);
    openConnectChooser(a.from, a.to, at ? at.x + 12 : undefined, at ? at.y + 12 : undefined, {
      head: "What is this line?",
      keep: "Just a line, on this diagram only",
      why: "Kept in this diagram's file. The estate has no connection between them, and no other diagram shows it.",
      chose: function () { if (cv && Canvas.engine.item(key)) Canvas.engine.remove([key]); },
    });
  }

  // An end of a line that is one of the estate's records on the drawing.
  function recordEnd(end) {
    return typeof end === "string" && !Canvas.engine.item(end) && !!state.cy && state.cy.getElementById(end).nonempty();
  }

  function shapeName(shape) {
    var found = ((Canvas.engine && Canvas.engine.SHAPES) || []).filter(function (s) { return s[0] === shape; })[0];
    return found ? found[1] : "Shape";
  }

  // A small picture of a shape of the diagram's own, as the engine draws it.
  function shapePicture(shape) {
    var ns = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", "-1.5 -1.5 31 23");
    svg.setAttribute("class", "cv-shape-pic");
    svg.setAttribute("aria-hidden", "true");
    var path = document.createElementNS(ns, "path");
    path.setAttribute("d", shape === "rounded"
      ? "M5 0H23A5 5 0 0 1 28 5V15A5 5 0 0 1 23 20H5A5 5 0 0 1 0 15V5A5 5 0 0 1 5 0Z"
      : Canvas.engine.pathData(shape, 28, 20));
    svg.appendChild(path);
    return svg;
  }

  // A line's route, small, as the Line menu and its panel show it.
  function routePicture(route) {
    var ns = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", "-1.5 -1.5 31 23");
    svg.setAttribute("class", "cv-shape-pic is-line");
    svg.setAttribute("aria-hidden", "true");
    var path = document.createElementNS(ns, "path");
    path.setAttribute("d", route === "square" ? "M1 19H14V1H27" : route === "curved" ? "M1 19Q14 19 14 10Q14 1 27 1" : "M1 19L27 1");
    svg.appendChild(path);
    return svg;
  }

  // The menu under Shapes or under Line: which button opened it.
  var menuFor = null;

  function closeShapeMenu() {
    var menu = $("cvShapeMenu");
    if (!menu || menu.hidden) return;
    menu.hidden = true;
    if (menuFor) $(menuFor).setAttribute("aria-expanded", "false");
    menuFor = null;
  }

  function openShapeMenu() { openToolMenu("cvShapes"); }
  function openLineMenu() { openToolMenu("cvLine"); }

  function openToolMenu(from) {
    var menu = $("cvShapeMenu");
    if (!cv || !Canvas.engine) return;
    var again = !menu.hidden && menuFor === from;
    closeShapeMenu();
    if (again) return;
    menu.textContent = "";
    menu.classList.toggle("is-lines", from === "cvLine");
    if (from === "cvLine") {
      Canvas.engine.ROUTES.forEach(function (r) {
        menu.appendChild(el("button", { type: "button", role: "menuitem", class: "cv-shape-item",
          "aria-pressed": String(cv.tool === "line" && (cv.lineRoute || "straight") === r[0]),
          onclick: function () { closeShapeMenu(); setCanvasTool("line", r[0]); } },
          [routePicture(r[0]), el("span", { text: r[1] })]));
      });
    } else {
      Canvas.engine.SHAPES.forEach(function (s) {
        menu.appendChild(el("button", { type: "button", role: "menuitem", class: "cv-shape-item",
          "aria-pressed": String(cv.tool === "shape" && cv.toolShape === s[0]),
          onclick: function () { closeShapeMenu(); setCanvasTool("shape", s[0]); } },
          [shapePicture(s[0]), el("span", { text: s[1] })]));
      });
    }
    menu.style.left = ($("cvTools").offsetLeft + $(from).offsetLeft) + "px";
    menu.hidden = false;
    menuFor = from;
    $(from).setAttribute("aria-expanded", "true");
    var first = menu.querySelector("button");
    if (first) first.focus();
  }

  var ROLE_WORDS = { note: "Note", text: "Text", frame: "Frame", line: "Line" };
  var FILL_WORDS = { yellow: "Yellow", mint: "Mint", lavender: "Lavender", rose: "Rose", white: "White", stone: "Stone" };
  //: A fill each kind of thing starts with, as the engine draws it.
  var ROLE_FILL = { note: "yellow", shape: "white", frame: "white" };

  // An end of a line, said: a record by its name, a shape by its words.
  function endWords(end) {
    if (Array.isArray(end)) return "a point on the sheet";
    var it = Canvas.engine.item(end);
    if (it) return it.label ? "\u201c" + it.label + "\u201d" : (it.role === "shape" ? shapeName(it.shape) : ROLE_WORDS[it.role]).toLowerCase();
    var rec = indexItem(end);
    return rec ? rec.name : end;
  }

  function segmented(label, options, current, pick) {
    var row = el("div", { class: "cv-seg", role: "radiogroup", "aria-label": label });
    options.forEach(function (o) {
      row.appendChild(el("button", { type: "button", role: "radio", class: "cv-seg-b",
        "aria-checked": String(o[0] === current), text: o[1], onclick: function () { pick(o[0]); } }));
    });
    return row;
  }

  function canvasOwnDetails(box, keys) {
    var eng = Canvas.engine;
    var items = eng && eng.live() ? keys.map(function (k) { return eng.item(k); }).filter(Boolean) : [];
    if (!items.length) { canvasDiagramDetails(box); return; }
    var keysLine = "Delete removes it \u00b7 Ctrl+D copies it \u00b7 Ctrl+] brings it forward \u00b7 Ctrl+[ sends "
      + "it back \u00b7 the arrows nudge it, Shift by ten";
    var a = items[0], key = a.key, look = a.look || {};
    var redo = function () { if (cv && cv.sel && cv.sel.kind === "own") canvasSelect(cv.sel, true); };
    var change = function (patch) { eng.update(key, patch); redo(); };
    box.appendChild(el("span", { class: "cv-badge is-own", text: a.role === "line" ? "Line \u00b7 on this diagram only" : "On this diagram only" }));
    box.appendChild(el("h2", { class: "cv-h", text: a.role === "shape" ? shapeName(a.shape) : ROLE_WORDS[a.role] }));
    box.appendChild(el("p", { class: "cv-lede", text: a.role === "line"
      ? "From " + endWords(a.from) + " to " + endWords(a.to) + ". Drawn on this diagram only: it is not a connection "
        + "in the estate, and no other diagram shows it."
      : "Kept where it is put, in this diagram's own file. It is not a record, and no other diagram shows it." }));

    var words = el("textarea", { class: "cv-input", rows: a.role === "line" || a.role === "frame" ? "2" : "3",
      "aria-label": a.role === "frame" ? "Title" : "Words",
      placeholder: a.role === "line" ? "What the line says, if anything" : a.role === "frame" ? "What it holds" : "What it says" });
    words.value = a.label || "";
    var typed = null;
    words.addEventListener("input", function () {
      clearTimeout(typed);
      typed = setTimeout(function () { eng.update(key, { label: words.value }); }, 400);
    });
    words.addEventListener("change", function () { clearTimeout(typed); eng.update(key, { label: words.value }); });
    box.appendChild(cvField(a.role === "frame" ? "Title" : "Words", words));

    if (a.role === "shape") {
      var shapes = el("div", { class: "cv-shape-row", role: "radiogroup", "aria-label": "Shape" });
      eng.SHAPES.forEach(function (s) {
        shapes.appendChild(el("button", { type: "button", role: "radio", class: "cv-shape-b", title: s[1], "aria-label": s[1],
          "aria-checked": String(s[0] === a.shape), onclick: function () { change({ shape: s[0] }); } }, [shapePicture(s[0])]));
      });
      box.appendChild(el("div", { class: "cv-field" }, [el("span", { class: "cv-label", text: "Shape" }), shapes]));
    }

    box.appendChild(el("p", { class: "cv-label", text: "Look" }));
    if (a.role !== "line" && a.role !== "text") {
      var fill = look.fill || ROLE_FILL[a.role] || "white";
      var swatches = el("div", { class: "cv-swatches", role: "radiogroup", "aria-label": "Fill" });
      eng.FILL_ORDER.forEach(function (f) {
        swatches.appendChild(el("button", { type: "button", role: "radio", class: "cv-swatch", title: FILL_WORDS[f],
          "aria-label": FILL_WORDS[f], "aria-checked": String(f === fill),
          style: "--sw:" + eng.FILLS[f][0] + ";--sw-edge:" + eng.FILLS[f][1],
          onclick: function () { change({ look: { fill: f === ROLE_FILL[a.role] ? null : f } }); } }));
      });
      box.appendChild(swatches);
    }
    var looks = el("div", { class: "cv-look-row" });
    if (a.role !== "text") {
      var lines = a.role === "line" ? [["solid", "Solid"], ["dashed", "Dashed"]] : [["solid", "Solid"], ["dashed", "Dashed"], ["none", "None"]];
      looks.appendChild(segmented("Outline", lines, look.line || "solid", function (v) {
        change({ look: { line: v === "solid" ? null : v } });
      }));
    }
    var sizeNow = look.text || (a.role === "line" ? "s" : "m");
    looks.appendChild(segmented("Size of the words", [["s", "S"], ["m", "M"], ["l", "L"]], sizeNow, function (v) {
      change({ look: { text: v === (a.role === "line" ? "s" : "m") ? null : v } });
    }));
    box.appendChild(looks);
    if (a.role === "line") {
      box.appendChild(el("p", { class: "cv-label", text: "Route" }));
      box.appendChild(segmented("Route", eng.ROUTES, a.route || "straight", function (v) { change({ route: v }); }));
      box.appendChild(el("p", { class: "cv-label", text: "Ends" }));
      box.appendChild(segmented("Ends", [["end", "One arrow"], ["both", "Both"], ["none", "None"]], a.ends || "end",
        function (v) { change({ ends: v }); }));
    }

    box.appendChild(el("div", { class: "cv-acts" }, [
      a.role === "line" ? null : el("button", { type: "button", class: "btn small", onclick: function () { eng.edit(key); } },
        [svgIcon("i-pencil"), el("span", { text: "Type in it" })]),
      el("button", { type: "button", class: "btn small", onclick: function () { eng.remove([key]); } },
        [svgIcon("i-x"), el("span", { text: "Delete" })]),
    ].filter(Boolean)));
    box.appendChild(el("p", { class: "cv-small cv-keys", text: (a.role === "line" ? "" : "Double-click it to type in it \u00b7 ") + keysLine }));
  }

  /* The keys of the canvas, before the app's own: Undo and Redo always, and
   * for what of its own is selected, Delete, copy, order and nudge. Not
   * while something is being typed, nor while a menu asks a question. */
  function canvasKeys(e) {
    if (!cv || $("cvTools").hidden) return;
    var t = e.target;
    if (t && (/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName) || t.isContentEditable)) return;
    if ($("ctxMenu")) return;
    var mod = e.ctrlKey || e.metaKey, k = e.key, done = true;
    var eng = Canvas.engine && Canvas.engine.live() ? Canvas.engine : null;
    var keys = eng ? eng.selected() : [];
    var step = e.shiftKey ? 10 : 1;
    if (mod && !e.altKey && (k === "z" || k === "Z")) canvasUndo(!e.shiftKey);
    else if (mod && (k === "y" || k === "Y")) canvasUndo(false);
    else if (k === "Escape" && (DRAWING_TOOLS[cv.tool] || cv.tool === "pan")) setCanvasTool("select");
    else if (!mod && !e.altKey && (k === "v" || k === "V")) setCanvasTool("select");
    else if (!mod && !e.altKey && (k === "h" || k === "H")) setCanvasTool("pan");
    else if (mod && (k === "g" || k === "G") && pickedBoxes(cv.sel).length) frameThem();
    else if (cv.sel && cv.sel.kind === "several" && /^Arrow/.test(k)) {
      var dx = k === "ArrowLeft" ? -step : k === "ArrowRight" ? step : 0, dy = k === "ArrowUp" ? -step : k === "ArrowDown" ? step : 0;
      movePicked(pickedBoxes(cv.sel).map(function (it) { return { item: it, dx: dx, dy: dy }; }));
    }
    else if (!keys.length) done = false;
    else if (k === "Delete" || k === "Backspace") eng.remove(keys);
    else if (k === "Escape") eng.select([]);
    else if (mod && (k === "d" || k === "D")) eng.copy(keys);
    else if (mod && k === "]") eng.order(keys, false);
    else if (mod && k === "[") eng.order(keys, true);
    else if (k === "ArrowLeft") eng.nudge(keys, -step, 0);
    else if (k === "ArrowRight") eng.nudge(keys, step, 0);
    else if (k === "ArrowUp") eng.nudge(keys, 0, -step);
    else if (k === "ArrowDown") eng.nudge(keys, 0, step);
    else if (k === "Enter" && keys.length === 1) eng.edit(keys[0]);
    else done = false;
    if (done) { e.preventDefault(); e.stopPropagation(); }
  }
  document.addEventListener("keydown", canvasKeys, true);
  document.addEventListener("mousedown", function (e) {
    var menu = $("cvShapeMenu");
    if (menu && !menu.hidden && !menu.contains(e.target) && !(menuFor && $(menuFor).contains(e.target))) closeShapeMenu();
  });

  function canvasHint(text) {
    var tip = $("cvHint");
    tip.textContent = text || "";
    tip.hidden = !text;
  }

  function cvField(label, input, wide) {
    return el("label", { class: "cv-field" + (wide === false ? " is-half" : "") }, [
      el("span", { class: "cv-label", text: label }), input,
    ]);
  }

  function canvasDiagramDetails(box) {
    var d = cv.data;
    box.appendChild(el("h2", { class: "cv-h", text: "This diagram" }));
    var name = el("input", { type: "text", class: "cv-input", "aria-label": "Name" });
    name.value = d.title || "";
    name.addEventListener("input", function () {
      d.title = name.value;
      $("viewTitle").textContent = name.value || "Untitled diagram";
      canvasSoon();
    });
    box.appendChild(cvField("Name", name));
    var what = el("textarea", { class: "cv-input", rows: "3", placeholder: "Say in a line what this diagram answers",
      "aria-label": "What it is for" });
    what.value = d.description || "";
    what.addEventListener("input", function () { d.description = what.value; canvasSoon(); });
    box.appendChild(cvField("What it is for", what));
    var layer = el("select", { class: "cv-input", "aria-label": "Layer" });
    (cv.parts.categories || VIEW_CATEGORIES).forEach(function (c) { layer.appendChild(el("option", { value: c, text: c })); });
    layer.value = d.category || "Application";
    var section = el("select", { class: "cv-input", "aria-label": "Section" });
    function sections() {
      section.textContent = "";
      section.appendChild(el("option", { value: "", text: "Choose…" }));
      var seen = {};
      ((state.overview && state.overview.views) || []).forEach(function (v) {
        if (v.category !== layer.value || !v.section || seen[v.section]) return;
        seen[v.section] = 1;
        section.appendChild(el("option", { value: v.section, text: v.section }));
      });
      if (d.section && !seen[d.section]) section.appendChild(el("option", { value: d.section, text: d.section }));
      section.value = d.section || "";
    }
    sections();
    layer.addEventListener("change", function () {
      d.category = layer.value;
      if (d.section) delete d.section;
      sections();
      setCanvasHead();
      canvasSoon(0);
    });
    section.addEventListener("change", function () { d.section = section.value; canvasSoon(0); });
    box.appendChild(el("div", { class: "cv-pair" }, [cvField("Layer", layer, false), cvField("Section", section, false)]));

    box.appendChild(el("h3", { class: "cv-sub", text: "On it" }));
    var on = el("ul", { class: "cv-on-list" });
    (d.places || []).forEach(function (p, i) {
      on.appendChild(el("li", {}, [
        el("button", { type: "button", class: "cv-link", text: placeTitle(p),
          onclick: function () { canvasSelect({ kind: "place", index: i }); } }),
        el("span", { class: "cv-what", text: "a view, as a boundary" }),
      ]));
    });
    ((d.scope && d.scope.pin) || []).forEach(function (id) {
      var item = indexItem(id);
      on.appendChild(el("li", {}, [
        el("button", { type: "button", class: "cv-link", text: item ? item.name : id,
          onclick: function () { canvasSelect({ kind: "record", id: id }); } }),
        el("span", { class: "cv-what", text: item ? typeWord(item.type) : "" }),
      ]));
    });
    // Its own, by their words; what has none counted in one line that
    // picks them all, since five lines called Line say nothing.
    var pick = function (keys) { if (Canvas.engine && Canvas.engine.live()) Canvas.engine.select(keys); };
    var unsaid = {}, quiet = [];
    (d.annotations || []).forEach(function (a) {
      if (!a.label || a.role === "frame" && a.label === "Frame") {
        unsaid[a.role] = (unsaid[a.role] || 0) + 1;
        quiet.push(a.key);
        return;
      }
      on.appendChild(el("li", {}, [
        el("button", { type: "button", class: "cv-link", text: a.label, onclick: function () { pick([a.key]); } }),
        el("span", { class: "cv-what", text: "its own " + a.role }),
      ]));
    });
    if (quiet.length) {
      var counted = Object.keys(unsaid).map(function (r) { return unsaid[r] + " " + r + (unsaid[r] > 1 ? "s" : ""); });
      on.appendChild(el("li", {}, [
        el("button", { type: "button", class: "cv-link", text: spoken(counted), onclick: function () { pick(quiet); } }),
        el("span", { class: "cv-what", text: "its own, without words" }),
      ]));
    }
    box.appendChild(on.childNodes.length ? on : el("p", { class: "cv-none", text: "Nothing yet." }));
    if (!noRecords()) {
      var kept = canvasKept();
      box.appendChild(el("h3", { class: "cv-sub", text: "Layout" }));
      box.appendChild(el("p", { class: "cv-small cv-layout-say", text: kept
        ? "Arranged by hand: what is on it stays where you put it, and what you place next goes where there "
          + "is room. Where each box sits is kept in this diagram's file."
        : "Laid out automatically: the layout places every box each time the diagram is drawn. Move a box "
          + "and the diagram keeps your arrangement from then on." }));
      if (kept) {
        box.appendChild(el("div", { class: "cv-acts" }, [
          el("button", { type: "button", class: "btn small", onclick: canvasLayOutAgain },
            [svgIcon("i-rotate-ccw"), el("span", { text: "Lay out again" })]),
        ]));
      }
    }
    box.appendChild(el("p", { class: "cv-note" }, [svgIcon("i-info"), el("span", { text:
      "Everything you place is a record in the model, and this diagram is a view of them: a system drawn "
      + "here shows on every diagram it belongs to. What you draw with Shapes, Text, Note, Frame and Line is "
      + "this diagram's own, kept in its file and nowhere else." })]));
    if (cv.id) {
      box.appendChild(el("div", { class: "cv-acts" }, [
        el("button", { type: "button", class: "btn small", onclick: function () { selectView(cv.id); } },
          [svgIcon("i-grid"), el("span", { text: "Open as a diagram" })]),
      ]));
    }
  }

  function indexItem(id) {
    return (state.index || []).filter(function (i) { return i.id === id; })[0] || null;
  }

  function partNameOf(componentType) {
    var part = (cv.parts.parts || []).filter(function (p) { return p.id === componentType; })[0];
    return part ? part.name : "";
  }

  function articled(word) {
    return (/^[aeiou]/i.test(word) ? "an " : "a ") + word;
  }

  //: The words a missing field is asked for by.
  var NEED_WORDS = { owner_org_id: "an owner", data_owner_org_id: "a data owner" };

  function canvasRecordDetails(box, id) {
    var mine = cv;
    box.appendChild(el("p", { class: "cv-none", text: "Reading…" }));
    api("/api/entity?id=" + encodeURIComponent(id)).then(function (data) {
      if (cv !== mine || !cv.sel || cv.sel.id !== id) return;
      box.textContent = "";
      var r = data.record, type = data.type, spec = state.schema.entities[type];
      var home = data.home || { kind: data.generated ? "generated" : "own" };
      var editable = !data.generated && home.kind !== "imported" && home.kind !== "harvested";
      var fresh = !!cv.made[id];
      box.appendChild(el("span", { class: "cv-badge" + (fresh ? " is-new" : ""),
        text: capFirst(spec.label) + (fresh ? " · new" : "") }));
      box.appendChild(el("h2", { class: "cv-h", text: r.name || id }));
      var part = partNameOf(r.component_type);
      box.appendChild(el("p", { class: "cv-lede", text: part
        ? "Made from the library part " + part + (r.product && r.product !== r.name
          ? ": " + r.product + (r.cloud_provider ? " on " + r.cloud_provider : "") : "") + "."
        : [capFirst(spec.label), r.company_domain, r.status].filter(Boolean).join(" · ") }));
      if (!editable) {
        box.appendChild(el("p", { class: "cv-note" }, [svgIcon("i-info"), el("span", { text: data.generated
          ? "Made by the shape " + r.archetype_instance + "; it is changed there."
          : (home.note || "It is brought in from elsewhere and changed there.") })]));
      }

      var shown = spec.fields.filter(function (f) { return f.name === "name" || f.required; });
      var rank = function (f) { return f.name === "name" ? 0 : f.enum ? 2 : 1; };
      shown = shown.map(function (f, i) { return [f, i]; }).sort(function (a, b) {
        return rank(a[0]) - rank(b[0]) || a[1] - b[1];
      }).map(function (p) { return p[0]; });
      var inputs = {};
      var grid = el("div", { class: "cv-form" });
      shown.forEach(function (f) {
        var input;
        if (f.enum || f.ref) {
          input = el("select", { class: "cv-input", "aria-label": fieldWord(f.name) });
          var refLabel = f.ref && state.schema.entities[f.ref] ? state.schema.entities[f.ref].label : "";
          input.appendChild(el("option", { value: "", text: f.ref ? "Choose " + articled(refLabel) : "Choose…" }));
          var options = f.enum ? f.enum.map(function (v) { return [v, v]; })
            : (state.index || []).filter(function (i) { return i.type === f.ref; })
                .sort(function (a, b) { return String(a.name).localeCompare(String(b.name)); })
                .map(function (i) { return [i.id, i.name || i.id]; });
          options.forEach(function (o) { input.appendChild(el("option", { value: o[0], text: o[1] })); });
          if (r[f.name] && !options.some(function (o) { return o[0] === String(r[f.name]); })) {
            input.appendChild(el("option", { value: r[f.name], text: r[f.name] }));
          }
        } else {
          input = el("input", { type: "text", class: "cv-input", "aria-label": fieldWord(f.name) });
        }
        input.value = r[f.name] == null ? "" : String(r[f.name]);
        if (!editable) input.disabled = true;
        inputs[f.name] = input;
        var mark = function () { input.classList.toggle("is-open", f.required && !input.value); };
        mark();
        input.addEventListener(f.enum || f.ref ? "change" : "input", function () {
          mark();
          canvasSetField(type, id, f.name, input.value);
          check();
        });
        grid.appendChild(cvField(capFirst(fieldWord(f.name)), input, f.enum ? false : undefined));
      });
      box.appendChild(grid);

      var node = state.cy ? state.cy.getElementById(id) : null;
      var where = node && node.length ? node.ancestors().filter(function (g) { return !!g.data("field"); })
        .sort(function (a, b) { return (a.data("depth") || 0) - (b.data("depth") || 0); }) : null;
      var levels = where ? where.filter(function (g) {
        return g.data("field") !== "cloud_provider" || where.length === 1;
      }) : null;
      if (levels && levels.length) {
        box.appendChild(el("h3", { class: "cv-sub", text: "Placed in" }));
        var chips = el("div", { class: "cv-chips-in" });
        levels.forEach(function (g) {
          chips.appendChild(el("span", { class: "cv-in" }, [
            capFirst(PLACE_WORDS[g.data("field")] || fieldWord(g.data("field"))) + ": ",
            el("b", { text: g.data("value") }),
          ]));
        });
        box.appendChild(chips);
        var inner = levels[levels.length - 1];
        var word = PLACE_WORDS[inner.data("field")] || fieldWord(inner.data("field"));
        box.appendChild(el("p", { class: "cv-small", text: "Set by the " + word + " it sits in. Moved within its "
          + word + " it is only drawn somewhere else; moved into another " + word + " you are asked first, since "
          + "that changes the record." }));
      }

      var checkBox = el("p", { class: "cv-check" });
      box.appendChild(checkBox);
      function check() {
        var missing = shown.filter(function (f) { return f.required && !inputs[f.name].value; }).map(function (f) {
          return NEED_WORDS[f.name] || articled(fieldWord(f.name));
        });
        checkBox.textContent = "";
        checkBox.className = "cv-check" + (missing.length ? " is-open" : " is-ok");
        checkBox.appendChild(svgIcon(missing.length ? "i-circle-alert" : "i-circle-check"));
        checkBox.appendChild(el("span", { text: missing.length
          ? "It needs " + spoken(missing) + " to pass the checks. Everything else it has."
          : "It has everything the checks ask of " + articled(spec.label) + "." }));
      }
      check();

      var acts = el("div", { class: "cv-acts" });
      var pinned = pinsOf().indexOf(id) !== -1;
      if (pinned) {
        acts.appendChild(el("button", { type: "button", class: "btn small", onclick: function () { unplace(id); } },
          [svgIcon("i-x"), el("span", { text: "Take it off this diagram" })]));
      }
      if (editable) {
        acts.appendChild(el("button", { type: "button", class: "btn small", onclick: function () {
          openEntityEditor(type, id, r, function () { canvasDraw().then(function () { canvasSelect({ kind: "record", id: id }); }); },
            null, home);
        } }, [svgIcon("i-pencil"), el("span", { text: "Every field" })]));
      }
      box.appendChild(acts);
      if (!pinned) {
        box.appendChild(el("p", { class: "cv-small", text: "It is drawn here because "
          + ((cv.data.places || []).length ? placeTitle(cv.data.places[0]) : "the diagram's query") + " draws it." }));
      }
    }).catch(fail);
  }

  function spoken(items) {
    if (items.length <= 1) return items.join("");
    return items.slice(0, -1).join(", ") + " and " + items[items.length - 1];
  }

  function canvasSetField(type, id, field, value) {
    var mine = cv;
    var values = {};
    values[field] = value;
    // One timer per record and field: a name still being typed on one box
    // must not be dropped because a field of another was changed.
    var key = id + " " + field;
    clearTimeout(cv.fieldTimers[key]);
    cv.fieldTimers[key] = setTimeout(function () {
      if (cv !== mine) return;
      setCanvasStatus("saving");
      api("/api/save", { type: type, id: id, patch: true, values: values }).then(function () {
        if (cv !== mine) return;
        setCanvasStatus("saved");
        loadIndex();
        if (field === "name") {
          var h = cv.sel && cv.sel.id === id ? $("cvDetails").querySelector(".cv-h") : null;
          if (h) h.textContent = value || id;
          cv.focus = { id: id, keep: true, zoom: state.cy ? state.cy.zoom() : null };
          canvasDraw();
        }
      }).catch(function (err) { if (cv === mine) setCanvasStatus("failed", err.message); });
    }, field === "name" ? 600 : 0);
  }

  function unplace(id) {
    var pins = pinsOf();
    var at = pins.indexOf(id);
    if (at === -1) return;
    pins.splice(at, 1);
    var item = indexItem(id);
    var kept = canvasKept(), lines = {}, tail = " / " + id;
    if (kept) {
      Object.keys(kept).forEach(function (k) {
        if (k === id || k.slice(-tail.length) === tail) { lines[k] = kept[k]; delete kept[k]; }
      });
    }
    canvasSave().then(canvasDraw).then(function () {
      canvasSelect(null);
      toast("ok", "Taken off this diagram", (item ? item.name : id) + " is still in the model.", { label: "Undo", go: function () {
        if (!cv) return;
        pinsOf().push(id);
        if (canvasKept()) Object.keys(lines).forEach(function (k) { cv.data.positions[k] = lines[k]; });
        canvasSave().then(canvasDraw).then(function () { canvasSelect({ kind: "record", id: id }); }).catch(fail);
      } });
    }).catch(fail);
  }

  /* ---- a placed view ---- */

  function foldShown(place, field, value) {
    if (place.only && place.only[field]) return place.only[field].indexOf(value) !== -1;
    if (place.leave_out && place.leave_out[field]) return place.leave_out[field].indexOf(value) === -1;
    return true;
  }

  function setFold(place, field, value, on, all) {
    if (place.only && place.only[field]) {
      var only = place.only[field].filter(function (v) { return v !== value; });
      if (on) only.push(value);
      if (!only.length) return false;
      if (only.length === all.length) delete place.only[field]; else place.only[field] = only;
      if (!Object.keys(place.only).length) delete place.only;
      return true;
    }
    place.leave_out = place.leave_out || {};
    var out = (place.leave_out[field] || []).filter(function (v) { return v !== value; });
    if (!on) out.push(value);
    if (out.length >= all.length) return false;
    if (out.length) place.leave_out[field] = out; else delete place.leave_out[field];
    if (!Object.keys(place.leave_out).length) delete place.leave_out;
    return true;
  }

  function nodesWord(info) {
    if (!info) return "things";
    if (cv.parts.network === info.id) return "network parts";
    return info.types.length === 1 ? typeWord(info.types[0], true) : "things";
  }

  function canvasPlaceDetails(box, index) {
    var place = (cv.data.places || [])[index];
    if (!place) { canvasDiagramDetails(box); return; }
    var info = viewInfo(place.view);
    box.appendChild(el("span", { class: "cv-badge is-link" }, [svgIcon("i-link"), el("span", { text: "Boundary · a view" })]));
    box.appendChild(el("h2", { class: "cv-h", text: placeTitle(place) }));
    box.appendChild(el("p", { class: "cv-lede", text: "Placed from the view and kept in step with it. Change the view, "
      + "and every diagram it sits on follows; nothing here is a copy." }));

    box.appendChild(el("h3", { class: "cv-sub", text: "What it shows here" }));
    var own = place.parts !== false;
    var sw = el("button", { type: "button", class: "cv-switch", role: "switch", "aria-checked": String(own),
      onclick: function () {
        if (own) place.parts = false; else delete place.parts;
        canvasSave().then(canvasDraw).then(function () { canvasSelect({ kind: "place", index: index, stay: true }); }).catch(fail);
      } }, [el("span", { class: "knob" })]);
    box.appendChild(el("div", { class: "cv-toggle" }, [sw, el("span", { class: "cv-toggle-text" }, [
      el("b", { text: "Its " + nodesWord(info) }),
      el("span", { text: own ? "Drawn as the view draws them"
        : "Left out: only the boundaries holding what you placed stay" }),
    ])]));

    var fold = info && info.fold;
    if (fold && fold.values.length > 1) {
      box.appendChild(el("p", { class: "cv-label", text: capFirst(fold.words) }));
      var list = el("div", { class: "cv-folds" });
      var all = fold.values.map(function (v) { return v.value; });
      fold.values.forEach(function (v) {
        var cb = el("input", { type: "checkbox" });
        cb.checked = foldShown(place, fold.field, v.value);
        cb.addEventListener("change", function () {
          if (!setFold(place, fold.field, v.value, cb.checked, all)) {
            cb.checked = !cb.checked;
            toast("warn", "Something has to stay", "Leaving every one of them out leaves nothing to place; remove the boundary instead.");
            return;
          }
          canvasSave().then(canvasDraw).then(function () { canvasSelect({ kind: "place", index: index, stay: true }); }).catch(fail);
        });
        list.appendChild(el("label", { class: "cv-fold-row" }, [cb, el("span", { text: v.label })]));
      });
      box.appendChild(list);
      box.appendChild(el("p", { class: "cv-small", text: "One left out stays in the view; it is only left off here." }));
    }

    box.appendChild(el("h3", { class: "cv-sub", text: "Placed in it here" }));
    box.appendChild(el("p", { class: "cv-small", text: placedInside() }));
    box.appendChild(el("div", { class: "cv-acts" }, [
      el("button", { type: "button", class: "btn small", onclick: function () { selectView(place.view); } },
        [svgIcon("i-arrow-right"), el("span", { text: "Open the view" })]),
      el("button", { type: "button", class: "btn small", onclick: function () { removePlace(index); } },
        [svgIcon("i-x"), el("span", { text: "Remove" })]),
    ]));
  }

  /* What was placed inside the boundaries, said once: the names, how many
   * of them were made here, and where they sit. */
  function placedInside() {
    if (!state.cy) return "Nothing yet.";
    var names = [], zones = [], made = 0, types = {};
    pinsOf().forEach(function (id) {
      var n = state.cy.getElementById(id);
      if (!n.length || !n.parent().length) return;
      names.push(n.data("label") || id);
      if (cv.made[id]) made++;
      types[n.data("entityType")] = 1;
      var z = n.parent().data("value");
      if (z && zones.indexOf(z) === -1) zones.push(z);
    });
    if (!names.length) return "Nothing yet: drag a part into one of its boundaries.";
    var kinds = Object.keys(types);
    var word = kinds.length === 1 ? typeWord(kinds[0], names.length > 1) : (names.length > 1 ? "things" : "thing");
    return spoken(names) + ": " + names.length + " " + (made === names.length ? "new " : "") + word
      + (zones.length ? ", in " + spoken(zones) : "") + ".";
  }

  function removePlace(index) {
    var places = placesOf();
    var gone = places.splice(index, 1)[0];
    var before = canvasKept() ? JSON.parse(JSON.stringify(cv.data.positions)) : null;
    canvasSave().then(canvasDraw).then(function () {
      // What the view drew is off the sheet, and so are its lines in the
      // file, with those of anything else not drawn now (an account folded
      // off another placed view among them); Undo puts them all back.
      var kept = canvasKept();
      if (kept && state.cy) {
        var drawn = {};
        state.cy.nodes().forEach(function (n) { drawn[positionKey(n)] = true; });
        Object.keys(kept).forEach(function (k) { if (!drawn[k]) delete kept[k]; });
        canvasSoon(0);
      }
      canvasSelect(null);
      toast("ok", "Removed " + placeTitle(gone), "The view is as it was; it is only off this diagram.", { label: "Undo",
        go: function () {
          if (!cv) return;
          placesOf().splice(index, 0, gone);
          if (before) cv.data.positions = before;
          canvasSave().then(canvasDraw).then(function () { canvasSelect({ kind: "place", index: index, stay: true }); }).catch(fail);
        } });
    }).catch(fail);
  }

  /* One label per placed view, pinned to the sheet's corner: the view's
   * outermost boundary is often off the screen, and its name should not be. */
  function renderCanvasChips() {
    var box = $("cvChips");
    box.textContent = "";
    var places = (cv && cv.data.places) || [];
    box.hidden = !places.length;
    places.forEach(function (p, i) {
      var on = cv.sel && cv.sel.kind === "place" && cv.sel.index === i;
      box.appendChild(el("button", { type: "button", class: "cv-chip" + (on ? " is-on" : ""),
        onclick: function () { canvasSelect({ kind: "place", index: i }); } }, [
        svgIcon(cv.parts.network === p.view ? "i-network" : "i-grid"),
        el("span", { class: "n", text: placeTitle(p) }),
        el("span", { class: "k" }, [svgIcon("i-link"), el("span", { text: "a view, kept in step" })]),
      ]));
    });
  }

  /* What a placed view leaves off this diagram, said where the key would be,
   * with one click to bring it back. */
  function renderCanvasFold() {
    var box = $("cvFold");
    box.textContent = "";
    var said = [];
    ((cv && cv.data.places) || []).forEach(function (p) {
      var info = viewInfo(p.view);
      if (!info || !info.fold) return;
      var hidden = info.fold.values.filter(function (v) { return !foldShown(p, info.fold.field, v.value); });
      if (!hidden.length) return;
      var named = hidden.filter(function (v) { return v.value; });
      var none = hidden.filter(function (v) { return !v.value; });
      var words = info.fold.words;
      var text = (named.length ? named.length + " more " + (named.length === 1 ? words.replace(/s$/, "") : words) : "")
        + (none.length ? (named.length ? " and " : "") + none[0].label : "") + ", folded";
      said.push(el("span", { class: "cv-fold-one" }, [el("span", { text: text }),
        el("button", { type: "button", class: "cv-link", text: "Show", onclick: function () {
          if (p.only) delete p.only[info.fold.field];
          if (p.only && !Object.keys(p.only).length) delete p.only;
          if (p.leave_out) delete p.leave_out[info.fold.field];
          if (p.leave_out && !Object.keys(p.leave_out).length) delete p.leave_out;
          canvasSave().then(canvasDraw).catch(fail);
        } })]));
    });
    said.forEach(function (s) { box.appendChild(s); });
    box.hidden = !said.length;
  }

  /* ---- the picker: the library and the estate, to click or drag ---- */

  function closeCanvasPicker() {
    var pick = $("cvPicker");
    if (!pick) return;
    pick.hidden = true;
    pick.textContent = "";
    $("cvAdd").setAttribute("aria-expanded", "false");
    $("cvBoundary").setAttribute("aria-pressed", "false");
  }

  //: The words a product's name starts with that say whose it is: "EC2"
  //: asked for is Amazon EC2 exactly.
  var VENDOR_WORDS = /^(amazon|aws|azure|microsoft|google|gcp|cloud) /;

  /* How near a name is to what was asked: the same, or the same once the
   * vendor's word is off it; starting with it or holding it as a word; or
   * holding it at all. */
  function closeness(name, q) {
    var n = String(name || "").toLowerCase();
    if (!q) return 0;
    if (n === q || n.replace(VENDOR_WORDS, "") === q) return 0;
    if (n.indexOf(q) === 0 || (" " + n + " ").indexOf(" " + q + " ") !== -1) return 1;
    return 2;
  }

  function pickerItems(tab, q, boundaries) {
    var p = cv.parts, out = { library: [], estate: [] };
    var hit = function (text) { return !q || String(text || "").toLowerCase().indexOf(q) !== -1; };
    if (!boundaries && tab !== "estate") {
      // A part is found by what each cloud calls it as well as by its own
      // name: "EC2" is the virtual machine, named for what was asked.
      var parts = p.parts.slice().sort(function (a, b) {
        var ra = FIRST_PARTS.indexOf(a.id), rb = FIRST_PARTS.indexOf(b.id);
        return (ra === -1 ? 99 : ra) - (rb === -1 ? 99 : rb);
      }).map(function (x, i) {
        if (hit(x.name + " " + x.category + " " + x.typeLabel)) return { part: x, rank: closeness(x.name, q), at: i };
        var said = null;
        // Of a part's products the one closest to what was asked.
        Object.keys(x.products || {}).forEach(function (cloud) {
          x.products[cloud].forEach(function (product) {
            if (!hit(product)) return;
            if (!said || closeness(product, q) < closeness(said.product, q)) said = { cloud: cloud, product: product };
          });
        });
        // A former name, "Azure OpenAI", finds the cloud's usual product.
        if (!said) Object.keys(x.providers || {}).some(function (cloud) {
          if (!hit(x.providers[cloud]) || !(x.products || {})[cloud]) return false;
          said = { cloud: cloud, product: x.products[cloud][0] };
          return true;
        });
        return said ? { part: x, cloud: said.cloud, product: said.product, rank: closeness(said.product, q), at: i } : null;
      }).filter(Boolean);
      // What was asked for first: "EC2" is the virtual machine before the
      // accelerated instances whose answer says EC2 too.
      if (q) parts.sort(function (a, b) {
        return a.rank - b.rank || (a.product || a.part.name).length - (b.product || b.part.name).length || a.at - b.at;
      });
      out.library = parts.slice(0, q ? 30 : (tab === "library" ? 14 : 4)).map(function (found) {
        var x = found.part;
        return { kind: "part", id: x.id, name: found.product || x.name, part: x.name, products: x.products || {},
          product: found.product || "", cloud: found.cloud || "",
          sub: found.product ? x.name + " \u00b7 " + found.cloud + " \u00b7 " + x.typeLabel : "Part \u00b7 " + x.typeLabel,
          tag: "Box", icon: "i-box", typeLabel: x.typeLabel, type: x.type };
      });
    }
    if (tab !== "library") {
      var views = p.views.slice().sort(function (a, b) { return (a.id !== p.network) - (b.id !== p.network); })
        .filter(function (v) { return hit(v.title + " " + v.category); })
        .map(function (v) {
          var accounts = v.fold && v.fold.field === "cloud_account"
            ? v.fold.values.filter(function (x) { return x.value; }).length : 0;
          return { kind: "view", id: v.id, name: v.title, tag: "Boundary", icon: v.id === p.network ? "i-network" : "i-grid",
            sub: "View · " + v.nodes + " " + nodesWord(v) + (accounts ? ", " + accounts + " accounts" : "") };
        });
      var accounts = p.accounts.filter(function (a) { return hit(a.label); }).map(function (a) {
        return { kind: "account", value: a.value, name: a.value, tag: "Boundary", icon: "i-cloud",
          sub: a.label.split(" · ")[0] + " account · " + a.count + " network parts" };
      });
      var zones = p.zones.filter(function (z) { return hit(z.value + " zone"); }).map(function (z) {
        return { kind: "zone", value: z.value, name: z.value, tag: "Boundary", icon: "i-shield",
          sub: "Network zone · " + z.count + " network parts" };
      });
      var systems = boundaries ? [] : p.systems.filter(function (s) { return hit(s.name + " " + s.id + " " + s.domain); })
        .map(function (s) {
          return { kind: "system", id: s.id, name: s.name, tag: "Box", icon: "i-app-window",
            sub: "System" + (s.domain ? " · " + s.domain : "") };
        });
      if (!q && tab === "all") {
        out.estate = views.slice(0, 1).concat(accounts.slice(0, 1), zones.slice(0, 1), systems.slice(0, 1));
      } else {
        var cap = q ? 12 : (boundaries ? 40 : 8);
        out.estate = views.slice(0, q ? 8 : 40).concat(accounts.slice(0, cap), zones.slice(0, cap), systems.slice(0, cap));
      }
    }
    return out;
  }

  function openCanvasPicker(tab, boundaries) {
    if (!cv) return;
    var pick = $("cvPicker");
    var state2 = { tab: tab || "all" };
    pick.textContent = "";
    pick.hidden = false;
    $("cvAdd").setAttribute("aria-expanded", "true");
    $("cvBoundary").setAttribute("aria-pressed", String(!!boundaries));
    pick.classList.toggle("is-boundary", !!boundaries);
    var search = el("input", { type: "search", class: "cv-search", "aria-label": "Find something to place",
      placeholder: boundaries ? "Find a view, an account, a zone…" : "Find a part, a system, an account, a view…" });
    var tabs = el("div", { class: "cv-tabs", role: "tablist" });
    var list = el("div", { class: "cv-list" });
    var c = cv.parts.counts;
    pick.appendChild(el("div", { class: "cv-search-row" }, [svgIcon("i-search"), search]));
    if (!boundaries) {
      [["all", "All"], ["library", "Library"], ["estate", "This estate"]].forEach(function (t) {
        tabs.appendChild(el("button", { type: "button", role: "tab", class: "cv-tab",
          "aria-selected": String(state2.tab === t[0]),
          onclick: function () {
            state2.tab = t[0];
            tabs.querySelectorAll(".cv-tab").forEach(function (b) { b.setAttribute("aria-selected", String(b === this)); }, this);
            fill();
          } }, [t[1]]));
      });
      pick.appendChild(tabs);
    } else {
      pick.appendChild(el("p", { class: "cv-pick-head", text: "A boundary: a view, or an account or zone of " + (cv.parts.networkTitle || "the network") }));
    }
    pick.appendChild(list);
    pick.appendChild(el("p", { class: "cv-foot", text: c.systems + " systems, " + c.views + " views to place as boundaries and "
      + c.parts + " parts in all: type to find one, or drag it straight onto the sheet." }));

    function row(item) {
      var r = el("div", { class: "cv-row", draggable: "true", tabindex: "0", role: "button",
        "aria-label": "Place " + item.name + ", " + item.sub }, [
        el("span", { class: "cv-grip" }, [svgIcon("i-grip")]),
        el("span", { class: "cv-ico" }, [svgIcon(item.icon)]),
        el("span", { class: "cv-row-text" }, [el("b", { text: item.name }), el("span", { text: item.sub })]),
        el("span", { class: "cv-tag" + (item.tag === "Boundary" ? " is-boundary" : ""), text: item.tag }),
      ]);
      r.addEventListener("click", function () { canvasPlace(item, [], null); });
      r.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); canvasPlace(item, [], null); }
      });
      r.addEventListener("dragstart", function (e) {
        cvDrag = item;
        e.dataTransfer.effectAllowed = "copy";
        try { e.dataTransfer.setData("text/plain", item.name); } catch (err) { /* old engines */ }
        r.classList.add("is-dragging");
        setTimeout(function () { $("cvPicker").classList.add("is-carrying"); }, 0);
        $("cvEmpty").classList.add("is-drop");
        $("cvEmptyDrop").textContent = item.tag === "Boundary"
          ? "Drop to place " + item.name + " as a boundary" : "Drop to place " + item.name;
      });
      r.addEventListener("dragend", function () {
        r.classList.remove("is-dragging");
        clearCanvasDrop();
        cvDrag = null;
      });
      return r;
    }

    function fill() {
      list.textContent = "";
      var q = search.value.trim().toLowerCase();
      var got = pickerItems(state2.tab, q, boundaries);
      if (got.library.length) {
        list.appendChild(el("p", { class: "cv-group", text: "From the library" }));
        got.library.forEach(function (i) { list.appendChild(row(i)); });
      }
      if (got.estate.length) {
        list.appendChild(el("p", { class: "cv-group", text: "From this estate" }));
        got.estate.forEach(function (i) { list.appendChild(row(i)); });
      }
      if (!got.library.length && !got.estate.length) {
        list.appendChild(el("p", { class: "cv-none", text: "Nothing here is called that." }));
      }
    }
    search.addEventListener("input", fill);
    search.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { e.preventDefault(); closeCanvasPicker(); $("cvAdd").focus(); }
      if (e.key === "Enter") {
        var first = list.querySelector(".cv-row");
        if (first) { e.preventDefault(); first.click(); }
      }
    });
    fill();
    search.focus();
  }

  /* Where a box dropped at this point of the screen would go: the innermost
   * boundary holding the point that is one value of a field, and every one
   * around it, outermost first. */
  function canvasDropInfo(e) {
    if (!state.cy) return { into: [], group: null };
    var r = $("cy").getBoundingClientRect(), pan = state.cy.pan(), z = state.cy.zoom();
    var x = (e.clientX - r.left - pan.x) / z, y = (e.clientY - r.top - pan.y) / z;
    var hit = null;
    state.cy.nodes("[?isGroup]").forEach(function (g) {
      if (!g.data("field")) return;
      var bb = g.boundingBox({ includeLabels: false });
      if (x < bb.x1 || x > bb.x2 || y < bb.y1 || y > bb.y2) return;
      if (!hit || (g.data("depth") || 0) > (hit.data("depth") || 0)) hit = g;
    });
    if (!hit) return { into: [], group: null };
    var chain = hit.ancestors().add(hit).filter(function (g) { return !!g.data("field"); })
      .sort(function (a, b) { return (a.data("depth") || 0) - (b.data("depth") || 0); });
    return { group: hit, into: chain.map(function (g) {
      return { field: g.data("field"), value: g.data("stored"),
        label: (PLACE_WORDS[g.data("field")] || fieldWord(g.data("field"))) + " " + g.data("value") };
    }) };
  }

  function clearCanvasDrop() {
    $("cvPicker").classList.remove("is-carrying");
    if (state.cy) state.cy.nodes(".drop-into").removeClass("drop-into");
    $("cvTip").hidden = true;
    $("cvEmpty").classList.remove("is-drop");
  }

  function canvasDragOver(e) {
    if (!cv || !cvDrag) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
    var boxy = cvDrag.kind === "part" || cvDrag.kind === "system";
    var info = boxy ? canvasDropInfo(e) : { into: [], group: null };
    if (state.cy) {
      state.cy.nodes(".drop-into").forEach(function (g) { if (g !== info.group) g.removeClass("drop-into"); });
      if (info.group) info.group.addClass("drop-into");
    }
    var tip = $("cvTip");
    if (!state.cy) { tip.hidden = true; return; }
    tip.textContent = !boxy ? "Drop to place " + cvDrag.name + " as a boundary"
      : info.into.length ? "Drop: " + saidInto(info.into)
      : "Drop: on the sheet, in no boundary";
    tip.hidden = false;
    tip.style.left = Math.min(e.clientX + 16, window.innerWidth - tip.offsetWidth - 8) + "px";
    tip.style.top = Math.min(e.clientY + 20, window.innerHeight - tip.offsetHeight - 8) + "px";
  }

  function canvasDrop(e) {
    if (!cv || !cvDrag) return;
    e.preventDefault();
    var item = cvDrag;
    cvDrag = null;
    var boxy = item.kind === "part" || item.kind === "system";
    var info = boxy ? canvasDropInfo(e) : { into: [], group: null };
    clearCanvasDrop();
    var r = $("cy").getBoundingClientRect(), z = state.cy ? state.cy.zoom() : 1, pan = state.cy ? state.cy.pan() : { x: 0, y: 0 };
    canvasPlace(item, info.into, { x: e.clientX, y: e.clientY, group: info.group ? info.group.id() : null,
      mx: (e.clientX - r.left - pan.x) / z, my: (e.clientY - r.top - pan.y) / z });
  }

  /* Where something lands, said: an account names its cloud already, so the
   * cloud is left out of the words though not out of the record. */
  function saidInto(into) {
    var fields = into.map(function (i) { return i.field; });
    return into.filter(function (i) {
      return !(i.field === "cloud_provider" && fields.indexOf("cloud_account") !== -1);
    }).map(function (i) { return i.label; }).join(", ");
  }

  /* A new record's name, asked where it was dropped before it is made: the
   * id is made from the name, and a name typed afterward would leave a
   * Lending portal filed as SYS-WEB-APPLICATION. */
  /* The cloud a drop lands in, by the boundaries it was dropped into, and
   * the products that cloud offers for the part, the usual one first. */
  function cloudOf(into) {
    var step = (into || []).filter(function (i) { return i.field === "cloud_provider"; })[0];
    return step ? String(step.value) : "";
  }

  function askPartName(item, into, at) {
    closeContextMenu();
    var cloud = cloudOf(into), choices = cloud ? ((item.products || {})[cloud] || []) : [];
    // What is recorded as its product: the one searched for, if it is this
    // cloud's, else the cloud's usual one. The server keeps it to the
    // cloud's own (api_canvas_record).
    var product = choices.indexOf(item.product) !== -1 ? item.product : choices[0] || "";
    var menu = el("div", { class: "ctx-menu connect-menu cv-name-menu", id: "ctxMenu", role: "dialog",
      "aria-label": "Name the new " + item.typeLabel });
    menu.appendChild(el("div", { class: "ctx-head", text: "A new " + item.typeLabel + ", from " + (item.part || item.name) }));
    var where = saidInto(into);
    menu.appendChild(el("p", { class: "connect-ask", text: where ? "In " + where + "." : "On the sheet, in no boundary." }));
    var input = el("input", { type: "text", class: "connect-input", "aria-label": "Its name" });
    input.value = product || item.product || item.part || item.name;
    var picks = null;
    if (choices.length) {
      picks = el("div", { class: "cv-offers", role: "radiogroup", "aria-label": "What " + cloud + " calls it" });
      var mark = function () {
        Array.prototype.forEach.call(picks.children, function (b) { b.setAttribute("aria-checked", String(b.textContent === product)); });
      };
      choices.forEach(function (choice) {
        picks.appendChild(el("button", { type: "button", role: "radio", class: "cv-offer", text: choice, onclick: function () {
          // The name follows the product while it is still a product's.
          if (!input.value.trim() || choices.indexOf(input.value.trim()) !== -1) input.value = choice;
          product = choice;
          mark();
          input.focus();
          twin();
        } }));
      });
      mark();
    }
    function go() {
      var name = input.value.trim();
      if (!name) { input.focus(); return; }
      closeContextMenu();
      var named = {};
      Object.keys(item).forEach(function (k) { named[k] = item[k]; });
      named.named = name;
      named.chosen = product;
      canvasPlace(named, into, at);
    }
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); go(); }
      if (e.key === "Escape") { e.preventDefault(); closeContextMenu(); }
    });
    // A name the estate already has is a thing that may exist already: the
    // whole point is to place it rather than make it twice.
    var same = el("p", { class: "cv-same", hidden: "hidden" });
    function twin() {
      var said = input.value.trim().toLowerCase();
      var found = said && (state.index || []).filter(function (i) {
        return i.type === item.type && String(i.name || "").toLowerCase() === said;
      })[0];
      same.textContent = "";
      same.hidden = !found;
      if (!found) return;
      same.appendChild(el("span", { text: "The estate has " + articled(item.typeLabel) + " called " + found.name + " already. " }));
      same.appendChild(el("button", { type: "button", class: "cv-link", text: "Place that one", onclick: function () {
        closeContextMenu();
        canvasPlace({ kind: "system", id: found.id, name: found.name }, into, at);
      } }));
      same.appendChild(el("span", { text: " Placing a new one names it " + found.name + " 2." }));
    }
    input.addEventListener("input", twin);
    if (picks) {
      menu.appendChild(el("p", { class: "cv-name-label", text: "What " + cloud + " calls it" }));
      menu.appendChild(picks);
    }
    menu.appendChild(el("label", { class: "cv-name-label", text: "Its name" }));
    menu.appendChild(input);
    menu.appendChild(same);
    menu.appendChild(el("div", { class: "connect-acts" }, [
      el("button", { type: "button", class: "btn small", text: "Cancel", onclick: closeContextMenu }),
      el("button", { type: "button", class: "btn small primary", text: "Place it", onclick: go }),
    ]));
    twin();
    placeChooser(menu, at ? at.x : undefined, at ? at.y : undefined);
    input.focus();
    input.select();
  }

  /* Placing: a part is a new record, a system is pinned, a view or an
   * account or a zone is a place on the diagram's file. Every one saves and
   * redraws, and selects what was placed. */
  function canvasPlace(item, into, at) {
    if (!cv) return;
    closeCanvasPicker();
    var mine = cv;
    if (item.kind === "part" && !item.named) {
      askPartName(item, into || [], at);
      return;
    }
    if (item.kind === "part") {
      setCanvasStatus("saving");
      api("/api/canvas/record", { part: item.id, into: into || [], name: item.named, product: item.chosen || "" }).then(function (res) {
        if (cv !== mine) return null;
        cv.made[res.id] = res.part;
        cv.focus = { id: res.id };
        pinsOf().push(res.id);
        if (at && at.group) canvasDropAt(res.id, at.group, { x: at.mx, y: at.my });
        return loadIndex().then(canvasSave).then(canvasDraw).then(function () {
          canvasSelect({ kind: "record", id: res.id });
          var where = saidInto(into || []);
          toast("ok", "Placed " + res.name, (where ? "In " + where + ". " : "") + "Saved in " + res.path + ".");
        });
      }).catch(function (err) { if (cv === mine) setCanvasStatus("failed", err.message); });
      return;
    }
    if (item.kind === "system") {
      if (pinsOf().indexOf(item.id) !== -1 || drawnHere(item.id)) {
        toast("ok", item.name + " is on it already");
        canvasSelect({ kind: "record", id: item.id });
        return;
      }
      pinsOf().push(item.id);
      cv.focus = { id: item.id };
      if (at && at.group) canvasDropAt(item.id, at.group, { x: at.mx, y: at.my });
      canvasSave().then(canvasDraw).then(function () {
        canvasSelect({ kind: "record", id: item.id });
        // Dropped into a boundary it does not sit in: that is a change to
        // the record, so it is asked, as a drag between boundaries is.
        if (at && at.group && state.cy) {
          var g = state.cy.getElementById(at.group), n = state.cy.getElementById(item.id);
          if (g.length && n.length && !n.ancestors().contains(g)) {
            canvasDropAt(item.id, at.group, { x: at.mx, y: at.my });
            openRegroupChooser(item.id, g, at.x, at.y);
          }
        }
      }).catch(fail);
      return;
    }
    var places = placesOf();
    var index;
    if (item.kind === "view") {
      index = indexOfPlace(item.id);
      if (index !== -1) {
        toast("ok", item.name + " is placed already");
        canvasSelect({ kind: "place", index: index });
        return;
      }
      places.push({ view: item.id });
      index = places.length - 1;
    } else {
      var net = cv.parts.network;
      var field = item.kind === "account" ? "cloud_account" : "network_zone";
      index = indexOfPlace(net);
      if (index === -1) {
        var only = {};
        only[field] = [item.value];
        places.push({ view: net, only: only });
        index = places.length - 1;
      } else {
        var p = places[index];
        if (p.only && p.only[field]) {
          if (p.only[field].indexOf(item.value) === -1) p.only[field].push(item.value);
        } else if (p.leave_out && (p.leave_out[field] || []).indexOf(item.value) !== -1) {
          p.leave_out[field] = p.leave_out[field].filter(function (v) { return v !== item.value; });
          if (!p.leave_out[field].length) delete p.leave_out[field];
          if (!Object.keys(p.leave_out).length) delete p.leave_out;
        } else {
          toast("ok", item.name + " is on it already", "It is part of " + placeTitle(p) + ", which is placed.");
          canvasSelect({ kind: "place", index: index });
          return;
        }
      }
    }
    canvasSave().then(canvasDraw).then(function () { canvasSelect({ kind: "place", index: index, stay: true }); }).catch(fail);
  }


  // What the rest of the app calls, and the two it reads live.
  var Canvas = app.Canvas;
  Canvas.closePicker = closeCanvasPicker;
  Canvas.dragOver = canvasDragOver;
  Canvas.draw = canvasDraw;
  Canvas.drop = canvasDrop;
  Canvas.dropAt = canvasDropAt;
  Canvas.focus = canvasFocus;
  Canvas.guides = canvasGuides;
  Canvas.guidesOff = canvasGuidesOff;
  Canvas.leave = leaveCanvas;
  Canvas.mark = canvasMark;
  Canvas.movedBox = canvasMovedBox;
  Canvas.movedGroup = canvasMovedGroup;
  Canvas.open = openCanvas;
  Canvas.openPicker = openCanvasPicker;
  Canvas.openShapes = openShapeMenu;
  Canvas.openLines = openLineMenu;
  Canvas.ownChanged = canvasOwnChanged;
  Canvas.ownDrawn = canvasOwnDrawn;
  Canvas.ownSelected = canvasOwnSelected;
  Canvas.pickAlso = canvasPickAlso;
  Canvas.picked = canvasPicked;
  Canvas.undo = canvasUndo;
  Canvas.save = canvasSave;
  Canvas.select = canvasSelect;
  Canvas.setTool = setCanvasTool;
  Canvas.settle = canvasSettle;
  Canvas.tap = canvasTap;
  Object.defineProperty(Canvas, "cv", { get: function () { return cv; } });
  Object.defineProperty(Canvas, "dragging", { get: function () { return cvDrag; } });
})(window.TerraneApp);
