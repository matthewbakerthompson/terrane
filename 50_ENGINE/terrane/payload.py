"""A view as the app draws it: the payload `/api/graph` returns.

Every picture of a view starts here, whatever paints it. The app's canvas,
its PNG export, the review pack, `/api/svg` and `terrane render`'s SVG all
read the same dictionary: the boundaries first, parents before children,
each styled the way its provider draws that kind of container and carrying
its mark; then the nodes with the palette's colors, the technology line and
the mark in the corner; then the edges with their line style; and the
legend, which has a row for every channel the drawing uses. It lived in the
app's server, which is why the engine could not write SVG without importing
the app; it lives here so the engine and the app draw from one source.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from . import regroup
from .matrix import matrix_of
from .palette import Palette, boundary_label, boundary_style, legend_order, role_of
from .query import View, ViewGraph, group_kinds, resolve
from .render_mermaid import boundary_legend, flows_across
from .schema import ENTITY_TYPES, RELATION_TYPES
from .techline import TechnologyLines

#: Edge kinds drawn dotted: obligations rather than traffic.
GOVERNANCE_EDGES = {
    "system_governed_by_control", "data_governed_by_control",
    "capability_governed_by_control", "system_subject_to_policy",
    "data_subject_to_policy", "capability_subject_to_policy", "policy_id",
}
#: Edge kinds drawn dashed: what a thing runs on or is mastered by.
PLATFORM_EDGES = {"system_uses_tech_service", "sot", "tech_service_connects_to"}


def edge_style(kind: str) -> str:
    if kind in GOVERNANCE_EDGES:
        return "dotted"
    if kind in PLATFORM_EDGES:
        return "dashed"
    return "solid"


def _marks(model, view: View, graph) -> tuple:
    """What `style.marks` puts on each node: the ids at the other end of
    the relation it names, and a key of those ids with their names and how
    many nodes carry each, most first. The capability map carries the
    frameworks each capability is placed in this way, so the app can show
    where one framework lands on the whole map without a view per
    framework."""
    name = str((view.style or {}).get("marks") or "")
    spec = RELATION_TYPES.get(name)
    if spec is None:
        return {}, []
    keys = {node.key for node in graph.nodes}
    out: Dict[str, set] = {}
    for row in model.relation_rows(name):
        left, right = str(row.get(spec.left_column) or ""), str(row.get(spec.right_column) or "")
        if left in keys and right:
            out.setdefault(left, set()).add(right)
        elif right in keys and left:
            out.setdefault(right, set()).add(left)
    counts: Dict[str, int] = {}
    for linked in out.values():
        for other in linked:
            counts[other] = counts.get(other, 0) + 1
    legend = []
    for other in sorted(counts, key=lambda k: (-counts[k], k)):
        located = model.find(other)
        record = model.get(located[0], other) if located else None
        legend.append({"key": other, "label": str((record or {}).get("name") or other),
                       "count": counts[other]})
    return {key: sorted(linked) for key, linked in out.items()}, legend


def _mark(icons, technology: TechnologyLines, node) -> str:
    """The mark in a node's corner: its own (a provider's service, a bought
    system's vendor), else for a system of ours the mark of the platform
    service its technology line names first. Asked for so a reader sees an
    AWS workload from an Azure one at a glance, as the line says in words;
    the system's own name still confers nothing."""
    own = icons.for_node(node.entity_type, node.record)
    if own or node.entity_type != "systems":
        return own
    lead = technology.lead(node.record)
    return icons.for_node("tech_services", lead) if lead else ""


