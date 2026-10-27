"""View resolution: turn a declarative view spec into a concrete graph.

A view never names the things it draws. It names a filter. That is the whole
reason a new application needs no diagram edits: it appears in every view whose
filter it already matches.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Set, Tuple

from .archetype import ArchetypeError, substitute
from .loader import load_folder
from .model import Model
from .palette import ORDINAL
from .schema import ENTITY_TYPES, NETWORK_ZONES, RELATION_TYPES

#: Edges that are not relation tables: system-to-system through an interface
#: entity, and the data asset's system of record foreign key.
PSEUDO_EDGES = {
    "interfaces": ("systems", "systems"),
    "source_of_truth": ("data_assets", "systems"),
    # Ownership is a field, not a relation row, but an accountability diagram
    # needs to draw it. Handled like the others rather than forcing every
    # `owner_org_id` to be duplicated into a relation table.
    "owner": ("org_units", "systems"),
}


class ViewError(ValueError):
    """A view spec is malformed or resolves to nothing usable."""


class Node(NamedTuple):
    key: str
    label: str
    entity_type: str
    #: What to sort by inside a boundary. Numeric where the field is numeric,
    #: so stage 10 follows stage 9 rather than stage 1.
    sort_key: Tuple[int, str]
    #: Enclosing boundaries, outermost first. A single-level `group_by` yields
    #: one entry; a list yields nested containers, which is how an account /
    #: region / network-zone diagram gets drawn.
    groups: Tuple[str, ...]
    style_key: str
    record: dict
    #: The field each level of `groups` came from, so a boundary is known by
    #: kind and not by depth: a SaaS system with no account or region draws
    #: its network tier at depth two, and it is still a network tier.
    group_fields: Tuple[str, ...] = ()

    @property
    def group(self) -> str:
        """The innermost boundary. Kept for callers that want one label."""
        return self.groups[-1] if self.groups else ""


class Edge(NamedTuple):
    source: str
    target: str
    label: str
    kind: str
    #: The interface this edge draws, when it draws one, so a flow's hops can
    #: be found on the diagram. Blank for every other kind of edge.
    ref: str = ""


class ViewGraph(NamedTuple):
    view: "View"
    nodes: List[Node]
    edges: List[Edge]
    #: Every distinct boundary path, outermost first, in draw order. A parent
    #: always appears before its children.
    groups: List[Tuple[str, ...]]
    notes: List[str]
    #: How many of the things the scope matched the view's limit left off;
    #: 0 when nothing was cut.
    cut: int = 0



#: Between the levels of a path a qualifier holds, outermost first:
#: "Sales and Service > Sales > Customer Offer".
PATH_SEPARATOR = " > "

#: Fields that name the same container as `cloud_provider`.
_PROVIDER_FIELDS = ("cloud_provider", "hosting")


def group_kinds(graph: "ViewGraph") -> Dict[Tuple[str, ...], Tuple[str, str]]:
    """What each boundary is: the field it was grouped by, and the provider
    it belongs to -- the provider level of its own path where the view
    groups by one, else the provider most of the things inside it carry.
    Both are learned from the nodes inside rather than from depth, because
    a partially populated record collapses its empty levels. The renderers
    draw a region as a region and an AWS one as AWS's."""
    fields = list(graph.view.group_by or [])
    kinds: Dict[Tuple[str, ...], Dict[str, int]] = {}
    providers: Dict[Tuple[str, ...], Dict[str, int]] = {}
    for node in graph.nodes:
        own = str(node.record.get("cloud_provider") or node.record.get("hosting") or "")
        node_fields = list(node.group_fields) + fields[len(node.group_fields):len(node.groups)]
        above = ""
        for depth in range(1, len(node.groups) + 1):
            prefix = node.groups[:depth]
            field = node_fields[depth - 1] if depth - 1 < len(node_fields) else ""
            if field in _PROVIDER_FIELDS:
                above = prefix[-1]
            votes = kinds.setdefault(prefix, {})
            votes[field] = votes.get(field, 0) + 1
            votes = providers.setdefault(prefix, {})
            votes[above or own] = votes.get(above or own, 0) + 1
    out: Dict[Tuple[str, ...], Tuple[str, str]] = {}
    for path in graph.groups:
        voted = kinds.get(path, {})
        if voted:
            kind = max(voted, key=voted.get)
        else:
            kind = fields[len(path) - 1] if len(path) - 1 < len(fields) else ""
        named = {k: v for k, v in providers.get(path, {}).items() if k}
        out[path] = (kind, max(named, key=named.get) if named else "")
    return out


#: The order categories are shown in: the business layer first, because that
#: is what the estate exists for, and the change views last.
VIEW_CATEGORIES = (
    "Business", "Application", "Data", "Technology", "Governance", "Change", "Other",
)

#: What kind of thing a view is, which decides how it should be drawn and how
#: big it is allowed to get.
#:
#: * `diagram` -- has a subject and a level. Read closely by someone about to
#:   change something, so shapes carry meaning and it should fit on a page.
#: * `map` -- no subject; everything, cut one way. Scanned rather than read,
#:   so it is allowed to be large and wants packing rather than ranking.
#: * `report` -- answers a question with a set. Its honest output is a table;
#:   drawing it as a graph adds nothing but the suggestion that the lines mean
#:   something.
#: An unreplaced `{token}` left in a bound scope.
_TOKEN_IN_SCOPE = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*(\|[^}]*)?\}")

#: A timeline draws the dated things in a view as bars on a calendar of
#: quarters, sectioned by whatever the view groups by; the undated things it
#: reaches are listed under each bar rather than drawn. Roadmaps and work
#: packages carried quarters for three rounds before anything drew them.
VIEW_KINDS = ("diagram", "map", "report", "timeline")

#: An architecture diagram past this many boxes has stopped being one. Maps and
#: reports have no such limit, because nobody reads them linearly.
DIAGRAM_MAX_NODES = 40


class Parameter(NamedTuple):
    """One thing a view has to be told before it can be drawn."""

    name: str
    #: Entity type the value must name, so the app can offer a picker and the
    #: engine can refuse a value that is not one.
    type: Optional[str] = None
    required: bool = True
    default: Optional[str] = None
    description: str = ""
    #: A field the value is one value of, for a subject that is a word on the
    #: records rather than a record: a business domain is `Servicing` on
    #: eight systems, and no record of its own. Set instead of `type`.
    field: Optional[str] = None


