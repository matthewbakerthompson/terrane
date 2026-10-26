"""A sketch joins the estate.

Every reader ends in a sketch, and a sketch is drawn in a scratch
repository that is thrown away. The point of reading what a team already
has was to arrive at a model, so this writes the sketch into a real
repository: each record its own file under `10_MODEL`, in the folder of
its type, with a header that says where it came from; each relation row
into `10_MODEL/relations/adopted.yaml`; each view the sketch wrote out
into `30_VIEWS`, a page read from a file as the diagram of the things
pinned to it (`adopted_view`). Nothing already in the estate is touched: a record whose
id is there stays as it is and is said, a row already recorded is not
recorded twice, a view that exists keeps its file. The sketch's defaults
are filled as they are for a drawing, and the placeholder owner a sketch
gets stands in unless an org unit of the estate is named for the job.
The estate is validated after, and what changed in the count is said, so
the person who adopted a sketch knows what they took on.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from . import validate as validate_module
from .correct import CorrectError, revise, revise_override, revise_row, text_of, typed_like
from .loader import read_data_file
from .model import load
from .estate import views_of
from .query import load_views
from .quick import SKETCH_ORG, QuickError, _own_zone, answer_parameters, fill_defaults
from .schema import ENTITY_TYPES, RELATION_TYPES
from .shipped import shipped_root
from .sketch import yaml_text

RELATIONS_FILE = "adopted.yaml"


class AdoptError(ValueError):
    pass


class Adoption(NamedTuple):
    #: Entity type to the ids written, and to the ids already there.
    added: Dict[str, List[str]]
    skipped: Dict[str, List[str]]
    rows_added: int
    rows_skipped: int
    views_added: List[str]
    views_skipped: List[str]
    written: List[Path]
    notes: List[str]
    #: Validate's counts after, and before, so the difference is plain.
    errors: int
    warnings: int
    errors_before: int
    warnings_before: int
    #: With `correct`: entity type to the ids whose files took a differing
    #: cell, and each change as a line, `SYS-X name: old -> new`.
    changed: Dict[str, List[str]] = {}
    changes: List[str] = []
    #: With `correct`: the relation rows whose qualifier took the sketch's.
    rows_corrected: int = 0
    #: The relation rows added (or, dry, that would be), by relation: the
    #: picture of the change draws each as a line in full.
    rows_new: Dict[str, List[dict]] = {}
    #: The ids added that the sketch gave no owner: the placeholder owns
    #: them, or the org unit named for the job. The app asks who, by count.
    unowned: List[str] = []

    @property
    def count(self) -> int:
        return sum(len(ids) for ids in self.added.values())


def _safe(entity_id: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_." else "-" for ch in str(entity_id))


#: What every reader calls the one page of a file it read.
READ_VIEW = "imported"

#: The layer a page of a drawing is filed under, by what most of the
#: things on it are: a reader says nothing of layers, and every page of
#: every drawing adopted went under Other, while the canvas it opens on
#: offered Application as its layer.
LAYER_OF = {"systems": "Application", "interfaces": "Application", "offered_interfaces": "Application",
            "actors": "Application", "products": "Application", "flows": "Application",
            "data_assets": "Data", "tech_services": "Technology",
            "capabilities": "Business", "frameworks": "Business", "value_streams": "Business",
            "value_stream_stages": "Business", "org_units": "Business", "processes": "Business",
            "policies": "Governance", "controls": "Governance",
            "roadmaps": "Change", "work_packages": "Change", "architecture_change_requests": "Change"}


def adopted_view(item: dict, source_name: str, held: Optional[Dict[str, List[str]]] = None) -> dict:
    """A view the sketch wrote out, as the estate keeps it.

    The one page of a file, which every reader calls `imported`, is named
    for the file: the second drawing adopted found the first one's
    `imported` there, and its page was skipped as a view already here, so
    the drawing someone brought became records and no diagram.

    A type named bare (`- type: systems`) means the sketch's systems, since
    a sketch is drawn over its own records alone; written as it was into an
    estate it meant every system there, and the page of a five-box PlantUML
    diagram adopted into the sample was the whole estate. With `held`, the
    sketch's ids by type, it is those ids. A page that is then a list of
    things (an `id_in` per type and nothing else) is kept as the things
    pinned to it, which is what a diagram drawn on the canvas is: it opens
    there to be arranged and added to, and a thing taken out of the estate
    later is a stale pin said by validate rather than a page that no longer
    draws. Such a page with no `category` is filed under the layer most of
    its things belong to (`LAYER_OF`), Application on a tie."""
    item = dict(item)
    stem = Path(str(source_name)).stem if Path(str(source_name)).suffix else ""
    named = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    if str(item.get("view_id")) == READ_VIEW and named:
        item["view_id"] = named
    scope = item.get("scope")
    include = scope.get("include") if isinstance(scope, dict) and set(scope) == {"include"} else None
    if not isinstance(include, list) or not include:
        return item
    if held is not None:
        include = [{"type": step["type"], "where": {"id_in": list(held.get(str(step["type"])) or [])}}
                   if isinstance(step, dict) and set(step) == {"type"} else step for step in include]
        item["scope"] = dict(scope, include=include)
    if all(isinstance(step, dict) and set(step) == {"type", "where"} and isinstance(step["where"], dict)
           and set(step["where"]) == {"id_in"} and isinstance(step["where"]["id_in"], list) for step in include):
        item["scope"] = {"pin": [str(i) for step in include for i in step["where"]["id_in"]]}
        if not item.get("category"):
            votes: Dict[str, int] = {}
            for step in include:
                layer = LAYER_OF.get(str(step["type"]), "Application")
                votes[layer] = votes.get(layer, 0) + len(step["where"]["id_in"])
            if votes:
                item["category"] = max(votes, key=lambda layer: (votes[layer], layer == "Application"))
    return item


#: What a record says to be expanded, or where it came from, is not a
#: cell to correct: a shape is answered under the instance, not edited in
#: what it made.
NOT_CORRECTED = ("archetype", "compose", "parameters", "modules", "archetype_instance", "module",
                 "overrides", "exclude", "extra", "without")


def corrections(existing: dict, given: dict, pk: str) -> Dict[str, Tuple[Any, Any]]:
    """What the sketch says differently of a record that is there: field
    to (as it is, as the sketch says), for the cells the sketch filled. A
    blank is left alone, since a workbook cannot say "clear this"; the id
    and the composition are not cells to correct; a list in another order
    and a bool spelled Yes are the same value."""
    out: Dict[str, Tuple[Any, Any]] = {}
    for key, raw in given.items():
        if key == pk or str(key).startswith("_") or key in NOT_CORRECTED:
            continue
        if raw is None or raw == [] or (isinstance(raw, str) and not raw.strip()):
            continue
        new = typed_like(raw, existing.get(key))
        if text_of(existing.get(key)) != text_of(new):
            out[str(key)] = (existing.get(key), new)
    return out


def join_estate(doc: dict, root: Path, *, owner: Optional[str] = None, source_name: str = "a sketch",
                dry_run: bool = False, shipped: Optional[Path] = None, correct: bool = False) -> Adoption:
    """Write the sketch `doc` into the repository at `root`; what was
    added, what was already there, and the estate's validation after.
    With `dry_run` nothing is written and the counts say what would be.
    With `correct`, a record already there takes the sketch's differing
    cells (`corrections`), written into its own file with the file
    otherwise left as it is (`terrane.correct`), so a reviewer's workbook
    comes back as corrections; a correction to what a shape made goes
    under the product's overrides (`revise_override`)."""
    root = Path(root)
    model_dir = root / "10_MODEL"
    if not model_dir.is_dir():
        raise AdoptError("%s has no 10_MODEL: not a repository" % root)
    model = load(root)
    views = views_of(root)
    before = validate_module.run(model, views)
    doc, notes = _own_zone(dict(doc), shipped or shipped_root())
    entities, filled_notes = fill_defaults(doc)
    notes = list(filled_notes) + notes
    # The sketch's records as written, before the defaults: a correction is
    # what the sketch said, not what was filled in to draw it.
    given_by_type: Dict[str, Dict[str, dict]] = {
        t: {str(r.get(ENTITY_TYPES[t].pk)): r for r in (doc.get(t) or []) if isinstance(r, dict)} for t in ENTITY_TYPES}
    changed: Dict[str, List[str]] = {}
    changes: List[str] = []
    placeholder = {str(r.get(ENTITY_TYPES[t].pk)) for t, records in entities.items() for r in records
                   if t != "org_units" and r.get("owner_org_id") == SKETCH_ORG}
    unowned: List[str] = []

    if owner:
        if model.get("org_units", owner) is None and not any(
                r.get("org_unit_id") == owner for r in entities.get("org_units", [])):
            raise AdoptError("no org unit %s in the estate to own what is adopted" % owner)
        for type_name, records in entities.items():
            for record in records:
                if record.get("owner_org_id") == SKETCH_ORG:
                    record["owner_org_id"] = owner
        if entities.get("org_units"):
            entities["org_units"] = [r for r in entities["org_units"] if r.get("org_unit_id") != SKETCH_ORG]
            if not entities["org_units"]:
                del entities["org_units"]
        notes = [n for n in notes if SKETCH_ORG not in n]
        notes.append("%s owns what the sketch left without an owner" % owner)
    # A product on a shape or from parts asks for parameters a sketch may
    # leave out. The drawing answers them and says so; the record written
    # has to carry the answers too, or the estate does not load after:
    # `terrane adopt from-parts.yaml` wrote the product and then failed on it.
    _touched, answered = answer_parameters(entities, root, owner or SKETCH_ORG)
    notes.extend(answered)

    header = ["Adopted from %s by `terrane adopt`." % source_name]
    added: Dict[str, List[str]] = {}
    skipped: Dict[str, List[str]] = {}
    written: List[Path] = []
    for type_name in ENTITY_TYPES:
        records = entities.get(type_name) or []
        if not records:
            continue
        entity_type = ENTITY_TYPES[type_name]
        folder = model_dir / entity_type.folder
        for record in records:
            entity_id = str(record[entity_type.pk])
            existing = model.get(type_name, entity_id)
            if existing is not None:
                if correct:
                    diffs = corrections(existing, given_by_type.get(type_name, {}).get(entity_id) or {}, entity_type.pk)
                    if diffs and existing.get("archetype_instance"):
                        # Made by a shape: the record has no file of its
                        # own, and the method keeps what reality says
                        # differently from the shape under the product's
                        # overrides, so the correction goes there. It was
                        # said and left before, the answer named and not
                        # taken.
                        instance_id = str(existing["archetype_instance"])
                        found = model.find(instance_id)
                        if found is None:
                            notes.append("%s: made by the shape %s on %s, which is not in the estate; left as it is"
                                         % (entity_id, existing.get("archetype"), instance_id))
                            diffs = {}
                        else:
                            instance_type, instance = found
                            source_path = Path(str(instance.get("_source_file") or ""))
                            try:
                                if not dry_run:
                                    revise_override(source_path, ENTITY_TYPES[instance_type].pk, instance_id, entity_id,
                                                    {k: new for k, (_old, new) in diffs.items()})
                            except (CorrectError, OSError) as exc:
                                notes.append("%s: %s; left as it is" % (entity_id, exc))
                            else:
                                changed.setdefault(type_name, []).append(entity_id)
                                if source_path not in written:
                                    written.append(source_path)
                                for key, (old, new) in diffs.items():
                                    changes.append("%s %s: %s -> %s, under the overrides of %s" % (
                                        entity_id, key, text_of(old) or "(blank)", text_of(new), instance_id))
                                continue
                            diffs = {}
                    if diffs:
                        source_path = Path(str(existing.get("_source_file") or ""))
                        try:
                            if not dry_run:
                                revise(source_path, entity_type.pk, entity_id, {k: new for k, (_old, new) in diffs.items()})
                        except (CorrectError, OSError) as exc:
                            notes.append("%s: %s; left as it is" % (entity_id, exc))
                        else:
                            changed.setdefault(type_name, []).append(entity_id)
                            if source_path not in written:
                                written.append(source_path)
                            for key, (old, new) in diffs.items():
                                changes.append("%s %s: %s -> %s" % (entity_id, key, text_of(old) or "(blank)", text_of(new)))
                            continue
                skipped.setdefault(type_name, []).append(entity_id)
                continue
            added.setdefault(type_name, []).append(entity_id)
            if entity_id in placeholder:
                unowned.append(entity_id)
            path = folder / ("%s.yaml" % _safe(entity_id))
            written.append(path)
            if not dry_run:
                folder.mkdir(parents=True, exist_ok=True)
                path.write_text(yaml_text(record, header), encoding="utf-8")

    rows_added = rows_skipped = rows_corrected = 0
    relations = doc.get("relations") or {}
    if relations and not isinstance(relations, dict):
        raise QuickError("relations: a mapping of relation name to rows")
    new_rows: Dict[str, List[dict]] = {}
    for relation_name, rows in relations.items():
        relation = RELATION_TYPES.get(relation_name)
        if relation is None:
            notes.append("relations.%s: not a relation of the schema; left out" % relation_name)
            continue
        # Every row here by its pair, and by the triple the loader counts a
        # row as: a capability refers to a framework under several names,
        # and the workbook of the pictures came back with each of them.
        existing_rows: Dict[Tuple[str, str], List[dict]] = {}
        for r in model.relations.get(relation_name, []):
            existing_rows.setdefault((str(r.get(relation.left_column)), str(r.get(relation.right_column))), []).append(r)
        have = set(existing_rows)

        def _said(r: dict) -> str:
            return text_of(r.get(relation.qualifier)) if relation.qualifier else ""

        recorded = {(pair[0], pair[1], _said(r)) for pair, here in existing_rows.items() for r in here}
        given_pairs: Dict[Tuple[str, str], int] = {}
        for row in rows or []:
            pair = (str(row.get(relation.left_column)), str(row.get(relation.right_column)))
            given_pairs[pair] = given_pairs.get(pair, 0) + 1
        for row in rows or []:
            key = (str(row.get(relation.left_column)), str(row.get(relation.right_column)))
            if key in have:
                # With `correct`, the one row of a pair takes the sketch's
                # differing qualifier, the way a record takes a cell. A row
                # the estate has as given is recorded, whatever its
                # neighbors say; a pair with several rows here, or several
                # in the sketch, has no one row to correct, and the first
                # corrected into a duplicate of the second was the bug.
                given = row.get(relation.qualifier) if relation.qualifier else None
                here = existing_rows.get(key) or []
                there = here[0] if len(here) == 1 else None
                if correct and given not in (None, "") and (key[0], key[1], text_of(given)) not in recorded \
                        and given_pairs.get(key, 0) == 1 and len(here) > 1:
                    notes.append("%s %s -> %s: %d rows here and none with %s %r; a row among several is not "
                                 "corrected; left as they are" % (relation_name, key[0], key[1], len(here),
                                                                  relation.qualifier, text_of(given)))
                elif correct and given not in (None, "") and (key[0], key[1], text_of(given)) not in recorded \
                        and given_pairs.get(key, 0) > 1:
                    notes.append("%s %s -> %s: the sketch has %d rows for the pair; which corrects the row here is "
                                 "not the tool's to pick; left as it is" % (relation_name, key[0], key[1],
                                                                            given_pairs[key]))
                elif correct and there is not None and given not in (None, "") \
                        and (key[0], key[1], text_of(given)) not in recorded:
                    if there.get("archetype_instance"):
                        notes.append("%s %s -> %s: made by a shape on %s; a correction goes under the product's "
                                     "overrides; left as it is" % (relation_name, key[0], key[1], there["archetype_instance"]))
                    else:
                        source_path = Path(str(there.get("_source") or ""))
                        try:
                            if not dry_run:
                                revise_row(source_path, relation_name, relation.left_column, key[0],
                                           relation.right_column, key[1], relation.qualifier, given)
                        except (CorrectError, OSError) as exc:
                            notes.append("%s %s -> %s: %s; left as it is" % (relation_name, key[0], key[1], exc))
                        else:
                            rows_corrected += 1
                            if source_path not in written:
                                written.append(source_path)
                            changes.append("%s %s -> %s %s: %s -> %s" % (
                                relation_name, key[0], key[1], relation.qualifier,
                                text_of(there.get(relation.qualifier)) or "(blank)", text_of(given)))
                            continue
                rows_skipped += 1
                continue
            have.add(key)
            new_rows.setdefault(relation_name, []).append(dict(row))
            rows_added += 1
    if new_rows:
        path = model_dir / "relations" / RELATIONS_FILE
        written.append(path)
        if not dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            held: dict = {}
            if path.is_file():
                data = read_data_file(path)
                if isinstance(data, dict):
                    held = {k: list(v or []) for k, v in data.items()}
            for relation_name, rows in new_rows.items():
                held.setdefault(relation_name, []).extend(rows)
            path.write_text(yaml_text(held, ["Rows adopted from sketches by `terrane adopt`; the latest from %s."
                                             % source_name]), encoding="utf-8")

    views_added: List[str] = []
    views_skipped: List[str] = []
    views_dir = root / "30_VIEWS"
    held = {type_name: [str(r[ENTITY_TYPES[type_name].pk]) for r in records] for type_name, records in entities.items()}
    for item in doc.get("views") or []:
        if not isinstance(item, dict) or not item.get("view_id"):
            continue  # a shipped view by name is in the repository already
        item = adopted_view(item, source_name, held)
        view_id = str(item["view_id"])
        base = view_id.split("--", 1)[0]
        if "--" in view_id and (views_dir / ("%s.view.yaml" % _safe(base))).is_file():
            # A page of this repository's own view on a subject, as a
            # workbook of the pictures names it: the view is here already.
            views_skipped.append(view_id)
            notes.append("%s: a page of this repository's own %s view on a subject; not added as a view" % (view_id, base))
            continue
        path = views_dir / ("%s.view.yaml" % _safe(view_id))
        if path.is_file():
            views_skipped.append(view_id)
            continue
        views_added.append(view_id)
        written.append(path)
        if not dry_run:
            views_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(yaml_text(item, header), encoding="utf-8")

    if dry_run:
        errors, warnings = len(before.errors), len(before.warnings)
    else:
        after_model = load(root)
        after = validate_module.run(after_model, load_views(views_dir))
        errors, warnings = len(after.errors), len(after.warnings)
    return Adoption(added, skipped, rows_added, rows_skipped, views_added, views_skipped, written, notes,
                    errors, warnings, len(before.errors), len(before.warnings), changed, changes, rows_corrected,
                    new_rows, unowned)


