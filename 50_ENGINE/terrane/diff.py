"""What changed in the architecture between two revisions.

Architecture as code invites the question `git` answers for code and nobody
could answer for the model: what moved between then and now, in the model's
own terms. A file diff says a YAML line changed; this says a system was added,
a status went from Planned to Active, a work package reached two more systems,
a view became a timeline. Both revisions are loaded with the engine as it is
today, so a revision the current engine cannot load is an error rather than a
guess.

A revision is exported with `git archive` into a temporary folder -- only the
folders the engine reads -- and loaded from there; "the working tree" is the
repository itself, uncommitted edits included, which is what a reviewer wants
to see before committing them.
"""

from __future__ import annotations

import io
import posixpath
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Tuple

from . import model as model_module
from .connections import kind_of, load_connections
from .library import LAYER_FOLDERS, PACKAGE, LibraryError, named_paths, shipped_name
from .modules import ModuleError, load_modules
from .query import load_views
from .schema import ENTITY_TYPES

#: The folders the engine reads. Anything else at a revision -- artifacts,
#: tests, the app -- is not the architecture.
#: The folders a revision is read from. The connection kinds are among
#: them since a revision's interfaces are of the kinds its own library
#: said: without them HEAD against the working tree was every interface
#: changed, its kind read as new.
MODEL_FOLDERS = (
    "10_MODEL", "20_ARCHETYPES", "24_CONNECTIONS", "25_COMPONENTS", "26_BLOCKS", "27_PATTERNS", "28_MODULES",
    "30_VIEWS",
)


class DiffError(ValueError):
    pass


class Snapshot(NamedTuple):
    """One revision's architecture, in comparable form."""

    #: (entity type, id) -> the record, private keys dropped.
    entities: Dict[Tuple[str, str], Dict[str, Any]]
    #: relation name -> rows, each as a sorted tuple of (column, value).
    relations: Dict[str, List[Tuple[Tuple[str, str], ...]]]
    #: view id -> (title, kind).
    views: Dict[str, Tuple[str, str]]
    #: archetype id -> version.
    shapes: Dict[str, str]
    #: module id -> name.
    parts: Dict[str, str]
    #: interface id -> the connection kind its fields say it is, for the
    #: interfaces of one: a reviewer changes a connection's kind by one
    #: word, and the change log said two fields.
    kinds: Dict[str, str] = {}


class Change(NamedTuple):
    field: str
    before: str
    after: str


class Diff(NamedTuple):
    since: str
    until: str
    added: List[Tuple[str, str, str]]           # (type, id, name)
    removed: List[Tuple[str, str, str]]
    changed: List[Tuple[str, str, str, List[Change]]]
    relations_added: Dict[str, List[Dict[str, str]]]
    relations_removed: Dict[str, List[Dict[str, str]]]
    views_added: List[Tuple[str, str]]          # (id, title)
    views_removed: List[Tuple[str, str]]
    views_changed: List[Tuple[str, str, List[Change]]]
    shapes_changed: List[Tuple[str, str, str]]  # (id, before, after)
    parts_added: List[str]
    parts_removed: List[str]

    @property
    def empty(self) -> bool:
        return not any((
            self.added, self.removed, self.changed, self.relations_added, self.relations_removed,
            self.views_added, self.views_removed, self.views_changed, self.shapes_changed,
            self.parts_added, self.parts_removed,
        ))


def _clean(record: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in record.items() if not str(k).startswith("_")}


