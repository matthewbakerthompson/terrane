"""Moving a record into another boundary on a drawing.

A boundary on a drawing is not a shape somebody drew: it is one value of a
field the view groups by, `system_category` or `company_domain`, and a box
sits in it because its record holds that value. So dropping a box into a
different boundary is not a change to the drawing, which keeps no positions,
but to the record. It sets the field, and the box moves on every drawing
grouped by that field, which is why the app says where before it writes.

Three things are worked out here so the app does not guess them: which
boundaries a drop can mean (a field's one stored value, not a kind of thing
or a framework's relation), what the drop would change on the record, and
which drawings that change moves the box on, joins it to or takes it off.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Tuple

from .importer import LIST_FIELDS
from .model import Model
from .query import View, ViewError, bind, group_kinds, render_targets, resolve
from .records import home_of
from .schema import ENTITY_TYPES


class Boundary(NamedTuple):
    """A boundary a record can be moved into: the field, and its value as
    the records inside store it -- an org unit's id where the boundary is
    labeled with its name."""

    field: str
    value: Any


def settable(field: str) -> bool:
    """Whether a `group_by` entry is a field a record holds one value of.
    `type` is the table a record is in, and `relation@target` reads a
    relation's qualifier; neither is a field to set."""
    return bool(field) and field != "type" and "@" not in field and field not in LIST_FIELDS


def boundaries(graph) -> Dict[Tuple[str, ...], Boundary]:
    """Every boundary on a drawing that one field's one value makes, by its
    path. A boundary whose records store two different values under one
    label -- two org units of the same name -- is left out: a drop there
    could not say which it meant."""
    kinds = group_kinds(graph)
    fields = list(graph.view.group_by or [])
    seen: Dict[Tuple[str, ...], Dict[str, Any]] = {}
    for node in graph.nodes:
        node_fields = list(node.group_fields) + fields[len(node.group_fields):len(node.groups)]
        for depth in range(1, len(node.groups) + 1):
            path = node.groups[:depth]
            kind = kinds.get(path, ("", ""))[0]
            field = node_fields[depth - 1] if depth - 1 < len(node_fields) else ""
            # A collapsed level is the outer field's boundary, and a record
            # that reached it through the inner one does not say its value.
            if field != kind or not settable(field):
                continue
            value = node.record.get(field)
            # Text, a number or a yes-or-no travels to the app and back as
            # itself; a date PyYAML parsed would not survive the JSON.
            if value in (None, "") or not isinstance(value, (str, int, float, bool)):
                continue
            seen.setdefault(path, {})[repr(value)] = value
    return {
        path: Boundary(kinds[path][0], next(iter(values.values())))
        for path, values in seen.items()
        if len(values) == 1
    }


class Change(NamedTuple):
    field: str
    before: Any
    after: Any


class Drawing(NamedTuple):
    """One drawing grouped by a field the move changes, with what the move
    does to the box there. `subject` is the id a subject view is drawn for,
    blank for a view that has none."""

    view_id: str
    title: str
    subject: str
    subject_name: str
    #: `moves` (drawn before and after, in another boundary), `joins` (drawn
    #: only after) or `leaves` (drawn only before): a view whose scope
    #: filters on the field it groups by takes the box off when it moves.
    effect: str


class Plan(NamedTuple):
    entity_id: str
    entity_type: str
    name: str
    changes: List[Change]
    #: Why the move cannot be made here, or None.
    blocked: Optional[str]
    #: Something saving will also do, said before it does: a harvested
    #: record moves into a file of its own.
    note: Optional[str]
    drawings: List[Drawing]


def words(field: str) -> str:
    """A field as a person says it: `owner_org_id` is the owner org."""
    return field[:-3].replace("_", " ") if field.endswith("_id") else field.replace("_", " ")


