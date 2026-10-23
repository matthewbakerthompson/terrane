"""Bake the app into a static site for GitHub Pages.

Every GET the UI makes is answered at build time and written to a file, and a
small shim in the browser rewrites `fetch("/api/...")` onto those files. The
app's own `app.js` ships unmodified, so the hosted demo cannot drift from the
local tool.

The handlers are called directly rather than crawled over HTTP. There is no
server to start, no port to race on, and the output is deterministic, which
matters because CI compares it.

Anything that would change the model is refused by the shim with an explanation,
because Pages is static hosting: there is nothing to write to.

The app draws in a tone (Stone or Graphite), and the server styles every
drawing in the tone asked for. So everything a tone colors is baked once per
tone: the first at the plain paths, each other under `api/<tone>/`, which is
where the shim looks when the page asks for it.

    python 80_APP/tools/export_site.py --out site
    python 80_APP/tools/export_site.py --root 90_EXAMPLE/thurman-health --out site/thurman-health

The first bakes the checkout's own model into `site/` and every estate in
`ESTATES` into a folder of it, each home page linking the others; the second
bakes one model alone, as `terrane --root` and `server.py --root` take it.
`--out` names a folder that does not exist yet, or an empty one: the bake
deletes nothing, so a second bake goes to a new folder.
"""

from __future__ import annotations

import argparse
import json
import posixpath
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

APP_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_DIR.parent
WEB_DIR = APP_DIR / "web"

sys.path.insert(0, str(APP_DIR / "app"))

import server  # noqa: E402

from terrane import icons as icons_module  # noqa: E402
from terrane.cli import is_sample_estate  # noqa: E402
from terrane.schema import ENTITY_TYPES  # noqa: E402

#: Copied verbatim into the site. `fonts/` and `vendor/` are what make the
#: hosted page work with no third-party requests at all.
# The marks travel with the site: without the icons folder every corner of
# the hosted demo asked for a file that was not there.
ASSETS = ("app.js", "styles.css", "favicon.svg", "vendor", "fonts", "icons")

#: The estates published beside the checkout's own model: the folder of the
#: site each is baked into, its root, and the line the other estates' home
#: pages describe it with. Each is baked by a run of this script of its own,
#: so nothing `server` holds at module level -- the model cache, the
#: validation memo, the icon map -- can carry one estate into another's files.
ESTATES: Tuple[Tuple[str, str, str], ...] = (
    ("thurman-health", "90_EXAMPLE/thurman-health",
     "A regional health system on the same library and views"),
)

#: How the other estates name the checkout's model while it is the sample.
#: Its `model.yaml` says "Architecture Model" on purpose, since the sample
#: carries no company name, and from a hospital's home page that names
#: nothing. Once `terrane clear` has taken the sample out, the model's own
#: name is used and no line is claimed for it.
SAMPLE = ("The sample estate", "A card issuer, the model the engine is tested on")

#: What each published home page reads to link the others. A file beside the
#: page rather than an API answer: the local app serves one model and has no
#: other to link, so there it is absent and the home page says nothing.
ESTATES_FILE = "estates.json"


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8")


def _call(handler: Callable, query: Dict[str, List[str]] | None = None) -> Any:
    return handler(query or {}, {})


def bake_api(out: Path) -> int:
    api = out / "api"
    written = 0

    # One model for the whole bake: nothing writes to it while the export
    # runs, and checking the folders before every one of six thousand calls
    # was more than half the time the export took.
    server._load_all()
    server._CACHE["frozen"] = True
    try:
        return _bake(api, written)
    finally:
        server._CACHE["frozen"] = False


