"""Local web app for the architecture model.

Standard library only, binds to loopback, no outbound calls. It reads the model
in `10_MODEL/`, serves it as a graph you can pan around, and writes edits back
as YAML files that look like something a person would have written.

The point is that editing the model and looking at the model are the same
activity. A model you can only change from a command line gets changed by one
person; a model you can change in a browser gets changed by the team that owns
the systems, which is the only way it stays current.

    python 80_APP/app/server.py --port 8020
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
import sys
import threading
import traceback
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse

APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parents[1]
WEB_DIR = APP_DIR.parent / "web"

sys.path.insert(0, str(REPO_ROOT / "50_ENGINE"))

from terrane import exports, impact as impact_module, importer, validate  # noqa: E402
from terrane import icons as icons_module  # noqa: E402
from terrane import sources as sources_module  # noqa: E402
from terrane import records as records_module  # noqa: E402
from terrane import regroup as regroup_module  # noqa: E402
from terrane import places as places_module  # noqa: E402
from terrane import needs as needs_module  # noqa: E402
from terrane.connections import kind_of, load_connections, sorted_by_kind  # noqa: E402
from terrane.archetype import ArchetypeError, expand, parse_archetype  # noqa: E402
from terrane.blocks import LibraryError, load_blocks, load_components  # noqa: E402
from terrane.blocks import expand as block_expand  # noqa: E402
from terrane.loader import ModelFileError, parse_data_text, read_data_file  # noqa: E402
from terrane.model import ModelError, load  # noqa: E402
from terrane.palette import TONES, Palette  # noqa: E402
from terrane.estate import is_shipped_view, views_of  # noqa: E402
from terrane.shipped import sample_inventory  # noqa: E402
from terrane.query import VIEW_CATEGORIES, ViewError, bind, load_views, parse_view  # noqa: E402
from terrane.query import render_targets, resolve  # noqa: E402
from terrane.render_mermaid import render as render_mermaid  # noqa: E402
from terrane.render_mermaid import render_markdown, render_timeline  # noqa: E402
from terrane.render_sequence import all_flows, steps_for  # noqa: E402
from terrane.render_sequence import render as render_sequence  # noqa: E402
from terrane.render_structurizr import render_workspace  # noqa: E402
from terrane.schema import ENTITY_TYPES, RELATION_TYPES  # noqa: E402
from terrane.importer import LIST_FIELDS, _yaml_scalar as _yaml_value  # noqa: E402
from terrane.blocks import PATTERN_STATUS, load_patterns  # noqa: E402
from terrane.answers import adopted_patterns, estate_answers  # noqa: E402
from terrane.adoption import candidates as shape_candidates, drifts as shape_drifts  # noqa: E402
from terrane.cmdb import load_field_sot, read_ci_export, reconcile as reconcile_cmdb  # noqa: E402
from terrane.archetype import landing_providers  # noqa: E402
from terrane.build_types import BuildTypeError, load_build_types, uses_by_build_types  # noqa: E402
from terrane.archetype import (  # noqa: E402
    ArchetypeError as _ArchetypeError,
    effective_bind,
    landing_providers,
    landing_zone_gaps,
    landing_zone_index,
    resolve_kind,
)
from terrane.modules import (  # noqa: E402
    MODULES_DIR, ModuleError, load_modules, members_of, parse_module, provided_count, uses_of,
)
from terrane.archetype import ARCHETYPES_DIR  # noqa: E402
from terrane.library import (  # noqa: E402
    LAYER_FOLDERS, REPLACES, LibraryRoot, library_of, library_roots, own_root,
    shown as _shown,
    summary as library_summary,
)
from terrane.sketch import (  # noqa: E402
    SketchError, guess_slug, module_text_from_sketch, view_text_from_sketch,
)
from terrane.compose import (  # noqa: E402
    keep_comments,
    ASSEMBLED_HEADER, shaped_header, shaped_text,
    VOCABULARY, ComposeError, archetype_text_from_parts, assembled_text, blocks_needed, inline_shape,
)
from terrane.sketch import dump_yaml, yaml_text  # noqa: E402
from terrane.draw import Undrawable, drawing_mode, render_svg  # noqa: E402
from terrane.icons import IconMap  # noqa: E402
from terrane.payload import GOVERNANCE_EDGES, PLATFORM_EDGES, graph_payload  # noqa: E402,F401
from terrane.payload import edge_style as _edge_style  # noqa: E402,F401

_LOCK = threading.Lock()

SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


# --------------------------------------------------------------------------
# model access
# --------------------------------------------------------------------------


#: The parsed model and views, and the fingerprints of the files each came
#: from. They are kept apart because a view is read by nothing the model
#: loads: a pin or a hide used to reparse 894 entities and their shapes,
#: most of the six seconds the click took.
_CACHE: Dict[str, Any] = {
    "fingerprint": None, "model": None, "views": None, "root": None, "views_mark": None,
}

#: The layers the model's loader expands products with, in every library:
#: shapes, component types, blocks and parts. With the records, they are
#: what the model is made of, and a change to any of them means the cached
#: parse is stale. Only the shapes were watched once, so a part changed
#: while the app ran was expanded from its old text until a model file
#: changed.
_MODEL_LAYERS = ("20_ARCHETYPES", "25_COMPONENTS", "26_BLOCKS", "28_MODULES")
_VIEWS_WATCHED = ("30_VIEWS",)


def _roots() -> List[LibraryRoot]:
    """The libraries the model names, or the shipped one alone when
    `library_paths` cannot be read: the load says what is wrong with it."""
    try:
        return library_roots(REPO_ROOT)
    except LibraryError:
        return [LibraryRoot(REPO_ROOT, "")]


def _watched() -> List[Any]:
    return ["10_MODEL"] + [base.path / layer for base in _roots() for layer in _MODEL_LAYERS]


def _fingerprint(folders=None):
    """A cheap answer to "has anything changed".

    Stat-walking the tree costs a few milliseconds; parsing it costs most of a
    second, and every request used to pay that. Size is in the fingerprint as
    well as mtime because a same-second edit can leave mtime unmoved on some
    filesystems, and a wrong answer here means an edit that does not appear.
    """
    marks = []
    for folder in _watched() if folders is None else folders:
        base = REPO_ROOT / folder
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file():
                stat = path.stat()
                marks.append((str(path), stat.st_mtime_ns, stat.st_size))
    return tuple(marks)


def _load_all():
    # Held still by a caller that knows nothing changes underneath it: the
    # site export calls six thousand handlers against one model, and walking
    # the folders before each was more than half of its time.
    if _CACHE.get("frozen") and _CACHE["model"] is not None and _CACHE["root"] == REPO_ROOT:
        return _CACHE["model"], _CACHE["views"]
    fingerprint = _fingerprint()
    views_mark = _fingerprint(_VIEWS_WATCHED)
    same_root = _CACHE["root"] == REPO_ROOT
    if same_root and _CACHE["fingerprint"] == fingerprint:
        model = _CACHE["model"]
    else:
        model = load(REPO_ROOT)
    if same_root and _CACHE["views_mark"] == views_mark and _CACHE["views"] is not None:
        views = _CACHE["views"]
    else:
        views = views_of(REPO_ROOT)
    _CACHE.update({
        "fingerprint": fingerprint, "views_mark": views_mark,
        "model": model, "views": views, "root": REPO_ROOT,
    })
    return model, views


#: Validation reads every layer of every library, so they key the memo
#: below alongside the model itself.
def _library_watched() -> List[Any]:
    return [base.path / layer for base in _roots() for layer in LAYER_FOLDERS]


_REPORT: Dict[str, Any] = {"model": None, "views": None, "library": None, "report": None}


def _report(model, views):
    """Validation of the model as loaded, once. A write validated, and the
    overview the app fetched straight after validated the same model again,
    each run most of a second of the wait after a click."""
    library = _fingerprint(_library_watched())
    if _REPORT["model"] is model and _REPORT["views"] is views and _REPORT["library"] == library:
        return _REPORT["report"]
    report = validate.run(model, views)
    _REPORT.update({"model": model, "views": views, "library": library, "report": report})
    return report


def _write_text(path: Path, text: str) -> None:
    """A file as the repository keeps it: LF, whatever the platform. Written
    with Windows line endings, a pin undone left a file git called modified
    though not a character in it had changed."""
    path.write_text(text, encoding="utf-8", newline="\n")


def _entity_path(type_name: str, entity_id: str) -> Path:
    entity_type = ENTITY_TYPES[type_name]
    return REPO_ROOT / "10_MODEL" / entity_type.folder / ("%s.yaml" % entity_id)


def _write_entity(type_name: str, entity_id: str, values: Dict[str, Any]) -> Path:
    """Write a new entity as its own file, in metamodel field order.

    Only ever a new one: an entity that exists is changed where it lives, by
    `_save_existing`. Writing every save here is what once put a second copy
    of a harvested system beside the first and left a model that would not
    load."""
    path = _entity_path(type_name, entity_id)
    if path.exists():
        raise ApiError(
            "%s already exists and is not %s; nothing was written"
            % (path.relative_to(REPO_ROOT), entity_id),
            409,
        )
    try:
        lines = records_module.record_lines(type_name, entity_id, values)
    except ValueError as exc:
        raise ApiError(str(exc))
    lines.insert(0, "# Added in the app. `terrane validate` is the gate, not this form.")
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_text(path, "\n".join(lines) + "\n")
    return path


def _restore(touched: List[Tuple[Path, Optional[str]]]) -> None:
    """Put back what a failed write changed: a file it made goes, a file it
    rewrote gets its old text."""
    for path, previous in reversed(touched):
        if previous is None:
            if path.exists():
                path.unlink()
        else:
            _write_text(path, previous)


def _save_existing(type_name: str, entity_id: str, record: dict, values: Dict[str, Any]):
    """Change an entity where it lives. Returns the files touched, with what
    each held before, the file it lives in now, and a sentence when it moved."""
    planned: Dict[Path, Tuple[Optional[str], str]] = {}
    try:
        path, moved = records_module.change(REPO_ROOT, type_name, entity_id, record, values, planned)
    except records_module.Refused as exc:
        raise ApiError(str(exc), 409)
    except ValueError as exc:
        raise ApiError(str(exc))
    except KeyError:
        home = records_module.home_of(type_name, record)
        raise ApiError("%s is not in %s any more; reload and try again" % (entity_id, home.path.name), 409)
    return _write_planned(planned), path, moved


def _write_planned(planned: Dict[Path, Tuple[Optional[str], str]]) -> List[Tuple[Path, Optional[str]]]:
    """Write what the engine planned, a new file first so a record that
    moves is never in neither place; returns the files touched, with what
    each held before, for `_restore`."""
    touched: List[Tuple[Path, Optional[str]]] = []
    order = sorted(planned, key=lambda p: planned[p][0] is not None)
    try:
        for path in order:
            before, after = planned[path]
            if before is None:
                path.parent.mkdir(parents=True, exist_ok=True)
            touched.append((path, before))
            _write_text(path, after)
    except OSError as exc:
        _restore(touched)
        raise ApiError("could not write %s: %s" % (path.name, exc), 500)
    return touched


_ICONS = None


def _icon_map() -> IconMap:
    """The shipped marks, read once; `web/icons/map.json` is a file in the
    app, not in the model, so the model cache does not govern it."""
    global _ICONS
    if _ICONS is None:
        _ICONS = IconMap(WEB_DIR)
    return _ICONS


def _palette(model, query=None) -> Palette:
    """The estate's palette in the tone the page asked for. The app sends
    its tone with every request, so a drawing on screen matches the shell
    around it; a request without one (a script, an export) gets the
    estate's own base, which is classic unless `palette: base:` says."""
    tone = ((query or {}).get("tone") or [""])[0]
    return Palette(model.config.get("palette"), tone if tone in TONES else None)


def _tone(model) -> str:
    """The tone the app opens in: the estate's base when it is one of the
    app's tones, else the first of them."""
    base = (model.config.get("palette") or {}).get("base") if isinstance(model.config.get("palette"), dict) else None
    return base if base in TONES else TONES[0]


def _graph_payload(model, view, palette) -> dict:
    """The view as drawn, from the engine's builder (`terrane.payload`), with
    the app's icon map and the library's component types; the same
    dictionary `terrane render` draws its SVG from."""
    components = {}
    try:
        components = load_components(REPO_ROOT)
    except LibraryError:
        pass
    return graph_payload(model, view, palette, _icon_map(), components)


# --------------------------------------------------------------------------
# API handlers
# --------------------------------------------------------------------------


def _on_canvas(view) -> bool:
    """Whether a view is a drawing rather than a query: it places other views,
    or it is only the things pinned to it. Edit opens it on the canvas."""
    own = view.own or view
    return bool(own.places) or (bool(own.scope.get("pin")) and not own.scope.get("include"))


def api_overview(query, _body) -> dict:
    model, views = _load_all()
    report = _report(model, views)
    try:
        modules = load_modules(REPO_ROOT)
    except ModuleError:
        modules = {}
    view_summaries = []
    palette = Palette(model.config.get("palette"))
    for view in views:
        try:
            # A parameterized view has no single graph. Summarize the one
            # `render_for` would draw first, so the rail shows a real count
            # rather than marking it broken.
            graph = resolve(model, bind(
                view,
                dict(render_targets(model, view)) if view.parameters else None,
                model,
            ))
            view_summaries.append(
                {
                    "viewId": view.view_id,
                    "title": view.title,
                    "category": view.category,
                    "section": view.section,
                    "kind": view.kind,
                    "canvas": _on_canvas(view),
                    "parameters": [p.name for p in view.parameters],
                    "description": view.description,
                    "nodes": len(graph.nodes),
                    "edges": len(graph.edges),
                    # What the boxes are, so a card can say "22 capabilities"
                    # rather than "22 nodes".
                    "types": dict(Counter(node.entity_type for node in graph.nodes)),
                    "ok": True,
                }
            )
        except ViewError as exc:
            view_summaries.append(
                {
                    "viewId": view.view_id,
                    "title": view.title,
                    "category": view.category,
                    "section": view.section,
                    "kind": view.kind,
                    "canvas": _on_canvas(view),
                    "parameters": [p.name for p in view.parameters],
                    "description": view.description,
                    "nodes": 0,
                    "edges": 0,
                    "ok": False,
                    "problem": str(exc),
                }
            )
    return {
        "modelName": model.config.get("name") or "Architecture Model",
        # Which estate this is, so the sample can say it is one and point at
        # starting your own, and the estate menu can mark the open one.
        "estate": {"path": str(REPO_ROOT), "folder": REPO_ROOT.name, "sample": bool(model.config.get("sample_estate"))},
        "tone": _tone(model),
        "tones": list(TONES),
        # The tone's hue per entity type, for the places the page colors by
        # type with no drawing at hand: the layers in the sidebar, the
        # spectrum, the sequence's heads.
        "swatches": {name: {"fill": s.fill, "stroke": s.stroke, "ink": s.ink}
                     for name, s in _palette(model, query).types.items()},
        "counts": model.counts(),
        "entityCount": sum(len(v) for v in model.entities.values()),
        "relationCount": sum(len(v) for v in model.relations.values()),
        "flowCount": len(model.all_of("flows")),
        "views": view_summaries,
        "errors": len(report.errors),
        "warnings": len(report.warnings),
        "empty": not any(model.entities.values()),
        "archetypes": [
            {
                "id": a.archetype_id,
                "title": a.title,
                "description": a.description,
                "appliesTo": a.applies_to,
                "provides": sum(len(v) for v in a.provides.values()) + sum(
                    m.get("provides", 0) for m in _module_summaries(a, modules) if not m.get("kit")
                ),
                "modules": _module_summaries(a, modules),
                "slots": _slot_summaries(a, modules),
                "parameters": [
                    dict({"name": p.name}, **_asked(p, estate_answers(model.config)))
                    for p in a.parameters
                ],
            }
            for a in sorted(model.archetypes.values(), key=lambda x: x.archetype_id)
        ],
    }


def api_schema(_query, _body) -> dict:
    out = {}
    for name, entity_type in ENTITY_TYPES.items():
        out[name] = {
            "pk": entity_type.pk,
            "label": entity_type.label,
            "folder": entity_type.folder,
            "fields": [
                {
                    "name": f.name,
                    "required": f.required,
                    "enum": list(f.enum) if f.enum else None,
                    "ref": f.ref,
                    "extension": f.extension,
                }
                for f in entity_type.fields
            ],
        }
    return {
        "entities": out,
        "relations": {
            name: {
                "left": spec.left,
                "right": spec.right,
                "leftColumn": spec.left_column,
                "rightColumn": spec.right_column,
                "qualifier": spec.qualifier,
            }
            for name, spec in RELATION_TYPES.items()
        },
    }


#: How `terrane render` names one subject's copy of a parameterized view.
BOUND_SEPARATOR = "--"


def _find_view(views, view_id: str):
    """A view and the parameters baked into its id, if any.

    `system-architecture--sys-auth-switch` is the committed artifact's name.
    Resolving it back to the view plus a subject is what makes every generated
    file addressable rather than a dead end.
    """
    for view in views:
        if view.view_id == view_id:
            return view, {}
    if BOUND_SEPARATOR not in view_id:
        return None, {}
    base, _, tail = view_id.rpartition(BOUND_SEPARATOR)
    for view in views:
        if view.view_id != base or not view.parameters:
            continue
        return view, {view.parameters[0].name: tail.upper()}
    return None, {}


def api_graph(query, _body) -> dict:
    view_id = (query.get("view") or [""])[0]
    model, views = _load_all()
    palette = _palette(model, query)
    view, from_id = _find_view(views, view_id)
    if view is None:
        raise ApiError("unknown view %r" % view_id, 404)
    declared = view
    supplied: Dict[str, str] = dict(from_id)

    if view.parameters:
        # `p_<name>=<id>` in the query string. A parameterized view with
        # nothing supplied falls back to the first thing `render_for` picks,
        # so a link to it always draws something rather than erroring.
        for p in view.parameters:
            asked = (query.get("p_" + p.name) or [""])[0]
            if asked:
                supplied[p.name] = asked
        for parameter, value in render_targets(model, view):
            supplied.setdefault(parameter, "")
            if not supplied[parameter]:
                supplied[parameter] = value
        try:
            view = bind(view, supplied, model)
        except ViewError as exc:
            raise ApiError(str(exc), 400)

    try:
        payload = _graph_payload(model, view, palette)
    except ViewError as exc:
        raise ApiError(str(exc), 409)
    payload["viewId"] = view_id
    # The value drawn, not the value asked for: with nothing supplied the
    # server picks one, and a picker showing something else is a lie.
    payload["parameters"] = [
        {
            "name": p.name,
            "type": p.type,
            "description": p.description,
            "value": supplied.get(p.name, ""),
        }
        for p in declared.parameters
    ]
    payload["membership"] = _membership(model, declared)
    return payload


def _listed(value) -> List[str]:
    if value in (None, ""):
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [str(value).strip()]


def _membership(model, view) -> dict:
    """What a person pinned to this drawing or hid from it, by name, so the
    summary shows the decisions rather than leaving them in the file. A pin
    is the one place a view names a thing instead of describing it, and a
    drawing that says so is one nobody mistakes for a query."""

    def named(ids):
        out = []
        for entity_id in ids:
            found = model.find(entity_id)
            out.append({
                "id": entity_id,
                "name": (found[1].get("name") if found else None) or entity_id,
                "type": found[0] if found else None,
                "gone": found is None,
            })
        return out

    return {
        "pinned": named(_listed(view.scope.get("pin"))),
        "hidden": named(_listed(view.scope.get("hide"))),
        "editable": bool(view.source_file),
    }


def _with_places(view):
    """A view read from a file's data, merged with the views it places as
    they are now. Parsed alone, a diagram drawn on the canvas would draw
    without the boundaries it was drawn on."""
    if not view.places:
        return view
    _model, views = _load_all()
    return places_module.attach(view, views)


def _drawn(model, data: dict, subject: Dict[str, str]) -> set:
    """The ids a view's data draws, bound to the subject on screen."""
    try:
        view = _with_places(parse_view(data))
        if view.parameters:
            supplied = {k: str(v) for k, v in (subject or {}).items() if v}
            for parameter, value in render_targets(model, view):
                supplied.setdefault(parameter, value)
            view = bind(view, supplied, model)
        return {node.key for node in resolve(model, view).nodes}
    except ViewError:
        return set()


def api_view_membership(_query, body) -> dict:
    """Pin a thing to one drawing, or hide it from one, with the smallest
    change to the view's file that does it.

    *Show* takes a thing off the view's hidden list and pins it only if it is
    still not drawn; *hide* unpins it and hides it only if it is still drawn.
    So a thing the query already brings is never pinned, and one only a pin
    brought is never hidden as well: the file says as little as it can, and
    the query stays the thing that decides.
    """
    view_id = str(body.get("view") or "").strip()
    asked = {key: _listed(body.get(key)) for key in ("show", "hide", "unpin", "unhide")}
    subject = body.get("subject") or {}
    if not any(asked.values()):
        raise ApiError("nothing to change")
    with _LOCK:
        _shipped_only(view_id)
        path = _existing_view_file(view_id)
        if path is None:
            raise ApiError("unknown view %r" % view_id, 404)
        old = path.read_text(encoding="utf-8-sig")
        data = parse_data_text(old, path.name)
        if not isinstance(data, dict) or str(data.get("view_id") or "") != view_id:
            raise ApiError("%s does not hold only %s" % (path.name, view_id), 409)
        model, _views = _load_all()
        for entity_id in asked["show"] + asked["hide"]:
            if model.find(entity_id) is None:
                raise ApiError("unknown entity %r" % entity_id, 404)

        scope = dict(data.get("scope") or {})
        pins, hides = _listed(scope.get("pin")), _listed(scope.get("hide"))
        changes: List[Tuple[str, str]] = []

        def with_lists():
            out = dict(scope)
            for key, values in (("pin", pins), ("hide", hides)):
                if values:
                    out[key] = list(values)
                else:
                    out.pop(key, None)
            return dict(data, scope=out)

        for entity_id in asked["unpin"]:
            if entity_id in pins:
                pins.remove(entity_id)
                changes.append(("unpinned", entity_id))
        for entity_id in asked["unhide"]:
            if entity_id in hides:
                hides.remove(entity_id)
                changes.append(("shown", entity_id))
        for entity_id in asked["show"]:
            if entity_id in hides:
                hides.remove(entity_id)
                changes.append(("shown", entity_id))
            if entity_id not in _drawn(model, with_lists(), subject):
                pins.append(entity_id)
                changes.append(("pinned", entity_id))
        for entity_id in asked["hide"]:
            if entity_id in pins:
                pins.remove(entity_id)
                changes.append(("unpinned", entity_id))
            if entity_id in _drawn(model, with_lists(), subject):
                hides.append(entity_id)
                changes.append(("hidden", entity_id))

        named = {}
        for _what, entity_id in changes:
            found = model.find(entity_id)
            named[entity_id] = (found[1].get("name") if found else None) or entity_id
        if not changes:
            return {"view": view_id, "changes": [], "path": path.relative_to(REPO_ROOT).as_posix()}

        new = with_lists()
        _write_text(path, records_module.rewrite(old, new))
        try:
            model, views = _load_all()
        except (ModelError, ArchetypeError, ViewError, ModelFileError) as exc:
            _write_text(path, old)
            raise ApiError("that change would break the model: %s" % exc, 409)
        # Only this view changed, so only this view is checked: a hide that
        # left it drawing nothing is the one thing a pin or a hide can break.
        problem = None
        if not _drawn(model, new, subject):
            problem = "%s draws nothing now; undo the last change or add something to it." % view_id

    return {
        "view": view_id,
        "path": path.relative_to(REPO_ROOT).as_posix(),
        "changes": [{"what": what, "id": entity_id, "name": named[entity_id]} for what, entity_id in changes],
        "problem": problem,
    }


#: Every way two things can be joined, so a neighborhood view draws all of it.
#: An authored view picks its edges deliberately; a focus view is exploratory
#: and hiding a connection is the one thing it must not do.
FOCUS_EDGES = (
    [{"via": "interfaces"}, {"via": "owner"}, {"via": "source_of_truth"}]
    + [{"via": name} for name in RELATION_TYPES]
)

#: Past this the picture stops being a neighborhood and becomes the landscape.
FOCUS_MAX_DEPTH = 4


def focus_view(model, entity_id: str, depth: int):
    """A view built on the fly, centered on one entity.

    Twenty-two authored views answer twenty-two questions well. The question
    asked while exploring — what is around this thing — is not one of them, and
    a view file per entity is not an answer to it.
    """
    found = model.find(entity_id)
    if found is None:
        raise ApiError("unknown entity %r" % entity_id, 404)
    type_name, record = found
    name = record.get("name") or entity_id
    return parse_view(
        {
            "view_id": "focus",
            "title": "%s, %d hop%s out" % (name, depth, "" if depth == 1 else "s"),
            "description": (
                "Everything within %d relationship hop%s of %s, across every kind "
                "of connection. Built on the fly rather than from a view file."
                % (depth, "" if depth == 1 else "s", entity_id)
            ),
            "scope": {
                "include": [{"type": type_name, "where": {"id_in": [entity_id]}}],
                "expand": [{"depth": depth}],
            },
            "edges": FOCUS_EDGES,
            "layout": "cose" if depth > 1 else "LR",
            "limits": {"max_nodes": 240},
        }
    )


def api_focus(query, _body) -> dict:
    entity_id = (query.get("id") or [""])[0]
    try:
        depth = int((query.get("depth") or ["1"])[0] or 1)
    except ValueError:
        raise ApiError("depth must be a number")
    depth = max(1, min(depth, FOCUS_MAX_DEPTH))

    model, _views = _load_all()
    view = focus_view(model, entity_id, depth)
    payload = _graph_payload(model, view, _palette(model, query))
    payload["focusId"] = entity_id
    payload["depth"] = depth
    payload["maxDepth"] = FOCUS_MAX_DEPTH
    return payload


def api_entity(query, _body) -> dict:
    entity_id = (query.get("id") or [""])[0]
    model, _views = _load_all()
    found = model.find(entity_id)
    if found is None:
        raise ApiError("unknown entity %r" % entity_id, 404)
    type_name, record = found
    entity_type = ENTITY_TYPES[type_name]

    related = []
    for name, spec in RELATION_TYPES.items():
        for row in model.relation_rows(name):
            left, right = row.get(spec.left_column), row.get(spec.right_column)
            other = None
            if left == entity_id:
                other, direction = right, "out"
            elif right == entity_id:
                other, direction = left, "in"
            if other:
                located = model.find(str(other))
                related.append(
                    {
                        "relation": name,
                        "direction": direction,
                        "otherId": other,
                        "otherName": located[1].get("name") if located else other,
                        "qualifier": row.get(spec.qualifier) if spec.qualifier else None,
                    }
                )
    for record_i in model.all_of("interfaces"):
        src, dst = record_i.get("source_system_id"), record_i.get("target_system_id")
        if entity_id in (src, dst):
            other = dst if src == entity_id else src
            located = model.find(str(other)) if other else None
            related.append(
                {
                    "relation": "interface",
                    "direction": "out" if src == entity_id else "in",
                    "otherId": other,
                    "otherName": located[1].get("name") if located else other,
                    "qualifier": record_i.get("protocol"),
                    "via": record_i.get("interface_id"),
                }
            )
        elif record_i.get("offered_interface_id") == entity_id:
            # What goes through an interface: the system at the far end of
            # each connection, the one that is not its owner.
            owner = record.get("system_id")
            other = dst if src == owner else src
            located = model.find(str(other)) if other else None
            related.append(
                {
                    "relation": "through",
                    "direction": "in",
                    "otherId": other,
                    "otherName": located[1].get("name") if located else other,
                    "qualifier": record_i.get("protocol"),
                    "via": record_i.get("interface_id"),
                }
            )
    # What a system offers, and the system an interface is offered by: a
    # reference field the relation tables above do not hold.
    for offered in model.all_of("offered_interfaces"):
        if offered.get("system_id") == entity_id:
            related.append({"relation": "offers", "direction": "out", "otherId": offered["offered_interface_id"],
                            "otherName": offered.get("name") or offered["offered_interface_id"],
                            "qualifier": offered.get("protocol")})
    if type_name == "offered_interfaces" and record.get("system_id"):
        located = model.find(str(record["system_id"]))
        related.append({"relation": "offers", "direction": "in", "otherId": record["system_id"],
                        "otherName": located[1].get("name") if located else record["system_id"],
                        "qualifier": None})

    clean = {k: v for k, v in record.items() if not k.startswith("_")}
    return {
        "type": type_name,
        "pk": entity_type.pk,
        "label": entity_type.label,
        "record": clean,
        "sourceFile": str(Path(record.get("_source_file", "")).relative_to(REPO_ROOT))
        if record.get("_source_file")
        else "",
        "generated": bool(record.get("archetype_instance")),
        "home": _home_payload(type_name, record),
        "related": related,
    }