def _text(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return ", ".join(_text(v) for v in value)
    if isinstance(value, dict):
        return ", ".join("%s=%s" % (k, _text(v)) for k, v in sorted(value.items()))
    return str(value if value is not None else "")


def snapshot(root: Path) -> Snapshot:
    """Load a revision's folders the way the engine does and flatten them."""
    root = Path(root)
    try:
        model = model_module.load(root)
    except Exception as exc:  # noqa: BLE001 -- whatever the loader raises is the reason
        raise DiffError("%s does not load with this engine: %s" % (root, exc)) from exc
    entities: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for type_name, entity_type in ENTITY_TYPES.items():
        for record in model.all_of(type_name):
            entities[(type_name, str(record[entity_type.pk]))] = _clean(record)
    relations: Dict[str, List[Tuple[Tuple[str, str], ...]]] = {}
    for name, rows in model.relations.items():
        relations[name] = sorted(
            tuple(sorted((str(k), _text(v)) for k, v in row.items() if not str(k).startswith("_")))
            for row in rows
        )
    views: Dict[str, Tuple[str, str]] = {}
    if (root / "30_VIEWS").exists():
        for view in load_views(root / "30_VIEWS"):
            views[view.view_id] = (view.title, view.kind)
    shapes = {a.archetype_id: str(a.version) for a in model.archetypes.values()}
    parts: Dict[str, str] = {}
    if (root / "28_MODULES").exists():
        try:
            parts = {m.module_id: m.name for m in load_modules(root).values()}
        except ModuleError:
            parts = {}
    library = load_connections(root)
    kinds: Dict[str, str] = {}
    for record in model.all_of("interfaces"):
        kind = kind_of(record, library)
        if kind:
            kinds[str(record["interface_id"])] = kind
    return Snapshot(entities, relations, views, shapes, parts, kinds)


def _git(cwd: Path, *args: str) -> str:
    """git's stdout, or `DiffError` with its stderr."""
    done = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)
    if done.returncode != 0:
        raise DiffError("git %s: %s" % (" ".join(args), done.stderr.strip()))
    return done.stdout


def export_revision(repo: Path, rev: str) -> Path:
    """The model folders at `rev`, extracted to a temporary directory, and
    the path of the estate in it.

    `git archive` writes a tar to stdout and Python unpacks it, so nothing
    but git is needed. Folders that do not exist at that revision are left
    out rather than failing the export: an old revision before the parts
    existed is still an architecture. An estate kept in a subfolder of its
    repository is extracted at that subfolder's place, with the library
    its `shipped_library` names fetched from the same revision to the
    place the name reaches: the second estate names `../..`, and the
    export of its own folders alone did not load.
    """
    repo = Path(repo)
    listing = subprocess.run(
        ["git", "-C", str(repo), "ls-tree", "--name-only", rev],
        capture_output=True, text=True,
    )
    if listing.returncode != 0:
        raise DiffError("git does not know %r: %s" % (rev, listing.stderr.strip()))
    present = [f for f in MODEL_FOLDERS if f in listing.stdout.split()]
    if "10_MODEL" not in present:
        raise DiffError("%s has no 10_MODEL; nothing to compare" % rev)
    out = Path(tempfile.mkdtemp(prefix="aac-rev-"))
    prefix = _git(repo, "rev-parse", "--show-prefix").strip().strip("/")
    root = out.joinpath(*prefix.split("/")) if prefix else out
    root.mkdir(parents=True, exist_ok=True)
    _extract(repo, rev, present, root)
    # The organization's libraries, as that revision's model.yaml names
    # them: without them the revision's shapes and parts would not load,
    # and a change to one of its own patterns would not be a change at all.
    try:
        named = named_paths(root)
    except LibraryError:
        named = []
    kept = [
        name for name in named
        if subprocess.run(
            ["git", "-C", str(repo), "ls-tree", "--name-only", rev, "--", name],
            capture_output=True, text=True,
        ).stdout.strip()
    ]
    if kept:
        _extract(repo, rev, kept, root)
    try:
        shipped = shipped_name(root)
    except LibraryError:
        shipped = ""
    # The installed package's library is in no revision of this repository;
    # the revision is read with the library of the terrane that reads it.
    if shipped and shipped != PACKAGE and prefix:
        target = posixpath.normpath(posixpath.join(prefix, shipped))
        if target != "." and not target.startswith(".."):
            raise DiffError("%s names a shipped library at %r, which is not a folder above it" % (repo, shipped))
        if target == ".":
            top = Path(_git(repo, "rev-parse", "--show-toplevel").strip())
            there = _git(top, "ls-tree", "--name-only", rev).split()
            layers = [name for name in there if name in LAYER_FOLDERS]
            if layers:
                _extract(top, rev, layers, out)
    return root


def _extract(repo: Path, rev: str, paths, out: Path) -> None:
    archive = subprocess.run(
        ["git", "-C", str(repo), "archive", "--format=tar", rev, *paths],
        capture_output=True,
    )
    if archive.returncode != 0:
        raise DiffError("git archive %s failed: %s" % (rev, archive.stderr.decode("utf-8", "replace").strip()))
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
        # The data filter, where Python has it (3.12, and the backports):
        # the default extraction is deprecated and says so on every run.
        if hasattr(tarfile, "data_filter"):
            tar.extractall(out, filter="data")
        else:
            tar.extractall(out)


def _name(record: Dict[str, Any], entity_id: str) -> str:
    return str(record.get("name") or entity_id)


