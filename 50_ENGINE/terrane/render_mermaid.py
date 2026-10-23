"""Mermaid flowchart renderer.

Mermaid is the default because it renders with no toolchain at all: GitHub,
Backstage TechDocs, Docs Studio and the SharePoint publish path all display it
from source. The cost is layout control, so `limits.max_nodes` on a view is a
real constraint rather than a formality.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, List

from .matrix import matrix_of
from .palette import Palette, boundary_label, boundary_style, legend_order, role_of
from .query import ViewGraph, group_kinds

_SAFE_ID = re.compile(r"[^A-Za-z0-9_]")

#: Characters that break Mermaid labels even inside quotes.
_LABEL_REPLACEMENTS = (
    ('"', "#quot;"),
    ("<", "#lt;"),
    (">", "#gt;"),
    ("|", "/"),
    ("\n", " "),
)


def node_id(raw: str) -> str:
    """Mermaid identifiers cannot carry hyphens or dots; ids are stable per key."""
    cleaned = _SAFE_ID.sub("_", str(raw))
    return cleaned if cleaned and not cleaned[0].isdigit() else "n_" + cleaned


def label(raw: str, max_len: int = 42) -> str:
    text = str(raw or "").strip()
    for needle, replacement in _LABEL_REPLACEMENTS:
        text = text.replace(needle, replacement)
    text = re.sub(r"\s+", " ", text)
    if len(text) > max_len:
        text = text[: max_len - 1].rstrip() + "…"
    return text


def wrap_label(raw: str, width: int = 26, lines: int = 3, max_len: int = 84) -> str:
    """A node's name on up to three lines rather than cut short.

    Mermaid does not wrap a flowchart label on its own, so a forty-six
    character control name was cut to an ellipsis, and a diagram that cuts
    the names of the things it is about is a poor diagram of them. Words
    break at spaces; only a name past three full lines is still cut.
    """
    text = label(raw, max_len)
    if len(text) <= width:
        return text
    out: List[str] = []
    current = ""
    for word in text.split(" "):
        if current and len(current) + 1 + len(word) > width and len(out) < lines - 1:
            out.append(current)
            current = word
        else:
            current = word if not current else current + " " + word
    out.append(current)
    return "<br/>".join(out)


#: Shape belongs to the entity type, the same way hue does. The component
#: type used to override it, which put a capability's hexagon on a tech
#: service and left the reader with two taxonomies on one channel.
_SHAPES = {
    "systems": ("[\"", "\"]"),
    "products": ("([\"", "\"])"),
    "capabilities": ("{{\"", "\"}}"),
    "data_assets": ("[(\"", "\")]"),
    "tech_services": ("[/\"", "\"/]"),
    "org_units": ("[\"", "\"]"),
    "interfaces": (">\"", "\"]"),
    # What a system offers is the one rounded box: no other type has the
    # bracket, so it reads back as what it is, beside its owner.
    "offered_interfaces": ("(\"", "\")"),
    "actors": ("([\"", "\"])"),
    # A control is a subroutine box: something that runs. A policy is a
    # trapezoid, which is the nearest Mermaid has to a document.
    "controls": ("[[\"", "\"]]"),
    "policies": ("[/\"", "\"\\]"),
    # A process is the other trapezoid: work that runs, leaning the other way
    # from the policy that governs it.
    "processes": ("[\\\"", "\"/]"),
}


def _shape(entity_type: str, shape: str = "") -> tuple:
    return _SHAPES.get(entity_type, ("[\"", "\"]"))


def _class_name(style_key: str) -> str:
    return "s_" + node_id(style_key).lower()


def _style_class(node) -> str:
    """One class per (entity type, dimension value) pair drawn."""
    return _class_name("%s__%s" % (node.entity_type, node.style_key))


def group_id(path) -> str:
    # Built from the whole path, not just the leaf, so two `Private-App` zones
    # in different accounts do not collide into one box.
    return node_id("grp_" + "__".join(path))


#: Below this many edges per node a graph is a catalog rather than a flow.
#: Ranking a catalog produces one very long line; banding it does not.
CATALOG_EDGE_RATIO = 0.5


_SHAPE_CACHE: Dict[str, str] = {}


def component_shapes() -> Dict[str, str]:
    """Component type to shape name, read once from the library.

    Missing or unreadable is not an error: the entity type is a perfectly good
    fallback, and a broken component file should not stop a diagram rendering.
    """
    if _SHAPE_CACHE:
        return _SHAPE_CACHE
    try:
        from .blocks import load_components
        from .shipped import shipped_root

        for component in load_components(shipped_root()).values():
            _SHAPE_CACHE[component.component_type_id] = component.shape
    except Exception:  # noqa: BLE001 - shapes are a nicety, not a requirement
        _SHAPE_CACHE["__none__"] = "rectangle"
    return _SHAPE_CACHE


def group_direction(graph: ViewGraph) -> str:
    """Which way nodes run inside a boundary.

    A view can say. Otherwise: a catalog gets boundaries turned across the
    diagram, so each one is a band and the bands stack; anything with enough
    edges to rank keeps the diagram's own direction, because its edges need to
    point the same way as everything else.
    """
    outer = _direction(graph.view.layout)
    outer = "TB" if outer == "TB" else "LR"
    declared = graph.view.group_direction
    if declared in ("TB", "LR"):
        return declared
    nodes = len(graph.nodes)
    if nodes > 8 and len(graph.edges) / max(nodes, 1) < CATALOG_EDGE_RATIO:
        return "LR" if outer == "TB" else "TB"
    return outer


def _direction(layout) -> str:
    """Mermaid knows four directions. A view laid out as a wheel or a force
    graph in the app is drawn left to right here, which is the honest
    fallback: Mermaid has no concentric layout to offer."""
    value = str(layout or "LR").upper()
    return value if value in ("LR", "TB", "RL", "BT") else "LR"


def technology_lines(graph: ViewGraph, model) -> Dict[str, str]:
    """The technology line under each node's name, for the committed
    diagram: the same line the app paints, read from the model. Nothing
    without a model, and nothing if the library will not load; the line
    is a nicety, not a requirement."""
    if model is None:
        return {}
    try:
        from .blocks import load_components
        from .techline import TechnologyLines

        lines = TechnologyLines(model, load_components(model.root))
    except Exception:  # noqa: BLE001 - see above
        return {}
    return {node.key: lines.of(node.entity_type, node.record) for node in graph.nodes}


def render(graph: ViewGraph, palette: Palette, model=None) -> str:
    # Settle the colors against this diagram's own categories first, so no two
    # of them share a hue and the legend can be read.
    palette.assign(node.style_key for node in graph.nodes)
    view = graph.view
    inner = group_direction(graph)
    shapes = component_shapes()
    tech = technology_lines(graph, model)
    lines: List[str] = []
    lines.append("%%{init: {'flowchart': {'curve': 'basis'}} }%%")
    lines.append("flowchart %s" % _direction(view.layout))
    # Concatenated rather than %-formatted: `%%` is the escape for a literal
    # percent, which would silently halve the Mermaid comment marker.
    lines.append("  %% " + label(view.title, 120))
    lines.append("  %% Generated from the model by `terrane render`. Do not edit by hand.")
    lines.append("")

    by_path: Dict[tuple, List] = {}
    for node in graph.nodes:
        by_path.setdefault(node.groups, []).append(node)

    def emit_node(node, indent: str) -> None:
        open_shape, close_shape = _shape(node.entity_type)
        text = wrap_label(node.label)
        line = tech.get(node.key)
        if line:
            # The technology on a second line in brackets, the way a C4
            # container names its own, at the name's size: Mermaid cannot
            # size one line of a label differently from the next.
            text += "<br/>[%s]" % label(line, 40)
        lines.append("%s%s%s%s%s" % (indent, node_id(node.key), open_shape, text, close_shape))

    def children_of(path: tuple) -> List[tuple]:
        return [g for g in graph.groups if len(g) == len(path) + 1 and g[:-1] == path]

    kinds = group_kinds(graph)

    def emit_boundary(path: tuple, depth: int) -> None:
        # One boundary, then everything nested inside it, named the way the
        # provider names it: "region eu-west-2", "account prod-lending".
        indent = "  " * (depth + 1)
        kind, provider = kinds.get(path, ("", ""))
        lines.append(
            '%ssubgraph %s["%s"]'
            % (indent, group_id(path), label(boundary_label(kind, path[-1], provider), 60))
        )
        lines.append("%s  direction %s" % (indent, inner))
        for node in sorted(by_path.get(path, []), key=lambda n: n.sort_key):
            emit_node(node, indent + "  ")
        for child in children_of(path):
            emit_boundary(child, depth + 1)
        lines.append("%send" % indent)

    for path in [g for g in graph.groups if len(g) == 1]:
        emit_boundary(path, 0)
        lines.append("")

    ungrouped = sorted(by_path.get((), []), key=lambda n: n.sort_key)
    for node in ungrouped:
        emit_node(node, "  ")
    if ungrouped:
        lines.append("")

    for edge in graph.edges:
        arrow = "-.->" if edge.kind in ("system_uses_tech_service", "sot") else "-->"
        if edge.kind == "offers":
            # No traffic and no head: the interface is the system's own.
            arrow = "---"
        if edge.label:
            lines.append(
                "  %s %s|\"%s\"| %s"
                % (node_id(edge.source), arrow, label(edge.label, 24), node_id(edge.target))
            )
        else:
            lines.append("  %s %s %s" % (node_id(edge.source), arrow, node_id(edge.target)))
    lines.append("")

    # Hue by entity type; the view's dimension as border weight, tint or
    # dash. One class per pair actually drawn.
    dimension = view.style.get("color_by")
    classes: Dict[str, tuple] = {}
    for node in graph.nodes:
        name = _style_class(node)
        if name not in classes:
            classes[name] = (node.entity_type, node.style_key)
    for name in sorted(classes):
        entity_type, value = classes[name]
        style = palette.node_style(entity_type, dimension, value)
        rule = "fill:%s,stroke:%s,color:%s,stroke-width:%spx" % (
            style.fill, style.stroke, style.ink, style.width
        )
        if style.dash == "dashed":
            rule += ",stroke-dasharray:6 3"
        elif style.dash == "dotted":
            rule += ",stroke-dasharray:2 3"
        if style.faded:
            rule += ",opacity:0.55"
        lines.append("  classDef %s %s;" % (name, rule))
    for name in sorted(classes):
        members = [node_id(n.key) for n in graph.nodes if _style_class(n) == name]
        if members:
            lines.append("  class %s %s;" % (",".join(members), name))

    if graph.groups:
        # A boundary is drawn the way its provider draws that kind of
        # container: a dashed teal AWS region, a solid blue Azure
        # subscription, a green public subnet. Anything that is not a cloud
        # container keeps the depth tint. One class per style actually drawn.
        styles: Dict[tuple, List[str]] = {}
        for path in graph.groups:
            kind, provider = kinds.get(path, ("", ""))
            style = boundary_style(kind, path[-1], provider, len(path), palette=palette)
            styles.setdefault((style.fill, style.stroke, style.dash, style.ink), []).append(group_id(path))
        for index, key in enumerate(sorted(styles), start=1):
            fill, stroke, dash, ink = key
            rule = "fill:%s,stroke:%s,color:%s" % (fill, stroke, ink)
            if dash == "dashed":
                rule += ",stroke-dasharray:6 3"
            elif dash == "dotted":
                rule += ",stroke-dasharray:2 3"
            lines.append("  classDef boundary%d %s;" % (index, rule))
            lines.append("  class %s boundary%d;" % (",".join(styles[key]), index))

    return "\n".join(lines).rstrip() + "\n"


def boundary_legend(graph: ViewGraph) -> List[dict]:
    """The kinds of boundary a diagram draws, each once, in draw order: what
    the legend names beside the entity types and the line styles."""
    kinds = group_kinds(graph)
    out: List[dict] = []
    seen = set()
    for path in graph.groups:
        kind, provider = kinds.get(path, ("", ""))
        style = boundary_style(kind, path[-1], provider, len(path))
        if not style.key or style.key in seen:
            continue
        seen.add(style.key)
        out.append({"key": style.key, "fill": style.fill, "stroke": style.stroke,
                    "dash": style.dash, "ink": style.ink})
    return out


def flows_across(graph: ViewGraph, model) -> List[dict]:
    """The recorded flows with at least one hop on this diagram, each with
    its steps in order and whether each step is drawn: the numbered walk a
    reference architecture puts beside its picture. A step's `n` is its
    place in the walk, 1 upward; `sequence` is the model's own ordering
    value, which may count by tens."""
    from .render_sequence import all_flows, steps_for

    drawn = {edge.ref for edge in graph.edges if edge.ref}
    if not drawn:
        return []
    out: List[dict] = []
    for flow_id in all_flows(model):
        steps = steps_for(model, flow_id)
        if not any(str(s["interface"].get("interface_id")) in drawn for s in steps):
            continue
        record = model.get("flows", flow_id) or {}
        listed = []
        for step in steps:
            interface = step["interface"]
            source = model.get("systems", str(interface.get("source_system_id"))) or {}
            target = model.get("systems", str(interface.get("target_system_id"))) or {}
            listed.append({
                "n": len(listed) + 1,
                "sequence": step["sequence"],
                "interfaceId": str(interface.get("interface_id") or ""),
                "fromId": str(interface.get("source_system_id") or ""),
                "from": source.get("name") or interface.get("source_system_id"),
                "toId": str(interface.get("target_system_id") or ""),
                "to": target.get("name") or interface.get("target_system_id"),
                "protocol": interface.get("protocol") or "",
                "drawn": str(interface.get("interface_id")) in drawn,
            })
        out.append({
            "id": flow_id,
            "name": record.get("name") or flow_id,
            "description": str(record.get("description") or "").strip(),
            "steps": listed,
            "drawn": sum(1 for s in listed if s["drawn"]),
        })
    out.sort(key=lambda w: (-w["drawn"], w["name"].lower()))
    return out


def render_markdown(graph: ViewGraph, palette: Palette, model=None, picture: str = "") -> str:
    """The same diagram wrapped for docs, with a legend, the boundaries, the
    flows that cross it, and provenance. `picture` is the relative path of
    the view drawn as the app draws it, where `terrane render` wrote one; it
    goes under the Mermaid, which stays the portable source, since a docs
    build that copies this folder alone has no `../svg/` to show."""
    view = graph.view
    parts: List[str] = ["# %s" % view.title, ""]
    if view.description:
        parts.extend([view.description.strip(), ""])
    parts.extend(["```mermaid", render(graph, palette, model).rstrip(), "```", ""])
    if picture:
        parts.append("The same view as the app draws it, written beside the Mermaid by `terrane render`:")
        parts.append("")
        parts.append("![%s](%s)" % (view.title.replace("]", ")"), picture))
        parts.append("")

    types = sorted({node.entity_type for node in graph.nodes})
    if len(types) > 1:
        parts.append("**Hue is the entity type.**")
        parts.append("")
        parts.append("| | Entity type |")
        parts.append("|---|---|")
        for entity_type in types:
            swatch = palette.type_swatch(entity_type)
            parts.append("| `%s` | %s |" % (swatch.stroke, entity_type.replace("_", " ")))
        parts.append("")

    dimension = view.style.get("color_by")
    role = role_of(dimension)
    values = legend_order(dimension, (node.style_key for node in graph.nodes))
    if role == "ordinal" and len(values) > 1:
        parts.append(
            "**%s** is drawn as border weight and tint, strongest first."
            % dimension.replace("_", " ")
        )
        parts.append("")
        parts.append("| Border | Value |")
        parts.append("|---|---|")
        for value in values:
            style = palette.node_style(types[0], dimension, value)
            parts.append("| %spx | %s |" % (style.width, value))
        parts.append("")
    elif role == "status" and len(values) > 1:
        parts.append(
            "**status** is drawn as the border style: solid for Active, dashed for "
            "Planned, dotted for Proposed, and faded for Deprecated and Retired."
        )
        parts.append("")
    elif role == "nominal" and len(values) > 1 and dimension in view.group_by:
        parts.append(
            "**%s** is the boundary each node sits in." % dimension.replace("_", " ")
        )
        parts.append("")

    boundaries = boundary_legend(graph)
    if boundaries:
        parts.append("**Boundaries** are drawn the way their provider draws them.")
        parts.append("")
        parts.append("| Border | Boundary |")
        parts.append("|---|---|")
        for entry in boundaries:
            parts.append("| %s `%s` | %s |" % (entry["dash"], entry["stroke"], entry["key"]))
        parts.append("")

    walks = flows_across(graph, model) if model is not None else []
    if walks:
        parts.append("## Flows across this diagram")
        parts.append("")
        parts.append(
            "Each flow is a recorded sequence of interfaces. The steps drawn on this "
            "diagram are numbered; a step whose interface is not on it is marked."
        )
        parts.append("")
        for walk in walks:
            parts.append("**%s**%s" % (walk["name"], (": " + walk["description"]) if walk["description"] else ""))
            parts.append("")
            for step in walk["steps"]:
                parts.append(
                    "%s. %s \u2192 %s%s%s"
                    % (step["n"], step["from"], step["to"],
                       (" (%s)" % step["protocol"]) if step["protocol"] else "",
                       "" if step["drawn"] else " \u2014 not on this diagram")
                )
            parts.append("")

    parts.append(
        "%d entities, %d relationships. Generated from the model; edit the model, not this file."
        % (len(graph.nodes), len(graph.edges))
    )
    for note in graph.notes:
        parts.append("")
        parts.append("> %s" % note)
    return "\n".join(parts).rstrip() + "\n"


def legend_keys(graph: ViewGraph) -> Iterable[str]:
    return sorted({node.style_key for node in graph.nodes})


def quarter_bounds(quarter) -> Optional[Tuple[str, str]]:
    """The first and last day of a `YYYY-Qn` quarter, or None for anything
    else. The field dictionary says quarters; a gantt wants days."""
    text = str(quarter or "")
    if len(text) != 7 or text[4:6] != "-Q" or not text[:4].isdigit() or text[6] not in "1234":
        return None
    year, q = int(text[:4]), int(text[6])
    first_month = (q - 1) * 3 + 1
    last_month = first_month + 2
    return (
        "%04d-%02d-01" % (year, first_month),
        "%04d-%02d-%02d" % (year, last_month, {3: 31, 6: 30, 9: 30, 12: 31}[last_month]),
    )


def _timeline_tasks(graph: ViewGraph):
    """(section, node, first day, last day) for every node with a quarter at
    each end, in section, start, label order. The section is what the view
    groups by, so a work package sits under its roadmap's name."""
    rows = []
    for node in graph.nodes:
        start = quarter_bounds(node.record.get("start_date"))
        end = quarter_bounds(node.record.get("end_date"))
        if not start or not end:
            continue
        rows.append((node.groups[-1] if node.groups else "", node, start[0], end[1]))
    rows.sort(key=lambda r: (r[0].lower(), r[2], r[1].label.lower()))
    return rows