def _bake(api: Path, written: int) -> int:
    plain = {"tone": [server.TONES[0]]}
    overview = _call(server.api_overview, plain)
    _write(api / "overview.json", overview)
    _write(api / "schema.json", _call(server.api_schema))
    _write(api / "validate.json", _call(server.api_validate))
    _write(api / "flows.json", _call(server.api_flows, plain))
    # Settings reads on the hosted copy: the kept sources and the estate's
    # facts. Bringing anything in needs the local app, and the page says so.
    _write(api / "sources.json", _call(server.api_sources))
    _write(api / "project.json", _call(server.api_project))
    written += 2
    # The home page's recent changes: the log of the commit the site is built from.
    _write(api / "log.json", _call(server.api_log))
    # The chunk gallery reads on the hosted copy; assembling needs the local
    # app, and the panel says so.
    chunks = _call(server.api_chunks, plain)
    _write(api / "chunks.json", chunks)
    written += 6
    # A product assembled from parts opens again on the hosted copy, to
    # read; saving it needs the local app.
    for product in chunks.get("assembled") or []:
        _write(api / "assemble" / "open" / ("%s.json" % product["id"]),
               _call(server.api_assemble_open, {"id": [product["id"]]}))
        written += 1

    everything = _call(server.api_list)
    _write(api / "list.json", everything)
    written += 1
    for type_name in ENTITY_TYPES:
        _write(api / "list" / ("%s.json" % type_name), _call(server.api_list, {"type": [type_name]}))
        written += 1

    written += _bake_graphs(api, overview, server.TONES[0])
    for view in overview["views"]:
        view_id = view["viewId"]
        try:
            _write(
                api / "source" / ("%s.json" % view_id),
                _call(server.api_source, {"view": [view_id]}),
            )
            written += 1
        except server.ApiError:
            pass
        # The editor is read-only here, but showing someone the query behind a
        # diagram is most of its value and costs one small file per view. The
        # composer's vocabulary is left out: it is nine tenths of the payload,
        # the same in every file, and the published copy never composes.
        view_payload = _call(server.api_view, {"id": [view_id]})
        view_payload.pop("vocab", None)
        _write(api / "view" / ("%s.json" % view_id), view_payload)
        written += 1

    # Archetypes and entity files are read-only here too, but the shape behind
    # a product and the file behind a box are most of what someone came to see.
    # The tables and the coverage report are most of why someone opens the
    # demo: a diagram shows what somebody already asked, a table does not.
    _write(api / "coverage.json", _call(server.api_coverage))
    # What the diagrams need, read-only here: the one list under Checks, and
    # each view's beside its drawing. Setting a field on many records needs
    # the local app.
    _write(api / "needs.json", _call(server.api_needs))
    written += 1
    for view in overview["views"]:
        _write(api / "needs" / "view" / ("%s.json" % view["viewId"]),
               _call(server.api_needs_view, {"view": [view["viewId"]]}))
        written += 1
    # What changed since the previous commit, if the checkout has one to
    # compare with; a shallow clone or a folder that is not a repository is
    # baked as its error, so the hosted page says why rather than failing.
    try:
        _write(api / "diff.json", _call(server.api_diff))
    except server.ApiError as exc:
        _write(api / "diff.json", {"error": exc.message})
    written += 1
    # The model against the sample CMDB export; a checkout without the
    # sample is baked as its error, the same way.
    try:
        _write(api / "cmdb" / "drift.json", _call(server.api_cmdb_drift))
    except server.ApiError as exc:
        _write(api / "cmdb" / "drift.json", {"error": exc.message})
    written += 1
    # Adding a block writes to disk, but reading the library is most of why
    # somebody opens it, so the demo carries it.
    _write(api / "library.json", _call(server.api_library))
    written += 1
    catalog = _call(server.api_table)
    _write(api / "table" / "catalog.json", catalog)
    written += 2
    for entry in catalog["entities"]:
        _write(
            api / "table" / ("entity-%s.json" % entry["id"]),
            _call(server.api_table, {"type": [entry["id"]]}),
        )
        written += 1
    for entry in catalog["relations"]:
        _write(
            api / "table" / ("relation-%s.json" % entry["id"]),
            _call(server.api_table, {"relation": [entry["id"]]}),
        )
        written += 1

    for archetype in overview["archetypes"]:
        _write(
            api / "archetype" / ("%s.json" % archetype["id"]),
            _call(server.api_archetype, {"id": [archetype["id"]]}),
        )
        written += 1

    for item in everything["items"]:
        _write(api / "entity" / ("%s.json" % item["id"]), _call(server.api_entity, {"id": [item["id"]]}))
        _write(
            api / "impact" / ("%s.json" % item["id"]),
            _call(server.api_impact, {"id": [item["id"]], "depth": ["3"]}),
        )
        _write(
            api / "relations" / ("%s.json" % item["id"]),
            _call(server.api_relations, {"id": [item["id"]]}),
        )
        written += 3
        try:
            _write(
                api / "entity-source" / ("%s.json" % item["id"]),
                _call(server.api_entity_source, {"id": [item["id"]]}),
            )
            written += 1
        except server.ApiError:
            # A generated entity has no file of its own; nothing to bake.
            pass
    written += _bake_focus(api, everything["items"], server.TONES[0])

    # The other tones: only what a tone colors, under a folder of its own.
    for tone in server.TONES[1:]:
        toned = api / tone
        _write(toned / "overview.json", _call(server.api_overview, {"tone": [tone]}))
        _write(toned / "flows.json", _call(server.api_flows, {"tone": [tone]}))
        _write(toned / "chunks.json", _call(server.api_chunks, {"tone": [tone]}))
        written += 3 + _bake_graphs(toned, overview, tone) + _bake_focus(toned, everything["items"], tone)
    return written