def graph_payload(model, view: View, palette: Palette, icons, components: Dict[str, object],
                  graph: Optional[ViewGraph] = None) -> dict:
    """The view resolved and styled for drawing. `icons` answers
    `for_group(key)` and `for_node(entity_type, record)` with the served
    path of a mark or nothing (`terrane.icons.IconMap`); `components` is the
    library's component types, for the category glyph and the technology
    line. `graph` is the view already resolved, for a caller that has it;
    otherwise it is resolved here, and a `ViewError` says why it cannot be."""
    if graph is None:
        graph = resolve(model, view)
    dimension = view.style.get("color_by") or ""
    role = role_of(dimension)
    # A nominal dimension the view also groups by is already drawn as the
    # boundary; saying so lets the legend explain rather than repeat.
    grouped = dimension in (view.group_by or ())
    # What goes under a node's name: the C4 technology line, read from the
    # model rather than typed. And the mark in its corner, where the
    # provider or vendor lets the mark travel.
    technology = TechnologyLines(model, components)

    def gid(path) -> str:
        return "grp::" + "::".join(path)

    elements: List[dict] = []
    # Boundaries first, parents before children, so Cytoscape can nest them.
    # Each is drawn the way its provider draws that kind of container, and
    # named with the kind: "region eu-west-2", "account prod-lending".
    kinds = group_kinds(graph)
    # The field a boundary is one value of, and that value as the records
    # store it, for the boundaries a box can be dropped into: `value` is what
    # the boundary is labeled, an org unit's name where the field holds its id.
    settable = regroup.boundaries(graph)
    for path in graph.groups:
        kind, provider = kinds.get(path, ("", ""))
        style = boundary_style(kind, path[-1], provider, len(path), palette=palette)
        into = settable.get(path)
        elements.append(
            {
                "data": {
                    "id": gid(path),
                    "label": boundary_label(kind, path[-1], provider),
                    "value": path[-1],
                    "parent": gid(path[:-1]) if len(path) > 1 else None,
                    "isGroup": True,
                    "depth": len(path),
                    "kind": kind,
                    "field": into.field if into else None,
                    "stored": into.value if into else None,
                    "provider": provider,
                    "bfill": style.fill,
                    "bstroke": style.stroke,
                    "bdash": style.dash,
                    "bink": style.ink,
                    "bkey": style.key,
                    "icon": icons.for_group(style.key),
                }
            }
        )
    marks, marks_legend = _marks(model, view, graph)
    type_counts: Dict[str, int] = {}
    value_counts: Dict[str, int] = {}
    for node in graph.nodes:
        style = palette.node_style(node.entity_type, dimension, node.style_key)
        component = components.get(str(node.record.get("component_type") or ""))
        type_counts[node.entity_type] = type_counts.get(node.entity_type, 0) + 1
        value_counts[node.style_key] = value_counts.get(node.style_key, 0) + 1
        elements.append(
            {
                "data": {
                    "id": node.key,
                    "label": node.label,
                    "parent": gid(node.groups) if node.groups else None,
                    "entityType": node.entity_type,
                    "componentType": node.record.get("component_type") or "",
                    "componentCategory": component.category if component else "",
                    "tech": technology.of(node.entity_type, node.record),
                    "icon": _mark(icons, technology, node),
                    # When a thing is, for a timeline: quarters, or blank.
                    "start": str(node.record.get("start_date") or ""),
                    "end": str(node.record.get("end_date") or ""),
                    "status": str(node.record.get("status") or ""),
                    "styleKey": node.style_key,
                    "fill": style.fill,
                    "stroke": style.stroke,
                    "ink": style.ink,
                    "strokeWidth": style.width,
                    "dash": style.dash,
                    "faded": style.faded,
                    "marks": marks.get(node.key, []) if marks_legend else None,
                }
            }
        )
    edge_kinds: Dict[str, str] = {}
    for i, edge in enumerate(graph.edges):
        edge_kinds.setdefault(edge.kind, edge_style(edge.kind))
        elements.append(
            {
                "data": {
                    "id": "e%d::%s::%s" % (i, edge.source, edge.target),
                    "source": edge.source,
                    "target": edge.target,
                    "label": edge.label,
                    "kind": edge.kind,
                    "lineStyle": edge_style(edge.kind),
                    # The interface an edge draws, so a flow can be walked
                    # across the drawing hop by hop.
                    "ref": edge.ref,
                }
            }
        )

    # The legend has three parts, because the drawing has three channels:
    # hue is the entity type, the view's dimension is a border or a tint, and
    # the line style is the kind of relationship.
    sample_type = sorted(type_counts)[0] if type_counts else "systems"
    dimension_keys = []
    for value in legend_order(dimension, value_counts):
        style = palette.node_style(sample_type, dimension, value)
        dimension_keys.append({
            "value": value,
            "count": value_counts[value],
            "fill": style.fill,
            "stroke": style.stroke,
            "width": style.width,
            "dash": style.dash,
            "faded": style.faded,
        })
    grid = matrix_of(graph)
    out = {
        "viewId": view.view_id,
        "title": view.title,
        "description": view.description,
        "kind": view.kind,
        # The grid a report asks for under `style.matrix`, and the marks a
        # view puts on its nodes under `style.marks`, each with its key.
        "matrix": grid.as_dict() if grid is not None else None,
        "marks": {"relation": str((view.style or {}).get("marks") or ""), "keys": marks_legend}
        if marks_legend else None,
        "layout": view.layout,
        # The order each grouped field's values are laid out in, so a tier
        # diagram reads edge to data whatever the edges say.
        "lanes": {field: list(values) for field, values in (view.lanes or {}).items()},
        "colorBy": dimension,
        "elements": elements,
        "notes": list(graph.notes),
        "counts": {"nodes": len(graph.nodes), "edges": len(graph.edges)},
        # The recorded flows with a hop on this drawing, steps in order, each
        # step saying whether it is drawn: the numbered walk beside the
        # picture that every reference architecture carries.
        "flows": flows_across(graph, model),
        "legend": {
            "types": [
                {
                    "key": entity_type,
                    "label": ENTITY_TYPES[entity_type].label if entity_type in ENTITY_TYPES
                    else entity_type,
                    "fill": palette.type_swatch(entity_type).fill,
                    "stroke": palette.type_swatch(entity_type).stroke,
                    "count": type_counts[entity_type],
                }
                for entity_type in sorted(type_counts)
            ],
            "dimension": {
                "name": dimension,
                "role": role,
                "grouped": grouped,
                "keys": dimension_keys,
            },
            "edges": [
                {"kind": kind, "style": edge_kinds[kind]} for kind in sorted(edge_kinds)
            ],
            "boundaries": boundary_legend(graph),
        },
    }
    # Where things were put by hand on the canvas, by key: a drawing with any
    # is arranged rather than laid out (terrane.draw.arranged). Left off a view
    # the layout places, which is every one written as a query.
    kept = getattr(view, "positions", None) or {}
    if kept:
        out["positions"] = {key: list(at) for key, at in sorted(kept.items())}
    return out