#: What the picture of a change reaches out to from the new things, one hop
#: along each: the relations of the schema, and the types each pulls in.
REACH = (
    ("interfaces", ["systems"]),
    ("actor_uses_system", ["actors", "systems"]),
    ("system_reads_writes", ["systems", "data_assets"]),
    ("system_uses_tech_service", ["systems", "tech_services"]),
    ("system_realizes_capability", ["systems", "capabilities"]),
    ("product_includes_system", ["products", "systems"]),
    ("process_uses_system", ["processes", "systems"]),
    ("process_uses_data_asset", ["processes", "data_assets"]),
    ("system_subject_to_policy", ["systems", "policies"]),
    ("system_governed_by_control", ["systems", "controls"]),
    # The data's governance as well as a system's: a Visio drawing's policy
    # on the card ledger was a box on its own, the line to the ledger the
    # file drew nowhere in the picture.
    ("data_subject_to_policy", ["data_assets", "policies"]),
    ("data_governed_by_control", ["data_assets", "controls"]),
)


def estate_copy(root: Path, tmp: Path) -> Path:
    """The estate at `root` copied under `tmp`, and where it sits there:
    at its place below the repository whose library its `shipped_library`
    names, with that library's layer folders beside it and the folders
    `library_paths` names along. A copy of the estate's own folders alone
    did not load for the second estate, which names `../..` and a library
    of its own, so its adoption picture was an error."""
    import shutil

    from .library import LAYER_FOLDERS, LibraryError, from_package, named_paths
    from .library import shipped_root as library_home

    root, tmp = Path(root), Path(tmp)
    try:
        home = library_home(root).resolve()
    except LibraryError as exc:
        raise AdoptError(str(exc)) from exc
    if from_package(root):
        # The copy names the package as the estate does, and reads the same
        # library from it; there is no repository above to rebuild.
        home = root.resolve()
    place = tmp.joinpath(*root.resolve().relative_to(home).parts) if home != root.resolve() else tmp
    ignore = shutil.ignore_patterns("__pycache__")
    for folder in ("10_MODEL", "30_VIEWS") + tuple(LAYER_FOLDERS):
        if (root / folder).is_dir():
            shutil.copytree(root / folder, place / folder, ignore=ignore)
    if home != root.resolve():
        for folder in LAYER_FOLDERS:
            if (home / folder).is_dir():
                shutil.copytree(home / folder, tmp / folder, ignore=ignore)
    try:
        named = named_paths(root)
    except LibraryError:
        named = []
    for name in named:
        source, target = (root / name).resolve(), (place / name).resolve()
        if source.is_dir() and tmp.resolve() in target.parents and not target.exists():
            shutil.copytree(source, target, ignore=ignore)
    return place