class View(NamedTuple):
    view_id: str
    title: str
    description: str
    #: Which shelf it sits on. Twenty-six views in one flat list is a list.
    category: str
    #: diagram, map or report. See `VIEW_KINDS`.
    kind: str
    #: What the view has to be told. Empty for the twenty-six that are about
    #: the whole estate.
    parameters: Sequence[Parameter]
    #: Which entities to render this view once for. A selection clause, the
    #: same shape as `scope.include`, naming the parameter it binds.
    render_for: Optional[dict]
    scope: dict
    group_by: Sequence[str]
    edges: Sequence[dict]
    node_label: str
    #: Field to order nodes by inside a boundary. Defaults to the label, which
    #: is right for a landscape and wrong for anything with a sequence in it.
    order_by: Optional[str]
    #: Direction inside a boundary. Left unset it is chosen from the shape of
    #: the graph, which is nearly always the right answer.
    group_direction: Optional[str]
    style: dict
    layout: str
    limits: dict
    renderers: Sequence[str]
    source_file: Optional[Path] = None
    #: The order the values of a grouped field are laid out in: a tier
    #: diagram reads edge to data whatever the edges say. Given on the view
    #: as `lanes`, else the field's reading order where it has one; `lanes:
    #: false` turns it off. Field name to ordered values.
    lanes: Dict[str, List[str]] = {}
    #: The section of its layer the view sits in, for a list that would
    #: otherwise run to eighteen titles under Business: "Capabilities",
    #: "Processes and value streams". Blank sits in the layer itself.
    section: str = ""
    #: Other views placed on this one as boundaries, read as they are now
    #: each time views are loaded (terrane.places): `{view, only, leave_out,
    #: parts}` each. Empty for every view not drawn on the canvas.
    places: Sequence[dict] = ()
    #: This view as its file says, before the views it places were merged
    #: in; None for a view that places nothing.
    own: Optional[Any] = None
    #: Where each thing on this drawing was put by hand, for a diagram
    #: arranged on the canvas: a box keyed by the boundaries it sits in and
    #: its id (`AWS / prod-lending / SYS-X`), a boundary by its path, each to
    #: its top-left corner `(x, y)` in the boundary around it. Empty for a
    #: drawing the layout places, which is every view written as a query.
    positions: Dict[str, Tuple[int, int]] = {}
    #: What the diagram draws of its own on the canvas -- shapes, text,
    #: notes, frames and free lines, none of them records -- as its file
    #: lists them (`terrane.annotations`). Empty for every view not drawn on
    #: the canvas.
    annotations: Sequence[dict] = ()
    #: The view one level above this one, for a view about one thing: a
    #: system's architecture goes up to its domain's landscape, and that to
    #: the application landscape. What the level above is drawn for is read
    #: off the subject (`terrane.levels`). None for a view with no level
    #: above it, which is every view about the whole estate.
    up: Optional[str] = None
    #: How it draws its own (`terrane.annotations.LOOKS`): Illustrated unless it says tiles.
    look: str = "illustrated"


def _enum_of(field: str) -> Sequence[str]:
    """The ordered values a field is declared with, on whichever entity type
    declares it; empty for a free field."""
    for entity_type in ENTITY_TYPES.values():
        for spec in entity_type.fields:
            if spec.name == field and getattr(spec, "enum", None):
                return tuple(spec.enum)
    return ()


def _ordered_values(field: str) -> Sequence[str]:
    """The reading order of a field that has one: the network tiers edge to
    data, a lifecycle status proposed to retired, the ordinal scales the
    legend lists in order. A field that is merely enumerated, a provider or
    a kind of actor, has no reading order, and its boundaries follow the
    edges unless the view says otherwise."""
    if field == "network_zone":
        return NETWORK_ZONES
    if field == "status":
        return _enum_of("status")
    return ORDINAL.get(field, ())


def _lanes_of(data: dict, group_by: Sequence[str]) -> Dict[str, List[str]]:
    """What order each grouped field's values are laid out in. `lanes` on
    the view is a list for the innermost `group_by` field or a mapping of
    field to values; a grouped field with a reading order and no `lanes`
    entry takes that order; `lanes: false` leaves every field to the
    edges."""
    raw = data.get("lanes")
    out: Dict[str, List[str]] = {}
    if raw is False:
        return out
    if isinstance(raw, dict):
        for field, values in raw.items():
            out[str(field)] = [str(v) for v in (values or [])]
    elif isinstance(raw, (list, tuple)):
        if not group_by:
            raise ViewError("view %s: lanes orders a group_by, and there is none" % data.get("view_id"))
        out[group_by[-1]] = [str(v) for v in raw]
    elif raw is not None:
        raise ViewError(
            "view %s: lanes is a list of values for the innermost group_by field, a mapping of "
            "field to values, or false" % data.get("view_id")
        )
    for field in group_by:
        if field not in out:
            order = _ordered_values(field)
            if order:
                out[field] = list(order)
    return out


def _parameters_of(data: dict) -> List[Parameter]:
    out: List[Parameter] = []
    for raw in data.get("parameters") or []:
        if isinstance(raw, str):
            out.append(Parameter(name=raw))
            continue
        if not isinstance(raw, dict) or "name" not in raw:
            raise ViewError("a view parameter needs a name")
        if raw.get("type") and raw["type"] not in ENTITY_TYPES:
            raise ViewError(
                "view parameter %r names an unknown entity type %r"
                % (raw["name"], raw["type"])
            )
        field = str(raw.get("field") or "").strip() or None
        if field and raw.get("type"):
            # One or the other: a record's id, or a word on the records.
            # Both would leave the picker not knowing which list to offer.
            raise ViewError(
                "view parameter %r takes a %s or a value of %s, not both"
                % (raw["name"], raw["type"], field)
            )
        if field and not any(spec.name == field for t in ENTITY_TYPES.values() for spec in t.fields):
            raise ViewError("view parameter %r names a field no record has: %r" % (raw["name"], field))
        out.append(Parameter(
            name=str(raw["name"]),
            type=raw.get("type"),
            required=bool(raw.get("required", True)),
            default=raw.get("default"),
            description=str(raw.get("description") or ""),
            field=field,
        ))
    return out


