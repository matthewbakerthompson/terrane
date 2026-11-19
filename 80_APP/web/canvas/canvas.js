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
        undo: [], redo: [], toolShape: "rectangle", file: data, page: 0 };
      if (viewId) state.viewId = viewId;
      state.selectedId = null;
      document.querySelector(".shell").classList.add("canvas-mode");
      $("cvTools").hidden = false;
      // The drawing tools are maxGraph's: the old canvas has none of them.
      $("cvTools").classList.toggle("no-own", !(Canvas.engine && Canvas.engine.enabled()));
      $("cvDetails").hidden = false;
      setCanvasTool("select");
      renderUndo();
      renderPages();
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
    closeKitPanel();
    closeShapeMenu();
    // The canvas's own model goes with it; a view drawn next is Cytoscape's.
    if (Canvas.engine) Canvas.engine.detach();
    document.querySelector(".shell").classList.remove("canvas-mode");
    ["cvTools", "cvChips", "cvEmpty", "cvDetails", "cvFold", "cvTip", "cvLayout", "cvStatus", "cvKeys", "cvGuideX", "cvGuideY", "cvFileDrop", "cvHint", "cvBar"]
      .forEach(function (id) { $(id).hidden = true; });
    // The group's outline is made the first time one is picked; the sheet
    // it sits on is the next view's too.
    if ($("cvGroup")) $("cvGroup").hidden = true;
    if ($("cvLayers")) { $("cvLayers").hidden = true; $("cvLayersBtn").setAttribute("aria-expanded", "false"); }
    if ($("cvPages")) $("cvPages").hidden = true;
    closePageMenu();
    Canvas.drawLayer = null;
    Canvas.inside = null;
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

  /* ---- pages (V16) ----
   * A diagram's first page is its file's top level, as every diagram's
   * one page always was; the rest are under `pages:`, each a key, a name
   * and what it has of its own (PAGE_FIELDS in terrane/query.py). The
   * canvas works on the page on the sheet as `cv.data`, the diagram's
   * fields with that page's own, and puts it back among the others when
   * the file is saved (`cv.file`). Undo is the page's: changing pages
   * starts it again. */
  var PAGE_FIELDS = ["places", "scope", "positions", "annotations", "groups", "locked"];

  // The page at `i` as the canvas works on it: the first is the file.
  function pageData(c, i) {
    if (!i) return c.file;
    var page = c.file.pages[i - 1], out = {};
    Object.keys(c.file).forEach(function (k) {
      if (PAGE_FIELDS.indexOf(k) === -1 && k !== "pages" && k !== "page") out[k] = c.file[k];
    });
    PAGE_FIELDS.forEach(function (k) { if (k in page) out[k] = JSON.parse(JSON.stringify(page[k])); });
    return out;
  }

  // The page on the sheet put back in its place in the file.
  function commitPage(c) {
    if (!c.page) return;
    var at = c.file.pages[c.page - 1];
    PAGE_FIELDS.forEach(function (k) { if (k in c.data) at[k] = c.data[k]; else delete at[k]; });
    Object.keys(c.data).forEach(function (k) { if (PAGE_FIELDS.indexOf(k) === -1) c.file[k] = c.data[k]; });
    Object.keys(c.file).forEach(function (k) {
      if (PAGE_FIELDS.indexOf(k) === -1 && k !== "pages" && k !== "page" && !(k in c.data)) delete c.file[k];
    });
  }

  // The whole file, as it is saved: the page on the sheet tidied as one
  // is, in its place among the others.
  function canvasFile(c) {
    var page = canvasData(c);
    if (!c.page) return page;
    commitPage(c);
    var file = JSON.parse(JSON.stringify(c.file)), at = file.pages[c.page - 1];
    PAGE_FIELDS.forEach(function (k) { if (k in page) at[k] = page[k]; else delete at[k]; });
    file.view_id = page.view_id;
    return file;
  }

  // Every page, first included, each its key (blank for the first), its
  // name and its own fields, for what reorders or copies them.
  function allPages(c) {
    commitPage(c);
    var first = { key: "", name: c.file.page || "Page 1" };
    PAGE_FIELDS.forEach(function (k) { if (k in c.file) first[k] = JSON.parse(JSON.stringify(c.file[k])); });
    return [first].concat((c.file.pages || []).map(function (p) { return JSON.parse(JSON.stringify(p)); }));
  }

  function freePageKey(list) {
    for (var n = 2; ; n += 1) if (!list.some(function (p) { return p.key === "page-" + n; })) return "page-" + n;
  }

  // The pages written back in this order, the one at `current` on the
  // sheet; a page moved out of first place takes a key.
  function setPages(c, list, current) {
    var file = c.file, first = list[0];
    PAGE_FIELDS.forEach(function (k) { if (k in first) file[k] = first[k]; else delete file[k]; });
    if (first.name && first.name !== "Page 1") file.page = first.name; else delete file.page;
    var rest = list.slice(1).map(function (p) {
      var out = { key: p.key || freePageKey(list), name: p.name };
      if (!p.key) p.key = out.key;
      PAGE_FIELDS.forEach(function (k) { if (k in p) out[k] = p[k]; });
      return out;
    });
    if (rest.length) file.pages = rest; else delete file.pages;
    showPage(current);
  }

  // A page put on the sheet, its own Undo begun.
  function showPage(i) {
    cv.page = i;
    cv.data = pageData(cv, i);
    cv.undo = [];
    cv.redo = [];
    cv.sel = null;
    Canvas.inside = null;
    renderUndo();
    renderPages();
    canvasSoon(0);
    // The diagram's own drawn again for this page: a sheet with no records
    // on either page is the same empty drawing, which the engine does not
    // draw anew, and the last page's shapes stayed on it.
    return canvasDraw().then(function () {
      if (!cv) return;
      if (Canvas.engine && Canvas.engine.live()) Canvas.engine.own(cv.data.annotations || []);
      canvasSelect(null);
    });
  }

  function switchPage(i) {
    if (!cv || i === cv.page) return Promise.resolve();
    commitPage(cv);
    return showPage(i);
  }

  function addPage() {
    if (!cv) return;
    var list = allPages(cv), key = freePageKey(list);
    list.push({ key: key, name: "Page " + (list.length + 1) });
    setPages(cv, list, list.length - 1);
  }

  // The tabs at the sheet's foot: one a page, the one on the sheet marked,
  // and + for one more.
  function renderPages() {
    var bar = $("cvPages");
    if (!bar) return;
    if (!cv) { bar.hidden = true; return; }
    bar.textContent = "";
    allPages(cv).forEach(function (p, i) {
      var tab = el("button", { type: "button", role: "tab", class: "cv-page" + (i === cv.page ? " is-on" : ""),
        "aria-selected": String(i === cv.page), "data-page": String(i), text: p.name });
      tab.addEventListener("click", function () { switchPage(i); });
      tab.addEventListener("dblclick", function () { if (i === cv.page) renamePage(tab, i); });
      tab.addEventListener("contextmenu", function (e) { e.preventDefault(); openPageMenu(tab, i); });
      bar.appendChild(tab);
    });
    bar.appendChild(el("button", { type: "button", class: "cv-page-add", "aria-label": "New page",
      title: "New page: one more sheet in this diagram's file, with its own shapes and its own records placed, "
        + "under the diagram's name and look. A record on two pages is one record.", onclick: addPage },
      [svgIcon("i-plus")]));
    bar.hidden = false;
  }

  function renamePage(tab, i) {
    closePageMenu();
    var list = allPages(cv), input = el("input", { type: "text", class: "cv-input cv-page-name", maxlength: "60",
      "aria-label": "The page's name" });
    input.value = list[i].name;
    tab.replaceWith(input);
    input.focus();
    input.select();
    var done = false;
    function keep() {
      if (done) return;
      done = true;
      var v = input.value.trim();
      if (v && v !== list[i].name) {
        list[i].name = v;
        setPagesKeepingSheet(list);
      } else renderPages();
    }
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); keep(); }
      if (e.key === "Escape") { e.preventDefault(); done = true; renderPages(); }
      e.stopPropagation();
    });
    input.addEventListener("blur", keep);
  }

  // The pages written back with the page on the sheet still on it, not
  // drawn again: a name changed moves nothing.
  function setPagesKeepingSheet(list) {
    var file = cv.file;
    if (list[0].name && list[0].name !== "Page 1") file.page = list[0].name; else delete file.page;
    (file.pages || []).forEach(function (p, i) { p.name = list[i + 1].name; });
    if (!cv.page) cv.data = file;
    renderPages();
    canvasSoon(0);
  }

  // A page's menu, over its tab: open, rename, duplicate, move it, delete.
  function openPageMenu(tab, i) {
    var menu = $("cvPageMenu");
    if (!menu || !cv) return;
    menu.textContent = "";
    var list = allPages(cv), confirming = false;
    function item(text, icon, act, disabled, key) {
      var b = el("button", { type: "button", role: "menuitem", class: "cv-page-item" }, [svgIcon(icon),
        el("span", { text: text }), key ? el("span", { class: "cv-page-key", text: key }) : null]);
      if (disabled) b.disabled = true;
      b.addEventListener("click", act);
      menu.appendChild(b);
      return b;
    }
    item("Open", "i-file-up", function () { closePageMenu(); switchPage(i); });
    item("Rename", "i-pencil", function () {
      closePageMenu();
      switchPage(i).then(function () {
        var t = document.querySelector('#cvPages .cv-page[data-page="' + i + '"]');
        if (t) renamePage(t, i);
      });
    }, false, "Double-click");
    item("Duplicate", "i-copy", function () {
      closePageMenu();
      var copy = JSON.parse(JSON.stringify(list[i]));
      copy.key = freePageKey(list);
      copy.name = ("Copy of " + list[i].name).slice(0, 60);
      list.splice(i + 1, 0, copy);
      setPages(cv, list, i + 1);
    });
    item("Move left", "i-arrow-left", function () { closePageMenu(); movePage(list, i, -1); }, i === 0);
    item("Move right", "i-arrow-right", function () { closePageMenu(); movePage(list, i, 1); }, i === list.length - 1);
    var gone = item("Delete the page", "i-x", function () {
      if (!confirming) {
        confirming = true;
        gone.querySelector("span").textContent = "Delete it and all on it";
        gone.classList.add("is-sure");
        return;
      }
      closePageMenu();
      list.splice(i, 1);
      setPages(cv, list, Math.max(0, cv.page === i ? i - 1 : cv.page > i ? cv.page - 1 : cv.page));
    }, list.length < 2);
    gone.classList.add("is-danger");
    var sheet = $("mapSheet").getBoundingClientRect(), b = tab.getBoundingClientRect();
    menu.style.left = Math.round(b.left - sheet.left) + "px";
    menu.hidden = false;
    menu.style.top = Math.round(b.top - sheet.top - menu.offsetHeight - 6) + "px";
    setTimeout(function () { document.addEventListener("pointerdown", closeOnPress, true); }, 0);
  }

  function closeOnPress(e) {
    var menu = $("cvPageMenu");
    if (menu && !menu.contains(e.target)) closePageMenu();
  }

  function closePageMenu() {
    var menu = $("cvPageMenu");
    if (menu) menu.hidden = true;
    document.removeEventListener("pointerdown", closeOnPress, true);
  }

  function movePage(list, i, step) {
    var to = i + step;
    if (to < 0 || to >= list.length) return;
    var moving = list.splice(i, 1)[0];
    list.splice(to, 0, moving);
    var current = cv.page === i ? to : cv.page === to ? i : cv.page;
    setPages(cv, list, current);
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
      return api("/api/canvas/save", { id: mine.id, data: canvasFile(mine) });
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
    // A guide's line or an equal gap first, axis by axis; else, with Snap
    // to grid on, the grid.
    var grid = snapOn() ? onGrid(n) : null, snap = from.snap || {};
    if (from.snap || grid) {
      n.position({ x: snap.x != null ? snap.x : grid ? grid.x : n.position("x"),
                   y: snap.y != null ? snap.y : grid ? grid.y : n.position("y") });
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
    return JSON.stringify({ annotations: cv.data.annotations || [], positions: cv.data.positions || null,
      locked: cv.data.locked || [], groups: cv.data.groups || [], layers: cv.data.layers || null });
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
    if ((then.locked || []).length) cv.data.locked = then.locked; else delete cv.data.locked;
    if ((then.groups || []).length) cv.data.groups = then.groups; else delete cv.data.groups;
    if (then.layers) cv.data.layers = then.layers; else delete cv.data.layers;
    Canvas.inside = null;
    renderLayers();
    applyLocks();
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

  /* ---- the status bar, under the sheet ----
   * Which of the two the diagram is, laid out or arranged by hand; what is
   * on it, records and its own; and Snap to grid, kept in this browser. */
  //: The grid, in the drawing's units, that Snap to grid puts things on.
  var GRID = 10;
  var SNAP_KEY = "aac.canvas.snap";
  var snapping = null;

  function snapOn() {
    if (snapping === null) {
      try { snapping = localStorage.getItem(SNAP_KEY) === "1"; } catch (e) { snapping = false; }
    }
    return snapping;
  }

  // Line jumps, on unless turned off: V14 draws the canvas with them.
  var JUMPS_KEY = "aac.canvas.jumps";
  var jumping = null;

  function jumpsOn() {
    if (jumping === null) {
      try { jumping = localStorage.getItem(JUMPS_KEY) !== "0"; } catch (e) { jumping = true; }
    }
    return jumping;
  }

  function toggleJumps() {
    jumping = !jumpsOn();
    try {
      if (jumping) localStorage.removeItem(JUMPS_KEY); else localStorage.setItem(JUMPS_KEY, "0");
    } catch (e) { /* private mode: for this page only */ }
    renderCanvasStatus();
  }

  function toggleSnap() {
    snapping = !snapOn();
    try {
      if (snapping) localStorage.setItem(SNAP_KEY, "1"); else localStorage.removeItem(SNAP_KEY);
    } catch (e) { /* private mode: on for this page only */ }
    renderCanvasStatus();
  }

  // On the grid: a box's corner on a line of it, as a drawing tool puts a
  // shape's.
  function onGrid(n) {
    var p = n.position(), w = n.width(), h = n.height();
    return { x: Math.round((p.x - w / 2) / GRID) * GRID + w / 2, y: Math.round((p.y - h / 2) / GRID) * GRID + h / 2 };
  }

  function renderCanvasStatus() {
    var bar = $("cvStatus");
    if (!bar) return;
    bar.hidden = !cv;
    if (!cv) return;
    var records = state.cy ? state.cy.nodes().filter(function (n) { return !n.isParent() && !n.data("isGroup"); }).length : 0;
    var own = (cv.data.annotations || []).length;
    var words = [];
    if (records) words.push(records === 1 ? "1 record" : records + " records");
    if (own) words.push(own + " of its own");
    var count = $("cvCount");
    count.textContent = "";
    if (words.length) {
      count.appendChild(svgIcon("i-blocks"));
      count.appendChild(el("span", { text: words.join(" \u00b7 ") }));
    }
    $("cvSnap").setAttribute("aria-pressed", snapOn() ? "true" : "false");
    $("cvJumps").setAttribute("aria-pressed", jumpsOn() ? "true" : "false");
    if (Canvas.engine && Canvas.engine.live()) {
      Canvas.engine.grid(snapOn() ? GRID : 0);
      Canvas.engine.jumps(jumpsOn());
    }
    applyLocks();
  }

  /* ---- locked on this diagram ----
   * A record or a shape of the diagram's own kept where it is here: not
   * carried, nudged, lined up or taken along by a frame until it is
   * unlocked. The diagram's file lists them under `locked:`, records by id
   * and its own by key; it changes nothing of the record. */
  function lockedHere() {
    return cv && Array.isArray(cv.data.locked) ? cv.data.locked : [];
  }

  function isLocked(name) {
    return lockedHere().indexOf(name) !== -1 || recordsLocked().indexOf(name) !== -1;
  }

  // Every record on the drawing, when the estate's place among the drawing
  // layers is locked.
  function recordsLocked() {
    var estate = cv && (cv.data.layers || []).filter(function (l) { return l.key === ESTATE_LAYER; })[0];
    if (!estate || !estate.locked || !state.cy) return [];
    return state.cy.nodes().filter(function (n) { return !n.data("isGroup"); }).map(function (n) { return n.id(); });
  }

  // Cytoscape will not carry what is not grabbable, and the engine's
  // pointer asks it; only what this made ungrabbable is made grabbable.
  function applyLocks() {
    var cy = state.cy, set = lockedHere().concat(recordsLocked());
    if (cy && cv) {
      cy.nodes().forEach(function (n) {
        if (set.indexOf(n.id()) !== -1) { n.ungrabify(); n.scratch("_locked", true); }
        else if (n.scratch("_locked")) { n.grabify(); n.removeScratch("_locked"); }
      });
    }
    if (Canvas.engine && Canvas.engine.live()) Canvas.engine.lock(set);
  }

  function setLocked(list, on) {
    if (!cv || !list.length) return;
    remember();
    var now = lockedHere().slice();
    list.forEach(function (x) {
      var at = now.indexOf(x);
      if (on && at === -1) now.push(x);
      if (!on && at !== -1) now.splice(at, 1);
    });
    if (now.length) cv.data.locked = now.sort(); else delete cv.data.locked;
    applyLocks();
    canvasSoon(0);
    if (cv.sel) canvasSelect(cv.sel, true);
  }

  function pickedNames() {
    var keys = Canvas.engine && Canvas.engine.live() ? Canvas.engine.selected() : [];
    return pickedIds(cv && cv.sel).concat(keys);
  }

  function toggleLockPicked() {
    var all = cv ? pickedNames() : [];
    if (!all.length) return false;
    setLocked(all, !all.every(isLocked));
    return true;
  }

  // Lock it here, or Unlock, for the panel of what is picked.
  function lockButton(list) {
    var on = list.length > 0 && list.every(isLocked);
    return el("button", { type: "button", class: "btn small", "aria-pressed": String(on),
      title: on ? "Let it move again on this diagram" : "Keep it where it is on this diagram (Ctrl+Shift+L)",
      onclick: function () { setLocked(list, !on); } },
      [svgIcon(on ? "i-lock-open" : "i-lock"), el("span", { text: on ? "Unlock" : "Lock it here" })]);
  }

  function lockedNote(list) {
    return list.length && list.every(isLocked) ? el("p", { class: "cv-small cv-locked" }, [svgIcon("i-lock"),
      el("span", { text: (list.length === 1 ? "Locked" : "All locked") + " on this diagram: it stays where it is until "
        + "it is unlocked." })]) : null;
  }

  function renderCanvasLayout() {
    renderCanvasStatus();
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
    // Or where its gap to a box in line with it is the next gap along, or
    // the same both sides: the nearer of the two wins an axis, and the
    // gaps are measured on the sheet as V14 draws them.
    // Bodies, not bounding boxes: a box carried or picked is drawn with a
    // wider outline, and measured by it the gap came out units off.
    var body = function (s) {
      var q = s.position(), w = s.width(), h = s.height();
      return { x1: q.x - w / 2, x2: q.x + w / 2, y1: q.y - h / 2, y2: q.y + h / 2, w: w, h: h };
    };
    var nb = body(n);
    var boxes = frameKids(cy, parent.length ? parent : null).filter(function (s) {
      return s !== n && !s.data("isGroup");
    }).map(body);
    var even = { x: evenGap(boxes, nb, "x", reach), y: evenGap(boxes, nb, "y", reach) };
    if (even.x && (best.x === null || even.x.d < best.dx)) { best.x = even.x.start + nb.w / 2; best.dx = even.x.d; best.sx = null; }
    else even.x = null;
    if (even.y && (best.y === null || even.y.d < best.dy)) { best.y = even.y.start + nb.h / 2; best.dy = even.y.d; best.sy = null; }
    else even.y = null;
    from.snap = best.x === null && best.y === null ? null : { x: best.x, y: best.y };
    var cr = $("cy").getBoundingClientRect(), sr = $("mapSheet").getBoundingClientRect();
    var ox = cr.left - sr.left, oy = cr.top - sr.top;
    measureGaps([even.x, even.y], z, pan, ox, oy);
    var gx = $("cvGuideX"), gy = $("cvGuideY");
    if (best.sx) {
      var y1 = Math.min(p.y, best.sx.y) - 30, y2 = Math.max(p.y, best.sx.y) + 30;
      gx.style.left = Math.round(ox + best.x * z + pan.x) + "px";
      gx.style.top = Math.round(oy + y1 * z + pan.y) + "px";
      gx.style.height = Math.round((y2 - y1) * z) + "px";
    }
    if (best.sy) {
      var x1 = Math.min(p.x, best.sy.x) - 60, x2 = Math.max(p.x, best.sy.x) + 60;
      gy.style.top = Math.round(oy + best.y * z + pan.y) + "px";
      gy.style.left = Math.round(ox + x1 * z + pan.x) + "px";
      gy.style.width = Math.round((x2 - x1) * z) + "px";
    }
    gx.hidden = !best.sx;
    gy.hidden = !best.sy;
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
    measureGaps([]);
  }

  /* Along one axis ("y", a column; "x", a row), where the box `nb` would
   * start for its gap to the nearest box in line with it to be the gap
   * that box has to the next, before it or after it, or for it to sit
   * midway between the two nearest: the nearest of those within `reach`,
   * with the two gaps it makes, each from and to along the axis and where
   * across it the measure goes. Boxes in line overlap it across the axis. */
  function evenGap(boxes, nb, a, reach) {
    var o = a === "y" ? "x" : "y", lo = a + "1", hi = a + "2", olo = o + "1", ohi = o + "2";
    var size = nb[hi] - nb[lo];
    var line = boxes.filter(function (b) { return b[ohi] > nb[olo] && b[olo] < nb[ohi]; });
    var before = line.filter(function (b) { return b[hi] <= nb[lo] + reach; })
      .sort(function (p, q) { return q[hi] - p[hi]; });
    var after = line.filter(function (b) { return b[lo] >= nb[hi] - reach; })
      .sort(function (p, q) { return p[lo] - q[lo]; });
    var ways = [];
    function side(boxes2) {
      return Math.max.apply(null, [nb[ohi]].concat(boxes2.map(function (b) { return b[ohi]; })));
    }
    if (before.length > 1) {
      var g1 = before[0][lo] - before[1][hi];
      if (g1 > 0) ways.push({ start: before[0][hi] + g1, gap: g1, across: side([before[0], before[1]]),
        marks: [[before[1][hi], before[0][lo]], [before[0][hi], before[0][hi] + g1]] });
    }
    if (after.length > 1) {
      var g2 = after[1][lo] - after[0][hi];
      if (g2 > 0) ways.push({ start: after[0][lo] - g2 - size, gap: g2, across: side([after[0], after[1]]),
        marks: [[after[0][lo] - g2, after[0][lo]], [after[0][hi], after[1][lo]]] });
    }
    if (before.length && after.length) {
      var g3 = (after[0][lo] - before[0][hi] - size) / 2;
      if (g3 > 0) ways.push({ start: before[0][hi] + g3, gap: g3, across: side([before[0], after[0]]),
        marks: [[before[0][hi], before[0][hi] + g3], [after[0][lo] - g3, after[0][lo]]] });
    }
    var best = null;
    ways.forEach(function (w) {
      var d = Math.abs(w.start - nb[lo]);
      if (d <= reach && (!best || d < best.d)) { best = w; best.d = d; }
    });
    if (best) best.axis = a;
    return best;
  }

  /* The red measures of equal gaps, each with its size in units, beside
   * the boxes they space; none when the list is empty. */
  function measureGaps(evens, z, pan, ox, oy) {
    var sheet = $("mapSheet");
    if (!sheet) return;
    Array.prototype.slice.call(sheet.querySelectorAll(".cv-gap")).forEach(function (m) { m.remove(); });
    evens.forEach(function (e) {
      if (!e) return;
      e.marks.forEach(function (span) {
        var down = e.axis === "y", at = e.across + 10 / z;
        var m = el("div", { class: "cv-gap " + (down ? "is-y" : "is-x"), "aria-hidden": "true" },
          [el("span", { class: "cv-gap-n num", text: String(Math.round(e.gap)) })]);
        if (down) {
          m.style.left = Math.round(ox + at * z + pan.x) + "px";
          m.style.top = Math.round(oy + span[0] * z + pan.y) + "px";
          m.style.height = Math.max(1, Math.round((span[1] - span[0]) * z)) + "px";
        } else {
          m.style.top = Math.round(oy + at * z + pan.y) + "px";
          m.style.left = Math.round(ox + span[0] * z + pan.x) + "px";
          m.style.width = Math.max(1, Math.round((span[1] - span[0]) * z)) + "px";
        }
        sheet.appendChild(m);
      });
    });
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
    else if (sel.kind === "own" && pickedGroup(sel.keys)) canvasGroupDetails(box, pickedGroup(sel.keys));
    else if (sel.kind === "own" && sel.keys.length === 1 && swimOf(sel.keys[0])) canvasSwimDetails(box, sel.keys[0]);
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
    if (tool === "shape" && shape === "swimlane") return "Drag the swimlane's size, or click for one of three lanes: "
      + "what is drawn in a lane moves with it. Esc stops.";
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
  // A value as JSON with every mapping's keys in order: the engine writes
  // an item's fields in another order than the file holds them, and the
  // same list compared as text was a change.
  function canonical(value) {
    return JSON.stringify(value, function (k, v) {
      if (!v || typeof v !== "object" || Array.isArray(v)) return v;
      return Object.keys(v).sort().reduce(function (o, key) { o[key] = v[key]; return o; }, {});
    });
  }

  function canvasOwnChanged(list) {
    if (!cv) return;
    // A change that changes nothing is no step for Undo and nothing to
    // save: maxGraph says one for a press on a shape locked here, and one
    // Undo after it undid nothing.
    if (canonical(list) === canonical(cv.data.annotations || [])) return;
    // Lining several up says itself as one step, before it moves them.
    if (!cv.holdUndo) remember();
    if (list.length) cv.data.annotations = list; else delete cv.data.annotations;
    if (cv.data.groups) setTimeout(tidyGroups, 0);
    renderLayers();
    if (list.length) arrangeForOwn();
    $("cvEmpty").hidden = !canvasEmpty();
    renderCanvasStatus();
    canvasSoon(0);
    // The panel follows the change, unless the change is being typed in it.
    var typing = document.activeElement && /^(TEXTAREA|INPUT)$/.test(document.activeElement.tagName)
      && $("cvDetails").contains(document.activeElement);
    if (cv.sel && (cv.sel.kind === "own" || cv.sel.kind === "several") && !typing) canvasSelect(cv.sel, true);
    else renderBar();
  }

  function canvasOwnSelected(keys, additive) {
    if (!cv || cv.picking) return;
    // Painting a look copied (Copy the look): one of its own clicked takes
    // it. Only a click comes this way; a band dragged round several, or a
    // pick made by code, goes to canvasPicked and paints nothing.
    if (Canvas.painting && keys.length === 1 && !additive && keys[0] !== Canvas.painting.from) {
      paintOnto(widen(keys), Canvas.painting.look);
    }
    if (!additive && !keys.length && (!cv.sel || (cv.sel.kind !== "own" && cv.sel.kind !== "several"))) return;
    keys = widen(additive ? notDropped(pickedKeys(cv.sel), keys) : keys);
    canvasPick(additive ? pickedIds(cv.sel) : [], keys);
  }

  /* ---- groups (V16) ----
   * The diagram's own picked and moved as one. A group is a name kept in
   * the diagram's file (`groups:`, each a key, a name and the group it
   * sits in, if any), and each of its own in one says so (`group:`). It
   * has no box of its own, so nothing draws it: picked, its outline and
   * its name show over the drawing, as the bar over several does. A pick
   * of one in a group picks the group whole, at the level the pick is at:
   * a double-click goes inside it, and Esc comes back out. It is not a
   * maxGraph parent: frames are those, and a group may sit in a frame and
   * hold one, which a parent of the frame's could not. */
  function groupsOf() { return (cv && cv.data.groups) || []; }
  function groupByKey(key) { return groupsOf().filter(function (g) { return g.key === key; })[0] || null; }

  // The groups a group sits in, it first and the outermost last.
  function chainOf(group) {
    var out = [], g = group;
    while (g && out.indexOf(g) === -1) {
      out.push(g);
      var e = groupByKey(g);
      g = e && e.group;
    }
    return out;
  }

  function groupOf(key) {
    var eng = Canvas.engine, a = eng && eng.live() ? eng.item(key) : null;
    return a && a.group && groupByKey(a.group) ? a.group : null;
  }

  // What a pick of `key` picks: the group just inside the one gone into,
  // the outermost when none is, or the thing itself.
  function unitOf(key) {
    var chain = chainOf(groupOf(key));
    if (!chain.length) return { key: key };
    var at = Canvas.inside ? chain.indexOf(Canvas.inside) : -1;
    if (at === 0) return { key: key };
    return { group: at > 0 ? chain[at - 1] : chain[chain.length - 1] };
  }

  // Every one of its own a group holds, at any depth.
  function membersOf(group) {
    return (cv.data.annotations || []).filter(function (a) {
      return a.role !== "line" && a.group && chainOf(a.group).indexOf(group) !== -1;
    }).map(function (a) { return a.key; });
  }

  function widen(keys) {
    // Out of a group gone into when nothing picked is in it.
    if (Canvas.inside && !keys.some(function (k) { return chainOf(groupOf(k)).indexOf(Canvas.inside) !== -1; })) {
      Canvas.inside = null;
    }
    var out = [];
    keys.forEach(function (k) {
      var u = unitOf(k);
      (u.group ? membersOf(u.group) : [k]).forEach(function (m) { if (out.indexOf(m) === -1) out.push(m); });
    });
    return out;
  }

  // A Shift-click on one of a group picked takes the whole group out, or
  // widening would put back the one maxGraph took.
  function notDropped(before, keys) {
    var drop = [];
    before.forEach(function (k) {
      if (keys.indexOf(k) !== -1) return;
      var u = unitOf(k);
      (u.group ? membersOf(u.group) : [k]).forEach(function (m) { drop.push(m); });
    });
    return keys.filter(function (k) { return drop.indexOf(k) === -1; });
  }

  // The group picked whole, if what is picked is exactly one.
  function pickedGroup(keys) {
    if (!keys || keys.length < 2) return null;
    var u = unitOf(keys[0]);
    if (!u.group) return null;
    var all = membersOf(u.group);
    return all.length === keys.length && all.every(function (k) { return keys.indexOf(k) !== -1; }) ? u.group : null;
  }

  function newGroupKey() {
    var n = 0;
    groupsOf().forEach(function (g) {
      var m = /^group-(\d+)$/.exec(g.key);
      if (m) n = Math.max(n, Number(m[1]));
    });
    return "group-" + (n + 1);
  }

  // What a pick groups: each picked thing at its level, a group as one.
  function unitsOf(keys) {
    var eng = Canvas.engine, out = [];
    keys.forEach(function (k) {
      var a = eng.item(k);
      // A lane is grouped with its swimlane, never on its own.
      if (!a || a.role === "line" || a.role === "lane") return;
      var u = unitOf(k), id = u.group ? "g:" + u.group : "k:" + k;
      if (out.indexOf(id) === -1) out.push(id);
    });
    return out;
  }

  function groupThem() {
    var eng = Canvas.engine && Canvas.engine.live() ? Canvas.engine : null;
    if (!cv || !eng || !cv.sel || cv.sel.kind !== "own") return false;
    var keys = cv.sel.keys.slice(), units = unitsOf(keys);
    if (units.length < 2) return false;
    var key = newGroupKey(), entry = { key: key, name: "Group " + key.split("-")[1] };
    if (Canvas.inside) entry.group = Canvas.inside;
    remember();
    cv.holdUndo = true;
    try {
      cv.data.groups = groupsOf().concat([entry]);
      eng.together(function () {
        units.forEach(function (u) {
          if (u.indexOf("g:") === 0) groupByKey(u.slice(2)).group = key;
          else eng.update(u.slice(2), { group: key });
        });
      });
    } finally {
      cv.holdUndo = false;
    }
    canvasSoon(0);
    canvasPick([], widen(keys));
    return true;
  }

  // A group let go: what was in it goes into the group it sat in, if any.
  function letGo(entry) {
    var eng = Canvas.engine, parent = entry.group || null;
    groupsOf().forEach(function (o) {
      if (o.group === entry.key) { if (parent) o.group = parent; else delete o.group; }
    });
    var held = (cv.data.annotations || []).filter(function (a) { return a.group === entry.key; });
    cv.data.groups = groupsOf().filter(function (o) { return o.key !== entry.key; });
    if (!cv.data.groups.length) delete cv.data.groups;
    if (held.length && eng && eng.live()) {
      eng.together(function () { held.forEach(function (a) { eng.update(a.key, { group: parent }); }); });
    }
  }

  function ungroup(group) {
    var entry = groupByKey(group);
    if (!cv || !entry) return false;
    var keys = membersOf(group);
    remember();
    cv.holdUndo = true;
    try { letGo(entry); } finally { cv.holdUndo = false; }
    canvasSoon(0);
    canvasPick([], keys);
    return true;
  }

  function ungroupPicked() {
    var g = cv && cv.sel && cv.sel.kind === "own" ? pickedGroup(cv.sel.keys) : null;
    return g ? ungroup(g) : false;
  }

  /* A group holding fewer than two things lets them go, and one its own
   * name a group the file does not have is let out: a delete that left one
   * in a group, or a duplicate of one of a group, alone in its copy. The
   * step it makes is the one that caused it, for Undo. */
  function tidyGroups() {
    var eng = Canvas.engine && Canvas.engine.live() ? Canvas.engine : null;
    if (!cv || !eng) return;
    cv.holdUndo = true;
    try {
      for (var pass = 0; pass < 8; pass += 1) {
        var count = {};
        groupsOf().forEach(function (g) { count[g.key] = 0; });
        var strays = [];
        (cv.data.annotations || []).forEach(function (a) {
          if (!a.group) return;
          if (a.group in count) count[a.group] += 1; else strays.push(a.key);
        });
        groupsOf().forEach(function (g) { if (g.group && g.group in count) count[g.group] += 1; });
        var gone = groupsOf().filter(function (g) { return count[g.key] < 2; });
        if (strays.length) eng.together(function () { strays.forEach(function (k) { eng.update(k, { group: null }); }); });
        if (!gone.length && !strays.length) break;
        gone.forEach(letGo);
      }
    } finally {
      cv.holdUndo = false;
    }
  }

  // A double-click on one in a group picked whole goes inside it (engine.js).
  function canvasGoIn(key) {
    var eng = Canvas.engine, g = cv && cv.sel && cv.sel.kind === "own" ? pickedGroup(cv.sel.keys) : null;
    if (!eng || !g || membersOf(g).indexOf(key) === -1) return false;
    Canvas.inside = g;
    canvasPick([], widen([key]));
    return true;
  }

  // Esc inside a group comes out of it, the group picked whole again.
  function goOut() {
    var g = Canvas.inside;
    if (!g) return false;
    var entry = groupByKey(g);
    Canvas.inside = entry && entry.group ? entry.group : null;
    canvasPick([], widen(membersOf(g)));
    return true;
  }

  // The copy of a group a duplicate or a paste puts its copies in, made the
  // first time one asks, named as the group copied; set going and stopped
  // round each (Canvas.regroup), so nothing else makes one.
  function groupKeyFor(old) {
    var r = Canvas.regroup;
    if (!r || !old) return null;
    if (r.made[old]) return r.made[old];
    var src = (r.from || []).filter(function (g) { return g.key === old; })[0];
    var key = newGroupKey(), entry = { key: key, name: src ? src.name : "Group " + key.split("-")[1] };
    r.made[old] = key;
    cv.data.groups = groupsOf().concat([entry]);
    var parent = src && src.group ? groupKeyFor(src.group) : null;
    if (parent) entry.group = parent;
    return key;
  }

  function regrouping(from, fn) {
    Canvas.regroup = { from: from || [], made: {} };
    try { return fn(); } finally { Canvas.regroup = null; }
  }

  //: A count said in words, for the group's panel.
  var COUNT_WORDS = ["None", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven",
    "Twelve"];

  // A group picked whole (V16): its name, what is in it, and Ungroup.
  function canvasGroupDetails(box, group) {
    var eng = Canvas.engine, entry = groupByKey(group), keys = membersOf(group);
    box.appendChild(el("span", { class: "cv-badge is-own", text: "Group \u00b7 on this diagram only" }));
    box.appendChild(el("h2", { class: "cv-h", text: entry.name }));
    box.appendChild(el("p", { class: "cv-lede", text: (COUNT_WORDS[keys.length] || String(keys.length))
      + " of the diagram's own, picked, moved and turned as one. A group has no box; its name is shown only while it is "
      + "picked." }));
    var name = el("input", { type: "text", class: "cv-input", maxlength: "60", "aria-label": "Its name" });
    name.value = entry.name;
    name.addEventListener("change", function () {
      var v = name.value.trim();
      if (!v || v === entry.name) { name.value = entry.name; return; }
      remember();
      entry.name = v;
      canvasSoon(0);
      canvasSelect(cv.sel, true);
    });
    box.appendChild(cvField("Name", name));
    box.appendChild(el("p", { class: "cv-label", text: "In it" }));
    var list = el("div", { class: "cv-picks" });
    // What it holds as it was put in: its own, and the groups inside it.
    groupsOf().filter(function (g) { return g.group === group; }).forEach(function (g) {
      list.appendChild(el("button", { type: "button", class: "cv-pick is-own", onclick: function () {
        Canvas.inside = group;
        canvasPick([], membersOf(g.key));
      } }, [el("span", { class: "cv-pick-dot", "aria-hidden": "true" }), el("span", { class: "cv-pick-n", text: g.name }),
        el("span", { class: "cv-pick-id", text: "a group in it" })]));
    });
    (cv.data.annotations || []).filter(function (a) { return a.group === group; }).forEach(function (a) {
      list.appendChild(el("button", { type: "button", class: "cv-pick is-own", onclick: function () {
        Canvas.inside = group;
        canvasPick([], [a.key]);
      } }, [el("span", { class: "cv-pick-dot", "aria-hidden": "true" }),
        el("span", { class: "cv-pick-n", text: firstLine(a.label) || (a.role === "shape" ? shapeName(a.shape) : ROLE_WORDS[a.role]) }),
        el("span", { class: "cv-pick-id", text: "its own " + a.role })]));
    });
    box.appendChild(list);
    box.appendChild(el("p", { class: "cv-small cv-keyline", text: "Double-click to go in \u00b7 Esc comes out \u00b7 "
      + "Ctrl+Shift+U ungroups" }));
    // Turned as one about its middle, by the degrees said, either way.
    var by = el("input", { type: "number", class: "cv-input cv-turn-by", min: "1", max: "180", step: "15",
      "aria-label": "Degrees to turn it by" });
    by.value = "90";
    var turnBy = function (sign) {
      var d = Math.max(1, Math.min(180, Math.round(Number(by.value) || 90)));
      if (eng) eng.turnTogether(keys, sign * d);
    };
    box.appendChild(section("Turned", hint("about its middle, as one"), [el("div", { class: "cv-turn-row" }, [
      cvField("Degrees", by),
      el("button", { type: "button", class: "btn small", onclick: function () { turnBy(-1); } },
        [svgIcon("i-rotate-ccw"), el("span", { text: "Turn left" })]),
      el("button", { type: "button", class: "btn small", onclick: function () { turnBy(1); } },
        [svgIcon("i-rotate-cw"), el("span", { text: "Turn right" })]),
    ])]));
    box.appendChild(el("div", { class: "cv-acts" }, [
      el("button", { type: "button", class: "btn small", onclick: function () { ungroup(group); } },
        [svgIcon("i-ungroup"), el("span", { text: "Ungroup" })]),
      lockButton(keys),
      el("button", { type: "button", class: "btn small", onclick: function () { if (eng) eng.remove(keys); } },
        [svgIcon("i-x"), el("span", { text: "Delete" })]),
    ]));
    var held = lockedNote(keys);
    if (held) box.appendChild(held);
    box.appendChild(el("p", { class: "cv-small", text: "Its look is each shape's own; Copy the look on a group copies "
      + "the look of the first in it." }));
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
    canvasPick(ids, widen(keys));
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
    ["frame", "i-frame", "Put a frame around them (Ctrl+G)"], ["group", "i-group", "Group them (Ctrl+Shift+G)"],
  ];

  /* The bar, over what is picked when it is more than one thing: on the
   * sheet above them, where the eye already is. */
  function renderBar() {
    if (Canvas.engine && Canvas.engine.live()) Canvas.engine.stretches();
    var bar = $("cvBar");
    if (!bar) return;
    var sel = cv && cv.sel, cy = state.cy;
    var items = sel && cy ? pickedBoxes(sel) : [];
    // A group picked whole shows its outline and its name, not the bar.
    var group = sel && sel.kind === "own" ? pickedGroup(sel.keys) : null;
    renderGroupOutline(group, items, group ? null : lanePicked(sel));
    if (items.length < 2 || group) { bar.hidden = true; return; }
    if (!bar.childNodes.length) {
      BAR.forEach(function (b) {
        if (!b) { bar.appendChild(el("span", { class: "sep", "aria-hidden": "true" })); return; }
        bar.appendChild(el("button", { type: "button", class: "cv-bar-b", "data-do": b[0], title: b[2], "aria-label": b[2],
          onclick: function () { arrangePicked(b[0]); } }, [svgIcon(b[1])]));
      });
    }
    // Only the diagram's own group, two things or more at their level.
    Array.prototype.forEach.call(bar.querySelectorAll('[data-do="group"]'), function (b) {
      b.disabled = !sel || sel.kind !== "own" || unitsOf(sel.keys).length < 2;
    });
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

  // A group's outline and its name, over the drawing while it is picked:
  // the group has no box of its own to draw.
  // A lane picked alone: its place among its swimlane's lanes, and how
  // many there are.
  function lanePicked(sel) {
    var a = sel && sel.kind === "own" && sel.keys.length === 1 ? swimOf(sel.keys[0]) : null;
    if (!a || a.role !== "lane" || !(a.in || []).length) return null;
    var all = Canvas.engine.lanes(a.in[a.in.length - 1]);
    var at = all.map(function (l) { return l.key; }).indexOf(a.key);
    return at < 0 ? null : "Lane " + (at + 1) + " of " + all.length;
  }

  function renderGroupOutline(group, items, lane) {
    var sheet = $("mapSheet"), out = $("cvGroup");
    if ((!group && !lane) || !items.length || !state.cy || !sheet) { if (out) out.hidden = true; return; }
    if (!out) {
      out = el("div", { id: "cvGroup", class: "cv-gathered", "aria-hidden": "true" }, [
        el("span", { class: "cv-gathered-tag" })]);
      sheet.appendChild(out);
    }
    var tag = out.querySelector(".cv-gathered-tag");
    tag.textContent = "";
    tag.appendChild(svgIcon(lane ? "i-table" : "i-group"));
    tag.appendChild(el("span", { class: "cv-gathered-name" }));
    // A lane's own outline is maxGraph's, picked: the tab is all it adds.
    out.classList.toggle("is-lane", !!lane);
    var entry = group ? groupByKey(group) : null, u = unionOf(items), cy = state.cy, z = cy.zoom(), pan = cy.pan();
    var cr = $("cy").getBoundingClientRect(), sr = sheet.getBoundingClientRect(), pad = lane ? 0 : 8;
    out.querySelector(".cv-gathered-name").textContent = lane || (entry ? entry.name : "") + " \u00b7 " + membersOf(group).length;
    out.style.left = Math.round(cr.left - sr.left + u.x1 * z + pan.x - pad) + "px";
    out.style.top = Math.round(cr.top - sr.top + u.y1 * z + pan.y - pad) + "px";
    out.style.width = Math.round((u.x2 - u.x1) * z + 2 * pad) + "px";
    out.style.height = Math.round((u.y2 - u.y1) * z + 2 * pad) + "px";
    out.hidden = false;
  }

  /* Lined up, spread or framed: each record moved where it is kept, each
   * of the diagram's own by maxGraph, one step for Undo, and saved. */
  function arrangePicked(how) {
    if (!cv || !state.cy) return;
    var items = pickedBoxes(cv.sel);
    if (items.length < 2) return;
    if (how === "frame") { frameThem(); return; }
    if (how === "group") { groupThem(); return; }
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
    moves = moves.filter(function (m) {
      return (Math.abs(m.dx) >= 0.5 || Math.abs(m.dy) >= 0.5) && !isLocked(m.item.id || m.item.key);
    });
    if (!moves.length) return;
    remember();
    cv.holdUndo = true;
    try {
      moveRecords(moves.filter(function (m) { return m.item.id; }).map(function (m) {
        return { id: m.item.id, dx: m.dx, dy: m.dy };
      }));
      var own = moves.filter(function (m) { return m.item.key; });
      if (own.length) Canvas.engine.moveEach(own.map(function (m) { return { key: m.item.key, dx: m.dx, dy: m.dy }; }));
    } finally {
      cv.holdUndo = false;
    }
    canvasSoon(0);
    renderBar();
  }

  // Records moved where they are kept, the lines routed again around them.
  function moveRecords(records) {
    var cy = state.cy;
    if (!records.length || !cy) return;
    records.forEach(function (m) {
      var n = cy.getElementById(m.id), p = n.position();
      n.position({ x: p.x + m.dx, y: p.y + m.dy });
    });
    if (!canvasKept()) { cv.data.positions = keepAll(cy); rebaseOwn(); }
    else records.forEach(function (m) { keepLeaf(cy, cy.getElementById(m.id), cv.data.positions); });
    rerouteInPlace(cy);
    renderCanvasLayout();
  }

  // The records picked now, which a drag moves itself (engine.js).
  function canvasPickedIds() {
    return cv ? pickedIds(cv.sel) : [];
  }

  /* The records a frame was drawn round, moved with it (engine.js): in the
   * step its own move made for Undo, which already holds where they were. */
  function canvasRecordsMoved(ids, dx, dy) {
    if (!cv || !state.cy) return;
    var here = ids.filter(function (id) { return state.cy.getElementById(id).length && !isLocked(id); });
    if (!here.length) return;
    cv.holdUndo = true;
    try {
      moveRecords(here.map(function (id) { return { id: id, dx: dx, dy: dy }; }));
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
      + ": line them up, spread them, frame them" + (sel.ids.length ? "." : " or group them.")
      + (sel.ids.length ? " Their fields stay their own, each in its record's panel." : "") }));
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
        el("span", { class: "cv-pick-n", text: firstLine(a.label) || (a.role === "shape" ? shapeName(a.shape) : ROLE_WORDS[a.role]) }),
        el("span", { class: "cv-pick-id", text: "its own " + a.role }),
      ]));
    });
    box.appendChild(list);
    var acts = [el("button", { type: "button", class: "btn small", onclick: frameThem },
      [svgIcon("i-frame"), el("span", { text: "Put a frame around them" })]), lockButton(sel.ids.concat(sel.keys))];
    // The diagram's own group; a record is the estate's, and stays out.
    if (!sel.ids.length && unitsOf(sel.keys).length >= 2) {
      acts.unshift(el("button", { type: "button", class: "btn small primary", onclick: groupThem },
        [svgIcon("i-group"), el("span", { text: "Group them" })]));
    }
    if (sel.keys.length) {
      acts.push(el("button", { type: "button", class: "btn small", onclick: function () { if (eng) eng.remove(sel.keys); } },
        [svgIcon("i-x"), el("span", { text: sel.ids.length ? "Delete its own" : "Delete them" })]));
    }
    box.appendChild(el("div", { class: "cv-acts" }, acts));
    box.appendChild(el("p", { class: "cv-small", text: (sel.ids.length ? "" : "A group has no box of its own. It is "
      + "picked, moved, copied and turned as one, and a double-click goes inside it to pick one of it. ")
      + "A frame is this diagram's own, drawn under what it is around. "
      + "What is inside it moves with it, its own and the records, and a frame sets no field the way "
      + "dropping a box into a boundary does; a group can sit in a frame, and a frame in a group." }));
    box.appendChild(el("p", { class: "cv-small cv-keyline", text: "Drag across the sheet to pick several \u00b7 Shift-click "
      + "adds or takes one \u00b7 the arrows nudge them, Shift by ten \u00b7 Ctrl+G frames them \u00b7 Ctrl+Shift+G groups "
      + "them \u00b7 Space and drag, "
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
      : shape === "swimlane" ? "M0 0H28V20H0Z M0 5H28 M0 12.5H28 M8 5V20"
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
      // A swimlane, the last of them (V16): a pool of lanes.
      menu.appendChild(el("button", { type: "button", role: "menuitem", class: "cv-shape-item",
        "aria-pressed": String(cv.tool === "shape" && cv.toolShape === "swimlane"),
        onclick: function () { closeShapeMenu(); setCanvasTool("shape", "swimlane"); } },
        [shapePicture("swimlane"), el("span", { text: "Swimlane" })]));
    }
    menu.style.left = ($("cvTools").offsetLeft + $(from).offsetLeft) + "px";
    menu.hidden = false;
    menuFor = from;
    $(from).setAttribute("aria-expanded", "true");
    var first = menu.querySelector("button");
    if (first) first.focus();
  }

  var ROLE_WORDS = { note: "Note", text: "Text", frame: "Frame", line: "Line", pool: "Swimlane", lane: "Lane" };
  // What a thing of the diagram's own is called in a list: a shape's first
  // line of words, its name, without the caption under it.
  function firstLine(label) {
    return String(label || "").split("\n").filter(function (p) { return p.trim(); })[0] || "";
  }

  var FILL_WORDS = { yellow: "Yellow", mint: "Mint", lavender: "Lavender", rose: "Rose", white: "Paper", stone: "Stone",
    accent: "Accent, for what the drawing is about", none: "No fill" };
  //: A fill each kind of thing starts with, as the engine draws it; a frame
  //: starts with none.
  var ROLE_FILL = { note: "yellow", shape: "white" };

  // An end of a line, said: a record by its name, a shape by its words.
  function endWords(end) {
    if (Array.isArray(end)) return "a point on the sheet";
    var it = Canvas.engine.item(end);
    if (it) return firstLine(it.label) ? "\u201c" + firstLine(it.label) + "\u201d" : (it.role === "shape" ? shapeName(it.shape) : ROLE_WORDS[it.role]).toLowerCase();
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

  // The providers' and vendors' marks a tile can carry, the ones a record
  // carries (GET /api/icons), asked for once.
  var markList = null;
  function marks() {
    if (!markList) {
      markList = api("/api/icons").then(function (r) { return r.marks || []; },
        function (err) { markList = null; throw err; });
    }
    return markList;
  }

  // A shape's Icon field as a tile: the plain icons or a provider's marks,
  // a box that finds one in every set by a word ("kubernetes" finds EKS, AKS
  // and GKE), and the icons, the one it carries ticked.
  function iconField(a, change) {
    var eng = Canvas.engine, kind = eng.KIND_ICONS[a.shape || "rectangle"] || "box";
    var mine = (a.look || {}).icon || kind, slash = mine.indexOf("/");
    var grid = el("div", { class: "cv-icons", role: "radiogroup", "aria-label": "Icon" });
    var sets = el("select", { class: "cv-input", "aria-label": "Icon set" });
    [["plain", "Plain icons"]].concat(eng.MARK_SETS).forEach(function (s) {
      sets.appendChild(el("option", { value: s[0], text: s[1] }));
    });
    sets.value = slash > 0 ? mine.slice(0, slash) : "plain";
    var find = el("input", { type: "search", class: "cv-input cv-icon-find", placeholder: "Find an icon",
      "aria-label": "Find an icon" });
    function button(name, title, pic) {
      return el("button", { type: "button", role: "radio", class: "cv-icon-b", title: title, "aria-label": title,
        "aria-checked": String(name === mine),
        onclick: function () { change({ look: { icon: name === kind ? null : name } }); } }, [pic]);
    }
    function plain(name) {
      var pic = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      ["viewBox:0 0 24 24", "width:16", "height:16", "fill:none", "stroke:currentColor", "stroke-width:2",
        "stroke-linecap:round", "stroke-linejoin:round"].forEach(function (pair) {
        var at = pair.indexOf(":");
        pic.setAttribute(pair.slice(0, at), pair.slice(at + 1));
      });
      pic.innerHTML = window.TerraneOwnIcons[name];
      return button(name, name, pic);
    }
    function fill() {
      var q = find.value.trim().toLowerCase(), shelf = sets.value;
      grid.textContent = "";
      // A word looks in every set; without one, the set picked.
      if (q || shelf === "plain") {
        Object.keys(window.TerraneOwnIcons || {}).forEach(function (name) {
          if (!q || name.replace(/-/g, " ").indexOf(q) !== -1) grid.appendChild(plain(name));
        });
      }
      if (!q && shelf === "plain") return;
      marks().then(function (list) {
        if (find.value.trim().toLowerCase() !== q || sets.value !== shelf) return;
        list.forEach(function (m) {
          if (q ? (m.set + " " + m.words).toLowerCase().indexOf(q) === -1 : m.icon.indexOf(shelf + "/") !== 0) return;
          grid.appendChild(button(m.icon, m.set + ": " + m.icon.slice(m.icon.indexOf("/") + 1).replace(/-/g, " "),
            el("img", { src: "icons/" + m.icon + ".svg", width: "20", height: "20", alt: "" })));
        });
        if (!grid.children.length) grid.appendChild(el("p", { class: "cv-icons-none", text: "No icon matches that." }));
      }, function () {
        grid.appendChild(el("p", { class: "cv-icons-none", text: "The providers' marks did not load." }));
      });
    }
    sets.addEventListener("change", fill);
    find.addEventListener("input", fill);
    fill();
    return el("div", { class: "cv-field" }, [el("span", { class: "cv-label", text: "Icon" }), sets, find, grid]);
  }

  // How the diagram draws its own shapes (V16): Illustrated, the app's own
  // picture language, or Icon tiles. Kept in its file as `look: tiles`;
  // Illustrated is the file saying nothing. Offered in the diagram's own
  // panel, and in the Style tab of anything of its own picked.
  function lookChoice(after) {
    var d = cv.data;
    var looks = segmented("Look", [["illustrated", "Illustrated"], ["tiles", "Icon tiles"]],
      d.look === "tiles" ? "tiles" : "illustrated", function (v) {
        if (v === "tiles") d.look = "tiles"; else delete d.look;
        Array.prototype.forEach.call(looks.children, function (b, i) {
          b.setAttribute("aria-checked", String((i === 1) === (v === "tiles")));
        });
        if (Canvas.engine) Canvas.engine.setLook(v);
        canvasSoon(0);
        if (after) after();
      });
    return looks;
  }

  // Where its words link to (V16's toolbar, its last button): an address on
  // the web or for email (LINK in terrane/annotations.py), so no file can
  // carry a script to run on a click. Opened from the mark at its corner on
  // the canvas, and from the shape itself in the picture, on a slide and on
  // a draw.io page.
  var LINK = /^(https?:\/\/|mailto:)\S+$/;
  function linkRow(a, key, change) {
    var input = el("input", { type: "url", class: "cv-input cv-link-in", placeholder: "https://\u2026",
      "aria-label": "Its link", maxlength: "2000" });
    input.value = a.link || "";
    var said = el("p", { class: "cv-small", hidden: "" });
    var keep = function () {
      var v = input.value.trim();
      if (v === (a.link || "")) return;
      if (v && !LINK.test(v)) {
        said.textContent = "A link starts with https://, http:// or mailto:";
        said.hidden = false;
        return;
      }
      change({ link: v || null });
    };
    input.addEventListener("change", keep);
    input.addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); keep(); } });
    return el("div", { class: "cv-link-row" }, [input, el("span", { class: "cv-link-acts" }, [
      el("button", { type: "button", class: "btn small", disabled: a.link ? null : "",
        onclick: function () { window.open(a.link, "_blank", "noopener"); } }, [el("span", { text: "Open" })]),
      el("button", { type: "button", class: "btn small", disabled: a.link ? null : "",
        onclick: function () { Canvas.linkFor = null; change({ link: null }); } }, [el("span", { text: "Remove" })]),
    ]), said]);
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

    // A line keeps the one panel it had; the rest are styled and arranged
    // in two tabs (V16), the one last opened kept as the pick moves on.
    if (a.role === "line") { lineDetails(box, a, key, look, change, keysLine, redo); return; }
    var tab = Canvas.ownTab === "arrange" ? "arrange" : "style";
    var tabs = segmented("Style or arrange", [["style", "Style"], ["arrange", "Arrange"]], tab, function (v) {
      Canvas.ownTab = v;
      redo();
    });
    tabs.classList.add("cv-tabs");
    box.appendChild(tabs);
    if (tab === "arrange") arrangeTab(box, a, key, change);
    else styleTab(box, a, key, look, change, redo);
    box.appendChild(el("div", { class: "cv-acts" }, [
      el("button", { type: "button", class: "btn small" + (Canvas.painting ? " is-on" : ""),
        "aria-pressed": String(!!Canvas.painting), onclick: function () {
          if (Canvas.painting) stopPainting(); else startPainting(a);
          redo();
        } }, [svgIcon("i-paintbrush"), el("span", { text: Canvas.painting ? "Stop painting" : "Copy the look" })]),
      lockButton([key]),
      el("button", { type: "button", class: "btn small", onclick: function () { eng.remove([key]); } },
        [svgIcon("i-x"), el("span", { text: "Delete" })]),
    ]));
    var held = lockedNote([key]);
    if (held) box.appendChild(held);
    box.appendChild(el("p", { class: "cv-small cv-keyline", text: tab === "arrange"
      ? "Ctrl+] brings it forward \u00b7 Ctrl+[ sends it back \u00b7 the arrows nudge it, Shift by ten \u00b7 drag a "
        + "corner to size it" + (a.role === "frame" ? "" : ", or the dot above it to turn it")
      : "Copy the look, then click shapes to paint it onto them; Esc stops. Ctrl+Alt+C and Ctrl+Alt+V do it by "
        + "keys \u00b7 Double-click it to type in it \u00b7 Delete removes it \u00b7 Ctrl+D copies it" }));
  }

  /* ---- drawing layers (V16) ----
   * A popover off the toolbar: the diagram's drawing layers top first, the
   * estate's records among them, each with its grip, shown or hidden,
   * locked or not, its name and how much is on it; a click on a name marks
   * it to draw on, a double-click renames it. A diagram with no layers in
   * its file shows the two it starts with, and the first change writes
   * them. */
  var ESTATE_LAYER = "estate";

  function layersOf() {
    return cv && cv.data.layers ? cv.data.layers : [{ key: "layer-1", name: "Layer 1" }, { key: ESTATE_LAYER }];
  }
  function drawingLayers() { return layersOf().filter(function (l) { return l.key !== ESTATE_LAYER; }); }
  function layerHomeKey() {
    var list = layersOf(), keys = list.map(function (l) { return l.key; }), at = keys.indexOf(ESTATE_LAYER);
    if (at === -1) at = keys.length;
    return at > 0 ? keys[at - 1] : drawingLayers()[0].key;
  }
  // The layer what is drawn goes on: the one marked, else what names none's.
  function drawLayer() {
    var keys = drawingLayers().map(function (l) { return l.key; });
    return Canvas.drawLayer && keys.indexOf(Canvas.drawLayer) !== -1 ? Canvas.drawLayer : layerHomeKey();
  }

  // A change to the layers: one step for Undo, drawn and saved.
  function changeLayers(fn) {
    if (!cv) return;
    remember();
    var list = JSON.parse(JSON.stringify(layersOf()));
    fn(list);
    cv.data.layers = list;
    if (Canvas.engine && Canvas.engine.live()) Canvas.engine.setLayers(list);
    applyLocks();
    canvasSoon(0);
    renderLayers();
  }

  function toggleLayers() {
    var pop = $("cvLayers");
    if (!pop || !cv) return;
    pop.hidden = !pop.hidden;
    $("cvLayersBtn").setAttribute("aria-expanded", String(!pop.hidden));
    renderLayers();
  }

  // What is picked, to the drawing layer above or below its own, skipping
  // the estate's; one step for Undo.
  function moveToLayer(keys, step) {
    var eng = Canvas.engine, order = drawingLayers().map(function (l) { return l.key; });
    if (!cv || !eng || order.length < 2) return;
    if (!cv.data.layers) cv.data.layers = layersOf();
    var home = layerHomeKey(), moves = [];
    keys.forEach(function (k) {
      var a = eng.item(k);
      if (!a || (a.in || []).length) return;
      var at = order.indexOf(eng.layerOf(k) || home), to = Math.max(0, Math.min(order.length - 1, at + step));
      if (to !== at) moves.push([k, order[to]]);
    });
    if (!moves.length) return;
    remember();
    cv.holdUndo = true;
    try {
      eng.together(function () { moves.forEach(function (m) { eng.update(m[0], { layer: m[1] === home ? null : m[1] }); }); });
    } finally {
      cv.holdUndo = false;
    }
    renderLayers();
  }

  function renderLayers() {
    var pop = $("cvLayers");
    if (!pop || pop.hidden || !cv) return;
    pop.textContent = "";
    var list = layersOf(), home = layerHomeKey(), mark = drawLayer();
    var counts = {};
    (cv.data.annotations || []).forEach(function (a) {
      if ((a.in || []).length) return;
      var k = a.layer && list.some(function (l) { return l.key === a.layer; }) ? a.layer : home;
      counts[k] = (counts[k] || 0) + 1;
    });
    var records = state.cy ? state.cy.nodes().filter(function (n) { return !n.data("isGroup"); }).length : 0;
    pop.appendChild(el("div", { class: "cv-layers-h" }, [el("span", { class: "cv-label", text: "Drawing layers" }),
      el("button", { type: "button", class: "cv-link-b", text: "+ New layer", onclick: function () {
        var n = 1;
        while (layersOf().some(function (l) { return l.key === "layer-" + n; })) n += 1;
        Canvas.drawLayer = "layer-" + n;
        changeLayers(function (l) { l.unshift({ key: "layer-" + n, name: "Layer " + n }); });
      } })]));
    pop.appendChild(el("p", { class: "cv-small", text: "The top of the list is drawn on top. What you draw goes on the "
      + "layer marked." }));
    var rows = el("div", { class: "cv-layer-list", role: "list" });
    list.forEach(function (l) {
      var estate = l.key === ESTATE_LAYER, here = l.key === mark;
      var status = statusOf(l, mark);
      var eye = el("button", { type: "button", class: "cv-layer-b", "aria-pressed": String(!l.hidden),
        title: estate ? "The estate's records are on every drawing of the diagram" : l.hidden ? "Show it" : "Hide it",
        "aria-label": l.hidden ? "Show it" : "Hide it",
        onclick: function () { changeLayers(function (all) { var x = find(all, l.key); if (x.hidden) delete x.hidden; else x.hidden = true; }); } },
        [svgIcon(l.hidden ? "i-eye-off" : "i-eye")]);
      if (estate) eye.disabled = true;
      var lock = el("button", { type: "button", class: "cv-layer-b", "aria-pressed": String(!!l.locked),
        title: l.locked ? "Unlock it" : "Lock it: nothing on it is picked or moved", "aria-label": l.locked ? "Unlock it" : "Lock it",
        onclick: function () { changeLayers(function (all) { var x = find(all, l.key); if (x.locked) delete x.locked; else x.locked = true; }); } },
        [svgIcon(l.locked ? "i-lock" : "i-lock-open")]);
      var name = el("button", { type: "button", class: "cv-layer-n", text: estate ? "Records from the estate" : l.name,
        onclick: function () { if (!estate) markLayer(l.key); } });
      if (estate) name.disabled = true;
      name.addEventListener("dblclick", function () { if (!estate) renameLayer(row, l); });
      var gone = estate || drawingLayers().length < 2 ? null : el("button", { type: "button", class: "cv-layer-b cv-layer-x",
        title: "Delete the layer: what is on it goes to the layer under it", "aria-label": "Delete the layer",
        onclick: function () { deleteLayer(l.key); } }, [svgIcon("i-x")]);
      var row = el("div", { class: "cv-layer" + (here ? " is-on" : "") + (l.hidden ? " is-hidden" : ""), role: "listitem",
        "data-key": l.key }, [
        el("span", { class: "cv-lane-grip", title: "Drag to put it elsewhere in the stack", "aria-hidden": "true" }, [svgIcon("i-grip")]),
        eye, lock,
        el("div", { class: "cv-layer-what" }, [name, el("span", { class: "cv-layer-s", text: status })]),
        el("span", { class: "cv-layer-c", text: String(estate ? records : counts[l.key] || 0) }),
        gone,
      ]);
      row.querySelector(".cv-lane-grip").addEventListener("pointerdown", function (ev) { dragLayer(ev, row, rows, l.key); });
      rows.appendChild(row);
    });
    pop.appendChild(rows);
    pop.appendChild(el("p", { class: "cv-small", text: "A hidden drawing layer is left out of Export and the review pack. "
      + "What is picked goes to the layer above or below with Ctrl+Alt+] and Ctrl+Alt+[, or its Drawing layer in "
      + "Arrange." }));
  }

  function find(list, key) { return list.filter(function (l) { return l.key === key; })[0]; }

  // What a layer's row says under its name.
  function statusOf(l, mark) {
    if (l.key === ESTATE_LAYER) return l.locked ? "locked" : "every record on the drawing";
    return l.hidden ? "hidden" : l.key === mark ? "drawing here" : l.locked ? "locked" : "";
  }

  // A layer marked to draw on, its row and the others said again where
  // they are: drawn anew, the row under the pointer would take no
  // double-click to rename it.
  function markLayer(key) {
    Canvas.drawLayer = key;
    var list = layersOf();
    Array.prototype.forEach.call(document.querySelectorAll("#cvLayers .cv-layer"), function (row) {
      var l = find(list, row.dataset.key);
      if (!l) return;
      row.classList.toggle("is-on", l.key === key);
      row.querySelector(".cv-layer-s").textContent = statusOf(l, key);
    });
  }

  function renameLayer(row, l) {
    var input = el("input", { type: "text", class: "cv-input cv-layer-name", maxlength: "60", "aria-label": "The layer's name" });
    input.value = l.name;
    var name = row.querySelector(".cv-layer-n");
    name.replaceWith(input);
    input.focus();
    input.select();
    var done = false;
    function keep() {
      if (done) return;
      done = true;
      var v = input.value.trim();
      if (v && v !== l.name) changeLayers(function (all) { find(all, l.key).name = v; });
      else renderLayers();
    }
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); keep(); }
      if (e.key === "Escape") { e.preventDefault(); done = true; renderLayers(); }
      e.stopPropagation();
    });
    input.addEventListener("blur", keep);
  }

  // A layer deleted: what is on it goes to the drawing layer under it (the
  // one above, for the bottom one), in the same step.
  function deleteLayer(key) {
    var eng = Canvas.engine, order = drawingLayers().map(function (l) { return l.key; });
    var at = order.indexOf(key);
    if (at === -1 || order.length < 2) return;
    var into = order[at + 1 < order.length ? at + 1 : at - 1];
    remember();
    cv.holdUndo = true;
    try {
      var list = JSON.parse(JSON.stringify(layersOf())).filter(function (l) { return l.key !== key; });
      var home = (function () { var keys = list.map(function (l) { return l.key; }), e = keys.indexOf(ESTATE_LAYER);
        return e > 0 ? keys[e - 1] : keys.filter(function (k) { return k !== ESTATE_LAYER; })[0]; })();
      var oldHome = layerHomeKey();
      cv.data.layers = list;
      if (Canvas.drawLayer === key) Canvas.drawLayer = into;
      eng.setLayers(list);
      eng.together(function () {
        (cv.data.annotations || []).forEach(function (a) {
          if ((a.in || []).length) return;
          var on = a.layer || oldHome, now = on === key ? into : on;
          var want = now === home ? null : now;
          if ((a.layer || null) !== want) eng.update(a.key, { layer: want });
        });
      });
    } finally {
      cv.holdUndo = false;
    }
    applyLocks();
    canvasSoon(0);
    renderLayers();
  }

  // A layer's row carried by its grip to another place in the stack.
  function dragLayer(ev, row, list, key) {
    ev.preventDefault();
    var rows = Array.prototype.slice.call(list.children), others = rows.filter(function (r) { return r !== row; });
    var from = rows.indexOf(row), to = from;
    row.classList.add("is-carried");
    function move(e) {
      to = others.filter(function (r) { var b = r.getBoundingClientRect(); return e.clientY > b.top + b.height / 2; }).length;
      others.forEach(function (r, i) {
        r.classList.toggle("is-before", i === to && to !== from);
        r.classList.toggle("is-after", i === others.length - 1 && to === others.length && to !== from);
      });
    }
    function up() {
      document.removeEventListener("pointermove", move);
      document.removeEventListener("pointerup", up);
      row.classList.remove("is-carried");
      if (to === from) { renderLayers(); return; }
      // What named no layer stays where it was drawn: on the layer that
      // was just above the estate, said now by name.
      var oldHome = layerHomeKey();
      changeLayers(function (all) {
        var moving = find(all, key);
        all.splice(all.indexOf(moving), 1);
        all.splice(to, 0, moving);
      });
      var home = layerHomeKey();
      if (home !== oldHome) {
        cv.holdUndo = true;
        try {
          Canvas.engine.together(function () {
            (cv.data.annotations || []).forEach(function (a) {
              if ((a.in || []).length) return;
              var on = a.layer || oldHome, want = on === home ? null : on;
              if ((a.layer || null) !== want) Canvas.engine.update(a.key, { layer: want });
            });
          });
        } finally {
          cv.holdUndo = false;
        }
      }
    }
    document.addEventListener("pointermove", move);
    document.addEventListener("pointerup", up);
  }

  /* ---- swimlanes (V16) ---- */
  // The swimlane or lane picked alone, or nothing.
  function swimOf(key) {
    var eng = Canvas.engine, a = eng && eng.live() ? eng.item(key) : null;
    return a && (a.role === "pool" || a.role === "lane") ? a : null;
  }

  //: Who a lane may stand for (V16): an actor or an org unit.
  var STANDS = { actors: "an actor", org_units: "an org unit" };

  // A swimlane's lane picked, or the swimlane itself: what it stands for,
  // its lanes in order, which way they run and where their names sit.
  function canvasSwimDetails(box, key) {
    var eng = Canvas.engine, a = eng.item(key), lane = a.role === "lane";
    var pool = lane ? eng.item((a.in || [])[(a.in || []).length - 1]) : a;
    if (!pool) { canvasDiagramDetails(box); return; }
    var all = eng.lanes(pool.key), redo = function () { if (cv && cv.sel) canvasSelect(cv.sel, true); };
    var title = pool.label || "Swimlane", down = pool.runs === "down";
    var record = lane && a.stands_for ? indexItem(a.stands_for) : null;
    box.appendChild(el("span", { class: "cv-badge is-own", text: (lane ? "Lane" : "Swimlane") + " \u00b7 on this diagram only" }));
    box.appendChild(el("h2", { class: "cv-h", text: lane ? (record ? record.name : a.label || "Lane") : title }));
    box.appendChild(el("p", { class: "cv-lede", text: lane
      ? "A lane of \u201c" + title + "\u201d. What is drawn in it moves with it, and a box carried into another lane changes lanes."
      : "Its lanes " + (down ? "side by side down it" : "stacked across it") + ", each holding what is drawn in it. "
        + "What is drawn in a lane moves with it, and a box carried into another lane changes lanes." }));
    if (lane) box.appendChild(standsSection(a, record, redo));
    else {
      var name = el("input", { type: "text", class: "cv-input", maxlength: "120", "aria-label": "Its name" });
      name.value = pool.label || "";
      name.addEventListener("change", function () { eng.update(pool.key, { label: name.value.trim() || "Swimlane" }); redo(); });
      box.appendChild(cvField("Name", name));
    }
    if (lane && !record) {
      var words = el("input", { type: "text", class: "cv-input", maxlength: "120", "aria-label": "The lane's name" });
      words.value = a.label || "";
      words.addEventListener("change", function () { eng.update(key, { label: words.value.trim() || "Lane" }); redo(); });
      box.appendChild(cvField("Name", words));
    }
    box.appendChild(lanesSection(pool, all, lane ? key : null, redo));
    box.appendChild(el("p", { class: "cv-label", text: "The lanes run" }));
    box.appendChild(segmented("The lanes run", [["across", "Across"], ["down", "Down"]], down ? "down" : "across",
      function (v) { eng.swimRuns(pool.key, v); redo(); }));
    box.appendChild(segmented("Where each lane's name sits", [["left", "Names at the left"], ["top", "Names at the top"]],
      pool.names === "top" ? "top" : "left", function (v) { eng.swimNames(pool.key, v); redo(); }));
    var gone = el("button", { type: "button", class: "btn small", onclick: function () { eng.remove([key]); } },
      [svgIcon("i-x"), el("span", { text: lane ? "Delete the lane" : "Delete the swimlane" })]);
    if (lane && all.length < 2) {
      gone.disabled = true;
      gone.title = "A swimlane keeps one lane at least; delete the swimlane instead";
    }
    box.appendChild(el("div", { class: "cv-acts" }, [lockButton([key]), gone]));
    var held = lockedNote([key]);
    if (held) box.appendChild(held);
    box.appendChild(el("p", { class: "cv-small", text: lane
      ? "A swimlane is drawn from Shapes, the last of them. Deleting a lane keeps what was in it, moved up into the "
        + "lane above."
      : "A lane is picked by its name, or by a click inside it. Deleting the swimlane deletes what is drawn in its "
        + "lanes too." }));
  }

  // What a lane stands for: an actor or an org unit, or nothing in the
  // estate, chosen by its name.
  function standsSection(a, record, redo) {
    var eng = Canvas.engine;
    var sec = section("Stands for", record ? null : hint("Nothing in the estate"));
    var find = el("div", { class: "cv-stands-find", hidden: "" });
    var input = el("input", { type: "search", class: "cv-input cv-stands-in", placeholder: "Find an actor or an org unit",
      "aria-label": "Find an actor or an org unit" });
    var found = el("div", { class: "cv-picks cv-stands-list" });
    function list() {
      var q = input.value.trim().toLowerCase();
      found.textContent = "";
      (state.index || []).filter(function (i) {
        return STANDS[i.type] && (!q || String(i.name || "").toLowerCase().indexOf(q) !== -1 || i.id.toLowerCase().indexOf(q) !== -1);
      }).slice(0, 8).forEach(function (i) {
        found.appendChild(el("button", { type: "button", class: "cv-pick", onclick: function () {
          eng.update(a.key, { stands_for: i.id, label: i.name || i.id });
          redo();
        } }, [el("span", { class: "cv-pick-dot", "aria-hidden": "true" }), el("span", { class: "cv-pick-n", text: i.name || i.id }),
          el("span", { class: "cv-pick-id", text: i.id })]));
      });
      if (!found.childNodes.length) found.appendChild(el("p", { class: "cv-small", text: "No actor or org unit by that name." }));
    }
    input.addEventListener("input", list);
    find.appendChild(input);
    find.appendChild(found);
    function open() { find.hidden = false; list(); input.focus(); }
    if (record) {
      sec.appendChild(el("div", { class: "cv-stands" }, [
        svgIcon(record.type === "actors" ? "i-users" : "i-blocks"),
        el("div", { class: "cv-stands-what" }, [el("span", { class: "cv-stands-n", text: record.name || record.id }),
          el("span", { class: "cv-stands-id", text: record.id + " \u00b7 " + (STANDS[record.type] || record.label || "a record") })]),
        el("button", { type: "button", class: "cv-link-b", text: "Change", onclick: open }),
      ]));
      sec.appendChild(el("p", { class: "cv-small", text: "Its name follows the record's, and the record's page lists the "
        + "diagrams it has a lane on." }));
      sec.appendChild(el("button", { type: "button", class: "cv-link-b", text: "Stand for nothing", onclick: function () {
        eng.update(a.key, { stands_for: null });
        redo();
      } }));
    } else {
      sec.appendChild(el("button", { type: "button", class: "btn small", onclick: open },
        [svgIcon("i-search"), el("span", { text: "Choose an actor or an org unit" })]));
    }
    sec.appendChild(find);
    return sec;
  }

  // A swimlane's lanes in order, the one picked marked: a click picks one,
  // its grip drags it to another place, and one more is added at the end.
  function lanesSection(pool, all, current, redo) {
    var eng = Canvas.engine;
    var add = el("button", { type: "button", class: "cv-link-b", text: "+ Add a lane", onclick: function () {
      var key = eng.addLane(pool.key);
      if (key) canvasPick([], [key]);
    } });
    var list = el("div", { class: "cv-lanes", role: "list" });
    all.forEach(function (l, i) {
      var rec = l.stands_for ? indexItem(l.stands_for) : null;
      var row = el("div", { class: "cv-lane" + (l.key === current ? " is-on" : ""), role: "listitem", "data-key": l.key }, [
        el("span", { class: "cv-lane-grip", title: "Drag to put it elsewhere among the lanes", "aria-hidden": "true" },
          [svgIcon("i-grip")]),
        el("button", { type: "button", class: "cv-lane-n", text: rec ? rec.name : l.label || "Lane " + (i + 1),
          onclick: function () { canvasPick([], [l.key]); } }),
        el("span", { class: "cv-lane-id", text: l.stands_for || "" }),
      ]);
      row.querySelector(".cv-lane-grip").addEventListener("pointerdown", function (ev) { dragLane(ev, row, list, l.key, redo); });
      list.appendChild(row);
    });
    var sec = section("Lanes", add, [list]);
    return sec;
  }

  // A lane's row carried by its grip to another place in the list, and the
  // lane put there among its swimlane's lanes.
  function dragLane(ev, row, list, key, redo) {
    ev.preventDefault();
    var rows = Array.prototype.slice.call(list.children), from = rows.indexOf(row), to = from;
    var others = rows.filter(function (r) { return r !== row; });
    row.classList.add("is-carried");
    // Its place among the others: how many of them are above the pointer.
    function move(e) {
      to = others.filter(function (r) { var b = r.getBoundingClientRect(); return e.clientY > b.top + b.height / 2; }).length;
      others.forEach(function (r, i) {
        r.classList.toggle("is-before", i === to && to !== from);
        r.classList.toggle("is-after", i === others.length - 1 && to === others.length && to !== from);
      });
    }
    function up() {
      document.removeEventListener("pointermove", move);
      document.removeEventListener("pointerup", up);
      row.classList.remove("is-carried");
      others.forEach(function (r) { r.classList.remove("is-before", "is-after"); });
      if (to !== from) Canvas.engine.moveLane(key, to);
      redo();
    }
    document.addEventListener("pointermove", move);
    document.addEventListener("pointerup", up);
  }

  // A heading, with what goes at its right, over what it heads.
  function section(title, right, kids) {
    return el("div", { class: "cv-sec" }, [el("div", { class: "cv-sec-h" },
      [el("span", { class: "cv-label", text: title }), right || null])].concat(kids || []));
  }

  function hint(text) { return el("span", { class: "cv-aside", text: text }); }

  // What it says, typed: kept a moment after the last key, and on leaving.
  function wordsBox(a, key) {
    var eng = Canvas.engine;
    var words = el("textarea", { class: "cv-input", rows: a.role === "line" || a.role === "frame" ? "2" : "3",
      "aria-label": a.role === "frame" ? "Title" : "Words",
      placeholder: a.role === "line" ? "What the line says, if anything" : a.role === "frame" ? "What it holds"
        : a.role === "shape" ? "Its name, and on the next line what it is" : "What it says" });
    words.value = a.label || "";
    var typed = null;
    words.addEventListener("input", function () {
      clearTimeout(typed);
      typed = setTimeout(function () { eng.update(key, { label: words.value }); }, 400);
    });
    words.addEventListener("change", function () { clearTimeout(typed); eng.update(key, { label: words.value }); });
    return words;
  }

  // A line of the diagram's own: its words, outline, size, route and ends.
  //: Where a line's words sit (V16): at its start, its middle, its end.
  var LABEL_PLACES = [["start", "Start"], ["middle", "Middle"], ["end", "End"]];

  /* A line's words (V16), a row a place it says something: where, and the
   * words. + Add a label opens the next place free; a place changed carries
   * the words to it. Its middle's are the line's label, the others its
   * `labels`. */
  function labelsSection(a, key, look, change, redo) {
    var said = { start: (a.labels || {}).start || "", middle: a.label || "", end: (a.labels || {}).end || "" };
    var draft = Canvas.labelDraft && Canvas.labelDraft.key === key ? Canvas.labelDraft.at : null;
    var write = function (next) {
      var labels = {};
      if (next.start) labels.start = next.start;
      if (next.end) labels.end = next.end;
      Canvas.labelDraft = null;
      change({ label: next.middle || "", labels: Object.keys(labels).length ? labels : null });
    };
    var rows = el("div", { class: "cv-labels" });
    LABEL_PLACES.forEach(function (p) {
      if (!said[p[0]] && draft !== p[0]) return;
      var place = el("select", { class: "cv-input cv-label-at", "aria-label": "Where the words sit" });
      LABEL_PLACES.forEach(function (q) {
        var o = el("option", { value: q[0], text: q[1] });
        if (q[0] === p[0]) o.selected = true;
        else if (said[q[0]]) o.disabled = true;
        place.appendChild(o);
      });
      var words = el("input", { type: "text", class: "cv-input cv-label-in", maxlength: "120",
        "aria-label": "What it says at its " + p[0], placeholder: "What it says at its " + p[0] });
      words.value = said[p[0]];
      words.addEventListener("change", function () {
        var next = Object.assign({}, said);
        next[p[0]] = words.value.trim();
        write(next);
      });
      words.addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); words.blur(); } });
      place.addEventListener("change", function () {
        var next = Object.assign({}, said), v = words.value.trim();
        next[p[0]] = "";
        next[place.value] = v;
        if (!v) { Canvas.labelDraft = { key: key, at: place.value }; redo(); return; }
        write(next);
      });
      rows.appendChild(el("div", { class: "cv-label-row", "data-at": p[0] }, [place, words]));
    });
    // The middle first, as a line is most often labeled, then each end.
    var free = ["middle", "start", "end"].map(function (k) {
      return LABEL_PLACES.filter(function (p) { return p[0] === k; })[0];
    }).filter(function (p) { return !said[p[0]] && draft !== p[0]; })[0];
    var add = free ? el("button", { type: "button", class: "cv-link-b", text: "+ Add a label", onclick: function () {
      Canvas.labelDraft = { key: key, at: free[0] };
      redo();
      var input = document.querySelector('#cvDetails .cv-label-row[data-at="' + free[0] + '"] input');
      if (input) input.focus();
    } }) : null;
    var size = segmented("Size of the words", [["s", "S"], ["m", "M"], ["l", "L"]], look.text || "s", function (v) {
      change({ look: { text: v === "s" ? null : v } });
    });
    return section("Labels", add, [rows, el("div", { class: "cv-label-size" }, [hint("Size of the words"), size])]);
  }

  //: The heads an end of a line may have (V16), by notation, as its
  //: popover offers them (HEADS in annotations.py, held equal by a test).
  var HEAD_GROUPS = [
    ["Plain", [["none", "Nothing"], ["arrow", "Arrow"], ["open-arrow", "Open arrow"], ["dot", "Dot"]]],
    ["UML", [["inherits", "Inherits"], ["made-of", "Is made of"], ["has", "Has"], ["depends-on", "Depends on"]]],
    ["Crow's foot", [["one", "One"], ["many", "Many"], ["one-or-many", "One or many"], ["none-or-one", "None or one"],
      ["none-or-many", "None or many"]]],
    ["ArchiMate", [["serving", "Serving"], ["triggering", "Triggering"], ["flow", "Flow"], ["realization", "Realization"],
      ["assignment", "Assignment"], ["access", "Access"]]],
  ];
  //: The line a UML or ArchiMate head draws, as its notation does.
  var HEAD_LINES = { "depends-on": "dashed", flow: "dashed", realization: "dotted", access: "dotted" };

  function headName(head) {
    var found = "Nothing";
    HEAD_GROUPS.forEach(function (g) { g[1].forEach(function (h) { if (h[0] === head) found = h[1]; }); });
    return found;
  }

  // A head as its picker and popover show it, 30 by 12, pointing right: a
  // stretch of line to where the line stops, then its parts, as the
  // picture draws them (HEAD_GLYPHS).
  function headGlyph(head) {
    var ns = "http://www.w3.org/2000/svg", g = Canvas.engine.HEAD_GLYPHS[head] || { stop: 0, parts: [] };
    var svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", "0 0 30 12");
    svg.setAttribute("width", "30");
    svg.setAttribute("height", "12");
    svg.setAttribute("class", "cv-head-glyph");
    svg.setAttribute("aria-hidden", "true");
    var add = function (tag, attrs) {
      var n = document.createElementNS(ns, tag);
      Object.keys(attrs).forEach(function (k) { n.setAttribute(k, attrs[k]); });
      svg.appendChild(n);
    };
    var x = function (a) { return 28 - a; };
    // The stretch dashed or dotted as the head draws its line, and
    // Assignment's dot at the other end, as the frame draws them.
    var stretch = { d: "M2 6H" + x(g.stop), fill: "none" }, dash = { dashed: "4 3", dotted: "2 3" }[HEAD_LINES[head]];
    if (dash) stretch["stroke-dasharray"] = dash;
    add("path", stretch);
    if (head === "assignment") add("circle", { cx: 4, cy: 6, r: 2, fill: "currentColor" });
    g.parts.forEach(function (part) {
      var kind = part[0], v = part[1];
      if (kind === "dot" || kind === "ring") {
        add("circle", { cx: x(v[0]), cy: 6, r: v[1], fill: kind === "dot" ? "currentColor" : "none" });
        return;
      }
      var d = "";
      for (var i = 0; i < v.length; i += 2) d += (i ? "L" : "M") + x(v[i]) + " " + (6 - v[i + 1]);
      add("path", { d: d + (kind === "line" ? "" : "Z"), fill: kind === "fill" ? "currentColor" : "none" });
    });
    return svg;
  }

  // An end of a line as its panel names it: the first line of what it
  // joins, or where it was left on the sheet.
  function endName(end, place) {
    if (Array.isArray(end)) return "its " + place;
    var it = Canvas.engine.item(end);
    if (it) return firstLine(it.label) || (it.role === "shape" ? shapeName(it.shape) : ROLE_WORDS[it.role]).toLowerCase();
    var rec = indexItem(end);
    return rec ? rec.name : end;
  }

  /* A line's ends (V16), a row each: where, and a picker that opens its
   * heads by notation. A UML or ArchiMate head draws its line as its
   * notation does, one taken off gives back the plain line, and
   * Assignment puts a dot at the other end where it has nothing. */
  function endsSection(a, look, change) {
    var heads = Canvas.engine.headsOf(a), places = ["start", "end"];
    var names = [endName(a.from, "start"), endName(a.to, "end")];
    var choose = function (i, head) {
      var next = heads.slice(), was = next[i];
      next[i] = head;
      if (head === "assignment" && next[1 - i] === "none") next[1 - i] = "dot";
      var patch = { heads: { start: next[0], end: next[1] } };
      var line = HEAD_LINES[next[0]] || HEAD_LINES[next[1]];
      if (line) patch.look = { line: line };
      else if (HEAD_LINES[was] && look.line === HEAD_LINES[was]) patch.look = { line: null };
      closeHeads();
      change(patch);
    };
    var rows = places.map(function (place, i) {
      var pick = el("button", { type: "button", class: "cv-head-pick", "aria-haspopup": "dialog", "aria-expanded": "false",
        "aria-label": "The head at " + names[i] + ": " + headName(heads[i]) }, [headGlyph(heads[i]),
        el("span", { class: "cv-head-name", text: headName(heads[i]) }), el("span", { class: "cv-head-chev", "aria-hidden": "true" })]);
      pick.addEventListener("click", function () {
        if (Canvas.headsOpen && Canvas.headsOpen.anchor === pick) { closeHeads(); return; }
        openHeads(pick, names[i], heads[i], function (h) { choose(i, h); });
      });
      return el("div", { class: "cv-end-row", "data-at": place }, [el("span", { class: "cv-end-at", text: "At " + names[i] }), pick]);
    });
    return section("Ends", null, rows);
  }

  // The heads of one end (V16): by notation, the one it has marked; Escape
  // or a click elsewhere shuts it with nothing changed.
  function openHeads(anchor, name, current, pick) {
    closeHeads();
    var pop = el("div", { class: "cv-heads", id: "cvHeads", role: "dialog", "aria-label": "The end at " + name });
    pop.appendChild(el("p", { class: "cv-heads-h", text: "The end at " + name }));
    HEAD_GROUPS.forEach(function (g) {
      pop.appendChild(el("p", { class: "cv-label", text: g[0] }));
      pop.appendChild(el("div", { class: "cv-heads-row", role: "group", "aria-label": g[0] }, g[1].map(function (h) {
        var b = el("button", { type: "button", class: "cv-head-opt", "aria-pressed": String(h[0] === current), "data-head": h[0],
          onclick: function () { pick(h[0]); } }, [headGlyph(h[0]), el("span", { text: h[1] })]);
        return b;
      })));
    });
    pop.appendChild(el("p", { class: "cv-small", text: "A UML or ArchiMate head draws its line as its notation does: "
      + "Depends on and Flow dashed, Realization and Access dotted. Assignment puts a dot at the other end." }));
    document.body.appendChild(pop);
    anchor.setAttribute("aria-expanded", "true");
    // Beside the panel, its top at the picker's, held on the screen.
    var r = anchor.getBoundingClientRect(), panel = $("cvDetails").getBoundingClientRect();
    pop.style.left = Math.max(8, panel.left - pop.offsetWidth - 10) + "px";
    pop.style.top = Math.max(8, Math.min(r.top - 14, window.innerHeight - pop.offsetHeight - 8)) + "px";
    var current0 = pop.querySelector('.cv-head-opt[aria-pressed="true"]');
    if (current0) current0.focus();
    Canvas.headsOpen = { pop: pop, anchor: anchor, away: function (e) {
      if (!pop.contains(e.target) && !anchor.contains(e.target)) closeHeads();
    }, key: function (e) {
      // Its own Escape, on the window to come before the canvas's keys on
      // the document, which would drop the line picked as well.
      if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); closeHeads(); anchor.focus(); }
    } };
    setTimeout(function () {
      if (!Canvas.headsOpen || Canvas.headsOpen.pop !== pop) return;
      document.addEventListener("pointerdown", Canvas.headsOpen.away, true);
      window.addEventListener("keydown", Canvas.headsOpen.key, true);
    }, 0);
  }

  function closeHeads() {
    var o = Canvas.headsOpen;
    if (!o) return;
    Canvas.headsOpen = null;
    document.removeEventListener("pointerdown", o.away, true);
    window.removeEventListener("keydown", o.key, true);
    if (o.pop.parentNode) o.pop.parentNode.removeChild(o.pop);
    o.anchor.setAttribute("aria-expanded", "false");
  }

  function lineDetails(box, a, key, look, change, keysLine, redo) {
    var eng = Canvas.engine;
    box.appendChild(labelsSection(a, key, look, change, redo));
    var looks = el("div", { class: "cv-look-row" });
    looks.appendChild(segmented("Outline", [["solid", "Solid"], ["dashed", "Dashed"], ["dotted", "Dotted"]], look.line || "solid",
      function (v) { change({ look: { line: v === "solid" ? null : v } }); }));
    looks.appendChild(segmented("How heavy it is", [["s", "S"], ["m", "M"], ["l", "L"]], look.weight || "m", function (v) {
      change({ look: { weight: v === "m" ? null : v } });
    }));
    box.appendChild(section("Look", null, [looks]));
    var route = [segmented("Route", eng.ROUTES, a.route || "straight", function (v) { change({ route: v }); })];
    if (a.route === "square") {
      route.push(segmented("Turns", [["sharp", "Sharp turns"], ["rounded", "Rounded turns"]],
        a.turns === "rounded" ? "rounded" : "sharp", function (v) { change({ turns: v === "rounded" ? "rounded" : null }); }));
    }
    box.appendChild(section("Route", null, route));
    if (Array.isArray(a.via) && a.via.length && (!a.route || a.route === "straight")) {
      box.appendChild(el("div", { class: "cv-acts" }, [el("button", { type: "button", class: "btn small",
        onclick: function () { change({ via: null }); } },
        [el("span", { text: a.via.length === 1 ? "Remove the bend" : "Remove the " + a.via.length + " bends" })])]));
    }
    // A square or curved line's turns kept where its stretches were moved
    // by hand (V16): said, and given back to the line to turn by itself.
    if (a.route === "square" || a.route === "curved") {
      var kept = Array.isArray(a.via) ? a.via.length : 0;
      box.appendChild(section("Bends", kept ? el("button", { type: "button", class: "cv-link-b", text: "Remove the bends",
        onclick: function () { change({ via: null }); } }) : null, [el("p", { class: "cv-small", text: kept
        ? "Moved by hand: it keeps " + (kept === 1 ? "its bend" : "its " + kept + " bends") + " where you put "
          + (kept === 1 ? "it" : "them") + " and stays " + (a.route === "curved" ? "curved" : "square")
          + ". Remove the bends and it finds its own way around the boxes again."
        : "Drag a stretch to move it. Until you do, it finds its own way around the boxes." })]));
    }
    // Its heads, after its bends, as V16 lists them.
    box.appendChild(endsSection(a, look, change));
    box.appendChild(el("div", { class: "cv-acts" }, [
      lockButton([key]),
      el("button", { type: "button", class: "btn small", onclick: function () { eng.remove([key]); } },
        [svgIcon("i-x"), el("span", { text: "Delete" })]),
    ]));
    var held = lockedNote([key]);
    if (held) box.appendChild(held);
    var straight = !a.route || a.route === "straight";
    box.appendChild(el("p", { class: "cv-small cv-keyline", text: (straight
      ? "Drag the dot halfway along it to bend it; Shift and a click on a bend take it out \u00b7 " : "") + keysLine }));
  }

  // The Style tab (V16): the diagram's look, the words and their size, the
  // shape and as tiles its icon, the fill and how much of it shows, the
  // edge, how heavy, and the corners, and Illustrated's hard shadow.
  function styleTab(box, a, key, look, change, redo) {
    var eng = Canvas.engine, tiles = eng.look() === "tiles";
    box.appendChild(section("Look of this diagram", hint("all its shapes"), [lookChoice(redo)]));
    if (a.role !== "text") box.appendChild(stylesSection(a, key, redo));
    var sizes = segmented("Size of the words", [["s", "S"], ["m", "M"], ["l", "L"]], look.text || "m", function (v) {
      change({ look: { text: v === "m" ? null : v } });
    });
    box.appendChild(section(a.role === "frame" ? "Title" : "Words", el("span", { class: "cv-sec-r" }, [hint("Size"), sizes]),
      [wordsTools(a, look, change, redo)].concat(a.link || Canvas.linkFor === key ? [linkRow(a, key, change)] : [],
        [wordsBox(a, key)])));
    if (a.role === "shape") {
      // Illustrated sets a shape's first line as its name and the rest as
      // a caption under it; the panel says so where the words are typed.
      box.appendChild(el("p", { class: "cv-small", text: "The first line is its name; the lines after it, a caption." }));
      var shapes = el("div", { class: "cv-shape-row", role: "radiogroup", "aria-label": "Shape" });
      eng.SHAPES.forEach(function (s) {
        shapes.appendChild(el("button", { type: "button", role: "radio", class: "cv-shape-b", title: s[1], "aria-label": s[1],
          "aria-checked": String(s[0] === a.shape), onclick: function () { change({ shape: s[0] }); } }, [shapePicture(s[0])]));
      });
      box.appendChild(section("Shape", null, [shapes]));
      // As Icon tiles a shape carries an icon: its kind's, or one picked here.
      if (tiles) box.appendChild(iconField(a, change));
    }
    if (a.role === "text") return;

    var fill = look.fill || ROLE_FILL[a.role] || "none";
    var swatches = el("div", { class: "cv-swatches", role: "radiogroup", "aria-label": "Fill" });
    // A frame starts with no fill, and can go back to none.
    (a.role === "frame" ? ["none"] : []).concat(eng.FILL_ORDER).forEach(function (f) {
      swatches.appendChild(el("button", { type: "button", role: "radio", class: "cv-swatch" + (f === "none" ? " is-none" : ""),
        title: FILL_WORDS[f], "aria-label": FILL_WORDS[f], "aria-checked": String(f === fill),
        style: "--sw:" + (tiles && eng.TILE_FILLS[f] ? eng.TILE_FILLS[f][1] : eng.FILLS[f] || "transparent") +
          ";--sw-edge:" + eng.INK,
        onclick: function () { change({ look: { fill: f === "none" || f === ROLE_FILL[a.role] ? null : f } }); } }));
    });
    var opacity = el("input", { type: "number", class: "cv-input cv-opacity", min: "10", max: "100", step: "10",
      "aria-label": "Opacity, in percent" });
    opacity.value = String(look.opacity || 100);
    opacity.addEventListener("change", function () {
      var v = Math.max(10, Math.min(100, Math.round(Number(opacity.value) || 100)));
      change({ look: { opacity: v === 100 ? null : v } });
    });
    box.appendChild(section("Fill", hint("Opacity"), [el("div", { class: "cv-fill-row" },
      [swatches, el("span", { class: "cv-opacity-box" }, [opacity, el("span", { class: "cv-unit", text: "%" })])])]));

    var edge = segmented("Edge", [["solid", "Solid"], ["dashed", "Dashed"], ["none", "None"]], look.line || "solid",
      function (v) { change({ look: { line: v === "solid" ? null : v } }); });
    var weight = segmented("How heavy the edge is", [["s", "S"], ["m", "M"], ["l", "L"]], look.weight || "m",
      function (v) { change({ look: { weight: v === "m" ? null : v } }); });
    var parts = [el("div", { class: "cv-look-row" }, [edge, weight])];
    var round = eng.cornersOf(a);
    if (round !== null) {
      // Its kind's radius, so dragged back to it the file says nothing.
      var kinds = eng.cornersOf(Object.assign({}, a, { look: Object.assign({}, a.look, { corners: null }) }));
      var corners = el("input", { type: "range", class: "cv-range", min: "0", max: "32", step: "1",
        "aria-label": "Corners, the radius they are rounded by" });
      corners.value = String(round);
      var said = el("span", { class: "cv-range-v", text: String(round) });
      corners.addEventListener("input", function () { said.textContent = corners.value; });
      corners.addEventListener("change", function () {
        var v = Number(corners.value);
        change({ look: { corners: v === kinds ? null : v } });
      });
      parts.push(el("div", { class: "cv-corners" }, [hint("Corners"), corners, said]));
    }
    box.appendChild(section(round !== null ? "Edge and corners" : "Edge", null, parts));
    // The hard ink shadow a shape or a note casts, drawn Illustrated.
    if (!tiles && (a.role === "shape" || a.role === "note")) {
      box.appendChild(section("Shadow", look.opacity ? hint("none under a see-through fill") : null,
        [segmented("Shadow", [["none", "None"], ["hard", "Hard"]],
        look.shadow === "none" ? "none" : "hard", function (v) { change({ look: { shadow: v === "none" ? "none" : null } }); })]));
    }
  }

  // The Arrange tab (V16): its size, how far it is turned, and its order
  // among what shares its frame.
  function arrangeTab(box, a, key, change) {
    var eng = Canvas.engine, locked = isLocked(key), size = a.size || [0, 0];
    var w = el("input", { type: "number", class: "cv-input cv-width", min: "8", max: "4000", step: "1", "aria-label": "Width" });
    var h = el("input", { type: "number", class: "cv-input cv-height", min: "8", max: "4000", step: "1",
      "aria-label": "Height" });
    w.value = String(Math.round(size[0]));
    h.value = String(Math.round(size[1]));
    w.disabled = h.disabled = locked;
    var sized = function () { change({ size: [Number(w.value), Number(h.value)] }); };
    w.addEventListener("change", sized);
    h.addEventListener("change", sized);
    box.appendChild(section("Size", hint("in the drawing's units"),
      [el("div", { class: "cv-pair" }, [cvField("Width", w), cvField("Height", h)])]));
    // Where it sits: its corner from the corner of the frame or lane it sits
    // in, or of the sheet, as the file keeps it. A lane's place is its
    // swimlane's to say.
    if (a.role !== "lane") {
      var at = a.at || [0, 0], inFrame = (a.in || []).length > 0;
      var px = el("input", { type: "number", class: "cv-input cv-x", step: "1", "aria-label": "Across" });
      var py = el("input", { type: "number", class: "cv-input cv-y", step: "1", "aria-label": "Down" });
      px.value = String(Math.round(at[0]));
      py.value = String(Math.round(at[1]));
      px.disabled = py.disabled = locked;
      var placed = function () { change({ at: [Number(px.value), Number(py.value)] }); };
      px.addEventListener("change", placed);
      py.addEventListener("change", placed);
      box.appendChild(section("Place", hint(inFrame ? "from the corner of what it sits in" : "from the sheet's corner"),
        [el("div", { class: "cv-pair" }, [cvField("Across", px), cvField("Down", py)])]));
    }
    if (a.role === "shape" || a.role === "note" || a.role === "text") {
      // Turned about its middle, as maxGraph's handle above it turns it.
      var turn = el("input", { type: "number", class: "cv-input cv-turn", min: "-180", max: "180", step: "15",
        "aria-label": "Turned, in degrees" });
      turn.value = String(a.rotate || 0);
      turn.disabled = locked;
      turn.addEventListener("change", function () {
        var v = Math.round(Number(turn.value) || 0) % 360;
        if (v > 180) v -= 360;
        if (v <= -180) v += 360;
        change({ rotate: v });
      });
      box.appendChild(section("Turned", hint("about its middle"), [cvField("Degrees clockwise", turn)]));
    }
    // The drawing layer it is on, when the diagram has layers and it sits
    // in no frame (what sits in one goes with it).
    if (cv.data.layers && !(a.in || []).length) {
      var layer = el("select", { class: "cv-input cv-layer", "aria-label": "Drawing layer" });
      drawingLayers().forEach(function (l) {
        var o = el("option", { value: l.key, text: l.name });
        if (l.key === (Canvas.engine.layerOf(key) || "")) o.selected = true;
        layer.appendChild(o);
      });
      layer.disabled = locked;
      layer.addEventListener("change", function () { change({ layer: layer.value === layerHomeKey() ? null : layer.value }); });
      box.appendChild(section("Drawing layer", hint("Ctrl+Alt+] and Ctrl+Alt+[ move it"), [layer]));
    }
    box.appendChild(section("Order", hint("among what shares its frame"), [el("div", { class: "cv-acts" }, [
      el("button", { type: "button", class: "btn small", onclick: function () { eng.order([key], false); } },
        [el("span", { text: "Bring forward" })]),
      el("button", { type: "button", class: "btn small", onclick: function () { eng.order([key], true); } },
        [el("span", { text: "Send back" })]),
    ])]));
  }

  /* Copy the look (V16), the format painter: what the picked one looks
   * like, painted onto each of its own clicked next until Esc, or by
   * Ctrl+Alt+C and Ctrl+Alt+V. What a kind has no use for is left alone:
   * a line takes only its outline and the size of its words, text only how
   * its words are set, a frame's name no bold, place or list; an icon says
   * what a shape is, not how it looks, and stays. */
  var PAINTS = {
    shape: ["fill", "line", "text", "opacity", "weight", "corners", "shadow", "bold", "italic", "underline", "strike",
      "align"],
    note: ["fill", "line", "text", "opacity", "weight", "corners", "shadow", "bold", "italic", "underline", "strike",
      "align", "list"],
    frame: ["fill", "line", "text", "opacity", "weight", "corners", "italic", "underline", "strike"],
    text: ["text", "bold", "italic", "underline", "strike", "align", "list"], line: ["line", "text"],
  };

  /* Styles (V16): five to start from, and the diagram's own, saved by name
   * in its file (`saved_styles:`). A style is a look: chosen, it is copied
   * onto what is picked, one step for Undo, as Copy the look paints, and its
   * chip is ticked while the look is the style's. */
  var STYLES = [
    ["Service", { fill: "accent" }],
    ["Data", { fill: "stone" }],
    ["Outside", { fill: "white", line: "dashed", shadow: "none" }],
    ["Risk", { fill: "rose", weight: "l", bold: true }],
    ["Quiet", { fill: "white", weight: "s", shadow: "none" }],
  ];

  // Whether a look is a style's, over what the kind takes, each side's fill
  // as it shows.
  function sameLook(style, a) {
    var mine = lookOf(a);
    return (PAINTS[a.role] || []).every(function (k) {
      var x = style[k], y = mine[k];
      if (k === "fill") { x = x || ROLE_FILL[a.role]; y = y || ROLE_FILL[a.role]; }
      return (x === undefined ? null : x) === (y === undefined ? null : y);
    });
  }

  // A style's chip: its fill and edge in little, its name under it, and
  // for one of the diagram's own a way to take it out.
  function styleChip(name, l, a, key, redo, remove) {
    var eng = Canvas.engine;
    var edge = (l.weight === "l" ? 2 : l.weight === "s" ? 0.75 : 1.25) + "px " + (l.line === "dashed" ? "dashed" : "solid") +
      " " + (l.line === "none" ? "transparent" : eng.INK);
    var b = el("button", { type: "button", class: "cv-style", title: name, "aria-pressed": String(sameLook(l, a)),
      onclick: function () { paintOnto([key], l); redo(); } }, [
      el("span", { class: "cv-style-sw" }, [el("span", { class: "cv-style-chip",
        style: "background:" + (eng.FILLS[l.fill || "white"] || "transparent") + ";border:" + edge }),
        el("span", { class: "cv-style-bar" })]),
      el("span", { class: "cv-style-name", text: name })]);
    var kids = [b];
    if (remove) {
      kids.push(el("button", { type: "button", class: "cv-style-x", title: "Remove the style " + name,
        "aria-label": "Remove the style " + name, onclick: remove }, [svgIcon("i-x")]));
    }
    return el("div", { class: "cv-style-wrap", role: "listitem" }, kids);
  }

  // The estate's saved styles written whole to model.yaml, and offered
  // on every diagram from now.
  function keepEstateStyles(list, redo) {
    api("/api/canvas/styles", { styles: list }).then(function (res) {
      if (cv && cv.parts) cv.parts.styles = res.styles || [];
      redo();
    }).catch(fail);
  }

  function stylesSection(a, key, redo) {
    var d = cv.data, row = el("div", { class: "cv-styles", role: "list", "aria-label": "Styles" });
    var every = (cv.parts && cv.parts.styles) || [];
    STYLES.forEach(function (s) { row.appendChild(styleChip(s[0], s[1], a, key, redo)); });
    // The estate's, offered on every diagram, kept in model.yaml.
    every.forEach(function (s) {
      var chip = styleChip(s.name, s.look || {}, a, key, redo, function () {
        keepEstateStyles(every.filter(function (o) { return o !== s; }), redo);
      });
      chip.classList.add("is-estate");
      chip.querySelector(".cv-style").title = s.name + ", for every diagram";
      row.appendChild(chip);
    });
    (d.saved_styles || []).forEach(function (s) {
      row.appendChild(styleChip(s.name, s.look || {}, a, key, redo, function () {
        d.saved_styles = (d.saved_styles || []).filter(function (o) { return o !== s; });
        if (!d.saved_styles.length) delete d.saved_styles;
        canvasSoon(0);
        redo();
      }));
    });
    var form = el("div", { class: "cv-style-form", hidden: "" });
    var name = el("input", { type: "text", class: "cv-input", maxlength: "40", placeholder: "Name the style",
      "aria-label": "The style's name" });
    var said = el("p", { class: "cv-small", hidden: "" });
    var keep = function () {
      var n = name.value.trim();
      var taken = STYLES.map(function (s) { return s[0]; }).concat((d.saved_styles || []).map(function (s) { return s.name; }),
        every.map(function (s) { return s.name; }));
      said.hidden = false;
      if (!n) { said.textContent = "Give it a name first."; return; }
      if (taken.some(function (t) { return t.toLowerCase() === n.toLowerCase(); })) {
        said.textContent = n + " is a style already.";
        return;
      }
      var made = { name: n, look: lookOf(Canvas.engine.item(key)) };
      if (forEvery) { keepEstateStyles(every.concat([made]), redo); return; }
      d.saved_styles = (d.saved_styles || []).concat([made]);
      canvasSoon(0);
      redo();
    };
    name.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); keep(); }
      else if (e.key === "Escape") { e.preventDefault(); form.hidden = true; said.hidden = true; }
    });
    // Kept in this diagram's file, or in model.yaml for every diagram.
    var forEvery = false;
    var where = segmented("Where the style is kept", [["here", "This diagram"], ["every", "Every diagram"]], "here",
      function (v) {
        forEvery = v === "every";
        Array.prototype.forEach.call(where.children, function (b, i) { b.setAttribute("aria-checked", String((i === 1) === forEvery)); });
      });
    form.appendChild(where);
    form.appendChild(name);
    form.appendChild(el("button", { type: "button", class: "btn small", onclick: keep }, [el("span", { text: "Save" })]));
    var open = el("button", { type: "button", class: "cv-link-b", text: "Save this as a style",
      onclick: function () { form.hidden = false; name.focus(); } });
    return section("Styles", open, [row, form, said]);
  }

  // The words' toolbar (V16): bold, italic, underline and strikethrough for
  // all of its words, a note's or text's lines as a list, and where they
  // sit. A frame's name is bold already, at its left, on one line.
  function wordsTools(a, look, change, redo) {
    var row = el("div", { class: "cv-words-tools", role: "toolbar", "aria-label": "How the words are set" });
    var toggles = [["italic", "Italic", "i-italic"], ["underline", "Underline", "i-underline"],
      ["strike", "Strikethrough", "i-strike"]];
    if (a.role !== "frame") toggles.unshift(["bold", "Bold", "i-bold"]);
    if (a.role === "note" || a.role === "text") toggles.push(["list", "A list of its lines", "i-list"]);
    toggles.forEach(function (t) {
      row.appendChild(el("button", { type: "button", class: "cv-tool-b", title: t[1], "aria-label": t[1],
        "aria-pressed": String(look[t[0]] === true), onclick: function () {
          var p = {};
          p[t[0]] = look[t[0]] === true ? null : true;
          // A list sits at the left.
          if (t[0] === "list") p.align = null;
          change({ look: p });
        } }, [svgIcon(t[2])]));
    });
    // Its last button sets where its words link to (linkRow).
    row.appendChild(el("button", { type: "button", class: "cv-tool-b", title: a.link ? "Its link: " + a.link : "Link",
      "aria-label": "Link", "aria-pressed": String(!!a.link || Canvas.linkFor === a.key), onclick: function () {
        Canvas.linkFor = Canvas.linkFor === a.key ? null : a.key;
        redo();
      } }, [svgIcon("i-link")]));
    if (a.role !== "frame" && !look.list) {
      var home = a.role === "shape" ? "center" : "left", now = look.align || home;
      var aligns = el("span", { class: "cv-tool-set", role: "radiogroup", "aria-label": "Where the words sit" });
      [["left", "To the left", "i-text-left"], ["center", "In the middle", "i-text-center"],
        ["right", "To the right", "i-text-right"]].forEach(function (t) {
        aligns.appendChild(el("button", { type: "button", role: "radio", class: "cv-tool-b", title: t[1], "aria-label": t[1],
          "aria-checked": String(now === t[0]), onclick: function () { change({ look: { align: t[0] === home ? null : t[0] } }); } },
          [svgIcon(t[2])]));
      });
      row.appendChild(aligns);
    }
    return row;
  }

  // A look as it shows: a shape's paper and a note's yellow said outright,
  // so painted onto the other they come along.
  function lookOf(a) {
    var l = Object.assign({}, (a && a.look) || {});
    if (a && !l.fill && ROLE_FILL[a.role]) l.fill = ROLE_FILL[a.role];
    delete l.icon;
    return l;
  }

  function paintOnto(keys, l) {
    var eng = Canvas.engine;
    if (!eng || !eng.live() || !l) return 0;
    var painted = 0;
    eng.together(function () {
      keys.forEach(function (k) {
        var b = eng.item(k);
        if (!b || isLocked(k)) return;
        var patch = {};
        (PAINTS[b.role] || []).forEach(function (name) {
          var v = l[name];
          if (name === "line" && b.role === "line" && v === "none") return;
          if (name === "fill" && v && v === ROLE_FILL[b.role]) v = null;
          patch[name] = v === undefined ? null : v;
        });
        eng.update(k, { look: patch });
        painted += 1;
      });
    });
    return painted;
  }

  function startPainting(a) {
    Canvas.painting = { look: lookOf(a), from: a.key };
    document.body.classList.add("cv-painting");
  }

  function stopPainting() {
    Canvas.painting = null;
    document.body.classList.remove("cv-painting");
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
    if (k === "Escape" && Canvas.painting) {
      stopPainting();
      if (cv.sel) canvasSelect(cv.sel, true);
    }
    else if (mod && !e.altKey && (k === "z" || k === "Z")) canvasUndo(!e.shiftKey);
    else if (mod && (k === "y" || k === "Y")) canvasUndo(false);
    // By the key's place, not its letter: with Alt held a layout may type
    // another character.
    else if (mod && e.altKey && (e.code === "BracketRight" || e.code === "BracketLeft") && keys.length) {
      moveToLayer(keys, e.code === "BracketRight" ? -1 : 1);
    }
    else if (mod && e.altKey && e.code === "KeyC" && keys.length) Canvas.copiedLook = lookOf(eng.item(keys[0]));
    else if (mod && e.altKey && e.code === "KeyV" && keys.length && Canvas.copiedLook) {
      paintOnto(keys, Canvas.copiedLook);
      if (cv.sel) canvasSelect(cv.sel, true);
    }
    else if (k === "Escape" && (DRAWING_TOOLS[cv.tool] || cv.tool === "pan")) setCanvasTool("select");
    else if (!mod && !e.altKey && (k === "v" || k === "V")) setCanvasTool("select");
    else if (!mod && !e.altKey && (k === "h" || k === "H")) setCanvasTool("pan");
    else if (!mod && !e.altKey && TOOL_KEYS[k.toLowerCase()] && ownTools()) setCanvasTool(TOOL_KEYS[k.toLowerCase()]);
    else if (!mod && !e.altKey && (k === "a" || k === "A")) $("cvAdd").click();
    else if (!mod && !e.altKey && (k === "b" || k === "B")) openCanvasPicker("boundaries");
    else if (!mod && k === "?") toggleKeys();
    else if (mod && e.shiftKey && (k === "g" || k === "G")) groupThem();
    else if (mod && e.shiftKey && (k === "u" || k === "U")) ungroupPicked();
    else if (mod && (k === "g" || k === "G") && pickedBoxes(cv.sel).length) frameThem();
    else if (mod && e.shiftKey && (k === "l" || k === "L") && toggleLockPicked()) { /* said in the panel */ }
    else if (mod && !e.shiftKey && (k === "c" || k === "C") && canvasCopy()) { /* kept */ }
    else if (mod && !e.shiftKey && (k === "v" || k === "V") && canvasPaste()) { /* drawn */ }
    else if (cv.sel && cv.sel.kind === "several" && /^Arrow/.test(k)) {
      var dx = k === "ArrowLeft" ? -step : k === "ArrowRight" ? step : 0, dy = k === "ArrowUp" ? -step : k === "ArrowDown" ? step : 0;
      movePicked(pickedBoxes(cv.sel).map(function (it) { return { item: it, dx: dx, dy: dy }; }));
    }
    else if (!keys.length) done = false;
    else if (k === "Delete" || k === "Backspace") eng.remove(keys);
    else if (k === "Escape") { if (!goOut()) eng.select([]); }
    else if (mod && (k === "d" || k === "D")) regrouping(groupsOf(), function () { return eng.copy(keys); });
    else if (mod && k === "]") eng.order(keys, false);
    else if (mod && k === "[") eng.order(keys, true);
    else if (/^Arrow/.test(k)) {
      var free = keys.filter(function (key) { return !isLocked(key); });
      if (free.length) eng.nudge(free, k === "ArrowLeft" ? -step : k === "ArrowRight" ? step : 0,
        k === "ArrowUp" ? -step : k === "ArrowDown" ? step : 0);
    }
    else if (k === "Enter" && keys.length === 1) eng.edit(keys[0]);
    else done = false;
    if (done) { e.preventDefault(); e.stopPropagation(); }
  }
  document.addEventListener("keydown", canvasKeys, true);
  document.addEventListener("mousedown", function (e) {
    var menu = $("cvShapeMenu");
    if (menu && !menu.hidden && !menu.contains(e.target) && !(menuFor && $(menuFor).contains(e.target))) closeShapeMenu();
  });

  /* ---- copy and paste, across diagrams ----
   * What is picked, kept in this browser: the diagram's own as shapes and
   * lines at their places on the sheet, the records by id. Pasted on any
   * canvas diagram, the records it does not draw are placed on it, where
   * there is room as Add places them, and the shapes drawn with new keys:
   * on the diagram they came from, a step down and across from where they
   * were; on another, in the middle of what the sheet shows. */
  var CLIP_KEY = "aac.canvas.clip";
  var clipHeld = null;

  function canvasCopy() {
    if (!cv) return false;
    var eng = Canvas.engine && Canvas.engine.live() ? Canvas.engine : null;
    var ids = pickedIds(cv.sel), keys = eng ? eng.selected() : [];
    if (!ids.length && !keys.length) return false;
    var clip = { from: cv.id || "", model: (state.overview && state.overview.modelName) || "",
      own: keys.length ? eng.clip(keys) : [], records: ids.slice(), pasted: 0, groups: groupsOf() };
    clipHeld = clip;
    try { localStorage.setItem(CLIP_KEY, JSON.stringify(clip)); } catch (e) { /* private mode: this page only */ }
    var words = [];
    if (ids.length) words.push(ids.length === 1 ? "1 record" : ids.length + " records");
    if (clip.own.length) words.push(clip.own.length + " of its own");
    toast("ok", "Copied " + words.join(" and "), "Ctrl+V puts it on this diagram or another.");
    return true;
  }

  function heldClip() {
    try {
      var kept = localStorage.getItem(CLIP_KEY);
      if (kept) return JSON.parse(kept);
    } catch (e) { /* private mode */ }
    return clipHeld;
  }

  function canvasPaste() {
    var clip = heldClip();
    if (!cv || !clip || (!(clip.own || []).length && !(clip.records || []).length)) return false;
    var mine = cv, cy = state.cy;
    // The records this estate has and this diagram does not draw yet.
    var known = {};
    (state.index || []).forEach(function (it) { known[it.id] = true; });
    var adding = (clip.records || []).filter(function (id) {
      return known[id] && pinsOf().indexOf(id) === -1 && !drawnHere(id);
    });
    var strange = (clip.records || []).filter(function (id) { return !known[id]; });
    var own = clip.own || [];
    // Where the shapes go: a step on from where they were on their own
    // diagram, a step more each time; else the middle of the sheet.
    var dx = 0, dy = 0;
    if (own.length) {
      var boxes = own.filter(function (a) { return a.box; });
      var x1 = Math.min.apply(null, boxes.map(function (a) { return a.box.x; }).concat([Infinity]));
      var y1 = Math.min.apply(null, boxes.map(function (a) { return a.box.y; }).concat([Infinity]));
      var x2 = Math.max.apply(null, boxes.map(function (a) { return a.box.x + a.box.w; }).concat([-Infinity]));
      var y2 = Math.max.apply(null, boxes.map(function (a) { return a.box.y + a.box.h; }).concat([-Infinity]));
      if (clip.from && clip.from === cv.id) {
        clip.pasted = (clip.pasted || 0) + 1;
        dx = dy = 24 * clip.pasted;
      } else if (cy && isFinite(x1)) {
        var ext = cy.extent();
        dx = Math.round((ext.x1 + ext.x2) / 2 - (x1 + x2) / 2);
        dy = Math.round((ext.y1 + ext.y2) / 2 - (y1 + y2) / 2);
      }
      clipHeld = clip;
      try { localStorage.setItem(CLIP_KEY, JSON.stringify(clip)); } catch (e) { /* private mode */ }
    }
    function drawOwn() {
      if (cv !== mine || !own.length || !Canvas.engine || !Canvas.engine.live()) return [];
      return regrouping(clip.groups, function () { return Canvas.engine.paste(own, dx, dy); });
    }
    function said(made) {
      var words = [];
      if (adding.length) words.push(adding.length === 1 ? "1 record" : adding.length + " records");
      if (made.length) words.push(made.length + " of its own");
      var more = strange.length ? " " + strange.length + " of the records copied are not in this estate, and are left out." : "";
      if (!words.length) {
        toast("ok", "Nothing to paste here", "What was copied is on this diagram already." + more);
        return;
      }
      toast("ok", "Pasted " + words.join(" and "), (adding.length ? "The records go where the diagram has room. " : "") + more);
    }
    if (!adding.length) {
      said(drawOwn());
      return true;
    }
    adding.forEach(function (id) { pinsOf().push(id); });
    canvasSave().then(canvasDraw).then(function () {
      if (cv !== mine) return;
      var made = drawOwn();
      said(made);
      // What was pasted is picked, the records with the shapes.
      canvasPick(adding.slice(), made);
    }).catch(fail);
    return true;
  }

  /* ---- a key for every tool ----
   * The drawing tools by their first letter, a shape by R as most tools
   * have it; Select and the Hand are V and H, above. The sheet behind "?
   * for keys" and the command palette say the same keys from this list. */
  var TOOL_KEYS = { r: "shape", t: "text", n: "note", f: "frame", l: "line" };
  var KEY_SHEET = [
    ["Tools", [["V", "Select"], ["H", "Hand, or hold Space"], ["R", "Shape, the last one chosen"], ["T", "Text"],
      ["N", "Note"], ["F", "Frame"], ["L", "Line, the last route chosen"], ["A", "Add from the library or the estate"],
      ["B", "Add a boundary"]]],
    ["Editing", [["Ctrl+Z", "Undo"], ["Ctrl+Shift+Z", "Redo"], ["Delete", "Delete its own"], ["Ctrl+D", "Duplicate"], ["Ctrl+C", "Copy, for this diagram or another"], ["Ctrl+V", "Paste"],
      ["Ctrl+Alt+C", "Copy the look"], ["Ctrl+Alt+V", "Paint the look copied"], ["Ctrl+Shift+G", "Group them"],
      ["Ctrl+Alt+]", "To the drawing layer above"], ["Ctrl+Alt+[", "To the drawing layer below"],
      ["Ctrl+Shift+U", "Ungroup"],
      ["Ctrl+] [", "Forward, back"], ["Arrows", "Nudge, Shift by ten"], ["Enter", "Type in it"],
      ["Ctrl+G", "Frame what is picked"], ["Ctrl+Shift+L", "Lock or unlock it here"], ["Esc", "Let go"]]],
    ["Around", [["Ctrl+K", "Commands and search"], ["/", "Search"], ["Shift+click", "Pick one more, or one fewer"],
      ["?", "These keys"]]],
  ];

  // The diagram's own tools, which a view written as a query does not take.
  function ownTools() {
    return !$("cvTools").classList.contains("no-own");
  }

  function toggleKeys(open) {
    var sheet = $("cvKeys"), btn = $("cvKeysBtn");
    if (!sheet) return;
    var show = open === undefined ? sheet.hidden : !!open;
    if (show && !sheet.firstChild) {
      KEY_SHEET.forEach(function (group) {
        var dl = el("dl");
        group[1].forEach(function (row) {
          dl.appendChild(el("dt", null, row[0].split(" ").map(function (k) { return el("kbd", { text: k }); })));
          dl.appendChild(el("dd", { text: row[1] }));
        });
        sheet.appendChild(el("section", null, [el("h3", { text: group[0] }), dl]));
      });
    }
    sheet.hidden = !show;
    btn.setAttribute("aria-expanded", String(show));
  }

  /* The canvas's tools and actions in the command palette, first while it
   * is open, each with its key. */
  function canvasPaletteActions() {
    if (!cv) return [];
    var out = [{ kind: "action", name: "Select", hint: "Tool \u00b7 V", go: function () { setCanvasTool("select"); } },
      { kind: "action", name: "Hand", hint: "Tool \u00b7 H", go: function () { setCanvasTool("pan"); } }];
    if (ownTools()) {
      [["Shape", "shape", "R"], ["Text", "text", "T"], ["Note", "note", "N"], ["Frame", "frame", "F"],
        ["Line", "line", "L"]].forEach(function (t) {
        out.push({ kind: "action", name: t[0], hint: "Tool \u00b7 " + t[2], go: function () { setCanvasTool(t[1]); } });
      });
    }
    out.push({ kind: "action", name: "Add from the library or the estate", hint: "A", go: function () { $("cvAdd").click(); } });
    if (cv.undo.length) out.push({ kind: "action", name: "Undo", hint: "Ctrl+Z", go: function () { canvasUndo(true); } });
    if (cv.redo.length) out.push({ kind: "action", name: "Redo", hint: "Ctrl+Shift+Z", go: function () { canvasUndo(false); } });
    if (pickedBoxes(cv.sel).length) out.push({ kind: "action", name: "Frame what is picked", hint: "Ctrl+G", go: frameThem });
    if (pickedBoxes(cv.sel).length) out.push({ kind: "action", name: "Copy what is picked", hint: "Ctrl+C", go: canvasCopy });
    if (pickedNames().length) out.push({ kind: "action", name: pickedNames().every(isLocked) ? "Unlock what is picked"
      : "Lock what is picked", hint: "Ctrl+Shift+L", go: toggleLockPicked });
    if (heldClip()) out.push({ kind: "action", name: "Paste", hint: "Ctrl+V", go: canvasPaste });
    out.push({ kind: "action", name: snapOn() ? "Snap to grid off" : "Snap to grid on", hint: "The ten-unit grid",
      go: toggleSnap });
    out.push({ kind: "action", name: jumpsOn() ? "Line jumps off" : "Line jumps on",
      hint: "Where lines cross, one hops the other", go: toggleJumps });
    if (canvasKept()) out.push({ kind: "action", name: "Lay out again", hint: "Hand every box back to the layout",
      go: canvasLayOutAgain });
    out.push({ kind: "action", name: "Keys", hint: "?", go: function () { toggleKeys(true); } });
    return out;
  }

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

    box.appendChild(el("div", { class: "cv-field" }, [el("span", { class: "cv-label", text: "Look" }), lookChoice()]));

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
        el("button", { type: "button", class: "cv-link", text: firstLine(a.label), onclick: function () { pick([a.key]); } }),
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
      acts.appendChild(lockButton([id]));
      box.appendChild(acts);
      var held = lockedNote([id]);
      if (held) box.appendChild(held);
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

  /* ---- Add on shelves (V18) ----
   * The library's kinds by what each is for, its kits, and the estate's
   * systems and boundaries, a shelf each, every shelf under its headings.
   * It was four tabs over one list: Library showed the eleven kits and the
   * first fourteen of 109 kinds, unsorted, and the database, the queue and
   * the other ninety-five were reachable only by typing their names. */

  //: Add's shelves, in the order they are listed: the library's four, which
  //: the server tells apart (`_shelf_of` in server.py), and the estate's two.
  var SHELVES = [
    { id: "kits", side: "library", name: "Whole applications", icon: "blocks",
      say: "A kit places the systems an application is made of, with their lines, in the account you drop it in." },
    { id: "parts", side: "library", name: "Parts of an application", icon: "box",
      say: "One box each: the pieces a system you build is made of, each in the zone it usually runs in." },
    { id: "business", side: "library", name: "Business systems", icon: "building-2",
      say: "One box each: what an organization runs, mostly bought, so it sits in no subnet of ours." },
    { id: "blocks", side: "library", name: "Building blocks", icon: "layers",
      say: "Several cloud services that arrive together, with their lines. Dropped in an account, they are that cloud's products." },
    { id: "cloud", side: "library", name: "Cloud services", icon: "cloud",
      say: "One box each: what systems run on. Dropped in an account, it is that cloud's product." },
    { id: "systems", side: "estate", name: "Systems", found: "Systems in this estate", icon: "database",
      say: "The estate's own systems, by domain. Placed as they are, where they belong." },
    { id: "data", side: "estate", name: "Data", found: "Data in this estate", icon: "table",
      say: "The estate's data, by classification. Placed, each is joined by a line to the systems on the diagram that read or write it." },
    { id: "actors", side: "estate", name: "Actors", icon: "circle-user",
      say: "Who uses the systems, outside the company and inside it. Placed, each is joined by a line to the systems on the diagram it uses." },
    { id: "teams", side: "estate", name: "Teams", icon: "users",
      say: "The organization's units, under the one each sits in. Placed, each is joined by a line to what it owns on the diagram." },
    { id: "boundaries", side: "estate", name: "Boundaries", icon: "square-dashed", say: "" },
  ];

  //: The shelf Add opens on, the one picked last, kept per browser.
  var SHELF_KEY = "aac.add.shelf";

  //: The shelves of what is placed whole, rather than as a box: quick
  //: connect joins its line to one box, so it offers none of these.
  var WHOLE_SHELVES = ["kits", "blocks", "boundaries"];

  //: The lines a record placed from Add brings (V19): what reads and writes
  //: a data asset and the system that keeps its master, the systems an
  //: actor uses, what a team owns, and a block's services' own. A new
  //: diagram draws interfaces alone, so a data asset placed on it stood by
  //: itself beside the systems that write it.
  var LINES_OF = { data_assets: ["system_reads_writes", "source_of_truth"], actors: ["actor_uses_system"],
    org_units: ["owner"], tech_services: ["tech_service_connects_to"] };

  function addLines(type) {
    var want = LINES_OF[type] || [];
    if (!want.length) return;
    if (!Array.isArray(cv.data.edges) || !cv.data.edges.length) cv.data.edges = [{ via: "interfaces" }];
    want.forEach(function (via) {
      if (!cv.data.edges.some(function (e) { return e && e.via === via; })) cv.data.edges.push({ via: via });
    });
  }

  // A word for more than one: a capability, two capabilities.
  function plural(word) {
    return /[^aeiou]y$/.test(word) ? word.slice(0, -1) + "ies" : /(s|x|ch|sh)$/.test(word) ? word + "es" : word + "s";
  }

  // "ten more systems", in a sentence.
  function inWords(n, word) {
    var said = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"][n];
    return (said || String(n)) + " " + (n === 1 ? word : plural(word));
  }

  // Who writes a data asset, keeps its master and reads it, said.
  function dataSaid(d) {
    var parts = [], others = (d.writers || []).filter(function (w) { return w !== d.master; });
    if (d.master && (d.writers || []).indexOf(d.master) !== -1) parts.push(d.master + " writes it and keeps the master");
    else if (d.master) parts.push(d.master + " keeps the master");
    if (others.length) parts.push(listed(others) + (others.length === 1 ? " writes" : " write") + " it");
    if (d.readers) parts.push(inWords(d.readers, parts.length ? "more system" : "system") + (d.readers === 1 ? " reads" : " read") + " it");
    if (!parts.length) return "No system is recorded reading or writing it.";
    var said = parts.join("; ");
    return said.charAt(0).toUpperCase() + said.slice(1) + ". Placed, a line joins it to each of them that is on the diagram.";
  }

  // The systems an actor uses, said, the first few by name.
  function usesSaid(a) {
    var uses = a.uses || [];
    if (!uses.length) return "No system is recorded as one it uses.";
    var named = uses.length > 4 ? uses.slice(0, 3).concat([inWords(uses.length - 3, "more system")]) : uses;
    return "Uses " + listed(named) + ". Placed, a line joins it to each of them that is on the diagram.";
  }

  // What a team owns, said by kind, the three it has most of by name.
  function ownsSaid(t) {
    var owns = t.owns || [];
    if (!owns.length) return "It owns nothing in the estate yet.";
    var named = owns.slice(0, 3).map(function (o) { return o[1] + " " + (o[1] === 1 ? o[0] : plural(o[0])); });
    var rest = owns.slice(3).reduce(function (n, o) { return n + o[1]; }, 0);
    if (rest) named.push(rest + " more " + (rest === 1 ? "record" : "records"));
    return "Owns " + listed(named) + ". Placed, a line joins it to each of them that is on the diagram.";
  }

  //: How many of one shelf's finds Everything found shows before a link to
  //: the rest, so a short word does not bury the other shelves under one.
  var FOUND_EACH = 8;

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

  // An icon of the kinds' own (kind-icons.js), else the chrome's sprite.
  function lucide(name) {
    var drawn = (window.TerraneKindIcons || {}).icons || {};
    if (!drawn[name]) return svgIcon("i-" + name);
    var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", "i");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("aria-hidden", "true");
    svg.innerHTML = drawn[name];
    return svg;
  }

  // The icon beside a kind: its own, else its category's, else a box.
  function kindIconName(part) {
    var t = window.TerraneKindIcons || {};
    return (t.kinds || {})[part.id] || (t.categories || {})[part.category] || "box";
  }

  function lowerFirst(text) {
    // "AI agent" keeps its capitals; "Async worker" is the async worker.
    return /^[A-Z][a-z]/.test(text) ? text.charAt(0).toLowerCase() + text.slice(1) : text;
  }

  function listed(words) {
    return words.length < 2 ? words.join("") : words.slice(0, -1).join(", ") + " and " + words[words.length - 1];
  }

  /* Which kits make a system of this kind, and as what: "Also in the
   * Event-driven service kit, as its async worker." A kit that makes two
   * of it says both. */
  function kitsSaid(kits) {
    var by = [], seen = {};
    (kits || []).forEach(function (k) {
      if (!seen[k.id]) { seen[k.id] = { name: k.name, as: [] }; by.push(seen[k.id]); }
      if (seen[k.id].as.indexOf(k.as) === -1) seen[k.id].as.push(k.as);
    });
    if (!by.length) return "";
    var as = function (k) { return listed(k.as.map(lowerFirst)); };
    var same = by.every(function (k) { return as(k) === as(by[0]); });
    if (by.length > 3) return "Also in " + by.length + " kits" + (same ? ", as their " + as(by[0]) : "") + ".";
    if (by.length === 1) return "Also in the " + by[0].name + " kit, as its " + as(by[0]) + ".";
    if (same) return "Also in the " + listed(by.map(function (k) { return k.name; })) + " kits, as their " + as(by[0]) + ".";
    return "Also in " + listed(by.map(function (k) { return "the " + k.name + " kit as its " + as(k); })) + ".";
  }

  // What a kind is sold as, said short: one maker's answer whole, or the
  // usual product of each cloud.
  function offeredSaid(x) {
    var clouds = Object.keys(x.providers || {});
    if (clouds.length === 1) return String(x.providers[clouds[0]]).replace(/\s*\(formerly [^)]*\)/g, "");
    return clouds.map(function (c) { return ((x.products || {})[c] || [])[0]; }).filter(Boolean).join(", ");
  }

  /* Everything Add offers, shelf by shelf, each with the heading it is
   * listed under: the kinds as the server orders them, the kits by their
   * category, the estate's systems by domain and its boundaries by what
   * they are. Opened by quick connect, only what is a box. */
  function shelfItems(link) {
    var p = cv.parts, out = {};
    SHELVES.forEach(function (s) { out[s.id] = []; });
    (link ? [] : p.blocks || []).forEach(function (b) {
      out.blocks.push({ kind: "block", id: b.id, name: b.name, block: b, group: b.category, tag: "Block", icon: "layers",
        sub: counted(b.services.length, "cloud service") + ": " + b.services.map(function (s) { return s.name; }).join(" \u00b7 "),
        find: b.name + " " + b.category });
    });
    (p.data || []).forEach(function (d) {
      out.data.push({ kind: "record", type: "data_assets", id: d.id, name: d.name, src: d, group: d.classification || "Unclassified",
        tag: "Data", icon: "table", sub: d.domain, find: d.name + " " + d.id + " " + d.classification + " " + d.domain });
    });
    (p.actors || []).forEach(function (a) {
      out.actors.push({ kind: "record", type: "actors", id: a.id, name: a.name, src: a,
        group: a.internal ? "Inside the company" : "Outside the company", tag: "Actor", icon: "circle-user", sub: a.kind,
        find: a.name + " " + a.id + " " + a.kind });
    });
    (p.teams || []).forEach(function (t) {
      out.teams.push({ kind: "record", type: "org_units", id: t.id, name: t.name, src: t,
        group: t.parent ? "In " + t.parent : "At the top", tag: "Team", icon: "users", sub: t.parent,
        find: t.name + " " + t.id + " " + t.parent });
    });
    if (!link) (p.kits || []).forEach(function (k) {
      out.kits.push({ kind: "kit", id: k.id, name: k.name, kit: k, group: k.category, tag: "Kit", icon: "blocks",
        sub: counted(k.systems.length, "system") + ": " + k.systems.map(function (s) { return s.name; }).join(" · "),
        find: k.name + " " + k.category });
    });
    (p.parts || []).forEach(function (x) {
      (out[x.shelf] || out.cloud).push({ kind: "part", id: x.id, name: x.name, part: x.name, src: x,
        group: x.group || x.category, products: x.products || {}, product: "", cloud: "", typeLabel: x.typeLabel,
        type: x.type, tag: "Box", icon: kindIconName(x), sub: offeredSaid(x) });
    });
    // By domain, the domains in alphabetical order and the systems of none
    // after them.
    (p.systems || []).map(function (s, i) { return { s: s, i: i }; }).sort(function (a, b) {
      return (!a.s.domain) - (!b.s.domain) || a.s.domain.toLowerCase().localeCompare(b.s.domain.toLowerCase()) || a.i - b.i;
    }).forEach(function (o) {
      var s = o.s;
      out.systems.push({ kind: "system", id: s.id, name: s.name, src: s, group: s.domain || "No domain", tag: "System",
        icon: "app-window", sub: "", find: s.name + " " + s.id + " " + s.domain });
    });
    if (!link) boundaryItems(p, out.boundaries);
    SHELVES.forEach(function (s) { out[s.id].forEach(function (i) { i.shelf = s.id; }); });
    return out;
  }

  function boundaryItems(p, into) {
    p.views.slice().sort(function (a, b) { return (a.id !== p.network) - (b.id !== p.network); }).forEach(function (v) {
      var accounts = v.fold && v.fold.field === "cloud_account"
        ? v.fold.values.filter(function (x) { return x.value; }).length : 0;
      into.push({ kind: "view", id: v.id, name: v.title, group: "Views", tag: "Boundary",
        icon: v.id === p.network ? "network" : "grid", find: v.title + " " + v.category,
        sub: "View · " + v.nodes + " " + nodesWord(v) + (accounts ? ", " + accounts + " accounts" : "") });
    });
    p.accounts.forEach(function (a) {
      into.push({ kind: "account", value: a.value, name: a.value, group: "Accounts", tag: "Boundary",
        icon: "cloud", find: a.label, sub: a.label.split(" · ")[0] + " account · " + a.count + " network parts" });
    });
    p.zones.forEach(function (z) {
      into.push({ kind: "zone", value: z.value, name: z.value, group: "Network zones", tag: "Boundary",
        icon: "shield", find: z.value + " zone", sub: "Network zone · " + z.count + " network parts" });
    });
  }

  /* How an item answers what was typed, or null: how near (`closeness`),
   * and for a kind found by what a cloud or a maker calls it, that product,
   * which it is then placed as. */
  function answers(item, q) {
    var hit = function (text) { return String(text || "").toLowerCase().indexOf(q) !== -1; };
    if (item.kind === "part") {
      var x = item.src;
      if (hit([x.name, x.category, x.group, x.typeLabel].concat(x.aliases || []).join(" "))) return { rank: closeness(x.name, q) };
      var said = null;
      // Of a kind's products the one closest to what was asked: "EC2" is
      // the virtual machine, placed as Amazon EC2.
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
      return said ? { rank: closeness(said.product, q), cloud: said.cloud, product: said.product } : null;
    }
    if (hit(item.find)) return { rank: closeness(item.name, q) };
    // A kit is found by a system it makes as well, after what is called so:
    // "chat" is the assistant chat's kind before the kit that has one.
    if (item.kind === "kit" && hit(item.kit.systems.map(function (s) { return s.name; }).join(" "))) return { rank: 9 };
    if (item.kind === "block" && hit(item.block.services.map(function (s) { return s.name; }).join(" "))) return { rank: 9 };
    return null;
  }

  // Items under their headings, the headings in the order they come.
  function headed(items) {
    var out = [], by = {};
    items.forEach(function (i) {
      if (!by[i.group]) { by[i.group] = { name: i.group, items: [] }; out.push(by[i.group]); }
      by[i.group].items.push(i);
    });
    return out;
  }

  function closeCanvasPicker() {
    var pick = $("cvPicker");
    if (cv) cv.connect = null;
    if (!pick) return;
    pick.hidden = true;
    pick.textContent = "";
    $("cvAdd").setAttribute("aria-expanded", "false");
  }

  /* Add: the shelves beside what the picked one holds, and below both what
   * the one pointed at is. Typed, every shelf is searched at once and what
   * was found is listed by shelf and heading, Everything found first.
   * Opened from the Boundaries key on Boundaries; from quick connect, only
   * what is a box, since what is chosen is joined to that record. */
  function openCanvasPicker(tab, boundaries, link) {
    if (!cv) return;
    var pick = $("cvPicker");
    closeCanvasPicker();
    if (link) cv.connect = link;
    pick.textContent = "";
    pick.hidden = false;
    // A drop that ended before its drag had begun left it faded and deaf
    // to clicks: a drag's own timer marks the list as carried.
    pick.classList.remove("is-carrying");
    $("cvAdd").setAttribute("aria-expanded", "true");
    var shelves = SHELVES.filter(function (s) { return !link || WHOLE_SHELVES.indexOf(s.id) === -1; });
    var ids = shelves.map(function (s) { return s.id; });
    var kept = "";
    try { kept = localStorage.getItem(SHELF_KEY) || ""; } catch (e) { kept = ""; }
    var library = ["kits", "parts", "business", "blocks", "cloud"];
    var first = boundaries || tab === "boundaries" ? "boundaries"
      : tab === "estate" ? (kept && library.indexOf(kept) === -1 ? kept : "systems")
      : tab === "library" ? (library.indexOf(kept) !== -1 ? kept : "parts")
      : kept;
    var at = { shelf: ids.indexOf(first) !== -1 ? first : "parts", found: "everything" };
    var items = shelfItems(link);
    var shown = [], current = -1, finds = null, moved = "";

    var search = el("input", { type: "search", class: "cv-search", "aria-label": "Find something to place",
      placeholder: "Find a kind, a product like RDS, a system, an account…" });
    var nav = el("div", { class: "cv-shelves", role: "tablist", "aria-label": "Shelves" });
    var list = el("div", { class: "cv-list" });
    var foot = el("div", { class: "cv-detail", "aria-live": "polite" });
    pick.appendChild(el("div", { class: "cv-search-row" }, [svgIcon("i-search"), search]));
    if (link) {
      pick.appendChild(el("p", { class: "cv-pick-link" }, [svgIcon("i-link"), el("span", {
        text: "What comes next to " + ((indexItem(link.from) || {}).name || link.from) + "? A line will join them." })]));
    }
    pick.appendChild(el("div", { class: "cv-shelf-body" }, [nav, list]));
    pick.appendChild(foot);

    function shelfOf(id) { return SHELVES.filter(function (s) { return s.id === id; })[0]; }

    function placeable(item, node) {
      var n = shown.length;
      shown.push(item);
      node.addEventListener("click", function () { canvasPlace(item, [], null); });
      node.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); canvasPlace(item, [], null); }
      });
      // Pointed at by a pointer that moved, not by the list redrawn under
      // one at rest: typing with the pointer on the list made the row
      // under it the one Enter placed.
      node.addEventListener("mousemove", function (e) {
        var xy = e.clientX + "," + e.clientY;
        if (xy === moved) return;
        moved = xy;
        if (current !== n) point(n, false);
      });
      node.addEventListener("focus", function () { point(n, false); });
      node.addEventListener("dragstart", function (e) {
        cvDrag = item;
        e.dataTransfer.effectAllowed = "copy";
        try { e.dataTransfer.setData("text/plain", item.name); } catch (err) { /* old engines */ }
        node.classList.add("is-dragging");
        setTimeout(function () { $("cvPicker").classList.add("is-carrying"); }, 0);
        $("cvEmpty").classList.add("is-drop");
        $("cvEmptyDrop").textContent = item.tag === "Boundary"
          ? "Drop to place " + item.name + " as a boundary" : "Drop to place " + (item.product || item.name);
      });
      node.addEventListener("dragend", function () {
        node.classList.remove("is-dragging");
        clearCanvasDrop();
        cvDrag = null;
      });
      return node;
    }

    function said(item) { return "Place " + (item.product || item.name) + (item.sub ? ", " + item.sub : ""); }

    // One of a shelf's kinds or systems, two to a row: its icon and name.
    function cell(item) {
      return placeable(item, el("div", { class: "cv-row is-cell", draggable: "true", tabindex: "0", role: "button",
        "aria-label": said(item), title: item.name }, [
        el("span", { class: "cv-grip" }, [svgIcon("i-grip")]),
        el("span", { class: "cv-ico" }, [lucide(item.icon)]),
        el("span", { class: "cv-cell-name", text: item.name }),
      ]));
    }

    // A kit or a boundary as it is browsed, or anything found: a line each.
    function row(item, found) {
      var note = found ? (item.product ? item.product + " · " + item.cloud : item.kind === "system" ? "" : item.sub) : item.sub;
      var whole = item.kind === "kit" || item.kind === "block";
      return placeable(item, el("div", { class: "cv-row" + (found ? " is-line" : "") + (whole && !found ? " is-kit" : ""),
        draggable: "true", tabindex: "0", role: "button", "aria-label": said(item) }, [
        el("span", { class: "cv-grip" }, [svgIcon("i-grip")]),
        el("span", { class: "cv-ico" }, [lucide(item.icon)]),
        el("span", { class: "cv-row-text" }, [el("b", { text: item.name }), note ? el("span", { text: note }) : null]),
        el("span", { class: "cv-tag" + (item.tag === "Boundary" ? " is-boundary" : item.tag === "Kit" || item.tag === "Block" ? " is-kit" : ""), text: item.tag }),
      ]));
    }

    function headings(groups, grid, found) {
      groups.forEach(function (g) {
        list.appendChild(el("p", { class: "cv-group" }, [el("span", { text: g.name }),
          el("span", { class: "cv-group-n", text: String(g.items.length) })]));
        var box = el("div", { class: grid ? "cv-grid" : "cv-rows" });
        g.items.forEach(function (i) { box.appendChild(grid ? cell(i) : row(i, found)); });
        list.appendChild(box);
      });
    }

    function shelfButton(id, name, n) {
      var on = (finds ? at.found : at.shelf) === id;
      return el("button", { type: "button", role: "tab", class: "cv-shelf" + (id === "everything" ? " is-all" : ""),
        "aria-selected": String(on), disabled: finds && !n && id !== "everything" ? "disabled" : null,
        onclick: function () {
          if (finds) at.found = id;
          else {
            at.shelf = id;
            try { localStorage.setItem(SHELF_KEY, id); } catch (e) { /* private mode: this page only */ }
          }
          render();
          list.scrollTop = 0;
        } }, [el("span", { text: name }), el("span", { class: "cv-shelf-n", text: String(n) })]);
    }

    function fillNav(total) {
      nav.textContent = "";
      if (finds) nav.appendChild(shelfButton("everything", "Everything found", total));
      [["library", "The library"], ["estate", "This estate"]].forEach(function (side) {
        var mine = shelves.filter(function (s) { return s.side === side[0]; });
        if (!mine.length) return;
        nav.appendChild(el("p", { class: "cv-shelf-side", text: side[1] }));
        mine.forEach(function (s) { nav.appendChild(shelfButton(s.id, s.name, (finds || items)[s.id].length)); });
      });
      nav.appendChild(el("p", { class: "cv-shelf-hint",
        text: finds ? "Pick a shelf to see only what it found." : "Opens on the shelf you used last." }));
    }

    // What was found on one shelf, under its headings in the shelf's order
    // and nearest first under each: "EC2" is the virtual machine before the
    // accelerated instances whose answer says EC2 too.
    function found(id, q) {
      var hits = items[id].map(function (item, i) {
        var a = answers(item, q);
        if (!a) return null;
        var hit = Object.assign({}, item, { near: a.rank }, a.product ? { product: a.product, cloud: a.cloud } : {});
        return { item: hit, group: item.group, at: i };
      }).filter(Boolean);
      return headed(hits).reduce(function (all, g) {
        // Equals keep the shelf's order; shortest first put Merchant Portal
        // Web ahead of Authorization Switch when "pay" was in neither name.
        return all.concat(g.items.sort(function (a, b) { return a.item.near - b.item.near || a.at - b.at; })
          .map(function (h) { return h.item; }));
      }, []);
    }

    // How near a shelf's best find is to what was typed.
    function nearest(id) {
      return finds[id].reduce(function (n, i) { return Math.min(n, i.near); }, 99);
    }

    function render() {
      var q = search.value.trim().toLowerCase();
      finds = null;
      var order = shelves;
      if (q) {
        finds = {};
        shelves.forEach(function (s) { finds[s.id] = found(s.id, q); });
        if (at.found !== "everything" && !finds[at.found].length) at.found = "everything";
        // The shelf with what was asked for first, the shelves' own order
        // between equals: "rds" is Amazon RDS before the work tracking
        // whose Azure Boards holds the letters.
        order = shelves.slice().sort(function (a, b) {
          return nearest(a.id) - nearest(b.id) || shelves.indexOf(a) - shelves.indexOf(b);
        });
      }
      var total = finds ? shelves.reduce(function (n, s) { return n + finds[s.id].length; }, 0) : 0;
      fillNav(total);
      list.textContent = "";
      shown = [];
      if (!finds) {
        var shelf = shelfOf(at.shelf);
        list.appendChild(el("div", { class: "cv-shelf-head" }, [el("h3", { text: shelf.name }), el("p", {
          text: shelf.id === "boundaries"
            ? "A view, or an account or zone of " + (cv.parts.networkTitle || "the network") + ", drawn as a box around what it holds."
            : shelf.say })]));
        headings(headed(items[shelf.id]), WHOLE_SHELVES.indexOf(shelf.id) === -1, false);
        if (!items[shelf.id].length) list.appendChild(el("p", { class: "cv-none", text: "Nothing on this shelf yet." }));
      } else {
        // Said once, from what was found: the first kind found by a
        // product's name says how.
        var byProduct = null;
        order.forEach(function (s) {
          finds[s.id].forEach(function (i) { if (i.product && (!byProduct || i.near < byProduct.near)) byProduct = i; });
        });
        list.appendChild(el("div", { class: "cv-shelf-head" }, [
          el("h3", { text: counted(total, "thing") + " found for “" + search.value.trim() + "”" }),
          el("p", { text: !total ? "Nothing on any shelf is called that." : "By shelf." + (byProduct
            ? " A kind is found by what its makers call it too: “" + byProduct.product + "” is listed under "
              + byProduct.name + "." : "") })]));
        order.forEach(function (s) {
          if (at.found !== "everything" && at.found !== s.id) return;
          var all = finds[s.id];
          if (!all.length) return;
          var some = at.found === "everything" ? all.slice(0, FOUND_EACH) : all;
          list.appendChild(el("p", { class: "cv-found-shelf" }, [lucide(s.icon), el("span", { text: s.found || s.name })]));
          headings(headed(some), false, true);
          if (some.length < all.length) {
            list.appendChild(el("button", { type: "button", class: "cv-link cv-found-more",
              text: "All " + all.length + " found on " + s.name, onclick: function () {
                at.found = s.id;
                render();
                list.scrollTop = 0;
              } }));
          }
        });
      }
      point(finds && shown.length ? 0 : -1, false);
    }

    // The one pointed at, by the pointer or the arrow keys: marked, and said
    // in the foot. Found, the first is pointed at, and Enter places it.
    function point(n, scroll) {
      current = n;
      var nodes = list.querySelectorAll(".cv-row");
      Array.prototype.forEach.call(nodes, function (node, i) { node.classList.toggle("is-current", i === n); });
      if (scroll && nodes[n]) nodes[n].scrollIntoView({ block: "nearest" });
      tell(shown[n] || null);
    }

    function tell(item) {
      foot.textContent = "";
      var act = link ? "Click to place it, joined to " + ((indexItem(link.from) || {}).name || link.from) + " by a line."
        : finds ? "Enter places it; the arrow keys move through what was found."
        : item && (item.kind === "kit" || item.kind === "block") ? "Drag it into an account, or click to place it."
        : "Drag it onto the sheet, or click to place it.";
      if (!item) {
        foot.appendChild(el("p", { class: "cv-detail-hint", text: "Point at one to read what it is. " + act }));
        return;
      }
      var shelf = shelfOf(item.shelf);
      var about = item.kind === "part" ? item.src.description
        : item.kind === "kit" ? item.kit.description
        : item.kind === "block" ? item.block.description
        : item.type === "data_assets" ? item.src.description + (item.src.classification ? " " + item.src.classification + "." : "")
        : item.kind === "record" ? item.src.description
        : item.kind === "system" ? (item.src.description || "A system of the estate" + (item.src.status ? ", " + item.src.status.toLowerCase() : "") + ".")
        : item.sub + ". Drawn as a box around what it holds.";
      var more = item.kind === "part" ? [item.product ? "Placed, it is named " + item.product + "." : "",
        kitsSaid(item.src.kits)].filter(Boolean).join(" ")
        : item.kind === "kit" ? "It places " + listed(item.kit.systems.map(function (s) { return lowerFirst(s.name); })) + "."
        : item.kind === "block" ? "It places " + listed(item.block.services.map(function (s) { return lowerFirst(s.name); }))
          + (item.block.lines.length ? ", with " + inWords(item.block.lines.length, "line") + " between them." : ".")
        : item.type === "data_assets" ? dataSaid(item.src)
        : item.type === "actors" ? usesSaid(item.src)
        : item.type === "org_units" ? ownsSaid(item.src)
        : "";
      foot.appendChild(el("span", { class: "cv-ico" }, [lucide(item.icon)]));
      foot.appendChild(el("div", { class: "cv-detail-text" }, [
        el("p", { class: "cv-detail-name" }, [el("b", { text: item.name }),
          finds ? el("span", { class: "cv-detail-where", text: (shelf ? shelf.name : "") + " · " + item.group })
            : el("span", { class: "cv-tag" + (item.tag === "Boundary" ? " is-boundary" : item.tag === "Kit" || item.tag === "Block" ? " is-kit" : ""), text: item.tag })]),
        el("p", { class: "cv-detail-about", text: String(about || "").trim() }),
        el("p", { class: "cv-detail-more", text: (more ? more + " " : "") + act }),
      ]));
    }

    search.addEventListener("input", function () {
      if (!search.value.trim()) at.found = "everything";
      render();
      list.scrollTop = 0;
    });
    search.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { e.preventDefault(); closeCanvasPicker(); $("cvAdd").focus(); }
      if (e.key === "ArrowDown" && shown.length) { e.preventDefault(); point(Math.min(current + 1, shown.length - 1), true); }
      if (e.key === "ArrowUp" && shown.length) { e.preventDefault(); point(Math.max(current - 1, 0), true); }
      if (e.key === "Enter") {
        var chosen = shown[current] || shown[0];
        if (chosen) { e.preventDefault(); canvasPlace(chosen, [], null); }
      }
    });
    render();
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
    return { group: hit, into: chain.map(intoOf) };
  }

  // A boundary that is one value of a field, as what is placed in it takes it.
  function intoOf(g) {
    return { field: g.data("field"), value: g.data("stored"),
      label: (PLACE_WORDS[g.data("field")] || fieldWord(g.data("field"))) + " " + g.data("value") };
  }

  /* ---- quick connect, from a record ----
   * An arrow on a record's box asks in Add which record comes next. A part
   * made new goes a step that way in the same boundaries, or where the
   * arrow was carried to; a record of the estate goes where it belongs,
   * since putting it in another boundary would change it. A line joins the
   * two either way and asks whether it is a connection, as a line drawn
   * between two records does. */
  var QUICK_GAP = 60;

  function canvasQuickConnect(from, dir, at) {
    if (!cv || !state.cy) return;
    var n = state.cy.getElementById(from);
    if (!n.length) return;
    var r = $("cy").getBoundingClientRect(), z = state.cy.zoom(), pan = state.cy.pan(), info, m;
    if (at) {
      info = canvasDropInfo({ clientX: at.x, clientY: at.y });
      m = { x: (at.x - r.left - pan.x) / z, y: (at.y - r.top - pan.y) / z };
    } else {
      var p = n.position(), w = n.width(), h = n.height();
      m = { x: p.x + (dir === "e" ? w + QUICK_GAP : dir === "w" ? -(w + QUICK_GAP) : 0),
        y: p.y + (dir === "s" ? h + QUICK_GAP : dir === "n" ? -(h + QUICK_GAP) : 0) };
      var chain = n.ancestors().filter(function (g) { return !!g.data("field"); })
        .sort(function (a, b) { return (a.data("depth") || 0) - (b.data("depth") || 0); });
      info = { group: chain.length ? chain[chain.length - 1] : null, into: chain.map(intoOf) };
    }
    openCanvasPicker("all", false, { from: from, into: info.into, at: { x: r.left + m.x * z + pan.x,
      y: r.top + m.y * z + pan.y, group: info.group ? info.group.id() : null, mx: m.x, my: m.y } });
  }

  // The line quick connect draws, asking whether it is a connection. A
  // record just placed is drawn on the canvas a moment after Cytoscape lays
  // it out, and a line to a box not yet drawn had no end to hold.
  function joinQuick(from, to, tries, mine) {
    mine = mine || cv;
    if (!cv || cv !== mine || from === to || !Canvas.engine || !Canvas.engine.live()) return;
    var drawn = Canvas.engine.boxes() || {};
    if (!drawn[from] || !drawn[to]) {
      if ((tries || 0) < 60) setTimeout(function () { joinQuick(from, to, (tries || 0) + 1, mine); }, 50);
      return;
    }
    var key = Canvas.engine.add({ role: "line", from: from, to: to });
    if (key) canvasOwnDrawn(key, "line");
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
    var boxy = cvDrag.kind !== "view" && cvDrag.kind !== "account" && cvDrag.kind !== "zone";
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
    var boxy = item.kind !== "view" && item.kind !== "account" && item.kind !== "zone";
    var info = boxy ? canvasDropInfo(e) : { into: [], group: null };
    clearCanvasDrop();
    var r = $("cy").getBoundingClientRect(), z = state.cy ? state.cy.zoom() : 1, pan = state.cy ? state.cy.pan() : { x: 0, y: 0 };
    canvasPlace(item, info.into, { x: e.clientX, y: e.clientY, group: info.group ? info.group.id() : null,
      mx: (e.clientX - r.left - pan.x) / z, my: (e.clientY - r.top - pan.y) / z });
  }

  /* ---- a kit, placed whole (V17) ----
   * The owner placed "AI assistant" and got one box. Dropped into an
   * account, a kit asks what it needs and says what it makes there before
   * anything is written: its name, the account (the one it was dropped
   * in), who owns it, what its parameters ask, and each system with the
   * landing zone's services it runs on, from the server's real expansion
   * (`/api/canvas/kit`). Place writes one product through Assemble's own
   * create and pins the systems it made; Just one box is the part of the
   * same name, as Add placed it before. */

  function counted(n, word) { return n + " " + word + (n === 1 ? "" : "s"); }

  var COUNT_WORDS = ["No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve"];

  function countedWord(n, word) {
    return (COUNT_WORDS[n] || String(n)) + " " + word + (n === 1 ? "" : "s");
  }

  // "A, B and C".
  function listed(items) {
    return items.length < 2 ? items.join("") : items.slice(0, -1).join(", ") + " and " + items[items.length - 1];
  }

  // A part as Add lists it with nothing searched: Just one box places it.
  function partItem(x) {
    return { kind: "part", id: x.id, name: x.name, part: x.name, products: x.products || {}, product: "", cloud: "",
      sub: "Part · " + x.typeLabel, tag: "Box", icon: "i-box", typeLabel: x.typeLabel, type: x.type };
  }

  function closeKitPanel() {
    var box = $("cvKit"), mark = $("cvKitMark");
    if (box) { box.hidden = true; box.textContent = ""; }
    if (mark) mark.hidden = true;
    if (cv) cv.kit = null;
  }

  function openKitPanel(item, into, at) {
    if (!cv) return;
    closeContextMenu();
    closeKitPanel();
    var mine = cv, box = $("cvKit"), mark = $("cvKitMark"), k = item.kit;
    var ask = { kit: k.id, into: into || [], name: k.name, "with": {} };
    var res = null, busy = false, timer = null, built = false, seq = 0;
    var same = (cv.parts.parts || []).filter(function (x) { return x.name.toLowerCase() === k.name.toLowerCase(); })[0];
    cv.kit = ask;
    // Where it was dropped, marked while it is asked.
    if (at && mark) {
      mark.textContent = "";
      mark.appendChild(svgIcon("i-blocks"));
      mark.appendChild(el("b", { text: k.name }));
      mark.appendChild(el("span", { text: "Kit · " + counted(k.systems.length, "system") }));
      var r = box.parentNode.getBoundingClientRect();
      mark.style.left = Math.max(8, at.x - r.left - 14) + "px";
      mark.style.top = Math.max(8, at.y - r.top - 16) + "px";
      mark.hidden = false;
    }
    box.textContent = "";
    box.hidden = false;
    box.onkeydown = function (e) {
      if (e.key === "Escape" && e.target.type !== "search") { e.preventDefault(); closeKitPanel(); }
    };
    var sub = el("p", { class: "cv-kit-sub" });
    var name = el("input", { type: "text", class: "cv-kit-input", "aria-label": "Name" });
    var nameHint = el("p", { class: "cv-kit-hint" });
    var lands = el("select", { class: "cv-kit-input", "aria-label": "Lands in" });
    var landsHint = el("p", { class: "cv-kit-hint" });
    var owner = el("select", { class: "cv-kit-input", "aria-label": "Owned by" });
    var ownerHint = el("p", { class: "cv-kit-hint" });
    // The owner the estate offers, with its reason, said in a line; the
    // choice opens on Change, or when there is none to offer.
    var ownerSaid = el("p", { class: "cv-kit-hint cv-kit-owned", hidden: "hidden" });
    var ownerBox = el("div", { class: "cv-kit-owner" });
    var asks = el("div", { class: "cv-kit-asks" });
    var makes = el("div", { class: "cv-kit-makes" });
    var waits = el("p", { class: "cv-kit-waits", hidden: "hidden" });
    var placeBtn = el("button", { type: "button", class: "btn primary", onclick: place });
    var acts = el("div", { class: "cv-kit-acts" }, [placeBtn]);
    if (same) {
      acts.appendChild(el("button", { type: "button", class: "btn", text: "Just one box", onclick: function () {
        closeKitPanel();
        askPartName(partItem(same), into || [], at);
      } }));
    }
    box.appendChild(el("div", { class: "cv-kit-head" }, [svgIcon("i-blocks"),
      el("h2", { text: "Place the " + k.name + " kit" }),
      el("button", { type: "button", class: "cv-kit-x", "aria-label": "Close", onclick: closeKitPanel }, [svgIcon("i-x")])]));
    box.appendChild(sub);
    var body = el("div", { class: "cv-kit-body" });
    box.appendChild(body);
    body.appendChild(el("label", { class: "cv-kit-label", text: "Name" }));
    body.appendChild(name);
    body.appendChild(nameHint);
    body.appendChild(el("label", { class: "cv-kit-label", text: "Lands in" }));
    body.appendChild(lands);
    body.appendChild(landsHint);
    body.appendChild(ownerSaid);
    ownerBox.appendChild(el("label", { class: "cv-kit-label", text: "Owned by" }));
    ownerBox.appendChild(owner);
    ownerBox.appendChild(ownerHint);
    body.appendChild(ownerBox);
    body.appendChild(asks);
    body.appendChild(makes);
    box.appendChild(waits);
    box.appendChild(acts);
    name.value = k.name;
    name.addEventListener("input", function () {
      ask.name = name.value.trim();
      clearTimeout(timer);
      timer = setTimeout(load, 250);
    });
    name.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); place(); }
    });
    lands.addEventListener("change", function () {
      ask.lands = lands.value;
      // Who owns it follows where it lands until the person says.
      if (!ask.ownerSaid) delete ask.owner;
      load();
    });
    owner.addEventListener("change", function () {
      ask.owner = owner.value;
      ask.ownerSaid = true;
      load();
    });
    name.focus();
    name.select();
    makes.appendChild(el("p", { class: "cv-kit-none", text: "Reading what it makes…" }));
    placeBtn.textContent = "Place " + counted(k.systems.length, "system");
    placeBtn.disabled = true;
    load();

    function load() {
      var body = { kit: ask.kit, into: ask.into, name: ask.name, lands: ask.lands || "", "with": ask["with"] };
      if ("owner" in ask) body.owner = ask.owner;
      // Only the answer to the last question asked: a name typed fast
      // asks several times.
      var n = ++seq;
      return api("/api/canvas/kit", body).then(function (got) {
        if (cv !== mine || cv.kit !== ask || n !== seq) return;
        res = got;
        if (!ask.lands && got.lands) ask.lands = got.lands;
        if (!built) buildAsks(got.asks);
        built = true;
        draw();
      }).catch(function (err) {
        if (cv !== mine || cv.kit !== ask || n !== seq) return;
        res = null;
        makes.textContent = "";
        makes.appendChild(el("p", { class: "cv-kit-none", text: err.message }));
        placeBtn.disabled = true;
      });
    }

    function systemName(id) {
      var s = (cv.parts.systems || []).filter(function (x) { return x.id === id; })[0];
      return s ? s.name : id;
    }

    /* What the kit's parameters ask, built once so typing keeps its place:
     * the estate's systems as chips with a way to add one, or a box for a
     * name. */
    function buildAsks(list) {
      asks.textContent = "";
      (list || []).forEach(function (a) {
        asks.appendChild(el("label", { class: "cv-kit-label", text: a.ask }));
        if (!a.names) {
          var input = el("input", { type: "text", class: "cv-kit-input", "aria-label": a.ask });
          input.value = a.value == null ? "" : String(a.value);
          input.addEventListener("input", function () {
            ask["with"][a.name] = input.value.trim();
            clearTimeout(timer);
            timer = setTimeout(load, 250);
          });
          asks.appendChild(input);
        } else {
          var chips = el("div", { class: "cv-kit-chips" });
          var finder = el("div", { class: "cv-kit-find", hidden: "hidden" });
          var chosen = function () {
            var v = a.name in ask["with"] ? ask["with"][a.name] : a.value;
            return Array.isArray(v) ? v.slice() : v ? [v] : [];
          };
          var set = function (ids) {
            ask["with"][a.name] = a.list ? ids : (ids[0] || "");
            chipsOf();
            load();
          };
          var chipsOf = function () {
            chips.textContent = "";
            var ids = chosen();
            ids.forEach(function (id) {
              chips.appendChild(el("span", { class: "cv-kit-chip" }, [el("span", { text: systemName(id) }),
                el("button", { type: "button", "aria-label": "Take out " + systemName(id), onclick: function () {
                  set(chosen().filter(function (x) { return x !== id; }));
                } }, [svgIcon("i-x")])]));
            });
            if (a.list || !ids.length) {
              chips.appendChild(el("button", { type: "button", class: "cv-kit-add", onclick: function () {
                finder.hidden = !finder.hidden;
                if (!finder.hidden) findIn("");
              } }, [svgIcon("i-plus"), el("span", { text: "Add" })]));
            }
          };
          var search = el("input", { type: "search", class: "cv-kit-input", "aria-label": "Find a system for " + a.ask,
            placeholder: "Find a system…" });
          var found = el("div", { class: "cv-kit-found" });
          var findIn = function (q) {
            found.textContent = "";
            var have = chosen();
            (cv.parts.systems || []).filter(function (s) {
              return have.indexOf(s.id) === -1 && (!q || (s.name + " " + s.id).toLowerCase().indexOf(q) !== -1);
            }).slice(0, 6).forEach(function (s) {
              found.appendChild(el("button", { type: "button", class: "cv-kit-pick", onclick: function () {
                finder.hidden = true;
                search.value = "";
                set(a.list ? chosen().concat([s.id]) : [s.id]);
              } }, [el("b", { text: s.name }), el("span", { text: s.domain || s.id })]));
            });
            if (!found.children.length) found.appendChild(el("p", { class: "cv-kit-none", text: "No other system is called that." }));
          };
          search.addEventListener("input", function () { findIn(search.value.trim().toLowerCase()); });
          search.addEventListener("keydown", function (e) {
            if (e.key === "Escape") { e.preventDefault(); finder.hidden = true; }
            if (e.key === "Enter") { var first = found.querySelector(".cv-kit-pick"); if (first) { e.preventDefault(); first.click(); } }
          });
          finder.appendChild(search);
          finder.appendChild(found);
          chipsOf();
          asks.appendChild(chips);
          asks.appendChild(finder);
        }
        if (a.hint) asks.appendChild(el("p", { class: "cv-kit-hint", text: a.hint }));
      });
    }

    function options(select, list, value, none) {
      var want = (none && !value ? [{ value: "", label: none }] : []).concat(list);
      var key = want.map(function (o) { return o.value; }).join("\n");
      if (select.dataset.key !== key) {
        select.textContent = "";
        want.forEach(function (o) { select.appendChild(el("option", { value: o.value, text: o.label })); });
        select.dataset.key = key;
      }
      select.value = value || "";
    }

    function draw() {
      if (!res) return;
      var land = (res.landsOptions || []).filter(function (l) { return l.value === res.lands; })[0];
      var n = res.makes.length ? res.makes.reduce(function (t, g) { return t + g.systems.length; }, 0) : k.systems.length;
      sub.textContent = land
        ? countedWord(n, "system") + " on the " + land.provider + " landing zone of " + land.account
          + (res.dropped ? ", where you dropped it" : "") + ". They land in its subnets by zone."
        : countedWord(n, "system") + " on the landing zone of the account it lands in: choose one below.";
      nameHint.textContent = "Saved as one product, " + res.id + ", made from the kit."
        + (res.taken ? " " + res.taken + " is taken." : "");
      options(lands, (res.landsOptions || []).map(function (l) { return { value: l.value, label: l.label }; }),
        res.lands, "Choose an account");
      landsHint.textContent = !land ? "Its systems land in that account's subnets by zone."
        : res.dropped ? "The account you dropped it in" + (res.domain ? ", in the " + res.domain + " domain." : ".")
        : "Its systems land in this account's subnets by zone." + (res.domain ? " Its records are in the " + res.domain + " domain." : "");
      options(owner, (res.owners || []).map(function (o) { return { value: o.id, label: o.name }; }),
        res.owner, "Choose who owns it");
      ownerHint.textContent = res.owner && res.owner === res.suggested && res.ownerWhy ? res.ownerWhy
        : "The org unit that answers for it, and for every system it makes.";
      var folded = !ask.ownerOpen && res.owner && res.owner === res.suggested && res.ownerWhy;
      var who = (res.owners || []).filter(function (o) { return o.id === res.owner; })[0];
      ownerBox.hidden = !!folded;
      ownerSaid.hidden = !folded;
      ownerSaid.textContent = "";
      if (folded) {
        ownerSaid.appendChild(el("span", { text: "Owned by " + (who ? who.name : res.owner) + ", "
          + res.ownerWhy.charAt(0).toLowerCase() + res.ownerWhy.slice(1) + " " }));
        ownerSaid.appendChild(el("button", { type: "button", class: "cv-link", text: "Change", onclick: function () {
          ask.ownerOpen = true;
          draw();
          owner.focus();
        } }));
      }
      makes.textContent = "";
      makes.appendChild(el("p", { class: "cv-kit-makes-h", text: "What it makes here" }));
      if (!land) {
        makes.appendChild(el("p", { class: "cv-kit-none", text: "Choose where it lands to see what each system runs on there." }));
      }
      res.makes.forEach(function (g) {
        var head = g.placed ? "In the " + g.words + " subnets"
          : g.zone ? (g.none ? "In the " + g.words + " zone, which " + land.account + " has no subnet for" : "Outside the subnets")
          : "In no network zone";
        if (g.shared && g.shared.length) head += ", on " + listed(g.shared);
        makes.appendChild(el("p", { class: "cv-kit-zone", text: head }));
        g.systems.forEach(function (s) {
          var adds = (s.adds || []).map(function (u) { return (u.own ? "its own " : "") + u.name; });
          makes.appendChild(el("p", { class: "cv-kit-made" }, [el("b", { text: s.part }),
            el("span", { text: adds.length ? listed(adds) : "" })]));
        });
      });
      waits.hidden = !res.missing.length;
      waits.textContent = res.missing.length ? "Place waits for " + listed(res.missing) + "." : "";
      placeBtn.textContent = "Place " + counted(n, "system");
      placeBtn.disabled = busy || !res.assembly;
    }

    function place() {
      if (!res || !res.assembly || busy || cv !== mine) return;
      busy = true;
      draw();
      var made = res, systems = [];
      made.makes.forEach(function (g) { g.systems.forEach(function (s) { systems.push(s.id); }); });
      var land = (made.landsOptions || []).filter(function (l) { return l.value === made.lands; })[0];
      setCanvasStatus("saving");
      api("/api/assemble/create", made.assembly).then(function (out) {
        if (cv !== mine) return null;
        closeKitPanel();
        var ids = systems.filter(function (id) { return (out.generated || []).indexOf(id) !== -1; });
        ids.forEach(function (id) {
          cv.made[id] = made.kitName;
          if (pinsOf().indexOf(id) === -1) pinsOf().push(id);
        });
        cv.focus = ids.length ? { id: ids[0] } : null;
        return loadIndex().then(canvasSave).then(canvasDraw).then(function () {
          if (ids.length) canvasSelect({ kind: "record", id: ids[0] });
          toast("ok", "Placed " + made.name, counted(ids.length, "system") + " and their lines"
            + (land ? ", in " + land.account : "") + ". Saved in " + out.path + ".");
        });
      }).catch(function (err) {
        busy = false;
        if (cv !== mine) return;
        setCanvasStatus("failed", err.message);
        if (cv.kit === ask) { waits.hidden = false; waits.textContent = err.message; draw(); }
      });
    }
  }

  /* A building block dropped (V19): its name, where it lands and who owns
   * it, and what it makes there, each service with the cloud's product, in
   * the order its lines run. Place writes them with their lines, given the
   * account's fields and the owner, and pins them; the Library's Add a block
   * wrote the same records with no account, which left them in no box. */
  function openBlockPanel(item, into, at) {
    if (!cv) return;
    closeContextMenu();
    closeKitPanel();
    var mine = cv, box = $("cvKit"), mark = $("cvKitMark"), b = item.block;
    var ask = { block: b.id, into: into || [], name: b.name };
    var res = null, busy = false, timer = null, seq = 0;
    cv.kit = ask;
    if (at && mark) {
      mark.textContent = "";
      mark.appendChild(lucide("layers"));
      mark.appendChild(el("b", { text: b.name }));
      mark.appendChild(el("span", { text: "Block \u00b7 " + counted(b.services.length, "service") }));
      var r = box.parentNode.getBoundingClientRect();
      mark.style.left = Math.max(8, at.x - r.left - 14) + "px";
      mark.style.top = Math.max(8, at.y - r.top - 16) + "px";
      mark.hidden = false;
    }
    box.textContent = "";
    box.hidden = false;
    box.onkeydown = function (e) {
      if (e.key === "Escape") { e.preventDefault(); closeKitPanel(); }
    };
    var sub = el("p", { class: "cv-kit-sub" });
    var name = el("input", { type: "text", class: "cv-kit-input", "aria-label": "Name" });
    var nameHint = el("p", { class: "cv-kit-hint" });
    var lands = el("select", { class: "cv-kit-input", "aria-label": "Lands in" });
    var landsHint = el("p", { class: "cv-kit-hint" });
    var owner = el("select", { class: "cv-kit-input", "aria-label": "Owned by" });
    var ownerHint = el("p", { class: "cv-kit-hint" });
    var makes = el("div", { class: "cv-kit-makes" });
    var waits = el("p", { class: "cv-kit-waits", hidden: "hidden" });
    var placeBtn = el("button", { type: "button", class: "btn primary", onclick: place });
    box.appendChild(el("div", { class: "cv-kit-head" }, [lucide("layers"),
      el("h2", { text: "Place the " + b.name + " block" }),
      el("button", { type: "button", class: "cv-kit-x", "aria-label": "Close", onclick: closeKitPanel }, [svgIcon("i-x")])]));
    box.appendChild(sub);
    var body = el("div", { class: "cv-kit-body" });
    box.appendChild(body);
    [["Name", name, nameHint], ["Lands in", lands, landsHint], ["Owned by", owner, ownerHint]].forEach(function (f) {
      body.appendChild(el("label", { class: "cv-kit-label", text: f[0] }));
      body.appendChild(f[1]);
      body.appendChild(f[2]);
    });
    body.appendChild(makes);
    box.appendChild(waits);
    box.appendChild(el("div", { class: "cv-kit-acts" }, [placeBtn,
      el("button", { type: "button", class: "btn", text: "Cancel", onclick: closeKitPanel })]));
    name.value = b.name;
    name.addEventListener("input", function () {
      ask.name = name.value.trim();
      clearTimeout(timer);
      timer = setTimeout(load, 250);
    });
    name.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); place(); }
    });
    lands.addEventListener("change", function () {
      ask.lands = lands.value;
      if (!ask.ownerSaid) delete ask.owner;
      load();
    });
    owner.addEventListener("change", function () {
      ask.owner = owner.value;
      ask.ownerSaid = true;
      load();
    });
    name.focus();
    name.select();
    makes.appendChild(el("p", { class: "cv-kit-none", text: "Reading what it makes\u2026" }));
    placeBtn.textContent = "Place " + counted(b.services.length, "service");
    placeBtn.disabled = true;
    load();

    function asked() {
      var said = { block: ask.block, into: ask.into, name: ask.name, lands: ask.lands || "" };
      if ("owner" in ask) said.owner = ask.owner;
      return said;
    }

    function load() {
      // Only the answer to the last question asked: a name typed fast asks
      // several times.
      var n = ++seq;
      return api("/api/canvas/block", asked()).then(function (got) {
        if (cv !== mine || cv.kit !== ask || n !== seq) return;
        res = got;
        if (!ask.lands && got.lands) ask.lands = got.lands;
        draw();
      }).catch(function (err) {
        if (cv !== mine || cv.kit !== ask || n !== seq) return;
        res = null;
        makes.textContent = "";
        makes.appendChild(el("p", { class: "cv-kit-none", text: err.message }));
        placeBtn.disabled = true;
      });
    }

    function options(select, list, value, none) {
      var want = (none && !value ? [{ value: "", label: none }] : []).concat(list);
      var key = want.map(function (o) { return o.value; }).join("\n");
      if (select.dataset.key !== key) {
        select.textContent = "";
        want.forEach(function (o) { select.appendChild(el("option", { value: o.value, text: o.label })); });
        select.dataset.key = key;
      }
      select.value = value || "";
    }

    function draw() {
      if (!res) return;
      var land = (res.landsOptions || []).filter(function (l) { return l.value === res.lands; })[0];
      var n = res.makes.length, many = inWords(n, "cloud service");
      many = many.charAt(0).toUpperCase() + many.slice(1);
      sub.textContent = land
        ? many + " on " + land.provider + " in " + land.account + ", " + land.region
          + (res.dropped ? ", where you dropped it" : "") + (res.chain ? ", each joined to the next in the order below." : ".")
        : many + " in the account it lands in: choose one below.";
      var first = res.makes[0], last = res.makes[n - 1];
      nameHint.textContent = (n > 1 ? "Each is named for it: " + first.name + ", " + last.name + "." : "")
        + (res.clashes.length ? " The estate has " + listed(res.clashes) + " already." : "");
      options(lands, (res.landsOptions || []).map(function (l) { return { value: l.value, label: l.label }; }),
        res.lands, "Choose an account");
      landsHint.textContent = !land ? "Its services land in that account, each as that cloud's product."
        : res.dropped ? "The account you dropped it in." : "Its services land in this account.";
      options(owner, (res.owners || []).map(function (o) { return { value: o.id, label: o.name }; }),
        res.owner, "Choose who owns it");
      ownerHint.textContent = res.owner && res.owner === res.suggested && res.ownerWhy ? res.ownerWhy
        : "The org unit that answers for its services.";
      makes.textContent = "";
      makes.appendChild(el("p", { class: "cv-kit-makes-h", text: land ? "What it makes here" : "What it makes" }));
      res.makes.forEach(function (m) {
        makes.appendChild(el("p", { class: "cv-kit-made" }, [el("b", { text: m.kind }), el("span", { text: m.product })]));
      });
      if (res.lines.length) {
        makes.appendChild(el("p", { class: "cv-kit-hint", text: res.chain
          ? "Joined by " + inWords(res.lines.length, "line") + ", each service to the next."
          : "With " + inWords(res.lines.length, "line") + ": " + res.lines.map(function (l) {
            return lowerFirst(l[0]) + " to " + lowerFirst(l[1]);
          }).join(", ") + "." }));
      }
      var waiting = (res.missing.length ? ["Place waits for " + listed(res.missing) + "."] : [])
        .concat(res.clashes.length ? ["The estate has " + listed(res.clashes) + " already: give it another name."] : []);
      waits.hidden = !waiting.length;
      waits.textContent = waiting.join(" ");
      placeBtn.textContent = "Place " + counted(n, "service");
      placeBtn.disabled = busy || !!res.missing.length || !!res.clashes.length;
    }

    function place() {
      if (!res || busy || res.missing.length || res.clashes.length || cv !== mine) return;
      busy = true;
      draw();
      var land = (res.landsOptions || []).filter(function (l) { return l.value === res.lands; })[0];
      setCanvasStatus("saving");
      api("/api/canvas/block", Object.assign(asked(), { place: true })).then(function (out) {
        if (cv !== mine) return null;
        closeKitPanel();
        out.placed.forEach(function (id) {
          cv.made[id] = b.name;
          if (pinsOf().indexOf(id) === -1) pinsOf().push(id);
        });
        addLines("tech_services");
        cv.focus = out.placed.length ? { id: out.placed[0] } : null;
        var folder = (out.paths[0] || "").replace(/[^/]*$/, "");
        return loadIndex().then(canvasSave).then(canvasDraw).then(function () {
          if (out.placed.length) canvasSelect({ kind: "record", id: out.placed[0] });
          toast("ok", "Placed " + out.name, counted(out.placed.length, "cloud service") + " and their lines"
            + (land ? ", in " + land.account : "") + ". Saved in " + folder + ".");
        });
      }).catch(function (err) {
        busy = false;
        if (cv !== mine) return;
        setCanvasStatus("failed", err.message);
        // Drawn first: draw says what Place waits for, and would wipe why it
        // failed.
        if (cv.kit === ask) { draw(); waits.hidden = false; waits.textContent = err.message; }
      });
    }
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
        canvasPlace({ kind: "system", id: found.id, name: found.name, link: item.link }, into, at);
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
    // Chosen after a quick connect arrow: joined to the record it was on.
    var link = item.link || ((item.kind === "part" || item.kind === "system" || item.kind === "record") && cv.connect) || null;
    closeCanvasPicker();
    if (item.kind === "kit") {
      openKitPanel(item, into || [], at);
      return;
    }
    if (item.kind === "block") {
      openBlockPanel(item, into || [], at);
      return;
    }
    var mine = cv;
    if (link && !item.link) {
      item = Object.assign({}, item, { link: link });
      if (!(into && into.length) && !at) {
        into = link.into;
        at = item.kind === "part" ? link.at : null;
      }
    }
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
          if (link) joinQuick(link.from, res.id);
          var where = saidInto(into || []);
          toast("ok", "Placed " + res.name, (where ? "In " + where + ". " : "") + "Saved in " + res.path + ".");
        });
      }).catch(function (err) { if (cv === mine) setCanvasStatus("failed", err.message); });
      return;
    }
    // A system, or a data asset, an actor or a team (V19): pinned, with the
    // lines that join it to what is there.
    if (item.kind === "system" || item.kind === "record") {
      if (pinsOf().indexOf(item.id) !== -1 || drawnHere(item.id)) {
        if (!link) toast("ok", item.name + " is on it already");
        canvasSelect({ kind: "record", id: item.id });
        if (link) joinQuick(link.from, item.id);
        return;
      }
      pinsOf().push(item.id);
      if (item.type) addLines(item.type);
      cv.focus = { id: item.id };
      if (at && at.group) canvasDropAt(item.id, at.group, { x: at.mx, y: at.my });
      canvasSave().then(canvasDraw).then(function () {
        canvasSelect({ kind: "record", id: item.id });
        if (link) joinQuick(link.from, item.id);
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
  // The engine measures the diagram's own as the canvas measures records.
  Canvas.evenGap = evenGap;
  Canvas.measureGaps = measureGaps;
  Canvas.quickConnect = canvasQuickConnect;
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
  Canvas.toggleLayers = toggleLayers;
  Canvas.switchPage = switchPage;
  // A record's name now, for a lane that stands for it.
  Canvas.recordName = function (id) { var it = indexItem(id); return it ? it.name || "" : ""; };
  Canvas.goIn = canvasGoIn;
  Canvas.groupKeyFor = groupKeyFor;
  Canvas.toggleSnap = toggleSnap;
  Canvas.toggleJumps = toggleJumps;
  Canvas.toggleKeys = toggleKeys;
  Canvas.copy = canvasCopy;
  Canvas.paste = canvasPaste;
  Canvas.paletteActions = canvasPaletteActions;
  Canvas.pickedIds = canvasPickedIds;
  Canvas.recordsMoved = canvasRecordsMoved;
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
