/* Read-only static hosting.
 *
 * Every GET the UI makes is answered from a file baked at build time by
 * 80_APP/tools/export_site.py; anything that would change the model explains
 * itself instead. app.js ships unmodified, so the hosted demo cannot drift
 * away from the local tool.
 *
 * This file is only present on the built site. Running the app locally never
 * loads it, and the real server answers instead.
 */
(function () {
  "use strict";

  var realFetch = window.fetch.bind(window);
  var BASE = document.baseURI;
  //: The tone tools/export_site.py bakes at the plain paths (the first of
  //: terrane.palette.TONES); every other tone's drawings are under api/<tone>/.
  var PLAIN_TONE = "stone";
  //: What a tone colors, and so what is baked once per tone.
  var TONED = /^api\/(overview|flows|chunks|graph|focus)(\.json|\/)/;
  //: How many hops of neighborhood tools/export_site.py bakes.
  var FOCUS_DEPTHS = 2;
  var MSG =
    "This is the read-only hosted demo. Editing, import, validate-on-save and " +
    "render write to the model on disk, so they run in the app on your own " +
    "machine: pip install terrane, then terrane init and terrane app.";

  window.__AAC_STATIC__ = true;

  function reply(obj, status) {
    return new Response(JSON.stringify(obj), {
      status: status || 200,
      headers: { "Content-Type": "application/json" },
    });
  }

  // Mirrors the dump layout in tools/export_site.py.
  function staticPath(path, params) {
    var p = path.replace(/^\//, "");
    if (p === "api/overview") return "api/overview.json";
    if (p === "api/schema") return "api/schema.json";
    if (p === "api/validate") return "api/validate.json";
    if (p === "api/flows") return "api/flows.json";
    if (p === "api/log") return "api/log.json";
    if (p === "api/sources") return "api/sources.json";
    if (p === "api/project") return "api/project.json";
    if (p === "api/list") {
      var type = params.get("type");
      return type ? "api/list/" + type + ".json" : "api/list.json";
    }
    if (p === "api/graph") {
      // A view with a subject is baked once per subject, under the view's
      // own folder; the bare view file is what `render_for` picks first.
      var subject = null;
      params.forEach(function (value, key) {
        if (key.indexOf("p_") === 0 && value && !subject) subject = key.slice(2) + "--" + value;
      });
      if (subject) return "api/graph/" + params.get("view") + "/" + subject + ".json";
      return "api/graph/" + params.get("view") + ".json";
    }
    if (p === "api/entity") return "api/entity/" + params.get("id") + ".json";
    // Baked at depth 3; the depth control is a local-app affordance.
    if (p === "api/impact") return "api/impact/" + params.get("id") + ".json";
    if (p === "api/relations") return "api/relations/" + params.get("id") + ".json";
    // Baked at one and two hops. Deeper is a local-app affordance: the files
    // get large fast, and past two hops it stops being a neighborhood anyway.
    // The source of an authored view is baked; a focus view's is not, and
    // the format tabs are the same either way.
    if (p === "api/source" && params.get("view")) {
      return "api/source/" + params.get("view") + ".json";
    }
    // What the diagrams need: the one list, and each view's as first drawn.
    if (p === "api/needs") return "api/needs.json";
    if (p === "api/needs/view" && params.get("view")) {
      var bound = false;
      params.forEach(function (value, key) { if (key.indexOf("p_") === 0 && value) bound = true; });
      return bound ? null : "api/needs/view/" + params.get("view") + ".json";
    }
    if (p === "api/coverage") return "api/coverage.json";
    if (p === "api/library") return "api/library.json";
    if (p === "api/chunks") return "api/chunks.json";
    if (p === "api/assemble/open") return "api/assemble/open/" + params.get("id") + ".json";
    if (p === "api/table") {
      var entity = params.get("type"), relation = params.get("relation");
      if (entity) return "api/table/entity-" + entity + ".json";
      if (relation) return "api/table/relation-" + relation + ".json";
      return "api/table/catalog.json";
    }
    if (p === "api/archetype") {
      var a = params.get("id");
      return a ? "api/archetype/" + a + ".json" : null;
    }
    if (p === "api/entity/source") {
      return "api/entity-source/" + params.get("id") + ".json";
    }
    if (p === "api/view") {
      var v = params.get("id");
      return v ? "api/view/" + v + ".json" : null;
    }
    if (p === "api/focus") {
      return "api/focus/" + params.get("id") + "-" + (params.get("depth") || "1") + ".json";
    }
    return null;
  }

  window.fetch = function (input, opts) {
    opts = opts || {};
    var url = typeof input === "string" ? input : input.url;
    var i = url.indexOf("/api/");
    if (i === -1 && url.indexOf("api/") !== 0) return realFetch(input, opts);

    var method = (opts.method || "GET").toUpperCase();
    if (method !== "GET") return Promise.resolve(reply({ error: MSG }, 405));

    var raw = i === -1 ? "/" + url : url.slice(i);
    var qi = raw.indexOf("?");
    var path = qi === -1 ? raw : raw.slice(0, qi);
    var params = new URLSearchParams(qi === -1 ? "" : raw.slice(qi + 1));

    var file = staticPath(path, params);
    if (!file) return Promise.resolve(reply({ error: "Not part of the static demo. " + MSG }, 404));
    var tone = params.get("tone");
    if (tone && tone !== PLAIN_TONE && /^[a-z]+$/.test(tone) && TONED.test(file)) {
      file = "api/" + tone + "/" + file.slice(4);
    }

    return realFetch(new URL(file, BASE).href).then(function (res) {
      if (!res.ok) {
        return reply({ error: "Not part of the static demo. " + MSG }, 404);
      }
      return res.json().then(function (data) {
        // A view that resolved to nothing was baked as its error; hand it back
        // with the status the app expects so it renders the empty state.
        if (data && data.error && path === "/api/graph") return reply(data, 409);
        // Only one and two hops are baked, so tell the app that rather than
        // letting it offer a control that can only produce an error.
        if (data && path === "/api/focus") data.maxDepth = FOCUS_DEPTHS;
        return reply(data);
      });
    });
  };

  // Turn off what cannot work here, rather than letting someone fill in a form
  // and only then be told the server is a folder of JSON files.
  document.addEventListener("DOMContentLoaded", function () {
    // `btnNew` stays live: it opens the archetypes, which are worth reading
    // here even though instantiating one writes and so runs locally.
    // `btnComponents` stays live: the library is worth reading here even
    // though adding a block writes and so runs locally.
    ["btnRender", "btnNewEmpty", "btnImportEmpty", "btnNewView"].forEach(function (id) {
      var btn = document.getElementById(id);
      if (!btn) return;
      btn.disabled = true;
      btn.title = MSG;
    });

    var actions = document.querySelector(".tb-actions");
    if (actions) {
      var tag = document.createElement("span");
      tag.textContent = "read-only";
      tag.title = MSG;
      tag.style.cssText =
        "font-family:var(--mono);font-size:9.5px;letter-spacing:.08em;" +
        "text-transform:uppercase;color:var(--ink-3);border:1px solid var(--rule-2);" +
        "border-radius:3px;padding:2px 7px;white-space:nowrap";
      actions.insertBefore(tag, actions.firstChild);
    }

    var idle = document.getElementById("inspIdle");
    if (idle) {
      idle.textContent =
        "Select anything on the map to see where it runs and what it connects to. " +
        "This is the read-only demo; editing runs in the local app.";
    }
  });
})();