def diff(before: Snapshot, after: Snapshot, since: str = "", until: str = "") -> Diff:
    added, removed, changed = [], [], []
    for key in sorted(set(after.entities) - set(before.entities)):
        added.append((key[0], key[1], _name(after.entities[key], key[1])))
    for key in sorted(set(before.entities) - set(after.entities)):
        removed.append((key[0], key[1], _name(before.entities[key], key[1])))
    for key in sorted(set(before.entities) & set(after.entities)):
        old, new = before.entities[key], after.entities[key]
        changes = [
            Change(field, _text(old.get(field)), _text(new.get(field)))
            for field in sorted(set(old) | set(new))
            if _text(old.get(field)) != _text(new.get(field))
        ]
        # A connection's kind, first, when it moved: the library's one word
        # for what the fields below it say, and the word a reviewer used.
        if key[0] == "interfaces":
            was, now = before.kinds.get(key[1], ""), after.kinds.get(key[1], "")
            if was != now:
                changes.insert(0, Change("kind", was, now))
        if changes:
            changed.append((key[0], key[1], _name(new, key[1]), changes))

    relations_added: Dict[str, List[Dict[str, str]]] = {}
    relations_removed: Dict[str, List[Dict[str, str]]] = {}
    for name in sorted(set(before.relations) | set(after.relations)):
        old_rows = set(before.relations.get(name, []))
        new_rows = set(after.relations.get(name, []))
        plus = sorted(new_rows - old_rows)
        minus = sorted(old_rows - new_rows)
        if plus:
            relations_added[name] = [dict(row) for row in plus]
        if minus:
            relations_removed[name] = [dict(row) for row in minus]

    views_added = [(v, after.views[v][0]) for v in sorted(set(after.views) - set(before.views))]
    views_removed = [(v, before.views[v][0]) for v in sorted(set(before.views) - set(after.views))]
    views_changed = []
    for v in sorted(set(before.views) & set(after.views)):
        changes = [
            Change(field, old, new)
            for field, old, new in zip(("title", "kind"), before.views[v], after.views[v])
            if old != new
        ]
        if changes:
            views_changed.append((v, after.views[v][0], changes))
    shapes_changed = [
        (s, before.shapes[s], after.shapes[s])
        for s in sorted(set(before.shapes) & set(after.shapes))
        if before.shapes[s] != after.shapes[s]
    ]
    return Diff(
        since, until, added, removed, changed, relations_added, relations_removed,
        views_added, views_removed, views_changed, shapes_changed,
        sorted(set(after.parts) - set(before.parts)), sorted(set(before.parts) - set(after.parts)),
    )


def between(repo: Path, since: str, until: Optional[str] = None) -> Diff:
    """The diff from `since` to `until`, or to the working tree when `until`
    is not given."""
    before = snapshot(export_revision(repo, since))
    after = snapshot(export_revision(repo, until)) if until else snapshot(Path(repo))
    return diff(before, after, since, until or "the working tree")


def as_dict(d: Diff) -> Dict[str, Any]:
    return {
        "since": d.since,
        "until": d.until,
        "empty": d.empty,
        "totals": {
            "added": len(d.added), "removed": len(d.removed), "changed": len(d.changed),
            "relationsAdded": sum(len(v) for v in d.relations_added.values()),
            "relationsRemoved": sum(len(v) for v in d.relations_removed.values()),
            "views": len(d.views_added) + len(d.views_removed) + len(d.views_changed),
            "library": len(d.shapes_changed) + len(d.parts_added) + len(d.parts_removed),
        },
        "added": [{"type": t, "id": i, "name": n} for t, i, n in d.added],
        "removed": [{"type": t, "id": i, "name": n} for t, i, n in d.removed],
        "changed": [
            {"type": t, "id": i, "name": n,
             "changes": [{"field": c.field, "before": c.before, "after": c.after} for c in cs]}
            for t, i, n, cs in d.changed
        ],
        "relationsAdded": d.relations_added,
        "relationsRemoved": d.relations_removed,
        "viewsAdded": [{"id": v, "title": t} for v, t in d.views_added],
        "viewsRemoved": [{"id": v, "title": t} for v, t in d.views_removed],
        "viewsChanged": [
            {"id": v, "title": t, "changes": [{"field": c.field, "before": c.before, "after": c.after} for c in cs]}
            for v, t, cs in d.views_changed
        ],
        "shapesChanged": [{"id": s, "before": b, "after": a} for s, b, a in d.shapes_changed],
        "partsAdded": list(d.parts_added),
        "partsRemoved": list(d.parts_removed),
    }