def _home_payload(type_name: str, record: dict) -> dict:
    """Where the record lives and what a save would do, so the inspector can
    say it before anyone fills in a form."""
    home = records_module.home_of(type_name, record)
    where = ""
    if home.path is not None:
        try:
            where = str(home.path.relative_to(REPO_ROOT))
        except ValueError:
            where = str(home.path)
    return {"kind": home.kind, "file": where, "note": home.note}


def api_impact(query, _body) -> dict:
    """What else is affected if this entity changes."""
    entity_id = (query.get("id") or [""])[0]
    depth = int((query.get("depth") or ["3"])[0])
    model, _views = _load_all()
    try:
        result = impact_module.analyze(model, entity_id, max_distance=max(1, min(depth, 5)))
    except KeyError:
        raise ApiError("unknown entity %r" % entity_id, 404)
    return impact_module.to_payload(result)


#: Relations written by the app land here, so hand-authored relation files are
#: never rewritten by a form. Everything else in `relations/` stays yours.
APP_RELATIONS = "app_edits.yaml"


def _relation_targets(model, spec, side: str) -> List[dict]:
    """Candidate entities for one end of a relation, for the picker."""
    type_name = spec.left if side == "left" else spec.right
    entity_type = ENTITY_TYPES[type_name]
    return [
        {
            "id": record[entity_type.pk],
            "name": record.get("name") or record[entity_type.pk],
            "type": type_name,
        }
        for record in sorted(
            model.all_of(type_name), key=lambda r: str(r.get("name") or "").lower()
        )
    ]


def api_relations(query, _body) -> dict:
    """What can be linked to what, and what already is.

    Drives the linkage picker: for a given entity, which relations it can take
    part in, which end it sits on, and the candidates for the other end.
    """
    entity_id = (query.get("id") or [""])[0]
    model, _views = _load_all()
    found = model.find(entity_id)
    if found is None:
        raise ApiError("unknown entity %r" % entity_id, 404)
    type_name, _record = found

    options = []
    for name, spec in RELATION_TYPES.items():
        for side in ("left", "right"):
            if (spec.left if side == "left" else spec.right) != type_name:
                continue
            other_side = "right" if side == "left" else "left"
            options.append(
                {
                    "relation": name,
                    "side": side,
                    "otherType": spec.right if side == "left" else spec.left,
                    "otherLabel": ENTITY_TYPES[
                        spec.right if side == "left" else spec.left
                    ].label,
                    "qualifier": spec.qualifier,
                    "candidates": _relation_targets(model, spec, other_side),
                }
            )

    existing = []
    for name, spec in RELATION_TYPES.items():
        for row in model.relation_rows(name):
            left, right = str(row.get(spec.left_column)), str(row.get(spec.right_column))
            if entity_id not in (left, right):
                continue
            other = right if left == entity_id else left
            located = model.find(other)
            existing.append(
                {
                    "relation": name,
                    "left": left,
                    "right": right,
                    "otherId": other,
                    "otherName": located[1].get("name") if located else other,
                    "qualifier": row.get(spec.qualifier) if spec.qualifier else None,
                    "editable": Path(str(row.get("_source", ""))).name == APP_RELATIONS,
                }
            )
    return {"id": entity_id, "type": type_name, "options": options, "existing": existing}


def _load_app_relations(filename: str = APP_RELATIONS) -> dict:
    path = REPO_ROOT / "10_MODEL" / "relations" / filename
    if not path.exists():
        return {}
    return read_data_file(path) or {}


def _write_app_relations(data: dict, filename: str = APP_RELATIONS) -> Path:
    lines = [
        "# Relations created in the app.",
        "#",
        "# Kept separate so a form never rewrites a hand-authored relation file.",
        "# Editing this by hand is fine; the app reads it back the same way.",
    ]
    for name in sorted(data):
        rows = data[name]
        if not rows:
            continue
        spec = RELATION_TYPES[name]
        columns = [spec.left_column, spec.right_column]
        if spec.qualifier:
            columns.append(spec.qualifier)
        lines.append("")
        lines.append("%s:" % name)
        for row in rows:
            first = True
            for column in columns:
                if not row.get(column):
                    continue
                lines.append(
                    "%s%s: %s"
                    % ("  - " if first else "    ", column, _yaml_value(row[column]))
                )
                first = False
    path = REPO_ROOT / "10_MODEL" / "relations" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def api_relate(_query, body) -> dict:
    """Create one relation row."""
    name = body.get("relation")
    left = str(body.get("left") or "").strip()
    right = str(body.get("right") or "").strip()
    qualifier = str(body.get("qualifier") or "").strip()

    if name not in RELATION_TYPES:
        raise ApiError("unknown relation %r" % name)
    spec = RELATION_TYPES[name]
    if not (SAFE_ID.match(left) and SAFE_ID.match(right)):
        raise ApiError("both ends must be identifiers")

    with _LOCK:
        model, _views = _load_all()
        for end, expected in ((left, spec.left), (right, spec.right)):
            located = model.find(end)
            if located is None:
                raise ApiError("unknown entity %r" % end, 404)
            if located[0] != expected:
                raise ApiError(
                    "%s is a %s; %s expects a %s on that end"
                    % (end, located[0], name, expected)
                )

        for row in model.relation_rows(name):
            if (str(row.get(spec.left_column)), str(row.get(spec.right_column))) == (left, right):
                if not spec.qualifier or str(row.get(spec.qualifier) or "") == qualifier:
                    raise ApiError("that link already exists", 409)

        data = _load_app_relations()
        row = {spec.left_column: left, spec.right_column: right}
        if spec.qualifier and qualifier:
            row[spec.qualifier] = qualifier
        data.setdefault(name, []).append(row)
        path = _write_app_relations(data)

        model, views = _load_all()
        report = _report(model, views)
    return {
        "linked": "%s %s %s" % (left, name, right),
        "path": str(path.relative_to(REPO_ROOT)),
        "errors": [f.format() for f in report.errors],
        "warnings": len(report.warnings),
    }


def api_unrelate(_query, body) -> dict:
    """Remove one relation row, if the app is the one that wrote it."""
    name = body.get("relation")
    left = str(body.get("left") or "").strip()
    right = str(body.get("right") or "").strip()
    if name not in RELATION_TYPES:
        raise ApiError("unknown relation %r" % name)
    spec = RELATION_TYPES[name]

    with _LOCK:
        data = _load_app_relations()
        rows = data.get(name) or []
        keep = [
            r for r in rows
            if (str(r.get(spec.left_column)), str(r.get(spec.right_column))) != (left, right)
        ]
        if len(keep) == len(rows):
            raise ApiError(
                "that link is not in %s. Relations written by hand are removed by "
                "hand, so the app never edits a file it did not create." % APP_RELATIONS,
                409,
            )
        data[name] = keep
        _write_app_relations(data)
        model, views = _load_all()
        report = _report(model, views)
    return {
        "unlinked": "%s %s %s" % (left, name, right),
        "errors": [f.format() for f in report.errors],
        "warnings": len(report.warnings),
    }


def api_flows(query, _body) -> dict:
    """Every flow, with its ordered steps resolved to names."""
    model, _views = _load_all()
    out = []
    for flow_id in all_flows(model):
        record = model.get("flows", flow_id) or {}
        steps = []
        for step in steps_for(model, flow_id):
            interface = step["interface"]
            source = model.get("systems", str(interface.get("source_system_id"))) or {}
            target = model.get("systems", str(interface.get("target_system_id"))) or {}
            steps.append(
                {
                    "sequence": step["sequence"],
                    "interfaceId": interface["interface_id"],
                    "fromId": interface.get("source_system_id"),
                    "from": source.get("name") or interface.get("source_system_id"),
                    "toId": interface.get("target_system_id"),
                    "to": target.get("name") or interface.get("target_system_id"),
                    "protocol": interface.get("protocol"),
                    "style": interface.get("integration_style"),
                }
            )
        out.append(
            {
                "id": flow_id,
                "name": record.get("name") or flow_id,
                "description": record.get("description") or "",
                "trigger": record.get("trigger") or "",
                "target": record.get("target_latency") or "",
                "criticality": record.get("criticality") or "",
                "status": record.get("status") or "",
                "mermaid": render_sequence(model, flow_id),
                "steps": steps,
            }
        )
    # Every step joins two systems, so the heads of a sequence are drawn
    # in the systems' swatch of the tone the page asked for.
    swatch = _palette(model, query).type_swatch("systems")
    return {"flows": out, "swatch": {"fill": swatch.fill, "stroke": swatch.stroke, "ink": swatch.ink}}


def api_source(query, _body) -> dict:
    """The diagram source for whatever is on screen.

    A PNG is what you show someone; the source is what you commit, paste into a
    pull request, or hand to a wiki that renders Mermaid. Focus views have no
    artifact on disk, so this is the only way to get one out of them at all.
    """
    view_id = (query.get("view") or [""])[0]
    focus_id = (query.get("focus") or [""])[0]
    model, views = _load_all()
    palette = Palette(model.config.get("palette"))

    if focus_id:
        try:
            depth = int((query.get("depth") or ["1"])[0] or 1)
        except ValueError:
            raise ApiError("depth must be a number")
        view = focus_view(model, focus_id, max(1, min(depth, FOCUS_MAX_DEPTH)))
    else:
        view, from_id = _find_view(views, view_id)
        if view is None:
            raise ApiError("unknown view %r" % view_id, 404)
        if view.parameters:
            targets = from_id or dict(render_targets(model, view))
            if not targets:
                # An empty selection, not a missing argument: nothing on this
                # model qualifies for the view yet, and saying so beats asking
                # for a value there is no candidate for.
                raise ApiError(
                    "view %s takes %s and nothing qualifies yet; there is nothing to draw"
                    % (view.view_id, ", ".join(p.name for p in view.parameters)),
                    404,
                )
            try:
                view = bind(view, targets, model)
            except ViewError as exc:
                raise ApiError(str(exc), 400)

    try:
        graph = resolve(model, view)
    except ViewError as exc:
        raise ApiError(str(exc), 409)

    # The app and `terrane render` must not be two renderers: a timeline's Mermaid
    # is the same gantt the artifact holds. Its Structurizr DSL is of the
    # graph -- the packages and the systems they reach -- which stands.
    mermaid_text = render_timeline(graph) if view.kind == "timeline" else render_mermaid(graph, palette, model)
    return {
        "viewId": view.view_id,
        "title": view.title,
        "formats": [
            {
                "id": "mermaid",
                "label": "Mermaid",
                "extension": "mmd",
                "text": mermaid_text,
            },
            {
                "id": "structurizr",
                "label": "Structurizr DSL",
                "extension": "dsl",
                "text": render_workspace(model, [graph], palette, name=view.title),
            },
        ],
    }


#: A view file has to be named after its own id, so the folder stays browsable
#: and two files can never claim the same view.
VIEW_SUFFIX = ".view.yaml"

STARTER_VIEW = """\
view_id: %s
title: %s
description: >
  One sentence on the question this diagram answers, and what a reader should
  do about what they see. A view without this is a picture nobody can act on.
layout: LR
node_label: name
renderers: [mermaid]

# What is on the diagram. Every clause names an entity type and an optional
# `where`; the results are unioned.
scope:
  include:
    - type: systems
      where:
        status: [Active]
  # Optional. Pulls in neighbors of what `include` selected.
  # expand:
  #   - relation: interfaces
  #     depth: 1
  #     types: [systems]

# Boundaries. A single field, or a list for nested containers.
# group_by: company_domain

# What to draw between the nodes. `interfaces`, `owner`, `source_of_truth`,
# or any relation name.
edges:
  - via: interfaces
    label: protocol

style:
  color_by: criticality

limits:
  max_nodes: 60
"""


def _view_path(view_id: str) -> Path:
    if not SAFE_ID.match(view_id):
        raise ApiError("a view id must be an identifier: letters, digits, . _ -")
    return REPO_ROOT / "30_VIEWS" / (view_id + VIEW_SUFFIX)


def _existing_view_file(view_id: str) -> Optional[Path]:
    """Where a view actually lives, which need not be the canonical name."""
    folder = REPO_ROOT / "30_VIEWS"
    canonical = _view_path(view_id)
    if canonical.exists():
        return canonical
    for path in sorted(folder.glob("*")):
        if path.suffix.lower() not in (".yaml", ".yml", ".json"):
            continue
        try:
            data = read_data_file(path)
        except ModelFileError:
            continue
        if isinstance(data, dict) and str(data.get("view_id") or "") == view_id:
            return path
    return None


def _shipped_view_file(view_id: str) -> Optional[Path]:
    """The installed terrane's file for a shipped view the estate reads and
    has no copy of its own: read to show, never written."""
    if _existing_view_file(view_id) is not None or not is_shipped_view(REPO_ROOT, view_id):
        return None
    from terrane.shipped import shipped_root

    folder = shipped_root() / "30_VIEWS"
    for path in [folder / (view_id + VIEW_SUFFIX)] + sorted(folder.glob("*")):
        if path.is_file() and path.suffix.lower() in (".yaml", ".yml", ".json"):
            data = read_data_file(path)
            if isinstance(data, dict) and str(data.get("view_id") or "") == view_id:
                return path
    return None


def _shipped_only(view_id: str) -> None:
    """Refuse a change to a shipped view the estate has no copy of, saying how
    to make one: the editor's save writes the estate's own copy, which says
    `replaces:`, and a pin or a hide then changes that copy."""
    if _shipped_view_file(view_id) is not None:
        raise ApiError("%r is a view shipped with terrane. Open it in the view editor and save it to make "
                       "this estate's own copy, which stands in for the shipped one; change that copy." % view_id,
                       409)


def _with_replaces(text: str, view_id: str) -> str:
    """A shipped view's text as the estate's copy of it: `replaces:` with its
    own id, under the `view_id` line, unless it says so already."""
    if re.search(r"^replaces\s*:", text, re.M):
        return text
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if re.match(r"^view_id\s*:", line):
            return "".join(lines[:i + 1] + ["replaces: %s\n" % view_id] + lines[i + 1:])
    return "replaces: %s\n" % view_id + text


def _yaml_complaint(message: str) -> str:
    """The parser's complaint, minus the parts that mean nothing in a text box.

    PyYAML answers with a source name (`<unicode string>`), a position, a copy
    of the offending line and a caret under it. In a file that is helpful; in a
    textarea the person is already looking at the line, so what is left worth
    saying is what went wrong and where.
    """
    lines = [line for line in str(message).splitlines() if line.strip()]
    complaints: List[str] = []
    where = ""
    skip_snippet = False
    for line in lines:
        stripped = line.strip()
        if stripped == "^":
            continue
        position = re.search(r"line (\d+), column (\d+)(:?)", stripped)
        if position:
            where = "line %s, column %s" % position.groups()[:2]
            # PyYAML's own parser follows a position ending in a colon with the
            # source line, echoed back; libyaml's has no colon and no echo, and
            # the line after it is the complaint itself.
            skip_snippet = bool(position.group(3))
            continue
        if skip_snippet:
            skip_snippet = False
            continue
        if complaints and stripped == complaints[-1]:
            continue
        complaints.append(stripped)

    if not complaints:
        detail = "could not parse it"
    elif len(complaints) == 1:
        detail = complaints[0]
    else:
        # The last line names what actually broke; the first names the context.
        detail = "%s (%s)" % (complaints[-1], complaints[0])
    return detail + (" at " + where if where else "")


def _view_from_text(text: str, expect_id: Optional[str] = None):
    """Parse editor text into a View, with the failure the editor should show."""
    try:
        data = parse_data_text(text, "the view you are editing")
    except ModelFileError as exc:
        raise ApiError("that is not valid YAML: %s" % _yaml_complaint(exc.message), 422)
    if not isinstance(data, dict):
        raise ApiError("a view is a mapping of fields, not a %s" % type(data).__name__, 422)
    try:
        view = parse_view(data)
    except ViewError as exc:
        raise ApiError(str(exc), 422)
    if not SAFE_ID.match(str(view.view_id)):
        raise ApiError("a view id must be an identifier: letters, digits, . _ -", 422)
    if expect_id and str(view.view_id) != expect_id:
        raise ApiError(
            "this file is %s; changing view_id to %r would leave two views claiming "
            "one file. Save it as a new view instead." % (expect_id, view.view_id),
            409,
        )
    return _with_places(view)


def api_view(query, _body) -> dict:
    """The source of one view, plus what the editor needs to help someone write.

    Every diagram in here is a query, so the honest thing to let someone edit
    is the query -- not a canvas that pretends the diagram is the artifact.
    """
    view_id = (query.get("id") or [""])[0]
    model, _views = _load_all()

    if view_id:
        path = _existing_view_file(view_id)
        shipped = _shipped_view_file(view_id) if path is None else None
        if path is None and shipped is None:
            raise ApiError("unknown view %r" % view_id, 404)
        if shipped is not None:
            # The shipped text, shown; a save writes the estate's own copy.
            text = shipped.read_text(encoding="utf-8-sig")
            where = "shipped with terrane; saving writes %s" % (Path("30_VIEWS") / (view_id + VIEW_SUFFIX)).as_posix()
        else:
            text = path.read_text(encoding="utf-8-sig")
            where = str(path.relative_to(REPO_ROOT))
    else:
        # A starter that resolves to something on the first preview. An empty
        # box is a worse place to begin than a working example.
        text = STARTER_VIEW % ("my-view", "My View")
        where = str(Path("30_VIEWS") / ("my-view" + VIEW_SUFFIX))

    try:
        data = parse_data_text(text, where)
    except ModelFileError:
        data = None
    return {
        "id": view_id,
        "text": text,
        "data": data if isinstance(data, dict) else None,
        "path": where,
        "isNew": not view_id,
        "help": _view_help(model),
        "vocab": _view_vocabulary(model),
    }


#: Fields a filter or a box has no use for: free text, and the bookkeeping of
#: a shape. The composer lists every other field a type has.
_UNFILTERED = ("name", "description", "archetype_instance", "module", "last_reviewed")


def _view_vocabulary(model) -> dict:
    """What the composer offers, read out of the model: for each type, how
    many there are and each field with the values it holds -- the declared
    list where the metamodel has one, else the values in use, most used
    first -- and every relation with its two ends. A value nobody has used
    yet is still typed, never refused."""
    types: Dict[str, Any] = {}
    for type_name, entity_type in ENTITY_TYPES.items():
        records = list(model.entities.get(type_name, {}).values())
        fields = []
        for spec in entity_type.fields:
            if spec.name in _UNFILTERED or spec.name == entity_type.pk:
                continue
            seen: Dict[str, int] = {}
            for record in records:
                value = record.get(spec.name)
                for item in (value if isinstance(value, list) else [value]):
                    if item in (None, "") or isinstance(item, dict):
                        continue
                    seen[str(item)] = seen.get(str(item), 0) + 1
            if not seen and not spec.enum:
                continue
            values = list(spec.enum) if spec.enum else [
                v for v, _n in sorted(seen.items(), key=lambda kv: (-kv[1], kv[0]))[:60]
            ]
            fields.append({"name": spec.name, "values": values, "ref": spec.ref, "used": sum(seen.values())})
        types[type_name] = {"label": entity_type.label, "count": len(records), "fields": fields}
    relations = [
        {"name": name, "left": spec.left, "right": spec.right, "qualifier": spec.qualifier}
        for name, spec in sorted(RELATION_TYPES.items())
    ]
    return {"types": types, "relations": relations}


def _view_help(model) -> dict:
    """The vocabulary, taken from the model rather than from a document.

    A cheatsheet written by hand goes stale; this cannot.
    """
    group_fields = set()
    for type_name, entity_type in ENTITY_TYPES.items():
        for record in model.entities.get(type_name, {}).values():
            for field in entity_type.fields:
                if record.get(field.name) not in (None, "") and not field.ref:
                    group_fields.add(field.name)
    for skip in ("name", "description", "tags"):
        group_fields.discard(skip)

    return {
        "types": sorted(ENTITY_TYPES),
        "relations": sorted(RELATION_TYPES),
        "edgeVia": ["interfaces", "owner", "source_of_truth"] + sorted(RELATION_TYPES),
        "operators": [
            {"name": "tags_any", "note": "matches if the record carries any of these tags"},
            {"name": "tags_all", "note": "matches only if it carries all of them"},
            {"name": "tags_none", "note": "excludes anything carrying one of them"},
            {"name": "has_any", "note": "relation names: at least one of them exists"},
            {"name": "has_all", "note": "every one of those relations exists"},
            {"name": "has_none", "note": "none of those relations exists"},
            {"name": "id_in", "note": "an explicit list of ids"},
            {"name": "id_prefix", "note": "every id starting with this"},
            {"name": "<field>: [a, b]", "note": "field equals any of these values"},
            {"name": "<field>: {not: [a]}", "note": "field is none of these"},
            {"name": "<field>: {exists: true}", "note": "field is present and not empty"},
        ],
        "groupFields": sorted(group_fields),
        "layouts": ["LR", "TB"],
    }


def api_view_preview(query, body) -> dict:
    """Draw the view in the editor without writing anything to disk.

    Given text, the text is drawn and handed back parsed, which is how the
    file editor returns to the composer. Given data, the data is drawn and
    handed back as the file it would be saved as: the view's own file
    rewritten by value, or a new one written plain. The composer shows that
    text, and saves a new view from it."""
    data = body.get("data")
    view_id = str(body.get("id") or "").strip() or None
    if isinstance(data, dict):
        try:
            view = _with_places(parse_view(data))
        except ViewError as exc:
            raise ApiError(str(exc), 422)
        existing = _existing_view_file(view_id) if view_id else None
        if existing is not None:
            text = records_module.rewrite(existing.read_text(encoding="utf-8-sig"), data)
        else:
            text = yaml_text(data)
    else:
        text = str(body.get("text") or "")
        view = _view_from_text(text)
        data = parse_data_text(text, "the view you are editing")
    model, _views = _load_all()
    try:
        payload = _graph_payload(model, view, _palette(model, query))
    except ViewError as exc:
        raise ApiError(str(exc), 409)
    payload["preview"] = True
    payload["text"] = text
    payload["data"] = data
    return payload


def api_view_save(_query, body) -> dict:
    text = str(body.get("text") or "")
    editing = str(body.get("id") or "").strip() or None

    with _LOCK:
        copying = editing is not None and _shipped_view_file(editing) is not None
        if editing is not None and _existing_view_file(editing) is None and not copying:
            raise ApiError("unknown view %r" % editing, 404)

        view = _view_from_text(text, expect_id=editing)
        view_id = str(view.view_id)
        existing = _existing_view_file(view_id)
        if editing is None and existing is not None:
            raise ApiError(
                "a view called %r already exists in %s. Open it and edit it, or "
                "choose another id." % (view_id, existing.relative_to(REPO_ROOT)),
                409,
            )
        if editing is None and _shipped_view_file(view_id) is not None:
            raise ApiError(
                "%r is the id of a view shipped with terrane. Open that view and save it to make this "
                "estate's own copy, or choose another id." % view_id, 409)
        if copying:
            # The estate's own copy of a shipped view, standing in for it.
            text = _with_replaces(text, view_id)
        path = existing if existing is not None else _view_path(view_id)

        previous = path.read_text(encoding="utf-8-sig") if path.exists() else None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")

        # Everything is loaded again from disk: a view that only parses in
        # memory is not saved, it is a file the next start would refuse.
        try:
            model, views = _load_all()
        except (ModelError, ArchetypeError, ViewError, ModelFileError) as exc:
            if previous is None:
                path.unlink()
            else:
                path.write_text(previous, encoding="utf-8")
            raise ApiError("saving that would break the model: %s" % exc, 409)

        report = _report(model, views)
        problem = None
        try:
            graph = resolve(model, view)
            counts = {"nodes": len(graph.nodes), "edges": len(graph.edges)}
            notes = list(graph.notes)
        except ViewError as exc:
            # Saved anyway. Someone stopping halfway through an edit should not
            # lose the work, but they should be told the view draws nothing.
            counts = {"nodes": 0, "edges": 0}
            notes = []
            problem = str(exc)

    return {
        "id": view_id,
        "title": view.title,
        "path": str(path.relative_to(REPO_ROOT)),
        "created": previous is None,
        "counts": counts,
        "notes": notes,
        "problem": problem,
        "errors": [f.format() for f in report.errors],
        "warnings": len(report.warnings),
    }


def api_view_compose(_query, body) -> dict:
    """Save a view from its data rather than its text, keeping every line of
    the file whose value did not change: the comment beside an expansion
    rule, a description wrapped by hand. The composer and the connect
    chooser's "draw these lines here" both write this way, so the file stays
    one a person would recognize as theirs."""
    view_id = str(body.get("id") or "").strip()
    data = body.get("data")
    if not isinstance(data, dict):
        raise ApiError("a view is a mapping of fields", 422)
    with _LOCK:
        _shipped_only(view_id)
        path = _existing_view_file(view_id)
        if path is None:
            raise ApiError("unknown view %r" % view_id, 404)
        if str(data.get("view_id") or "") != view_id:
            raise ApiError(
                "this file is %s; changing view_id would leave two views claiming one file" % view_id, 409)
        try:
            view = _with_places(parse_view(data))
        except ViewError as exc:
            raise ApiError(str(exc), 422)
        old = path.read_text(encoding="utf-8-sig")
        _write_text(path, records_module.rewrite(old, data))
        try:
            model, views = _load_all()
        except (ModelError, ArchetypeError, ViewError, ModelFileError) as exc:
            _write_text(path, old)
            raise ApiError("saving that would break the model: %s" % exc, 409)
        problem = None
        try:
            graph = resolve(model, view) if not view.parameters else None
            counts = {"nodes": len(graph.nodes), "edges": len(graph.edges)} if graph else None
        except ViewError as exc:
            counts = {"nodes": 0, "edges": 0}
            problem = str(exc)
    return {
        "id": view_id,
        "path": path.relative_to(REPO_ROOT).as_posix(),
        "counts": counts,
        "problem": problem,
    }


def _field_via(field_name: str) -> List[str]:
    """The edge kinds that draw a reference field, for "does this view show
    it"; `owner` and `source_of_truth` are the names views use for the two
    every drawing knows."""
    out = [field_name]
    if field_name == "owner_org_id":
        out.append("owner")
    return out


def _qualifier_values(model, name: str, spec) -> List[str]:
    """What has been written in a relation's qualifier before, most used
    first, so the chooser offers the words the model already uses rather
    than a box to type a new spelling of one into."""
    seen: Dict[str, int] = {}
    for row in model.relation_rows(name):
        value = str(row.get(spec.qualifier) or "").strip()
        if value:
            seen[value] = seen.get(value, 0) + 1
    return [v for v, _n in sorted(seen.items(), key=lambda kv: (-kv[1], kv[0]))][:10]


