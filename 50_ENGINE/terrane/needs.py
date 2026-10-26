"""What each diagram needs from the records, and how many records lack it.

A view never names what it draws. It names a filter, the boundaries it boxes
things into and the lines it draws between them, and each of those reads a
field: Tiered Architecture draws the systems with a `network_zone` and boxes
them by it; the Application Landscape boxes every system by its
`company_domain`; Who Owns What draws a line along each `owner_org_id`. An
estate brought in from a portfolio export has names, owners and a lifecycle
and very little else, so most diagrams draw little or nothing, and nothing
said which fields would fill which. This module says it, view by view and
field by field, read off the view's own query rather than a list kept by
hand, so a view an organization writes says what it needs as the shipped
ones do.

What a view does with a field is its role:

* `selects` -- a `where` the record must pass to be drawn. A blank fails it,
  and the record is left off for want of the field; that is counted only
  where the blank is a gap rather than an answer: the clause asks that the
  field be filled (`exists: true`), or the field is one every record of the
  type must have. A system with no `source` was not harvested, and a
  technology service with no `cloud_account` may be SaaS; neither lacks
  anything a filter on that field wants.
* `groups` -- a boundary. A drawn record with the field blank sits one level
  out (a subnet with no zone sits in its region's box); counted, not
  judged, since a VPC has no availability zone by nature.
* `lines` -- a reference field the lines follow (`owner`, `policy_id`). A
  field naming a record of the record's own type is a hierarchy, and its
  blank is the top of it, not a gap: it is not counted.
* `shades`, `orders` -- `style.color_by` and `order_by`.

A tag the scope asks for (`tags_any: [network-fabric]`) and a relation the
lines are drawn along (`interfaces`, `tech_service_connects_to`) are needs
too, of their own kinds: a tag is wanted on some records and not others,
and a relation is drawn with Connect rather than set; both are counted and
neither makes a diagram thin.

The needs are declared from the view before anything is counted, so a view
over a type the estate has none of still says what it reads: Network
Topology in an estate of systems alone says it draws technology services
tagged `network-fabric`, boxed by provider, account, region and zone.

Where a record sits on a cloud (`cloud_account`, `region`,
`availability_zone`) is asked only of records on a cloud or not yet said to
be anywhere: an on-premise or SaaS system holds none of them, and the query
collapses its empty levels for that reason. The fields a shape sets
(`records.UNASKED`) are never a need: a system is made by a part, not given
one.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, NamedTuple, Optional, Sequence, Set, Tuple

from .model import Model
from .query import _TOKEN_IN_SCOPE, View, ViewError, _related, _value_or_said, located, matches, resolve
from .records import UNASKED
from .schema import ENTITY_TYPES, RELATION_TYPES

#: What a view does with a field, in the order they are listed.
ROLES = ("selects", "groups", "lines", "shades", "orders")

#: The kinds of need: a field a record holds (set on many at once), a tag the
#: scope asks for, and a relation the lines or the scope are drawn from.
KINDS = ("field", "tag", "relation")

#: A view is thin when this share of what it would draw is left off for want
#: of a field, or sits outside its outermost boxes.
THIN = 0.5

#: Where a record sits on a cloud, asked only of records on one.
CLOUD_PLACED = ("cloud_account", "region", "availability_zone")
CLOUDS = ("AWS", "Azure", "GCP")

#: How many values in use a free field offers to choose from.
VALUES_SHOWN = 40

#: The `where` keys that name things or leave things out on purpose, which
#: no record lacks.
_DELIBERATE = ("tags_none", "has_none", "id_in", "id_prefix")


class Need(NamedTuple):
    #: The entity type it is read on.
    type: str
    #: The field; `tags` for a tag need; the relation for a relation need.
    field: str
    #: `field`, `tag` or `relation` (see KINDS).
    kind: str
    #: What the view does with it, in ROLES order.
    roles: Tuple[str, ...]
    #: How many records it is asked of: the records drawn, and for a
    #: selecting field the records left off for want of it as well. Zero
    #: when the estate has none of the type.
    asked: int
    #: The ids of those that lack it, sorted.
    lacking: Tuple[str, ...]
    #: What it takes, in reading order where it has one, as (value, label):
    #: a view's lanes, the field's list, the records a reference names, or
    #: the values in use, most used first. A tag need's tags.
    values: Tuple[Tuple[str, str], ...]
    #: Whether a value can be set on many records at once: a field a record
    #: holds one value of, or a tag to add.
    settable: bool
    #: For each role, how many of `lacking` it is about, so "left off" and
    #: "outside the boxes" are not one number.
    by_role: Tuple[Tuple[str, int], ...] = ()
    #: The ids it was asked of, for merging the views' needs into one list.
    asked_ids: Tuple[str, ...] = ()


class ViewNeeds(NamedTuple):
    view_id: str
    title: str
    category: str
    kind: str
    #: The subject a subject view was drawn for, or "".
    subject: str
    #: Records drawn.
    drawn: int
    #: Records left off for want of a field and nothing else, by id.
    kept_off: Tuple[str, ...]
    needs: List[Need]
    #: `empty` (draws nothing), `thin` (as many left off for want of a field
    #: as drawn, or most of what is drawn outside its outermost boxes),
    #: `full`, or `subject` (a view drawn for one thing at a time, given
    #: none, whose needs are said on each drawing).
    state: str
    #: Why the view could not be read, for a view that is broken rather than
    #: empty; "" otherwise.
    problem: str = ""
    #: Records the view's limit leaves off the drawing although the scope
    #: matched them. Their needs are counted all the same.
    cut: int = 0


def _blank(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == ()


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(v) for v in value]
    return [str(value)]


def _spec(type_name: str, field: str):
    entity_type = ENTITY_TYPES.get(type_name)
    if entity_type is None:
        return None
    return next((f for f in entity_type.fields if f.name == field), None)


def _pk(type_name: str) -> str:
    return ENTITY_TYPES[type_name].pk


def _id(record: dict) -> str:
    return str(record.get(_pk(record["_type"])) or "")


def asked_of(record: dict, field: str) -> bool:
    """Whether a field is asked of this record at all: a cloud placement
    only of a record on a cloud, or of one not yet said to be anywhere."""
    if field not in CLOUD_PLACED:
        return True
    where = str(record.get("cloud_provider") or record.get("hosting") or "")
    return not where or where in CLOUDS


def _gap_field(type_name: str, key: str, expected: Any) -> bool:
    """Whether a blank in this `where` key is a gap: the clause asks for the
    field filled, or every record of the type must have it."""
    if key in UNASKED or "@" in key or key.startswith(("tags_", "has_")) or key in _DELIBERATE:
        return False
    if isinstance(expected, dict):
        return bool(expected.get("exists")) if "exists" in expected else False
    spec = _spec(type_name, key)
    return spec is not None and spec.required


# ---------------------------------------------------------------------------
# The needs a view declares, before anything is counted.
# ---------------------------------------------------------------------------


def drawn_types(view: View) -> List[str]:
    """The types a view draws: what its scope includes and pins, and what
    its expansion reaches."""
    out: List[str] = []

    def add(name: Optional[str]) -> None:
        if name in ENTITY_TYPES and name not in out:
            out.append(name)

    for clause in view.scope.get("include") or []:
        add(clause.get("type") if isinstance(clause, dict) else None)
    for rule in view.scope.get("expand") or []:
        if not isinstance(rule, dict):
            continue
        kept = _as_list(rule.get("types"))
        if kept:
            for name in kept:
                add(name)
            continue
        relation = rule.get("relation")
        if relation in RELATION_TYPES:
            add(RELATION_TYPES[relation].left)
            add(RELATION_TYPES[relation].right)
        elif relation == "interfaces":
            add("systems")
    return out


def declared(view: View, types: Sequence[str] = ()) -> List[Tuple[str, str, str, str]]:
    """Every (type, field, kind, role) the view reads, in the order it reads
    them: the scope, the boundaries, the lines, the shade, the order. A pin
    adds its type through `types`."""
    out: List[Tuple[str, str, str, str]] = []
    drawn = list(drawn_types(view))
    for name in types:
        if name not in drawn:
            drawn.append(name)

    def add(type_name: str, field: str, kind: str, role: str) -> None:
        entry = (type_name, field, kind, role)
        if entry not in out:
            out.append(entry)

    def each_declaring(field: str, role: str) -> None:
        if field in UNASKED:
            return
        for type_name in drawn:
            if _spec(type_name, field) is not None:
                add(type_name, field, "field", role)

    for clause in view.scope.get("include") or []:
        if not isinstance(clause, dict) or clause.get("type") not in ENTITY_TYPES:
            continue
        type_name = clause["type"]
        for key, expected in (clause.get("where") or {}).items():
            if key in ("tags_any", "tags_all"):
                add(type_name, "tags", "tag", "selects")
            elif key in ("has_any", "has_all"):
                for relation in _as_list(expected):
                    add(type_name, relation, "relation", "selects")
            elif "@" in key and "{" not in key:
                add(type_name, key.split("@", 1)[0], "relation", "selects")
            elif _gap_field(type_name, key, expected):
                add(type_name, key, "field", "selects")

    for field in view.group_by or ():
        if field == "type" or "{" in field:
            continue
        if "@" in field:
            relation = RELATION_TYPES.get(field.split("@", 1)[0])
            if relation is not None:
                for type_name in drawn:
                    if type_name in (relation.left, relation.right):
                        add(type_name, relation.name, "relation", "groups")
            continue
        each_declaring(field, "groups")

    for spec in view.edges or ():
        via = str(spec.get("via") or "") if isinstance(spec, dict) else ""
        if not via:
            continue
        if via == "owner":
            each_declaring("owner_org_id", "lines")
        elif via == "interfaces":
            if "systems" in drawn:
                add("systems", "interfaces", "relation", "lines")
        elif via in RELATION_TYPES:
            relation = RELATION_TYPES[via]
            for type_name in drawn:
                if type_name in (relation.left, relation.right):
                    add(type_name, via, "relation", "lines")
        else:
            for type_name in drawn:
                field = _spec(type_name, via)
                # A field naming a record of its own type is a hierarchy, and
                # its blank is the top of it, not a gap.
                if field is not None and field.ref and field.ref != type_name and via not in UNASKED:
                    add(type_name, via, "field", "lines")

    color_by = (view.style or {}).get("color_by")
    if color_by and color_by != "type":
        each_declaring(str(color_by), "shades")
    if view.order_by:
        each_declaring(str(view.order_by), "orders")
    return out


# ---------------------------------------------------------------------------
# Counting.
# ---------------------------------------------------------------------------

#: How one key of a `where` went for a record: passed, failed for want of a
#: field the clause needs filled, of a tag or of a relation, or failed on
#: purpose (a value the clause leaves out, an id it does not name).
PASS, BLANK, TAG, RELATION, OFF = "pass", "blank", "tag", "relation", "off"


def _verdict(model: Model, record: dict, key: str, expected: Any) -> str:
    if matches(model, record, {key: expected}):
        return PASS
    if key in ("tags_any", "tags_all"):
        return TAG
    if key in ("has_any", "has_all"):
        return RELATION
    if key in _DELIBERATE:
        return OFF
    if "@" in key:
        return RELATION if _value_or_said(model, record, key) in (None, "") else OFF
    if not _blank(record.get(key)):
        return OFF
    return BLANK if _gap_field(record["_type"], key, expected) else OFF


class _Tally:
    def __init__(self, entries: Sequence[Tuple[str, str, str, str]]) -> None:
        self.order = []
        self.asked: Dict[Tuple[str, str, str], Set[str]] = {}
        self.lacking: Dict[Tuple[str, str, str], Dict[str, Set[str]]] = {}
        for type_name, field, kind, role in entries:
            key = (type_name, field, kind)
            if key not in self.asked:
                self.order.append(key)
                self.asked[key] = set()
                self.lacking[key] = {}
            self.lacking[key].setdefault(role, set())

    def ask(self, key: Tuple[str, str, str], role: str, entity_id: str, lacks: bool) -> None:
        if key not in self.asked or role not in self.lacking[key]:
            return
        self.asked[key].add(entity_id)
        if lacks:
            self.lacking[key][role].add(entity_id)


def _deliberately_off(model: Model, view: View) -> Set[str]:
    off: Set[str] = set()
    for clause in view.scope.get("exclude") or []:
        type_name = clause.get("type") if isinstance(clause, dict) else None
        if type_name in ENTITY_TYPES:
            for record in model.all_of(type_name):
                if matches(model, record, clause.get("where")):
                    off.add(_id(record))
    return off | set(_as_list(view.scope.get("hide")))


def _count_scope(model: Model, view: View, drawn: Set[str], tally: _Tally) -> Set[str]:
    """The scope's needs counted; returns the records left off for want of
    a field and nothing else."""
    off = _deliberately_off(model, view)
    kept_off: Set[str] = set()
    for clause in view.scope.get("include") or []:
        if not isinstance(clause, dict) or clause.get("type") not in ENTITY_TYPES:
            continue
        type_name = clause["type"]
        where = clause.get("where") or {}
        if not where:
            continue
        for record in model.all_of(type_name):
            entity_id = _id(record)
            if entity_id in off:
                continue
            verdicts = {key: _verdict(model, record, key, expected) for key, expected in where.items()}
            if entity_id in drawn:
                for key, verdict in verdicts.items():
                    for need in _needs_of_key(type_name, key, where[key]):
                        tally.ask(need, "selects", entity_id, False)
                continue
            failed = {k: v for k, v in verdicts.items() if v != PASS}
            if not failed or OFF in failed.values():
                continue
            for key, verdict in failed.items():
                for need in _needs_of_key(type_name, key, where[key]):
                    tally.ask(need, "selects", entity_id, True)
            # Asked of the records it passes too, so the share is of both.
            for key, verdict in verdicts.items():
                if verdict == PASS:
                    for need in _needs_of_key(type_name, key, where[key]):
                        tally.ask(need, "selects", entity_id, False)
            if all(v == BLANK for v in failed.values()):
                kept_off.add(entity_id)
    return kept_off


def _needs_of_key(type_name: str, key: str, expected: Any) -> List[Tuple[str, str, str]]:
    if key in ("tags_any", "tags_all"):
        return [(type_name, "tags", "tag")]
    if key in ("has_any", "has_all"):
        return [(type_name, relation, "relation") for relation in _as_list(expected)]
    if "@" in key:
        return [(type_name, key.split("@", 1)[0], "relation")]
    return [(type_name, key, "field")]


def _count_drawing(model: Model, view: View, nodes: Sequence[Any], edges: Sequence[Any], tally: _Tally) -> None:
    """What the drawn records lack of the boundaries, lines, shade and order."""

    def field_need(field: str, role: str) -> None:
        for node in nodes:
            if asked_of(node.record, field):
                tally.ask((node.entity_type, field, "field"), role, node.key, _blank(node.record.get(field)))

    for field in view.group_by or ():
        if field == "type" or "{" in field:
            continue
        if "@" in field:
            name = field.split("@", 1)[0]
            for node in nodes:
                said = _value_or_said(model, node.record, field.split("#", 1)[0])
                tally.ask((node.entity_type, name, "relation"), "groups", node.key, not said)
            continue
        field_need(field, "groups")

    linked: Set[Tuple[str, str]] = set()
    for edge in edges:
        linked.add((edge.kind, edge.source))
        linked.add((edge.kind, edge.target))
    for spec in view.edges or ():
        via = str(spec.get("via") or "") if isinstance(spec, dict) else ""
        if via == "owner":
            field_need("owner_org_id", "lines")
        elif via == "interfaces":
            for node in nodes:
                tally.ask((node.entity_type, "interfaces", "relation"), "lines", node.key,
                          ("interface", node.key) not in linked)
        elif via in RELATION_TYPES:
            for node in nodes:
                tally.ask((node.entity_type, via, "relation"), "lines", node.key, (via, node.key) not in linked)
        elif via:
            field_need(via, "lines")

    color_by = (view.style or {}).get("color_by")
    if color_by and color_by != "type":
        field_need(str(color_by), "shades")
    if view.order_by:
        field_need(str(view.order_by), "orders")


def values_of(model: Model, type_name: str, field: str,
              lanes: Optional[Sequence[str]] = None) -> Tuple[Tuple[str, str], ...]:
    """What a field takes, in the order a person would choose from: the
    view's lanes, the field's own list, the records a reference names by
    name, or the values the estate already uses, the most used first."""
    if lanes:
        return tuple((str(v), str(v)) for v in lanes)
    spec = _spec(type_name, field)
    if spec is not None and spec.enum:
        return tuple((str(v), str(v)) for v in spec.enum)
    if spec is not None and spec.ref:
        named = sorted(((str(r.get(_pk(spec.ref)) or ""), str(r.get("name") or r.get(_pk(spec.ref)) or ""))
                        for r in model.all_of(spec.ref)), key=lambda pair: (pair[1].lower(), pair[0]))
        return tuple(pair for pair in named if pair[0])
    used = Counter(str(r.get(field)) for r in model.all_of(type_name)
                   if not _blank(r.get(field)) and not isinstance(r.get(field), (list, dict)))
    return tuple((value, value) for value, _n in sorted(used.items(), key=lambda kv: (-kv[1], kv[0]))[:VALUES_SHOWN])


def _tag_values(view: View, type_name: str) -> Tuple[Tuple[str, str], ...]:
    out: List[str] = []
    for clause in view.scope.get("include") or []:
        if isinstance(clause, dict) and clause.get("type") == type_name:
            for key in ("tags_any", "tags_all"):
                for tag in _as_list((clause.get("where") or {}).get(key)):
                    if tag not in out:
                        out.append(tag)
    return tuple((t, t) for t in out)


def _state(view: View, drawn: int, kept_off: int, needs: Sequence[Need], lines: int) -> str:
    if not drawn:
        return "empty"
    if kept_off and kept_off >= THIN * (drawn + kept_off):
        return "thin"
    # A diagram is read along its lines; one that draws none is a list of
    # boxes. A map or a table is not judged on them.
    if view.kind == "diagram" and view.edges and not lines:
        return "thin"
    fields = [f for f in view.group_by or () if f != "type"]
    outer = fields[0] if fields and "@" not in fields[0] and "{" not in fields[0] else None
    if outer is not None and outer == (view.group_by or [None])[0]:
        asked = outside = 0
        for need in needs:
            if need.field == outer and need.kind == "field" and "groups" in need.roles:
                asked += need.asked
                outside += dict(need.by_role).get("groups", 0)
        if asked and outside >= THIN * asked:
            return "thin"
    return "full"


def needs_of(model: Model, view: View, subject: str = "", graph=None) -> ViewNeeds:
    """What one view needs, and how many records lack each thing. A view
    that takes a subject is read bound (`query.bind`); given unbound, its
    state is `subject` and nothing is counted, since what it draws depends
    on the one thing it is drawn for. `graph` is the view already resolved,
    when the caller has it."""
    base = dict(view_id=view.view_id, title=view.title, category=view.category, kind=view.kind,
                subject=subject)
    if view.parameters and _TOKEN_IN_SCOPE.search(repr(view.scope)):
        return ViewNeeds(drawn=0, kept_off=(), needs=[], state="subject", **base)
    problem = ""
    if graph is None:
        try:
            graph = resolve(model, view)
        except ViewError as exc:
            if "selected no entities" not in str(exc):
                problem = str(exc)
            graph = None
    # Counted over everything the view selects, not the first sixty it
    # shows: a landscape cut at its limit is still about them all. What it
    # draws is said as the render draws it; this said "109 drawn" of a table
    # the render cut to sixty.
    whole = graph
    if graph is not None and graph.cut:
        whole = resolve(model, view._replace(limits=dict(view.limits or {}, max_nodes=0)))
    nodes = whole.nodes if whole is not None else []
    edges = whole.edges if whole is not None else []
    pinned = sorted({kind for kind, _id in located(model, view.scope.get("pin"))})
    tally = _Tally(declared(view, pinned))
    drawn = {node.key for node in nodes}
    kept_off = _count_scope(model, view, drawn, tally)
    _count_drawing(model, view, nodes, edges, tally)
    shown = len(graph.nodes) if graph is not None else 0

    needs: List[Need] = []
    for key in tally.order:
        type_name, field, kind = key
        roles = tally.lacking[key]
        lacking: Set[str] = set()
        for ids in roles.values():
            lacking |= ids
        if kind == "field":
            values = values_of(model, type_name, field, view.lanes.get(field))
        elif kind == "tag":
            values = _tag_values(view, type_name)
        else:
            values = ()
        needs.append(Need(
            type=type_name, field=field, kind=kind,
            roles=tuple(r for r in ROLES if r in roles),
            asked=len(tally.asked[key]),
            lacking=tuple(sorted(lacking)),
            values=values, settable=kind in ("field", "tag"),
            by_role=tuple((r, len(roles[r])) for r in ROLES if r in roles),
            asked_ids=tuple(sorted(tally.asked[key])),
        ))
    return ViewNeeds(drawn=shown, kept_off=tuple(sorted(kept_off)), needs=needs,
                     state="empty" if problem else _state(view, len(drawn), len(kept_off), needs, len(edges)),
                     problem=problem, cut=len(drawn) - shown, **base)


class FieldNeed(NamedTuple):
    """One field across every diagram that reads it: the one list."""

    type: str
    field: str
    kind: str
    #: The records lacking it on any of the views, by id.
    lacking: Tuple[str, ...]
    #: How many records those views ask it of.
    asked: int
    #: The views reading it, as (view id, title, roles, how many lack it there).
    views: Tuple[Tuple[str, str, Tuple[str, ...], int], ...]
    values: Tuple[Tuple[str, str], ...]
    settable: bool


def estate_needs(model: Model, views: Iterable[View]) -> List[ViewNeeds]:
    """Every view's needs, a subject view's left as `subject`."""
    return [needs_of(model, view) for view in views]


def by_field(model: Model, results: Sequence[ViewNeeds], views: Sequence[View] = ()) -> List[FieldNeed]:
    """The one list: each field, tag and relation the diagrams read, the
    records lacking it on any of them, and which diagrams read it; fields
    first, the most lacking first."""
    lanes: Dict[str, Sequence[str]] = {}
    for view in views:
        for field, order in (view.lanes or {}).items():
            lanes.setdefault(field, order)
    merged: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for result in results:
        for need in result.needs:
            key = (need.type, need.field, need.kind)
            entry = merged.setdefault(key, {"lacking": set(), "asked": set(), "views": [],
                                            "values": need.values, "settable": need.settable})
            entry["lacking"] |= set(need.lacking)
            entry["asked"] |= set(need.asked_ids)
            entry["views"].append((result.view_id, result.title, need.roles, len(need.lacking)))
            if need.kind == "tag":
                entry["values"] = tuple(dict.fromkeys(tuple(entry["values"]) + tuple(need.values)))
    out = []
    for (type_name, field, kind), entry in merged.items():
        values = entry["values"]
        if kind == "field" and field in lanes:
            values = values_of(model, type_name, field, lanes[field])
        if kind == "relation":
            # A line is missing from a drawing when its other end is not on
            # it, which differs drawing by drawing; across them all, what a
            # record lacks is any row of the relation at all.
            entry["lacking"] = {i for i in entry["asked"] if not _related(model, i, field)}
        out.append(FieldNeed(type_name, field, kind, tuple(sorted(entry["lacking"])), len(entry["asked"]),
                             tuple(entry["views"]), values, entry["settable"]))
    out.sort(key=lambda n: (KINDS.index(n.kind), -len(n.lacking), -n.asked, n.type, n.field))
    return out


def states(results: Sequence[ViewNeeds]) -> Dict[str, int]:
    """How many views are in each state, every state named."""
    out = {state: 0 for state in ("full", "thin", "empty", "subject")}
    for result in results:
        out[result.state] = out.get(result.state, 0) + 1
    return out


#: What a role means for a record lacking the field, in words.
ROLE_WORDS = {
    "selects": "left off without it",
    "groups": "outside the boxes",
    "lines": "drawn without the line",
    "shades": "unshaded",
    "orders": "placed last",
}