def plan(model: Model, views: Sequence[View], entity_id: str, into: Sequence[Tuple[str, Any]]) -> Plan:
    """What dropping `entity_id` into a boundary would do. `into` is the
    boundary and the ones around it, outermost first, as (field, value) --
    the levels a drop means; a level whose value the record already holds
    changes nothing and is left out of the changes."""
    found = model.find(entity_id)
    if found is None:
        raise KeyError(entity_id)
    type_name, record = found
    entity_type = ENTITY_TYPES[type_name]
    name = str(record.get("name") or entity_id)
    declared = {f.name for f in entity_type.fields}
    label = entity_type.label

    changes: List[Change] = []
    blocked: Optional[str] = None
    if type_name == "offered_interfaces":
        # Drawn in its owner's boundaries because it is part of its owner:
        # it holds none of the fields the boundaries are made of.
        owner = model.find(str(record.get("system_id") or ""))
        blocked = "%s is drawn on %s, the system that offers it: move the system, and it moves with it." % (
            name, owner[1].get("name") if owner else "the system that offers it")
        into = []
    for field, value in into:
        if not settable(field):
            blocked = ("Those boxes are types: %s stays a %s, and something of another type is made "
                       "with New." % (name, label.lower())) if field == "type" else (
                "Those boxes come from what %s is linked to, not from a field it holds: change the link "
                "in its details." % name)
            break
        if field not in declared:
            blocked = "%s is a %s, which has no %s." % (name, label, words(field))
            break
        current = record.get(field)
        if isinstance(current, (list, tuple)):
            blocked = "%s holds a list of %s; change it in the form." % (name, words(field))
            break
        if str(current if current is not None else "") != str(value):
            changes.append(Change(field, current, value))

    note = None
    if blocked is None and changes:
        home = home_of(type_name, record)
        if home.kind == "generated" and record.get("archetype_instance"):
            blocked = (
                "Made by %s, so its %s is set there: under `overrides` on the "
                "instance, or on the shape it is built on."
                % (record["archetype_instance"], " and ".join(words(c.field) for c in changes))
            )
        elif home.kind in ("generated", "imported"):
            blocked = home.note
        elif home.kind == "harvested":
            note = (
                "It was harvested into %s, which the business-layer import rewrites; "
                "saving moves it into a file of its own." % home.path.name
            )

    # Where it would move is worked out only for a move that can be made:
    # the chooser for one that cannot says why and nothing else.
    drawings = drawings_moved(model, views, entity_id, changes) if changes and blocked is None else []
    return Plan(entity_id, type_name, name, changes, blocked, note, drawings)


def _with_changes(model: Model, type_name: str, entity_id: str, changes: Sequence[Change]) -> Model:
    """The model as it would be after the move, without touching the one
    the server holds: a shallow copy sharing everything but the one record.
    The adjacency is rebuilt, since a reference field is an edge."""
    after = copy.copy(model)
    after.entities = dict(model.entities)
    after.entities[type_name] = dict(model.entities[type_name])
    record = dict(model.entities[type_name][entity_id])
    for change in changes:
        record[change.field] = change.after
    after.entities[type_name][entity_id] = record
    after._adjacent = None
    return after


def _drawn(model: Model, view: View, entity_id: str) -> Optional[Tuple[str, ...]]:
    """The boundary path the box sits in on one drawing, or None when the
    drawing does not draw it."""
    try:
        graph = resolve(model, view)
    except ViewError:
        return None
    for node in graph.nodes:
        if node.key == entity_id:
            return node.groups
    return None


def drawings_moved(
    model: Model, views: Sequence[View], entity_id: str, changes: Sequence[Change]
) -> List[Drawing]:
    """Every drawing grouped by a field the move changes on which the box
    is drawn, before or after, and what happens to it there. A subject view
    is every subject it is drawn for. Resolving all of them is a quarter of
    a second on this model, cheap enough to be exact rather than to list the
    views that merely group by the field."""
    if not changes:
        return []
    type_name = model.find(entity_id)[0]
    after = _with_changes(model, type_name, entity_id, changes)
    fields = {c.field for c in changes}
    out: List[Drawing] = []
    for view in views:
        if not fields & set(view.group_by or ()):
            continue
        if view.parameters:
            try:
                targets = render_targets(model, view)
            except ViewError:
                continue
            bound = []
            for parameter, value in targets:
                try:
                    bound.append((value, bind(view, {parameter: value}, model), bind(view, {parameter: value}, after)))
                except ViewError:
                    continue
        else:
            bound = [("", view, view)]
        for subject, as_now, as_after in bound:
            now, then = _drawn(model, as_now, entity_id), _drawn(after, as_after, entity_id)
            if now is None and then is None:
                continue
            if now is not None and then is not None:
                if now == then:
                    continue
                effect = "moves"
            else:
                effect = "joins" if now is None else "leaves"
            located = model.find(subject) if subject else None
            out.append(Drawing(
                view.view_id, view.title, subject,
                # A subject that is a field's value (a domain) is its own name.
                str(located[1].get("name") or subject) if located else subject, effect,
            ))
    return out