def api_connect_options(query, _body) -> dict:
    """Every way the metamodel lets two things be joined, both ways round,
    and which of them already are: a relation row, an interface between two
    systems, or one of them naming the other in a reference field. With a
    view, each says whether that drawing draws such a line, so a connection
    made on a drawing that would not show it can say so."""
    a = (query.get("from") or [""])[0]
    b = (query.get("to") or [""])[0]
    view_id = (query.get("view") or [""])[0]
    model, views = _load_all()
    found_a, found_b = model.find(a), model.find(b)
    if found_a is None or found_b is None:
        raise ApiError("unknown entity %r" % (a if found_a is None else b), 404)
    if a == b:
        raise ApiError("a thing is not connected to itself here")
    ta, ra = found_a
    tb, rb = found_b

    drawn_vias = None
    if view_id:
        view, _from_id = _find_view(views, view_id)
        if view is not None:
            drawn_vias = {str(e.get("via")) for e in (view.edges or [{"via": "interfaces"}])}

    def drawn(vias):
        if drawn_vias is None:
            return None
        return any(v in drawn_vias for v in vias)

    options: List[dict] = []
    for name, spec in sorted(RELATION_TYPES.items()):
        pairs = [(a, b, ta, tb), (b, a, tb, ta)] if a != b else [(a, b, ta, tb)]
        for left, right, left_type, right_type in pairs:
            if spec.left != left_type or spec.right != right_type:
                continue
            exists = [
                str(row.get(spec.qualifier) or "") if spec.qualifier else ""
                for row in model.relation_rows(name)
                if str(row.get(spec.left_column)) == left and str(row.get(spec.right_column)) == right
            ]
            options.append({
                "kind": "relation", "relation": name, "from": left, "to": right,
                "qualifier": spec.qualifier,
                "values": _qualifier_values(model, name, spec) if spec.qualifier else [],
                "exists": bool(exists), "existing": exists,
                "drawn": drawn([name]),
            })
    if ta == "systems" and tb == "systems":
        # Every kind of connection the library knows, for the second step: a
        # new interface is proposed with the chosen kind's fields. And what
        # either end offers that the connection could go through: the API
        # the one called offers, the topic the one publishing offers.
        kinds = _connection_kinds()
        for source, target in ((a, b), (b, a)):
            found = [
                r for r in model.all_of("interfaces")
                if r.get("source_system_id") == source and r.get("target_system_id") == target
            ]
            offered = [_offered_payload(model, r) for r in model.all_of("offered_interfaces")
                       if (r.get("system_id") == target and r.get("integration_style") != "Event")
                       or (r.get("system_id") == source and r.get("integration_style") == "Event")]
            options.append({
                "kind": "interface", "from": source, "to": target,
                "exists": bool(found), "existing": [str(r.get("interface_id")) for r in found],
                "existingKinds": sorted({kinds[k].name for k in (kind_of(r, kinds) for r in found) if k}),
                "kinds": [_kind_payload(k) for k in kinds.values()],
                "offered": sorted(offered, key=lambda o: o["name"].lower()),
                "drawn": drawn(["interfaces"]),
            })
    if {ta, tb} == {"systems", "offered_interfaces"}:
        # A system dropped on an interface another system offers: a
        # connection between the two systems, through it. Made the way the
        # traffic runs: the caller to the API's owner, a topic's publisher
        # to its reader.
        door, door_record, other = (b, rb, a) if tb == "offered_interfaces" else (a, ra, b)
        owner = str(door_record.get("system_id") or "")
        if owner and owner != other:
            event = door_record.get("integration_style") == "Event"
            source, target = (owner, other) if event else (other, owner)
            found = [r for r in model.all_of("interfaces")
                     if r.get("offered_interface_id") == door
                     and r.get("source_system_id") == source and r.get("target_system_id") == target]
            located = model.find(owner)
            options.insert(0, {
                "kind": "through", "from": source, "to": target, "door": _offered_payload(model, door_record),
                "ownerName": located[1].get("name") if located else owner,
                "exists": bool(found), "existing": [str(r.get("interface_id")) for r in found],
                "drawn": drawn(["interfaces"]),
            })
    for holder, other, holder_type, other_type, record in ((a, b, ta, tb, ra), (b, a, tb, ta, rb)):
        for spec in ENTITY_TYPES[holder_type].fields:
            if spec.ref != other_type or spec.name in ("source_system_id", "target_system_id"):
                continue
            home = records_module.home_of(holder_type, record)
            editable = home.kind in ("own", "shared", "harvested")
            options.append({
                "kind": "field", "field": spec.name, "from": holder, "to": other,
                "current": record.get(spec.name) or None,
                "exists": str(record.get(spec.name) or "") == other,
                "editable": editable, "why": None if editable else home.note,
                "drawn": drawn(_field_via(spec.name)),
            })

    return {
        "from": {"id": a, "type": ta, "name": ra.get("name") or a},
        "to": {"id": b, "type": tb, "name": rb.get("name") or b},
        "options": options,
    }


def _offered_payload(model, record: dict) -> dict:
    """An offered interface as the connect chooser offers it: what a new
    connection through it is proposed with."""
    owner = model.find(str(record.get("system_id") or ""))
    return {
        "id": record["offered_interface_id"], "name": record.get("name") or record["offered_interface_id"],
        "system": record.get("system_id"), "systemName": owner[1].get("name") if owner else record.get("system_id"),
        "protocol": record.get("protocol") or "", "integration_style": record.get("integration_style") or "",
        "auth_method": record.get("auth_method") or "", "data_classification": record.get("data_classification") or "",
        "frequency": record.get("frequency") or "",
    }


def api_regroup_options(_query, body) -> dict:
    """What dropping a box into another boundary would change, asked before
    anything is written. A boundary is one value of a field, so the answer
    is the field set on the record, from what to what, and every drawing
    grouped by that field the box moves on, joins or leaves -- or why this
    record cannot be moved from here. The write is the one-field save."""
    entity_id = str(body.get("id") or "").strip()
    into = []
    for level in body.get("into") or []:
        if not isinstance(level, dict) or not str(level.get("field") or "").strip():
            raise ApiError("each level of `into` is a field and a value")
        into.append((str(level["field"]).strip(), level.get("value")))
    if not into:
        raise ApiError("nothing to move it into")
    model, views = _load_all()
    try:
        plan = regroup_module.plan(model, views, entity_id, into)
    except KeyError:
        raise ApiError("unknown entity %r" % entity_id, 404)
    fields = {f.name: f for f in ENTITY_TYPES[plan.entity_type].fields}
    # The drawing the box was dropped on, so the chooser can call the rest
    # "other" views, and warn when the move takes the box off this one.
    here, from_id = _find_view(views, str(body.get("view") or ""))
    here_subject = str(body.get("subject") or next(iter(from_id.values()), ""))

    def said(field, value):
        # A reference field holds an id, and the boundary was labeled with
        # the name; the chooser says it the way the drawing did.
        if value in (None, ""):
            return ""
        spec = fields.get(field)
        if spec is not None and spec.ref:
            located = model.get(spec.ref, str(value))
            if located and located.get("name"):
                return str(located["name"])
        return str(value)

    def plain(value):
        return value if value is None or isinstance(value, (str, int, float, bool)) else str(value)

    return {
        "entity": {"id": plan.entity_id, "type": plan.entity_type, "name": plan.name},
        "changes": [
            {
                "field": c.field,
                "words": regroup_module.words(c.field),
                "before": plain(c.before), "beforeLabel": said(c.field, c.before),
                "after": plain(c.after), "afterLabel": said(c.field, c.after),
            }
            for c in plan.changes
        ],
        "blocked": plan.blocked,
        "note": plan.note,
        "drawings": [
            {
                "view": d.view_id, "title": d.title, "subject": d.subject,
                "subjectName": d.subject_name, "effect": d.effect,
                "here": here is not None and d.view_id == here.view_id
                and (not d.subject or d.subject == here_subject),
            }
            for d in plan.drawings
        ],
    }


def api_view_delete(_query, body) -> dict:
    view_id = str(body.get("id") or "").strip()
    with _LOCK:
        _shipped_only(view_id)
        path = _existing_view_file(view_id)
        if path is None:
            raise ApiError("unknown view %r" % view_id, 404)
        # A view file holds exactly one view, so removing it removes one thing.
        # The entity delete guard exists because that is not true of every file.
        data = read_data_file(path)
        if not isinstance(data, dict) or str(data.get("view_id") or "") != view_id:
            raise ApiError("%s does not hold only %s" % (path.name, view_id), 409)
        path.unlink()
        model, views = _load_all()
        report = _report(model, views)
    return {
        "deleted": view_id,
        "path": str(path.relative_to(REPO_ROOT)),
        "errors": [f.format() for f in report.errors],
        "warnings": len(report.warnings),
    }


ARCHETYPE_SUFFIX = ".yaml"

STARTER_ARCHETYPE = """\
archetype_id: %s
title: %s
version: 0.1.0
applies_to: products
description: >
  What this shape actually creates, and why the pieces are the ones they are.
  An archetype is the difference between onboarding being a small edit and
  onboarding being a new diagram, so it is worth saying what it stands for.

# Values supplied per instance. `{name}` in any string below is replaced, and
# `{name|upper}`, `|lower`, `|slug` and `|title` are available as filters.
parameters:
  - name: slug
    required: true
    description: Short lower-case token used in identifiers, e.g. lending
  - name: product_name
    required: true
  - name: owner_org
    required: true

# Applied to every entity this creates, unless the entity overrides it.
defaults:
  status: Planned
  architecture_domain: Application
  togaf_layer: Application

provides:
  systems:
    - system_id: "SYS-{slug|upper}-API"
      name: "{product_name} API"
      description: The service this product exposes.
      criticality: High
      network_zone: Private-App

    - system_id: "SYS-{slug|upper}-STORE"
      name: "{product_name} Store"
      description: Where this product keeps its own state.
      criticality: High
      network_zone: Private-Data

  interfaces:
    - interface_id: "INT-{slug|upper}-API-STORE"
      name: "{product_name} API to Store"
      source_system_id: "SYS-{slug|upper}-API"
      target_system_id: "SYS-{slug|upper}-STORE"
      protocol: SQL
      integration_style: Request-response

relations:
  product_includes_system:
    - system_id: "SYS-{slug|upper}-API"
    - system_id: "SYS-{slug|upper}-STORE"
"""


def _archetype_path(archetype_id: str) -> Path:
    """Where a new shape is written: the organization's library when the
    model names one, the shipped one when it does not."""
    if not SAFE_ID.match(archetype_id):
        raise ApiError("an archetype id must be an identifier: letters, digits, . _ -")
    return own_root(REPO_ROOT).path / ARCHETYPES_DIR / (archetype_id + ARCHETYPE_SUFFIX)


def _existing_archetype_file(archetype_id: str) -> Optional[Path]:
    """The file holding the shape the model reads. The libraries are searched
    last first, so a shape the organization replaced opens as its own
    version, which is the one every product is built from."""
    for base in reversed(_roots()):
        folder = base.path / ARCHETYPES_DIR
        canonical = folder / (archetype_id + ARCHETYPE_SUFFIX)
        if canonical.exists():
            return canonical
        for path in sorted(folder.glob("*")):
            if path.suffix.lower() not in (".yaml", ".yml", ".json"):
                continue
            try:
                data = read_data_file(path)
            except ModelFileError:
                continue
            if isinstance(data, dict) and str(data.get("archetype_id") or "") == archetype_id:
                return path
    return None


def _says_replaces(text: str, record_id: str) -> bool:
    """Whether a file's text says it stands in for `record_id`."""
    try:
        data = parse_data_text(text, "the file")
    except ModelFileError:
        return False
    items = data if isinstance(data, list) else [data]
    return any(
        isinstance(item, dict) and str(item.get(REPLACES) or "").strip() == record_id
        for item in items
    )


def _not_ours(kind: str, record_id: str, where: Path, home: LibraryRoot) -> ApiError:
    """The refusal for a save that would edit a library read before the
    organization's: say which, and the one line that makes it a replacement."""
    owner = library_of(REPO_ROOT, where)
    return ApiError(
        "%s %s is %s's (%s), and this model keeps its own library in %s/. Add `%s: %s` "
        "to save it there as your version, or choose another id."
        % (kind, record_id, "`%s/`" % owner if owner else "the shipped library",
           _shown(REPO_ROOT, where), home.name, REPLACES, record_id),
        409,
    )


def _archetype_from_text(text: str, expect_id: Optional[str] = None):
    try:
        data = parse_data_text(text, "the archetype you are editing")
    except ModelFileError as exc:
        raise ApiError("that is not valid YAML: %s" % _yaml_complaint(exc.message), 422)
    if not isinstance(data, dict):
        raise ApiError(
            "an archetype is a mapping of fields, not a %s" % type(data).__name__, 422
        )
    try:
        archetype = parse_archetype(data)
    except ArchetypeError as exc:
        raise ApiError(str(exc), 422)
    if not SAFE_ID.match(str(archetype.archetype_id)):
        raise ApiError("an archetype id must be an identifier: letters, digits, . _ -", 422)
    if archetype.applies_to not in ENTITY_TYPES:
        raise ApiError("applies_to names an unknown entity type %r" % archetype.applies_to, 422)
    if expect_id and str(archetype.archetype_id) != expect_id:
        raise ApiError(
            "this file is %s; changing archetype_id to %r would leave two archetypes "
            "claiming one file. Save it as a new archetype instead."
            % (expect_id, archetype.archetype_id),
            409,
        )
    return archetype


def _sample_instance(archetype) -> dict:
    """A stand-in instance, so a preview can show what the shape produces.

    Required parameters with no default get their own name as the value. That
    is obviously a placeholder in the output, which is the point: the preview
    is about the shape, not about a particular product.
    """
    entity_type = ENTITY_TYPES[archetype.applies_to]
    parameters = {}
    for param in archetype.parameters:
        if param.default is not None:
            parameters[param.name] = param.default
        elif param.required:
            parameters[param.name] = "sample-" + param.name
    return {
        entity_type.pk: "SAMPLE-" + str(archetype.archetype_id).upper(),
        "name": "Sample %s" % archetype.title,
        "status": "Planned",
        "archetype": archetype.archetype_id,
        "parameters": parameters,
    }


def _archetype_instances(model, archetype_id: str) -> List[str]:
    """The records that ask for a shape, not the ones the shape made.

    Generated entities carry the archetype name as well, so filtering on that
    field alone answers "every box this produced" when the question was "who
    asked for it".
    """
    return sorted(
        str(record[ENTITY_TYPES[type_name].pk])
        for type_name in ENTITY_TYPES
        for record in model.all_of(type_name)
        if record.get("archetype") == archetype_id
        and not record.get("archetype_instance")
    )


def api_archetype(query, _body) -> dict:
    """The source of one archetype, or a starter for a new one.

    An archetype is what makes onboarding a product a small edit instead of a
    new diagram, so being unable to write one in the app left the most valuable
    thing in the repository as a text-editor-only feature.
    """
    archetype_id = (query.get("id") or [""])[0]
    if archetype_id:
        path = _existing_archetype_file(archetype_id)
        if path is None:
            raise ApiError("unknown archetype %r" % archetype_id, 404)
        text = path.read_text(encoding="utf-8-sig")
        where = _shown(REPO_ROOT, path)
    else:
        text = STARTER_ARCHETYPE % ("my-archetype", "My Archetype")
        where = _shown(REPO_ROOT, _archetype_path("my-archetype"))

    model, _views = _load_all()
    return {
        "id": archetype_id,
        "text": text,
        "path": where,
        "isNew": not archetype_id,
        "instances": _archetype_instances(model, archetype_id) if archetype_id else [],
        "help": _archetype_help(),
    }


def _archetype_help() -> dict:
    return {
        "types": sorted(ENTITY_TYPES),
        "relations": sorted(RELATION_TYPES),
        "filters": [
            {"name": "{x|upper}", "note": "UPPER CASE, for identifiers"},
            {"name": "{x|lower}", "note": "lower case"},
            {"name": "{x|slug}", "note": "lower case with hyphens"},
            {"name": "{x|title}", "note": "Title Case, for names"},
        ],
        "instanceKeys": [
            {"name": "overrides", "note": "change a field on one generated entity"},
            {"name": "exclude", "note": "drop a generated entity, and what depended on it"},
            {"name": "extra", "note": "add entities alongside what the shape provides"},
            {"name": "patterns", "note": "patterns this instance applies beyond the shape's"},
            {"name": "choose", "note": "slot name to the option this instance takes, or `none`"},
        ],
        "shapeKeys": [
            {"name": "entity_defaults", "note": "what every entity has in common, by type, plus `all`"},
            {"name": "blocks", "note": "building blocks the shape is built on; `bind` names what is shared, `landing-zone` for the zone's own"},
            {"name": "provider", "note": "the cloud every block resolves against"},
            {"name": "runs_on", "note": "on a system: `block` or `block.component` it runs on"},
            {"name": "uses", "note": "on a system: shared tech service ids it runs on, or kinds the landing zone answers"},
            {"name": "patterns", "note": "patterns every instance applies"},
            {"name": "slots", "note": "where the shape varies: a need, its options, and the default"},
            {"name": "bind", "note": "the landing zone by kind: component type to the shared service that is that kind here"},
        ],
    }


def api_archetype_preview(_query, body) -> dict:
    """What this shape would create, without writing anything."""
    archetype = _archetype_from_text(str(body.get("text") or ""))
    try:
        expansion = expand(
            _sample_instance(archetype), archetype, archetype.applies_to, _expansion_library()
        )
    except ArchetypeError as exc:
        raise ApiError(str(exc), 409)

    produced = []
    for type_name, records in sorted(expansion.entities.items()):
        pk = ENTITY_TYPES[type_name].pk
        for record in records:
            produced.append(
                {
                    "type": type_name,
                    "id": str(record.get(pk) or ""),
                    "name": str(record.get("name") or ""),
                }
            )
    return {
        "id": archetype.archetype_id,
        "title": archetype.title,
        "appliesTo": archetype.applies_to,
        "parameters": [
            {"name": p.name, "required": p.required, "default": p.default,
             "description": p.description}
            for p in archetype.parameters
        ],
        "produces": produced,
        "relations": {name: len(rows) for name, rows in sorted(expansion.relations.items())},
        "counts": {
            "entities": len(produced),
            "relations": sum(len(r) for r in expansion.relations.values()),
        },
    }


def api_archetype_save(_query, body) -> dict:
    text = str(body.get("text") or "")
    editing = str(body.get("id") or "").strip() or None

    with _LOCK:
        if editing is not None and _existing_archetype_file(editing) is None:
            raise ApiError("unknown archetype %r" % editing, 404)

        archetype = _archetype_from_text(text, expect_id=editing)
        archetype_id = str(archetype.archetype_id)
        existing = _existing_archetype_file(archetype_id)
        home = own_root(REPO_ROOT)
        # A shape read from a library before the organization's is never
        # written in place while the model keeps one of its own: the save
        # goes to the organization's library as a replacement, which it has
        # to say it is.
        theirs = (
            existing is not None and home.name
            and library_of(REPO_ROOT, existing) != home.name
        )
        if theirs:
            if not _says_replaces(text, archetype_id):
                raise _not_ours("shape", archetype_id, existing, home)
            path = _archetype_path(archetype_id)
        elif editing is None and existing is not None:
            raise ApiError(
                "an archetype called %r already exists in %s. Open it and edit it, "
                "or choose another id." % (archetype_id, _shown(REPO_ROOT, existing)),
                409,
            )
        else:
            path = existing if existing is not None else _archetype_path(archetype_id)
        previous = path.read_text(encoding="utf-8-sig") if path.exists() else None

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")

        # Editing a shape re-expands every instance of it. If that breaks, the
        # edit is undone: a saved archetype that will not load is worse than a
        # rejected save, because the model stops loading at all.
        try:
            model, views = _load_all()
        except (ModelError, ArchetypeError, ViewError, ModelFileError) as exc:
            if previous is None:
                path.unlink()
            else:
                path.write_text(previous, encoding="utf-8")
            raise ApiError("saving that would break the model: %s" % exc, 409)

        report = _report(model, views)
        instances = _archetype_instances(model, archetype_id)
        generated = sum(
            1
            for type_name in ENTITY_TYPES
            for record in model.all_of(type_name)
            if str(record.get("archetype_instance") or "") in set(instances)
        )

    return {
        "id": archetype_id,
        "title": archetype.title,
        "path": _shown(REPO_ROOT, path),
        "created": previous is None,
        "instances": instances,
        "generated": generated,
        "errors": [f.format() for f in report.errors],
        "warnings": len(report.warnings),
    }


def api_archetype_delete(_query, body) -> dict:
    archetype_id = str(body.get("id") or "").strip()
    with _LOCK:
        path = _existing_archetype_file(archetype_id)
        if path is None:
            raise ApiError("unknown archetype %r" % archetype_id, 404)
        model, _views = _load_all()
        used_by = _archetype_instances(model, archetype_id)
        if used_by:
            # Removing it would delete every entity it generates, silently.
            raise ApiError(
                "%s is instantiated by %s. Delete those first, or change them to "
                "another archetype." % (archetype_id, ", ".join(used_by)),
                409,
            )
        path.unlink()
        model, views = _load_all()
        report = _report(model, views)
    # Deleting the organization's version of a shape brings back the one it
    # replaced; the reply says so rather than leaving it to be noticed.
    restored = model.archetypes.get(archetype_id)
    return {
        "deleted": archetype_id,
        "path": _shown(REPO_ROOT, path),
        "restored": _shown(REPO_ROOT, restored.source_file) if restored is not None else "",
        "errors": [f.format() for f in report.errors],
        "warnings": len(report.warnings),
    }


def api_entity_source(query, _body) -> dict:
    """The YAML file behind one entity, for the times a form cannot say it."""
    entity_id = (query.get("id") or [""])[0]
    model, _views = _load_all()
    found = model.find(entity_id)
    if found is None:
        raise ApiError("unknown entity %r" % entity_id, 404)
    type_name, record = found

    source = record.get("_source_file")
    if not source:
        raise ApiError("%s was generated, so it has no file of its own" % entity_id, 409)
    path = Path(str(source))
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.exists():
        raise ApiError("%s is recorded in %s, which is not there" % (entity_id, source), 404)

    data = read_data_file(path)
    instance = record.get("archetype_instance")
    why = None
    if instance:
        # Editing the output of a shape is editing the wrong thing: the next
        # expansion overwrites it, and the change is lost without a trace.
        why = (
            "%s is generated by the archetype instance %s. Edit that instance, or "
            "the archetype, and this is regenerated." % (entity_id, instance)
        )
    elif not isinstance(data, dict):
        # A file holding several records is edited as a whole or not at all,
        # and rewriting it from one entity's editor is how the other records in
        # it get lost. The same reason delete refuses to touch shared files.
        why = (
            "This file holds several records, so editing it here would rewrite "
            "the others. Open it in an editor."
        )
    return {
        "id": entity_id,
        "type": type_name,
        "text": path.read_text(encoding="utf-8-sig"),
        "path": str(path.relative_to(REPO_ROOT)),
        "editable": why is None,
        "why": why,
    }


def api_entity_source_save(_query, body) -> dict:
    entity_id = str(body.get("id") or "").strip()
    text = str(body.get("text") or "")

    with _LOCK:
        current = api_entity_source({"id": [entity_id]}, None)
        if not current["editable"]:
            raise ApiError(current["why"] or "that file is not editable here", 409)

        try:
            data = parse_data_text(text, current["path"])
        except ModelFileError as exc:
            raise ApiError("that is not valid YAML: %s" % _yaml_complaint(exc.message), 422)
        if not isinstance(data, dict):
            raise ApiError("this file holds one record, so it is a mapping", 422)

        pk = ENTITY_TYPES[current["type"]].pk
        if str(data.get(pk) or "") != entity_id:
            raise ApiError(
                "this file is %s. Changing %s renames the entity, which would leave "
                "every reference to it dangling; use the model tools for that."
                % (entity_id, pk),
                409,
            )

        path = REPO_ROOT / current["path"]
        previous = path.read_text(encoding="utf-8-sig")
        path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
        try:
            model, views = _load_all()
        except (ModelError, ArchetypeError, ViewError, ModelFileError) as exc:
            path.write_text(previous, encoding="utf-8")
            raise ApiError("saving that would break the model: %s" % exc, 409)
        report = _report(model, views)

    return {
        "id": entity_id,
        "path": current["path"],
        "errors": [f.format() for f in report.errors],
        "warnings": len(report.warnings),
    }


#: Keys the loader adds that are not part of anyone's model.
INTERNAL_KEYS = ("_source", "_source_file")