def subject_slug(value: Any) -> str:
    """How one subject's copy of a view is named after it:
    `system-architecture--sys-auth-switch`, and for a subject that is words
    rather than an id, `domain-landscape--risk-and-compliance`. An id is
    already its own slug once lowered."""
    return re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")


def field_values(model: Model, field: str, type_name: Optional[str] = None) -> List[str]:
    """The values a field takes on the model's records, or on one type's,
    sorted: the subjects a view about one value of the field can be drawn
    for."""
    kinds = [type_name] if type_name else list(ENTITY_TYPES)
    found = set()
    for kind in kinds:
        for record in model.all_of(kind):
            value = record.get(field)
            if value not in (None, "") and not isinstance(value, (list, dict)):
                found.add(str(value))
    return sorted(found)


def _keys_bound(value: Any, ids: Dict[str, Any]) -> Any:
    """A bound scope's mapping keys, bound too: a view about one framework
    filters on `capability_references_framework@{framework}`, and the token
    is in the key. Done here rather than in the archetypes' `substitute`,
    whose templates never put a token in a key."""
    if isinstance(value, dict):
        return {(substitute(k, ids) if isinstance(k, str) and "{" in k else k): _keys_bound(v, ids)
                for k, v in value.items()}
    if isinstance(value, list):
        return [_keys_bound(v, ids) for v in value]
    return value


def bind(
    view: View,
    values: Optional[Dict[str, str]] = None,
    model: Optional[Model] = None,
) -> View:
    """A view with its parameters filled in, ready to resolve.

    Substitution happens here rather than at query time, so everything
    downstream -- resolving, rendering, the app -- deals with an ordinary view
    and needs to know nothing about parameters.

    The scope binds to the id, because that is what it matches on. The title
    and description bind to the name, because a diagram titled
    `SYS-AUTH-SWITCH` is a diagram nobody wants.
    """
    if not view.parameters:
        return view
    supplied = dict(values or {})
    ids: Dict[str, Any] = {}
    names: Dict[str, Any] = {}
    for param in view.parameters:
        value = supplied.get(param.name, param.default)
        if value in (None, ""):
            if param.required:
                raise ViewError(
                    "view %s needs a value for %r" % (view.view_id, param.name)
                )
            value = ""
        ids[param.name] = value
        readable = value
        if model is not None and param.type and value:
            record = model.get(param.type, str(value))
            if record is None:
                raise ViewError(
                    "view %s: %r is not a %s" % (view.view_id, value, param.type)
                )
            readable = record.get("name") or value
        if model is not None and param.field and value and str(value) not in field_values(model, param.field):
            # A domain nobody's records name draws an empty landscape that
            # looks like a domain with nothing in it.
            raise ViewError(
                "view %s: no record has %s %r"
                % (view.view_id, param.field.replace("_", " "), value)
            )
        names[param.name] = readable

    try:
        scope = _keys_bound(substitute(view.scope, ids), ids)
        title = substitute(view.title, names)
        description = substitute(view.description, names)
        # A view about one framework groups by that framework's paths: the
        # group_by names the parameter as the scope does.
        group_by = [substitute(field, ids) for field in view.group_by]
    except ArchetypeError as exc:
        raise ViewError(str(exc))
    return view._replace(scope=scope, title=title, description=description, group_by=group_by)


def render_targets(model: Model, view: View) -> List[Tuple[str, str]]:
    """The values a view should be rendered once for, from `render_for`.

    A high-criticality system with no architecture diagram is the gap this
    closes, so the selection is a query over the model rather than a list
    somebody has to keep up to date.
    """
    spec = view.render_for
    if not spec:
        return []
    parameter = spec.get("parameter") or (view.parameters[0].name if view.parameters else "")
    type_name = spec.get("type")
    if type_name not in ENTITY_TYPES:
        raise ViewError(
            "view %s: render_for names an unknown entity type %r"
            % (view.view_id, type_name)
        )
    pk = ENTITY_TYPES[type_name].pk
    # A view about one value of a field is drawn once for each value the
    # selected records take: a landscape per business domain the systems
    # name, so a ninth domain gets its drawing without anyone listing it.
    field = spec.get("field")
    out = []
    seen = set()
    for record in model.all_of(type_name):
        if matches(model, record, spec.get("where")):
            value = record.get(field) if field else record[pk]
            if value in (None, "") or str(value) in seen:
                continue
            seen.add(str(value))
            out.append((parameter, str(value)))
    out.sort(key=lambda pair: pair[1])
    limit = int(spec.get("limit", 60) or 0)
    if limit and len(out) > limit:
        # Silently rendering the first N would look like the rest do not
        # qualify; the caller reports what was dropped.
        out = out[:limit]
    return out


def _kind_of(data: dict) -> str:
    """The declared kind, or a guess from the shape of the view.

    Guessing is deliberate rather than defaulting to `diagram`: an unmarked
    view that groups by entity type is almost always a report, and calling it
    a diagram is how six of them ended up being drawn as graphs.
    """
    declared = str(data.get("kind") or "").strip().lower()
    if declared in VIEW_KINDS:
        return declared
    group_by = _as_list(data.get("group_by"))
    if group_by == ["type"]:
        return "report"
    return "map" if not data.get("edges") else "diagram"


def parse_view(data: dict, source: Optional[Path] = None) -> View:
    if not isinstance(data, dict) or "view_id" not in data:
        raise ViewError("%s: missing view_id" % (source or "<view>"))
    return View(
        view_id=data["view_id"],
        title=data.get("title") or data["view_id"],
        description=data.get("description", "") or "",
        category=str(data.get("category") or "Other"),
        kind=_kind_of(data),
        parameters=_parameters_of(data),
        render_for=data.get("render_for") or None,
        scope=data.get("scope") or {},
        group_by=_as_list(data.get("group_by")),
        edges=list(data.get("edges") or []),
        node_label=data.get("node_label", "name"),
        order_by=data.get("order_by") or None,
        group_direction=(data.get("group_direction") or "").upper() or None,
        style=data.get("style") or {},
        layout=data.get("layout", "LR"),
        limits=data.get("limits") or {},
        renderers=list(data.get("renderers") or ["mermaid"]),
        lanes=_lanes_of(data, _as_list(data.get("group_by"))),
        source_file=source,
        section=str(data.get("section") or "").strip(),
        places=_places_of(data),
        positions=_positions_of(data),
        annotations=_annotations_of(data),
        up=str(data.get("up") or "").strip() or None,
        look=_look_of(data),
    )