def _reached(graph: ViewGraph) -> Dict[str, List[Tuple[str, str]]]:
    """Dated node key to (label, edge label) for the undated things its
    edges reach: the systems a work package delivers, under its bar."""
    by_key = {node.key: node for node in graph.nodes}
    dated = {section_node[1].key for section_node in _timeline_tasks(graph)}
    out: Dict[str, List[Tuple[str, str]]] = {}
    for edge in graph.edges:
        if edge.source in dated and edge.target in by_key and edge.target not in dated:
            out.setdefault(edge.source, []).append((by_key[edge.target].label, edge.label or ""))
    for pairs in out.values():
        pairs.sort(key=lambda p: p[0].lower())
    return out


def _gantt_text(text: str) -> str:
    # A colon starts a task's metadata and a hash a comment; neither belongs
    # in a name, and a name is the only place either could arrive from.
    return str(text).replace(":", " -").replace("#", "")


def render_timeline(graph: ViewGraph) -> str:
    """A timeline as a Mermaid gantt: one bar per dated thing, sectioned by
    what the view groups by. The undated things the view reaches are not
    drawn -- a system has no quarter -- and the docs page lists them under
    the bar they hang from. Time is the one axis a layout must not choose,
    which is why this is not a flowchart with dates in the labels."""
    view = graph.view
    lines = [
        "gantt",
        "  title %s" % _gantt_text(view.title),
        "  dateFormat YYYY-MM-DD",
        "  axisFormat %Y-%m",
    ]
    current = None
    for section, node, start, end in _timeline_tasks(graph):
        if section != current:
            lines.append("  section %s" % _gantt_text(section or "Unplaced"))
            current = section
        status = str(node.record.get("status") or "")
        tag = "active, " if status == "Active" else "done, " if status in ("Deprecated", "Retired") else ""
        task_id = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in node.key)
        lines.append("  %s :%s%s, %s, %s" % (_gantt_text(node.label), tag, task_id, start, end))
    return "\n".join(lines) + "\n"