def _cell(value) -> object:
    """A value a table can render and a CSV can hold."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    if isinstance(value, dict):
        return "; ".join("%s=%s" % (k, v) for k, v in sorted(value.items()))
    return str(value)


def _where(record: dict) -> str:
    source = record.get("_source_file") or record.get("_source") or ""
    if not source:
        return ""
    path = Path(str(source))
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(source)


def _entity_table(model, type_name: str) -> dict:
    entity_type = ENTITY_TYPES[type_name]
    records = sorted(
        model.all_of(type_name),
        key=lambda r: str(r.get("name") or r.get(entity_type.pk) or "").lower(),
    )

    # Columns in the order the schema declares them, then anything the records
    # carry that the schema does not know about -- which is worth seeing, since
    # a field nobody declared is either a typo or a convention forming.
    declared = [f.name for f in entity_type.fields]
    ordered = [entity_type.pk] + [n for n in declared if n != entity_type.pk]
    extra = sorted(
        {
            key
            for record in records
            for key in record
            if key not in ordered and key not in INTERNAL_KEYS
        }
    )

    columns = []
    for name in ordered + extra:
        field = next((f for f in entity_type.fields if f.name == name), None)
        filled = sum(1 for r in records if r.get(name) not in (None, "", [], {}))
        columns.append(
            {
                "name": name,
                "pk": name == entity_type.pk,
                "required": bool(field and field.required),
                "ref": field.ref if field else None,
                "enum": list(field.enum) if field and field.enum else None,
                "declared": field is not None,
                "filled": filled,
            }
        )
    columns.append(
        {"name": "_file", "pk": False, "required": False, "ref": None,
         "enum": None, "declared": False, "filled": len(records)}
    )

    rows = []
    for record in records:
        row = {name: _cell(record.get(name)) for name in ordered + extra}
        row["_file"] = _where(record)
        rows.append(row)

    return {
        "kind": "entity",
        "id": type_name,
        "label": entity_type.label,
        "plural": type_name.replace("_", " "),
        "pk": entity_type.pk,
        "columns": columns,
        "rows": rows,
        "count": len(rows),
    }


def _relation_table(model, name: str) -> dict:
    spec = RELATION_TYPES[name]
    rows_in = model.relation_rows(name)
    ordered = [spec.left_column, spec.right_column]
    if spec.qualifier:
        ordered.append(spec.qualifier)
    extra = sorted(
        {
            key
            for row in rows_in
            for key in row
            if key not in ordered and key not in INTERNAL_KEYS
        }
    )

    def label_of(entity_id) -> str:
        located = model.find(str(entity_id))
        return str(located[1].get("name") or entity_id) if located else str(entity_id)

    rows = []
    for row in rows_in:
        out = {name_: _cell(row.get(name_)) for name_ in ordered + extra}
        # The ids are the record; the names are what makes it readable.
        out["_left"] = label_of(row.get(spec.left_column))
        out["_right"] = label_of(row.get(spec.right_column))
        out["_file"] = _where(row)
        rows.append(out)
    rows.sort(key=lambda r: (str(r.get("_left") or "").lower(), str(r.get("_right") or "").lower()))

    columns = [
        {"name": spec.left_column, "pk": True, "required": True, "ref": spec.left,
         "enum": None, "declared": True, "filled": len(rows)},
        {"name": "_left", "pk": False, "required": False, "ref": None,
         "enum": None, "declared": False, "filled": len(rows)},
        {"name": spec.right_column, "pk": True, "required": True, "ref": spec.right,
         "enum": None, "declared": True, "filled": len(rows)},
        {"name": "_right", "pk": False, "required": False, "ref": None,
         "enum": None, "declared": False, "filled": len(rows)},
    ]
    if spec.qualifier:
        columns.append(
            {"name": spec.qualifier, "pk": False, "required": False, "ref": None,
             "enum": None, "declared": True,
             "filled": sum(1 for r in rows if r.get(spec.qualifier))}
        )
    for name_ in extra:
        columns.append(
            {"name": name_, "pk": False, "required": False, "ref": None,
             "enum": None, "declared": False,
             "filled": sum(1 for r in rows if r.get(name_) not in (None, "", [], {}))}
        )
    columns.append(
        {"name": "_file", "pk": False, "required": False, "ref": None,
         "enum": None, "declared": False, "filled": len(rows)}
    )

    return {
        "kind": "relation",
        "id": name,
        "label": name.replace("_", " "),
        "left": spec.left,
        "right": spec.right,
        "columns": columns,
        "rows": rows,
        "count": len(rows),
    }


def api_table(query, _body) -> dict:
    """The model as tables: every field of every record, nothing hidden.

    A diagram answers a question somebody already had. A table is where you go
    when you do not know what you are looking for yet, and it is the one thing
    a model in files cannot show you without a text editor open.
    """
    type_name = (query.get("type") or [""])[0]
    relation = (query.get("relation") or [""])[0]
    model, _views = _load_all()

    if type_name:
        if type_name not in ENTITY_TYPES:
            raise ApiError("unknown entity type %r" % type_name, 404)
        return _entity_table(model, type_name)
    if relation:
        if relation not in RELATION_TYPES:
            raise ApiError("unknown relation %r" % relation, 404)
        return _relation_table(model, relation)

    return {
        "kind": "catalog",
        "entities": [
            {"id": name, "label": ENTITY_TYPES[name].label,
             "plural": name.replace("_", " "),
             "count": len(model.all_of(name))}
            for name in sorted(ENTITY_TYPES)
        ],
        "relations": [
            {"id": name, "label": name.replace("_", " "),
             "left": RELATION_TYPES[name].left, "right": RELATION_TYPES[name].right,
             "count": len(model.relation_rows(name))}
            for name in sorted(RELATION_TYPES)
        ],
    }


def _field_coverage(model) -> List[dict]:
    out = []
    for type_name in sorted(ENTITY_TYPES):
        entity_type = ENTITY_TYPES[type_name]
        records = model.all_of(type_name)
        fields = []
        for field in entity_type.fields:
            if field.name == entity_type.pk:
                continue
            filled = sum(1 for r in records if r.get(field.name) not in (None, "", [], {}))
            fields.append(
                {
                    "name": field.name,
                    "required": field.required,
                    "filled": filled,
                    "share": round(filled / len(records), 3) if records else 0.0,
                }
            )
        out.append(
            {
                "type": type_name,
                "label": entity_type.label,
                "plural": type_name.replace("_", " "),
                "count": len(records),
                "fields": fields,
            }
        )
    return out


def _ends(model, relation: str, side: str) -> set:
    spec = RELATION_TYPES[relation]
    column = spec.left_column if side == "left" else spec.right_column
    return {str(row.get(column)) for row in model.relation_rows(relation) if row.get(column)}


def _gap(model, key: str, title: str, why: str, type_name: str, ids) -> dict:
    entity_type = ENTITY_TYPES[type_name]
    items = []
    for entity_id in sorted(ids):
        record = model.get(type_name, entity_id) or {}
        items.append({"id": entity_id, "name": record.get("name") or entity_id,
                      "type": type_name})
    return {
        "key": key,
        "title": title,
        "why": why,
        "type": type_name,
        "total": len(model.all_of(type_name)),
        "items": items,
        "count": len(items),
    }


#: What each drift category asks of a person, the same words the report uses.
DRIFT_ACTIONS = {
    "LINKED_OK": "Nothing. Linked and agreeing.",
    "ATTR_MISMATCH": "Decide per field. field_sot.yaml records who wins.",
    "UNLINKED_MATCH": "Record cmdb_ci_sys_id on the system to make the link durable.",
    "CANDIDATE_MATCH": "Human confirmation. Not applied automatically.",
    "AMBIGUOUS": "Disambiguate the model names, then re-run.",
    "MODEL_ONLY": "Either the CI is missing from ServiceNow, or the system is stale.",
    "CMDB_ONLY": "Either the model is incomplete, or the CI is junk. Usually the latter, for now.",
}


def api_cmdb_drift(query, _body) -> dict:
    """The model against a CMDB export, read-only: the same reconciliation
    `terrane cmdb drift` runs, for the Drift panel. `export` names a CSV inside
    the repository; left out, the sample export. Nothing is written to
    ServiceNow or to the model."""
    asked = (query.get("export") or [""])[0].strip()
    base = REPO_ROOT / "60_SOURCES" / "servicenow"
    path = (REPO_ROOT / asked).resolve() if asked else base / "sample_cmdb_ci_export.csv"
    if asked and REPO_ROOT.resolve() not in path.parents:
        raise ApiError("the CI export has to be a file inside the repository", 400)
    if not path.exists():
        raise ApiError("CI export not found: %s" % (asked or path.name), 404)
    model, _views = _load_all()
    rows = read_ci_export(path)
    field_sot = load_field_sot(base / "field_sot.yaml") if (base / "field_sot.yaml").exists() else {}
    shown = str(path.relative_to(REPO_ROOT.resolve())).replace("\\", "/")
    result = reconcile_cmdb(model, rows, field_sot=field_sot, export_path=shown)
    total = len(model.all_of("systems"))
    linked = result.counts.get("LINKED_OK", 0) + result.counts.get("ATTR_MISMATCH", 0)
    return {
        "export": shown,
        "ciRecords": len(rows),
        "coverage": {
            "systems": total,
            "linked": linked,
            "percent": round(100.0 * linked / total) if total else None,
        },
        "counts": dict(sorted(result.counts.items())),
        "actions": DRIFT_ACTIONS,
        "fieldSot": dict(result.field_sot),
        "rows": [row._asdict() for row in result.rows],
    }


def api_diff(query, _body) -> dict:
    """What changed in the architecture since a revision, in the model's own
    terms: `since` is any git revision (default the previous commit), `until`
    a later one or, left out, the working tree with its uncommitted edits."""
    from terrane import diff as diff_module

    since = (query.get("since") or ["HEAD~1"])[0].strip() or "HEAD~1"
    until = (query.get("until") or [""])[0].strip() or None
    try:
        result = diff_module.between(REPO_ROOT, since, until)
    except diff_module.DiffError as exc:
        raise ApiError(str(exc), 400)
    payload = diff_module.as_dict(result)
    payload["markdown"] = diff_module.format_markdown(result)
    return payload


def api_log(query, _body) -> dict:
    """The last few commits, for the home page: what changed, when, in the
    words of whoever changed it. Read from git where the app runs; the
    hosted copy bakes the log of the commit it was built from, so the page
    and the deck beside it describe the same revision. A checkout with no
    history says so rather than inventing one."""
    import subprocess

    try:
        count = max(1, min(50, int((query.get("n") or ["8"])[0])))
    except ValueError:
        count = 8
    try:
        run = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "log", "-n", str(count), "--date=short",
             "--format=%h%x1f%ad%x1f%s"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
    except OSError:
        return {"commits": [], "why": "git is not installed here"}
    if run.returncode != 0:
        return {"commits": [], "why": "not a git checkout"}
    commits = []
    for line in run.stdout.splitlines():
        parts = line.split("\x1f")
        if len(parts) == 3:
            commits.append({"sha": parts[0], "date": parts[1], "subject": parts[2]})
    return {"commits": commits}


def api_coverage(_query, _body) -> dict:
    """What the model does not say, which is the half people forget to look at.

    Validation answers "is anything wrong". This answers "what is missing",
    which is a different question: a model with no errors and no owners
    recorded is a model that will not survive its first incident.
    """
    model, views = _load_all()
    gaps: List[dict] = []

    realized = _ends(model, "system_realizes_capability", "right") | _ends(
        model, "product_realizes_capability", "right"
    )
    all_capabilities = {str(c["capability_id"]) for c in model.all_of("capabilities")}
    gaps.append(_gap(
        model, "capability.unrealized", "Capabilities nothing realizes",
        "The business says it does this and the estate does not show how. Either a "
        "system is missing from the model, or the capability is aspirational.",
        "capabilities", all_capabilities - realized,
    ))

    realizing = _ends(model, "system_realizes_capability", "left")
    all_systems = {str(s["system_id"]) for s in model.all_of("systems")}
    gaps.append(_gap(
        model, "system.no-capability", "Systems no capability claims",
        "Something is running that no business capability accounts for. Usually "
        "the capability map is incomplete; occasionally the system is.",
        "systems", all_systems - realizing,
    ))

    for type_name in sorted(ENTITY_TYPES):
        if not any(f.name == "owner_org_id" for f in ENTITY_TYPES[type_name].fields):
            continue
        pk = ENTITY_TYPES[type_name].pk
        unowned = {
            str(r[pk]) for r in model.all_of(type_name)
            if not r.get("owner_org_id")
            # An external actor has no internal owner by definition. Flagging
            # every cardholder and regulator is how a gap report gets ignored.
            and str(r.get("internal", "Yes")).strip().lower() != "no"
        }
        if unowned:
            gaps.append(_gap(
                model, "owner.missing." + type_name,
                "%ss with no owner" % ENTITY_TYPES[type_name].label.capitalize(),
                "The first question in an incident is who to call, and this is the "
                "field that answers it.",
                type_name, unowned,
            ))

    gaps.append(_gap(
        model, "data.no-sot", "Data with no system of record",
        "Without one, every copy is equally authoritative, which is the same as "
        "none of them being.",
        "data_assets",
        {str(d["data_asset_id"]) for d in model.all_of("data_assets")
         if not d.get("source_of_truth")},
    ))

    writers: Dict[str, set] = {}
    for row in model.relation_rows("system_reads_writes"):
        if str(row.get("operation") or "").lower() in ("write", "readwrite"):
            writers.setdefault(str(row.get("data_asset_id")), set()).add(
                str(row.get("system_id"))
            )
    gaps.append(_gap(
        model, "data.many-writers", "Data more than one system writes",
        "Not necessarily wrong, but it is where reconciliation problems come from, "
        "and it should be a decision rather than an accident.",
        "data_assets",
        {asset for asset, systems in writers.items() if len(systems) > 1},
    ))

    connected = set()
    for record in model.all_of("interfaces"):
        for key in ("source_system_id", "target_system_id"):
            if record.get(key):
                connected.add(str(record[key]))
    gaps.append(_gap(
        model, "system.no-interface", "Systems connected to nothing",
        "An estate has very few genuinely standalone systems. Usually this means "
        "the integrations exist and are not written down.",
        "systems", all_systems - connected,
    ))

    hosted = _ends(model, "system_uses_tech_service", "left")
    gaps.append(_gap(
        model, "system.no-platform", "Systems with nothing recorded about where they run",
        "Nothing to answer a platform change impact question with, so any answer "
        "given about them is a guess.",
        "systems", all_systems - hosted,
    ))

    gaps.append(_gap(
        model, "system.no-cmdb", "Systems not linked to the CMDB",
        "Reconciliation can only cover what is linked; the rest is invisible to "
        "the drift report either way.",
        "systems",
        {str(s["system_id"]) for s in model.all_of("systems")
         if not s.get("cmdb_ci_sys_id")},
    ))

    carrying = _ends(model, "interface_transports_data_asset", "left")
    gaps.append(_gap(
        model, "interface.no-payload", "Interfaces with no payload recorded",
        "The line is on the diagram but what crosses it is unknown, which is the "
        "question a privacy or data-lineage review actually asks.",
        "interfaces",
        {str(i["interface_id"]) for i in model.all_of("interfaces")} - carrying,
    ))

    gaps.append(_gap(
        model, "actor.no-system", "Actors that touch nothing",
        "An actor with no entry point cannot appear on a context diagram, which "
        "is the only thing actors are for.",
        "actors",
        {str(a["actor_id"]) for a in model.all_of("actors")}
        - _ends(model, "actor_uses_system", "left"),
    ))

    gaps.append(_gap(
        model, "flow.no-steps", "Flows with no steps",
        "A flow with no steps renders an empty sequence diagram, which is worse "
        "than not having the flow.",
        "flows",
        {str(f["flow_id"]) for f in model.all_of("flows")}
        - _ends(model, "flow_step", "left"),
    ))

    # Anything on no diagram is in the model and invisible, which is how a
    # model and the picture people work from drift apart.
    #
    # Interfaces are the exception worth handling rather than reporting: they
    # are drawn as the edges between systems, never as nodes, so counting
    # nodes alone said all of them were missing from every diagram.
    drawn = set()
    for view in views:
        try:
            graph = resolve(model, bind(
                view,
                dict(render_targets(model, view)) if view.parameters else None,
                model,
            ))
        except ViewError:
            continue
        keys = set()
        for node in graph.nodes:
            drawn.add(node.key)
            keys.add(node.key)
        if any(spec.get("via") == "interfaces" for spec in (view.edges or [{"via": "interfaces"}])):
            for record in model.all_of("interfaces"):
                if (str(record.get("source_system_id")) in keys
                        and str(record.get("target_system_id")) in keys):
                    drawn.add(str(record["interface_id"]))

    for type_name in sorted(ENTITY_TYPES):
        # A flow is not on a view at all: it renders its own sequence diagram,
        # and `flow.no-steps` above is the gap that actually applies to it.
        if type_name == "flows":
            continue
        pk = ENTITY_TYPES[type_name].pk
        missing = {str(r[pk]) for r in model.all_of(type_name)} - drawn
        if missing:
            gaps.append(_gap(
                model, "undrawn." + type_name,
                "%ss on no diagram" % ENTITY_TYPES[type_name].label.capitalize(),
                "In the model and on none of the views, so nobody looking at a "
                "diagram will ever see it. Either a view is missing, or it is.",
                type_name, missing,
            ))

    gaps.extend(_governance_gaps(model))
    gaps.extend(_library_gaps(model))

    gaps = [g for g in gaps if g["count"]]
    gaps.sort(key=lambda g: (-g["count"], g["key"]))

    return {
        "gaps": gaps,
        "fields": _field_coverage(model),
        "totals": {
            "entities": sum(len(model.all_of(n)) for n in ENTITY_TYPES),
            "relations": sum(len(model.relation_rows(n)) for n in RELATION_TYPES),
            "views": len(views),
            "drawn": len(drawn),
            "gaps": sum(g["count"] for g in gaps),
        },
    }


def _governance_gaps(model) -> List[dict]:
    """Where the control register and the estate do not meet.

    The register says what must be enforced; the estate says where. Each gap
    is one way the two fail to line up, and every one of them is a question
    an audit will ask sooner or later. Nothing is reported for a model with no
    register: a gap that fires on every system in every model is noise.
    """
    gaps: List[dict] = []
    if not model.all_of("controls"):
        return gaps

    live = ("Active", "Planned")
    governed_systems = _ends(model, "system_governed_by_control", "left")
    enforced = _ends(model, "system_governed_by_control", "right") | _ends(
        model, "data_governed_by_control", "right"
    )
    gaps.append(_gap(
        model, "control.unenforced", "Controls nothing in the estate enforces",
        "The register says this must happen and the estate does not say where. "
        "Either the enforcement point is not modeled, or the control is a "
        "document rather than a mechanism.",
        "controls",
        {str(c["control_id"]) for c in model.all_of("controls")} - enforced,
    ))

    gaps.append(_gap(
        model, "system.restricted-no-control", "Restricted systems recording no control",
        "A system handling Restricted data with no control recorded is either "
        "uncontrolled or undocumented, and an assessor will assume the first.",
        "systems",
        {
            str(s["system_id"]) for s in model.all_of("systems")
            if str(s.get("data_classification_supported")) == "Restricted"
            and str(s.get("status")) in live
        } - governed_systems,
    ))

    # The inference gap, and the reason the capability join is imported at
    # all. The business says the capability is governed by a control; the
    # estate says this system realizes the capability and records no control
    # for it. One of those two statements is incomplete.
    expected: Dict[str, set] = {}
    for row in model.relation_rows("capability_governed_by_control"):
        expected.setdefault(str(row["capability_id"]), set()).add(str(row["control_id"]))
    recorded: Dict[str, set] = {}
    for row in model.relation_rows("system_governed_by_control"):
        recorded.setdefault(str(row["system_id"]), set()).add(str(row["control_id"]))
    unrecorded = set()
    for row in model.relation_rows("system_realizes_capability"):
        system_id = str(row["system_id"])
        wanted = expected.get(str(row["capability_id"]), set())
        record = model.get("systems", system_id) or {}
        if wanted and str(record.get("status")) in live and not (
            wanted & recorded.get(system_id, set())
        ):
            unrecorded.add(system_id)
    gaps.append(_gap(
        model, "system.inherited-control-unrecorded",
        "Systems realizing a governed capability and recording none of its controls",
        "The business layer says the capability is governed by a control, and "
        "the estate says this system realizes the capability without recording "
        "any control for it. Either the system enforces it and nobody wrote that "
        "down, or the control is enforced somewhere this system is not.",
        "systems", unrecorded,
    ))

    gaps.append(_gap(
        model, "data.pii-no-policy", "Personal data subject to no policy",
        "Every privacy regime starts from which policy governs the data. A "
        "personal data asset with none recorded cannot answer that.",
        "data_assets",
        {
            str(d["data_asset_id"]) for d in model.all_of("data_assets")
            if str(d.get("pii_flag")) == "Yes"
        } - _ends(model, "data_subject_to_policy", "left"),
    ))

    if model.all_of("policies"):
        with_controls = {
            str(c.get("policy_id")) for c in model.all_of("controls") if c.get("policy_id")
        }
        gaps.append(_gap(
            model, "policy.no-control", "Policies with no control under them",
            "A policy nothing enforces is a statement of intent. That may be all "
            "it is meant to be, but it should be a decision rather than a gap.",
            "policies",
            {str(p["policy_id"]) for p in model.all_of("policies")} - with_controls,
        ))
    return gaps


def _library_gaps(model) -> List[dict]:
    """Where the estate and the pattern catalog do not meet.

    Two questions a review board asks of a catalog: who is on a pattern we
    have retired, and who is on no pattern at all. The second is not a fault
    -- a product can be built without one -- but a product that names none is
    a design nobody has compared against the catalog.
    """
    gaps: List[dict] = []
    try:
        _components, _blocks, patterns = _library()
    except LibraryError:
        return gaps
    if not patterns:
        return gaps
    retired = {p.pattern_id for p in patterns.values() if p.status in ("Deprecated", "Retired")}
    on_retired = set()
    on_none = set()
    for record in model.all_of("products"):
        applied = set(model.list_of(record, "patterns"))
        if applied & retired:
            on_retired.add(str(record["product_id"]))
        if not applied and str(record.get("status")) in ("Active", "Planned"):
            on_none.add(str(record["product_id"]))
    gaps.append(_gap(
        model, "product.deprecated-pattern", "Products applying a deprecated pattern",
        "The board has retired the pattern and the product is still on it. Each one "
        "is a migration nobody has scheduled.",
        "products", on_retired,
    ))
    gaps.append(_gap(
        model, "product.no-pattern", "Products applying no pattern",
        "Not necessarily wrong: nothing has to be built from a pattern. But a product "
        "that names none is a design nobody has held up against the catalog.",
        "products", on_none,
    ))
    return gaps


#: Blocks written from the app land here, for the same reason app-written
#: relations do: a form never rewrites a file somebody authored by hand.
BLOCK_ADDITIONS = "from_blocks.yaml"


def _library():
    components = load_components(REPO_ROOT)
    blocks = load_blocks(REPO_ROOT, components)
    return components, blocks, load_patterns(REPO_ROOT, blocks)


def _expansion_library():
    """What `expand` needs: component types, blocks and modules, the landing
    zone a part's kinds resolve against, and what the estate answers for the
    parameters that ask it -- without which every preview of a vendor
    product failed on who owns the private egress."""
    components = load_components(REPO_ROOT)
    model, _views = _load_all()
    return (
        components,
        load_blocks(REPO_ROOT, components),
        load_modules(REPO_ROOT),
        landing_zone_index(model.all_of("tech_services")),
        estate_answers(model.config),
    )


def _unanswered(kind: str, provider: str, service):
    """Why a kind has no bound service, for the form to say instead of
    "binds none": nothing of that kind is tagged on this landing zone."""
    if not kind or service:
        return None
    return "no %s service of kind `%s` is tagged landing-zone" % (provider or "shared", kind)


def _module_summaries(archetype, modules) -> List[dict]:
    """The parts of a shape, as the New form and the overview show them.

    A kit appears as a header carrying its own parameters, followed by its
    members as parts in their own right: each still droppable on its own
    terms, each still asking what the kit did not bind for it. The header is
    not a switch -- a kit is dropped by dropping its members, and a kit with
    a member that cannot be dropped cannot be dropped either -- so the form
    shows a group where the shape shows one name.

    Parameters the shape already binds with `with` are not asked again; the
    ones left are what the instance has to say.
    """
    out: List[dict] = []
    try:
        zone = effective_bind(archetype)
    except _ArchetypeError:
        zone = dict(archetype.bind)
    landing = _landing_zone()
    answers = _estate_answers()

    def resolved(kind: str):
        return zone.get(kind) or resolve_kind(kind, archetype.provider, landing)[0]

    def walk(entry: dict, in_kit: str) -> None:
        module_id = str(entry.get("module"))
        alias = str(entry.get("as") or module_id)
        bound = set((entry.get("with") or {}).keys())
        module = modules.get(module_id)
        if module is None:
            out.append({"alias": alias, "id": module_id, "name": module_id, "missing": True})
            return
        summary = {
            "alias": alias,
            "id": module_id,
            "name": module.name,
            "category": module.category,
            "description": module.description,
            "optional": module.optional,
            "requires": list(module.requires),
            "provides": provided_count(module, modules),
            "kit": module.is_kit,
            "in_kit": in_kit,
            "members": members_of(module, modules) if module.is_kit else [],
            "parameters": [
                {
                    "name": p.name,
                    **_asked(p, answers),
                    # A kind, and what the shape binds it to: the form shows
                    # the bound service as the value the product gets unless
                    # it says otherwise.
                    "component": p.component,
                    "bound": resolved(p.component) if p.component else None,
                    "gap": _unanswered(p.component, archetype.provider, resolved(p.component))
                    if p.component else None,
                }
                for p in module.parameters if p.name not in bound
            ],
        }
        out.append(summary)
        if module.is_kit:
            for member in module.modules:
                walk(member, alias)

    for entry in archetype.modules:
        walk(entry, "")
    return out


def _estate_answers() -> Dict[str, Any]:
    """What the estate answers under `answers` in model.yaml, off the model
    on disk; nothing when it says nothing or does not load."""
    try:
        model, _views = _load_all()
        return estate_answers(model.config)
    except Exception:  # noqa: BLE001 -- a summary must not fail for this
        return {}


def _asked(p, answers: Dict[str, Any]) -> dict:
    """`required`, `default` and `description` for a form, with the estate's
    answer where the parameter takes one. Without this every vendor product's
    form asked, starred, who owns the private egress, which the estate says
    once for all of them."""
    if not getattr(p, "estate", False):
        return {"required": p.required, "default": p.default, "description": p.description}
    said = answers.get(p.name)
    note = ("The estate answers this with %s, in model.yaml." % (
        ", ".join(str(x) for x in said) if isinstance(said, list) else said)
        if p.name in answers else "The estate answers this, under `answers` in model.yaml.")
    return {
        "required": p.required and p.name not in answers,
        "default": said if p.name in answers else p.default,
        "description": ("%s. %s" % (p.description.strip().rstrip("."), note)) if p.description else note,
    }


def _landing_zone():
    """The landing zone by provider and kind, off the model on disk."""
    try:
        model, _views = _load_all()
    except Exception:  # noqa: BLE001 -- a summary must not fail for this
        return {}
    return landing_zone_index(model.all_of("tech_services"))


def _slot_summaries(archetype, modules) -> List[dict]:
    """Where a shape varies, as the New form shows it: one radio group per
    slot, the default checked, `none` offered where the slot allows it."""
    out = []
    try:
        zone = effective_bind(archetype)
    except _ArchetypeError:
        zone = dict(archetype.bind)
    landing = _landing_zone()
    answers = _estate_answers()

    def resolved(kind: str):
        return zone.get(kind) or resolve_kind(kind, archetype.provider, landing)[0]

    for slot in archetype.slots:
        options = []
        for option in slot.options:
            module = modules.get(option)
            answered = dict(slot.answers.get(option) or {})
            options.append({
                "id": option,
                "name": module.name if module else option,
                "description": module.description if module else "",
                "provides": provided_count(module, modules) if module else 0,
                # The shape binds nothing on an option by kind; what it can
                # answer from its own parameters it says under the slot's
                # `with`, and the rest is the product's to say -- once the
                # option is chosen.
                "answered": answered,
                "parameters": [
                    {"name": p.name, **_asked(p, answers), "component": p.component,
                     "answered": answered.get(p.name),
                     "bound": resolved(p.component) if p.component else None,
                     "gap": _unanswered(p.component, archetype.provider, resolved(p.component))
                     if p.component else None}
                    for p in (module.parameters if module else [])
                ],
            })
        out.append({
            "name": slot.name,
            "description": slot.description,
            "default": slot.default,
            "optional": slot.optional,
            "options": options,
        })
    return out


def api_library(_query, _body) -> dict:
    """The component types, the blocks made of them, and the patterns above.

    Three levels rather than one because they answer different questions. A
    component type is what a box on a diagram *is*; a block is what you reach
    for when designing, because nobody assembles a workload by picking forty
    individual services; a pattern is the block plus the decision, which is
    what a review board actually governs.
    """
    components, blocks, patterns = _library()
    by_category: Dict[str, List[dict]] = {}
    for component in components.values():
        by_category.setdefault(component.category, []).append({
            "id": component.component_type_id,
            "name": component.name,
            "appliesTo": component.applies_to,
            "description": component.description,
            "shape": component.shape,
            "providers": component.providers,
            "defaults": component.defaults,
            "library": component.library,
            "replaced": component.replaced,
        })
    for entries in by_category.values():
        entries.sort(key=lambda c: c["name"].lower())

    model, _views = _load_all()
    # Who owns each pattern and what it meets are the estate's, in its
    # model.yaml, not the shipped pattern's (terrane/answers.py).
    patterns = adopted_patterns(patterns, model.config)
    in_use: Dict[str, int] = {}
    for type_name in ENTITY_TYPES:
        for record in model.all_of(type_name):
            key = str(record.get("component_type") or "")
            if key:
                in_use[key] = in_use.get(key, 0) + 1

    in_patterns: Dict[str, List[str]] = {}
    for pattern in patterns.values():
        for block_id in pattern.blocks:
            in_patterns.setdefault(block_id, []).append(pattern.name)
    products = model.all_of("products")
    interfaces = model.all_of("interfaces")
    status_order = {status: index for index, status in enumerate(PATTERN_STATUS)}

    def by_name(records, pk):
        return sorted(records, key=lambda r: str(r.get("name") or r[pk]).lower())

    def control_ref(control_id: str) -> dict:
        record = model.get("controls", control_id)
        return {"id": control_id, "name": (record or {}).get("name") or control_id}

    return {
        "components": [
            {"category": name, "types": by_category[name]}
            for name in sorted(by_category)
        ],
        "blocks": [
            {
                "id": block.building_block_id,
                "name": block.name,
                "category": block.category,
                "description": block.description,
                "provides": [
                    {
                        "component": p.component,
                        "name": components[p.component].name,
                        "shape": components[p.component].shape,
                        "category": components[p.component].category,
                    }
                    for p in block.provides
                ],
                "relations": [{"from": a, "to": b} for a, b in block.relations],
                "defaults": block.defaults,
                "inPatterns": sorted(in_patterns.get(block.building_block_id, [])),
                "library": block.library,
                "replaced": block.replaced,
            }
            for block in sorted(blocks.values(), key=lambda b: (b.category, b.name))
        ],
        # The decision, and who has taken it: adoption is read off the
        # `patterns` field of every product, not off a register.
        "patterns": [
            {
                "id": pattern.pattern_id,
                "name": pattern.name,
                "status": pattern.status,
                "category": pattern.category,
                "blocks": list(pattern.blocks),
                "intent": pattern.intent,
                "consequences": pattern.consequences,
                "whenNotToUse": pattern.when_not_to_use,
                "satisfies": [control_ref(c) for c in pattern.satisfies],
                "owner": pattern.owner_org_id,
                "decisionRef": pattern.decision_ref,
                "methodRef": pattern.method_ref,
                "library": pattern.library,
                "replaced": pattern.replaced,
                # Products first, then the interfaces on the pattern: three
                # of the method's patterns are about how two systems talk,
                # and the interface is the record that knows.
                "appliedBy": [
                    {"id": r["product_id"], "name": r.get("name") or r["product_id"],
                     "kind": "product"}
                    for r in by_name(products, "product_id")
                    if pattern.pattern_id in model.list_of(r, "patterns")
                ] + [
                    {"id": r["interface_id"], "name": r.get("name") or r["interface_id"],
                     "kind": "interface"}
                    for r in by_name(interfaces, "interface_id")
                    if pattern.pattern_id in model.list_of(r, "patterns")
                ],
            }
            for pattern in sorted(
                patterns.values(),
                key=lambda p: (status_order.get(p.status, 9), p.name.lower()),
            )
        ],
        "providers": sorted(
            {name for c in components.values() for name in c.providers}
        ),
        "inUse": in_use,
        # The parts, and which shapes are composed from each.
        "modules": _library_modules(model),
        "landingZones": _library_landing_zones(model),
        "adoption": _library_adoption(model),
        "connections": _library_connections(model),
        "libraries": _library_sources(model, components, blocks, patterns),
    }


def _library_sources(model, components, blocks, patterns) -> List[dict]:
    """The organization's libraries, each with what it adds and replaces by
    layer, for the line the Library opens with. Empty while the model names
    none, and then the page says nothing about it."""
    try:
        modules = load_modules(REPO_ROOT)
    except ModuleError:
        modules = {}
    try:
        types = load_build_types(REPO_ROOT)
    except BuildTypeError:
        types = {}
    layers = {
        "shape": model.archetypes, "connection kind": _connection_kinds(),
        "component type": components, "building block": blocks, "pattern": patterns,
        "part": modules, "build type": types,
    }
    return [
        {"name": name,
         "adds": {layer: added for layer, (added, _r) in counts.items() if added},
         "replaces": {layer: replaced for layer, (_a, replaced) in counts.items() if replaced}}
        for name, counts in library_summary(REPO_ROOT, layers)
    ]


def _connection_kinds() -> dict:
    try:
        return load_connections(REPO_ROOT)
    except LibraryError:
        # `terrane validate` says what is wrong with the file; the chooser and the
        # Library carry on without kinds rather than failing to open.
        return {}


def _kind_payload(kind) -> dict:
    return {
        "id": kind.connection_id, "name": kind.name, "description": kind.description,
        "style": kind.integration_style, "protocols": list(kind.protocols),
        "authMethods": list(kind.auth_methods), "frequency": kind.frequency,
        "direction": kind.direction, "patterns": list(kind.patterns), "defaults": kind.defaults(),
        "library": kind.library, "replaced": kind.replaced,
    }


def _library_connections(model) -> dict:
    """The connection kinds for the Library panel, each with the interfaces
    its fields make it, and the ones of no kind: `library/connections.md`."""
    kinds = _connection_kinds()
    by_kind, none = sorted_by_kind(model.all_of("interfaces"), kinds)

    def ref(record) -> dict:
        return {"id": record["interface_id"], "name": record.get("name") or record["interface_id"],
                "protocol": record.get("protocol"), "style": record.get("integration_style")}

    return {
        "kinds": [dict(_kind_payload(k), interfaces=[ref(r) for r in by_kind[k.connection_id]])
                  for k in kinds.values()],
        "none": [ref(r) for r in none],
    }


def _library_adoption(model) -> dict:
    """Shapes and the estate, for the Library panel: who is on a shape and
    how far they have moved, and which hand-authored products a shape's
    parts would reproduce. The same picture as `library/adoption.md`."""
    try:
        modules = load_modules(REPO_ROOT)
    except ModuleError:
        return {"onShapes": [], "candidates": []}
    shapes = list(model.archetypes.values())
    return {
        "onShapes": [
            {
                "product": d.product_id, "name": d.name, "shape": d.archetype_id, "moves": d.moves,
                "answers": list(d.answered_defaults), "overrides": list(d.overrides),
                "extras": dict(d.extras), "added": list(d.added), "dropped": list(d.dropped),
                "renamed": list(d.renamed),
                "choices": [
                    {"slot": slot, "pick": pick, "default": default}
                    for slot, (pick, default) in d.choices.items()
                ],
            }
            for d in shape_drifts(model, shapes, modules)
        ],
        "candidates": [
            {
                "product": c.product_id, "name": c.name, "shape": c.archetype_id,
                "covered": [alias for alias, _cat in c.covered],
                "missing": [alias for alias, _cat in c.missing_optional],
                "spare": list(c.spare),
            }
            for c in shape_candidates(model, shapes, modules)
        ],
    }


def _library_modules(model) -> List[dict]:
    try:
        modules = load_modules(REPO_ROOT)
    except ModuleError as exc:
        return [{"id": "broken", "name": "The module library did not load", "error": str(exc)}]
    # Where each part is used: by shapes directly, through a slot, or inside
    # a kit. The library could not answer this before, which is how eight
    # parts came to be composed by nothing without anybody noticing.
    in_shapes = uses_of(modules, model.archetypes.values())
    try:
        uses_by_build_types(in_shapes, load_build_types(REPO_ROOT), modules)
    except BuildTypeError:
        pass
    return [
        {
            "id": m.module_id,
            "name": m.name,
            "category": m.category,
            "description": m.description,
            "optional": m.optional,
            "requires": list(m.requires),
            "patterns": list(m.patterns),
            "provides": {t: len(v) for t, v in m.provides.items()},
            "relations": sum(len(v) for v in m.relations.values()),
            "kit": m.is_kit,
            "members": members_of(m, modules) if m.is_kit else [],
            "needs": list(m.needs),
            "parameters": [
                {"name": p.name, "required": p.required, "default": p.default,
                 "description": p.description}
                for p in m.parameters
            ],
            "inShapes": sorted(set(in_shapes.get(m.module_id, []))),
            "library": m.library,
            "replaced": m.replaced,
        }
        for m in sorted(modules.values(), key=lambda m: (m.category, m.name.lower()))
    ]


def _library_landing_zones(model) -> List[dict]:
    """Each provider a shape lands on: what it answers for, by kind, and the
    kinds the parts name that it cannot. The same picture as
    `library/landing-zones.md`, read off the model for the Library panel."""
    try:
        modules = load_modules(REPO_ROOT)
    except ModuleError:
        return []
    shapes = list(model.archetypes.values())
    services = list(model.all_of("tech_services"))
    zone = landing_zone_index(services)
    names = {str(s["tech_service_id"]): str(s.get("name") or s["tech_service_id"]) for s in services}
    primary = {str(s["tech_service_id"]): str(s.get("component_type") or "") for s in services}
    asked: Dict[str, List[str]] = {}
    for module in sorted(modules.values(), key=lambda m: m.module_id):
        for p in module.parameters:
            if p.component and p.default is None:
                asked.setdefault(p.component, []).append("%s (%s)" % (module.module_id, p.name))
    gaps = {(g.provider, g.kind): g for g in landing_zone_gaps(modules, shapes, zone)}
    out = []
    for provider in landing_providers(shapes):
        own = {k for (p, k) in zone if p == provider}
        kinds = []
        for kind in sorted(own | set(asked)):
            _found, candidates = resolve_kind(kind, provider, zone)
            gap = gaps.get((provider, kind))
            kinds.append({
                "kind": kind,
                "services": [
                    {"id": i, "name": names.get(i, i),
                     # A service answering for a kind that is not its own says
                     # which it is: Key Vault, a secrets manager, for `kms`.
                     "alsoKind": primary.get(i) if primary.get(i) and primary.get(i) != kind else None}
                    for i in candidates
                ],
                "shared": bool(candidates) and kind not in own,
                "ambiguous": len(candidates) > 1,
                "askedBy": asked.get(kind, []),
                "gap": gap is not None,
                "boundBy": list(gap.bound_by) if gap is not None else [],
            })
        out.append({
            "provider": provider,
            "shapes": [a.archetype_id for a in shapes if str(a.provider) == provider],
            "kinds": kinds,
            "gaps": sum(1 for k in kinds if k["gap"]),
        })
    return out


def api_block_preview(_query, body) -> dict:
    """What a block would create, without writing anything."""
    components, blocks, _patterns = _library()
    block_id = str(body.get("block") or "")
    if block_id not in blocks:
        raise ApiError("unknown building block %r" % block_id, 404)
    name = str(body.get("name") or "").strip()
    if not name:
        raise ApiError("a block needs a name for the thing being built")
    provider = str(body.get("provider") or "").strip() or None

    out = block_expand(blocks[block_id], name, components, provider=provider)
    model, _views = _load_all()
    produced = []
    for type_name, records in sorted(out["entities"].items()):
        pk = ENTITY_TYPES[type_name].pk
        for record in records:
            produced.append({
                "type": type_name,
                "id": record[pk],
                "name": record.get("name"),
                "product": record.get("product") or "",
                "component": record.get("component_type"),
                # An id already in the model is the one thing that stops a
                # block being added, so it is reported before anything is written.
                "clash": model.find(str(record[pk])) is not None,
            })
    return {
        "block": block_id,
        "name": name,
        "provider": provider or "",
        "produces": produced,
        "relations": sum(len(rows) for rows in out["relations"].values()),
        "clashes": [p["id"] for p in produced if p["clash"]],
    }


def api_block_add(_query, body) -> dict:
    """Write a block's entities and relations into the model."""
    preview = api_block_preview(None, body)
    if preview["clashes"]:
        raise ApiError(
            "already in the model: %s. Choose another name, or remove them first."
            % ", ".join(preview["clashes"]),
            409,
        )

    components, blocks, _patterns = _library()
    block = blocks[str(body["block"])]
    name = str(body["name"]).strip()
    provider = str(body.get("provider") or "").strip() or None
    out = block_expand(block, name, components, provider=provider)

    with _LOCK:
        written = []
        for type_name, records in sorted(out["entities"].items()):
            pk = ENTITY_TYPES[type_name].pk
            for record in records:
                values = {k: v for k, v in record.items() if k != pk}
                written.append(str(_write_entity(type_name, str(record[pk]), values)))

        if out["relations"]:
            data = _load_app_relations(BLOCK_ADDITIONS)
            for relation, rows in out["relations"].items():
                data.setdefault(relation, []).extend(rows)
            _write_app_relations(data, BLOCK_ADDITIONS)

        try:
            model, views = _load_all()
        except (ModelError, ArchetypeError, ViewError, ModelFileError) as exc:
            raise ApiError("adding that broke the model: %s" % exc, 409)
        report = _report(model, views)

    return {
        "block": block.building_block_id,
        "name": name,
        "created": [p["id"] for p in preview["produces"]],
        "files": len(written),
        "relations": preview["relations"],
        "errors": [f.format() for f in report.errors],
        "warnings": len(report.warnings),
    }