def format_markdown(d: Diff) -> str:
    """The diff as a page: counts first, then each kind of change, each item
    with its name and id so the reader does not have to look anything up."""
    lines = ["# What changed since %s" % d.since, ""]
    if d.empty:
        lines.append("Nothing. `%s` and %s hold the same architecture." % (d.since, d.until))
        return "\n".join(lines) + "\n"
    rel_plus = sum(len(v) for v in d.relations_added.values())
    rel_minus = sum(len(v) for v in d.relations_removed.values())
    lines.append(
        "Between `%s` and %s: %d entit%s added, %d removed, %d changed; %d relationship row%s "
        "added, %d removed; %d view%s and %d library item%s touched."
        % (d.since, d.until, len(d.added), "y" if len(d.added) == 1 else "ies", len(d.removed),
           len(d.changed), rel_plus, "" if rel_plus == 1 else "s", rel_minus,
           len(d.views_added) + len(d.views_removed) + len(d.views_changed),
           "" if len(d.views_added) + len(d.views_removed) + len(d.views_changed) == 1 else "s",
           len(d.shapes_changed) + len(d.parts_added) + len(d.parts_removed),
           "" if len(d.shapes_changed) + len(d.parts_added) + len(d.parts_removed) == 1 else "s")
    )
    lines.append("")

    by_type: Dict[str, Dict[str, list]] = {}
    for t, i, n in d.added:
        by_type.setdefault(t, {"added": [], "removed": [], "changed": []})["added"].append((i, n))
    for t, i, n in d.removed:
        by_type.setdefault(t, {"added": [], "removed": [], "changed": []})["removed"].append((i, n))
    for t, i, n, cs in d.changed:
        by_type.setdefault(t, {"added": [], "removed": [], "changed": []})["changed"].append((i, n, cs))
    if by_type:
        lines.append("## Entities")
        lines.append("")
        for t in sorted(by_type):
            buckets = by_type[t]
            summary = ", ".join(
                "%d %s" % (len(buckets[k]), k) for k in ("added", "removed", "changed") if buckets[k]
            )
            lines.append("### %s — %s" % (t.replace("_", " "), summary))
            lines.append("")
            for i, n in buckets["added"]:
                lines.append("- added: %s (`%s`)" % (n, i))
            for i, n in buckets["removed"]:
                lines.append("- removed: %s (`%s`)" % (n, i))
            for i, n, cs in buckets["changed"]:
                lines.append(
                    "- %s (`%s`): %s"
                    % (n, i, "; ".join("`%s` %s → %s" % (c.field, c.before or "—", c.after or "—") for c in cs))
                )
            lines.append("")

    if d.relations_added or d.relations_removed:
        lines.append("## Relationships")
        lines.append("")
        lines.append("| Relationship | Added | Removed |")
        lines.append("|---|---:|---:|")
        for name in sorted(set(d.relations_added) | set(d.relations_removed)):
            lines.append(
                "| `%s` | %d | %d |"
                % (name, len(d.relations_added.get(name, [])), len(d.relations_removed.get(name, [])))
            )
        lines.append("")
        for name in sorted(d.relations_added):
            for row in d.relations_added[name]:
                lines.append("- added `%s`: %s" % (name, ", ".join("%s=%s" % kv for kv in sorted(row.items()))))
        for name in sorted(d.relations_removed):
            for row in d.relations_removed[name]:
                lines.append("- removed `%s`: %s" % (name, ", ".join("%s=%s" % kv for kv in sorted(row.items()))))
        lines.append("")

    if d.views_added or d.views_removed or d.views_changed or d.shapes_changed or d.parts_added or d.parts_removed:
        lines.append("## Views and library")
        lines.append("")
        for v, t in d.views_added:
            lines.append("- view added: %s (`%s`)" % (t, v))
        for v, t in d.views_removed:
            lines.append("- view removed: %s (`%s`)" % (t, v))
        for v, t, cs in d.views_changed:
            lines.append("- view %s (`%s`): %s" % (t, v, "; ".join("%s %s → %s" % (c.field, c.before, c.after) for c in cs)))
        for s, b, a in d.shapes_changed:
            lines.append("- shape `%s`: version %s → %s" % (s, b, a))
        for p in d.parts_added:
            lines.append("- part added: `%s`" % p)
        for p in d.parts_removed:
            lines.append("- part removed: `%s`" % p)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