def _look_of(data: dict) -> str:
    """How the diagram draws its own: Illustrated unless it says Icon tiles."""
    from .annotations import DEFAULT_LOOK, LOOKS

    raw = data.get("look")
    if raw in (None, ""):
        return DEFAULT_LOOK
    if raw not in LOOKS:
        raise ViewError("view %s: look is one of %s" % (data.get("view_id"), ", ".join(LOOKS)))
    return str(raw)


#: Between the boundaries a thing sits in, and between them and its id, in
#: a key of `positions`. The app's crumb uses the same mark.
POSITION_SEP = " / "


def position_key(path: Sequence[str], key: str = "") -> str:
    """The key a box (its boundaries and its id) or a boundary (its path
    alone) is kept under in `positions`."""
    return POSITION_SEP.join([str(p) for p in path] + ([str(key)] if key else []))


def _positions_of(data: dict) -> Dict[str, Tuple[int, int]]:
    """Where things were put by hand, each a pair of whole pixels. A key
    that names nothing on the drawing is kept, not refused: an account
    folded off the diagram comes back where it was."""
    raw = data.get("positions")
    if raw in (None, "", {}):
        return {}
    where = "view %s: positions" % data.get("view_id")
    if not isinstance(raw, dict):
        raise ViewError("%s is a mapping of what was placed to its corner, [x, y]" % where)
    out: Dict[str, Tuple[int, int]] = {}
    for key, value in raw.items():
        name = str(key).strip()
        # A bool is an int to Python and a slip of the hand to anyone else.
        if (not name or not isinstance(value, (list, tuple)) or len(value) != 2
                or any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in value)):
            raise ViewError("%s: %s should be [x, y], two numbers" % (where, name or "a key"))
        out[name] = (int(round(value[0])), int(round(value[1])))
    return out


def _annotations_of(data: dict) -> List[dict]:
    """The diagram's own shapes, checked as `terrane.annotations` reads them."""
    from .annotations import AnnotationError, read

    try:
        return read(data.get("annotations"), "view %s: annotations" % data.get("view_id"))
    except AnnotationError as exc:
        raise ViewError(str(exc)) from None


def _places_of(data: dict) -> List[dict]:
    """The views a view places, each a mapping; a bare id is the place of
    that view whole."""
    raw = data.get("places")
    if raw in (None, "", []):
        return []
    if not isinstance(raw, list):
        raise ViewError("view %s: places is a list of views to place" % data.get("view_id"))
    return [{"view": item} if isinstance(item, str) else item for item in raw]


def load_views(folder: Path) -> List[View]:
    views: List[View] = []
    seen: Set[str] = set()
    for path, data in load_folder(folder):
        view = parse_view(data, path)
        if view.view_id in seen:
            raise ViewError("duplicate view_id %r" % view.view_id)
        seen.add(view.view_id)
        views.append(view)
    order = {name: index for index, name in enumerate(VIEW_CATEGORIES)}
    # A view placing another in this folder is drawn with it from here on;
    # one placing a shipped view is completed by `estate.views_of`.
    from .places import with_places
    return with_places(sorted(
        views,
        key=lambda v: (order.get(v.category, len(order)), v.title.lower(), v.view_id),
    ))


# -- filtering ---------------------------------------------------------


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(v) for v in value]
    return [str(value)]


def matches(model: Model, record: dict, where: Optional[dict]) -> bool:
    """Evaluate one `where` clause against one record."""
    if not where:
        return True
    tags = set(model.tags(record))
    for key, expected in where.items():
        if key == "tags_any":
            if not tags & set(_as_list(expected)):
                return False
        elif key == "tags_all":
            if not set(_as_list(expected)) <= tags:
                return False
        elif key == "tags_none":
            # Excluding by tag is as common as including by one: "the stack,
            # but not the network fabric" has no positive tag to filter on.
            if tags & set(_as_list(expected)):
                return False
        elif key in ("has_any", "has_all", "has_none"):
            # Whether a relation exists at all, which no field on the record
            # can answer. `render_for` is what wanted it: the governance
            # diagram of a system with no control, no policy and no capability
            # to inherit one through is a single box, and the coverage report
            # says that better than a picture of nothing does.
            #
            # Resolution goes through `_related`, the same function `expand`
            # uses, so a `has_` filter and the expansion rule it guards agree
            # by construction rather than by both being edited together. That
            # also means an unknown relation name raises here, as it does
            # there, instead of quietly matching nothing.
            pk = ENTITY_TYPES[record["_type"]].pk
            entity_id = str(record.get(pk, ""))
            wanted = _as_list(expected)
            present = {r for r in wanted if _related(model, entity_id, r)}
            if key == "has_any" and not present:
                return False
            if key == "has_all" and present != set(wanted):
                return False
            if key == "has_none" and present:
                return False
        elif key == "id_in":
            pk = ENTITY_TYPES[record["_type"]].pk
            if str(record.get(pk)) not in set(_as_list(expected)):
                return False
        elif key == "id_prefix":
            pk = ENTITY_TYPES[record["_type"]].pk
            if not any(str(record.get(pk, "")).startswith(p) for p in _as_list(expected)):
                return False
        elif isinstance(expected, dict) and "not" in expected:
            if str(_value_or_said(model, record, key)) in set(_as_list(expected["not"])):
                return False
        elif isinstance(expected, dict) and "exists" in expected:
            present = _value_or_said(model, record, key) not in (None, "")
            if present is not bool(expected["exists"]):
                return False
        else:
            if str(_value_or_said(model, record, key)) not in set(_as_list(expected)):
                return False
    return True


