"""Every view as a C4-PlantUML diagram, the way the reader takes it back.

C4-PlantUML is how most development teams drew C4 before Mermaid had it,
and the reader (`plantuml_import`) brings those diagrams in. This is the
way back out: a view of the estate, or a sketch's, as `@startuml` with
the C4 include, a `Boundary` per boundary nested as the view nests them, a
`Person` per actor, a `System` per system (`System_Ext` where it is SaaS
or external), a `SystemDb` per data asset, a `Deployment_Node` per
technology service, and a `System` with a tag naming the type for
everything the C4 vocabulary has no word for (a capability, a process, a
product, a policy, a control), so the picture still colors it the way the
method does: every type present is an element tag carrying the method's
own fill, border and ink, and the legend lists them. A `Rel` per line, an
interface's name and protocol as its label and technology, a relation's
word as its label. Aliases are the model's ids with the hyphens made
underscores, which the reader turns back into the ids, so a diagram
exported and read again is the sketch it came from, domains included.

The public PlantUML server renders the file as it is; nothing here is
drawn by this engine, which is the point of an export.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from .draw.shapes import edge_word
from .palette import Palette, boundary_label
from .query import View, ViewError, ViewGraph, bind, group_kinds, render_targets, resolve, subject_slug
from .render_mermaid import technology_lines
from .schema import ENTITY_TYPES, RELATION_TYPES

#: The C4 macro each type is written as; a type not here is a `System`
#: tagged with the type.
MACROS: Dict[str, str] = {"actors": "Person", "systems": "System", "data_assets": "SystemDb",
                          "tech_services": "Deployment_Node"}
EXTERNAL_HOSTING = ("saas", "external")


def alias(key: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_]", "_", str(key))
    return text if text and not text[0].isdigit() else "n_" + text


def _quote(text: str) -> str:
    return '"%s"' % " ".join(str(text or "").split()).replace('"', "'")


#: The record's own fields a comment under the element carries, since the
#: macro cannot: the domain (a boundary is the view's grouping, actors by
#: kind on the context page, and the reader took it for the domain), the
#: hosting (`System_Ext` read back as External whatever the record said),
#: an actor's kind and whether it is internal (every Person read back as a
#: person). PlantUML ignores a `'` line, so the picture is the same.
MARK_FIELDS = ("company_domain", "hosting", "actor_kind", "internal")
#: What a connection kind proposes and a Rel cannot carry, pinned under the
#: Rel as the record has them, so the proposal is not written over them; and
#: the interface it goes through, which a landscape drawing the line to the
#: box would otherwise lose on the way back.
REL_MARK_FIELDS = ("integration_style", "auth_method", "frequency", "direction", "patterns",
                   "offered_interface_id")


def _mark(indent: str, alias_text: str, record: dict, built_with: str, entity_type: str = "") -> List[str]:
    """The `' aac ALIAS: field="value"; ...` line under an element, or
    nothing when the record says none of it; `built_with` is the technology
    the description was given as a sentence (by the export for a System,
    by the reader for a node's technology slot), so the reader can take
    the sentence off again. The domain is said even when blank, where the
    type has one: a record with none read back with the boundary's name
    for its domain, "System" on a page grouped by type. The estate's own
    page read back "corrected" seven systems and eight actors before this
    line."""
    fields = ["%s=%s" % (key, _quote(str(record[key]))) for key in MARK_FIELDS if record.get(key) not in (None, "")]
    has_domain = entity_type in ENTITY_TYPES and any(f.name == "company_domain" for f in ENTITY_TYPES[entity_type].fields)
    if has_domain and record.get("company_domain") in (None, ""):
        fields.insert(0, 'company_domain=""')
    if built_with:
        fields.append("technology=%s" % _quote(built_with))
    return ["%s' aac %s: %s" % (indent, alias_text, "; ".join(fields))] if fields else []


def _macro(node) -> str:
    kind = MACROS.get(node.entity_type, "System")
    record = node.record or {}
    if node.entity_type == "actors" and str(record.get("internal") or "").lower() == "no":
        return "Person_Ext"
    if node.entity_type == "systems" and str(record.get("hosting") or "").lower() in EXTERNAL_HOSTING:
        return "System_Ext"
    return kind


#: Who writes the pages `export_plantuml` sweeps, as the third line of each says.
_EXPORT = "terrane export plantuml"


def render_plantuml(graph: ViewGraph, model=None, *, title: Optional[str] = None,
                    palette: Optional[Palette] = None, generated_by: str = _EXPORT) -> str:
    """The view graph as a C4-PlantUML diagram."""
    view = graph.view
    palette = palette or Palette((model.config.get("palette") if model is not None else None) or None)
    tech = technology_lines(graph, model) if model is not None else {}
    kinds = group_kinds(graph)
    # An interface of a connection kind carries the kind's id as its Rel's
    # tag, with an AddRelTag so the legend names it and the reader takes
    # it back as the kind; the kinds are the estate's own after the
    # shipped ones, and none when the library cannot be read.
    connections: dict = {}
    if model is not None:
        from .connections import kind_of, load_connections
        from .library import LibraryError

        try:
            connections = load_connections(model.root)
        except LibraryError:
            connections = {}
    rel_tags: Dict[str, str] = {}
    for edge in graph.edges:
        if edge.ref and model is not None and connections:
            found = kind_of(model.get("interfaces", edge.ref) or {}, connections)
            if found:
                rel_tags[edge.ref] = found
    by_path: Dict[tuple, List] = {}
    for node in graph.nodes:
        by_path.setdefault(node.groups, []).append(node)
    types_present = sorted({node.entity_type for node in graph.nodes})
    lines: List[str] = ["@startuml", "' %s" % " ".join(str(title or view.title).split()),
                        "' Generated from the model by `%s`. Edit the model, not the diagram." % generated_by,
                        "!include <C4/C4_Deployment>", "", "title %s" % " ".join(str(title or view.title).split())]
    if types_present:
        lines.append("")
        for type_name in types_present:
            swatch = palette.type_swatch(type_name)
            legend = ENTITY_TYPES[type_name].label if type_name in ENTITY_TYPES else type_name
            lines.append('AddElementTag("%s", $bgColor="%s", $borderColor="%s", $fontColor="%s", $legendText="%s")'
                         % (type_name, swatch.fill, swatch.stroke, swatch.ink, legend))
    for tag in sorted(set(rel_tags.values())):
        lines.append('AddRelTag("%s", $legendText="%s")' % (tag, connections[tag].name))
    lines.append("")

    def element(node, indent: str) -> List[str]:
        macro = _macro(node)
        record = node.record or {}
        description = " ".join(str(record.get("description") or "").split())
        technology = tech.get(node.key, "")
        args = [alias(node.key), _quote(node.label)]
        if macro == "Deployment_Node":
            slot = technology or str(record.get("kind") or record.get("component_type") or "")
            args.append(_quote(slot))
            if description:
                args.append(_quote(description))
            # The reader appends "Built with <slot>." to a node's description
            # itself; the mark names the slot so it can take that off again.
            return (["%s%s(%s, $tags=%s) {" % (indent, macro, ", ".join(args), _quote(node.entity_type))]
                    + _mark(indent + "  ", alias(node.key), record, " ".join(slot.split()), node.entity_type)
                    + ["%s}" % indent])
        built_with = technology if technology and macro in ("System", "System_Ext") else ""
        if built_with:
            description = ("%s Built with %s." % (description, built_with)).strip()
        if description:
            args.append(_quote(description))
        return (["%s%s(%s, $tags=%s)" % (indent, macro, ", ".join(args), _quote(node.entity_type))]
                + _mark(indent, alias(node.key), record, built_with, node.entity_type))

    def children_of(path: tuple) -> List[tuple]:
        return [g for g in graph.groups if len(g) == len(path) + 1 and g[:-1] == path]

    def boundary(path: tuple, depth: int) -> None:
        indent = "  " * depth
        kind, provider = kinds.get(path, ("", ""))
        lines.append("%sBoundary(%s, %s) {" % (indent, alias("b_" + "__".join(path)),
                                              _quote(boundary_label(kind, path[-1], provider))))
        for node in sorted(by_path.get(path, []), key=lambda n: n.sort_key):
            lines.extend(element(node, indent + "  "))
        for child in children_of(path):
            boundary(child, depth + 1)
        lines.append("%s}" % indent)

    for path in [g for g in graph.groups if len(g) == 1]:
        boundary(path, 0)
    for node in sorted(by_path.get((), []), key=lambda n: n.sort_key):
        lines.extend(element(node, ""))
    if graph.edges:
        lines.append("")
    for edge in graph.edges:
        label, technology = edge.label or "", ""
        if edge.ref and model is not None:
            record = model.get("interfaces", edge.ref) or {}
            name, protocol = str(record.get("name") or ""), str(record.get("protocol") or "")
            if name or protocol:
                label, technology = name or label, protocol
        elif not label and edge.kind == "offers":
            # Drawn the traffic's way: the API before its service, the
            # topic after its publisher.
            label = "offered by" if model is not None and model.get("offered_interfaces", edge.source) else "offers"
        elif not label and edge.kind:
            label = edge_word(edge.kind)
        args = [alias(edge.source), alias(edge.target), _quote(label)]
        if technology:
            args.append(_quote(technology))
        if edge.ref in rel_tags:
            args.append("$tags=%s" % _quote(rel_tags[edge.ref]))
        lines.append("Rel(%s)" % ", ".join(args))
        if edge.ref:
            # The interface's id under the Rel, which has no slot for one
            # (read back, the landscape's sixty-four lines were sixty-four
            # new interfaces), the kind it is of, and the record's own
            # values for what the kind proposes, which the proposal wrote
            # over on the way back: fifty-eight "corrections" of an
            # unchanged page.
            record = (model.get("interfaces", edge.ref) if model is not None else None) or {}
            fields = ["source=%s" % _quote(alias(edge.source)), "target=%s" % _quote(alias(edge.target)),
                      "label=%s" % _quote(label), "interface_id=%s" % _quote(edge.ref)]
            if edge.ref in rel_tags:
                fields.append("kind=%s" % _quote(rel_tags[edge.ref]))
            for key in REL_MARK_FIELDS:
                value = record.get(key)
                if value not in (None, "", []):
                    fields.append("%s=%s" % (key, _quote(";".join(str(v) for v in value) if isinstance(value, list)
                                                         else str(value))))
            lines.append("' aac rel: %s" % "; ".join(fields))
        elif edge.kind == "sot":
            lines.append("' aac rel: source=%s; target=%s; label=%s; field=%s" % (
                _quote(alias(edge.source)), _quote(alias(edge.target)), _quote(label), _quote("source_of_truth")))
        elif edge.kind == "offers":
            lines.append("' aac rel: source=%s; target=%s; label=%s; field=%s" % (
                _quote(alias(edge.source)), _quote(alias(edge.target)), _quote(label), _quote("system_id")))
        elif model is not None and edge.kind in RELATION_TYPES:
            # A line of a relation: the row it draws, with its qualifier,
            # or that it was derived and is no row (a parent capability to
            # the framework its children reference), so neither comes back
            # as a new row or a corrected one.
            spec = RELATION_TYPES[edge.kind]
            row = next((r for r in model.relation_rows(edge.kind)
                        if {str(r.get(spec.left_column)), str(r.get(spec.right_column))} == {edge.source, edge.target}),
                       None)
            fields = ["source=%s" % _quote(alias(edge.source)), "target=%s" % _quote(alias(edge.target)),
                      "label=%s" % _quote(label)]
            if row is None:
                fields.append('derived="1"')
            else:
                fields.append("relation=%s" % _quote(edge.kind))
                if spec.qualifier and row.get(spec.qualifier) not in (None, "", []):
                    value = row[spec.qualifier]
                    fields.append("%s=%s" % (spec.qualifier, _quote(";".join(str(v) for v in value)
                                                                    if isinstance(value, list) else str(value))))
            lines.append("' aac rel: %s" % "; ".join(fields))
    lines.extend(["", "SHOW_LEGEND()", "@enduml"])
    return "\n".join(lines) + "\n"


def export_plantuml(model, views: Sequence[View], out_dir: Path, palette: Optional[Palette] = None) -> Tuple[List[Path], List[str]]:
    """Every picture view of the estate as a `.puml` under `out_dir`, bound
    once per subject where the view takes one, a file that is no longer a
    view removed; the files written and the notes."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []
    notes: List[str] = []
    palette = palette or Palette(model.config.get("palette"))
    for view in views:
        if view.kind in ("report", "timeline"):
            continue
        bound_views: List[Tuple[View, str]] = []
        if view.parameters:
            for parameter, value in render_targets(model, view):
                # An id names its file as it is; a subject that is words (a
                # business domain) by its slug, so no file name has a space.
                named = subject_slug(value) if view.parameters[0].field else value
                try:
                    bound_views.append((bind(view, {parameter: value}, model), "%s--%s" % (view.view_id, named)))
                except ViewError as exc:
                    notes.append("%s: %s" % (view.view_id, exc))
        else:
            bound_views.append((view, view.view_id))
        for bound, name in bound_views:
            try:
                graph = resolve(model, bound)
            except ViewError as exc:
                notes.append("%s: %s; left out" % (name, exc))
                continue
            path = out_dir / ("%s.puml" % name)
            path.write_text(render_plantuml(graph, model, title=bound.title, palette=palette), encoding="utf-8",
                            newline="\n")
            written.append(path)
    # Only a page this export wrote goes: the sweep once took every `.puml`
    # in whatever folder the caller named, a person's own diagrams with it.
    keep = {p.resolve() for p in written}
    for old in sorted(out_dir.glob("*.puml")):
        if old.resolve() not in keep and _exported(old):
            old.unlink()
    return written, notes


def _exported(path: Path) -> bool:
    """Whether a `.puml` is one `export_plantuml` wrote: its third line says
    so, under the title, and a file of anyone else's does not."""
    try:
        with path.open(encoding="utf-8-sig", errors="replace") as handle:
            head = [handle.readline() for _ in range(3)]
    except OSError:
        return False
    return not path.is_symlink() and head[0].strip() == "@startuml" \
        and head[2].startswith("' Generated from the model by `%s`." % _EXPORT)