def api_list(query, _body) -> dict:
    """List entities of one type, or of every type when none is given.

    The app searches across everything, so the no-type form backs one client
    side index rather than a request per entity type.
    """
    type_name = (query.get("type") or [""])[0]
    if type_name and type_name not in ENTITY_TYPES:
        raise ApiError("unknown entity type %r" % type_name, 404)
    wanted = [type_name] if type_name else list(ENTITY_TYPES)

    model, _views = _load_all()
    items = []
    for name in wanted:
        entity_type = ENTITY_TYPES[name]
        for record in model.all_of(name):
            items.append(
                {
                    "id": record[entity_type.pk],
                    "type": name,
                    "label": entity_type.label,
                    "name": record.get("name"),
                    "status": record.get("status"),
                    "criticality": record.get("criticality"),
                    "domain": record.get("company_domain"),
                    "generated": bool(record.get("archetype_instance")),
                }
            )
    items.sort(key=lambda i: (i["type"], str(i.get("name") or i["id"]).lower()))
    return {"type": type_name or "all", "items": items}


def _append_extra(path: Path, type_name: str, record: dict) -> str:
    """Add one record under `extra.<type>` in an instance file, by text.

    The file is a person's: it has comments, and an order. So this does not
    parse and rewrite it; it finds the `extra:` block, the type under it,
    and puts the new item at the top of that list, creating what is missing.
    Two-space indentation is what every instance file in the repository
    uses and what `terrane new` writes.
    """
    text = path.read_text(encoding="utf-8-sig")
    lines = text.rstrip("\n").split("\n")
    item = []
    first = True
    for key, value in record.items():
        if value in (None, "", []):
            continue
        prefix = "    - " if first else "      "
        if isinstance(value, list):
            item.append("%s%s: [%s]" % (prefix, key, ", ".join(_yaml_value(v) for v in value)))
        else:
            item.append("%s%s: %s" % (prefix, key, _yaml_value(value)))
        first = False

    def find(prefix: str, start: int) -> int:
        for i in range(start, len(lines)):
            if lines[i].startswith(prefix):
                return i
            # Left the block: a line at a shallower indent that is not blank
            # or a comment.
            if start and lines[i].strip() and not lines[i].startswith(" ") and not lines[i].startswith("#"):
                return -1
        return -1

    at = find("extra:", 0)
    if at == -1:
        lines += ["", "# Added in the app, as part of this product.", "extra:", "  %s:" % type_name] + item
    else:
        under = find("  %s:" % type_name, at + 1)
        if under == -1:
            lines[at + 1:at + 1] = ["  %s:" % type_name] + item
        else:
            lines[under + 1:under + 1] = item
    new_text = "\n".join(lines) + "\n"
    path.write_text(new_text, encoding="utf-8")
    return text


def api_save(_query, body) -> dict:
    type_name = body.get("type")
    entity_id = str(body.get("id") or "").strip()
    values = body.get("values") or {}
    # An archetype instance to add the entity to, under its `extra`, instead
    # of writing a file of its own.
    instance_id = str(body.get("instance") or "").strip() or None
    # Only the fields given, the rest kept as they are. The form sends a whole
    # record, where a field left out is a field cleared; a gesture that sets
    # one owner sends one field.
    patch = bool(body.get("patch"))
    if type_name not in ENTITY_TYPES:
        raise ApiError("unknown entity type %r" % type_name)
    if not SAFE_ID.match(entity_id):
        raise ApiError("%r is not a usable identifier" % entity_id)

    with _LOCK:
        model, _views = _load_all()
        existing = model.find(entity_id)
        if existing and existing[0] != type_name:
            raise ApiError(
                "%s is already used by a %s; ids are unique across types"
                % (entity_id, existing[0])
            )
        if existing and existing[1].get("archetype_instance"):
            raise ApiError(
                "%s was generated by archetype instance %s. Edit the instance, or "
                "use an override on it, rather than the generated entity."
                % (entity_id, existing[1]["archetype_instance"]),
                409,
            )
        if instance_id:
            if existing:
                raise ApiError("%s already exists; only a new entity can be added to an instance" % entity_id, 409)
            found = model.find(instance_id)
            if found is None or not found[1].get("archetype"):
                raise ApiError("%s is not an archetype instance" % instance_id, 404)
            source = found[1].get("_source_file")
            if not source:
                raise ApiError("%s has no file to add to" % instance_id, 409)
            path = Path(source)
            entity_type = ENTITY_TYPES[type_name]
            known = {f.name for f in entity_type.fields} | {entity_type.pk}
            unknown = sorted(k for k in values if k not in known and not k.startswith("_"))
            if unknown:
                raise ApiError("%s has no field(s): %s" % (entity_type.label, ", ".join(unknown)))
            record: Dict[str, Any] = {entity_type.pk: entity_id}
            for field in entity_type.fields:
                if field.name in values and field.name != entity_type.pk:
                    record[field.name] = values[field.name]
            previous = _append_extra(path, type_name, record)
            try:
                model, views = _load_all()
            except (ModelError, ArchetypeError, ViewError, ModelFileError) as exc:
                path.write_text(previous, encoding="utf-8")
                raise ApiError("adding that would break the instance: %s" % exc, 409)
            report = _report(model, views)
            return {
                "saved": entity_id,
                "path": str(path.relative_to(REPO_ROOT)),
                "instance": instance_id,
                "errors": [f.format() for f in report.errors],
                "warnings": len(report.warnings),
            }
        moved = None
        if patch:
            if not existing:
                raise ApiError("%s does not exist, so there is nothing to change on it" % entity_id, 404)
            fields = {f.name for f in ENTITY_TYPES[type_name].fields}
            whole = {k: v for k, v in existing[1].items() if k in fields and k != ENTITY_TYPES[type_name].pk}
            whole.update(values)
            values = whole
        if existing:
            touched, path, moved = _save_existing(type_name, entity_id, existing[1], values)
        else:
            path = _write_entity(type_name, entity_id, values)
            touched = [(path, None)]
        # Loaded again from disk before anything is reported saved: a file
        # that only parses in memory is a model the next start refuses.
        try:
            model, views = _load_all()
        except (ModelError, ArchetypeError, ViewError, ModelFileError) as exc:
            _restore(touched)
            raise ApiError("saving that would break the model: %s" % exc, 409)
        report = _report(model, views)
    return {
        "saved": entity_id,
        "path": str(path.relative_to(REPO_ROOT)),
        "moved": moved,
        "errors": [f.format() for f in report.errors],
        "warnings": len(report.warnings),
    }


def api_delete(_query, body) -> dict:
    entity_id = str(body.get("id") or "").strip()
    if not SAFE_ID.match(entity_id):
        raise ApiError("%r is not a usable identifier" % entity_id)
    with _LOCK:
        model, _views = _load_all()
        found = model.find(entity_id)
        if found is None:
            raise ApiError("unknown entity %r" % entity_id, 404)
        type_name, record = found
        if record.get("archetype_instance"):
            raise ApiError(
                "%s is generated by %s. Exclude it on the instance instead."
                % (entity_id, record["archetype_instance"]),
                409,
            )
        path = Path(record.get("_source_file", ""))
        if not path.exists():
            raise ApiError("no file backs %s" % entity_id, 409)
        try:
            path.relative_to(REPO_ROOT / "10_MODEL")
        except ValueError:
            raise ApiError("refusing to delete outside 10_MODEL", 403)
        # A file holding a list is shared by several records, and deleting the
        # file would take the others with it; the record's own lines are taken
        # out instead. Whether it is a list is parsed rather than sniffed from
        # the text: an earlier version checked whether the file started with
        # "-", which a leading comment defeats, and deleting one org unit took
        # the whole set with it.
        home = records_module.home_of(type_name, record)
        if home.kind == "imported":
            raise ApiError(home.note, 409)
        if home.kind == "harvested":
            raise ApiError(
                "%s was harvested from the business layer, and the next import would "
                "bring it back. Add it to `exclude` in 60_SOURCES/business_layer/aliases.yaml "
                "to strike it for good." % entity_id,
                409,
            )
        previous = path.read_text(encoding="utf-8-sig")
        if home.kind == "shared":
            _write_text(path, records_module.remove_item(previous, type_name, entity_id))
        else:
            path.unlink()
        try:
            model, views = _load_all()
        except (ModelError, ArchetypeError, ViewError, ModelFileError) as exc:
            _write_text(path, previous)
            raise ApiError("deleting that would break the model: %s" % exc, 409)
        report = _report(model, views)
    return {
        "deleted": entity_id,
        "errors": [f.format() for f in report.errors],
        "warnings": len(report.warnings),
    }