def _value_or_said(model: Model, record: dict, key: str):
    """A record's field, or what a relation says when the key is written
    `relation@target`, so a filter can ask for the capabilities a framework
    places as easily as for the ones with a field set."""
    said = _through(model, record, key)
    return said if said is not None else record.get(key, "")


def _select(model: Model, clauses: Sequence[dict]) -> Set[Tuple[str, str]]:
    selected: Set[Tuple[str, str]] = set()
    for clause in clauses or []:
        type_name = clause.get("type")
        if type_name not in ENTITY_TYPES:
            raise ViewError("scope clause has unknown type %r" % type_name)
        pk = ENTITY_TYPES[type_name].pk
        for record in model.all_of(type_name):
            if matches(model, record, clause.get("where")):
                selected.add((type_name, str(record[pk])))
    return selected


def _expand(
    model: Model, seed: Set[Tuple[str, str]], rules: Sequence[dict]
) -> Set[Tuple[str, str]]:
    """Pull in neighbors reachable from the seed, per expansion rules."""
    result = set(seed)
    for rule in rules or []:
        depth = int(rule.get("depth", 1))
        keep_types = set(_as_list(rule.get("types"))) or None
        relation = rule.get("relation")
        frontier = set(result)
        for _ in range(max(depth, 0)):
            found: Set[Tuple[str, str]] = set()
            for _type_name, entity_id in frontier:
                for neighbor_id in _related(model, entity_id, relation):
                    located = model.find(neighbor_id)
                    if located is None:
                        continue
                    if keep_types and located[0] not in keep_types:
                        continue
                    candidate = (located[0], neighbor_id)
                    if candidate not in result:
                        found.add(candidate)
            if not found:
                break
            result |= found
            frontier = found
    return result


def reference_fields(name: Optional[str]) -> List[Tuple[str, Any]]:
    """Every (entity type, field) pair where `name` is a reference field.

    A field that points at another entity is a relationship the model already
    records, and a view should be able to follow it and draw it without
    anybody duplicating it into a relation table: a control's policy, a
    capability's parent, an org unit's parent. `owner` and `source_of_truth`
    predate this and keep their names.
    """
    if not name:
        return []
    found = []
    for type_name, entity_type in ENTITY_TYPES.items():
        for field in entity_type.fields:
            if field.name == name and field.ref:
                found.append((type_name, field))
    return found


def _related(model: Model, entity_id: str, relation: Optional[str]) -> Set[str]:
    if relation in (None, "any", "*"):
        return model.neighbors(entity_id)
    if relation == "interfaces":
        found = set()
        for record in model.all_of("interfaces"):
            src, dst = record.get("source_system_id"), record.get("target_system_id")
            if src == entity_id and dst:
                found.add(str(dst))
            if dst == entity_id and src:
                found.add(str(src))
        return found
    if relation == "owner":
        found = set()
        for type_name in ENTITY_TYPES:
            for record in model.all_of(type_name):
                owner = record.get("owner_org_id")
                pk = ENTITY_TYPES[type_name].pk
                if owner == entity_id and record.get(pk):
                    found.add(str(record[pk]))
                if record.get(pk) == entity_id and owner:
                    found.add(str(owner))
        return found
    if relation == "source_of_truth":
        found = set()
        for record in model.all_of("data_assets"):
            if record.get("source_of_truth") == entity_id:
                found.add(str(record["data_asset_id"]))
            if record.get("data_asset_id") == entity_id and record.get("source_of_truth"):
                found.add(str(record["source_of_truth"]))
        return found
    reference = reference_fields(relation)
    if reference:
        found = set()
        for type_name, field in reference:
            pk = ENTITY_TYPES[type_name].pk
            for record in model.all_of(type_name):
                target = record.get(field.name)
                if target in (None, ""):
                    continue
                if str(target) == entity_id and record.get(pk):
                    found.add(str(record[pk]))
                if str(record.get(pk)) == entity_id:
                    found.add(str(target))
        return found
    if relation not in RELATION_TYPES:
        raise ViewError("expand rule names unknown relation %r" % relation)
    spec = RELATION_TYPES[relation]
    found = set()
    for row in model.relation_rows(relation):
        left, right = row.get(spec.left_column), row.get(spec.right_column)
        if left == entity_id and right:
            found.add(str(right))
        if right == entity_id and left:
            found.add(str(left))
    return found


# -- graph building ----------------------------------------------------


def _through(model: Model, record: dict, key: str) -> Optional[str]:
    """What a relation says about a record, for a key written
    `relation@target`: the qualifier values of the record's rows in that
    relation whose other end is `target`, joined with "; " when there are
    several, or "" when there are none. None when the key is not of that
    form, so an ordinary field name passes through untouched.

    This is how a capability is placed on a framework's landscape. Where a
    capability sits in a framework is a row in
    `capability_references_framework`, one per placement, with the place
    written in the row's `ref` as a path in the framework's own terms:
    "Sales and Service > Sales > Customer Offer" for BIAN, "Service
    management > Incident Management" for ITIL, "Data Governance" for a
    framework with one level. Every framework is placed the same way, so
    one landscape view draws them all, and one an organization adds.
    """
    if "@" not in key:
        return None
    name, target = key.split("@", 1)
    # `relation@target#2` is the second level of the path the qualifier
    # holds ("Sales and Service > Sales > Customer Offer"), so a framework's
    # landscape nests as the framework does. A thing placed twice in one
    # framework is drawn at its first placement, alphabetically; the
    # inspector lists every one. Joining the two into one boundary named
    # for both was how the BIAN map came to have "Account Management; Cards".
    level = 0
    if "#" in target:
        target, wanted = target.rsplit("#", 1)
        if not wanted.isdigit() or int(wanted) < 1:
            raise ViewError("a path level is a number from 1, in %r" % key)
        level = int(wanted)
    relation = RELATION_TYPES.get(name)
    if relation is None:
        raise ViewError("unknown relation %r in %r" % (name, key))
    if not relation.qualifier:
        raise ViewError("relation %r carries no value to group by, in %r" % (name, key))
    entity_type = str(record.get("_type") or "")
    me = str(record.get(ENTITY_TYPES[entity_type].pk) or "") if entity_type in ENTITY_TYPES else ""
    values = set()
    for row in model.relation_rows(name):
        left, right = str(row.get(relation.left_column) or ""), str(row.get(relation.right_column) or "")
        if (relation.left == entity_type and left == me and right == target) or (
            relation.right == entity_type and right == me and left == target
        ):
            values.add(str(row.get(relation.qualifier) or target))
    if level:
        if not values:
            return ""
        parts = [part.strip() for part in sorted(values)[0].split(PATH_SEPARATOR)]
        return parts[level - 1] if level <= len(parts) else ""
    return "; ".join(sorted(values))