def render_timeline_markdown(graph: ViewGraph, picture: str = "") -> str:
    """The timeline wrapped for docs: the drawing where there is one, the
    gantt, then a table of every bar with what sits under it."""
    view = graph.view
    tasks = _timeline_tasks(graph)
    reached = _reached(graph)
    parts: List[str] = ["# %s" % view.title, ""]
    if view.description:
        parts.extend([view.description.strip(), ""])
    if picture:
        parts.append("![%s](%s)" % (view.title.replace("]", ")"), picture))
        parts.append("")
    parts.extend(["```mermaid", render_timeline(graph).rstrip(), "```", ""])
    parts.append("| Under | What | From | To | Status | Reaches |")
    parts.append("|---|---|---|---|---|---|")
    for section, node, start, end in tasks:
        under = ", ".join(
            "%s (%s)" % (label, effect.lower()) if effect else label
            for label, effect in reached.get(node.key, [])
        ) or "—"
        parts.append(
            "| %s | %s <br>`%s` | %s | %s | %s | %s |"
            % (section or "—", node.label, node.key, str(node.record.get("start_date") or ""),
               str(node.record.get("end_date") or ""), str(node.record.get("status") or "—"), under)
        )
    undated = len(graph.nodes) - len(tasks)
    parts.extend([
        "",
        "%d dated thing%s; %d without a quarter, listed under the bars that reach them. "
        "Generated from the model; this is a timeline, so the axis is time and the "
        "layout chose nothing."
        % (len(tasks), "" if len(tasks) == 1 else "s", undated),
    ])
    for note in graph.notes:
        parts.append("")
        parts.append("> %s" % note)
    return "\n".join(parts).rstrip() + "\n"