def _count(n: int, noun: str) -> str:
    return "%d %s" % (n, noun if n == 1 else noun + "s")


def _these(things: int, lines: int) -> str:
    """'the 1 thing and 2 connections', or whichever of the two there are."""
    parts = [_count(n, noun) for n, noun in ((things, "thing"), (lines, "connection")) if n]
    return "the " + " and ".join(parts)


def change_picture(doc: dict, root: Path, *, owner: Optional[str] = None, source_name: str = "a sketch",
                   date: str = "", correct: bool = False, sheet: bool = True):
    """What the sketch would add to the estate, as a picture: the new
    records drawn in full among the estate's own things one hop away,
    which are faded, so a reviewer sees the change against what is there
    before anything is written; with `correct`, what it would correct as
    well, each corrected record with the heavy border the diff picture
    gives a changed one, and a corrected connection as a heavy line between
    its two ends. The estate is copied to a scratch folder and the sketch
    adopted into the copy; the repository is not touched. Nothing to show
    is said as `AdoptError`. `sheet=False` draws it without the title
    block, legend and footer, for a page that says those itself, as the
    app's does around a dropped drawing."""
    import tempfile

    from .blocks import load_components
    from .draw import Undrawable, drawing_mode, render_svg
    from .draw.elk import open_runner
    from .icons import IconMap, web_dir
    from .palette import Palette
    from .payload import graph_payload
    from .query import parse_view, resolve
    from .quick import Drawing, _fonts

    root = Path(root)
    with tempfile.TemporaryDirectory(prefix="aac-change-") as tmp:
        scratch = estate_copy(root, Path(tmp))
        result = join_estate(doc, scratch, owner=owner, source_name=source_name, shipped=shipped_root(),
                             correct=correct)
        # The new things, less the placeholder owner, and less the
        # interfaces, which are lines on the picture and not boxes; with
        # `correct`, the corrected things beside them. A connection added
        # or corrected is a line between its two ends, which are kept: the
        # reviewer who changed one connection's kind saw a picture of
        # nothing, the interface counted and drawn nowhere.
        model = load(scratch)
        added = {type_name: ids for type_name, ids in result.added.items()
                 if type_name not in ("org_units", "interfaces")}
        corrected = {type_name: ids for type_name, ids in result.changed.items()
                     if type_name not in ("org_units", "interfaces")}
        # What a new product's shape or parts make is new too: the systems,
        # the lines between them, the data they master, drawn in full and
        # not faded as if the estate had them. The adopter adds the product
        # alone, since the file is the decision and the render makes the
        # rest, and the notebook's product from a kit was one box in full
        # over two faded systems that were its own.
        makers = {entity_id for ids in result.added.values() for entity_id in ids}
        made: Dict[str, List[str]] = {}
        for type_name in ENTITY_TYPES:
            pk = ENTITY_TYPES[type_name].pk
            for record in model.all_of(type_name):
                entity_id = str(record.get(pk) or "")
                if str(record.get("archetype_instance") or "") in makers and entity_id and entity_id not in makers:
                    made.setdefault(type_name, []).append(entity_id)
        made_lines = set(made.pop("interfaces", []))
        made.pop("org_units", None)
        made_ids = {entity_id for ids in made.values() for entity_id in ids}
        new_ids = {entity_id for ids in added.values() for entity_id in ids} | made_ids
        corrected_ids = {entity_id for ids in corrected.values() for entity_id in ids}
        new_lines = set(result.added.get("interfaces", [])) | made_lines
        corrected_lines = set(result.changed.get("interfaces", []))
        drawn = {relation for relation, _types in REACH if relation in RELATION_TYPES}
        new_rows = {relation: list(rows) for relation, rows in result.rows_new.items() if relation in drawn}
        made_rows = 0
        for relation in drawn:
            rows = [row for row in model.relation_rows(relation) if str(row.get("archetype_instance") or "") in makers]
            if rows:
                new_rows.setdefault(relation, []).extend(rows)
                made_rows += len(rows)
        connections = len(result.added.get("interfaces", [])) + result.rows_added
        made_connections = len(made_lines) + made_rows
        if not new_ids and not corrected_ids and not connections and not corrected_lines:
            raise AdoptError("nothing to show: everything in %s is in the estate already" % source_name)
        if not new_ids and not corrected_ids and not new_lines and not corrected_lines and not new_rows:
            raise AdoptError("%s adds only rows (%d) of relations the picture does not draw; nothing to draw"
                             % (source_name, connections))
        shown: Dict[str, List[str]] = {}
        for type_name in ENTITY_TYPES:
            ids = list(added.get(type_name, []))
            ids += [i for i in made.get(type_name, []) + corrected.get(type_name, []) if i not in ids]
            if ids:
                shown[type_name] = ids
        said = []
        if new_ids or connections:
            said.append("%s %s would add to the estate%s%s" % (
                _these(len(new_ids - made_ids), connections), source_name,
                ", and %s it makes" % _these(len(made_ids), made_connections) if made_ids or made_connections else "",
                ", the things drawn in full" if new_ids else ""))
        if corrected_ids or corrected_lines:
            said.append("%s it would correct, %s" % (
                _these(len(corrected_ids), len(corrected_lines)),
                "with a heavy border" if not corrected_lines else "as a heavy line" if not corrected_ids
                else "with a heavy border, the connections as heavy lines"))
        adds, corrects = bool(new_ids or connections), bool(corrected_ids or corrected_lines)
        title = "What %s %s" % (source_name, "adds and corrects" if adds and corrects else "corrects" if corrects
                                else "adds")
        # The neighborhood one hop away belongs to what the file adds: a
        # corrected record may be the estate's hub (the card ledger is),
        # and one hop from it is the estate, so it is drawn where it is,
        # heavy, with no neighbors of its own pulled in.
        boxes: Dict[str, List[str]] = {t: list(ids) for t, ids in shown.items()}

        def keep(type_name: str, entity_id: str) -> None:
            if entity_id and type_name not in ("org_units", "interfaces") and model.get(type_name, entity_id) is not None \
                    and entity_id not in boxes.setdefault(type_name, []):
                boxes[type_name].append(entity_id)

        # One hop, counted off the rows by hand: a view's expand clauses
        # compound, each hop taken from the set the one before it grew, so
        # one hop along ten relations from a hub was the estate.
        for interface in model.all_of("interfaces"):
            ends = (str(interface.get("source_system_id") or ""), str(interface.get("target_system_id") or ""))
            line = str(interface.get("interface_id") or "")
            if new_ids.intersection(ends) or line in new_lines or line in corrected_lines:
                for end in ends:
                    keep("systems", end)
        added_edges = set()
        for relation, _types in REACH:
            spec = RELATION_TYPES.get(relation)
            if spec is None:
                continue
            # The rows the file adds, and the rows a new product's shape
            # made: both ends kept, the line drawn in full.
            for row in new_rows.get(relation, []):
                left, right = str(row.get(spec.left_column) or ""), str(row.get(spec.right_column) or "")
                added_edges.add((relation, left, right))
                keep(spec.left, left)
                keep(spec.right, right)
            for row in model.relation_rows(relation):
                left, right = str(row.get(spec.left_column) or ""), str(row.get(spec.right_column) or "")
                if left in new_ids or right in new_ids:
                    keep(spec.left, left)
                    keep(spec.right, right)
        view = parse_view({
            "view_id": "change", "title": title, "kind": "diagram", "layout": "LR",
            # The first letter up and the rest as said: `capitalize` lowered
            # the sketch's own name, "merchant onboarding would add".
            "description": "%s%s." % ("; ".join(said)[:1].upper() + "; ".join(said)[1:],
                                       ", and what is there already, faded" if adds or corrected_lines else ""),
            "node_label": "name", "renderers": ["mermaid"], "group_by": "company_domain",
            "scope": {"include": [{"type": t, "where": {"id_in": ids}} for t, ids in boxes.items()]},
            "edges": [{"via": relation} for relation, _types in REACH],
            "style": {"color_by": "type"}, "limits": {"max_nodes": 200},
        }, Path("change"))
        graph = resolve(model, view)
        shipped = shipped_root()
        web = web_dir(root) or web_dir(shipped) or shipped / "web"
        icons = IconMap(web)
        payload = graph_payload(model, view, Palette(model.config.get("palette")), icons, load_components(scratch),
                                graph=graph)
        from .diff_picture import CHANGED_WIDTH

        for element in payload.get("elements", []):
            data = element["data"]
            if data.get("isGroup"):
                continue
            if data.get("source"):
                # A line, marked as the diff picture marks one: corrected
                # heavy, new in full, the rest faded so the ones that move
                # stand out.
                ref = str(data.get("ref") or "")
                key = (str(data.get("kind") or ""), str(data["source"]), str(data["target"]))
                if ref in corrected_lines:
                    data["strokeWidth"] = CHANGED_WIDTH
                elif ref not in new_lines and key not in added_edges:
                    data["faded"] = True
                continue
            if data["id"] in corrected_ids:
                data["strokeWidth"] = CHANGED_WIDTH
            elif data["id"] not in new_ids:
                data["faded"] = True
        runner = open_runner(web)
        try:
            drawing_mode(payload)
            svg = render_svg(payload, icon_loader=icons.read, font_loader=_fonts(web), sheet=sheet,
                             model_name=str(model.config.get("name") or "Architecture Model"), date=date, elk=runner)
        except Undrawable as exc:
            raise AdoptError("the change cannot be drawn: %s" % exc) from exc
        finally:
            if runner is not None:
                runner.close()
    return Drawing("change", "diagram", svg, None, title=view.title)