def _one_group(record: dict, field: str, model: Optional[Model] = None) -> str:
    if field == "type":
        return ENTITY_TYPES[record["_type"]].label.title()
    if model is not None:
        said = _through(model, record, field)
        if said is not None:
            return said or "Unassigned"
    value = record.get(field)
    if value in (None, ""):
        return "Unassigned"
    # A reference field holds an id. The boundary wants the name: nobody reads
    # a diagram whose boxes are labeled ORG-SERVICING and VS-ACQUIRE-CUSTOMER.
    if model is not None:
        entity_type = ENTITY_TYPES.get(record.get("_type") or "")
        declared = next(
            (f for f in entity_type.fields if f.name == field), None
        ) if entity_type else None
        if declared is not None and declared.ref:
            located = model.get(declared.ref, str(value))
            if located and located.get("name"):
                return str(located["name"])
    return str(value)


def _group_levels(
    record: dict, group_by: Sequence[str], model: Optional[Model] = None
) -> Tuple[Tuple[str, str], ...]:
    """The boundary levels one record sits in, outermost first, each as the
    field it came from and the value it has.

    Two collapses, both there because a partially populated record should draw
    a smaller diagram rather than a broken one:

    * a level that resolves to `Unassigned` is dropped wherever it appears, so
      a SaaS system with no account or region nests directly under its provider
      instead of sitting inside two empty boxes;
    * consecutive identical levels collapse to one, so an on-premise system
      whose provider and network zone are both `On-prem` gets a single
      boundary rather than a box inside an identical box.

    The field survives beside the value so the renderers know a collapsed
    path's levels by kind: `("SaaS", "Edge")` is a provider and a network
    tier, not a provider and an account.
    """
    levels: List[Tuple[str, str]] = []
    for field in group_by:
        value = _one_group(record, field, model)
        if value == "Unassigned":
            continue
        if levels and levels[-1][1] == value:
            continue
        levels.append((field, value))
    return tuple(levels)


def _groups_of(
    record: dict, group_by: Sequence[str], model: Optional[Model] = None
) -> Tuple[str, ...]:
    """Boundary path for one record, outermost first: its levels' values."""
    return tuple(value for _field, value in _group_levels(record, group_by, model))


def _sort_key(record: dict, order_by: Optional[str], label: str) -> Tuple[int, str]:
    raw = str(record.get(order_by) or "") if order_by else ""
    if not raw:
        return (10 ** 9, label.lower())
    digits = re.match(r"\s*(\d+)", raw)
    return (int(digits.group(1)) if digits else 10 ** 9, raw.lower())


def located(model: Model, ids: Any) -> Set[Tuple[str, str]]:
    """The things a view's `pin` or `hide` names, as (type, id). An id the
    model no longer holds is skipped here and reported by `terrane validate`
    as `view.stale_pin`, so a pin outliving its system is a finding rather
    than a view that will not draw."""
    out: Set[Tuple[str, str]] = set()
    for entity_id in _as_list(ids):
        found = model.find(entity_id)
        if found is not None:
            out.add((found[0], entity_id))
    return out


