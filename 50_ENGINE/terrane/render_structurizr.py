"""Structurizr DSL export.

Mermaid's layout degrades once a view passes roughly forty nodes, which is
exactly where a full application landscape starts. Structurizr handles those
well, so the engine emits one `workspace.dsl` covering the whole model plus a
view block for every view that lists `structurizr` among its renderers.

C4 has no notion of a business capability or an org unit, so those are carried
as tagged elements only when a view selects them, and the mapping is recorded in
the header of the generated file rather than silently invented.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Set, Tuple

from .model import Model
from .palette import Palette
from .query import View, ViewGraph
from .render_mermaid import node_id
from .schema import ENTITY_TYPES, RELATION_TYPES

TAGS = {
    "systems": "System",
    "tech_services": "Technology Service",
    "data_assets": "Data Asset",
    "capabilities": "Capability",
    "org_units": "Org Unit",
    "products": "Product",
    "interfaces": "Interface",
    "controls": "Control",
    "policies": "Policy",
}


def placement_of(record: dict) -> tuple:
    """Boundary path for the workspace, most-containing first.

    Flattened into a single `group` name with " / " separators: nested groups
    are a newer DSL feature and an unparsed workspace is worse than a flat one.
    """
    parts = [
        record.get("cloud_account"),
        record.get("region"),
        record.get("network_zone"),
    ]
    path = tuple(str(p) for p in parts if p)
    return path or ((str(record.get("company_domain")),) if record.get("company_domain") else ())


def _quote(text: str) -> str:
    return '"%s"' % str(text or "").replace('"', "'").replace("\n", " ").strip()


def _identifier(entity_id: str) -> str:
    return node_id(entity_id).lower()


def _properties(marks: Dict[str, str], indent: str) -> str:
    """A `properties` block with the record's fields as `aac.` keys, which
    Structurizr shows on the element and keeps through an edit, and the
    reader prefers to the tags and the groups: every element here is a
    software system told apart by tags the reader ignored, so an actor
    read back as a system, and the groups are placements, not domains."""
    lines = [" {", "%s    properties {" % indent]
    lines.extend('%s        "aac.%s" %s' % (indent, key, _quote(value)) for key, value in marks.items())
    lines.extend(["%s    }" % indent, "%s}" % indent])
    return "\n".join(lines)


def _element_marks(type_name: str, record: dict, entity_id: str) -> Dict[str, str]:
    from .render_plantuml import MARK_FIELDS

    marks = {"type": type_name, "id": str(entity_id)}
    entity_type = ENTITY_TYPES.get(type_name)
    for key in MARK_FIELDS:
        value = record.get(key)
        if value not in (None, "", []):
            marks[key] = ";".join(str(v) for v in value) if isinstance(value, list) else str(value)
        elif key == "company_domain" and entity_type is not None and any(f.name == key for f in entity_type.fields):
            marks[key] = ""  # said blank, or the group would stand in for it on the way back
    return marks


def _element_lines(model: Model, entity_ids: Iterable[Tuple[str, str]]) -> Dict[str, List[str]]:
    """Group element declarations by their `company_domain`."""
    grouped: Dict[str, List[str]] = {}
    for type_name, entity_id in entity_ids:
        record = model.get(type_name, entity_id)
        if record is None:
            continue
        group = " / ".join(placement_of(record)) or "Unassigned"
        tags = [TAGS.get(type_name, "Element")]
        for extra in ("criticality", "status", "hosting"):
            value = record.get(extra)
            if value:
                tags.append(str(value))
        grouped.setdefault(group, []).append(
            "%s = softwareSystem %s %s %s%s"
            % (
                _identifier(entity_id),
                _quote(record.get("name") or entity_id),
                _quote(record.get("description") or ""),
                _quote(",".join(tags)),
                _properties(_element_marks(type_name, record, entity_id), "            "),
            )
        )
    return grouped


def _relationship_lines(model: Model, keep: Set[str]) -> List[str]:
    lines: List[str] = []
    seen: Set[Tuple[str, str, str]] = set()
    # An interface of a connection kind carries the kind as the
    # relationship's tag, the DSL's third string, so the reader takes it
    # back as the kind; the kinds are the estate's own after the shipped.
    from .connections import kind_of, load_connections
    from .library import LibraryError

    try:
        catalog = load_connections(model.root)
    except LibraryError:
        catalog = {}

    def add(source: str, target: str, description: str, technology: str = "", tags: str = "",
            marks: Optional[Dict[str, str]] = None) -> None:
        if source not in keep or target not in keep:
            return
        key = (source, target, description)
        if key in seen:
            return
        seen.add(key)
        suffix = ""
        if technology or tags:
            suffix += " %s" % _quote(technology)  # the DSL puts the technology before the tags, empty if need be
        if tags:
            suffix += " %s" % _quote(tags)
        # The record behind the line, as properties: an interface's id and
        # what its kind proposes as the record has it, a row's relation and
        # qualifier, a field's name. Read back, the lines were 157 new
        # interfaces and rows the reader had to guess at.
        lines.append(
            "%s -> %s %s%s%s"
            % (_identifier(source), _identifier(target), _quote(description), suffix,
               _properties(marks, "        ") if marks else "")
        )

    from .render_plantuml import REL_MARK_FIELDS

    for record in model.all_of("interfaces"):
        kind = (kind_of(record, catalog) or "") if catalog else ""
        marks = {"interface_id": str(record.get("interface_id") or "")}
        if kind:
            marks["kind"] = kind
        for key in REL_MARK_FIELDS:
            value = record.get(key)
            if value not in (None, "", []):
                marks[key] = ";".join(str(v) for v in value) if isinstance(value, list) else str(value)
        add(
            str(record.get("source_system_id") or ""),
            str(record.get("target_system_id") or ""),
            record.get("name") or "Interface",
            record.get("protocol") or "",
            kind,
            marks,
        )
    for name, spec in RELATION_TYPES.items():
        pretty = name.replace("_", " ")
        for row in model.relation_rows(name):
            marks = {"relation": name}
            if spec.qualifier and row.get(spec.qualifier) not in (None, "", []):
                value = row[spec.qualifier]
                marks[spec.qualifier] = ";".join(str(v) for v in value) if isinstance(value, list) else str(value)
            add(
                str(row.get(spec.left_column) or ""),
                str(row.get(spec.right_column) or ""),
                pretty,
                marks=marks,
            )
    for record in model.all_of("data_assets"):
        owner = str(record.get("source_of_truth") or "")
        if owner:
            add(owner, str(record["data_asset_id"]), "masters", marks={"field": "source_of_truth"})
    for record in model.all_of("offered_interfaces"):
        owner = str(record.get("system_id") or "")
        if owner:
            add(owner, str(record["offered_interface_id"]), "offers", marks={"field": "system_id"})
    return lines


def _view_block(graph: ViewGraph) -> List[str]:
    view = graph.view
    # `systemLandscape <key> <description>` takes the description positionally.
    # Passing the title there and then emitting `description` inside the block
    # overrode it, and the title was lost. Both are set as properties instead.
    lines = ["systemLandscape %s {" % _identifier(view.view_id)]
    lines.append("    title %s" % _quote(view.title))
    if view.description:
        lines.append("    description %s" % _quote(view.description))
    for node in graph.nodes:
        lines.append("    include %s" % _identifier(node.key))
    lines.append("    autoLayout %s" % ("lr" if view.layout.upper() == "LR" else "tb"))
    lines.append("}")
    return lines


def render_workspace(
    model: Model,
    graphs: List[ViewGraph],
    palette: Palette,
    name: Optional[str] = None,
) -> str:
    """Emit a Structurizr DSL workspace for the model and the given views."""
    for graph in graphs:
        palette.assign(node.style_key for node in graph.nodes)
    selected: Set[Tuple[str, str]] = set()
    for graph in graphs:
        for node in graph.nodes:
            selected.add((node.entity_type, node.key))
    if not selected:
        for type_name in ("systems", "tech_services", "data_assets"):
            pk = ENTITY_TYPES[type_name].pk
            for record in model.all_of(type_name):
                selected.add((type_name, str(record[pk])))

    keep = {entity_id for _t, entity_id in selected}
    grouped = _element_lines(model, sorted(selected))

    workspace_name = name or model.config.get("name") or "Architecture"
    out: List[str] = []
    out.append("// Generated from the model by `terrane render`. Do not edit by hand.")
    out.append("// C4 has no capability or org-unit element; those are exported as")
    out.append("// tagged software systems and are only present when a view selects them.")
    out.append(
        "workspace %s %s {"
        % (_quote(workspace_name), _quote(model.config.get("description") or ""))
    )
    out.append("")
    out.append("    model {")
    for group in sorted(grouped):
        out.append("        group %s {" % _quote(group))
        for line in sorted(grouped[group]):
            out.append("            %s" % line)
        out.append("        }")
    out.append("")
    for line in _relationship_lines(model, keep):
        out.append("        %s" % line)
    out.append("    }")
    out.append("")
    out.append("    views {")
    for graph in graphs:
        for line in _view_block(graph):
            out.append("        %s" % line)
        out.append("")
    out.append("        styles {")
    style_keys: Set[str] = set()
    for graph in graphs:
        style_keys |= {node.style_key for node in graph.nodes}
    for tag in sorted(set(TAGS.values()) | style_keys):
        swatch = palette.swatch(tag)
        out.append("            element %s {" % _quote(tag))
        out.append("                background %s" % swatch.fill)
        out.append("                stroke %s" % swatch.stroke)
        out.append("                color %s" % swatch.ink)
        out.append("            }")
    out.append("        }")
    out.append("    }")
    out.append("}")
    return "\n".join(out).rstrip() + "\n"