def api_instantiate(_query, body) -> dict:
    """Create a product from an archetype -- the small-change path."""
    archetype_id = body.get("archetype")
    entity_id = str(body.get("id") or "").strip()
    values = body.get("values") or {}
    params = body.get("parameters") or {}
    # The parts the instance does without, and the parameters it gives the
    # parts it keeps: {alias: {parameter: value}}.
    without = [str(x) for x in (body.get("without") or []) if str(x).strip()]
    module_params = body.get("moduleParams") or {}
    choose = {str(k): str(v) for k, v in (body.get("choose") or {}).items() if str(v).strip()}
    if not SAFE_ID.match(entity_id):
        raise ApiError("%r is not a usable identifier" % entity_id)

    with _LOCK:
        model, _views = _load_all()
        archetype = model.archetypes.get(archetype_id)
        if archetype is None:
            raise ApiError("unknown archetype %r" % archetype_id, 404)
        if model.find(entity_id) is not None:
            raise ApiError("%s already exists" % entity_id, 409)

        entity_type = ENTITY_TYPES[archetype.applies_to]
        lines = ["# Created in the app from archetype %s." % archetype_id]
        lines.append("%s: %s" % (entity_type.pk, _yaml_value(entity_id)))
        for field in entity_type.fields:
            value = values.get(field.name)
            if value not in (None, ""):
                lines.append("%s: %s" % (field.name, _yaml_value(value)))
        lines.append("")
        lines.append("archetype: %s" % archetype_id)
        lines.append("parameters:")
        for param in archetype.parameters:
            if param.name in params and str(params[param.name]).strip():
                lines.append("  %s: %s" % (param.name, _yaml_value(params[param.name])))
        if without:
            lines.append("")
            lines.append("# Parts of the shape this product does without.")
            lines.append("without: [%s]" % ", ".join(without))
        # Only the choices that differ from the shape's default are written,
        # so a product on the defaults says nothing and the file stays small.
        defaults = {s.name: (s.default or "none") for s in archetype.slots}
        differing = [(k, v) for k, v in choose.items() if k in defaults and v != defaults[k]]
        if differing:
            lines.append("")
            lines.append("# Where this product chooses differently from the shape's default.")
            lines.append("choose:")
            for key, value in differing:
                lines.append("  %s: %s" % (key, _yaml_value(value)))
        try:
            library_modules = load_modules(REPO_ROOT)
        except ModuleError:
            library_modules = {}
        # Every part the form showed a switch for, kit members included, and
        # every slot option the product actually chose: a parameter given for
        # an option it did not choose is not written, for the same reason one
        # given for a dropped part is not.
        aliases = {
            m["alias"]: m["id"]
            for m in _module_summaries(archetype, library_modules)
            if not m.get("missing") and not m.get("kit")
        }
        aliases.update({
            m["alias"]: m["id"]
            for m in _module_summaries(archetype, library_modules)
            if not m.get("missing") and m.get("kit")
        })
        chosen_now = {s.name: choose.get(s.name, s.default or "none") for s in archetype.slots}
        for slot in archetype.slots:
            for option in slot.options:
                if chosen_now.get(slot.name) == option:
                    aliases[option] = option
        given = []
        for alias, supplied in module_params.items():
            kept = {k: v for k, v in (supplied or {}).items() if str(v).strip()}
            if kept and alias in aliases and alias not in without:
                given.append((alias, aliases[alias], kept))
        if given:
            lines.append("")
            lines.append("# What this product tells the parts it keeps.")
            lines.append("modules:")
            for alias, module_id, kept in given:
                lines.append("  - module: %s" % module_id)
                if alias != module_id:
                    lines.append("    as: %s" % alias)
                lines.append("    with:")
                for key, value in kept.items():
                    lines.append("      %s: %s" % (key, _yaml_value(value)))
        path = _entity_path(archetype.applies_to, entity_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        try:
            model, views = _load_all()
        except (ModelError, ArchetypeError) as exc:
            path.unlink()
            raise ApiError("archetype expansion failed, nothing written: %s" % exc, 409)
        report = _report(model, views)
        created = [
            r[ENTITY_TYPES[t].pk]
            for t in ENTITY_TYPES
            for r in model.all_of(t)
            if r.get("archetype_instance") == entity_id
        ]
    return {
        "created": entity_id,
        "path": str(path.relative_to(REPO_ROOT)),
        "generated": sorted(created),
        "errors": [f.format() for f in report.errors],
        "warnings": len(report.warnings),
    }


def api_validate(_query, _body) -> dict:
    model, views = _load_all()
    report = _report(model, views)
    return {
        "errors": [
            {"code": f.code, "message": f.message, "where": _rel(f.where)} for f in report.errors
        ],
        "warnings": [
            {"code": f.code, "message": f.message, "where": _rel(f.where)}
            for f in report.warnings
        ],
        "summary": validate.summarize(report),
    }


def _rel(where: str) -> str:
    if not where:
        return ""
    try:
        return str(Path(where).relative_to(REPO_ROOT))
    except ValueError:
        return where


def api_render(_query, _body) -> dict:
    """The same generation as `terrane render`, from the app.

    It used to be a second, shorter renderer, and the two disagreed: this one
    wrote a diagram for every report and never removed a stale subject file.
    Now it *is* the command, so what the button produces is what CI checks.
    """
    import argparse
    import contextlib
    import io

    from terrane import cli

    with _LOCK:
        model, views = _load_all()
        rendered, skipped = [], []
        for view in views:
            try:
                graph = resolve(model, bind(
                    view,
                    dict(render_targets(model, view)) if view.parameters else None,
                    model,
                ))
            except ViewError as exc:
                skipped.append({"viewId": view.view_id, "reason": str(exc)})
                continue
            rendered.append(
                {"viewId": view.view_id, "nodes": len(graph.nodes), "edges": len(graph.edges)}
            )
        log = io.StringIO()
        with contextlib.redirect_stdout(log):
            cli.cmd_render(argparse.Namespace(root=str(REPO_ROOT), view=None, format="all", out=None))
            cli.cmd_schema(argparse.Namespace(root=str(REPO_ROOT), out=None))
        out_dir = REPO_ROOT / "70_ARTIFACTS"
        exports.export_csv(model, out_dir / "export" / "csv")
        exports.export_backstage(model, out_dir / "export" / "backstage")
        exports.export_json(model, out_dir / "export" / "model.json")
        written = 0
        for line in log.getvalue().splitlines():
            if "file(s) written" in line:
                try:
                    written += int(line.split()[0])
                except ValueError:
                    pass
    return {"filesWritten": written, "rendered": rendered, "skipped": skipped}


def api_import(_query, body) -> dict:
    source = str(body.get("source") or "").strip()
    if not source:
        raise ApiError("no source directory given")
    path = Path(source)
    if not path.is_absolute():
        path = REPO_ROOT / path
    with _LOCK:
        model, _views = _load_all()
        outcome = importer.import_csv(
            REPO_ROOT, path, model, overwrite=bool(body.get("overwrite"))
        )
        model, views = _load_all()
        report = _report(model, views)
    return {
        "imported": outcome.imported,
        "filesWritten": len(outcome.written),
        "conflicts": outcome.conflicts[:50],
        "conflictCount": len(outcome.conflicts),
        "errors": [f.format() for f in report.errors],
    }


# ---- sources ----------------------------------------------------------------
# An export from another tool, brought in through a mapping or held against
# the model (`terrane/sources.py`). An upload is staged in a folder of its own
# outside the repository until it is brought in, and written into the
# repository only when the person keeps it as a source.

_STAGED: Dict[str, Dict[str, Any]] = {}

#: An upload larger than this is refused rather than read: an inventory is
#: thousands of rows, not hundreds of megabytes.
_UPLOAD_LIMIT = 25 * 1024 * 1024


def _source_kinds() -> dict:
    return {kind: {"label": ENTITY_TYPES[kind].label, "fields": sources_module.kind_fields(kind),
                   "prefix": None} for kind in sources_module.KINDS}


def api_sources(_query, _body) -> dict:
    """Every kept source, a comparing one with what differs now."""
    model, _views = _load_all()
    out = []
    for source in sources_module.list_sources(REPO_ROOT):
        if source["kind"] == "compares":
            try:
                source["compared"] = sources_module.compare_counts(model, REPO_ROOT, source)
            except Exception as exc:  # noqa: BLE001 -- a source that does not read says why
                source["problem"] = str(exc)
        out.append(source)
    return {"sources": out, "folder": sources_module.SOURCES}


def _staged(token: str) -> Dict[str, Any]:
    staged = _STAGED.get(str(token or ""))
    if staged is None:
        raise ApiError("that upload is no longer here; choose the file again", 410)
    return staged


def _stage(name: str, data: bytes, sheet: Optional[str] = None, token: Optional[str] = None) -> Dict[str, Any]:
    """The upload read, and written as the mapping engine reads it into a
    folder of its own outside the repository."""
    import secrets
    import tempfile

    name = Path(str(name or "")).name
    try:
        table = sources_module.read_table(name, data, sheet)
    except sources_module.SourceError as exc:
        raise ApiError(str(exc), 422)
    if not table.rows:
        raise ApiError("%s has a header and no rows" % name, 422)
    staged = _STAGED.get(token or "") if token else None
    if staged is None:
        token = secrets.token_hex(8)
        staged = {"dir": Path(tempfile.mkdtemp(prefix="terrane-source-"))}
        _STAGED[token] = staged
    data_on_disk = sources_module.utf8_csv(data) if name.lower().endswith(".csv") else data
    (staged["dir"] / name).write_bytes(data_on_disk)
    staged.update({"token": token, "name": name, "data": data_on_disk, "table": table})
    return staged


def _unstage(token: str) -> None:
    import shutil

    staged = _STAGED.pop(token, None)
    if staged is not None:
        # Exactly the folder mkdtemp made for this upload, and nothing above it.
        shutil.rmtree(staged["dir"])


def _table_answer(staged: Dict[str, Any], model, kind: Optional[str] = None) -> dict:
    table = staged["table"]
    suggestion = sources_module.suggest(table, model, kind)
    return {
        "token": staged["token"], "file": table.file, "sheet": table.sheet, "sheets": table.sheets,
        "rows": len(table.rows), "columns": sources_module.columns_of(table),
        "suggestion": suggestion,
        "kinds": {k: dict(v, prefix=sources_module.id_prefix(model, k)) for k, v in _source_kinds().items()},
    }


def api_sources_read(_query, body) -> dict:
    """An upload, or another sheet of one, or a kept source opened again:
    its columns and what each looks like, and a suggestion of what each is
    for the person to confirm."""
    import base64

    model, _views = _load_all()
    if body.get("source"):
        folder, data = _kept(body["source"])
        choice = sources_module.choice_of(data)
        if choice is None:
            raise ApiError("this source's mapping is more than the steps show; edit %s/%s/%s"
                           % (sources_module.SOURCES, folder.name, sources_module.MAPPING), 422)
        path = folder / str(choice["file"])
        if not path.is_file():
            raise ApiError("%s is not in %s" % (choice["file"], folder.name), 404)
        staged = _stage(path.name, path.read_bytes(), choice.get("sheet"))
        staged["source"] = folder.name
        answer = _table_answer(staged, model)
        answer["saved"] = choice
        answer["name"] = next((s["name"] for s in sources_module.list_sources(REPO_ROOT) if s["id"] == folder.name),
                              folder.name)
        return answer
    if body.get("token") and not body.get("data"):
        staged = _staged(body["token"])
        if body.get("sheet") is not None:
            _stage(staged["name"], staged["data"], body.get("sheet") or None, token=staged["token"])
        return _table_answer(staged, model, body.get("kind") or None)
    try:
        data = base64.b64decode(str(body.get("data") or ""), validate=False)
    except ValueError:
        raise ApiError("the file did not arrive whole; choose it again", 400)
    if not data:
        raise ApiError("the file is empty", 422)
    if len(data) > _UPLOAD_LIMIT:
        raise ApiError("the file is %d MB; an export of more than %d MB is not read here"
                       % (len(data) // (1024 * 1024), _UPLOAD_LIMIT // (1024 * 1024)), 413)
    staged = _stage(str(body.get("name") or ""), data, body.get("sheet") or None)
    return _table_answer(staged, model)


def _choice_columns(choice: dict) -> Dict[str, List[str]]:
    return {str(c): [str(t) for t in (ts if isinstance(ts, list) else [ts]) if t]
            for c, ts in (choice.get("columns") or {}).items()}


def api_sources_words(_query, body) -> dict:
    """The export's words for each field with a fixed list, and the names a
    reference needs found."""
    staged = _staged(body.get("token"))
    choice = body.get("choice") or {}
    kind = str(choice.get("kind") or "")
    if kind not in sources_module.KINDS:
        raise ApiError("%s is not a kind of record a source brings in" % kind, 422)
    model, _views = _load_all()
    return sources_module.words_needed(staged["table"], kind, _choice_columns(choice), model)


def _mapping_from(staged: Dict[str, Any], choice: dict) -> dict:
    kind = str(choice.get("kind") or "")
    if kind not in sources_module.KINDS:
        raise ApiError("%s is not a kind of record a source brings in" % kind, 422)
    return sources_module.build_mapping(
        staged["table"], kind, _choice_columns(choice), code=choice.get("code") or None,
        values=choice.get("values") or {}, defaults=choice.get("defaults") or {},
        prefix=choice.get("prefix") or None, units_from=choice.get("unitsFrom") or None,
        description=str(choice.get("description") or ""))


def _kept(source_id: str):
    try:
        return sources_module.mapping_of(REPO_ROOT, Path(str(source_id)).name)
    except (sources_module.SourceError, sources_module.MappingError) as exc:
        raise ApiError(str(exc), 422)


def api_sources_preview(_query, body) -> dict:
    """Everything bringing it in would write, and what the checks would
    newly say, with nothing written."""
    model, views = _load_all()
    if body.get("source") and not body.get("token"):
        folder, data = _kept(body["source"])
    else:
        staged = _staged(body.get("token"))
        folder = staged["dir"]
        try:
            data = _mapping_from(staged, body.get("choice") or {})
        except sources_module.SourceError as exc:
            raise ApiError(str(exc), 422)
    try:
        result = sources_module.preview(model, views, folder, data, before=_report(model, views))
    except sources_module.MappingError as exc:
        raise ApiError(str(exc), 422)
    answer = result.as_dict()
    answer["mapping"] = sources_module.render_mapping(data)
    return answer


def api_sources_bring_in(_query, body) -> dict:
    """The export brought in through its mapping, and kept as a source when
    asked: its file and mapping in a folder of 60_SOURCES, with a note of
    this run."""
    with _LOCK:
        model, _views = _load_all()
        staged = None
        if body.get("source") and not body.get("token"):
            folder, data = _kept(body["source"])
            kept = folder
        else:
            staged = _staged(body.get("token"))
            try:
                data = _mapping_from(staged, body.get("choice") or {})
            except sources_module.SourceError as exc:
                raise ApiError(str(exc), 422)
            name = " ".join(str(body.get("keep") or "").split())
            if name:
                try:
                    kept = sources_module.keep(REPO_ROOT, name, {staged["name"]: staged["data"]}, data)
                except sources_module.SourceError as exc:
                    raise ApiError(str(exc), 422)
                folder = kept
            else:
                kept = None
                folder = staged["dir"]
                _write_text(folder / sources_module.MAPPING, sources_module.render_mapping(data))
        try:
            outcome = importer.import_csv(REPO_ROOT, folder, model, mapping=folder / sources_module.MAPPING)
        except sources_module.MappingError as exc:
            raise ApiError(str(exc), 422)
        if kept is not None:
            sources_module.note_run(kept, outcome.imported, len(outcome.held))
        if staged is not None:
            _unstage(staged["token"])
        model, views = _load_all()
        report = _report(model, views)
    return {
        "imported": outcome.imported, "filesWritten": len(outcome.written),
        "held": outcome.held, "conflicts": outcome.conflicts[:50], "conflictCount": len(outcome.conflicts),
        "skipped": outcome.skipped, "source": kept.name if kept is not None else None,
        "errors": [f.format() for f in report.errors],
    }


def _git(*args: str) -> str:
    import subprocess

    try:
        done = subprocess.run(["git", "-C", str(REPO_ROOT)] + list(args), capture_output=True, text=True,
                              timeout=10)
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def api_project(_query, _body) -> dict:
    """What the Project tab says about this estate: its name, where it
    lives, what it reads its library and views from, the governance it is
    pinned to, and whether its ignore file keeps credentials out."""
    from terrane.estate import SECRET_PATTERNS

    model, _views = _load_all()
    config = model.config or {}
    ignore = REPO_ROOT / ".gitignore"
    lines = {line.strip() for line in ignore.read_text(encoding="utf-8").splitlines()} if ignore.is_file() else set()
    governance = config.get("governance") if isinstance(config.get("governance"), dict) else None
    return {
        "name": config.get("name") or "Architecture Model",
        "description": str(config.get("description") or "").strip(),
        "folder": REPO_ROOT.name,
        "path": str(REPO_ROOT),
        "sample": bool(config.get("sample_estate")),
        "library": "package" if config.get("shipped_library") == "package" else "repository",
        "views": "package" if str(config.get("shipped_views") or "").startswith("package") else "repository",
        "libraryPaths": [str(p) for p in (config.get("library_paths") or [])],
        "governance": {"repository": str(governance.get("repository") or ""), "ref": str(governance.get("ref") or "")}
        if governance else None,
        "requires": str(config.get("requires_terrane") or ""),
        "git": {"branch": _git("rev-parse", "--abbrev-ref", "HEAD"), "remote": _git("remote", "get-url", "origin")},
        "secretsKeptOut": all(p in lines for p in SECRET_PATTERNS),
        "secretsMissing": [p for p in SECRET_PATTERNS if p not in lines],
    }


def api_project_guard(_query, _body) -> dict:
    """The credential lines added to the estate's ignore file, under its own."""
    from terrane.estate import guard_secrets

    with _LOCK:
        changed = guard_secrets(REPO_ROOT / ".gitignore")
    return {"changed": changed}


def api_sources_discard(_query, body) -> dict:
    """An upload let go without bringing it in: its staging folder removed."""
    if body.get("token"):
        _unstage(str(body["token"]))
    return {"ok": True}


# ---- sketches -------------------------------------------------------------
# A sketch is a set of ids an architect grows from the map. It lives in the
# browser until it is written back, and it is written back only in the forms
# the repository keeps: a view file, or a module in the library.


def _sketch_ids(body) -> List[str]:
    ids = [str(x).strip() for x in (body.get("ids") or []) if str(x).strip()]
    if not ids:
        raise ApiError("a sketch needs at least one entity", 422)
    if len(ids) > 240:
        raise ApiError("a sketch of more than 240 things is a landscape, not a sketch", 422)
    return ids


def api_sketch_view(query, body) -> dict:
    """The view text for a sketch, and the drawing it would make.

    Nothing is written. Saving goes through `/api/view/save` with this text,
    so a sketch is validated exactly like a view someone typed.
    """
    ids = _sketch_ids(body)
    view_id = str(body.get("id") or "sketch").strip() or "sketch"
    if not SAFE_ID.match(view_id):
        raise ApiError("a view id must be an identifier: letters, digits, . _ -", 422)
    model, _views = _load_all()
    try:
        text = view_text_from_sketch(
            model,
            ids=ids,
            view_id=view_id,
            title=str(body.get("title") or "Sketch"),
            description=str(body.get("description") or ""),
            category=str(body.get("category") or "Sketches"),
            group_by=[str(g) for g in (body.get("groupBy") or []) if str(g).strip()],
            color_by=str(body.get("colorBy") or "").strip() or None,
            layout=str(body.get("layout") or "LR"),
        )
    except SketchError as exc:
        raise ApiError(str(exc), 404)
    view = _view_from_text(text)
    try:
        payload = _graph_payload(model, view, _palette(model, query))
    except ViewError as exc:
        raise ApiError(str(exc), 409)
    payload["preview"] = True
    payload["sketch"] = True
    payload["text"] = text
    return payload


def api_sketch_module(_query, body) -> dict:
    """The module text a sketch would become, with the report of how."""
    ids = _sketch_ids(body)
    model, _views = _load_all()
    module_id = str(body.get("module_id") or "").strip()
    if module_id and not SAFE_ID.match(module_id):
        raise ApiError("a module id must be an identifier: letters, digits, . _ -", 422)
    try:
        text, report = module_text_from_sketch(
            model,
            ids=ids,
            module_id=module_id or "my-part",
            name=str(body.get("name") or "My part"),
            description=str(body.get("description") or "What this part is and why it exists."),
            category=str(body.get("category") or "Other"),
            slug=str(body.get("slug") or "").strip() or None,
            product_name=str(body.get("product_name") or "").strip() or None,
            optional=bool(body.get("optional", True)),
        )
    except SketchError as exc:
        raise ApiError(str(exc), 422)
    try:
        modules = load_modules(REPO_ROOT)
    except ModuleError:
        modules = {}
    report["exists"] = module_id in modules
    # The shape's own binding beats a guess from the ids: a sketch that
    # includes five AWS services would otherwise be told its slug is `aws`.
    report["guessedSlug"] = report.get("slug") or guess_slug(ids)
    return {"text": text, "report": report,
            "folder": _shown(REPO_ROOT, own_root(REPO_ROOT).path / MODULES_DIR) + "/"}


def api_module_save(_query, body) -> dict:
    """Write one module file into 28_MODULES/ from its text: the
    organization's when the model names a library of its own, so a save
    never edits the shipped one.

    The text is parsed and the library reloaded before the write counts. A
    module that only parses in memory would break the next start and every
    shape composed from it.
    """
    text = str(body.get("text") or "")
    editing = str(body.get("id") or "").strip() or None
    try:
        data = parse_data_text(text, "the module you are editing")
    except ModelFileError as exc:
        raise ApiError("that is not valid YAML: %s" % _yaml_complaint(exc.message), 422)
    listed = data if isinstance(data, list) else [data]
    if not listed or not all(isinstance(item, dict) for item in listed):
        raise ApiError("a module file is a mapping, or a list of them", 422)
    try:
        parsed = [parse_module(item) for item in listed]
    except ModuleError as exc:
        raise ApiError(str(exc), 422)
    module_id = parsed[0].module_id
    if not SAFE_ID.match(module_id):
        raise ApiError("a module id must be an identifier: letters, digits, . _ -", 422)
    if editing and editing != module_id:
        raise ApiError(
            "this file is %s; changing module_id to %r would leave two modules claiming "
            "one file." % (editing, module_id), 409,
        )

    with _LOCK:
        try:
            existing = load_modules(REPO_ROOT)
        except ModuleError as exc:
            raise ApiError("the module library does not load: %s" % exc, 409)
        home = own_root(REPO_ROOT)
        folder = home.path / MODULES_DIR
        path = folder / ("%s.yaml" % module_id)
        for item in parsed:
            known = existing.get(item.module_id)
            if known is not None and known.source_file is not None:
                if Path(known.source_file).resolve() != path.resolve():
                    # A part from a library read before the organization's
                    # may be replaced from it, and only by saying so.
                    if home.name and known.library != home.name:
                        if _says_replaces(text, item.module_id):
                            continue
                        raise _not_ours("part", item.module_id, Path(known.source_file), home)
                    raise ApiError(
                        "a module called %r already exists in %s. Edit that file, or "
                        "choose another id."
                        % (item.module_id, _shown(REPO_ROOT, known.source_file)),
                        409,
                    )
        previous = path.read_text(encoding="utf-8-sig") if path.exists() else None
        folder.mkdir(parents=True, exist_ok=True)
        path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
        try:
            load_modules(REPO_ROOT)
            model, views = _load_all()
        except (ModuleError, ModelError, ArchetypeError, ViewError, ModelFileError) as exc:
            if previous is None:
                path.unlink()
            else:
                path.write_text(previous, encoding="utf-8")
            raise ApiError("saving that would break the library: %s" % exc, 409)
        report = _report(model, views)

    return {
        "id": module_id,
        "path": _shown(REPO_ROOT, path),
        "library": home.name,
        "created": previous is None,
        "modules": [m.module_id for m in parsed],
        "errors": [f.format() for f in report.errors],
        "warnings": len(report.warnings),
    }


def api_archetype_compose(_query, body) -> dict:
    """The archetype text for a choice of parts. Nothing is written: the
    editor previews and saves it like a typed shape."""
    archetype_id = str(body.get("id") or "").strip()
    if archetype_id and not SAFE_ID.match(archetype_id):
        raise ApiError("an archetype id must be an identifier: letters, digits, . _ -", 422)
    try:
        text = archetype_text_from_parts(
            REPO_ROOT,
            archetype_id=archetype_id or "my-shape",
            title=str(body.get("title") or "My shape"),
            description=str(body.get("description") or "What this shape creates, and why."),
            parameters=[str(p) for p in (body.get("parameters") or [])],
            modules=list(body.get("modules") or []),
            blocks=list(body.get("blocks") or []),
            patterns=[str(p) for p in (body.get("patterns") or [])],
            provider=str(body.get("provider") or "").strip() or None,
            applies_to=str(body.get("appliesTo") or "products"),
            extra_parameters=list(body.get("extraParameters") or []),
            # The landing zone by kind, for the parts that name one and no
            # chosen block binds.
            bind={str(k): str(v) for k, v in (body.get("bind") or {}).items()},
        )
    except (ComposeError, ModuleError, LibraryError) as exc:
        raise ApiError(str(exc), 422)
    return {"text": text, "path": _shown(REPO_ROOT, _archetype_path(archetype_id or "my-shape"))}


def api_compose_options(_query, _body) -> dict:
    """What the composer offers: the vocabulary, the parts, the blocks with
    their components and the shared services that could stand for each."""
    components, blocks, patterns = _library()
    model, _views = _load_all()
    try:
        modules = load_modules(REPO_ROOT)
    except ModuleError:
        modules = {}
    vocabulary = [dict(p) for p in VOCABULARY]
    shared = [
        {"id": r["tech_service_id"], "name": r.get("name") or r["tech_service_id"],
         "component": r.get("component_type") or "", "provider": r.get("cloud_provider") or r.get("provider") or ""}
        for r in model.all_of("tech_services")
        if not r.get("archetype_instance")
    ]
    shared.sort(key=lambda s: s["name"].lower())
    return {
        "vocabulary": vocabulary,
        "providers": sorted({name for c in components.values() for name in c.providers}),
        "modules": [
            {"id": m.module_id, "name": m.name, "category": m.category, "description": m.description,
             "optional": m.optional, "requires": list(m.requires), "runsOn": blocks_needed(m),
             "parameters": [{"name": p.name, "required": p.required, "default": p.default,
                             "description": p.description} for p in m.parameters]}
            for m in sorted(modules.values(), key=lambda m: (m.category, m.name.lower()))
        ],
        "blocks": [
            {"id": b.building_block_id, "name": b.name, "category": b.category, "description": b.description,
             "components": [{"id": p.component, "name": components[p.component].name}
                            for p in b.provides]}
            for b in sorted(blocks.values(), key=lambda b: (b.category, b.name.lower()))
        ],
        "patterns": [
            {"id": p.pattern_id, "name": p.name, "status": p.status, "category": p.category}
            for p in sorted(patterns.values(), key=lambda p: p.name.lower())
        ],
        "shared": shared,
    }


# --------------------------------------------------------------------------
# Assembling a project from parts
# --------------------------------------------------------------------------
#
# The parts of the library are diagram chunks: a handful of entities with the
# relations between them, parameterized. A shape is a fixed choice of them;
# a project assembled here is a choice made once, for one product, with the
# small edits a product always needs -- a name, an answer, a part dropped, a
# field overridden -- and written as one file whose `compose` block is the
# whole architecture. The preview is the product's own architecture view,
# resolved against a scratch copy of the model with the assembly in it, so
# what is drawn before the file exists is what the file will draw.


#: How a template token reads on a chunk's thumbnail, before any product
#: has answered it.
_THUMB_TOKENS = {
    "product_name": "Product", "vendor": "Vendor", "slug": "product", "caller_system": "Caller",
    "consumer_system": "Consumer", "system": "System", "name": "Role", "item": "Spoke",
    "idp": "IdP", "bus": "Bus", "stream": "Stream", "vault": "Vault", "platform": "Platform",
    "front_door": "Gateway", "warehouse": "Warehouse", "hub": "Hub", "spokes": "Spokes",
}

_TOKEN_IN_TEXT = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)(?:\|[a-z]+)?\}")


def _thumb_text(value: Any) -> str:
    text = str(value or "")

    def swap(match) -> str:
        name = match.group(1)
        return _THUMB_TOKENS.get(name, name.replace("_", " "))

    return _TOKEN_IN_TEXT.sub(swap, text)


def _chunk_shape(module, modules) -> dict:
    """What a chunk draws as, before any answers: its entities by type and
    the lines between them, tokens read as words. A kit draws its members.
    Enough for a thumbnail; the preview is the real expansion."""
    nodes: List[dict] = []
    edges: List[dict] = []
    seen: Dict[str, str] = {}
    for member_id in members_of(module, modules):
        member = modules[member_id]
        for type_name, templates in member.provides.items():
            pk = ENTITY_TYPES[type_name].pk if type_name in ENTITY_TYPES else "id"
            for template in templates:
                if type_name == "interfaces":
                    continue
                raw_id = str(template.get(pk) or "")
                key = _thumb_text(raw_id) or raw_id
                if key in seen:
                    continue
                seen[key] = type_name
                nodes.append({
                    "id": key,
                    "type": type_name,
                    "name": _thumb_text(template.get("name") or raw_id),
                    "each": bool(template.get("each")),
                })
        for template in member.provides.get("interfaces", []):
            edges.append({
                "from": _thumb_text(template.get("source_system_id")),
                "to": _thumb_text(template.get("target_system_id")),
                "label": _thumb_text(template.get("protocol") or ""),
            })
        for relation_name, rows in member.relations.items():
            spec = RELATION_TYPES.get(relation_name)
            if spec is None:
                continue
            for row in rows:
                edges.append({
                    "from": _thumb_text(row.get(spec.left_column)),
                    "to": _thumb_text(row.get(spec.right_column)),
                    "label": relation_name.replace("_", " "),
                    "soft": True,
                })
    # A line to something outside the chunk is drawn to a placeholder, so
    # the thumbnail shows that the chunk reaches out.
    for edge in edges:
        for end in ("from", "to"):
            if edge[end] and edge[end] not in seen:
                seen[edge[end]] = "outside"
                nodes.append({"id": edge[end], "type": "outside", "name": edge[end], "each": False})
    return {"nodes": nodes, "edges": edges}


def api_chunks(query, _body) -> dict:
    """Everything the Assemble panel needs: the parts as chunks with what
    each draws, the vocabulary, the providers and their landing zones, the
    shapes a project could start from, and the lists the project's own
    fields pick from."""
    model, _views = _load_all()
    palette = _palette(model, query)
    try:
        modules = load_modules(REPO_ROOT)
    except ModuleError as exc:
        raise ApiError("the module library did not load: %s" % exc, 409)
    components, blocks, patterns = _library()
    landing = landing_zone_index(model.all_of("tech_services"))
    try:
        build_types = load_build_types(REPO_ROOT)
    except BuildTypeError:
        build_types = {}
    # The standard service of each kind on each cloud, by name: what a part
    # runs on without anyone choosing it.
    service_pk = ENTITY_TYPES["tech_services"].pk
    service_names = {str(r.get(service_pk)): str(r.get("name") or r.get(service_pk)) for r in model.all_of("tech_services")}
    zone_services: Dict[str, Dict[str, dict]] = {}
    for (provider, kind), ids in landing.items():
        if provider and ids:
            zone_services.setdefault(provider, {})[kind] = {"id": ids[0], "name": service_names.get(ids[0], ids[0])}

    in_kits: Dict[str, List[str]] = {}
    for kit in modules.values():
        for member_id in members_of(kit, modules):
            if member_id != kit.module_id:
                in_kits.setdefault(member_id, []).append(kit.module_id)

    chunks = []
    for module in sorted(modules.values(), key=lambda m: (m.category, m.name.lower())):
        chunks.append({
            "id": module.module_id,
            "name": module.name,
            "category": module.category,
            "description": module.description,
            "optional": module.optional,
            "requires": list(module.requires),
            "needs": list(module.needs),
            "patterns": list(module.patterns),
            "kit": module.is_kit,
            "members": members_of(module, modules) if module.is_kit else [],
            "inKits": in_kits.get(module.module_id, []),
            "runsOn": blocks_needed(module),
            "provides": provided_count(module, modules),
            "parameters": [
                {"name": p.name, **_asked(p, estate_answers(model.config)), "component": p.component,
                 # The landing-zone service of that kind per provider, so the
                 # form can say what the chunk will get before it is asked.
                 "bound": {
                     provider: resolve_kind(p.component, provider, landing)[0]
                     for provider in landing_providers(model.archetypes.values())
                 } if p.component else None}
                for p in module.parameters
            ],
            "shape": _chunk_shape(module, modules),
        })

    shapes = [
        _shape_payload(archetype)
        for archetype in sorted(model.archetypes.values(), key=lambda a: a.archetype_id)
        if archetype.applies_to == "products"
    ]

    def distinct(type_names, field):
        values = set()
        for type_name in type_names:
            for record in model.all_of(type_name):
                value = record.get(field)
                if value:
                    values.add(str(value))
        return sorted(values)

    by_provider: Dict[str, Dict[str, List[str]]] = {}
    for type_name in ("systems", "tech_services"):
        for record in model.all_of(type_name):
            provider = str(record.get("cloud_provider") or "")
            if not provider:
                continue
            slot = by_provider.setdefault(provider, {"accounts": [], "regions": []})
            for key, field in (("accounts", "cloud_account"), ("regions", "region")):
                value = str(record.get(field) or "")
                if value and value not in slot[key]:
                    slot[key].append(value)
    for slot in by_provider.values():
        slot["accounts"].sort()
        slot["regions"].sort()

    # The products the panel can open again with their chunks picked and
    # their edits in place: the ones it assembled, and the ones on a shape.
    assembled = []
    for product in sorted(model.all_of("products"), key=lambda r: str(r.get("product_id"))):
        shape_id = str(product.get("archetype") or "")
        if not shape_id:
            continue
        if shape_id.startswith("compose:"):
            shape = (getattr(model, "composed", {}) or {}).get(shape_id)
            on_shape = ""
        else:
            shape = model.archetypes.get(shape_id)
            on_shape = shape_id
        if shape is None:
            continue
        assembled.append({
            "id": str(product.get("product_id")),
            "name": product.get("name") or product.get("product_id"),
            "status": product.get("status") or "",
            "provider": shape.provider or "",
            "shape": on_shape,
            "chunks": len(shape.modules) + len(shape.slots),
        })

    swatches = {}
    for type_name in ENTITY_TYPES:
        swatch = palette.type_swatch(type_name)
        swatches[type_name] = {"fill": swatch.fill, "stroke": swatch.stroke}

    return {
        "chunks": chunks,
        "vocabulary": [dict(p) for p in VOCABULARY],
        "providers": sorted({name for c in components.values() for name in c.providers}),
        "landingZones": by_provider,
        "shapes": shapes,
        "assembled": assembled,
        "patterns": [{"id": p.pattern_id, "name": p.name, "status": p.status} for p in
                     sorted(patterns.values(), key=lambda p: p.name.lower())],
        "orgs": sorted(
            ({"id": r["org_unit_id"], "name": r.get("name") or r["org_unit_id"]} for r in model.all_of("org_units")),
            key=lambda o: o["name"].lower()),
        "domains": distinct(("systems", "products", "capabilities"), "company_domain"),
        "categories": distinct(("products",), "product_category"),
        "types": [
            {"id": t.build_type_id, "name": t.name, "description": t.description,
             "requires": list(t.requires), "includes": list(t.includes), "offers": list(t.offers),
             "shapes": dict(t.shapes),
             "products": sum(1 for r in model.all_of("products") if str(r.get("build_type") or "") == t.build_type_id)}
            for t in build_types.values()
        ],
        "landing": zone_services,
        "swatches": swatches,
        "fields": {
            "systems": [f.name for f in ENTITY_TYPES["systems"].fields if f.name not in ("archetype", "archetype_instance")],
            "interfaces": [f.name for f in ENTITY_TYPES["interfaces"].fields if f.name not in ("archetype", "archetype_instance")],
            "tech_services": [f.name for f in ENTITY_TYPES["tech_services"].fields if f.name not in ("archetype", "archetype_instance")],
            "data_assets": [f.name for f in ENTITY_TYPES["data_assets"].fields if f.name not in ("archetype", "archetype_instance")],
            "actors": [f.name for f in ENTITY_TYPES["actors"].fields if f.name not in ("archetype", "archetype_instance")],
        },
    }


def _shape_payload(archetype) -> dict:
    """A shape as the panel holds it: its parts with what it binds for each,
    its slots, its blocks and binds and patterns, and what it asks."""
    parts = []
    for entry in archetype.modules:
        parts.append({"module": str(entry.get("module")), "as": str(entry.get("as") or entry.get("module")),
                      "with": dict(entry.get("with") or {})})
    return {
        "id": archetype.archetype_id, "title": archetype.title, "provider": archetype.provider,
        "modules": parts,
        "slots": [{"name": s.name, "options": list(s.options), "default": s.default, "optional": s.optional,
                   "with": {k: dict(v) for k, v in s.answers.items()}}
                  for s in archetype.slots],
        "blocks": [dict(b) for b in archetype.blocks],
        "bind": dict(archetype.bind),
        "patterns": list(archetype.patterns),
        "parameters": [{"name": p.name, "default": p.default, "required": p.required} for p in archetype.parameters],
    }


def _module_items(entries) -> List[dict]:
    """Module entries as the file writes them: the module, an alias when it
    differs, and the bindings that say something."""
    parts: List[dict] = []
    for entry in entries or []:
        if isinstance(entry, str):
            entry = {"module": entry}
        module_id = str((entry or {}).get("module") or "").strip()
        if not module_id:
            continue
        item: Dict[str, Any] = {"module": module_id}
        if entry.get("as") and str(entry["as"]) != module_id:
            item["as"] = str(entry["as"])
        bound = {str(k): v for k, v in (entry.get("with") or {}).items() if v not in (None, "", [])}
        if bound:
            item["with"] = bound
        parts.append(item)
    return parts


def _assembly(body) -> Tuple[str, dict]:
    """The instance record an assembly request describes, as the file would
    say it, checked for the things a bad request gets wrong. A request that
    names `archetype` describes a product on that shape: its answers, its
    choices, what it does without and what it tells the parts; one that
    names `compose` describes a product assembled from parts with no shape."""
    instance_id = str(body.get("id") or "").strip()
    if not SAFE_ID.match(instance_id):
        raise ApiError("%r is not a usable identifier" % instance_id, 422)
    values = {k: v for k, v in (body.get("values") or {}).items() if v not in (None, "", [])}
    archetype = str(body.get("archetype") or "").strip()
    compose = body.get("compose") or {}
    parts = _module_items(body.get("modules") if archetype else compose.get("modules"))
    if not archetype and not parts:
        raise ApiError("pick at least one part", 422)
    parameters = {str(k): v for k, v in (body.get("parameters") or {}).items() if v not in (None, "")}
    overrides = {}
    for entity_id, fields in (body.get("overrides") or {}).items():
        kept = {str(k): v for k, v in (fields or {}).items() if v not in (None, "")}
        if kept:
            overrides[str(entity_id)] = kept
    exclude = [str(x) for x in (body.get("exclude") or []) if str(x).strip()]
    extra = body.get("extra") or None
    record: Dict[str, Any] = {"product_id": instance_id}
    record.update(values)
    build_type = str(body.get("buildType") or "").strip()
    if build_type:
        record["build_type"] = build_type
    if archetype:
        record["archetype"] = archetype
        choose = {str(k): str(v) for k, v in (body.get("choose") or {}).items() if str(v).strip()}
        if choose:
            record["choose"] = choose
        without = [str(x) for x in (body.get("without") or []) if str(x).strip()]
        if without:
            record["without"] = without
        kept = {str(k): str(v).strip() for k, v in (body.get("ids") or {}).items() if str(v).strip()}
        if kept:
            record["ids"] = kept
        if parts:
            record["modules"] = parts
    else:
        block: Dict[str, Any] = {"modules": parts}
        provider = str(compose.get("provider") or "").strip()
        if provider:
            block["provider"] = provider
        for key in ("blocks", "bind", "patterns", "relations", "title"):
            if compose.get(key):
                block[key] = compose[key]
        record["compose"] = block
    record["parameters"] = parameters
    if overrides:
        record["overrides"] = overrides
    if exclude:
        record["exclude"] = exclude
    if extra:
        record["extra"] = extra
    return instance_id, record


def _scratch_model(model):
    """A copy of the loaded model that can take an expansion without the
    cache or the next request seeing it."""
    import copy

    twin = copy.copy(model)
    twin.entities = {t: dict(v) for t, v in model.entities.items()}
    twin.relations = {n: list(v) for n, v in model.relations.items()}
    twin.warnings = list(model.warnings)
    twin._adjacent = None
    return twin


def _expand_assembly(model, instance_id: str, record: dict):
    """The shape of one and its expansion, or the reason there is none, said
    in the panel's terms: a chunk and its answer, not a shape and its
    parameter."""
    try:
        if record.get("archetype"):
            shape = model.archetypes.get(str(record["archetype"]))
            if shape is None:
                raise ApiError("unknown shape %r" % record["archetype"], 404)
            if shape.applies_to != "products":
                raise ApiError("shape %s makes a %s, not a product" % (shape.archetype_id, shape.applies_to), 422)
        else:
            shape = inline_shape(REPO_ROOT, record, "products", model.archetypes.values())
        expansion = expand(record, shape, "products", _expansion_library())
    except (ComposeError, ArchetypeError, ModuleError, LibraryError) as exc:
        raise ApiError(_assembly_words(str(exc), record), 422)
    return shape, expansion


def _product_text(model, instance_id: str, record: dict, header=None) -> str:
    """The product file as the panel writes it: in its shape's terms when it
    is on one, as a `compose` block when it is not. A person's own note
    above the data survives; the house header is not repeated under
    itself."""
    values = {k: v for k, v in record.items() if k not in _ASSEMBLY_KEYS}
    shape_id = str(record.get("archetype") or "")
    if shape_id:
        shape = model.archetypes.get(shape_id)
        defaults = {s.name: (s.default or "none") for s in shape.slots} if shape else {}
        return shaped_text(
            "products", instance_id, values, shape_id, record.get("parameters") or {},
            choose=record.get("choose"), without=record.get("without") or (),
            modules=record.get("modules") or (), overrides=record.get("overrides"),
            exclude=record.get("exclude") or (), extra=record.get("extra"),
            header=header if header and list(header) != list(shaped_header(shape_id)) else None,
            slot_defaults=defaults, ids=record.get("ids"),
        )
    return assembled_text(
        "products", instance_id, values, record["compose"], record.get("parameters") or {},
        record.get("overrides"), record.get("exclude") or (), record.get("extra"),
        header=header if header and list(header) != list(ASSEMBLED_HEADER) else None,
    )


def _assembly_words(message: str, record: dict) -> str:
    """An expansion error names the shape of one and its parameter; the
    person reading it picked a chunk and left an answer blank."""
    match = re.search(r"requires parameter '([^']+)'", message)
    if match:
        name = match.group(1)
        try:
            modules = load_modules(REPO_ROOT)
        except ModuleError:
            modules = {}
        for entry in (record.get("compose") or {}).get("modules") or []:
            module = modules.get(str(entry.get("module")))
            if module and any(p.name == name for p in module.parameters):
                return "The %s chunk needs %s; fill it in on its card." % (module.name, name.replace("_", " "))
        return "The project needs %s before it can be drawn." % name.replace("_", " ")
    return message.replace("archetype compose:%s" % record.get("product_id", ""), "the assembly")


def api_assemble_preview(query, body) -> dict:
    """What a choice of chunks makes, before anything is written: the
    product's own architecture diagram over a scratch copy of the model,
    every entity it would create, the conflicts with what exists, and the
    file as it would be written."""
    instance_id, record = _assembly(body)
    model, views = _load_all()
    shape, expansion = _expand_assembly(model, instance_id, record)

    scratch = _scratch_model(model)
    # Saving over a product the panel made: it and what it generated come out
    # of the scratch first, so it is judged against the rest of the estate
    # and not against its own last expansion.
    replacing = str(body.get("replace") or "") == instance_id and model.find(instance_id) is not None
    if replacing:
        _drop_instance(scratch, instance_id)
    conflicts = []
    source = Path("10_MODEL/products/%s.yaml" % instance_id)
    if scratch.find(instance_id) is not None:
        conflicts.append(instance_id)
    else:
        scratch._add_entity(ENTITY_TYPES["products"], dict(expansion.instance), source)
    produced = []
    for type_name, records in expansion.entities.items():
        pk = ENTITY_TYPES[type_name].pk
        for produced_record in records:
            entity_id = str(produced_record.get(pk) or "")
            produced.append({
                "type": type_name,
                "id": entity_id,
                "name": str(produced_record.get("name") or ""),
                "description": str(produced_record.get("description") or ""),
                # The fields a small edit most often touches, with their
                # values, so the form can show what it would be changing.
                "fields": {k: v for k, v in produced_record.items()
                           if k in ("status", "criticality", "service_tier", "network_zone", "system_category",
                                    "protocol", "resilience", "data_classification", "data_classification_supported",
                                    "owner_org_id", "cloud_account", "region", "actor_kind", "interaction")},
                "fromChunk": _chunk_of(produced_record, shape),
            })
            if scratch.find(entity_id) is not None:
                conflicts.append(entity_id)
            else:
                scratch._add_entity(ENTITY_TYPES[type_name], dict(produced_record), source)
    for relation_name, rows in expansion.relations.items():
        for row in rows:
            try:
                scratch._add_relation(relation_name, dict(row), str(source))
            except ModelError:
                pass

    # No drawing while anything clashes: the view would pull the other
    # product's entities in under this one's name and draw a lie.
    graph = None
    graph_error = ""
    view, _from = _find_view(views, "product-architecture")
    if view is not None and not conflicts:
        try:
            bound = bind(view, {"product": instance_id}, scratch)
            graph = _graph_payload(scratch, bound, _palette(model, query))
            graph["viewId"] = "product-architecture"
            graph["title"] = "%s — Architecture, as assembled" % (record.get("name") or instance_id)
        except (ViewError, ApiError) as exc:
            graph_error = str(exc)

    text = _product_text(model, instance_id, record)
    if str(body.get("replace") or "") == instance_id:
        # The preview is the file that Save would write: the note above the
        # data and the comments beside it, as the save keeps them.
        found = model.find(instance_id)
        if found is not None:
            try:
                current_path, _current = _assembled_file(instance_id, found[1])
                current = current_path.read_text(encoding="utf-8")
                text = keep_comments(_product_text(model, instance_id, record, _leading_comment(current_path)), current)
            except (ApiError, OSError):
                pass
    shape_match = None if record.get("archetype") else _matching_shape(model, record["compose"])
    return {
        "id": instance_id,
        "archetype": str(record.get("archetype") or ""),
        "graph": graph,
        "graphError": graph_error,
        "produced": sorted(produced, key=lambda p: (_TYPE_ORDER.get(p["type"], 9), p["id"])),
        "relations": {name: len(rows) for name, rows in sorted(expansion.relations.items())},
        "counts": {
            "entities": len(produced),
            "relations": sum(len(r) for r in expansion.relations.values()),
            "byType": {t: len(r) for t, r in sorted(expansion.entities.items())},
        },
        "conflicts": sorted(set(conflicts)),
        "blocks": [dict(b) for b in shape.blocks],
        "patterns": list(expansion.instance.get("patterns") or []),
        "shapeMatch": shape_match,
        "replacing": replacing,
        "text": text,
        "path": str(source).replace("\\", "/"),
    }


_ASSEMBLY_KEYS = {
    "product_id", "compose", "parameters", "overrides", "exclude", "extra",
    "archetype", "choose", "without", "modules", "ids",
}
_TYPE_ORDER = {"systems": 0, "interfaces": 1, "data_assets": 2, "actors": 3, "tech_services": 4}


def _chunk_of(record: dict, shape) -> str:
    """Which part made a record, by the module alias the expansion noted,
    or blank for a block's own component."""
    return str(record.get("module") or "")


def _matching_shape(model, compose: dict) -> Optional[dict]:
    """The shipped shape whose parts, with its slots at their defaults, are
    exactly this choice: the assembly is that shape, and should say so."""
    try:
        modules = load_modules(REPO_ROOT)
    except ModuleError:
        return None
    chosen = set()
    for entry in compose.get("modules") or []:
        module = modules.get(str(entry.get("module")))
        if module is None:
            return None
        chosen.update(members_of(module, modules))
    provider = str(compose.get("provider") or "")
    for archetype in sorted(model.archetypes.values(), key=lambda a: a.archetype_id):
        if archetype.applies_to != "products" or str(archetype.provider or "") != provider:
            continue
        has = set()
        for entry in archetype.modules:
            module = modules.get(str(entry.get("module")))
            if module is not None:
                has.update(members_of(module, modules))
        for slot in archetype.slots:
            if slot.default and slot.default in modules:
                has.update(members_of(modules[slot.default], modules))
        if has and has == chosen:
            return {"id": archetype.archetype_id, "title": archetype.title}
    return None


def _leading_comment(path: Path) -> List[str]:
    """The comment a file opens with, without its `#`, so a rewrite can keep
    what a person wrote above the data."""
    lines: List[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return lines
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("#"):
            lines.append(line[1:].lstrip(" ") if line != "#" else "")
        elif not line.strip():
            if lines:
                lines.append("")
        else:
            break
    while lines and not lines[-1]:
        lines.pop()
    return lines


def _assembled_file(product_id: str, record: dict) -> Tuple[Path, dict]:
    """The file a product assembled from parts was written to, and the data
    in it. Refused, by name, for a product on a shape, one with no file of
    its own, or one that shares a file: the panel edits a `compose` block in
    a product's own file and nothing else."""
    source = record.get("_source_file")
    if not source:
        raise ApiError("%s has no file of its own" % product_id, 409)
    path = Path(str(source))
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.exists():
        raise ApiError("%s is recorded in %s, which is not there" % (product_id, source), 404)
    data = read_data_file(path)
    shared = isinstance(data, list)
    if shared:
        data = next((d for d in data if isinstance(d, dict) and str(d.get("product_id")) == product_id), None)
    if not isinstance(data, dict) or not (data.get("compose") or data.get("archetype")):
        raise ApiError(
            "%s is not assembled from parts, nor on a shape; the panel opens a product whose file "
            "says `compose:` or `archetype:`" % product_id, 422)
    if shared:
        raise ApiError(
            "%s lives in %s with other records; the panel opens a product that has a file of its own"
            % (product_id, Path(str(source)).as_posix()), 409)
    return path, data


def _drop_instance(scratch, instance_id: str) -> List[str]:
    """Take an assembled product and everything it generated out of a scratch
    model, so a re-assembly is judged against the rest of the estate and not
    against its own last expansion. Returns what went."""
    gone = set()
    for records in scratch.entities.values():
        for entity_id, record in list(records.items()):
            if entity_id == instance_id or record.get("archetype_instance") == instance_id:
                del records[entity_id]
                gone.add(entity_id)
    for name, rows in list(scratch.relations.items()):
        scratch.relations[name] = [
            row for row in rows
            if row.get("archetype_instance") != instance_id
            and not any(isinstance(value, str) and value in gone for value in row.values())
        ]
    scratch._adjacent = None
    return sorted(gone)


def _generated_by(model, instance_id: str) -> List[str]:
    """Every entity id an instance made, across the types."""
    return sorted(
        r[ENTITY_TYPES[t].pk] for t in ENTITY_TYPES for r in model.all_of(t)
        if r.get("archetype_instance") == instance_id
    )


def api_assemble_open(query, _body) -> dict:
    """A product assembled from parts, as the panel holds it, read from its
    own file: the chunks with their answers, the project's fields, the
    overrides and exclusions, and the comment the file opens with."""
    product_id = str((query.get("id") or [""])[0]).strip()
    model, _views = _load_all()
    found = model.find(product_id)
    if found is None:
        raise ApiError("unknown product %r" % product_id, 404)
    type_name, record = found
    if type_name != "products":
        raise ApiError("%s is a %s, not a product" % (product_id, ENTITY_TYPES[type_name].label), 422)
    path, data = _assembled_file(product_id, record)
    try:
        shown = path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        shown = path.as_posix()
    shape_id = str(data.get("archetype") or "")
    shape = model.archetypes.get(shape_id) if shape_id else None
    if shape_id and shape is None:
        raise ApiError("%s is on shape %s, which the model does not have" % (product_id, shape_id), 409)
    return {
        "id": product_id,
        "path": shown,
        "values": {k: v for k, v in data.items() if k not in _ASSEMBLY_KEYS},
        "archetype": shape_id,
        "shape": _shape_payload(shape) if shape else None,
        "choose": {str(k): str(v) for k, v in (data.get("choose") or {}).items()},
        "without": [str(x) for x in (data.get("without") or [])],
        "ids": {str(k): str(v) for k, v in (data.get("ids") or {}).items()},
        "modules": _module_items(data.get("modules")),
        "compose": dict(data.get("compose") or {}),
        "parameters": dict(data.get("parameters") or {}),
        "overrides": dict(data.get("overrides") or {}),
        "exclude": [str(x) for x in (data.get("exclude") or [])],
        "extra": data.get("extra") or None,
        "note": _leading_comment(path),
        "generated": _generated_by(model, product_id),
    }


def api_assemble_create(_query, body) -> dict:
    """Write the assembled project: one product file whose `compose` block
    names the parts, or -- when asked to keep the choice as a shape -- the
    shape in 20_ARCHETYPES and the product on it. Reloads and validates;
    nothing stays written if the model will not load."""
    instance_id, record = _assembly(body)
    save_shape = body.get("saveShape") or None
    if save_shape and record.get("archetype"):
        raise ApiError("%s is on shape %s already; there is no second shape to keep" % (instance_id, record["archetype"]), 422)
    # `replace` names the product the panel opened: saving over it is
    # allowed, and only for a product with a file of its own, written as an
    # assembly. Anything else is refused by name.
    replacing = str(body.get("replace") or "") == instance_id
    with _LOCK:
        model, _views = _load_all()
        existing = model.find(instance_id)
        if existing is not None and not replacing:
            raise ApiError("%s already exists" % instance_id, 409)
        product_path = _entity_path("products", instance_id)
        before: List[str] = []
        header: List[str] = []
        if replacing:
            if existing is None:
                raise ApiError("%s is not in the model, so there is nothing to save over" % instance_id, 409)
            current_path, _data = _assembled_file(instance_id, existing[1])
            if current_path.resolve() != product_path.resolve():
                raise ApiError(
                    "%s lives in %s; the panel rewrites only a product's own file"
                    % (instance_id, current_path.as_posix()), 409)
            header = _leading_comment(current_path)
            before = _generated_by(model, instance_id)
        shape, expansion = _expand_assembly(model, instance_id, record)
        for type_name, records in expansion.entities.items():
            pk = ENTITY_TYPES[type_name].pk
            for produced_record in records:
                entity_id = str(produced_record.get(pk) or "")
                clash = model.find(entity_id)
                if clash is not None and not (replacing and clash[1].get("archetype_instance") == instance_id):
                    raise ApiError(
                        "%s already exists; change the slug, or drop the chunk that makes it" % entity_id, 409
                    )

        written: List[Path] = []
        product_path.parent.mkdir(parents=True, exist_ok=True)
        if save_shape:
            shape_id = str(save_shape.get("id") or "").strip()
            if not SAFE_ID.match(shape_id):
                raise ApiError("a shape id must be an identifier: letters, digits, . _ -", 422)
            shape_path = _archetype_path(shape_id)
            if shape_path.exists() or shape_id in model.archetypes:
                raise ApiError("shape %s already exists" % shape_id, 409)
            compose = record["compose"]
            try:
                shape_text = archetype_text_from_parts(
                    REPO_ROOT,
                    archetype_id=shape_id,
                    title=str(save_shape.get("title") or shape_id),
                    description=str(save_shape.get("description") or
                                    "Kept from the assembly of %s: the parts and the landing zone it was built on."
                                    % instance_id),
                    parameters=[p.name for p in shape.parameters if p.name in {v["name"] for v in VOCABULARY}],
                    modules=compose.get("modules") or [],
                    blocks=[dict(b) for b in shape.blocks],
                    patterns=list(compose.get("patterns") or []),
                    provider=str(compose.get("provider") or "") or None,
                    bind=dict(compose.get("bind") or {}),
                )
            except (ComposeError, ModuleError, LibraryError) as exc:
                raise ApiError(str(exc), 422)
            shape_path.write_text(shape_text, encoding="utf-8")
            written.append(shape_path)
            # The product sits on the shape it just made: the same answers,
            # and whatever the shape does not carry stays on the instance.
            lines = ["# Created in the app: assembled from parts, and kept as shape %s." % shape_id]
            data: Dict[str, Any] = {"product_id": instance_id}
            data.update({k: v for k, v in record.items() if k not in _ASSEMBLY_KEYS})
            data["archetype"] = shape_id
            data["parameters"] = record.get("parameters") or {}
            for key in ("overrides", "exclude", "extra"):
                if record.get(key):
                    data[key] = record[key]
            product_text = "\n".join(lines) + "\n\n" + "\n".join(dump_yaml(data)) + "\n"
        else:
            product_text = _product_text(model, instance_id, record, header)
        previous = product_path.read_text(encoding="utf-8") if replacing and product_path.exists() else None
        if previous is not None and not save_shape:
            # What a person wrote beside the data stays beside it.
            product_text = keep_comments(product_text, previous)
        product_path.write_text(product_text, encoding="utf-8")
        written.append(product_path)

        try:
            model, views = _load_all()
        except (ModelError, ArchetypeError) as exc:
            for path in written:
                if path == product_path and previous is not None:
                    path.write_text(previous, encoding="utf-8")
                else:
                    path.unlink(missing_ok=True)
            raise ApiError(
                "the assembly did not load, nothing %s: %s" % ("changed" if replacing else "written", exc), 409)
        report = _report(model, views)
        created = [
            r[ENTITY_TYPES[t].pk]
            for t in ENTITY_TYPES
            for r in model.all_of(t)
            if r.get("archetype_instance") == instance_id
        ]
        removed = sorted(set(before) - set(created))
    return {
        "created": instance_id,
        "replaced": replacing,
        "removed": removed,
        "path": str(product_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "shape": str(save_shape.get("id")) if save_shape else None,
        "generated": sorted(created),
        "errors": [f.format() for f in report.errors],
        "warnings": len(report.warnings),
    }


def api_svg(query) -> str:
    """The view as the sheet the PNG button exports, drawn in Python rather
    than by the browser (`terrane.draw`). The same query as `/api/graph`, plus
    `plain=1` for the drawing without its title block and legend,
    `labels=on|off` to force the connection labels, `sheet=WxH` for the
    sheet the layout fits (a tile map wraps to its width and is as tall as
    it needs to be), and `fonts=embed` to carry Geist inside the file
    rather than name it from `web/fonts/`. The tile maps, the packed maps
    and the layered diagrams are drawn; a view the app lays out organically
    is refused with the reason rather than drawn differently, and a view
    the app would hand to ELK is drawn on the dagre path the app itself
    falls back to, which the sheet's `data-layout` says."""
    payload = api_graph(query, None)
    try:
        drawing_mode(payload)
    except Undrawable as exc:
        raise ApiError(str(exc), 409)
    sheet = (query.get("sheet") or ["1240x871.4375"])[0]
    try:
        width, height = (float(v) for v in sheet.lower().split("x"))
    except ValueError:
        raise ApiError("sheet must be WxH, like 1240x871", 400)
    labels_asked = (query.get("labels") or [""])[0]
    labels = True if labels_asked == "on" else False if labels_asked == "off" else None
    embed = (query.get("fonts") or [""])[0] == "embed"

    def font_loader(name: str):
        target = WEB_DIR / "fonts" / name
        return target.read_bytes() if target.is_file() else None

    try:
        return render_svg(
            payload, sheet_width=width, sheet_height=height, icon_loader=_icon_map().read,
            font_loader=font_loader if embed else None, font_url_prefix="" if embed else "/fonts/",
            sheet=(query.get("plain") or [""])[0] != "1", labels=labels,
            model_name=str(_load_all()[0].config.get("name") or "Architecture Model"),
        )
    except Undrawable as exc:
        # A ribbon is only known once it is laid out.
        raise ApiError(str(exc), 409)


# ---------------------------------------------------------------------------
# The canvas: a diagram drawn by placing things, saved as it is drawn.
# ---------------------------------------------------------------------------

#: The record kinds a library part can be placed as. A part for anything else
#: (an org unit, a control) is not a box on an architecture diagram.
_CANVAS_KINDS = ("systems", "tech_services")

#: The view whose accounts and zones the picker offers as boundaries of their
#: own: an account placed is that view kept to the account.
_NETWORK_VIEW = "network-topology"

_CANVAS_CACHE: Dict[str, Any] = {"model": None, "views": None, "placeable": None}


def _canvas_network(views) -> Optional[Any]:
    """The view an account or a zone is placed from: Network Topology where
    the estate draws it, else the first view boxed by cloud account."""
    by_id = {v.view_id: v for v in views}
    found = by_id.get(_NETWORK_VIEW)
    if found is not None and "cloud_account" in found.group_by:
        return found
    for view in views:
        if "cloud_account" in view.group_by and not view.parameters and not view.places:
            return view
    return None


def _fold_of(view, graph) -> dict:
    """What a placed view can leave out, one checkbox each: its accounts where
    it is boxed by account, else the values of its outermost boundary."""
    field = "cloud_account" if "cloud_account" in view.group_by else view.group_by[0]
    seen: Dict[str, dict] = {}
    for node in graph.nodes:
        value = str(node.record.get(field) or "")
        if field == "cloud_account":
            provider = str(node.record.get("cloud_provider") or "")
            label = " · ".join(p for p in (provider, value) if p) or "None"
        else:
            label = value or "None"
        entry = seen.setdefault(value, {"value": value, "label": label, "count": 0})
        entry["count"] += 1
    values = sorted(seen.values(), key=lambda e: (e["value"] == "", -e["count"], e["label"].lower()))
    return {"field": field, "words": _canvas_field_word(field), "values": values}


def _canvas_field_word(field: str) -> str:
    return {"cloud_account": "accounts", "cloud_provider": "clouds", "region": "regions",
            "availability_zone": "zones", "network_zone": "network zones",
            "company_domain": "domains"}.get(field, field.replace("_", " ") + "s")


def _canvas_views(model, views) -> List[dict]:
    """Every view that can be placed as a boundary: one that boxes what it
    draws, about the whole estate, and not itself a drawing of placed views.
    Resolved once per model, since the picker shows how much each holds."""
    # Held by the objects, not their ids: a model loaded again can be given
    # the address of the one it replaced.
    if _CANVAS_CACHE["model"] is model and _CANVAS_CACHE["views"] is views:
        return _CANVAS_CACHE["placeable"]
    out = []
    for view in views:
        if not view.group_by or view.parameters or view.places or view.kind == "report":
            continue
        if "type" in view.group_by:
            continue
        try:
            graph = resolve(model, view)
        except ViewError:
            continue
        fold = _fold_of(view, graph)
        out.append({
            "id": view.view_id, "title": view.title, "category": view.category, "section": view.section,
            "kind": view.kind, "nodes": len(graph.nodes), "groupBy": list(view.group_by), "fold": fold,
            "types": sorted({n.entity_type for n in graph.nodes}),
        })
    _CANVAS_CACHE.update({"model": model, "views": views, "placeable": out})
    return out


def api_canvas_parts(_query, _body) -> dict:
    """What the canvas's picker offers: the library's parts, each placed as a
    new record, and what the estate already has: views placed as boundaries,
    an account or a network zone as Network Topology kept to it, a system
    placed as it is."""
    model, views = _load_all()
    components = load_components(REPO_ROOT)
    parts = []
    for component in components.values():
        if component.applies_to not in _CANVAS_KINDS or component.replaced:
            continue
        parts.append({
            "id": component.component_type_id, "name": component.name, "category": component.category,
            "type": component.applies_to, "typeLabel": ENTITY_TYPES[component.applies_to].label,
            "description": component.description,
        })
    # Systems first: a diagram is mostly what runs, and the platform parts
    # it runs on are a search away.
    parts.sort(key=lambda p: (p["type"] != "systems", p["category"].lower(), p["name"].lower()))
    placeable = _canvas_views(model, views)
    network = _canvas_network(views)
    accounts: List[dict] = []
    zones: List[dict] = []
    if network is not None:
        listed = [v for v in placeable if v["id"] == network.view_id]
        if listed and listed[0]["fold"]["field"] == "cloud_account":
            accounts = [dict(v) for v in listed[0]["fold"]["values"] if v["value"]]
        counted: Dict[str, int] = {}
        try:
            for node in resolve(model, network).nodes:
                zone = str(node.record.get("network_zone") or "")
                if zone:
                    counted[zone] = counted.get(zone, 0) + 1
        except ViewError:
            pass
        zones = [{"value": z, "count": n} for z, n in sorted(counted.items(), key=lambda kv: (-kv[1], kv[0]))]
    systems = [
        {"id": str(r["system_id"]), "name": str(r.get("name") or r["system_id"]),
         "domain": str(r.get("company_domain") or ""), "status": str(r.get("status") or "")}
        for r in sorted(model.all_of("systems"), key=lambda r: str(r.get("name") or "").lower())
    ]
    return {
        "parts": parts,
        "views": placeable,
        "network": network.view_id if network is not None else None,
        "networkTitle": network.title if network is not None else None,
        "accounts": accounts,
        "zones": zones,
        "systems": systems,
        "counts": {"systems": len(systems), "views": len(placeable), "parts": len(parts)},
        "categories": [c for c in VIEW_CATEGORIES if c != "Other"],
    }


#: A new diagram's file, in the order a person would write it.
_CANVAS_ORDER = ("view_id", "title", "description", "category", "section", "kind", "places", "layout",
                 "node_label", "group_by", "scope", "edges", "style", "limits")


def _canvas_ordered(data: dict) -> dict:
    out = {k: data[k] for k in _CANVAS_ORDER if k in data and data[k] not in (None, "", [], {})}
    for key, value in data.items():
        if key not in out and key != "positions" and value not in (None, "", [], {}):
            out[key] = value
    # Positions last, after anything the file had of its own: the longest
    # part, and the one a reader of the file looks at least. In key order,
    # so the lines of one boundary sit together and a save moves none.
    if data.get("positions"):
        out["positions"] = {k: data["positions"][k] for k in sorted(data["positions"])}
    return out


def _canvas_id(title: str, views) -> str:
    """A new diagram's id from its title, unused by any view here or shipped."""
    from terrane.blocks import slug as block_slug

    base = block_slug(title or "") or "diagram"
    taken = {v.view_id for v in views}
    candidate, n = base, 2
    while candidate in taken or (REPO_ROOT / "30_VIEWS" / (candidate + VIEW_SUFFIX)).exists():
        candidate, n = "%s-%d" % (base, n), n + 1
    return candidate


def api_canvas_save(_query, body) -> dict:
    """Write the diagram on the canvas: a new file the first time something
    is placed on it, and after that the same file rewritten by value, so a
    comment someone added to it by hand stays. Refused, and nothing kept,
    when it places a view that is not here."""
    data = body.get("data")
    view_id = str(body.get("id") or "").strip()
    if not isinstance(data, dict):
        raise ApiError("a diagram is a mapping of fields", 422)
    data = {k: v for k, v in data.items() if v not in (None,)}
    if not data.get("scope"):
        data.pop("scope", None)
    with _LOCK:
        model, views = _load_all()
        created = not view_id
        if created:
            view_id = _canvas_id(str(data.get("title") or ""), views)
        data["view_id"] = view_id
        try:
            view = parse_view(data)
        except ViewError as exc:
            raise ApiError(str(exc), 422)
        by_id = {(v.own or v).view_id: (v.own or v) for v in views}
        wrong = places_module.problems(view, by_id)
        if wrong:
            raise ApiError("this diagram %s" % "; ".join(wrong), 422)
        if created:
            path = _view_path(view_id)
            old = None
            _write_text(path, yaml_text(_canvas_ordered(data)))
        else:
            _shipped_only(view_id)
            path = _existing_view_file(view_id)
            if path is None:
                raise ApiError("unknown view %r" % view_id, 404)
            old = path.read_text(encoding="utf-8-sig")
            _write_text(path, records_module.rewrite(old, _canvas_ordered(data)))
        try:
            model, views = _load_all()
        except (ModelError, ArchetypeError, ViewError, ModelFileError) as exc:
            if old is None:
                path.unlink()
            else:
                _write_text(path, old)
            raise ApiError("saving that would break the model: %s" % exc, 409)
        report = _report(model, views)
    return {
        "id": view_id,
        "path": path.relative_to(REPO_ROOT).as_posix(),
        "created": created,
        "data": data,
        "errors": [f.format() for f in report.errors if view_id in f.message],
    }


def api_canvas_record(_query, body) -> dict:
    """A new record from a library part, placed where it was dropped: the
    part's defaults, the fields of every boundary it was dropped into, and
    nothing guessed. What the kind of record must have and the drop did not
    say (an owner, a criticality) is left empty and listed, so the person
    is asked rather than told a default they never chose."""
    part = str(body.get("part") or "").strip()
    into = body.get("into") or []
    components = load_components(REPO_ROOT)
    component = components.get(part)
    if component is None:
        raise ApiError("unknown library part %r" % part, 404)
    type_name = component.applies_to
    if type_name not in _CANVAS_KINDS:
        raise ApiError("%s is a part for %s, which is not drawn as a box" % (component.name, type_name), 422)
    entity_type = ENTITY_TYPES[type_name]
    fields = {f.name: f for f in entity_type.fields}
    values: Dict[str, Any] = {}
    for key, value in (component.defaults or {}).items():
        if key in fields:
            values[key] = value
    if "component_type" in fields:
        values["component_type"] = component.component_type_id
    if "status" in fields:
        values["status"] = "Planned"
    for step in into if isinstance(into, list) else []:
        if not isinstance(step, dict):
            continue
        field, value = str(step.get("field") or ""), step.get("value")
        if field in fields and value not in (None, ""):
            values[field] = value
    from terrane.inventory import slug as id_slug
    from terrane.sources import id_prefix

    with _LOCK:
        model, _views = _load_all()
        names = {str(r.get("name") or "").lower() for r in model.all_of(type_name)}
        name = str(body.get("name") or "").strip() or component.name
        stem, n = name, 2
        while name.lower() in names:
            name, n = "%s %d" % (stem, n), n + 1
        values["name"] = name
        prefix = id_prefix(model, type_name)
        entity_id, n = prefix + id_slug(name), 2
        while model.find(entity_id) is not None or _entity_path(type_name, entity_id).exists():
            entity_id, n = "%s%s-%d" % (prefix, id_slug(name), n), n + 1
        path = _write_entity(type_name, entity_id, values)
        try:
            model, views = _load_all()
        except (ModelError, ArchetypeError, ViewError, ModelFileError) as exc:
            path.unlink()
            raise ApiError("adding that would break the model: %s" % exc, 409)
        report = _report(model, views)
    missing = [f.name for f in entity_type.fields if f.required and values.get(f.name) in (None, "")]
    return {
        "id": entity_id,
        "type": type_name,
        "name": name,
        "part": component.name,
        "path": path.relative_to(REPO_ROOT).as_posix(),
        "missing": missing,
        "errors": [f.format() for f in report.errors if entity_id in f.message],
    }


# ---- what the diagrams need ---------------------------------------------------
# Each view reads fields: the ones its scope selects by, boxes by, draws its
# lines along and shades by (`terrane/needs.py`). A diagram that draws nothing or
# draws thin says which, and how many records lack each; the one list says
# it across every diagram, and a field is set on many records at once
# through the same save that changes one, each where it lives.

#: What the bulk editor shows beside a record's name, per kind of record:
#: the fields a person decides a value from.
_NEED_CONTEXT = {
    "systems": ("hosting", "owner_org_id", "system_category", "criticality", "status"),
    "tech_services": ("cloud_provider", "cloud_account", "service_category", "status"),
    "data_assets": ("classification", "source_of_truth", "status"),
    "org_units": ("parent_org_id", "status"),
    "capabilities": ("capability_level", "capability_tier", "status"),
    "processes": ("value_stream_id", "criticality", "status"),
    "interfaces": ("source_system_id", "target_system_id", "status"),
}


def _need_json(need) -> dict:
    return {
        "type": need.type, "field": need.field, "kind": need.kind, "roles": list(need.roles),
        "asked": need.asked, "lacking": len(need.lacking), "byRole": dict(need.by_role),
        "settable": need.settable, "values": [{"value": v, "label": l} for v, l in need.values],
        "has": ENTITY_TYPES[need.type].label if need.type in ENTITY_TYPES else need.type,
    }


def _view_needs(model, view, subject: str = "") -> dict:
    result = needs_module.needs_of(model, view, subject=subject)
    return {
        "viewId": result.view_id, "title": result.title, "category": result.category, "kind": result.kind,
        "subject": result.subject, "state": result.state, "drawn": result.drawn,
        "keptOff": len(result.kept_off), "problem": result.problem,
        "needs": [_need_json(n) for n in result.needs],
    }


def _bound(model, views, view_id: str, query) -> Tuple[Any, str]:
    """A view by id, bound to the subject asked for (`p_<name>`) or the one
    `render_for` picks first, as `api_graph` binds it."""
    view, supplied = _find_view(views, view_id)
    if view is None:
        raise ApiError("unknown view %r" % view_id, 404)
    if not view.parameters:
        return view, ""
    supplied = dict(supplied)
    for p in view.parameters:
        asked = (query.get("p_" + p.name) or [""])[0]
        if asked:
            supplied[p.name] = asked
    for parameter, value in render_targets(model, view):
        supplied.setdefault(parameter, "")
        if not supplied[parameter]:
            supplied[parameter] = value
    subject = supplied.get(view.parameters[0].name, "")
    if not subject:
        return view, ""
    try:
        return bind(view, supplied, model), subject
    except ViewError as exc:
        raise ApiError(str(exc), 400)


def api_needs_view(query, _body) -> dict:
    """What one diagram needs, as drawn: for the brief beside it, and for
    the empty sheet of one that draws nothing."""
    model, views = _load_all()
    view, subject = _bound(model, views, (query.get("view") or [""])[0], query)
    return _view_needs(model, view, subject)


def api_needs(_query, _body) -> dict:
    """The one list: every field the diagrams read and how many records lack
    it, the kinds of record the estate has none of, and the lines."""
    model, views = _load_all()
    results = needs_module.estate_needs(model, views)
    listed = needs_module.by_field(model, results, views)
    none: Dict[str, List[dict]] = {}
    fields, lines = [], []
    for need in listed:
        row = {
            "type": need.type, "field": need.field, "kind": need.kind,
            "lacking": len(need.lacking), "asked": need.asked, "settable": need.settable,
            "values": [{"value": v, "label": l} for v, l in need.values],
            "views": [{"viewId": v, "title": t, "roles": list(r), "lacking": n} for v, t, r, n in need.views],
        }
        if not model.all_of(need.type):
            seen = none.setdefault(need.type, [])
            for v in row["views"]:
                if v["viewId"] not in [s["viewId"] for s in seen]:
                    seen.append({"viewId": v["viewId"], "title": v["title"]})
        elif need.kind == "relation":
            if need.lacking:
                lines.append(row)
        elif need.lacking:
            fields.append(row)
    return {
        "states": needs_module.states(results),
        "views": [{"viewId": r.view_id, "title": r.title, "category": r.category, "state": r.state,
                   "drawn": r.drawn, "keptOff": len(r.kept_off)} for r in results],
        "fields": fields,
        "none": [{"type": t, "label": ENTITY_TYPES[t].label, "views": v}
                 for t, v in sorted(none.items(), key=lambda kv: (-len(kv[1]), kv[0]))],
        "lines": lines,
    }


def _said_value(model, type_name: str, field: str, value) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    spec = next((f for f in ENTITY_TYPES[type_name].fields if f.name == field), None)
    if spec is not None and spec.ref:
        found = model.get(spec.ref, str(value))
        if found and found.get("name"):
            return str(found["name"])
    return str(value)


def api_needs_records(query, _body) -> dict:
    """The records lacking one field, for setting it on many at once: on one
    diagram when a view is named, across every diagram otherwise; each with
    the fields a person decides the value from, and whether it can be
    changed here."""
    model, views = _load_all()
    type_name = (query.get("type") or [""])[0]
    field = (query.get("field") or [""])[0]
    if type_name not in ENTITY_TYPES:
        raise ApiError("unknown entity type %r" % type_name)
    view_id = (query.get("view") or [""])[0]
    lanes = None
    if view_id:
        view, subject = _bound(model, views, view_id, query)
        result = needs_module.needs_of(model, view, subject=subject)
        found = [n for n in result.needs if n.type == type_name and n.field == field]
        lanes = view.lanes.get(field)
        reading = [{"viewId": result.view_id, "title": result.title, "roles": list(found[0].roles)}] if found else []
    else:
        results = needs_module.estate_needs(model, views)
        found = [n for n in needs_module.by_field(model, results, views) if n.type == type_name and n.field == field]
        reading = [{"viewId": v, "title": t, "roles": list(r)} for v, t, r, _n in found[0].views] if found else []
        lanes = next((v.lanes.get(field) for v in views if v.lanes.get(field)), None)
    if not found:
        raise ApiError("no diagram reads %s on %s" % (field, ENTITY_TYPES[type_name].label), 404)
    need = found[0]
    if not need.settable:
        raise ApiError("%s is a relation, drawn by connecting two records rather than set on one" % field, 422)
    context = [c for c in _NEED_CONTEXT.get(type_name, ("status",)) if c != field
               and any(f.name == c for f in ENTITY_TYPES[type_name].fields)]
    rows = []
    for entity_id in need.lacking:
        record = model.get(type_name, entity_id)
        if record is None:
            continue
        home = records_module.home_of(type_name, record)
        rows.append({
            "id": entity_id, "name": str(record.get("name") or entity_id),
            "context": {c: _said_value(model, type_name, c, record.get(c)) for c in context},
            "has": _said_value(model, type_name, field, record.get(field)),
            "editable": home.kind not in ("generated", "imported"),
            "why": home.note if home.kind in ("generated", "imported") else "",
            "moves": home.kind == "harvested",
        })
    spec = next((f for f in ENTITY_TYPES[type_name].fields if f.name == field), None)
    values = needs_module.values_of(model, type_name, field, lanes) if need.kind == "field" else need.values
    return {
        "type": type_name, "label": ENTITY_TYPES[type_name].label, "field": field, "kind": need.kind,
        "values": [{"value": v, "label": l} for v, l in values],
        "free": bool(spec is not None and not spec.enum and not spec.ref and need.kind == "field"),
        "context": context, "records": rows, "asked": need.asked, "reading": reading,
    }


#: The last batch of records set on many at once, so it can be put back:
#: each file's text before and after, keyed by a token the app holds.
_BATCHES: Dict[str, Dict[str, Any]] = {}


def api_records_set(_query, body) -> dict:
    """One field set on many records, each changed where it lives, written
    together and put back together if the model does not load after."""
    import secrets

    type_name = str(body.get("type") or "")
    field = str(body.get("field") or "")
    ids = [str(i) for i in (body.get("ids") or []) if str(i).strip()]
    if not ids:
        raise ApiError("no records chosen")
    with _LOCK:
        model, _views = _load_all()
        try:
            batch = records_module.set_many(model, REPO_ROOT, type_name, ids, field, body.get("value"))
        except records_module.Refused as exc:
            raise ApiError(str(exc), 422)
        # The bytes as they were, so Undo puts back a file's line endings
        # too: an import on Windows writes CRLF, and the app writes LF.
        raw = {str(p): (p.read_bytes() if old is not None else None) for p, (old, _new) in batch.files.items()}
        touched = _write_planned(batch.files)
        try:
            model, views = _load_all()
        except (ModelError, ArchetypeError, ViewError, ModelFileError) as exc:
            _restore(touched)
            raise ApiError("setting that would break the model: %s" % exc, 409)
        report = _report(model, views)
        token = secrets.token_hex(8)
        _BATCHES.clear()
        _BATCHES[token] = {"files": {str(p): (raw[str(p)], new) for p, (_old, new) in batch.files.items()}}
    return {
        "changed": batch.changed, "moved": batch.moved, "unchanged": batch.unchanged,
        "refused": [{"id": i, "why": w} for i, w in batch.refused],
        "files": len(batch.files), "undo": token if batch.files else None,
        "errors": [f.format() for f in report.errors],
    }


def api_records_undo(_query, body) -> dict:
    """The last batch put back, file by file, as long as nothing has changed
    the files since; one that has is named and left as it is."""
    with _LOCK:
        batch = _BATCHES.get(str(body.get("token") or ""))
        if batch is None:
            raise ApiError("there is nothing to undo now", 410)
        changed_since = []
        for name, (_old, new) in batch["files"].items():
            path = Path(name)
            now = path.read_text(encoding="utf-8-sig") if path.exists() else None
            if now != new:
                changed_since.append(path.name)
        if changed_since:
            raise ApiError("%s changed since; nothing was put back" % ", ".join(sorted(changed_since)), 409)
        for name, (old, _new) in batch["files"].items():
            path = Path(name)
            if old is None:
                path.unlink()
            else:
                path.write_bytes(old)
        _BATCHES.clear()
        model, views = _load_all()
        report = _report(model, views)
    return {"restored": len(batch["files"]), "errors": [f.format() for f in report.errors]}


# ---- estates ----------------------------------------------------------------
# The app opens one estate at a time and can open another without a restart:
# everything here reads REPO_ROOT when it is called, so opening one is
# setting it. Starting one is `terrane init` and joining one `terrane
# connect`, the engine's own functions, not a copy of them.

#: The checkout the app runs from, whatever estate it has open.
CHECKOUT_ROOT = REPO_ROOT


def _estate_card(root: Path) -> dict:
    config = read_data_file(root / "10_MODEL" / "model.yaml") or {}
    config = config if isinstance(config, dict) else {}
    return {
        "path": str(root), "folder": root.name,
        "name": str(config.get("name") or root.name),
        "sample": bool(config.get("sample_estate")),
        "current": root.resolve() == REPO_ROOT.resolve(),
    }


def _is_estate(root: Path) -> bool:
    return (root / "10_MODEL" / "model.yaml").is_file()


def api_estates(_query, _body) -> dict:
    """This estate and the ones that ship with the checkout; the app adds
    those this browser has opened before."""
    known = [REPO_ROOT, CHECKOUT_ROOT, CHECKOUT_ROOT / "90_EXAMPLE" / "thurman-health"]
    out, seen = [], set()
    for root in known:
        key = str(root.resolve()).lower()
        if key in seen or not _is_estate(root):
            continue
        seen.add(key)
        out.append(_estate_card(root))
    return {"estates": out, "suggest": str(CHECKOUT_ROOT.parent)}


def _open(root: Path) -> dict:
    """Open an estate in place of this one, or refuse with why and keep the
    one that is open."""
    global REPO_ROOT
    root = Path(root).expanduser()
    if not root.is_absolute():
        raise ApiError("an estate's folder is a whole path, such as C:\\dev\\estates\\northwind", 422)
    if not _is_estate(root):
        raise ApiError("%s holds no estate (no 10_MODEL/model.yaml)" % root, 404)
    previous = REPO_ROOT
    REPO_ROOT = root.resolve()
    try:
        model, views = _load_all()
    except Exception as exc:  # noqa: BLE001 -- an estate that does not load is not opened
        REPO_ROOT = previous
        raise ApiError("%s does not load: %s" % (root, exc), 409)
    entities = sum(len(v) for v in model.entities.values())
    return dict(_estate_card(REPO_ROOT), records=entities, views=len(views))


def api_estate_open(_query, body) -> dict:
    with _LOCK:
        return _open(Path(str(body.get("path") or "").strip()))


def api_estate_start(_query, body) -> dict:
    """An empty estate in a folder of its own, as `terrane init` makes it,
    opened."""
    from terrane import __version__
    from terrane.estate import InitError, init_estate

    name = " ".join(str(body.get("name") or "").split())
    folder = Path(str(body.get("folder") or "").strip()).expanduser()
    if not name:
        raise ApiError("an estate has a name", 422)
    if not str(folder) or not folder.is_absolute():
        raise ApiError("the folder is a whole path, such as C:\\dev\\estates\\northwind", 422)
    if folder.exists() and any(folder.iterdir()) and not (folder / ".git").exists():
        raise ApiError("%s already holds files; an estate starts in an empty folder or a fresh clone" % folder, 409)
    with _LOCK:
        try:
            written, kept = init_estate(folder, name, __version__)
        except InitError as exc:
            raise ApiError(str(exc), 409)
        opened = _open(folder)
    opened["written"] = [p.relative_to(folder).as_posix() for p in written]
    opened["kept"] = [p.relative_to(folder).as_posix() for p in kept]
    return opened


def api_estate_join(_query, body) -> dict:
    """A clone of an estate's repository and the governance it pins, as
    `terrane connect` makes them, opened. Git signs in, through its own
    credential manager; nothing here holds a password."""
    from terrane.workspace import WorkspaceError, _name_of, connect

    url = str(body.get("url") or "").strip()
    into = Path(str(body.get("into") or "").strip()).expanduser()
    if not url:
        raise ApiError("the repository's address, as its page gives it for cloning", 422)
    if not str(into) or not into.is_absolute():
        raise ApiError("the folder to clone into is a whole path, such as C:\\dev\\estates", 422)
    with _LOCK:
        try:
            done = connect(url, into=into / _name_of(url))
        except WorkspaceError as exc:
            raise ApiError(str(exc), 409)
        opened = _open(done.root)
    opened["notes"] = list(done.notes)
    opened["cloned"] = bool(done.cloned)
    return opened


ROUTES: Dict[Tuple[str, str], Callable] = {
    ("POST", "/api/archetype/compose"): api_archetype_compose,
    ("GET", "/api/canvas/parts"): api_canvas_parts,
    ("POST", "/api/canvas/save"): api_canvas_save,
    ("POST", "/api/canvas/record"): api_canvas_record,
    ("GET", "/api/compose/options"): api_compose_options,
    ("GET", "/api/chunks"): api_chunks,
    ("POST", "/api/assemble/preview"): api_assemble_preview,
    ("POST", "/api/assemble/create"): api_assemble_create,
    ("GET", "/api/assemble/open"): api_assemble_open,
    ("POST", "/api/sketch/view"): api_sketch_view,
    ("POST", "/api/sketch/module"): api_sketch_module,
    ("POST", "/api/module/save"): api_module_save,
    ("GET", "/api/overview"): api_overview,
    ("GET", "/api/needs"): api_needs,
    ("GET", "/api/needs/view"): api_needs_view,
    ("GET", "/api/needs/records"): api_needs_records,
    ("POST", "/api/records/set"): api_records_set,
    ("POST", "/api/records/undo"): api_records_undo,
    ("GET", "/api/estates"): api_estates,
    ("POST", "/api/estate/open"): api_estate_open,
    ("POST", "/api/estate/start"): api_estate_start,
    ("POST", "/api/estate/join"): api_estate_join,
    ("GET", "/api/sources"): api_sources,
    ("GET", "/api/project"): api_project,
    ("POST", "/api/project/guard"): api_project_guard,
    ("POST", "/api/sources/read"): api_sources_read,
    ("POST", "/api/sources/words"): api_sources_words,
    ("POST", "/api/sources/preview"): api_sources_preview,
    ("POST", "/api/sources/bring-in"): api_sources_bring_in,
    ("POST", "/api/sources/discard"): api_sources_discard,
    ("GET", "/api/schema"): api_schema,
    ("GET", "/api/graph"): api_graph,
    ("GET", "/api/entity"): api_entity,
    ("GET", "/api/focus"): api_focus,
    ("GET", "/api/source"): api_source,
    ("GET", "/api/view"): api_view,
    ("GET", "/api/connect/options"): api_connect_options,
    ("POST", "/api/regroup/options"): api_regroup_options,
    ("POST", "/api/view/preview"): api_view_preview,
    ("POST", "/api/view/save"): api_view_save,
    ("POST", "/api/view/delete"): api_view_delete,
    ("POST", "/api/view/membership"): api_view_membership,
    ("POST", "/api/view/compose"): api_view_compose,
    ("GET", "/api/archetype"): api_archetype,
    ("POST", "/api/archetype/preview"): api_archetype_preview,
    ("POST", "/api/archetype/save"): api_archetype_save,
    ("POST", "/api/archetype/delete"): api_archetype_delete,
    ("GET", "/api/entity/source"): api_entity_source,
    ("GET", "/api/table"): api_table,
    ("GET", "/api/coverage"): api_coverage,
    ("GET", "/api/diff"): api_diff,
    ("GET", "/api/log"): api_log,
    ("GET", "/api/cmdb/drift"): api_cmdb_drift,
    ("GET", "/api/library"): api_library,
    ("POST", "/api/block/preview"): api_block_preview,
    ("POST", "/api/block/add"): api_block_add,
    ("POST", "/api/entity/source/save"): api_entity_source_save,
    ("GET", "/api/impact"): api_impact,
    ("GET", "/api/flows"): api_flows,
    ("GET", "/api/relations"): api_relations,
    ("POST", "/api/relate"): api_relate,
    ("POST", "/api/unrelate"): api_unrelate,
    ("GET", "/api/list"): api_list,
    ("GET", "/api/validate"): api_validate,
    ("POST", "/api/save"): api_save,
    ("POST", "/api/delete"): api_delete,
    ("POST", "/api/instantiate"): api_instantiate,
    ("POST", "/api/render"): api_render,
    ("POST", "/api/import"): api_import,
}


class Handler(BaseHTTPRequestHandler):
    server_version = "terrane-app"

    def log_message(self, fmt, *args):  # noqa: A003
        sys.stderr.write("[terrane-app] %s\n" % (fmt % args))

    def _send(self, status: int, payload: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        # Never cache. This is a local tool whose files change under the user's
        # hands; a cached app.js means an edit appears to do nothing, which is
        # far more expensive than re-reading a few hundred kilobytes.
        self.send_header("Cache-Control", "no-store, must-revalidate")
        # Everything the page needs is served from here. No outbound anything.
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'none'",
        )
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    def _json(self, status: int, data: Any) -> None:
        self._send(status, json.dumps(data).encode("utf-8"), "application/json; charset=utf-8")

    def _handle(self, method: str) -> None:
        parsed = urlparse(self.path)
        # The one answer that is not JSON: a picture.
        if method == "GET" and parsed.path == "/api/svg":
            try:
                svg = api_svg(parse_qs(parsed.query))
            except ApiError as exc:
                self._json(exc.status, {"error": exc.message})
                return
            except (ModelError, ViewError) as exc:
                self._json(409, {"error": str(exc)})
                return
            self._send(200, svg.encode("utf-8"), "image/svg+xml; charset=utf-8")
            return
        route = ROUTES.get((method, parsed.path))
        if route is not None:
            try:
                body = {}
                if method == "POST":
                    length = int(self.headers.get("Content-Length") or 0)
                    if length:
                        body = json.loads(self.rfile.read(length).decode("utf-8"))
                self._json(200, route(parse_qs(parsed.query), body))
            except ApiError as exc:
                self._json(exc.status, {"error": exc.message})
            except (ModelError, ArchetypeError, ViewError, importer.ImportError_) as exc:
                self._json(409, {"error": str(exc)})
            except Exception as exc:  # noqa: BLE001
                traceback.print_exc()
                self._json(500, {"error": "%s: %s" % (type(exc).__name__, exc)})
            return
        if method == "POST":
            self._json(404, {"error": "no such endpoint"})
            return
        self._serve_static(parsed.path)

    def _serve_static(self, path: str) -> None:
        rel = unquote(path).lstrip("/") or "index.html"
        target = (WEB_DIR / rel).resolve()
        try:
            target.relative_to(WEB_DIR.resolve())
        except ValueError:
            self._json(403, {"error": "forbidden"})
            return
        if target.is_dir() or not target.exists():
            self._json(404, {"error": "not found"})
            return
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"
        body = target.read_bytes()
        if target.suffix == ".svg" and "icons" in target.relative_to(WEB_DIR.resolve()).parts:
            body = icons_module.sized(body)
        self._send(200, body, ctype)

    def do_GET(self):  # noqa: N802
        self._handle("GET")

    def do_HEAD(self):  # noqa: N802
        self._handle("GET")

    def do_POST(self):  # noqa: N802
        self._handle("POST")


def main(argv: Optional[List[str]] = None) -> int:
    global REPO_ROOT
    parser = argparse.ArgumentParser(description="Architecture model app (local).")
    parser.add_argument("--port", type=int, default=8020)
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="loopback by default; there is no authentication here",
    )
    parser.add_argument(
        "--root",
        help="the model to open, as `terrane --root` takes it (defaults to this checkout); "
        "90_EXAMPLE/thurman-health is the second example estate",
    )
    args = parser.parse_args(argv)
    if args.root:
        # An estate kept inside the repository is a root of its own -- its
        # model and its views -- served by this checkout's engine and app.
        # Everything the server reads or writes is found from REPO_ROOT at
        # call time, so naming the root here is the whole of it.
        REPO_ROOT = Path(args.root).resolve()

    # The hints below name the installed command and no folder of the
    # repository's: this file ships inside the package and is started by
    # `terrane app`, and the note for an empty model once sent a pip user
    # to `../90_EXAMPLE/csv`, which only a clone has.
    try:
        model, views = _load_all()
    except Exception as exc:  # noqa: BLE001
        print("The model did not load: %s" % exc, file=sys.stderr)
        print("Run `terrane validate` in %s for what to fix, then start the app again." % REPO_ROOT,
              file=sys.stderr)
        return 1

    entities = sum(len(v) for v in model.entities.values())
    print("Architecture model app")
    print("  estate  %s" % REPO_ROOT)
    print("  model   %d entities, %d views" % (entities, len(views)))
    if not entities:
        print("  note    the model is empty. Bring in an inventory with Import in the app, or in")
        print("          the estate's folder with `terrane adopt <a spreadsheet>` or")
        print("          `terrane import csv --from <a folder of CSVs>`.")
        print("  sample  an inventory to try it with:")
        print("          %s" % sample_inventory())
    print("")
    print("  http://%s:%d" % (args.host, args.port))
    print("")
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