def describe(result: Adoption, dry_run: bool = False) -> List[str]:
    """The adoption in a few lines, for the command and the notebook."""
    verb = "would adopt" if dry_run else "adopted"
    fix = "would correct" if dry_run else "corrected"
    lines: List[str] = []
    for type_name in ENTITY_TYPES:
        ids = result.added.get(type_name, [])
        there = result.skipped.get(type_name, [])
        fixed = result.changed.get(type_name, [])
        if not ids and not there and not fixed:
            continue
        line = "%-30s %s %d" % (type_name.replace("_", " "), verb, len(ids))
        if fixed:
            line += ", %s %d (%s)" % (fix, len(fixed), ", ".join(fixed[:4]) + (", ..." if len(fixed) > 4 else ""))
        if there:
            line += ", %d already here%s (%s)" % (len(there), " as they are" if result.changed else "",
                                                  ", ".join(there[:4]) + (", ..." if len(there) > 4 else ""))
        lines.append(line)
    for change in result.changes:
        lines.append("  %s" % change)
    if result.rows_added or result.rows_skipped or result.rows_corrected:
        lines.append("%-30s %s %d row(s)%s%s" % (
            "relations", verb, result.rows_added,
            ", %s %d" % (fix, result.rows_corrected) if result.rows_corrected else "",
            ", %d already recorded" % result.rows_skipped if result.rows_skipped else ""))
    if result.views_added or result.views_skipped:
        lines.append("%-30s %s %s%s" % ("views", verb, ", ".join(result.views_added) or "none",
                                          "; %s already here" % ", ".join(result.views_skipped) if result.views_skipped else ""))
    if not result.count and not result.rows_added and not result.views_added and not result.changed \
            and not result.rows_corrected:
        lines.insert(0, "nothing to adopt: everything in the sketch is in the estate already")
    lines.append("%d file(s) %s" % (len(result.written), "would be written" if dry_run else "written"))
    if not dry_run:
        change = result.warnings - result.warnings_before
        lines.append("validate: %d error(s), %d warning(s)%s" % (
            result.errors, result.warnings,
            " (%s%d)" % ("+" if change > 0 else "", change) if change else ""))
    return lines