def _bake_graphs(api: Path, overview: dict, tone: str) -> int:
    """Every view's drawing in one tone, and every subject's for the views
    that take one."""
    written = 0
    for view in overview["views"]:
        view_id = view["viewId"]
        try:
            payload = _call(server.api_graph, {"view": [view_id], "tone": [tone]})
        except server.ApiError as exc:
            # A view that resolves to nothing is baked as its error, so the
            # hosted page explains itself the same way the local app does.
            payload = {"error": exc.message}
        _write(api / "graph" / ("%s.json" % view_id), payload)
        written += 1
        # A view that takes a subject is baked once per subject the picker
        # offers, not only for the one `render_for` picks first. Without this
        # the hosted demo answered every subject with the same diagram.
        for param in view.get("parameters") or []:
            spec = next((p for p in payload.get("parameters", []) if p["name"] == param), None)
            type_name = spec.get("type") if spec else None
            if not type_name:
                continue
            for item in _call(server.api_list, {"type": [type_name]})["items"]:
                try:
                    subject = _call(server.api_graph,
                                    {"view": [view_id], "p_" + param: [item["id"]], "tone": [tone]})
                except server.ApiError as exc:
                    subject = {"error": exc.message}
                _write(api / "graph" / view_id / ("%s--%s.json" % (param, item["id"])), subject)
                written += 1
    return written


def _bake_focus(api: Path, items: list, tone: str) -> int:
    """Every record's neighborhood in one tone, at one and two hops. Past
    that a neighborhood view has become the landscape, and the files get
    large enough to be worth not shipping."""
    written = 0
    for item in items:
        for depth in ("1", "2"):
            _write(
                api / "focus" / ("%s-%s.json" % (item["id"], depth)),
                _call(server.api_focus, {"id": [item["id"]], "depth": [depth], "tone": [tone]}),
            )
            written += 1
    return written