def render_table(graph: ViewGraph, picture: str = "") -> str:
    """A report as the table it always was.

    Six of the twenty-six views answer a question with a set: which
    capabilities have a system, what is attached to each platform service, what
    personal data each system holds. Drawing a set as a graph adds nothing
    except the suggestion that the lines between the rows mean something.

    The relationship is the row, so the table is edges rather than nodes: each
    one is a pair and whatever the model records about the pairing.
    """
    grid = matrix_of(graph)
    if grid is not None:
        return _matrix_markdown(graph, grid, picture)
    view = graph.view
    by_key = {node.key: node for node in graph.nodes}
    parts: List[str] = ["# %s" % view.title, ""]
    if view.description:
        parts.extend([view.description.strip(), ""])
    if picture:
        parts.extend(["![%s](%s)" % (view.title.replace("]", ")"), picture), ""])

    if not graph.edges:
        parts.extend([
            "%d entities, and no relationship between any of them recorded in the "
            "model." % len(graph.nodes),
            "",
            "| | Entity | Id |",
            "|---|---|---|",
        ])
        for index, node in enumerate(sorted(graph.nodes, key=lambda n: n.label.lower()), 1):
            parts.append("| %d | %s | `%s` |" % (index, node.label, node.key))
        parts.append("")
        return "\n".join(parts)

    labeled = any(edge.label for edge in graph.edges)
    header = "| From | | To |" + (" Detail |" if labeled else "")
    parts.extend([header, "|---|---|---|" + ("---|" if labeled else "")])

    def side(key: str) -> str:
        node = by_key.get(key)
        return "%s <br>`%s`" % (node.label, key) if node else "`%s`" % key

    for edge in sorted(graph.edges, key=lambda e: (str(e.kind), side(e.source).lower())):
        row = "| %s | %s | %s |" % (side(edge.source), edge.kind.replace("_", " "),
                                    side(edge.target))
        if labeled:
            row += " %s |" % (edge.label or "")
        parts.append(row)

    parts.extend([
        "",
        "%d relationships across %d entities. Generated from the model; this is a "
        "report rather than a diagram, so it is a table."
        % (len(graph.edges), len(graph.nodes)),
    ])
    for note in graph.notes:
        parts.append("")
        parts.append("> %s" % note)
    return "\n".join(parts) + "\n"