def resolve(model: Model, view: View) -> ViewGraph:
    """Evaluate a view against the model.

    A parameterized view must be bound first. Resolving one unbound would
    match a scope full of `{system}` tokens, select nothing, and look like an
    empty model rather than a missing argument.
    """
    if view.parameters and _TOKEN_IN_SCOPE.search(repr(view.scope)):
        raise ViewError(
            "view %s takes %s and has not been given %s"
            % (
                view.view_id,
                ", ".join(p.name for p in view.parameters),
                "them" if len(view.parameters) > 1 else "it",
            )
        )
    notes: List[str] = []
    include = view.scope.get("include")
    pinned = located(model, view.scope.get("pin"))
    # A diagram drawn on the canvas with nothing from the estate on it yet,
    # only shapes of its own, draws those and nothing of the model.
    if not include and not view.scope.get("pin") and view.annotations:
        return ViewGraph(view, [], [], [], notes)
    if not include and not pinned:
        raise ViewError("view %s has no scope.include" % view.view_id)

    named = _select(model, include) if include else set()
    selected = _expand(model, named, view.scope.get("expand") or [])
    # A pin is one thing, not a seed: pinning the SIEM on a context drawing
    # should not bring with it every system that sends it logs. It counts as
    # named, so a cut keeps it, which is the reason anyone pinned it.
    selected |= pinned
    named |= pinned
    for excluded in _select(model, view.scope.get("exclude") or []):
        selected.discard(excluded)
    # Hidden last, so a thing both pinned and hidden is hidden: the newer
    # wish, and the one a person can see is missing and undo.
    for hidden in located(model, view.scope.get("hide")):
        selected.discard(hidden)

    if not selected:
        raise ViewError("view %s selected no entities" % view.view_id)

    # The drawing is in id order. The cut, when there is one, keeps what the
    # scope names before what expansion reached: cut by id alone, a subject
    # view lost its subject -- the ledger's governance diagram matched
    # fifty-six entities, kept forty, and `SYS-` sorts after every `CAP-`
    # and `CTL-`, so the one system the diagram was about was the first
    # thing dropped.
    max_nodes = int(view.limits.get("max_nodes", 0) or 0)
    ordered = sorted(selected, key=lambda item: (item[0], item[1]))
    cut = 0
    if max_nodes and len(ordered) > max_nodes and view.kind == "report":
        # A report is a table and has no page to fit, so it is listed whole
        # and its limit only says the scope may have stopped filtering. Cut
        # at its sixty, the capability realization table kept the estate's
        # 55 systems and the first five capabilities by id, and so listed
        # five rows of the realizations; a product with four more systems
        # would have left it one.
        notes.append(
            "%d entities matched, past limits.max_nodes of %d; a report is listed whole. "
            "Check the scope still filters, or raise the limit." % (len(ordered), max_nodes)
        )
    elif max_nodes and len(ordered) > max_nodes:
        # Pins before everything else the scope names: a pin is a person
        # saying this one stays, and a view that matched every system would
        # otherwise drop it by id like any of them.
        preferred = sorted(
            selected, key=lambda item: (item not in pinned, item not in named, item[0], item[1])
        )
        named_count = len(named & selected)
        # A scope that names more than the limit loses some of what it named:
        # the integration diagram matched 55 systems and kept 40, and said it
        # showed "the 40 the scope names and the first 0 of the rest".
        if named_count >= max_nodes:
            shown = "the first %d of the %d the scope names, by id" % (max_nodes, named_count)
        else:
            shown = "the %d the scope names and the first %d of the rest by id" % (
                named_count, max_nodes - named_count)
        notes.append(
            "%d entities matched; showing %s. Narrow the scope or raise limits.max_nodes."
            % (len(ordered), shown)
        )
        cut = len(ordered) - max_nodes
        ordered = sorted(preferred[:max_nodes], key=lambda item: (item[0], item[1]))

    keep: Set[str] = {entity_id for _type, entity_id in ordered}
    color_by = view.style.get("color_by")
    nodes: List[Node] = []
    for type_name, entity_id in ordered:
        record = model.get(type_name, entity_id)
        assert record is not None
        label = str(record.get(view.node_label) or entity_id)
        # `type` is not a field on the record, it is the table the record is
        # in, so it is answered the way `group_by: type` is. Left to the field
        # lookup every node came out `default`, and a legend with one gray
        # entry is a legend that says nothing.
        if color_by == "type":
            style_key = type_name
        else:
            style_key = str(record.get(color_by) or "default") if color_by else type_name
        levels = _group_levels(record, view.group_by, model)
        nodes.append(
            Node(
                key=entity_id,
                label=label,
                entity_type=type_name,
                sort_key=_sort_key(record, view.order_by, label),
                groups=tuple(value for _field, value in levels),
                style_key=style_key,
                record=record,
                group_fields=tuple(field for field, _value in levels),
            )
        )

    edges = _build_edges(model, view, keep, notes)
    # A wheel keeps its lines on its hub as a map does: it puts the subject
    # in the middle and each connection on a spoke, and the interface engine's
    # listener drawn on the ring had every one of its nine feeds cross the
    # wheel to reach it.
    if view.kind == "diagram" and str(view.layout or "").lower() != "concentric":
        hidden = {entity_id for _type, entity_id in located(model, view.scope.get("hide"))}
        nodes, edges = _offered_on_owners(model, view, nodes, edges, hidden)

    # A map is scanned and may be any size. A diagram is read, and past a page
    # it has stopped being one -- which is a modeling finding, not a layout
    # problem, so it is said here rather than worked around in the renderer.
    # An offered interface is part of its owner's box and is not counted.
    counted = sum(1 for node in nodes if node.entity_type != "offered_interfaces")
    if view.kind == "diagram" and counted > DIAGRAM_MAX_NODES:
        notes.append(
            "%d entities on an architecture diagram. Past about %d this has "
            "become a landscape: narrow the scope, or mark it `kind: map`."
            % (counted, DIAGRAM_MAX_NODES)
        )
    return ViewGraph(
        view=view, nodes=nodes, edges=edges, groups=group_paths(nodes, view.lanes), notes=notes, cut=cut
    )


#: The edge kind joining an offered interface to the system that offers it.
OFFERS = "offers"


def _offered_on_owners(
    model: Model, view: View, nodes: List[Node], edges: List[Edge], hidden: Set[str]
) -> Tuple[List[Node], List[Edge]]:
    """A diagram's lines through an offered interface, ended at it.

    A connection that names the interface one of its ends offers is drawn to
    that interface rather than to the box behind it, and the interface is
    drawn as a node of its own in its owner's boundaries, joined to its
    owner by a short `offers` line. Forty callers of one API meet at the API
    rather than at forty points of the service's border, and the drawing says
    which door each goes through. The joining line runs the way the traffic
    does -- caller, API, service; publisher, topic, consumer -- so a ranked
    layout puts the interface between its owner and the far ends instead of
    beside the owner with its lines doubling back. An interface the scope
    selected itself is drawn the same way, in its owner's boundaries when the
    owner is drawn. Maps and reports keep their lines on the boxes: a
    landscape is about the systems."""
    by_key = {node.key: node for node in nodes}
    owner_end: Dict[str, Dict[str, int]] = {}
    rerouted: List[Edge] = []
    # The field the interface lines are labeled with. A line through an
    # interface that says what the interface says -- six lines into the
    # ledger's queue, each "MQ" -- says it on the interface once instead.
    label_field = next((spec.get("label") for spec in (view.edges or [])
                        if spec.get("via") == "interfaces" and spec.get("label")), None)
    for edge in edges:
        if edge.kind != "interface" or not edge.ref:
            rerouted.append(edge)
            continue
        record = model.get("interfaces", edge.ref) or {}
        offered_id = str(record.get("offered_interface_id") or "")
        offered = model.get("offered_interfaces", offered_id) if offered_id else None
        owner = str((offered or {}).get("system_id") or "")
        if offered is None or offered_id in hidden or owner not in (edge.source, edge.target) \
                or edge.source == edge.target:
            rerouted.append(edge)
            continue
        at = "target" if owner == edge.target else "source"
        counts = owner_end.setdefault(offered_id, {"target": 0, "source": 0})
        counts[at] += 1
        label = edge.label
        if label_field and label and str(offered.get(label_field) or "") == label:
            label = ""
        if at == "target":
            rerouted.append(edge._replace(target=offered_id, label=label))
        else:
            rerouted.append(edge._replace(source=offered_id, label=label))
    for node in nodes:
        if node.entity_type == "offered_interfaces" and node.key not in owner_end:
            owner_end[node.key] = {"target": 0, "source": 0}
    if not owner_end:
        return nodes, edges

    color_by = view.style.get("color_by")
    out_nodes = [node for node in nodes if not (node.entity_type == "offered_interfaces")]
    joins: List[Edge] = []
    for offered_id in sorted(owner_end):
        record = model.get("offered_interfaces", offered_id)
        if record is None:
            continue
        owner = str(record.get("system_id") or "")
        home = by_key.get(owner)
        drawn = by_key.get(offered_id)
        label = str(record.get(view.node_label) or offered_id)
        # Colored by the view's dimension as its own record says, else as
        # its owner's does: an interface is part of the system behind it, so
        # the API of a high-criticality service is drawn as high, and an
        # integration diagram's legend does not grow a row for the blank.
        if color_by == "type":
            style_key = "offered_interfaces"
        elif color_by:
            own = record.get(color_by)
            if own in (None, "") and home is not None:
                own = home.record.get(color_by)
            style_key = str(own or "default")
        else:
            style_key = "offered_interfaces"
        if home is not None:
            groups, fields = home.groups, home.group_fields
        elif drawn is not None:
            groups, fields = drawn.groups, drawn.group_fields
        else:
            groups, fields = (), ()
        out_nodes.append(Node(
            key=offered_id, label=label, entity_type="offered_interfaces",
            sort_key=_sort_key(record, view.order_by, label), groups=groups,
            style_key=style_key, record=record, group_fields=fields,
        ))
        if home is None:
            continue
        counts = owner_end[offered_id]
        if counts["source"] > counts["target"]:
            joins.append(Edge(source=owner, target=offered_id, label="", kind=OFFERS))
        else:
            joins.append(Edge(source=offered_id, target=owner, label="", kind=OFFERS))
    # One line per caller and interface: a caller with two connections through
    # one API draws one line to it, as two connections to one box always have.
    seen: Set[Tuple[str, str, str]] = set()
    out_edges: List[Edge] = []
    for edge in rerouted + joins:
        key = (edge.source, edge.target, edge.kind)
        if key in seen:
            continue
        seen.add(key)
        out_edges.append(edge)
    # In type and id order, as the scope's own nodes are.
    out_nodes.sort(key=lambda node: (node.entity_type, node.key))
    return out_nodes, out_edges


