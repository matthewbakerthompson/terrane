/* Architecture model app.
 *
 * Plain browser JS, no build step. The server owns the model; this file owns
 * the map, the inspector, and the forms that write back to it.
 */

(function () {
  "use strict";

  if (window.cytoscapeDagre) cytoscape.use(window.cytoscapeDagre);

  var state = {
    shutShelves: {},
    //: What a parameterized view is currently about, by parameter name.
    subject: {},
    overview: null,
    schema: null,
    index: [],
    viewId: null,
    selectedId: null,
    cy: null,
    drawer: null,
    lastGraph: null,
    //: The ids picked to draw together. Kept in this browser until they are
    //: written back as a view or a module.
    sketch: [],
    //: Connection labels: null lets the drawing's density decide, true and
    //: false are the Labels button. Reset when the view changes.
    labels: null,
    labelsShown: true,
    //: The flow being walked on the drawing, or null.
    walk: null,
    //: The tile map's magnification; the canvas keeps its own in Cytoscape.
    tileZoom: 1,
  };

  var $ = function (id) { return document.getElementById(id); };

  function el(tag, attrs, kids) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === "class") node.className = attrs[k];
      else if (k === "text") node.textContent = attrs[k];
      else if (k.slice(0, 2) === "on") node.addEventListener(k.slice(2), attrs[k]);
      else if (attrs[k] !== null && attrs[k] !== undefined) node.setAttribute(k, attrs[k]);
    });
    (kids || []).forEach(function (kid) {
      if (kid) node.appendChild(typeof kid === "string" ? document.createTextNode(kid) : kid);
    });
    return node;
  }

  // ---- tone ---------------------------------------------------------------

  /* Stone or Graphite: the chrome's colors and the drawings' palette at
   * once, chosen in the sidebar's foot and kept per browser. The server
   * styles every drawing in the tone the page asks for, so the swatch beside
   * a layer and the boxes on its diagrams agree in either. A link can name
   * one (`#home&tone=graphite`), which is how a capture asks for the other
   * without touching anybody's setting. Set before anything paints. */
  var TONES = ["stone", "graphite"];
  var TONE_KEY = "terrane.tone";

  function toneFromUrl() {
    var m = /(?:^#|&)tone=([a-z]+)/.exec(window.location.hash || "");
    return m && TONES.indexOf(m[1]) !== -1 ? m[1] : "";
  }

  function storedTone() {
    var t = "";
    try { t = localStorage.getItem(TONE_KEY) || ""; } catch (err) { t = ""; }
    return TONES.indexOf(t) !== -1 ? t : "";
  }

  function tone() { return document.documentElement.getAttribute("data-tone") || TONES[0]; }

  document.documentElement.setAttribute("data-tone", toneFromUrl() || storedTone() || TONES[0]);

  /* What the drawing code paints that the model does not color: the lines,
   * their labels, the selection. Read from the tone's CSS so a Cytoscape
   * style and the page beside it cannot drift apart. */
  var DRAW = {};
  function readDrawColors() {
    var css = window.getComputedStyle(document.documentElement);
    ["edge", "edge-ink", "label-bg", "label-rule", "select", "hl"].forEach(function (name) {
      DRAW[name] = css.getPropertyValue("--draw-" + name).trim();
    });
    DRAW.accent = css.getPropertyValue("--accent").trim();
  }

  // ---- transport --------------------------------------------------------

  function api(path, body) {
    var opts = body
      ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }
      : {};
    // Every request names the tone: what the server draws, it draws in it.
    if (path.indexOf("/api/") === 0) path += (path.indexOf("?") === -1 ? "?" : "&") + "tone=" + tone();
    return fetch(path, opts).then(function (res) {
      return res.json().then(function (data) {
        if (!res.ok) throw new Error(data && data.error ? data.error : "request failed");
        return data;
      });
    });
  }

  function toast(kind, title, detail, action) {
    var node = el("div", { class: "toast " + kind }, [
      el("span", { class: "t", text: title }),
      detail ? el("span", { class: "d", text: detail }) : null,
      action ? el("button", { class: "btn small toast-act", type: "button", text: action.label,
        onclick: function () { node.remove(); action.go(); } }) : null,
    ]);
    $("toasts").appendChild(node);
    setTimeout(function () { node.remove(); }, kind === "err" ? 9000 : action ? 9000 : 4500);
  }

  function fail(err) { toast("err", "That did not work", err.message || String(err)); }

  // ---- title block ------------------------------------------------------

  function fact(term, value, cls) {
    return el("div", { class: "tb-fact" + (cls ? " " + cls : "") }, [
      el("dt", { text: term }),
      el("dd", { text: String(value) }),
    ]);
  }

  function renderFacts(o) {
    var known = (state.schema && state.schema.entities) || null;
    var types = Object.keys(o.counts || {}).filter(function (k) {
      return o.counts[k] > 0 && (!known || known[k]);
    }).length;
    $("facts").textContent = Number(o.entityCount || 0).toLocaleString("en-US") + " "
      + plural(o.entityCount || 0, "record") + (types ? " of " + types + " " + plural(types, "type") : "");
    // Errors only: they are what blocks a merge. Warnings are on the page
    // the button opens, not in red beside the nav.
    var badge = $("checksBadge");
    if (badge) {
      badge.textContent = o.errors ? String(o.errors) : "";
      badge.classList.toggle("is-bad", !!o.errors);
      badge.title = (o.errors || 0) + " " + plural(o.errors || 0, "error") + " \u00b7 "
        + (o.warnings || 0) + " " + plural(o.warnings || 0, "warning");
    }
  }

  //: The shelves, in the order they are shown. The business layer first,
  //: because that is what the estate exists for, and change last.
  var VIEW_CATEGORIES = ["Business", "Application", "Data", "Technology", "Governance", "Change", "Other"];

  /* A view that takes a subject is titled with a placeholder, "{system} —
   * Architecture". The rail says what goes in the hole, "System —
   * Architecture", rather than showing the hole: braces read as a template
   * left unfilled. */
  var SUBJECT_NOUNS = {
    systems: "System", products: "Product", capabilities: "Capability", frameworks: "Framework",
    processes: "Process", work_packages: "Work package", value_streams: "Value stream",
    roadmaps: "Roadmap", controls: "Control", policies: "Policy",
  };

  function viewTitle(v) {
    var title = String(v.title || v.viewId || "");
    // The overview lists a view's parameters by name; a drawn view carries
    // them as records with a type. Either way the name is the noun.
    (v.parameters || []).forEach(function (param) {
      var name = typeof param === "string" ? param : param.name;
      var noun = SUBJECT_NOUNS[param.type] || String(name || "subject").replace(/_/g, " ");
      noun = noun.charAt(0).toUpperCase() + noun.slice(1);
      title = title.split("{" + name + "}").join(noun);
    });
    return title;
  }

  /* One glyph per kind of view, in place of a word: a map is a grid of
   * tiles, a diagram two boxes and a line, a report its rows, a timeline its
   * bars. A view about one thing at a time wears a target, because it is. */
  var KIND_GLYPHS = {
    map: '<rect x="0.75" y="0.75" width="5.5" height="3.5" rx="0.5"/><rect x="7.75" y="0.75" width="5.5" height="3.5" rx="0.5"/>'
      + '<rect x="0.75" y="5.75" width="5.5" height="3.5" rx="0.5"/><rect x="7.75" y="5.75" width="5.5" height="3.5" rx="0.5"/>',
    diagram: '<rect x="0.75" y="2.75" width="4.5" height="4.5" rx="0.5"/><rect x="8.75" y="2.75" width="4.5" height="4.5" rx="0.5"/><path d="M5.25 5h3.5"/>',
    report: '<path d="M0.75 1.5h12.5M0.75 5h12.5M0.75 8.5h12.5"/>',
    timeline: '<path d="M0.75 2h5.5M4 5h7M2.25 8h4.5" stroke-width="2"/>',
    subject: '<circle cx="7" cy="5" r="4"/><circle cx="7" cy="5" r="1.1" fill="currentColor"/>',
  };
  var KIND_WORDS = { map: "map", diagram: "diagram", report: "table", timeline: "timeline" };

  function viewGlyph(kind, perSubject) {
    var span = el("span", { class: "vglyph", "aria-hidden": "true" });
    var key = perSubject ? "subject" : (KIND_GLYPHS[kind] ? kind : "diagram");
    span.innerHTML = '<svg viewBox="0 0 14 10" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round">'
      + KIND_GLYPHS[key] + "</svg>";
    return span;
  }

  function viewButton(v) {
    var shown = viewTitle(v);
    var perSubject = !!(v.parameters && v.parameters.length);
    return el("button", {
      type: "button",
      class: v.ok ? "" : "broken",
      title: v.ok
        ? shown + " \u00b7 " + (KIND_WORDS[v.kind] || "diagram") + (perSubject ? ", for one selected subject" : "")
          + (v.description ? "\n" + v.description : "")
        : v.problem,
      // Current only while it is the drawing on screen: on the Flows or the
      // Checks page the last view drawn is not where the person is.
      "aria-current": v.viewId === state.viewId && (!state.panel || state.panel === "report") ? "true" : "false",
      onclick: function () { peekView(null); selectView(v.viewId); },
      onmouseenter: function (e) { peekView(v, e.currentTarget); },
      onmouseleave: function () { peekView(null); },
    }, [
      viewGlyph(v.kind, perSubject),
      el("span", { class: "vname", text: shown }),
      v.ok ? null : el("span", { class: "vcount", text: "\u2014" }),
    ]);
  }

  function groupViews(views) {
    var byCategory = {};
    (views || []).forEach(function (v) {
      var key = VIEW_CATEGORIES.indexOf(v.category) === -1 ? "Other" : v.category;
      (byCategory[key] = byCategory[key] || []).push(v);
    });
    return VIEW_CATEGORIES
      .filter(function (name) { return byCategory[name]; })
      .map(function (name) { return { name: name, views: byCategory[name] }; });
  }

  /* A layer's views in the sections they say they sit in, in the order
   * they first appear; views that name none share one untitled section. */
  //: The order sections are listed in, within whichever layer has them:
  //: the map before what it is measured against, the landscape before its
  //: detail, plans before their impact. A section not named here follows.
  var SECTION_ORDER = ["Capabilities", "Frameworks", "Processes and value streams", "People and channels",
    "Landscape", "Integration", "Capabilities and processes", "Products and systems", "Lineage and flow",
    "Governance", "Hosting", "Network and resilience", "Plans", "Impact"];

  function sectionsOf(views) {
    var order = [], by = {};
    views.forEach(function (v) {
      var name = v.section || "";
      if (!by[name]) { by[name] = []; order.push(name); }
      by[name].push(v);
    });
    function rank(name) { var i = SECTION_ORDER.indexOf(name); return i === -1 ? SECTION_ORDER.length : i; }
    order.sort(function (a, b) { return rank(a) - rank(b) || a.localeCompare(b); });
    return order.map(function (name) { return { name: name, views: by[name] }; });
  }

  /* The sidebar: every layer, and under the open one its sections, each a
   * submenu of its views. Eighteen titles under Business in one list was a
   * list nobody read. A layer's name opens its page, where the same views
   * are pictures; the chevron opens and closes it without leaving the page.
   * A view is marked current only while it is the drawing on screen. */
  function renderViewList(o) {
    var list = $("viewList");
    list.textContent = "";
    if (!o) return;
    state.openSections = state.openSections || {};
    // A report is drawn as a page, and it is still the view on screen.
    var drawn = !state.panel || state.panel === "report";
    groupViews(o.views).forEach(function (group) {
      var holdsCurrent = drawn && group.views.some(function (v) { return v.viewId === state.viewId; });
      var body = el("div", { class: "shelf-body" });
      var sections = sectionsOf(group.views);
      if (group.views.length > 5 && sections.length > 1) {
        sections.forEach(function (s) {
          var key = group.name + "/" + s.name;
          var here = drawn && s.views.some(function (v) { return v.viewId === state.viewId; });
          var items = el("ul", {});
          s.views.forEach(function (v) { items.appendChild(el("li", {}, [viewButton(v)])); });
          var sub = el("details", { class: "sub-shelf" }, [
            el("summary", {}, [
              el("span", { class: "sub-name", text: s.name || "More" }),
              el("span", { class: "shelf-n mono", text: String(s.views.length) }),
            ]),
            items,
          ]);
          sub.open = here || state.openSections[key] === true;
          sub.addEventListener("toggle", function () { state.openSections[key] = sub.open; });
          body.appendChild(sub);
        });
      } else {
        var items = el("ul", {});
        group.views.forEach(function (v) { items.appendChild(el("li", {}, [viewButton(v)])); });
        body.appendChild(items);
      }
      var onPage = state.panel === "diagrams" && state.homeLayer === group.name;
      var box = el("details", { class: "shelf", style: layerSwatchStyle(group.name) }, [
        el("summary", { class: onPage ? "is-here" : "" }, [
          el("span", { class: "shelf-chev", role: "button", "aria-label": "Show or hide " + group.name + "'s diagrams" }),
          el("span", { class: "shelf-name", text: group.name }),
          el("span", { class: "shelf-n mono", text: String(group.views.length) }),
        ]),
        body,
      ]);
      box.open = holdsCurrent || onPage || state.shutShelves[group.name] === false;
      box.querySelector("summary").addEventListener("click", function (e) {
        e.preventDefault();
        if (e.target.closest(".shelf-chev")) {
          box.open = !box.open;
          state.shutShelves[group.name] = !box.open;
          return;
        }
        state.shutShelves[group.name] = false;
        openDiagrams(group.name);
      });
      list.appendChild(box);
    });
    // Flows last, beside the layers rather than among the pages: a flow is a
    // diagram too, drawn from the same connections. It opens the Flows page.
    if (o.flowCount !== undefined) {
      var flows = el("button", { type: "button", id: "btnFlows", class: "shelf-flows", style: layerSwatchStyle("Flows"),
        title: "Business transactions traced across systems, step by step",
        "aria-current": state.panel === "flows" ? "page" : "false",
        onclick: function () { openFlows(); } }, [
        el("span", { class: "shelf-name", text: "Flows" }),
        el("span", { class: "shelf-n mono", text: String(o.flowCount) }),
      ]);
      list.appendChild(flows);
    }
  }

  // ---- search -----------------------------------------------------------

  function loadIndex() {
    return api("/api/list").then(function (data) {
      state.index = data.items.map(function (item) {
        item.hay = ((item.name || "") + " " + item.id + " " + (item.type || "")).toLowerCase();
        return item;
      });
    });
  }

  /* Where a found thing goes: selected on the drawing when it is on it, and
   * drawn with its neighborhood when it is not. The two search boxes used
   * to land in two different places. */
  function goToEntity(id) {
    if (state.cy && !state.panel && state.cy.getElementById(id).length) {
      showEntity(id);
      return;
    }
    showFocus(id, 1);
  }

  // ---- map --------------------------------------------------------------

  /* Node boxes are sized from the label at 12px Geist 600. The estimate is
   * calibrated rather than measured (Cytoscape cannot size a node to its own
   * text), so the constants are the average glyph width and the line height
   * of that face at that size, plus the padding the box wants around them. */
  var LABEL_WIDTH = 132;
  //: The technology line under a name: its height in the node, and the
  //: average glyph width at its size, for the box to hold it.
  var TECH_H = 11;
  var TECH_CHAR_W = 4.6;
  //: Height a node gives each edge past its third, so a fan has a side to
  //: leave from and the labels on it a stretch to sit on.
  var FAN_PX = 12;
  var CHAR_W = 6.8;
  var LINE_H = 16;
  var PAD_X = 28;
  var PAD_Y = 20;


  /* ---- the technology line ------------------------------------------------
   * What a node runs on, under its name, smaller and quieter: the second
   * line the C4 model asks for. Cytoscape draws one label per node, so the
   * line is painted on a canvas over the drawing, in the document's own
   * font, following every pan, zoom and move and fading with its node.
   */
  var TECH_FONT = 8;
  function attachTechLayer(cy) {
    var host = cy.container();
    if (!host) return;
    if (window.getComputedStyle(host).position === "static") host.style.position = "relative";
    var canvas = document.createElement("canvas");
    canvas.className = "tech-layer";
    canvas.setAttribute("aria-hidden", "true");
    canvas.style.cssText = "position:absolute;left:0;top:0;width:100%;height:100%;pointer-events:none;z-index:4;";
    host.appendChild(canvas);
    var queued = false;
    function paint() {
      queued = false;
      if (cy.destroyed()) return;
      var dpr = window.devicePixelRatio || 1;
      var w = host.clientWidth, h = host.clientHeight;
      if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
        canvas.width = Math.round(w * dpr);
        canvas.height = Math.round(h * dpr);
      }
      var ctx = canvas.getContext("2d");
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      var z = cy.zoom();
      var px = TECH_FONT * z;
      // Below this the line is a smear under a name that is barely a word.
      if (px < 5.5) return;
      ctx.font = "500 " + px + "px Geist, system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "alphabetic";
      cy.nodes("[tech]").forEach(function (n) {
        if (!n.data("tech") || n.data("isGroup") || !n.visible()) return;
        var p = n.renderedPosition();
        ctx.globalAlpha = n.hasClass("dim") ? 0.3 : (n.data("faded") ? 0.55 : 1);
        ctx.fillStyle = "#5b6577";
        var text = fitText(ctx, String(n.data("tech")), n.renderedWidth() - 10 * z);
        ctx.fillText(text, p.x, p.y + n.renderedHeight() / 2 - 5.5 * z);
      });
      ctx.globalAlpha = 1;
    }
    function schedule() {
      if (queued) return;
      queued = true;
      window.requestAnimationFrame(paint);
    }
    cy.on("render", schedule);
    cy.on("destroy", function () { if (canvas.parentNode) canvas.parentNode.removeChild(canvas); });
    schedule();
  }

  function fitText(ctx, text, maxWidth) {
    if (ctx.measureText(text).width <= maxWidth) return text;
    var cut = text;
    while (cut.length > 1 && ctx.measureText(cut + "\u2026").width > maxWidth) cut = cut.slice(0, -1);
    return cut + "\u2026";
  }

  //: An offered interface's box: the same text measure, less padding, so
  //: it reads as a tab on its owner rather than a box beside it.
  var PILL_PAD_X = 20;
  var PILL_PAD_Y = 8;
  //: Its ends' radius: a pill at one line and a protocol.
  var PILL_RADIUS = 14;

  /* A box's size is worked out once per drawing (evenBoxes) and carried on
   * the node; one that has not been through that, a box placed on the
   * canvas a moment ago, is sized from its own name. */
  function labelBox(node) {
    var even = node.data("bw");
    if (even) return { w: even, h: node.data("bh") };
    var box = textBox(node);
    return { w: box.w, h: fanned(box.h, node.data("degree") || 0) };
  }

  /* What the name needs: up to three lines of it, room for the mark or the
   * component glyph in the corner so neither sits on text, and for the
   * technology line under the name when there is one. */
  function textBox(node) {
    if (SHAPES[node.data("entityType")] === "pill") return pillBox(node);
    var text = String(node.data("label") || "");
    var oneLine = text.length * CHAR_W;
    var lines = Math.min(3, Math.max(1, Math.ceil(oneLine / LABEL_WIDTH)));
    var w = lines > 1 ? LABEL_WIDTH : Math.max(64, oneLine);
    if (node.data("icon")) w += 22;
    else if (node.data("glyph") || node.data("ticon")) w += 10;
    var tech = String(node.data("tech") || "");
    if (tech) w = Math.max(w, Math.min(LABEL_WIDTH, tech.length * TECH_CHAR_W));
    var h = lines * LINE_H + PAD_Y + (tech ? TECH_H : 0);
    return { w: Math.round(w + PAD_X), h: Math.round(h) };
  }

  /* Room on a side for a fan of edges, twelve pixels an edge past three:
   * a hub with seven connections is twice the height of a leaf. */
  function fanned(h, degree) {
    return degree > 3 ? Math.max(h, Math.min(degree, 7) * FAN_PX) : h;
  }

  /* An offered interface: its name and its protocol under it, at the
   * sheet's own text sizes, in a box padded less than a system's. The fan
   * rule holds for it too, since six callers meeting at one queue need the
   * room. */
  function pillBox(node) {
    var text = String(node.data("label") || "");
    var oneLine = text.length * CHAR_W;
    var lines = Math.min(3, Math.max(1, Math.ceil(oneLine / LABEL_WIDTH)));
    var w = lines > 1 ? LABEL_WIDTH : Math.max(48, oneLine);
    var tech = String(node.data("tech") || "");
    if (tech) w = Math.max(w, Math.min(LABEL_WIDTH, tech.length * TECH_CHAR_W));
    var h = lines * LINE_H + PILL_PAD_Y + (tech ? TECH_H : 0);
    return { w: Math.round(w + PILL_PAD_X), h: Math.round(h) };
  }

  /* Even boxes: every box of one kind in a drawing is as wide as the widest
   * of them and as tall as the tallest name among them, and only a fan of
   * connections makes one taller. Sized each from its own name, the systems
   * on the context diagram ran from 92 to 182 pixels wide, and a column of
   * fourteen had fourteen left edges. `terrane render` sizes them the same
   * way (terrane/draw/packed.py, `prepare`). */
  function evenBoxes(elements) {
    var wide = {}, tall = {};
    var leaves = elements.filter(function (e) { return !e.data.source && !e.data.isGroup; });
    leaves.forEach(function (e) {
      var key = String(e.data.entityType || "");
      var box = textBox(dataNode(e.data));
      wide[key] = Math.max(wide[key] || 0, box.w);
      tall[key] = Math.max(tall[key] || 0, box.h);
    });
    leaves.forEach(function (e) {
      var key = String(e.data.entityType || "");
      e.data.bw = wide[key];
      e.data.bh = fanned(tall[key], e.data.degree || 0);
    });
  }

  // The node interface the box rules read, over a payload's plain data.
  function dataNode(d) {
    return { data: function (key) { return d[key]; } };
  }

  /* Shape belongs to the entity type, the way hue does. A component type
   * used to override it, which put a capability's hexagon on a tech service
   * and asked the reader to hold two taxonomies on one channel. The
   * component now gets a corner glyph instead. */
  var SHAPES = {
    systems: "round-rectangle",
    products: "round-tag",
    capabilities: "hexagon",
    data_assets: "barrel",
    tech_services: "rhomboid",
    org_units: "rectangle",
    interfaces: "tag",
    /* What a system offers -- an API, a topic, a file drop -- is the one
     * pill: small, beside its owner in the owner's hue, the lines of every
     * caller meeting at it. No corner, so no mark; the shape says it. */
    offered_interfaces: "pill",
    actors: "ellipse",
    flows: "round-tag",
    value_streams: "round-tag",
    value_stream_stages: "round-tag",
    controls: "octagon",
    policies: "cut-rectangle",
    frameworks: "rectangle",
    processes: "pentagon",
    /* The two plan objects are rounded and the decision is not: a diamond is
     * what a decision has looked like since the first flowchart, and a
     * roadmap that looked like one would claim to be a choice rather than a
     * consequence of one. */
    roadmaps: "round-octagon",
    work_packages: "round-diamond",
    architecture_change_requests: "diamond",
  };

  /* One monochrome glyph per component category, drawn in the top-right
   * corner of the node. What kind of infrastructure a box is should be
   * readable without stealing the hue that says what kind of entity it is. */
  var GLYPH_PATHS = {
    Application: "M2 3.5h12v9H2z M2 6.5h12",
    Compute: "M4.5 4.5h7v7h-7z M8 2v2.5 M8 11.5V14 M2 8h2.5 M11.5 8H14",
    Data: "M8 3c3.3 0 5 .9 5 2s-1.7 2-5 2-5-.9-5-2 1.7-2 5-2z M3 5v6c0 1.1 1.7 2 5 2s5-.9 5-2V5",
    Integration: "M2 5.5h9l-2.5-2.5 M14 10.5H5l2.5 2.5",
    Network: "M8 3.5a1.5 1.5 0 1 0 0 .01 M3.5 12.5a1.5 1.5 0 1 0 0 .01 M12.5 12.5a1.5 1.5 0 1 0 0 .01 M8 5v3 M8 8l-4 3.5 M8 8l4 3.5",
    Operations: "M2.5 11a5.5 5.5 0 0 1 11 0 M8 11l2.5-4",
    Security: "M8 2l5 2v4c0 3-2.2 5.2-5 6-2.8-.8-5-3-5-6V4z",
    Storage: "M2 5h12v6H2z M11 8h1",
    /* A spark for a model or the service that serves one; a building for
     * the enterprise applications an organization runs rather than builds. */
    AI: "M8 2.5l1.4 3.6L13 7.5l-3.6 1.4L8 12.5 6.6 8.9 3 7.5l3.6-1.4z M12.5 2v2 M11.5 3h2",
    Enterprise: "M3 13.5V4.5l5-2 5 2v9 M6 7h1 M9 7h1 M6 9.5h1 M9 9.5h1 M7 13.5v-2h2v2",
  };
  var GLYPHS = {};
  Object.keys(GLYPH_PATHS).forEach(function (name) {
    var svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16">'
      + '<path d="' + GLYPH_PATHS[name] + '" fill="none" stroke="#3f4a5c" stroke-width="1.5" '
      + 'stroke-linecap="round" stroke-linejoin="round"/></svg>';
    GLYPHS[name] = "data:image/svg+xml;utf8," + encodeURIComponent(svg);
  });

  /* The type's own mark, for the corner of a node that has no provider mark
   * and no component glyph: a reader should know what kind of thing a box
   * is without the legend. Drawn in the node's own stroke color, on the
   * shapes with a corner to put it in; a hexagon or an octagon says its
   * type by being one. The marks are Lucide's (ISC), the same set the
   * sidebar uses. */
  var TYPE_ICON_BODIES = {
    systems: '<rect width="18" height="18" x="3" y="3" rx="2"/>',
    products: '<path d="M11 21.73a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73z"/><path d="M12 22V12"/><polyline points="3.29 7 12 12 20.71 7"/><path d="m7.5 4.27 9 5.15"/>',
    interfaces: '<path d="m16 3 4 4-4 4"/><path d="M20 7H4"/><path d="m8 21-4-4 4-4"/><path d="M4 17h16"/>',
    data_assets: '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5V19A9 3 0 0 0 21 19V5"/><path d="M3 12A9 3 0 0 0 21 12"/>',
    tech_services: '<rect width="20" height="8" x="2" y="2" rx="2" ry="2"/><rect width="20" height="8" x="2" y="14" rx="2" ry="2"/><line x1="6" x2="6.01" y1="6" y2="6"/><line x1="6" x2="6.01" y1="18" y2="18"/>',
    org_units: '<path d="M10 12h4"/><path d="M10 8h4"/><path d="M14 21v-3a2 2 0 0 0-4 0v3"/><path d="M6 10H4a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-2"/><path d="M6 21V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v16"/>',
    policies: '<path d="M15 12h-5"/><path d="M15 8h-5"/><path d="M19 17V5a2 2 0 0 0-2-2H4"/><path d="M8 21h12a2 2 0 0 0 2-2v-1a1 1 0 0 0-1-1H11a1 1 0 0 0-1 1v1a2 2 0 1 1-4 0V5a2 2 0 1 0-4 0v2a1 1 0 0 0 1 1h3"/>',
    frameworks: '<path d="M12 5v16"/><path d="M20.001 19A2 2 0 0022 17V5a2 2 0 00-1.999-2L16 3.002A5 5 0 0012 5a5 5 0 00-4-2H4a2 2 0 00-2 2v12a2 2 0 001.999 2H8a5 5 0 014 2 5 5 0 014-2z"/>',
    value_streams: '<circle cx="6" cy="19" r="3"/><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/><circle cx="18" cy="5" r="3"/>',
    value_stream_stages: '<path d="M12 13v8"/><path d="M12 3v3"/><path d="M18.172 6a2 2 0 0 1 1.414.586l2.06 2.06a1.207 1.207 0 0 1 0 1.708l-2.06 2.06a2 2 0 0 1-1.414.586H4a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1z"/>',
    flows: '<circle cx="6" cy="19" r="3"/><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/><circle cx="18" cy="5" r="3"/>',
  };
  var CORNERED = { "round-rectangle": 1, "rectangle": 1, "round-tag": 1, "tag": 1, "cut-rectangle": 1, "barrel": 1 };
  var TYPE_ICON_CACHE = {};
  function typeIcon(type, stroke) {
    var body = TYPE_ICON_BODIES[type];
    if (!body) return null;
    var key = type + "|" + stroke;
    if (!TYPE_ICON_CACHE[key]) {
      TYPE_ICON_CACHE[key] = "data:image/svg+xml;utf8," + encodeURIComponent(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="'
        + stroke + '" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + body + "</svg>");
    }
    return TYPE_ICON_CACHE[key];
  }

  //: Filled from `/api/library` on boot: component type id to its category.
  var COMPONENT_CATEGORY = {};

  // Nested boundaries tint progressively so containment reads as containment.
  // Four percent of lightness per level: enough to see the area, not enough
  // to compete with the nodes sitting in it.
  var BOUNDARY_FILL = ["#f3f5fb", "#e7ebf6", "#dbe1f0", "#cfd7ea"];

  /* The boundary name is 10px Geist Mono: 6.1px an advance. It sits 12px in
   * from the left border. A boundary needs enough inside width that an edge
   * arriving at the center of a lone child, which is the box's center,
   * passes 14px clear of the name's end. The same two numbers feed the
   * stylesheet and the layout, which must agree on how wide a boundary is. */
  var TITLE_CHAR = 6.1;
  function titleWidth(label) { return String(label || "").length * TITLE_CHAR; }
  function titleRoom(label) { return Math.round(2 * titleWidth(label) + 4); }
  /* Geist 600 at 11px, the boundary name's face: each printable glyph's
   * advance as Chrome measures it, from 50_ENGINE/terrane/draw/fonts/metrics.json
   * and held equal to it by a test. Not for sizing anything: the router
   * keeps its runs off the word itself, and the nominal width above runs
   * fourteen pixels long on "subscription azure-platform-prod" and six short
   * on "AWS", so a run past the end of a long name counted as through it and
   * a run through the "d" of "prod" was chosen over it. Advances without
   * the kerning, which leaves "AWS" a pixel and a half wide: wide is the
   * safe side of a box a line keeps out of. A table rather than measureText,
   * which answers in the fallback face until the web font has loaded;
   * anything else counts as an n. */
  var NAME_ADVANCE = {
    " ": 2.6, "!": 2.67, "\"": 4.14, "#": 6.07, "$": 7.22, "%": 9.0, "&": 7.45, "'": 2.15, "(": 3.37, ")": 3.37,
    "*": 4.66, "+": 6.23, ",": 2.48, "-": 4.6, ".": 2.48, "/": 5.59, "0": 7.51, "1": 4.7, "2": 7.06, "3": 7.01,
    "4": 7.07, "5": 7.22, "6": 6.76, "7": 5.92, "8": 7.08, "9": 6.8, ":": 3.37, ";": 3.37, "<": 6.03, "=": 6.03,
    ">": 6.03, "?": 6.39, "@": 10.38, "A": 7.8, "B": 7.64, "C": 7.96, "D": 7.79, "E": 6.76, "F": 6.6, "G": 7.99,
    "H": 7.91, "I": 3.19, "J": 6.79, "K": 7.39, "L": 6.45, "M": 9.92, "N": 8.23, "O": 8.39, "P": 7.3, "Q": 8.33,
    "R": 7.58, "S": 7.35, "T": 6.42, "U": 7.69, "V": 7.8, "W": 10.9, "X": 7.26, "Y": 6.74, "Z": 6.35, "[": 4.12,
    "\\": 5.33, "]": 4.12, "^": 4.95, "_": 6.16, "`": 2.95, "a": 6.38, "b": 6.83, "c": 6.38, "d": 6.83,
    "e": 6.5, "f": 4.72, "g": 6.82, "h": 6.61, "i": 2.96, "j": 3.39, "k": 6.91, "l": 3.27, "m": 9.81, "n": 6.61,
    "o": 6.63, "p": 6.83, "q": 6.83, "r": 4.5, "s": 6.08, "t": 4.7, "u": 6.57, "v": 6.42, "w": 9.23, "x": 6.91,
    "y": 6.27, "z": 6.24, "{": 4.41, "|": 3.12, "}": 4.41, "~": 5.75
  };
  function nameWidth(label) {
    var t = String(label || ""), w = 0;
    for (var i = 0; i < t.length; i++) {
      var ch = t.charAt(i);
      w += NAME_ADVANCE.hasOwnProperty(ch) ? NAME_ADVANCE[ch] : NAME_ADVANCE.n;
    }
    return w;
  }
  /* The word a boundary's name is, in Cytoscape's box for the boundary:
   * centered half its nominal width past twelve in (where the stylesheet's
   * margin puts it), its own width wide, four pixels of air about it; seven
   * down, eleven high. What both routers keep their lines off. */
  function nameWord(bb, label) {
    var mid = bb.x1 + 13 + titleWidth(label) / 2, hw = nameWidth(label) / 2 + 4;
    return [Math.max(bb.x1, mid - hw), bb.y1 + 4, Math.min(bb.x2, mid + hw), Math.min(bb.y2, bb.y1 + 22)];
  }

  /* The stylesheet is rebuilt when the layout family changes: layered layouts
   * get orthogonal edges, routed by routeDrawing(), which is what makes the
   * drawing read as an architecture diagram rather than a force graph;
   * organic layouts keep beziers, where right angles would lie about the
   * geometry. */
  /* The encoding rule, in one place. Hue is the entity type. The view's
   * dimension arrives from the server as a border weight and a tint (ordered
   * data), a border style (status), or nothing (a nominal dimension the
   * boundaries already say). Line style is the kind of relationship. Nothing
   * else carries meaning, so nothing else varies. */
  function graphStyle(layered) {
    if (!DRAW.edge) readDrawColors();
    var edgeBase = {
      "width": 1.6,
      "line-color": DRAW.edge,
      "target-arrow-color": DRAW.edge,
      "target-arrow-shape": "triangle",
      "arrow-scale": 1.1,
      "line-style": "data(lineStyle)",
      "curve-style": layered ? "round-segments" : "bezier",
      /* What is shown is decided by placeEdgeLabels(): the label, on its own
       * line at a spot that overlaps nothing, or nothing until hover. */
      "label": "data(shown)",
      "text-margin-x": "data(lx)",
      "text-margin-y": "data(ly)",
      "font-family": "Geist, system-ui, sans-serif",
      "font-size": 10,
      "font-weight": 500,
      "color": DRAW["edge-ink"],
      /* A label sits in a small white card with a hairline edge, so where
       * it covers its own line, or a line that crosses, it reads as a label
       * on a line rather than as text that happens to be near one. */
      "text-background-color": DRAW["label-bg"],
      "text-background-opacity": 0.96,
      "text-background-padding": 3,
      "text-background-shape": "roundrectangle",
      "text-border-width": 1,
      "text-border-color": DRAW["label-rule"],
      "text-border-opacity": 1,
      /* Edge labels only exist once you are close enough to read them: at
       * a 9.5px face that is a zoom of about 85%. Below it a drawing reads
       * as lines, not as a fog of protocol names. Hover and selection always
       * show them. */
      "min-zoomed-font-size": 8,
    };
    if (layered) {
      /* The points come from routeDrawing(): the grid router's corners
       * round every node and name, or the three pieces where the grid has
       * no way through. */
      edgeBase["segment-weights"] = "data(segw)";
      edgeBase["segment-distances"] = "data(segd)";
      edgeBase["segment-radii"] = 10;
      edgeBase["edge-distances"] = "node-position";
      /* Where the line leaves and arrives: the point on each side ELK
       * routed to, or the node's edge when the drawing was routed here. */
      edgeBase["source-endpoint"] = "data(sep)";
      edgeBase["target-endpoint"] = "data(tep)";
    } else {
      // On a packed or organic layout the edges cross whatever they cross.
      // They are context, not the reading order, so they step back.
      edgeBase["opacity"] = 0.45;
      edgeBase["width"] = 1.3;
    }
    return [
      {
        selector: "node",
        style: {
          "background-color": "data(fill)",
          "border-color": "data(stroke)",
          "border-width": "data(strokeWidth)",
          "border-style": "data(dash)",
          "color": "data(ink)",
          "label": "data(label)",
          "font-family": "Geist, system-ui, sans-serif",
          "font-size": 12,
          "font-weight": 600,
          "text-valign": "center",
          "text-halign": "center",
          /* The name moves up to leave the technology line its room, and
           * left to leave the mark in the corner its room. */
          "text-margin-y": function (n) { return n.data("tech") ? -(TECH_H / 2) : 0; },
          "text-margin-x": function (n) { return n.data("icon") ? -10 : (n.data("glyph") || n.data("ticon")) ? -4 : 0; },
          "text-wrap": "wrap",
          "text-max-width": function (n) { return LABEL_WIDTH - (n.data("icon") ? 20 : (n.data("glyph") || n.data("ticon")) ? 8 : 0); },
          "width": function (n) { return labelBox(n).w; },
          "height": function (n) { return labelBox(n).h; },
          "shape": function (n) {
            var shape = SHAPES[n.data("entityType")] || "round-rectangle";
            return shape === "pill" ? "round-rectangle" : shape;
          },
          /* Below this rendered size a label is a smear, and a smear on a
           * colored box says less than the box alone. Six pixels is the
           * threshold at which Plex Sans still resolves into words. */
          "min-zoomed-font-size": 6,
        },
      },
      { selector: "node[?faded]", style: { "opacity": 0.55 } },
      { selector: "node[entityType = \"offered_interfaces\"]", style: { "corner-radius": PILL_RADIUS } },
      {
        selector: "node[glyph]",
        style: {
          "background-image": "data(glyph)",
          "background-width": 13,
          "background-height": 13,
          "background-position-x": "100%",
          "background-position-y": "0%",
          /* A rhomboid's top-right corner is the tip of its slant, so the
           * glyph there sat half outside the shape. It moves in on those. */
          "background-offset-x": function (n) {
            return SHAPES[n.data("entityType")] === "rhomboid" ? -16 : -5;
          },
          "background-offset-y": 5,
          "background-clip": "none",
          "background-image-opacity": 0.9,
        },
      },
      {
        selector: "node[ticon]",
        style: {
          "background-image": "data(ticon)",
          "background-width": 12,
          "background-height": 12,
          "background-position-x": "100%",
          "background-position-y": "0%",
          "background-offset-x": -6,
          "background-offset-y": 5,
          "background-clip": "none",
          "background-image-opacity": 0.85,
        },
      },
      {
        /* The provider's or vendor's own mark, top right, a little larger
         * than the glyph it replaces: a reader of AWS or Azure diagrams
         * knows it before reading the name. Served from web/icons, whose
         * CREDITS.md says whose each one is. */
        selector: "node[icon]",
        style: {
          "background-image": "data(icon)",
          "background-width": 18,
          "background-height": 18,
          "background-position-x": "100%",
          "background-position-y": "0%",
          "background-offset-x": function (n) {
            return SHAPES[n.data("entityType")] === "rhomboid" ? -16 : -4;
          },
          "background-offset-y": 4,
          "background-clip": "none",
          "background-image-opacity": 1,
        },
      },
      {
        selector: "node[?isGroup]",
        style: {
          /* Drawn the way the provider draws that kind of container, from
           * the server's boundary style: a dashed teal AWS region, a solid
           * blue Azure subscription, a green public subnet. A boundary that
           * is not a cloud container keeps the depth tint. */
          "background-color": function (n) {
            if (n.data("bfill")) return n.data("bfill");
            var d = (n.data("depth") || 1) - 1;
            return BOUNDARY_FILL[Math.min(d, BOUNDARY_FILL.length - 1)];
          },
          "background-opacity": 1,
          "background-image": "none",
          "border-width": function (n) { return n.data("bkey") ? 1.4 : 1; },
          "border-style": function (n) { return n.data("bdash") || "solid"; },
          "border-color": function (n) { return n.data("bstroke") || "#8f9bb5"; },
          "shape": "round-rectangle",
          "label": "data(label)",
          /* The boundary name sits inside its own box, top left, the way a
           * region or subnet is named on a cloud diagram. `top` puts the
           * label above the box; the margin brings it down into the box's
           * own padding, clear of the border and of the first child. At 8 it
           * straddled the border line, which read as a collision. */
          "text-valign": "top",
          "text-halign": "center",
          /* `left` anchors the label outside the box, on whatever sits to
           * the left of it. Centered, then shifted left by half the box
           * less half the text, it sits inside at the top-left corner. */
          "text-margin-x": function (n) {
            /* The outer width: `width()` on a compound is the inside, and
             * measuring from it put the name a padding's worth too far in. */
            return Math.round(-(n.outerWidth() / 2) + titleWidth(n.data("label")) / 2 + 12);
          },
          "text-margin-y": 19,
          /* One line, always. Wrapped at the 132 pixels every node label
           * wraps at, "account prod-riskops" broke in two, and with the
           * margin set for one line the first sat on the border. The box
           * is already at least twice the name's width (`min-width`), so
           * the line has its room. */
          "text-wrap": "none",
          /* A boundary is at least wide enough that an edge arriving at the
           * center of a lone child clears the name in the corner. */
          "min-width": function (n) { return titleRoom(n.data("label")) + (n.data("icon") ? 28 : 0); },
          "font-family": "Geist, system-ui, sans-serif",
          "font-size": 11,
          "font-weight": 600,
          "color": function (n) { return n.data("bink") || "#3b4a6b"; },
          "text-background-opacity": 0,
          "text-border-width": 0,
          "padding": 24,
          "min-zoomed-font-size": 5,
        },
      },
      {
        /* The provider's own mark for the kind of container, top right, the
         * way the AWS and Azure diagram kits draw a cloud, an account, a
         * region or a subnet. The name keeps the top-left corner; the box
         * grows for the mark the way it does for the name. */
        selector: "node[?isGroup][icon]",
        style: {
          "background-image": "data(icon)",
          "background-width": 20,
          "background-height": 20,
          "background-position-x": "100%",
          "background-position-y": "0%",
          "background-offset-x": -7,
          "background-offset-y": 6,
          "background-clip": "none",
          "background-image-opacity": 1,
        },
      },
      { selector: "edge", style: edgeBase },
      /* An offered interface joined to the system offering it: part of the
       * owner, not traffic to it, so no head. */
      { selector: "edge[kind = \"offers\"]", style: { "target-arrow-shape": "none" } },
      // A pair with no side facing the other across a gap: a curve, not a
      // route through one of them.
      { selector: "edge.free", style: { "curve-style": "bezier" } },
      /* A label turned to lie along its line, where placeEdgeLabels() found
       * no room for it upright. The margins still shift it in the sheet's
       * axes; Cytoscape rotates about the shifted point. */
      { selector: "edge.rot", style: { "text-rotation": "autorotate" } },
      /* A hop of the flow being walked: its number before its label, in a
       * warm badge, the way a reference architecture numbers its steps. */
      {
        selector: "edge.step",
        style: {
          "label": "data(stepLabel)",
          "text-rotation": "none",
          "min-zoomed-font-size": 0,
          "font-weight": 700,
          "color": DRAW.select,
          "text-background-color": DRAW["label-bg"],
          "text-border-color": DRAW.accent,
          "text-border-width": 1.2,
          "line-color": DRAW.accent,
          "target-arrow-color": DRAW.accent,
          "width": 2.4,
          "z-index": 12,
        },
      },
      { selector: "node.hover", style: { "border-width": 2.6, "z-index": 10 } },
      {
        selector: "edge.hover, edge.hl",
        style: {
          "line-color": DRAW.hl,
          "target-arrow-color": DRAW.hl,
          "width": 2.2,
          "label": "data(label)",
          "min-zoomed-font-size": 0,
          "z-index": 9,
        },
      },
      { selector: "node.hl", style: { "border-color": DRAW.hl, "z-index": 8 } },
      /* The selected node itself: heavier than its neighborhood, so the
       * subject and the context are two things rather than one. */
      {
        selector: "node.sel",
        style: {
          "border-width": 3.4,
          "border-color": DRAW.select,
          "underlay-color": DRAW.select,
          "underlay-opacity": 0.12,
          "underlay-padding": 5,
          "z-index": 11,
        },
      },
      /* Impact confidence, weakening with distance. */
      { selector: "node.conf-direct", style: { "border-width": 3, "border-color": DRAW.select } },
      { selector: "node.conf-likely", style: { "border-width": 2.2, "border-color": "#334155" } },
      { selector: "node.conf-possible", style: { "border-width": 1.6, "border-color": "#64748b", "opacity": 0.85 } },
      { selector: "node.dim, edge.dim", style: { "opacity": 0.14 } },
      { selector: "node[?isGroup].dim", style: { "opacity": 0.45 } },
    ];
  }

  /* ---- layout ----------------------------------------------------------
   * A layered layout that respects containment. cytoscape-dagre positions
   * leaf nodes and ignores their parents, so a boundary ended up as the
   * bounding box of wherever its children landed: overlapping, stacked,
   * spanning the sheet. This walks the boundaries bottom-up, lays out each
   * one's own children with dagre (or a grid, when nothing inside it is
   * connected), and then treats the finished boundary as one node in its
   * parent's layout. Edges that cross a boundary are drawn between the
   * boundaries at that level, which is what orders them sensibly.
   */

  // `boundaryPad` must equal the compound `padding` in graphStyle, because
  // the layout sizes a boundary from its leaves and Cytoscape draws it from
  // the same leaves plus that padding. The name sits inside the padding.
  var LAYOUT = { nodesep: 26, ranksep: 48, edgesep: 14, gapX: 24, gapY: 20,
                 boundaryPad: 24, boundaryLabel: 0 };

  /* Lay the graph out both ways and keep the direction that fits the sheet
   * at the larger zoom, preferring the view's own direction unless the other
   * is clearly better. Three layouts of sixty nodes cost nothing visible.
   * The two weighed are dagre's own ranking, untucked: weighed tucked, a
   * drawing whose own direction tucking had made merely poor kept it, and
   * six capability alignments came out up to a seventh wider with their
   * capabilities in a row, where they had always turned; and one tucking
   * made better the other way turned, and Dispute Management went from a
   * strip to a square with a band of nothing through it. Tucking takes
   * space out of a drawing; which way it reads is decided as it always was. */
  function bestDirection(cy, preferred) {
    var box = cy.container().getBoundingClientRect();
    function zoomFor(dir) {
      layoutHierarchy(cy, dir, false, false, true);
      var bb = cy.elements().boundingBox();
      return Math.min(box.width / Math.max(bb.w, 1), box.height / Math.max(bb.h, 1));
    }
    var other = preferred === "TB" ? "LR" : "TB";
    var own = zoomFor(preferred);
    var alt = zoomFor(other);
    var dir = alt > own * 1.3 ? other : preferred;
    layoutHierarchy(cy, dir, false, false);
    return dir;
  }

  /* Dagre leaves a hole wherever a column's first ranks are empty: the
   * network topology had the shared-network account under nothing, and a
   * quarter of the AWS box was blank. In rank order, each boundary slides
   * toward the start of the rank axis until it would come within a rank
   * gap of something it overlaps across that axis, so nothing changes its
   * place relative to what is beside or before it, and nothing ever moves
   * the other way. How a level of boundaries was drawn before tucking, and
   * still is where tucking takes no space out. */
  function compactRanks(items, target, vertical, ranksep) {
    function pos(it) { var t = target[it.node.id()]; return vertical ? t.y : t.x; }
    function half(it) { return (vertical ? it.h : it.w) / 2; }
    function span(it) {
      var t = target[it.node.id()];
      return vertical ? [t.x - it.w / 2, t.x + it.w / 2] : [t.y - it.h / 2, t.y + it.h / 2];
    }
    var origin = Infinity;
    items.forEach(function (it) { origin = Math.min(origin, pos(it) - half(it)); });
    var done = [];
    items.slice().sort(function (a, b) { return pos(a) - pos(b); }).forEach(function (it) {
      var s = span(it);
      var floor = origin;
      done.forEach(function (d) {
        if (d.lo < s[1] + 8 && d.hi > s[0] - 8) floor = Math.max(floor, d.end + ranksep);
      });
      var t = target[it.node.id()];
      var moved = Math.min(pos(it), floor + half(it));
      if (vertical) t.y = moved; else t.x = moved;
      done.push({ lo: s[0], hi: s[1], end: moved + half(it) });
    });
  }

  /* Dagre ranks a boundary as one node and centers each rank across the
   * axis, so a level that holds boundaries came out as columns of very
   * different sizes with the space between them blank: Network Topology's
   * shared-network account hung halfway down the AWS box, Risk Ops sat a
   * rank later under Lending because twenty pixels of the shared account
   * were in its way, and the on-premises box stood off the right edge for
   * the sake of a box 230 pixels wide; 2,997 by 1,765 for 33 boxes, the
   * leaves a fourteenth of it. Sliding a boundary along the rank axis
   * alone could not reach any of those holes.
   *
   * Rank by rank: each boundary goes to the earliest place along the rank
   * axis that is clear of what is already placed, inside the breadth the
   * level already has, nearest the start across it; then the rank's leaves
   * move as one row, keeping their places across and their alignment, to
   * the first place clear of what they would sit beside. Leaves stay rows,
   * so the diagram still reads along its ranks: moving them one by one
   * packed Product Architecture tight and put its data
   * stores under Azure with the lines running every way. What an edge
   * leaves a leaf for stays a rank gap after that leaf; what an edge leaves
   * a boundary for may sit beside the boundary, never before its start.
   * `breadth`, when given, narrows the breadth to that share of it, never
   * below the widest boundary (TUCK_BREADTHS says why). */
  function tuckRanks(items, target, vertical, ranksep, preds, breadth) {
    var gap = LAYOUT.nodesep;
    function along(it) { var t = target[it.node.id()]; return vertical ? t.y - it.h / 2 : t.x - it.w / 2; }
    function across(it) { var t = target[it.node.id()]; return vertical ? t.x - it.w / 2 : t.y - it.h / 2; }
    function sizeA(it) { return vertical ? it.h : it.w; }
    function sizeC(it) { return vertical ? it.w : it.h; }
    var lo = Infinity, hi = -Infinity, origin = Infinity, ranks = {}, byId = {};
    items.forEach(function (it) {
      lo = Math.min(lo, across(it));
      hi = Math.max(hi, across(it) + sizeC(it));
      origin = Math.min(origin, along(it));
      // Dagre puts every node of a rank on one center line.
      var t = target[it.node.id()];
      var key = Math.round(vertical ? t.y : t.x);
      (ranks[key] = ranks[key] || []).push(it);
      byId[it.node.id()] = it;
    });
    var widest = 0;
    items.forEach(function (it) { if (it.node.isParent()) widest = Math.max(widest, sizeC(it)); });
    hi = Math.max(lo + widest, lo + (hi - lo) * (breadth === undefined ? 1 : breadth));
    // Id to [along start, along end, across start, across end].
    var placed = {};
    function floorOf(it) {
      var f = origin;
      (preds[it.node.id()] || []).forEach(function (pid) {
        var p = placed[pid];
        if (p) f = Math.max(f, byId[pid].node.isParent() ? p[0] : p[1] + ranksep);
      });
      return f;
    }
    function put(it, a, c) {
      var A = sizeA(it), C = sizeC(it);
      placed[it.node.id()] = [a, a + A, c, c + C];
      target[it.node.id()] = vertical ? { x: c + C / 2, y: a + A / 2 } : { x: a + A / 2, y: c + C / 2 };
    }
    function clear(a, c, A, C) {
      return Object.keys(placed).every(function (pid) {
        var p = placed[pid];
        return !(a < p[1] + ranksep && a + A > p[0] - ranksep && c < p[3] + gap && c + C > p[2] - gap);
      });
    }
    Object.keys(ranks).map(Number).sort(function (a, b) { return a - b; }).forEach(function (key) {
      var rank = ranks[key].slice().sort(function (a, b) { return across(a) - across(b); });
      rank.forEach(function (it) {
        if (!it.node.isParent()) return;
        var A = sizeA(it), C = sizeC(it), floor = floorOf(it);
        var ends = Object.keys(placed).map(function (pid) { return placed[pid]; });
        var alongs = [origin, along(it)].concat(ends.map(function (p) { return p[1] + ranksep; }))
          .filter(function (a) { return a >= floor - 1e-9; }).sort(function (a, b) { return a - b; });
        var acrosses = [lo, across(it)].concat(ends.map(function (p) { return p[3] + gap; }))
          .filter(function (c) { return c >= lo - 1e-9 && c + C <= hi + 1e-9; }).sort(function (a, b) { return a - b; });
        var spot = null;
        for (var i = 0; i < alongs.length && !spot; i += 1) {
          for (var j = 0; j < acrosses.length; j += 1) {
            if (clear(alongs[i], acrosses[j], A, C)) { spot = [alongs[i], acrosses[j]]; break; }
          }
        }
        // Nothing fits inside the breadth: after everything, where it was.
        if (!spot) {
          var last = floor;
          ends.forEach(function (p) { last = Math.max(last, p[1] + ranksep); });
          spot = [last, across(it)];
        }
        put(it, spot[0], spot[1]);
      });
      var row = rank.filter(function (it) { return !it.node.isParent(); });
      if (!row.length) return;
      var top = Infinity, floor = -Infinity;
      row.forEach(function (it) { top = Math.min(top, along(it)); floor = Math.max(floor, floorOf(it)); });
      row.forEach(function (it) {
        var c1 = across(it), c2 = across(it) + sizeC(it);
        Object.keys(placed).forEach(function (pid) {
          var p = placed[pid];
          if (p[2] < c2 + 8 && p[3] > c1 - 8) floor = Math.max(floor, p[1] + ranksep);
        });
      });
      var offs = row.map(function (it) { return along(it) - top; });
      row.forEach(function (it, i) { put(it, floor + offs[i], across(it)); });
    });
  }

  /* Boundaries that start at the same place along the rank axis are a
   * column, and each column sits centered across the drawing. Dagre hangs
   * each wherever its edges pull it: the shared network account hung at
   * the foot of the AWS box with a blank quarter above it, and the
   * integration architecture came out as a staircase, every column a step
   * lower than the last, three quarters of the sheet empty. A column is
   * only moved where the move overlaps nothing in another column. */
  function centerColumns(items, target, vertical) {
    function start(it) { var t = target[it.node.id()]; return vertical ? t.y - it.h / 2 : t.x - it.w / 2; }
    function span(it) {
      var t = target[it.node.id()];
      return vertical ? [t.x - it.w / 2, t.x + it.w / 2] : [t.y - it.h / 2, t.y + it.h / 2];
    }
    function rankSpan(it) {
      var t = target[it.node.id()];
      return vertical ? [t.y - it.h / 2, t.y + it.h / 2] : [t.x - it.w / 2, t.x + it.w / 2];
    }
    var lo = Infinity, hi = -Infinity, columns = {};
    items.forEach(function (it) {
      var s = span(it);
      lo = Math.min(lo, s[0]);
      hi = Math.max(hi, s[1]);
      var key = Math.round(start(it) / 8);
      (columns[key] = columns[key] || []).push(it);
    });
    var middle = (lo + hi) / 2;
    Object.keys(columns).forEach(function (key) {
      var column = columns[key];
      var cLo = Infinity, cHi = -Infinity;
      column.forEach(function (it) { var s = span(it); cLo = Math.min(cLo, s[0]); cHi = Math.max(cHi, s[1]); });
      var shift = middle - (cLo + cHi) / 2;
      if (Math.abs(shift) < 1) return;
      // Nothing in another column may end up under a moved boundary.
      var clear = column.every(function (it) {
        var r = rankSpan(it), s = span(it);
        return items.every(function (other) {
          if (column.indexOf(other) !== -1) return true;
          var orr = rankSpan(other), os = span(other);
          var alongOverlap = r[0] < orr[1] + 8 && r[1] > orr[0] - 8;
          var acrossOverlap = s[0] + shift < os[1] + 8 && s[1] + shift > os[0] - 8;
          return !(alongOverlap && acrossOverlap);
        });
      });
      if (!clear) return;
      column.forEach(function (it) {
        var t = target[it.node.id()];
        if (vertical) t.x += shift; else t.y += shift;
      });
    });
  }

  /* The axis each edge was ranked along, by edge id, from the last layout:
   * "x" or "y" for an edge dagre placed, nothing for one it did not. The
   * router prefers to leave a node along that axis, since that is the
   * direction the layout made room in. */
  var EDGE_AXIS = {};
  //: The order each grouped field's values are laid out in, from the view:
  //: field name to values. A level of boundaries of one such field is laid
  //: out in that order rather than by the edges between them.
  var LANES = {};
  //: How many loose systems a lane puts in one row before starting another.
  var LANE_ROW = 6;
  //: The shares of its breadth the top level is tucked inside besides the
  //: whole of it. Tucked inside the breadth dagre gave it, Thurman Health's
  //: integration diagram came out 1,124 by 1,665, long and thin, the sheet
  //: no better filled than before; at seven tenths it is 1,540 by 1,164.
  var TUCK_BREADTHS = [0.9, 0.8, 0.7, 0.6, 0.5];

  // `untucked`: dagre's own ranking at every level, which bestDirection
  // decides the direction by.
  function layoutHierarchy(cy, dir, forceGrid, gridRoot, untucked) {
    var dagreLib = window.dagre;
    if (!dagreLib || !dagreLib.graphlib) return false;
    EDGE_AXIS = {};
    var box = cy.container().getBoundingClientRect();
    var ratio = box.height ? Math.max(0.6, Math.min(2.4, box.width / box.height)) : 1.4;

    function childrenOf(parent) {
      return parent ? parent.children() : cy.nodes().filter(function (n) {
        return n.parent().length === 0;
      });
    }

    // A boundary's extent, from the leaves inside it. Cytoscape's own
    // compound bounds are cached between renders, so reading them mid-layout
    // reported the size before the children moved and put siblings on top of
    // each other. Matches the stylesheet: `padding` plus room for the name.
    function extent(node) {
      if (!node.isParent()) {
        var p = node.position(), w = node.width(), h = node.height();
        return { x1: p.x - w / 2, y1: p.y - h / 2, x2: p.x + w / 2, y2: p.y + h / 2 };
      }
      var box = null;
      node.children().forEach(function (c) {
        var e = extent(c);
        box = box ? { x1: Math.min(box.x1, e.x1), y1: Math.min(box.y1, e.y1),
                      x2: Math.max(box.x2, e.x2), y2: Math.max(box.y2, e.y2) } : e;
      });
      if (!box) return { x1: 0, y1: 0, x2: 0, y2: 0 };
      var pad = LAYOUT.boundaryPad;
      // The stylesheet widens a boundary to make room for its name, evenly
      // on both sides; the layout has to count the same room.
      var extra = Math.max(0, titleRoom(node.data("label")) + (node.data("icon") ? 28 : 0) - (box.x2 - box.x1)) / 2;
      return { x1: box.x1 - pad - extra, y1: box.y1 - pad - LAYOUT.boundaryLabel,
               x2: box.x2 + pad + extra, y2: box.y2 + pad };
    }

    // The lane each boundary at a level belongs in, when every one of them
    // is a boundary of a field the view orders; null otherwise. A value the
    // lanes do not name follows the named ones.
    function laneOrder(items) {
      if (!items.length) return null;
      var field = items[0].node.data("kind");
      var order = field && LANES[field];
      if (!order || !order.length) return null;
      var out = {};
      for (var i = 0; i < items.length; i += 1) {
        var n = items[i].node;
        if (!n.data("isGroup") || n.data("kind") !== field) return null;
        var at = order.indexOf(String(n.data("value")));
        out[n.id()] = at === -1 ? order.length + i : at;
      }
      return out;
    }

    function place(parent) {
      var kids = childrenOf(parent);
      kids.forEach(function (k) { if (k.isParent()) place(k); });
      if (!kids.length) return;
      // A map's top level is a catalog of boundaries: pack them into rows
      // rather than chaining them by whatever edges cross between them.
      var grid = forceGrid || (gridRoot && !parent);

      var byId = {};
      kids.forEach(function (k) { byId[k.id()] = k; });
      var items = kids.map(function (k) {
        var e = extent(k);
        return { node: k, w: e.x2 - e.x1, h: e.y2 - e.y1, box: e };
      });

      // An edge between two descendants of different children is an edge
      // between those children, at this level.
      function within(n) {
        var cur = n;
        while (cur.length && !byId[cur.id()]) cur = cur.parent();
        return cur.length ? cur.id() : null;
      }
      var seen = {}, among = [];
      var levelAxis = (parent ? (dir === "TB" ? "LR" : "TB") : dir) === "TB" ? "y" : "x";
      // The gap between ranks makes room for the widest label that has to
      // sit in it, the way Graphviz sizes a rank for its edge labels. A
      // label on a piece of edge needs that piece nearly its own width; a
      // boundary's padding on each side of the gap gives some of it.
      var widest = 0;
      if (!grid) {
        cy.edges().forEach(function (e) {
          var a = within(e.source()), b = within(e.target());
          if (!a || !b || a === b) return;
          EDGE_AXIS[e.id()] = levelAxis;
          widest = Math.max(widest, labelPx(e.data("label")));
          var key = a + ">" + b;
          if (seen[key]) return;
          seen[key] = true;
          among.push([a, b]);
        });
      }
      var allGroups = items.every(function (it) { return it.node.isParent(); });
      var ranksep = Math.max(LAYOUT.ranksep, widest ? widest + 24 - (allGroups ? 2 * LAYOUT.boundaryPad : 0) : 0);

      var target = {};
      var lane = grid ? null : laneOrder(items);
      if (lane) {
        // A tier diagram reads edge to data whatever the edges say: the
        // boundaries of a laned field take one rank each in the field's
        // order, centered across the axis, and the edges go where they go.
        var laneDir = parent ? (dir === "TB" ? "LR" : "TB") : dir;
        var stacked = laneDir === "TB";
        var cursor = 0;
        items.slice().sort(function (a, b) { return lane[a.node.id()] - lane[b.node.id()]; }).forEach(function (it) {
          var size = stacked ? it.h : it.w;
          target[it.node.id()] = stacked ? { x: 0, y: cursor + size / 2 } : { x: cursor + size / 2, y: 0 };
          cursor += size + ranksep;
        });
      } else if (among.length) {
        // Inside a boundary the ranks run across the diagram's own direction,
        // so each boundary is a lane and the lanes stack: the reading order
        // is then boundary by boundary rather than one long chain that
        // happens to pass through boxes.
        var rankdir = parent ? (dir === "TB" ? "LR" : "TB") : dir;
        function ranked(rd) {
          var g = new dagreLib.graphlib.Graph();
          g.setGraph({ rankdir: rd, nodesep: LAYOUT.nodesep, ranksep: ranksep,
                       edgesep: LAYOUT.edgesep, marginx: 0, marginy: 0 });
          g.setDefaultEdgeLabel(function () { return {}; });
          items.forEach(function (it) { g.setNode(it.node.id(), { width: it.w, height: it.h }); });
          among.forEach(function (pair) { g.setEdge(pair[0], pair[1]); });
          // Inside a lane, what nothing connects to runs along the band in
          // rows rather than stacking across it: dagre gives every loose node
          // rank zero, which drew the edge tier as a tower of five. Chaining
          // the loose leaves with ranking-only edges, a row's worth at a time,
          // lays each chain out as a row under the connected ones.
          if (parent && LANES[parent.data("kind")]) {
            var touched = {};
            among.forEach(function (pair) { touched[pair[0]] = true; touched[pair[1]] = true; });
            var loose = items.filter(function (it) { return !touched[it.node.id()] && !it.node.isParent(); });
            for (var r = 0; r + 1 < loose.length; r += 1) {
              if ((r + 1) % LANE_ROW !== 0) g.setEdge(loose[r].node.id(), loose[r + 1].node.id());
            }
          }
          dagreLib.layout(g);
          var out = {};
          items.forEach(function (it) {
            var n = g.node(it.node.id());
            out[it.node.id()] = { x: n.x, y: n.y };
          });
          return out;
        }
        function extentOf(t) {
          var x1 = Infinity, y1 = Infinity, x2 = -Infinity, y2 = -Infinity;
          items.forEach(function (it) {
            var c = t[it.node.id()];
            x1 = Math.min(x1, c.x - it.w / 2); x2 = Math.max(x2, c.x + it.w / 2);
            y1 = Math.min(y1, c.y - it.h / 2); y2 = Math.max(y2, c.y + it.h / 2);
          });
          return [x2 - x1, y2 - y1];
        }
        // The sheet height a placement needs once its width is scaled to
        // the sheet's: whichever of width and height overshoots more decides.
        function sheetScore(t) {
          var e = extentOf(t);
          return Math.max(e[0] / ratio, e[1]);
        }
        // A level that holds a boundary is tucked as soon as it is ranked;
        // dagre's own ranking comes back beside it, for the turn below.
        var holdsGroup = items.some(function (it) { return it.node.isParent(); });
        var preds = {};
        among.forEach(function (pair) { (preds[pair[1]] = preds[pair[1]] || []).push(pair[0]); });
        // Dagre's ranking of the level, and what is drawn of it: tucked, or
        // as it was drawn before tucking.
        function copyOf(t) {
          var out = {};
          Object.keys(t).forEach(function (k) { out[k] = { x: t[k].x, y: t[k].y }; });
          return out;
        }
        function arranged(rd, breadth) {
          var raw = ranked(rd);
          var plain = copyOf(raw);
          if (allGroups) {
            compactRanks(items, plain, rd === "TB", ranksep);
            centerColumns(items, plain, rd === "TB");
          }
          if (untucked || !holdsGroup || items.length < 2) return [raw, plain];
          var tucked = copyOf(raw);
          tuckRanks(items, tucked, rd === "TB", ranksep, preds, breadth);
          // Tucked, everything hangs from the start across; each column
          // then sits centered across the drawing where it can, as a level
          // of boundaries always did.
          centerColumns(items, tucked, rd === "TB");
          // A row of leaves that a hung boundary stands in front of goes
          // after it, and the level can come out longer than it was:
          // Lending Performance's top level grew 120 pixels so. And a level
          // tucked into no less room is only moved about: General Ledger's
          // system went under its processes for nothing. Either way it is
          // drawn as it was.
          if (breadth === undefined) {
            var te = extentOf(tucked), pe = extentOf(plain);
            if (te[0] > pe[0] + 1e-9 || te[1] > pe[1] + 1e-9 ||
                (te[0] > pe[0] - 1 && te[1] > pe[1] - 1)) return [raw, plain];
          }
          return [raw, tucked];
        }
        var drawn = arranged(rankdir);
        var raw = drawn[0];
        target = drawn[1];
        // The top level is the one the sheet sees whole. Three clouds side
        // by side made the network topology four times as wide as high and
        // a quarter of its size at fit; ranked the other way the clouds
        // stack and the sheet is used. The levels inside were placed before
        // this one and keep the view's own alternation; only the outermost
        // arrangement turns, and only when the view's own direction is
        // clearly the worse fit, so a drawing an author read top to bottom
        // stays that way unless the sheet cannot show it. Weighed as dagre
        // ranks it, as it always was (bestDirection says why).
        if (!parent && items.length > 1) {
          var otherDir = rankdir === "TB" ? "LR" : "TB";
          var turnedPair = arranged(otherDir);
          if (sheetScore(turnedPair[0]) < sheetScore(raw) / 1.25) {
            target = turnedPair[1];
            rankdir = otherDir;
            var turnedAxis = rankdir === "TB" ? "y" : "x";
            cy.edges().forEach(function (e) {
              var a = within(e.source()), b = within(e.target());
              if (a && b && a !== b) EDGE_AXIS[e.id()] = turnedAxis;
            });
          }
        }
        // The direction settled, the top level is tucked inside narrower
        // breadths too, and the one that fits the sheet best is kept.
        if (!untucked && !parent && holdsGroup && items.length > 1) {
          var best = sheetScore(target);
          TUCK_BREADTHS.forEach(function (breadth) {
            var tried = arranged(rankdir, breadth)[1];
            var score = sheetScore(tried);
            if (score < best - 1e-9) { best = score; target = tried; }
          });
        }
      } else {
        // Nothing connected, or a map: pack into rows whose total shape is
        // near the sheet's. A fixed column count made every boundary a wide
        // strip and the whole a ribbon; wrapping at a width derived from the
        // area keeps the drawing close to the shape of the space it has.
        //
        // At the top level the items are boundaries of unequal size, and
        // filling rows in their own order left a hole under every short one
        // beside a tall one: the BIAN landscape came out as a staircase with
        // half the sheet empty. So there the tallest go first, so a row's
        // height is set by its first item, and the row width is one of
        // several tried, for the packing whose shape is nearest the sheet's
        // with the least empty space. Inside a boundary the order is the
        // view's own and stays.
        var area = 0, widest = 0, sumW = 0;
        items.forEach(function (it) {
          area += (it.w + LAYOUT.gapX) * (it.h + LAYOUT.gapY);
          widest = Math.max(widest, it.w);
          sumW += it.w + LAYOUT.gapX;
        });
        var wanted = parent ? 1.5 : ratio;
        // Tallest first packs unequal boundaries tightly; the view's own
        // order packs near-equal ones no worse and reads better. At the top
        // level both are tried and the fit decides.
        var laneAt = laneOrder(items);
        var orders = laneAt
          ? [items.slice().sort(function (a, b) { return laneAt[a.node.id()] - laneAt[b.node.id()]; })]
          : parent ? [items] : [items, items.slice().sort(function (a, b) {
            return (b.h - a.h) || (b.w - a.w);
          })];
        var order = items;
        function packAt(width) {
          // Bottom-left skyline packing: each item goes to the lowest spot
          // it fits, leftmost among equals. Items of one size fill rows
          // exactly as a row packer would, so a boundary's leaves keep their
          // order; boundaries of unequal size slide under one another
          // instead of leaving a hole beside every tall one.
          var sky = [{ x: 0, w: width, y: 0 }];
          var at = {}, maxX = 0, maxY = 0;
          order.forEach(function (it) {
            var w = it.w + LAYOUT.gapX, h = it.h + LAYOUT.gapY;
            var spot = null;
            for (var i = 0; i < sky.length; i++) {
              var x = sky[i].x;
              if (x > 0 && x + it.w > width + 1) continue;
              var y = 0;
              for (var j = i; j < sky.length && sky[j].x < x + w; j++) y = Math.max(y, sky[j].y);
              if (!spot || y < spot.y || (y === spot.y && x < spot.x)) spot = { x: x, y: y };
            }
            var px = spot.x, py = spot.y;
            at[it.node.id()] = { x: px + it.w / 2, y: py + it.h / 2 };
            maxX = Math.max(maxX, px + it.w);
            maxY = Math.max(maxY, py + it.h);
            var next = [];
            sky.forEach(function (s) {
              var s1 = s.x, s2 = s.x + s.w;
              if (s2 <= px || s1 >= px + w) { next.push(s); return; }
              if (s1 < px) next.push({ x: s1, w: px - s1, y: s.y });
              if (s2 > px + w) next.push({ x: px + w, w: s2 - (px + w), y: s.y });
            });
            next.push({ x: px, w: w, y: py + h });
            next.sort(function (a, b) { return a.x - b.x; });
            sky = next;
          });
          return { at: at, w: maxX, h: maxY };
        }
        var base = Math.max(widest, Math.sqrt(area * wanted));
        var tries = parent ? [1] : [0.6, 0.75, 0.9, 1, 1.15, 1.3, 1.5, 1.75, 2];
        var best = null;
        orders.forEach(function (candidate) { order = candidate; tries.forEach(function (f) {
          var res = packAt(Math.max(widest, Math.min(sumW, base * f)));
          // The score is the fit itself: the sheet height a packing needs
          // once its width is scaled to the sheet's, so whichever of width
          // and height overshoots more decides. Scoring shape and waste
          // separately chose one wide row for the technology stack and lost
          // a fifth of the fit to the empty corner under it.
          var score = Math.max(res.w / wanted, res.h);
          if (!best || score < best.score) best = { score: score, at: res.at };
        }); });
        target = best.at;
      }

      items.forEach(function (it) {
        var to = target[it.node.id()];
        if (!it.node.isParent()) { it.node.position(to); return; }
        // A finished boundary moves as a unit: shift every leaf inside it.
        var dx = to.x - (it.box.x1 + it.box.x2) / 2, dy = to.y - (it.box.y1 + it.box.y2) / 2;
        it.node.descendants().filter(function (d) { return !d.isParent(); })
          .positions(function (d) { var p = d.position(); return { x: p.x + dx, y: p.y + dy }; });
      });
    }

    place(null);
    return true;
  }

  /* ---- a diagram arranged by hand ------------------------------------------
   * A diagram drawn on the canvas is laid out until a box is moved; from then
   * on its file keeps `positions`, one line per box and boundary, and the
   * layout only proposes. Laid out afresh on every drawing, a diagram of
   * Network Topology given a second system turned two zones side by side
   * into one above the other: a layout run again keeps nothing of the last.
   * terrane/draw/arranged.py is this, line for line, so the picture `terrane
   * render` commits and the review pack draw the arrangement too.
   *
   * Every boundary is a frame, and the sheet the outermost one. A box is kept
   * by its top-left in the frame around it, a boundary by its frame's corner
   * in its parent's, so a boundary moved takes what is in it and changes one
   * line. In a frame where something is kept, what is not goes where there is
   * room beside it, in the order the layout read them; in a frame where
   * nothing is, its things keep the layout's arrangement of them.
   */
  //: The room left between something placed where there is room and what
  //: was there: the packed layout's gaps.
  var ARRANGE_GAP = { x: 24, y: 20 };

  /* What a box or boundary is kept under: the boundaries it sits in, then
   * its id; a boundary its path alone. The crumb's mark between them. */
  function positionKey(n) {
    var path = [];
    var cur = n.data("isGroup") ? n : n.parent();
    while (cur && cur.length) { path.unshift(String(cur.data("value"))); cur = cur.parent(); }
    if (!n.data("isGroup")) path.push(n.id());
    return path.join(" / ");
  }

  function frameKids(cy, g) {
    return g ? g.children() : cy.nodes().filter(function (n) { return n.parent().length === 0; });
  }

  function unionBoxes(boxes) {
    var out = null;
    boxes.forEach(function (b) {
      out = out ? { x1: Math.min(out.x1, b.x1), y1: Math.min(out.y1, b.y1), x2: Math.max(out.x2, b.x2), y2: Math.max(out.y2, b.y2) }
        : { x1: b.x1, y1: b.y1, x2: b.x2, y2: b.y2 };
    });
    return out;
  }

  function shiftBox(b, at) { return { x1: b.x1 + at.x, y1: b.y1 + at.y, x2: b.x2 + at.x, y2: b.y2 + at.y }; }

  /* A boundary around what it holds, as the layout sizes it: `extent()` in
   * layoutHierarchy, the padding and room for a name wider than the rest. */
  function paddedBox(g, c) {
    var pad = LAYOUT.boundaryPad;
    var extra = Math.max(0, titleRoom(g.data("label")) + (g.data("icon") ? 28 : 0) - (c.x2 - c.x1)) / 2;
    return { x1: c.x1 - pad - extra, y1: c.y1 - pad - LAYOUT.boundaryLabel, x2: c.x2 + pad + extra, y2: c.y2 + pad };
  }

  /* Where a box of this size goes among these: beside or under one of
   * them, clear of all by the gaps, growing what the frame holds least, and
   * of equal growth the highest and then the leftmost, so a hole is filled
   * in reading order before the frame grows. */
  function freeSpot(occupied, w, h) {
    var gx = ARRANGE_GAP.x, gy = ARRANGE_GAP.y;
    var whole = unionBoxes(occupied);
    var cands = [[whole.x1, whole.y2 + gy], [whole.x2 + gx, whole.y1]];
    occupied.forEach(function (r) { cands.push([r.x2 + gx, r.y1]); cands.push([r.x1, r.y2 + gy]); });
    var best = null;
    cands.forEach(function (c) {
      var x = c[0], y = c[1];
      var clash = occupied.some(function (r) {
        return r.x1 - gx < x + w && x < r.x2 + gx && r.y1 - gy < y + h && y < r.y2 + gy;
      });
      if (clash) return;
      var grown = (Math.max(whole.x2, x + w) - Math.min(whole.x1, x)) * (Math.max(whole.y2, y + h) - Math.min(whole.y1, y));
      if (!best || grown < best.g || (grown === best.g && (y < best.y || (y === best.y && x < best.x)))) {
        best = { g: grown, x: x, y: y };
      }
    });
    return { x: best.x, y: best.y };
  }

  /* The layout's proposal, with what was kept put back where it was kept
   * and the rest placed around it. Leaves the sheet's origin at nought and
   * each boundary's frame corner in the scratch, for a move to be kept
   * against. */
  function arrangeKept(cy, kept) {
    var auto = {};
    cy.nodes().forEach(function (n) {
      if (!n.data("isGroup")) auto[n.id()] = { x: n.position("x"), y: n.position("y") };
    });
    function autoExtent(n) {
      if (!n.data("isGroup")) {
        var a = auto[n.id()], w = n.width(), h = n.height();
        return { x1: a.x - w / 2, y1: a.y - h / 2, x2: a.x + w / 2, y2: a.y + h / 2 };
      }
      return paddedBox(n, unionBoxes(n.children().map(autoExtent)));
    }
    var at = {}, ext = {};
    function own(n) {
      return n.data("isGroup") ? ext[n.id()] : { x1: 0, y1: 0, x2: n.width(), y2: n.height() };
    }
    function frame(g) {
      var kids = frameKids(cy, g);
      kids.forEach(function (k) { if (k.data("isGroup")) frame(k); });
      var held = kids.filter(function (k) { return kept[positionKey(k)] !== undefined; });
      if (!held.length) {
        var proposed = kids.map(function (k) { return { n: k, a: autoExtent(k) }; });
        var mx = Math.min.apply(null, proposed.map(function (p) { return p.a.x1; }));
        var my = Math.min.apply(null, proposed.map(function (p) { return p.a.y1; }));
        proposed.forEach(function (p) {
          var o = own(p.n);
          at[p.n.id()] = { x: p.a.x1 - mx - o.x1, y: p.a.y1 - my - o.y1 };
        });
      } else {
        var occupied = [];
        held.forEach(function (k) {
          var v = kept[positionKey(k)];
          at[k.id()] = { x: Number(v[0]), y: Number(v[1]) };
          occupied.push(shiftBox(own(k), at[k.id()]));
        });
        // In the order the layout read them; on a tie, the payload's.
        kids.filter(function (k) { return kept[positionKey(k)] === undefined; })
          .map(function (k) { return { n: k, a: autoExtent(k) }; })
          .sort(function (p, q) { return (p.a.y1 - q.a.y1) || (p.a.x1 - q.a.x1); })
          .forEach(function (p) {
            var o = own(p.n), w = o.x2 - o.x1, h = o.y2 - o.y1;
            var s = freeSpot(occupied, w, h);
            at[p.n.id()] = { x: s.x - o.x1, y: s.y - o.y1 };
            occupied.push({ x1: s.x, y1: s.y, x2: s.x + w, y2: s.y + h });
          });
      }
      if (g) ext[g.id()] = paddedBox(g, unionBoxes(kids.map(function (k) { return shiftBox(own(k), at[k.id()]); })));
    }
    frame(null);
    var frames = { "": { x: 0, y: 0 } };
    cy.startBatch();
    (function lay(g, ox, oy) {
      frameKids(cy, g).forEach(function (k) {
        var p = at[k.id()];
        if (k.data("isGroup")) {
          frames[k.id()] = { x: ox + p.x, y: oy + p.y };
          lay(k, ox + p.x, oy + p.y);
        } else {
          k.position({ x: ox + p.x + k.width() / 2, y: oy + p.y + k.height() / 2 });
        }
      });
    })(null, 0, 0);
    cy.endBatch();
    cy.scratch("_frames", frames);
  }

  /* What the drawing keeps the moment it is first arranged: every box and
   * boundary where it is now, in whole pixels (`kept_from` in Python). A
   * boundary's corner is the least corner of what it holds, so the first
   * thing in every frame sits near [0, 0]; each corner is rounded where it
   * is on the sheet and the difference taken after, so nothing deep in the
   * drawing drifts by the sum of its boundaries' roundings. */
  function keepAll(cy) {
    var corner = {};
    function visit(g) {
      var kids = frameKids(cy, g);
      kids.forEach(function (k) {
        if (k.data("isGroup")) { visit(k); return; }
        var p = k.position();
        corner[k.id()] = { x: Math.round(p.x - k.width() / 2), y: Math.round(p.y - k.height() / 2) };
      });
      if (g && kids.length) {
        corner[g.id()] = {
          x: Math.min.apply(null, kids.map(function (k) { return corner[k.id()].x; })),
          y: Math.min.apply(null, kids.map(function (k) { return corner[k.id()].y; })),
        };
      }
    }
    visit(null);
    var out = {}, frames = {};
    function record(g, origin) {
      frameKids(cy, g).forEach(function (k) {
        var c = corner[k.id()];
        out[positionKey(k)] = [c.x - origin.x, c.y - origin.y];
        if (k.data("isGroup")) { frames[k.id()] = { x: c.x, y: c.y }; record(k, c); }
      });
    }
    var top = frameKids(cy, null);
    if (top.length) {
      var o = {
        x: Math.min.apply(null, top.map(function (k) { return corner[k.id()].x; })),
        y: Math.min.apply(null, top.map(function (k) { return corner[k.id()].y; })),
      };
      frames[""] = o;
      record(null, o);
    }
    cy.scratch("_frames", frames);
    return out;
  }

  /* One box's corner in its frame as it is now, set on the box too, so the
   * sheet shows the whole pixel the file says. */
  function keepLeaf(cy, n, kept) {
    var frames = cy.scratch("_frames") || {};
    var g = n.parent();
    var o = frames[g.length ? g.id() : ""];
    if (!o) return false;
    var p = n.position(), w = n.width(), h = n.height();
    var at = [Math.round(p.x - w / 2 - o.x), Math.round(p.y - h / 2 - o.y)];
    kept[positionKey(n)] = at;
    n.position({ x: o.x + at[0] + w / 2, y: o.y + at[1] + h / 2 });
    return true;
  }

  /* A boundary moved by (dx, dy): its line, and the frames of everything in
   * it, which moved with it. The move is whole pixels, so what is inside
   * stays on the pixels the file says. */
  function keepGroupMove(cy, g, dx, dy, kept) {
    var frames = cy.scratch("_frames") || {};
    var rx = Math.round(dx), ry = Math.round(dy);
    if (rx !== dx || ry !== dy) {
      g.descendants().filter(function (d) { return !d.data("isGroup"); }).positions(function (d) {
        var p = d.position();
        return { x: p.x + rx - dx, y: p.y + ry - dy };
      });
    }
    var key = positionKey(g);
    var parent = g.parent();
    var po = frames[parent.length ? parent.id() : ""] || { x: 0, y: 0 };
    var was = kept[key] || (frames[g.id()] ? [frames[g.id()].x - po.x, frames[g.id()].y - po.y] : [0, 0]);
    kept[key] = [Math.round(was[0] + rx), Math.round(was[1] + ry)];
    g.descendants().add(g).forEach(function (d) {
      if (frames[d.id()]) frames[d.id()] = { x: frames[d.id()].x + rx, y: frames[d.id()].y + ry };
    });
    cy.scratch("_frames", frames);
  }

  /* The lines again for boxes that moved, without a new layout: the router
   * the arranged drawing uses, from where everything is now. A drawing ELK
   * laid out gives up its routes, which were for the boxes where ELK put
   * them. */
  function rerouteInPlace(cy) {
    cy.scratch("_elk", false);
    cy.startBatch();
    cy.edges().forEach(function (e) {
      e.data("sep", "outside-to-node");
      e.data("tep", "outside-to-node");
      e.removeData("elx");
      e.removeData("ely");
    });
    cy.endBatch();
    routeDrawing(cy, cy.scratch("_dir") === "TB");
    placeEdgeLabels(cy);
  }

  //: A graph with this few edges per node is a catalog rather than a flow, and
  //: ranking it produces a ribbon. Half an edge per node is generous: the
  //: views that read well all sit above one.
  var CATALOG_EDGE_RATIO = 0.5;

  //: Past this, a diagram is a ribbon: too wide to read at any zoom that keeps
  //: the labels legible. Measured across the views that read well, none is
  //: outside 0.3 to 4.5, so six is a generous ceiling.
  var RIBBON_RATIO = 6;

  function ratioOf(cy) {
    var box = cy.elements().boundingBox();
    return box.w / Math.max(box.h, 1);
  }

  function unribbon(cy) {
    // A hub gets one rank per layer, so a wide fan-out is always one long
    // line. An organic layout has no ranks to be wide. Seeded from where the
    // layered pass left things, so the result is still the same every time.
    var ratio = ratioOf(cy);
    if (ratio <= RIBBON_RATIO && ratio >= 1 / RIBBON_RATIO) return false;
    cy.layout({
      name: "cose", animate: false, randomize: false, padding: 26,
      nodeRepulsion: 12000, idealEdgeLength: 90, numIter: 600,
      nodeDimensionsIncludeLabels: true,
    }).run();
    return true;
  }

  function isCatalog(payload) {
    var nodes = payload.counts.nodes, edges = payload.counts.edges;
    return nodes > 8 && edges / Math.max(nodes, 1) < CATALOG_EDGE_RATIO;
  }

  function layoutOptions(name, fallbackDir) {
    if (name === "cose") return { name: "cose", animate: false, nodeRepulsion: 9000, idealEdgeLength: 110, padding: 26 };
    if (name === "concentric") {
      // A wheel: the best-connected node in the middle, everything else on
      // one ring around it, spread evenly. Left to its own degree-based
      // levels, four nodes came out as a line, because a ring of one node
      // is a point.
      return {
        name: "concentric", animate: false, padding: 40, minNodeSpacing: 70,
        equidistant: true, startAngle: Math.PI / 2, avoidOverlap: true,
        concentric: function (n) {
          if (n.data("isGroup")) return 0;
          var top = n.cy().nodes().filter(function (x) { return !x.data("isGroup"); }).maxDegree(false);
          return n.degree(false) === top ? 2 : 1;
        },
        levelWidth: function () { return 1; },
      };
    }
    if (name === "grid") return { name: "grid", animate: false, padding: 26, avoidOverlap: true };
    var dir = name === "dagre-tb" ? "TB" : name === "dagre-lr" ? "LR" : fallbackDir;
    if (window.cytoscapeDagre) {
      return { name: "dagre", rankDir: dir, animate: false, padding: 26, nodeSep: 38, rankSep: 84 };
    }
    return { name: "breadthfirst", directed: true, animate: false, padding: 26 };
  }

  function updateZoomPct() {
    var span = $("zoomPct");
    if (span && state.cy) span.textContent = Math.round(state.cy.zoom() * 100) + "%";
  }

  /* ---- reports ----------------------------------------------------------
   * Six of the views answer a question with a set rather than showing a
   * structure. Drawing a set as a graph adds nothing except the suggestion
   * that the lines between the rows mean something.
   */

  function reportTable(payload) {
    var byKey = {};
    payload.elements.forEach(function (e) {
      if (!e.data.isGroup && !e.data.source) byKey[e.data.id] = e.data;
    });
    var edges = payload.elements.filter(function (e) { return e.data.source; });

    // `name` is the key, and the CSV's header; `label` is what a reader of
    // the table sees. A report is read by people, and "from_id" is a column
    // name from a dump rather than a heading.
    var columns = [
      { name: "from", label: "From", filled: edges.length },
      { name: "relationship", label: "Relationship", filled: edges.length },
      { name: "to", label: "To", filled: edges.length },
      { name: "detail", label: "Detail", filled: edges.filter(function (e) { return e.data.label; }).length },
      { name: "from_id", label: "From id", filled: edges.length },
      { name: "to_id", label: "To id", filled: edges.length },
    ];

    function nameOf(id) { return (byKey[id] && byKey[id].label) || id; }

    var rows = edges.map(function (e) {
      return {
        from: nameOf(e.data.source),
        relationship: String(e.data.kind || "").replace(/_/g, " "),
        to: nameOf(e.data.target),
        detail: e.data.label || "",
        from_id: e.data.source,
        to_id: e.data.target,
      };
    });
    // A column that says the same thing on every row says it once, above
    // the table, and leaves the width to the columns that vary.
    if (rows.length > 1) {
      columns.forEach(function (c) {
        var seen = {};
        rows.forEach(function (row) { seen[String(row[c.name] === undefined || row[c.name] === null ? "" : row[c.name])] = true; });
        var values = Object.keys(seen);
        if (values.length === 1 && values[0] !== "") c.constant = values[0];
      });
    }

    // A report whose question has no relationships is still a report: the set
    // is the answer, and an empty table says more than an empty canvas.
    if (!rows.length) {
      columns = [{ name: "entity", filled: 1 }, { name: "id", filled: 1 },
                 { name: "type", filled: 1 }];
      rows = Object.keys(byKey).map(function (id) {
        return { entity: byKey[id].label, id: id, type: byKey[id].entityType };
      });
    }

    return {
      kind: "report", id: payload.viewId, label: payload.title,
      columns: columns, rows: rows, count: rows.length,
    };
  }

  /* A timeline: the dated things in the view as bars on a calendar of
   * quarters, sectioned by what the view groups by, with the undated things
   * each reaches listed under its bar. Drawn as a grid rather than a graph
   * because time is the one axis a layout must not choose. */
  var QUARTER = /^(\d{4})-Q([1-4])$/;

  function quarterIndex(q) {
    var m = QUARTER.exec(q || "");
    return m ? parseInt(m[1], 10) * 4 + parseInt(m[2], 10) - 1 : null;
  }

  function quarterLabel(index) {
    return Math.floor(index / 4) + " Q" + ((index % 4) + 1);
  }

  //: The quarter the calendar is in, in the timeline's own index.
  function quarterNow() {
    var d = new Date();
    return d.getFullYear() * 4 + Math.floor(d.getMonth() / 3);
  }

  /* A work package's own drawing is its footprint; that is where a bar
   * leads. A model with no footprint view falls back to the neighborhood. */
  function openWorkPackage(id) {
    var has = (state.overview && state.overview.views || []).some(function (v) { return v.viewId === "change-footprint"; });
    if (has) {
      showPanel(false);
      state.viewId = "change-footprint";
      state.subject = { work_package: id };
      selectView("change-footprint");
      return;
    }
    showFocus(id, 1);
  }

  function drawTimeline(payload) {
    state.lastGraph = payload;
    state.panel = "timeline";
    showPanel(true);
    var panel = $("dataPanel");
    panel.textContent = "";
    panel.classList.remove("is-table");

    panel.appendChild(el("div", { class: "page-head" }, [
      el("div", { class: "page-head-row" }, [
        el("div", { class: "page-head-text" }, [
          el("p", { class: "crumb" }, crumbParts(payload.viewId)),
          el("h1", { text: payload.title }),
          el("p", { class: "sub", text: payload.description || "" }),
        ]),
      ]),
    ]));
    renderSubjectBar(payload);

    var groups = {}, byId = {}, tasks = [];
    payload.elements.forEach(function (e) {
      if (e.data.isGroup) { groups[e.data.id] = e.data.label; return; }
      if (e.data.source) return;
      byId[e.data.id] = e.data;
      var a = quarterIndex(e.data.start), b = quarterIndex(e.data.end);
      if (a !== null && b !== null && b >= a) tasks.push({ d: e.data, a: a, b: b });
    });
    if (!tasks.length) {
      panel.appendChild(el("p", { class: "brief-hint", text:
        "Nothing in this view carries a start and end quarter, so there is nothing to place." }));
      syncUrl();
      return;
    }
    // What each bar reaches: the systems it builds or changes, as the edge says.
    var reached = {};
    payload.elements.forEach(function (e) {
      if (!e.data.source) return;
      var to = byId[e.data.target];
      if (!to || quarterIndex(to.start) !== null) return;
      (reached[e.data.source] = reached[e.data.source] || []).push({
        id: to.id, label: to.label, verb: String(e.data.label || "").toLowerCase() || "touches",
      });
    });
    var now = quarterNow();
    var first = Math.min.apply(null, tasks.map(function (t) { return t.a; }));
    var last = Math.max.apply(null, tasks.map(function (t) { return t.b; }));
    if (now >= first - 2 && now <= last + 2) { first = Math.min(first, now); last = Math.max(last, now); }
    var span = last - first + 1;

    var key = el("div", { class: "tl-key" });
    [["is-active", "Active"], ["is-planned", "Planned"], ["is-proposed", "Proposed"]].forEach(function (pair) {
      key.appendChild(el("span", { class: "tl-key-item" }, [
        el("span", { class: "tl-key-bar " + pair[0] }), el("span", { text: pair[1] }),
      ]));
    });
    key.appendChild(el("span", { class: "tl-key-item" }, [el("span", { class: "tl-chip-dot" }), el("span", { text: "builds" })]));
    key.appendChild(el("span", { class: "tl-key-item" }, [el("span", { class: "tl-chip-dot is-changes" }), el("span", { text: "changes" })]));
    if (now >= first && now <= last) key.appendChild(el("span", { class: "tl-key-item" }, [el("span", { class: "tl-key-now" }), el("span", { text: "this quarter" })]));
    panel.appendChild(key);

    var wrap = el("div", { class: "tl-wrap" });
    var grid = el("div", { class: "tl-grid" });
    grid.style.gridTemplateColumns = "minmax(220px, 300px) repeat(" + span + ", minmax(72px, 1fr))";
    var row = 1;
    var corner = el("div", { class: "tl-corner" });
    corner.style.gridRow = "1 / 3";
    grid.appendChild(corner);
    // Years over quarters: a year's cell spans the quarters of it on the sheet.
    var q = first;
    while (q <= last) {
      var year = Math.floor(q / 4);
      var until = Math.min(last, year * 4 + 3);
      var cell = el("div", { class: "tl-year", text: String(year) });
      cell.style.gridRow = "1";
      cell.style.gridColumn = (q - first + 2) + " / " + (until - first + 3);
      grid.appendChild(cell);
      q = until + 1;
    }
    for (q = first; q <= last; q++) {
      var qc = el("div", { class: "tl-quarter" + (q % 4 === 0 ? " is-year" : "") + (q === now ? " is-now" : ""),
        text: "Q" + ((q % 4) + 1) });
      qc.style.gridRow = "2";
      qc.style.gridColumn = String(q - first + 2);
      grid.appendChild(qc);
    }
    row = 3;

    function cells(r) {
      for (var i = first; i <= last; i++) {
        var c = el("div", { class: "tl-cell" + (i % 4 === 0 ? " is-year" : "") + (i === now ? " is-now" : "") });
        c.style.gridRow = String(r);
        c.style.gridColumn = String(i - first + 2);
        grid.appendChild(c);
      }
    }

    var sections = {};
    tasks.forEach(function (t) { (sections[t.d.parent || ""] = sections[t.d.parent || ""] || []).push(t); });
    Object.keys(sections).sort(function (x, y) {
      return String(groups[x] || "").localeCompare(String(groups[y] || ""));
    }).forEach(function (sectionKey) {
      var list = sections[sectionKey].sort(function (x, y) { return (x.a - y.a) || x.d.label.localeCompare(y.d.label); });
      var from = Math.min.apply(null, list.map(function (t) { return t.a; }));
      var to = Math.max.apply(null, list.map(function (t) { return t.b; }));
      var head = el("div", { class: "tl-section" }, [
        el("span", { class: "name", text: groups[sectionKey] || "—" }),
        el("span", { class: "n", text: list.length + " " + plural(list.length, "work package") + " · "
          + quarterLabel(from) + (to !== from ? " to " + quarterLabel(to) : "") }),
      ]);
      head.style.gridRow = String(row);
      head.style.gridColumn = "1 / -1";
      grid.appendChild(head);
      row += 1;
      list.forEach(function (t) {
        var r = row;
        cells(r);
        var label = el("button", { class: "tl-label", type: "button",
          title: "Open the footprint of " + t.d.label,
          onclick: function () { openWorkPackage(t.d.id); } }, [
          el("span", { class: "name", text: t.d.label }),
          el("span", { class: "st", text: (t.d.status || "") + " · " + t.d.start + (t.d.end !== t.d.start ? " to " + t.d.end : "") }),
        ]);
        label.style.gridRow = String(r);
        label.style.gridColumn = "1";
        grid.appendChild(label);
        var under = reached[t.d.id] || [];
        var builds = under.filter(function (u) { return u.verb === "builds"; }).length;
        var changes = under.length - builds;
        var words = [];
        if (builds) words.push(builds + " built");
        if (changes) words.push(changes + " changed");
        var bar = el("button", { class: "tl-bar is-" + String(t.d.status || "").toLowerCase(), type: "button",
          title: t.d.label + ": " + t.d.start + " to " + t.d.end + (t.d.status ? ", " + t.d.status : "") + ". Open its footprint.",
          onclick: function () { openWorkPackage(t.d.id); } }, [
          el("span", { class: "tl-bar-text", text: words.length ? words.join(" · ") : t.d.label }),
        ]);
        bar.style.gridRow = String(r);
        bar.style.gridColumn = (t.a - first + 2) + " / " + (t.b - first + 3);
        grid.appendChild(bar);
        row += 1;
        if (under.length) {
          var note = el("div", { class: "tl-under" });
          var shown = under.slice(0, 5);
          shown.forEach(function (u) {
            note.appendChild(el("button", { class: "tl-chip" + (u.verb === "changes" ? " is-changes" : ""), type: "button",
              title: u.label + ": " + u.verb, onclick: function () { goToEntity(u.id); } }, [
              el("span", { class: "tl-chip-dot" + (u.verb === "changes" ? " is-changes" : "") }),
              el("span", { text: u.label }),
            ]));
          });
          if (under.length > shown.length) {
            note.appendChild(el("button", { class: "tl-chip is-more", type: "button",
              text: "and " + (under.length - shown.length) + " more",
              onclick: function () { openWorkPackage(t.d.id); } }));
          }
          note.style.gridRow = String(row);
          note.style.gridColumn = "2 / -1";
          grid.appendChild(note);
          row += 1;
        }
      });
    });
    wrap.appendChild(grid);
    panel.appendChild(wrap);
    var kind = tasks[0].d.entityType;
    var named = ((payload.legend && payload.legend.types) || []).filter(function (t) { return t.key === kind; })[0];
    var what = named ? named.label : "item";
    panel.appendChild(el("p", { class: "brief-hint", text:
      tasks.length + " " + plural(tasks.length, what) + " across " + span + " " + plural(span, "quarter")
      + ". A bar spans the recorded start and end quarters and opens the work package's footprint; "
      + "the chips under it are the systems it builds or changes." }));
    syncUrl();
  }

  function drawReport(payload) {
    state.lastGraph = payload;
    state.panel = "report";
    showPanel(true);
    var panel = $("dataPanel");
    panel.textContent = "";
    panel.classList.add("is-table");

    // The crumb a drawing wears: a report is a diagram drawn as a table.
    panel.appendChild(el("div", { class: "panel-head" }, [
      el("div", {}, [
        el("p", { class: "crumb" }, crumbParts(payload.viewId)),
        el("h1", { text: payload.title }),
        el("p", { class: "sub", text: payload.description || "" }),
      ]),
    ]));

    var host = el("div", { class: "table-host" });
    panel.appendChild(host);
    renderSubjectBar(payload);
    if (payload.matrix) {
      panel.classList.remove("is-table");
      host.appendChild(matrixGrid(payload));
    } else {
      renderTable(host, reportTable(payload));
    }
    syncUrl();
  }

  /* A report's grid: the domains down the side by tier, the frameworks
   * across the top, a ring for how firmly the domain follows the framework
   * and a count of its capabilities placed there. A column's head and a
   * count open that framework's landscape; a domain opens in the inspector. */
  function matrixGrid(payload) {
    var m = payload.matrix;
    var cells = {};
    m.cells.forEach(function (c) { cells[c.row + "|" + c.column] = c; });
    var MARK_CLASS = { "Governed by": "is-governed", "Aligned to": "is-aligned", "Informed by": "is-informed" };
    function landscape(columnKey) {
      return function () {
        state.subject = { framework: columnKey };
        state.viewId = "framework-landscape";
        selectView("framework-landscape");
      };
    }
    var hasLandscape = (state.overview && state.overview.views || []).some(function (v) { return v.viewId === "framework-landscape"; });
    var head = el("tr", {}, [el("th", { class: "mx-name", text: "Capability domain" })]);
    m.columns.forEach(function (c) {
      var label = [el("span", { class: "mx-col", text: c.label }), c.detail ? el("span", { class: "mx-kind", text: c.detail }) : null];
      head.appendChild(el("th", { class: "mx-head" }, [
        hasLandscape && c.total ? el("button", { type: "button", title: "Open " + c.label + "'s landscape", onclick: landscape(c.key) }, label)
          : el("span", {}, label),
      ]));
    });
    head.appendChild(el("th", { class: "mx-total", text: "Placed" }));
    var body = el("tbody");
    m.groups.forEach(function (g) {
      if (g.name) {
        body.appendChild(el("tr", { class: "mx-group" }, [
          el("td", { colspan: String(m.columns.length + 2), text: (BAND_GLOSS.capability_tier && BAND_GLOSS.capability_tier[g.name])
            ? g.name + " \u00b7 " + BAND_GLOSS.capability_tier[g.name].toLowerCase() : g.name }),
        ]));
      }
      g.rows.forEach(function (r) {
        var tr = el("tr", {}, [
          el("td", { class: "mx-name" }, [
            el("button", { type: "button", class: "mx-row", text: r.label, onclick: function () { showEntity(r.key); } }),
            r.size ? el("span", { class: "mx-size", text: String(r.size) }) : null,
          ]),
        ]);
        m.columns.forEach(function (c) {
          var cell = cells[r.key + "|" + c.key];
          var td = el("td", { class: "mx-cell" });
          if (!cell) { td.appendChild(el("span", { class: "mx-none", "aria-hidden": "true" })); tr.appendChild(td); return; }
          var said = [];
          if (cell.mark) {
            td.appendChild(el("span", { class: "mx-mark " + (MARK_CLASS[cell.mark] || "is-aligned"), title: cell.mark }));
            said.push(cell.mark);
          }
          if (cell.count) {
            var chip = el(hasLandscape ? "button" : "span", { class: "mx-count" + (cell.count >= 10 ? " is-deep" : cell.count >= 4 ? " is-mid" : ""),
              type: hasLandscape ? "button" : null, text: String(cell.count),
              title: cell.count + " " + plural(cell.count, "capability") + " placed in " + c.label });
            if (hasLandscape) chip.addEventListener("click", landscape(c.key));
            td.appendChild(chip);
            said.push(cell.count + " placed");
          }
          td.setAttribute("aria-label", r.label + ", " + c.label + ": " + said.join(", "));
          tr.appendChild(td);
        });
        tr.appendChild(el("td", { class: "mx-total", text: r.total ? String(r.total) : "\u2014" }));
        body.appendChild(tr);
      });
    });
    var foot = el("tr", { class: "mx-foot" }, [el("td", { class: "mx-name", text: "Placed in each" })]);
    m.columns.forEach(function (c) { foot.appendChild(el("td", { class: "mx-cell", text: c.total ? String(c.total) : "\u2014" })); });
    foot.appendChild(el("td"));
    var key = el("p", { class: "mx-key" }, [
      el("span", { class: "mx-mark is-governed" }), " Governed by ",
      el("span", { class: "mx-mark is-aligned" }), " Aligned to ",
      el("span", { class: "mx-mark is-informed" }), " Informed by ",
      el("span", { class: "mx-count is-mid", text: "8" }), " capabilities placed in it",
    ]);
    return el("div", { class: "matrix-host" }, [
      el("table", { class: "matrix" }, [el("thead", {}, [head]), body, el("tfoot", {}, [foot])]),
      key,
    ]);
  }

  /* ---- a view with a subject --------------------------------------------
   * Every other view here is about the whole estate. This one is about one
   * thing, so it has to be told which, and the picker is the difference
   * between a diagram and a diagram nobody can point at what they meant.
   */

  /* The frameworks a map's capabilities are placed in, as a lens over the
   * whole map: none, all of them, or one, which dims everything not placed
   * in it. Kept per view while the page is open. The marks come from the
   * view's `style.marks`, so a map of anything can carry a lens. */
  var MARK_COLORS = 8;

  function markColor(payload, key) {
    var keys = ((payload && payload.marks && payload.marks.keys) || []).map(function (k) { return k.key; });
    var i = keys.indexOf(key);
    return "var(--mark-" + ((i < 0 ? 0 : i) % MARK_COLORS) + ")";
  }

  function markName(payload, key) {
    var found = ((payload && payload.marks && payload.marks.keys) || []).filter(function (k) { return k.key === key; })[0];
    return found ? found.label : key;
  }

  function lensOf(viewId) { return (state.lens || {})[viewId] || "all"; }

  function applyLens() {
    var host = $("tiles"), g = state.lastGraph;
    if (!g || !g.marks) { host.removeAttribute("data-lens"); return; }
    var lens = lensOf(g.viewId);
    host.setAttribute("data-lens", lens === "none" || lens === "all" ? lens : "one");
    Array.prototype.forEach.call(host.querySelectorAll(".tile"), function (t) {
      var marks = (t.getAttribute("data-marks") || "").split(" ").filter(Boolean);
      t.classList.toggle("is-lens-off", lens !== "none" && lens !== "all" && marks.indexOf(lens) === -1);
      Array.prototype.forEach.call(t.querySelectorAll(".tile-marks i"), function (i) {
        i.classList.toggle("is-other", lens !== "all" && lens !== "none" && i.getAttribute("data-fw") !== lens);
      });
    });
    Array.prototype.forEach.call(document.querySelectorAll("#subjectBar .lens-pill"), function (p) {
      p.setAttribute("aria-pressed", p.getAttribute("data-lens") === lens ? "true" : "false");
    });
  }

  function lensBar(bar, payload) {
    var group = el("div", { class: "lens", role: "group", "aria-label": "Show frameworks" }, [
      el("span", { class: "lens-tag", text: "Frameworks" }),
    ]);
    function pill(key, label, count) {
      var b = el("button", { class: "lens-pill", type: "button", "data-lens": key,
        title: count ? label + " \u00b7 " + count + " " + plural(count, "capability") + " placed in it" : label,
        onclick: function () {
          state.lens = state.lens || {};
          state.lens[payload.viewId] = key;
          applyLens();
        } }, [
        key !== "none" && key !== "all" ? el("i", { class: "lens-sw" }) : null,
        el("span", { text: label }),
        count ? el("span", { class: "n", text: String(count) }) : null,
      ]);
      var sw = b.querySelector(".lens-sw");
      if (sw) sw.style.setProperty("--mc", markColor(payload, key));
      group.appendChild(b);
    }
    pill("none", "None");
    pill("all", "All");
    payload.marks.keys.forEach(function (k) { pill(k.key, k.label, k.count); });
    bar.appendChild(group);
  }

  function renderSubjectBar(payload) {
    var bar = $("subjectBar");
    bar.textContent = "";
    var params = payload && payload.parameters;
    var lens = !!(payload && payload.marks && isTileMap(payload));
    if ((!params || !params.length) && !lens) {
      bar.hidden = true;
      return;
    }
    bar.hidden = false;
    if (lens && (!params || !params.length)) {
      lensBar(bar, payload);
      applyLens();
      return;
    }
    bar.appendChild(el("span", { class: "subject-tag", text: "Drawn for" }));

    params.forEach(function (param) {
      var picker = el("select", { "aria-label": param.description || param.name });
      var candidates = state.index.filter(function (item) {
        return !param.type || item.type === param.type;
      });
      // A name is enough; the id only tells apart two that share one.
      var seen = {};
      candidates.forEach(function (item) { var n = item.name || item.id; seen[n] = (seen[n] || 0) + 1; });
      candidates.forEach(function (item) {
        var n = item.name || item.id;
        picker.appendChild(el("option", { value: item.id, text: seen[n] > 1 ? n + " (" + item.id + ")" : n }));
      });
      // The server falls back to whatever `render_for` picks first, so the
      // drawn subject is in the payload rather than in the query string.
      var drawn = state.subject[param.name] || param.value;
      if (drawn) picker.value = drawn;
      picker.addEventListener("change", function () {
        state.subject[param.name] = picker.value;
        selectView(state.viewId);
      });
      bar.appendChild(el("label", { class: "subject-pick" }, [
        el("span", { class: "sp-name", text: SUBJECT_NOUNS[param.type] || capFirst(String(param.name).replace(/_/g, " ")) }),
        picker,
      ]));
    });

    if (params[0] && params[0].description) {
      bar.appendChild(el("span", { class: "subject-why", text: params[0].description }));
    }
  }

  function drawGraph(payload) {
    // "Auto" picks the layout the view was written for: layered in its own
    // direction, packed when it is a catalog with nothing much connected,
    // and tiles when it is a map with nothing connected at all.
    var picker = $("layoutPicker");
    var choice = picker.value || "auto";
    if ((choice === "auto" || choice === "tiles") && isTileMap(payload)) { drawTiles(payload); return; }
    if (choice === "tiles") choice = "auto";
    state.lastGraph = payload;
    state.walk = null;
    setStageHead(payload, payload.counts.nodes + " nodes · " + payload.counts.edges + " edges");

    var prior = priorPositions();
    if (state.cy) { state.cy.destroy(); state.cy = null; }
    $("tiles").hidden = true;
    $("cy").hidden = false;
    $("cy").classList.add("is-laying");
    $("btnLabels").disabled = false;
    // A view may ask for a layout that is not layered at all: a hub is a
    // wheel (concentric), a neighborhood is organic (cose). Auto honors it.
    var asked = String(payload.layout || "").toLowerCase();
    var mode = choice !== "auto" ? choice
      : (asked === "concentric" || asked === "cose" || asked === "grid") ? asked
      : isCatalog(payload) ? "packed"
      : payload.layout === "TB" ? "dagre-tb" : "dagre-lr";
    // Arranged by hand on the canvas: the layered layout proposes and what
    // was kept overrides it, whatever the view would otherwise be given, as
    // `terrane render` does (terrane/draw/arranged.py). A layout chosen from the
    // menu still draws it the automatic way.
    var kept = payload.positions && Object.keys(payload.positions).length ? payload.positions : null;
    var arranged = !!kept && choice === "auto" && asked !== "concentric" && asked !== "cose" && asked !== "grid";
    if (arranged) mode = payload.layout === "TB" ? "dagre-tb" : "dagre-lr";
    // A map is scanned, not read along its edges, so it packs at every
    // level: boundaries into rows, nodes into grids inside them. A diagram
    // keeps its ranks.
    var packed = !arranged && (mode === "packed" || (choice === "auto" && payload.kind === "map"));
    var hierarchical = mode.indexOf("dagre") === 0 || packed;
    var dir = mode === "dagre-tb" ? "TB" : mode === "dagre-lr" ? "LR"
      : payload.layout === "TB" ? "TB" : "LR";

    LANES = payload.lanes || {};
    // A node with many edges needs a taller side for the fan and for the
    // labels the placer would otherwise hide: the switch on the governance
    // diagram sent five edges out of a 39px side. Degree is known before the
    // layout picks sides, so the box grows with it.
    var degree = {};
    payload.elements.forEach(function (e) {
      if (!e.data.source) return;
      degree[e.data.source] = (degree[e.data.source] || 0) + 1;
      degree[e.data.target] = (degree[e.data.target] || 0) + 1;
    });
    // Component glyphs, resolved from the library's categories.
    payload.elements.forEach(function (e) {
      if (e.data.source) {
        e.data.shown = e.data.label || "";
        e.data.lx = 0;
        e.data.ly = 0;
        // A straight line until the layout lays the pieces down.
        e.data.segw = "0.5";
        e.data.segd = "0";
        e.data.sep = "outside-to-node";
        e.data.tep = "outside-to-node";
        return;
      }
      if (e.data.isGroup) {
        // A boundary with no mark drops the empty field the way a leaf does;
        // Cytoscape cannot parse an empty image.
        if (!e.data.icon) delete e.data.icon;
        return;
      }
      e.data.degree = degree[e.data.id] || 0;
      var category = e.data.componentCategory
        || COMPONENT_CATEGORY[e.data.componentType] || "";
      if (GLYPHS[category]) e.data.glyph = GLYPHS[category];
      else delete e.data.glyph;
      // The provider's or vendor's own mark, where one travels, takes the
      // corner the glyph would have had.
      if (e.data.icon) delete e.data.glyph; else delete e.data.icon;
      var corner = !e.data.icon && !e.data.glyph && CORNERED[SHAPES[e.data.entityType]]
        ? typeIcon(e.data.entityType, e.data.stroke) : null;
      if (corner) e.data.ticon = corner; else delete e.data.ticon;
    });
    evenBoxes(payload.elements);

    state.cy = cytoscape({
      container: $("cy"),
      elements: payload.elements,
      // Right angles belong to ranked layouts; a packed grid has no ranks
      // for them to follow, so its edges curve.
      style: graphStyle(hierarchical && !packed),
      layout: hierarchical
        ? { name: "preset", animate: false, fit: false, positions: function () { return { x: 0, y: 0 }; } }
        : layoutOptions(mode, dir),
    });
    attachTechLayer(state.cy);
    state.cy.on("viewport", keepPlace);
    state.cy.on("dragpan scrollzoom pinchzoom", function () { returning = null; });
    // The sheet the layout was made on, before a subject bar or a note
    // takes its top: the wheel and the organic layout are placed about its
    // middle, so the fixture capture records it (`__aacLayout`). The layered
    // layout reads the sheet's own rectangle, fractions and all, and since
    // tucking lets a level's breadth decide its shape, Product Architecture
    // turned on the 904.6-pixel sheet it was laid out on and not on the
    // 861.6 left once the subject bar came: the capture records that too.
    var laidOn = [state.cy.width(), state.cy.height()];
    var laidRect = state.cy.container().getBoundingClientRect();
    var laidIn = [laidRect.width, laidRect.height];
    // ELK routes every line for boxes where it put them, which an
    // arrangement is not.
    var useElk = hierarchical && !packed && !arranged && elkFits(state.cy);
    var cyNow = state.cy;

    function fitFirst() {
      openReadable(cyNow);
      cyNow.container().classList.remove("is-laying");
    }

    if (hierarchical && !useElk) {
      if (packed) {
        layoutHierarchy(state.cy, dir, true, true);
      } else if (choice === "auto") {
        // The view says which way it reads. If the other direction fits the
        // sheet markedly better, that is the one drawn: a tall diagram in a
        // wide sheet is legible to nobody.
        dir = bestDirection(state.cy, dir);
        state.cy.style().fromJson(graphStyle(true)).update();
      } else {
        layoutHierarchy(state.cy, dir, false, false);
      }
      if (arranged) {
        arrangeKept(state.cy, kept);
        // Before the fit, the lines and the glide from the last drawing:
        // a box let go in another boundary, settled once the glide was
        // under way, glided on to where there was room and stayed there.
        if (cv) canvasSettle();
      }
      fitFirst();
    }

    if (useElk) {
      // The rest of the drawing waits for the layout; a newer drawing that
      // replaced this one in the meantime is left alone.
      layoutElk(cyNow, dir, choice === "auto").then(function (used) {
        if (state.cy !== cyNow) return;
        dir = used;
        fitFirst();
        finishGraph(true);
        settle(cyNow, prior, fitFirst);
      }).catch(function (err) {
        if (state.cy !== cyNow) return;
        if (window.console) console.warn("ELK could not lay this drawing out; using the fallback", err);
        cyNow.scratch("_elk", false);
        if (choice === "auto") dir = bestDirection(cyNow, dir); else layoutHierarchy(cyNow, dir, false, false);
        cyNow.style().fromJson(graphStyle(true)).update();
        fitFirst();
        finishGraph(true);
        settle(cyNow, prior, fitFirst);
      });
    } else {
      finishGraph(hierarchical && !packed);
      settle(cyNow, hierarchical ? prior : null, hierarchical ? fitFirst : null);
    }

    function finishGraph(layeredNow) {
    $("cy").classList.remove("is-laying");
    // The direction drawn, for the lines routed again after a box is moved.
    state.cy.scratch("_dir", dir);
    state.cy.on("tap", "node", function (evt) {
      if (cv) { canvasTap(evt.target); return; }
      if (evt.target.data("isGroup")) return;
      showEntity(evt.target.id());
    });
    state.cy.on("tap", function (evt) {
      if (evt.target !== state.cy) return;
      if (cv) { if (cv.tool === "connect") setCanvasTool("select"); canvasSelect(null); return; }
      clearSelection();
    });
    // A drawing shown whole, too small to read: double-click a part of it
    // to read it there.
    state.cy.on("dbltap", function (evt) {
      if (cv || evt.target !== state.cy || state.cy.zoom() >= READ_ZOOM - 0.01) return;
      state.cy.zoom({ level: READ_ZOOM, renderedPosition: evt.renderedPosition });
    });
    // Drop one box on another to connect them, or into another boundary to
    // move it there. A drop that means something puts it back where it was
    // and asks: how the two connect, or whether to set the field the
    // boundary is a value of. A drop on nothing leaves it where it fell; on
    // a view the layout decides where things go, so that is not kept, and
    // on the canvas it is (the diagram is arranged by hand from then on).
    var dragFrom = null, groupFrom = null;
    function dropTarget(n) {
      var p = n.position(), hit = null;
      state.cy.nodes().forEach(function (m) {
        if (hit || m === n || m.data("isGroup")) return;
        var bb = m.boundingBox({ includeLabels: false });
        if (p.x >= bb.x1 && p.x <= bb.x2 && p.y >= bb.y1 && p.y <= bb.y2) hit = m;
      });
      return hit;
    }
    // The boundary a dragged box would go into: the innermost one holding
    // the point, measured as the boxes were when the drag began. A compound
    // grows to keep its child inside, so measured now the box's own
    // boundary would hold every point it was dragged to. Only a boundary
    // that is one value of a field can take it, and not one it is already
    // in; a boundary that is a kind of thing around it must be its own, or
    // the drop would set the field and leave it somewhere else.
    function dropGroup(n) {
      var p = n.position(), hit = null;
      dragFrom.groups.forEach(function (g) {
        var bb = g.bb;
        if (p.x < bb.x1 || p.x > bb.x2 || p.y < bb.y1 || p.y > bb.y2) return;
        if (!hit || g.depth > hit.depth) hit = g;
      });
      if (!hit || !hit.node.data("field")) return null;
      var mine = n.ancestors();
      if (mine.contains(hit.node)) return null;
      var foreign = hit.node.ancestors().filter(function (a) { return !a.data("field") && !mine.contains(a); });
      return foreign.length ? null : hit.node;
    }
    function clearDrop() {
      state.cy.nodes(".drop-target").removeClass("drop-target");
      state.cy.nodes(".drop-into").removeClass("drop-into");
      state.cy.nodes(".drag-home").removeClass("drag-home");
    }
    state.cy.on("grab", "node", function (evt) {
      var n = evt.target;
      // A boundary carried on the canvas takes what is in it, and where it
      // is put is kept; anywhere else it is carried and nothing is kept.
      groupFrom = cv && n.data("isGroup") && !window.__AAC_STATIC__
        ? { id: n.id(), pos: { x: n.position().x, y: n.position().y } } : null;
      if (n.data("isGroup") || window.__AAC_STATIC__) { dragFrom = null; return; }
      dragFrom = {
        id: n.id(), pos: { x: n.position().x, y: n.position().y },
        groups: state.cy.nodes("[?isGroup]").map(function (g) {
          return { node: g, depth: g.data("depth") || 0, bb: g.boundingBox({ includeLabels: false }) };
        }),
      };
    });
    state.cy.on("drag", "node", function (evt) {
      if (!dragFrom) return;
      // On the first move rather than the grab, which every click is: a box
      // fading as it was clicked to select it read as a fault.
      if (!dragFrom.carried) {
        dragFrom.carried = true;
        evt.target.addClass("dragging");
        // The box's own boundary stretches to keep it inside, and painted
        // over its neighbors it hid the boxes and boundaries it could be
        // dropped on. While the box is carried the boundary is an outline.
        evt.target.ancestors().addClass("drag-home");
      }
      var t = dropTarget(evt.target), g = t ? null : dropGroup(evt.target);
      state.cy.nodes(".drop-target").forEach(function (m) { if (m !== t) m.removeClass("drop-target"); });
      state.cy.nodes(".drop-into").forEach(function (m) { if (m !== g) m.removeClass("drop-into"); });
      if (t) t.addClass("drop-target");
      if (g) g.addClass("drop-into");
      // On the canvas, a box carried within its own boundary lines up with
      // the boxes beside it, and says so with a guide.
      if (cv && !t && !g) canvasGuides(evt.target, dragFrom); else canvasGuidesOff(dragFrom);
    });
    state.cy.on("free", "node", function (evt) {
      if (groupFrom && evt.target.id() === groupFrom.id) {
        var gf = groupFrom, gp = evt.target.position();
        groupFrom = null;
        if (cv && Math.abs(gp.x - gf.pos.x) + Math.abs(gp.y - gf.pos.y) >= 1) {
          canvasMovedGroup(evt.target, gp.x - gf.pos.x, gp.y - gf.pos.y);
        }
        return;
      }
      if (!dragFrom) return;
      var n = evt.target, from = dragFrom, t = dropTarget(n), g = t ? null : dropGroup(n);
      dragFrom = null;
      n.removeClass("dragging");
      clearDrop();
      canvasGuidesOff(from);
      if (!t && !g) {
        // On the canvas a box put down in its own boundary stays where it
        // was put, and the diagram keeps it there.
        if (cv && from.carried) canvasMovedBox(n, from);
        return;
      }
      // Where it was dropped, before it goes back: on an arranged canvas a
      // box moved into another boundary lands there once the move is made.
      if (g && cv) canvasDropAt(from.id, g.id(), { x: n.position().x, y: n.position().y });
      n.animate({ position: from.pos, duration: REDUCED.matches ? 0 : 180 });
      var box = $("cy").getBoundingClientRect(), rp = (t || n).renderedPosition();
      if (t) { openConnectChooser(from.id, t.id(), box.left + rp.x + 12, box.top + rp.y + 12); return; }
      openRegroupChooser(from.id, g, box.left + rp.x + 12, box.top + rp.y + 12);
    });
    state.cy.on("cxttap", "node", function (evt) {
      // Pin and hide are what the canvas's own panel does by placing and
      // taking off; the menu's versions would leave the canvas to do them.
      if (cv || evt.target.data("isGroup")) return;
      var o = evt.originalEvent || {};
      state.selectedId = evt.target.id();
      highlight(evt.target.id());
      openContextMenu(evt.target.id(), o.clientX || 0, o.clientY || 0);
    });
    state.cy.on("mouseover", "node", function (evt) {
      var n = evt.target;
      if (n.data("isGroup")) return;
      n.addClass("hover");
      n.connectedEdges().addClass("hover");
    });
    state.cy.on("mouseout", "node", function (evt) {
      evt.target.removeClass("hover");
      evt.target.connectedEdges().removeClass("hover");
    });
    // A layered graph with no boundaries can still come out as one long
    // line when a hub fans out. Only then does an organic pass run, and the
    // edges follow it: right angles on a force layout lie about the geometry.
    var hasGroups = payload.elements.some(function (e) { return e.data.isGroup; });
    // Where the layered pass left every node before the organic one moves
    // it: the seeds the fixture capture reads back, since cose from the
    // same seeds is the same drawing and from any other is a different one.
    var seeds = {};
    state.cy.nodes().forEach(function (n) { var p = n.position(); seeds[n.id()] = [p.x, p.y]; });
    if (!useElk && !arranged && hierarchical && !hasGroups && mode !== "packed" && unribbon(state.cy)) {
      state.cy.style().fromJson(graphStyle(false)).update();
      openReadable(state.cy);
      layeredNow = false;
    }
    if (layeredNow && !useElk) routeDrawing(state.cy, dir === "TB");
    // What the layout decided, for the fixture capture in tools/dev to read
    // back: the direction drawn, who drew it, and the axis each edge was
    // ranked along; and, asked for, the three pieces the fallback would
    // draw, which the fixtures hold the Python's equal to. Nothing in the
    // app reads it.
    var drawn = state.cy;
    window.__aacLayout = { dir: dir, layered: layeredNow, elk: !!useElk, arranged: arranged, axis: EDGE_AXIS,
      seeds: layeredNow ? null : seeds, sheet: laidOn, rect: laidIn,
      pieces: function () { return planPieces(drawn, dir === "TB"); } };

    state.cy.on("zoom", updateZoomPct);
    updateZoomPct();
    placeEdgeLabels(state.cy);

    // What is already in the sketch wears a halo, so picking from a view
    // shows what has been picked.
    state.cy.style().selector("node.sk").style({
      "overlay-color": DRAW.accent, "overlay-opacity": 0.14, "overlay-padding": 6,
    }).selector("node.mute, edge.mute").style({ "opacity": 0.12 })
      .selector("node.drop-target").style({
        "overlay-color": DRAW.accent, "overlay-opacity": 0.18, "overlay-padding": 8,
      })
      // The boundary a box would be moved into: its edge drawn in the
      // drop color, and a wash light enough to read the names through.
      .selector("node[?isGroup].drop-into").style({
        "border-color": DRAW.accent, "border-width": 2.5, "border-style": "solid",
        "overlay-color": DRAW.accent, "overlay-opacity": 0.07, "overlay-padding": 0,
      })
      .selector("node[?isGroup].drag-home").style({
        "background-opacity": 0, "border-opacity": 0.35, "text-opacity": 0.35,
      })
      // See-through while carried, so the box it would connect to shows.
      .selector("node.dragging").style({ "opacity": 0.55 }).update();
    markSketch();
    renderSketchBar();

    renderSubjectBar(payload);
    renderLegend(payload);
    if (cv) {
      canvasMark();
      // After the glide from the old drawing, which the refit runs first.
      setTimeout(canvasFocus, REDUCED.matches ? 0 : 380);
    } else if (state.selectedId) {
      highlight(state.selectedId);
    } else {
      $("inspBody").hidden = true;
      $("inspIdle").hidden = false;
      renderBrief();
    }
    }
  }

  /* ---- ELK ------------------------------------------------------------------
   * The layered drawings are laid out by ELK, the Eclipse Layout Kernel, when
   * it is loaded: it lays out a boundary as a container rather than as the
   * box around wherever its children landed, routes every edge orthogonally
   * around nodes and boundaries, and places each edge label where it
   * overlaps nothing. Dagre, and the router written to compensate for it,
   * remain the fallback for a browser without it or a drawing it refuses.
   */
  var elkInstance = null;

  function elkAvailable() { return typeof window.ELK === "function"; }

  /* Where ELK is the better draughtsman. It routes every edge around the
   * boundaries, which reads well while they are few and unordered: a
   * system's architecture, a domain and its neighbors, an account's zones.
   * A tiered drawing, whose edges run against the tiers, and a landscape of
   * forty nodes in a dozen boxes came out as loops around the whole sheet,
   * and keep the router written for dagre, which lets an edge cross a band. */
  function elkFits(cy) {
    if (!elkAvailable()) return false;
    var leaves = 0, groups = 0, laned = false;
    cy.nodes().forEach(function (n) {
      if (!n.data("isGroup")) { leaves += 1; return; }
      groups += 1;
      var field = n.data("kind");
      if (field && LANES[field] && LANES[field].length) laned = true;
    });
    return !laned && leaves <= 30 && groups <= 8;
  }

  function elkGraph(cy, dir) {
    var lanes = LANES || {};
    var padTop = LAYOUT.boundaryPad + 14;
    function laneIndex(n) {
      var field = n.data("kind");
      var order = field && lanes[field];
      if (!order || !order.length) return null;
      var at = order.indexOf(String(n.data("value")));
      return at === -1 ? order.length : at;
    }
    function build(n) {
      var out = { id: n.id() };
      if (n.isParent()) {
        var kids = n.children();
        out.children = kids.map(build);
        out.layoutOptions = {
          "elk.padding": "[top=" + padTop + ",left=" + LAYOUT.boundaryPad + ",bottom=" + LAYOUT.boundaryPad + ",right=" + LAYOUT.boundaryPad + "]",
          "elk.nodeSize.minimum": "(" + (titleRoom(n.data("label")) + (n.data("icon") ? 28 : 0)) + ",40)",
          "elk.nodeSize.constraints": "MINIMUM_SIZE",
        };
        lanesOf(kids, out);
      } else {
        var box = labelBox(n);
        out.width = box.w;
        out.height = box.h;
      }
      return out;
    }
    // Siblings that are boundaries of a field with a reading order are
    // laid out in that order, as partitions: the tiers of a tiered drawing
    // read edge to data whatever the edges between them say.
    function lanesOf(kids, parent) {
      var indices = {};
      var any = false;
      kids.forEach(function (k) { var i = laneIndex(k); if (i !== null) { indices[k.id()] = i; any = true; } });
      if (!any) return;
      parent.layoutOptions = parent.layoutOptions || {};
      parent.layoutOptions["elk.partitioning.activate"] = "true";
      var most = Math.max.apply(null, Object.keys(indices).map(function (k) { return indices[k]; }));
      (parent.children || []).forEach(function (c) {
        c.layoutOptions = c.layoutOptions || {};
        c.layoutOptions["elk.partitioning.partition"] = String(indices[c.id] === undefined ? most + 1 : indices[c.id]);
      });
    }
    var roots = cy.nodes().filter(function (n) { return n.parent().length === 0; });
    var root = { id: "__root", children: roots.map(build), edges: [] };
    root.layoutOptions = {
      "elk.algorithm": "layered",
      "elk.direction": dir === "TB" ? "DOWN" : "RIGHT",
      "elk.hierarchyHandling": "INCLUDE_CHILDREN",
      "elk.edgeRouting": "ORTHOGONAL",
      "elk.layered.spacing.nodeNodeBetweenLayers": "44",
      "elk.spacing.nodeNode": "18",
      "elk.spacing.edgeNode": "12",
      "elk.spacing.edgeEdge": "10",
      "elk.layered.spacing.edgeNodeBetweenLayers": "16",
      "elk.layered.spacing.edgeEdgeBetweenLayers": "10",
      "elk.spacing.componentComponent": "36",
      "elk.spacing.edgeLabel": "4",
      "elk.edgeLabels.inline": "true",
      "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
      "elk.layered.nodePlacement.favorStraightEdges": "true",
      "elk.layered.crossingMinimization.strategy": "LAYER_SWEEP",
      "elk.layered.considerModelOrder.strategy": "NODES_AND_EDGES",
      // No post-compaction: it slid boxes along the rank axis after the
      // lines into and out of boundaries were routed, so a line crossing a
      // boundary ran past its turn and back (six on the servicing domain,
      // ending in open sheet), and a column of systems came out ragged.
      "elk.layered.compaction.connectedComponents": "true",
      "elk.layered.unnecessaryBendpoints": "true",
      "elk.layered.thoroughness": "10",
      "elk.padding": "[top=12,left=12,bottom=12,right=12]",
    };
    lanesOf(roots, root);
    // Edges, with a box for each label that will be shown, so the layout
    // leaves room for it. A label that repeats the line style, or repeats
    // the word on another edge between the same two nodes, is left out.
    var said = {};
    cy.edges().forEach(function (e) {
      var s = e.source(), t = e.target();
      if (!s.length || !t.length || s.data("isGroup") || t.data("isGroup") || s.id() === t.id()) return;
      var entry = { id: e.id(), sources: [s.id()], targets: [t.id()] };
      var text = String(e.data("label") || "");
      var redundant = text.length > 0 && text.toLowerCase() === String(edgeWord(e.data("kind")) || "").toLowerCase();
      var pair = [s.id(), t.id()].sort().join("|") + "|" + text;
      if (text && !redundant && !said[pair]) {
        said[pair] = true;
        entry.labels = [{ text: text, width: labelPx(text) + 6, height: LABEL_H + 4 }];
      }
      root.edges.push(entry);
    });
    return root;
  }

  function applyElk(cy, root) {
    var origin = {};
    var pos = {};
    origin[root.id] = { x: 0, y: 0 };
    function walk(node, ox, oy) {
      (node.children || []).forEach(function (c) {
        var ax = ox + (c.x || 0), ay = oy + (c.y || 0);
        origin[c.id] = { x: ax, y: ay };
        if (c.children && c.children.length) walk(c, ax, ay);
        else pos[c.id] = { x: ax + (c.width || 0) / 2, y: ay + (c.height || 0) / 2 };
      });
    }
    walk(root, 0, 0);
    var edges = [];
    function collect(node) {
      (node.edges || []).forEach(function (e) { edges.push(e); });
      (node.children || []).forEach(collect);
    }
    collect(root);
    var labels = {};
    cy.startBatch();
    cy.nodes().forEach(function (n) { if (!n.isParent() && pos[n.id()]) n.position(pos[n.id()]); });
    edges.forEach(function (ed) {
      var e = cy.getElementById(ed.id);
      if (!e.length) return;
      var sec = ed.sections && ed.sections[0];
      var o = origin[ed.container] || origin[root.id];
      function abs(p) { return { x: o.x + p.x, y: o.y + p.y }; }
      var sp = e.source().position(), tp = e.target().position();
      if (!sec) {
        e.data("segw", "0.5"); e.data("segd", "0");
        e.data("sep", "outside-to-node"); e.data("tep", "outside-to-node");
        return;
      }
      var start = abs(sec.startPoint), end = abs(sec.endPoint);
      e.data("sep", Math.round(start.x - sp.x) + "px " + Math.round(start.y - sp.y) + "px");
      e.data("tep", Math.round(end.x - tp.x) + "px " + Math.round(end.y - tp.y) + "px");
      // Segment points are given against the line between the two centers:
      // how far along it, and how far to its left.
      var dx = tp.x - sp.x, dy = tp.y - sp.y;
      var len2 = dx * dx + dy * dy || 1, len = Math.sqrt(len2);
      var bends = (sec.bendPoints || []).map(abs);
      if (!bends.length) {
        e.data("segw", "0.5"); e.data("segd", "0");
      } else {
        var ws = [], ds = [];
        bends.forEach(function (pt) {
          var vx = pt.x - sp.x, vy = pt.y - sp.y;
          ws.push(((vx * dx + vy * dy) / len2).toFixed(4));
          ds.push(((vy * dx - vx * dy) / len).toFixed(2));
        });
        e.data("segw", ws.join(" "));
        e.data("segd", ds.join(" "));
      }
      e.removeClass("free");
      if (ed.labels && ed.labels[0] && ed.labels[0].x !== undefined) {
        var lb = ed.labels[0];
        var c = abs({ x: lb.x + (lb.width || 0) / 2, y: lb.y + (lb.height || 0) / 2 });
        labels[ed.id] = c;
      }
    });
    cy.endBatch();
    // The label offsets are relative to the midpoint of the path as drawn,
    // which exists only once the path does.
    cy.startBatch();
    cy.edges().forEach(function (e) {
      var c = labels[e.id()];
      if (!c) { e.removeData("elx"); e.removeData("ely"); return; }
      var mid = e.midpoint();
      e.data("elx", Math.round(c.x - mid.x));
      e.data("ely", Math.round(c.y - mid.y));
    });
    cy.endBatch();
    cy.scratch("_elk", true);
  }

  /* Lay the drawing out; with `tryBoth`, in the view's direction and the
   * other, keeping the one that fits the sheet at the larger zoom unless
   * the view's own is close. Resolves to the direction used. */
  function layoutElk(cy, dir, tryBoth) {
    if (!elkInstance) elkInstance = new window.ELK();
    var box = cy.container().getBoundingClientRect();
    function run(d) {
      return elkInstance.layout(elkGraph(cy, d)).then(function (out) {
        return { dir: d, out: out, w: out.width || 1, h: out.height || 1 };
      });
    }
    function zoomFor(r) {
      return Math.min((box.width || 1) / Math.max(r.w, 1), (box.height || 1) / Math.max(r.h, 1));
    }
    var other = dir === "TB" ? "LR" : "TB";
    var runs = tryBoth ? Promise.all([run(dir), run(other)]) : run(dir).then(function (r) { return [r]; });
    return runs.then(function (results) {
      var best = results[0];
      if (results.length > 1 && zoomFor(results[1]) > zoomFor(results[0]) * 1.3) best = results[1];
      applyElk(cy, best.out);
      return best.dir;
    });
  }

  /* What is shown of the labels ELK placed: all of them under the budget,
   * none above it, the Labels button either way; the offsets stay as the
   * layout chose them. */
  function showElkLabels(cy, force) {
    var labeled = cy.edges().filter(function (e) { return e.data("elx") !== undefined; });
    var show = force ? true : (state.labels === null ? labeled.length <= LABEL_BUDGET : state.labels);
    if (!force) {
      state.labelsShown = show;
      var btn = $("btnLabels");
      if (btn) {
        btn.setAttribute("aria-pressed", show ? "true" : "false");
        btn.disabled = labeled.length === 0;
      }
    }
    cy.startBatch();
    cy.edges().forEach(function (e) {
      e.removeClass("rot");
      if (show && e.data("elx") !== undefined) {
        e.data("shown", String(e.data("label") || ""));
        e.data("lx", e.data("elx"));
        e.data("ly", e.data("ely"));
      } else {
        e.data("shown", "");
        e.data("lx", 0);
        e.data("ly", 0);
      }
    });
    cy.endBatch();
  }

  /* ---- tile maps ----------------------------------------------------------
   * A map with no edges is not a graph: it is a set of things sorted into
   * boxes, and a graph layout has nothing to say about where each goes. The
   * capability domains drew as 136 identical hexagons fitted at a third of
   * their size. So an edgeless map is drawn as tiles: a band per top-level
   * boundary where the field has a reading order (the tiers of a capability
   * map), a card per boundary otherwise, each thing a tile tinted by the
   * view's dimension from the same palette the canvas uses. HTML rather
   * than canvas: crisp at any size, wrapped to the width of the sheet,
   * scrolled rather than shrunk, every tile a button. Any layout but Auto
   * or Tiles draws the same view as a graph.
   */
  function isTileMap(payload) {
    return payload.kind === "map" && !payload.sketch
      && !payload.elements.some(function (e) { return !!e.data.source; });
  }

  function tilesShown() { return !$("tiles").hidden; }

  //: A line under a band's name, where the field is one everybody reads the
  //: same way.
  var BAND_GLOSS = {
    capability_tier: { Direct: "Strategy and management", Core: "Customer-facing operations", Enable: "Shared support services" },
  };

  function plural(n, word) {
    if (n === 1) return word;
    if (/y$/.test(word) && !/[aeiou]y$/.test(word)) return word.slice(0, -1) + "ies";
    if (/(s|x|ch|sh)$/.test(word)) return word + "es";
    return word + "s";
  }

  /* What a tile map is of, said the same way over the sheet and in the
   * brief: the things by their own name, and the innermost boxes. */
  function tileMeta(payload) {
    var types = (payload.legend && payload.legend.types) || [];
    var typeLabel = types[0] ? types[0].label : "item";
    var parents = {};
    payload.elements.forEach(function (e) { if (e.data.isGroup && e.data.parent) parents[e.data.parent] = true; });
    var leaves = payload.elements.filter(function (e) { return e.data.isGroup && !parents[e.data.id]; }).length;
    return payload.counts.nodes + " " + plural(payload.counts.nodes, typeLabel)
      + (leaves ? " \u00b7 " + leaves + " " + plural(leaves, "group") : "");
  }

  function sentence(text) {
    var t = String(text || "").replace(/_/g, " ");
    return t.charAt(0).toUpperCase() + t.slice(1);
  }

  function setStageHead(payload, meta) {
    $("viewTitle").textContent = payload.title;
    var desc = $("viewDesc");
    desc.textContent = payload.description || "";
    desc.title = payload.description || "";
    desc.classList.remove("open");
    $("viewMeta").textContent = meta;
    var tag = $("viewKind");
    if (tag) {
      var word = KIND_WORDS[payload.kind] || "";
      tag.textContent = word ? word.charAt(0).toUpperCase() + word.slice(1) : "";
      tag.hidden = !word;
    }
  }

  // "No edges connected" is a finding on a diagram and a description of a
  // map: a tile map says nothing about it.
  function visibleNotes(g) {
    return (g.notes || []).filter(function (n) { return !(isTileMap(g) && /^No edges/i.test(n)); });
  }

  function drawTiles(payload) {
    arrive();
    state.lastGraph = payload;
    state.walk = null;
    if (state.cy) { state.cy.destroy(); state.cy = null; }
    var host = $("tiles");
    host.textContent = "";
    host.hidden = false;
    $("cy").hidden = true;
    $("btnLabels").disabled = true;
    setTileZoom(1);

    var groups = {}, roots = [], nodes = [], loose = [];
    payload.elements.forEach(function (e) {
      var d = e.data;
      if (d.source) return;
      if (d.isGroup) groups[d.id] = { data: d, groups: [], nodes: [] };
      else nodes.push(d);
    });
    // The payload lists boundaries parents first and in lane order, so
    // keeping its order keeps the reading order.
    payload.elements.forEach(function (e) {
      var d = e.data;
      if (!d.isGroup) return;
      if (d.parent && groups[d.parent]) groups[d.parent].groups.push(groups[d.id]);
      else roots.push(groups[d.id]);
    });
    nodes.forEach(function (d) {
      if (d.parent && groups[d.parent]) groups[d.parent].nodes.push(d);
      else loose.push(d);
    });
    var typeLabel = (payload.legend && payload.legend.types && payload.legend.types[0])
      ? payload.legend.types[0].label : "item";
    setStageHead(payload, tileMeta(payload));

    function countOf(g) {
      return g.nodes.length + g.groups.reduce(function (n, k) { return n + countOf(k); }, 0);
    }
    function tile(d) {
      var b = el("button", { class: "tile" + (d.faded ? " is-faded" : ""), type: "button", "data-id": d.id,
        title: d.label + (d.styleKey && d.styleKey !== "default" ? " \u00b7 " + d.styleKey : "") }, [
        el("span", { class: "tile-name", text: d.label }),
        d.tech ? el("span", { class: "tile-sub", text: d.tech }) : null,
      ]);
      if (payload.marks && d.marks && d.marks.length) {
        b.setAttribute("data-marks", d.marks.join(" "));
        b.title += " \u00b7 placed in " + d.marks.map(function (k) { return markName(payload, k); }).join(", ");
        var marks = el("span", { class: "tile-marks", "aria-hidden": "true" });
        d.marks.forEach(function (k) {
          var dot = el("i", { "data-fw": k });
          dot.style.setProperty("--mc", markColor(payload, k));
          marks.appendChild(dot);
        });
        b.appendChild(marks);
      }
      b.style.setProperty("--tf", d.fill);
      b.style.setProperty("--ts", d.stroke);
      // The palette's border weights run 1 to 2.6 on the canvas; on a tile
      // the same scale reads at 1 to 2 pixels.
      b.style.setProperty("--tw", (1 + Math.max(0, Math.min(1, ((d.strokeWidth || 1) - 1) / 1.6))).toFixed(2) + "px");
      b.addEventListener("click", function () { showEntity(d.id); });
      b.addEventListener("contextmenu", function (e) {
        e.preventDefault();
        openContextMenu(d.id, e.clientX, e.clientY);
      });
      b.addEventListener("keydown", function (e) {
        if ((e.key === "Delete" || e.key === "Backspace") && viewEditable()) {
          e.preventDefault();
          state.selectedId = d.id;
          changeMembership({ hide: [d.id] });
        } else if (e.key === "ContextMenu" || (e.shiftKey && e.key === "F10")) {
          e.preventDefault();
          var r = b.getBoundingClientRect();
          openContextMenu(d.id, r.left + 12, r.bottom - 4);
        }
      });
      return b;
    }
    function grid(list, cls) {
      var g = el("div", { class: "tgrid" + (cls ? " " + cls : "") });
      list.forEach(function (d) { g.appendChild(tile(d)); });
      return g;
    }
    function card(g) {
      var box = el("section", { class: "tcard" }, [
        el("h4", { class: "tcard-h" }, [
          el("span", { text: g.data.label }),
          el("span", { class: "tcard-n", text: String(countOf(g)) }),
        ]),
      ]);
      if (g.nodes.length) box.appendChild(grid(g.nodes, "is-list"));
      if (g.groups.length) {
        var inner = el("div", { class: "tcards is-nested" });
        g.groups.forEach(function (k) { inner.appendChild(card(k)); });
        box.appendChild(inner);
      }
      return box;
    }
    function band(g) {
      var gloss = (BAND_GLOSS[g.data.kind] || {})[g.data.value];
      var n = countOf(g);
      var body = el("div", { class: "tband-body" });
      if (g.groups.length) {
        var cards = el("div", { class: "tcards" });
        g.groups.forEach(function (k) { cards.appendChild(card(k)); });
        body.appendChild(cards);
      }
      if (g.nodes.length) body.appendChild(grid(g.nodes));
      return el("section", { class: "tband" }, [
        el("h3", { class: "tband-h" }, [
          el("span", { class: "tband-name", text: g.data.label }),
          gloss ? el("span", { class: "tband-gloss", text: gloss }) : null,
          el("span", { class: "tband-n", text: n + " " + plural(n, typeLabel) }),
        ]),
        body,
      ]);
    }
    // Bands when the top-level field has a reading order or there are only
    // a few; cards when there are many, so twenty-two domains wrap into
    // columns instead of stacking into one long scroll.
    var lanes = payload.lanes || {};
    var banded = roots.length > 0 && (lanes[roots[0].data.kind] || roots.length <= 4);
    if (banded) {
      roots.forEach(function (g) { host.appendChild(band(g)); });
    } else if (roots.length) {
      var cards = el("div", { class: "tcards" });
      roots.forEach(function (g) { cards.appendChild(card(g)); });
      host.appendChild(cards);
    }
    if (loose.length) host.appendChild(grid(loose));

    markSketch();
    renderSketchBar();
    renderSubjectBar(payload);
    renderLegend(payload);
    if (state.selectedId) {
      highlight(state.selectedId);
    } else {
      $("inspBody").hidden = true;
      $("inspIdle").hidden = false;
      renderBrief();
    }
  }

  /* The whole tile map on the sheet: the largest zoom at which nothing is
   * left below the fold. The map reflows to the width as it shrinks, so the
   * height is measured at each step rather than computed once. Asked for by
   * the capability map, which is a hundred and thirty-six tiles and was only
   * ever seen a screenful at a time. */
  function fitTiles() {
    var host = $("tiles");
    // Below the buttons' floor on purpose: the overview is for where things
    // are, not for reading every name.
    var steps = [1, 0.9, 0.8, 0.72, 0.64, 0.57, 0.5, 0.44, 0.38, 0.33];
    for (var i = 0; i < steps.length; i++) {
      setTileZoom(steps[i]);
      host.scrollTop = 0;
      if (host.scrollHeight <= host.clientHeight + 2) return;
    }
  }

  function setTileZoom(z) {
    z = Math.max(0.33, Math.min(2, z || 1));
    state.tileZoom = z;
    $("tiles").style.zoom = String(z);
    $("zoomPct").textContent = Math.round(z * 100) + "%";
  }

  function tileOf(id) {
    var key = window.CSS && CSS.escape ? CSS.escape(id) : String(id).replace(/"/g, '\\"');
    return $("tiles").querySelector('.tile[data-id="' + key + '"]');
  }

  function clearTiles() {
    $("tiles").querySelectorAll(".tile").forEach(function (t) {
      t.classList.remove("is-sel", "is-dim", "conf-direct", "conf-likely", "conf-possible");
    });
  }

  /* The tile map as a picture, for the PNG button and the review pack: the
   * tiles' own markup and stylesheet inside an SVG, the fonts carried along
   * as data so the picture is set in the same face, rasterized at 2x. */
  function fileData(path, mime) {
    return fetch(path).then(function (r) { return r.arrayBuffer(); }).then(function (buf) {
      var bytes = new Uint8Array(buf), bin = "";
      for (var i = 0; i < bytes.length; i += 1) bin += String.fromCharCode(bytes[i]);
      return "data:" + mime + ";base64," + btoa(bin);
    });
  }

  function tilesPng(scale) {
    var S = scale || 2;
    var host = $("tiles");
    var was = state.tileZoom || 1;
    host.style.zoom = "1";
    var w = host.clientWidth, h = host.scrollHeight;
    var clone = host.cloneNode(true);
    host.style.zoom = String(was);
    clone.hidden = false;
    clone.classList.add("is-export");
    clone.style.cssText = "width:" + w + "px;height:" + h + "px;zoom:1;overflow:visible";
    // The faces the tiles are set in, carried as data: a picture loaded
    // from a data URL fetches nothing, so a face named by path would fall
    // back to the system's and wrap every name somewhere else. These were
    // the Plex files until the faces changed, and the export fell back.
    var fonts = ["geist-latin-400-normal", "geist-latin-500-normal",
                 "geist-latin-600-normal", "geist-mono-latin-400-normal"];
    return Promise.all([fetch("styles.css").then(function (r) { return r.text(); })].concat(
      fonts.map(function (name) { return fileData("fonts/" + name + ".woff2", "font/woff2"); })
    )).then(function (parts) {
      var css = parts[0];
      fonts.forEach(function (name, i) {
        css = css.split('url("fonts/' + name + '.woff2")').join('url("' + parts[i + 1] + '")');
      });
      var xhtml = new XMLSerializer().serializeToString(clone);
      var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="' + w + '" height="' + h + '">'
        + "<style><![CDATA[" + css.replace(/\]\]>/g, "") + "]]></style>"
        + '<foreignObject width="' + w + '" height="' + h + '">' + xhtml + "</foreignObject></svg>";
      return new Promise(function (resolve, reject) {
        var img = new Image();
        img.onload = function () {
          var canvas = document.createElement("canvas");
          canvas.width = w * S;
          canvas.height = h * S;
          var ctx = canvas.getContext("2d");
          ctx.fillStyle = "#ffffff";
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          ctx.scale(S, S);
          ctx.drawImage(img, 0, 0);
          try { resolve(canvas.toDataURL("image/png")); } catch (err) { reject(err); }
        };
        img.onerror = function () { reject(new Error("the tile map could not be rasterized")); };
        img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
      });
    });
  }

  function currentDrawingPng(scale) {
    if (tilesShown()) return tilesPng(scale);
    return state.cy ? drawingPng(state.cy, scale) : Promise.reject(new Error("no drawing on the page"));
  }

  /* ---- routing -----------------------------------------------------------
   * On a layered drawing every edge is three straight pieces: out of one
   * node, across the gap, into the other. Cytoscape's taxi edges drew the
   * same shape, but every edge left a node from the middle of its side, so
   * five edges out of one system ran along one line until the first of them
   * turned off, and a label on that stretch belonged to all five; and a taxi
   * edge falls back to a straight line the moment an endpoint is moved. So
   * the edges on each side of a node are fanned along that side, in the
   * order of where they are going so the fan does not cross itself,
   * fourteen pixels apart or as close as the side allows, and the pieces
   * are laid down from the fanned points as segment edges. A shape with no
   * straight side keeps its edges at the middle. Two nodes with no side
   * facing the other across a gap are joined by a curve.
   */
  var FANNED = { "round-rectangle": 1, "rectangle": 1, "cut-rectangle": 1,
                 "octagon": 1, "round-octagon": 1, "pill": 1 };
  var FAN_STEP = 14;
  var FAN_INSET = 8;
  var FACE_GAP = 8;
  /* Middle pieces of different edges keep this far apart along the axis
   * they cross, so two edges through one corridor read as two, and a label
   * turned along each still has room. */
  var TURN_APART = 28;
  /* A run across the gap closer than this to a boundary's border, along
   * it, reads as the border: the transit gateway's line to the risk
   * account turned on its region's bottom edge, and three lines into one
   * zone shared a run down its left. One step of the turn ladder clears it. */
  var BORDER_NEAR = 8;
  /* The fanned shapes whose sides are straight where the fan puts a line:
   * a rectangle's corner is at most the fan's inset, a pill's longer
   * radius is off by a pixel and a half at worst. An octagon's side is flat
   * only across its middle, so an end pinned there would start in the air;
   * it keeps the end Cytoscape finds. */
  var PORTED = { "round-rectangle": 1, "rectangle": 1, "cut-rectangle": 1, "pill": 1 };
  /* How far past the end of a boundary's name a port is moved to clear it. */
  var NAME_CLEAR = 6;

  /* The three pieces, planned: for every edge its segment points and where
   * its two ends are, or null for a pair joined by a curve. Written by
   * writeRoutes(); the fallback for an edge the grid cannot carry. */
  function planPieces(cy, down) {
    var P = down ? "y" : "x";
    function half(n, axis) { return (axis === "x" ? n.width() : n.height()) / 2; }
    function other(axis) { return axis === "x" ? "y" : "x"; }
    // Every leaf, for keeping runs out from behind nodes they do not touch.
    var boxes = cy.nodes().filter(function (n) { return !n.data("isGroup"); }).map(function (n) {
      var bb = n.boundingBox({ includeLabels: false, includeOverlays: false });
      return { id: n.id(), x1: bb.x1, y1: bb.y1, x2: bb.x2, y2: bb.y2 };
    });
    /* And every boundary's name, in its top-left corner: a run through a
     * name strikes the word out. The turn ten short of the first row of a
     * tier is in the tier's padding, which is where its name is, and
     * Tiered Architecture's long run to the edge tier ran straight through
     * "Private-App"; fifteen lines on the nine dagre drawings did the same.
     * Kept off after the nodes, not with them: counted as one more node,
     * seven of those lines went behind a box instead, which hides a line
     * rather than crossing out a word and is no better. The box is the
     * word as drawn, centered half its nominal width past twelve in, its
     * own width wide (nameWidth) and four pixels of air about it, not the
     * corner the label placer keeps clear: in that, a line leaving a first
     * column through the padding beside the word counted the same as one
     * through it, and the border below put Integration Architecture's
     * through the C of "Channel". The id is no node's, so no edge is
     * exempt. Its four borders too, after the names (BORDER_NEAR); and the
     * box itself, for the borders a route crosses. */
    var borders = [], bounds = [];
    cy.nodes().filter(function (n) { return n.data("isGroup"); }).forEach(function (n) {
      var bb = n.boundingBox({ includeLabels: false, includeOverlays: false });
      bounds.push(bb);
      var word = nameWord(bb, n.data("label"));
      boxes.push({ id: "", name: true, x1: word[0], y1: word[1], x2: word[2], y2: word[3] });
      borders.push({ a: "y", at: bb.y1, lo: bb.x1, hi: bb.x2 }, { a: "y", at: bb.y2, lo: bb.x1, hi: bb.x2 },
                   { a: "x", at: bb.x1, lo: bb.y1, hi: bb.y2 }, { a: "x", at: bb.x2, lo: bb.y1, hi: bb.y2 });
    });
    // Whether a straight piece along `a`, between u1 and u2 at `v` across,
    // passes through a box.
    function hits(b, a, u1, u2, v) {
      var lo = Math.min(u1, u2), hi = Math.max(u1, u2);
      var bl = a === "x" ? b.x1 : b.y1, bh = a === "x" ? b.x2 : b.y2;
      var cl = a === "x" ? b.y1 : b.x1, ch = a === "x" ? b.y2 : b.x2;
      return hi >= bl - 2 && lo <= bh + 2 && v >= cl - 2 && v <= ch + 2;
    }
    /* How many of a boundary's borders a straight piece along `a`, between
     * u1 and u2 at `v` across, goes through: a line into a box that holds
     * neither of its ends and out again is two more than the route needs.
     * The onboarding drawing's line from Card Servicing Service to Customer
     * Identity API climbed inside Private-Data, beside its border, because
     * nothing counted it. A piece on a border counts as through it, so a
     * turn laid along one saves nothing. */
    function crossings(b, a, u1, u2, v) {
      var cl = a === "x" ? b.y1 : b.x1, ch = a === "x" ? b.y2 : b.x2;
      if (v < cl || v > ch) return 0;
      var lo = Math.min(u1, u2), hi = Math.max(u1, u2);
      var bl = a === "x" ? b.x1 : b.y1, bh = a === "x" ? b.x2 : b.y2;
      return (bl >= lo && bl <= hi ? 1 : 0) + (bh >= lo && bh <= hi ? 1 : 0);
    }
    /* The best three-piece route from s to t leaving along `a`: out to the
     * turn at c1 across, along the turn from c1 to c2, in from the turn at
     * c2. The turn is halfway unless another turn passes behind fewer
     * nodes; the candidates are halfway and a little short of or past
     * every node between. Returns the turn and how many nodes the route
     * still passes behind. */
    // Middle pieces already laid, so a later edge through the same
    // corridor takes its own line.
    var laid = [];
    function plan(sNode, tNode, a, c1, c2, labelW) {
      var sp = sNode.position(), tp = tNode.position();
      var c = other(a);
      var dir = tp[a] >= sp[a] ? 1 : -1;
      var from = sp[a] + dir * half(sNode, a), to = tp[a] - dir * half(tNode, a);
      var mid = (from + to) / 2;
      function inRange(v) { return (v - from) * dir > 6 && (to - v) * dir > 6; }
      var cands = [mid];
      [12, 24, 36, 48].forEach(function (d) {
        if (inRange(mid + d)) cands.push(mid + d);
        if (inRange(mid - d)) cands.push(mid - d);
      });
      boxes.forEach(function (b) {
        if (b.id === sNode.id() || b.id === tNode.id()) return;
        var bl = a === "x" ? b.x1 : b.y1, bh = a === "x" ? b.x2 : b.y2;
        [bl - 10, bh + 10].forEach(function (v) { if (inRange(v)) cands.push(v); });
      });
      // And a step either side of every boundary's border, so a turn can
      // be in the open ground between two boundaries rather than inside
      // one: nothing else offered the gap beside Private-Data.
      bounds.forEach(function (b) {
        var bl = a === "x" ? b.x1 : b.y1, bh = a === "x" ? b.x2 : b.y2;
        [bl - 12, bl + 12, bh - 12, bh + 12].forEach(function (v) { if (inRange(v)) cands.push(v); });
      });
      // A labeled edge also tries the turns that leave one piece long
      // enough to carry the label upright, with a little to spare.
      if (labelW) {
        [from + dir * (labelW + 4), to - dir * (labelW + 4)].forEach(function (v) { if (inRange(v)) cands.push(v); });
      }
      // Fewest nodes passed behind; then fewest names run through; then
      // fewest boundary borders crossed; then fewest borders run along;
      // then fewest middle pieces already on that line; then a piece the
      // label fits on; then nearest halfway.
      var lo = Math.min(c1, c2) - 4, hi = Math.max(c1, c2) + 4;
      function score(turn) {
        var n = 0, m = 0;
        boxes.forEach(function (b) {
          if (b.id === sNode.id() || b.id === tNode.id()) return;
          var k = (hits(b, a, from, turn, c1) ? 1 : 0) + (hits(b, c, c1, c2, turn) ? 1 : 0)
            + (hits(b, a, turn, to, c2) ? 1 : 0);
          if (b.name) m += k; else n += k;
        });
        var x = 0;
        bounds.forEach(function (b) {
          x += crossings(b, a, from, turn, c1) + crossings(b, c, c1, c2, turn) + crossings(b, a, turn, to, c2);
        });
        var r = 0;
        borders.forEach(function (b) {
          if (b.a === a && Math.abs(b.at - turn) < BORDER_NEAR
              && Math.min(Math.max(c1, c2), b.hi) - Math.max(Math.min(c1, c2), b.lo) >= 12) r++;
        });
        var crowd = 0;
        laid.forEach(function (l) {
          if (l.a === a && Math.abs(l.turn - turn) < TURN_APART && l.lo < hi && l.hi > lo) crowd++;
        });
        // Upright on a piece out of or into a node, the label needs the
        // piece to be nearly its width past the node; along the middle
        // piece it may overhang both corners.
        var fits = !labelW || Math.abs(turn - from) >= labelW - 2 || Math.abs(to - turn) >= labelW - 2
          || Math.abs(c2 - c1) >= labelW - 24;
        return { turn: turn, n: n, m: m, x: x, r: r, crowd: crowd, fits: fits, d: Math.abs(turn - mid) };
      }
      var best = null;
      cands.forEach(function (turn) {
        var got = score(turn);
        var even = best && got.n === best.n && got.m === best.m && got.x === best.x && got.r === best.r;
        if (!best || got.n < best.n
            || (got.n === best.n && got.m < best.m)
            || (got.n === best.n && got.m === best.m && got.x < best.x)
            || (got.n === best.n && got.m === best.m && got.x === best.x && got.r < best.r)
            || (even && got.crowd < best.crowd)
            || (even && got.crowd === best.crowd && got.fits && !best.fits)
            || (even && got.crowd === best.crowd && got.fits === best.fits && got.d < best.d)) best = got;
      });
      best.dir = dir;
      best.lo = lo;
      best.hi = hi;
      return best;
    }
    var plans = [], sides = {}, routes = {};
    cy.edges().forEach(function (e) {
      var sNode = e.source(), tNode = e.target();
      if (!sNode.length || !tNode.length || sNode.data("isGroup") || tNode.data("isGroup")
          || sNode.id() === tNode.id()) {
        routes[e.id()] = null;
        return;
      }
      var sp = sNode.position(), tp = tNode.position();
      // Which axis to leave along: whichever has room, and of those the
      // one whose route passes behind fewer nodes, then through fewer
      // names; on a tie the axis the layout ranked this edge along, or the
      // drawing's own direction.
      var preferred = EDGE_AXIS[e.id()] || P;
      var choice = null;
      [preferred, other(preferred)].forEach(function (a) {
        var gap = Math.abs(tp[a] - sp[a]) - half(sNode, a) - half(tNode, a);
        if (gap < FACE_GAP) return;
        var c = other(a);
        var got = plan(sNode, tNode, a, sp[c], tp[c], labelPx(e.data("label")));
        if (!choice || got.n < choice.n || (got.n === choice.n && got.m < choice.m)) {
          choice = { axis: a, n: got.n, m: got.m, dir: got.dir };
        }
      });
      if (!choice) { routes[e.id()] = null; return; }
      var axis = choice.axis, cross = other(axis), dir = choice.dir;
      var item = { e: e, s: sNode, t: tNode, axis: axis, cross: cross, dir: dir, offS: 0, offT: 0 };
      plans.push(item);
      var keyS = sNode.id() + "|" + axis + dir, keyT = tNode.id() + "|" + axis + (-dir);
      (sides[keyS] = sides[keyS] || []).push({ plan: item, role: "offS", node: sNode, at: tp[cross] });
      (sides[keyT] = sides[keyT] || []).push({ plan: item, role: "offT", node: tNode, at: sp[cross] });
    });
    Object.keys(sides).forEach(function (key) {
      var list = sides[key];
      if (list.length < 2) return;
      var node = list[0].node;
      var cross = list[0].plan.cross;
      if (!FANNED[SHAPES[node.data("entityType")] || "round-rectangle"]) return;
      var room = half(node, cross) - FAN_INSET;
      if (room <= 0) return;
      list.sort(function (a, b) { return a.at - b.at; });
      var step = Math.min(FAN_STEP, (2 * room) / (list.length - 1));
      list.forEach(function (item, i) { item.plan[item.role] = (i - (list.length - 1) / 2) * step; });
    });
    /* Where a line leaves or arrives: on the side, at its place in the
     * fan, given to Cytoscape outright. Left to `outside-to-node`, the end
     * was found on the ray from the center to the first turn, so a line
     * fanned off the middle of a side left from near the middle and
     * drifted to its place along the whole run: Card Servicing Service's
     * line to Customer Identity API on the onboarding drawing slanted
     * across three hundred and fifty pixels. */
    function portAt(n, a, sign, off) {
      if (!PORTED[SHAPES[n.data("entityType")] || "round-rectangle"]) return "outside-to-node";
      var out = sign * (half(n, a) + (Number(n.data("strokeWidth")) || 1) / 2);
      return (a === "x" ? out : off) + "px " + (a === "x" ? off : out) + "px";
    }
    // The name a straight piece along `a`, between u1 and u2 at `v`
    // across, runs through, if any.
    function nameOn(a, u1, u2, v) {
      for (var i = 0; i < boxes.length; i++) if (boxes[i].name && hits(boxes[i], a, u1, u2, v)) return boxes[i];
      return null;
    }
    function better(p, q) {
      return p.n < q.n || (p.n === q.n && (p.m < q.m || (p.m === q.m && (p.x < q.x || (p.x === q.x && p.r < q.r)))));
    }
    plans.forEach(function (item) {
      var sp = item.s.position(), tp = item.t.position();
      var a = item.axis, c = item.cross;
      var c1 = sp[c] + item.offS, c2 = tp[c] + item.offT;
      var labelW = labelPx(item.e.data("label"));
      var got = plan(item.s, item.t, a, c1, c2, labelW);
      /* A line out of a port, or into one, runs at the port's place along
       * the side whatever the turn, so where that place is under a name the
       * turn cannot help. On one line, "subscription azure-data-prod" was
       * wide enough to sit over the ingestion hub's top port, and the line
       * down into it struck the word. The port moves along its side: first
       * to where the line's other end is, which makes it straight, then past
       * the far end of the word, then back past the near end; never within
       * half a fan step of another port on that side, where the two lines
       * merged into one arrow; and takes the best of those places if the
       * route is better for it. The first better place was taken at first,
       * and a straight line that still ran through the word won on the
       * borders it crossed before the place past the word was tried. */
      var from = sp[a] + item.dir * half(item.s, a), to = tp[a] - item.dir * half(item.t, a);
      [["offS", item.s, sp, true], ["offT", item.t, tp, false]].forEach(function (end) {
        var node = end[1], p = end[2], first = end[3];
        if (!got.m || !PORTED[SHAPES[node.data("entityType")] || "round-rectangle"]) return;
        var word = first ? nameOn(a, from, got.turn, c1) : nameOn(a, got.turn, to, c2);
        if (!word) return;
        var room = half(node, c) - FAN_INSET;
        var wl = c === "x" ? word.x1 : word.y1, wh = c === "x" ? word.x2 : word.y2;
        var key = node.id() + "|" + a + (first ? item.dir : -item.dir);
        var others = (sides[key] || []).filter(function (en) { return en.plan !== item; })
          .map(function (en) { return p[c] + en.plan[en.role]; });
        var moved = null;
        [first ? c2 : c1, wh + NAME_CLEAR, wl - NAME_CLEAR].forEach(function (v) {
          if (Math.abs(v - p[c]) > room) return;
          if (others.some(function (o) { return Math.abs(o - v) < FAN_STEP / 2; })) return;
          var tried = plan(item.s, item.t, a, first ? v : c1, first ? c2 : v, labelW);
          if (better(tried, got)) { got = tried; moved = v; }
        });
        if (moved === null) return;
        if (first) c1 = moved; else c2 = moved;
        item[end[0]] = moved - p[c];
      });
      var turn = got.turn;
      laid.push({ a: a, turn: turn, lo: got.lo, hi: got.hi });
      var p1 = {}, p2 = {};
      p1[a] = turn; p1[c] = c1;
      p2[a] = turn; p2[c] = c2;
      routes[item.e.id()] = {
        points: Math.abs(p1[c] - p2[c]) < 0.5 ? [[p1.x, p1.y]] : [[p1.x, p1.y], [p2.x, p2.y]],
        sep: portAt(item.s, a, item.dir, item.offS), tep: portAt(item.t, a, -item.dir, item.offT),
      };
    });
    return routes;
  }

  /* A plan into Cytoscape: each edge's points as segment points, given
   * against the line between the two centers (how far along it, and how far
   * to its left), and its ends; an edge with no route a curve. */
  function writeRoutes(cy, routes) {
    cy.startBatch();
    cy.edges().forEach(function (e) {
      var r = routes[e.id()];
      e.data("sep", r ? r.sep : "outside-to-node");
      e.data("tep", r ? r.tep : "outside-to-node");
      e.toggleClass("free", !r);
      if (!r) return;
      var sp = e.source().position(), tp = e.target().position();
      var dx = tp.x - sp.x, dy = tp.y - sp.y;
      var len2 = dx * dx + dy * dy || 1, len = Math.sqrt(len2);
      var ws = [], ds = [];
      r.points.forEach(function (pt) {
        var vx = pt[0] - sp.x, vy = pt[1] - sp.y;
        ws.push(((vx * dx + vy * dy) / len2).toFixed(4));
        ds.push(((vy * dx - vx * dy) / len).toFixed(2));
      });
      e.data("segw", ws.join(" "));
      e.data("segd", ds.join(" "));
    });
    cy.endBatch();
  }

  /* ---- the grid router ----------------------------------------------------
   * The three pieces above turn a line once and let its run pass behind
   * whatever stands in the way, because dagre leaves no corridors. This is
   * the router the Python drawing has used since round thirty
   * (`terrane/draw/router.py`), which the fixtures hold this one equal to: the
   * corridors are a grid, a line along each side of every node a margin
   * out, along each side of every boundary, along the edges of every
   * boundary's name, and through every port; a piece of the grid through a
   * node is closed; and every edge is the cheapest way over that grid by A*,
   * where a bend costs a turn's worth, a border crossed of a boundary that
   * holds neither end costs a boundary's worth, a name run through costs
   * two turns', a piece beside a node costs by its length, and a piece
   * another edge already took costs a share, so two edges through one gap
   * take two lines. Runs that still share a corridor are nudged apart. An
   * edge the grid cannot carry, a port boxed in on every side, takes the
   * three pieces. What the three pieces could not clear on the product
   * drawings: 81 lines behind a box, 13 through a name.
   *
   * Deterministic the way the Python is: the grid is sorted coordinates,
   * the edges go in the payload's order, the queue breaks ties on the order
   * of insertion, and every step is the same arithmetic in the same order,
   * so the two land on the same points.
   */
  var GRID_MARGIN = 10;
  var GRID_BEND = 36;
  var GRID_CROSS = 48;
  var GRID_NAME = 80;
  var GRID_NEAR = 2;
  var GRID_SHARED = 14;
  /* A run along a boundary's border nearer than this reads as the border:
   * the corridor at the top edge of a name's box is four pixels inside its
   * boundary, and Tiered Architecture had twelve runs along borders there.
   * Such a run costs by its length, like a node's clearance. */
  var GRID_HUG_NEAR = 6;
  var GRID_HUG = 1;
  /* Above one the search runs straighter at the goal and settles for a
   * route a little dearer, a few times sooner. */
  var GRID_EPSILON = 1.3;
  var GRID_NUDGE = 7;
  var GRID_NUDGE_MAX = GRID_MARGIN - 3;
  // The four ways to move on the grid, as index steps: right, down, left, up.
  var GRID_STEPS = [[1, 0], [0, 1], [-1, 0], [0, -1]];

  // Strings in Python's order, which for the ids drawn is code unit order.
  function byString(a, b) { return a < b ? -1 : a > b ? 1 : 0; }

  /* The grid's lines, sorted, one of any within a hundredth of a pixel,
   * each snapped to the nearest 1024th. The app and the Python place a
   * node equal to the sixth decimal, not to the last bit, and a search
   * over a grid meets many routes of exactly equal cost: a difference in
   * the twelfth place chose between them, and Integration Architecture's
   * line from the lending API to the ledger queue ran a hundred pixels
   * apart in the two. Snapped, every coordinate is the same binary
   * fraction in both, and every length and cost summed from them is exact. */
  function gridDedupe(values) {
    var out = [];
    values.slice().sort(function (a, b) { return a - b; }).forEach(function (v) {
      if (!out.length || v - out[out.length - 1] > 0.01) out.push(v);
    });
    return out.map(function (v) { return Math.floor(v * 1024 + 0.5) / 1024; });
  }

  // The index of a coordinate the grid was built from.
  function gridIndex(values, v) {
    var lo = 0, hi = values.length - 1;
    while (lo <= hi) {
      var mid = (lo + hi) >> 1;
      if (Math.abs(values[mid] - v) <= 0.011) return mid;
      if (values[mid] < v) lo = mid + 1; else hi = mid - 1;
    }
    throw new Error("not on the grid: " + v);
  }

  function bisectRight(a, x) {
    var lo = 0, hi = a.length;
    while (lo < hi) { var mid = (lo + hi) >> 1; if (x < a[mid]) hi = mid; else lo = mid + 1; }
    return lo;
  }

  function bisectLeft(a, x) {
    var lo = 0, hi = a.length;
    while (lo < hi) { var mid = (lo + hi) >> 1; if (a[mid] < x) lo = mid + 1; else hi = mid; }
    return lo;
  }

  /* The pieces whose inside crosses the box's inside, by the index ranges
   * the box spans: a horizontal piece i * ny + j runs from xs[i] to
   * xs[i + 1] at ys[j], a vertical one from ys[j] to ys[j + 1] at xs[i]. */
  function gridPiecesIn(xs, ys, box, onH, onV) {
    var ny = ys.length, i, j;
    var loJ = bisectRight(ys, box[1] + 0.011), hiJ = bisectLeft(ys, box[3] - 0.011);
    var loI = Math.max(0, bisectRight(xs, box[0] + 0.011) - 1);
    var hiI = Math.min(xs.length - 1, bisectLeft(xs, box[2] - 0.011));
    for (j = loJ; j < hiJ; j++) for (i = loI; i < hiI; i++) onH(i * ny + j);
    var loI2 = bisectRight(xs, box[0] + 0.011), hiI2 = bisectLeft(xs, box[2] - 0.011);
    var loJ2 = Math.max(0, bisectRight(ys, box[1] + 0.011) - 1);
    var hiJ2 = Math.min(ys.length - 1, bisectLeft(ys, box[3] - 0.011));
    for (i = loI2; i < hiI2; i++) for (j = loJ2; j < hiJ2; j++) onV(i * ny + j);
  }

  // The grid line just below `v` when `v` is strictly between two; else -1.
  function gridBetween(values, v) {
    for (var i = 0; i < values.length - 1; i++) {
      if (values[i] + 0.011 < v && v < values[i + 1] - 0.011) return i;
    }
    return -1;
  }

  function makeGrid(xs, ys, bodies, clearances, borders, soft) {
    var nx = xs.length, ny = ys.length, n = nx * ny;
    var g = { xs: xs, ys: ys, nx: nx, ny: ny,
              closedH: new Uint8Array(n), closedV: new Uint8Array(n),
              nearH: new Int32Array(n), nearV: new Int32Array(n),
              softH: new Int32Array(n), softV: new Int32Array(n),
              usedH: new Int32Array(n), usedV: new Int32Array(n),
              hugH: new Int32Array(n), hugV: new Int32Array(n),
              crossH: {}, crossV: {},
              best: new Float64Array(n * 4).fill(Infinity), came: new Int32Array(n * 4).fill(-1) };
    bodies.forEach(function (b) {
      gridPiecesIn(xs, ys, b, function (k) { g.closedH[k] = 1; }, function (k) { g.closedV[k] = 1; });
    });
    clearances.forEach(function (b) {
      gridPiecesIn(xs, ys, b, function (k) { g.nearH[k] += 1; }, function (k) { g.nearV[k] += 1; });
    });
    borders.forEach(function (entry) {
      var gid = entry[0], b = entry[1];
      var js = [], is = [];
      ys.forEach(function (y, j) { if (b[1] - 0.011 <= y && y <= b[3] + 0.011) js.push(j); });
      xs.forEach(function (x, i) { if (b[0] - 0.011 <= x && x <= b[2] + 0.011) is.push(i); });
      [b[0], b[2]].forEach(function (x) {
        var i = gridBetween(xs, x);
        if (i < 0) return;
        js.forEach(function (j) { (g.crossH[i * ny + j] = g.crossH[i * ny + j] || []).push(gid); });
      });
      [b[1], b[3]].forEach(function (y) {
        var j = gridBetween(ys, y);
        if (j < 0) return;
        is.forEach(function (i) { (g.crossV[i * ny + j] = g.crossV[i * ny + j] || []).push(gid); });
      });
    });
    soft.forEach(function (b) {
      gridPiecesIn(xs, ys, b, function (k) { g.softH[k] += 1; }, function (k) { g.softV[k] += 1; });
    });
    // A piece along a boundary's border, nearer it than GRID_HUG_NEAR, over
    // the border's own span.
    borders.forEach(function (entry) {
      var b = entry[1], i, j;
      [b[1], b[3]].forEach(function (y) {
        for (j = 0; j < ny; j++) {
          if (Math.abs(ys[j] - y) >= GRID_HUG_NEAR) continue;
          for (i = 0; i < nx - 1; i++) if (xs[i + 1] > b[0] + 0.011 && xs[i] < b[2] - 0.011) g.hugH[i * ny + j] += 1;
        }
      });
      [b[0], b[2]].forEach(function (x) {
        for (i = 0; i < nx; i++) {
          if (Math.abs(xs[i] - x) >= GRID_HUG_NEAR) continue;
          for (j = 0; j < ny - 1; j++) if (ys[j + 1] > b[1] + 0.011 && ys[j] < b[3] - 0.011) g.hugV[i * ny + j] += 1;
        }
      });
    });
    return g;
  }

  // Whether the piece out of cell (i, j) in direction `d` is a wall or the
  // edge of the grid.
  function gridPieceClosed(g, i, j, d) {
    var ni = i + GRID_STEPS[d][0], nj = j + GRID_STEPS[d][1];
    if (ni < 0 || ni >= g.nx || nj < 0 || nj >= g.ny) return true;
    if (GRID_STEPS[d][0]) return g.closedH[Math.min(i, ni) * g.ny + j] === 1;
    return g.closedV[i * g.ny + Math.min(j, nj)] === 1;
  }

  // The queue's order: estimate, then cost so far, then insertion.
  function heapLess(a, b) {
    return a[0] < b[0] || (a[0] === b[0] && (a[1] < b[1] || (a[1] === b[1] && a[2] < b[2])));
  }

  function heapPush(heap, item) {
    heap.push(item);
    var i = heap.length - 1;
    while (i > 0) {
      var p = (i - 1) >> 1;
      if (!heapLess(heap[i], heap[p])) break;
      var t = heap[i]; heap[i] = heap[p]; heap[p] = t;
      i = p;
    }
  }

  function heapPop(heap) {
    var top = heap[0], last = heap.pop();
    if (heap.length) {
      heap[0] = last;
      var i = 0;
      for (;;) {
        var l = 2 * i + 1, r = l + 1, m = i;
        if (l < heap.length && heapLess(heap[l], heap[m])) m = l;
        if (r < heap.length && heapLess(heap[r], heap[m])) m = r;
        if (m === i) break;
        var t = heap[i]; heap[i] = heap[m]; heap[m] = t;
        i = m;
      }
    }
    return top;
  }

  /* The cheapest route from (si, sj) leaving in `outDir` to (gi, gj)
   * arriving in `inDir`, as a list of cells, or null. `outside` holds the
   * boundaries the edge crosses for free, one of its ends being inside;
   * `win` is the index box the search may use. */
  function gridSearch(g, si, sj, outDir, gi, gj, inDir, outside, win) {
    var xs = g.xs, ys = g.ys, nx = g.nx, ny = g.ny;
    var gx = xs[gi], gy = ys[gj];
    var loI = win ? win[0] : 0, loJ = win ? win[1] : 0, hiI = win ? win[2] : nx - 1, hiJ = win ? win[3] : ny - 1;
    // What is left at least: the distance, and the turns a route moving in
    // `d` must still make to arrive moving in `inDir`.
    function h(x, y, d) {
      var dx = gx - x, dy = gy - y, bends = 0, toward;
      if (Math.abs(dx) > 0.01 && Math.abs(dy) > 0.01) {
        bends = 1;
        if ((d === 0 && dx < 0) || (d === 2 && dx > 0) || (d === 1 && dy < 0) || (d === 3 && dy > 0)) bends = 2;
      } else if (Math.abs(dx) > 0.01) {
        toward = dx > 0 ? 0 : 2;
        bends = d === toward ? 0 : d === (toward + 2) % 4 ? 2 : 1;
      } else if (Math.abs(dy) > 0.01) {
        toward = dy > 0 ? 1 : 3;
        bends = d === toward ? 0 : d === (toward + 2) % 4 ? 2 : 1;
      }
      if (bends === 0 && d !== inDir) bends = 2;
      return (Math.abs(dx) + Math.abs(dy) + GRID_BEND * bends) * GRID_EPSILON;
    }
    var best = g.best, came = g.came, touched = [];
    function reset() {
      touched.forEach(function (k) { best[k] = Infinity; came[k] = -1; });
    }
    // A port whose straight stub is a wall is left whichever way is open.
    var outDirs = gridPieceClosed(g, si, sj, outDir) ? [0, 1, 2, 3] : [outDir];
    var goalKeys = {};
    if (gridPieceClosed(g, gi, gj, (inDir + 2) % 4)) {
      for (var gd = 0; gd < 4; gd++) goalKeys[(gi * ny + gj) * 4 + gd] = true;
    } else {
      goalKeys[(gi * ny + gj) * 4 + inDir] = true;
    }
    var heap = [], counter = 0;
    outDirs.forEach(function (d) {
      var first = (si * ny + sj) * 4 + d;
      best[first] = 0;
      touched.push(first);
      counter += 1;
      heapPush(heap, [h(xs[si], ys[sj], d), 0, counter, first]);
    });
    while (heap.length) {
      var top = heapPop(heap), cost0 = top[1], key = top[3];
      if (cost0 > best[key]) continue;
      if (goalKeys[key]) {
        var path = [];
        for (var cur = key; cur !== -1; cur = came[cur]) {
          var c = Math.floor(cur / 4);
          path.push([Math.floor(c / ny), c % ny]);
        }
        path.reverse();
        reset();
        return path;
      }
      var cell = Math.floor(key / 4), d0 = key % 4;
      var i = Math.floor(cell / ny), j = cell % ny;
      for (var nd = 0; nd < 4; nd++) {
        var di = GRID_STEPS[nd][0], dj = GRID_STEPS[nd][1];
        var ni = i + di, nj = j + dj;
        if (ni < loI || ni > hiI || nj < loJ || nj > hiJ) continue;
        var piece, length, near, crossed, shared, soft, hug;
        if (di) {
          piece = (di > 0 ? i : ni) * ny + j;
          if (g.closedH[piece]) continue;
          length = Math.abs(xs[ni] - xs[i]);
          near = g.nearH[piece]; crossed = g.crossH[piece]; shared = g.usedH[piece]; soft = g.softH[piece];
          hug = g.hugH[piece];
        } else {
          piece = i * ny + (dj > 0 ? j : nj);
          if (g.closedV[piece]) continue;
          length = Math.abs(ys[nj] - ys[j]);
          near = g.nearV[piece]; crossed = g.crossV[piece]; shared = g.usedV[piece]; soft = g.softV[piece];
          hug = g.hugV[piece];
        }
        var cost = cost0 + length;
        if (nd !== d0) cost += GRID_BEND;
        if (near) cost += GRID_NEAR * length * near;
        if (crossed) {
          for (var q = 0; q < crossed.length; q++) if (!outside[crossed[q]]) cost += GRID_CROSS;
        }
        if (shared) cost += GRID_SHARED * shared;
        if (soft) cost += GRID_NAME * soft;
        if (hug) cost += GRID_HUG * length * hug;
        var nkey = (ni * ny + nj) * 4 + nd;
        if (cost < best[nkey]) {
          if (best[nkey] === Infinity) touched.push(nkey);
          best[nkey] = cost;
          came[nkey] = key;
          counter += 1;
          heapPush(heap, [cost + h(xs[ni], ys[nj], nd), cost, counter, nkey]);
        }
      }
    }
    reset();
    return null;
  }

  // The index box around two grid points, `reach` pixels wider each way.
  function gridWindow(g, a, b, reach) {
    var xs = g.xs, ys = g.ys;
    var xLo = Math.min(xs[a[0]], xs[b[0]]) - reach, xHi = Math.max(xs[a[0]], xs[b[0]]) + reach;
    var yLo = Math.min(ys[a[1]], ys[b[1]]) - reach, yHi = Math.max(ys[a[1]], ys[b[1]]) + reach;
    var loI = 0, hiI = xs.length - 1, loJ = 0, hiJ = ys.length - 1, i, j;
    for (i = 0; i < xs.length; i++) if (xs[i] <= xLo) loI = i;
    for (i = xs.length - 1; i >= 0; i--) if (xs[i] >= xHi) hiI = i;
    for (j = 0; j < ys.length; j++) if (ys[j] <= yLo) loJ = j;
    for (j = ys.length - 1; j >= 0; j--) if (ys[j] >= yHi) hiJ = j;
    return [loI, loJ, hiI, hiJ];
  }

  // The polyline with its straight runs joined, the two ends kept.
  function gridCorners(points) {
    var out = [];
    points.forEach(function (p) {
      var last = out[out.length - 1];
      if (last && Math.abs(last[0] - p[0]) < 0.01 && Math.abs(last[1] - p[1]) < 0.01) return;
      if (out.length >= 2) {
        var a = out[out.length - 2], b = last;
        if ((Math.abs(a[0] - b[0]) < 0.01 && Math.abs(b[0] - p[0]) < 0.01)
            || (Math.abs(a[1] - b[1]) < 0.01 && Math.abs(b[1] - p[1]) < 0.01)) {
          out[out.length - 1] = p;
          return;
        }
      }
      out.push(p);
    });
    return out;
  }

  /* A port inside a boundary's name, moved along its side past the far end
   * of the word, else back past the near end, else left. */
  function gridOffTheName(port, axis, names, box) {
    for (var k = 0; k < names.length; k++) {
      var nm = names[k];
      if (!(nm[0] < port[0] && port[0] < nm[2] && nm[1] < port[1] && port[1] < nm[3])) continue;
      var lo, hi, v, cands, c;
      if (axis === "y") {
        lo = box[0] + FAN_INSET; hi = box[2] - FAN_INSET;
        cands = [nm[2] + NAME_CLEAR, nm[0] - NAME_CLEAR];
        for (c = 0; c < 2; c++) { v = cands[c]; if (lo <= v && v <= hi) return [v, port[1]]; }
      } else {
        lo = box[1] + FAN_INSET; hi = box[3] - FAN_INSET;
        cands = [nm[3] + NAME_CLEAR, nm[1] - NAME_CLEAR];
        for (c = 0; c < 2; c++) { v = cands[c]; if (lo <= v && v <= hi) return [port[0], v]; }
      }
    }
    return port;
  }

  // Whether a run moved by its shift would lie in a name's box.
  function gridIntoAName(bundle, shifts, vertical, names) {
    for (var r = 0; r < bundle.length; r++) {
      if (shifts[r] === 0) continue;
      var run = bundle[r], f = run.fixed + shifts[r];
      for (var k = 0; k < names.length; k++) {
        var nm = names[k];
        if (vertical ? (nm[0] < f && f < nm[2] && run.lo < nm[3] && run.hi > nm[1])
            : (nm[1] < f && f < nm[3] && run.lo < nm[2] && run.hi > nm[0])) return true;
      }
    }
    return false;
  }

  /* Runs of different edges that share a corridor, moved apart a few pixels
   * each, the stubs out of the ports left alone; the order in a bundle
   * follows where each run came from, so the bundle does not braid. A
   * bundle the spread would move into a name is spread to one side, away
   * from it, or not at all: three lines in the corridor at the edge of
   * "Policy" were spread seven pixels each way, and one ran through it. */
  function gridNudge(routes, names) {
    var runs = [];
    Object.keys(routes).forEach(function (id) {
      var route = routes[id];
      if (!route || route.points.length < 4) return;
      var pts = route.points;
      for (var k = 1; k < pts.length - 2; k++) {
        var a = pts[k], b = pts[k + 1];
        var vertical = Math.abs(a[0] - b[0]) < 0.01;
        var lo = vertical ? Math.min(a[1], b[1]) : Math.min(a[0], b[0]);
        var hi = vertical ? Math.max(a[1], b[1]) : Math.max(a[0], b[0]);
        var before = vertical ? pts[k - 1][0] : pts[k - 1][1];
        var after = vertical ? pts[k + 2][0] : pts[k + 2][1];
        runs.push({ route: route, k: k, vertical: vertical, fixed: vertical ? a[0] : a[1], lo: lo, hi: hi,
                    order: (before + after) / 2, edge: route.id });
      }
    });
    [true, false].forEach(function (vertical) {
      var pool = runs.filter(function (r) { return r.vertical === vertical; });
      pool.sort(function (a, b) { return (a.fixed - b.fixed) || (a.lo - b.lo) || byString(a.edge, b.edge); });
      var i = 0;
      while (i < pool.length) {
        var bundle = [pool[i]], top = pool[i].hi, j = i + 1;
        while (j < pool.length && Math.abs(pool[j].fixed - pool[i].fixed) < 0.01 && pool[j].lo < top - 0.01) {
          bundle.push(pool[j]);
          top = Math.max(top, pool[j].hi);
          j += 1;
        }
        i = j;
        if (bundle.length < 2) continue;
        bundle.sort(function (a, b) { return (a.order - b.order) || byString(a.edge, b.edge); });
        var n = bundle.length, step = Math.min(GRID_NUDGE, 2 * GRID_NUDGE_MAX / (n - 1)), pos;
        var shifts = [];
        for (pos = 0; pos < n; pos++) shifts.push((pos - (n - 1) / 2) * step);
        if (gridIntoAName(bundle, shifts, vertical, names)) {
          var side = Math.min(GRID_NUDGE, GRID_NUDGE_MAX / (n - 1)), away = [], toward = [], none = [];
          for (pos = 0; pos < n; pos++) {
            away.push((pos - (n - 1)) * side);
            toward.push(pos * side);
            none.push(0);
          }
          shifts = [away, toward, none].filter(function (alt) {
            return !gridIntoAName(bundle, alt, vertical, names);
          })[0] || none;
        }
        bundle.forEach(function (run, at) {
          var shift = shifts[at], pts = run.route.points;
          [run.k, run.k + 1].forEach(function (idx) {
            pts[idx] = vertical ? [pts[idx][0] + shift, pts[idx][1]] : [pts[idx][0], pts[idx][1] + shift];
          });
        });
      }
    });
  }

  /* Every edge between two leaves routed round the others: its corners and
   * its two ends, null for an edge with no two leaves to join, undefined for
   * one the grid could not carry. `route_grid` in the Python, step for step. */
  function planGrid(cy, down) {
    var P = down ? "y" : "x";
    function other(a) { return a === "x" ? "y" : "x"; }
    function coord(pt, a) { return a === "x" ? pt[0] : pt[1]; }
    var order = [], node = {}, centers = {}, boxes = {}, clearance = {}, enclosing = {};
    cy.nodes().forEach(function (n) {
      if (n.data("isGroup")) return;
      var p = n.position(), bb = n.boundingBox({ includeLabels: false, includeOverlays: false });
      var id = n.id();
      order.push(id);
      node[id] = n;
      centers[id] = [p.x, p.y];
      boxes[id] = [bb.x1, bb.y1, bb.x2, bb.y2];
      clearance[id] = [bb.x1 - GRID_MARGIN, bb.y1 - GRID_MARGIN, bb.x2 + GRID_MARGIN, bb.y2 + GRID_MARGIN];
      // The boundaries that hold the leaf, which a line to it crosses free.
      var held = {};
      n.ancestors().forEach(function (g) { held[g.id()] = true; });
      enclosing[id] = held;
    });
    function half(id, a) { var b = boxes[id]; return (a === "x" ? b[2] - b[0] : b[3] - b[1]) / 2; }
    // Whether a point is inside a third node's clearance: a gap in a stack
    // no line can enter.
    function boxed(id, pt, partner) {
      for (var k = 0; k < order.length; k++) {
        var lid = order[k];
        if (lid === id || lid === partner) continue;
        var b = clearance[lid];
        if (b[0] < pt[0] && pt[0] < b[2] && b[1] < pt[1] && pt[1] < b[3]) return true;
      }
      return false;
    }
    // The port a margin out from a side, or halfway across a gap too
    // narrow for two margins.
    function portOf(id, a, sign, partner) {
      var c = centers[id];
      var gap = Math.abs(coord(centers[partner], a) - coord(c, a)) - half(id, a) - half(partner, a);
      var stub = gap >= 2 * GRID_MARGIN ? GRID_MARGIN : Math.max(1, gap / 2);
      var out = coord(c, a) + sign * (half(id, a) + stub);
      return a === "x" ? [out, c[1]] : [c[0], out];
    }
    // The side of a node that faces its partner: along the ranked axis
    // where there is room between the two, else the other; never a side
    // whose port sits in someone else's clearance, when there is a choice.
    function choose(id, partner, preferred) {
      var here = centers[id], there = centers[partner];
      var options = [preferred, other(preferred)].map(function (a) {
        return { a: a, s: coord(there, a) >= coord(here, a) ? 1 : -1,
                 gap: Math.abs(coord(there, a) - coord(here, a)) - half(id, a) - half(partner, a) };
      });
      var usable = options.filter(function (o) { return o.gap >= FACE_GAP; });
      if (!usable.length) usable = options.slice().sort(function (x, y) { return y.gap - x.gap; });
      for (var k = 0; k < usable.length; k++) {
        if (!boxed(id, portOf(id, usable[k].a, usable[k].s, partner), partner)) return usable[k];
      }
      return usable[0];
    }

    var plans = [], routes = {};
    cy.edges().forEach(function (e) {
      var s = e.source(), t = e.target();
      if (!s.length || !t.length || s.data("isGroup") || t.data("isGroup") || s.id() === t.id()) {
        routes[e.id()] = null;
        return;
      }
      var preferred = EDGE_AXIS[e.id()] || P;
      var cs = choose(s.id(), t.id(), preferred), ct = choose(t.id(), s.id(), preferred);
      plans.push({ id: e.id(), s: s.id(), t: t.id(), axis: cs.a, dir: cs.s, tAxis: ct.a, tSign: ct.s,
                   offS: 0, offT: 0 });
    });

    // The ports fanned along each side, in the order of where they go.
    var sides = new Map();
    function onSide(key, entry) {
      if (!sides.has(key)) sides.set(key, []);
      sides.get(key).push(entry);
    }
    plans.forEach(function (plan) {
      onSide(plan.s + "|" + plan.axis + plan.dir,
             { plan: plan, role: "offS", id: plan.s, axis: plan.axis, at: coord(centers[plan.t], other(plan.axis)) });
      onSide(plan.t + "|" + plan.tAxis + plan.tSign,
             { plan: plan, role: "offT", id: plan.t, axis: plan.tAxis, at: coord(centers[plan.s], other(plan.tAxis)) });
    });
    sides.forEach(function (list) {
      if (list.length < 2) return;
      var id = list[0].id, cross = other(list[0].axis);
      if (!FANNED[SHAPES[node[id].data("entityType")] || "round-rectangle"]) return;
      var room = half(id, cross) - FAN_INSET;
      if (room <= 0) return;
      list.sort(function (x, y) { return (x.at - y.at) || byString(x.plan.id, y.plan.id); });
      var step = Math.min(FAN_STEP, (2 * room) / (list.length - 1));
      list.forEach(function (entry, i) { entry.plan[entry.role] = (i - (list.length - 1) / 2) * step; });
    });

    // The grid: the clearances' sides, a margin either side of every
    // boundary's border, the edges of every name, and the ports.
    var xs = [], ys = [], borders = [], names = [];
    order.forEach(function (id) {
      var b = clearance[id];
      xs.push(b[0], b[2]);
      ys.push(b[1], b[3]);
    });
    cy.nodes().forEach(function (n) {
      if (!n.data("isGroup")) return;
      var bb = n.boundingBox({ includeLabels: false, includeOverlays: false });
      var gb = [bb.x1, bb.y1, bb.x2, bb.y2];
      borders.push([n.id(), gb]);
      xs.push(gb[0] - GRID_MARGIN, gb[0] + GRID_MARGIN, gb[2] - GRID_MARGIN, gb[2] + GRID_MARGIN);
      ys.push(gb[1] - GRID_MARGIN, gb[1] + GRID_MARGIN, gb[3] - GRID_MARGIN, gb[3] + GRID_MARGIN);
      var word = nameWord(bb, n.data("label"));
      names.push(word);
      xs.push(word[0], word[2]);
      ys.push(word[1], word[3]);
    });
    plans.forEach(function (plan) {
      [[plan.s, plan.t, "offS", plan.axis, plan.dir], [plan.t, plan.s, "offT", plan.tAxis, plan.tSign]]
        .forEach(function (end) {
          var id = end[0], role = end[2], a = end[3];
          var port = portOf(id, a, end[4], end[1]);
          port = a === "x" ? [port[0], port[1] + plan[role]] : [port[0] + plan[role], port[1]];
          var moved = gridOffTheName(port, a, names, boxes[id]);
          if (moved !== port) {
            port = moved;
            plan[role] = a === "x" ? port[1] - centers[id][1] : port[0] - centers[id][0];
          }
          plan[role + "Port"] = port;
          xs.push(port[0]);
          ys.push(port[1]);
        });
    });
    if (xs.length && ys.length) {
      var x0 = Math.min.apply(null, xs), x9 = Math.max.apply(null, xs);
      var y0 = Math.min.apply(null, ys), y9 = Math.max.apply(null, ys);
      xs.push(x0 - 2 * GRID_MARGIN, x9 + 2 * GRID_MARGIN);
      ys.push(y0 - 2 * GRID_MARGIN, y9 + 2 * GRID_MARGIN);
    }
    var grid = makeGrid(gridDedupe(xs), gridDedupe(ys), order.map(function (id) { return boxes[id]; }),
                        order.map(function (id) { return clearance[id]; }), borders, names);

    plans.forEach(function (plan) {
      var start = plan.offSPort, goal = plan.offTPort;
      var si = gridIndex(grid.xs, start[0]), sj = gridIndex(grid.ys, start[1]);
      var gi = gridIndex(grid.xs, goal[0]), gj = gridIndex(grid.ys, goal[1]);
      var outDir = plan.axis === "x" ? (plan.dir > 0 ? 0 : 2) : (plan.dir > 0 ? 1 : 3);
      // Arriving squarely is moving into the target's side.
      var inDir = plan.tAxis === "x" ? (plan.tSign > 0 ? 2 : 0) : (plan.tSign > 0 ? 3 : 1);
      var outside = {};
      Object.keys(enclosing[plan.s]).forEach(function (g) { outside[g] = true; });
      Object.keys(enclosing[plan.t]).forEach(function (g) { outside[g] = true; });
      // Near first, the whole grid only when nothing near will do.
      var path = gridSearch(grid, si, sj, outDir, gi, gj, inDir, outside, gridWindow(grid, [si, sj], [gi, gj], 240))
        || gridSearch(grid, si, sj, outDir, gi, gj, inDir, outside, null);
      if (!path) { routes[plan.id] = undefined; return; }
      for (var k = 0; k + 1 < path.length; k++) {
        var p = path[k], q = path[k + 1];
        if (p[0] !== q[0]) grid.usedH[Math.min(p[0], q[0]) * grid.ny + p[1]] += 1;
        else grid.usedV[p[0] * grid.ny + Math.min(p[1], q[1])] += 1;
      }
      routes[plan.id] = { id: plan.id, plan: plan,
                          points: gridCorners(path.map(function (cell) { return [grid.xs[cell[0]], grid.ys[cell[1]]]; })) };
    });
    gridNudge(routes, names);
    // The ends, on the node's side at the port's place, for a straight side.
    function pinned(id, a, sign, port) {
      var n = node[id];
      if (!PORTED[SHAPES[n.data("entityType")] || "round-rectangle"]) return "outside-to-node";
      var out = sign * ((a === "x" ? n.width() : n.height()) / 2 + (Number(n.data("strokeWidth")) || 1) / 2);
      var off = a === "x" ? port[1] - centers[id][1] : port[0] - centers[id][0];
      return (a === "x" ? out : off) + "px " + (a === "x" ? off : out) + "px";
    }
    Object.keys(routes).forEach(function (id) {
      var r = routes[id];
      if (!r) return;
      var plan = r.plan;
      r.sep = pinned(plan.s, plan.axis, plan.dir, r.points[0]);
      r.tep = pinned(plan.t, plan.tAxis, plan.tSign, r.points[r.points.length - 1]);
    });
    return routes;
  }

  /* A layered drawing's lines: the grid's, and the three pieces for an edge
   * the grid could not carry; the three pieces for all of them if the grid
   * failed outright, which it should not, since a drawing with its lines
   * missing is worse than one with its lines behind a box. */
  function routeDrawing(cy, down) {
    var routes = null, pieces = null;
    try {
      routes = planGrid(cy, down);
    } catch (err) {
      if (window.console) console.warn("grid router:", err);
    }
    if (!routes) {
      writeRoutes(cy, planPieces(cy, down));
      return;
    }
    Object.keys(routes).forEach(function (id) {
      if (routes[id] !== undefined) return;
      if (!pieces) pieces = planPieces(cy, down);
      routes[id] = pieces[id];
    });
    writeRoutes(cy, routes);
  }

  /* ---- edge label placement ----------------------------------------------
   * A label belongs on its own line. The first version slid a label up to
   * forty-eight pixels off its edge to find clear ground, and a label that
   * far from its line was read as belonging to whichever line it was nearest,
   * or to none. Now a label sits on the run of its edge that holds the
   * midpoint: at the midpoint, or slid along that run, never off it. A label
   * with no clear spot on its own line shows nothing until hover, which is
   * better than a smear. Two edges between the same two nodes carrying the
   * same word say it once. Sizes are estimated from the 9.5px monospace face
   * rather than measured, which is within a pixel or two and a hundred times
   * cheaper.
   *
   * Above a budget of labeled edges the labels come off altogether, unless
   * the Labels button says otherwise. A landscape reads as lines; the
   * protocol of any one of them is a hover away.
   */
  var LABEL_CHAR = 5.8;
  var LABEL_H = 15;
  function labelPx(text) { var t = String(text || ""); return t ? t.length * LABEL_CHAR + 8 : 0; }
  /* Breathing room around a placed label: a label touching a node reads as
   * part of the node. */
  var LABEL_GAP = 4;
  /* And a little more from other labels, each already in its own card. */
  var LABEL_APART = 6;
  /* How far along a run a label may slide from where it started, in order.
   * Ten pixels a step near the start: the gap between two stacked nodes is
   * twenty-six, and a coarser ladder stepped over it. The steps widen with
   * distance, so a long run between boundaries is searched to its ends. */
  var LABEL_SLIDES = [0];
  [10, 20, 30, 42, 56, 72, 90, 110, 134, 162, 194, 230, 270, 316].forEach(function (d) {
    LABEL_SLIDES.push(d, -d);
  });
  /* A run shorter than this is an elbow, not a place to put anything. */
  var LABEL_RUN_MIN = 24;
  /* A label may reach this far past the end of its run, onto the corner of
   * the same edge. Past that it reads as beside the next run, not on it. */
  var LABEL_OVERHANG = 16;
  /* Past this many labeled connections the drawing is a landscape and the
   * labels are off unless asked for. The diagrams that read well with every
   * label on all carry fewer than thirty. */
  var LABEL_BUDGET = 36;

  function overlaps(a, b) {
    return !(a.x2 < b.x1 || b.x2 < a.x1 || a.y2 < b.y1 || b.y2 < a.y1);
  }

  /* The straight pieces of an edge as drawn. Cytoscape keeps the rendered
   * path in a private scratch; when that is missing the chord from end to
   * end is the one piece. */
  function segmentsOf(e) {
    // The path is computed lazily; asking for the midpoint computes it, so
    // what is read below is the edge as it will be drawn, not as it was.
    e.midpoint();
    var pts = null;
    try { pts = e._private.rscratch.allpts; } catch (err) { pts = null; }
    var segs = [];
    if (pts && pts.length >= 4) {
      for (var i = 0; i + 3 < pts.length; i += 2) {
        var ax = pts[i], ay = pts[i + 1], bx = pts[i + 2], by = pts[i + 3];
        var len = Math.hypot(bx - ax, by - ay);
        if (len >= 1) segs.push({ ax: ax, ay: ay, bx: bx, by: by, len: len, ux: (bx - ax) / len, uy: (by - ay) / len });
      }
    }
    if (!segs.length) {
      var s = e.sourceEndpoint(), g = e.targetEndpoint();
      var chord = Math.hypot(g.x - s.x, g.y - s.y) || 1;
      segs.push({ ax: s.x, ay: s.y, bx: g.x, by: g.y, len: chord, ux: (g.x - s.x) / chord, uy: (g.y - s.y) / chord });
    }
    return segs;
  }

  /* The runs of an edge a label may sit on, each with a point to hang it
   * from: the midpoint for the run that holds it, first; then the middle
   * of the others, longest first. A label moved to another run of its own
   * edge is still on its own line, which a label moved off the midpoint
   * into open space was not. */
  function edgeRuns(e, segs) {
    var mid = e.midpoint();
    var holder = null, holderT = 0.5, best = Infinity;
    segs.forEach(function (r) {
      var t = ((mid.x - r.ax) * (r.bx - r.ax) + (mid.y - r.ay) * (r.by - r.ay)) / (r.len * r.len);
      t = Math.max(0, Math.min(1, t));
      var d = Math.hypot(mid.x - (r.ax + t * (r.bx - r.ax)), mid.y - (r.ay + t * (r.by - r.ay)));
      if (d <= 6 && d < best) { best = d; holder = r; holderT = t; }
    });
    if (!holder) { holder = segs[0]; holderT = 0.5; mid = { x: (holder.ax + holder.bx) / 2, y: (holder.ay + holder.by) / 2 }; }
    var others = segs.filter(function (r) { return r !== holder && r.len >= LABEL_RUN_MIN; })
      .sort(function (a, b) { return b.len - a.len; });
    return [holder].concat(others).map(function (r) {
      var isMid = r === holder;
      var t = isMid ? holderT : 0.5;
      return { x: isMid ? mid.x : (r.ax + r.bx) / 2, y: isMid ? mid.y : (r.ay + r.by) / 2,
               ux: r.ux, uy: r.uy, back: t * r.len, ahead: (1 - t) * r.len, mid: isMid };
    });
  }

  /* Whether a straight piece passes through a box: Liang-Barsky clipping
   * of the piece against the box, true when anything of it is left. */
  function pieceCrosses(box, r) {
    var t0 = 0, t1 = 1, dx = r.bx - r.ax, dy = r.by - r.ay;
    var p = [-dx, dx, -dy, dy];
    var q = [r.ax - box.x1, box.x2 - r.ax, r.ay - box.y1, box.y2 - r.ay];
    for (var i = 0; i < 4; i++) {
      if (p[i] === 0) {
        if (q[i] < 0) return false;
      } else {
        var t = q[i] / p[i];
        if (p[i] < 0) { if (t > t1) return false; if (t > t0) t0 = t; }
        else { if (t < t0) return false; if (t < t1) t1 = t; }
      }
    }
    return true;
  }

  /* Whether the stretch of a run from `c - along` to `c + along` lies on a
   * piece of some other edge: parallel, within three pixels, overlapping
   * along the line. A label on such a stretch would belong to both. */
  function sharedStretch(cx, cyy, ux, uy, along, own, pieces) {
    for (var i = 0; i < pieces.length; i++) {
      var p = pieces[i];
      if (p.edge === own) continue;
      var r = p.seg;
      if (Math.abs(ux * r.uy - uy * r.ux) > 0.08) continue;
      // Perpendicular distance from the candidate's center to the piece's line.
      var dist = Math.abs((r.ax - cx) * r.uy - (r.ay - cyy) * r.ux);
      if (dist > 3) continue;
      var t1 = (r.ax - cx) * ux + (r.ay - cyy) * uy, t2 = (r.bx - cx) * ux + (r.by - cyy) * uy;
      if (Math.max(Math.min(t1, t2), -along) < Math.min(Math.max(t1, t2), along)) return true;
    }
    return false;
  }

  /* ---- placement --------------------------------------------------------
   * For each label, in order of length: every run of its edge, first upright
   * and then, on a run that is not near horizontal, turned to lie along the
   * line; on each, a ladder of slides from the anchor. The first candidate
   * that clears every node, every boundary name, every label already placed,
   * every stretch another edge shares and, in the first pass, every boundary
   * border, is kept. A turned label is the answer to a layered diagram's
   * narrow gaps: upright, "gives effect to" is wider than the ground between
   * two boundaries and had nowhere to go; along the line it is fifteen
   * pixels across. */
  function placeEdgeLabels(cy, force) {
    if (!cy) return;
    if (cy.scratch("_elk")) { showElkLabels(cy, force); return; }
    // A label that only repeats what the line style already says ("runs
    // on" on every dashed line) is clutter the legend carries; it is never
    // placed, and hovering the line still shows it.
    var redundant = cy.edges().filter(function (e) {
      var text = String(e.data("label") || "");
      return text.length > 0 && text.toLowerCase() === String(edgeWord(e.data("kind")) || "").toLowerCase();
    });
    var labeled = cy.edges().filter(function (e) { return String(e.data("label") || "").length > 0; }).difference(redundant);
    // `force` is a drawing of its own, outside the stage: every label on,
    // and the stage's Labels button left alone.
    var show = force ? true : (state.labels === null ? labeled.length <= LABEL_BUDGET : state.labels);
    if (!force) {
      state.labelsShown = show;
      var btn = $("btnLabels");
      if (btn) {
        btn.setAttribute("aria-pressed", show ? "true" : "false");
        btn.disabled = labeled.length === 0;
      }
    }
    var taken = cy.nodes().filter(function (n) { return !n.data("isGroup"); })
      .map(function (n) {
        var bb = n.boundingBox({ includeLabels: false, includeOverlays: false });
        return { x1: bb.x1 - 2, y1: bb.y1 - 2, x2: bb.x2 + 2, y2: bb.y2 + 2 };
      });
    // A boundary's name sits in its top-left corner and is kept clear. Its
    // four border lines are kept clear too, but softly: where boundaries nest
    // there is often no room off a line, and a label on a line, in its own
    // card, loses less than no label.
    var lines = [];
    cy.nodes().filter(function (n) { return n.data("isGroup"); }).forEach(function (n) {
      var bb = n.boundingBox({ includeLabels: false, includeOverlays: false });
      taken.push({ x1: bb.x1, y1: bb.y1, x2: bb.x1 + 24 + titleWidth(n.data("label")), y2: bb.y1 + 30 });
      lines.push({ x1: bb.x1, y1: bb.y1 - 3, x2: bb.x2, y2: bb.y1 + 3 });
      lines.push({ x1: bb.x1, y1: bb.y2 - 3, x2: bb.x2, y2: bb.y2 + 3 });
      lines.push({ x1: bb.x1 - 3, y1: bb.y1, x2: bb.x1 + 3, y2: bb.y2 });
      lines.push({ x1: bb.x2 - 3, y1: bb.y1, x2: bb.x2 + 3, y2: bb.y2 });
    });
    // Every straight piece of every edge, labeled or not, for the shared
    // stretch check.
    var segsOf = {}, pieces = [];
    if (show) {
      cy.edges().forEach(function (e) {
        var segs = segmentsOf(e);
        segsOf[e.id()] = segs;
        segs.forEach(function (seg) { pieces.push({ edge: e.id(), seg: seg }); });
      });
    }
    var placed = [];
    var said = {};
    function hide(e) {
      e.data("shown", "");
      e.data("lx", 0);
      e.data("ly", 0);
      e.removeClass("rot");
    }
    function clearAt(box, pass, own) {
      var apart = { x1: box.x1 - LABEL_APART, y1: box.y1 - LABEL_APART,
                    x2: box.x2 + LABEL_APART, y2: box.y2 + LABEL_APART };
      for (var k = 0; k < taken.length; k++) if (overlaps(box, taken[k])) return false;
      if (pass === 0) for (var l = 0; l < lines.length; l++) if (overlaps(box, lines[l])) return false;
      for (var j = 0; j < placed.length; j++) if (overlaps(apart, placed[j])) return false;
      // Labels are drawn with their own edge, so a later edge is drawn over
      // an earlier edge's card. The first pass wants a card no other edge
      // crosses; the second takes a crossed card over no card.
      if (pass === 0) {
        var inner = { x1: box.x1 + LABEL_GAP, y1: box.y1 + LABEL_GAP, x2: box.x2 - LABEL_GAP, y2: box.y2 - LABEL_GAP };
        for (var m = 0; m < pieces.length; m++) {
          if (pieces[m].edge !== own && pieceCrosses(inner, pieces[m].seg)) return false;
        }
      }
      return true;
    }
    // Longer labels first: they are the hardest to place, and a short one
    // fits around them more easily than the other way round.
    var edges = labeled.sort(function (a, b) {
      return String(b.data("label")).length - String(a.data("label")).length;
    });
    cy.startBatch();
    redundant.forEach(function (e) { hide(e); });
    edges.forEach(function (e) {
      if (!show) { hide(e); return; }
      var text = String(e.data("label"));
      var pair = [e.source().id(), e.target().id()].sort().join("|") + "|" + text;
      if (said[pair]) { hide(e); return; }
      var w = text.length * LABEL_CHAR + 8;
      var h = LABEL_H;
      var mid = e.midpoint();
      var runs = edgeRuns(e, segsOf[e.id()]);
      var found = null;
      for (var pass = 0; pass < 2 && !found; pass++) {
        for (var r = 0; r < runs.length && !found; r++) {
          var run = runs[r];
          var flat = Math.abs(run.uy) < 0.35;
          for (var turn = 0; turn < (flat ? 1 : 2) && !found; turn++) {
            // Half extents of the label, along the run and across it, and
            // in the sheet's own axes for the collision box.
            var along = turn ? w / 2 : Math.abs(run.ux) * w / 2 + Math.abs(run.uy) * h / 2;
            var hx = turn ? Math.abs(run.ux) * w / 2 + Math.abs(run.uy) * h / 2 : w / 2;
            var hy = turn ? Math.abs(run.uy) * w / 2 + Math.abs(run.ux) * h / 2 : h / 2;
            for (var i = 0; i < LABEL_SLIDES.length && !found; i++) {
              var s = LABEL_SLIDES[i];
              // A slid label stays within its run, give or take the corner:
              // past that it is off the line. Unslid on the run that holds
              // the midpoint, a label may overhang a short run by more, since
              // what it overhangs is the same edge turning.
              if (s > 0 && s + along > run.ahead + LABEL_OVERHANG) continue;
              if (s < 0 && -s + along > run.back + LABEL_OVERHANG) continue;
              if (s === 0 && !run.mid && along > Math.min(run.back, run.ahead) + LABEL_OVERHANG) continue;
              var cx = run.x + s * run.ux, cyy = run.y + s * run.uy;
              if (sharedStretch(cx, cyy, run.ux, run.uy, Math.min(along, 10), e.id(), pieces)) continue;
              var box = { x1: cx - hx - LABEL_GAP, y1: cyy - hy - LABEL_GAP,
                          x2: cx + hx + LABEL_GAP, y2: cyy + hy + LABEL_GAP };
              if (clearAt(box, pass, e.id())) found = { dx: cx - mid.x, dy: cyy - mid.y, box: box, turn: !!turn };
            }
          }
        }
      }
      if (found) {
        e.data("shown", text);
        e.data("lx", Math.round(found.dx));
        e.data("ly", Math.round(found.dy));
        e.toggleClass("rot", found.turn);
        placed.push(found.box);
        said[pair] = true;
      } else {
        hide(e);
      }
    });
    cy.endBatch();
  }

  /* ---- legend ----------------------------------------------------------
   * Three channels, three rows: what the hue and shape mean (entity type),
   * what the border and tint mean (the view's dimension), and what the line
   * style means (the relationship). A legend that only lists colors was a
   * legend for a third of the drawing.
   */

  var SHAPE_SVG = {
    "round-rectangle": '<rect x="1" y="1" width="18" height="12" rx="2.5"/>',
    "pill": '<rect x="1" y="2.5" width="18" height="9" rx="4.5"/>',
    "rectangle": '<rect x="1" y="1" width="18" height="12"/>',
    "round-tag": '<path d="M1 3a2 2 0 0 1 2-2h11l5 6-5 6H3a2 2 0 0 1-2-2z"/>',
    "hexagon": '<path d="M5 1h10l4 6-4 6H5L1 7z"/>',
    "barrel": '<path d="M3 1h14c1.5 0 2 1 2 2v8c0 1-.5 2-2 2H3c-1.5 0-2-1-2-2V3c0-1 .5-2 2-2z"/>',
    "rhomboid": '<path d="M5 1h14l-4 12H1z"/>',
    "tag": '<path d="M1 1h13l5 6-5 6H1z"/>',
    "ellipse": '<ellipse cx="10" cy="7" rx="9" ry="6"/>',
    "octagon": '<path d="M6 1h8l5 4v4l-5 4H6l-5-4V5z"/>',
    "cut-rectangle": '<path d="M4 1h12l3 3v6l-3 3H4l-3-3V4z"/>',
    "pentagon": '<path d="M10 1l9 5.5-3.5 6.5h-11L1 6.5z"/>',
    "round-octagon": '<path d="M6 1h8a5 5 0 0 1 5 4v4a5 5 0 0 1-5 4H6a5 5 0 0 1-5-4V5a5 5 0 0 1 5-4z"/>',
    "diamond": '<path d="M10 1l9 6-9 6-9-6z"/>',
    "round-diamond": '<path d="M8.5 1.6a2 2 0 0 1 3 0l6.9 4.6a1.2 1.2 0 0 1 0 1.6l-6.9 4.6a2 2 0 0 1-3 0L1.6 7.8a1.2 1.2 0 0 1 0-1.6z"/>',
  };

  function shapeKey(entityType, fill, stroke, width, dash) {
    var span = el("span", { class: "sw-shape" });
    var shape = SHAPE_SVG[SHAPES[entityType] || "round-rectangle"] || SHAPE_SVG["round-rectangle"];
    var dashAttr = dash === "dashed" ? ' stroke-dasharray="4 2"' : dash === "dotted" ? ' stroke-dasharray="1.5 2"' : "";
    span.innerHTML = '<svg viewBox="0 0 20 14" width="20" height="14" fill="' + fill
      + '" stroke="' + stroke + '" stroke-width="' + (width || 1.4) + '"' + dashAttr + '>' + shape + '</svg>';
    return span;
  }

  function boundaryKey(b) {
    var span = el("span", { class: "sw-shape" });
    var dashAttr = b.dash === "dashed" ? ' stroke-dasharray="4 2"' : b.dash === "dotted" ? ' stroke-dasharray="1.5 2"' : "";
    span.innerHTML = '<svg viewBox="0 0 20 14" width="20" height="14"><rect x="1" y="1" width="18" height="12" rx="2" fill="'
      + b.fill + '" stroke="' + b.stroke + '" stroke-width="1.4"' + dashAttr + '/></svg>';
    return span;
  }

  function lineKey(style, bare) {
    var span = el("span", { class: "sw-line" });
    var dashAttr = style === "dashed" ? ' stroke-dasharray="5 3"' : style === "dotted" ? ' stroke-dasharray="1.5 2.5"' : "";
    span.innerHTML = '<svg viewBox="0 0 26 8" width="26" height="8"><path d="M1 4h22" fill="none" stroke="' + DRAW.edge + '" stroke-width="1.6"'
      + dashAttr + '/>' + (bare ? "" : '<path d="M19 1l4 3-4 3z" fill="' + DRAW.edge + '"/>') + '</svg>';
    return span;
  }

  /* A relation table's name, as the sentence it stands for, read from the
   * selected thing: "system_reads_writes" out of a system is "reads or
   * writes", into a data asset it is "read or written by". */
  var RELATION_PHRASES = {
    interface: ["calls", "called by"],
    interfaces: ["calls", "called by"],
    offers: ["offers", "offered by"],
    through: ["goes through", "used by"],
    system_uses_tech_service: ["runs on", "run on by"],
    sot: ["masters", "mastered by"],
    system_reads_writes: ["reads or writes", "read or written by"],
    system_realizes_capability: ["realizes", "realized by"],
    product_includes_system: ["includes", "part of"],
    actor_uses_system: ["uses", "used by"],
    tech_service_connects_to: ["connects to", "connected from"],
    system_governed_by_control: ["governed by", "governs"],
    system_subject_to_policy: ["subject to", "binds"],
    data_governed_by_control: ["governed by", "governs"],
    data_subject_to_policy: ["subject to", "binds"],
    capability_governed_by_control: ["governed by", "governs"],
    process_uses_system: ["uses", "used by"],
    process_uses_data_asset: ["uses", "used by"],
    process_supports_capability: ["supports", "supported by"],
    process_governed_by_control: ["governed by", "governs"],
    process_subject_to_policy: ["subject to", "binds"],
    stage_crosses_capability: ["needs", "needed by"],
    work_package_changes_system: ["changes", "changed by"],
    work_package_builds_system: ["builds", "built by"],
    work_package_affects_system: ["affects", "affected by"],
    change_request_affects_system: ["affects", "affected by"],
    interface_transports_data_asset: ["carries", "carried by"],
    product_realizes_capability: ["realizes", "realized by"],
    capability_subject_to_policy: ["subject to", "binds"],
    capability_references_framework: ["is placed in", "places"],
    capability_aligns_to_framework: ["follows", "is followed by"],
    flow_step: ["has a step through", "is a step of"],
  };

  /* A reference field, as what the thing holding it says about the thing it
   * names: a system is owned by an org unit, a data asset is mastered by a
   * system. */
  var FIELD_PHRASES = {
    owner_org_id: "is owned by", data_owner_org_id: "has its data owned by",
    data_steward_org_id: "is stewarded by", source_of_truth: "is mastered by",
    parent_capability_id: "sits under", parent_org_unit_id: "reports to",
    policy_id: "gives effect to", value_stream_id: "is a stage of",
    roadmap_id: "is on", change_request_id: "was decided by",
    requestor_org_id: "was requested by", approver_org_id: "was approved by",
    system_id: "is offered by", offered_interface_id: "goes through",
  };

  function relationPhrase(kind, direction) {
    var pair = RELATION_PHRASES[kind];
    if (pair) return direction === "in" ? pair[1] : pair[0];
    return String(kind || "").replace(/_id$/, "").replace(/_/g, " ");
  }

  var EDGE_WORDS = {
    interface: "calls", system_uses_tech_service: "runs on", sot: "masters",
    tech_service_connects_to: "connects to", owner: "owns",
    system_realizes_capability: "realizes", product_includes_system: "includes",
    system_reads_writes: "reads / writes", actor_uses_system: "uses",
    policy_id: "gives effect to", control_id: "governed by",
    offers: "offers",
  };

  function edgeWord(kind) {
    if (EDGE_WORDS[kind]) return EDGE_WORDS[kind];
    if (RELATION_PHRASES[kind]) return RELATION_PHRASES[kind][0];
    return String(kind || "").replace(/_id$/, "").replace(/_/g, " ");
  }

  // A node with no value for the dimension is drawn plain and said plainly.
  function keyLabel(value) {
    /* When the dimension is the entity type, the key is the table name, and a
     * legend row reading `architecture_change_requests` is naming a file
     * rather than a thing. No dimension value in the model carries a
     * meaningful underscore. */
    return value === "default" ? "not recorded" : String(value).replace(/_/g, " ");
  }

  function renderLegend(payload) {
    var box = $("legend");
    box.textContent = "";
    var legend = payload.legend;
    if (!legend || !legend.types) return;

    var types = el("div", { class: "lg-row" });
    legend.types.forEach(function (t) {
      var key = el("button", { class: "key as-key", type: "button", "aria-pressed": "false",
        title: legend.types.length > 1 ? "Fade every " + t.label + " on the map" : "" }, [
        shapeKey(t.key, t.fill, t.stroke, 1.4, "solid"),
        el("span", { text: t.label + (legend.types.length > 1 ? " · " + t.count : "") }),
      ]);
      // A legend that filters: click a type to fade it, so a mixed picture
      // can be read one kind of thing at a time.
      key.addEventListener("click", function () {
        if (!state.cy || legend.types.length < 2) return;
        var nodes = state.cy.nodes().filter(function (n) { return n.data("entityType") === t.key; });
        var muted = key.classList.toggle("is-faded");
        key.setAttribute("aria-pressed", muted ? "true" : "false");
        nodes.toggleClass("mute", muted);
        nodes.connectedEdges().forEach(function (e) {
          e.toggleClass("mute", e.source().hasClass("mute") || e.target().hasClass("mute"));
        });
      });
      types.appendChild(key);
    });
    box.appendChild(types);

    var dim = legend.dimension || {};
    if (dim.name && dim.keys && dim.keys.length > 1 && (dim.role === "ordinal" || dim.role === "status")) {
      var row = el("div", { class: "lg-row" }, [
        el("span", { class: "cap", text: sentence(dim.name) }),
      ]);
      var sample = legend.types[0] ? legend.types[0].key : "systems";
      dim.keys.forEach(function (k) {
        var key = el("span", { class: "key" + (k.faded ? " is-faded" : "") }, [
          shapeKey(sample, k.fill, k.stroke, k.width, k.dash),
          el("span", { text: keyLabel(k.value) + " · " + k.count }),
        ]);
        row.appendChild(key);
      });
      box.appendChild(row);
    } else if (dim.name && dim.grouped && dim.role === "nominal") {
      box.appendChild(el("div", { class: "lg-row" }, [
        el("span", { class: "cap", text: "Boundary" }),
        el("span", { class: "lg-note", text: dim.name.replace(/_/g, " ") }),
      ]));
    }

    if (legend.boundaries && legend.boundaries.length) {
      var bounds = el("div", { class: "lg-row" }, [el("span", { class: "cap", text: "Boundaries" })]);
      legend.boundaries.forEach(function (b) {
        bounds.appendChild(el("span", { class: "key" }, [boundaryKey(b), el("span", { text: b.key })]));
      });
      box.appendChild(bounds);
    }

    if (legend.edges && legend.edges.length) {
      var edges = el("div", { class: "lg-row" });
      // Two relations drawn the same way and said the same way are one key:
      // "governed by" dotted, whether a system or a capability is.
      var saidKeys = {};
      legend.edges.forEach(function (e) {
        var word = edgeWord(e.kind);
        if (saidKeys[e.style + "|" + word]) return;
        saidKeys[e.style + "|" + word] = true;
        edges.appendChild(el("span", { class: "key" }, [lineKey(e.style, e.kind === "offers"), el("span", { text: word })]));
      });
      box.appendChild(edges);
    }

    visibleNotes(payload).forEach(function (note) {
      box.appendChild(el("span", { class: "note", text: note }));
    });
    if (state.cy && state.labels === null && !state.labelsShown) {
      box.appendChild(el("span", { class: "note", text:
        "Labels are off at this density: hover a node to read its connections, or press Labels." }));
    }
  }

  /* The idle inspector is a reading panel for the whole view, not a blank
   * space waiting for a click: what the view claims, what the colors mean,
   * and how much of the model it caught. */
  function renderBrief() {
    var box = $("inspIdle");
    if (!box) return;
    box.textContent = "";
    var g = state.lastGraph;
    if (!g) {
      box.appendChild(el("p", { class: "brief-p", text: "Choose a view to see its diagram." }));
      return;
    }
    box.appendChild(el("h3", { class: "brief-h", text: "This view" }));
    if (g.description) box.appendChild(el("p", { class: "brief-p", text: g.description }));

    var groups = g.elements.filter(function (e) { return e.data.isGroup; }).length;
    box.appendChild(el("p", { class: "brief-meta mono", text: isTileMap(g) ? tileMeta(g)
      : g.counts.nodes + " nodes · " + g.counts.edges + " edges" +
        (groups ? " · " + groups + " boundaries" : "") }));

    var legend = g.legend || {};
    if (legend.types && legend.types.length) {
      box.appendChild(el("h3", { class: "brief-h", text: "Items shown" }));
      legend.types.forEach(function (t) {
        box.appendChild(el("div", { class: "brief-row" }, [
          shapeKey(t.key, t.fill, t.stroke, 1.4, "solid"),
          t.label,
          el("span", { class: "brief-count", text: String(t.count) }),
        ]));
      });
    }
    var dim = legend.dimension || {};
    // Colored by type, the dimension is the list just above; a second copy
    // under "type · hue and shape" said the same thing twice.
    if (dim.name && dim.keys && dim.keys.length && dim.role !== "type") {
      var how = dim.role === "ordinal" ? "shade and border"
        : dim.role === "status" ? "border style"
        : dim.grouped ? "grouping" : "";
      box.appendChild(el("h3", { class: "brief-h", text: sentence(dim.name) + (how ? " · " + how : "") }));
      var sample = legend.types[0] ? legend.types[0].key : "systems";
      dim.keys.forEach(function (k) {
        var swatchEl = (dim.role === "ordinal" || dim.role === "status")
          ? shapeKey(sample, k.fill, k.stroke, k.width, k.dash)
          : el("span", { class: "sw-blank" });
        box.appendChild(el("div", { class: "brief-row" + (k.faded ? " is-faded" : "") }, [
          swatchEl, keyLabel(k.value), el("span", { class: "brief-count", text: String(k.count) }),
        ]));
      });
    }

    if (g.viewId && g.viewId === state.viewId && !state.preview && !state.focus && !inSketchMode()) {
      loadBriefNeeds(box, g.viewId);
    }
    visibleNotes(g).forEach(function (note) {
      box.appendChild(el("p", { class: "brief-note", text: note }));
    });
    renderMembership(box, g);
    renderFlowWalks(box, g);
    var editable = viewEditable();
    box.appendChild(el("p", { class: "brief-hint", text: (isTileMap(g)
      ? "Click a tile to see its details, connections and source file."
      : "Click any item to see its details, connections and source file. Hover to highlight its connections.")
      + (editable ? " Right-click one to hide it from this view." : "") }));
  }

  /* ---- on this view ------------------------------------------------------
   * The query decides what a drawing shows, and it still does. What a person
   * may add is a decision about one drawing: keep this here whatever its
   * fields say, or leave that off. Each is written into the view's own file
   * as `pin` or `hide`, the smallest change that does it, and both are listed
   * here, so a pinned box is never mistaken for one the query found. Where a
   * box sits is still not saved: that stays the layout's to decide, from the
   * model, which is what keeps the drawing and the model from drifting.
   */
  function viewEditable() {
    var g = state.lastGraph;
    return !!(g && g.membership && g.membership.editable && g.viewId && g.viewId === state.viewId
      && !state.preview && !state.focus && !inSketchMode() && !window.__AAC_STATIC__);
  }

  function drawnHere(id) {
    var g = state.lastGraph;
    return !!(g && (g.elements || []).some(function (e) {
      return e.data.id === id && !e.data.source && !e.data.isGroup;
    }));
  }

  function listedHere(list, id) {
    var m = state.lastGraph && state.lastGraph.membership;
    return !!(m && (m[list] || []).some(function (p) { return p.id === id; }));
  }

  var MEMBERSHIP_WORDS = {
    pinned: "Pinned to this view", hidden: "Hidden from this view",
    unpinned: "No longer pinned", shown: "Back on this view",
  };
  var MEMBERSHIP_UNDO = { pinned: "unpin", hidden: "unhide", unpinned: "show", shown: "hide" };

  function changeMembership(change, undoing) {
    if (!viewEditable()) return Promise.resolve(null);
    var body = { view: state.viewId, subject: state.subject };
    Object.keys(change).forEach(function (k) { body[k] = change[k]; });
    var keep = state.selectedId;
    return api("/api/view/membership", body).then(function (res) {
      if (!res.changes.length) {
        toast("ok", "Nothing to change", "It is already that way on this view.");
        return res;
      }
      var undo = {};
      res.changes.forEach(function (c) {
        var op = MEMBERSHIP_UNDO[c.what];
        if ((undo[op] = undo[op] || []).indexOf(c.id) === -1) undo[op].push(c.id);
      });
      var last = res.changes[res.changes.length - 1];
      var again = { label: "Undo", go: function () { changeMembership(undo, true); } };
      if (res.problem) toast("warn", MEMBERSHIP_WORDS[last.what] + ": " + last.name, res.problem, again);
      else if (undoing) toast("ok", "Undone", "Saved in " + res.path + ".");
      else toast("ok", MEMBERSHIP_WORDS[last.what] + ": " + last.name, "Saved in " + res.path + ".", again);
      return selectView(state.viewId).then(function () {
        if (keep) showEntity(keep);
        return res;
      });
    }).catch(fail);
  }

  function addToView() {
    if (!viewEditable()) return;
    openPicker({
      placeholder: "Add to this view: type a name or an id…",
      skip: drawnHere,
      onPick: function (id) {
        changeMembership({ show: [id] }).then(function () { if (drawnHere(id)) showEntity(id); });
      },
    });
  }

  function membershipSection(id) {
    if (!viewEditable()) return null;
    var kids = [];
    function act(label, change, title) {
      kids.push(el("button", { class: "btn small", type: "button", text: label, title: title || null,
        onclick: function () { changeMembership(change); } }));
    }
    if (drawnHere(id)) {
      if (listedHere("pinned", id)) {
        kids.push(el("p", { class: "on-view-note", text:
          "Pinned here by hand. The view's query did not find it, so the next thing like it will not appear by itself." }));
        act("Unpin", { unpin: [id] });
      }
      act("Hide from this view", { hide: [id] }, "Leave it off this drawing; the model and every other view keep it");
    } else if (listedHere("hidden", id)) {
      kids.push(el("p", { class: "on-view-note", text: "Hidden from this view by hand." }));
      act("Show it again", { unhide: [id] });
    } else {
      kids.push(el("p", { class: "on-view-note", text: "Not on this view." }));
      act("Add to this view", { show: [id] }, "Pin it to this drawing");
    }
    return section("On this view", [el("div", { class: "on-view" }, kids)]);
  }

  function renderMembership(box, g) {
    var m = g.membership;
    if (!m) return;
    var editable = viewEditable();
    function rows(title, list, label, change) {
      if (!list.length) return;
      box.appendChild(el("h3", { class: "brief-h", text: title }));
      list.forEach(function (p) {
        box.appendChild(el("div", { class: "brief-pin" + (p.gone ? " is-gone" : "") }, [
          el("button", { class: "bp-name", type: "button", text: p.name,
            title: p.gone ? p.id + " is no longer in the model" : p.id,
            onclick: p.gone ? null : function () { showEntity(p.id); } }),
          editable ? el("button", { class: "btn small bp-act", type: "button", text: label,
            onclick: function () { var c = {}; c[change] = [p.id]; changeMembership(c); } }) : null,
        ]));
      });
    }
    rows("Pinned to this view", m.pinned || [], "Unpin", "unpin");
    rows("Hidden from this view", m.hidden || [], "Show", "unhide");
    if (editable) {
      box.appendChild(el("button", { class: "btn small brief-add", type: "button",
        text: "Add to this view…", title: "Pin anything in the model to this drawing",
        onclick: addToView }));
    }
  }

  /* ---- the right-click menu ------------------------------------------------
   * What can be done to one box, where the box is. Every item here is also a
   * button in the inspector; the menu only saves the trip across the screen. */
  function closeContextMenu() {
    var old = $("ctxMenu");
    if (old) old.remove();
  }

  function openContextMenu(id, x, y) {
    closeContextMenu();
    var node = (state.lastGraph && state.lastGraph.elements || []).filter(function (e) { return e.data.id === id; })[0];
    var name = node ? node.data.label || id : id;
    var items = [["Open details", function () { showEntity(id); }]];
    if (viewEditable()) {
      items.push(null);
      if (listedHere("pinned", id)) items.push(["Unpin from this view", function () { state.selectedId = id; changeMembership({ unpin: [id] }); }]);
      items.push(["Hide from this view", function () { state.selectedId = id; changeMembership({ hide: [id] }); }]);
    }
    if (!window.__AAC_STATIC__) {
      items.push(["Connect to…", function () { connectFrom(id); }]);
    }
    items.push(null);
    items.push(["Focus on this", function () { showFocus(id, 1); }]);
    items.push(["Show the impact", function () { showEntity(id); showImpact(id); }]);
    items.push([inSketch(id) ? "Take out of the sketch" : "Add to the sketch", function () { sketchToggle(id); }]);
    var menu = el("div", { class: "ctx-menu", id: "ctxMenu", role: "menu", "aria-label": name }, [
      el("div", { class: "ctx-head", text: name }),
    ]);
    items.forEach(function (it) {
      if (!it) { menu.appendChild(el("div", { class: "ctx-sep", role: "separator" })); return; }
      menu.appendChild(el("button", { type: "button", role: "menuitem", text: it[0],
        onclick: function () { closeContextMenu(); it[1](); } }));
    });
    document.body.appendChild(menu);
    var r = menu.getBoundingClientRect();
    menu.style.left = Math.max(8, Math.min(x, window.innerWidth - r.width - 8)) + "px";
    menu.style.top = Math.max(8, Math.min(y, window.innerHeight - r.height - 8)) + "px";
    var buttons = menu.querySelectorAll("button");
    if (buttons.length) buttons[0].focus();
    menu.addEventListener("keydown", function (e) {
      var list = Array.prototype.slice.call(menu.querySelectorAll("button"));
      var at = list.indexOf(document.activeElement);
      if (e.key === "Escape") { e.preventDefault(); closeContextMenu(); return; }
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        var next = (at + (e.key === "ArrowDown" ? 1 : list.length - 1)) % list.length;
        list[next].focus();
      }
    });
  }

  function contextMenuAtNode(id) {
    if (!state.cy) return;
    var n = state.cy.getElementById(id);
    if (!n.length) return;
    var box = $("cy").getBoundingClientRect(), p = n.renderedPosition();
    openContextMenu(id, box.left + p.x, box.top + p.y);
  }

  /* ---- the export -----------------------------------------------------------
   * A diagram pasted into a deck has to say what it is. The export carries
   * a title block over the drawing -- the view's title and description, the
   * model's name, the date and the counts -- and the legend under it: the
   * entity types, the dimension, the boundaries, the line styles. The
   * drawing itself is what the PNG button always exported, at 2x.
   */
  /* The drawing as a picture: Cytoscape's own PNG with the technology lines
   * painted onto it where the layer paints them on the screen. The PNG
   * button and the screenshot tool both take it from here. */
  function drawingPng(cy, scale) {
    var S = scale || 2;
    return new Promise(function (resolve, reject) {
      var image = new Image();
      image.onload = function () {
        var canvas = document.createElement("canvas");
        canvas.width = image.width;
        canvas.height = image.height;
        var ctx = canvas.getContext("2d");
        ctx.drawImage(image, 0, 0);
        var bb = cy.elements().boundingBox();
        var k = bb.w > 0 ? image.width / bb.w : S;
        ctx.textAlign = "center";
        ctx.textBaseline = "alphabetic";
        ctx.font = "500 " + (TECH_FONT * k) + "px Geist, system-ui, sans-serif";
        cy.nodes("[tech]").forEach(function (n) {
          if (!n.data("tech") || n.data("isGroup")) return;
          var p = n.position();
          ctx.globalAlpha = n.hasClass("dim") ? 0.3 : (n.data("faded") ? 0.55 : 1);
          ctx.fillStyle = "#5b6577";
          var text = fitText(ctx, String(n.data("tech")), (n.width() - 10) * k);
          ctx.fillText(text, (p.x - bb.x1) * k, (p.y + n.height() / 2 - bb.y1) * k - 5.5 * k);
        });
        resolve(canvas.toDataURL("image/png"));
      };
      image.onerror = reject;
      image.src = cy.png({ full: true, scale: S, bg: "#ffffff" });
    });
  }
  window.__aacDrawingPng = currentDrawingPng;

  // Where a box is on the screen, for the probes that drive the drawing the
  // way a person would (80_APP/tools/dev); nothing in the app reads it.
  window.__aacNodeAt = function (id) {
    if (!state.cy) return null;
    var n = state.cy.getElementById(id);
    if (!n.length) return null;
    var box = $("cy").getBoundingClientRect(), p = n.renderedPosition();
    return { x: box.left + p.x, y: box.top + p.y };
  };

  function exportPng(cy, graph, filename) {
    var drawing = new Image();
    drawing.onload = function () {
      var S = 2;
      var pad = 28 * S;
      var width = Math.max(drawing.width + 2 * pad, 1100 * S);
      var canvas = document.createElement("canvas");
      var ctx = canvas.getContext("2d");
      var title = (graph && graph.title) || "Architecture";
      var desc = (graph && graph.description) || "";
      var sans = "Geist, system-ui, sans-serif";
      var mono = "Geist Mono, ui-monospace, monospace";
      // Measure the description's lines at the final width first.
      ctx.font = (14 * S) + "px " + sans;
      var lines = wrapText(ctx, desc, width - 2 * pad);
      var headH = pad + 30 * S + (lines.length ? lines.length * 20 * S + 6 * S : 0) + 18 * S;
      var legendRows = legendLines(graph);
      var footH = (legendRows.length ? legendRows.length * 22 * S + 14 * S : 0) + 30 * S + pad;
      canvas.width = width;
      canvas.height = headH + drawing.height + footH;
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      // The title block.
      ctx.fillStyle = "#101828";
      ctx.font = "600 " + (24 * S) + "px " + sans;
      ctx.fillText(title, pad, pad + 24 * S);
      ctx.font = (12 * S) + "px " + mono;
      ctx.fillStyle = "#495366";
      var facts = [state.overview && state.overview.modelName || "", new Date().toISOString().slice(0, 10),
        graph && graph.counts ? graph.counts.nodes + " nodes \u00b7 " + graph.counts.edges + " edges" : ""].filter(Boolean).join("   \u00b7   ");
      var factsW = ctx.measureText(facts).width;
      ctx.fillText(facts, width - pad - factsW, pad + 22 * S);
      ctx.font = (14 * S) + "px " + sans;
      ctx.fillStyle = "#343d50";
      lines.forEach(function (line, i) { ctx.fillText(line, pad, pad + 30 * S + 20 * S * (i + 1)); });
      ctx.strokeStyle = "#d2dae5";
      ctx.lineWidth = 1 * S;
      ctx.beginPath(); ctx.moveTo(pad, headH - 10 * S); ctx.lineTo(width - pad, headH - 10 * S); ctx.stroke();
      // The drawing, centered, technology lines and all.
      ctx.drawImage(drawing, (width - drawing.width) / 2, headH);
      // The legend.
      var y = headH + drawing.height + 14 * S;
      ctx.beginPath(); ctx.moveTo(pad, y); ctx.lineTo(width - pad, y); ctx.stroke();
      y += 10 * S;
      legendRows.forEach(function (row) {
        var x = pad;
        ctx.font = "500 " + (10.5 * S) + "px " + mono;
        ctx.fillStyle = "#2841b9";
        ctx.fillText(row.cap.toUpperCase(), x, y + 14 * S);
        x += ctx.measureText(row.cap.toUpperCase()).width + 14 * S;
        row.keys.forEach(function (key) {
          drawKey(ctx, key, x, y + 3 * S, S);
          x += 26 * S;
          ctx.font = (12 * S) + "px " + sans;
          ctx.fillStyle = "#343d50";
          ctx.fillText(key.text, x, y + 14 * S);
          x += ctx.measureText(key.text).width + 18 * S;
        });
        y += 22 * S;
      });
      ctx.font = (11 * S) + "px " + mono;
      ctx.fillStyle = "#495366";
      ctx.fillText("Generated from the model by architecture-as-code \u00b7 " + ((graph && graph.viewId) || "") + " \u00b7 edit the model, not the picture",
        pad, canvas.height - pad + 6 * S);
      var a = document.createElement("a");
      a.href = canvas.toDataURL("image/png");
      a.download = filename;
      a.click();
    };
    currentDrawingPng(2).then(function (url) { drawing.src = url; }).catch(fail);
  }

  function wrapText(ctx, text, maxWidth) {
    var words = String(text || "").split(/\s+/).filter(Boolean);
    var lines = [], line = "";
    words.forEach(function (word) {
      var probe = line ? line + " " + word : word;
      if (ctx.measureText(probe).width > maxWidth && line) { lines.push(line); line = word; }
      else line = probe;
    });
    if (line) lines.push(line);
    return lines.slice(0, 4);
  }

  function legendLines(graph) {
    var legend = (graph && graph.legend) || {};
    var rows = [];
    if (legend.types && legend.types.length) {
      rows.push({ cap: "type", keys: legend.types.map(function (t) {
        return { kind: "shape", type: t.key, fill: t.fill, stroke: t.stroke, dash: "solid", text: t.label + " \u00b7 " + t.count };
      }) });
    }
    var dim = legend.dimension || {};
    if (dim.name && dim.keys && dim.keys.length > 1 && (dim.role === "ordinal" || dim.role === "status")) {
      rows.push({ cap: dim.name.replace(/_/g, " "), keys: dim.keys.map(function (k) {
        return { kind: "shape", type: legend.types[0] ? legend.types[0].key : "systems", fill: k.fill, stroke: k.stroke,
          dash: k.dash, width: k.width, text: keyLabel(k.value) + " \u00b7 " + k.count };
      }) });
    }
    if (legend.boundaries && legend.boundaries.length) {
      rows.push({ cap: "boundaries", keys: legend.boundaries.map(function (b) {
        return { kind: "box", fill: b.fill, stroke: b.stroke, dash: b.dash, text: b.key };
      }) });
    }
    if (legend.edges && legend.edges.length) {
      var said = {};
      var keys = [];
      legend.edges.forEach(function (e) {
        var word = edgeWord(e.kind);
        if (said[e.style + "|" + word]) return;
        said[e.style + "|" + word] = true;
        keys.push({ kind: "line", dash: e.style, text: word });
      });
      rows.push({ cap: "lines", keys: keys });
    }
    return rows;
  }

  function drawKey(ctx, key, x, y, S) {
    ctx.save();
    ctx.lineWidth = (key.width || 1.4) * S;
    ctx.setLineDash(key.dash === "dashed" ? [4 * S, 2 * S] : key.dash === "dotted" ? [1.5 * S, 2 * S] : []);
    if (key.kind === "line") {
      ctx.strokeStyle = DRAW.edge;
      ctx.beginPath(); ctx.moveTo(x, y + 7 * S); ctx.lineTo(x + 20 * S, y + 7 * S); ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = DRAW.edge;
      ctx.beginPath(); ctx.moveTo(x + 16 * S, y + 4 * S); ctx.lineTo(x + 21 * S, y + 7 * S); ctx.lineTo(x + 16 * S, y + 10 * S); ctx.fill();
    } else {
      ctx.fillStyle = key.fill || "#ffffff";
      ctx.strokeStyle = key.stroke || "#8f9bb5";
      var w = 20 * S, h = 13 * S, r = 3 * S;
      ctx.beginPath();
      ctx.moveTo(x + r, y); ctx.lineTo(x + w - r, y); ctx.quadraticCurveTo(x + w, y, x + w, y + r);
      ctx.lineTo(x + w, y + h - r); ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
      ctx.lineTo(x + r, y + h); ctx.quadraticCurveTo(x, y + h, x, y + h - r);
      ctx.lineTo(x, y + r); ctx.quadraticCurveTo(x, y, x + r, y); ctx.closePath();
      ctx.fill(); ctx.stroke();
    }
    ctx.restore();
  }

  /* ---- walking a flow -------------------------------------------------------
   * A reference architecture numbers the steps on its picture and tells the
   * story beside it. A flow here is a recorded sequence of interfaces, and
   * every interface drawn knows which it is, so a flow can be walked on any
   * drawing that carries its hops: the hops numbered and lit, everything
   * else dimmed, the narrative in the inspector with the steps that are not
   * on this drawing said so.
   */
  function renderFlowWalks(box, g) {
    var flows = g.flows || [];
    if (!flows.length || !state.cy) return;
    box.appendChild(el("h3", { class: "brief-h", text: "Flows across this drawing" }));
    flows.forEach(function (flow) {
      var walking = state.walk && state.walk.id === flow.id;
      var row = el("button", { type: "button", class: "walk-row" + (walking ? " is-on" : ""),
        "aria-pressed": walking ? "true" : "false",
        onclick: function () { if (walking) stopWalk(); else walkFlow(flow); } }, [
        el("span", { class: "walk-name", text: flow.name }),
        el("span", { class: "walk-n mono", text: flow.drawn + " of " + flow.steps.length + " steps here" }),
      ]);
      box.appendChild(row);
      if (walking) {
        var list = el("ol", { class: "walk-steps" });
        flow.steps.forEach(function (step) {
          list.appendChild(el("li", { class: step.drawn ? "" : "is-off" }, [
            el("span", { class: "walk-step mono", text: String(step.n) }),
            el("span", {}, [
              el("button", { type: "button", class: "flow-hop", text: step.from,
                onclick: function () { showEntity(step.fromId); } }),
              " \u2192 ",
              el("button", { type: "button", class: "flow-hop", text: step.to,
                onclick: function () { showEntity(step.toId); } }),
              step.protocol ? el("span", { class: "walk-proto mono", text: step.protocol }) : null,
              step.drawn ? null : el("span", { class: "walk-off", text: "not on this drawing" }),
            ]),
          ]));
        });
        box.appendChild(list);
        if (flow.description) box.appendChild(el("p", { class: "brief-p", text: flow.description }));
      }
    });
  }

  function walkFlow(flow) {
    if (!state.cy) return;
    state.walk = flow;
    state.selectedId = null;
    var cy = state.cy;
    cy.elements().removeClass(IMPACT_CLASSES);
    var byRef = {};
    flow.steps.forEach(function (step) { byRef[step.interfaceId] = step; });
    var hops = cy.edges().filter(function (e) { return !!byRef[e.data("ref")]; });
    var ends = hops.connectedNodes();
    var kept = hops.union(ends).union(ends.ancestors());
    cy.elements().difference(kept).addClass("dim");
    ends.addClass("hl");
    hops.forEach(function (e) {
      var step = byRef[e.data("ref")];
      e.data("stepLabel", step.n + "  " + (e.data("label") || ""));
      e.data("lx", 0);
      e.data("ly", 0);
    });
    hops.addClass("step");
    $("inspBody").hidden = true;
    $("inspIdle").hidden = false;
    renderBrief();
    announce("Walking " + flow.name + ": " + flow.drawn + " of " + flow.steps.length + " steps on this drawing.");
  }

  function stopWalk() {
    state.walk = null;
    if (state.cy) {
      state.cy.elements().removeClass(IMPACT_CLASSES);
      placeEdgeLabels(state.cy);
    }
    renderBrief();
  }

  var IMPACT_CLASSES = "hl sel dim conf-direct conf-likely conf-possible step";

  function highlight(id) {
    if (tilesShown()) {
      clearTiles();
      var tile = tileOf(id);
      if (tile) {
        tile.classList.add("is-sel");
        tile.scrollIntoView({ block: "nearest", inline: "nearest" });
        announce("Selected " + (tile.querySelector(".tile-name").textContent || id) + ".");
      }
    }
    if (!state.cy) return;
    var node = state.cy.getElementById(id);
    state.cy.elements().removeClass(IMPACT_CLASSES);
    if (!node || node.length === 0) return;
    var hood = node.closedNeighborhood();
    state.cy.elements().difference(hood).addClass("dim");
    hood.addClass("hl");
    node.addClass("sel");
    announce("Selected " + (node.data("label") || id) + ", " +
      String(node.data("entityType") || "").replace(/_/g, " ") + ", " +
      node.connectedEdges().length + " connections.");
  }

  /* The screen reader's view of the map: one sentence per selection, so the
   * relationship between what was tabbed to and what lit up is said aloud. */
  function announce(text) {
    var live = $("live");
    if (!live) return;
    live.textContent = "";
    setTimeout(function () { live.textContent = text; }, 30);
  }

  function clearSelection() {
    state.selectedId = null;
    state.walk = null;
    inspectorOver(false);
    syncUrl();
    if (state.cy) state.cy.elements().removeClass(IMPACT_CLASSES);
    if (tilesShown()) clearTiles();
    $("inspBody").hidden = true;
    $("inspIdle").hidden = false;
    renderBrief();
  }

  /* The URL is the shareable state. A hosted map nobody can link into is a map
   * nobody sends to anyone, which is most of the value of hosting it. */
  function syncUrl() {
    if (cv) {
      var drawing = "#draw" + (cv.id ? "=" + encodeURIComponent(cv.id) : "");
      if (window.location.hash !== drawing) window.history.replaceState(null, "", drawing);
      return;
    }
    if (state.panel === "assemble" && asm) {
      var opened = "#assemble" + (asm.replace ? "&open=" + encodeURIComponent(asm.replace) : "");
      if (window.location.hash !== opened) window.history.replaceState(null, "", opened);
      return;
    }
    if (state.panel === "needs" || (state.panel === "setmany" && state.setMany)) {
      var ask = state.setMany && state.setMany.ask;
      var page = state.panel === "needs" ? "#needs" : "#set&type=" + encodeURIComponent(ask.type) + "&field="
        + encodeURIComponent(ask.field) + (ask.view ? "&of=" + encodeURIComponent(ask.view) : "")
        + (ask.subject ? "&subject=" + encodeURIComponent(ask.subject) : "");
      if (window.location.hash !== page) window.history.replaceState(null, "", page);
      return;
    }
    if (state.panel === "settings") {
      var tabbed = "#settings&tab=" + encodeURIComponent(state.settingsTab || "sources");
      if (window.location.hash !== tabbed) window.history.replaceState(null, "", tabbed);
      return;
    }
    if (state.panel === "start" || state.panel === "diagrams" || state.panel === "guide") {
      var want = state.panel === "start" ? "#home"
        : state.panel === "diagrams" ? "#diagrams" + (state.homeLayer && state.homeLayer !== "All"
          ? "&layer=" + encodeURIComponent(state.homeLayer) : "")
        : "#" + state.panel;
      if (window.location.hash !== want) window.history.replaceState(null, "", want);
      return;
    }
    // The pages over the drawing name themselves too, with what is chosen
    // on each. They wrote nothing, so a reload on the Model, the Library,
    // Checks or a flow landed on whatever was under them: Home, or the
    // capability map.
    var over = pageHash();
    if (over) {
      if (window.location.hash !== over) window.history.replaceState(null, "", over);
      return;
    }
    var hash = "#view=" + encodeURIComponent(state.viewId || "");
    if (state.focus) {
      hash += "&focus=" + encodeURIComponent(state.focus.id) + "&depth=" + state.focus.depth;
    }
    Object.keys(state.subject).forEach(function (name) {
      hash += "&p_" + encodeURIComponent(name) + "=" + encodeURIComponent(state.subject[name]);
    });
    if (state.selectedId) hash += "&id=" + encodeURIComponent(state.selectedId);
    if (window.location.hash !== hash) {
      window.history.replaceState(null, "", hash);
    }
  }

  /* The address of a page over the drawing, from what is open on it; empty
   * for any other. The words are the sidebar's (`#model`, not the panel's
   * old name `data`), since a person reads them in the address bar. */
  function pageHash() {
    function arg(key, value) { return value ? "&" + key + "=" + encodeURIComponent(value) : ""; }
    var p = state.panel;
    if (p === "data") return "#model" + arg("table", state.dataTable);
    if (p === "library") return "#library" + arg("shelf", state.libShelf);
    if (p === "validate") return "#checks" + arg("rule", state.checkRule);
    if (p === "coverage") return "#checks&tab=coverage";
    if (p === "drift") return "#checks&tab=drift" + arg("export", state.driftExport);
    if (p === "changes") {
      var c = state.changes || {};
      return "#checks&tab=changes" + arg("since", c.since) + arg("until", c.until);
    }
    if (p === "flows") return "#flows" + arg("flow", state.flowId);
    return "";
  }

  function isPageHash(w) {
    return w.model !== undefined || w.library !== undefined || w.checks !== undefined || w.flows !== undefined;
  }

  // The other half: open the page an address names, as it was.
  function openPageFrom(w) {
    if (w.model !== undefined) openData(w.table || null);
    else if (w.library !== undefined) openLibrary(null, w.shelf || "");
    else if (w.flows !== undefined) openFlows(w.flow || null);
    else if (w.tab === "coverage") openCoverage();
    else if (w.tab === "drift") openDrift(w["export"] || "");
    else if (w.tab === "changes") openChanges(w.since || "", w.until || "");
    else openValidate(w.rule || "");
  }

  function readUrl() {
    var out = {};
    (window.location.hash || "").replace(/^#/, "").split("&").forEach(function (pair) {
      var bits = pair.split("=");
      if (!bits[0]) return;
      // `#home` is a bare key; everything else is key=value.
      out[bits[0]] = bits.length > 1 ? decodeURIComponent(bits[1]) : "";
    });
    return out;
  }

  /* Where a drawing sits: the Diagrams page, then its layer, over the
   * title, so the way back is a word rather than the sidebar. */
  function crumbParts(viewId) {
    var v = (state.overview && state.overview.views || []).filter(function (x) { return x.viewId === viewId; })[0];
    var layer = state.focus ? "Focus" : (v && v.category) || "";
    var parts = [el("button", { type: "button", text: "Diagrams", onclick: function () { openDiagrams("All"); } })];
    if (layer) {
      parts.push(el("span", { class: "sep", text: "/" }));
      parts.push(el("button", { type: "button", text: layer, onclick: function () {
        openDiagrams(VIEW_CATEGORIES.indexOf(layer) === -1 ? "All" : layer);
      } }));
    }
    return parts;
  }

  function renderCrumb(viewId) {
    var box = $("viewCrumb");
    if (!box) return;
    box.textContent = "";
    crumbParts(viewId).forEach(function (part) { box.appendChild(part); });
  }

  function selectView(viewId) {
    leaveCanvas();
    if (state.panel) showPanel(false);
    if (viewId !== state.viewId) { state.subject = {}; state.labels = null; }
    state.viewId = viewId;
    state.recent = [viewId].concat((state.recent || []).filter(function (id) { return id !== viewId; })).slice(0, 6);
    rememberView(viewId);
    state.preview = false;
    if (state.focus) { state.focus = null; renderFocusBar(); }
    renderNeedStrip(null);
    renderViewList(state.overview);
    renderCrumb(viewId);
    var extra = Object.keys(state.subject).map(function (name) {
      return "&p_" + encodeURIComponent(name) + "=" + encodeURIComponent(state.subject[name]);
    }).join("");
    return api("/api/graph?view=" + encodeURIComponent(viewId) + extra)
      .then(function (payload) {
        $("stageEmpty").hidden = true;
        if (payload.kind === "report") { drawReport(payload); return; }
        if (payload.kind === "timeline") { drawTimeline(payload); return; }
        if (state.panel) showPanel(false);
        drawGraph(payload);
        syncUrl();
      })
      .catch(function (err) {
        var v = (state.overview.views || []).filter(function (x) { return x.viewId === viewId; })[0];
        $("viewTitle").textContent = v ? v.title : viewId;
        $("viewDesc").textContent = v ? v.description : "";
        $("viewMeta").textContent = "";
        if (state.cy) { state.cy.destroy(); state.cy = null; }
        $("tiles").hidden = true;
        $("cy").hidden = false;
        $("legend").textContent = "";
        state.lastGraph = null;
        renderBrief();
        $("emptyWhy").textContent = err.message;
        $("emptyPlain").hidden = false;
        $("emptyNeeds").hidden = true;
        $("stageEmpty").hidden = false;
        if (/selected no entities/.test(err.message)) renderEmptyNeeds(viewId);
      });
  }

  // ---- inspector --------------------------------------------------------

  // Placement leads: "which account, which region, which zone" is the first
  // question anyone asks of a box on an infrastructure diagram.
  var PLACEMENT = [
    ["cloud_provider", "cloud"],
    ["cloud_account", "account"],
    ["region", "region"],
    ["network_zone", "zone"],
    ["resilience", "resilience"],
    ["environment", "env"],
  ];

  var GRADED = { High: "is-high", Medium: "is-med", Low: "is-ok", Active: "is-ok", Planned: "" };

  function chip(key, value, cls) {
    var label = String(key || "");
    return el("span", { class: "chip" + (cls ? " " + cls : "") }, [
      el("span", { class: "k", text: label.charAt(0).toUpperCase() + label.slice(1) }),
      el("span", { class: "v", text: String(value) }),
    ]);
  }

  function section(title, kids) {
    return el("div", { class: "insp-sec" }, [el("h3", { text: title })].concat(kids));
  }

  //: Below this width the inspector is a sheet over the stage, opened by a
  //: selection and closed by its own button, the toggle, or Escape.
  var NARROW = window.matchMedia("(max-width: 1240px)");
  var REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)");

  function inspectorOver(on) {
    document.querySelector(".shell").classList.toggle("insp-over", !!on);
  }

  function showEntity(id) {
    state.selectedId = id;
    state.impactShown = null;
    highlight(id);
    syncUrl();
    renderSketchBar();
    if (NARROW.matches && !state.panel) inspectorOver(true);
    api("/api/entity?id=" + encodeURIComponent(id)).then(function (data) {
      var body = $("inspBody");
      var r = data.record;
      body.textContent = "";
      $("inspIdle").hidden = true;
      body.hidden = false;

      var home = data.home || { kind: data.generated ? "generated" : "own" };
      var imported = home.kind === "imported";
      var acts = el("div", { class: "acts" });
      if (!imported) {
        acts.appendChild(el("button", {
          class: "btn small", type: "button",
          text: data.generated ? "Open instance" : "Edit",
          onclick: function () {
            if (data.generated) showEntity(r.archetype_instance);
            else openEntityEditor(data.type, id, r, null, null, home);
          },
        }));
      }
      // A product assembled from parts, or on a shape, is edited in the
      // Assemble panel; so is anything either made.
      var composed = String(r.archetype || "").indexOf("compose:") === 0;
      var assembled = !!r.archetype && (data.type === "products" || data.generated);
      if (assembled) {
        acts.appendChild(el("button", {
          class: "btn small", type: "button", text: data.generated ? "Open assembly" : "Open in Assemble",
          title: "Open the product in Assemble with its parts selected and its edits in place",
          onclick: function () { openAssemble({ open: data.generated ? r.archetype_instance : id }); },
        }));
      }
      acts.appendChild(el("button", {
        class: "btn small", type: "button", text: "Focus",
        title: "Draw everything around this",
        onclick: function () { showFocus(id, state.focus ? state.focus.depth : 1); },
      }));
      acts.appendChild(el("button", {
        class: "btn small", type: "button", text: "Connect\u2026",
        title: "Connect this to something else in the model",
        onclick: function () { connectFrom(id); },
      }));
      acts.appendChild(el("button", {
        class: "btn small", type: "button", text: "Impact",
        title: "What else is affected if this changes",
        onclick: function () { showImpact(id); },
      }));
      acts.appendChild(el("button", {
        class: "btn small" + (inSketch(id) ? " on" : ""), type: "button",
        text: inSketch(id) ? "In sketch" : "Sketch",
        title: inSketch(id) ? "Take this out of the sketch" : "Pick this to draw with other things",
        onclick: function () { sketchToggle(id); showEntity(id); },
      }));

      var sw = swatchOf(data.type);
      body.appendChild(el("div", { class: "insp-head" }, [
        el("span", { class: "kind-tag is-type", style: "background:" + sw[0] + ";color:" + sw[1] }, [
          el("span", { class: "sw", style: "background:" + sw[0] + ";border-color:" + sw[1] }),
          el("span", { text: String(data.label || data.type || "").replace(/^./, function (c) { return c.toUpperCase(); }) }),
        ]),
        el("h2", { text: r.name || id }),
        el("span", { class: "id", text: id + "  ·  " + data.label }),
        acts,
      ]));
      var onView = membershipSection(id);
      if (onView) body.appendChild(onView);
      if (data.type === "systems") {
        var offers = data.related.filter(function (rel) { return rel.relation === "offers"; });
        var offerList = el("div", { class: "rel-list" });
        offers.forEach(function (rel) {
          offerList.appendChild(el("div", { class: "rel" }, [
            el("span", { class: "dir", text: "\u25cb" }),
            el("div", {}, [
              el("button", { type: "button", text: rel.otherName, onclick: function () { showEntity(rel.otherId); } }),
              rel.qualifier ? el("span", { class: "via", text: rel.qualifier }) : null,
            ]),
          ]));
        });
        body.appendChild(section("Offers" + (offers.length ? " \u00b7 " + offers.length : ""), [
          offers.length ? offerList : el("p", { class: "brief-hint", text:
            "Nothing others connect to: an API, a topic or a file drop it offers is a record of its own, "
            + "and the connections through it say so." }),
          window.__AAC_STATIC__ || imported ? null : el("button", { class: "btn small", type: "button",
            text: "Add what it offers\u2026",
            title: "An API, a topic or a file drop this system offers for others to connect to",
            onclick: function () { proposeOffered(id, r, data); } }),
        ]));
      }

      if (imported) {
        body.appendChild(section("Imported", [el("p", { class: "banner", text: home.note })]));
      }
      if (data.generated) {
        body.appendChild(section("Generated", [
          el("p", { class: "banner", text:
            "Made by " + (composed ? "the assembly " : "archetype instance ") + r.archetype_instance
              + ". Open it in Assemble to rename this, drop it or set a field on it; a change here would be "
              + "overwritten on the next render." }),
        ]));
      }

      var chips = [];
      PLACEMENT.forEach(function (pair) {
        if (r[pair[0]]) chips.push(chip(pair[1], r[pair[0]]));
      });
      if (r.criticality) chips.push(chip("criticality", r.criticality, GRADED[r.criticality]));
      if (r.status) chips.push(chip("status", r.status, GRADED[r.status]));
      // A control's placement is not where it runs but what kind of thing it
      // is, how often, and under which regulation.
      if (r.control_type) chips.push(chip("type", r.control_type));
      if (r.frequency) chips.push(chip("runs", r.frequency));
      if (r.regulatory_framework) chips.push(chip("framework", r.regulatory_framework));
      // What an offered interface is spoken in, said once for every
      // connection through it.
      if (data.type === "offered_interfaces") {
        if (r.protocol) chips.push(chip("protocol", r.protocol));
        if (r.integration_style) chips.push(chip("style", r.integration_style));
        if (r.auth_method) chips.push(chip("auth", r.auth_method));
        if (r.data_classification) chips.push(chip("classification", r.data_classification, GRADED[r.data_classification]));
      }
      if (chips.length) body.appendChild(section("Placement", [el("div", { class: "placement" }, chips)]));

      // Where a capability sits on the map, and the way to place it in a
      // framework: where it sits in a framework is listed with its other
      // connections, as "placed in" and, for a domain, "follows".
      var onMap = [];
      if (r.capability_level) onMap.push(chip("level", r.capability_level));
      if (r.capability_tier) onMap.push(chip("tier", r.capability_tier));
      if (r.strategic_importance) onMap.push(chip("importance", r.strategic_importance));
      if (data.type === "capabilities") {
        body.appendChild(section("On the map", [
          onMap.length ? el("div", { class: "placement" }, onMap) : null,
          window.__AAC_STATIC__ ? null : el("button", { class: "btn small", type: "button", text: "Map to a framework\u2026",
            title: "Say where this capability sits in a framework" + (r.capability_level === "L0" ? ", and how firmly it follows it" : ""),
            onclick: function () { openFrameworkMapper(id, r); } }),
        ]));
      } else if (onMap.length) {
        body.appendChild(section("On the map", [el("div", { class: "placement" }, onMap)]));
      }

      if (r.description) {
        body.appendChild(section("Description", [el("p", { class: "desc", text: r.description })]));
      }

      // A product says which patterns it applies. The chips open the
      // library, which is where the decision behind each one lives.
      var applied = Array.isArray(r.patterns)
        ? r.patterns
        : String(r.patterns || "").split(/[;,]/).map(function (p) { return p.trim(); }).filter(Boolean);
      if (applied.length) {
        var chips2 = el("div", { class: "placement" });
        applied.forEach(function (p) {
          chips2.appendChild(el("button", { class: "help-chip as-btn", type: "button", text: p,
            title: "Read the pattern in the library",
            onclick: function () { openLibrary(null); } }));
        });
        body.appendChild(section("Applies patterns · " + applied.length, [chips2]));
      }

      if (data.related.length) {
        // Grouped by relation: a ledger used by forty processes is forty rows
        // under one heading, not forty headings.
        var groups = {};
        var order = [];
        data.related.forEach(function (rel) {
          var key = rel.relation + "|" + rel.direction;
          if (!groups[key]) { groups[key] = { relation: rel.relation, direction: rel.direction, items: [] }; order.push(key); }
          groups[key].items.push(rel);
        });
        var rels = el("div", { class: "rels" });
        order.forEach(function (key) {
          var g = groups[key];
          var list = el("div", { class: "rel-list" });
          g.items.forEach(function (rel) {
            list.appendChild(el("div", { class: "rel" }, [
              el("span", { class: "dir", text: rel.direction === "out" ? "→" : "←" }),
              el("div", {}, [
                el("button", { type: "button", text: rel.otherName || rel.otherId,
                  onclick: function () { showEntity(rel.otherId); } }),
                rel.qualifier ? el("span", { class: "via", text: rel.qualifier }) : null,
              ]),
            ]));
          });
          var box = el("details", { class: "rel-group" }, [
            el("summary", {}, [
              el("span", { class: "rg-name", text: relationPhrase(g.relation, g.direction) }),
              el("span", { class: "rg-n mono", text: String(g.items.length) }),
            ]),
            list,
          ]);
          // Small lists open; a long one folds so the panel stays readable.
          box.open = g.items.length <= 6 || order.length === 1;
          rels.appendChild(box);
        });
        body.appendChild(section("Connected · " + data.related.length, [rels]));
      }

      var skip = { name: 1, description: 1, archetype_instance: 1, patterns: 1 };
      PLACEMENT.forEach(function (p) { skip[p[0]] = 1; });
      skip.criticality = 1;
      skip.status = 1;
      skip[data.pk] = 1;
      var dl = el("dl", { class: "kv" });
      var shown = 0;
      Object.keys(r).forEach(function (k) {
        if (skip[k] || r[k] === null || r[k] === "" || r[k] === undefined) return;
        shown++;
        dl.appendChild(el("dt", { text: sentence(k), title: k }));
        dl.appendChild(el("dd", { text: Array.isArray(r[k]) ? r[k].join(", ") : String(r[k]) }));
      });
      if (shown) {
        body.appendChild(el("div", { class: "insp-sec" }, [
          el("details", { class: "fields" }, [
            el("summary", { text: "All fields (" + shown + ")" }),
            dl,
          ]),
        ]));
      }

      if (data.sourceFile) {
        body.appendChild(section("File", [
          el("div", { class: "mono", style: "font-size:11px;color:var(--ink-3);overflow-wrap:anywhere",
            text: data.sourceFile }),
        ]));
      }

      // Destruction lives at the end, on its own, rather than beside Impact
      // in a row of five identical buttons.
      if (!data.generated && !imported) {
        body.appendChild(el("div", { class: "insp-sec insp-danger" }, [
          el("button", { class: "btn small danger", type: "button", text: "Delete this " + data.label,
            onclick: function () { deleteEntity(id, home); } }),
        ]));
      }
    }).catch(fail);
  }

  var CONF_ORDER = { direct: 0, likely: 1, possible: 2 };

  function impactList(hops, emptyText) {
    if (!hops.length) return el("p", { class: "brief-hint", text: emptyText });
    var box = el("div", { class: "impact-list" });
    hops.slice(0, 60).forEach(function (h) {
      box.appendChild(el("div", { class: "impact-row conf-" + h.confidence }, [
        el("span", { class: "conf", text: h.confidence }),
        el("div", { class: "impact-main" }, [
          el("button", { type: "button", text: h.name,
            onclick: function () { showEntity(h.id); } }),
          el("span", { class: "via", text: h.via.replace(/_/g, " ") }),
        ]),
      ]));
    });
    if (hops.length > 60) {
      box.appendChild(el("p", { class: "brief-hint",
        text: (hops.length - 60) + " more not shown" }));
    }
    return box;
  }

  function byConfidence(a, b) {
    return CONF_ORDER[a.confidence] - CONF_ORDER[b.confidence] ||
           a.name.localeCompare(b.name);
  }

  function showImpact(id) {
    state.impactShown = id;
    api("/api/impact?id=" + encodeURIComponent(id)).then(function (d) {
      var body = $("inspBody");
      body.textContent = "";
      $("inspIdle").hidden = true;
      body.hidden = false;

      body.appendChild(el("div", { class: "insp-head" }, [
        el("h2", { text: d.rootName }),
        el("span", { class: "id", text: d.root + "  \u00b7  impact" }),
        el("div", { class: "acts" }, [
          el("button", { class: "btn small", type: "button", text: "Back to details",
            onclick: function () { showEntity(id); } }),
        ]),
      ]));

      d.notes.forEach(function (n) {
        body.appendChild(el("div", { class: "insp-sec" },
          [el("p", { class: "banner", text: n })]));
      });

      body.appendChild(section(
        "Affected if this changes \u00b7 " + d.counts.downstream,
        [impactList(d.downstream.slice().sort(byConfidence), "Nothing depends on this.")]));

      body.appendChild(section(
        "This depends on \u00b7 " + d.counts.upstream,
        [impactList(d.upstream.slice().sort(byConfidence),
                    "This depends on nothing recorded.")]));

      // The whole blast radius lit on the map at once, rather than one hop,
      // and weakening with distance the way the list does.
      if (state.cy) {
        var conf = {};
        d.downstream.forEach(function (h) { conf[h.id] = h.confidence; });
        state.cy.elements().removeClass(IMPACT_CLASSES);
        var root = state.cy.getElementById(d.root);
        var inRadius = state.cy.nodes().filter(function (n) { return conf[n.id()] || n.id() === d.root; });
        if (inRadius.length) {
          state.cy.elements().difference(inRadius.closedNeighborhood()).addClass("dim");
          inRadius.forEach(function (n) {
            n.addClass("hl");
            if (conf[n.id()]) n.addClass("conf-" + conf[n.id()]);
          });
          inRadius.connectedEdges().addClass("hl");
        }
        if (root.length) root.addClass("sel");
        announce("Impact of " + d.rootName + ": " + d.counts.downstream + " affected, " +
          d.counts.upstream + " depended on.");
      } else if (tilesShown()) {
        clearTiles();
        var confT = {};
        d.downstream.forEach(function (h) { confT[h.id] = h.confidence; });
        $("tiles").querySelectorAll(".tile").forEach(function (t) {
          var tid = t.getAttribute("data-id");
          if (tid === d.root) t.classList.add("is-sel");
          else if (confT[tid]) t.classList.add("conf-" + confT[tid]);
          else t.classList.add("is-dim");
        });
        announce("Impact of " + d.rootName + ": " + d.counts.downstream + " affected, " +
          d.counts.upstream + " depended on.");
      }
    }).catch(fail);
  }

  /* ---- linkage ---------------------------------------------------------
   * Relations are where most of a model's value lives. An editor that can
   * write an entity's own fields but not its links can create things and never
   * connect them, which is how a model fills up with orphans.
   */

  /* ---- focus -----------------------------------------------------------
   * Authored views answer the questions someone thought to ask in advance.
   * The question asked while exploring is "what is around this thing", and a
   * view file per entity is not an answer to it. This builds one on demand.
   */

  function focusLabel(depth) {
    return depth + (depth === 1 ? " hop" : " hops");
  }

  function renderFocusBar() {
    var bar = $("focusBar");
    if (!state.focus) {
      bar.hidden = true;
      return;
    }
    bar.hidden = false;
    $("focusOn").textContent = state.focus.name || state.focus.id;
    $("focusDepth").textContent = focusLabel(state.focus.depth);
    $("btnFocusOut").disabled = state.focus.depth <= 1;
    $("btnFocusIn").disabled = state.focus.depth >= (state.focus.maxDepth || 4);
    var v = (state.overview.views || []).filter(function (x) {
      return x.viewId === state.viewId;
    })[0];
    $("btnFocusExit").textContent = v ? "Back to " + v.title : "Back to the view";
  }

  function showFocus(id, depth) {
    if (state.panel) showPanel(false);
    depth = Math.max(1, depth || 1);
    return api("/api/focus?id=" + encodeURIComponent(id) + "&depth=" + depth)
      .then(function (payload) {
        state.focus = {
          id: payload.focusId,
          depth: payload.depth,
          maxDepth: payload.maxDepth,
          name: (payload.title || "").split(",")[0],
        };
        state.selectedId = id;
        $("stageEmpty").hidden = true;
        renderViewList(state.overview);
        drawGraph(payload);
        renderFocusBar();
        syncUrl();
        showEntity(id);
      })
      .catch(fail);
  }

  function exitFocus() {
    if (!state.focus) return;
    var id = state.focus.id;
    state.focus = null;
    renderFocusBar();
    selectView(state.viewId);
    state.selectedId = id;
  }

  /* ---- sketch -----------------------------------------------------------
   * A sketch is the set of things an architect has picked to draw together:
   * grown from any view, one thing or a screenful at a time, plus what is
   * connected to something already in it. It lives in this browser until it
   * is written back, and it can only be written back as the repository keeps
   * things: a view file whose scope is the list itself, or a module whose
   * templates are the things rewritten in the vocabulary of the shape that
   * made them. The drawing is never the artifact; the file is.
   */
  var SKETCH_KEY = "aac.sketch";

  function sketchLoad() {
    try {
      var raw = localStorage.getItem(SKETCH_KEY);
      state.sketch = raw ? JSON.parse(raw) : [];
    } catch (err) { state.sketch = []; }
    if (!Array.isArray(state.sketch)) state.sketch = [];
  }

  function sketchStore() {
    try { localStorage.setItem(SKETCH_KEY, JSON.stringify(state.sketch)); } catch (err) { /* private mode */ }
    markSketch();
    renderSketchBar();
  }

  function inSketch(id) { return state.sketch.indexOf(id) !== -1; }

  function inSketchMode() { return !!(state.lastGraph && state.lastGraph.sketch); }

  function sketchAdd(ids) {
    var added = 0;
    ids.forEach(function (id) {
      if (id && !inSketch(id)) { state.sketch.push(id); added++; }
    });
    sketchStore();
    return added;
  }

  function sketchToggle(id) {
    if (inSketch(id)) {
      state.sketch = state.sketch.filter(function (x) { return x !== id; });
      sketchStore();
    } else {
      sketchAdd([id]);
    }
    if (inSketchMode()) drawSketch();
  }

  function markSketch() {
    if (tilesShown()) {
      $("tiles").querySelectorAll(".tile").forEach(function (t) {
        t.classList.toggle("is-sk", inSketch(t.getAttribute("data-id")));
      });
    }
    if (!state.cy) return;
    state.cy.nodes().removeClass("sk");
    state.sketch.forEach(function (id) { state.cy.getElementById(id).addClass("sk"); });
  }

  function renderSketchBar() {
    var bar = $("sketchBar");
    var n = state.sketch.length;
    var drawing = inSketchMode();
    // The bar belongs to the sheet. On the home page or a data panel it is
    // a strip of buttons above something they do not act on.
    if ((!n && !drawing) || state.panel) { bar.hidden = true; return; }
    bar.hidden = false;
    $("sketchCount").textContent = n + (n === 1 ? " thing" : " things") + (drawing ? ", drawn" : "");
    $("btnSketchExpand").disabled = !state.selectedId;
    $("btnSketchScreen").disabled = !state.cy || drawing || !state.lastGraph || /^(report|timeline)$/.test(state.lastGraph.kind);
    $("btnSketchNew").disabled = !n;
    $("btnSketchConnect").disabled = !selectedSystem() || sketchSystems().filter(function (s) {
      return s.id !== state.selectedId;
    }).length === 0;
    $("btnSketchDraw").disabled = !n || drawing;
    $("btnSketchView").disabled = !n;
    $("btnSketchModule").disabled = !n;
    $("btnSketchClear").disabled = !n;
    $("btnSketchExit").hidden = !drawing;
  }

  function drawSketch() {
    if (!state.sketch.length) {
      toast("warn", "Nothing in the sketch yet",
        "Open a thing in the inspector and press Sketch, or add everything on screen.");
      return;
    }
    if (window.__AAC_STATIC__) {
      toast("warn", "Sketches draw through the local app", "The published copy is read-only.");
      return;
    }
    if (state.panel) showPanel(false);
    var n = state.sketch.length;
    api("/api/sketch/view", { ids: state.sketch, title: "Sketch of " + n + (n === 1 ? " thing" : " things") })
      .then(function (payload) {
        state.focus = null;
        renderFocusBar();
        $("stageEmpty").hidden = true;
        drawGraph(payload);
        renderSketchBar();
      })
      .catch(fail);
  }

  function exitSketch() {
    if (!inSketchMode()) return;
    state.lastGraph = null;
    renderSketchBar();
    selectView(state.viewId);
  }

  function sketchAddScreen() {
    if (!state.cy) return;
    var ids = state.cy.nodes().filter(function (n) { return !n.data("isGroup"); })
      .map(function (n) { return n.id(); });
    var added = sketchAdd(ids);
    toast("ok", "Added " + added + " to the sketch", state.sketch.length + " in it now");
  }

  /* ---- a sketch that creates --------------------------------------------
   * Picking from what exists is half of authoring. The other half is the
   * box that is not there yet and the line between two boxes. Both go
   * through the entity editor, so the form, the validation and the file are
   * the same as for anything else; the sketch only fills in what it already
   * knows: where the picked things sit, and which two systems to join.
   */

  /* The picked things, as the search index knows them. */
  function sketchItems() {
    var byId = {};
    state.index.forEach(function (item) { byId[item.id] = item; });
    return state.sketch.map(function (id) { return byId[id] || { id: id, type: "?", name: id }; });
  }

  function sketchSystems() {
    return sketchItems().filter(function (item) { return item.type === "systems"; });
  }

  function selectedSystem() {
    if (!state.selectedId) return null;
    var item = state.index.filter(function (i) { return i.id === state.selectedId; })[0];
    return item && item.type === "systems" ? item : null;
  }

  //: Fields worth copying from a picked thing onto a new one: where it sits
  //: and who owns it, never what it is.
  var PLACEMENT_FIELDS = [
    "owner_org_id", "company_domain", "hosting", "environment", "cloud_provider",
    "cloud_account", "region", "network_zone", "data_classification_supported",
    "data_classification", "criticality", "togaf_layer", "architecture_domain",
    "abstraction_level", "service_tier", "resilience",
  ];

  /* The placement the sketch implies: the fields the first picked system
   * (or the first picked thing) carries, as defaults for a new one. */
  function sketchPlacement(type) {
    var picked = sketchSystems()[0] || sketchItems()[0];
    if (!picked) return Promise.resolve({ defaults: { status: "Planned" }, into: null });
    return api("/api/entity?id=" + encodeURIComponent(picked.id)).then(function (data) {
      var spec = state.schema.entities[type];
      var allowed = {};
      spec.fields.forEach(function (f) { allowed[f.name] = 1; });
      var out = { status: "Planned" };
      PLACEMENT_FIELDS.forEach(function (f) {
        if (allowed[f] && data.record[f] != null && data.record[f] !== "") out[f] = data.record[f];
      });
      return { defaults: out, into: instanceOf(data) };
    });
  }

  /* The product a generated thing belongs to, as {id, name}, or null. */
  function instanceOf(data) {
    var id = data.generated && data.record.archetype_instance;
    if (!id) return null;
    var item = state.index.filter(function (i) { return i.id === id; })[0];
    return { id: id, name: item ? item.name : id };
  }

  /* What kind of thing to create, then the editor with the placement filled. */
  function openSketchNew() {
    if (!state.sketch.length || readOnlyCopy("Creating")) return;
    var kinds = [
      ["systems", "A system: something that runs and is owned"],
      ["data_assets", "A data asset: something mastered, moved or stored"],
      ["tech_services", "A technology service: something the systems run on"],
      ["actors", "An actor: a person or party that uses the systems"],
    ];
    openDrawer("New thing in the sketch", state.sketch.length + " things picked", function (body) {
      body.appendChild(el("p", { class: "explain", text:
        "The editor opens with the placement of the things already picked: owner, domain, "
        + "cloud, account, zone and tier. Change what differs; the rest is inherited." }));
      var list = el("div", { class: "pick-list" });
      kinds.forEach(function (pair) {
        var spec = state.schema.entities[pair[0]];
        if (!spec) return;
        list.appendChild(el("button", { class: "pick-row as-btn", type: "button", onclick: function () {
          closeDrawer();
          sketchPlacement(pair[0]).then(function (placed) {
            openEntityEditor(pair[0], null, placed.defaults, function (id) {
              sketchAdd([id]);
              if (inSketchMode()) drawSketch();
            }, placed.into);
          }).catch(fail);
        } }, [
          el("span", { text: spec.label.charAt(0).toUpperCase() + spec.label.slice(1) }),
          el("span", { class: "via", text: pair[1] }),
        ]));
      });
      body.appendChild(list);
    }, null);
  }

  /* An interface from the selected system to another picked one. The id
   * and the name are proposed from the two ends; the editor has the rest. */
  function openSketchConnect() {
    var from = selectedSystem();
    if (!from || readOnlyCopy("Connecting")) return;
    var others = sketchSystems().filter(function (s) { return s.id !== from.id; });
    if (!others.length) return;
    openDrawer("Connect " + (from.name || from.id), "to another picked system", function (body) {
      body.appendChild(el("p", { class: "explain", text:
        "Creates an interface, which is how a connection is recorded here: a thing with a "
        + "protocol, a direction and a classification, not a line. Pick the other end." }));
      var list = el("div", { class: "pick-list" });
      others.forEach(function (to) {
        list.appendChild(el("button", { class: "pick-row as-btn", type: "button", onclick: function () {
          closeDrawer();
          proposeInterface(from.id, to.id, function (id) {
            sketchAdd([id]);
            if (inSketchMode()) drawSketch();
          });
        } }, [
          el("span", { text: to.name || to.id }),
          el("span", { class: "via mono", text: to.id }),
        ]));
      });
      body.appendChild(list);
    }, null);
  }

  /* An interface from one system to another, in the entity form with
   * everything that can be guessed filled in: the two ends, a name, the
   * owner and domain of the calling side, the usual defaults. It is a form
   * rather than a line because a connection here is a thing with a
   * protocol, a direction and a classification. */
  function proposeInterface(fromId, toId, onSaved, kind, through) {
    if (readOnlyCopy("Connecting")) return;
    Promise.all([
      api("/api/entity?id=" + encodeURIComponent(fromId)),
      api("/api/entity?id=" + encodeURIComponent(toId)),
    ]).then(function (pair) {
      var data = pair[0], a = data.record, b = pair[1].record;
      var stem = function (id) { return id.replace(/^SYS-/, ""); };
      var defaults = {
        source_system_id: fromId,
        target_system_id: toId,
        name: (a.name || fromId) + " to " + (b.name || toId),
        status: "Planned",
        protocol: "HTTPS",
        direction: "Outbound",
        integration_style: "Request-response",
        frequency: "Realtime",
      };
      ["owner_org_id", "company_domain", "togaf_layer", "architecture_domain"].forEach(function (f) {
        if (a[f]) defaults[f] = a[f];
      });
      if (a.data_classification_supported) defaults.data_classification = a.data_classification_supported;
      if (kind) {
        Object.keys(kind.defaults).forEach(function (f) {
          var v = kind.defaults[f];
          defaults[f] = Array.isArray(v) ? v.join(", ") : v;
        });
      }
      if (through) {
        defaults.offered_interface_id = through.id;
        ["protocol", "integration_style", "auth_method", "data_classification", "frequency"].forEach(function (f) {
          if (through[f]) defaults[f] = through[f];
        });
        if (through.integration_style === "Event") defaults.direction = "Outbound";
      }
      openEntityEditor("interfaces", null, defaults, onSaved, instanceOf(data));
      // The id is proposed after the form exists, so it can be changed.
      var idBox = $("drawerBody").querySelector("#f__id");
      if (idBox && !idBox.value) idBox.value = "INT-" + stem(fromId) + "-" + stem(toId);
    }).catch(fail);
  }

  /* What a system offers for others to connect to, as a new record: the
   * form with its system, owner and domain filled in, and an API's usual
   * protocol and style, every one of them editable. */
  function proposeOffered(systemId, record, data) {
    if (readOnlyCopy("Adding what a system offers")) return;
    var defaults = {
      system_id: systemId,
      name: (record.name || systemId).replace(/ Service$/, "") + " API",
      status: record.status || "Planned",
      protocol: "HTTPS",
      integration_style: "Request-response",
      auth_method: "OAuth2",
      togaf_layer: "Application",
      architecture_domain: "Application",
    };
    ["owner_org_id", "company_domain"].forEach(function (f) { if (record[f]) defaults[f] = record[f]; });
    if (record.data_classification_supported) defaults.data_classification = record.data_classification_supported;
    openEntityEditor("offered_interfaces", null, defaults, null, instanceOf(data));
    var idBox = $("drawerBody").querySelector("#f__id");
    if (idBox && !idBox.value) idBox.value = "OI-" + systemId.replace(/^SYS-/, "").replace(/-API$/, "") + "-API";
  }

  /* ---- connecting two things ----------------------------------------------
   * Drop one box on another, or choose Connect to and pick the other end, and
   * the chooser lists every way the metamodel lets those two kinds of thing
   * be joined, both ways round: a relation row, an interface between two
   * systems, one of them naming the other in a field. Nothing it offers can
   * be refused for its types, and what is already recorded is shown as
   * recorded rather than offered twice. A connection made on a drawing that
   * does not draw that kind of line says so, and offers to draw it.
   */
  function connectFrom(id) {
    if (readOnlyCopy("Connecting")) return;
    var item = (state.index || []).filter(function (x) { return x.id === id; })[0];
    openPicker({
      placeholder: "Connect " + (item && item.name || id) + " to: type a name or an id…",
      skip: function (other) { return other === id; },
      onPick: function (other) { openConnectChooser(id, other); },
    });
  }

  function connectSentence(opt, names) {
    var a = names[opt.from] || opt.from, b = names[opt.to] || opt.to;
    if (opt.kind === "through") {
      // One end is the interface's owner, which was not one of the two dropped.
      var nameOf = function (sid) { return sid === opt.door.system ? opt.ownerName || sid : names[sid] || sid; };
      return nameOf(opt.from) + (opt.door.integration_style === "Event" ? " publishes to " : " calls ")
        + nameOf(opt.to) + " through " + opt.door.name;
    }
    if (opt.kind === "interface") return a + " calls " + b;
    if (opt.kind === "field") return a + " " + (FIELD_PHRASES[opt.field] || opt.field.replace(/_id$/, "").replace(/_/g, " ")) + " " + b;
    return a + " " + relationPhrase(opt.relation, "out") + " " + b;
  }

  function connectHint(opt, names) {
    if (opt.kind === "through") {
      if (opt.exists) return "recorded as " + opt.existing.join(", ");
      return "a new connection, " + ([opt.door.protocol, opt.door.auth_method].filter(Boolean).join(", ")
        || "as the interface says");
    }
    if (opt.kind === "interface") {
      if (opt.exists) return "recorded as " + opt.existing.join(", ")
        + (opt.existingKinds && opt.existingKinds.length ? " (" + opt.existingKinds.join(", ").toLowerCase() + ")" : "");
      return "a new interface" + (opt.kinds && opt.kinds.length ? ", by one of " + opt.kinds.length + " kinds" : "");
    }
    if (opt.kind === "field") {
      if (!opt.editable) return opt.why || "not editable here";
      if (opt.exists) return "recorded";
      return opt.current ? "instead of " + (names[opt.current] || opt.current) : "sets " + opt.field.replace(/_/g, " ");
    }
    if (opt.exists) return "recorded" + (opt.existing.filter(Boolean).length ? " as " + opt.existing.filter(Boolean).join(", ") : "");
    return opt.qualifier ? "with its " + opt.qualifier.replace(/_/g, " ") : "a new link";
  }

  /* A chooser where the drop was, kept on the screen; with no point given,
   * centered near the top of the sheet. */
  function placeChooser(menu, x, y) {
    document.body.appendChild(menu);
    var r = menu.getBoundingClientRect(), sheet = $("cy").getBoundingClientRect();
    var px = x === undefined ? sheet.left + sheet.width / 2 - r.width / 2 : x;
    var py = y === undefined ? sheet.top + 80 : y;
    menu.style.left = Math.max(8, Math.min(px, window.innerWidth - r.width - 8)) + "px";
    menu.style.top = Math.max(8, Math.min(py, window.innerHeight - r.height - 8)) + "px";
    var first = menu.querySelector("button:not([disabled]), input");
    if (first) first.focus();
  }

  function openConnectChooser(a, b, x, y) {
    closeContextMenu();
    var q = "/api/connect/options?from=" + encodeURIComponent(a) + "&to=" + encodeURIComponent(b)
      + (viewEditable() || (cv && cv.id) ? "&view=" + encodeURIComponent(state.viewId) : "");
    api(q).then(function (d) {
      var names = {};
      names[d.from.id] = d.from.name;
      names[d.to.id] = d.to.name;
      var menu = el("div", { class: "ctx-menu connect-menu", id: "ctxMenu", role: "dialog",
        "aria-label": "Connect " + d.from.name + " and " + d.to.name });
      function place() { placeChooser(menu, x, y); }
      function list() {
        menu.textContent = "";
        menu.appendChild(el("div", { class: "ctx-head", text: "Connect " + d.from.name + " and " + d.to.name }));
        var open = d.options.filter(function (o) { return !o.exists && o.editable !== false; });
        var done = d.options.filter(function (o) { return o.exists; });
        var blocked = d.options.filter(function (o) { return !o.exists && o.editable === false; });
        if (!d.options.length) {
          menu.appendChild(el("p", { class: "connect-none", text:
            "Nothing in the metamodel joins a " + d.from.type.replace(/_/g, " ").replace(/s$/, "")
            + " to a " + d.to.type.replace(/_/g, " ").replace(/s$/, "") + " directly." }));
        }
        open.forEach(function (o) {
          menu.appendChild(el("button", { type: "button", class: "connect-opt", onclick: function () { choose(o); } }, [
            el("span", { class: "co-s", text: connectSentence(o, names) }),
            el("span", { class: "co-h", text: connectHint(o, names) }),
          ]));
        });
        if (done.length || blocked.length) menu.appendChild(el("div", { class: "ctx-sep", role: "separator" }));
        done.concat(blocked).forEach(function (o) {
          menu.appendChild(el("button", { type: "button", class: "connect-opt is-done", disabled: "disabled" }, [
            el("span", { class: "co-s", text: connectSentence(o, names) }),
            el("span", { class: "co-h", text: connectHint(o, names) }),
          ]));
        });
        menu.appendChild(el("div", { class: "ctx-sep", role: "separator" }));
        menu.appendChild(el("button", { type: "button", class: "connect-more", text: "Every link of " + d.from.name + "…",
          onclick: function () { closeContextMenu(); openLinkEditor(a); } }));
      }
      function choose(o) {
        if (o.kind === "through") {
          closeContextMenu();
          proposeInterface(o.from, o.to, function () { afterConnect(o, names); }, null, o.door);
          return;
        }
        if (o.kind === "interface") {
          if (o.offered && o.offered.length) { askThrough(o); return; }
          if (o.kinds && o.kinds.length) { askKind(o); return; }
          closeContextMenu();
          proposeInterface(o.from, o.to, function () { afterConnect(o, names); });
          return;
        }
        if (o.kind === "relation" && o.qualifier) { askQualifier(o); return; }
        write(o, "");
      }
      /* Which of what the two offer the connection goes through: the API
       * the one called offers, or the topic the one publishing does. One
       * fills the form from the interface; none goes on to the kinds. */
      function askThrough(o) {
        menu.textContent = "";
        menu.appendChild(el("div", { class: "ctx-head", text: connectSentence(o, names) }));
        menu.appendChild(el("p", { class: "connect-ask", text: "Through which of what they offer?" }));
        o.offered.forEach(function (door) {
          menu.appendChild(el("button", { type: "button", class: "connect-opt", onclick: function () {
            closeContextMenu();
            proposeInterface(o.from, o.to, function () { afterConnect(o, names); }, null, door);
          } }, [
            el("span", { class: "co-s", text: door.name }),
            el("span", { class: "co-h", text: [door.systemName, door.protocol, door.auth_method].filter(Boolean).join(" \u00b7 ") }),
          ]));
        });
        menu.appendChild(el("div", { class: "ctx-sep", role: "separator" }));
        menu.appendChild(el("button", { type: "button", class: "connect-opt", onclick: function () {
          if (o.kinds && o.kinds.length) { askKind(o); return; }
          closeContextMenu();
          proposeInterface(o.from, o.to, function () { afterConnect(o, names); });
        } }, [
          el("span", { class: "co-s", text: "Not through one of these" }),
          el("span", { class: "co-h", text: "a connection of one of the kinds" }),
        ]));
        menu.appendChild(el("div", { class: "connect-acts" }, [
          el("button", { type: "button", class: "btn small", text: "Back", onclick: function () { list(); place(); } }),
        ]));
        place();
      }

      /* How one system calls the other, from the library's connection
       * kinds: each fills the interface form with its protocol, its
       * authentication, its frequency and the pattern it applies. */
      function askKind(o) {
        menu.textContent = "";
        menu.appendChild(el("div", { class: "ctx-head", text: connectSentence(o, names) }));
        menu.appendChild(el("p", { class: "connect-ask", text: "How? Each fills the form in; everything stays editable." }));
        o.kinds.forEach(function (k) {
          var said = [k.defaults.protocol, k.defaults.auth_method].filter(Boolean).join(", ")
            + (k.patterns.length ? " · " + k.patterns.join(", ") : "");
          menu.appendChild(el("button", { type: "button", class: "connect-opt", title: k.description,
            onclick: function () {
              closeContextMenu();
              proposeInterface(o.from, o.to, function () { afterConnect(o, names); }, k);
            } }, [
            el("span", { class: "co-s", text: k.name }),
            el("span", { class: "co-h", text: said }),
          ]));
        });
        menu.appendChild(el("div", { class: "ctx-sep", role: "separator" }));
        menu.appendChild(el("button", { type: "button", class: "connect-opt", onclick: function () {
          closeContextMenu();
          proposeInterface(o.from, o.to, function () { afterConnect(o, names); });
        } }, [
          el("span", { class: "co-s", text: "Some other way" }),
          el("span", { class: "co-h", text: "the form with the usual defaults" }),
        ]));
        menu.appendChild(el("div", { class: "connect-acts" }, [
          el("button", { type: "button", class: "btn small", text: "Back", onclick: function () { list(); place(); } }),
        ]));
        place();
      }

      function askQualifier(o) {
        menu.textContent = "";
        var word = o.qualifier.replace(/_/g, " ");
        menu.appendChild(el("div", { class: "ctx-head", text: connectSentence(o, names) }));
        menu.appendChild(el("p", { class: "connect-ask", text: "Its " + word + ", if it has one:" }));
        var row = el("div", { class: "connect-values" });
        o.values.forEach(function (v) {
          row.appendChild(el("button", { type: "button", class: "btn small", text: v, onclick: function () { write(o, v); } }));
        });
        menu.appendChild(row);
        var input = el("input", { type: "text", class: "connect-input", placeholder: o.values.length ? "Or another" : "Type it",
          "aria-label": "The " + word });
        input.addEventListener("keydown", function (e) {
          if (e.key === "Enter" && input.value.trim()) { e.preventDefault(); write(o, input.value.trim()); }
        });
        menu.appendChild(input);
        menu.appendChild(el("div", { class: "connect-acts" }, [
          el("button", { type: "button", class: "btn small", text: "Back", onclick: function () { list(); place(); } }),
          el("button", { type: "button", class: "btn small", text: "Without one", onclick: function () { write(o, input.value.trim()); } }),
        ]));
        place();
        // Typing is the quick way to an answer; the suggestions are a click.
        input.focus();
      }
      function write(o, qualifier) {
        closeContextMenu();
        var call = o.kind === "field"
          ? api("/api/save", { type: o.from === d.from.id ? d.from.type : d.to.type, id: o.from, patch: true,
              values: (function () { var v = {}; v[o.field] = o.to; return v; })() })
          : api("/api/relate", { relation: o.relation, left: o.from, right: o.to, qualifier: qualifier });
        call.then(function () { afterConnect(o, names); }).catch(fail);
      }
      menu.addEventListener("keydown", function (e) {
        if (e.key === "Escape") { e.preventDefault(); closeContextMenu(); }
      });
      list();
      place();
    }).catch(fail);
  }

  function afterConnect(o, names) {
    var via = o.kind === "interface" || o.kind === "through" ? "interfaces" : o.kind === "field" ? o.field : o.relation;
    var said = connectSentence(o, names);
    if (cv) {
      var edges = cv.data.edges || (cv.data.edges = []);
      var added = o.drawn === false && !edges.some(function (e) { return e.via === via; });
      if (added) edges.push({ via: via });
      toast("ok", "Connected: " + said, added ? "The diagram draws " + edgeWord(via) + " lines now." : "");
      cv.focus = { id: o.to, also: o.from };
      loadIndex();
      (added ? canvasSave() : Promise.resolve()).then(canvasDraw).catch(fail);
      return;
    }
    if (o.drawn === false && viewEditable()) {
      toast("ok", "Connected: " + said, "This view does not draw that kind of line yet.",
        { label: "Draw them here", go: function () { drawLinesHere(via); } });
    } else {
      toast("ok", "Connected: " + said);
    }
    if (state.viewId && !state.focus && !inSketchMode()) selectView(state.viewId);
    else refresh();
  }

  /* The view's `edges` with one more kind on it, written through the
   * composer's save so the rest of the file stays as it was. A view with no
   * `edges` draws interfaces, so that is written out rather than lost. */
  function drawLinesHere(via) {
    if (!viewEditable()) return;
    var viewId = state.viewId;
    api("/api/view?id=" + encodeURIComponent(viewId)).then(function (d) {
      if (!d.data) throw new Error("the view's file does not parse");
      var data = d.data;
      var edges = (data.edges && data.edges.length) ? data.edges.slice() : [{ via: "interfaces" }];
      if (edges.some(function (e) { return e.via === via; })) return null;
      edges.push({ via: via });
      data.edges = edges;
      return api("/api/view/compose", { id: viewId, data: data });
    }).then(function (res) {
      if (!res) return;
      toast("ok", "This view draws " + edgeWord(via) + " lines now", "Saved in " + res.path + ".");
      selectView(viewId);
    }).catch(fail);
  }

  /* ---- moving a box into another boundary ----------------------------------
   * A boundary is one value of a field the view groups by, so dropping a box
   * into another one sets that field on the record, and the box moves on
   * every drawing grouped by it. The chooser says so before anything is
   * written: the field from and to, the other views the box moves on,
   * joins or comes off, and for a record made by a shape or brought in by an
   * import, why it cannot be moved from here. Confirming is the one-field
   * save, and Undo is the same save with the old value.
   */
  var REGROUP_EFFECT = { joins: "it joins this one", leaves: "it comes off this one" };

  function openRegroupChooser(id, group, x, y) {
    closeContextMenu();
    if (readOnlyCopy("Moving a box")) return;
    var into = group.ancestors().add(group).filter(function (g) { return !!g.data("field"); })
      .sort(function (a, b) { return (a.data("depth") || 0) - (b.data("depth") || 0); })
      .map(function (g) { return { field: g.data("field"), value: g.data("stored") }; });
    var where = group.data("value");
    var shown = ((state.lastGraph || {}).parameters || [])[0];
    api("/api/regroup/options", { id: id, into: into, view: state.viewId, subject: shown ? shown.value : "" })
      .then(function (d) {
        if (!d.changes.length && !d.blocked) return;
        var name = d.entity.name;
        var menu = el("div", { class: "ctx-menu connect-menu regroup-menu", id: "ctxMenu", role: "dialog",
          "aria-label": "Move " + name + " into " + where });
        menu.appendChild(el("div", { class: "ctx-head", text: "Move " + name + " into " + where }));
        menu.addEventListener("keydown", function (e) {
          if (e.key === "Escape") { e.preventDefault(); closeContextMenu(); }
        });
        if (d.blocked) {
          menu.appendChild(el("p", { class: "connect-none", text: d.blocked }));
          menu.appendChild(el("div", { class: "connect-acts" }, [
            el("button", { type: "button", class: "btn small", text: "Close", onclick: closeContextMenu }),
          ]));
          placeChooser(menu, x, y);
          return;
        }
        d.changes.forEach(function (c) {
          menu.appendChild(el("p", { class: "regroup-change" }, [
            "Sets its " + c.words + " to ", el("b", { text: c.afterLabel || String(c.after) }),
            c.beforeLabel ? ", from " + c.beforeLabel + "." : "; it has none now.",
          ]));
        });
        var words = d.changes.map(function (c) { return c.words; }).join(" or ");
        var here = d.drawings.filter(function (w) { return w.here; })[0];
        var others = d.drawings.filter(function (w) { return !w.here; });
        if (!others.length) {
          menu.appendChild(el("p", { class: "regroup-where", text:
            "No other view is grouped by " + words + ", so this is the only one it moves on." }));
        } else {
          menu.appendChild(el("p", { class: "regroup-where", text:
            "That is a change to the record, so it moves on every view grouped by " + words + ". "
            + (others.length === 1 ? "One other:" : others.length + " others:") }));
          var list = el("ul", { class: "regroup-views" });
          others.slice(0, 8).forEach(function (w) {
            list.appendChild(el("li", {}, [
              el("span", { class: "co-s", text: w.title + (w.subjectName ? ", for " + w.subjectName : "") }),
              REGROUP_EFFECT[w.effect] ? el("span", { class: "co-h", text: REGROUP_EFFECT[w.effect] }) : null,
            ]));
          });
          if (others.length > 8) list.appendChild(el("li", { class: "co-h", text: "and " + (others.length - 8) + " more" }));
          menu.appendChild(list);
        }
        if (here && here.effect === "leaves") {
          menu.appendChild(el("p", { class: "regroup-where", text:
            "It comes off this view too: what this view selects depends on its " + words + "." }));
        }
        if (d.note) menu.appendChild(el("p", { class: "regroup-where", text: d.note }));
        menu.appendChild(el("div", { class: "connect-acts" }, [
          el("button", { type: "button", class: "btn small", text: "Cancel", onclick: closeContextMenu }),
          el("button", { type: "button", class: "btn small primary", text: "Move it", onclick: function () { move(d); } }),
        ]));
        placeChooser(menu, x, y);
      }).catch(fail);

    function move(d) {
      closeContextMenu();
      var values = {}, back = {};
      d.changes.forEach(function (c) {
        values[c.field] = c.after;
        back[c.field] = c.before === null ? "" : c.before;
      });
      var fields = d.changes.map(function (c) { return c.words; }).join(" and ");
      fields = fields.charAt(0).toUpperCase() + fields.slice(1);
      function save(v) {
        return api("/api/save", { type: d.entity.type, id: d.entity.id, patch: true, values: v });
      }
      save(values).then(function (res) {
        toast("ok", "Moved " + d.entity.name + " into " + where,
          fields + " set in " + res.path + "." + (res.moved ? " " + res.moved : ""),
          { label: "Undo", go: function () {
            save(back).then(function (r) {
              toast("ok", "Undone", "Saved in " + r.path + ".");
              redrawAfterMove(d.entity.id);
            }).catch(fail);
          } });
        redrawAfterMove(d.entity.id);
      }).catch(fail);
    }
  }

  // The drawing again from the model, with the moved box selected so the
  // eye finds where it went.
  function redrawAfterMove(id) {
    if (cv) {
      cv.focus = { id: id, keep: true, zoom: state.cy ? state.cy.zoom() : null };
      canvasDraw().then(function () { if (cv) canvasSelect({ kind: "record", id: id }); });
      return;
    }
    var drawn = state.viewId && !state.focus && !inSketchMode() ? selectView(state.viewId) : refresh();
    Promise.resolve(drawn).then(function () { if (drawnHere(id)) showEntity(id); });
  }

  /* What is connected to one thing, as a pick list grouped by relation. */
  function openSketchExpand(id) {
    api("/api/entity?id=" + encodeURIComponent(id)).then(function (data) {
      openDrawer("Add what is connected", (data.record.name || id), function (body) {
        if (!data.related.length) {
          body.appendChild(el("p", { class: "brief-hint", text: "Nothing is connected to this." }));
          return;
        }
        body.appendChild(el("p", { class: "explain", text:
          "Everything one hop from " + (data.record.name || id) + ", by relation. Untick what "
          + "the sketch does not need." }));
        var groups = {};
        data.related.forEach(function (rel) {
          (groups[rel.relation] = groups[rel.relation] || []).push(rel);
        });
        Object.keys(groups).sort().forEach(function (relation) {
          body.appendChild(el("p", { class: "group-title", text: relation.replace(/_/g, " ") + " · " + groups[relation].length }));
          var list = el("div", { class: "pick-list" });
          groups[relation].forEach(function (rel) {
            var already = inSketch(rel.otherId);
            var box = el("input", { type: "checkbox", "data-pick": rel.otherId });
            box.checked = !already;
            box.disabled = already;
            list.appendChild(el("label", { class: "pick-row" + (already ? " is-in" : "") }, [
              box,
              el("span", { text: rel.otherName || rel.otherId }),
              el("span", { class: "via mono", text: already ? "in the sketch" : (rel.qualifier || (rel.direction === "out" ? "→" : "←")) }),
            ]));
          });
          body.appendChild(list);
        });
      }, function () {
        var body = $("drawerBody");
        var ids = [];
        Array.prototype.forEach.call(body.querySelectorAll("[data-pick]"), function (box) {
          if (box.checked && !box.disabled) ids.push(box.getAttribute("data-pick"));
        });
        var added = sketchAdd(ids);
        toast("ok", "Added " + added + " to the sketch", state.sketch.length + " in it now");
        if (inSketchMode()) drawSketch();
        return Promise.resolve(true);
      });
    }).catch(fail);
  }

  /* The sketch as a view file. The form asks what a view file needs and the
   * server writes the query; saving goes through the same door as a typed
   * view, so it is validated the same way. */
  function readOnlyCopy(what) {
    if (!window.__AAC_STATIC__) return false;
    toast("warn", what + " writes to the model on disk", "It runs in the local app; the published copy is read-only.");
    return true;
  }

  function openSketchView() {
    if (!state.sketch.length || readOnlyCopy("Saving a view")) return;
    api("/api/view").then(function (info) {
      var help = info.help || {};
      var categories = {};
      (state.overview.views || []).forEach(function (v) { if (v.category) categories[v.category] = 1; });
      var stamp = new Date().toISOString().slice(0, 10);
      openDrawer("Save the sketch as a view", state.sketch.length + " things", function (body) {
        body.appendChild(el("p", { class: "explain", text:
          "Written to 30_VIEWS/ as a query whose scope is the list of things in the sketch. "
          + "It renders with every other view from then on; widen it in the editor when the "
          + "picture becomes a standing question." }));
        function field(id, label, input, hint) {
          var lab = el("label", { for: id }, [label]);
          if (hint) lab.appendChild(el("span", { class: "hint", text: hint }));
          body.appendChild(el("div", { class: "field" }, [lab, input]));
          return input;
        }
        field("sk_id", "view id", el("input", { id: "sk_id", type: "text", value: "sketch-" + stamp }),
          "letters, digits, . _ -");
        field("sk_title", "title", el("input", { id: "sk_title", type: "text", value: "Sketch " + stamp }));
        field("sk_desc", "description", el("textarea", { id: "sk_desc", rows: "3" }),
          "the question this diagram answers, and what to do about what it shows");
        var cat = el("input", { id: "sk_cat", type: "text", value: "Sketches", list: "sk_cats" });
        var dl = el("datalist", { id: "sk_cats" });
        Object.keys(categories).sort().forEach(function (c) { dl.appendChild(el("option", { value: c })); });
        field("sk_cat", "category", cat, "which shelf it sits on in the rail");
        body.appendChild(dl);
        var gsel = el("select", { id: "sk_group", multiple: "multiple", size: "6" });
        (help.groupFields || []).forEach(function (g) { gsel.appendChild(el("option", { value: g, text: g })); });
        field("sk_group", "group by", gsel, "boundaries, outermost first; leave empty for none");
        var csel = el("select", { id: "sk_color" });
        csel.appendChild(el("option", { value: "type", text: "type" }));
        (help.groupFields || []).forEach(function (g) { csel.appendChild(el("option", { value: g, text: g })); });
        field("sk_color", "color by", csel, "the dimension on the border and tint");
        var lsel = el("select", { id: "sk_layout" });
        lsel.appendChild(el("option", { value: "LR", text: "Left to right" }));
        lsel.appendChild(el("option", { value: "TB", text: "Top to bottom" }));
        field("sk_layout", "layout", lsel);
      }, function () {
        var body = $("drawerBody");
        var groupBy = Array.prototype.filter.call(body.querySelector("#sk_group").options, function (o) { return o.selected; })
          .map(function (o) { return o.value; });
        var spec = {
          ids: state.sketch,
          id: body.querySelector("#sk_id").value.trim(),
          title: body.querySelector("#sk_title").value.trim(),
          description: body.querySelector("#sk_desc").value.trim(),
          category: body.querySelector("#sk_cat").value.trim(),
          groupBy: groupBy,
          colorBy: body.querySelector("#sk_color").value,
          layout: body.querySelector("#sk_layout").value,
        };
        if (!spec.id || !spec.title) { toast("err", "A view needs an id and a title"); return Promise.resolve(false); }
        return api("/api/sketch/view", spec).then(function (payload) {
          return api("/api/view/save", { text: payload.text });
        }).then(function (saved) {
          toast("ok", (saved.created ? "Created " : "Saved ") + saved.path,
            saved.counts.nodes + " nodes, " + saved.counts.edges + " edges");
          // The refresh picks the view it finds in `state.viewId`, so the
          // new one is set before it runs rather than selected after it.
          state.lastGraph = null;
          state.focus = null;
          state.viewId = saved.id;
          window.history.replaceState(null, "", "#view=" + encodeURIComponent(saved.id));
          return Promise.resolve(refresh()).then(function () { return true; });
        });
      });
    }).catch(fail);
  }

  /* The sketch as a module: the things rewritten as templates, in the
   * vocabulary of the shape that made them, so the next product gets the
   * same part from the library. The text is shown and can be edited before
   * it is written. */
  function openSketchModule() {
    if (!state.sketch.length || readOnlyCopy("Saving a module")) return;
    api("/api/sketch/module", { ids: state.sketch }).then(function (first) {
      var report = first.report || {};
      openDrawer("Save the sketch as a module", state.sketch.length + " things", function (body) {
        body.appendChild(el("p", { class: "explain", text:
          "Written to " + (first.folder || "28_MODULES/") + " as a part with parameters. Ids and names become tokens, "
          + "fields the shape's defaults already supply are dropped, and platform use and "
          + "governance come back as shorthands. Read the text before saving: it is the file." }));
        function field(id, label, input, hint) {
          var lab = el("label", { for: id }, [label]);
          if (hint) lab.appendChild(el("span", { class: "hint", text: hint }));
          body.appendChild(el("div", { class: "field" }, [lab, input]));
          return input;
        }
        field("sm_id", "module id", el("input", { id: "sm_id", type: "text", placeholder: "e.g. private-vendor-path" }));
        field("sm_name", "name", el("input", { id: "sm_name", type: "text", placeholder: "e.g. Private vendor path" }));
        field("sm_cat", "category", el("input", { id: "sm_cat", type: "text", value: "Other" }),
          "Integration, Identity, Network, Data, Security, Operations, Vendor…");
        field("sm_desc", "description", el("textarea", { id: "sm_desc", rows: "3" }),
          "what the part is and why it exists; the form shows it");
        field("sm_slug", "slug", el("input", { id: "sm_slug", type: "text", value: report.guessedSlug || "" }),
          "the product token in the ids, replaced by {slug}");
        field("sm_product", "product name", el("input", { id: "sm_product", type: "text" }),
          "replaced by {product_name} where it appears; blank to use the shape's binding");
        var opt = el("input", { id: "sm_opt", type: "checkbox" });
        opt.checked = true;
        body.appendChild(el("div", { class: "field" }, [
          el("label", { class: "part-head", for: "sm_opt" }, [opt, el("span", { text: "optional: an instance may drop it" })]),
        ]));
        body.appendChild(el("div", { class: "acts" }, [
          el("button", { class: "btn small", type: "button", text: "Regenerate", onclick: regenerate }),
        ]));
        var line = el("p", { class: "sketch-report", id: "sm_report" });
        body.appendChild(line);
        var area = el("textarea", { class: "mono wide", id: "sm_text", spellcheck: "false" });
        area.value = first.text || "";
        body.appendChild(area);
        showReport(report);
        function showReport(r) {
          line.textContent = "";
          if (r.exists) {
            line.appendChild(el("span", { class: "editor-status is-bad", text: "A module with this id already exists. " }));
          }
          line.appendChild(el("span", { text: r.entities + " entities, " + r.recovered + " relations recovered, "
            + Object.keys(r.dropped || {}).length + " default fields dropped"
            + (r.generatedFrom ? ", vocabulary of " + r.generatedFrom : ", hand-authored") + ". " }));
          (r.tokens || []).forEach(function (t) { line.appendChild(el("code", { class: "help-chip", text: t })); });
        }
        function regenerate() {
          api("/api/sketch/module", {
            ids: state.sketch,
            module_id: body.querySelector("#sm_id").value.trim(),
            name: body.querySelector("#sm_name").value.trim(),
            category: body.querySelector("#sm_cat").value.trim(),
            description: body.querySelector("#sm_desc").value.trim(),
            slug: body.querySelector("#sm_slug").value.trim(),
            product_name: body.querySelector("#sm_product").value.trim(),
            optional: body.querySelector("#sm_opt").checked,
          }).then(function (res) {
            area.value = res.text;
            showReport(res.report || {});
          }).catch(fail);
        }
        ["sm_id", "sm_name", "sm_cat", "sm_desc", "sm_slug", "sm_product", "sm_opt"].forEach(function (id) {
          body.querySelector("#" + id).addEventListener("change", regenerate);
        });
      }, function () {
        var body = $("drawerBody");
        var text = body.querySelector("#sm_text").value;
        if (!body.querySelector("#sm_id").value.trim()) { toast("err", "A module needs an id"); return Promise.resolve(false); }
        return api("/api/module/save", { text: text }).then(function (saved) {
          toast("ok", (saved.created ? "Created " : "Saved ") + saved.path,
            saved.errors.length ? saved.errors.length + " model errors" : "The library has it now");
          return true;
        });
      });
    }).catch(fail);
  }

  /* ---- diagram source ---------------------------------------------------
   * A PNG is what you show someone. The source is what you commit, paste into
   * a pull request, or hand to a wiki that renders Mermaid itself. A focus
   * view has no artifact on disk, so this is the only way to get one out.
   */

  function copyText(text, label) {
    function fallback() {
      var box = document.createElement("textarea");
      box.value = text;
      box.setAttribute("readonly", "");
      box.style.cssText = "position:fixed;top:-1000px";
      document.body.appendChild(box);
      box.select();
      var ok = false;
      try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
      document.body.removeChild(box);
      toast(ok ? "ok" : "err", ok ? "Copied " + label : "Could not copy",
        ok ? null : "Select the text and copy it by hand.");
    }
    if (!navigator.clipboard || !navigator.clipboard.writeText) return fallback();
    navigator.clipboard.writeText(text).then(function () {
      toast("ok", "Copied " + label);
    }, fallback);
  }

  /* ---- the view editor -------------------------------------------------
   * Every diagram in here is a query, so the honest thing to let someone edit
   * is the query. A canvas would let them draw a picture the model does not
   * support, and the whole point is that the two cannot drift apart.
   */

  var VIEW_HELP_GROUPS = [
    ["Entity types", "types", "scope.include[].type"],
    ["Edge kinds", "edgeVia", "edges[].via"],
    ["Group by", "groupFields", "group_by"],
  ];

  function helpList(title, items, where) {
    var box = el("details", { class: "help-box" }, [
      el("summary", {}, [
        el("span", { text: title }),
        el("span", { class: "help-where mono", text: where }),
      ]),
    ]);
    var wrap = el("div", { class: "help-chips" });
    items.forEach(function (item) {
      wrap.appendChild(el("code", { class: "help-chip", text: item }));
    });
    box.appendChild(wrap);
    return box;
  }

  function openViewEditor(viewId, initialText) {
    var q = viewId ? "?id=" + encodeURIComponent(viewId) : "";
    api("/api/view" + q).then(function (d) {
      var readOnly = !!window.__AAC_STATIC__;
      var area, status;

      openDrawer(readOnly ? "View source" : d.isNew ? "New view" : "Edit view", d.path, function (body) {
        $("drawer").classList.add("wide");

        body.appendChild(el("p", { class: "explain", text: d.isNew
          ? "A view is a query, not a drawing. Describe what belongs on the diagram " +
            "and the engine draws it — which is why a new system appears on every " +
            "view it matches without anyone reopening this."
          : "Editing the query behind the diagram. Preview draws it without writing " +
            "anything; Save writes the file and reloads the model." }));

        area = el("textarea", {
          class: "code-area mono",
          spellcheck: "false",
          autocomplete: "off",
          "aria-label": "View source",
        });
        area.value = typeof initialText === "string" ? initialText : d.text;
        area.readOnly = readOnly;
        area.addEventListener("keydown", codeTab);

        status = el("p", { class: "editor-status", text: readOnly
          ? "The hosted demo is read-only. This is the file as committed."
          : "Not previewed yet." });

        // Preview needs the engine, so it is not offered where there is none.
        // The view it would draw is already on the canvas behind this anyway.
        var acts = el("div", { class: "editor-acts" });
        if (!readOnly) {
          acts.appendChild(el("button", {
            class: "btn small", type: "button", text: "Preview",
            title: "Draw it without saving",
            onclick: function () { previewView(); },
          }));
        }
        if (!readOnly) {
          // Back to the parts with whatever the text now says, read by the
          // server's own parser, so nothing typed here is lost on the way.
          acts.appendChild(el("button", {
            class: "btn small", type: "button", text: "Back to the parts",
            onclick: function () {
              api("/api/view/preview", { text: area.value }).then(function (payload) {
                openViewComposer(d.isNew ? null : d.id, payload.data);
              }).catch(function (err) {
                status.className = "editor-status is-bad";
                status.textContent = err.message;
              });
            },
          }));
        }
        if (!d.isNew && !readOnly) {
          acts.appendChild(el("button", {
            class: "btn small danger", type: "button", text: "Delete view",
            onclick: function () { deleteView(d.id); },
          }));
        }

        var help = el("div", { class: "editor-help" });
        VIEW_HELP_GROUPS.forEach(function (group) {
          var items = d.help[group[1]] || [];
          if (items.length) help.appendChild(helpList(group[0], items, group[2]));
        });
        var ops = el("details", { class: "help-box" }, [
          el("summary", {}, [
            el("span", { text: "where operators" }),
            el("span", { class: "help-where mono", text: "scope.include[].where" }),
          ]),
        ]);
        var opList = el("dl", { class: "help-ops" });
        d.help.operators.forEach(function (op) {
          opList.appendChild(el("dt", { class: "mono", text: op.name }));
          opList.appendChild(el("dd", { text: op.note }));
        });
        ops.appendChild(opList);
        help.appendChild(ops);

        body.appendChild(el("div", { class: "editor-grid" }, [
          el("div", { class: "editor-main" }, [area, status, acts]),
          help,
        ]));

        function previewView() {
          status.className = "editor-status";
          status.textContent = "Drawing\u2026";
          api("/api/view/preview", { text: area.value }).then(function (payload) {
            state.preview = true;
            $("stageEmpty").hidden = true;
            drawGraph(payload);
            status.className = "editor-status is-ok";
            status.textContent = "Draws " + payload.counts.nodes + " nodes and " +
              payload.counts.edges + " edges. Nothing saved yet." +
              (payload.notes.length ? " " + payload.notes.join(" ") : "");
          }).catch(function (err) {
            status.className = "editor-status is-bad";
            status.textContent = err.message;
          });
        }

        function deleteView(id) {
          if (!window.confirm("Delete the view " + id + "? This removes its file from 30_VIEWS.")) return;
          api("/api/view/delete", { id: id }).then(function (res) {
            toast("ok", "Deleted " + id, res.path);
            closeDrawer();
            state.viewId = null;
            refresh();
          }).catch(fail);
        }
      }, readOnly ? null : function () {
        return api("/api/view/save", { id: d.isNew ? "" : d.id, text: area.value })
          .then(function (res) {
            if (res.problem) {
              toast("warn", "Saved, but it draws nothing", res.problem);
            } else {
              toast(res.errors.length ? "warn" : "ok",
                (res.created ? "Created " : "Saved ") + res.id,
                res.errors.length ? res.errors[0]
                  : res.counts.nodes + " nodes · " + res.counts.edges + " edges");
            }
            state.preview = false;
            state.viewId = res.id;
            return refresh().then(function () { return true; });
          });
      });
    }).catch(fail);
  }

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

  var CANVAS_HINT = "Draw it: press + or drag a part in. Whatever is selected shows its details on the right.";

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
        saving: Promise.resolve(), status: viewId ? "saved" : "fresh", timer: null, fieldTimers: {}, focus: null };
      if (viewId) state.viewId = viewId;
      state.selectedId = null;
      document.querySelector(".shell").classList.add("canvas-mode");
      $("cvTools").hidden = false;
      $("cvDetails").hidden = false;
      setCanvasTool("select");
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
    document.querySelector(".shell").classList.remove("canvas-mode");
    ["cvTools", "cvChips", "cvEmpty", "cvDetails", "cvFold", "cvTip", "cvLayout", "cvGuideX", "cvGuideY"]
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

  function canvasEmpty(c) {
    var s = (c || cv).data.scope || {};
    return !((c || cv).data.places || []).length && !(s.pin || []).length && !(s.include || []).length;
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
    // Positions are where the things on it sit; with nothing on it there is
    // nowhere, and an empty object is not written either.
    if (canvasEmpty(c) || (data.positions && !Object.keys(data.positions).length)) delete data.positions;
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
    if (canvasEmpty()) {
      if (state.cy) { state.cy.destroy(); state.cy = null; }
      state.lastGraph = null;
      $("legend").textContent = "";
      $("zoomPct").textContent = "";
      $("tiles").hidden = true;
      $("stageEmpty").hidden = true;
      $("cvEmpty").hidden = false;
      renderCanvasLayout();
      return Promise.resolve();
    }
    $("cvEmpty").hidden = true;
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
    }).catch(function (err) {
      if (cv === mine) setCanvasStatus("failed", err.message);
    });
  }

  function canvasMark() {
    if (!cv || !state.cy) return;
    var cy = state.cy;
    if (!cy.scratch("_cvStyled")) {
      cy.scratch("_cvStyled", true);
      cy.style().selector("node[?isGroup].cv-on").style({
        "border-color": DRAW.accent, "border-width": 2.5, "border-style": "solid",
      }).selector("node.cv-from").style({
        "overlay-color": DRAW.accent, "overlay-opacity": 0.18, "overlay-padding": 6,
      }).update();
    }
    cy.elements().removeClass(IMPACT_CLASSES + " cv-on cv-from");
    var sel = cv.sel;
    // The box outlined, not the rest dimmed: on a sheet being drawn on, the
    // other boxes are where the next thing goes.
    if (sel && sel.kind === "record") cy.getElementById(sel.id).addClass("sel");
    if (sel && sel.kind === "place") cy.nodes("[?isGroup]").filter(function (g) { return !g.parent().length; }).addClass("cv-on");
    if (cv.from) cy.getElementById(cv.from).addClass("cv-from");
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
    if (from.snap) {
      n.position({ x: from.snap.x === null ? n.position("x") : from.snap.x,
                   y: from.snap.y === null ? n.position("y") : from.snap.y });
    }
    var first = !canvasKept();
    if (first) cv.data.positions = keepAll(cy);
    else keepLeaf(cy, n, cv.data.positions);
    canvasArranged(first);
    canvasSelect({ kind: "record", id: n.id() });
  }

  /* A boundary put down somewhere else, with everything in it. */
  function canvasMovedGroup(g, dx, dy) {
    var cy = state.cy;
    if (!cv || !cy) return;
    var first = !canvasKept();
    if (first) cv.data.positions = keepAll(cy);
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
    if (!cv || canvasEmpty()) { box.hidden = true; return; }
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

  function canvasSelect(sel) {
    if (!cv) return;
    cv.sel = sel;
    state.selectedId = sel && sel.kind === "record" ? sel.id : null;
    canvasMark();
    renderCanvasChips();
    var box = $("cvDetails");
    box.textContent = "";
    if (!sel) canvasDiagramDetails(box);
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
    var id = node.id();
    if (cv.tool === "connect") {
      if (!cv.from) {
        cv.from = id;
        canvasMark();
        canvasHint("Now the box it connects to.");
        return;
      }
      if (cv.from === id) return;
      var from = cv.from;
      setCanvasTool("select");
      var box = $("cy").getBoundingClientRect(), rp = node.renderedPosition();
      openConnectChooser(from, id, box.left + rp.x + 12, box.top + rp.y + 12);
      return;
    }
    canvasSelect({ kind: "record", id: id });
  }

  function setCanvasTool(tool) {
    if (!cv) return;
    cv.tool = tool;
    cv.from = null;
    $("cvSelect").setAttribute("aria-pressed", String(tool === "select"));
    $("cvConnect").setAttribute("aria-pressed", String(tool === "connect"));
    $("mapSheet").classList.toggle("cv-connecting", tool === "connect");
    canvasHint(tool === "connect" ? "Click the box a connection starts from, then the one it goes to. Esc stops." : "");
    canvasMark();
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
    box.appendChild(on.childNodes.length ? on : el("p", { class: "cv-none", text: "Nothing yet." }));
    if (!canvasEmpty()) {
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
      + "here shows on every diagram it belongs to." })]));
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
        ? "Made from the library part " + part + "."
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

  function pickerItems(tab, q, boundaries) {
    var p = cv.parts, out = { library: [], estate: [] };
    var hit = function (text) { return !q || String(text || "").toLowerCase().indexOf(q) !== -1; };
    if (!boundaries && tab !== "estate") {
      var parts = p.parts.slice().sort(function (a, b) {
        var ra = FIRST_PARTS.indexOf(a.id), rb = FIRST_PARTS.indexOf(b.id);
        return (ra === -1 ? 99 : ra) - (rb === -1 ? 99 : rb);
      }).filter(function (x) { return hit(x.name + " " + x.category + " " + x.typeLabel); });
      out.library = parts.slice(0, q ? 30 : (tab === "library" ? 14 : 4)).map(function (x) {
        return { kind: "part", id: x.id, name: x.name, sub: "Part · " + x.typeLabel, tag: "Box", icon: "i-box",
          typeLabel: x.typeLabel, type: x.type };
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
  function askPartName(item, into, at) {
    closeContextMenu();
    var menu = el("div", { class: "ctx-menu connect-menu cv-name-menu", id: "ctxMenu", role: "dialog",
      "aria-label": "Name the new " + item.typeLabel });
    menu.appendChild(el("div", { class: "ctx-head", text: "A new " + item.typeLabel + ", from " + item.name }));
    var where = saidInto(into);
    menu.appendChild(el("p", { class: "connect-ask", text: where ? "In " + where + "." : "On the sheet, in no boundary." }));
    var input = el("input", { type: "text", class: "connect-input", "aria-label": "Its name" });
    input.value = item.name;
    function go() {
      var name = input.value.trim();
      if (!name) { input.focus(); return; }
      closeContextMenu();
      var named = {};
      Object.keys(item).forEach(function (k) { named[k] = item[k]; });
      named.named = name;
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
      api("/api/canvas/record", { part: item.id, into: into || [], name: item.named }).then(function (res) {
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

  /* ---- the view composer ---------------------------------------------------
   * A view is a query, and this is the query in parts: what it shows, what it
   * brings in around that, what is pinned or hidden, which lines it draws,
   * how it boxes and shades. Every part is a choice read out of the model,
   * every change redraws the sheet behind the panel, and Save writes the file
   * by value, so a comment somebody wrote beside a rule is still there
   * afterward. What the parts cannot say -- a filter on what a relation
   * says, lanes, a parameter -- is kept as it was and shown as written, and
   * the file is one click away.
   */
  var COMPOSE_OPS = [["is", "is"], ["not", "is not"], ["set", "is filled in"], ["unset", "is empty"]];
  var COMPOSE_KINDS = [["diagram", "Diagram"], ["map", "Map"], ["report", "Table"]];

  function typeWord(type, many) {
    var spec = state.schema && state.schema.entities && state.schema.entities[type];
    var one = spec ? spec.label : String(type || "").replace(/_/g, " ").replace(/s$/, "");
    return many ? String(type || "").replace(/_/g, " ") : one;
  }

  //: Fields whose column name is not the word for them: an acronym, a
  //: system's id in another tool, a name that only made sense in the file.
  var FIELD_WORDS = {
    togaf_layer: "TOGAF layer", cmdb_ci_sys: "CMDB id", cmdb_ci_class: "CMDB class",
    company_domain: "business domain", data_classification_supported: "highest data classification",
    system_category: "category", node_label: "box labels", order_by: "order", group_direction: "box direction",
    render_for: "which subjects it is drawn for", parameters: "a subject to choose", lanes: "lanes",
    owner_org_id: "owner", capability_tier: "tier", capability_level: "level",
  };

  function fieldWord(name) {
    if (FIELD_WORDS[name]) return FIELD_WORDS[name];
    return String(name || "").replace(/_id$/, "").replace(/_/g, " ");
  }

  function capFirst(text) {
    text = String(text || "");
    return text.charAt(0).toUpperCase() + text.slice(1);
  }

  /* A `where` as conditions the form can show, and back. A key the form has
   * no words for -- has_any, a relation@target filter, an id list -- is kept
   * as written and shown as it is, removable but not rewritten. */
  function whereToConditions(where) {
    var out = [];
    Object.keys(where || {}).forEach(function (key) {
      var value = where[key];
      var plain = /^[a-z][a-z0-9_]*$/.test(key) && ["has_any", "has_all", "has_none", "tags_all",
        "tags_none", "id_in", "id_prefix"].indexOf(key) === -1;
      if (key === "tags_any") {
        out.push({ field: "tags", op: "is", values: [].concat(value || []) });
      } else if (plain && value && typeof value === "object" && !Array.isArray(value) && "not" in value) {
        out.push({ field: key, op: "not", values: [].concat(value.not || []) });
      } else if (plain && value && typeof value === "object" && !Array.isArray(value) && "exists" in value) {
        out.push({ field: key, op: value.exists ? "set" : "unset", values: [] });
      } else if (plain && (typeof value !== "object" || Array.isArray(value))) {
        out.push({ field: key, op: "is", values: [].concat(value === null || value === undefined ? [] : value).map(String) });
      } else {
        out.push({ raw: true, key: key, value: value });
      }
    });
    return out;
  }

  function conditionsToWhere(conds) {
    var where = {};
    conds.forEach(function (c) {
      if (c.raw) { where[c.key] = c.value; return; }
      if (c.field === "tags") { if (c.values.length) where.tags_any = c.values.slice(); return; }
      // A condition still waiting for its value says nothing yet; written as
      // "is one of nothing" it emptied the drawing while a value was chosen.
      if ((c.op === "is" || c.op === "not") && !c.values.length) return;
      if (c.op === "set") where[c.field] = { exists: true };
      else if (c.op === "unset") where[c.field] = { exists: false };
      else if (c.op === "not") where[c.field] = { not: c.values.slice() };
      else where[c.field] = c.values.length === 1 ? c.values[0] : c.values.slice();
    });
    return where;
  }

  function rawWords(c) {
    var v = c.value;
    var said = Array.isArray(v) ? v.join(", ") : (v && typeof v === "object") ? JSON.stringify(v) : String(v);
    var words = { has_any: "has any of", has_all: "has all of", has_none: "has none of",
      tags_all: "is tagged all of", tags_none: "is tagged none of", id_in: "is one of", id_prefix: "id starts with" };
    return (words[c.key] || c.key.replace(/@/, " as said in ").replace(/_/g, " ")) + ": " + said;
  }

  function openViewComposer(viewId, startData) {
    if (window.__AAC_STATIC__) { openViewEditor(viewId); return; }
    var q = viewId ? "?id=" + encodeURIComponent(viewId) : "";
    api("/api/view" + q).then(function (d) {
      var source = startData || d.data;
      if (!source) {
        toast("warn", "The parts cannot read this view", "Its file does not parse, so it opens as text.");
        openViewEditor(viewId);
        return;
      }
      var data = JSON.parse(JSON.stringify(source));
      var vocab = d.vocab || { types: {}, relations: [] };
      var isNew = d.isNew;
      var lastText = d.text, lastDrawn = [], status, timer = null;
      if (!data.scope) data.scope = {};
      if (!Array.isArray(data.scope.include)) data.scope.include = data.scope.include ? [data.scope.include] : [];
      var clauses = data.scope.include.map(function (c) {
        return { type: c.type, conds: whereToConditions(c.where), rest: c };
      });

      state.onDrawerClose = function () {
        if (state.preview) { state.preview = false; if (state.viewId) selectView(state.viewId); }
      };

      openDrawer(isNew ? "New view" : "Edit view", d.path, function (body) {
        // A side panel with the sheet beside it, not over it: the drawing is
        // the preview, so the shell gives the panel a column of its own and
        // the drawing fits what is left.
        $("drawer").classList.add("composer");
        document.querySelector(".shell").classList.add("composing");
        body.classList.add("composer-body");
        render(body);
        preview();
      }, function () { return save(); });
      $("scrim").hidden = true;

      function sync() {
        data.scope.include = clauses.map(function (c) {
          var out = {};
          Object.keys(c.rest || {}).forEach(function (k) { if (k !== "type" && k !== "where") out[k] = c.rest[k]; });
          out.type = c.type;
          var where = conditionsToWhere(c.conds);
          if (Object.keys(where).length) out.where = where;
          return out;
        });
        if (!data.scope.include.length) delete data.scope.include;
      }

      function changed(rerender) {
        sync();
        if (rerender) render($("drawerBody"));
        clearTimeout(timer);
        timer = setTimeout(preview, 320);
      }

      function preview() {
        if (status) { status.className = "editor-status"; status.textContent = "Drawing…"; }
        api("/api/view/preview", { id: viewId || null, data: data }).then(function (payload) {
          state.preview = true;
          $("stageEmpty").hidden = true;
          drawGraph(payload);
          lastText = payload.text || lastText;
          var before = lastDrawn.join(",");
          lastDrawn = ((payload.legend && payload.legend.types) || []).map(function (t) { return t.key; });
          if (lastDrawn.join(",") !== before) render($("drawerBody"));
          if (status) {
            status.className = "editor-status is-ok";
            status.textContent = "Draws " + payload.counts.nodes + " items and " + payload.counts.edges
              + " lines. Nothing saved yet." + (payload.notes.length ? " " + payload.notes.join(" ") : "");
          }
        }).catch(function (err) {
          if (status) { status.className = "editor-status is-bad"; status.textContent = err.message; }
        });
      }

      function save() {
        sync();
        var done = function (res, created) {
          toast(res.problem ? "warn" : "ok", (created ? "Created " : "Saved ") + (data.title || res.id),
            res.problem || res.path);
          state.onDrawerClose = null;
          state.preview = false;
          state.viewId = res.id;
          return refresh().then(function () { return true; });
        };
        if (!isNew) {
          return api("/api/view/compose", { id: viewId, data: data }).then(function (res) { return done(res, false); });
        }
        return api("/api/view/preview", { data: data }).then(function (payload) {
          return api("/api/view/save", { id: "", text: payload.text });
        }).then(function (res) { return done(res, true); });
      }

      function shownTypes() {
        var seen = {}, out = [];
        clauses.forEach(function (c) { if (c.type && !seen[c.type]) { seen[c.type] = true; out.push(c.type); } });
        lastDrawn.forEach(function (t) { if (!seen[t]) { seen[t] = true; out.push(t); } });
        return out;
      }

      function fieldsOf(type) {
        return ((vocab.types[type] || {}).fields || []);
      }

      function chipList(values, onRemove) {
        var box = el("span", { class: "cmp-chips" });
        values.forEach(function (v, i) {
          box.appendChild(el("span", { class: "cmp-chip" }, [
            el("span", { text: v }),
            el("button", { type: "button", class: "cmp-x", "aria-label": "Remove " + v, text: "×",
              onclick: function () { onRemove(i); } }),
          ]));
        });
        return box;
      }

      function valueAdder(known, chosen, onAdd, placeholder, word) {
        var left = known.filter(function (v) { return chosen.indexOf(v) === -1; });
        if (left.length) {
          var sel = el("select", { class: "cmp-select", "aria-label": placeholder || "Add a value" }, [
            el("option", { value: "", text: placeholder || "+ value" }),
          ]);
          left.forEach(function (v) { sel.appendChild(el("option", { value: v, text: word ? word(v) : v })); });
          sel.addEventListener("change", function () { if (sel.value) onAdd(sel.value); });
          return sel;
        }
        var input = el("input", { type: "text", class: "cmp-input", placeholder: placeholder || "Type a value, then Enter" });
        input.addEventListener("keydown", function (e) {
          if (e.key === "Enter" && input.value.trim()) { e.preventDefault(); onAdd(input.value.trim()); }
        });
        return input;
      }

      function sectionBox(title, hint, kids) {
        return el("section", { class: "cmp-sec" }, [
          el("h3", { class: "cmp-h", text: title }),
          hint ? el("p", { class: "cmp-hint", text: hint }) : null,
        ].concat(kids));
      }

      function render(body) {
        body.textContent = "";
        body.appendChild(el("div", { class: "cmp-top" }, [
          el("p", { class: "explain", text: "Choose what this diagram shows and how it is laid out. The "
            + "diagram beside this panel changes as you go; nothing is saved until you press Save." }),
          el("button", { type: "button", class: "btn small ghost", text: "Edit the file instead",
            title: "The same view as YAML, for what the parts cannot say",
            onclick: function () { state.onDrawerClose = null; openViewEditor(viewId, lastText); } }),
        ]));

        // Name and shelf.
        var title = el("input", { type: "text", class: "cmp-input wide", value: data.title || "", "aria-label": "Title" });
        title.addEventListener("input", function () {
          data.title = title.value;
          if (isNew) {
            var slug = title.value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
            data.view_id = slug || "my-view";
            idBox.value = data.view_id;
          }
          changed(false);
        });
        var desc = el("textarea", { class: "cmp-input wide", rows: "2", "aria-label": "Description" });
        desc.value = String(data.description || "").trim();
        desc.addEventListener("input", function () { data.description = desc.value; changed(false); });
        var shelf = el("select", { class: "cmp-select", "aria-label": "Layer" });
        VIEW_CATEGORIES.forEach(function (c) {
          var o = el("option", { value: c, text: c });
          if ((data.category || "Other") === c) o.selected = true;
          shelf.appendChild(o);
        });
        shelf.addEventListener("change", function () { data.category = shelf.value; changed(false); });
        var kind = el("div", { class: "seg", role: "group", "aria-label": "Kind" });
        COMPOSE_KINDS.forEach(function (k) {
          kind.appendChild(el("button", { type: "button", class: "seg-b" + ((data.kind || "diagram") === k[0] ? " on" : ""),
            "aria-pressed": (data.kind || "diagram") === k[0] ? "true" : "false", text: k[1],
            onclick: function () { data.kind = k[0]; changed(true); } }));
        });
        var idBox = el("input", { type: "text", class: "cmp-input mono-in", value: data.view_id || "",
          "aria-label": "File name", readonly: isNew ? null : "readonly" });
        idBox.addEventListener("input", function () { data.view_id = idBox.value.trim(); changed(false); });
        body.appendChild(sectionBox("Name", null, [
          el("label", { class: "cmp-row" }, [el("span", { class: "cmp-k", text: "Title" }), title]),
          el("label", { class: "cmp-row" }, [el("span", { class: "cmp-k", text: "What it is for" }), desc]),
          el("div", { class: "cmp-row" }, [el("span", { class: "cmp-k", text: "Layer" }), shelf,
            el("span", { class: "cmp-k inline", text: "Kind" }), kind]),
          isNew ? el("label", { class: "cmp-row" }, [el("span", { class: "cmp-k", text: "Saved as" }), idBox,
            el("span", { class: "cmp-hint inline", text: ".view.yaml, in 30_VIEWS" })]) : null,
        ]));

        // What it shows.
        var showRows = [];
        clauses.forEach(function (c, ci) {
          var typeSel = el("select", { class: "cmp-select", "aria-label": "Type" });
          Object.keys(vocab.types).sort().forEach(function (t) {
            var o = el("option", { value: t, text: capFirst(typeWord(t, true)) + " (" + vocab.types[t].count + ")" });
            if (t === c.type) o.selected = true;
            typeSel.appendChild(o);
          });
          typeSel.addEventListener("change", function () {
            c.type = typeSel.value;
            c.conds = c.conds.filter(function (k) { return k.raw; });
            changed(true);
          });
          var conds = el("div", { class: "cmp-conds" });
          c.conds.forEach(function (k, ki) {
            var rm = el("button", { type: "button", class: "cmp-x cmp-cond-x", "aria-label": "Remove this condition",
              title: "Remove this condition", text: "×",
              onclick: function () { c.conds.splice(ki, 1); changed(true); } });
            if (k.raw) {
              conds.appendChild(el("div", { class: "cmp-cond is-raw", title: "Written in the file; edit it there" }, [
                el("span", { text: "where " + rawWords(k) }), rm]));
              return;
            }
            var spec = fieldsOf(c.type).filter(function (f) { return f.name === k.field; })[0] || { values: [] };
            var op = el("select", { class: "cmp-select", "aria-label": "How" });
            COMPOSE_OPS.forEach(function (p) {
              if (k.field === "tags" && (p[0] === "not" || p[0] === "set" || p[0] === "unset")) return;
              var o = el("option", { value: p[0], text: k.field === "tags" ? "has any of" : p[1] });
              if (p[0] === k.op) o.selected = true;
              op.appendChild(o);
            });
            op.addEventListener("change", function () { k.op = op.value; if (k.op === "set" || k.op === "unset") k.values = []; changed(true); });
            var parts = [el("span", { class: "cmp-w", text: "where " + fieldWord(k.field) }), op];
            if (k.op === "is" || k.op === "not") {
              parts.push(chipList(k.values, function (i) { k.values.splice(i, 1); changed(true); }));
              parts.push(valueAdder(spec.values || [], k.values, function (v) { k.values.push(v); changed(true); },
                k.values.length ? "+ or…" : "+ choose…"));
            }
            parts.push(rm);
            conds.appendChild(el("div", { class: "cmp-cond" }, parts));
          });
          var used = c.conds.map(function (k) { return k.field; });
          var addField = el("select", { class: "cmp-select ghost", "aria-label": "Add a condition" }, [
            el("option", { value: "", text: c.conds.length ? "+ and only where…" : "+ only where…" }),
          ]);
          fieldsOf(c.type).forEach(function (f) {
            if (used.indexOf(f.name) !== -1 || f.ref) return;
            addField.appendChild(el("option", { value: f.name, text: fieldWord(f.name) }));
          });
          addField.addEventListener("change", function () {
            if (!addField.value) return;
            c.conds.push({ field: addField.value, op: "is", values: [] });
            changed(true);
          });
          showRows.push(el("div", { class: "cmp-clause" }, [
            el("div", { class: "cmp-row" }, [
              el("span", { class: "cmp-k", text: ci ? "Also show" : "Show" }), typeSel,
              el("button", { type: "button", class: "cmp-x", "aria-label": "Stop showing these",
                title: "Stop showing these", text: "×",
                onclick: function () { clauses.splice(ci, 1); changed(true); } }),
            ]),
            conds,
            el("div", { class: "cmp-row tight" }, [addField]),
          ]));
        });
        var addType = el("select", { class: "cmp-select ghost", "aria-label": "Show another type" }, [
          el("option", { value: "", text: clauses.length ? "+ also show…" : "+ show…" }),
        ]);
        Object.keys(vocab.types).sort().forEach(function (t) {
          if (!vocab.types[t].count) return;
          addType.appendChild(el("option", { value: t, text: capFirst(typeWord(t, true)) }));
        });
        addType.addEventListener("change", function () {
          if (!addType.value) return;
          clauses.push({ type: addType.value, conds: [], rest: {} });
          changed(true);
        });
        body.appendChild(sectionBox("What it shows", "Everything that matches, including what is added to the model later.",
          showRows.concat([el("div", { class: "cmp-row tight" }, [addType])])));

        // What it brings in.
        var rules = data.scope.expand || [];
        var expandRows = rules.map(function (rule, ri) {
          var rel = el("select", { class: "cmp-select", "aria-label": "Reached by" });
          [["any", "anything connected"], ["interfaces", "calls between systems"], ["owner", "ownership"]]
            .concat(vocab.relations.map(function (r) {
              return [r.name, typeWord(r.left) + " " + relationPhrase(r.name, "out") + " " + typeWord(r.right)];
            })).forEach(function (p) {
              var o = el("option", { value: p[0], text: p[1] });
              if ((rule.relation || "any") === p[0]) o.selected = true;
              rel.appendChild(o);
            });
          rel.addEventListener("change", function () { rule.relation = rel.value; changed(false); });
          var depth = el("select", { class: "cmp-select", "aria-label": "How far" });
          [1, 2, 3].forEach(function (n) {
            var o = el("option", { value: String(n), text: n === 1 ? "one step" : n + " steps" });
            if (Number(rule.depth || 1) === n) o.selected = true;
            depth.appendChild(o);
          });
          depth.addEventListener("change", function () { rule.depth = Number(depth.value); changed(false); });
          var only = [].concat(rule.types || []);
          var onlyAdd = valueAdder(Object.keys(vocab.types).filter(function (t) { return vocab.types[t].count; }), only,
            function (t) { rule.types = only.concat([t]); changed(true); }, only.length ? "+ or" : "of any type",
            function (t) { return capFirst(typeWord(t, true)); });
          return el("div", { class: "cmp-cond" }, [
            el("span", { class: "cmp-w", text: "Whatever is linked by" }), rel, depth,
            only.length ? el("span", { class: "cmp-w", text: "only" }) : null,
            chipList(only.map(function (t) { return typeWord(t, true); }), function (i) {
              only.splice(i, 1);
              if (only.length) rule.types = only; else delete rule.types;
              changed(true);
            }),
            onlyAdd,
            el("button", { type: "button", class: "cmp-x", "aria-label": "Remove this rule", text: "×",
              onclick: function () { rules.splice(ri, 1); if (!rules.length) delete data.scope.expand; changed(true); } }),
          ]);
        });
        body.appendChild(sectionBox("Also bring in", "Things connected to what it shows, even when they do not match it.",
          expandRows.concat([el("div", { class: "cmp-row tight" }, [el("button", { type: "button", class: "btn small",
            text: "+ Bring in neighbors", onclick: function () {
              data.scope.expand = rules.concat([{ relation: "interfaces", depth: 1 }]);
              changed(true);
            } })])])));

        // Pinned and hidden.
        var pins = [].concat(data.scope.pin || []), hides = [].concat(data.scope.hide || []);
        function nameOf(id) {
          var hit = (state.index || []).filter(function (x) { return x.id === id; })[0];
          return hit ? (hit.name || id) : id;
        }
        function setList(key, list) { if (list.length) data.scope[key] = list; else delete data.scope[key]; }
        body.appendChild(sectionBox("Pinned and hidden", "A pinned thing stays on this diagram even when it stops "
          + "matching; a hidden one stays off it even when it matches.", [
          el("div", { class: "cmp-row" }, [el("span", { class: "cmp-k", text: "Pinned" }),
            chipList(pins.map(nameOf), function (i) { pins.splice(i, 1); setList("pin", pins); changed(true); }),
            el("button", { type: "button", class: "btn small", text: "+ Pin…", onclick: function () {
              openPicker({ placeholder: "Pin to this view: type a name or an id…",
                skip: function (id) { return pins.indexOf(id) !== -1; },
                onPick: function (id) { pins.push(id); setList("pin", pins); changed(true); } });
            } })]),
          el("div", { class: "cmp-row" }, [el("span", { class: "cmp-k", text: "Hidden" }),
            chipList(hides.map(nameOf), function (i) { hides.splice(i, 1); setList("hide", hides); changed(true); }),
            el("button", { type: "button", class: "btn small", text: "+ Hide…", onclick: function () {
              openPicker({ placeholder: "Hide from this view: type a name or an id…",
                skip: function (id) { return hides.indexOf(id) !== -1; },
                onPick: function (id) { hides.push(id); setList("hide", hides); changed(true); } });
            } })]),
        ]));

        // Lines.
        var types = shownTypes();
        var has = {};
        types.forEach(function (t) { has[t] = true; });
        var choices = [];
        if (has.systems) choices.push({ via: "interfaces", label: "a system calls a system" });
        vocab.relations.forEach(function (r) {
          if (has[r.left] && has[r.right]) {
            choices.push({ via: r.name, label: typeWord(r.left) + " " + relationPhrase(r.name, "out") + " " + typeWord(r.right) });
          }
        });
        types.forEach(function (t) {
          fieldsOf(t).forEach(function (f) {
            if (!f.ref || !has[f.ref] || f.name === "source_system_id" || f.name === "target_system_id") return;
            var via = f.name === "owner_org_id" ? "owner" : f.name;
            if (choices.some(function (c) { return c.via === via; })) return;
            choices.push({ via: via, label: typeWord(t) + " " + (FIELD_PHRASES[f.name] || fieldWord(f.name)) + " " + typeWord(f.ref) });
          });
        });
        var edges = data.edges && data.edges.length ? data.edges : null;
        var drawnVia = (edges || [{ via: "interfaces" }]).map(function (e) { return e.via; });
        (edges || []).forEach(function (e) {
          if (!choices.some(function (c) { return c.via === e.via; })) choices.push({ via: e.via, label: edgeWord(e.via) });
        });
        var lineRows = choices.map(function (c) {
          var box = el("input", { type: "checkbox" });
          box.checked = drawnVia.indexOf(c.via) !== -1;
          box.addEventListener("change", function () {
            var list = (data.edges && data.edges.length ? data.edges : [{ via: "interfaces" }]).slice();
            if (box.checked) list.push({ via: c.via });
            else list = list.filter(function (e) { return e.via !== c.via; });
            data.edges = list;
            changed(false);
          });
          return el("label", { class: "cmp-check" }, [box, el("span", { text: c.label })]);
        });
        body.appendChild(sectionBox("Lines", "Which connections to draw. Only the ones that can join what is shown are listed.",
          [el("div", { class: "cmp-checks" }, lineRows.length ? lineRows
            : [el("p", { class: "cmp-hint", text: "Nothing on this drawing can be joined to anything else on it." })])]));

        // Boxes and shading.
        var groups = [].concat(data.group_by || []);
        var fieldNames = {};
        types.forEach(function (t) { fieldsOf(t).forEach(function (f) { if (!f.ref || f.name === "owner_org_id") fieldNames[f.name] = true; }); });
        var groupAdd = valueAdder(Object.keys(fieldNames).sort(function (a, b) {
          return fieldWord(a).localeCompare(fieldWord(b));
        }), groups, function (v) {
          groups.push(v);
          data.group_by = groups.length === 1 ? groups[0] : groups.slice();
          changed(true);
        }, groups.length ? "+ then, inside those, by…" : "+ choose…", fieldWord);
        // Unset, a drawing colors each thing by its type; "type" said
        // outright means the same, so it is one choice and not two.
        var colorBy = (data.style || {}).color_by || "";
        var shade = el("select", { class: "cmp-select", "aria-label": "Color by" }, [
          el("option", { value: "", text: "Type", selected: colorBy === "" || colorBy === "type" ? "selected" : null })]);
        Object.keys(fieldNames).sort(function (a, b) { return fieldWord(a).localeCompare(fieldWord(b)); }).forEach(function (f) {
          var o = el("option", { value: f, text: capFirst(fieldWord(f)) });
          if (colorBy === f) o.selected = true;
          shade.appendChild(o);
        });
        shade.addEventListener("change", function () {
          data.style = data.style || {};
          if (shade.value) data.style.color_by = shade.value; else delete data.style.color_by;
          if (!Object.keys(data.style).length) delete data.style;
          changed(false);
        });
        var dir = el("div", { class: "seg", role: "group", "aria-label": "Direction" });
        [["LR", "Left to right"], ["TB", "Top to bottom"]].forEach(function (p) {
          var on = (data.layout || "LR") === p[0];
          dir.appendChild(el("button", { type: "button", class: "seg-b" + (on ? " on" : ""), "aria-pressed": on ? "true" : "false",
            text: p[1], onclick: function () { data.layout = p[0]; changed(true); } }));
        });
        var cap = el("input", { type: "number", min: "0", step: "5", class: "cmp-input narrow", "aria-label": "At most",
          value: (data.limits || {}).max_nodes || "" });
        cap.addEventListener("change", function () {
          var n = parseInt(cap.value, 10);
          data.limits = data.limits || {};
          if (n > 0) data.limits.max_nodes = n; else delete data.limits.max_nodes;
          if (!Object.keys(data.limits).length) delete data.limits;
          changed(false);
        });
        body.appendChild(sectionBox("Boxes and color", null, [
          el("div", { class: "cmp-row" }, [el("span", { class: "cmp-k", text: "Group into boxes by" }),
            chipList(groups.map(fieldWord), function (i) {
              groups.splice(i, 1);
              if (!groups.length) delete data.group_by; else data.group_by = groups.length === 1 ? groups[0] : groups.slice();
              changed(true);
            }), groupAdd]),
          el("div", { class: "cmp-row" }, [el("span", { class: "cmp-k", text: "Color by" }), shade]),
          el("div", { class: "cmp-row" }, [el("span", { class: "cmp-k", text: "Direction" }), dir,
            el("span", { class: "cmp-k inline", text: "At most" }), cap, el("span", { class: "cmp-hint inline", text: "items" })]),
        ]));

        var kept = ["parameters", "render_for", "lanes", "order_by", "group_direction", "node_label"]
          .filter(function (k) { return data[k] !== undefined && data[k] !== null; });
        if (kept.length) {
          body.appendChild(el("p", { class: "cmp-hint", text: "This view also sets "
            + kept.map(fieldWord).join(", ") + ", which only the file can change: Edit the file instead, above." }));
        }
        status = el("p", { class: "editor-status", text: "Drawing…" });
        body.appendChild(status);
      }
    }).catch(fail);
  }

  /* ---- the model as data ------------------------------------------------
   * A diagram answers a question somebody already had. A table is where you
   * go when you do not know what you are looking for yet, and a model in
   * files cannot show you that without a text editor open. Everything here
   * works on the hosted demo, because being able to read the data is most of
   * what a demo is for.
   */

  /* ---- coming back after a reload --------------------------------------------
   * The address says which page and what is chosen on it. How far down the
   * page was read, and which part of a drawing was on the sheet, are kept
   * for this tab only: a link sent to someone opens the page the way it
   * opens, not where the sender had scrolled. A reload put a person zoomed
   * into one corner of a drawing back at the whole of it, and one halfway
   * down Diagrams back at the top. */
  var PLACE_KEY = "aac.place";
  var returning = (function () {
    try { return JSON.parse(sessionStorage.getItem(PLACE_KEY) || "null"); } catch (err) { return null; }
  })();
  var placeQueued = false;

  // A place belongs to an address, less the selection: what is selected
  // moves the inspector, not the drawing.
  function placeKey() { return window.location.hash.replace(/&id=[^&]*/, ""); }

  function keepPlace() {
    if (placeQueued) return;
    placeQueued = true;
    setTimeout(function () {
      placeQueued = false;
      var place = { key: placeKey() };
      var panel = $("dataPanel");
      if (!panel.hidden) place.scroll = panel.scrollTop;
      else if (state.cy && !state.cy.destroyed() && !tilesShown()) place.viewport = { zoom: state.cy.zoom(), pan: state.cy.pan() };
      else return;
      try { sessionStorage.setItem(PLACE_KEY, JSON.stringify(place)); } catch (err) { /* private mode */ }
    }, 250);
  }

  // The kept place, while the page it was kept for is the one open. Any
  // other page drops it, so it is spent on the first page after a reload
  // and never jumps a person who has since moved on.
  function returnTo(kind) {
    if (!returning) return null;
    if (returning.key !== placeKey()) { returning = null; return null; }
    return returning[kind] || null;
  }

  // A page's rows arrive after it opens, so the scroll waits until the page
  // is long enough to hold it, for a few seconds at most.
  function restoreScroll() {
    var want = returnTo("scroll");
    if (!want) return;
    var panel = $("dataPanel"), tries = 0;
    (function again() {
      if (!returning) return;
      if (!panel.hidden && panel.scrollHeight - panel.clientHeight >= want) {
        panel.scrollTop = want;
        returning = null;
        return;
      }
      tries += 1;
      if (tries < 50) setTimeout(again, 100); else returning = null;
    })();
  }

  /* Fit the drawing to the part of the sheet the floating key and controls
   * leave clear, rather than to the whole sheet and half under them. */
  function fitSheet(cy, pad) {
    if (!cy || cy.destroyed()) return;
    var bb = cy.elements().boundingBox({ includeLabels: false });
    if (!(bb.w > 0) || !(bb.h > 0)) { cy.fit(undefined, pad || 24); return; }
    var clear = clearSheet(cy, pad);
    var z = Math.min(clear.w / bb.w, clear.h / bb.h, cy.maxZoom());
    cy.zoom(z);
    cy.pan({ x: (cy.width() - bb.w * z) / 2 - bb.x1 * z, y: clear.top + (clear.h - bb.h * z) / 2 - bb.y1 * z });
    syncOverview(cy);
  }

  /* The part of the sheet a drawing is placed in, in screen pixels: inside
   * the padding, above the floating key and controls, and below the note
   * over a thin drawing when there is one. */
  function clearSheet(cy, pad) {
    pad = pad || 24;
    var footH = 0;
    var foot = $("mapSheet").querySelector(".sheet-foot");
    if (foot) {
      Array.prototype.forEach.call(foot.children, function (c) {
        if (c.offsetHeight && getComputedStyle(c).display !== "none") footH = Math.max(footH, c.offsetHeight);
      });
      if (footH) footH += 14;
    }
    var strip = $("needStrip");
    var topH = strip && !strip.hidden && strip.offsetHeight ? strip.offsetHeight + 14 : 0;
    return { left: pad, top: pad + topH, w: Math.max(40, cy.width() - pad * 2), h: Math.max(40, cy.height() - pad * 2 - footH - topH) };
  }

  /* ---- opening a drawing at a size it reads at -----------------------------
   * Fitted whole, the network topology opened at 27% and the integration
   * architecture at 32%: every name a smear of three or four pixels, which
   * is the fit doing what it was asked. A drawing whose names read when it
   * is whole still opens whole. One that would have to shrink them below
   * ten pixels opens at READ_ZOOM instead, on its busiest part, with the
   * overview in the corner of the sheet saying where that is and the whole
   * drawing a click away. */
  //: The zoom a drawing too large for the sheet opens at: a box's name at
  //: about ten pixels, and the labels on the lines shown.
  var READ_ZOOM = 0.85;

  function openReadable(cy) {
    if (!cy || cy.destroyed()) return;
    // After a reload, the part of the drawing that was on the sheet. Every
    // refit while the drawing first settles (a note arriving over it) keeps
    // to it, until the person moves the drawing or asks for the fit.
    var back = returnTo("viewport");
    if (back && cy === state.cy) {
      cy.zoom(back.zoom);
      cy.pan(back.pan);
      syncOverview(cy);
      return;
    }
    var bb = cy.elements().boundingBox({ includeLabels: false });
    if (!(bb.w > 0) || !(bb.h > 0)) { fitSheet(cy, 24); return; }
    var clear = clearSheet(cy, 24);
    if (Math.min(clear.w / bb.w, clear.h / bb.h) >= READ_ZOOM) { fitSheet(cy, 24); return; }
    var z = READ_ZOOM;
    var at = busiestWindow(cy, bb, clear.w / z, clear.h / z);
    cy.zoom(z);
    cy.pan({ x: clear.left - at.x * z, y: clear.top - at.y * z });
    syncOverview(cy);
  }

  /* Where on the drawing a window of the given size (in the drawing's own
   * units) holds the most: each box counts one and one more for each of
   * its connections, counted only when it is wholly inside, and the subject
   * a view is drawn for counts more than everything else together. The
   * window's edges are tried along the boxes' own edges, so the best one
   * cuts no box it could have held; among equals the one nearest the top
   * left wins, where reading starts. What it holds is then centered in it. */
  function busiestWindow(cy, bb, W, H) {
    var M = 14;
    var subject = (((state.lastGraph || {}).parameters || [])[0] || {}).value;
    var items = [];
    cy.nodes().forEach(function (n) {
      if (n.isParent()) return;
      var b = n.boundingBox({ includeLabels: false });
      var weight = 1 + n.connectedEdges().length;
      if (subject && (n.id() === subject || n.ancestors().filter(function (a) { return a.id() === subject; }).length)) weight += 10000;
      items.push({ x1: b.x1, y1: b.y1, x2: b.x2, y2: b.y2, weight: weight });
    });
    function starts(lo, hi, size, edges) {
      if (hi - lo <= size) return [lo - (size - (hi - lo)) / 2];
      var seen = {}, out = [];
      edges.forEach(function (v) {
        v = Math.max(lo, Math.min(hi - size, v));
        var key = Math.round(v / 4);
        if (!seen[key]) { seen[key] = true; out.push(v); }
      });
      return out;
    }
    var xs = starts(bb.x1, bb.x2, W, [bb.x1].concat(items.map(function (it) { return it.x1 - M; }),
      items.map(function (it) { return it.x2 + M - W; })));
    var ys = starts(bb.y1, bb.y2, H, [bb.y1].concat(items.map(function (it) { return it.y1 - M; }),
      items.map(function (it) { return it.y2 + M - H; })));
    var best = null;
    xs.forEach(function (x) {
      ys.forEach(function (y) {
        var score = 0;
        items.forEach(function (it) {
          if (it.x1 >= x && it.x2 <= x + W && it.y1 >= y && it.y2 <= y + H) score += it.weight;
        });
        var lead = (x - bb.x1) + (y - bb.y1);
        if (!best || score > best.score || (score === best.score && lead < best.lead)) best = { x: x, y: y, score: score, lead: lead };
      });
    });
    // Center what the window holds, without showing past the drawing's
    // edge on an axis where the drawing is larger than the window.
    var held = items.filter(function (it) {
      return it.x1 >= best.x && it.x2 <= best.x + W && it.y1 >= best.y && it.y2 <= best.y + H;
    });
    if (!held.length) return best;
    var hx1 = Infinity, hy1 = Infinity, hx2 = -Infinity, hy2 = -Infinity;
    held.forEach(function (it) {
      hx1 = Math.min(hx1, it.x1); hy1 = Math.min(hy1, it.y1); hx2 = Math.max(hx2, it.x2); hy2 = Math.max(hy2, it.y2);
    });
    function centered(lo, hi, from, to, size) {
      var v = (from + to) / 2 - size / 2;
      return hi - lo <= size ? lo - (size - (hi - lo)) / 2 : Math.max(lo, Math.min(hi - size, v));
    }
    return { x: centered(bb.x1, bb.x2, hx1, hx2, W), y: centered(bb.y1, bb.y2, hy1, hy2, H) };
  }

  /* ---- the overview ---------------------------------------------------------
   * The whole drawing, small, in the corner of the sheet, with the part on
   * the sheet marked. Press anywhere on it to go there and drag to move
   * along; Whole drawing fits all of it. It shows only while some of the
   * drawing is off the sheet, so a drawing that fits never has it. */
  var OVERVIEW_W = 188, OVERVIEW_H = 112;
  var overview = { cy: null, base: null, scale: 1, bb: null, queued: false, ox: 0, oy: 0 };

  function syncOverview(cy) {
    var box = $("overview");
    if (!box) return;
    if (overview.cy !== cy) {
      overview.cy = cy;
      overview.base = null;
      if (cy) {
        cy.on("viewport", function () { scheduleOverview(cy); });
        cy.on("dragfree", function () { overview.base = null; scheduleOverview(cy); });
        cy.on("destroy", function () { if (overview.cy === cy) { overview.cy = null; box.hidden = true; } });
      }
    }
    overview.base = null;
    scheduleOverview(cy);
  }

  function scheduleOverview(cy) {
    if (overview.queued) return;
    overview.queued = true;
    window.requestAnimationFrame(function () {
      overview.queued = false;
      paintOverview(cy);
    });
  }

  /* The note can be closed for the drawing it is over, and put away for
   * good from its own last line. For good is kept in this browser, and
   * Settings, Appearance brings it back: put away with no way back, it was
   * the hidden sidebar again. */
  var READ_NOTE_KEY = "aac.readNote";
  function readNoteOff() {
    try { return localStorage.getItem(READ_NOTE_KEY) === "off"; } catch (err) { return false; }
  }
  function setReadNote(on) {
    try {
      if (on) localStorage.removeItem(READ_NOTE_KEY); else localStorage.setItem(READ_NOTE_KEY, "off");
    } catch (err) { /* private mode: closed for this drawing only */ }
    if (state.cy) scheduleOverview(state.cy);
  }

  function paintOverview(cy) {
    var box = $("overview"), prompt = $("readPrompt");
    if (!box || !prompt) return;
    box.hidden = true;
    prompt.hidden = true;
    if (!cy || cy.destroyed() || cy !== state.cy || tilesShown()) return;
    var bb = cy.elements().boundingBox({ includeLabels: false });
    if (!(bb.w > 0) || !(bb.h > 0)) return;
    var ext = cy.extent();
    var slack = 4 / cy.zoom();
    var whole = ext.x1 <= bb.x1 + slack && ext.x2 >= bb.x2 - slack && ext.y1 <= bb.y1 + slack && ext.y2 >= bb.y2 - slack;
    if (whole) {
      // Shown whole at a size nobody reads, a drawing too large to read
      // whole says so, and the way back is the button or a double-click.
      // One that reads whole has nothing to say: it was zoomed out by hand.
      var clear = clearSheet(cy, 24);
      if (cy.zoom() < READ_ZOOM - 0.01 && Math.min(clear.w / bb.w, clear.h / bb.h) < READ_ZOOM
          && overview.closedFor !== cy && !readNoteOff()) {
        $("readWhy").textContent = "Shown whole at " + Math.round(cy.zoom() * 100) + "%, the names are too small to read.";
        prompt.hidden = false;
      }
      return;
    }
    box.hidden = false;
    var canvas = $("overviewPic");
    var dpr = window.devicePixelRatio || 1;
    var s = Math.min(OVERVIEW_W / bb.w, OVERVIEW_H / bb.h);
    var cw = Math.round(bb.w * s), ch = Math.round(bb.h * s);
    if (!overview.base || overview.scale !== s) {
      overview.scale = s;
      overview.bb = bb;
      canvas.width = Math.round(cw * dpr);
      canvas.height = Math.round(ch * dpr);
      canvas.style.width = cw + "px";
      canvas.style.height = ch + "px";
      var base = document.createElement("canvas");
      base.width = canvas.width;
      base.height = canvas.height;
      var g = base.getContext("2d");
      g.setTransform(dpr * s, 0, 0, dpr * s, -bb.x1 * s * dpr, -bb.y1 * s * dpr);
      // Boundaries outermost first, then the boxes, each in its own colors.
      var groups = cy.nodes().filter(function (n) { return n.isParent(); }).sort(function (a, b) {
        return a.ancestors().length - b.ancestors().length;
      });
      groups.forEach(function (n) {
        var b = n.boundingBox({ includeLabels: false });
        g.fillStyle = n.style("background-color");
        g.strokeStyle = n.style("border-color");
        g.lineWidth = 1 / s;
        g.fillRect(b.x1, b.y1, b.w, b.h);
        g.strokeRect(b.x1, b.y1, b.w, b.h);
      });
      cy.nodes().forEach(function (n) {
        if (n.isParent()) return;
        var b = n.boundingBox({ includeLabels: false });
        g.fillStyle = n.style("background-color");
        g.strokeStyle = n.style("border-color");
        g.lineWidth = 1.5 / s;
        g.fillRect(b.x1, b.y1, b.w, b.h);
        g.strokeRect(b.x1, b.y1, b.w, b.h);
      });
      overview.base = base;
    }
    var ctx = canvas.getContext("2d");
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(overview.base, 0, 0);
    var accent = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "#0f766e";
    var rx = (ext.x1 - bb.x1) * s * dpr, ry = (ext.y1 - bb.y1) * s * dpr;
    var rw = ext.w * s * dpr, rh = ext.h * s * dpr;
    ctx.save();
    // What is off the sheet steps back into the plate; the part on it
    // stays as drawn.
    var plate = getComputedStyle(canvas.parentNode).backgroundColor || "rgb(246, 244, 240)";
    ctx.fillStyle = plate.replace(/^rgb\(([^)]*)\)$/, "rgba($1, 0.62)");
    ctx.beginPath();
    ctx.rect(0, 0, canvas.width, canvas.height);
    ctx.rect(rx, ry, rw, rh);
    ctx.fill("evenodd");
    ctx.strokeStyle = accent;
    ctx.lineWidth = 2 * dpr;
    ctx.strokeRect(rx, ry, rw, rh);
    ctx.restore();
  }

  // Center the sheet on a point of the overview, given in its pixels.
  function overviewGo(px, py) {
    var cy = overview.cy;
    if (!cy || cy.destroyed() || !overview.bb) return;
    var s = overview.scale, bb = overview.bb;
    var mx = bb.x1 + px / s, my = bb.y1 + py / s;
    var clear = clearSheet(cy, 24), z = cy.zoom();
    cy.pan({ x: clear.left + clear.w / 2 - mx * z, y: clear.top + clear.h / 2 - my * z });
  }

  /* Where each thing on the old drawing was on the screen, so the same thing
   * on the new one can start there and glide into place. */
  function priorPositions() {
    if (!state.cy || state.cy.destroyed() || REDUCED.matches) return null;
    var out = {}, n = 0;
    state.cy.nodes().forEach(function (node) {
      if (node.isParent()) return;
      var p = node.renderedPosition();
      out[node.id()] = { x: p.x, y: p.y };
      n += 1;
    });
    return n ? out : null;
  }

  /* A view morphs into the next: what both drawings show glides from where
   * it was to where it is now, and what is new fades in. The eye keeps the
   * thing it was looking at, which a redraw never let it do. */
  function morph(cy, prior) {
    if (!prior || !cy || cy.destroyed()) return false;
    var leaves = cy.nodes().filter(function (n) { return !n.isParent(); });
    if (!leaves.length || leaves.length > 160) return false;
    var zoom = cy.zoom(), pan = cy.pan();
    var moved = 0;
    cy.startBatch();
    leaves.forEach(function (n) {
      var to = n.position();
      n.scratch("_to", { x: to.x, y: to.y });
      var was = prior[n.id()];
      if (was) {
        n.position({ x: (was.x - pan.x) / zoom, y: (was.y - pan.y) / zoom });
        moved += 1;
      } else {
        n.style("opacity", 0);
      }
    });
    var fresh = cy.edges().filter(function (e) { return !prior[e.source().id()] || !prior[e.target().id()]; });
    fresh.style("opacity", 0);
    cy.endBatch();
    if (!moved) {
      cy.startBatch();
      leaves.forEach(function (n) { n.position(n.scratch("_to")); n.removeStyle("opacity"); });
      fresh.removeStyle("opacity");
      cy.endBatch();
      return false;
    }
    leaves.forEach(function (n) {
      if (prior[n.id()]) {
        n.animate({ position: n.scratch("_to") }, { duration: 340, easing: "ease-out-quart" });
      } else {
        n.animate({ style: { opacity: 1 } }, { duration: 300, easing: "ease-out-quart",
          complete: function () { n.removeStyle("opacity"); } });
      }
    });
    fresh.forEach(function (e) {
      e.animate({ style: { opacity: 1 } }, { duration: 300, easing: "ease-out-quart",
        complete: function () { e.removeStyle("opacity"); } });
    });
    return true;
  }

  function settle(cy, prior, refit) {
    if (refit) refit();
    if (!morph(cy, prior)) arrive();
  }

  /* The sheet rises into place when a different view lands on it, and holds
   * still for a relayout of the same one: the motion says "new", not "drawn". */
  function arrive() {
    var sheet = $("mapSheet");
    if (!sheet || state.arrivedFor === state.viewId) return;
    state.arrivedFor = state.viewId;
    sheet.classList.remove("is-in");
    void sheet.offsetWidth;
    sheet.classList.add("is-in");
  }

  /* The title block's reading links carry a rule under the open page. */
  function syncNav() {
    var current = { library: "btnComponents", data: "btnData", guide: "btnHelp", start: "btnHome", diagrams: "btnDiagrams",
      validate: "btnChecks", coverage: "btnChecks", drift: "btnChecks", changes: "btnChecks",
      settings: "btnSettings" }[state.panel] || "";
    ["btnComponents", "btnData", "btnHelp", "btnHome", "btnDiagrams", "btnChecks", "btnSettings"].forEach(function (id) {
      var b = $(id);
      if (!b) return;
      if (id === current) b.setAttribute("aria-current", "page");
      else b.removeAttribute("aria-current");
    });
    var flows = document.querySelector(".shelf-flows");
    if (flows) flows.setAttribute("aria-current", state.panel === "flows" ? "page" : "false");
  }

  function showPanel(on) {
    if (on) leaveCanvas();
    // The panel replaces the working area rather than sharing it: a table of
    // 36 columns next to an inspector is a table nobody can read.
    $("dataPanel").hidden = !on;
    $("mapSheet").hidden = on;
    document.querySelector(".stage-head").hidden = on;
    document.querySelector(".shell").classList.toggle("panel-open", on);
    inspectorOver(false);
    $("focusBar").hidden = on || !state.focus;
    // The subject picker belongs to the drawing. A report with a subject
    // puts its own back after this; a panel over a drawing shows none.
    $("subjectBar").hidden = true;
    state.panel = on ? state.panel : null;
    syncNav();
    if (state.overview) renderViewList(state.overview);
    if (!on) {
      $("dataPanel").textContent = "";
      $("dataPanel").classList.remove("is-table");
      if (state.cy) {
        state.cy.resize();
        if (state.lastGraph && state.lastGraph.kind !== "report" && state.lastGraph.kind !== "timeline") {
          renderSubjectBar(state.lastGraph);
        }
      }
    }
  }

  function csvCell(value) {
    var text = value === null || value === undefined ? "" : String(value);
    return /[",\n]/.test(text) ? '"' + text.replace(/"/g, '""') + '"' : text;
  }

  function download(filename, text, mime) {
    var blob = new Blob([text], { type: mime + ";charset=utf-8" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    // Revoking immediately can cancel the download in some browsers.
    setTimeout(function () { URL.revokeObjectURL(url); }, 4000);
    toast("ok", "Downloaded " + filename);
  }

  function tableCsv(table, columns, rows) {
    var lines = [columns.map(function (c) { return csvCell(c.name); }).join(",")];
    rows.forEach(function (row) {
      lines.push(columns.map(function (c) { return csvCell(row[c.name]); }).join(","));
    });
    // A trailing newline, and \n not \r\n: the exporter writes the same.
    return lines.join("\n") + "\n";
  }

  /* ---- the landing page -------------------------------------------------
   * Opening straight onto a diagram assumes the person already knew which
   * diagram they wanted. Usually they did not, and twenty-six views, four
   * flows, a data browser and a coverage report is a lot to find by clicking
   * around a toolbar.
   */

  function startCard(title, why, note, onclick) {
    return el("button", { class: "start-card", type: "button", onclick: onclick }, [
      el("span", { class: "sc-title", text: title }),
      el("span", { class: "sc-why", text: why }),
      note ? el("span", { class: "sc-n mono", text: note }) : null,
    ]);
  }

  function makeRow(label, note, onclick, disabled) {
    var row = el("button", { class: "make-row", type: "button", onclick: onclick }, [
      el("span", { class: "mr-label", text: label }),
      el("span", { class: "mr-note", text: note }),
    ]);
    if (disabled) {
      row.disabled = true;
      row.title = "Writes to the model on disk, so it runs in the local app.";
    }
    return row;
  }

  /* ---- the component library ---------------------------------------------
   * Two levels, because they answer different questions. A component type is
   * what a box on a diagram *is*. A block is what you reach for when
   * designing, because nobody assembles a workload by picking forty
   * individual services.
   *
   * Neither names a vendor. The block says "a public web tier"; resolving it
   * against AWS gives CloudFront, AWS WAF and an ALB, and against Azure gives
   * Front Door, Azure WAF and an Application Gateway. Same block.
   */

  function componentChip(entry, count, names) {
    return el("div", { class: "lib-comp", title: entry.description || "" }, [
      el("span", { class: "lc-name", text: entry.name }),
      count ? el("span", { class: "lc-n mono", text: String(count) }) : null,
      libraryMark(entry, names, true),
    ]);
  }

  /* Which library a card was read from, when it is not the shipped one, and
   * what it stands in for. A replacement nobody can see on the page would be
   * the silent shadow the `replaces:` rule exists to prevent. */
  function libraryMark(rec, names, short) {
    if (!rec.library) return null;
    // Inside a chip the name is the mark; the sentence is on hover.
    var text = short ? rec.library : "From " + rec.library;
    if (rec.replaced && !short) {
      var from = (names || []).filter(function (n) { return rec.replaced.indexOf(n + "/") === 0; })[0];
      text += ", in place of " + (from ? from + "\u2019s" : "the shipped one");
    }
    return el("span", { class: "lib-from", text: text,
      title: rec.replaced ? "Replaces the one in " + rec.replaced : "Read from " + rec.library + "/" });
  }

  /* "2 patterns and 1 part", from a layer -> count map. */
  function countedLayers(counts) {
    var said = Object.keys(counts).map(function (k) {
      return counts[k] + " " + k + (counts[k] === 1 ? "" : "s");
    });
    if (said.length < 2) return said.join("");
    return said.slice(0, -1).join(", ") + " and " + said[said.length - 1];
  }

  /* The line the Library opens with when the model names libraries of its
   * own: what each adds and what it replaces. Nothing when it names none. */
  function librariesLine(libraries) {
    if (!libraries || !libraries.length) return null;
    var said = libraries.map(function (l) {
      var adds = countedLayers(l.adds || {}), replaces = countedLayers(l.replaces || {});
      var what = adds && replaces ? "adds " + adds + ", and replaces " + replaces
        : adds ? "adds " + adds : replaces ? "replaces " + replaces : "adds nothing yet";
      return l.name + " " + what;
    });
    return el("p", { class: "lib-sources", text:
      "Read from the shipped library and then your own: " + said.join("; ") + ". "
      + "A card from your library says so, and one that stands in for a shipped one says that too." });
  }

  /* A long page of shelves becomes one shelf at a time. Every group title
   * on the page is a tab; what follows it, up to the next title, is that
   * tab's pane. A title's own buttons move to the top of its pane. The
   * choice is kept, so coming back lands on the same shelf. */
  function shelvesToTabs(panel, wantLabel) {
    var kids = Array.prototype.slice.call(panel.children);
    var titles = kids.filter(function (k) { return k.classList && k.classList.contains("group-title"); });
    if (titles.length < 2) return;
    var strip = el("div", { class: "page-tabs lib-tabs", role: "tablist" });
    var panes = [], tabs = [];
    titles.forEach(function (title, i) {
      var pane = el("section", { class: "lib-pane", role: "tabpanel" });
      var acts = el("div", { class: "pane-acts" });
      Array.prototype.slice.call(title.children).forEach(function (c) { acts.appendChild(c); });
      var words = title.textContent.trim();
      var m = words.match(/^(.*?)(?:\s\u00b7\s(\d+))?$/);
      var label = m ? m[1] : words, count = m && m[2] ? m[2] : "";
      if (acts.children.length) pane.appendChild(acts);
      var node = title.nextSibling;
      while (node && !(node.classList && node.classList.contains("group-title"))) {
        var next = node.nextSibling;
        pane.appendChild(node);
        node = next;
      }
      panel.insertBefore(pane, title);
      panel.removeChild(title);
      panes.push(pane);
      var tab = el("button", { class: "page-tab", type: "button", role: "tab", onclick: function () { show(i); } }, [
        el("span", { class: "pt-label", text: label }),
        count ? el("span", { class: "pt-count num", text: count }) : null,
      ]);
      tab.dataset.label = label;
      tabs.push(tab);
      strip.appendChild(tab);
    });
    panel.insertBefore(strip, panes[0]);
    function show(i) {
      state.libTab = i;
      state.libShelf = tabs[i].dataset.label.toLowerCase();
      panes.forEach(function (p, j) { p.hidden = j !== i; });
      tabs.forEach(function (t, j) {
        t.classList.toggle("is-on", j === i);
        t.setAttribute("aria-selected", j === i ? "true" : "false");
      });
      panel.scrollTop = 0;
      if (state.panel === "library") syncUrl();
    }
    var start = typeof state.libTab === "number" && state.libTab < panes.length ? state.libTab : 0;
    if (wantLabel) tabs.forEach(function (t, j) { if (t.dataset.label.toLowerCase().indexOf(wantLabel) === 0) start = j; });
    show(start);
  }

  function openLibrary(openBlock, shelf) {
    api("/api/library").then(function (lib) {
      var readOnly = !!window.__AAC_STATIC__;
      state.panel = "library";
      showPanel(true);
      var panel = $("dataPanel");
      panel.textContent = "";
      panel.classList.remove("is-table");

      panel.appendChild(el("div", { class: "panel-head" }, [
        el("div", {}, [
          el("h1", { text: "Library" }),
          el("p", { class: "sub", text:
            "The decisions, the handfuls of components that always arrive together, "
            + "and the vocabulary underneath. Nothing here names a vendor: a block says "
            + "\u201ca public web tier\u201d, and which cloud it lands on decides what "
            + "that is called." }),
          librariesLine(lib.libraries),
        ]),
      ]));
      var libNames = (lib.libraries || []).map(function (l) { return l.name; });

      // ---- patterns -------------------------------------------------------
      // A block plus the decision. The status is the lifecycle a review board
      // governs, and the adoption line is read off the model, not a register.
      var blockById = {};
      lib.blocks.forEach(function (b) { blockById[b.id] = b; });
      panel.appendChild(el("p", { class: "group-title", text:
        "Patterns \u00b7 " + lib.patterns.length }));
      panel.appendChild(el("p", { class: "brief-hint", text:
        "A block plus the decision: what it is for, what it costs, and when not to use "
        + "it. This is what a review board governs. Who applies each one is read off "
        + "the products in the model, so it is current whether or not anybody kept a "
        + "register." }));
      var plist = el("div", { class: "pattern-list" });
      lib.patterns.forEach(function (p) {
        var card = el("article", { class: "pattern-card is-" + p.status.toLowerCase() }, [
          el("div", { class: "pc-head" }, [
            el("span", { class: "pc-name", text: p.name }),
            el("span", { class: "pc-status mono", text: p.status }),
            el("span", { class: "pc-cat mono", text: p.category }),
            p.decisionRef ? el("span", { class: "pc-ref mono", text: p.decisionRef }) : null,
            p.methodRef ? el("span", { class: "pc-ref mono", text: p.methodRef,
              title: "The method's reference pattern this one implements" }) : null,
            libraryMark(p, libNames),
          ]),
          el("p", { class: "pc-text" }, [el("b", { text: "Intent. " }), p.intent]),
          el("p", { class: "pc-text" }, [el("b", { text: "What it costs. " }), p.consequences]),
          el("p", { class: "pc-text" }, [el("b", { text: "When not to use it. " }), p.whenNotToUse]),
        ]);
        var facts = el("div", { class: "pc-facts" });
        facts.appendChild(el("span", { class: "pc-k", text: "made of" }));
        p.blocks.forEach(function (id) {
          var b = blockById[id];
          facts.appendChild(el("button", { class: "help-chip as-btn", type: "button",
            text: b ? b.name : id, title: "Open the block",
            onclick: function () { if (b) openBlockForm(b, lib, readOnly); } }));
        });
        if (p.satisfies.length) {
          facts.appendChild(el("span", { class: "pc-k", text: "satisfies" }));
          p.satisfies.forEach(function (c) {
            facts.appendChild(el("button", { class: "help-chip as-btn", type: "button",
              text: c.name, title: c.id,
              onclick: function () { showPanel(false); showEntity(c.id); } }));
          });
        }
        facts.appendChild(el("span", { class: "pc-k", text: "applied by" }));
        if (p.appliedBy.length) {
          p.appliedBy.forEach(function (r) {
            // An interface on the pattern reads as the connection it is.
            facts.appendChild(el("button", { class: "help-chip as-btn" + (r.kind === "interface" ? " is-iface" : ""),
              type: "button", text: r.name,
              title: r.id + (r.kind === "interface" ? " \u00b7 interface" : ""),
              onclick: function () { showPanel(false); showEntity(r.id); } }));
          });
        } else {
          facts.appendChild(el("span", { class: "pc-none", text: "nothing in the model yet" }));
        }
        card.appendChild(facts);
        plist.appendChild(card);
      });
      panel.appendChild(plist);

      // ---- connection kinds ---------------------------------------------
      // The ways two systems are connected here, each with the interfaces
      // its fields make it; the ones of no kind are the finding.
      var conn = lib.connections || { kinds: [], none: [] };
      if (conn.kinds.length) {
        var total = conn.none.length + conn.kinds.reduce(function (n, k) { return n + k.interfaces.length; }, 0);
        panel.appendChild(el("p", { class: "group-title", text: "Connections \u00b7 " + conn.kinds.length }));
        panel.appendChild(el("p", { class: "brief-hint", text:
          "The ways two systems are connected here. An interface is of a kind when its style "
          + "and protocol say so, read off its own fields, so " + (total - conn.none.length) + " of "
          + total + " are counted whether or not anyone chose a kind. Connecting two systems on "
          + "a drawing offers these, and the form arrives filled in." }));
        var klist = el("div", { class: "pattern-list" });
        conn.kinds.forEach(function (k) {
          var card = el("article", { class: "pattern-card" }, [
            el("div", { class: "pc-head" }, [
              el("span", { class: "pc-name", text: k.name }),
              el("span", { class: "pc-cat", text: k.style }),
              libraryMark(k, libNames),
            ]),
            el("p", { class: "pc-text", text: k.description }),
          ]);
          var facts = el("div", { class: "pc-facts" });
          facts.appendChild(el("span", { class: "pc-k", text: "over" }));
          k.protocols.forEach(function (p) { facts.appendChild(el("span", { class: "help-chip", text: p })); });
          if (k.authMethods.length) {
            facts.appendChild(el("span", { class: "pc-k", text: "signed in by" }));
            k.authMethods.forEach(function (p) { facts.appendChild(el("span", { class: "help-chip", text: p })); });
          }
          if (k.patterns.length) {
            facts.appendChild(el("span", { class: "pc-k", text: "built as" }));
            k.patterns.forEach(function (p) { facts.appendChild(el("span", { class: "help-chip", text: p })); });
          }
          facts.appendChild(el("span", { class: "pc-k", text: k.interfaces.length + " in the estate" }));
          k.interfaces.slice(0, 6).forEach(function (r) {
            facts.appendChild(el("button", { class: "help-chip as-btn is-iface", type: "button", text: r.name,
              title: r.id, onclick: function () { showPanel(false); showEntity(r.id); } }));
          });
          if (k.interfaces.length > 6) {
            facts.appendChild(el("span", { class: "pc-none", text: "and " + (k.interfaces.length - 6) + " more" }));
          }
          card.appendChild(facts);
          klist.appendChild(card);
        });
        if (conn.none.length) {
          var odd = el("article", { class: "pattern-card is-candidate" }, [
            el("div", { class: "pc-head" }, [el("span", { class: "pc-name", text: "Of no kind" })]),
            el("p", { class: "pc-text", text: "Built unlike anything around them, or a kind the library has "
              + "yet to learn. Several sharing a shape is a kind waiting to be written in 24_CONNECTIONS." }),
          ]);
          var oddFacts = el("div", { class: "pc-facts" });
          conn.none.forEach(function (r) {
            oddFacts.appendChild(el("button", { class: "help-chip as-btn is-iface", type: "button",
              text: r.name + " (" + (r.protocol || "no protocol") + ")", title: r.id,
              onclick: function () { showPanel(false); showEntity(r.id); } }));
          });
          odd.appendChild(oddFacts);
          klist.appendChild(odd);
        }
        panel.appendChild(klist);
      }

      // ---- modules --------------------------------------------------------
      // The plug-and-play parts: what a shape is composed from, and what a
      // vendor either needs or does not.
      if (lib.modules && lib.modules.length) {
        panel.appendChild(el("p", { class: "group-title" }, [
          "Parts \u00b7 " + lib.modules.length,
          readOnly ? null : el("button", { class: "btn small gt-act", type: "button", text: "Assemble a project",
            title: "Pick parts and write a project made of them",
            onclick: function () { openAssemble(null); } }),
        ]));
        panel.appendChild(el("p", { class: "brief-hint", text:
          "A part of a product, with parameters: a handful of systems, interfaces and data "
          + "assets that arrive together. Shapes are composed from these, and a product "
          + "keeps the parts it needs. Onboarding a new vendor is choosing parts, not drawing." }));
        var mgrid = el("div", { class: "block-grid" });
        lib.modules.forEach(function (m) {
          if (m.error) {
            mgrid.appendChild(el("p", { class: "editor-status is-bad", text: m.error }));
            return;
          }
          var made = Object.keys(m.provides || {}).map(function (t) {
            return m.provides[t] + " " + t.replace(/_/g, " ");
          });
          if (m.relations) made.push(m.relations + " relations");
          var card = el("div", { class: "block-card is-part" }, [
            el("div", { class: "bc-head" }, [
              el("span", { class: "bc-name", text: m.name }),
              el("span", { class: "bc-cat mono", text: m.category }),
            ]),
            libraryMark(m, libNames),
            el("p", { class: "bc-why", text: m.description }),
          ]);
          var parts = el("div", { class: "bc-parts" });
          made.forEach(function (t) { parts.appendChild(el("code", { class: "help-chip", text: t })); });
          if (!m.optional) parts.appendChild(el("code", { class: "help-chip is-fixed", text: "always" }));
          if (m.kit) parts.appendChild(el("code", { class: "help-chip is-fixed",
            text: "kit: " + (m.members || []).join(" + ") }));
          (m.requires || []).forEach(function (r) {
            parts.appendChild(el("code", { class: "help-chip", text: "needs " + r }));
          });
          card.appendChild(parts);
          if (m.inShapes && m.inShapes.length) {
            card.appendChild(el("p", { class: "bc-in mono", text: "in " + m.inShapes.join(", ") }));
          }
          mgrid.appendChild(card);
        });
        panel.appendChild(mgrid);
      }

      // ---- blocks ---------------------------------------------------------
      panel.appendChild(el("p", { class: "group-title", text:
        "Building blocks \u00b7 " + lib.blocks.length }));
      panel.appendChild(el("p", { class: "brief-hint", text: readOnly
        ? "Adding a block writes to the model on disk, so that runs in the local app. "
          + "What each one is made of is here to read."
        : "Pick one, name the thing being built, and it creates every component and "
          + "the relations between them. Five or six blocks compose a workload." }));

      var grid = el("div", { class: "block-grid" });
      lib.blocks.forEach(function (block) {
        var card = el("button", { class: "block-card", type: "button",
          onclick: function () { openBlockForm(block, lib, readOnly); } }, [
          el("div", { class: "bc-head" }, [
            el("span", { class: "bc-name", text: block.name }),
            el("span", { class: "bc-cat mono", text: block.category }),
          ]),
          libraryMark(block, libNames),
          el("p", { class: "bc-why", text: block.description }),
        ]);
        var parts = el("div", { class: "bc-parts" });
        block.provides.forEach(function (p) {
          parts.appendChild(el("code", { class: "help-chip", text: p.name }));
        });
        card.appendChild(parts);
        if (block.inPatterns && block.inPatterns.length) {
          card.appendChild(el("p", { class: "bc-in mono",
            text: "in " + block.inPatterns.join(", ") }));
        }
        grid.appendChild(card);
      });
      panel.appendChild(grid);

      // ---- component types ------------------------------------------------
      panel.appendChild(el("p", { class: "group-title", text: "Component types" }));
      panel.appendChild(el("p", { class: "brief-hint", text:
        "The vocabulary underneath. A count beside one means the model already has "
        + "that many; no count means nothing in the estate is recorded as being it." }));
      var cats = el("div", { class: "cov-grid" });
      lib.components.forEach(function (group) {
        var list = el("div", { class: "lib-list" });
        group.types.forEach(function (entry) {
          list.appendChild(componentChip(entry, lib.inUse[entry.id], libNames));
        });
        cats.appendChild(el("div", { class: "cov-block" }, [
          el("p", { class: "cb-head" }, [
            el("span", { class: "cb-name", text: group.category }),
            el("span", { class: "cb-n mono", text: String(group.types.length) }),
          ]),
          list,
        ]));
      });
      panel.appendChild(cats);

      // ---- landing zones --------------------------------------------------
      // What each provider already runs for whatever lands on it, by kind,
      // and the kinds the parts name that it cannot answer: the same picture
      // as library/landing-zones.md, and the shelf a vendor onboarding checks
      // before it starts.
      if (lib.landingZones && lib.landingZones.length) {
        panel.appendChild(el("p", { class: "group-title", text: "Landing zones" }));
        panel.appendChild(el("p", { class: "brief-hint", text:
          "One shared service of each kind, tagged landing-zone, found by kind when a part "
          + "asks. A kind the parts ask for that has no service is where the next onboarding "
          + "on that provider would stop." }));
        var zones = el("div", { class: "cov-grid" });
        lib.landingZones.forEach(function (zone) {
          var list = el("div", { class: "lz-list" });
          zone.kinds.forEach(function (k) {
            var row = el("div", { class: "lz-row" + (k.gap ? " is-gap" : "") });
            row.appendChild(el("span", { class: "lz-kind mono", text: k.kind }));
            if (k.services.length) {
              var names = k.services.map(function (s) {
                return s.name + (s.alsoKind ? " — a " + s.alsoKind.replace(/-/g, " ") + " that answers for it" : "");
              }).join(", ");
              row.appendChild(el("span", { class: "lz-svc", text:
                names + (k.shared ? ", shared" : "") + (k.ambiguous ? " — ambiguous" : "") }));
            } else {
              row.appendChild(el("span", { class: "lz-svc lz-none", text:
                "none" + (k.boundBy.length ? " — bound by hand on " + k.boundBy.join(", ") : "") }));
            }
            if (k.askedBy.length) {
              row.appendChild(el("span", { class: "lz-asked", text: "asked for by " + k.askedBy.join(", ") }));
            }
            list.appendChild(row);
          });
          zones.appendChild(el("div", { class: "cov-block" }, [
            el("p", { class: "cb-head" }, [
              el("span", { class: "cb-name", text: zone.provider }),
              el("span", { class: "cb-n mono", text:
                zone.kinds.length + " kinds" + (zone.gaps ? " · " + zone.gaps + " missing" : "") }),
            ]),
            el("p", { class: "brief-hint", text: "Shapes here: " + zone.shapes.join(", ") }),
            list,
          ]));
        });
        panel.appendChild(zones);
      }

      // ---- shapes and the estate ------------------------------------------
      // Who is on a shape and how far they have moved, and which hand-authored
      // products a shape's parts would reproduce: pattern adoption's
      // counterpart for the modular layer.
      var adoption = lib.adoption || {};
      if ((adoption.onShapes || []).length || (adoption.candidates || []).length) {
        panel.appendChild(el("p", { class: "group-title", text: "Shapes and the estate" }));
        panel.appendChild(el("p", { class: "brief-hint", text:
          "Moves counts every way a product differs from a bare instance of its shape; a high "
          + "count is where the shape's next default lives. A candidate is a product nobody put on "
          + "a shape whose systems are what a shape's parts would make." }));
        var grid = el("div", { class: "cov-grid" });
        var onList = el("div", { class: "lz-list" });
        (adoption.onShapes || []).forEach(function (d) {
          var bits = [];
          if (d.answers.length) bits.push("answers " + d.answers.join(", "));
          if (d.overrides.length) bits.push(d.overrides.length + " override" + (d.overrides.length === 1 ? "" : "s"));
          Object.keys(d.extras).forEach(function (t) { bits.push(d.extras[t] + " extra " + t); });
          if (d.added.length) bits.push("adds " + d.added.join(", "));
          if (d.dropped.length) bits.push("drops " + d.dropped.join(", "));
          d.choices.forEach(function (c) { if (!c.default) bits.push(c.slot + ": " + c.pick + " (not the default)"); });
          var row = el("div", { class: "lz-row" });
          row.appendChild(el("span", { class: "lz-kind mono", text: d.shape }));
          row.appendChild(el("span", { class: "lz-svc", text: d.name + " · " + d.moves + " move" + (d.moves === 1 ? "" : "s") }));
          if (bits.length) row.appendChild(el("span", { class: "lz-asked", text: bits.join("; ") }));
          onList.appendChild(row);
        });
        grid.appendChild(el("div", { class: "cov-block" }, [
          el("p", { class: "cb-head" }, [
            el("span", { class: "cb-name", text: "On a shape" }),
            el("span", { class: "cb-n mono", text: String((adoption.onShapes || []).length) }),
          ]),
          (adoption.onShapes || []).length ? onList : el("p", { class: "brief-hint", text: "None yet." }),
        ]));
        var candList = el("div", { class: "lz-list" });
        (adoption.candidates || []).forEach(function (c) {
          var row = el("div", { class: "lz-row is-gap" });
          row.appendChild(el("span", { class: "lz-kind mono", text: c.shape }));
          row.appendChild(el("span", { class: "lz-svc lz-none", text: c.name }));
          row.appendChild(el("span", { class: "lz-asked", text:
            "has " + c.covered.join(", ")
            + (c.missing.length ? "; lacks " + c.missing.join(", ") + " (optional)" : "")
            + (c.spare.length ? "; " + c.spare.length + " system" + (c.spare.length === 1 ? "" : "s") + " no part makes" : "") }));
          candList.appendChild(row);
        });
        grid.appendChild(el("div", { class: "cov-block" }, [
          el("p", { class: "cb-head" }, [
            el("span", { class: "cb-name", text: "Candidates" }),
            el("span", { class: "cb-n mono", text: String((adoption.candidates || []).length) }),
          ]),
          (adoption.candidates || []).length ? candList : el("p", { class: "brief-hint", text: "None: every product with systems a shape makes is on one." }),
        ]));
        panel.appendChild(grid);
      }

      shelvesToTabs(panel, openBlock ? "building blocks" : (shelf || ""));
      if (openBlock) {
        var wanted = lib.blocks.filter(function (b) { return b.id === openBlock; })[0];
        if (wanted) openBlockForm(wanted, lib, readOnly);
      }
    }).catch(fail);
  }

  function openBlockForm(block, lib, readOnly) {
    var nameInput, providerPicker, result;

    openDrawer(block.name, block.category, function (body) {
      body.appendChild(el("p", { class: "explain", text: block.description }));

      nameInput = el("input", { type: "text", id: "blk__name",
        placeholder: "Lending, Card Servicing, Screening\u2026" });
      nameInput.readOnly = readOnly;
      body.appendChild(el("div", { class: "field" }, [
        el("label", { for: "blk__name" }, ["what is being built"]),
        nameInput,
      ]));

      providerPicker = el("select", { id: "blk__provider" });
      providerPicker.appendChild(el("option", { value: "", text: "\u2014 not chosen yet" }));
      lib.providers.forEach(function (name) {
        providerPicker.appendChild(el("option", { value: name, text: name }));
      });
      body.appendChild(el("div", { class: "field" }, [
        el("label", { for: "blk__provider" }, ["provider"]),
        providerPicker,
        el("span", { class: "field-why", text:
          "Optional. Without one the components carry the shape and no product "
          + "name, which is the honest state for a design that has not chosen a "
          + "cloud yet." }),
      ]));

      result = el("div", { class: "produces" });
      body.appendChild(result);

      if (!readOnly) {
        body.appendChild(el("div", { class: "editor-acts" }, [
          el("button", { class: "btn small", type: "button", text: "Preview",
            onclick: function () { previewBlock(); } }),
        ]));
      }

      function previewBlock() {
        result.textContent = "";
        api("/api/block/preview", {
          block: block.id, name: nameInput.value, provider: providerPicker.value,
        }).then(function (d) {
          result.appendChild(el("p", { class: "group-title", text:
            "It creates \u00b7 " + d.produces.length + " entities, "
            + d.relations + " relations" }));
          var list = el("ul", { class: "produces-list" });
          d.produces.forEach(function (p) {
            list.appendChild(el("li", { class: p.clash ? "is-clash" : "" }, [
              el("code", { class: "help-chip", text: p.component }),
              el("span", { class: "mono", text: p.id }),
              el("span", { class: "produces-name",
                text: p.clash ? "already in the model" : (p.product || p.name) }),
            ]));
          });
          result.appendChild(list);
        }).catch(function (err) {
          result.appendChild(el("p", { class: "editor-status is-bad", text: err.message }));
        });
      }
    }, readOnly ? null : function () {
      return api("/api/block/add", {
        block: block.id,
        name: $("blk__name").value,
        provider: $("blk__provider").value,
      }).then(function (res) {
        toast(res.errors.length ? "warn" : "ok",
          "Added " + res.created.length + " components",
          res.errors.length ? res.errors[0]
            : block.name + " for " + res.name + ", " + res.relations + " relations");
        return refresh().then(function () { return true; });
      });
    });
  }

  /* A stylized picture of each starting view, so the landing page shows what
   * a view looks like before it is opened: a context diagram is a thing in
   * the middle with actors around it, a capability map is bands of tiles. */
  var THUMBS = {
    "system-context": '<rect x="46" y="24" width="28" height="16" rx="2" class="th-f"/>'
      + '<path d="M20 14l26 14M20 50l26-14M100 14L74 28M100 50L74 36M60 10v14" class="th-l"/>'
      + '<circle cx="14" cy="12" r="6" class="th-o"/><circle cx="14" cy="52" r="6" class="th-o"/>'
      + '<circle cx="106" cy="12" r="6" class="th-o"/><circle cx="106" cy="52" r="6" class="th-o"/><circle cx="60" cy="6" r="4.5" class="th-o"/>',
    "capability-map": [4, 25, 46].map(function (y, i) {
      return '<rect x="2" y="' + y + '" width="16" height="14" rx="1.5" class="th-b"/>'
        + [0, 1, 2, 3].map(function (j) {
          return '<rect x="' + (24 + j * 24) + '" y="' + y + '" width="20" height="14" rx="1.5" class="th-t'
            + ((i + j) % 3 === 0 ? " is-deep" : "") + '"/>';
        }).join("");
    }).join(""),
    "application-landscape": '<rect x="2" y="2" width="56" height="28" rx="2" class="th-g"/>'
      + '<rect x="62" y="2" width="56" height="28" rx="2" class="th-g"/><rect x="2" y="34" width="116" height="28" rx="2" class="th-g"/>'
      + [[7, 7], [24, 7], [41, 7], [7, 18], [24, 18], [67, 7], [84, 7], [101, 7], [67, 18], [84, 18],
         [7, 39], [24, 39], [41, 39], [58, 39], [75, 39], [92, 39], [7, 50], [24, 50], [41, 50]].map(function (p, i) {
        return '<rect x="' + p[0] + '" y="' + p[1] + '" width="14" height="8" rx="1" class="th-t' + (i % 4 === 0 ? " is-deep" : "") + '"/>';
      }).join(""),
    "network-topology": '<rect x="2" y="2" width="116" height="60" rx="3" class="th-g"/>'
      + '<rect x="8" y="10" width="48" height="44" rx="2" class="th-g"/><rect x="64" y="10" width="48" height="44" rx="2" class="th-g"/>'
      + '<rect x="14" y="18" width="36" height="12" rx="1.5" class="th-t"/><rect x="14" y="36" width="36" height="12" rx="1.5" class="th-t"/>'
      + '<rect x="70" y="18" width="36" height="12" rx="1.5" class="th-t"/><rect x="70" y="36" width="36" height="12" rx="1.5" class="th-t"/>'
      + '<path d="M50 24h20M50 42h20" class="th-l"/>',
  };
  var KIND_THUMBS = {
    map: [0, 1].map(function (r) {
      return [0, 1, 2, 3].map(function (c) {
        return '<rect x="' + (4 + c * 29) + '" y="' + (6 + r * 28) + '" width="25" height="22" rx="2" class="th-t' + ((r + c) % 3 === 0 ? " is-deep" : "") + '"/>';
      }).join("");
    }).join(""),
    diagram: '<rect x="6" y="24" width="28" height="16" rx="2" class="th-t"/><rect x="46" y="8" width="28" height="16" rx="2" class="th-t is-deep"/>'
      + '<rect x="46" y="40" width="28" height="16" rx="2" class="th-t"/><rect x="86" y="24" width="28" height="16" rx="2" class="th-t"/>'
      + '<path d="M34 32l12-16M34 32l12 16M74 16l12 16M74 48l12-16" class="th-l"/>',
    report: [0, 1, 2, 3, 4].map(function (r) {
      return '<path d="M6 ' + (10 + r * 12) + 'h108" class="th-r"/>';
    }).join("") + '<path d="M40 4v56M80 4v56" class="th-l"/>',
    timeline: '<rect x="8" y="10" width="40" height="10" rx="2" class="th-t is-deep"/><rect x="30" y="27" width="56" height="10" rx="2" class="th-t"/>'
      + '<rect x="56" y="44" width="54" height="10" rx="2" class="th-t"/><path d="M8 60h104" class="th-l"/>',
  };

  // ---- the palette: one box for everything ------------------------------

  /* Views, the things in the model, and the actions the bar offers, ranked
   * by how early the words match. Ctrl+K (or the slash) opens it anywhere;
   * with nothing typed it offers the views opened most recently. */
  var pal = { open: false, hits: [], at: 0, from: null, pick: null };

  function paletteActions() {
    var here = viewEditable() ? [
      { kind: "action", name: "Add to this view…", hint: "Pin anything in the model to this drawing", go: function () { setTimeout(addToView, 0); } },
    ] : [];
    return here.concat(tourPossible() ? [
      { kind: "action", name: "Take the tour", hint: "Seven steps through the sample estate, with a pointer", go: function () { startTour(null); } },
    ] : [], [
      { kind: "action", name: "Assemble a project", hint: "Pick parts, see the drawing, save one file", go: function () { openAssemble(null); } },
      { kind: "action", name: "New product from a shape", hint: "Answer a few questions", go: openArchetypePicker },
      { kind: "action", name: "Library", hint: "Parts, blocks, patterns and component types", go: function () { openLibrary(null); } },
      { kind: "action", name: "Model", hint: "Every record and relation as tables", go: function () { openData(null); } },
      { kind: "action", name: "Flows", hint: "Business transactions, step by step", go: function () { openFlows(); } },
      { kind: "action", name: "Validate", hint: "Run every rule", go: function () { openValidate(); } },
      { kind: "action", name: "Coverage", hint: "Find the gaps", go: openCoverage },
      { kind: "action", name: "Drift", hint: "The model against the CMDB export", go: openDrift },
      { kind: "action", name: "Changes", hint: "Since an earlier revision", go: function () { openChanges(); } },
      { kind: "action", name: "Home", hint: "Where to start", go: openStart },
      { kind: "action", name: "Diagrams", hint: "Every diagram, by layer", go: function () { openDiagrams("All"); } },
      { kind: "action", name: "Stone tone", hint: "Warm grays, a teal accent", go: function () { setTone("stone"); } },
      { kind: "action", name: "Graphite tone", hint: "Neutral grays, an amber accent", go: function () { setTone("graphite"); } },
      { kind: "action", name: "Help", hint: "How to use this app", go: openGuide },
      { kind: "action", name: "Fit the drawing", hint: "The whole sheet again", go: function () { $("btnFit").click(); } },
      { kind: "action", name: "Labels on or off", hint: "Every connection's label, or none", go: function () { $("btnLabels").click(); } },
      { kind: "action", name: "Download as PNG", hint: "The drawing as a picture", go: function () { $("btnPng").click(); } },
    ]);
  }

  function paletteSearch(q) {
    q = (q || "").trim().toLowerCase();
    var views = (state.overview && state.overview.views || []).filter(function (v) { return v.ok !== false; });
    function score(name, extra) {
      if (!q) return 0;
      var n = String(name || "").toLowerCase();
      if (n.indexOf(q) === 0) return 0;
      if (n.split(/[\s\/\-_]+/).some(function (w) { return w.indexOf(q) === 0; })) return 1;
      if (n.indexOf(q) !== -1) return 2;
      if (extra && String(extra).toLowerCase().indexOf(q) !== -1) return 3;
      return -1;
    }
    var groups = [];
    if (pal.mode) {
      if (!q) return groups;
      var picks = [];
      // Things of a kind the drawing already shows come first: typing SIEM
      // on a drawing of systems means the system, not the interfaces named
      // after it.
      var shown = {};
      ((state.lastGraph && state.lastGraph.elements) || []).forEach(function (e) {
        if (e.data.entityType) shown[e.data.entityType] = true;
      });
      (state.index || []).forEach(function (item) {
        if (pal.mode.skip && pal.mode.skip(item.id)) return;
        var s = score(item.name || item.id, item.id);
        if (s >= 0) picks.push({ s: s, k: shown[item.type] ? 0 : 1, item: item });
      });
      picks.sort(function (a, b) {
        return a.s - b.s || a.k - b.k
          || String(a.item.name || a.item.id).localeCompare(String(b.item.name || b.item.id));
      });
      var mode = pal.mode;
      if (picks.length) {
        groups.push({ name: "In the model", items: picks.slice(0, 12).map(function (x) {
          return { kind: "thing", type: x.item.type, name: x.item.name || x.item.id,
            hint: x.item.id + " · " + (x.item.label || x.item.type || ""),
            go: function () { mode.onPick(x.item.id); } };
        }) });
      }
      return groups;
    }
    var vs = [];
    if (!q) {
      (state.recent || []).forEach(function (id) {
        var v = views.filter(function (x) { return x.viewId === id; })[0];
        if (v) vs.push({ s: 0, v: v });
      });
    } else {
      views.forEach(function (v) {
        var s = score(viewTitle(v), v.description);
        if (s >= 0) vs.push({ s: s, v: v });
      });
      vs.sort(function (a, b) { return a.s - b.s || viewTitle(a.v).localeCompare(viewTitle(b.v)); });
    }
    if (vs.length) {
      groups.push({ name: q ? "Views" : "Recent views", items: vs.slice(0, 7).map(function (x) {
        return { kind: "view", view: x.v, name: viewTitle(x.v),
          hint: (x.v.category || "") + " · " + (KIND_WORDS[x.v.kind] || "diagram"),
          go: function () { selectView(x.v.viewId); } };
      }) });
    }
    if (q) {
      var things = [];
      (state.index || []).forEach(function (item) {
        var s = score(item.name || item.id, item.id);
        if (s >= 0) things.push({ s: s, item: item });
      });
      things.sort(function (a, b) {
        return a.s - b.s || String(a.item.name || a.item.id).localeCompare(String(b.item.name || b.item.id));
      });
      if (things.length) {
        groups.push({ name: "In the model", items: things.slice(0, 8).map(function (x) {
          return { kind: "thing", type: x.item.type, name: x.item.name || x.item.id,
            hint: x.item.id + " · " + (x.item.label || x.item.type || ""),
            go: function () { goToEntity(x.item.id); } };
        }) });
      }
    }
    var acts = paletteActions().map(function (a) { a.s = score(a.name, a.hint); return a; })
      .filter(function (a) { return a.s >= 0; });
    acts.sort(function (a, b) { return a.s - b.s; });
    if (acts.length) groups.push({ name: "Actions", items: q ? acts : acts.slice(0, 6) });
    return groups;
  }

  function markRow() {
    var rows = $("paletteList").querySelectorAll(".pal-row");
    Array.prototype.forEach.call(rows, function (r, i) {
      r.setAttribute("aria-selected", i === pal.at ? "true" : "false");
      if (i === pal.at && r.scrollIntoView) r.scrollIntoView({ block: "nearest" });
    });
  }

  function renderPalette() {
    var list = $("paletteList");
    list.textContent = "";
    var groups = paletteSearch($("paletteBox").value);
    pal.hits = [];
    pal.pick = function (i) {
      var it = pal.hits[i];
      if (!it) return;
      closePalette();
      it.go();
    };
    groups.forEach(function (g) {
      list.appendChild(el("div", { class: "pal-group", text: g.name }));
      g.items.forEach(function (it) {
        var i = pal.hits.length;
        pal.hits.push(it);
        var mark;
        if (it.kind === "thing") {
          var s = swatchOf(it.type);
          mark = el("span", { class: "pr-k", style: "background:" + s[0] + ";border-color:" + s[1] });
        } else if (it.kind === "view") {
          mark = viewGlyph(it.view.kind, !!(it.view.parameters && it.view.parameters.length));
        } else {
          mark = el("span", { class: "pr-a", text: "›" });
        }
        list.appendChild(el("button", { class: "pal-row", type: "button", role: "option",
          "aria-selected": i === pal.at ? "true" : "false",
          onclick: function () { pal.pick(i); },
          onmousemove: function () { if (pal.at !== i) { pal.at = i; markRow(); } } }, [
          mark,
          el("span", { class: "pr-name", text: it.name }),
          el("span", { class: "pr-hint", text: it.hint || "" }),
        ]));
      });
    });
    if (!pal.hits.length) {
      list.appendChild(el("div", { class: "pal-empty", text: pal.mode
        ? ($("paletteBox").value.trim() ? "Nothing in the model matches that, or it is already on this view." : "Type a name or an id.")
        : "Nothing matches. Try a view, a system, an id or an action." }));
    }
    if (pal.at >= pal.hits.length) pal.at = 0;
    markRow();
  }

  function openPalette() {
    pal.from = document.activeElement;
    pal.open = true;
    pal.at = 0;
    $("palette").hidden = false;
    var box = $("paletteBox");
    box.value = "";
    if (!pal.placeholder) pal.placeholder = box.placeholder;
    box.placeholder = pal.mode ? pal.mode.placeholder : pal.placeholder;
    renderPalette();
    box.focus();
  }

  function openPicker(mode) {
    pal.mode = mode;
    openPalette();
  }

  function closePalette() {
    pal.open = false;
    pal.mode = null;
    $("palette").hidden = true;
    if (pal.from && pal.from.focus && document.contains(pal.from)) pal.from.focus();
  }

  // ---- miniatures ---------------------------------------------------------

  /* A small true drawing of a view: shapes in their colors, lines between
   * them, no words. A diagram is placed by dagre; a map is its groups as
   * rows of tiles. The landing page's cards and the rail's hover card use
   * them, so what a view looks like is known before it is opened. */
  var MINIS = {};

  function miniatureFor(viewId) {
    if (MINIS[viewId]) return Promise.resolve(MINIS[viewId]);
    return api("/api/graph?view=" + encodeURIComponent(viewId)).then(function (payload) {
      MINIS[viewId] = payload;
      return payload;
    });
  }

  function placeholderThumb(v) {
    var span = el("span", { class: "mini", "aria-hidden": "true" });
    span.innerHTML = '<svg viewBox="0 0 120 64">' + (THUMBS[v.viewId] || KIND_THUMBS[v.kind] || KIND_THUMBS.diagram) + "</svg>";
    return span;
  }

  function miniature(payload) {
    var NS = "http://www.w3.org/2000/svg";
    var els = payload.elements || [];
    var nodes = els.filter(function (e) { return !e.data.source && !e.data.isGroup; });
    var edges = els.filter(function (e) { return e.data.source; });
    if (!nodes.length || payload.kind === "report" || payload.kind === "timeline") return null;
    var svg = document.createElementNS(NS, "svg");
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    svg.setAttribute("aria-hidden", "true");
    function shape(n, x, y, w, h) {
      var s;
      if (n.data.entityType === "actors") {
        s = document.createElementNS(NS, "ellipse");
        s.setAttribute("cx", x + w / 2); s.setAttribute("cy", y + h / 2);
        s.setAttribute("rx", w / 2); s.setAttribute("ry", h / 2);
      } else {
        s = document.createElementNS(NS, "rect");
        s.setAttribute("x", x); s.setAttribute("y", y);
        s.setAttribute("width", w); s.setAttribute("height", h);
        s.setAttribute("rx", 2);
      }
      s.setAttribute("fill", n.data.fill || "#e2e8f0");
      s.setAttribute("stroke", n.data.stroke || "#475569");
      s.setAttribute("stroke-width", "1");
      return s;
    }
    var dagreLib = window.dagre;
    if (isTileMap(payload) || !edges.length || !dagreLib || !dagreLib.layout) {
      // Groups as boxes, tiles in rows inside each, boxes packed in rows.
      var groups = {}, order = [];
      nodes.forEach(function (n) {
        var key = n.data.parent || "";
        if (!groups[key]) { groups[key] = []; order.push(key); }
        groups[key].push(n);
      });
      var T = 18, TH = 11, G = 4, P = 6, COLS = 6, MAXW = 320;
      var x = 0, y = 0, rowH = 0, placed = [];
      order.forEach(function (key) {
        var list = groups[key];
        var cols = Math.min(COLS, list.length), rows = Math.ceil(list.length / cols);
        var cap = key ? 6 : 0;
        var bw = cols * (T + G) - G + P * 2, bh = rows * (TH + G) - G + P * 2 + cap;
        if (x + bw > MAXW && x > 0) { x = 0; y += rowH + G * 2; rowH = 0; }
        placed.push({ key: key, list: list, x: x, y: y, w: bw, h: bh, cols: cols, cap: cap });
        x += bw + G * 2;
        rowH = Math.max(rowH, bh);
      });
      var W = Math.max.apply(null, placed.map(function (p) { return p.x + p.w; }));
      svg.setAttribute("viewBox", "0 0 " + W + " " + (y + rowH));
      placed.forEach(function (p) {
        if (p.key) {
          var box = document.createElementNS(NS, "rect");
          box.setAttribute("x", p.x); box.setAttribute("y", p.y);
          box.setAttribute("width", p.w); box.setAttribute("height", p.h);
          box.setAttribute("rx", 3); box.setAttribute("fill", "#f3f5fb");
          box.setAttribute("stroke", "#c5cde0"); box.setAttribute("stroke-width", "1");
          svg.appendChild(box);
        }
        p.list.forEach(function (n, i) {
          svg.appendChild(shape(n, p.x + P + (i % p.cols) * (T + G), p.y + P + p.cap + Math.floor(i / p.cols) * (TH + G), T, TH));
        });
      });
      return svg;
    }
    var g = new dagreLib.graphlib.Graph();
    g.setGraph({ rankdir: payload.layout === "TB" ? "TB" : "LR", nodesep: 8, ranksep: 26, marginx: 4, marginy: 4 });
    g.setDefaultEdgeLabel(function () { return {}; });
    var known = {};
    nodes.forEach(function (n) { known[n.data.id] = true; g.setNode(n.data.id, { width: 30, height: 14 }); });
    edges.forEach(function (e) { if (known[e.data.source] && known[e.data.target]) g.setEdge(e.data.source, e.data.target); });
    dagreLib.layout(g);
    svg.setAttribute("viewBox", "0 0 " + Math.max(1, g.graph().width || 1) + " " + Math.max(1, g.graph().height || 1));
    g.edges().forEach(function (key) {
      var pts = g.edge(key).points || [];
      if (!pts.length) return;
      var path = document.createElementNS(NS, "path");
      path.setAttribute("d", pts.map(function (p, i) { return (i ? "L" : "M") + p.x.toFixed(1) + " " + p.y.toFixed(1); }).join(" "));
      path.setAttribute("fill", "none"); path.setAttribute("stroke", "#9aa5b8"); path.setAttribute("stroke-width", "1");
      svg.appendChild(path);
    });
    nodes.forEach(function (n) {
      var p = g.node(n.data.id);
      if (p) svg.appendChild(shape(n, p.x - p.width / 2, p.y - p.height / 2, p.width, p.height));
    });
    return svg;
  }

  function swapMini(box, viewId) {
    return miniatureFor(viewId).then(function (payload) {
      var svg = miniature(payload);
      if (!svg || !box.isConnected) return;
      box.textContent = "";
      box.appendChild(svg);
      box.classList.add("is-live");
    }).catch(function () {});
  }

  /* Resting on a view in the rail shows what it is before it is opened:
   * its miniature, its description, its size, beside the rail. */
  var peekTimer = null;
  function peekView(v, btn) {
    var box = $("railPeek");
    if (peekTimer) { clearTimeout(peekTimer); peekTimer = null; }
    if (!v || !btn) { box.hidden = true; return; }
    peekTimer = setTimeout(function () {
      var r = btn.getBoundingClientRect();
      box.textContent = "";
      var mini = placeholderThumb(v);
      box.appendChild(mini);
      box.appendChild(el("div", { class: "rp-title", text: viewTitle(v) }));
      if (v.description) box.appendChild(el("p", { class: "rp-desc", text: v.description }));
      box.appendChild(el("div", { class: "rp-n", text: (KIND_WORDS[v.kind] || "diagram")
        + (v.nodes ? " · " + v.nodes + " " + plural(v.nodes, "node") : "")
        + (v.edges ? " · " + v.edges + " " + plural(v.edges, "edge") : "") }));
      box.style.left = Math.round(r.right + 10) + "px";
      box.style.top = Math.round(Math.max(8, Math.min(r.top, window.innerHeight - 280))) + "px";
      box.hidden = false;
      swapMini(mini, v.viewId);
    }, 380);
  }

  // ---- the landing page's picture and spectrum ---------------------------

  /* The node swatches of 50_ENGINE/terrane/palette.py, for the places the page
   * colors by entity type with no graph at hand to read them from. The
   * overview carries the tone's own, estate overrides and all; this table
   * is classic's, for the moment before it arrives. */
  var TYPE_SWATCH = {
    systems: ["#c7d6ff", "#4338ca"], offered_interfaces: ["#e6ecff", "#6366f1"], products: ["#fbcfe8", "#be185d"],
    interfaces: ["#a5f3fc", "#0e7490"], data_assets: ["#a7f3d0", "#047857"], tech_services: ["#fed7aa", "#c2410c"], capabilities: ["#ddd6fe", "#6d28d9"],
    value_streams: ["#e9d5ff", "#9333ea"], value_stream_stages: ["#f3e8ff", "#a855f7"], org_units: ["#cbd5e1", "#334155"],
    actors: ["#fde68a", "#b45309"], flows: ["#fbcfe8", "#db2777"], controls: ["#fca5a5", "#b91c1c"],
    policies: ["#fecaca", "#dc2626"], frameworks: ["#d9f99d", "#4d7c0f"], processes: ["#bae6fd", "#0369a1"],
    roadmaps: ["#99f6e4", "#0f766e"], work_packages: ["#ccfbf1", "#0d9488"], architecture_change_requests: ["#fef08a", "#a16207"],
  };
  function swatchOf(type) {
    var toned = state.overview && state.overview.swatches;
    if (toned) {
      var s = toned[type] || toned["default"];
      if (s) return [s.fill, s.stroke];
    }
    return TYPE_SWATCH[type] || ["#e2e8f0", "#475569"];
  }

  /* Each layer on the rail wears the color of the entity its views are
   * mostly about, so the list and the drawings agree about what is what. */
  var LAYER_TYPE = { Business: "capabilities", Application: "systems", Data: "data_assets",
    Technology: "tech_services", Governance: "controls", Change: "work_packages", Flows: "flows" };
  function layerSwatchStyle(name) {
    var s = swatchOf(LAYER_TYPE[name] || "");
    return "--lf:" + s[0] + ";--ls:" + s[1];
  }

  //: What each validation rule means, in a sentence, for the list of
  //: warnings by rule. A code the map does not know is shown as itself.
  var RULE_WORDS = {
    "cmdb.unlinked": "Systems with no CMDB id",
    "governance.no_control": "Restricted systems recording no control",
    "governance.tier": "High-criticality systems with no service tier",
    "change.no_decision": "Work packages naming no change request",
    "pattern.deprecated": "Products applying a deprecated pattern",
    "types.unlisted_part": "Products with a part their build type does not list",
    "types.required_part": "Products missing a part their build type requires",
    "types.included_part": "Products that dropped a part their build type includes",
    "view.truncated": "Views that hit their node budget",
    "model.load": "Rows the loader had to drop",
    "library.shape_candidate": "Hand-written products a shape would reproduce",
    "library.unused_part": "Parts no product composes",
  };

  // ---- the pictures -------------------------------------------------------

  /* A picture per kind of diagram for the Diagrams page, drawn rather than
   * shot. Two inks and paper on a dotted plate, an offset shadow under what
   * matters, one accent where the eye should go. The six were drawn in the
   * design file (its "Illustration" components) and are written out here as the same shapes at the same coordinates; the
   * tone's colors are left to the stylesheet, so one set serves both tones.
   * The screenshots they replace were pastel thumbnails nobody could read at
   * card size, and a different picture style on every card. */
  var ILLO = (function () {
    var cache = {};
    function rect(x, y, w, h, cls, o) {
      o = o || {};
      var rx = o.r === undefined ? 3 : o.r, out = "";
      if (o.shadow) {
        out += '<rect class="k" x="' + (x + o.shadow) + '" y="' + (y + o.shadow) + '" width="' + w + '" height="' + h
          + '" rx="' + rx + '"/>';
      }
      return out + '<rect class="' + cls + '" x="' + x + '" y="' + y + '" width="' + w + '" height="' + h + '" rx="' + rx
        + '" stroke-width="' + (o.sw || 1.5) + '"/>';
    }
    function circle(cx, cy, r, cls, o) {
      o = o || {};
      var out = o.shadow ? '<circle class="k" cx="' + (cx + o.shadow) + '" cy="' + (cy + o.shadow) + '" r="' + r + '"/>' : "";
      return out + '<circle class="' + cls + '" cx="' + cx + '" cy="' + cy + '" r="' + r + '" stroke-width="' + (o.sw || 1.5) + '"/>';
    }
    function bar(x, y, w, cls) {
      return '<rect class="' + (cls || "lbl") + '" x="' + x + '" y="' + y + '" width="' + w + '" height="3" rx="1.5"/>';
    }
    function line(d, cls, sw) {
      return '<path class="' + (cls || "ln") + '" d="' + d + '" stroke-width="' + (sw || 1.5) + '"/>';
    }
    function curve(x1, y1, x2, y2) {
      var d = (x2 - x1) / 2;
      return "M" + x1 + " " + y1 + "C" + (x1 + d) + " " + y1 + " " + (x2 - d) + " " + y2 + " " + x2 + " " + y2;
    }
    function plug(x, y) { return '<circle class="k" cx="' + x + '" cy="' + y + '" r="2.5"/>'; }
    /* A box on a picture: paper, the wash, the mute or the accent, with an
     * offset shadow and, when there is room, two bars for its label. */
    function tile(x, y, w, h, kind, o) {
      o = o || {};
      var out = rect(x, y, w, h, kind, { shadow: o.shadow === undefined ? 2 : o.shadow, sw: o.sw || 1.25, r: o.r });
      if (o.labels !== false && w >= 30) {
        var lc = kind === "a" ? "on" : "lbl";
        out += bar(x + 7, y + 8, Math.min(30, w - 14), lc);
        if (h >= 24) out += bar(x + 7, y + 15, Math.min(18, w - 20), lc);
      }
      return out;
    }
    function person(x, y) {
      return circle(x + 12, y + 6, 6, "p") + '<path class="w" d="M' + x + " " + (y + 29) + "V" + (y + 27) + "A12 12 0 0 1 "
        + (x + 24) + " " + (y + 27) + "V" + (y + 29) + 'Z" stroke-width="1.5"/>';
    }
    function store(x, y, w, h, body, cap, shadow) {
      var ry = Math.round(h * 0.16);
      function geo(dx) {
        return "M" + (x + dx) + " " + (y + ry + dx) + "L" + (x + dx) + " " + (y + h - ry + dx) + "A" + (w / 2) + " " + ry
          + " 0 0 0 " + (x + w + dx) + " " + (y + h - ry + dx) + "L" + (x + w + dx) + " " + (y + ry + dx) + "Z";
      }
      var out = "";
      if (shadow) {
        out += '<path class="k" d="' + geo(shadow) + '"/><ellipse class="k" cx="' + (x + w / 2 + shadow) + '" cy="'
          + (y + ry + shadow) + '" rx="' + (w / 2) + '" ry="' + ry + '"/>';
      }
      return out + '<path class="' + body + '" d="' + geo(0) + '" stroke-width="1.5"/><ellipse class="' + cap + '" cx="'
        + (x + w / 2) + '" cy="' + (y + ry) + '" rx="' + (w / 2) + '" ry="' + ry + '" stroke-width="1.5"/>';
    }

    var DRAWN = {
      context: function () {
        var out = line(curve(58, 52, 120, 80) + curve(58, 134, 120, 96) + curve(200, 80, 244, 48) + curve(200, 96, 244, 128));
        out += person(32, 30) + person(32, 112);
        out += rect(120, 66, 80, 44, "a", { shadow: 3 }) + bar(130, 79, 40, "on") + bar(130, 86, 26, "on");
        [[120, 80], [120, 96], [200, 80], [200, 96]].forEach(function (p) { out += plug(p[0], p[1]); });
        return out + tile(244, 34, 56, 28, "p") + tile(244, 114, 56, 28, "m");
      },
      landscape: function () {
        var out = "";
        [[20, 18, 140, 68], [170, 18, 140, 68], [20, 96, 290, 62]].forEach(function (g) {
          out += rect(g[0], g[1], g[2], g[3], "mute bare", { r: 6 }) + bar(g[0] + 10, g[1] + 8, 34);
        });
        function grid(x0, y0, cols, step, kinds) {
          kinds.split("").forEach(function (k, i) {
            out += tile(x0 + (i % cols) * step, y0 + Math.floor(i / cols) * 21, 25, 15, k, { labels: false });
          });
        }
        grid(30, 38, 4, 31, "papwpwp");
        grid(180, 38, 4, 31, "wppppw");
        grid(30, 114, 9, 30.5, "ppwpppwpppwppwp");
        return out;
      },
      capability: function () {
        var out = "";
        [[[52, "w"], [70, "p"], [46, "a"], [54, "w"]], [[38, "p"], [58, "w"], [62, "p"], [34, "w"], [24, "p"]],
         [[84, "w"], [48, "a"], [58, "p"], [32, "w"]]].forEach(function (row, i) {
          var y = 22 + i * 47, x = 70;
          out += rect(20, y, 42, 38, "k bare", { r: 4 }) + bar(28, y + 10, 22, "on") + bar(28, y + 17, 14, "on");
          row.forEach(function (t) { out += tile(x, y, t[0], 38, t[1]); x += t[0] + 6; });
        });
        return out;
      },
      integration: function () {
        var top = [[40, "p"], [108, "w"], [176, "p"], [244, "m"]], bottom = [[74, "w"], [142, "p"], [210, "p"]];
        var out = line(top.map(function (t) { return "M" + (t[0] + 23) + " 54V82"; }).join("")
          + bottom.map(function (t) { return "M" + (t[0] + 23) + " 94V124"; }).join(""));
        out += rect(30, 82, 270, 12, "a", { shadow: 3, r: 6 });
        [70, 158, 236].forEach(function (x) { out += '<rect class="on" x="' + x + '" y="86" width="12" height="4" rx="2"/>'; });
        top.forEach(function (t) { out += tile(t[0], 26, 46, 28, t[1]); });
        bottom.forEach(function (t) { out += tile(t[0], 124, 46, 28, t[1]); });
        top.forEach(function (t) { out += circle(t[0] + 23, 68, 3.5, "p", { sw: 1.25 }); });
        bottom.forEach(function (t) { out += circle(t[0] + 23, 109, 3.5, "p", { sw: 1.25 }); });
        return out;
      },
      lineage: function () {
        var out = line(curve(64, 42, 128, 55) + curve(64, 91, 128, 55) + curve(64, 91, 128, 119) + curve(64, 140, 128, 119)
          + curve(186, 55, 254, 80) + curve(186, 119, 254, 100));
        [22, 71, 120].forEach(function (y) { out += store(24, y, 40, 34, "w", "p", 2); });
        out += tile(128, 40, 58, 30, "p") + tile(128, 104, 58, 30, "w");
        out += store(254, 60, 54, 56, "a", "w", 3);
        [[128, 55], [128, 119], [254, 80], [254, 100]].forEach(function (p) { out += plug(p[0], p[1]); });
        return out;
      },
      network: function () {
        var out = '<rect class="ik" x="64" y="16" width="252" height="144" rx="6" stroke-width="1.25" stroke-dasharray="5 4"/>';
        out += rect(76, 11, 36, 10, "k bare", { r: 3 }) + '<rect class="on" x="82" y="14.5" width="22" height="3" rx="1.5"/>';
        out += line("M44 94H57M71 94H80M176 70H204M176 118H204");
        var nodes = [["waw", "wwm"], ["mww", "wmw"]];
        [80, 196].forEach(function (zx, zi) {
          out += rect(zx, 32, 104, 114, "mute bare", { r: 6 }) + bar(zx + 8, 39, 26);
          [50, 98].forEach(function (sy, si) {
            out += tile(zx + 8, sy, 88, 40, "p", { labels: false });
            nodes[zi][si].split("").forEach(function (k, ni) {
              out += tile(zx + 18 + ni * 26, sy + 12, 16, 16, k, { labels: false, shadow: 0 });
            });
          });
        });
        [[80, 94], [176, 70], [204, 70], [176, 118], [204, 118]].forEach(function (p) { out += plug(p[0], p[1]); });
        out += circle(28, 94, 16, "p", { shadow: 2 });
        out += '<ellipse class="ik" cx="28" cy="94" rx="6" ry="16" stroke-width="1.25"/>' + line("M13 94H43", "ik", 1.25);
        return out + '<path class="a" d="M64 87L71 94L64 101L57 94Z" stroke-width="1.5"/>';
      },
      report: function () {
        var out = rect(48, 20, 234, 136, "p", { shadow: 3, r: 5 });
        out += '<rect class="mute" x="49.5" y="21.5" width="231" height="20" rx="3.5"/>';
        out += bar(60, 29, 40) + bar(150, 29, 30) + bar(232, 29, 28);
        var first = [52, 40, 60, 34, 46], second = [30, 44, 26, 38, 30], pill = ["a", "w", "p", "w", "m"];
        for (var i = 0; i < 5; i++) {
          var y = 42 + i * 22.8;
          if (i) out += line("M48 " + y + "H282", "ln", 1);
          out += bar(60, y + 10, first[i]) + bar(150, y + 10, second[i]);
          out += rect(230, y + 7, 36, 9, pill[i], { r: 4.5, sw: 1 });
        }
        return out;
      },
      timeline: function () {
        var out = '<path class="ln" d="M96 30V160M150 30V160M204 30V160M258 30V160" stroke-width="1" stroke-dasharray="3 4"/>';
        [96, 150, 204, 258].forEach(function (x) { out += bar(x + 8, 18, 22); });
        var labels = [44, 36, 50, 40, 30];
        var bars = [[96, 92, "w"], [132, 110, "p"], [150, 60, "a"], [190, 100, "w"], [232, 70, "p"]];
        bars.forEach(function (b, i) {
          var y = 40 + i * 24;
          out += bar(22, y + 5, labels[i]) + rect(b[0], y, b[1], 14, b[2], { shadow: 2, r: 4, sw: 1.25 });
        });
        return out + '<path class="al" d="M222 26V166" stroke-width="2"/>';
      },
    };

    /* Which picture a view gets: a report its table, a timeline its bars,
     * then by what the view is about, read from its name, and otherwise by
     * its kind. A rule here is a guess about a name; a wrong guess is a
     * picture of a neighboring kind of diagram, never a wrong number. */
    var RULES = [
      [/lineage|data-flow|dissemination|data-and-processes|restricted-data/, "lineage"],
      [/network|topology|multi-az|hosting|tiered|technology-stack|platform/, "network"],
      [/integration|hub-and-spoke|process-systems|interface/, "integration"],
      [/capabilit|value-stream|framework|apqc|bian|cri-|dmbok|itil|process-landscape|alignment/, "capability"],
      [/landscape|domain|estate|portfolio|ownership|parts|vendor|channels/, "landscape"],
    ];
    //: The six the design drew, by name: data lineage is a table in the
    //: model, but what it is about is where data goes.
    //: A framework's landscape is nested boxes in the framework's own terms,
    //: which is the landscape's picture rather than the tiers of the map.
    var NAMED = { "system-context": "context", "application-landscape": "landscape", "capability-map": "capability",
      "framework-landscape": "landscape",
      "integration-architecture": "integration", "data-lineage": "lineage", "network-topology": "network" };
    function keyFor(v) {
      if (NAMED[v.viewId]) return NAMED[v.viewId];
      if (v.kind === "report") return "report";
      if (v.kind === "timeline") return "timeline";
      var id = String(v.viewId || "");
      for (var i = 0; i < RULES.length; i++) if (RULES[i][0].test(id)) return RULES[i][1];
      return v.kind === "map" ? "landscape" : "context";
    }
    return {
      keyFor: keyFor,
      of: function (v) {
        var key = keyFor(v);
        if (!cache[key]) {
          cache[key] = '<svg viewBox="0 0 330 176" aria-hidden="true" focusable="false"><rect class="dots" width="330" height="176"/>'
            + DRAWN[key]() + "</svg>";
        }
        var box = el("span", { class: "illo", "data-illo": key });
        box.innerHTML = cache[key];
        return box;
      },
    };
  })();

  // ---- the Diagrams page --------------------------------------------------

  //: What the cards say for the views a newcomer should see first, in the
  //: order they lead the page; the rest say their own description.
  var CARD_WORDS = [
    ["system-context", "A system, who uses it, and what it connects to."],
    ["application-landscape", "Every system, grouped by business domain."],
    ["capability-map", "Everything the business does, on one page."],
    ["integration-architecture", "How systems talk to each other, and over what."],
    ["data-lineage", "Where each data asset comes from and where it goes."],
    ["network-topology", "Cloud accounts, regions and zones, and the links between them."],
  ];

  function singular(word) {
    if (/ies$/.test(word)) return word.replace(/ies$/, "y");
    if (/sses$/.test(word)) return word.replace(/sses$/, "ss");
    if (/(x|ch|sh)es$/.test(word)) return word.replace(/es$/, "");
    return word.replace(/s$/, "");
  }

  /* What a card's boxes are: "22 capabilities", or the two kinds there are
   * most of, "12 systems, 4 data assets". A view about one subject at a
   * time says so instead, since its count is only the first subject's. */
  function cardCount(v) {
    if (v.parameters && v.parameters.length) {
      return "pick a " + String(v.parameters[0]).replace(/_/g, " ");
    }
    if (v.kind === "report") return v.nodes + " " + plural(v.nodes, "row");
    var types = v.types || {};
    var keys = Object.keys(types).sort(function (a, b) { return types[b] - types[a]; });
    if (!keys.length) return v.nodes ? v.nodes + " " + plural(v.nodes, "item") : "";
    return keys.slice(0, 2).map(function (k) {
      var word = k.replace(/_/g, " ");
      return types[k] + " " + (types[k] === 1 ? singular(word) : word);
    }).join(", ");
  }

  function galleryCard(v, words) {
    var meta = v.ok === false ? "Cannot be drawn: " + (v.problem || "the view did not resolve")
      : [v.category, cardCount(v)].filter(Boolean).join(" · ");
    return el("button", { class: "gcard" + (v.ok === false ? " is-broken" : ""), type: "button",
      "data-view": v.viewId, title: v.description || "",
      onclick: function () { showPanel(false); selectView(v.viewId); } }, [
      ILLO.of(v),
      el("span", { class: "g-title", text: viewTitle(v) }),
      el("span", { class: "g-desc", text: words || v.description || "" }),
      el("span", { class: "g-meta", text: meta }),
    ]);
  }

  /* The Diagrams page: what this tool is for, in a line; every diagram the
   * model draws, as a picture, by layer; and the two ways to add one. The
   * dashboard that was here (counts, warnings, coverage, the log) answered
   * questions the Checks page answers better, and pushed the diagrams below
   * the fold on the page that is about them. */
  // ---- Home -----------------------------------------------------------------

  var RECENT_KEY = "terrane.recent";

  function recentViews() {
    var ids = [];
    try { ids = JSON.parse(localStorage.getItem(RECENT_KEY) || "[]") || []; } catch (err) { ids = []; }
    var byId = {};
    ((state.overview && state.overview.views) || []).forEach(function (v) { byId[v.viewId] = v; });
    return ids.map(function (id) { return byId[id]; }).filter(function (v) { return v && v.ok !== false; });
  }

  function rememberView(viewId) {
    var ids = [];
    try { ids = JSON.parse(localStorage.getItem(RECENT_KEY) || "[]") || []; } catch (err) { ids = []; }
    ids = [viewId].concat(ids.filter(function (id) { return id !== viewId; })).slice(0, 6);
    try { localStorage.setItem(RECENT_KEY, JSON.stringify(ids)); } catch (err) { /* private mode */ }
  }

  /* Home: what this is and where to go from here. The diagrams opened last
   * (or, the first time, three to start with), every layer as a way in,
   * and the model's state in a line. Not a dashboard: the checks have a page
   * of their own, and a number on the start page is a number nobody acts on. */
  // Lucide's arrow-right (ISC), the set the sidebar and the type marks use.
  var SVG_NS = "http://www.w3.org/2000/svg";
  function goArrow() {
    var svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("class", "he-go");
    svg.setAttribute("aria-hidden", "true");
    ["M5 12h14", "m12 5 7 7-7 7"].forEach(function (d) {
      var path = document.createElementNS(SVG_NS, "path");
      path.setAttribute("d", d);
      svg.appendChild(path);
    });
    return svg;
  }

  function openStart() {
    var o = state.overview || {};
    state.panel = "start";
    showPanel(true);
    var panel = $("dataPanel");
    panel.textContent = "";
    panel.classList.remove("is-table");
    var readOnly = !!window.__AAC_STATIC__;
    var views = o.views || [];

    // The estates the hosted demo publishes, as tabs over the head: the one
    // being read underlined, the others links to their own copy of the
    // site. The export writes the list beside the page from what it baked;
    // the local app serves one model and has no other to link, so it asks
    // for nothing and the strip stays empty.
    var estates = el("nav", { class: "home-estates", "aria-label": "Estates on this demo" });
    panel.appendChild(estates);
    if (readOnly) {
      fetch(new URL("estates.json", document.baseURI).href, { cache: "no-store" }).then(function (res) {
        return res.ok ? res.json() : null;
      }).then(function (data) {
        var list = (data && data.estates) || [];
        if (list.length < 2) return;
        estates.appendChild(el("span", { class: "he-lead", text: "Estates on this demo" }));
        list.forEach(function (estate) {
          var name = el("span", { class: "pt-label", text: estate.name });
          var kids = [name, estate.line ? el("span", { class: "pt-note", text: estate.line }) : null];
          if (estate.here) {
            estates.appendChild(el("span", { class: "page-tab is-on", "aria-current": "page" }, kids));
            return;
          }
          name.appendChild(goArrow());
          estates.appendChild(el("a", { class: "page-tab", href: estate.href }, kids));
        });
      }).catch(function () {});
    }

    panel.appendChild(el("div", { class: "gallery-head start-head" }, [
      el("div", {}, [
        el("h1", { text: o.modelName || "Architecture Model" }),
        el("p", { class: "lede", text: o.empty ? "An empty estate. Its " + views.length + " diagrams draw as soon as there "
          + "are records for them."
          : "Your architecture as one model, and every diagram drawn from it: "
          + "change a system once and every diagram it belongs to follows." }),
      ]),
      el("div", { class: "acts" }, [
        el("button", { class: "btn", type: "button", disabled: readOnly ? "disabled" : null, onclick: function () { openSettings("sources"); } },
          [svgIcon("i-upload"), el("span", { text: "Import" })]),
        el("button", { class: "btn primary", type: "button", disabled: readOnly ? "disabled" : null,
          onclick: function () { openCanvas(null); } }, [svgIcon("i-plus"), el("span", { text: "New diagram" })]),
      ]),
    ]));

    if (o.empty) {
      firstHour(panel, o);
      syncUrl();
      return;
    }
    if (o.estate && o.estate.sample && !readOnly) {
      panel.appendChild(el("div", { class: "st-callout sample-note" }, [
        el("p", { text: "This is the sample estate, a card issuer, here to show what a full estate draws. Your own starts "
          + "empty, in a folder and a repository of its own, and brings in your inventory." }),
        el("span", { class: "sample-acts" }, [
          tourPossible() ? el("button", { class: "btn small", type: "button", text: "Take the tour",
            onclick: function (e) { startTour(e.currentTarget.getBoundingClientRect()); } }) : null,
          el("button", { class: "btn small", type: "button", text: "Start your own estate", onclick: function () { openProject("start"); } }),
        ]),
      ]));
    }
    tourOffer(panel);
    var recent = recentViews().slice(0, 3);
    var words = {};
    CARD_WORDS.forEach(function (pair) { words[pair[0]] = pair[1]; });
    var starters = recent.length ? recent : CARD_WORDS.slice(0, 3).map(function (pair) {
      return views.filter(function (v) { return v.viewId === pair[0]; })[0];
    }).filter(Boolean);
    panel.appendChild(el("div", { class: "start-sec" }, [
      el("h2", { text: recent.length ? "Pick up where you left off" : "Start with these" }),
      el("button", { class: "hp-link", type: "button", text: "All " + views.length + " diagrams", onclick: function () { openDiagrams("All"); } }),
    ]));
    var grid = el("div", { class: "gallery start-recent" });
    starters.forEach(function (v) { grid.appendChild(galleryCard(v, words[v.viewId])); });
    panel.appendChild(grid);

    panel.appendChild(el("div", { class: "start-sec" }, [el("h2", { text: "Diagrams by layer" })]));
    var layers = el("div", { class: "start-layers" });
    groupViews(views).forEach(function (g) {
      var sections = sectionsOf(g.views).map(function (s) { return s.name; }).filter(Boolean);
      layers.appendChild(el("button", { class: "start-layer", type: "button", style: layerSwatchStyle(g.name),
        onclick: function () { openDiagrams(g.name); } }, [
        el("span", { class: "sl-head" }, [el("span", { class: "shelf-name", text: g.name }),
          el("span", { class: "sl-n", text: g.views.length + " " + plural(g.views.length, "diagram") })]),
        el("span", { class: "sl-what", text: sections.length ? sections.join(" \u00b7 ")
          : g.views.slice(0, 3).map(viewTitle).join(" \u00b7 ") }),
      ]));
    });
    if (o.flowCount !== undefined) {
      layers.appendChild(el("button", { class: "start-layer", type: "button", style: layerSwatchStyle("Flows"),
        onclick: function () { openFlows(); } }, [
        el("span", { class: "sl-head" }, [el("span", { class: "shelf-name", text: "Flows" }),
          el("span", { class: "sl-n", text: o.flowCount + " " + plural(o.flowCount, "flow") })]),
        el("span", { class: "sl-what", text: "Business transactions, traced across systems step by step" }),
      ]));
    }
    panel.appendChild(layers);

    var known = (state.schema && state.schema.entities) || null;
    var types = Object.keys(o.counts || {}).filter(function (k) { return o.counts[k] > 0 && (!known || known[k]); }).length;
    panel.appendChild(el("div", { class: "start-sec" }, [el("h2", { text: "The model" })]));
    panel.appendChild(el("p", { class: "start-model" }, [
      Number(o.entityCount || 0).toLocaleString("en-US") + " records of " + types + " " + plural(types, "type") + ", "
        + Number(o.relationCount || 0).toLocaleString("en-US") + " relationships. ",
      el("button", { class: "hp-link", type: "button", text: "Open the model", onclick: function () { openData(null); } }),
      el("span", { class: "start-dot", text: " \u00b7 " }),
      (o.errors ? o.errors + " " + plural(o.errors, "error") + " block a merge" : "Every gate passes")
        + ", " + (o.warnings || 0) + " " + plural(o.warnings || 0, "warning") + ". ",
      el("button", { class: "hp-link", type: "button", text: "Open the checks", onclick: function () { openValidate(); } }),
    ]));
    var thin = el("p", { class: "start-model" });
    panel.appendChild(thin);
    api("/api/needs").then(function (d) {
      var s = d.states;
      if (!s.thin && !s.empty) return;
      thin.appendChild(document.createTextNode([s.empty ? s.empty + " " + plural(s.empty, "diagram") + " " + (s.empty === 1
        ? "has" : "have") + " nothing to draw yet" : "", s.thin ? s.thin + " " + (s.thin === 1 ? "draws" : "draw") + " thin" : ""]
        .filter(Boolean).join(" and ") + ". "));
      thin.appendChild(el("button", { class: "hp-link", type: "button", text: "See what they need", onclick: function () { openNeeds(); } }));
    }).catch(function () { /* the published copy has no needs to read */ });
    syncUrl();
  }

  function openDiagrams(layer) {
    var o = state.overview || {};
    state.panel = "diagrams";
    if (layer) state.homeLayer = layer;
    var current = state.homeLayer || "All";
    showPanel(true);
    var panel = $("dataPanel");
    panel.textContent = "";
    panel.classList.remove("is-table");
    var readOnly = !!window.__AAC_STATIC__;
    var views = o.views || [];
    var words = {};
    CARD_WORDS.forEach(function (pair) { words[pair[0]] = pair[1]; });

    panel.appendChild(el("div", { class: "gallery-head" }, [
      el("div", {}, [
        el("h1", { text: "Diagrams" }),
        el("p", { class: "lede", text: "Every diagram here is drawn from one model of your architecture. "
          + "Change a system once, and every diagram it belongs to follows." }),
      ]),
      el("div", { class: "acts" }, [
        el("button", { class: "btn", type: "button", id: "galleryImport", disabled: readOnly ? "disabled" : null,
          onclick: function () { openSettings("sources"); } }, [svgIcon("i-upload"), el("span", { text: "Import" })]),
        el("button", { class: "btn primary", type: "button", id: "galleryNew", disabled: readOnly ? "disabled" : null,
          onclick: function () { openCanvas(null, state.homeLayer); } }, [svgIcon("i-plus"), el("span", { text: "New diagram" })]),
      ]),
    ]));

    var groups = groupViews(views);
    var tabs = el("div", { class: "layer-tabs", role: "tablist", "aria-label": "Layers" });
    function tab(name, n, go) {
      tabs.appendChild(el("button", { class: "layer-tab", type: "button", role: "tab",
        "aria-selected": name === current ? "true" : "false", onclick: go }, [
        el("span", { text: name }), el("span", { class: "n num", text: String(n) }),
      ]));
    }
    tab("All", views.length, function () { openDiagrams("All"); });
    groups.forEach(function (g) { tab(g.name, g.views.length, function () { openDiagrams(g.name); }); });
    if (o.flowCount !== undefined) tab("Flows", o.flowCount, function () { openFlows(); });
    panel.appendChild(tabs);

    // The six a newcomer should see lead, in the order they are listed;
    // then everything else in the layer order the sidebar uses.
    var shown = current === "All" ? views : views.filter(function (v) {
      return (VIEW_CATEGORIES.indexOf(v.category) === -1 ? "Other" : v.category) === current;
    });
    var lead = CARD_WORDS.map(function (pair) {
      return shown.filter(function (v) { return v.viewId === pair[0]; })[0];
    }).filter(Boolean);
    var rest = [];
    groupViews(shown).forEach(function (g) {
      g.views.forEach(function (v) { if (lead.indexOf(v) === -1) rest.push(v); });
    });
    // A layer's page is sectioned as the layer is, under the section's name;
    // the whole set leads with the six and runs on in layer order.
    var sections = current === "All" ? [] : sectionsOf(shown);
    if (sections.length > 1) {
      sections.forEach(function (s) {
        panel.appendChild(el("h2", { class: "gallery-sec", text: s.name || "More" }));
        var part = el("div", { class: "gallery" });
        s.views.forEach(function (v) { part.appendChild(galleryCard(v, words[v.viewId])); });
        panel.appendChild(part);
      });
    } else {
      var grid = el("div", { class: "gallery" });
      lead.concat(rest).forEach(function (v) { grid.appendChild(galleryCard(v, words[v.viewId])); });
      panel.appendChild(grid);
    }
    renderViewList(o);

    // The review pack, where the Pages job built one beside the site: a
    // slide per view, from the same model. Locally it is a command, and the
    // line stays empty rather than promising a file that is not there.
    var deck = el("p", { class: "gallery-foot" });
    panel.appendChild(deck);
    fetch(new URL("review-pack.pptx", document.baseURI).href, { method: "HEAD", cache: "no-store" }).then(function (res) {
      if (!res.ok) return;
      var size = Number(res.headers.get("content-length") || 0);
      deck.appendChild(el("a", { href: "review-pack.pptx", download: "review-pack.pptx", text: "Download the review pack" }));
      deck.appendChild(document.createTextNode(
        " · a slide per diagram with its picture, its description and its counts, built from this commit"
        + (size ? " (" + Math.max(1, Math.round(size / 1048576)) + " MB, PowerPoint)." : " (PowerPoint).")));
    }).catch(function () {});
    if (readOnly) {
      panel.appendChild(el("p", { class: "gallery-foot", text:
        "This is the read-only copy. Everything that reads the model works here; what writes "
        + "runs in the local app, started with python 80_APP/app/server.py." }));
    }
    syncUrl();
  }

  function svgIcon(id) {
    var NS = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(NS, "svg");
    svg.setAttribute("class", "i");
    svg.setAttribute("aria-hidden", "true");
    var use = document.createElementNS(NS, "use");
    use.setAttribute("href", "#" + id);
    svg.appendChild(use);
    return svg;
  }

  function openData(tableId) {
    api("/api/table").then(function (catalog) {
      state.panel = "data";
      showPanel(true);
      var panel = $("dataPanel");
      panel.textContent = "";
      panel.classList.add("is-table");

      var head = el("div", { class: "panel-head" }, [
        el("div", {}, [
          el("h1", { text: "Model" }),
          el("p", { class: "sub", text:
            "Every field of every record, and every row of every relation. This is "
            + "the model, not a rendering of it." }),
        ]),
      ]);
      panel.appendChild(head);

      var types = el("div", { class: "data-types", "aria-label": "Tables" });
      var host = el("div", { class: "table-host data-main" });
      panel.appendChild(el("div", { class: "data-cols" }, [types, host]));

      var tables = catalog.entities.map(function (t) {
        return { id: t.id, kind: "entity", label: t.label, plural: t.plural, count: t.count };
      }).concat(catalog.relations.map(function (t) {
        return { id: t.id, kind: "relation", label: t.label, plural: t.label, count: t.count };
      }));

      // A row per table: the entity's own swatch, its name, how many rows.
      function rowFor(t) {
        var sw = t.kind === "entity" ? swatchOf(t.id) : null;
        var row = el("button", { class: "data-type" + (t.kind === "relation" ? " is-rel" : "") + (t.count ? "" : " is-empty"),
          type: "button", onclick: function () { loadTable(t); } }, [
          sw ? el("span", { class: "dt-sw", style: "background:" + sw[0] + ";border-color:" + sw[1] })
             : el("span", { class: "dt-sw is-rel" }),
          el("span", { class: "dt-name", text: t.kind === "entity" ? t.plural : t.label }),
          el("span", { class: "dt-n num", text: String(t.count) }),
        ]);
        row.dataset.id = t.id;
        return row;
      }
      types.appendChild(el("p", { class: "dt-group", text: "Entities \u00b7 " + catalog.entities.length }));
      tables.filter(function (t) { return t.kind === "entity"; }).forEach(function (t) { types.appendChild(rowFor(t)); });
      types.appendChild(el("p", { class: "dt-group", text: "Relations \u00b7 " + catalog.relations.length }));
      tables.filter(function (t) { return t.kind === "relation"; }).forEach(function (t) { types.appendChild(rowFor(t)); });

      function loadTable(t) {
        state.dataTable = t.id;
        syncUrl();
        Array.prototype.forEach.call(types.querySelectorAll(".data-type"), function (c) {
          c.classList.toggle("is-on", c.dataset.id === t.id);
        });
        var query = t.kind === "entity"
          ? "type=" + encodeURIComponent(t.id)
          : "relation=" + encodeURIComponent(t.id);
        host.textContent = "";
        host.appendChild(el("p", { class: "brief-hint", text: "Loading\u2026" }));
        api("/api/table?" + query).then(function (data) {
          state.table = data;
          renderTable(host, data);
          var rows = (data.rows || []).length, cols = (data.columns || []).length;
          host.insertBefore(el("div", { class: "data-head" }, [
            el("h2", { class: "data-title", text: t.kind === "entity" ? t.plural : t.label }),
            el("span", { class: "kind-tag", text: rows + " " + plural(rows, t.kind === "entity" ? "record" : "row")
              + " \u00b7 " + cols + " " + plural(cols, "field") }),
          ]), host.firstChild);
        }).catch(function (err) {
          host.textContent = "";
          host.appendChild(el("p", { class: "brief-hint", text: err.message }));
        });
      }

      var wanted = tables.filter(function (t) { return t.id === tableId; })[0]
        || tables.filter(function (t) { return t.count; })[0];
      if (wanted) loadTable(wanted);
    }).catch(fail);
  }

  function renderTable(host, data) {
    host.textContent = "";
    var showEmpty = false;
    var sort = { column: null, dir: 1 };
    var filter = "";

    var filterBox = el("input", { type: "search", class: "table-filter",
      placeholder: "Filter " + data.count + " rows\u2026",
      "aria-label": "Filter rows" });
    var constants = data.columns.filter(function (c) { return c.constant !== undefined; });
    var emptyToggle = el("label", { class: "table-toggle" }, [
      el("input", { type: "checkbox" }),
      el("span", { text: constants.length ? "Show every column" : "Show empty columns" }),
    ]);
    var bar = el("div", { class: "table-bar" }, [
      filterBox,
      emptyToggle,
      el("span", { class: "table-count mono", id: "tableCount" }),
      el("button", { class: "btn small", type: "button", text: "CSV",
        onclick: function () {
          download(data.id + ".csv", tableCsv(data, visibleColumns(), currentRows()), "text/csv");
        } }),
      el("button", { class: "btn small", type: "button", text: "JSON",
        onclick: function () {
          download(data.id + ".json", JSON.stringify(currentRows(), null, 1), "application/json");
        } }),
    ]);
    var scroll = el("div", { class: "table-scroll" });
    host.appendChild(bar);
    host.appendChild(scroll);

    function visibleColumns() {
      return data.columns.filter(function (c) { return showEmpty || (c.filled > 0 && c.constant === undefined); });
    }

    function currentRows() {
      var q = filter.trim().toLowerCase();
      var rows = !q ? data.rows.slice() : data.rows.filter(function (row) {
        return Object.keys(row).some(function (k) {
          return String(row[k] === null || row[k] === undefined ? "" : row[k])
            .toLowerCase().indexOf(q) !== -1;
        });
      });
      if (sort.column) {
        rows.sort(function (a, b) {
          var x = a[sort.column], y = b[sort.column];
          var ax = x === null || x === undefined ? "" : String(x);
          var by = y === null || y === undefined ? "" : String(y);
          // Empty last whichever way it is sorted: a blank is not a value.
          if (!ax && by) return 1;
          if (ax && !by) return -1;
          var an = Number(ax), bn = Number(by);
          if (ax !== "" && by !== "" && !isNaN(an) && !isNaN(bn)) return (an - bn) * sort.dir;
          return ax.localeCompare(by) * sort.dir;
        });
      }
      return rows;
    }

    function draw() {
      var columns = visibleColumns();
      var rows = currentRows();
      scroll.textContent = "";
      $("tableCount").textContent = rows.length === data.count
        ? data.count + " rows"
        : rows.length + " of " + data.count + " rows";

      var table = el("table", { class: "data-table" });
      var headRow = el("tr", {});
      columns.forEach(function (c) {
        var th = el("th", { class: sort.column === c.name ? "is-sorted" : "" }, [
          el("button", { type: "button", class: "th-btn", onclick: function () {
            if (sort.column === c.name) sort.dir = -sort.dir;
            else { sort.column = c.name; sort.dir = 1; }
            draw();
          } }, [
            el("span", { text: c.label || c.name }),
            c.required ? el("span", { class: "th-req", text: "*" }) : null,
            el("span", { class: "th-arrow mono",
              text: sort.column === c.name ? (sort.dir > 0 ? "\u2191" : "\u2193") : "" }),
          ]),
          el("span", { class: "th-fill mono",
            text: c.filled === data.count ? "" : c.filled + "/" + data.count }),
        ]);
        headRow.appendChild(th);
      });
      table.appendChild(el("thead", {}, [headRow]));

      var body = el("tbody", {});
      rows.forEach(function (row) {
        var tr = el("tr", {});
        columns.forEach(function (c) {
          var value = row[c.name];
          var text = value === null || value === undefined ? "" : String(value);
          var cell = el("td", { class: (c.pk ? "is-key " : "") + (text ? "" : "is-blank") });
          var linkable = c.pk || c.ref || /_id$|^id$/.test(c.name);
          if (text && linkable && state.index.some(function (i) { return i.id === text; })) {
            cell.appendChild(el("button", { type: "button", class: "cell-link",
              text: text, onclick: function () { showPanel(false); showEntity(text); } }));
          } else {
            cell.textContent = text;
            cell.title = text.length > 60 ? text : "";
          }
          tr.appendChild(cell);
        });
        body.appendChild(tr);
      });
      table.appendChild(body);
      scroll.appendChild(table);
      if (!rows.length) {
        scroll.appendChild(el("p", { class: "brief-hint", text:
          filter ? "Nothing matches that." : "This table is empty." }));
      }
    }

    filterBox.addEventListener("input", function () { filter = this.value; draw(); });
    emptyToggle.querySelector("input").addEventListener("change", function () {
      showEmpty = this.checked;
      draw();
    });
    draw();
  }

  /* ---- coverage ---------------------------------------------------------
   * Validation answers "is anything wrong". This answers "what is missing",
   * which is the question nobody asks until it is too late: a model with no
   * errors and no owners recorded will not survive its first incident.
   */

  function bar(filled, total, cls) {
    var pct = total ? Math.round((filled / total) * 100) : 0;
    var track = el("span", { class: "meter " + (cls || ""), title: filled + " of " + total });
    var fill = el("span", { class: "meter-fill" });
    fill.style.width = pct + "%";
    track.appendChild(fill);
    return track;
  }

  /* What changed since a revision, in the model's own terms: a file diff
   * says a line moved, this says a system was added or a status changed. The
   * hosted copy has whatever was baked; the local app asks git. */
  function openChanges(since, until) {
    var readOnly = !!window.__AAC_STATIC__;
    state.panel = "changes";
    showPanel(true);
    state.changes = { since: since || "", until: until || "" };
    syncUrl();
    var panel = $("dataPanel");
    panel.textContent = "";
    panel.classList.remove("is-table");
    panel.appendChild(checksHead("changes",
      "What changed in the architecture between two revisions, in the model's own terms: "
      + "entities added, removed and changed field by field, relationship rows, views and "
      + "the library. Both revisions are loaded with the engine as it is now."));
    var sinceInput = el("input", { type: "text", id: "chg_since", value: since || "HEAD~1",
      placeholder: "HEAD~1, a tag, a commit" });
    var untilInput = el("input", { type: "text", id: "chg_until", value: until || "",
      placeholder: "the working tree" });
    if (readOnly) { sinceInput.readOnly = true; untilInput.readOnly = true; }
    var form = el("div", { class: "chg-form" }, [
      el("label", { for: "chg_since", text: "since" }), sinceInput,
      el("label", { for: "chg_until", text: "until" }), untilInput,
    ]);
    if (!readOnly) {
      form.appendChild(el("button", { class: "btn small", type: "button", text: "Compare",
        onclick: function () { openChanges(sinceInput.value, untilInput.value); } }));
    }
    panel.appendChild(form);
    var host = el("div", { class: "chg-body" });
    panel.appendChild(host);
    host.appendChild(el("p", { class: "brief-hint", text: "Comparing…" }));

    var url = "/api/diff";
    if (!readOnly) {
      url += "?since=" + encodeURIComponent(sinceInput.value || "HEAD~1")
        + (untilInput.value ? "&until=" + encodeURIComponent(untilInput.value) : "");
    }
    api(url).then(function (d) {
      host.textContent = "";
      if (d.error) {
        host.appendChild(el("p", { class: "brief-hint", text: d.error }));
        return;
      }
      if (readOnly) {
        sinceInput.value = d.since || "";
        untilInput.value = d.until || "";
      }
      var t = d.totals;
      var totals = el("div", { class: "cov-totals" });
      [["added", t.added], ["removed", t.removed], ["changed", t.changed],
       ["rows added", t.relationsAdded], ["rows removed", t.relationsRemoved],
       ["views", t.views], ["library", t.library]].forEach(function (pair) {
        totals.appendChild(el("div", { class: "cov-total" }, [
          el("span", { class: "ct-n", text: String(pair[1]) }),
          el("span", { class: "ct-k", text: pair[0] }),
        ]));
      });
      host.appendChild(totals);
      if (d.empty) {
        host.appendChild(el("p", { class: "brief-hint", text:
          "Nothing. " + d.since + " and " + d.until + " hold the same architecture." }));
        return;
      }
      function entityRow(item, kind) {
        return el("button", { type: "button", class: "gap-item", onclick: function () {
          showPanel(false); showEntity(item.id);
        } }, [
          el("span", { class: "gi-name", text: (kind ? kind + ": " : "") + item.name }),
          el("span", { class: "gi-id mono", text: item.id }),
        ]);
      }
      var byType = {};
      d.added.forEach(function (x) { (byType[x.type] = byType[x.type] || []).push(entityRow(x, "added")); });
      d.removed.forEach(function (x) {
        (byType[x.type] = byType[x.type] || []).push(el("div", { class: "gap-item is-gone" }, [
          el("span", { class: "gi-name", text: "removed: " + x.name }),
          el("span", { class: "gi-id mono", text: x.id }),
        ]));
      });
      d.changed.forEach(function (x) {
        var row = entityRow(x, "");
        row.appendChild(el("span", { class: "gi-diff", text: x.changes.map(function (c) {
          return c.field + ": " + (c.before || "—") + " → " + (c.after || "—");
        }).join("; ") }));
        (byType[x.type] = byType[x.type] || []).push(row);
      });
      Object.keys(byType).sort().forEach(function (type) {
        host.appendChild(el("p", { class: "group-title", text: type.replace(/_/g, " ") + " · " + byType[type].length }));
        var list = el("div", { class: "gap-items" });
        byType[type].forEach(function (row) { list.appendChild(row); });
        host.appendChild(list);
      });
      var relNames = Object.keys(d.relationsAdded).concat(Object.keys(d.relationsRemoved));
      relNames = relNames.filter(function (n, i) { return relNames.indexOf(n) === i; }).sort();
      if (relNames.length) {
        host.appendChild(el("p", { class: "group-title", text: "Relationships" }));
        var list = el("div", { class: "lz-list" });
        relNames.forEach(function (name) {
          var plus = (d.relationsAdded[name] || []).length, minus = (d.relationsRemoved[name] || []).length;
          var row = el("div", { class: "lz-row" });
          row.appendChild(el("span", { class: "lz-kind mono", text: name }));
          row.appendChild(el("span", { class: "lz-svc", text:
            (plus ? plus + " added" : "") + (plus && minus ? ", " : "") + (minus ? minus + " removed" : "") }));
          list.appendChild(row);
        });
        host.appendChild(list);
      }
      var lib = [];
      d.viewsAdded.forEach(function (v) { lib.push("view added: " + v.title + " (" + v.id + ")"); });
      d.viewsRemoved.forEach(function (v) { lib.push("view removed: " + v.title + " (" + v.id + ")"); });
      d.viewsChanged.forEach(function (v) {
        lib.push("view " + v.id + ": " + v.changes.map(function (c) { return c.field + " " + c.before + " → " + c.after; }).join("; "));
      });
      d.shapesChanged.forEach(function (s) { lib.push("shape " + s.id + ": version " + s.before + " → " + s.after); });
      d.partsAdded.forEach(function (p) { lib.push("part added: " + p); });
      d.partsRemoved.forEach(function (p) { lib.push("part removed: " + p); });
      if (lib.length) {
        host.appendChild(el("p", { class: "group-title", text: "Views and library" }));
        lib.forEach(function (line) { host.appendChild(el("p", { class: "brief-p", text: line })); });
      }
    }).catch(function (err) {
      host.textContent = "";
      host.appendChild(el("p", { class: "brief-hint", text: String(err && err.message || err) }));
    });
  }

  /* The model against a CMDB export, read-only: the same reconciliation the
   * command runs, with each finding a click from the system it is about. */
  //: What each drift category means, for the row that names it.
  var DRIFT_NAMES = {
    ATTR_MISMATCH: "Linked, but a field disagrees",
    UNLINKED_MATCH: "Matched by name, not yet linked",
    CANDIDATE_MATCH: "Probably the same, unconfirmed",
    AMBIGUOUS: "Several systems share the name",
    LINKED_OK: "Linked and agreeing",
    MODEL_ONLY: "In the model, not in the CMDB",
    CMDB_ONLY: "In the CMDB, not in the model",
  };

  function openDrift(exportPath) {
    state.panel = "drift";
    showPanel(true);
    // The tab's own button passes its click event, not a path.
    state.driftExport = typeof exportPath === "string" ? exportPath : "";
    syncUrl();
    var panel = $("dataPanel");
    panel.textContent = "";
    panel.classList.remove("is-table");
    panel.appendChild(checksHead("drift",
      "The model against a ServiceNow CI export, read-only: nothing is written to either. "
      + "The model stays authoritative while the CMDB is unreliable; the drift is the evidence "
      + "that makes the CMDB better, one reconciled CI at a time."));
    var host = el("div", { class: "chg-body" });
    panel.appendChild(host);
    host.appendChild(el("p", { class: "brief-hint", text: "Reconciling…" }));

    api("/api/cmdb/drift" + (typeof exportPath === "string" && exportPath
      ? "?export=" + encodeURIComponent(exportPath) : "")).then(function (d) {
      host.textContent = "";
      if (d.error) { host.appendChild(el("p", { class: "brief-hint", text: d.error })); return; }
      host.appendChild(el("p", { class: "brief-hint mono", text: "CI export: " + d.export + " · " + d.ciRecords + " records" }));
      var totals = el("div", { class: "cov-totals" });
      [["systems", d.coverage.systems], ["reconciled", d.coverage.linked],
       ["coverage", d.coverage.percent === null ? "—" : d.coverage.percent + "%"],
       ["CI records", d.ciRecords]].forEach(function (pair) {
        totals.appendChild(el("div", { class: "cov-total" }, [
          el("span", { class: "ct-n", text: String(pair[1]) }),
          el("span", { class: "ct-k", text: pair[0] }),
        ]));
      });
      host.appendChild(totals);

      host.appendChild(el("p", { class: "group-title", text: "Findings" }));
      var list = el("div", { class: "lz-list drift-findings" });
      // Largest first, named in words with the code beside: the code is what
      // the report and the CSV say, the words are what it means.
      Object.keys(d.counts).sort(function (a, b) { return d.counts[b] - d.counts[a]; }).forEach(function (category) {
        var row = el("div", { class: "lz-row" + (category === "ATTR_MISMATCH" ? " is-gap" : "") });
        row.appendChild(el("span", { class: "lz-kind" }, [
          DRIFT_NAMES[category] || category.replace(/_/g, " ").toLowerCase(),
          el("span", { class: "lz-code", text: category }),
        ]));
        row.appendChild(el("span", { class: "lz-svc", text: String(d.counts[category]) }));
        row.appendChild(el("span", { class: "lz-asked", text: d.actions[category] || "" }));
        list.appendChild(row);
      });
      host.appendChild(list);

      function systemRow(row, text, what, gone) {
        var name = gone
          ? el("span", { text: text })
          : el("button", { type: "button", text: text, onclick: function () {
              showPanel(false); showEntity(row.system_id);
            } });
        return el("div", { class: "drift-row" + (gone ? " is-gone" : "") }, [
          el("span", { class: "dr-sys" }, [name, el("span", { class: "gi-id", text: gone ? (row.cmdb_sys_id || "") : row.system_id })]),
          el("span", { class: "dr-what", text: what || "" }),
        ]);
      }
      var byCategory = {};
      d.rows.forEach(function (r) { (byCategory[r.category] = byCategory[r.category] || []).push(r); });

      var mismatches = byCategory.ATTR_MISMATCH || [];
      if (mismatches.length) {
        host.appendChild(el("p", { class: "group-title", text: "Attribute mismatches · " + mismatches.length }));
        host.appendChild(el("p", { class: "brief-hint", text:
          "Model on the left of the arrow, CMDB on the right; the source of truth per field is what field_sot.yaml says." }));
        var items = el("div", { class: "drift-rows" });
        mismatches.forEach(function (r) {
          items.appendChild(systemRow(r, r.model_name || r.system_id,
            r.field + ": " + (r.model_value || "—") + " → " + (r.cmdb_value || "—")
            + " (source of truth: " + (d.fieldSot[r.field] || "model") + ")"));
        });
        host.appendChild(items);
      }
      [["UNLINKED_MATCH", "Matched by name, not yet linked"], ["CANDIDATE_MATCH", "Candidates awaiting confirmation"],
       ["AMBIGUOUS", "Ambiguous"], ["MODEL_ONLY", "In the model, not in the CMDB"]].forEach(function (pair) {
        var rows = byCategory[pair[0]] || [];
        if (!rows.length) return;
        host.appendChild(el("p", { class: "group-title", text: pair[1] + " · " + rows.length }));
        var items = el("div", { class: "drift-rows" });
        rows.forEach(function (r) {
          var note = (r.cmdb_name ? "CMDB: " + r.cmdb_name + (r.cmdb_sys_id ? " (" + r.cmdb_sys_id + ")" : "") : "")
            + (r.confidence ? " · confidence " + r.confidence : "") + (r.note ? " · " + r.note : "");
          items.appendChild(systemRow(r, r.model_name || r.system_id, note));
        });
        host.appendChild(items);
      });
      var only = byCategory.CMDB_ONLY || [];
      if (only.length) {
        host.appendChild(el("p", { class: "group-title", text: "In the CMDB, not in the model · " + only.length }));
        var cis = el("div", { class: "drift-rows" });
        only.forEach(function (r) {
          cis.appendChild(systemRow(r, r.cmdb_name || "(unnamed CI)", r.sys_class_name || "", true));
        });
        host.appendChild(cis);
      }
      host.appendChild(el("p", { class: "brief-hint", text:
        "A high CMDB-only count is expected and is not a defect in the model. The number worth "
        + "tracking is coverage; the number worth escalating is a mismatch on a field the CMDB is "
        + "supposed to own." }));
    }).catch(function (err) {
      host.textContent = "";
      host.appendChild(el("p", { class: "brief-hint", text: String(err && err.message || err) }));
    });
  }

  function openCoverage() {
    api("/api/coverage").then(function (d) {
      state.panel = "coverage";
      showPanel(true);
      syncUrl();
      var panel = $("dataPanel");
      panel.textContent = "";
      panel.classList.remove("is-table");

      panel.appendChild(checksHead("coverage",
        "What the model does not say. Validation answers whether anything is "
        + "wrong; this answers what is missing, which is a different question."));

      var totals = el("div", { class: "cov-totals" });
      [
        ["entities", d.totals.entities],
        ["relations", d.totals.relations],
        ["views", d.totals.views],
        ["on a diagram", d.totals.drawn + " of " + d.totals.entities],
        ["gaps", d.totals.gaps],
      ].forEach(function (pair) {
        totals.appendChild(el("div", { class: "cov-total" }, [
          el("span", { class: "ct-n", text: String(pair[1]) }),
          el("span", { class: "ct-k", text: pair[0] }),
        ]));
      });
      panel.appendChild(totals);

      panel.appendChild(el("p", { class: "group-title", text: "Gaps \u00b7 " + d.gaps.length }));
      if (!d.gaps.length) {
        panel.appendChild(el("p", { class: "brief-hint", text:
          "Nothing missing that this knows how to look for. Worth being suspicious of." }));
      }
      d.gaps.forEach(function (gap) {
        var open = false;
        var items = el("div", { class: "gap-items", hidden: "hidden" });
        gap.items.forEach(function (item) {
          items.appendChild(el("button", { type: "button", class: "gap-item",
            onclick: function () { showPanel(false); showEntity(item.id); } }, [
            el("span", { class: "gi-name", text: item.name }),
            el("span", { class: "gi-id mono", text: item.id }),
          ]));
        });
        var card = el("div", { class: "gap-card" }, [
          el("button", { type: "button", class: "gap-head", onclick: function () {
            open = !open;
            items.hidden = !open;
            this.classList.toggle("is-open", open);
          } }, [
            el("span", { class: "gap-count mono", text: gap.count + " / " + gap.total }),
            el("span", { class: "gap-title", text: gap.title }),
            bar(gap.count, gap.total, "is-gap"),
          ]),
          el("p", { class: "gap-why", text: gap.why }),
          items,
        ]);
        panel.appendChild(card);
      });

      panel.appendChild(el("p", { class: "group-title", text: "Fields recorded" }));
      panel.appendChild(el("p", { class: "brief-hint", text:
        "How much of each type is actually filled in. A required field at less than "
        + "100% is a validation error; an optional one at zero is a field nobody uses." }));
      var grid = el("div", { class: "cov-grid" });
      d.fields.forEach(function (block) {
        if (!block.count) return;
        var list = el("div", { class: "cov-fields" });
        block.fields.slice().sort(function (a, b) { return b.share - a.share; })
          .forEach(function (f) {
            list.appendChild(el("div", { class: "cov-field" }, [
              el("span", { class: "cf-name", text: f.name },
                []),
              bar(f.filled, block.count, f.required && f.filled < block.count ? "is-gap" : ""),
              el("span", { class: "cf-n mono", text: f.filled + "/" + block.count }),
            ]));
          });
        grid.appendChild(el("div", { class: "cov-block" }, [
          el("p", { class: "cb-head" }, [
            el("span", { class: "cb-name", text: block.plural }),
            el("span", { class: "cb-n mono", text: String(block.count) }),
          ]),
          list,
        ]));
      });
      panel.appendChild(grid);
    }).catch(fail);
  }

  function openSource() {
    if (window.__AAC_STATIC__ && state.focus) {
      // Only the authored views' source is baked. Say that rather than letting
      // the request 404 into a message about editing, which is not the reason.
      openDrawer("Diagram source", "", function (body) {
        body.appendChild(el("p", { class: "brief-hint", text:
          "The source of a focus view is generated on request, so it runs in " +
          "the local app. Every authored view's source is available here." }));
      }, null);
      return;
    }
    var q = state.focus
      ? "focus=" + encodeURIComponent(state.focus.id) + "&depth=" + state.focus.depth
      : "view=" + encodeURIComponent(state.viewId || "");
    api("/api/source?" + q).then(function (d) {
      openDrawer("Diagram source", d.title, function (body) {
        body.appendChild(el("p", { class: "explain", text:
          "Generated from the model, the same as the committed artifacts. " +
          "Paste it anywhere that renders it; do not edit it by hand." }));

        var tabs = el("div", { class: "src-tabs" });
        var pane = el("pre", { class: "src-pane mono", tabindex: "0" });
        var copy = el("button", { class: "btn small", type: "button", text: "Copy" });
        var current = d.formats[0];

        function show(format) {
          current = format;
          pane.textContent = format.text;
          Array.prototype.forEach.call(tabs.children, function (b) {
            b.classList.toggle("is-on", b.dataset.id === format.id);
          });
          copy.textContent = "Copy " + format.label;
        }

        d.formats.forEach(function (format) {
          var tab = el("button", {
            class: "src-tab", type: "button", text: format.label,
            onclick: function () { show(format); },
          });
          tab.dataset.id = format.id;
          tabs.appendChild(tab);
        });
        copy.addEventListener("click", function () {
          copyText(current.text, current.label);
        });

        body.appendChild(el("div", { class: "src-head" }, [tabs, copy]));
        body.appendChild(pane);
        show(current);
      }, null);
    }).catch(fail);
  }

  /* Map a capability to a framework: which framework, where in it (a path
   * in the framework's own terms, outermost first), and for a domain how
   * firmly it follows it. One form, two links underneath: where a
   * capability sits is `capability_references_framework`, how firmly a
   * domain follows is `capability_aligns_to_framework`. */
  function openFrameworkMapper(capabilityId, record) {
    var isDomain = record.capability_level === "L0";
    Promise.all([api("/api/list?type=frameworks"), api("/api/table?relation=capability_references_framework")]).then(function (got) {
      var frameworks = got[0].items || [];
      var placed = (got[1].rows || []);
      openDrawer("Map to a framework", record.name || capabilityId, function (body) {
        body.appendChild(el("p", { class: "explain", text:
          "Say where " + (record.name || capabilityId) + " sits in a framework, in the framework's own terms, "
          + "outermost first: \u201cSales and Service > Sales > Customer Offer\u201d in BIAN, \u201cService management "
          + "> Incident Management\u201d in ITIL. The framework's landscape is drawn from these."
          + (isDomain ? " A domain also says how firmly it follows the framework." : "") }));
        // Where it is placed now, and the framework to open on: its own
        // first placement, else the one the model places most in.
        var mine = placed.filter(function (row) { return row.capability_id === capabilityId; });
        var used = {};
        placed.forEach(function (row) { used[row.framework_id] = (used[row.framework_id] || 0) + 1; });
        var nameOf = {};
        frameworks.forEach(function (f) { nameOf[f.id] = f.name || f.id; });
        var start = mine.length ? mine[0].framework_id
          : Object.keys(used).sort(function (a, b) { return used[b] - used[a]; })[0];
        if (mine.length) {
          body.appendChild(el("div", { class: "field" }, [el("label", { text: "Placed now" }),
            el("ul", { class: "placed-now" }, mine.map(function (row) {
              return el("li", {}, [el("strong", { text: nameOf[row.framework_id] || row.framework_id }),
                el("span", { text: " · " + (row.ref || row.value || "") })]);
            }))]));
        }
        var fw = el("select", { id: "f__fw" });
        frameworks.forEach(function (f) {
          fw.appendChild(el("option", { value: f.id, text: f.name || f.id, selected: f.id === start ? "selected" : null }));
        });
        var list = el("datalist", { id: "f__terms" });
        var term = el("input", { id: "f__term", type: "text", list: "f__terms", placeholder: "Area > Domain > Term" });
        function suggest() {
          list.textContent = "";
          var seen = {};
          placed.forEach(function (row) {
            var ref = row.ref || row.value;
            if (row.framework_id !== fw.value || !ref || seen[ref]) return;
            seen[ref] = true;
            list.appendChild(el("option", { value: ref }));
          });
        }
        fw.addEventListener("change", suggest);
        suggest();
        body.appendChild(el("div", { class: "field" }, [el("label", { for: "f__fw", text: "Framework" }), fw]));
        body.appendChild(el("div", { class: "field" }, [el("label", { for: "f__term", text: "Where in it" }), term, list,
          el("p", { class: "brief-hint", text: "Pick one the model already uses, or write a new one." })]));
        var firm = null;
        if (isDomain) {
          firm = el("select", { id: "f__firm" });
          [["", "Not said"], ["Governed by", "Governed by: a formal obligation"], ["Aligned to", "Aligned to: a chosen standard"],
           ["Informed by", "Informed by: a borrowing"]].forEach(function (o) {
            firm.appendChild(el("option", { value: o[0], text: o[1] }));
          });
          body.appendChild(el("div", { class: "field" }, [el("label", { for: "f__firm", text: "How firmly the domain follows it" }), firm]));
        }
        body.appendChild(el("p", { class: "brief-hint", text:
          "Many at once: a folder holding relations/capability_references_framework.csv, with the columns "
          + "capability_id, framework_id and ref, brought in with New \u203a Import." }));
      }, function () {
        var framework = $("f__fw").value, where = $("f__term").value.trim();
        var how = $("f__firm") ? $("f__firm").value : "";
        if (!where && !how) { toast("warn", "Nothing to save", "Say where it sits in the framework" + (isDomain ? ", or how firmly it follows it." : ".")); return false; }
        var calls = [];
        if (where) calls.push(api("/api/relate", { relation: "capability_references_framework", left: capabilityId, right: framework, qualifier: where }));
        if (how) calls.push(api("/api/relate", { relation: "capability_aligns_to_framework", left: capabilityId, right: framework, qualifier: how }));
        return Promise.all(calls).then(function (res) {
          var errors = [].concat.apply([], res.map(function (x) { return x.errors || []; }));
          toast(errors.length ? "warn" : "ok", "Mapped", errors.length ? errors[0] : (res[0] && res[0].path) || "");
          refresh();
          showEntity(capabilityId);
          return true;
        });
      });
    }).catch(fail);
  }

  function openLinkEditor(entityId) {
    api("/api/relations?id=" + encodeURIComponent(entityId)).then(function (d) {
      openDrawer("Connections", entityId, function (body) {
        body.appendChild(el("p", { class: "explain", text:
          "Links are written to 10_MODEL/relations/app_edits.yaml. Relations written " +
          "by hand stay yours: the app will not edit a file it did not create." }));

        var readOnly = !!window.__AAC_STATIC__;

        if (d.existing.length) {
          body.appendChild(el("p", { class: "group-title", text: "Existing · " + d.existing.length }));
          var list = el("div", { class: "link-list" });
          d.existing.forEach(function (link) {
            var row = el("div", { class: "link-row" }, [
              el("div", { class: "link-main" }, [
                el("span", { class: "link-rel", text: link.relation.replace(/_/g, " ") }),
                el("span", { class: "link-other", text: link.otherName || link.otherId }),
                link.qualifier ? el("span", { class: "link-q", text: link.qualifier }) : null,
              ]),
            ]);
            if (link.editable && !readOnly) {
              row.appendChild(el("button", {
                class: "btn small danger", type: "button", text: "Unlink",
                onclick: function () {
                  api("/api/unrelate", {
                    relation: link.relation, left: link.left, right: link.right,
                  }).then(function () {
                    toast("ok", "Unlinked");
                    closeDrawer();
                    refresh();
                    showEntity(entityId);
                  }).catch(fail);
                },
              }));
            } else {
              row.appendChild(el("span", { class: "link-locked mono", text: "hand-authored" }));
            }
            list.appendChild(row);
          });
          body.appendChild(list);
        }

        if (readOnly) {
          // Offering a form that can only bounce off a folder of JSON files is
          // worse than saying so before anything is filled in.
          body.appendChild(el("p", { class: "brief-hint", text:
            "Linking writes to the model on disk, so it runs in the local app. " +
            "What is shown above is every connection this has." }));
          return;
        }

        body.appendChild(el("p", { class: "group-title", text: "Add a link" }));
        if (!d.options.length) {
          body.appendChild(el("p", { class: "brief-hint", text:
            "No relation in the metamodel connects a " + d.type + " to anything." }));
          return;
        }

        var relSelect = el("select", { id: "l__rel", name: "relation" });
        d.options.forEach(function (opt, i) {
          relSelect.appendChild(el("option", {
            value: String(i),
            text: opt.relation.replace(/_/g, " ") + "  \u2192  " + opt.otherLabel,
          }));
        });
        body.appendChild(el("div", { class: "field" }, [
          el("label", { for: "l__rel" }, ["relation"]), relSelect,
        ]));

        var targetWrap = el("div", { id: "l__targetWrap" });
        body.appendChild(targetWrap);

        function renderTarget() {
          var opt = d.options[Number(relSelect.value)];
          targetWrap.textContent = "";
          var filter = el("input", { id: "l__filter", type: "text",
            placeholder: "Filter " + opt.otherLabel + "s\u2026" });
          var picker = el("select", { id: "l__target", size: "8", class: "picker" });
          function fill() {
            var q = filter.value.trim().toLowerCase();
            picker.textContent = "";
            opt.candidates
              .filter(function (c) {
                return !q || (c.name + " " + c.id).toLowerCase().indexOf(q) !== -1;
              })
              .slice(0, 200)
              .forEach(function (c) {
                picker.appendChild(el("option", { value: c.id, text: c.name + "  (" + c.id + ")" }));
              });
          }
          filter.addEventListener("input", fill);
          fill();
          targetWrap.appendChild(el("div", { class: "field" }, [
            el("label", { for: "l__filter" }, [opt.otherLabel]), filter, picker,
          ]));
          if (opt.qualifier) {
            targetWrap.appendChild(el("div", { class: "field" }, [
              el("label", { for: "l__q" }, [opt.qualifier]),
              el("input", { id: "l__q", type: "text" }),
            ]));
          }
        }
        relSelect.addEventListener("change", renderTarget);
        renderTarget();
      }, window.__AAC_STATIC__ ? null : function () {
        var body = $("drawerBody");
        var opt = d.options[Number(body.querySelector("#l__rel").value)];
        var target = body.querySelector("#l__target");
        if (!target || !target.value) {
          toast("err", "Pick something to link to");
          return Promise.resolve(false);
        }
        var q = body.querySelector("#l__q");
        var payload = {
          relation: opt.relation,
          left: opt.side === "left" ? entityId : target.value,
          right: opt.side === "left" ? target.value : entityId,
          qualifier: q ? q.value.trim() : "",
        };
        return api("/api/relate", payload).then(function (res) {
          toast(res.errors.length ? "warn" : "ok", "Linked",
            res.errors.length ? res.errors[0] : res.path);
          refresh();
          showEntity(entityId);
          return true;
        });
      });
    }).catch(fail);
  }

  function deleteEntity(id, home) {
    var what = home && home.kind === "shared"
      ? "This takes its lines out of " + home.file + "; the other records there stay."
      : "This removes its file from 10_MODEL.";
    if (!window.confirm("Delete " + id + "? " + what)) return;
    api("/api/delete", { id: id }).then(function (res) {
      toast(res.errors.length ? "warn" : "ok", "Deleted " + id,
        res.errors.length ? res.errors.length + " errors now — check Validate" : null);
      clearSelection();
      refresh();
    }).catch(fail);
  }

  // ---- drawer -----------------------------------------------------------

  function openDrawer(title, hint, build, onSave) {
    $("drawerTitle").textContent = title;
    $("drawerHint").textContent = hint || "";
    var body = $("drawerBody");
    body.textContent = "";
    // One drawer opening over another starts plain: the composer's layout
    // once carried into the text editor it handed over to.
    body.classList.remove("composer-body");
    $("drawer").classList.remove("composer");
    document.querySelector(".shell").classList.remove("composing");
    build(body);
    state.drawer = onSave;
    state.drawerOpener = document.activeElement;
    $("drawerSave").hidden = !onSave;
    // A drawer that writes has a Cancel; one that only shows has a Close.
    $("drawerCancel").textContent = onSave ? "Cancel" : "Close";
    $("drawer").hidden = false;
    $("scrim").hidden = false;
    var first = body.querySelector("input, select, textarea, button");
    (first || $("drawerClose")).focus();
  }

  function closeDrawer() {
    // A panel that drew a preview behind itself puts the saved drawing back
    // when it is closed without saving.
    var after = state.onDrawerClose;
    state.onDrawerClose = null;
    if (after) after();
    $("drawerBody").classList.remove("composer-body");
    $("drawer").classList.remove("composer");
    document.querySelector(".shell").classList.remove("composing");
    $("drawer").classList.remove("wide");
    $("drawer").hidden = true;
    $("scrim").hidden = true;
    state.drawer = null;
    // Focus goes back to whatever opened the drawer, so a keyboard does not
    // land at the top of the page after every dialog.
    var back = state.drawerOpener;
    state.drawerOpener = null;
    if (back && typeof back.focus === "function" && document.contains(back)) back.focus();
  }

  function fieldRow(field, value) {
    var id = "f_" + field.name;
    var label = el("label", { for: id }, [field.name.replace(/_/g, " ")]);
    if (field.required) label.appendChild(el("span", { class: "req", text: "*" }));
    if (field.ref) label.appendChild(el("span", { class: "hint", text: "→ " + field.ref }));

    var input;
    if (field.ref && state.index.length) {
      // A reference field is a pointer, so offer the things it can point at.
      // Typing an id by hand is how dangling references get created.
      input = el("select", { id: id, name: field.name });
      input.appendChild(el("option", { value: "", text: "\u2014" }));
      state.index
        .filter(function (item) { return item.type === field.ref; })
        .forEach(function (item) {
          input.appendChild(el("option", {
            value: item.id, text: (item.name || item.id) + "  (" + item.id + ")",
          }));
        });
      if (value != null && String(value) &&
          !state.index.some(function (i) { return i.id === String(value); })) {
        // Keep an unresolvable value visible rather than silently dropping it.
        input.appendChild(el("option", { value: String(value), text: String(value) + "  (unknown)" }));
      }
      input.value = value == null ? "" : String(value);
    } else if (field.enum) {
      input = el("select", { id: id, name: field.name });
      input.appendChild(el("option", { value: "", text: "—" }));
      field.enum.forEach(function (opt) { input.appendChild(el("option", { value: opt, text: opt })); });
      input.value = value == null ? "" : String(value);
    } else if (field.name === "description") {
      input = el("textarea", { id: id, name: field.name });
      input.value = value == null ? "" : String(value);
    } else {
      input = el("input", { id: id, name: field.name, type: "text" });
      input.value = value == null ? "" : (Array.isArray(value) ? value.join(", ") : String(value));
    }
    return el("div", { class: "field" + (field.ref ? " mono-in" : "") }, [label, input]);
  }

  function collect(container) {
    var out = {};
    Array.prototype.forEach.call(container.querySelectorAll("[name]"), function (input) {
      var v = input.value.trim();
      if (v) out[input.name] = v;
    });
    return out;
  }

  /* `into`, when given, is an archetype instance the new thing can be added
   * to under its `extra`, so it is part of the product and survives a
   * re-expansion. The form offers it; the person decides. */
  function openEntityEditor(type, existingId, record, onSaved, into, home) {
    var spec = state.schema.entities[type];
    var isNew = !existingId;
    openDrawer(
      isNew ? "New " + spec.label : "Edit " + spec.label,
      isNew ? "10_MODEL/" + spec.folder + "/" : (home && home.file) || "",
      function (body) {
        body.appendChild(el("p", { class: "explain", text:
          "Saved straight to a YAML file. The form gates nothing — `terrane validate` does, " +
          "and it runs on every save." }));
        if (home && home.kind === "harvested") {
          body.appendChild(el("p", { class: "banner", text: home.note }));
        } else if (home && home.kind === "shared") {
          body.appendChild(el("p", { class: "brief-hint", text:
            "This shares " + home.file + " with other records. Saving changes its own lines "
            + "there and leaves the rest of the file as it is." }));
        }
        if (isNew && into) {
          var intoBox = el("input", { id: "f__into", type: "checkbox" });
          intoBox.checked = true;
          body.appendChild(el("div", { class: "field into" }, [
            el("label", { class: "part-head", for: "f__into" }, [
              intoBox,
              el("span", { text: "Add to " + (into.name || into.id) + " as part of the product" }),
            ]),
            el("p", { class: "brief-hint", text:
              "Written under `extra` in " + into.id + "'s file rather than as a file of its own, "
              + "so it is included in the product and survives a re-expansion." }),
          ]));
        }

        body.appendChild(el("div", { class: "field mono-in" }, [
          el("label", { for: "f__id" }, [spec.pk, el("span", { class: "req", text: "*" })]),
          el("input", { id: "f__id", type: "text", value: existingId || "",
            placeholder: "SYS-EXAMPLE", readonly: existingId ? "readonly" : null }),
        ]));

        var required = spec.fields.filter(function (f) { return f.required; });
        var optional = spec.fields.filter(function (f) {
          return !f.required && f.name !== "archetype" && f.name !== "archetype_instance";
        });

        body.appendChild(el("p", { class: "group-title", text: "Required" }));
        required.forEach(function (f) { body.appendChild(fieldRow(f, record && record[f.name])); });

        var more = el("details", { class: "fields" }, [
          el("summary", { text: "Everything else (" + optional.length + ")" }),
        ]);
        optional.forEach(function (f) { more.appendChild(fieldRow(f, record && record[f.name])); });
        body.appendChild(el("p", { class: "group-title", text: "Optional" }));
        body.appendChild(more);

        if (!isNew && !window.__AAC_STATIC__) {
          body.appendChild(el("p", { class: "group-title", text: "Or edit the file" }));
          body.appendChild(el("button", {
            class: "btn small", type: "button", text: "Edit YAML",
            title: "The file behind this entity, comments and all",
            onclick: function () { openEntitySource(existingId); },
          }));
        }
      },
      function () {
        var body = $("drawerBody");
        var id = body.querySelector("#f__id").value.trim();
        if (!id) { toast("err", "An identifier is required"); return Promise.resolve(false); }
        var intoBox = body.querySelector("#f__into");
        var payload = { type: type, id: id, values: collect(body) };
        if (intoBox && intoBox.checked && into) payload.instance = into.id;
        return api("/api/save", payload).then(function (res) {
          toast(res.errors.length ? "warn" : "ok", "Saved " + id,
            res.errors.length ? res.errors[0]
              : res.moved ? res.moved
              : (res.instance ? "Part of " + res.instance : res.path));
          if (onSaved) onSaved(id);
          refresh();
          showEntity(id);
          return true;
        });
      }
    );
  }

  /* ---- composing a shape ------------------------------------------------
   * The same switches as the New form, one level up. A shape is modules on
   * blocks with a vocabulary; pick them and the archetype file is written,
   * then previewed and saved in the editor like a typed one.
   */
  function openArchetypeComposer() {
    if (readOnlyCopy("Composing a shape")) return;
    api("/api/compose/options").then(function (opt) {
      openDrawer("Compose a shape from parts", "20_ARCHETYPES/", function (body) {
        $("drawer").classList.add("wide");
        body.appendChild(el("p", { class: "explain", text:
          "A shape is parts on blocks, plus the questions an instance is asked. Pick them; "
          + "the archetype is written in the library's vocabulary and opens in the editor "
          + "for a preview before anything is saved." }));

        function field(id, label, input, hint) {
          var lab = el("label", { for: id }, [label]);
          if (hint) lab.appendChild(el("span", { class: "hint", text: hint }));
          body.appendChild(el("div", { class: "field" }, [lab, input]));
          return input;
        }
        field("cp_id", "archetype id", el("input", { id: "cp_id", type: "text", placeholder: "e.g. partner-api-onboarding" }));
        field("cp_title", "title", el("input", { id: "cp_title", type: "text", placeholder: "e.g. Partner API onboarding" }));
        field("cp_desc", "description", el("textarea", { id: "cp_desc", rows: "3" }),
          "what this shape creates and why the parts are the ones they are; the New form shows it");
        var prov = el("select", { id: "cp_provider" });
        prov.appendChild(el("option", { value: "", text: "none: no blocks, no cloud fields" }));
        (opt.providers || []).forEach(function (p) { prov.appendChild(el("option", { value: p, text: p })); });
        field("cp_provider", "provider", prov, "the cloud every block resolves against");

        // The vocabulary: what the instance will be asked for.
        body.appendChild(el("p", { class: "group-title", text: "What the instance is asked · vocabulary" }));
        body.appendChild(el("p", { class: "brief-hint", text:
          "Every module template can rely on these names. Untick what this shape does not need; "
          + "a part that still needs one is added back as a required parameter." }));
        var vocab = el("div", { class: "pick-list two-col" });
        var preset = { slug: 1, product_name: 1, owner_org: 1, domain: 1, account: 1, region: 1, criticality: 1, classification: 1 };
        (opt.vocabulary || []).forEach(function (p) {
          var box = el("input", { type: "checkbox", "data-vocab": p.name });
          box.checked = !!preset[p.name];
          vocab.appendChild(el("label", { class: "pick-row" }, [
            box,
            el("span", { class: "mono", text: p.name }),
            el("span", { class: "via", text: p.default != null ? "default " + p.default : (p.required ? "required" : "") }),
          ]));
        });
        body.appendChild(vocab);

        // The parts.
        body.appendChild(el("p", { class: "group-title", text: "Parts · " + (opt.modules || []).length }));
        var partList = el("div", { class: "part-list" });
        (opt.modules || []).forEach(function (m) {
          var box = el("input", { type: "checkbox", id: "cpm_" + m.id, "data-module": m.id });
          var part = el("div", { class: "part is-off" }, [
            el("label", { class: "part-head", for: "cpm_" + m.id }, [
              box,
              el("span", { class: "part-name", text: m.name }),
              el("span", { class: "part-cat mono", text: m.category || "" }),
              el("span", { class: "part-n mono", text:
                ((m.requires || []).length ? "needs " + m.requires.join(", ") : "")
                + ((m.runsOn || []).length ? ((m.requires || []).length ? "; " : "") + "on " + m.runsOn.join(", ") : "") }),
            ]),
            el("p", { class: "part-desc", text: m.description || "" }),
          ]);
          (m.parameters || []).forEach(function (p) {
            var lab = el("label", { for: "cpw_" + m.id + "_" + p.name }, [p.name.replace(/_/g, " ")]);
            if (p.description) lab.appendChild(el("span", { class: "hint", text: p.description }));
            part.appendChild(el("div", { class: "field part-field" }, [
              lab,
              el("input", { id: "cpw_" + m.id + "_" + p.name, type: "text", "data-with": p.name,
                "data-with-module": m.id,
                placeholder: p.default != null ? String(p.default) : "bound by the shape, e.g. {caller_system}" }),
            ]));
          });
          box.addEventListener("change", function () {
            part.classList.toggle("is-off", !box.checked);
            // What a part needs comes with it: the parts it requires, and
            // the blocks its templates run on.
            if (box.checked) {
              (m.requires || []).forEach(function (r) {
                var other = body.querySelector("#cpm_" + r);
                if (other && !other.checked) { other.checked = true; other.dispatchEvent(new Event("change")); }
              });
              (m.runsOn || []).forEach(function (b) {
                var blockBox = body.querySelector("#cpb_" + b);
                if (blockBox && !blockBox.checked) { blockBox.checked = true; blockBox.dispatchEvent(new Event("change")); }
              });
            }
          });
          partList.appendChild(part);
        });
        body.appendChild(partList);

        // The blocks, with what the landing zone already provides.
        body.appendChild(el("p", { class: "group-title", text: "Blocks · " + (opt.blocks || []).length }));
        body.appendChild(el("p", { class: "brief-hint", text:
          "Bind a component to the shared service that already provides it; leave it unbound "
          + "and every product gets one of its own, resolved to the provider's product." }));
        var blockList = el("div", { class: "part-list" });
        (opt.blocks || []).forEach(function (b) {
          var box = el("input", { type: "checkbox", id: "cpb_" + b.id, "data-block": b.id });
          var part = el("div", { class: "part is-off" }, [
            el("label", { class: "part-head", for: "cpb_" + b.id }, [
              box,
              el("span", { class: "part-name", text: b.name }),
              el("span", { class: "part-cat mono", text: b.category || "" }),
            ]),
            el("p", { class: "part-desc", text: b.description || "" }),
          ]);
          // Multi-cloud: a block may resolve against another provider than
          // the shape's. Identity on Azure under an AWS workload is the
          // common case, and it is one product, not two.
          var psel = el("select", { id: "cpprov_" + b.id, "data-block-provider": b.id });
          psel.appendChild(el("option", { value: "", text: "the shape's provider" }));
          (opt.providers || []).forEach(function (p) { psel.appendChild(el("option", { value: p, text: p })); });
          part.appendChild(el("div", { class: "field part-field" }, [
            el("label", { for: psel.id }, ["resolves against"]),
            psel,
          ]));
          (b.components || []).forEach(function (c) {
            var sel = el("select", { id: "cpbind_" + b.id + "_" + c.id, "data-bind": c.id, "data-bind-block": b.id });
            sel.appendChild(el("option", { value: "", text: "created per product" }));
            (opt.shared || []).filter(function (s) { return !s.component || s.component === c.id; })
              .forEach(function (s) {
                sel.appendChild(el("option", { value: s.id, text: s.name + "  (" + s.id + ")" }));
              });
            part.appendChild(el("div", { class: "field part-field" }, [
              el("label", { for: sel.id }, [c.name]),
              sel,
            ]));
          });
          box.addEventListener("change", function () { part.classList.toggle("is-off", !box.checked); });
          blockList.appendChild(part);
        });
        body.appendChild(blockList);

        body.appendChild(el("p", { class: "group-title", text: "Patterns every instance applies" }));
        var patList = el("div", { class: "pick-list two-col" });
        (opt.patterns || []).forEach(function (p) {
          patList.appendChild(el("label", { class: "pick-row" }, [
            el("input", { type: "checkbox", "data-pattern": p.id }),
            el("span", { text: p.name }),
            el("span", { class: "via mono", text: p.status }),
          ]));
        });
        body.appendChild(patList);
      }, function () {
        var body = $("drawerBody");
        var spec = {
          id: body.querySelector("#cp_id").value.trim(),
          title: body.querySelector("#cp_title").value.trim(),
          description: body.querySelector("#cp_desc").value.trim(),
          provider: body.querySelector("#cp_provider").value,
          parameters: [], modules: [], blocks: [], patterns: [],
        };
        if (!spec.id || !spec.title) { toast("err", "A shape needs an id and a title"); return Promise.resolve(false); }
        Array.prototype.forEach.call(body.querySelectorAll("[data-vocab]"), function (b) {
          if (b.checked) spec.parameters.push(b.getAttribute("data-vocab"));
        });
        Array.prototype.forEach.call(body.querySelectorAll("[data-module]"), function (b) {
          if (!b.checked) return;
          var id = b.getAttribute("data-module");
          var withs = {};
          Array.prototype.forEach.call(body.querySelectorAll("[data-with-module=\"" + id + "\"]"), function (i) {
            if (i.value.trim()) withs[i.getAttribute("data-with")] = i.value.trim();
          });
          spec.modules.push({ module: id, with: withs });
        });
        Array.prototype.forEach.call(body.querySelectorAll("[data-block]"), function (b) {
          if (!b.checked) return;
          var id = b.getAttribute("data-block");
          var bind = {};
          Array.prototype.forEach.call(body.querySelectorAll("[data-bind-block=\"" + id + "\"]"), function (s) {
            if (s.value) bind[s.getAttribute("data-bind")] = s.value;
          });
          var psel = body.querySelector("[data-block-provider=\"" + id + "\"]");
          spec.blocks.push({ block: id, bind: bind, provider: psel ? psel.value : "" });
        });
        Array.prototype.forEach.call(body.querySelectorAll("[data-pattern]"), function (b) {
          if (b.checked) spec.patterns.push(b.getAttribute("data-pattern"));
        });
        return api("/api/archetype/compose", spec).then(function (res) {
          closeDrawer();
          openArchetypeEditor(null, res.text);
          return false;
        });
      });
    }).catch(fail);
  }

  /* ---- assemble: a project from chunks ------------------------------------
   * The parts of the library are diagram chunks: a handful of entities with
   * the lines between them, parameterized. A shape is a fixed choice of
   * chunks; a project is a choice made once, for one product, with the small
   * edits a product always needs. The panel is the choosing: pick chunks on
   * the left, watch the product's own architecture drawing on the right,
   * rename and drop and override in the middle, and write one file. The
   * preview is the real expansion over a scratch copy of the model, so what
   * is drawn before the file exists is what the file will draw.
   */
  var asm = null;

  //: The chunk thumbnail: a 160x96 drawing of the entities a chunk makes.
  var THUMB_W = 160;
  var THUMB_H = 96;

  function slugOf(name) {
    var words = String(name || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim().split(/\s+/);
    return words[0] || "";
  }

  function idOf(name) {
    var words = String(name || "").toUpperCase().replace(/[^A-Z0-9]+/g, " ").trim().split(/\s+/).filter(Boolean);
    return words.length ? "PRD-" + words.slice(0, 3).join("-") : "";
  }

  function chunkThumb(chunk, swatches) {
    var shape = chunk.shape || { nodes: [], edges: [] };
    var inside = shape.nodes.filter(function (n) { return n.type !== "outside"; });
    var outside = shape.nodes.filter(function (n) { return n.type === "outside"; });
    var nodes = inside.concat(outside).slice(0, 6);
    var n = nodes.length;
    var cols = n <= 3 ? Math.max(n, 1) : Math.ceil(n / 2);
    var rows = n <= 3 ? 1 : 2;
    var bw = Math.min(50, (THUMB_W - 8) / cols - 8), bh = 20;
    var at = {};
    nodes.forEach(function (node, i) {
      var r = Math.floor(i / cols), c = i % cols;
      var inRow = Math.min(cols, n - r * cols);
      var left = (THUMB_W - inRow * (bw + 8) + 8) / 2;
      var top = rows === 1 ? (THUMB_H - bh) / 2 : 14 + r * (bh + 26);
      at[node.id] = { x: left + c * (bw + 8), y: top, cx: left + c * (bw + 8) + bw / 2, cy: top + bh / 2 };
    });
    var parts = ['<svg viewBox="0 0 ' + THUMB_W + ' ' + THUMB_H + '" width="' + THUMB_W + '" height="' + THUMB_H
      + '" role="img" aria-label="' + esc(chunk.name) + '">'];
    parts.push('<defs><marker id="th-arrow" viewBox="0 0 6 6" refX="5" refY="3" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0L6 3L0 6z" fill="#7b8798"/></marker></defs>');
    (shape.edges || []).forEach(function (e) {
      var a = at[e.from], b = at[e.to];
      if (!a || !b || e.from === e.to) return;
      parts.push('<line x1="' + a.cx + '" y1="' + a.cy + '" x2="' + b.cx + '" y2="' + b.cy
        + '" stroke="#7b8798" stroke-width="1" ' + (e.soft ? 'stroke-dasharray="3 2" ' : "") + 'marker-end="url(#th-arrow)"/>');
    });
    nodes.forEach(function (node) {
      var p = at[node.id];
      var sw = swatches[node.type] || { fill: "#ffffff", stroke: "#8f9bb5" };
      var outsideNode = node.type === "outside";
      parts.push('<rect x="' + p.x + '" y="' + p.y + '" width="' + bw + '" height="' + bh + '" rx="3" fill="'
        + (outsideNode ? "#ffffff" : sw.fill) + '" stroke="' + (outsideNode ? "#b4bdcc" : sw.stroke)
        + '" stroke-width="1" ' + (outsideNode ? 'stroke-dasharray="3 2"' : "") + '/>');
      var label = node.name.length > 11 ? node.name.slice(0, 10) + "…" : node.name;
      parts.push('<text x="' + p.cx + '" y="' + (p.cy + 2.5) + '" text-anchor="middle" font-size="7" font-family="Geist, system-ui, sans-serif" fill="'
        + (outsideNode ? "#64748b" : "#0f172a") + '">' + esc(label) + (node.each ? " ×n" : "") + '</text>');
    });
    if (!n) {
      parts.push('<text x="' + (THUMB_W / 2) + '" y="' + (THUMB_H / 2 + 3) + '" text-anchor="middle" font-size="8" fill="#64748b">a kit of parts</text>');
    }
    parts.push("</svg>");
    var box = el("span", { class: "chunk-thumb" });
    box.innerHTML = parts.join("");
    return box;
  }

  function esc(text) {
    return String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function openAssemble(preset) {
    api("/api/chunks").then(function (data) {
      var readOnly = !!window.__AAC_STATIC__;
      state.panel = "assemble";
      showPanel(true);
      var panel = $("dataPanel");
      panel.textContent = "";
      panel.classList.remove("is-table");
      var providers = data.shapes.map(function (s) { return s.provider; }).filter(function (p, i, a) { return p && a.indexOf(p) === i; });
      asm = {
        data: data, id: "", name: "", slug: "", provider: providers[0] || "",
        values: { status: "Planned", owner_org_id: "", criticality: "Medium", company_domain: "", product_category: "Digital channel", description: "" },
        params: { account: "", region: "", classification: "Confidential" },
        picked: {}, order: [], overrides: {}, exclude: {}, startShape: "", buildType: "",
        saveShape: false, shapeId: "", shapeTitle: "",
        preview: null, cy: null, timer: null, inflight: 0, touched: {},
        replace: "", path: "", note: [], kept: {}, more: {}, extra: null, unknown: [],
        shape: "", choose: {}, shapeWith: {}, slotOf: {}, withoutExtra: [], answers: {}, detach: false, stash: {}, ids: {},
      };
      // The one button that writes sits in the head with the steps, so
      // what is left to do and what happens next are read in one line.
      var createBtn = null;
      if (!readOnly) {
        createBtn = el("button", { class: "btn primary", id: "asm_create", type: "button", text: "Create project" });
        createBtn.addEventListener("click", createAssembled);
      }
      panel.appendChild(el("div", { class: "page-head asm-head" }, [
        el("div", { class: "page-head-row" }, [
          el("div", { class: "page-head-text" }, [
            el("h1", { id: "asm_h1", text: "Assemble a project" }),
            el("p", { class: "sub", id: "asm_sub", text:
              "Choose what kind of thing you are building, pick its parts, check the diagram they make, "
              + "make the small edits, and save it as one file. The landing zone decides what the parts run on." }),
          ]),
          el("div", { class: "page-acts" }, [createBtn]),
        ]),
        el("div", { class: "asm-steps", id: "asm_steps", "aria-label": "Where the project is" }),
      ]));
      var grid = el("div", { class: "asm" });
      var colProject = el("section", { class: "asm-col asm-project", "aria-label": "The project" });
      var colChunks = el("section", { class: "asm-col asm-chunks", "aria-label": "Chunks" });
      var colPreview = el("section", { class: "asm-col asm-preview", "aria-label": "Preview and edits" });
      grid.appendChild(colProject);
      grid.appendChild(colChunks);
      grid.appendChild(colPreview);
      panel.appendChild(grid);
      buildAssembleProject(colProject);
      buildAssembleChunks(colChunks);
      buildAssemblePreview(colPreview, readOnly);
      if (preset && preset.open) { loadAssembled(preset.open); return; }
      if (preset && preset.shape) applyStartShape(preset.shape);
      else if (preset && preset.chunks) preset.chunks.forEach(function (id) { pickChunk(id, true); });
      renderChunkCards();
      scheduleAssemblePreview();
      renderAsmSteps();
      syncUrl();
    }).catch(fail);
  }

  /* The four steps of assembling, as a strip: what the project is, which
   * parts, its details, and the save. Each is done, current or to come,
   * read off the state rather than off which pane the person last used,
   * since all three panes are on screen at once. */
  function renderAsmSteps() {
    var host = $("asm_steps");
    if (!host || !asm) return;
    var missing = assembleReady();
    var done = [
      !!(asm.buildType || asm.startShape || asm.shape || asm.order.length),
      asm.order.length > 0 || !!asm.shape,
      !!(asm.name && asm.id && asm.slug && asm.values.owner_org_id),
      !missing.length && !!asm.preview && !(asm.preview.conflicts || []).length,
    ];
    var current = done.indexOf(false);
    if (current === -1) current = 3;
    host.textContent = "";
    ["What it is", "Its parts", "Its details", "Review and save"].forEach(function (label, i) {
      if (i) host.appendChild(el("span", { class: "asm-step-line" }));
      var mode = i < current || (done[i] && i === 3) ? "done" : (i === current ? "on" : "todo");
      host.appendChild(el("span", { class: "asm-step is-" + mode }, [
        el("span", { class: "asm-step-n", text: mode === "done" ? "\u2713" : String(i + 1) }),
        el("span", { class: "asm-step-label", text: label }),
      ]));
    });
  }

  /* The kinds of thing the organization builds, as rows with a radio each:
   * one tick picks the standard parts. The first row is no kind at all. */
  function renderKindRows(host) {
    if (!host || !asm) return;
    host.textContent = "";
    function row(id, name, note) {
      var on = (asm.buildType || "") === id;
      return el("button", { class: "kind-row" + (on ? " is-on" : ""), type: "button", role: "radio",
        "aria-checked": on ? "true" : "false",
        onclick: function () { applyBuildType(id); } }, [
        el("span", { class: "kind-dot" }),
        el("span", { class: "kind-text" }, [
          el("span", { class: "kind-name", text: name }),
          note ? el("span", { class: "kind-note", text: note }) : null,
        ]),
      ]);
    }
    host.appendChild(row("", "Something else", "Pick the parts yourself."));
    var types = asm.data.types || [];
    // Four kinds in view, the rest behind one line; a chosen kind is
    // always in view, wherever it sits in the list.
    var shown = 4;
    var chosenAt = types.map(function (t) { return t.id; }).indexOf(asm.buildType);
    var open = !!asm.kindsOpen || chosenAt >= shown;
    types.forEach(function (t, i) {
      if (!open && i >= shown) return;
      host.appendChild(row(t.id, t.name, (t.description || "")
        + (t.products ? " " + t.products + (t.products === 1 ? " product is one." : " products are.") : "")));
    });
    if (!open && types.length > shown) {
      host.appendChild(el("button", { class: "hp-more kind-more", type: "button",
        text: "and " + (types.length - shown) + " more " + plural(types.length - shown, "kind"),
        onclick: function () { asm.kindsOpen = true; renderKindRows(host); } }));
    }
  }

  function assembleField(col, id, label, input, hint) {
    var lab = el("label", { for: id }, [label]);
    if (hint) lab.appendChild(el("span", { class: "hint", text: hint }));
    col.appendChild(el("div", { class: "field" }, [lab, input]));
    return input;
  }

  function buildAssembleProject(col) {
    var data = asm.data;
    if ((data.assembled || []).length) {
      col.appendChild(el("p", { class: "group-title", text: "Open" }));
      col.appendChild(el("p", { class: "brief-hint", text:
        "A product this panel made before, or one on a shape: its parts selected and its edits in place. Save rewrites its file." }));
      var openSel = el("select", { id: "asm_open", "aria-label": "Open an assembled project" });
      openSel.appendChild(el("option", { value: "", text: "\u2014 choose a product to open" }));
      data.assembled.forEach(function (p) {
        openSel.appendChild(el("option", { value: p.id, text: p.name + " \u00b7 " + p.chunks + " parts \u00b7 " + (p.provider || "no cloud")
          + (p.shape ? " \u00b7 on shape " + p.shape : "") }));
      });
      openSel.value = asm.replace || "";
      openSel.addEventListener("change", function () { if (openSel.value) loadAssembled(openSel.value); });
      col.appendChild(el("div", { class: "field" }, [openSel]));
    }
    // The first question: what kind of thing is this? A type fixes the
    // parts every build of its kind has, ticks the ones it usually has, and
    // offers the rest; the landing zone answers for what they run on.
    if ((data.types || []).length) {
      col.appendChild(el("p", { class: "group-title", text: "What are you building?" }));
      col.appendChild(el("p", { class: "brief-hint", text:
        "Choose the kind of thing. Its standard parts are selected for you, and anything you change is listed as a deviation." }));
      var kinds = el("div", { class: "kind-list", id: "asm_type", role: "radiogroup", "aria-label": "What kind of thing this is" });
      renderKindRows(kinds);
      col.appendChild(kinds);
      col.appendChild(el("p", { id: "asm_type_desc", class: "brief-hint", hidden: "" }));
    }
    col.appendChild(el("p", { class: "group-title", text: "Start from a shape" }));
    col.appendChild(el("p", { class: "brief-hint", text:
      "A shape is a saved choice of parts for one provider. Start from one and change it, or pick the parts yourself." }));
    var startHost = el("div", { id: "asm_start" });
    col.appendChild(startHost);
    renderStartShapes();
    col.appendChild(el("p", { class: "group-title", text: "The project" }));
    var name = assembleField(col, "asm_name", "name", el("input", { id: "asm_name", type: "text", placeholder: "e.g. Merchant Portal" }));
    var idIn = assembleField(col, "asm_id", "product id", el("input", { id: "asm_id", type: "text", class: "mono-in", placeholder: "PRD-MERCHANT-PORTAL" }),
      "follows the name until you change it");
    var slugIn = assembleField(col, "asm_slug", "slug", el("input", { id: "asm_slug", type: "text", placeholder: "merchant" }),
      "the short token in every identifier the chunks make");
    name.addEventListener("input", function () {
      asm.name = name.value.trim();
      if (!asm.touched.id) { asm.id = idOf(asm.name); idIn.value = asm.id; }
      if (!asm.touched.slug) { asm.slug = slugOf(asm.name); slugIn.value = asm.slug; }
      scheduleAssemblePreview();
    });
    idIn.addEventListener("input", function () { asm.touched.id = true; asm.id = idIn.value.trim(); setAssembleMode(); scheduleAssemblePreview(); });
    slugIn.addEventListener("input", function () { asm.touched.slug = true; asm.slug = slugIn.value.trim(); scheduleAssemblePreview(); });

    var prov = el("select", { id: "asm_provider" });
    prov.appendChild(el("option", { value: "", text: "none: no blocks, no cloud fields" }));
    (data.providers || []).forEach(function (p) { prov.appendChild(el("option", { value: p, text: p })); });
    prov.value = asm.provider;
    assembleField(col, "asm_provider", "landing zone", prov, "the cloud the parts run on");
    // The zone as segments: one tap each, the select behind them for the
    // code that sets it.
    prov.hidden = true;
    var zones = el("div", { class: "zone-segs", role: "radiogroup", "aria-label": "Landing zone" });
    function renderZones() {
      zones.textContent = "";
      [["", "None"]].concat((data.providers || []).map(function (p) { return [p, p]; })).forEach(function (pair) {
        var on = (asm.provider || "") === pair[0];
        zones.appendChild(el("button", { class: "zone-seg" + (on ? " is-on" : ""), type: "button", role: "radio",
          "aria-checked": on ? "true" : "false", text: pair[1],
          onclick: function () { prov.value = pair[0]; prov.dispatchEvent(new Event("change")); } }));
      });
    }
    prov.parentNode.appendChild(zones);
    renderZones();
    var acct = el("input", { id: "asm_account", type: "text", list: "asm_accounts", placeholder: "e.g. azure-payments-prod" });
    var acctList = el("datalist", { id: "asm_accounts" });
    var region = el("input", { id: "asm_region", type: "text", list: "asm_regions", placeholder: "the zone's default" });
    var regionList = el("datalist", { id: "asm_regions" });
    // What the landing zone answers for on this cloud: the service of each
    // kind a part can run on, so nobody has to choose the load balancer.
    var zoneBox = el("details", { class: "asm-zone", id: "asm_zone" }, [
      el("summary", { text: "Standard services" }),
      el("ul", { id: "asm_zone_list", class: "asm-zone-list" }),
    ]);
    function fillZone() {
      var zone = (data.landingZones || {})[asm.provider] || { accounts: [], regions: [] };
      acctList.textContent = ""; regionList.textContent = "";
      zone.accounts.forEach(function (a) { acctList.appendChild(el("option", { value: a })); });
      zone.regions.forEach(function (r) { regionList.appendChild(el("option", { value: r })); });
      region.placeholder = zone.regions[0] ? "e.g. " + zone.regions[0] : "the zone's default";
      var landing = (data.landing || {})[asm.provider] || {};
      var kinds = Object.keys(landing).sort();
      var list = zoneBox.querySelector("ul");
      list.textContent = "";
      kinds.forEach(function (kind) {
        list.appendChild(el("li", {}, [
          el("span", { class: "zk", text: kind.replace(/-/g, " ") }),
          el("span", { class: "zv", text: landing[kind].name }),
        ]));
      });
      zoneBox.querySelector("summary").textContent = asm.provider
        ? "Standard services on " + asm.provider + " · " + kinds.length : "Standard services";
      zoneBox.hidden = !kinds.length;
    }
    fillZone();
    col.appendChild(zoneBox);
    prov.addEventListener("change", function () {
      asm.provider = prov.value;
      renderZones();
      fillZone();
      // A type is the shape of that cloud where there is one; the parts
      // follow the cloud.
      if (asm.buildType) { applyBuildType(asm.buildType, true); return; }
      renderChunkCards();
      scheduleAssemblePreview();
    });
    assembleField(col, "asm_account", "account", acct, "the workload account or subscription");
    col.appendChild(acctList);
    assembleField(col, "asm_region", "region", region);
    col.appendChild(regionList);
    acct.addEventListener("input", function () { asm.params.account = acct.value.trim(); scheduleAssemblePreview(); });
    region.addEventListener("input", function () { asm.params.region = region.value.trim(); scheduleAssemblePreview(); });

    var owner = el("select", { id: "asm_owner" });
    owner.appendChild(el("option", { value: "", text: "— choose an owner" }));
    (data.orgs || []).forEach(function (o) { owner.appendChild(el("option", { value: o.id, text: o.name + "  (" + o.id + ")" })); });
    assembleField(col, "asm_owner", "owner", owner);
    owner.addEventListener("change", function () { asm.values.owner_org_id = owner.value; scheduleAssemblePreview(); });
    var domain = el("input", { id: "asm_domain", type: "text", list: "asm_domains", placeholder: "e.g. Payments" });
    var domainList = el("datalist", { id: "asm_domains" });
    (data.domains || []).forEach(function (d) { domainList.appendChild(el("option", { value: d })); });
    assembleField(col, "asm_domain", "domain", domain, "the business domain the views group by");
    col.appendChild(domainList);
    domain.addEventListener("input", function () { asm.values.company_domain = domain.value.trim(); scheduleAssemblePreview(); });

    function pick(id, label, options, current, onchange) {
      var sel = el("select", { id: id });
      options.forEach(function (o) { sel.appendChild(el("option", { value: o, text: o })); });
      sel.value = current;
      sel.addEventListener("change", function () { onchange(sel.value); scheduleAssemblePreview(); });
      assembleField(col, id, label, sel);
    }
    pick("asm_crit", "criticality", ["High", "Medium", "Low"], asm.values.criticality, function (v) { asm.values.criticality = v; });
    pick("asm_class", "classification", ["Restricted", "Confidential", "Internal", "Public"], asm.params.classification, function (v) { asm.params.classification = v; });
    pick("asm_state", "status", ["Planned", "Proposed", "Active"], asm.values.status, function (v) { asm.values.status = v; });
    var cat = el("input", { id: "asm_cat", type: "text", list: "asm_cats", value: asm.values.product_category });
    var catList = el("datalist", { id: "asm_cats" });
    (data.categories || []).forEach(function (c) { catList.appendChild(el("option", { value: c })); });
    assembleField(col, "asm_cat", "product category", cat);
    col.appendChild(catList);
    cat.addEventListener("input", function () { asm.values.product_category = cat.value.trim(); scheduleAssemblePreview(); });
    var desc = assembleField(col, "asm_desc", "description", el("textarea", { id: "asm_desc", rows: "3", placeholder: "What it is for, in a sentence or two." }));
    desc.addEventListener("input", function () { asm.values.description = desc.value.trim(); scheduleAssemblePreview(); });
    col.appendChild(el("p", { id: "asm_kept", class: "brief-hint", hidden: "" }));
    col.appendChild(el("div", { id: "asm_answers" }));
  }

  function renderStartShapes() {
    var host = $("asm_start");
    if (!host) return;
    host.textContent = "";
    var sel = el("select", { id: "asm_shape", "aria-label": "Start from a shape" });
    sel.appendChild(el("option", { value: "", text: "No shape: pick the parts yourself" }));
    asm.data.shapes.forEach(function (s) {
      sel.appendChild(el("option", { value: s.id, text: s.title + " · " + (s.provider || "no cloud") + " · " + s.modules.length + " parts" }));
    });
    sel.value = asm.startShape;
    sel.addEventListener("change", function () { applyStartShape(sel.value); renderChunkCards(); scheduleAssemblePreview(); });
    host.appendChild(el("div", { class: "field" }, [sel]));
  }

  /* Starting from a shape: its chunks, each with what the shape binds for
   * it, and the shape's provider. The shape's own answers are the project's
   * to give; only the parts come across. */
  function applyStartShape(shapeId) {
    asm.startShape = shapeId || "";
    asm.shape = "";
    asm.choose = {};
    asm.shapeWith = {};
    asm.slotOf = {};
    asm.picked = {};
    asm.order = [];
    var shape = asm.data.shapes.filter(function (s) { return s.id === shapeId; })[0];
    if (!shape) return;
    if (shape.provider && shape.provider !== asm.provider) {
      asm.provider = shape.provider;
      var prov = $("asm_provider");
      if (prov) {
        prov.value = shape.provider;
        prov.dispatchEvent(new Event("change"));
      }
    }
    shape.modules.forEach(function (m) {
      pickChunk(m.module, true);
      asm.picked[m.module].with = Object.assign({}, m.with || {});
    });
    shape.slots.forEach(function (s) {
      if (!s.default) return;
      pickChunk(s.default, true);
      if (asm.picked[s.default]) asm.picked[s.default].with = Object.assign({}, slotAnswers(shape, s.default));
    });
  }

  /* ---- opening a project the panel made --------------------------------
   * The file's chunks, answers and edits become the panel's state, and Save
   * rewrites the file in place. Change the id and Create makes a new project
   * beside it instead.
   */
  function loadAssembled(id) {
    api("/api/assemble/open?id=" + encodeURIComponent(id)).then(function (res) {
      var v = res.values || {};
      var params = res.parameters || {};
      var compose = res.compose || {};
      var shaped = res.archetype && res.shape ? res.shape : null;
      asm.replace = id;
      asm.path = res.path || "";
      asm.note = res.note || [];
      asm.id = id;
      asm.touched = { id: true, slug: true };
      asm.name = v.name || id;
      asm.slug = params.slug || slugOf(asm.name);
      asm.shape = shaped ? res.archetype : "";
      asm.detach = false;
      asm.provider = shaped ? (shaped.provider || "") : (compose.provider || "");
      // The answers beyond the project's own fields: what the shape asks,
      // or whatever else the file answered. Kept, shown, written back.
      asm.answers = {};
      Object.keys(params).forEach(function (k) { if (!FIXED_ANSWERS[k]) asm.answers[k] = params[k]; });
      asm.values = {
        status: v.status || "Planned", owner_org_id: v.owner_org_id || "",
        criticality: v.criticality || params.criticality || "Medium", company_domain: v.company_domain || "",
        product_category: v.product_category || "", description: String(v.description || "").trim(),
      };
      // Fields the form does not show are kept as written, and said so.
      asm.kept = {};
      Object.keys(v).forEach(function (k) { if (!(k in asm.values) && k !== "name") asm.kept[k] = v[k]; });
      asm.buildType = String(v.build_type || "");
      delete asm.kept.build_type;
      asm.params = { account: params.account || "", region: params.region || "", classification: params.classification || "Confidential" };
      asm.more = {};
      ["blocks", "bind", "patterns", "relations", "title"].forEach(function (k) { if (compose[k]) asm.more[k] = compose[k]; });
      asm.extra = res.extra || null;
      // The names a product keeps from before its shape travel with the
      // file; the panel carries them and does not edit them.
      asm.ids = JSON.parse(JSON.stringify(res.ids || {}));
      asm.picked = {}; asm.order = []; asm.unknown = [];
      asm.shapeWith = {}; asm.slotOf = {}; asm.withoutExtra = []; asm.choose = {};
      if (shaped) {
        // The shape's parts with what it binds, the chosen part of each
        // slot, then what the file adds or tells a part, less what it
        // does without. A dropped alias the cards cannot show (a kit's
        // member) is carried as it was written.
        shaped.slots.forEach(function (s) {
          asm.choose[s.name] = s.default || "none";
          (s.options || []).forEach(function (o) { asm.slotOf[o] = s.name; });
        });
        Object.keys(res.choose || {}).forEach(function (k) { asm.choose[k] = res.choose[k]; });
        shaped.modules.forEach(function (m) { takeShapePart(m.module, m.with || {}); });
        shaped.slots.forEach(function (s) {
          var pick = asm.choose[s.name];
          if (pick && pick !== "none") takeShapePart(pick, slotAnswers(shaped, pick));
        });
        (res.modules || []).forEach(function (m) {
          var entry = typeof m === "string" ? { module: m } : (m || {});
          if (!entry.module) return;
          if (!chunkById(entry.module)) { asm.unknown.push(entry.module); return; }
          if (!asm.picked[entry.module]) { asm.picked[entry.module] = { with: {} }; asm.order.push(entry.module); }
          Object.assign(asm.picked[entry.module].with, JSON.parse(JSON.stringify(entry.with || {})));
        });
        (res.without || []).forEach(function (alias) {
          if (asm.picked[alias] && !asm.slotOf[alias]) {
            delete asm.picked[alias];
            asm.order = asm.order.filter(function (x) { return x !== alias; });
          } else {
            asm.withoutExtra.push(alias);
          }
        });
      } else {
        (compose.modules || []).forEach(function (m) {
          var entry = typeof m === "string" ? { module: m } : (m || {});
          if (!entry.module) return;
          if (!chunkById(entry.module)) { asm.unknown.push(entry.module); return; }
          if (!asm.picked[entry.module]) { asm.picked[entry.module] = { with: {} }; asm.order.push(entry.module); }
          asm.picked[entry.module].with = JSON.parse(JSON.stringify(entry.with || {}));
          if (entry.as && entry.as !== entry.module) asm.picked[entry.module].as = entry.as;
        });
      }
      asm.overrides = JSON.parse(JSON.stringify(res.overrides || {}));
      asm.exclude = {};
      (res.exclude || []).forEach(function (x) { asm.exclude[x] = true; });
      asm.startShape = "";
      fillProjectForm();
      renderChunkCards();
      setAssembleMode();
      scheduleAssemblePreview();
      syncUrl();
      if (asm.unknown.length) {
        toast("warn", "Not in the library", "The file names " + asm.unknown.join(", ") + ", which the library no longer has; saving would drop "
          + (asm.unknown.length === 1 ? "it" : "them") + ".");
      }
    }).catch(fail);
  }

  /* ---- a product on a shape --------------------------------------------
   * Its chunks are the shape's, with what the shape binds for each; a slot
   * is a choice of one part among several; what the file drops is `without`
   * and what it adds or tells a part is `modules`. The panel holds all of
   * it in the same picked set, and Save writes the differences back in the
   * shape's terms, or the whole as a compose block when told to detach.
   */
  var FIXED_ANSWERS = { slug: 1, product_name: 1, owner_org: 1, domain: 1, account: 1, region: 1, criticality: 1, classification: 1 };

  function currentShape() {
    return asm && asm.shape ? asm.data.shapes.filter(function (s) { return s.id === asm.shape; })[0] || null : null;
  }

  /* What a shape answers for a slot's option from its own parameters. The
   * chosen part arrives with it, the way a listed part arrives with its
   * `with`, and Save writes only what the product says beyond it. */
  function slotAnswers(shape, option) {
    var out = {};
    ((shape && shape.slots) || []).forEach(function (s) {
      if (s["with"] && s["with"][option]) Object.assign(out, s["with"][option]);
    });
    return out;
  }

  function takeShapePart(id, withs) {
    if (!chunkById(id)) { asm.unknown.push(id); return; }
    asm.shapeWith[id] = JSON.parse(JSON.stringify(withs || {}));
    if (!asm.picked[id]) { asm.picked[id] = { with: {} }; asm.order.push(id); }
    asm.picked[id].with = JSON.parse(JSON.stringify(withs || {}));
  }

  function chooseSlot(name, value) {
    var shape = currentShape();
    var slot = shape && shape.slots.filter(function (s) { return s.name === name; })[0];
    if (!slot) return;
    var before = asm.choose[name];
    if (before && before !== "none" && asm.picked[before]) {
      // What the part was told survives being chosen away and back.
      asm.stash[before] = asm.picked[before].with;
      delete asm.picked[before];
      delete asm.shapeWith[before];
      asm.order = asm.order.filter(function (x) { return x !== before; });
    }
    asm.choose[name] = value;
    if (value && value !== "none") {
      takeShapePart(value, slotAnswers(shape, value));
      if (asm.stash[value] && asm.picked[value]) asm.picked[value].with = JSON.parse(JSON.stringify(asm.stash[value]));
    }
    renderChunkCards();
    scheduleAssemblePreview();
  }

  function renderSlots() {
    var host = $("asm_slots");
    if (!host) return;
    host.textContent = "";
    var shape = currentShape();
    if (!shape || !shape.slots.length) return;
    host.appendChild(el("p", { class: "group-title", text: "Choices \u00b7 " + shape.slots.length }));
    host.appendChild(el("p", { class: "brief-hint", text:
      "Where the shape offers more than one part for a need. The chosen part is picked below and cannot be dropped; choose another, or none, here." }));
    shape.slots.forEach(function (s) {
      var sel = el("select", { id: "asm_slot_" + s.name, "aria-label": "Choice of " + s.name.replace(/_/g, " ") });
      s.options.forEach(function (o) {
        var chunk = chunkById(o);
        sel.appendChild(el("option", { value: o, text: (chunk ? chunk.name : o) + (o === s.default ? " \u00b7 the shape's default" : "") }));
      });
      if (s.optional) sel.appendChild(el("option", { value: "none", text: "none" }));
      sel.value = asm.choose[s.name] || s.default || "none";
      sel.addEventListener("change", function () { chooseSlot(s.name, sel.value); });
      host.appendChild(el("div", { class: "field" }, [el("label", { for: "asm_slot_" + s.name }, [s.name.replace(/_/g, " ")]), sel]));
    });
  }

  /* The questions beyond the project's own fields: what the shape asks
   * (a vendor, an upstream system), or whatever else a file answered. */
  function renderAnswers() {
    var host = $("asm_answers");
    if (!host) return;
    host.textContent = "";
    var shape = currentShape();
    var names = [];
    (shape ? shape.parameters : []).forEach(function (p) { if (!FIXED_ANSWERS[p.name] && names.indexOf(p.name) === -1) names.push(p.name); });
    Object.keys(asm.answers || {}).forEach(function (k) { if (!FIXED_ANSWERS[k] && names.indexOf(k) === -1) names.push(k); });
    if (!names.length) return;
    host.appendChild(el("p", { class: "group-title", text: shape ? "What the shape asks" : "Other answers" }));
    names.forEach(function (name) {
      var spec = (shape ? shape.parameters : []).filter(function (p) { return p.name === name; })[0] || {};
      var current = asm.answers[name];
      var input = el("input", { id: "asm_ans_" + name, type: "text",
        value: current == null ? "" : (Array.isArray(current) ? current.join(", ") : String(current)),
        placeholder: spec.default == null ? (spec.required ? "required" : "") : String(spec.default) });
      input.addEventListener("input", function () {
        var v = parseWith(input.value);
        if (v === undefined) delete asm.answers[name]; else asm.answers[name] = v;
        scheduleAssemblePreview();
      });
      var lab = el("label", { for: "asm_ans_" + name }, [name.replace(/_/g, " ")]);
      if (spec.required) lab.appendChild(el("span", { class: "req", text: "*" }));
      host.appendChild(el("div", { class: "field" }, [lab, input]));
    });
  }

  function fillProjectForm() {
    function set(id, value) { var node = $(id); if (node) node.value = value == null ? "" : String(value); }
    set("asm_name", asm.name); set("asm_id", asm.id); set("asm_slug", asm.slug);
    var prov = $("asm_provider");
    if (prov && prov.value !== asm.provider) { prov.value = asm.provider; prov.dispatchEvent(new Event("change")); }
    set("asm_account", asm.params.account); set("asm_region", asm.params.region);
    set("asm_owner", asm.values.owner_org_id); set("asm_domain", asm.values.company_domain);
    set("asm_crit", asm.values.criticality); set("asm_class", asm.params.classification);
    set("asm_state", asm.values.status); set("asm_cat", asm.values.product_category);
    set("asm_desc", asm.values.description); set("asm_shape", asm.startShape); set("asm_open", asm.replace);
    var kindHost = $("asm_type");
    if (kindHost) renderKindRows(kindHost);
    var typeDesc = $("asm_type_desc");
    if (typeDesc) { var held = currentType(); typeDesc.textContent = held ? held.description : ""; }
    var kept = $("asm_kept");
    if (kept) {
      var bits = Object.keys(asm.kept || {}).map(function (k) {
        var value = asm.kept[k];
        return k.replace(/_/g, " ") + " " + (Array.isArray(value) ? value.join(", ") : String(value));
      });
      Object.keys(asm.more || {}).forEach(function (k) {
        var value = asm.more[k];
        bits.push(k + (Array.isArray(value) ? " (" + value.length + ")" : ""));
      });
      if (asm.extra) bits.push("extra");
      if (asm.ids && Object.keys(asm.ids).length) bits.push(Object.keys(asm.ids).length + " kept ids");
      if (asm.withoutExtra && asm.withoutExtra.length) bits.push("without " + asm.withoutExtra.join(", "));
      kept.hidden = !bits.length;
      kept.textContent = bits.length ? "Also kept from the file, as written: " + bits.join(" \u00b7 ") + "." : "";
    }
    renderAnswers();
    renderSlots();
  }

  /* The head and the button say what the button will do: rewrite the file
   * the project was opened from, or make a new project when the id changed. */
  function setAssembleMode() {
    var h1 = $("asm_h1"), sub = $("asm_sub"), btn = $("asm_create");
    var saving = !!(asm.replace && asm.id === asm.replace);
    if (h1) h1.textContent = asm.replace ? (asm.name || asm.replace) : "Assemble a project";
    if (sub) {
      if (!asm.replace) {
        sub.textContent = "Pick the parts a product is made of, see the diagram they make, make the small "
          + "edits a product always needs, and save it as one file. Every part comes from the "
          + "library; the landing zone answers for what they run on.";
      } else if (saving && asm.shape && !asm.detach) {
        sub.textContent = "Opened from " + asm.path + ", on shape " + asm.shape + ". Its parts are selected and its choices are "
          + "under Choices; drop a part and Save records it as left out, add another and Save adds it. The file stays the "
          + "shape's answers and the differences. Change the id to make a new product from it instead.";
      } else if (saving && asm.shape) {
        sub.textContent = "Opened from " + asm.path + ", on shape " + asm.shape + ". Save writes it as its own compose block, "
          + "with the shape's blocks and patterns copied in, and the shape no longer governs it.";
      } else if (saving) {
        sub.textContent = "Opened from " + asm.path + ". Change the parts, the answers or the edits; Save rewrites that file "
          + "and keeps the note above its data. Change the id to make a new project from it instead.";
      } else {
        sub.textContent = "Opened from " + asm.path + ", with the id changed: Create writes a new project and leaves "
          + asm.replace + " as it is.";
      }
    }
    if (btn) btn.textContent = saving ? "Save project" : "Create project";
    var keepRow = $("asm_keep_row"), detachRow = $("asm_detach_row");
    if (keepRow) keepRow.hidden = !!(asm.shape && !asm.detach);
    if (detachRow) detachRow.hidden = !asm.shape;
  }

  /* ---- list answers as rows -------------------------------------------------
   * The roles a part creates are a small table with a column per key; the
   * spokes of a hub are one id per line. Nobody types JSON into a form.
   */
  function withRaw(id, p) {
    var picked = asm.picked[id];
    return picked && picked.with ? picked.with[p.name] : undefined;
  }

  function listColumns(p, current) {
    if (Array.isArray(current) && current.length
        && current.every(function (r) { return r && typeof r === "object" && !Array.isArray(r); })) {
      var keys = [];
      current.forEach(function (r) { Object.keys(r).forEach(function (k) { if (keys.indexOf(k) === -1) keys.push(k); }); });
      return keys;
    }
    var text = String(p.description || "");
    if (/mapping/i.test(text)) {
      var found = [];
      text.replace(/`([a-z_]+)`/g, function (_m, k) { if (found.indexOf(k) === -1) found.push(k); return ""; });
      if (found.length) return found;
    }
    if (p.name === "roles") return ["id", "name", "description", "interaction"];
    return null;
  }

  function isIdList(p, current) {
    if (Array.isArray(current) || Array.isArray(p.default)) return true;
    return /\blist of [a-z ]*ids\b/i.test(String(p.description || ""));
  }

  /* What a new line in a list is likely to hold, read off the question. */
  function listPlaceholder(p) {
    var text = String(p.description || "");
    if (/block/i.test(text)) return "tier.component";
    if (/service/i.test(text)) return "TS-\u2026";
    if (/system|application|source/i.test(text)) return "SYS-\u2026";
    return "";
  }

  function listEditor(chunkId, p, columns) {
    var picked = asm.picked[chunkId];
    var current = picked.with[p.name];
    var rows = Array.isArray(current) ? current.slice() : [];
    if (columns) rows = rows.map(function (r) { return Object.assign({}, r); });
    var box = el("div", { class: "rows" });
    function commit() {
      var kept = rows.filter(function (r) {
        if (columns) return Object.keys(r).some(function (k) { return String(r[k] == null ? "" : r[k]).trim(); });
        return String(r == null ? "" : r).trim();
      });
      if (kept.length) picked.with[p.name] = kept; else delete picked.with[p.name];
      scheduleAssemblePreview();
    }
    function removeButton(i) {
      var rm = el("button", { type: "button", class: "btn small rows-rm", text: "\u00d7", title: "Remove",
        "aria-label": "Remove " + p.name.replace(/_/g, " ") + " " + (i + 1) });
      rm.addEventListener("click", function () { rows.splice(i, 1); commit(); draw(false); });
      return rm;
    }
    function draw(focusNew) {
      box.textContent = "";
      var first = null;
      if (columns) {
        // A record is a small card with a line per key: four inputs across
        // a narrow column would show four words.
        rows.forEach(function (row, i) {
          var rec = el("div", { class: "rows-rec" });
          rec.appendChild(el("div", { class: "rows-rec-head" }, [
            el("span", { class: "rows-rec-n mono", text: String(i + 1) }), removeButton(i),
          ]));
          columns.forEach(function (c, j) {
            var input = el("input", { type: "text", value: row[c] == null ? "" : String(row[c]),
              "aria-label": c.replace(/_/g, " ") + " of " + p.name.replace(/_/g, " ") + " " + (i + 1) });
            input.addEventListener("input", function () { row[c] = input.value; commit(); });
            rec.appendChild(el("label", { class: "rows-rec-field" }, [el("span", { class: "rows-rec-key", text: c.replace(/_/g, " ") }), input]));
            if (j === 0) first = input;
          });
          box.appendChild(rec);
        });
      } else {
        rows.forEach(function (value, i) {
          var input = el("input", { type: "text", class: "mono-in", value: value == null ? "" : String(value), placeholder: listPlaceholder(p),
            "aria-label": p.name.replace(/_/g, " ") + " " + (i + 1) });
          input.addEventListener("input", function () { rows[i] = input.value.trim(); commit(); });
          box.appendChild(el("div", { class: "rows-line" }, [input, removeButton(i)]));
          first = input;
        });
      }
      var add = el("button", { type: "button", class: "btn small", text: columns ? "+ row" : "+ id" });
      add.addEventListener("click", function () { rows.push(columns ? {} : ""); draw(true); });
      box.appendChild(add);
      if (focusNew && first) first.focus();
    }
    draw(false);
    return box;
  }

  function chunkById(id) {
    return asm.data.chunks.filter(function (c) { return c.id === id; })[0] || null;
  }

  /* Picking a chunk brings what it requires; dropping one is refused while
   * another picked chunk requires it, and the card says which. */
  function pickChunk(id, on) {
    var chunk = chunkById(id);
    if (!chunk) return;
    if (on) {
      if (!asm.picked[id]) { asm.picked[id] = { with: {} }; asm.order.push(id); }
      (chunk.requires || []).forEach(function (r) { if (!asm.picked[r]) pickChunk(r, true); });
      // What the provider's own shape binds for this chunk is the right
      // starting answer: an API that runs on the gateway, a channel on the
      // cluster. The project can still say otherwise.
      if (!Object.keys(asm.picked[id].with).length) {
        var shape = asm.data.shapes.filter(function (s) { return s.provider === asm.provider; })[0];
        var entry = shape && shape.modules.filter(function (m) { return m.module === id; })[0];
        if (entry && entry.with) asm.picked[id].with = Object.assign({}, entry.with);
      }
    } else {
      delete asm.picked[id];
      asm.order = asm.order.filter(function (x) { return x !== id; });
    }
  }

  function heldBy(id) {
    var kept = [];
    asm.order.forEach(function (other) {
      var chunk = chunkById(other);
      if (chunk && (chunk.requires || []).indexOf(id) !== -1) kept.push(chunk.name);
      if (chunk && chunk.kit && (chunk.members || []).indexOf(id) !== -1) kept.push(chunk.name);
    });
    return kept;
  }

  function buildAssembleChunks(col) {
    col.appendChild(el("div", { class: "asm-chunks-head" }, [
      el("p", { class: "group-title", id: "asm_chunks_title", text: "Parts" }),
      el("input", { id: "asm_filter", type: "search", class: "table-filter", placeholder: "Filter parts…", "aria-label": "Filter parts" }),
    ]));
    col.appendChild(el("p", { class: "brief-hint", text:
      "Each card is a part from the library and shows what it creates. A part brings whatever it requires." }));
    col.appendChild(el("div", { id: "asm_deviations", class: "asm-devs", hidden: "" }));
    col.appendChild(el("div", { id: "asm_slots" }));
    var host = el("div", { id: "asm_cards", class: "chunk-list" });
    col.appendChild(host);
    $("asm_filter").addEventListener("input", renderChunkCards);
  }

  function withValue(id, p) {
    var picked = asm.picked[id];
    var v = picked && picked.with ? picked.with[p.name] : undefined;
    if (v === undefined || v === null) return "";
    return Array.isArray(v) ? v.join(", ") : (typeof v === "object" ? JSON.stringify(v) : String(v));
  }

  function parseWith(text) {
    var t = String(text || "").trim();
    if (!t) return undefined;
    if (t[0] === "[" || t[0] === "{") {
      try { return JSON.parse(t); } catch (err) { /* not JSON: a word */ }
    }
    if (t.indexOf(",") !== -1) return t.split(",").map(function (x) { return x.trim(); }).filter(Boolean);
    return t;
  }

  function renderChunkCards() {
    var host = $("asm_cards");
    if (!host) return;
    var q = ($("asm_filter").value || "").trim().toLowerCase();
    host.textContent = "";
    var picked = asm.order.length;
    $("asm_chunks_title").textContent = "Parts · " + picked + " of " + asm.data.chunks.length + " selected";
    var shape = currentShape();
    if (shape && !shape.modules.length && !shape.slots.length) {
      host.appendChild(el("p", { class: "brief-hint", text:
        "This shape provides what it makes itself and has no parts to pick; what it draws is on the right, and the file is its answers "
        + "and overrides. Selecting a part here adds it to the product." }));
    }
    var type = currentType();
    var matches = asm.data.chunks.filter(function (c) {
      return !(q && (c.name + " " + c.description + " " + c.category + " " + c.id).toLowerCase().indexOf(q) === -1);
    });
    function roleOf(chunk) {
      if (!type) return "";
      if (type.requires.indexOf(chunk.id) !== -1) return "required";
      if (type.includes.indexOf(chunk.id) !== -1) return "included";
      if (type.offers.indexOf(chunk.id) !== -1) return "offered";
      return "other";
    }
    function byCategory(list, into) {
      var groups = {};
      list.forEach(function (c) { (groups[c.category || "Other"] = groups[c.category || "Other"] || []).push(c); });
      Object.keys(groups).sort().forEach(function (category) {
        into.appendChild(el("p", { class: "chunk-cat", text: category }));
        groups[category].forEach(function (chunk) { into.appendChild(chunkCard(chunk, roleOf(chunk))); });
      });
    }
    if (type) {
      // With a type chosen the list is the standard build first, then the
      // additions it offers, and the rest folded away: twenty-eight cards
      // in alphabetical categories was a catalog, not a choice.
      var standard = matches.filter(function (c) { return roleOf(c) === "required" || roleOf(c) === "included"; });
      var offered = matches.filter(function (c) { return roleOf(c) === "offered"; });
      var other = matches.filter(function (c) { return roleOf(c) === "other"; });
      if (standard.length) {
        host.appendChild(el("p", { class: "chunk-group", text: "Standard parts" }));
        standard.forEach(function (c) { host.appendChild(chunkCard(c, roleOf(c))); });
      }
      if (offered.length) {
        host.appendChild(el("p", { class: "chunk-group", text: "Optional additions" }));
        offered.forEach(function (c) { host.appendChild(chunkCard(c, "offered")); });
      }
      if (other.length) {
        var fold = el("details", { class: "chunk-fold" }, [
          el("summary", { text: "Other parts · " + other.length + " (not part of this type)" }),
        ]);
        var inner = el("div", { class: "chunk-list" });
        byCategory(other, inner);
        fold.appendChild(inner);
        fold.open = other.some(function (c) { return !!asm.picked[c.id]; });
        host.appendChild(fold);
      }
    } else {
      byCategory(matches, host);
    }
    renderDeviations();
    if (!host.childNodes.length) host.appendChild(el("p", { class: "brief-hint", text: "No part matches " + q + "." }));
  }

  function currentType() {
    if (!asm || !asm.buildType) return null;
    return (asm.data.types || []).filter(function (t) { return t.id === asm.buildType; })[0] || null;
  }

  /* Choosing a type: the shape that is the type on this cloud, with its
   * parts, where there is one; the type's required and included parts
   * against the landing zone where there is not. */
  function applyBuildType(id, keepPicks) {
    asm.buildType = id || "";
    var type = currentType();
    var desc = $("asm_type_desc");
    if (desc) desc.textContent = type ? type.description : "";
    var sel = $("asm_type");
    if (sel) renderKindRows(sel);
    if (type) {
      var shapeId = type.shapes[asm.provider] || type.shapes.any || "";
      if (shapeId && asm.data.shapes.some(function (s) { return s.id === shapeId; })) {
        applyStartShape(shapeId);
      } else {
        if (!keepPicks) {
          asm.startShape = ""; asm.shape = ""; asm.choose = {}; asm.shapeWith = {}; asm.slotOf = {};
          asm.picked = {}; asm.order = [];
        }
        type.requires.concat(type.includes).forEach(function (m) { pickChunk(m, true); });
      }
      var start = $("asm_shape");
      if (start) start.value = asm.startShape;
    }
    renderChunkCards();
    scheduleAssemblePreview();
  }

  /* Where the choice departs from the type's standard build, said as it is
   * made: a required part missing, an included part dropped, a part the
   * type does not list. The same three things `terrane validate` reports. */
  function renderDeviations() {
    var host = $("asm_deviations");
    if (!host) return;
    host.textContent = "";
    var type = currentType();
    if (!type) { host.hidden = true; return; }
    var have = {};
    asm.order.forEach(function (id) {
      have[id] = true;
      var c = chunkById(id);
      if (c && c.kit) (c.members || []).forEach(function (m) { if ((asm.withoutExtra || []).indexOf(m) === -1) have[m] = true; });
    });
    function present(id) {
      var c = chunkById(id);
      if (c && c.kit) return (c.members || []).every(function (m) { return have[m]; });
      return !!have[id];
    }
    function nameOf(id) { var c = chunkById(id); return c ? c.name : id; }
    var listed = {};
    type.requires.concat(type.includes, type.offers).forEach(function (id) {
      listed[id] = true;
      var c = chunkById(id);
      if (c && c.kit) (c.members || []).forEach(function (m) { listed[m] = true; });
    });
    var lines = [];
    type.requires.forEach(function (id) { if (!present(id)) lines.push({ kind: "bad", text: nameOf(id) + " is required for this type and is missing." }); });
    type.includes.forEach(function (id) { if (!present(id)) lines.push({ kind: "warn", text: nameOf(id) + " is included by default and has been dropped." }); });
    Object.keys(have).sort().forEach(function (id) { if (!listed[id]) lines.push({ kind: "warn", text: nameOf(id) + " is not part of this type." }); });
    host.hidden = false;
    if (!lines.length) {
      host.appendChild(el("p", { class: "asm-dev is-ok", text: "Matches the standard build for this type." }));
      return;
    }
    host.appendChild(el("p", { class: "asm-dev-h", text: "Deviations from the standard build" }));
    lines.forEach(function (l) { host.appendChild(el("p", { class: "asm-dev is-" + l.kind, text: l.text })); });
  }

  function chunkCard(chunk, role) {
    var on = !!asm.picked[chunk.id];
    var holders = on ? heldBy(chunk.id) : [];
    var slotName = on && asm.shape ? asm.slotOf[chunk.id] : null;
    var box = el("input", { type: "checkbox", id: "chunk_" + chunk.id, "aria-label": chunk.name });
    box.checked = on;
    box.disabled = holders.length > 0 || !!slotName || role === "required";
    var badges = [];
    if (role === "required") badges.push(el("span", { class: "chunk-n is-role", text: "required" }));
    else if (role === "included") badges.push(el("span", { class: "chunk-n is-role", text: "included by default" }));
    badges.push(el("span", { class: "chunk-n mono", text: chunk.provides + (chunk.provides === 1 ? " entity" : " entities") }));
    if (chunk.kit) badges.push(el("span", { class: "chunk-n mono", text: "kit of " + chunk.members.length }));
    if ((chunk.requires || []).length) badges.push(el("span", { class: "chunk-n mono", text: "needs " + chunk.requires.join(", ") }));
    var card = el("div", { class: "chunk" + (on ? " is-on" : "") }, [
      el("label", { class: "chunk-head", for: "chunk_" + chunk.id }, [
        box,
        chunkThumb(chunk, asm.data.swatches || {}),
        el("span", { class: "chunk-text" }, [
          el("span", { class: "chunk-name", text: chunk.name }),
          el("span", { class: "chunk-desc", text: chunk.description || "" }),
          el("span", { class: "chunk-badges" }, badges),
        ]),
      ]),
    ]);
    if (holders.length) {
      card.appendChild(el("span", { class: "part-why", text: "kept by " + holders.join(", ") }));
    }
    if (slotName) {
      card.appendChild(el("span", { class: "part-why", text: "chosen for " + slotName.replace(/_/g, " ") + "; change it under Choices" }));
    }
    if (on && chunk.kit && asm.shape && (chunk.members || []).length) {
      // A kit's members, each its own row: untick one and the product does
      // without it, which the file says as `without` by the member's alias.
      // A member nothing may drop, or one another kept part requires, is
      // shown and not offered.
      var members = el("div", { class: "kit-members" });
      members.appendChild(el("span", { class: "part-why", text: "members; untick one to do without it" }));
      chunk.members.forEach(function (mid) {
        var member = chunkById(mid);
        var dropped = (asm.withoutExtra || []).indexOf(mid) !== -1;
        var fixed = !!(member && member.optional === false);
        var neededBy = asm.order.filter(function (other) {
          var c = chunkById(other);
          return c && other !== mid && (asm.withoutExtra || []).indexOf(other) === -1 && (c.requires || []).indexOf(mid) !== -1;
        }).map(function (other) { var c = chunkById(other); return c ? c.name : other; });
        var mbox = el("input", { type: "checkbox", id: "kit_" + chunk.id + "_" + mid, "aria-label": member ? member.name : mid });
        mbox.checked = !dropped;
        mbox.disabled = fixed || neededBy.length > 0;
        mbox.addEventListener("change", function () {
          asm.withoutExtra = (asm.withoutExtra || []).filter(function (x) { return x !== mid; });
          if (!mbox.checked) asm.withoutExtra.push(mid);
          renderChunkCards();
          scheduleAssemblePreview();
        });
        members.appendChild(el("label", { class: "kit-member" + (dropped ? " is-off" : ""), for: "kit_" + chunk.id + "_" + mid }, [
          mbox,
          el("span", { class: "km-name", text: member ? member.name : mid }),
          el("span", { class: "km-note mono", text: fixed ? "cannot be dropped" : neededBy.length ? "needed by " + neededBy.join(", ") : "" }),
        ]));
      });
      card.appendChild(members);
    }
    if (on) {
      var fields = el("div", { class: "chunk-fields" });
      (chunk.parameters || []).forEach(function (p) {
        var inputId = "cw_" + chunk.id + "_" + p.name;
        var lab = el("label", { for: inputId }, [p.name.replace(/_/g, " ")]);
        if (p.required) lab.appendChild(el("span", { class: "req", text: "*" }));
        var hint = p.description || "";
        if (p.component) {
          var bound = p.bound && p.bound[asm.provider];
          hint = (hint ? hint.replace(/[.\s]+$/, "") + ". " : "") + "Of kind " + p.component.replace(/-/g, " ") + "; "
            + (bound ? "the " + (asm.provider || "shared") + " zone has " + bound : "no " + (asm.provider || "shared") + " service of that kind is tagged landing-zone") + ".";
        }
        if (hint) lab.appendChild(el("span", { class: "hint", text: hint }));
        var raw = withRaw(chunk.id, p);
        var columns = listColumns(p, raw);
        if (columns || isIdList(p, raw)) {
          // A list answer is rows: a table for mappings, a line per id.
          fields.appendChild(el("div", { class: "field part-field" }, [lab, listEditor(chunk.id, p, columns)]));
          return;
        }
        var placeholder = p.component && p.bound && p.bound[asm.provider] ? p.bound[asm.provider]
          : (p.default == null ? (p.required ? "required" : "") : (Array.isArray(p.default) ? p.default.join(", ") : String(p.default)));
        var input = el("input", { id: inputId, type: "text", value: withValue(chunk.id, p), placeholder: placeholder });
        input.addEventListener("input", function () {
          var v = parseWith(input.value);
          if (v === undefined) delete asm.picked[chunk.id].with[p.name];
          else asm.picked[chunk.id].with[p.name] = v;
          scheduleAssemblePreview();
        });
        fields.appendChild(el("div", { class: "field part-field" }, [lab, input]));
      });
      // What the chunk carries from a shape or a file that is not one of its
      // own questions: the block it runs on, the services it uses.
      var declared = {};
      (chunk.parameters || []).forEach(function (p) { declared[p.name] = true; });
      var carried = (asm.picked[chunk.id] && asm.picked[chunk.id].with) || {};
      Object.keys(carried).filter(function (k) { return !declared[k]; }).sort().forEach(function (k) {
        var value = carried[k];
        fields.appendChild(el("p", { class: "chunk-bind mono", text:
          k.replace(/_/g, " ") + " \u00b7 " + (Array.isArray(value) ? value.join(", ") : (typeof value === "object" ? JSON.stringify(value) : String(value))) }));
      });
      if (fields.childNodes.length) card.appendChild(fields);
    }
    box.addEventListener("change", function () {
      pickChunk(chunk.id, box.checked);
      renderChunkCards();
      scheduleAssemblePreview();
    });
    return card;
  }

  function buildAssemblePreview(col, readOnly) {
    col.appendChild(el("p", { class: "group-title", text: "What it makes" }));
    var sheet = el("div", { class: "asm-sheet" }, [
      el("div", { id: "asm_canvas", class: "asm-canvas", role: "img", "aria-label": "The assembled project, drawn" }),
      el("div", { id: "asm_legend", class: "legend asm-legend" }),
    ]);
    col.appendChild(sheet);
    col.appendChild(el("p", { id: "asm_status", class: "asm-status" }));
    col.appendChild(el("p", { class: "group-title", text: "Small edits" }));
    col.appendChild(el("p", { class: "brief-hint", text:
      "Every entity the parts create. Rename one, drop one, or set a field on it; each is saved as an override or an exclusion on the product, never into the part." }));
    col.appendChild(el("div", { id: "asm_edits" }));
    var fileBox = el("details", { class: "asm-file" }, [
      el("summary", { text: "The file as it would be written" }),
      el("pre", { id: "asm_text", class: "asm-text mono" }),
    ]);
    col.appendChild(fileBox);
    var foot = el("div", { class: "asm-foot" });
    if (readOnly) {
      foot.appendChild(el("p", { class: "brief-hint", text:
        "This is the read-only copy: the parts are here to read, and the preview and the file need the local app." }));
    } else {
      var keep = el("input", { type: "checkbox", id: "asm_keep" });
      var keepId = el("input", { id: "asm_keep_id", type: "text", placeholder: "shape id, e.g. merchant-digital-product", hidden: "" });
      var keepTitle = el("input", { id: "asm_keep_title", type: "text", placeholder: "shape title", hidden: "" });
      keep.addEventListener("change", function () {
        asm.saveShape = keep.checked;
        keepId.hidden = !keep.checked;
        keepTitle.hidden = !keep.checked;
      });
      keepId.addEventListener("input", function () { asm.shapeId = keepId.value.trim(); });
      keepTitle.addEventListener("input", function () { asm.shapeTitle = keepTitle.value.trim(); });
      foot.appendChild(el("div", { id: "asm_keep_row" }, [
        el("label", { class: "table-toggle" }, [keep, el("span", { text: "Also keep this choice of parts as a shape, for the next product like it" })]),
        el("div", { class: "asm-keep" }, [keepId, keepTitle]),
      ]));
      var detach = el("input", { type: "checkbox", id: "asm_detach" });
      detach.addEventListener("change", function () { asm.detach = detach.checked; setAssembleMode(); scheduleAssemblePreview(); });
      foot.appendChild(el("div", { id: "asm_detach_row", hidden: "" }, [
        el("label", { class: "table-toggle" }, [detach, el("span", { text: "Write it as its own compose block instead, and let go of the shape" })]),
      ]));
    }
    col.appendChild(foot);
  }

  function assemblyBody() {
    var modules = asm.order.map(function (id) {
      var entry = { module: id };
      if (asm.picked[id] && asm.picked[id].as) entry.as = asm.picked[id].as;
      var withs = asm.picked[id] && asm.picked[id].with;
      if (withs && Object.keys(withs).length) entry.with = withs;
      return entry;
    });
    var params = {
      slug: asm.slug, product_name: asm.name, owner_org: asm.values.owner_org_id,
      domain: asm.values.company_domain, account: asm.params.account, region: asm.params.region,
      criticality: asm.values.criticality, classification: asm.params.classification,
    };
    Object.keys(asm.answers || {}).forEach(function (k) {
      if (!FIXED_ANSWERS[k] && asm.answers[k] !== "" && asm.answers[k] != null) params[k] = asm.answers[k];
    });
    var held = currentShape();
    if (held && !asm.detach) {
      // Only what the shape asks: a shape built on no blocks asks for no
      // account, and refuses an answer it did not ask for.
      var declared = {};
      (held.parameters || []).forEach(function (p) { declared[p.name] = true; });
      Object.keys(FIXED_ANSWERS).forEach(function (k) { if (!declared[k]) delete params[k]; });
    }
    var exclude = Object.keys(asm.exclude).filter(function (k) { return asm.exclude[k]; });
    var body = {
      id: asm.id, values: Object.assign({ name: asm.name }, asm.kept || {}, asm.values),
      parameters: params, overrides: asm.overrides, exclude: exclude,
    };
    var shape = currentShape();
    if (shape && !asm.detach) {
      // In the shape's terms: what is dropped, what is added, and what a
      // kept part is told beyond what the shape binds for it.
      var shapeAliases = {};
      shape.modules.forEach(function (m) { shapeAliases[m.as || m.module] = true; });
      var without = (asm.withoutExtra || []).slice();
      Object.keys(shapeAliases).forEach(function (alias) { if (!asm.picked[alias]) without.push(alias); });
      var told = [];
      asm.order.forEach(function (id) {
        var withs = (asm.picked[id] && asm.picked[id].with) || {};
        var base = asm.shapeWith[id];
        if (base === undefined) {
          var entry = { module: id };
          if (Object.keys(withs).length) entry.with = withs;
          told.push(entry);
          return;
        }
        var delta = {};
        Object.keys(withs).forEach(function (k) { if (JSON.stringify(withs[k]) !== JSON.stringify(base[k])) delta[k] = withs[k]; });
        if (Object.keys(delta).length) told.push({ module: id, with: delta });
      });
      body.archetype = shape.id;
      body.choose = asm.choose;
      body.without = without;
      body.modules = told;
      if (asm.ids && Object.keys(asm.ids).length) body.ids = asm.ids;
    } else {
      var more = Object.assign({}, asm.more || {});
      if (shape && asm.detach) {
        // Detached: the shape's blocks, binds and patterns come along, so
        // the product keeps drawing as it did.
        if (shape.blocks && shape.blocks.length) more.blocks = shape.blocks;
        if (shape.bind && Object.keys(shape.bind).length) more.bind = shape.bind;
        if (shape.patterns && shape.patterns.length) more.patterns = shape.patterns;
      }
      body.compose = Object.assign(more, { provider: asm.provider, modules: modules });
    }
    if (asm.extra) body.extra = asm.extra;
    if (asm.replace) body.replace = asm.replace;
    if (asm.buildType) body.buildType = asm.buildType;
    return body;
  }

  function scheduleAssemblePreview() {
    if (!asm) return;
    if (asm.timer) clearTimeout(asm.timer);
    asm.timer = setTimeout(runAssemblePreview, 320);
  }

  function assembleReady() {
    var missing = [];
    if (!asm.name) missing.push("a name");
    if (!asm.id) missing.push("an id");
    if (!asm.slug) missing.push("a slug");
    if (!asm.values.owner_org_id) missing.push("an owner");
    // A product on a shape draws its shape, parts or none: the two shapes
    // that provide their entities themselves have nothing to pick.
    if (!asm.order.length && !asm.shape) missing.push("at least one part");
    return missing;
  }

  function setAssembleStatus(kind, text) {
    var box = $("asm_status");
    if (!box) return;
    box.textContent = text || "";
    box.className = "asm-status" + (kind ? " is-" + kind : "");
    renderAsmSteps();
  }

  function runAssemblePreview() {
    if (!asm || window.__AAC_STATIC__) return;
    var missing = assembleReady();
    var create = $("asm_create");
    if (missing.length) {
      setAssembleStatus("", "Needs " + missing.join(", ") + " before there is anything to draw.");
      if (create) create.disabled = true;
      return;
    }
    var body = assemblyBody();
    var ticket = ++asm.inflight;
    setAssembleStatus("busy", "Assembling…");
    api("/api/assemble/preview", body).then(function (res) {
      if (ticket !== asm.inflight) return;
      asm.preview = res;
      renderAssemblePreview(res);
      if (create) create.disabled = res.conflicts.length > 0;
    }).catch(function (err) {
      if (ticket !== asm.inflight) return;
      asm.preview = null;
      setAssembleStatus("bad", err.message || String(err));
      if (create) create.disabled = true;
    });
  }

  function renderAssemblePreview(res) {
    var c = res.counts;
    var parts = [];
    Object.keys(c.byType || {}).forEach(function (t) {
      var label = (state.schema && state.schema.entities[t] && state.schema.entities[t].label) || t;
      parts.push(c.byType[t] + " " + label + (c.byType[t] === 1 ? "" : "s"));
    });
    var line = parts.join(", ") + "; " + c.relations + " relationship" + (c.relations === 1 ? "" : "s") + ".";
    if (res.shapeMatch && !asm.shape) line += " This is the " + res.shapeMatch.title + " shape, part for part.";
    if (res.conflicts.length) {
      var fix = asm.replace && asm.id !== asm.replace
        ? " Change the slug, or put the id back to " + asm.replace + " to save over it."
        : " Change the slug or the id.";
      setAssembleStatus("bad", line + " Already in the model: " + res.conflicts.join(", ") + "." + fix);
    } else {
      setAssembleStatus("ok", line);
    }
    $("asm_text").textContent = res.text || "";
    renderAssembleEdits(res);
    if (res.graph && !res.conflicts.length) {
      drawPreviewGraph($("asm_canvas"), res.graph);
    } else {
      if (asm.cy) { asm.cy.destroy(); asm.cy = null; }
      $("asm_canvas").textContent = "";
      $("asm_legend").textContent = "";
      if (res.graphError) setAssembleStatus("bad", res.graphError);
    }
  }

  function drawPreviewGraph(container, payload) {
    if (asm.cy) { asm.cy.destroy(); asm.cy = null; }
    LANES = payload.lanes || {};
    // A node with many edges needs a taller side for the fan and for the
    // labels the placer would otherwise hide: the switch on the governance
    // diagram sent five edges out of a 39px side. Degree is known before the
    // layout picks sides, so the box grows with it.
    var degree = {};
    payload.elements.forEach(function (e) {
      if (!e.data.source) return;
      degree[e.data.source] = (degree[e.data.source] || 0) + 1;
      degree[e.data.target] = (degree[e.data.target] || 0) + 1;
    });
    payload.elements.forEach(function (e) {
      if (e.data.source) {
        e.data.shown = e.data.label || "";
        e.data.lx = 0; e.data.ly = 0; e.data.segw = "0.5"; e.data.segd = "0";
        e.data.sep = "outside-to-node"; e.data.tep = "outside-to-node";
        return;
      }
      if (e.data.isGroup) {
        // A boundary with no mark drops the empty field the way a leaf does;
        // Cytoscape cannot parse an empty image.
        if (!e.data.icon) delete e.data.icon;
        return;
      }
      e.data.degree = degree[e.data.id] || 0;
      var category = e.data.componentCategory || COMPONENT_CATEGORY[e.data.componentType] || "";
      if (GLYPHS[category]) e.data.glyph = GLYPHS[category];
      else delete e.data.glyph;
      if (e.data.icon) delete e.data.glyph; else delete e.data.icon;
      var corner = !e.data.icon && !e.data.glyph && CORNERED[SHAPES[e.data.entityType]]
        ? typeIcon(e.data.entityType, e.data.stroke) : null;
      if (corner) e.data.ticon = corner; else delete e.data.ticon;
    });
    evenBoxes(payload.elements);
    var cy = cytoscape({
      container: container,
      elements: payload.elements,
      style: graphStyle(true),
      layout: { name: "preset", animate: false, positions: function () { return { x: 0, y: 0 }; } },
    });
    attachTechLayer(cy);
    var wanted = payload.layout === "TB" ? "TB" : "LR";
    function routeByHand() {
      var dir = bestDirection(cy, wanted);
      cy.fit(undefined, 20);
      routeDrawing(cy, dir === "TB");
      placeEdgeLabels(cy, true);
    }
    if (elkFits(cy)) {
      layoutElk(cy, wanted, true).then(function () {
        if (asm.cy !== cy) return;
        cy.fit(undefined, 20);
        placeEdgeLabels(cy, true);
      }).catch(function () { if (asm.cy === cy) routeByHand(); });
    } else {
      routeByHand();
    }
    cy.on("tap", "node", function (evt) {
      var row = document.getElementById("asm_row_" + evt.target.id());
      if (!row) return;
      Array.prototype.forEach.call(document.querySelectorAll(".asm-edit.is-hit"), function (r) { r.classList.remove("is-hit"); });
      row.classList.add("is-hit");
      row.scrollIntoView({ block: "nearest" });
    });
    asm.cy = cy;
    var legend = $("asm_legend");
    legend.textContent = "";
    (payload.legend.types || []).forEach(function (t) {
      legend.appendChild(el("span", { class: "key" }, [shapeKey(t.key, t.fill, t.stroke, 1.4, "solid"), el("span", { text: t.label + " · " + t.count })]));
    });
  }

  function renderAssembleEdits(res) {
    var host = $("asm_edits");
    host.textContent = "";
    var swatches = asm.data.swatches || {};
    var fieldsOf = asm.data.fields || {};
    var table = el("table", { class: "asm-edits" });
    var cols = el("colgroup");
    ["c-sw", "c-name", "c-from", "c-keep", "c-set"].forEach(function (cls) { cols.appendChild(el("col", { class: cls })); });
    table.appendChild(cols);
    table.appendChild(el("thead", {}, [el("tr", {}, [
      el("th", { text: "" }), el("th", { text: "Entity" }), el("th", { text: "From" }), el("th", { text: "Keep" }), el("th", { text: "Set a field" }),
    ])]));
    var body = el("tbody");
    res.produced.forEach(function (p) {
      var sw = swatches[p.type] || { fill: "#fff", stroke: "#999" };
      var over = asm.overrides[p.id] || {};
      var nameIn = el("input", { type: "text", class: "asm-name", value: over.name || p.name, "aria-label": "Name of " + p.id });
      nameIn.addEventListener("change", function () {
        var v = nameIn.value.trim();
        asm.overrides[p.id] = asm.overrides[p.id] || {};
        if (v && v !== p.name) asm.overrides[p.id].name = v; else delete asm.overrides[p.id].name;
        if (!Object.keys(asm.overrides[p.id]).length) delete asm.overrides[p.id];
        scheduleAssemblePreview();
      });
      var keep = el("input", { type: "checkbox", "aria-label": "Keep " + p.id });
      keep.checked = !asm.exclude[p.id];
      keep.addEventListener("change", function () {
        if (keep.checked) delete asm.exclude[p.id]; else asm.exclude[p.id] = true;
        scheduleAssemblePreview();
      });
      var setBox = el("span", { class: "asm-set" });
      Object.keys(over).filter(function (k) { return k !== "name"; }).forEach(function (k) {
        var chip = el("button", { type: "button", class: "help-chip as-btn", title: "Remove this override",
          text: k + ": " + over[k] + " ×" });
        chip.addEventListener("click", function () {
          delete asm.overrides[p.id][k];
          if (!Object.keys(asm.overrides[p.id]).length) delete asm.overrides[p.id];
          scheduleAssemblePreview();
        });
        setBox.appendChild(chip);
      });
      var fieldSel = el("select", { "aria-label": "Field to set on " + p.id });
      fieldSel.appendChild(el("option", { value: "", text: "field…" }));
      (fieldsOf[p.type] || []).forEach(function (f) { if (f !== "name") fieldSel.appendChild(el("option", { value: f, text: f })); });
      var valIn = el("input", { type: "text", class: "asm-val", placeholder: "value", "aria-label": "Value" });
      var current = p.fields || {};
      fieldSel.addEventListener("change", function () { valIn.placeholder = current[fieldSel.value] !== undefined ? String(current[fieldSel.value]) : "value"; });
      var add = el("button", { type: "button", class: "btn small", text: "Set" });
      add.addEventListener("click", function () {
        if (!fieldSel.value || !valIn.value.trim()) return;
        asm.overrides[p.id] = asm.overrides[p.id] || {};
        asm.overrides[p.id][fieldSel.value] = valIn.value.trim();
        scheduleAssemblePreview();
      });
      setBox.appendChild(el("span", { class: "asm-set-form" }, [fieldSel, valIn, add]));
      var row = el("tr", { class: "asm-edit" + (asm.exclude[p.id] ? " is-dropped" : ""), id: "asm_row_" + p.id }, [
        el("td", {}, [shapeKey(p.type, sw.fill, sw.stroke, 1.4, "solid")]),
        el("td", {}, [nameIn, el("span", { class: "gi-id mono", text: p.id })]),
        el("td", { class: "mono asm-from", text: p.fromChunk || "block" }),
        el("td", {}, [keep]),
        el("td", {}, [setBox]),
      ]);
      body.appendChild(row);
    });
    table.appendChild(body);
    host.appendChild(table);
  }

  function createAssembled() {
    if (!asm) return;
    var missing = assembleReady();
    if (missing.length) { toast("err", "Not yet", "Needs " + missing.join(", ") + "."); return; }
    var body = assemblyBody();
    if (asm.saveShape && !body.archetype) {
      if (!asm.shapeId || !asm.shapeTitle) { toast("err", "The shape needs an id and a title"); return; }
      body.saveShape = { id: asm.shapeId, title: asm.shapeTitle };
    }
    var btn = $("asm_create");
    btn.disabled = true;
    api("/api/assemble/create", body).then(function (res) {
      var id = res.created;
      toast(res.errors.length ? "warn" : "ok", (res.replaced ? "Saved " : "Created ") + id,
        res.generated.length + " entities generated" + (res.shape ? ", shape " + res.shape + " kept" : "")
        + (res.removed && res.removed.length ? "; no longer made: " + res.removed.join(", ") : "")
        + (res.errors.length ? "; " + res.errors.length + " error(s), see Validate" : ""));
      if (asm.cy) { asm.cy.destroy(); asm.cy = null; }
      asm = null;
      return refresh().then(function () {
        showPanel(false);
        state.subject = { product: id };
        selectView("product-architecture");
      });
    }).catch(function (err) {
      btn.disabled = false;
      fail(err);
    });
  }

  /* ---- help ---------------------------------------------------------------
   * One page that says what this is and how to read it, reachable from the
   * bar. The rule for the map lives here in words, next to the keys.
   */
  /* ---- the Help page ----------------------------------------------------
   * The first steps, the reading rules for a drawing with the swatches the
   * legend uses, and the tour. The steps were also a strip above the sheet
   * on a first visit; the tour shows them now, and the strip went.
   */
  //: Each step as a line, and as the Help page says it.
  var COACH = [
    ["Choose a view", "The list on the left has every diagram, grouped by layer.",
      "The list on the left has every diagram, grouped by layer: business, application, data, technology, governance and change. Each one is generated from the model."],
    ["Click any item", "The panel on the right shows its details, connections and source file.",
      "The panel on the right shows the item's properties, everything it is connected to, and the file it is defined in. Hover over an item to highlight its connections."],
    ["Check the impact", "Impact highlights everything affected if the selected item changes.",
      "With an item selected, press Impact to highlight everything that depends on it. Press Focus to redraw the diagram around that item alone."],
  ];

  function openGuide() {
    state.panel = "guide";
    showPanel(true);
    var panel = $("dataPanel");
    panel.textContent = "";
    panel.classList.remove("is-table");
    var g = el("div", { class: "guide" });
    g.appendChild(el("div", { class: "panel-head" }, [
      el("div", {}, [
        el("h1", { text: "How to use this app" }),
        el("p", { class: "sub", text:
          "Every diagram is generated from the model, so nothing here is drawn by hand. "
          + "Change the model and every diagram follows; change one diagram and only that one does." }),
      ]),
    ]));

    g.appendChild(el("h2", { class: "guide-h", text: "Getting started" }));
    var steps = el("ol", { class: "guide-steps" });
    COACH.forEach(function (step, i) {
      steps.appendChild(el("li", {}, [
        el("span", { class: "gs-n", text: String(i + 1) }),
        el("span", { class: "gs-t", text: step[0] }),
        el("p", { class: "gs-p", text: step[2] }),
      ]));
    });
    g.appendChild(steps);

    g.appendChild(el("h2", { class: "guide-h", text: "Reading a diagram" }));
    var rows = el("div", { class: "guide-rows" });
    function row(swatches, strong, rest) {
      rows.appendChild(el("div", { class: "gr-sw" }, swatches));
      rows.appendChild(el("p", { class: "gr-t" }, [el("b", { text: strong + " " }), rest]));
    }
    row([shapeKey("systems", "#c7d6ff", "#4338ca"), shapeKey("capabilities", "#ddd6fe", "#6d28d9"), shapeKey("data_assets", "#a7f3d0", "#047857")],
      "Color and shape", "show the type of item: system, capability, data asset, and so on. They are the same on every diagram.");
    row([shapeKey("systems", "#c7d6ff", "#4338ca", 2.6), shapeKey("systems", "#dbe4ff", "#4338ca", 1.6), shapeKey("systems", "#eef2ff", "#4338ca", 1.0)],
      "Shade and border weight", "show the attribute the view is colored by, such as criticality, strategic importance or status. The legend below the diagram lists the values.");
    row([boundaryKey({ fill: "#e7ebf6", stroke: "#9aa5b8", dash: "solid" })],
      "Boxes", "show how the view groups items: by business domain, cloud account, network zone or tier.");
    row([lineKey("solid"), lineKey("dashed"), lineKey("dotted")],
      "Line style", "shows the type of relationship: solid for calls, dashed for runs on, dotted for governed by.");
    row([el("span", { class: "gr-mark" })],
      "Corner icon", "shows the cloud provider or vendor. Items without one show a small symbol for the component type.");
    g.appendChild(rows);

    g.appendChild(el("h2", { class: "guide-h", text: "Changing a diagram" }));
    var changes = el("div", { class: "guide-rows guide-changes" });
    [["Change what something is", "Select it and press Edit: its name, owner, where it runs. Every diagram it is on changes with it."],
     ["Move something into another box", "Drag it into the box it belongs in. A box is one value of a field, such as a business domain, so this changes the item itself, and it moves on every diagram grouped that way. You are told which before anything is saved, and it can be undone."],
     ["Change what one diagram shows", "Right-click a box and choose Hide from this view, or press Add to this view on the diagram's summary. Only that diagram changes, and each change can be undone."],
     ["Connect two things", "Drag one box onto the other, or right-click one and choose Connect to. Only connections the model allows between those two kinds of thing are offered."],
     ["Change what a diagram is about", "Press Edit over the drawing: what it shows, how it groups and shades, which lines it draws. The drawing updates as you change it."],
     ["Change the colors", "Pick Stone or Graphite from the two swatches at the foot of the sidebar. The page and every drawing change together; your organization can change the drawing colors for everyone in model.yaml."]].forEach(function (c) {
      changes.appendChild(el("p", { class: "gr-t" }, [el("b", { text: c[0] + ". " }), c[1]]));
    });
    g.appendChild(changes);

    g.appendChild(el("h2", { class: "guide-h", text: "Keyboard shortcuts" }));
    var keys = el("div", { class: "guide-keys" });
    [["/", "Open the jump box: a view, a thing in the model or an action. Ctrl+K opens it too."], ["\u2190 \u2192 \u2191 \u2193", "Move between items on the diagram."],
     ["Enter", "Open the highlighted item."], ["Delete", "Hide the highlighted item from this diagram."],
     ["Shift+F10", "Open the highlighted item's menu."], ["Esc", "Clear the selection, or close a panel."]].forEach(function (k) {
      keys.appendChild(el("kbd", { text: k[0] }));
      keys.appendChild(el("span", { text: k[1] }));
    });
    g.appendChild(keys);

    g.appendChild(el("h2", { class: "guide-h", text: "Where the data comes from" }));
    g.appendChild(el("p", { class: "guide-p", text:
      "The business layer (capabilities, value streams, processes, policies and controls) is imported "
      + "from the business architecture repository. The technology estate (systems, interfaces, data and "
      + "technology services) is maintained here, as YAML files under 10_MODEL. The URL includes the "
      + "current view and selection, so a link opens the same diagram for someone else." }));
    // The tour, whenever: Home offers it once.
    if (tourPossible()) {
      g.appendChild(el("p", { class: "guide-p" }, [
        el("button", { class: "btn small", type: "button", text: "Take the tour",
          title: "Seven steps through the sample estate, with a pointer showing where to press",
          onclick: function (e) { startTour(e.currentTarget.getBoundingClientRect()); } }),
      ]));
    }
    panel.appendChild(g);
    syncUrl();
  }

  /* ---- the tour ------------------------------------------------------------
   * Seven steps through the sample estate, each pointing at one control: a
   * pointer travels to it, a ring settles around it, and a card beside it
   * says what to press and why. The person presses it and the tour moves on
   * when the app gets there; Show me presses it for them. It took the place
   * of a strip of three steps above the sheet, dismissed with Got it, which
   * said where to look and never showed it. Nothing dims or blocks the page
   * while it runs. Drawn as V11 in the design file.
   */
  //: "taken" or "off": either way the offer on Home is not made again.
  var TOUR_KEY = "aac.tour";
  //: Not now: the offer waits for the next visit.
  var TOUR_LATER = "aac.tour.later";
  var TOUR_VIEW = "system-context";
  var TOUR_BOX = "Card Servicing Web";
  var POINTER_PATH = "M1 1 L1 17.5 L5.2 13.6 L8 20 L10.8 18.8 L8.1 12.6 L13.8 12.6 Z";
  var tour = null;

  function tourStored() {
    try { return localStorage.getItem(TOUR_KEY) || ""; } catch (err) { return ""; }
  }
  function tourStore(value) {
    try { localStorage.setItem(TOUR_KEY, value); } catch (err) { /* private mode: offered again next visit */ }
  }

  // The tour reads the sample estate's own view and systems, so it is made
  // where they are, and where the sidebar it points at is shown at all.
  function tourPossible() {
    var o = state.overview || {};
    return !!(o.estate && o.estate.sample) && window.innerWidth > 860
      && (o.views || []).some(function (v) { return v.viewId === TOUR_VIEW && v.ok !== false; });
  }

  function tourOffered() {
    if (tour || tourStored() || !tourPossible()) return false;
    try { if (sessionStorage.getItem(TOUR_LATER)) return false; } catch (err) { /* none kept */ }
    return true;
  }

  function onTourDrawing() {
    return !state.panel && !cv && state.viewId === TOUR_VIEW && !!state.cy && !state.cy.destroyed() && !tilesShown();
  }

  // The box step 3 points at: the sample's Card Servicing Web, or if an
  // edited sample has lost it, the first system on the drawing.
  function tourBox() {
    if (!onTourDrawing()) return null;
    var leaves = state.cy.nodes().filter(function (n) { return !n.isParent() && !n.data("isGroup"); });
    var named = leaves.filter(function (n) { return String(n.data("label") || "").replace(/\s+/g, " ") === TOUR_BOX; });
    if (named.length) return named[0];
    var systems = leaves.filter(function (n) { return n.data("entityType") === "systems"; });
    return systems.length ? systems[0] : null;
  }
  function tourBoxName() {
    var n = tourBox();
    return n ? String(n.data("label") || "").replace(/\s+/g, " ") : TOUR_BOX;
  }

  function shownRect(node) {
    if (!node || node.offsetParent === null) return null;
    var r = node.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < window.innerHeight ? r : null;
  }
  function boxRect(n) {
    var bb = n.renderedBoundingBox({ includeLabels: false });
    var c = state.cy.container().getBoundingClientRect();
    return { left: c.left + bb.x1, top: c.top + bb.y1, width: bb.w, height: bb.h };
  }
  function impactButton() {
    return Array.prototype.filter.call(document.querySelectorAll("#inspBody .acts .btn"), function (b) {
      return b.textContent.trim() === "Impact" && b.offsetParent !== null;
    })[0] || null;
  }
  function newDiagramRow() {
    var menu = $("newMenu");
    if (!menu || menu.hidden) return null;
    return Array.prototype.filter.call(menu.querySelectorAll(".nm-row"), function (r) {
      var t = r.querySelector(".nm-title");
      return t && t.textContent.trim() === "Diagram";
    })[0] || null;
  }
  function tourCard() {
    return document.querySelector('#dataPanel .gcard[data-view="' + TOUR_VIEW + '"]');
  }
  function readOnlyCopy() { return !!window.__AAC_STATIC__; }

  // Each step: what the card says, the page it needs (`prepare`), where it
  // points, what the person does that moves it on, and what Show me does.
  var TOUR_STEPS = [
    { title: "Every diagram, by layer",
      body: function () { return "Press Diagrams in the sidebar. Each one is drawn from the same model, so a system changed once changes on all of them."; },
      prepare: function () { if (state.panel !== "start") openStart(); },
      target: function () { return shownRect($("btnDiagrams")); },
      done: function () { return state.panel === "diagrams"; },
      act: function () { $("btnDiagrams").click(); } },
    { title: "Open one",
      body: function () { return "Press System Context: the people who use the card platform, and the systems they reach it through."; },
      prepare: function () { if (state.panel !== "diagrams") openDiagrams("All"); },
      target: function () {
        var cards = document.querySelectorAll('#dataPanel .gcard[data-view="' + TOUR_VIEW + '"]');
        for (var i = 0; i < cards.length; i++) { var r = shownRect(cards[i]); if (r) return r; }
        return null;
      },
      done: onTourDrawing,
      act: function () { var c = tourCard(); if (c) c.click(); } },
    { title: "Press a box", side: "below",
      body: function () { return "Press " + tourBoxName() + ". What it is, what it connects to and the file it is written in open on the right."; },
      prepare: function () { if (!onTourDrawing()) selectView(TOUR_VIEW); },
      target: function () { var n = tourBox(); return n ? boxRect(n) : null; },
      done: function () { return onTourDrawing() && !!state.selectedId; },
      act: function () { var n = tourBox(); if (n) showEntity(n.id()); } },
    // Its card goes to the drawing's left, off the box the step is about:
    // beside Impact, it covered Card Servicing Web.
    { title: "What depends on it", side: "stage",
      avoid: function () { var n = tourBox(); return n ? boxRect(n) : null; },
      body: function () { return "Press Impact. Everything that would feel a change to " + tourBoxName() + " lights up, here and on every other diagram."; },
      prepare: function () { if (!onTourDrawing()) selectView(TOUR_VIEW); tour.wantSelect = true; },
      target: function () { return onTourDrawing() ? shownRect(impactButton()) : null; },
      done: function () { return !!state.impactShown; },
      act: function () { var b = impactButton(); if (b) b.click(); } },
    { title: "Move around", side: "left", noShowMe: true,
      body: function () { return "Scroll to zoom and drag to move. Whole drawing puts all of it on the sheet, and the small map shows where you are."; },
      prepare: function () { if (!onTourDrawing()) selectView(TOUR_VIEW); },
      target: function () { return onTourDrawing() ? shownRect(document.querySelector(".controls")) : null; },
      done: null },
    { title: "The model underneath",
      body: function () { return "Press Model: every record as a table. Each diagram is a view of these records, so a change here reaches all of them."; },
      prepare: function () {},
      target: function () { return shownRect($("btnData")); },
      done: function () { return state.panel === "data"; },
      act: function () { $("btnData").click(); } },
    { title: "Draw your own", next: "Finish",
      body: function () {
        return readOnlyCopy()
          ? "Press New to see what can be made: a diagram, a system, a connection, a flow. This copy only reads; in your own estate each one makes a record."
          : "Press New, then Diagram: place parts from the library, systems the estate already has, or whole diagrams as boundaries.";
      },
      prepare: function () {},
      target: function () { return shownRect(newDiagramRow()) || shownRect($("btnNew")); },
      done: function () { return readOnlyCopy() ? !$("newMenu").hidden : !!cv; },
      act: function () {
        if ($("newMenu").hidden) toggleNewMenu();
        if (!readOnlyCopy()) setTimeout(function () { var row = newDiagramRow(); if (row) row.click(); }, 450);
      } },
  ];
  var TOUR_END = { title: "That is the tour", end: true,
    body: function () {
      return "Everything you saw is one model: change a system once and every diagram it is on follows. "
        + (readOnlyCopy() ? "" : "Start your own estate when you are ready. ")
        + "The tour is under Help whenever you want it again.";
    },
    prepare: function () {},
    target: function () { return shownRect($("btnHelp")); },
    done: null };

  function startTour(from) {
    if (!tourPossible()) {
      toast("warn", "The tour needs the sample estate", "and a window wide enough to show the sidebar");
      return;
    }
    if (tour) endTour(true);
    tourStore("taken");
    closeNewMenu();
    var pointer = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    pointer.setAttribute("class", "tour-pointer");
    pointer.setAttribute("viewBox", "0 0 15 21");
    pointer.setAttribute("aria-hidden", "true");
    var path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", POINTER_PATH);
    pointer.appendChild(path);
    var ring = el("div", { class: "tour-ring", "aria-hidden": "true" });
    var card = el("div", { class: "tour-card", role: "dialog", "aria-label": "Tour", "aria-live": "polite" });
    document.body.appendChild(ring);
    document.body.appendChild(pointer);
    document.body.appendChild(card);
    var start = from ? { x: from.left + from.width / 2, y: from.top + from.height / 2 }
      : { x: window.innerWidth / 2, y: window.innerHeight / 2 };
    tour = { step: -1, pointer: pointer, ring: ring, card: card, at: start, rect: "", timer: setInterval(tourTick, 150) };
    setPointer(start);
    tourGo(0);
  }

  function endTour(quietly) {
    if (!tour) return;
    clearInterval(tour.timer);
    [tour.pointer, tour.ring, tour.card].forEach(function (n) { if (n.parentNode) n.parentNode.removeChild(n); });
    tour = null;
    if (!quietly) toast("ok", "Tour ended", "Help has it again, whenever you want it");
  }

  function tourGo(i) {
    if (!tour) return;
    if (i < 0) i = 0;
    tour.step = i;
    var s = TOUR_STEPS[i] || TOUR_END;
    // The read-only copy's last step opens the New menu and leaves it open,
    // under the end card.
    if (s.end) closeNewMenu();
    // Every step but the end points at the sidebar or past it, and a hidden
    // sidebar is the one thing the tour opens itself.
    if (document.querySelector(".shell").classList.contains("rail-shut")) $("btnRail").click();
    tour.wantSelect = false;
    tour.since = Date.now();
    s.prepare();
    // A step already done when it is reached (Back to it, say) waits for
    // Next; one done after is the person's doing, and moves on.
    tour.wasDone = s.done ? !!s.done() : false;
    tour.travel = true;
    tour.rect = "";
    renderTourCard(s);
    tourTick();
  }

  function renderTourCard(s) {
    var card = tour.card, i = tour.step, n = TOUR_STEPS.length;
    card.textContent = "";
    var close = el("button", { class: "tc-close", type: "button", "aria-label": "End the tour", title: "End the tour (Esc)", text: "\u00d7",
      onclick: function () { endTour(); } });
    card.appendChild(el("div", { class: "tc-top" }, [
      el("span", { class: "tc-step", text: s.end ? "Tour done" : "Step " + (i + 1) + " of " + n }), close]));
    card.appendChild(el("h2", { class: "tc-title", text: s.title }));
    card.appendChild(el("p", { class: "tc-body", text: s.body() }));
    var away = el("p", { class: "tc-away", text: "This step is on another page." });
    away.appendChild(el("button", { class: "tc-link", type: "button", text: "Take me there",
      onclick: function () { tour.since = Date.now(); s.prepare(); } }));
    away.hidden = true;
    card.appendChild(away);
    var dots = el("span", { class: "tc-dots", "aria-hidden": "true" });
    if (!s.end) TOUR_STEPS.forEach(function (x, j) { dots.appendChild(el("i", { class: j === i ? "is-on" : (j < i ? "is-past" : "") })); });
    var btns = el("span", { class: "tc-btns" });
    if (s.end) {
      btns.appendChild(el("button", { class: "btn small ghost", type: "button", text: "Keep exploring", onclick: function () { endTour(true); } }));
      if (!readOnlyCopy()) {
        btns.appendChild(el("button", { class: "btn small primary", type: "button", text: "Start your own estate",
          onclick: function () { endTour(true); openProject("start"); } }));
      }
    } else {
      if (i > 0) btns.appendChild(el("button", { class: "btn small ghost", type: "button", text: "Back", onclick: function () { tourGo(i - 1); } }));
      if (!s.noShowMe) btns.appendChild(el("button", { class: "btn small", type: "button", text: "Show me", onclick: showMe }));
      btns.appendChild(el("button", { class: "btn small primary", type: "button", text: s.next || "Next", onclick: function () { tourGo(i + 1); } }));
    }
    card.appendChild(el("div", { class: "tc-foot" }, [dots, btns]));
    var first = btns.querySelector(".primary");
    if (first) first.focus({ preventScroll: true });
  }

  // Show me: the pointer presses the control, and the app does what the
  // press does.
  function showMe() {
    var s = TOUR_STEPS[tour.step];
    if (!s || !s.act) return;
    var at = tour.at;
    if (!REDUCED.matches) {
      var press = el("div", { class: "tour-press", style: "left:" + at.x + "px;top:" + at.y + "px" });
      document.body.appendChild(press);
      press.animate([{ transform: "scale(0.4)", opacity: 0.9 }, { transform: "scale(1.4)", opacity: 0 }], { duration: 420, easing: "ease-out" })
        .onfinish = function () { if (press.parentNode) press.parentNode.removeChild(press); };
      tour.pointer.animate([{ transform: pointerAt(at) }, { transform: pointerAt(at) + " scale(0.86)" }, { transform: pointerAt(at) }], { duration: 240 });
    }
    setTimeout(function () { if (tour) s.act(); }, REDUCED.matches ? 0 : 200);
  }

  function pointerAt(p) { return "translate(" + (p.x - 1.5) + "px," + (p.y - 1.5) + "px)"; }
  function setPointer(p) { tour.pointer.style.transform = pointerAt(p); tour.at = p; }

  // The pointer travels on a gentle curve, 700 ms, and rests just inside
  // the control, not over its words.
  function travel(to) {
    var from = tour.at;
    var dx = to.x - from.x, dy = to.y - from.y, len = Math.sqrt(dx * dx + dy * dy);
    if (REDUCED.matches || len < 4) { setPointer(to); return; }
    var c = { x: (from.x + to.x) / 2 - dy * 0.18, y: (from.y + to.y) / 2 + dx * 0.18 };
    var frames = [];
    for (var k = 0; k <= 12; k++) {
      var t = k / 12, u = 1 - t;
      frames.push({ transform: pointerAt({ x: u * u * from.x + 2 * u * t * c.x + t * t * to.x, y: u * u * from.y + 2 * u * t * c.y + t * t * to.y }) });
    }
    setPointer(to);
    tour.pointer.animate(frames, { duration: 700, easing: "ease-in-out" });
  }

  function tourTick() {
    if (!tour) return;
    var s = TOUR_STEPS[tour.step] || TOUR_END;
    if (tour.wantSelect && onTourDrawing()) {
      var box = tourBox();
      if (box) { tour.wantSelect = false; if (!state.selectedId) showEntity(box.id()); }
    }
    if (s.done) {
      var done = !!s.done();
      if (done && !tour.wasDone && !tour.moving) {
        tour.moving = true;
        setTimeout(function () { if (tour) { tour.moving = false; tourGo(tour.step + 1); } }, 450);
      }
      if (!done) tour.wasDone = false;
    }
    var r = s.target();
    var away = tour.card.querySelector(".tc-away");
    if (!r) {
      tour.ring.hidden = true;
      // Pages draw a moment after they open; only after that is a missing
      // control the person having gone somewhere else.
      if (away) away.hidden = Date.now() - tour.since < 2500;
      if (tour.rect !== "away") { tour.rect = "away"; placeTourCard(null, s); }
      return;
    }
    if (away) away.hidden = true;
    var key = [r.left, r.top, r.width, r.height].map(Math.round).join(",");
    if (key === tour.rect) return;
    tour.rect = key;
    tour.ring.hidden = false;
    tour.ring.style.left = (r.left - 3) + "px";
    tour.ring.style.top = (r.top - 3) + "px";
    tour.ring.style.width = (r.width + 6) + "px";
    tour.ring.style.height = (r.height + 6) + "px";
    var point = { x: r.left + Math.min(r.width * 0.5, 110), y: r.top + r.height * 0.6 };
    if (tour.travel) { tour.travel = false; travel(point); } else setPointer(point);
    placeTourCard(r, s);
  }

  // Beside the control on the side the step asks for, else the first side
  // with room, never over the control itself or what the step says to keep
  // in sight.
  function placeTourCard(r, s) {
    var card = tour.card, W = card.offsetWidth, H = card.offsetHeight, vw = window.innerWidth, vh = window.innerHeight, g = 16, m = 8;
    var stage = document.querySelector(".stage").getBoundingClientRect();
    var keep = [r, s.avoid ? s.avoid() : null].filter(Boolean);
    var x, y;
    if (!r) {
      x = stage.left + stage.width / 2 - W / 2; y = vh - H - 88;
    } else {
      var spots = {
        right: [r.left + r.width + g, r.top - 8],
        left: [r.left - W - g, r.top - 8],
        below: [r.left + r.width / 2 - W * 0.75, r.top + r.height + g],
        above: [r.left + r.width / 2 - W / 2, r.top - H - g],
        stage: [stage.left + 40, r.top - 8],
      };
      var order = [s.side || "right", "right", "left", "below", "above"];
      var pick = null;
      for (var k = 0; k < order.length && !pick; k++) {
        var p = spots[order[k]];
        var px = Math.max(m, Math.min(vw - W - m, p[0])), py = Math.max(m, Math.min(vh - H - m, p[1]));
        var clear = keep.every(function (q) {
          return px + W <= q.left - 4 || px >= q.left + q.width + 4 || py + H <= q.top - 4 || py >= q.top + q.height + 4;
        });
        if (clear) pick = [px, py];
      }
      if (!pick) pick = [m, vh - H - m];
      x = pick[0]; y = pick[1];
    }
    card.style.left = Math.round(x) + "px";
    card.style.top = Math.round(y) + "px";
  }

  // The offer, once, on Home: Start, Not now (this visit), or never.
  function tourOffer(panel) {
    if (!tourOffered()) return;
    var start = el("button", { class: "btn small primary", type: "button", text: "Start the tour" });
    var box;
    function gone() { if (box && box.parentNode) box.parentNode.removeChild(box); window.removeEventListener("resize", place); }
    function later() { try { sessionStorage.setItem(TOUR_LATER, "1"); } catch (err) { /* none kept */ } gone(); }
    function place() {
      // Home redrawn or left: the offer went with the page.
      if (!box.parentNode) { window.removeEventListener("resize", place); return; }
      var stage = document.querySelector(".stage").getBoundingClientRect();
      box.style.left = Math.round(stage.left + stage.width / 2 - box.offsetWidth / 2) + "px";
    }
    box = el("div", { class: "tour-card tour-offer", role: "dialog", "aria-label": "A tour of the sample estate" }, [
      el("div", { class: "tc-top" }, [
        el("span", { class: "tc-step", text: "New here?" }),
        el("button", { class: "tc-close", type: "button", "aria-label": "Not now", title: "Not now", text: "\u00d7", onclick: later }),
      ]),
      el("h2", { class: "tc-title", text: "A two-minute tour of the sample estate" }),
      el("p", { class: "tc-body", text: "A pointer shows you where to press, one step at a time: open a diagram, read a system, "
        + "see what depends on it, and draw your own. You can stop at any step." }),
      el("div", { class: "tc-foot" }, [
        el("button", { class: "tc-link", type: "button", text: "Don't offer this again", onclick: function () {
          tourStore("off");
          gone();
          toast("ok", "The tour will not be offered again", "Help has it, whenever you want it");
        } }),
        el("span", { class: "tc-btns" }, [
          el("button", { class: "btn small ghost", type: "button", text: "Not now", onclick: later }),
          start,
        ]),
      ]),
    ]);
    start.addEventListener("click", function () { var r = start.getBoundingClientRect(); gone(); startTour(r); });
    panel.appendChild(box);
    place();
    window.addEventListener("resize", place);
  }

  /* ---- flows -----------------------------------------------------------
   * A flowchart shows what connects to what; a sequence diagram shows what
   * happens in what order. Different question, so a different renderer.
   */

  function svgEl(tag, attrs, kids) {
    var node = document.createElementNS("http://www.w3.org/2000/svg", tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === "text") node.textContent = attrs[k];
      else if (k.slice(0, 2) === "on") node.addEventListener(k.slice(2), attrs[k]);
      else node.setAttribute(k, attrs[k]);
    });
    (kids || []).forEach(function (kid) { if (kid) node.appendChild(kid); });
    return node;
  }

  /* A flow as a sequence: a column per participant in order of first
   * appearance, a lifeline under each, an activation bar while a system is
   * busy, and a numbered arrow per step with its protocol on it. Drawn from
   * the steps the model records, not from the Mermaid the renderer writes,
   * so the two cannot disagree about a step; drawn in the house style of the
   * pictures (paper heads with an offset shadow on a dotted plate), with the
   * heads in the systems' swatch of the tone. Names are written whole and
   * wrap: "NICE Actimize Screening Integration Gateway" cut to its first
   * twenty-three characters named nothing. */
  function sequenceSvg(flow, swatch) {
    var parts = [], seen = {};
    flow.steps.forEach(function (s) {
      [[s.fromId, s.from], [s.toId, s.to]].forEach(function (p) {
        if (!seen[p[0]]) { seen[p[0]] = true; parts.push({ id: p[0], name: p[1] }); }
      });
    });
    var colW = 160, boxW = 136, top = 18, pad = 12;
    var lines = parts.map(function (p) { return wrapWords(p.name, 21); });
    var boxH = Math.max(40, 14 + 14 * Math.max.apply(null, lines.map(function (l) { return l.length; }).concat([1])));
    var firstY = top + boxH + 50, dy = 42;
    var width = pad * 2 + Math.max(1, parts.length) * colW;
    var height = firstY + flow.steps.length * dy + 28;
    var svg = svgEl("svg", { class: "seq", viewBox: "0 0 " + width + " " + height, width: width, height: height,
      role: "img", "aria-label": flow.name + ", " + flow.steps.length + " " + plural(flow.steps.length, "step") });
    svg.appendChild(svgEl("rect", { class: "dots", width: width, height: height }));
    var xOf = {}, first = {}, last = {};
    parts.forEach(function (p, i) { xOf[p.id] = pad + i * colW + colW / 2; });
    flow.steps.forEach(function (s, i) {
      [s.fromId, s.toId].forEach(function (id) {
        if (first[id] === undefined) first[id] = i;
        last[id] = i;
      });
    });
    parts.forEach(function (p) {
      svg.appendChild(svgEl("line", { class: "life", x1: xOf[p.id], y1: top + boxH + 6, x2: xOf[p.id], y2: height - 10 }));
    });
    // A system is busy from the first step it is in to the last.
    parts.forEach(function (p) {
      var y0 = firstY + first[p.id] * dy - 14, y1 = firstY + last[p.id] * dy + 14;
      svg.appendChild(svgEl("rect", { class: "act", x: xOf[p.id] - 5, y: y0, width: 10, height: y1 - y0, rx: 2 }));
    });
    parts.forEach(function (p, i) {
      var x = xOf[p.id];
      var g = svgEl("g", { class: "seq-part", tabindex: "0", role: "button",
        onclick: function () { goToEntity(p.id); },
        onkeydown: function (e) { if (e.key === "Enter") goToEntity(p.id); } });
      g.appendChild(svgEl("rect", { class: "shade", x: x - boxW / 2 + 3, y: top + 3, width: boxW, height: boxH, rx: 4 }));
      g.appendChild(svgEl("rect", { class: "head", x: x - boxW / 2, y: top, width: boxW, height: boxH, rx: 4,
        fill: swatch ? swatch.fill : "#ffffff", stroke: swatch ? swatch.stroke : "#1f2023" }));
      var t = svgEl("text", { class: "head-name", x: x, "text-anchor": "middle", fill: swatch ? swatch.ink : "#1f2023" });
      var y0 = top + boxH / 2 - (lines[i].length - 1) * 7 + 4;
      lines[i].forEach(function (line, k) {
        t.appendChild(svgEl("tspan", { x: x, y: y0 + k * 14, text: line }));
      });
      g.appendChild(t);
      g.appendChild(svgEl("title", { text: p.name }));
      svg.appendChild(g);
    });
    flow.steps.forEach(function (s, i) {
      var y = firstY + i * dy;
      var x1 = xOf[s.fromId], x2 = xOf[s.toId];
      var dashed = s.style && s.style !== "Request-response";
      var self = x1 === x2;
      var dir = x2 >= x1 ? 1 : -1;
      var from = x1 + dir * 5, tip = self ? x1 + 40 : x2 - dir * 5;
      svg.appendChild(svgEl("path", { class: "msg" + (dashed ? " async" : ""),
        d: self ? "M" + (x1 + 5) + " " + (y - 8) + "H" + (x1 + 40) + "V" + y + "H" + (x1 + 12)
          : "M" + from + " " + y + "H" + (tip - dir * 6) }));
      svg.appendChild(svgEl("path", { class: "tip",
        d: self ? "M" + (x1 + 5) + " " + y + "l8 -4.5v9z" : "M" + tip + " " + y + "l" + (-dir * 8) + " -4.5v9z" }));
      var left = Math.min(from, tip) + 10;
      svg.appendChild(svgEl("circle", { class: "num", cx: left + 8, cy: y - 14, r: 8.5 }));
      svg.appendChild(svgEl("text", { class: "num-t", x: left + 8, y: y - 10.5, "text-anchor": "middle", text: String(i + 1) }));
      var words = (s.protocol || "") + (dashed ? (s.protocol ? " · " : "") + String(s.style).toLowerCase() : "");
      if (words) svg.appendChild(svgEl("text", { class: "how", x: left + 22, y: y - 10, text: words }));
    });
    return svg;
  }

  //: A name broken into lines of about `width` characters at its spaces.
  function wrapWords(text, width) {
    var out = [], line = "";
    String(text || "").split(/\s+/).forEach(function (word) {
      if (line && (line + " " + word).length > width) { out.push(line); line = word; }
      else line = line ? line + " " + word : word;
    });
    if (line) out.push(line);
    return out.length ? out : [""];
  }

  /* Flows: what a flow is, in a line, and the button that makes one; the
   * flows on the left, the one chosen drawn as a sequence on the right with
   * its steps under it. The page used to open on a back link and say
   * "hops" without saying what a flow was, and offered no way to add one. */
  function openFlows(flowId) {
    api("/api/flows").then(function (d) {
      state.panel = "flows";
      showPanel(true);
      var panel = $("dataPanel");
      panel.textContent = "";
      panel.classList.remove("is-table");
      var readOnly = !!window.__AAC_STATIC__;
      var flows = d.flows || [];
      var current = flows.filter(function (f) { return f.id === flowId; })[0] || flows[0];
      state.flowId = current ? current.id : null;
      panel.appendChild(el("div", { class: "flows-head" }, [
        el("div", {}, [
          el("p", { class: "crumb" }, [
            el("button", { type: "button", text: "Diagrams", onclick: function () { openDiagrams("All"); } }),
            el("span", { class: "sep", text: "/" }),
            el("span", { text: "Flows" }),
          ]),
          el("h1", { text: "Flows" }),
          el("p", { class: "lede", text:
            "A flow follows one business transaction, such as a card payment or a loan application, through the "
            + "systems it touches, one step for each connection it crosses. Each step is a connection already in "
            + "the model, so a flow stays true when the systems change." }),
        ]),
        el("button", { class: "btn primary", type: "button", disabled: readOnly ? "disabled" : null,
          title: "A flow is named first; its steps are the connections it crosses, added after",
          onclick: function () { openEntityEditor("flows", null, null, function () { openFlows(); }); } },
          [svgIcon("i-plus"), el("span", { text: "New flow" })]),
      ]));
      if (!flows.length) {
        panel.appendChild(el("p", { class: "brief-hint", text:
          "No flows yet. Make one with New flow: name it, then add its steps, each a connection between two "
          + "systems that the model already records." }));
        syncUrl();
        return;
      }
      var list = el("div", { class: "flows-list" });
      flows.forEach(function (f) {
        var meta = [f.steps.length + " " + plural(f.steps.length, "step")];
        if (f.criticality) meta.push(String(f.criticality).toLowerCase() + " criticality");
        list.appendChild(el("button", { class: "flow-pick" + (current && f.id === current.id ? " is-on" : ""),
          type: "button", onclick: function () { openFlows(f.id); } }, [
          el("span", { class: "fp-name", text: f.name }),
          el("span", { class: "fp-meta", text: meta.join("  ·  ") }),
        ]));
      });
      var stage = el("div", { class: "flows-stage" });
      panel.appendChild(el("div", { class: "flows-cols" }, [list, stage]));
      if (current) {
        stage.appendChild(el("div", { class: "flow-top" }, [
          el("div", {}, [
            el("h2", { text: current.name }),
            current.description ? el("p", { class: "flow-desc", text: current.description }) : null,
          ]),
          el("div", { class: "acts" }, [
            el("button", { class: "btn small", type: "button", disabled: readOnly ? "disabled" : null,
              title: "Add or remove the connections this flow crosses",
              onclick: function () { openLinkEditor(current.id); } }, [svgIcon("i-pencil"), el("span", { text: "Edit steps" })]),
            el("button", { class: "btn small", type: "button", title: "The sequence as an SVG file",
              onclick: function () { downloadSvg(stage.querySelector("svg.seq"), current.id + ".svg"); } },
              [svgIcon("i-download"), el("span", { text: "Export" })]),
          ]),
        ]));
        stage.appendChild(el("div", { class: "flow-sheet" }, [sequenceSvg(current, d.swatch)]));
        var steps = el("ol", { class: "flow-steps" });
        current.steps.forEach(function (s, i) {
          steps.appendChild(el("li", {}, [
            el("span", { class: "n num", text: String(i + 1) }),
            el("span", {}, [
              el("button", { type: "button", class: "hop", onclick: function () { goToEntity(s.fromId); }, text: s.from }),
              el("span", { class: "arrow", "aria-hidden": "true", text: s.style && s.style !== "Request-response" ? "⇢" : "→" }),
              el("button", { type: "button", class: "hop", onclick: function () { goToEntity(s.toId); }, text: s.to }),
            ]),
            el("span", { class: "proto", text: s.protocol || "" }),
          ]));
        });
        stage.appendChild(el("h3", { class: "flow-steps-h", text: "Steps" }));
        stage.appendChild(steps);
        if (current.target) stage.appendChild(el("p", { class: "brief-hint", text: "Target: " + current.target + "." }));
      }
      renderViewList(state.overview);
      syncUrl();
    }).catch(fail);
  }

  /* The sequence as a file, with the tone's colors written into it: a
   * picture that leaves the page cannot read the page's stylesheet. */
  function downloadSvg(svg, name) {
    if (!svg) return;
    var copy = svg.cloneNode(true);
    copy.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    var live = svg.querySelectorAll("*"), out = copy.querySelectorAll("*");
    ["fill", "stroke", "stroke-width", "stroke-dasharray", "font-family", "font-size", "font-weight"].forEach(function (prop) {
      for (var i = 0; i < live.length; i++) {
        var value = window.getComputedStyle(live[i]).getPropertyValue(prop);
        if (value) out[i].setAttribute(prop, value);
      }
    });
    copy.querySelectorAll("rect.dots").forEach(function (r) { r.setAttribute("fill", window.getComputedStyle(document.documentElement).getPropertyValue("--illo-plate").trim()); });
    var blob = new Blob([new XMLSerializer().serializeToString(copy)], { type: "image/svg+xml" });
    var a = el("a", { href: URL.createObjectURL(blob), download: name });
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 0);
  }

  // ---- the New menu -------------------------------------------------------

  /* Everything that can be made, in one list over the page: the three
   * buttons that each made something different (New, the + by Views, and
   * New product on the home page) are this one menu now. */
  var NEW_ITEMS = [
    ["i-grid", "Diagram", "Draw it: place parts from the library and what the estate already has.",
      function () { openCanvas(null); }],
    ["i-app-window", "System", "An application or service, with its owner and where it runs.",
      function () { openEntityEditor("systems", null, null); }],
    ["i-arrows", "Connection", "An interface between two systems, and what crosses it.",
      function () { openEntityEditor("interfaces", null, null); }],
    ["i-link", "API or topic", "What a system offers for others to connect to: an API, a topic, a file drop.",
      function () { openEntityEditor("offered_interfaces", null, null); }],
    ["i-route", "Flow", "One business transaction, traced across systems step by step.",
      function () { openEntityEditor("flows", null, null, function () { openFlows(); }); }],
    ["i-package", "Product", "Built from library parts, or placed on a shape.",
      function () { openArchetypePicker(); }],
    null,
    ["i-upload", "Import", "Records from a CSV or Excel export: a portfolio, an inventory, a CMDB extract.",
      function () { openSettings("sources"); }],
  ];

  function closeNewMenu() {
    var menu = $("newMenu");
    if (!menu || menu.hidden) return;
    menu.hidden = true;
    $("btnNew").setAttribute("aria-expanded", "false");
  }

  function toggleNewMenu() {
    var menu = $("newMenu"), btn = $("btnNew");
    if (!menu.hidden) { closeNewMenu(); return; }
    var readOnly = !!window.__AAC_STATIC__;
    menu.textContent = "";
    NEW_ITEMS.forEach(function (item) {
      if (!item) { menu.appendChild(el("div", { class: "nm-rule", role: "separator" })); return; }
      // The read-only copy can open a product's shapes to read them; the
      // rest write, and say so rather than failing after a form is filled.
      var writes = item[1] !== "Product";
      menu.appendChild(el("button", { class: "nm-row", type: "button", role: "menuitem",
        disabled: readOnly && writes ? "disabled" : null,
        onclick: function () { closeNewMenu(); item[3](); } }, [
        el("span", { class: "nm-icon" }, [svgIcon(item[0])]),
        el("span", { class: "nm-text" }, [
          el("span", { class: "nm-title", text: item[1] }),
          el("span", { class: "nm-desc", text: item[2] }),
        ]),
      ]));
    });
    menu.hidden = false;
    var r = btn.getBoundingClientRect();
    menu.style.left = Math.round(r.left) + "px";
    menu.style.top = Math.round(Math.max(8, r.top - menu.offsetHeight - 10)) + "px";
    btn.setAttribute("aria-expanded", "true");
    var first = menu.querySelector(".nm-row:not([disabled])");
    if (first) first.focus();
  }

  /* ---- the archetype editor ---------------------------------------------
   * An archetype is what makes onboarding a product a small edit rather than
   * a new diagram, which makes it the most valuable file in the repository.
   * Leaving it editable only in a text editor put the best part of the method
   * out of reach of the people the app is for.
   */

  /* ---- entity source ----------------------------------------------------
   * A form can only offer what the schema knows about. The file can carry a
   * comment explaining why a field is what it is, which is often the most
   * useful thing in it, so the file is editable too.
   */

  function openEntitySource(entityId) {
    api("/api/entity/source?id=" + encodeURIComponent(entityId)).then(function (d) {
      var area;
      openDrawer("Edit YAML", d.path, function (body) {
        $("drawer").classList.add("wide");
        body.appendChild(el("p", { class: "explain", text: d.editable
          ? "Written back exactly as you leave it, comments and all. The model is "
            + "loaded again afterward; if that fails the file goes back as it was."
          : d.why }));

        area = el("textarea", {
          class: "code-area mono", spellcheck: "false", autocomplete: "off",
          "aria-label": "Entity source",
        });
        area.value = d.text;
        area.readOnly = !d.editable;
        area.addEventListener("keydown", codeTab);
        body.appendChild(area);
      }, !d.editable ? null : function () {
        return api("/api/entity/source/save", { id: entityId, text: area.value })
          .then(function (res) {
            toast(res.errors.length ? "warn" : "ok", "Saved " + entityId,
              res.errors.length ? res.errors[0] : res.path);
            refresh();
            showEntity(entityId);
            return true;
          });
      });
    }).catch(fail);
  }

  /* `initialText`, when given, replaces the starter: the composer hands its
   * text here so preview and save are the editor's, not a second copy. */
  function openArchetypeEditor(archetypeId, initialText) {
    var q = archetypeId ? "?id=" + encodeURIComponent(archetypeId) : "";
    api("/api/archetype" + q).then(function (d) {
      var readOnly = !!window.__AAC_STATIC__;
      var area, status, result;
      if (initialText && d.isNew) {
        d.text = initialText;
        var idLine = /^archetype_id:\s*(\S+)/m.exec(initialText);
        if (idLine) d.path = "20_ARCHETYPES/" + idLine[1] + ".yaml";
      }

      openDrawer(readOnly ? "Archetype source" : d.isNew ? "New archetype" : "Edit archetype", d.path, function (body) {
        $("drawer").classList.add("wide");

        body.appendChild(el("p", { class: "explain", text: d.isNew
          ? "A shape, plus the answers it needs. Instantiating it creates every system, "
            + "interface and relation in one edit, which is the whole point: a new product "
            + "should be a handful of parameters, not a new diagram."
          : "Editing this shape re-expands every instance of it. Preview shows what one "
            + "instance would create before anything is written." }));

        if (d.instances.length) {
          body.appendChild(el("p", { class: "brief-hint", text:
            "Instantiated by " + d.instances.join(", ") + ". Saving regenerates what "
            + "those produce." }));
        }

        area = el("textarea", {
          class: "code-area mono", spellcheck: "false", autocomplete: "off",
          "aria-label": "Archetype source",
        });
        area.value = d.text;
        area.readOnly = readOnly;
        area.addEventListener("keydown", codeTab);

        status = el("p", { class: "editor-status", text: readOnly
          ? "The hosted demo is read-only. This is the file as committed."
          : "Not previewed yet." });
        result = el("div", { class: "produces" });

        var acts = el("div", { class: "editor-acts" });
        if (!readOnly) {
          acts.appendChild(el("button", {
            class: "btn small", type: "button", text: "Preview",
            title: "What one instance would create",
            onclick: function () { previewArchetype(); },
          }));
          if (!d.isNew) {
            acts.appendChild(el("button", {
              class: "btn small danger", type: "button", text: "Delete archetype",
              onclick: function () {
                if (!window.confirm("Delete the archetype " + d.id + "?")) return;
                api("/api/archetype/delete", { id: d.id }).then(function (res) {
                  toast("ok", "Deleted " + d.id, res.restored
                    ? res.path + "; the one in " + res.restored + " is read again" : res.path);
                  closeDrawer();
                  refresh();
                }).catch(fail);
              },
            }));
          }
        }

        var help = el("div", { class: "editor-help" });
        help.appendChild(helpList("Entity types", d.help.types, "provides"));
        help.appendChild(helpList("Relations", d.help.relations, "relations"));
        help.appendChild(helpDefs("Placeholder filters", d.help.filters, "{name|filter}"));
        if (d.help.shapeKeys) {
          help.appendChild(helpDefs("Shape keys", d.help.shapeKeys, "on the archetype"));
        }
        help.appendChild(helpDefs("Per-instance keys", d.help.instanceKeys, "on the instance"));

        body.appendChild(el("div", { class: "editor-grid" }, [
          el("div", { class: "editor-main" }, [area, status, result, acts]),
          help,
        ]));

        function previewArchetype() {
          status.className = "editor-status";
          status.textContent = "Expanding\u2026";
          result.textContent = "";
          api("/api/archetype/preview", { text: area.value }).then(function (d2) {
            status.className = "editor-status is-ok";
            status.textContent = "One instance creates " + d2.counts.entities +
              " entities and " + d2.counts.relations + " relations. Nothing saved yet.";
            var list = el("ul", { class: "produces-list" });
            d2.produces.forEach(function (p) {
              list.appendChild(el("li", {}, [
                el("code", { class: "help-chip", text: p.type }),
                el("span", { class: "mono", text: p.id }),
                el("span", { class: "produces-name", text: p.name }),
              ]));
            });
            result.appendChild(el("p", { class: "group-title", text: "It produces" }));
            result.appendChild(list);
          }).catch(function (err) {
            status.className = "editor-status is-bad";
            status.textContent = err.message;
          });
        }
      }, readOnly ? null : function () {
        return api("/api/archetype/save", { id: d.isNew ? "" : d.id, text: area.value })
          .then(function (res) {
            toast(res.errors.length ? "warn" : "ok",
              (res.created ? "Created " : "Saved ") + res.id,
              res.errors.length ? res.errors[0]
                : res.instances.length
                  ? res.generated + " entities regenerated for " + res.instances.join(", ")
                  : res.path);
            return refresh().then(function () { return true; });
          });
      });
    }).catch(fail);
  }

  function helpDefs(title, items, where) {
    var box = el("details", { class: "help-box" }, [
      el("summary", {}, [
        el("span", { text: title }),
        el("span", { class: "help-where mono", text: where }),
      ]),
    ]);
    var list = el("dl", { class: "help-ops" });
    items.forEach(function (item) {
      list.appendChild(el("dt", { class: "mono", text: item.name }));
      list.appendChild(el("dd", { text: item.note }));
    });
    box.appendChild(list);
    return box;
  }

  // Tab indents rather than leaving the field: YAML without indentation is not
  // YAML, and every code box here needs the same behavior.
  function codeTab(e) {
    if (e.key !== "Tab" || e.ctrlKey || e.altKey || e.metaKey) return;
    var area = e.target;
    e.preventDefault();
    var start = area.selectionStart, end = area.selectionEnd;
    area.value = area.value.slice(0, start) + "  " + area.value.slice(end);
    area.selectionStart = area.selectionEnd = start + 2;
  }

  /* A parameter that names a kind: its own description, then the kind and
   * what the shape binds it to, as sentences. Run together, "the event
   * stream the worker consumes from A event stream; the shape binds ..." was
   * what the form said. */
  function kindHint(description, p) {
    var lead = description ? description.replace(/[.\s]+$/, "") + ". " : "";
    var binds = p.bound ? "the shape binds " + p.bound
      : p.gap ? p.gap : "the shape binds none";
    return lead + "Of kind " + p.component.replace(/-/g, " ") + "; " + binds + ".";
  }

  function openArchetypePicker() {
    var readOnly = !!window.__AAC_STATIC__;
    openDrawer(readOnly ? "Archetypes" : "New", "", function (body) {
      body.appendChild(el("p", { class: "explain", text: readOnly
        ? "An archetype builds a whole product from a handful of answers: the systems, "
          + "the interfaces between them, where they run, and what they consume. "
          + "Instantiating one writes to the model, so that runs in the local app; "
          + "the shapes themselves are here to read."
        : "A product is assembled from parts of the library, or built from a shape, which is "
          + "a saved choice of parts. Either way the diagram is chosen, not drawn." }));
      if (!readOnly) {
        body.appendChild(el("button", { class: "pick is-lead", type: "button", "aria-label": "Assemble a product from parts",
          onclick: function () { closeDrawer(); openAssemble(null); } }, [
          el("div", { class: "top" }, [
            el("span", { class: "t", text: "Assemble a product from parts" }),
            el("span", { class: "n", text: (state.overview.modules || []).length ? (state.overview.modules.length + " chunks") : "" }),
          ]),
          el("p", { class: "d", text:
            "Pick the parts, watch the diagram they make, rename and drop and override, and write "
            + "one file. Start from nothing or from a shape." }),
        ]));
        body.appendChild(el("p", { class: "group-title", text: "Or from a shape" }));
      }
      state.overview.archetypes.forEach(function (a) {
        // The card holds a paragraph, and a button with block content gets no
        // accessible name; the shape's title is the name.
        var pick = el("button", { class: "pick", type: "button", "aria-label": a.title,
          onclick: function () {
            if (readOnly) { openArchetypeEditor(a.id); return; }
            openInstantiate(a);
          } }, [
          el("div", { class: "top" }, [
            el("span", { class: "t", text: a.title }),
            el("span", { class: "n", text: a.provides + " entities" }),
          ]),
          el("p", { class: "d", text: a.description }),
        ]);
        var row = el("div", { class: "pick-row" }, [pick]);
        row.appendChild(el("button", {
          class: "btn small", type: "button",
          text: readOnly ? "Read shape" : "Edit shape",
          title: readOnly ? "The archetype file itself" : "Edit the archetype itself",
          onclick: function () { openArchetypeEditor(a.id); },
        }));
        body.appendChild(row);
      });
      if (readOnly) return;
      body.appendChild(el("div", { class: "acts" }, [
        el("button", {
          class: "btn small primary", type: "button",
          text: "Compose a shape from parts",
          title: "Pick modules, blocks and patterns from the library; get the archetype written",
          onclick: function () { openArchetypeComposer(); },
        }),
        el("button", {
          class: "btn small", id: "btnNewArchetype", type: "button",
          text: "Write a new archetype",
          onclick: function () { openArchetypeEditor(null); },
        }),
      ]));
      body.appendChild(el("p", { class: "group-title", text: "Or one entity at a time" }));
      Object.keys(state.schema.entities).sort().forEach(function (name) {
        body.appendChild(el("button", { class: "pick", type: "button",
          onclick: function () { openEntityEditor(name, null, null); } }, [
          el("div", { class: "top" }, [
            el("span", { class: "t", text: state.schema.entities[name].label }),
          ]),
        ]));
      });
    }, null);
  }

  function openInstantiate(archetype) {
    var spec = state.schema.entities[archetype.appliesTo];
    openDrawer("New from " + archetype.title, "10_MODEL/" + spec.folder + "/", function (body) {
      body.appendChild(el("p", { class: "explain", text: archetype.description }));

      body.appendChild(el("div", { class: "field mono-in" }, [
        el("label", { for: "f__id" }, [spec.pk, el("span", { class: "req", text: "*" })]),
        el("input", { id: "f__id", type: "text", placeholder: "PRD-EXAMPLE" }),
      ]));

      body.appendChild(el("p", { class: "group-title", text: "The " + spec.label }));
      spec.fields.filter(function (f) { return f.required; }).forEach(function (f) {
        body.appendChild(fieldRow(f, null));
      });

      body.appendChild(el("p", { class: "group-title", text: "Archetype parameters" }));
      archetype.parameters.forEach(function (p) {
        var label = el("label", { for: "p_" + p.name }, [p.name.replace(/_/g, " ")]);
        if (p.required) label.appendChild(el("span", { class: "req", text: "*" }));
        if (p.description) label.appendChild(el("span", { class: "hint", text: p.description }));
        body.appendChild(el("div", { class: "field" }, [
          label,
          el("input", { id: "p_" + p.name, "data-param": p.name, type: "text",
            placeholder: p.default == null ? "" : String(p.default) }),
        ]));
      });

      /* The choices. A slot is one need with more than one part that can
       * fill it; the shape names the default and the product picks. */
      var slots = archetype.slots || [];
      if (slots.length) {
        body.appendChild(el("p", { class: "group-title", text: "Choices \u00b7 " + slots.length }));
        body.appendChild(el("p", { class: "brief-hint", text:
          "Where this shape varies. Each is one need and the parts that can fill it." }));
        slots.forEach(function (s) {
          var group = el("div", { class: "part" }, [
            el("p", { class: "part-head" }, [
              el("span", { class: "part-name", text: s.name.replace(/_/g, " ") }),
              el("span", { class: "part-cat mono", text: s.optional ? "optional" : "one of" }),
            ]),
            el("p", { class: "part-desc", text: s.description || "" }),
          ]);
          var options = s.options.slice();
          if (s.optional) options.push({ id: "none", name: "None", description: "This product does without one." });
          var picked = s.default || (s.optional ? "none" : options[0].id);
          options.forEach(function (o) {
            var radio = el("input", { type: "radio", name: "slot_" + s.name,
              id: "slot_" + s.name + "_" + o.id, value: o.id, "data-slot": s.name });
            radio.checked = o.id === picked;
            group.appendChild(el("label", { class: "part-head", for: "slot_" + s.name + "_" + o.id }, [
              radio,
              el("span", { class: "part-name", text: o.name }),
              el("span", { class: "part-n mono", text: o.provides ? o.provides + " entities" : "" }),
            ]));
            if (o.description) group.appendChild(el("p", { class: "part-desc", text: o.description }));
            (o.parameters || []).forEach(function (p) {
              var label = el("label", { for: "mp_" + o.id + "_" + p.name }, [p.name.replace(/_/g, " ")]);
              if (p.required && p.answered == null) label.appendChild(el("span", { class: "req", text: "*" }));
              var hint = p.description || "";
              if (p.component) {
                hint = kindHint(hint, p);
              }
              if (p.answered != null) {
                // The shape answers it from its own parameters; the field
                // is for saying otherwise.
                hint = (hint ? hint.replace(/[.\s]+$/, "") + ". " : "") + "The shape answers this with " + String(p.answered) + ".";
              }
              if (hint) label.appendChild(el("span", { class: "hint", text: hint }));
              var value = p.answered != null ? p.answered : (p.bound != null ? p.bound : p.default);
              group.appendChild(el("div", { class: "field part-field" }, [
                label,
                el("input", { id: "mp_" + o.id + "_" + p.name, type: "text",
                  "data-module": o.id, "data-module-param": p.name,
                  placeholder: value == null ? "" : String(value) }),
              ]));
            });
          });
          body.appendChild(group);
        });
      }

      /* The parts. Each is a switch: on by default, off for what this
       * product does not need. A part another kept part depends on cannot be
       * switched off, and the form says which part is holding it. */
      var modules = archetype.modules || [];
      if (modules.length) {
        body.appendChild(el("p", { class: "group-title", text: "Parts · " + modules.length }));
        body.appendChild(el("p", { class: "brief-hint", text:
          "What this shape is composed from. Switch off the parts this product does "
          + "not need; the diagram is chosen, not drawn." }));
        var partList = el("div", { class: "part-list" });
        var boxes = {};
        function refreshParts() {
          modules.forEach(function (m) {
            var box = boxes[m.alias];
            if (!box) return;  // a kit header is a group, not a switch
            var dependents = modules.filter(function (o) {
              return boxes[o.alias] && boxes[o.alias].checked && (o.requires || []).indexOf(m.alias) !== -1;
            });
            var locked = !m.optional || dependents.length > 0;
            box.disabled = locked;
            box.closest(".part").classList.toggle("is-off", !box.checked);
            var why = box.closest(".part").querySelector(".part-why");
            why.textContent = !m.optional ? "always part of this shape"
              : dependents.length ? "needed by " + dependents.map(function (d) { return d.name; }).join(", ")
              : "";
          });
        }
        modules.forEach(function (m) {
          var part;
          if (m.kit) {
            /* A kit is a heading over its members, with the parameters the
             * kit itself asks for. Its members follow as ordinary switches. */
            part = el("div", { class: "part is-kit" }, [
              el("p", { class: "part-head" }, [
                el("span", { class: "part-name", text: m.name }),
                el("span", { class: "part-cat mono", text: "kit of " + m.members.length }),
                el("span", { class: "part-n mono", text: m.provides ? m.provides + " entities" : "" }),
              ]),
              el("p", { class: "part-desc", text: m.description || "" }),
            ]);
          } else {
            var box = el("input", { type: "checkbox", id: "part_" + m.alias, "data-part": m.alias });
            box.checked = true;
            boxes[m.alias] = box;
            part = el("div", { class: "part" + (m.in_kit ? " in-kit" : "") }, [
              el("label", { class: "part-head", for: "part_" + m.alias }, [
                box,
                el("span", { class: "part-name", text: m.name }),
                el("span", { class: "part-cat mono", text: m.category || "" }),
                el("span", { class: "part-n mono", text: m.provides ? m.provides + " entities" : "" }),
                el("span", { class: "part-n mono", text: m.in_kit ? "in " + m.in_kit : "" }),
              ]),
              el("p", { class: "part-desc", text: m.description || "" }),
              el("span", { class: "part-why" }),
            ]);
          }
          (m.parameters || []).forEach(function (p) {
            var label = el("label", { for: "mp_" + m.alias + "_" + p.name }, [p.name.replace(/_/g, " ")]);
            if (p.required) label.appendChild(el("span", { class: "req", text: "*" }));
            var hint = p.description || "";
            /* A parameter that names a kind shows what the shape binds it to;
             * the product can still say otherwise. */
            if (p.component) {
              hint = kindHint(hint, p);
            }
            if (hint) label.appendChild(el("span", { class: "hint", text: hint }));
            var value = p.bound != null ? p.bound : p.default;
            part.appendChild(el("div", { class: "field part-field" }, [
              label,
              el("input", { id: "mp_" + m.alias + "_" + p.name, type: "text",
                "data-module": m.alias, "data-module-param": p.name,
                placeholder: value == null ? "" : String(value) }),
            ]));
          });
          if (boxes[m.alias]) boxes[m.alias].addEventListener("change", refreshParts);
          partList.appendChild(part);
        });
        body.appendChild(partList);
        refreshParts();
      }
    }, function () {
      var body = $("drawerBody");
      var id = body.querySelector("#f__id").value.trim();
      if (!id) { toast("err", "An identifier is required"); return Promise.resolve(false); }
      var params = {};
      Array.prototype.forEach.call(body.querySelectorAll("[data-param]"), function (input) {
        var v = input.value.trim();
        if (v) params[input.getAttribute("data-param")] = v;
      });
      var without = [];
      Array.prototype.forEach.call(body.querySelectorAll("[data-part]"), function (box) {
        if (!box.checked) without.push(box.getAttribute("data-part"));
      });
      var choose = {};
      Array.prototype.forEach.call(body.querySelectorAll("[data-slot]:checked"), function (radio) {
        choose[radio.getAttribute("data-slot")] = radio.value;
      });
      var moduleParams = {};
      Array.prototype.forEach.call(body.querySelectorAll("[data-module-param]"), function (input) {
        var v = input.value.trim();
        if (!v) return;
        var alias = input.getAttribute("data-module");
        (moduleParams[alias] = moduleParams[alias] || {})[input.getAttribute("data-module-param")] = v;
      });
      return api("/api/instantiate", {
        archetype: archetype.id, id: id, values: collect(body), parameters: params,
        without: without, moduleParams: moduleParams, choose: choose,
      }).then(function (res) {
        toast("ok", "Created " + id, res.generated.length + " entities generated");
        refresh();
        showEntity(id);
        return true;
      });
    });
  }

  /* A finding names the thing it is about by id. The id is a link to it,
   * so a reader can go from "SYS-AML has no cmdb_ci_sys_id" to SYS-AML
   * without a search. Paths are shown with one kind of slash. */
  function findingMessage(text) {
    var parts = [];
    var rest = String(text || "");
    var pattern = /\b[A-Z][A-Z0-9]+(?:-[A-Z0-9]+)+\b/g;
    var last = 0, m;
    while ((m = pattern.exec(rest)) !== null) {
      var id = m[0];
      if (!state.index.some(function (i) { return i.id === id; })) continue;
      if (m.index > last) parts.push(rest.slice(last, m.index));
      parts.push(el("button", { type: "button", class: "ref", text: id, onclick: function () {
        closeDrawer();
        goToEntity(id);
      } }));
      last = m.index + id.length;
    }
    if (last < rest.length) parts.push(rest.slice(last));
    return parts;
  }

  function findingRow(f, isError) {
    return el("div", { class: "finding" + (isError ? " err" : "") }, [
      el("span", { class: "code", text: f.code }),
      el("span", { class: "msg" }, findingMessage(f.message).concat([
        f.where ? el("span", { class: "where", text: String(f.where).replace(/\\/g, "/") }) : null,
      ])),
    ]);
  }

  /* ---- the Checks page ----------------------------------------------------
   * Validate, Coverage, Drift and Changes are four answers to one question,
   * "is the model right", so they share a page and a row of tabs. Each tab
   * says in a line what it answers; the one page is where the sidebar's
   * Checks row goes, and where the home page's findings link to.
   */
  var CHECK_TABS = [
    ["validate", "Validate", "every rule, with the file each finding came from", function () { openValidate(); }],
    ["needs", "What the diagrams need", "the fields each one reads, and who lacks them", function () { openNeeds(); }],
    ["coverage", "Coverage", "what the model does not say", openCoverage],
    ["drift", "Drift", "the model against the CMDB export", openDrift],
    ["changes", "Changes", "since an earlier revision", function () { openChanges(); }],
  ];

  function renderArtifacts(btn) {
    btn.disabled = true;
    api("/api/render", {}).then(function (res) {
      toast("ok", "Rendered " + res.rendered.length + " views", res.filesWritten + " files into 70_ARTIFACTS");
    }).catch(fail).then(function () { btn.disabled = false; });
  }

  function checksHead(active, sub) {
    var readOnly = !!window.__AAC_STATIC__;
    var tabs = el("div", { class: "page-tabs", role: "tablist" });
    CHECK_TABS.forEach(function (t) {
      var on = t[0] === active;
      tabs.appendChild(el("button", { class: "page-tab" + (on ? " is-on" : ""), type: "button", role: "tab",
        "aria-selected": on ? "true" : "false", onclick: t[3] }, [
        el("span", { class: "pt-label", text: t[1] }),
        el("span", { class: "pt-note", text: t[2] }),
      ]));
    });
    var acts = el("div", { class: "page-acts" });
    if (!readOnly) {
      var render = el("button", { class: "btn", type: "button", text: "Regenerate the diagrams",
        title: "Render every view, flow and the library catalog into 70_ARTIFACTS" });
      render.addEventListener("click", function () { renderArtifacts(render); });
      acts.appendChild(render);
    }
    return el("div", { class: "page-head" }, [
      el("div", { class: "page-head-row" }, [
        el("div", { class: "page-head-text" }, [
          el("h1", { text: "Checks" }),
          el("p", { class: "sub", text: sub }),
        ]),
        acts,
      ]),
      tabs,
    ]);
  }

  function factTile(label, n, note, cls) {
    return el("div", { class: "hero-fact" + (cls ? " " + cls : "") }, [
      el("span", { class: "hf-k", text: label }),
      el("span", { class: "hf-n", text: Number(n).toLocaleString("en-US") }),
      el("span", { class: "hf-note", text: note || "" }),
    ]);
  }

  /* Validate, as a page: the totals and a list of rules on the left, the
   * findings grouped by rule on the right, each rule a fold with the file
   * every finding came from. A rule on the left narrows the right. */
  function openValidate(ruleFilter) {
    state.panel = "validate";
    showPanel(true);
    state.checkRule = ruleFilter || "";
    syncUrl();
    var panel = $("dataPanel");
    panel.textContent = "";
    panel.classList.remove("is-table");
    panel.appendChild(checksHead("validate",
      "The same gates CI runs, on the model as it is now. An error blocks a merge; "
      + "a warning is a finding the model is supposed to surface."));
    var host = el("div", { class: "chg-body" });
    panel.appendChild(host);
    host.appendChild(el("p", { class: "brief-hint", text: "Running the rules\u2026" }));
    api("/api/validate").then(function (data) {
      host.textContent = "";
      var errors = data.errors || [], warnings = data.warnings || [];
      var by = {};
      warnings.forEach(function (f) { (by[f.code] = by[f.code] || []).push(f); });
      var codes = Object.keys(by).sort(function (a, b) { return by[b].length - by[a].length; });

      var side = el("div", { class: "checks-side" });
      var main = el("div", { class: "checks-main" });
      host.appendChild(el("div", { class: "checks-cols" }, [side, main]));

      var tiles = el("div", { class: "hero-facts" });
      tiles.appendChild(factTile("Errors", errors.length, errors.length ? "these block a merge" : "every gate passes", errors.length ? "is-bad" : ""));
      tiles.appendChild(factTile("Warnings", warnings.length, codes.length + " " + plural(codes.length, "rule"), warnings.length ? "is-warn" : ""));
      side.appendChild(tiles);

      var filter = ruleFilter || "";
      var rules = el("div", { class: "home-panel checks-rules" });
      rules.appendChild(el("div", { class: "hp-head" }, [el("h2", { class: "hp-title", text: "By rule" })]));
      function ruleRow(code, n, label) {
        var row = el("button", { class: "hp-row" + (filter === code ? " is-on" : ""), type: "button",
          onclick: function () { openValidate(code); } }, [
          el("span", { class: "hp-text" }, [el("span", { class: "hp-desc", text: label })]),
          el("span", { class: "hp-count num", text: String(n) }),
        ]);
        rules.appendChild(row);
      }
      ruleRow("", errors.length + warnings.length, "All findings");
      if (errors.length) ruleRow("errors", errors.length, "Errors");
      codes.forEach(function (code) { ruleRow(code, by[code].length, code); });
      side.appendChild(rules);
      side.appendChild(el("p", { class: "brief-hint", text:
        "Warnings do not block a merge. What to do about each is a decision, not a fix: "
        + "a system can lack a CMDB id because the CMDB is behind, or because it is not a CI." }));

      if (!errors.length && !warnings.length) {
        main.appendChild(el("p", { class: "brief-hint", text: "Every rule passes. Nothing to report." }));
        return;
      }
      function group(title, code, rows, isError, open) {
        var box = el("details", { class: "fgroup" + (isError ? " is-bad" : "") });
        box.open = open;
        box.appendChild(el("summary", { class: "fgroup-head" }, [
          el("span", { class: "fg-dot" }),
          el("span", { class: "fg-text" }, [
            el("span", { class: "fg-title", text: title }),
            code ? el("span", { class: "fg-code", text: code }) : null,
          ]),
          el("span", { class: "sb-badge fg-n" + (isError ? " is-bad" : ""), text: String(rows.length) }),
        ]));
        var list = el("div", { class: "findings" });
        rows.forEach(function (f) { list.appendChild(findingRow(f, isError)); });
        box.appendChild(list);
        return box;
      }
      var shown = 0;
      if (errors.length && (!filter || filter === "errors")) {
        main.appendChild(group("Errors, which block a merge", "", errors, true, true));
        shown += 1;
      }
      codes.forEach(function (code, i) {
        if (filter && filter !== code) return;
        main.appendChild(group(RULE_WORDS[code] || code, code, by[code], false, !!filter || (i < 2 && !errors.length) || i < 1));
        shown += 1;
      });
      if (!shown) main.appendChild(el("p", { class: "brief-hint", text: "Nothing under that rule." }));
    }).catch(fail);
  }

  /* ---- What the diagrams need -----------------------------------------------
   * A view never names what it draws: it selects by fields, boxes by them,
   * draws its lines along them and shades by them (terrane/needs.py). A bare
   * inventory of three hundred systems has names, owners and a lifecycle,
   * and most diagrams draw little or nothing of it. This says which fields
   * would fill which, on each drawing and as one list, and sets a field on
   * many records at once through the save that changes one, each record
   * where it lives. */
  var NEED_ROLES = { selects: "selects", groups: "boxes", lines: "lines", shades: "shade", orders: "order" };
  var RELATION_WORDS = {
    interfaces: "Connections", system_realizes_capability: "Capabilities realized",
    system_reads_writes: "Data read and written", system_uses_tech_service: "Technology it runs on",
    tech_service_connects_to: "Network connections", work_package_affects_system: "Work packages",
    actor_uses_system: "People and channels", product_includes_system: "Products",
  };

  function oneOr(n, one, many) { return n === 1 ? one : many; }

  function needWord(n) {
    if (n.kind === "relation") return RELATION_WORDS[n.field] || capFirst(String(n.field).replace(/_/g, " "));
    if (n.kind === "tag") {
      return "Tagged " + (n.values || []).map(function (v) { return v.value; }).join(" or ");
    }
    return capFirst(fieldWord(n.field));
  }

  function roleWords(roles) {
    return (roles || []).map(function (r) { return NEED_ROLES[r] || r; }).join(", ");
  }

  /* One need, in a sentence: what lacking it does to this drawing. */
  function needSaid(n, many) {
    var types = typeWord(n.type, true);
    if (!n.asked) {
      return ((state.overview || {}).counts || {})[n.type] ? "None is drawn, so none is asked yet."
        : "The estate has no " + types + " yet.";
    }
    if (n.kind === "tag") {
      var carry = n.asked - n.lacking;
      return carry ? carry + " of " + n.asked + " " + types + " carry the tag; only those are drawn."
        : "None of the " + n.asked + " " + types + " carries the tag, so none is drawn.";
    }
    if (n.kind === "relation") {
      if (!n.lacking) return "Every one drawn has one.";
      return n.lacking === n.asked ? "None of the " + n.asked + " drawn has one yet."
        : n.lacking + " of " + n.asked + " drawn have none.";
    }
    if (!n.lacking) return "Every " + typeWord(n.type) + " " + (n.roles.indexOf("selects") !== -1 ? "it asks" : "drawn")
      + " has one.";
    var head = n.lacking + " of " + n.asked + " " + types + " have none, ";
    var by = n.byRole || {};
    if (by.selects) return head + "so they are left off.";
    if (by.groups) {
      return n.lacking === n.asked ? head + "so there are no boxes: every " + typeWord(n.type) + " sits loose on the sheet."
        : head + "so they sit outside the boxes.";
    }
    if (by.lines) return head + "so they are drawn without the line.";
    if (by.shades) return head + "so they are drawn unshaded.";
    return head + "so they are placed last.";
  }

  function needsUrl(viewId) {
    var extra = Object.keys(state.subject || {}).map(function (name) {
      return "&p_" + encodeURIComponent(name) + "=" + encodeURIComponent(state.subject[name]);
    }).join("");
    return "/api/needs/view?view=" + encodeURIComponent(viewId) + extra;
  }

  function needBar(n) {
    var share = n.asked ? Math.max(0, Math.min(1, (n.asked - n.lacking) / n.asked)) : 0;
    return el("span", { class: "nd-bar" + (n.lacking ? " is-short" : "") }, [
      el("i", { style: "width:" + Math.max(share ? 2 : 0, Math.round(share * 100)) + "%" }),
    ]);
  }

  /* The brief's "What it needs": every field and tag it reads, and the
   * relations only where something lacks one. */
  function needsSection(data) {
    var shown = data.needs.filter(function (n) { return n.kind !== "relation" || n.lacking; });
    if (!shown.length) return null;
    var types = {};
    data.needs.forEach(function (n) { types[n.type] = true; });
    var several = Object.keys(types).length > 1;
    var editable = !window.__AAC_STATIC__;
    var box = el("div", { class: "nd-brief" }, [el("h3", { class: "brief-h", text: "What it needs" })]);
    shown.forEach(function (n) {
      box.appendChild(el("div", { class: "nd-need" }, [
        el("div", { class: "nd-top" }, [
          el("strong", { text: needWord(n) }),
          el("span", { text: roleWords(n.roles) + (several ? " · " + typeWord(n.type, true) : "") }),
        ]),
        n.asked && n.kind !== "relation" ? needBar(n) : null,
        el("p", { class: "nd-said" + (n.lacking && n.kind === "field" ? " is-short" : ""), text: needSaid(n) }),
        editable && n.settable && n.lacking ? el("button", { class: "linkish nd-act", type: "button",
          onclick: function () { openSetMany({ type: n.type, field: n.field, view: data.viewId, subject: data.subject }); } },
          [svgIcon("i-list-checks"), el("span", { text: (n.kind === "tag" ? "Tag some " : "Set on many ")
            + typeWord(n.type, true) })]) : null,
      ]));
    });
    return box;
  }

  function loadBriefNeeds(box, viewId) {
    var slot = el("div", { class: "nd-slot" });
    box.appendChild(slot);
    var url = needsUrl(viewId);
    var show = function (data) {
      var sec = needsSection(data);
      if (sec) slot.appendChild(sec);
      renderNeedStrip(data);
    };
    // The brief is drawn again on every deselect; the needs change only
    // when the model does, which is when the overview is read again.
    var kept = state.needsKept;
    if (kept && kept.url === url && kept.overview === state.overview) { show(kept.data); return; }
    api(url).then(function (data) {
      if (state.viewId !== viewId) return;
      state.needsKept = { url: url, overview: state.overview, data: data };
      show(data);
    }).catch(function () { /* the published copy has no needs to read */ });
  }

  /* The one line over a thin drawing that says what would fill it. */
  function renderNeedStrip(data) {
    var strip = $("needStrip");
    if (!strip) return;
    strip.textContent = "";
    strip.hidden = true;
    $("mapSheet").classList.remove("has-strip");
    if (!data || data.state !== "thin" || state.panel || state.focus) return;
    var pick = null, text = "";
    var selects = data.needs.filter(function (n) { return n.kind === "field" && (n.byRole || {}).selects; })
      .sort(function (a, b) { return b.lacking - a.lacking; })[0];
    var boxes = data.needs.filter(function (n) { return n.kind === "field" && (n.byRole || {}).groups; })
      .sort(function (a, b) { return b.lacking - a.lacking; })[0];
    if (data.keptOff && selects) {
      pick = selects;
      text = data.keptOff + " " + typeWord(selects.type, true) + " are left off because they have no "
        + fieldWord(selects.field) + ".";
    } else if (boxes && boxes.lacking) {
      pick = boxes;
      text = boxes.lacking === boxes.asked
        ? "No " + typeWord(boxes.type) + " has a " + fieldWord(boxes.field) + ", so this " + (KIND_WORDS[data.kind] || "drawing")
          + " has no boxes to group them into."
        : boxes.lacking + " of " + boxes.asked + " " + typeWord(boxes.type, true) + " have no " + fieldWord(boxes.field)
          + " and sit outside the boxes.";
    } else {
      text = "Nothing drawn here is connected to anything else drawn here yet.";
    }
    if ((state.stripClosed || {})[data.viewId]) return;
    strip.appendChild(svgIcon("i-circle-alert"));
    strip.appendChild(el("span", { class: "grow", text: text }));
    if (pick && pick.settable && !window.__AAC_STATIC__) {
      strip.appendChild(el("button", { class: "btn small", type: "button", text: "Set " + fieldWord(pick.field),
        onclick: function () { openSetMany({ type: pick.type, field: pick.field, view: data.viewId, subject: data.subject }); } }));
    }
    strip.appendChild(el("button", { class: "icon-btn", type: "button", "aria-label": "Close this note", title: "Close this note; "
      + "the brief beside the drawing still says it", text: "×", onclick: function () {
        (state.stripClosed = state.stripClosed || {})[data.viewId] = true;
        strip.hidden = true;
        $("mapSheet").classList.remove("has-strip");
        if (state.cy && !tilesShown()) openReadable(state.cy);
      } }));
    strip.hidden = false;
    $("mapSheet").classList.add("has-strip");
    if (state.cy && !tilesShown()) openReadable(state.cy);
  }

  /* A drawing that draws nothing says what it draws and what the records
   * lack, in place of the error it used to show. */
  function renderEmptyNeeds(viewId) {
    api(needsUrl(viewId)).then(function (data) {
      if (state.viewId !== viewId) return;
      var host = $("emptyNeeds");
      host.textContent = "";
      var readOnly = !!window.__AAC_STATIC__;
      var settable = data.needs.filter(function (n) { return n.settable && n.lacking; })
        .sort(function (a, b) { return ((b.byRole || {}).selects || 0) - ((a.byRole || {}).selects || 0) || b.lacking - a.lacking; });
      var missing = data.needs.filter(function (n) { return !n.asked && (n.byRole || {}).selects !== undefined; });
      var title = data.title;
      var lede;
      var first = settable[0];
      if (data.problem) {
        lede = data.problem;
      } else if (first && (first.byRole || {}).selects && first.kind === "field") {
        lede = title + " draws the " + typeWord(first.type, true) + " that have a " + fieldWord(first.field)
          + ". None of the " + first.asked + " has one, so every one is left off.";
      } else if (first && first.kind === "tag") {
        lede = title + " draws the " + typeWord(first.type, true) + " " + needWord(first).toLowerCase()
          + ". " + needSaid(first);
      } else if (missing.length) {
        lede = title + " draws " + missing.map(function (n) { return typeWord(n.type, true); })
          .filter(function (w, i, all) { return all.indexOf(w) === i; }).join(" and ")
          + ", and the estate has none yet. Bring them in from an export, or place them on a canvas.";
      } else {
        lede = title + " selects nothing in the estate as it is.";
      }
      host.appendChild(el("h2", { text: "Nothing to draw yet" }));
      host.appendChild(el("p", { class: "nd-lede", text: lede }));
      var lanes = first && first.kind === "field" && first.values && first.values.length && first.values.length <= 8
        && (first.roles.indexOf("groups") !== -1) ? first.values : null;
      if (lanes) {
        host.appendChild(el("div", { class: "nd-lanes" }, lanes.map(function (v) {
          return el("div", { class: "nd-lane" }, [el("strong", { text: v.label }),
            el("span", { text: "0 " + typeWord(first.type, true) })]);
        })));
      }
      var acts = el("div", { class: "acts" });
      if (first && !readOnly) {
        acts.appendChild(el("button", { class: "btn primary", type: "button",
          onclick: function () { openSetMany({ type: first.type, field: first.field, view: data.viewId, subject: data.subject }); } },
          [svgIcon("i-list-checks"), el("span", { text: (first.kind === "tag" ? "Tag some " : "Set " + fieldWord(first.field) + " on many ")
            + typeWord(first.type, true) })]));
      } else if (missing.length && !readOnly) {
        acts.appendChild(el("button", { class: "btn primary", type: "button", onclick: function () { openSettings("sources"); } },
          [svgIcon("i-file-up"), el("span", { text: "Bring in an export" })]));
        acts.appendChild(el("button", { class: "btn", type: "button", text: "Draw on a canvas", onclick: function () { openCanvas(null); } }));
      }
      acts.appendChild(el("button", { class: "btn", type: "button", text: "What every diagram needs", onclick: function () { openNeeds(); } }));
      host.appendChild(acts);
      if (first && first.kind === "field") {
        host.appendChild(el("p", { class: "nd-foot", text: capFirst(fieldWord(first.field)) + " is a field on each "
          + typeWord(first.type) + (lanes ? "; the lanes are its values" : "") + ". Setting it writes each "
          + typeWord(first.type) + "'s own file." }));
      }
      $("emptyPlain").hidden = true;
      host.hidden = false;
      var box = $("inspIdle");
      if (box) {
        // The brief of a drawing that draws nothing: what it is, and what it reads.
        var v = (state.overview.views || []).filter(function (x) { return x.viewId === viewId; })[0];
        box.textContent = "";
        box.appendChild(el("h3", { class: "brief-h", text: "This view" }));
        if (v && v.description) box.appendChild(el("p", { class: "brief-p", text: v.description }));
        var sec = needsSection(data);
        if (sec) box.appendChild(sec);
      }
    }).catch(function () { /* the plain empty state stands */ });
  }

  /* The one list, as a tab of Checks. */
  function openNeeds() {
    state.panel = "needs";
    showPanel(true);
    var panel = $("dataPanel");
    panel.textContent = "";
    panel.classList.remove("is-table");
    panel.appendChild(checksHead("needs", "The same gates CI runs, on the model as it is now, and what each diagram "
      + "needs from the records to draw."));
    var host = el("div", { class: "st-body nd-page" });
    panel.appendChild(host);
    var main = el("div", { class: "st-main" }), side = el("aside", { class: "st-side" });
    host.appendChild(main);
    host.appendChild(side);
    main.appendChild(el("p", { class: "st-hint", text: "Reading every diagram…" }));
    side.appendChild(el("h2", { text: "How it is worked out" }));
    side.appendChild(el("p", { class: "st-lede", text: "Each diagram is a query: the records it selects, the boxes it puts them "
      + "in, the lines between them, the shade. Each of those reads a field." }));
    side.appendChild(el("p", { class: "st-lede", text: "A record with the field blank is left off a diagram that selects by it, "
      + "or sits outside the boxes of one that groups by it. Neither is an error; a diagram is only as full as the records." }));
    side.appendChild(el("p", { class: "st-lede", text: "A blank that is an answer is not counted: a SaaS system has no cloud "
      + "account, and the top of a hierarchy has no parent. Diagrams drawn for one system or product at a time say what "
      + "they need on each drawing." }));
    side.appendChild(el("p", { class: "st-foot" }, [svgIcon("i-terminal"),
      el("span", { text: "The command line says the same: terrane needs." })]));
    syncUrl();
    api("/api/needs").then(function (d) {
      main.textContent = "";
      var s = d.states;
      var total = s.full + s.thin + s.empty + s.subject;
      main.appendChild(el("p", { class: "nd-sum", text: "Of " + total + " diagrams, " + s.full + " draw in full, " + s.thin
        + " draw thin, " + s.empty + " have nothing to draw yet, and " + s.subject + " are drawn for one thing at a time." }));
      var readOnly = !!window.__AAC_STATIC__;
      function viewLinks(views, verb) {
        var span = el("span", { class: "nd-views" });
        views.slice(0, 3).forEach(function (v, i) {
          if (i) span.appendChild(document.createTextNode(", "));
          span.appendChild(el("button", { class: "linkish", type: "button", text: v.title, onclick: function () { selectView(v.viewId); } }));
        });
        if (views.length > 3) span.appendChild(document.createTextNode(" and " + (views.length - 3) + " more"));
        if (verb) span.appendChild(document.createTextNode(" " + verb));
        return span;
      }
      function section(title, note, rows) {
        main.appendChild(el("div", { class: "st-sec-head row nd-head" }, [el("h2", { text: title }), el("span", { class: "st-hint", text: note })]));
        var list = el("div", { class: "nd-list" });
        rows.forEach(function (r) { list.appendChild(r); });
        main.appendChild(list);
      }
      function row(what, sub, count, views, act) {
        return el("div", { class: "nd-row" }, [
          el("div", { class: "nd-what" }, [el("strong", { text: what }), el("span", { text: sub })]),
          el("div", { class: "nd-count" }, count),
          el("div", { class: "nd-read" }, [views]),
          el("div", { class: "nd-act" }, [act]),
        ]);
      }
      var RANK = ["selects", "groups", "lines", "shades", "orders"];
      function strongest(v) {
        return Math.min.apply(null, (v.roles || []).map(function (r) { return RANK.indexOf(r); }).concat([RANK.length]));
      }
      /* The diagram that needs it most leads, with what it does with it;
       * the rest are named after. Saying "shade by it" of a field one of
       * them draws nothing without undersold it. */
      function readBy(views) {
        var sorted = views.slice().sort(function (a, b) { return strongest(a) - strongest(b); });
        var lead = sorted[0], rest = sorted.slice(1), r = RANK[strongest(lead)];
        var verb = r === "selects" ? "draws only the records with it" : r === "groups" ? "boxes by it"
          : r === "lines" ? "draws lines along it" : r === "shades" ? "shades by it" : "reads it";
        var span = viewLinks([lead], verb);
        if (rest.length) {
          span.appendChild(document.createTextNode("; "));
          span.appendChild(viewLinks(rest, rest.length === 1 ? "reads it too" : "read it too"));
        }
        return span;
      }
      if (d.fields.length) {
        section("Fields to fill", "set on many records at once, each changed in its own file", d.fields.map(function (f) {
          var n = { type: f.type, field: f.field, kind: f.kind, asked: f.asked, lacking: f.lacking, values: f.values };
          var count = f.kind === "tag"
            ? [el("span", { class: "nd-n", text: (f.asked - f.lacking) + " of " + f.asked + " carry it" })]
            : [needBar(n), el("span", { class: "nd-n is-short", text: f.lacking + " of " + f.asked + " have none" })];
          return row(needWord(n), "on " + typeWord(f.type, true), count, readBy(f.views),
            readOnly ? null : el("button", { class: "btn small", type: "button", text: f.kind === "tag" ? "Tag some" : "Set on many",
              onclick: function () { openSetMany({ type: f.type, field: f.field }); } }));
        }));
      }
      if (d.none.length) {
        section("Kinds of record the estate has none of", "brought in, or placed on a canvas", d.none.map(function (k) {
          return row(capFirst(typeWord(k.type, true)), "none yet", [el("span", { class: "nd-n", text: k.views.length + " "
            + plural(k.views.length, "diagram") })], viewLinks(k.views, ""),
            readOnly ? null : el("button", { class: "btn small", type: "button", text: "Bring in", onclick: function () { openSettings("sources"); } }));
        }));
      }
      if (d.lines.length) {
        section("Lines", "drawn from connections, not set on a field", d.lines.map(function (l) {
          var n = { type: l.type, field: l.field, kind: "relation", asked: l.asked, lacking: l.lacking };
          return row(needWord(n), "on " + typeWord(l.type, true), [needBar(n),
            el("span", { class: "nd-n is-short", text: l.lacking + " of " + l.asked + " have none" })],
            viewLinks(l.views, l.views.length === 1 ? "draws them" : "draw them"),
            readOnly ? null : el("button", { class: "btn small", type: "button", text: "Bring in", onclick: function () { openSettings("sources"); } }));
        }));
      }
      if (!d.fields.length && !d.none.length && !d.lines.length) {
        main.appendChild(el("p", { class: "st-callout ok", text: "Every diagram has what it reads: no record lacks a field a "
          + "diagram selects, boxes or draws by." }));
      }
    }).catch(function (err) { main.textContent = ""; main.appendChild(el("p", { class: "st-hint", text: err.message })); });
  }

  /* ---- A field set on many records at once ----------------------------------
   * The records lacking one field, on one diagram or on any, with the fields
   * a person decides the value from beside each name; a value chosen once,
   * the records ticked, and one save that changes each where it lives. A
   * record a shape made or an import rewrites is shown and not offered, with
   * why. Undo puts every file back as it was, line endings and all. */
  function openSetMany(ask) {
    state.panel = "setmany";
    state.setMany = { ask: ask, data: null, value: null, chosen: {}, filters: {}, search: "" };
    showPanel(true);
    syncUrl();
    var q = "/api/needs/records?type=" + encodeURIComponent(ask.type) + "&field=" + encodeURIComponent(ask.field)
      + (ask.view ? "&view=" + encodeURIComponent(ask.view) : "");
    if (ask.view && ask.subject) {
      var v = (state.overview.views || []).filter(function (x) { return x.viewId === ask.view; })[0];
      if (v && v.parameters && v.parameters[0]) q += "&p_" + encodeURIComponent(v.parameters[0]) + "=" + encodeURIComponent(ask.subject);
    }
    var panel = $("dataPanel");
    panel.textContent = "";
    panel.appendChild(el("p", { class: "st-hint pad", text: "Reading the records…" }));
    api(q).then(function (data) {
      var sm = state.setMany;
      if (!sm || sm.ask !== ask) return;
      sm.data = data;
      // A column blank on every record says nothing to decide by.
      data.context = data.context.filter(function (c) {
        return data.records.some(function (r) { return r.context[c]; });
      });
      data.records.forEach(function (r) { if (r.editable) sm.chosen[r.id] = true; });
      if (data.values.length === 1) sm.value = data.values[0].value;
      renderSetMany();
    }).catch(function (err) {
      panel.textContent = "";
      panel.appendChild(el("p", { class: "st-callout warn", text: err.message }));
    });
  }

  function setManyShown() {
    var sm = state.setMany, d = sm.data;
    var words = sm.search.toLowerCase();
    return d.records.filter(function (r) {
      if (words && r.name.toLowerCase().indexOf(words) === -1 && r.id.toLowerCase().indexOf(words) === -1) return false;
      return Object.keys(sm.filters).every(function (c) { return !sm.filters[c] || r.context[c] === sm.filters[c]; });
    });
  }

  function renderSetMany() {
    var sm = state.setMany, d = sm.data, ask = sm.ask;
    var many = typeWord(d.type, true), one = typeWord(d.type);
    var word = d.kind === "tag" ? "The tag" : capFirst(fieldWord(d.field));
    var view = ask.view ? (state.overview.views || []).filter(function (x) { return x.viewId === ask.view; })[0] : null;
    var crumb = view
      ? [el("button", { type: "button", text: "Diagrams", onclick: function () { openDiagrams("All"); } }),
         el("span", { class: "sep", text: "/" }),
         el("button", { type: "button", text: view.title, onclick: function () { selectView(view.viewId); } }),
         el("span", { class: "sep", text: "/" }), el("span", { text: word })]
      : [el("button", { type: "button", text: "Checks", onclick: function () { openValidate(); } }),
         el("span", { class: "sep", text: "/" }),
         el("button", { type: "button", text: "What the diagrams need", onclick: function () { openNeeds(); } }),
         el("span", { class: "sep", text: "/" }), el("span", { text: word })];
    var reading = d.reading || [];
    var first = reading[0];
    var lede = first ? first.title + (first.roles.indexOf("selects") !== -1 ? " draws " + (d.kind === "tag" ? "only the "
      + many + " that carry it" : "a " + one + " only when it has one") : first.roles.indexOf("groups") !== -1
      ? " boxes " + many + " by it" : " reads it") + ". " : "";
    lede += d.records.length + " " + oneOr(d.records.length, one, many) + (d.kind === "tag" ? " do not carry it." : " have none.");
    var shell = settingsShell(word + (d.kind === "tag" ? ", on many " : ", on many ") + many, lede, crumb);
    var body = el("div", { class: "st-body flow" });
    shell.page.appendChild(body);
    var main = el("div", { class: "st-main" }), side = el("aside", { class: "st-side" });
    body.appendChild(main);
    body.appendChild(side);

    main.appendChild(el("h3", { class: "nd-sub", text: d.kind === "tag" ? "Add the tag" : "Set it to" }));
    if (d.free) {
      var list = "nd-values-" + d.field;
      var input = el("input", { class: "st-input nd-free", type: "text", list: list, value: sm.value || "",
        placeholder: d.values.length ? "One of these, or a new " + fieldWord(d.field) : "A " + fieldWord(d.field) });
      input.addEventListener("input", function () { sm.value = input.value.trim() || null; renderSetManyBar(); });
      main.appendChild(el("div", { class: "nd-pick" }, [input, el("datalist", { id: list }, d.values.map(function (v) {
        return el("option", { value: v.value });
      }))]));
    } else if (d.values.length > 12) {
      var sel = el("select", { class: "src-select strong" }, [el("option", { value: "", text: "Choose a " + fieldWord(d.field) })]
        .concat(d.values.map(function (v) { return el("option", { value: v.value, text: v.label }); })));
      if (sm.value) sel.value = sm.value;
      sel.addEventListener("change", function () { sm.value = sel.value || null; renderSetManyBar(); });
      main.appendChild(sel);
    } else {
      var pills = el("div", { class: "nd-pills", role: "radiogroup", "aria-label": word });
      d.values.forEach(function (v) {
        pills.appendChild(el("button", { type: "button", class: "nd-pill", role: "radio",
          "aria-checked": sm.value === v.value ? "true" : "false", text: v.label,
          onclick: function () { sm.value = v.value; renderSetMany(); } }));
      });
      main.appendChild(pills);
    }

    var filters = el("div", { class: "nd-filters" }, [el("span", { class: "st-hint", text: "Show" })]);
    d.context.forEach(function (c) {
      var seen = {};
      d.records.forEach(function (r) { var v = r.context[c]; if (v) seen[v] = (seen[v] || 0) + 1; });
      var keys = Object.keys(seen).sort();
      if (keys.length < 2) return;
      var sel = el("select", { class: "src-select", "aria-label": fieldWord(c) },
        [el("option", { value: "", text: capFirst(fieldWord(c)) + ": any" })].concat(keys.map(function (k) {
          return el("option", { value: k, text: capFirst(fieldWord(c)) + ": " + k + " (" + seen[k] + ")" });
        })));
      sel.value = sm.filters[c] || "";
      sel.addEventListener("change", function () { sm.filters[c] = sel.value; renderSetManyRows(); });
      filters.appendChild(sel);
    });
    var search = el("input", { class: "st-input nd-search", type: "search", placeholder: "Names", value: sm.search,
      "aria-label": "Find by name" });
    search.addEventListener("input", function () { sm.search = search.value; renderSetManyRows(); });
    filters.appendChild(search);
    main.appendChild(filters);
    main.appendChild(el("div", { class: "nd-table", id: "ndTable" }));
    main.appendChild(el("p", { class: "st-hint", id: "ndCounts" }));
    main.appendChild(el("div", { class: "nd-save", id: "ndBar" }));

    side.appendChild(el("h2", { text: "What it changes" }));
    side.appendChild(el("div", { class: "nd-effects", id: "ndEffects" }));
    side.appendChild(el("p", { class: "st-hint", text: "A record a shape made is changed on the shape, and one an import "
      + "rewrites at its source; they are listed and left alone. A harvested record moves into a file of its own, as "
      + "it does when one is saved." }));
    renderSetManyRows();
  }

  function renderSetManyRows() {
    var sm = state.setMany, d = sm.data;
    var host = $("ndTable");
    if (!host) return;
    host.textContent = "";
    var shown = setManyShown();
    var editable = shown.filter(function (r) { return r.editable; });
    var all = editable.length && editable.every(function (r) { return sm.chosen[r.id]; });
    var head = el("div", { class: "nd-tr head" }, [
      el("input", { type: "checkbox", "aria-label": "Choose every one shown", checked: all ? "checked" : null,
        onchange: function (e) { editable.forEach(function (r) { sm.chosen[r.id] = e.target.checked; }); renderSetManyRows(); } }),
      el("span", { text: "Name" }),
    ].concat(d.context.map(function (c) { return el("span", { text: capFirst(fieldWord(c)) }); })));
    host.appendChild(head);
    var cols = "28px minmax(160px, 1.4fr)" + d.context.map(function () { return " minmax(0, 1fr)"; }).join("");
    head.style.gridTemplateColumns = cols;
    shown.slice(0, 400).forEach(function (r) {
      var tr = el("label", { class: "nd-tr" + (r.editable ? "" : " is-off"), title: r.why || null }, [
        el("input", { type: "checkbox", disabled: r.editable ? null : "disabled", checked: sm.chosen[r.id] ? "checked" : null,
          onchange: function (e) { sm.chosen[r.id] = e.target.checked; renderSetManyBar(); } }),
        el("span", { class: "nd-name", text: r.name }),
      ].concat(d.context.map(function (c) { return el("span", { text: r.context[c] || "" }); })));
      tr.style.gridTemplateColumns = cols;
      host.appendChild(tr);
    });
    if (shown.length > 400) host.appendChild(el("p", { class: "st-hint pad", text: "The first 400 of " + shown.length
      + " are listed; every one shown and ticked is set." }));
    if (!shown.length) host.appendChild(el("p", { class: "st-hint pad", text: d.records.length ? "None of them matches."
      : "None lacks it now." }));
    renderSetManyBar();
  }

  /* What is set is what is shown and ticked: narrowing the list to the
   * on-premise systems and saving set every one of them, shown or not, the
   * first time it was walked. */
  function setManyChosen() {
    var sm = state.setMany;
    return setManyShown().filter(function (r) { return r.editable && sm.chosen[r.id]; });
  }

  function renderSetManyBar() {
    var sm = state.setMany, d = sm.data;
    var chosen = setManyChosen();
    var shown = setManyShown();
    var many = typeWord(d.type, true), one = typeWord(d.type);
    var counts = $("ndCounts");
    if (counts) {
      var hidden = d.records.length - shown.length;
      counts.textContent = shown.length + " shown, " + chosen.length + " chosen."
        + (hidden ? " " + hidden + " more " + oneOr(hidden, "lacks", "lack") + " it and " + oneOr(hidden, "is", "are") + " not shown." : "");
    }
    var effects = $("ndEffects");
    if (effects) {
      effects.textContent = "";
      var line = function (n, h, p) {
        effects.appendChild(el("div", { class: "nd-effect" }, [el("strong", { class: "nd-big", text: String(n) }),
          el("div", {}, [el("span", { class: "nd-eh", text: h }), p ? el("span", { class: "nd-ep", text: p }) : null])]));
      };
      (d.reading || []).forEach(function (v) {
        var r = v.roles;
        line(chosen.length, r.indexOf("selects") !== -1 ? "join " + v.title : r.indexOf("groups") !== -1
          ? "move into the boxes on " + v.title : r.indexOf("lines") !== -1 ? "get the line on " + v.title
          : "shaded on " + v.title, r.indexOf("selects") !== -1 && sm.value && d.kind === "field"
          ? "in " + sm.value + ", where nothing else keeps them off" : "");
      });
      var off = d.records.filter(function (r) { return !r.editable; }).length;
      var moves = chosen.filter(function (r) { return r.moves; }).length;
      if (moves) line(moves, "move into a file of their own", "harvested, so the next import leaves them alone");
      line(off, "cannot be changed here", off ? "made by a shape, or rewritten by an import" : "");
    }
    var bar = $("ndBar");
    if (!bar) return;
    bar.textContent = "";
    var ready = sm.value && chosen.length && !window.__AAC_STATIC__;
    bar.appendChild(el("button", { class: "btn primary", type: "button", disabled: ready ? null : "disabled",
      text: sm.value ? (d.kind === "tag" ? "Tag " + chosen.length + " " + oneOr(chosen.length, one, many) + " " + sm.value
        : "Set " + (d.values.filter(function (v) { return v.value === sm.value; })[0] || { label: sm.value }).label
          + " on " + chosen.length + " " + oneOr(chosen.length, one, many))
        : "Choose " + (d.kind === "tag" ? "a tag" : "a " + fieldWord(d.field)) + " first",
      onclick: saveSetMany }));
    bar.appendChild(el("span", { class: "st-hint grow", text: "Each " + one + " is changed in its own file, every other "
      + "line left as it was. Undo puts them back." }));
    bar.appendChild(el("button", { class: "btn", type: "button", text: "Back", onclick: function () {
      if (sm.ask.view) selectView(sm.ask.view); else openNeeds();
    } }));
  }

  function saveSetMany() {
    var sm = state.setMany, d = sm.data;
    var ids = setManyChosen().map(function (r) { return r.id; });
    if (!sm.value || !ids.length) return;
    var ask = sm.ask;
    api("/api/records/set", { type: d.type, field: d.field, value: sm.value, ids: ids }).then(function (res) {
      var n = res.changed.length;
      var detail = [res.moved.length ? res.moved.length + " moved into files of their own" : "",
        res.refused.length ? res.refused.length + " left as they were" : "",
        res.errors.length ? res.errors.length + " " + plural(res.errors.length, "error") + " in the checks" : ""]
        .filter(Boolean).join(" · ");
      var undo = res.undo ? { label: "Undo", go: function () {
        api("/api/records/undo", { token: res.undo }).then(function (u) {
          toast("ok", "Put back", u.restored + " " + plural(u.restored, "file") + " as they were.");
          return refresh().then(function () { openSetMany(ask); });
        }).catch(fail);
      } } : null;
      toast(res.refused.length ? "warn" : "ok", "Set " + fieldWord(d.field) + " on " + n + " " + oneOr(n, typeWord(d.type),
        typeWord(d.type, true)), detail || "Each changed in its own file.", undo);
      return refresh().then(function () {
        if (ask.view) return selectView(ask.view);
        openSetMany(ask);
      });
    }).catch(fail);
  }

  /* ---- Estates ---------------------------------------------------------------
   * The app opens one estate at a time and another without a restart.
   * Starting one is terrane init and joining one terrane connect, the
   * engine's own; the browser remembers the ones it has opened. */
  var ESTATES_KEY = "aac.estates";

  function rememberedEstates() {
    try { return JSON.parse(localStorage.getItem(ESTATES_KEY) || "[]") || []; } catch (err) { return []; }
  }

  function rememberEstate(card) {
    var list = rememberedEstates().filter(function (e) { return e.path.toLowerCase() !== card.path.toLowerCase(); });
    list.unshift({ path: card.path, name: card.name });
    try { localStorage.setItem(ESTATES_KEY, JSON.stringify(list.slice(0, 8))); } catch (err) { /* private mode */ }
  }

  function estateOpened(card, said) {
    rememberEstate(card);
    state.viewId = null;
    state.subject = {};
    state.selectedId = null;
    state.recent = [];
    MINIS = {};
    toast("ok", said + ": " + card.name, card.records + " " + plural(card.records, "record") + ", " + card.views + " diagrams.");
    window.history.replaceState(null, "", "#home");
    return refresh().then(function () { openStart(); });
  }

  function openEstate(path) {
    return api("/api/estate/open", { path: path }).then(function (card) { return estateOpened(card, "Opened"); }).catch(fail);
  }

  function estateMenu(anchor) {
    var old = document.querySelector(".estate-menu");
    if (old) { old.remove(); return; }
    var menu = el("div", { class: "estate-menu", role: "menu" }, [el("p", { class: "em-head", text: "Estates on this machine" })]);
    var list = el("div", { class: "em-list" });
    menu.appendChild(list);
    var close = function (e) {
      if (!menu.contains(e.target) && !anchor.contains(e.target)) { menu.remove(); document.removeEventListener("mousedown", close); }
    };
    document.addEventListener("mousedown", close);
    var item = function (label, sub, on, icon, go) {
      return el("button", { class: "em-item" + (on ? " is-on" : ""), type: "button", role: "menuitem",
        onclick: function () { menu.remove(); document.removeEventListener("mousedown", close); go(); } }, [
        icon ? svgIcon(icon) : null,
        el("span", { class: "em-text" }, [el("strong", { text: label }), sub ? el("span", { text: sub }) : null]),
        on ? svgIcon("i-check") : null,
      ]);
    };
    api("/api/estates").then(function (d) {
      var seen = {}, rows = [];
      d.estates.forEach(function (e) { seen[e.path.toLowerCase()] = true; rows.push(e); });
      rememberedEstates().forEach(function (e) {
        if (!seen[e.path.toLowerCase()]) { seen[e.path.toLowerCase()] = true; rows.push({ path: e.path, name: e.name }); }
      });
      rows.forEach(function (e) {
        list.appendChild(item(e.name, e.sample ? "the sample, a card issuer" : e.path, e.current, null, function () {
          if (!e.current) openEstate(e.path);
        }));
      });
    }).catch(function () { list.appendChild(el("p", { class: "st-hint pad", text: "Only this one, in the published copy." })); });
    if (!window.__AAC_STATIC__) {
      menu.appendChild(el("div", { class: "em-rule" }));
      menu.appendChild(item("Start a new estate…", null, false, "i-plus", function () { openProject("start"); }));
      menu.appendChild(item("Join one your team keeps…", null, false, "i-link", function () { openProject("join"); }));
      menu.appendChild(item("Open a folder…", null, false, "i-folder-open", function () { openProject("open"); }));
    }
    document.body.appendChild(menu);
    var r = anchor.getBoundingClientRect();
    menu.style.left = r.left + "px";
    menu.style.top = (r.bottom + 6) + "px";
    menu.style.width = r.width + "px";
  }

  function openProject(focus) {
    state.projectFocus = focus || null;
    openSettings("project");
  }

  function slugOf(name) {
    return String(name || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "estate";
  }

  /* Start, join or open: three rows of one list, each the engine's own. */
  function anotherEstate(main, p) {
    main.appendChild(el("div", { class: "st-sec-head" }, [el("h2", { text: "Another estate" }),
      el("p", { class: "st-lede", text: "Start one here, join one your team keeps, or open one on this machine. The app "
        + "switches to it; this one is left as it is." })]));
    var box = el("div", { class: "est-options" });
    main.appendChild(box);
    var base = String(p.path || "").replace(/[\\/][^\\/]*$/, "");
    var sep = base.indexOf("\\") !== -1 ? "\\" : "/";
    var field = function (label, input, wide) {
      return el("label", { class: "est-field" + (wide ? " wide" : "") }, [el("span", { text: label }), input]);
    };
    var option = function (key, icon, title, lede, fields, action, foot) {
      var row = el("div", { class: "est-option" + (state.projectFocus === key ? " is-on" : "") }, [
        el("div", { class: "est-top" }, [svgIcon(icon), el("div", { class: "est-text" }, [el("strong", { text: title }),
          el("span", { text: lede })])]),
      ]);
      if (fields) row.appendChild(el("div", { class: "est-fields" }, fields.concat([action])));
      else row.firstChild.appendChild(action);
      if (foot) row.appendChild(el("p", { class: "st-foot est-foot" }, [svgIcon("i-terminal"), el("span", { text: foot })]));
      box.appendChild(row);
      return row;
    };
    var name = el("input", { class: "st-input", type: "text", placeholder: "Northwind Bank", "aria-label": "The estate's name" });
    var folder = el("input", { class: "st-input", type: "text", "aria-label": "Its folder", value: base + sep + "my-estate" });
    var touched = false;
    folder.addEventListener("input", function () { touched = true; });
    name.addEventListener("input", function () { if (!touched) folder.value = base + sep + slugOf(name.value); });
    var start = el("button", { class: "btn primary", type: "button", text: "Start it" });
    start.addEventListener("click", function () {
      start.disabled = true;
      api("/api/estate/start", { name: name.value, folder: folder.value }).then(function (card) {
        return estateOpened(card, "Started");
      }).catch(fail).then(function () { start.disabled = false; });
    });
    option("start", "i-plus", "Start a new estate", "Empty, in a folder of its own. The library and the diagrams come "
      + "with terrane; the records are yours.", [field("Name", name), field("Folder", folder, true)], start,
      "The same as terrane init: model.yaml, a README and an ignore file. Nothing else is written.");
    var url = el("input", { class: "st-input", type: "text", placeholder: "https://dev.azure.com/org/project/_git/estate",
      "aria-label": "The repository's address" });
    var into = el("input", { class: "st-input", type: "text", value: base, "aria-label": "The folder to clone into" });
    var join = el("button", { class: "btn", type: "button", text: "Clone and open" });
    join.addEventListener("click", function () {
      join.disabled = true;
      toast("ok", "Cloning", "Git may ask you to sign in, in a window of its own.");
      api("/api/estate/join", { url: url.value, into: into.value }).then(function (card) {
        return estateOpened(card, "Joined");
      }).catch(fail).then(function () { join.disabled = false; });
    });
    option("join", "i-link", "Join one your team keeps", "Clone its repository and fetch the governance it pins. Git "
      + "signs you in; terrane keeps no password.", [field("Repository", url, true), field("Into", into)], join,
      "The same as terrane connect.");
    var path = el("input", { class: "st-input", type: "text", placeholder: base + sep + "an-estate", "aria-label": "A folder that holds an estate" });
    var open = el("button", { class: "btn", type: "button", text: "Open" });
    open.addEventListener("click", function () { openEstate(path.value); });
    option("open", "i-folder-open", "Open one on this machine", "A folder that holds one: its 10_MODEL/model.yaml is "
      + "what the app looks for. The estate menu above the search lists the ones opened before.",
      [field("Folder", path, true)], open, "");
    var focusOn = { start: name, join: url, open: path }[state.projectFocus];
    if (focusOn) setTimeout(function () { focusOn.focus(); }, 0);
    state.projectFocus = null;
  }

  /* Home for an estate with nothing in it yet: the first hour, in order. */
  function firstHour(panel, o) {
    var main = el("div", { class: "st-main fh" }), side = el("aside", { class: "st-side" });
    panel.appendChild(el("div", { class: "st-body" }, [main, side]));
    var readOnly = !!window.__AAC_STATIC__;
    var step = function (n, title, text, now, extra) {
      main.appendChild(el("div", { class: "fh-step" + (now ? " is-now" : "") }, [
        el("span", { class: "fh-n", text: String(n) }),
        el("div", { class: "fh-col" }, [el("h2", { text: title }), el("p", { text: text })].concat(extra || [])),
      ]));
    };
    step(1, "Bring in your inventory", "A CSV or Excel export from the portfolio tool or the CMDB: names, owners, a "
      + "lifecycle. You see every record it would add before anything is written.", true,
      readOnly ? [] : [dropZone(), el("button", { class: "linkish small", type: "button", text: "A folder of metamodel CSVs instead",
        onclick: openImport })]);
    step(2, "See what the diagrams need", "Each diagram reads a few fields: Tiered Architecture a network zone, the "
      + "landscape a business domain. Once the records are in, the list says which and how many lack each, and sets one "
      + "on many records at once.", false, [el("button", { class: "btn small", type: "button", text: "What the diagrams need",
        onclick: function () { openNeeds(); } })]);
    step(3, "Draw", "New diagram places what the estate has, and parts from the library, on a canvas.", false,
      readOnly ? [] : [el("button", { class: "btn small", type: "button", text: "New diagram", onclick: function () { openCanvas(null); } })]);
    side.appendChild(el("h2", { text: "Where it is" }));
    side.appendChild(el("p", { class: "st-lede", text: ((o.estate && o.estate.path) || "This folder")
      + ", with model.yaml, a README and an ignore file. Commit it, and push it to the repository your team keeps it in." }));
    side.appendChild(el("p", { class: "st-lede", text: "The library and the views are the installed terrane's. Your own "
      + "come later, beside them." }));
  }

  /* ---- Settings -------------------------------------------------------------
   * Where this estate lives, where its records come from, and how the app
   * looks. Sources is built: an export from another tool, brought in through
   * a mapping in three steps that write nothing until Bring in, or held
   * against the model. Project says what the estate is and keeps credentials
   * out of its repository; Connections says what is not built yet rather
   * than offer a form that does nothing. */
  var SETTINGS_TABS = [["project", "Project"], ["sources", "Sources"], ["connections", "Connections"],
    ["appearance", "Appearance"]];

  function openSettings(tab) {
    if (state.src && state.src.answer && state.src.answer.token) discardUpload(state.src.answer.token);
    state.src = null;
    state.panel = "settings";
    state.settingsTab = tab || state.settingsTab || "sources";
    showPanel(true);
    syncUrl();
    renderSettings();
  }

  function settingsShell(title, lede, crumb) {
    var panel = $("dataPanel");
    panel.textContent = "";
    panel.classList.remove("is-table");
    var page = el("div", { class: "settings" });
    panel.appendChild(page);
    var text = el("div", { class: "st-title" }, [
      crumb ? el("p", { class: "crumb" }, crumb) : null,
      el("h1", { text: title }),
      lede ? el("p", { class: "lede", text: lede }) : null,
    ]);
    var head = el("div", { class: "st-head" }, [text]);
    page.appendChild(head);
    return { page: page, head: head };
  }

  function renderSettings() {
    var shell = settingsShell("Settings", "Where this estate lives, where its records come from, and how the app "
      + "looks. What you change here is written to the estate's own files, like everything else.");
    var tabs = el("div", { class: "st-tabs", role: "tablist", "aria-label": "Settings" });
    SETTINGS_TABS.forEach(function (t) {
      var on = state.settingsTab === t[0];
      tabs.appendChild(el("button", { type: "button", role: "tab", class: "st-tab", "aria-selected": on ? "true" : "false",
        onclick: function () { if (!on) { state.settingsTab = t[0]; syncUrl(); renderSettings(); } } }, [
        el("span", { text: t[1] }),
        t[0] === "sources" && state.sourcesCount ? el("span", { class: "n", text: String(state.sourcesCount) }) : null,
      ]));
    });
    shell.page.appendChild(tabs);
    var body = el("div", { class: "st-body" });
    shell.page.appendChild(body);
    ({ project: renderProjectTab, sources: renderSourcesTab, connections: renderConnectionsTab,
      appearance: renderAppearanceTab }[state.settingsTab] || renderSourcesTab)(body);
  }

  function sideNote(side, title, icon, text, accent) {
    side.appendChild(el("div", { class: "st-note-block" + (accent ? " accent" : "") }, [
      el("h3", {}, [icon ? svgIcon(icon) : null, el("span", { text: title })]),
      el("p", { text: text }),
    ]));
  }

  function countsText(counts) {
    return Object.keys(counts || {}).filter(function (k) { return counts[k]; }).map(function (k) {
      return counts[k] + " " + (counts[k] === 1 ? typeWord(k) : typeWord(k, true));
    }).join(" · ");
  }

  function shortDate(iso) {
    var d = new Date(String(iso || "") + "T00:00:00");
    return isNaN(d.getTime()) ? String(iso || "") : d.toLocaleDateString(undefined, { day: "numeric", month: "short" });
  }

  // ---- Sources ------------------------------------------------------------
  function renderSourcesTab(body) {
    var readOnly = !!window.__AAC_STATIC__;
    var main = el("div", { class: "st-main" });
    var side = el("aside", { class: "st-side" });
    body.appendChild(main);
    body.appendChild(side);
    main.appendChild(el("div", { class: "st-sec-head" }, [
      el("h2", { text: "Bring in an export" }),
      el("p", { class: "st-lede", text: "A CSV or Excel file from another tool: an application portfolio, an "
        + "inventory, a CMDB extract. Nothing is written until you have seen what it would change." }),
    ]));
    if (readOnly) {
      main.appendChild(el("p", { class: "st-callout", text: "This is a read-only copy of the app. Bringing in an "
        + "export is done in the app running on your machine, where the model's files are." }));
    } else {
      main.appendChild(dropZone());
    }
    main.appendChild(el("div", { class: "st-sec-head row" }, [
      el("h2", { text: "Saved sources" }),
      el("span", { class: "st-hint", text: "Each keeps its mapping, so the next export comes in with one click" }),
    ]));
    var list = el("div", { class: "src-list" }, [el("p", { class: "st-hint pad", text: "Reading the sources…" })]);
    main.appendChild(list);
    main.appendChild(el("p", { class: "st-foot" }, [
      svgIcon("i-terminal"),
      el("span", { text: "A mapping is a file beside its export, and the command line reads the same one: "
        + "terrane import csv --map." }),
      readOnly ? null : el("button", { type: "button", class: "linkish", text: "A folder of metamodel CSVs instead",
        onclick: openImport }),
    ]));
    api("/api/sources").then(function (d) {
      state.sourcesCount = d.sources.length;
      renderSettingsCount();
      list.textContent = "";
      if (!d.sources.length) {
        list.appendChild(el("p", { class: "st-hint pad", text: "None yet. A file you bring in can be kept here, "
          + "with its mapping, in " + d.folder + "." }));
        return;
      }
      d.sources.forEach(function (s) { list.appendChild(sourceRow(s, readOnly)); });
    }).catch(function (err) {
      list.textContent = "";
      list.appendChild(el("p", { class: "st-hint pad", text: err.message }));
    });
    side.appendChild(el("h2", { text: "Two kinds of source" }));
    sideNote(side, "Brings in", "i-arrow-down-to-line", "Its rows become records in the model, through a mapping: "
      + "which column is which field, and which of its words are the model's. You see every record it would add "
      + "before anything is written.", true);
    sideNote(side, "Compares", "i-compare", "Its rows are held against the model, and what differs is listed in "
      + "Checks. Nothing is written either way. A CMDB is this kind: the model says what should be, the CMDB what "
      + "was found.");
    side.appendChild(el("div", { class: "st-rule" }));
    sideNote(side, "A live connection", null, "Pulling from ServiceNow on a schedule rather than from an export "
      + "belongs under Connections, which is not built yet.");
  }

  function renderSettingsCount() {
    var tab = Array.prototype.filter.call(document.querySelectorAll(".st-tab"), function (b) {
      return b.textContent.indexOf("Sources") === 0;
    })[0];
    if (!tab) return;
    var n = tab.querySelector(".n");
    if (!n) { n = el("span", { class: "n" }); tab.appendChild(n); }
    n.textContent = state.sourcesCount ? String(state.sourcesCount) : "";
  }

  function dropZone() {
    var input = el("input", { type: "file", accept: ".csv,.xlsx", class: "sr-only", tabindex: "-1" });
    input.addEventListener("change", function () { if (input.files && input.files[0]) readUpload(input.files[0]); });
    var drop = el("div", { class: "drop", tabindex: "0", role: "button",
      "aria-label": "Choose a CSV or Excel file to bring in" }, [
      el("span", { class: "drop-badge" }, [svgIcon("i-file-up")]),
      el("strong", { text: "Drop a CSV or Excel file here" }),
      el("span", { class: "drop-or" }, [
        el("span", { text: "or" }),
        el("button", { type: "button", class: "btn small", onclick: function (e) { e.stopPropagation(); input.click(); } },
          [svgIcon("i-folder-open"), el("span", { text: "Choose a file" })]),
      ]),
      el("span", { class: "drop-hint", text: ".csv or .xlsx. A workbook's first sheet with a header row is read, "
        + "and you can pick another." }),
      input,
    ]);
    drop.addEventListener("click", function () { input.click(); });
    drop.addEventListener("keydown", function (e) {
      if (e.target === drop && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); input.click(); }
    });
    ["dragenter", "dragover"].forEach(function (name) {
      drop.addEventListener(name, function (e) { e.preventDefault(); drop.classList.add("over"); });
    });
    ["dragleave", "drop"].forEach(function (name) {
      drop.addEventListener(name, function () { drop.classList.remove("over"); });
    });
    drop.addEventListener("drop", function (e) {
      e.preventDefault();
      var file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (file) readUpload(file);
    });
    return drop;
  }

  function sourceRow(s, readOnly) {
    var brings = s.kind === "brings in";
    var what, stateText, when, ok = false;
    if (brings) {
      what = s.last ? countsText(s.last.added) : (s.description || ("Makes " + s.makes.map(function (k) {
        return typeWord(k, true);
      }).join(", ")));
      stateText = s.last ? (s.last.held ? s.last.held + " held back" : "Everything came in") : "Not brought in yet";
      ok = !!(s.last && !s.last.held);
      when = s.last ? "Brought in " + shortDate(s.last.when) : "";
    } else if (s.compared) {
      var c = s.compared.counts || {};
      what = [[c.ATTR_MISMATCH, "differ"], [c.CMDB_ONLY, "only in the CMDB"], [c.MODEL_ONLY, "only in the model"]]
        .filter(function (p) { return p[0]; }).map(function (p) { return p[0] + " " + p[1]; }).join(" · ")
        || "Nothing differs";
      stateText = "Never written";
      when = "Compared just now";
    } else {
      what = s.problem || "";
      stateText = "Not read";
      when = "";
    }
    var files = s.files.join(" · ") + (s.compared ? " · " + s.compared.records + " records" : "");
    var acts = el("div", { class: "src-acts" });
    var act = function (label, icon, go, enabled) {
      acts.appendChild(el("button", { type: "button", class: "btn small", disabled: enabled === false ? "disabled" : null,
        title: enabled === false ? "Done in the app running on your machine" : null, onclick: go },
        [svgIcon(icon), el("span", { text: label })]));
    };
    if (brings) {
      act(s.last ? "Bring in again" : "Bring in", "i-refresh", function () { againSource(s); }, !readOnly);
      if (s.simple) act("Mapping", "i-columns", function () { editSource(s); }, !readOnly);
    } else {
      act("Compare again", "i-refresh", function () { renderSettings(); });
      act("Open in Checks", "i-list-checks", function () { openDrift(s.export); });
    }
    return el("div", { class: "src-row" }, [
      el("span", { class: "src-icon" }, [svgIcon(brings ? "i-file-sheet" : "i-compare")]),
      el("div", { class: "src-text" }, [
        el("div", { class: "src-top" }, [
          el("strong", { text: s.name }),
          el("span", { class: "kind-chip" + (brings ? " accent" : ""), text: brings ? "Brings in" : "Compares" }),
        ]),
        el("span", { class: "src-files", text: files }),
        el("span", { class: "src-what", text: what }),
      ]),
      el("div", { class: "src-state" }, [
        el("strong", { class: ok ? "ok" : "", text: stateText }),
        when ? el("span", { text: when }) : null,
      ]),
      acts,
    ]);
  }

  // ---- Bringing one in ----------------------------------------------------
  function discardUpload(token) {
    api("/api/sources/discard", { token: token }).catch(function () {});
  }

  function readUpload(file) {
    if (!/\.(csv|xlsx)$/i.test(file.name)) {
      toast("warn", "Not a CSV or Excel file", file.name + " is neither; save it as .csv or .xlsx and choose it again.");
      return;
    }
    var reader = new FileReader();
    reader.onload = function () {
      var data = String(reader.result || "").replace(/^data:[^,]*,/, "");
      api("/api/sources/read", { name: file.name, data: data }).then(function (answer) {
        startSource(answer, null);
      }).catch(function (err) { toast("err", "Could not read " + file.name, err.message); });
    };
    reader.onerror = function () { toast("err", "Could not read " + file.name, "The browser could not open the file."); };
    reader.readAsDataURL(file);
  }

  function titleOf(file) {
    var stem = String(file || "").replace(/\.[^.]+$/, "").replace(/[_\-]+/g, " ").trim();
    return stem ? stem.charAt(0).toUpperCase() + stem.slice(1) : "Source";
  }

  function startSource(answer, kept) {
    var sug = answer.saved || answer.suggestion;
    var columns = {};
    Object.keys(sug.columns || {}).forEach(function (c) { columns[c] = [].concat(sug.columns[c]); });
    state.src = {
      answer: answer, step: "columns", kept: kept || null,
      choice: {
        kind: sug.kind, columns: columns, code: sug.code || null,
        prefix: sug.prefix || (answer.kinds[sug.kind] || {}).prefix,
        values: JSON.parse(JSON.stringify(sug.values || {})), defaults: JSON.parse(JSON.stringify(sug.defaults || {})),
        unitsFrom: sug.unitsFrom || null,
      },
      words: null, preview: null,
      keepName: answer.name || titleOf(answer.file), keepOn: true,
    };
    renderSource();
  }

  function againSource(s) {
    state.src = { again: s.id, title: s.name, step: "review", answer: { file: s.files.join(" · ") }, preview: null };
    renderSource();
  }

  function editSource(s) {
    api("/api/sources/read", { source: s.id }).then(function (answer) {
      startSource(answer, s.id);
    }).catch(function (err) { toast("err", "Could not open " + s.name, err.message); });
  }

  function leaveSource() {
    openSettings("sources");
  }

  function renderSource() {
    var src = state.src;
    if (!src) { renderSettings(); return; }
    ({ columns: renderColumnsStep, words: renderWordsStep, review: renderReviewStep }[src.step] || renderColumnsStep)();
  }

  var SOURCE_STEPS = [["file", "File"], ["columns", "Columns"], ["words", "Words"], ["review", "Review"]];

  function sourceShell(stepKey, lede) {
    var src = state.src;
    var crumb = [
      el("button", { type: "button", text: "Settings", onclick: function () { openSettings("sources"); } }),
      el("span", { class: "sep", text: "/" }),
      el("button", { type: "button", text: "Sources", onclick: leaveSource }),
      el("span", { class: "sep", text: "/" }),
      el("span", { text: src.again ? src.title : src.kept ? "Mapping" : "New source" }),
    ];
    var shell = settingsShell(src.again ? src.title : src.answer.file, lede, crumb);
    var at = SOURCE_STEPS.map(function (s) { return s[0]; }).indexOf(stepKey);
    var steps = el("ol", { class: "src-steps", "aria-label": "Steps" });
    SOURCE_STEPS.forEach(function (s, i) {
      var cls = i < at || (src.again && i < 3) ? "done" : i === at ? "now" : "next";
      steps.appendChild(el("li", { class: cls, "aria-current": cls === "now" ? "step" : null }, [
        el("span", { class: "num" }, cls === "done" ? [svgIcon("i-check")] : [el("span", { text: String(i + 1) })]),
        el("span", { text: s[1] }),
      ]));
    });
    shell.head.appendChild(steps);
    var body = el("div", { class: "st-body flow" });
    shell.page.appendChild(body);
    var bar = el("div", { class: "src-bar" });
    shell.page.appendChild(bar);
    return { body: body, bar: bar };
  }

  function barButtons(bar, back, next) {
    bar.appendChild(el("button", { type: "button", class: "btn", onclick: back.go },
      [svgIcon("i-arrow-left"), el("span", { text: back.label })]));
    bar.appendChild(el("span", { class: "grow" }));
    bar.appendChild(el("span", { class: "st-hint", text: next.hint || "Nothing is written yet" }));
    bar.appendChild(el("button", { type: "button", class: "btn", text: "Cancel", onclick: leaveSource }));
    bar.appendChild(el("button", { type: "button", class: "btn primary", disabled: next.disabled ? "disabled" : null,
      onclick: next.go }, [el("span", { text: next.label }), svgIcon(next.icon || "i-arrow-right")]));
  }

  function kindInfo() {
    var src = state.src;
    return src.answer.kinds[src.choice.kind] || { label: src.choice.kind, fields: [] };
  }

  function foldWord(text) { return String(text || "").replace(/\s+/g, " ").trim().toLowerCase(); }

  function toMatch(column, fieldName) {
    var info = kindInfo();
    var f = info.fields.filter(function (x) { return x.name === fieldName; })[0];
    if (!f || !f.enum) return 0;
    var words = f.enum.map(foldWord);
    return (column.values || []).filter(function (p) { return words.indexOf(foldWord(p[0])) === -1; }).length;
  }

  function enumTargets() {
    var src = state.src, info = kindInfo(), out = [];
    Object.keys(src.choice.columns).forEach(function (c) {
      src.choice.columns[c].forEach(function (t) {
        var f = info.fields.filter(function (x) { return x.name === t; })[0];
        if (f && f.enum) out.push(t);
      });
    });
    return out;
  }

  function needWords(then) {
    var src = state.src;
    if (src.words) { then(); return; }
    api("/api/sources/words", { token: src.answer.token, choice: src.choice }).then(function (w) {
      if (state.src !== src) return;
      src.words = w;
      then();
    }).catch(function (err) { toast("err", "Could not read the words", err.message); });
  }

  function choiceChanged() {
    state.src.words = null;
    state.src.preview = null;
    renderSource();
  }

  function fieldLabel(f, info) {
    return f.pk ? capFirst(info.label) + " id, as the file has it" : capFirst(fieldWord(f.name));
  }

  function renderColumnsStep() {
    var src = state.src, a = src.answer, ch = src.choice, info = kindInfo();
    var anyWords = enumTargets().length > 0;
    var s = sourceShell("columns", a.rows + " " + plural(a.rows, "row") + " and " + a.columns.length + " columns"
      + (a.sheet ? ", from the sheet " + a.sheet : "") + ". Say which column is which field; the next step matches "
      + "the file's words to the model's.");
    var main = el("div", { class: "st-main" }), side = el("aside", { class: "st-side" });
    s.body.appendChild(main);
    s.body.appendChild(side);

    var each = el("div", { class: "src-each" }, [el("span", { text: "Each row of this file is a" })]);
    var kindSel = el("select", { class: "src-select strong", "aria-label": "Kind of record" });
    Object.keys(a.kinds).forEach(function (k) {
      kindSel.appendChild(el("option", { value: k, text: capFirst(a.kinds[k].label), selected: k === ch.kind ? "selected" : null }));
    });
    kindSel.addEventListener("change", function () {
      api("/api/sources/read", { token: a.token, kind: kindSel.value }).then(function (answer) {
        answer.name = a.name;
        startSource(answer, src.kept);
      }).catch(function (err) { toast("err", "Could not read it as that", err.message); });
    });
    each.appendChild(kindSel);
    if (a.sheets && a.sheets.length > 1) {
      each.appendChild(el("span", { text: "on the sheet" }));
      var sheetSel = el("select", { class: "src-select", "aria-label": "Sheet" });
      a.sheets.forEach(function (n) { sheetSel.appendChild(el("option", { value: n, text: n, selected: n === a.sheet ? "selected" : null })); });
      sheetSel.addEventListener("change", function () {
        api("/api/sources/read", { token: a.token, sheet: sheetSel.value }).then(function (answer) {
          answer.name = a.name;
          startSource(answer, src.kept);
        }).catch(function (err) { toast("err", "Could not read that sheet", err.message); });
      });
      each.appendChild(sheetSel);
    }
    main.appendChild(each);
    main.appendChild(el("p", { class: "st-hint", text: src.kept
      ? "As the kept mapping says. Change any, and the next step shows what it brings in."
      : "Filled in from the column names: check each, and change any that is wrong." }));

    var table = el("div", { class: "src-table", role: "table" });
    table.appendChild(el("div", { class: "src-tr head", role: "row" }, [
      el("span", { role: "columnheader", text: "Column in the file" }),
      el("span", { role: "columnheader", text: "What it holds" }),
      el("span", { role: "columnheader", text: "Goes to" }),
    ]));
    a.columns.forEach(function (col) {
      var name = col.column;
      var targets = ch.code === name ? ["@code"] : (ch.columns[name] || []);
      var picks = el("div", { class: "src-goes" });
      var pick = function (value, index) {
        var sel = el("select", { class: "src-select" + (value ? "" : " out"), "aria-label": "What " + name + " fills" });
        sel.appendChild(el("option", { value: "", text: index ? "Nothing else" : "Left out" }));
        if (!index) sel.appendChild(el("option", { value: "@code", text: "Its own id: kept for matching", selected: value === "@code" ? "selected" : null }));
        info.fields.forEach(function (f) {
          sel.appendChild(el("option", { value: f.name, text: fieldLabel(f, info), selected: value === f.name ? "selected" : null }));
        });
        sel.addEventListener("change", function () {
          var v = sel.value;
          var list = (ch.columns[name] || []).slice();
          if (v === "@code") {
            if (ch.code && ch.code !== name) delete ch.columns[ch.code];
            ch.code = name;
            delete ch.columns[name];
          } else {
            if (ch.code === name) ch.code = null;
            // A field is filled from one column: taking it here lets it go there.
            Object.keys(ch.columns).forEach(function (c) {
              if (c !== name) ch.columns[c] = ch.columns[c].filter(function (t) { return t !== v; });
              if (!ch.columns[c].length) delete ch.columns[c];
            });
            if (v) list[index] = v; else list.splice(index, 1);
            list = list.filter(function (t, i) { return t && list.indexOf(t) === i; });
            if (list.length) ch.columns[name] = list; else delete ch.columns[name];
          }
          if (ch.unitsFrom === name && (ch.columns[name] || []).indexOf("owner_org_id") === -1) ch.unitsFrom = null;
          choiceChanged();
        });
        var row = el("span", { class: "src-pick" }, [sel]);
        var n = value && value !== "@code" ? toMatch(col, value) : 0;
        if (n) row.appendChild(el("span", { class: "match-chip", text: n + " to match" }));
        if (index) row.appendChild(el("button", { type: "button", class: "cmp-x", "aria-label": "Fill only one field", title: "Fill only one field", text: "×",
          onclick: function () { ch.columns[name].splice(index, 1); choiceChanged(); } }));
        picks.appendChild(row);
      };
      pick(targets[0] || "", 0);
      // A column can fill two fields: the sample's tier is its criticality
      // and its service tier. An empty second pick is one just asked for.
      if (targets.length > 1) pick(targets[1] || "", 1);
      else if (targets[0] && targets[0] !== "@code") {
        picks.appendChild(el("button", { type: "button", class: "linkish small", text: "+ fills another field too",
          onclick: function () { ch.columns[name] = ch.columns[name].concat([""]); renderSource(); } }));
      }
      var samples = (col.samples || []).join(" · ") + (col.distinct > 3 ? " · +" + (col.distinct - 3) : "");
      table.appendChild(el("div", { class: "src-tr", role: "row" }, [
        el("strong", { role: "cell", text: name }),
        el("span", { role: "cell", class: "src-sample", text: samples || "empty in every row" }),
        el("span", { role: "cell" }, [picks]),
      ]));
    });
    main.appendChild(table);

    // What a record of this kind needs, and where each comes from.
    var mappedFrom = {};
    Object.keys(ch.columns).forEach(function (c) { ch.columns[c].forEach(function (t) { if (t) mappedFrom[t] = c; }); });
    var pkField = info.fields.filter(function (f) { return f.pk; })[0];
    side.appendChild(el("h2", { text: "A " + info.label + " needs" }));
    var needs = info.fields.filter(function (f) { return f.required; });
    var missing = needs.filter(function (f) { return !mappedFrom[f.name] && !ch.defaults[f.name]; });
    side.appendChild(el("p", { class: "st-lede", text: "Without these a record loads but fails the checks. "
      + (missing.length ? missing.length + " not in this file yet." : "All are covered.") }));
    var list = el("ul", { class: "needs" });
    needs.forEach(function (f) {
      var from = mappedFrom[f.name];
      var item = el("li", { class: from || ch.defaults[f.name] ? "ok" : "missing" }, [
        el("span", { class: "tick" }, [svgIcon(from || ch.defaults[f.name] ? "i-check" : "i-x")]),
      ]);
      var text = el("div", {}, [el("strong", { text: capFirst(fieldWord(f.name)) })]);
      if (from) text.appendChild(el("span", { text: "from " + from }));
      else if (f.enum || f.ref) {
        var dsel = el("select", { class: "src-select small", "aria-label": "Every row's " + fieldWord(f.name) });
        dsel.appendChild(el("option", { value: "", text: "Not in this file: choose one for every row" }));
        var opts = f.enum ? f.enum.map(function (e) { return [e, e]; })
          : (state.index || []).filter(function (x) { return x.type === f.ref; })
            .sort(function (x, y) { return String(x.name).localeCompare(String(y.name)); })
            .map(function (x) { return [x.id, x.name || x.id]; });
        opts.forEach(function (o) { dsel.appendChild(el("option", { value: o[0], text: o[1], selected: ch.defaults[f.name] === o[0] ? "selected" : null })); });
        dsel.addEventListener("change", function () {
          if (dsel.value) ch.defaults[f.name] = dsel.value; else delete ch.defaults[f.name];
          choiceChanged();
        });
        text.appendChild(dsel);
      } else {
        text.appendChild(el("span", { class: "warn", text: "Not in this file: choose the column that holds it" }));
      }
      item.appendChild(text);
      list.appendChild(item);
    });
    var pkFrom = pkField && mappedFrom[pkField.name];
    var firstName = (a.columns.filter(function (c) { return c.column === mappedFrom.name; })[0] || {}).samples;
    var idText = pkFrom ? "from " + pkFrom
      : mappedFrom.name ? "made from the name: " + ch.prefix + String((firstName || [""])[0]).toUpperCase().replace(/[^A-Z0-9]+/g, "-").replace(/^-|-$/g, "")
      : ch.code ? "made from " + ch.code : "";
    list.appendChild(el("li", { class: idText ? "ok" : "missing" }, [
      el("span", { class: "tick" }, [svgIcon(idText ? "i-check" : "i-x")]),
      el("div", {}, [el("strong", { text: "Id" }), el("span", { text: idText || "map the name, or a column of ids" })]),
    ]));
    side.appendChild(list);

    var owner = mappedFrom.owner_org_id;
    if (owner && ch.kind !== "org_units") {
      var also = el("div", { class: "st-also" }, [el("h3", { text: "Also from this file" })]);
      var box = el("input", { type: "checkbox", id: "srcUnits", checked: ch.unitsFrom === owner ? "checked" : null });
      box.addEventListener("change", function () { ch.unitsAsked = true; ch.unitsFrom = box.checked ? owner : null; choiceChanged(); });
      var note = el("span", { class: "st-hint" });
      also.appendChild(el("label", { class: "st-check", for: "srcUnits" }, [box,
        el("span", { text: "Make an org unit of each name the " + owner + " column holds, one per name." })]));
      also.appendChild(note);
      side.appendChild(also);
      needWords(function () {
        var ref = (state.src.words.refs || []).filter(function (r) { return r.field === "owner_org_id"; })[0];
        if (!ref) return;
        // In an estate that holds none of the owners yet -- every new one --
        // leaving this off held back every row of the first import. Made
        // from the file's own names, shown in Review before anything is
        // written, and kept off once a person has said so.
        if (!ref.found && ref.missing.length && !ch.unitsFrom && !ch.unitsAsked) {
          ch.unitsFrom = owner;
          choiceChanged();
          return;
        }
        note.textContent = ref.missing.length
          ? ref.missing.length + " of its " + (ref.missing.length + ref.found) + " names are not org units in the model; "
            + (ch.unitsFrom ? "they are made." : "without this, their rows wait.")
          : "Every name is an org unit the model holds already.";
      });
    }

    var blocked = missing.some(function (f) { return !f.enum && !f.ref; }) || !idText;
    barButtons(s.bar, { label: "Back", go: leaveSource }, {
      label: anyWords ? "Next: match the words" : "Next: review", disabled: blocked,
      hint: blocked ? "Say where each needed field comes from first" : null,
      go: function () { src.step = anyWords ? "words" : "review"; renderSource(); },
    });
  }

  function renderWordsStep() {
    var src = state.src, ch = src.choice;
    if (!src.words) {
      var s0 = sourceShell("words", "Reading the file's words…");
      barButtons(s0.bar, { label: "Back", go: function () { src.step = "columns"; renderSource(); } },
        { label: "Next: review", disabled: true, go: function () {} });
      needWords(renderSource);
      return;
    }
    var s = sourceShell("words", "Which of the file's words is which of the model's. A word the model already uses "
      + "needs nothing; one left unmatched holds its rows back, and nothing is guessed.");
    var main = el("div", { class: "st-main" }), side = el("aside", { class: "st-side" });
    s.body.appendChild(main);
    s.body.appendChild(side);
    var open = 0, waiting = 0, firstOpen = null;
    (src.words.words || []).forEach(function (g) {
      ch.values[g.field] = ch.values[g.field] || {};
      var chosen = ch.values[g.field];
      var card = el("div", { class: "word-card" }, [
        el("div", { class: "word-head" }, [el("strong", { text: capFirst(fieldWord(g.field)) }),
          el("span", { text: "from " + g.column })]),
      ]);
      g.words.forEach(function (w) {
        var row = el("div", { class: "word-row" }, [
          el("span", { class: "word", text: w.word }),
          el("span", { class: "rows", text: w.rows + " " + plural(w.rows, "row") }),
          svgIcon("i-arrow-right"),
        ]);
        if (w.same) {
          row.appendChild(el("span", { class: "same", text: "Already the model's word" }));
        } else {
          var has = Object.prototype.hasOwnProperty.call(chosen, w.word);
          var sel = el("select", { class: "src-select" + (has ? "" : " open"), "aria-label": "The model's word for " + w.word });
          sel.appendChild(el("option", { value: "@none", text: "Choose a word…" }));
          g.enum.forEach(function (e) { sel.appendChild(el("option", { value: e, text: e, selected: chosen[w.word] === e ? "selected" : null })); });
          sel.appendChild(el("option", { value: "", text: "Leave it empty", selected: has && chosen[w.word] === "" ? "selected" : null }));
          sel.addEventListener("change", function () {
            if (sel.value === "@none") delete chosen[w.word]; else chosen[w.word] = sel.value;
            src.preview = null;
            renderSource();
          });
          row.appendChild(sel);
          if (!has) {
            open += 1;
            waiting += w.rows;
            firstOpen = firstOpen || g;
            row.classList.add("open");
            row.appendChild(el("span", { class: "waits", text: w.rows + " " + plural(w.rows, "row") + " wait for this" }));
          }
        }
        card.appendChild(row);
      });
      main.appendChild(card);
    });
    if (!(src.words.words || []).length) {
      main.appendChild(el("p", { class: "st-hint", text: "No column this file fills has a fixed list of words." }));
    }
    side.appendChild(el("h2", { text: open ? (open === 1 ? "One word left" : open + " words left") : "Every word has a match" }));
    if (open && firstOpen) {
      side.appendChild(el("p", { class: "st-lede", text: "Nothing is guessed: say which of the model's words each is, "
        + "or leave the field empty for those rows." }));
      side.appendChild(el("p", { class: "st-hint", text: "The model's words for " + fieldWord(firstOpen.field) }));
      side.appendChild(el("div", { class: "chips" }, firstOpen.enum.map(function (e) {
        return el("span", { class: "chip-word", text: e });
      })));
      side.appendChild(el("div", { class: "st-rule" }));
      sideNote(side, "If you go on now", null, waiting + " " + plural(waiting, "row") + " wait until "
        + (open === 1 ? "that word has" : "those words have") + " a match; bring the file in again after choosing, "
        + "and only those are written.");
    } else {
      side.appendChild(el("p", { class: "st-lede", text: "The next step shows every record bringing it in would write, "
        + "before anything is written." }));
    }
    barButtons(s.bar, { label: "Back", go: function () { src.step = "columns"; renderSource(); } },
      { label: "Next: review", go: function () { src.step = "review"; renderSource(); } });
  }

  function renderReviewStep() {
    var src = state.src;
    if (!src.preview) {
      var s0 = sourceShell("review", "Reading what bringing it in would write…");
      barButtons(s0.bar, { label: "Back", go: reviewBack }, { label: "Bring in", disabled: true, go: function () {} });
      var ask = src.again ? { source: src.again } : { token: src.answer.token, choice: src.choice };
      api("/api/sources/preview", ask).then(function (p) {
        if (state.src !== src) return;
        src.preview = p;
        renderSource();
      }).catch(function (err) {
        if (state.src !== src) return;
        toast("err", "Could not read what it would write", err.message);
        s0.body.appendChild(el("p", { class: "st-callout", text: err.message }));
      });
      return;
    }
    var p = src.preview;
    var added = Object.keys(p.counts).reduce(function (n, k) { return n + p.counts[k]; }, 0);
    var present = Object.keys(p.present).reduce(function (n, k) { return n + p.present[k].length; }, 0);
    var s = sourceShell("review", "Everything bringing it in would write, before it is written. Each record goes to "
      + "its own file in the model, and the change is undone like any other.");
    var main = el("div", { class: "st-main" }), side = el("aside", { class: "st-side" });
    s.body.appendChild(main);
    s.body.appendChild(side);
    var figs = el("div", { class: "figs" });
    [[added, added === 1 ? "record added" : "records added", countsText(p.counts) || "nothing new", true],
     [present, "already here", present ? "left as they are" : "nothing already here is touched", false],
     [p.heldRows, "held back", p.heldRows ? plural(p.heldRows, "row") + " wait: the reasons are below" : "every row has what it needs", false]]
      .forEach(function (f) {
        figs.appendChild(el("div", { class: "fig" + (f[3] ? " accent" : "") }, [
          el("div", { class: "fig-top" }, [el("strong", { text: String(f[0]) }), el("span", { text: f[1] })]),
          el("span", { class: "fig-sub", text: f[2] }),
        ]));
      });
    main.appendChild(figs);
    var names = {};
    (state.index || []).forEach(function (x) { names[x.id] = x.name; });
    var pkOf = function (k) { return ((state.schema && state.schema.entities[k]) || {}).pk; };
    Object.keys(p.added).forEach(function (k) {
      p.added[k].forEach(function (r) { names[r[pkOf(k)]] = r.name; });
    });
    var list = el("div", { class: "added" });
    Object.keys(p.added).forEach(function (k) {
      var rows = p.added[k];
      list.appendChild(el("div", { class: "added-head", text: capFirst(typeWord(k, true)) + " · " + rows.length }));
      rows.slice(0, 60).forEach(function (r) {
        var bits = ["status", "criticality", "hosting", "protocol", "classification"].filter(function (f) { return r[f]; })
          .map(function (f) { return r[f]; });
        var owner = r.owner_org_id ? (names[r.owner_org_id] || r.owner_org_id) : "";
        var ends = r.source_system_id ? (names[r.source_system_id] || r.source_system_id) + " → "
          + (names[r.target_system_id] || r.target_system_id) : "";
        list.appendChild(el("div", { class: "added-row" }, [
          svgIcon("i-plus"),
          el("span", { class: "nm", text: r.name || r[pkOf(k)] }),
          el("span", { class: "bits", text: bits.join(" · ") }),
          el("span", { class: "own", text: ends || owner }),
        ]));
      });
      if (rows.length > 60) list.appendChild(el("div", { class: "added-row more", text: "and " + (rows.length - 60) + " more" }));
    });
    if (!added) list.appendChild(el("p", { class: "st-hint pad", text: "Nothing new: every row is in the model already, or waits below." }));
    main.appendChild(list);
    var notes = function (title, lines) {
      if (!lines.length) return;
      main.appendChild(el("div", { class: "src-notes" }, [el("h3", { text: title })].concat(
        lines.map(function (l) { return el("p", { text: l }); }))));
    };
    notes("Rows that wait", p.held);
    notes("Not written", p.conflicts);
    notes("Left out", p.skipped);

    var errors = p.findings.filter(function (f) { return f.severity === "error"; });
    sideNote(side, "Checked first", "i-list-checks", !p.findings.length
      ? "The checks have run on what would be written: nothing new to fix."
      : "The checks have run on what would be written. Once it is in, Checks will say "
        + (errors.length ? errors.length + " new " + plural(errors.length, "error") + " and " : "")
        + (p.findings.length - errors.length) + " new " + plural(p.findings.length - errors.length, "warning") + ":", !errors.length);
    if (p.findings.length) {
      side.appendChild(el("ul", { class: "found" }, p.findings.slice(0, 8).map(function (f) {
        return el("li", { class: f.severity, text: f.message });
      }).concat(p.findings.length > 8 ? [el("li", { text: "and " + (p.findings.length - 8) + " more" })] : [])));
    }
    if (!src.again) {
      side.appendChild(el("div", { class: "st-rule" }));
      var keepBox = el("input", { type: "checkbox", id: "srcKeep", checked: src.keepOn ? "checked" : null });
      keepBox.addEventListener("change", function () { src.keepOn = keepBox.checked; nameIn.disabled = !keepBox.checked; });
      var nameIn = el("input", { type: "text", class: "st-input", value: src.keepName, "aria-label": "The source's name",
        disabled: src.keepOn ? null : "disabled" });
      nameIn.addEventListener("input", function () { src.keepName = nameIn.value; });
      side.appendChild(el("div", { class: "st-keep" }, [
        el("label", { class: "st-check", for: "srcKeep" }, [keepBox, el("strong", { text: "Keep this as a source" })]),
        nameIn,
        el("p", { class: "st-hint", text: "Its export and mapping go in 60_SOURCES beside the model, so the next "
          + "export comes in with one click." }),
      ]));
    }
    barButtons(s.bar, { label: "Back", go: reviewBack }, {
      label: added ? "Bring in " + added + " " + plural(added, "record") : "Nothing to bring in",
      icon: "i-arrow-down-to-line", disabled: !added, go: bringIn,
    });
  }

  function reviewBack() {
    var src = state.src;
    if (src.again) { leaveSource(); return; }
    src.step = enumTargets().length ? "words" : "columns";
    renderSource();
  }

  function bringIn() {
    var src = state.src;
    var body = src.again ? { source: src.again }
      : { token: src.answer.token, choice: src.choice, keep: src.keepOn ? (src.keepName || "").trim() : "" };
    if (!src.again && src.keepOn && !body.keep) { toast("warn", "A kept source has a name", "Name it, or untick Keep."); return; }
    api("/api/sources/bring-in", body).then(function (res) {
      var total = Object.keys(res.imported).reduce(function (n, k) { return n + res.imported[k]; }, 0);
      var waits = res.held.length ? res.held.length + " " + plural(res.held.length, "reason") + " rows wait" : "";
      toast(waits || res.conflictCount ? "warn" : "ok", "Brought in " + total + " " + plural(total, "record"),
        [countsText(res.imported), waits, res.source ? "kept in " + "60_SOURCES/" + res.source : ""]
          .filter(Boolean).join(" · "));
      state.src = null;
      return refresh();
    }).catch(function (err) { toast("err", "Could not bring it in", err.message); });
  }

  // ---- Project, Connections, Appearance -------------------------------------
  function renderProjectTab(body) {
    var main = el("div", { class: "st-main" }), side = el("aside", { class: "st-side" });
    body.appendChild(main);
    body.appendChild(side);
    main.appendChild(el("p", { class: "st-hint", text: "Reading the estate…" }));
    api("/api/project").then(function (p) {
      main.textContent = "";
      main.appendChild(el("div", { class: "st-sec-head" }, [el("h2", { text: "This estate" }),
        p.description ? el("p", { class: "st-lede", text: p.description }) : null]));
      var facts = [
        ["Name", p.name],
        ["Folder", p.path],
        ["Repository", p.git && p.git.branch ? (p.git.remote || "a repository with no remote") + " · on " + p.git.branch : "not a git repository"],
        ["Library and views", p.library === "package" ? "the installed terrane's" + (p.requires ? ", " + p.requires : "") : "this repository's own folders"],
        ["A library of its own", p.libraryPaths.length ? p.libraryPaths.join(", ") : "none"],
        ["Governance", p.governance ? p.governance.repository + " at " + p.governance.ref : "not pinned to a governance repository"],
      ];
      main.appendChild(el("dl", { class: "facts" }, facts.reduce(function (out, f) {
        return out.concat([el("dt", { text: f[0] }), el("dd", { text: f[1] })]);
      }, [])));
      var guard = el("div", { class: "st-callout" + (p.secretsKeptOut ? " ok" : " warn") });
      if (p.secretsKeptOut) {
        guard.appendChild(el("p", { text: "The ignore file keeps credentials out: .env files, keys and certificates are "
          + "never committed." }));
      } else {
        guard.appendChild(el("p", { text: "The ignore file does not keep credentials out: "
          + p.secretsMissing.filter(function (x) { return x.charAt(0) !== "!"; }).join(", ")
          + " could be committed by mistake." }));
        if (!window.__AAC_STATIC__) {
          guard.appendChild(el("button", { type: "button", class: "btn small", text: "Add them to the ignore file",
            onclick: function () {
              api("/api/project/guard", {}).then(function () {
                toast("ok", "Credentials kept out", ".gitignore now leaves .env files and keys out.");
                renderSettings();
              }).catch(fail);
            } }));
        }
      }
      main.appendChild(guard);
      if (!window.__AAC_STATIC__) anotherEstate(main, p);
    }).catch(function (err) { main.textContent = ""; main.appendChild(el("p", { class: "st-hint", text: err.message })); });
    side.appendChild(el("h2", { text: "Once it has started" }));
    [["1", "Bring in your inventory", "A CSV or Excel export from the portfolio tool or the CMDB. You see every record it "
      + "would add before anything is written."],
     ["2", "See what the diagrams need", "Each diagram reads a few fields. The list says which, and how many records lack each."],
     ["3", "Fill a field on many at once", "Network zone on every on-premise system in one save, written into each record's own file."]]
      .forEach(function (s) {
        side.appendChild(el("div", { class: "est-step" }, [el("span", { class: "fh-n small", text: s[0] }),
          el("div", {}, [el("strong", { text: s[1] }), el("p", { text: s[2] })])]));
      });
    side.appendChild(el("p", { class: "st-hint", text: "Taking the sample out of this repository instead is terrane clear, "
      + "from a terminal: it says what it would remove before it removes anything." }));
  }

  function renderConnectionsTab(body) {
    var main = el("div", { class: "st-main" }), side = el("aside", { class: "st-side" });
    body.appendChild(main);
    body.appendChild(side);
    main.appendChild(el("div", { class: "st-sec-head" }, [
      el("h2", { text: "Connections" }),
      el("p", { class: "st-lede", text: "A live pull from another tool, ServiceNow first, on a button or a schedule "
        + "rather than from an export. Not built yet." }),
    ]));
    main.appendChild(el("div", { class: "st-callout" }, [
      el("p", { text: "Until then, a CMDB export brought in under Sources compares the same way, and nothing is "
        + "written to either side." }),
      el("button", { type: "button", class: "btn small", text: "Go to Sources", onclick: function () {
        state.settingsTab = "sources"; syncUrl(); renderSettings();
      } }),
    ]));
    side.appendChild(el("h2", { text: "Credentials" }));
    sideNote(side, "Never in the repository", "i-shield", "A connection's secret is never written to the estate's "
      + "files and never kept beside them. The estate names where the secret lives; the secret stays there.", true);
    sideNote(side, "Read when it is used", null, "From an environment variable, or from a secrets manager: Azure "
      + "Key Vault, AWS Secrets Manager or HashiCorp Vault, signed in to as the person running the app.");
  }

  function renderAppearanceTab(body) {
    var main = el("div", { class: "st-main" });
    body.appendChild(main);
    main.appendChild(el("div", { class: "st-sec-head" }, [
      el("h2", { text: "Tone" }),
      el("p", { class: "st-lede", text: "The app's colors and the diagrams' palette together. Kept in this browser; "
        + "tone= in the address asks for one without changing it." }),
    ]));
    var row = el("div", { class: "tones" });
    [["stone", "Stone", "Warm grays, a teal accent, a light sidebar."],
     ["graphite", "Graphite", "Neutral grays, an amber accent, a dark sidebar."]].forEach(function (t) {
      var on = tone() === t[0];
      row.appendChild(el("button", { type: "button", class: "tone-card t-" + t[0], "aria-pressed": on ? "true" : "false",
        onclick: function () { setTone(t[0]).then(function () { if (state.panel === "settings") renderSettings(); }); } }, [
        el("span", { class: "tone-strip" }, [el("i"), el("i"), el("i"), el("i")]),
        el("strong", { text: t[1] }),
        el("span", { text: t[2] }),
      ]));
    });
    main.appendChild(row);

    main.appendChild(el("div", { class: "st-rule" }));
    main.appendChild(el("div", { class: "st-sec-head" }, [
      el("h2", { text: "Notes on a drawing" }),
      el("p", { class: "st-lede", text: "Kept in this browser." }),
    ]));
    var noteBox = el("input", { type: "checkbox", id: "stReadNote" });
    noteBox.checked = !readNoteOff();
    noteBox.addEventListener("change", function () { setReadNote(noteBox.checked); });
    main.appendChild(el("label", { class: "st-check", for: "stReadNote" }, [noteBox,
      el("span", { text: "Say when a drawing shown whole is too small to read, with the way to a size it reads at." })]));
  }

  function openImport() {
    openDrawer("Import", "metamodel v2 CSVs", function (body) {
      body.appendChild(el("p", { class: "explain", text:
        "Point this at a folder of metamodel v2 CSVs — the layout `terrane export csv` writes. " +
        "Records already in the model are reported and left alone, never silently replaced." }));
      body.appendChild(el("div", { class: "field mono-in" }, [
        el("label", { for: "f__src" }, ["source folder"]),
        el("input", { id: "f__src", type: "text", value: "90_EXAMPLE/csv" }),
      ]));
      body.appendChild(el("div", { class: "field" }, [
        el("label", { for: "f__ow" }, [
          el("input", { id: "f__ow", type: "checkbox", style: "width:auto;margin-right:7px" }),
          "Overwrite records already in the model",
        ]),
      ]));
    }, function () {
      var body = $("drawerBody");
      return api("/api/import", {
        source: body.querySelector("#f__src").value.trim(),
        overwrite: body.querySelector("#f__ow").checked,
      }).then(function (res) {
        var total = Object.keys(res.imported).reduce(function (a, k) { return a + res.imported[k]; }, 0);
        toast(res.conflictCount ? "warn" : "ok", "Imported " + total + " records",
          res.conflictCount ? res.conflictCount + " already existed and were left alone"
                            : res.filesWritten + " files written");
        refresh();
        return true;
      });
    });
  }

  // ---- lifecycle --------------------------------------------------------

  function refresh() {
    return api("/api/overview").then(function (o) {
      if (o.tone && o.tone !== tone() && !storedTone() && !toneFromUrl()) {
        document.documentElement.setAttribute("data-tone", o.tone);
        syncToneSwitch();
        readDrawColors();
        return refresh();
      }
      state.overview = o;
      $("modelName").textContent = o.modelName;
      renderFacts(o);
      var fromUrl = readUrl();
      var known = function (id) {
        return o.views.some(function (v) { return v.viewId === id; });
      };
      var wanted = state.viewId && known(state.viewId)
        ? state.viewId
        : (fromUrl.view && known(fromUrl.view)
            ? fromUrl.view
            : (o.views.filter(function (v) { return v.ok; })[0] || o.views[0] || {}).viewId);
      if (fromUrl.id && !state.selectedId) state.selectedId = fromUrl.id;
      // A subject in the address bar is the subject drawn: a link to one
      // capability's diagram has to land on that capability.
      Object.keys(fromUrl).forEach(function (key) {
        if (key.indexOf("p_") === 0 && fromUrl[key]) state.subject[key.slice(2)] = fromUrl[key];
      });
      // selectView clears the subject when the view changes, and on first
      // load it always changes; naming the view first keeps the subject.
      if (Object.keys(state.subject).length && wanted) state.viewId = wanted;
      renderViewList(o);
      loadIndex();
      if (o.empty && !window.location.hash.replace(/^#(home)?$/, "")) {
        state.viewId = wanted;
        openStart();
      } else if (o.empty) {
        $("stageEmpty").hidden = false;
        $("emptyWhy").textContent = "The model is empty. Import an existing inventory, or create a product from an archetype.";
        $("viewTitle").textContent = "Empty model";
        $("viewDesc").textContent = "";
        $("viewMeta").textContent = "";
        if (state.cy) { state.cy.destroy(); state.cy = null; }
        $("tiles").hidden = true;
        $("cy").hidden = false;
        $("legend").textContent = "";
        state.lastGraph = null;
        renderBrief();
      } else if (fromUrl.draw !== undefined) {
        // A refresh while drawing redraws the canvas rather than reopening it.
        if (cv) canvasDraw(); else { state.viewId = wanted; openCanvas(fromUrl.draw || null); }
      } else if (fromUrl.guide !== undefined) {
        state.viewId = wanted;
        openGuide();
      } else if (fromUrl.settings !== undefined) {
        state.viewId = wanted;
        openSettings(fromUrl.tab || "sources");
      } else if (fromUrl.needs !== undefined) {
        state.viewId = wanted;
        openNeeds();
      } else if (fromUrl.set !== undefined && fromUrl.type && fromUrl.field) {
        state.viewId = wanted;
        openSetMany({ type: fromUrl.type, field: fromUrl.field, view: fromUrl.of || null, subject: fromUrl.subject || null });
      } else if (fromUrl.diagrams !== undefined) {
        state.viewId = wanted;
        openDiagrams(fromUrl.layer || "All");
      } else if (isPageHash(fromUrl)) {
        state.viewId = wanted;
        openPageFrom(fromUrl);
      } else if (fromUrl.home !== undefined || !window.location.hash) {
        // Arriving with no destination in mind is the common case.
        state.viewId = wanted;
        openStart();
      } else if (fromUrl.focus) {
        // A shared focus link should land on the neighborhood, not on the view
        // behind it, which is not what the person sending it meant.
        state.viewId = wanted;
        showFocus(fromUrl.focus, Number(fromUrl.depth) || 1);
      } else if (wanted) {
        selectView(wanted);
      }
      return o;
    });
  }

  function zoomStep(factor) {
    if (tilesShown()) { setTileZoom(state.tileZoom * factor); return; }
    if (!state.cy) return;
    var rect = state.cy.container().getBoundingClientRect();
    state.cy.zoom({
      level: state.cy.zoom() * factor,
      renderedPosition: { x: rect.width / 2, y: rect.height / 2 },
    });
  }

  function syncToneSwitch() {
    Array.prototype.forEach.call(document.querySelectorAll("#toneSwitch button"), function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-tone") === tone() ? "true" : "false");
    });
  }

  /* A new tone repaints the chrome at once, through the stylesheet, and
   * asks the server again for what it draws: the overview's swatches and
   * whatever is on screen, in the new tone's palette. */
  function setTone(next, keep) {
    if (TONES.indexOf(next) === -1 || next === tone()) return Promise.resolve();
    document.documentElement.setAttribute("data-tone", next);
    if (keep !== false) {
      try { localStorage.setItem(TONE_KEY, next); } catch (err) { /* private mode */ }
    }
    syncToneSwitch();
    readDrawColors();
    MINIS = {};
    var panel = state.panel;
    return api("/api/overview").then(function (o) {
      state.overview = o;
      renderViewList(o);
      if (panel === "start") openStart();
      else if (panel === "diagrams") openDiagrams();
      else if (panel === "flows") openFlows(state.flowId);
      else if (panel === "settings") openSettings(state.settingsTab);
      else if (panel === "needs") openNeeds();
      else if (panel === "setmany" && state.setMany) openSetMany(state.setMany.ask);
      else if (!panel && state.focus) showFocus(state.focus.id, state.focus.depth);
      else if ((!panel || panel === "report") && state.viewId) selectView(state.viewId);
    }).catch(fail);
  }

  function boot() {
    readDrawColors();
    $("btnChecks").addEventListener("click", function () { openValidate(); });
    $("btnSource").addEventListener("click", openSource);
    $("btnHome").addEventListener("click", openStart);
    $("btnEstate").addEventListener("click", function () { estateMenu($("btnEstate")); });
    $("btnSettings").addEventListener("click", function () { openSettings(); });
    $("btnDiagrams").addEventListener("click", function () { openDiagrams("All"); });
    $("btnData").addEventListener("click", function () { openData(null); });
    $("btnComponents").addEventListener("click", function () { openLibrary(null); });
    $("btnEditView").addEventListener("click", function () {
      if (state.focus) {
        // A focus view has no file. Offering to edit one would be a lie.
        toast("warn", "A focus view has no file",
          "It is built on request. Leave focus to edit an authored view.");
        return;
      }
      var listed = ((state.overview && state.overview.views) || []).filter(function (v) {
        return v.viewId === state.viewId;
      })[0];
      if (listed && listed.canvas && !window.__AAC_STATIC__) { openCanvas(state.viewId); return; }
      openViewComposer(state.viewId);
    });
    $("btnFocusExit").addEventListener("click", exitFocus);

    // The canvas's tools, its empty state, and dropping onto the sheet.
    $("cvAdd").addEventListener("click", function () {
      if ($("cvPicker").hidden || $("cvBoundary").getAttribute("aria-pressed") === "true") openCanvasPicker("all");
      else closeCanvasPicker();
    });
    $("cvSelect").addEventListener("click", function () { setCanvasTool("select"); });
    $("cvConnect").addEventListener("click", function () { setCanvasTool(cv && cv.tool === "connect" ? "select" : "connect"); });
    $("cvBoundary").addEventListener("click", function () {
      if (!$("cvPicker").hidden && $("cvBoundary").getAttribute("aria-pressed") === "true") closeCanvasPicker();
      else openCanvasPicker("estate", true);
    });
    $("cvFromLibrary").addEventListener("click", function () { openCanvasPicker("library"); });
    $("cvFromEstate").addEventListener("click", function () { openCanvasPicker("estate"); });
    $("mapSheet").addEventListener("dragover", canvasDragOver);
    $("mapSheet").addEventListener("drop", canvasDrop);
    $("mapSheet").addEventListener("dragleave", function (e) {
      if (!$("mapSheet").contains(e.relatedTarget)) {
        if (state.cy) state.cy.nodes(".drop-into").removeClass("drop-into");
        $("cvTip").hidden = true;
      }
    });
    document.addEventListener("mousedown", function (e) {
      var pick = $("cvPicker");
      if (pick.hidden || pick.contains(e.target) || $("cvAdd").contains(e.target)
          || $("cvBoundary").contains(e.target)) return;
      closeCanvasPicker();
    });
    $("btnHelp").addEventListener("click", openGuide);
    sketchLoad();
    $("btnSketch").addEventListener("click", drawSketch);
    // The drawing's own menu, not the browser's, over a box; and it goes
    // when anything else is touched.
    $("cy").addEventListener("contextmenu", function (e) { e.preventDefault(); });
    document.addEventListener("mousedown", function (e) {
      var menu = $("ctxMenu");
      if (menu && !menu.contains(e.target)) closeContextMenu();
    }, true);
    window.addEventListener("resize", closeContextMenu);
    $("cy").addEventListener("wheel", closeContextMenu, { passive: true });
    $("btnSketchDraw").addEventListener("click", drawSketch);
    $("btnSketchExit").addEventListener("click", exitSketch);
    $("btnSketchScreen").addEventListener("click", sketchAddScreen);
    $("btnSketchExpand").addEventListener("click", function () {
      if (state.selectedId) openSketchExpand(state.selectedId);
    });
    $("btnSketchView").addEventListener("click", openSketchView);
    $("btnSketchModule").addEventListener("click", openSketchModule);
    $("btnSketchNew").addEventListener("click", openSketchNew);
    $("btnSketchConnect").addEventListener("click", openSketchConnect);
    $("btnSketchClear").addEventListener("click", function () {
      var drawing = inSketchMode();
      state.sketch = [];
      sketchStore();
      if (drawing) exitSketch();
    });
    $("btnFocusIn").addEventListener("click", function () {
      if (state.focus) showFocus(state.focus.id, state.focus.depth + 1);
    });
    $("btnFocusOut").addEventListener("click", function () {
      if (state.focus) showFocus(state.focus.id, state.focus.depth - 1);
    });
    $("btnNew").addEventListener("click", function (e) { e.stopPropagation(); toggleNewMenu(); });
    document.addEventListener("mousedown", function (e) {
      var menu = $("newMenu");
      if (menu && !menu.hidden && !menu.contains(e.target) && e.target !== $("btnNew")
          && !$("btnNew").contains(e.target)) closeNewMenu();
    });
    window.addEventListener("resize", closeNewMenu);
    // The tone: the page's colors and the drawings' palette at once.
    syncToneSwitch();
    Array.prototype.forEach.call(document.querySelectorAll("#toneSwitch button"), function (b) {
      b.addEventListener("click", function () { setTone(b.getAttribute("data-tone")); });
    });
    $("btnExportPng").addEventListener("click", function () { $("btnPng").click(); });
    $("btnNewEmpty").addEventListener("click", openArchetypePicker);
    $("btnImportEmpty").addEventListener("click", function () { openSettings("sources"); });
    $("btnJump").addEventListener("click", function () { openPalette(); });
    document.addEventListener("click", function (e) {
      ["moreMenu", "exportMenu", "actsMenu"].forEach(function (id) {
        var menu = $(id);
        if (menu && menu.open && !menu.contains(e.target)) menu.open = false;
      });
    });
    ["btnFitW", "btnSource", "btnEditView", "btnExportPng", "btnSketch"].forEach(function (id) {
      $(id).addEventListener("click", function () {
        ["moreMenu", "exportMenu", "actsMenu"].forEach(function (m) { $(m).open = false; });
      });
    });
    $("jumpKey").textContent = /Mac|iPhone|iPad/.test(navigator.platform || "") ? "\u2318K" : "Ctrl K";
    $("paletteBox").addEventListener("input", function () { pal.at = 0; renderPalette(); });
    $("paletteBox").addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown") { e.preventDefault(); pal.at = Math.min(pal.hits.length - 1, pal.at + 1); markRow(); }
      else if (e.key === "ArrowUp") { e.preventDefault(); pal.at = Math.max(0, pal.at - 1); markRow(); }
      else if (e.key === "Enter") { e.preventDefault(); if (pal.pick) pal.pick(pal.at); }
    });
    $("palette").addEventListener("mousedown", function (e) { if (e.target === $("palette")) closePalette(); });
    $("btnFit").addEventListener("click", function () {
      if (tilesShown()) { fitTiles(); return; }
      if (state.cy) fitSheet(state.cy, 26);
    });
    // The overview: press a part of it to go there, drag to move along.
    (function () {
      var pic = $("overviewPic"), down = false;
      function go(e) {
        var r = pic.getBoundingClientRect();
        overviewGo(e.clientX - r.left, e.clientY - r.top);
      }
      pic.addEventListener("pointerdown", function (e) { down = true; pic.setPointerCapture(e.pointerId); go(e); });
      pic.addEventListener("pointermove", function (e) { if (down) go(e); });
      pic.addEventListener("pointerup", function () { down = false; });
      pic.addEventListener("pointercancel", function () { down = false; });
    })();
    $("btnWhole").addEventListener("click", function () { $("btnFit").click(); });
    // The button says the size it goes to, from the one number that decides it.
    $("btnReadSize").querySelector("span").textContent = "Read at " + Math.round(READ_ZOOM * 100) + "%";
    $("btnReadSize").addEventListener("click", function () { returning = null; if (state.cy) openReadable(state.cy); });
    $("btnReadClose").addEventListener("click", function () {
      overview.closedFor = state.cy;
      $("readPrompt").hidden = true;
    });
    $("btnReadNever").addEventListener("click", function () {
      overview.closedFor = state.cy;
      setReadNote(false);
      toast("ok", "That note will not show again", "Settings, Appearance brings it back");
    });
    // Labels: every connection's label on, or none. The drawing's density
    // decides until this is pressed; the choice holds until the view changes.
    $("btnLabels").addEventListener("click", function () {
      if (!state.cy) return;
      state.labels = this.getAttribute("aria-pressed") !== "true";
      placeEdgeLabels(state.cy);
      if (state.lastGraph) renderLegend(state.lastGraph);
    });
    // Fit width: a tall drawing takes the sheet's width and scrolls for the
    // rest, instead of shrinking until its labels go. The system context is
    // twice as tall as it is wide and fit at 43% in a laptop sheet, with two
    // thirds of the width empty either side. Capped so a narrow drawing is
    // not blown up past the size it reads at.
    $("btnFitW").addEventListener("click", function () {
      if (tilesShown()) { setTileZoom(1); $("tiles").scrollTop = 0; return; }
      if (!state.cy) return;
      var bb = state.cy.elements().boundingBox({ includeLabels: false });
      var pad = 26;
      if (!bb.w) return;
      var zoom = Math.min(1.25, (state.cy.width() - 2 * pad) / bb.w);
      state.cy.zoom(zoom);
      state.cy.pan({ x: pad - bb.x1 * zoom, y: pad - bb.y1 * zoom });
    });
    $("btnZoomIn").addEventListener("click", function () { zoomStep(1.25); });
    $("btnZoomOut").addEventListener("click", function () { zoomStep(0.8); });
    $("viewDesc").addEventListener("click", function () { this.classList.toggle("open"); });
    $("btnPng").addEventListener("click", function () {
      if (!state.cy && !tilesShown()) return;
      var name = (state.focus ? "focus-" + state.focus.id : state.viewId || "view") + ".png";
      exportPng(state.cy, state.lastGraph, name);
    });
    // A layout choice redraws the same graph; "Auto" hands the choice back
    // to the view. Either way the selection survives.
    $("layoutPicker").addEventListener("change", function () {
      if (!state.lastGraph || /^(report|timeline)$/.test(state.lastGraph.kind)) return;
      var keep = state.selectedId;
      drawGraph(state.lastGraph);
      if (keep) highlight(keep);
    });

    // Keyboard on the canvas: arrows walk the nodes in reading order, Enter
    // opens the one under the cursor, Escape lets go.
    $("cy").addEventListener("keydown", function (e) {
      if (!state.cy) return;
      if ((e.key === "Delete" || e.key === "Backspace") && state.selectedId && drawnHere(state.selectedId)) {
        if (!viewEditable()) return;
        e.preventDefault();
        changeMembership({ hide: [state.selectedId] });
        return;
      }
      if ((e.key === "ContextMenu" || (e.shiftKey && e.key === "F10")) && state.selectedId) {
        e.preventDefault();
        contextMenuAtNode(state.selectedId);
        return;
      }
      var keys = ["ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp", "Enter", "Escape"];
      if (keys.indexOf(e.key) === -1) return;
      e.preventDefault();
      if (e.key === "Escape") { clearSelection(); return; }
      var nodes = state.cy.nodes().filter(function (n) { return !n.data("isGroup"); })
        .sort(function (a, b) {
          var pa = a.position(), pb = b.position();
          return Math.round(pa.y / 40) - Math.round(pb.y / 40) || pa.x - pb.x;
        });
      if (!nodes.length) return;
      var index = -1;
      nodes.forEach(function (n, i) { if (n.id() === state.selectedId) index = i; });
      if (e.key === "Enter") {
        if (index >= 0) showEntity(nodes[index].id());
        return;
      }
      var forward = e.key === "ArrowRight" || e.key === "ArrowDown";
      var next = index === -1 ? 0 : (index + (forward ? 1 : nodes.length - 1)) % nodes.length;
      var node = nodes[next];
      state.selectedId = node.id();
      highlight(node.id());
      syncUrl();
      state.cy.animate({ center: { eles: node }, duration: 120 });
    });

    // Rail and inspector fold away so the drawing can have the width. The
    // choice is remembered per browser; it is a working preference, not state.
    function panelToggle(btnId, cls, key) {
      var btn = $(btnId);
      var shell = document.querySelector(".shell");
      var shut = false;
      try { shut = localStorage.getItem(key) === "1"; } catch (err) { shut = false; }
      function apply() {
        shell.classList.toggle(cls, shut);
        btn.setAttribute("aria-pressed", shut ? "false" : "true");
        if (state.cy) { state.cy.resize(); openReadable(state.cy); }
      }
      btn.addEventListener("click", function () {
        shut = !shut;
        returning = null;
        try { localStorage.setItem(key, shut ? "1" : "0"); } catch (err) { /* private mode */ }
        apply();
      });
      apply();
    }
    panelToggle("btnRail", "rail-shut", "aac.rail.shut");
    $("btnRailOpen").addEventListener("click", function () { $("btnRail").click(); });
    $("dataPanel").addEventListener("scroll", keepPlace, { passive: true });
    // On a narrow window the Inspector toggle shows and hides the sheet
    // instead; registered first so the column toggle does not also fire.
    $("btnInsp").addEventListener("click", function (e) {
      if (!NARROW.matches) return;
      e.stopImmediatePropagation();
      var shell = document.querySelector(".shell");
      inspectorOver(!shell.classList.contains("insp-over"));
    });
    panelToggle("btnInsp", "insp-shut", "aac.insp.shut");
    $("btnInspClose").addEventListener("click", function () { inspectorOver(false); });

    // Esc ends the tour, unless something nearer the person took it first.
    document.addEventListener("keydown", function (e) {
      if (tour && e.key === "Escape" && !e.defaultPrevented) endTour();
    });

    $("drawerClose").addEventListener("click", closeDrawer);
    $("drawerCancel").addEventListener("click", closeDrawer);
    $("scrim").addEventListener("click", closeDrawer);
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !$("newMenu").hidden) { closeNewMenu(); $("btnNew").focus(); return; }
      if (e.key === "Escape" && cv && !$("cvPicker").hidden) { closeCanvasPicker(); $("cvAdd").focus(); return; }
      if (e.key === "Escape" && cv && cv.tool === "connect" && $("drawer").hidden) { setCanvasTool("select"); return; }
      if (e.key === "Escape" && !$("drawer").hidden) { closeDrawer(); return; }
      if (e.key === "Escape" && document.querySelector(".shell").classList.contains("insp-over")) { inspectorOver(false); return; }
      // "/" goes to the search, as it does on GitHub and in most tools,
      // unless the keyboard is already in a field.
      var tag = (e.target && e.target.tagName || "").toLowerCase();
      var inField = tag === "input" || tag === "textarea" || tag === "select" || !!(e.target && e.target.isContentEditable);
      if ((e.ctrlKey || e.metaKey) && !e.altKey && String(e.key).toLowerCase() === "k") {
        e.preventDefault();
        if (pal.open) closePalette(); else openPalette();
        return;
      }
      if (e.key === "Escape" && pal.open) { closePalette(); return; }
      if (e.key === "/" && !inField) {
        e.preventDefault();
        openPalette();
      }
    });
    $("drawerSave").addEventListener("click", function () {
      if (!state.drawer) return closeDrawer();
      var btn = $("drawerSave");
      btn.disabled = true;
      Promise.resolve(state.drawer()).then(function (done) {
        if (done) closeDrawer();
      }).catch(fail).then(function () { btn.disabled = false; });
    });

    // rAF is suspended while the document is hidden, so a graph laid out in a
    // background tab paints nothing until something nudges it.
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "visible" && state.cy) {
        state.cy.resize();
        state.cy.forceRender();
      }
    });
    window.addEventListener("resize", function () { if (state.cy) state.cy.resize(); });

    window.addEventListener("hashchange", function () {
      var w = readUrl();
      if (w.draw !== undefined) {
        if (!cv || (cv.id || "") !== (w.draw || "")) openCanvas(w.draw || null);
        return;
      }
      if (w.home !== undefined) { openStart(); return; }
      if (isPageHash(w)) { if (pageHash() !== window.location.hash) openPageFrom(w); return; }
      if (w.diagrams !== undefined) { openDiagrams(w.layer || "All"); return; }
      if (w.guide !== undefined) { openGuide(); return; }
      if (w.needs !== undefined) { if (state.panel !== "needs") openNeeds(); return; }
      if (w.set !== undefined) { if (state.panel !== "setmany") openSetMany({ type: w.type, field: w.field, view: w.of || null }); return; }
      if (w.settings !== undefined) {
        if (state.panel !== "settings" || (w.tab || "sources") !== state.settingsTab) openSettings(w.tab || "sources");
        return;
      }
      if (w.assemble !== undefined) {
        if (state.panel !== "assemble" || !asm || (asm.replace || "") !== (w.open || "")) {
          openAssemble(w.open ? { open: w.open } : null);
        }
        return;
      }
      if (w.focus) {
        if (!state.focus || state.focus.id !== w.focus ||
            String(state.focus.depth) !== String(w.depth || 1)) {
          showFocus(w.focus, Number(w.depth) || 1);
        }
        return;
      }
      if (state.focus) { state.focus = null; renderFocusBar(); }
      Object.keys(w).forEach(function (key) {
        if (key.indexOf("p_") === 0) state.subject[key.slice(2)] = w[key];
      });
      // Back to a drawing from a page over it, or from the canvas, names
      // the view already current; it is drawn all the same.
      if (w.view && (w.view !== state.viewId || state.panel || cv)) selectView(w.view);
      if (w.id && w.id !== state.selectedId) showEntity(w.id);
    });

    // The shapes are a property of the component library, so they are fetched
    // rather than hard-coded. A failure here costs shapes, not the app.
    api("/api/library").then(function (lib) {
      lib.components.forEach(function (group) {
        group.types.forEach(function (t) { COMPONENT_CATEGORY[t.id] = group.category; });
      });
    }).catch(function () {});

    api("/api/schema").then(function (schema) {
      state.schema = schema;
      return refresh();
    }).then(function () {
      // A link naming an entity should land on it, not merely near it.
      var w = readUrl();
      if (w.id) showEntity(w.id);
      restoreScroll();
      // A link to the Assemble panel opens it, on the project it names.
      if (w.assemble !== undefined) openAssemble(w.open ? { open: w.open } : null);
    }).catch(fail);
  }

  document.addEventListener("DOMContentLoaded", boot);
})();
