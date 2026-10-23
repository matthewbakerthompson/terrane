"""What changed since a revision, as a picture.

`terrane diff` says what moved between two revisions in the model's own terms,
as a page; this draws it. The things added since the revision are drawn in
full, the things removed are drawn dashed in red (they are put back into a
scratch copy of the later model for the drawing, since a picture of what is
gone has to hold it), the things changed get a heavy border, and what is
there unchanged one hop away is faded, so the change reads against its
surroundings: the new system beside the ones it calls, the retired one
still showing where it sat. A line added is drawn in full, a line
removed dashed, and a line that changed, a connection whose protocol or
kind moved, heavy. With a view named, the same marks go on that view instead
of the change-scoped one, so a reviewer sees the application landscape as
it is now with what moved standing out.

The same painter as every other picture, and a hop out along the
structural relations as the adoption picture takes, so the two change
pictures read alike: what a file would add, and what a commit did. The hop
is counted off the rows by hand, from what was added or removed and from
nothing else: a view's expand clauses compound, each hop taken from the
set the one before grew, and a reviewer's one new line to the ledger drew
seventy boxes when the clause hopped on from the ledger. A thing that
changed is drawn where it is with no neighbors of its own, as the adoption
picture draws a corrected one, since the changed thing may be the hub.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .diff import Diff, DiffError, diff, export_revision, snapshot
from .model import ModelError, load
from .pictures import scratch_model
from .schema import ENTITY_TYPES, RELATION_TYPES

#: The hop out from what changed: the structural relations only. The
#: adoption picture reaches along ten, since a sketch adds a handful of
#: things; a change to a hub system reaches forty processes along
#: `process_uses_system` alone, and the picture of one rename was a
#: hundred and forty boxes.
REACH = (
    ("interfaces", ["systems"]),
    ("actor_uses_system", ["actors", "systems"]),
    ("system_reads_writes", ["systems", "data_assets"]),
    ("system_uses_tech_service", ["systems", "tech_services"]),
    ("product_includes_system", ["products", "systems"]),
)
#: The ink of a thing that is gone.
REMOVED = "#dc2626"
#: The border of a thing that changed.
CHANGED_WIDTH = 3.0
#: Things drawn as lines or not drawn at all, which are never boxes on
#: the picture: an interface is a line, an org unit a boundary's name.
NOT_BOXES = ("interfaces", "org_units")


def _edge_keys(rows_by_relation: Dict[str, List[Dict[str, str]]]) -> Set[Tuple[str, str, str]]:
    keys: Set[Tuple[str, str, str]] = set()
    for relation, rows in rows_by_relation.items():
        spec = RELATION_TYPES.get(relation)
        if spec is None:
            continue
        for row in rows:
            keys.add((relation, str(row.get(spec.left_column) or ""), str(row.get(spec.right_column) or "")))
    return keys


def _with_removed(after_root: Path, before, d: Diff):
    """The later model with the removed things put back, so the drawing can
    hold what is gone; an id that cannot go back (reused by another type)
    is left to the page."""
    scratch = scratch_model(load(after_root))
    for type_name, entity_id, _name in d.removed:
        record = before.entities.get((type_name, entity_id))
        if record is None:
            continue
        try:
            scratch._add_entity(ENTITY_TYPES[type_name], dict(record), Path("<removed>"))
        except ModelError:
            pass
    for relation, rows in d.relations_removed.items():
        for row in rows:
            try:
                scratch._add_relation(relation, dict(row), "<removed>")
            except ModelError:
                pass
    return scratch


def _ends(d: Diff, before, after) -> List[Tuple[str, str]]:
    """Both ends of every line that was added, removed or changed, by type
    and id: an interface's two systems, a relation row's left and right. A
    new line between two unchanged systems is a change worth a picture, and
    neither end would be a box without this; a connection whose protocol
    moved was counted among the changed and drawn nowhere."""
    ends: List[Tuple[str, str]] = []
    for snap, moved in ((after, d.added), (before, d.removed), (after, [c[:3] for c in d.changed])):
        for type_name, entity_id, _name in moved:
            if type_name != "interfaces":
                continue
            record = snap.entities.get((type_name, entity_id)) or {}
            for column in ("source_system_id", "target_system_id"):
                if record.get(column):
                    ends.append(("systems", str(record[column])))
    drawn = {relation for relation, _types in REACH}
    for rows_by_relation in (d.relations_added, d.relations_removed):
        for relation, rows in rows_by_relation.items():
            spec = RELATION_TYPES.get(relation)
            # A row of a relation the picture does not draw would put a box
            # on it with no line to say why; the page lists those rows.
            if spec is None or relation not in drawn:
                continue
            for row in rows:
                for side, column in ((spec.left, spec.left_column), (spec.right, spec.right_column)):
                    if row.get(column):
                        ends.append((side, str(row[column])))
    return ends


def _hop(model, moved: Set[str]) -> List[Tuple[str, str]]:
    """One hop out from the things that moved, by type and id: the other
    end of every interface and every drawn relation row that touches one.
    Counted off the rows, not asked of the view, since a view's expand
    clauses compound and one hop from a hub was the estate."""
    ends: List[Tuple[str, str]] = []
    for interface in model.all_of("interfaces"):
        pair = (str(interface.get("source_system_id") or ""), str(interface.get("target_system_id") or ""))
        if moved.intersection(pair):
            ends.extend(("systems", end) for end in pair if end)
    for relation, _types in REACH:
        spec = RELATION_TYPES.get(relation)
        if spec is None:
            continue
        for row in model.relation_rows(relation):
            left, right = str(row.get(spec.left_column) or ""), str(row.get(spec.right_column) or "")
            if left in moved or right in moved:
                ends.append((spec.left, left))
                ends.append((spec.right, right))
    return ends


def _change_view(d: Diff, before, after, since: str, until: str, model=None):
    """The view of the change: what moved, both ends of every line that
    moved, and with `model` the hop out from what was added or removed."""
    from .query import parse_view

    boxes: Dict[str, List[str]] = {}
    moved = [(t, i) for t, i, *_rest in list(d.added) + list(d.removed) + [c[:3] for c in d.changed]]
    hop = _hop(model, {i for _t, i, _n in list(d.added) + list(d.removed)}) if model is not None else []
    for type_name, entity_id in moved + _ends(d, before, after) + hop:
        if type_name not in NOT_BOXES and type_name in ENTITY_TYPES:
            ids = boxes.setdefault(type_name, [])
            if entity_id not in ids:
                ids.append(entity_id)
    if not boxes:
        raise DiffError("nothing to draw: what changed between %s and %s is views or the library, and the page "
                        "says it" % (since, until))
    counts = "%d added, %d removed, %d changed" % (len(d.added), len(d.removed), len(d.changed))
    return parse_view({
        "view_id": "changes", "title": "What changed since %s" % since, "kind": "diagram", "layout": "LR",
        "description": "The things that moved between %s and %s (%s): added drawn in full, removed dashed in red, "
                       "changed with a heavy border or a heavy line, and what is there unchanged one hop away, faded."
                       % (since, until, counts),
        "node_label": "name", "renderers": ["mermaid"], "group_by": "company_domain",
        "scope": {"include": [{"type": t, "where": {"id_in": ids}} for t, ids in boxes.items()]},
        "edges": [{"via": relation} for relation, _types in REACH],
        "style": {"color_by": "type"}, "limits": {"max_nodes": 200},
    }, Path("changes"))


def _named_view(after_root: Path, view_id: str):
    from .estate import views_of

    for view in views_of(Path(after_root)):
        if view.view_id == view_id:
            if view.parameters:
                raise DiffError("%s takes a subject; the change picture draws a view of the whole estate" % view_id)
            if view.kind == "report":
                raise DiffError("%s is a report, a table; the change picture draws a diagram or a map" % view_id)
            return view
    raise DiffError("no view %r in %s" % (view_id, after_root))


def mark(payload: dict, d: Diff) -> None:
    """The marks on a payload: added in full, removed dashed in red, changed
    with a heavy border, the rest faded; a line added in full, a line
    removed dashed, a line that changed heavy, a line that did not move
    faded."""
    added = {entity_id for _t, entity_id, _n in d.added}
    removed = {entity_id for _t, entity_id, _n in d.removed}
    changed = {entity_id for _t, entity_id, _n, _c in d.changed}
    added_edges = _edge_keys(d.relations_added)
    removed_edges = _edge_keys(d.relations_removed)
    for element in payload.get("elements", []):
        data = element["data"]
        if data.get("isGroup"):
            continue
        if data.get("source"):
            key = (str(data.get("kind") or ""), str(data["source"]), str(data["target"]))
            ref = str(data.get("ref") or "")
            if (ref and ref in removed) or key in removed_edges:
                data["lineStyle"] = "dashed"
                data["removed"] = True
            elif ref and ref in changed:
                data["strokeWidth"] = CHANGED_WIDTH
            elif not ((ref and ref in added) or key in added_edges):
                data["faded"] = True
            continue
        node_id = str(data["id"])
        if node_id in removed:
            data["dash"] = "dashed"
            data["stroke"] = REMOVED
            data["ink"] = REMOVED
        elif node_id in added:
            pass
        elif node_id in changed:
            data["strokeWidth"] = CHANGED_WIDTH
        else:
            data["faded"] = True


def changes_between(before_root: Path, after_root: Path, *, since: str = "before", until: str = "after",
                    view_id: Optional[str] = None, date: str = "", web: Optional[Path] = None):
    """The picture of what changed from the estate at `before_root` to the
    one at `after_root` (`terrane.quick.Drawing`); `DiffError` when nothing
    did, or when nothing that changed is a box."""
    from .blocks import load_components
    from .draw import Undrawable, drawing_mode, render_svg
    from .draw.elk import open_runner
    from .icons import IconMap, web_dir
    from .palette import Palette
    from .payload import graph_payload
    from .query import resolve
    from .quick import Drawing, _fonts
    from .shipped import shipped_root

    before_root, after_root = Path(before_root), Path(after_root)
    before, after = snapshot(before_root), snapshot(after_root)
    d = diff(before, after, since, until)
    if d.empty:
        raise DiffError("nothing changed between %s and %s" % (since, until))
    model = _with_removed(after_root, before, d)
    view = _named_view(after_root, view_id) if view_id else _change_view(d, before, after, since, until, model)
    graph = resolve(model, view)
    shipped = shipped_root()
    web = Path(web) if web else (web_dir(after_root) or web_dir(shipped) or shipped / "web")
    icons = IconMap(web)
    payload = graph_payload(model, view, Palette(model.config.get("palette")), icons, load_components(after_root),
                            graph=graph)
    mark(payload, d)
    runner = open_runner(web)
    try:
        drawing_mode(payload)
        svg = render_svg(payload, icon_loader=icons.read, font_loader=_fonts(web),
                         model_name=str(model.config.get("name") or "Architecture Model"), date=date, elk=runner)
    except Undrawable as exc:
        raise DiffError("the change cannot be drawn: %s" % exc) from exc
    finally:
        if runner is not None:
            runner.close()
    return Drawing("changes" if not view_id else view_id, view.kind, svg, None, title=view.title)


def changes_since(repo: Path, since: str, until: Optional[str] = None, *, view_id: Optional[str] = None,
                  date: str = "", web: Optional[Path] = None):
    """The picture of what changed in the repository at `repo` from the
    revision `since` to `until`, or to the working tree."""
    repo = Path(repo)
    before_root = export_revision(repo, since)
    after_root = export_revision(repo, until) if until else repo
    return changes_between(before_root, after_root, since=since, until=until or "the working tree",
                           view_id=view_id, date=date, web=web)