def group_paths(nodes: Sequence[Node], lanes: Optional[Dict[str, List[str]]] = None) -> List[Tuple[str, ...]]:
    """Every boundary path in the graph, parents before children, and
    siblings in their field's lane order where it has one, else by name. A
    value the lanes do not name follows the named ones, by name."""
    order_of = lanes or {}
    paths = set()
    field_at: Dict[Tuple[str, ...], str] = {}
    for node in nodes:
        for depth in range(1, len(node.groups) + 1):
            prefix = node.groups[:depth]
            paths.add(prefix)
            if depth - 1 < len(node.group_fields):
                field_at.setdefault(prefix, node.group_fields[depth - 1])

    def rank(path: Tuple[str, ...]):
        key = []
        for depth in range(1, len(path) + 1):
            prefix = path[:depth]
            order = order_of.get(field_at.get(prefix, ""), ())
            value = prefix[-1]
            key.append((order.index(value) if value in order else len(order), value))
        return (len(path), tuple(key))

    return sorted(paths, key=rank)


def _edge_label(record: dict, label_field: Optional[str]) -> str:
    if not label_field:
        return ""
    value = record.get(label_field)
    return "" if value in (None, "") else str(value)


def _build_edges(
    model: Model, view: View, keep: Set[str], notes: List[str]
) -> List[Edge]:
    edges: List[Edge] = []
    seen: Set[Tuple[str, str, str]] = set()
    specs = view.edges or [{"via": "interfaces"}]

    for spec in specs:
        via = spec.get("via")
        label_field = spec.get("label")
        if via == "interfaces":
            for record in model.all_of("interfaces"):
                src = str(record.get("source_system_id") or "")
                dst = str(record.get("target_system_id") or "")
                if src in keep and dst in keep:
                    _append(
                        edges, seen, src, dst, _edge_label(record, label_field), "interface",
                        str(record.get("interface_id") or ""),
                    )
            continue
        if via == "owner":
            for type_name in ENTITY_TYPES:
                pk = ENTITY_TYPES[type_name].pk
                for record in model.all_of(type_name):
                    owner = str(record.get("owner_org_id") or "")
                    entity = str(record.get(pk) or "")
                    if owner in keep and entity in keep:
                        _append(edges, seen, owner, entity, spec.get("text", "owns"), "owner")
            continue
        if via == "source_of_truth":
            for record in model.all_of("data_assets"):
                src = str(record.get("data_asset_id") or "")
                dst = str(record.get("source_of_truth") or "")
                if src in keep and dst in keep:
                    _append(edges, seen, dst, src, spec.get("text", "masters"), "sot")
            continue
        reference = reference_fields(via)
        if reference:
            # The edge runs from the record to what it points at, and reads
            # as the field name: a control `policy` its policy, a capability
            # `parent capability` its parent.
            default_text = str(via).replace("_id", "").replace("_", " ")
            for type_name, field in reference:
                pk = ENTITY_TYPES[type_name].pk
                for record in model.all_of(type_name):
                    src = str(record.get(pk) or "")
                    dst = str(record.get(field.name) or "")
                    if src in keep and dst in keep:
                        _append(edges, seen, src, dst, spec.get("text", default_text), via)
            continue
        if via not in RELATION_TYPES:
            raise ViewError("view %s references unknown edge via %r" % (view.view_id, via))
        relation = RELATION_TYPES[via]
        for row in model.relation_rows(via):
            src = str(row.get(relation.left_column) or "")
            dst = str(row.get(relation.right_column) or "")
            if src in keep and dst in keep:
                text = spec.get("text") or _edge_label(row, label_field or relation.qualifier)
                _append(edges, seen, src, dst, text, via)

    if not edges:
        notes.append("No edges connected the selected entities.")
    return edges


def _append(
    edges: List[Edge],
    seen: Set[Tuple[str, str, str]],
    source: str,
    target: str,
    label: str,
    kind: str,
    ref: str = "",
) -> None:
    key = (source, target, kind)
    if key in seen:
        return
    seen.add(key)
    edges.append(Edge(source=source, target=target, label=label, kind=kind, ref=ref))