def copy_assets(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name in ASSETS:
        src = WEB_DIR / name
        dst = out / name
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        elif src.exists():
            shutil.copy2(src, dst)
    # The marks as the app serves them: a size given to any that says only
    # its viewBox, or the canvas draws a fragment of it.
    for mark in (out / "icons").rglob("*.svg"):
        mark.write_bytes(icons_module.sized(mark.read_bytes()))

    shim = WEB_DIR / "static-shim.js"
    if not shim.exists():
        raise SystemExit("missing %s" % shim)
    shutil.copy2(shim, out / "static-shim.js")

    # The shim has to be installed before app.js runs, so it can replace fetch
    # before the first request goes out.
    html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    marker = '<script src="app.js"></script>'
    if marker not in html:
        raise SystemExit("index.html no longer loads app.js the expected way")
    html = html.replace(marker, '<script src="static-shim.js"></script>\n' + marker)
    (out / "index.html").write_text(html, encoding="utf-8")

    # GitHub Pages runs Jekyll unless told not to, which would eat any path
    # beginning with an underscore.
    (out / ".nojekyll").write_text("", encoding="utf-8")


def name_the_page(out: Path) -> None:
    """The tab says which model it holds. Two estates published side by side
    were two tabs called "Terrane"; and the replacement this replaced looked
    for the title the page had before the product was named, so it had
    quietly changed nothing since."""
    name = _model_name(out)
    path = out / "index.html"
    html = path.read_text(encoding="utf-8")
    marker = "<title>Terrane</title>"
    if marker not in html:
        raise SystemExit("index.html no longer carries the title the export names")
    path.write_text(html.replace(marker, "<title>%s · Terrane, read-only</title>" % name), encoding="utf-8")


def _model_name(site: Path) -> str:
    overview = json.loads((site / "api" / "overview.json").read_text(encoding="utf-8"))
    return overview.get("modelName") or "Architecture Model"


def link_estates(out: Path, sites: List[Tuple[str, str, str]]) -> None:
    """Write `estates.json` into every published site: each estate's name,
    its line and where it is from that page, with the page's own marked.

    `sites` is (folder under `out`, name, line), the checkout's own first at
    folder "". Written after every bake has finished, from what was baked, so
    no page links an estate whose bake did not happen."""
    for here, _name, _line in sites:
        listing = []
        for there, name, line in sites:
            href = posixpath.relpath("/" + there, "/" + here)
            listing.append({
                "name": name,
                "line": line,
                # A folder with its trailing slash, so the page it opens
                # resolves its own `api/` beside it and not beside this one.
                "href": "./" if href == "." else href + "/",
                "here": there == here,
            })
        _write(out / here / ESTATES_FILE, {"estates": listing})


def _refused(out: Path) -> bool:
    """A folder that already holds anything: the bake writes nothing there.
    It used to clear `--out` with `shutil.rmtree` first, whatever folder it
    named: `--out .` was the repository itself. Nothing is deleted here now,
    and what becomes of an old site is the person's call."""
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        print("error: %s already holds something; nothing was written. Bake into a folder "
              "that does not exist yet." % out, file=sys.stderr)
        return True
    return False


def bake_site(root: Path, out: Path) -> Tuple[int, int]:
    """One model into one folder: the assets, every answer, the page's name."""
    server.REPO_ROOT = root
    out.mkdir(parents=True, exist_ok=True)
    copy_assets(out)
    written = bake_api(out)
    name_the_page(out)
    return written, sum(1 for p in out.rglob("*") if p.is_file())


def _estate_root(root: str) -> Path:
    return (REPO_ROOT / root).resolve()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Bake the app into a static site.")
    parser.add_argument("--out", default="site", help="output directory (default: site)")
    parser.add_argument(
        "--root",
        help="bake this model alone, as `terrane --root` takes it; left out, the checkout's "
        "own model is baked with every estate in ESTATES in a folder beside it",
    )
    args = parser.parse_args(argv)

    out = Path(args.out)
    if not out.is_absolute():
        out = REPO_ROOT / out
    if _refused(out):
        return 2

    if args.root:
        root = Path(args.root).resolve()
        written, total = bake_site(root, out)
        print("Static site of %s written to %s" % (_model_name(out), out))
        print("  %d API responses baked, %d files" % (written, total))
        return 0

    written, total = bake_site(REPO_ROOT, out)
    print("Static site written to %s" % out)
    print("  %s: %d API responses baked, %d files" % (_model_name(out), written, total))
    name, line = SAMPLE if is_sample_estate(REPO_ROOT) else (_model_name(out), "")
    sites = [("", name, line)]
    for folder, root, estate_line in ESTATES:
        if not (_estate_root(root) / "10_MODEL").is_dir():
            # A checkout that has taken an estate out publishes without it,
            # and the other pages do not link a folder that is not there.
            print("  %s: not in this checkout, not published" % root)
            continue
        # A process of its own per estate; see ESTATES. Flushed first, or
        # the estate's lines print above the sample's.
        sys.stdout.flush()
        subprocess.run(
            [sys.executable, str(Path(__file__).resolve()),
             "--root", str(_estate_root(root)), "--out", str(out / folder)],
            check=True,
        )
        sites.append((folder, _model_name(out / folder), estate_line))
    link_estates(out, sites)

    print("")
    print("Serve it locally with:  python -m http.server --directory %s 8030" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