def _matrix_markdown(graph: ViewGraph, grid, picture: str = "") -> str:
    """A report's grid as a Markdown table: the rows in their groups, a
    column per column, each cell its mark and its count."""
    view = graph.view
    parts: List[str] = ["# %s" % view.title, ""]
    if view.description:
        parts.extend([view.description.strip(), ""])
    if picture:
        parts.extend(["![%s](%s)" % (view.title.replace("]", ")"), picture), ""])
    columns = list(grid.columns)
    parts.append("| | " + " | ".join(c.label for c in columns) + " | Placed |")
    parts.append("|---|" + "---|" * len(columns) + "---|")
    for group in grid.groups:
        if group.name:
            parts.append("| **%s** |" % group.name + " |" * (len(columns) + 1))
        for row in group.rows:
            cells = []
            for column in columns:
                cell = grid.cells.get((row.key, column.key))
                if cell is None:
                    cells.append("")
                    continue
                cells.append(" · ".join(part for part in (cell.mark, str(cell.count) if cell.count else "") if part))
            parts.append("| %s | %s | %s |" % (row.label, " | ".join(cells), row.total or ""))
    parts.append("| Placed in each | " + " | ".join(str(c.total or "") for c in columns) + " | |")
    parts.extend([
        "",
        "A word is how firmly the domain follows the framework (%s). A number is how many "
        "capabilities under the domain are placed in it (%s)." % (grid.mark.replace("_", " "),
                                                                    grid.count.replace("_", " ")),
        "",
    ])
    return "\n".join(parts)
