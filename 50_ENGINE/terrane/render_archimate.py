"""The estate as an ArchiMate model, in the Open Group's exchange format.

The way out to the tool most architecture practices already run: Archi,
and every other ArchiMate tool, imports the exchange format. The model's
records become elements of the ArchiMate types the reader
(`archimate_import`) maps back, so a model exported and read again is the
same model: an actor a business actor (a role a business role), a system
an application component, a data asset a data object, a capability a
capability, a process and a flow a business process, a product a product,
a value stream and its stages value streams, a work package and a change
request work packages, a policy a principle, a control a requirement, a
technology service a node or system software, an org unit a business
actor, a framework a grouping, an offered interface an application
interface composed in its component (Archi's table allows a component
composition, aggregation, flow, association, realization, triggering or
serving to an interface, and no assignment). The relations become
relationships of the kinds the reader expects: an interface a flow, ending
at the application interface when it goes through one, use a serving the other way
round, reading and writing an access with its type, realization and
support a realization, a product's systems an aggregation, a capability's
parent a composition, where a system runs a serving from the node,
governance a realization of the requirement, policy an association, the
rest associations. Roadmaps have no counterpart and are left out.

Every view of the estate that is a picture becomes a view of the model,
its elements placed where the engine's own layout places them, the
boundaries as nested nodes, every edge a connection to its relationship;
a report is a table and has no place in a diagram. Identifiers are the
model's own, prefixed `id-`, so a file exported twice is the same file.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from xml.sax.saxutils import escape, quoteattr

from .draw import Undrawable, drawing_mode
from .draw.layered import group_body, is_ribbon, layout_layered
from .draw.metrics import default_metrics
from .draw.packed import layout_packed, prepare
from .draw.tiles import layout_tiles
from .draw.wheel import layout_wheel
from .model import Model
from .payload import graph_payload
from .query import View, ViewError, bind, render_targets, resolve
from .schema import RELATION_TYPES

NS = "http://www.opengroup.org/xsd/archimate/3.0/"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
#: The method's entity types to ArchiMate element types; an actor's kind
#: and a technology service's kind refine the choice.
ELEMENT_TYPES: Dict[str, str] = {
    "actors": "BusinessActor", "systems": "ApplicationComponent", "data_assets": "DataObject",
    "capabilities": "Capability", "processes": "BusinessProcess", "flows": "BusinessProcess",
    "products": "Product", "value_streams": "ValueStream", "value_stream_stages": "ValueStream",
    "work_packages": "WorkPackage", "architecture_change_requests": "WorkPackage",
    "policies": "Principle", "controls": "Requirement", "tech_services": "Node", "org_units": "BusinessActor",
    "frameworks": "Grouping", "offered_interfaces": "ApplicationInterface",
}
SOFTWARE = re.compile(r"\b(database|db|sql|postgres|postgresql|oracle|mongo|mongodb|dynamo|cache|redis|runtime|"
                      r"middleware|broker|queue|kafka|message)\b", re.I)
NETWORK = re.compile(r"\b(network|vpc|vnet|subnet|dns|cdn|gateway|load balancer|firewall|waf|transit)\b", re.I)
#: The schema's relations to the ArchiMate relationship each becomes, and
#: whether it runs the other way round (what serves is what is used).
RELATIONSHIPS: Dict[str, Tuple[str, bool]] = {
    "actor_uses_system": ("Serving", True),
    "system_reads_writes": ("Access", False),
    "system_realizes_capability": ("Realization", False),
    "process_supports_capability": ("Realization", False),
    "process_uses_system": ("Serving", True),
    "process_uses_data_asset": ("Access", False),
    "product_includes_system": ("Aggregation", False),
    "product_realizes_capability": ("Realization", False),
    "system_uses_tech_service": ("Serving", True),
    "tech_service_connects_to": ("Association", False),
    "system_governed_by_control": ("Realization", False),
    "process_governed_by_control": ("Realization", False),
    "data_governed_by_control": ("Realization", False),
    "capability_governed_by_control": ("Realization", False),
    "system_subject_to_policy": ("Association", True),
    "process_subject_to_policy": ("Association", True),
    "data_subject_to_policy": ("Association", True),
    "capability_subject_to_policy": ("Association", True),
    "capability_aligns_to_framework": ("Association", False),
    "capability_references_framework": ("Association", False),
    "stage_crosses_capability": ("Association", False),
    "work_package_affects_system": ("Association", False),
    "change_request_affects_system": ("Association", False),
    "interface_transports_data_asset": ("", False),  # a relation of a relationship; left out
    "flow_step": ("", False),
}
ACCESS = {"read": "Read", "write": "Write", "readwrite": "ReadWrite", "both": "ReadWrite"}
#: The record's fields written as properties, by the name Archi shows: what
#: the element cannot say (the export groups by type, so a system's domain
#: read back as "System") and what a connection kind proposes, as the
#: record has it, so the proposal is not written over it on the way back.
PROPERTY_NAMES = {
    "company_domain": "Company domain", "hosting": "Hosting", "actor_kind": "Actor kind", "internal": "Internal",
    "integration_style": "Integration style", "auth_method": "Auth method", "frequency": "Frequency",
    "direction": "Direction", "patterns": "Patterns", "protocol": "Protocol",
    "data_classification": "Data classification", "specification": "Specification",
}
ELEMENT_FIELDS = ("company_domain", "hosting", "actor_kind", "internal")
FLOW_FIELDS = ("integration_style", "auth_method", "frequency", "direction", "patterns")
#: What an application interface carries beside its domain: what every
#: connection through it is spoken in, said once.
OFFERED_FIELDS = ("protocol", "integration_style", "auth_method", "frequency", "data_classification",
                  "specification", "patterns")


def _value(value) -> str:
    return ";".join(str(v) for v in value) if isinstance(value, list) else str(value)


def record_properties(type_name: str, record: dict, fields: Sequence[str] = ELEMENT_FIELDS) -> Dict[str, str]:
    """The record's own fields as properties: the domain always, blank or
    not, where the type has one (a record with none read back with the
    grouping's name for its domain), the rest when the record says them."""
    from .schema import ENTITY_TYPES

    out: Dict[str, str] = {}
    entity_type = ENTITY_TYPES.get(type_name)
    if fields is ELEMENT_FIELDS:
        # The method's type first: a value stream stage shares its prefix
        # with a value stream and is a ValueStream in ArchiMate too, and
        # sixty stages came back as sixty new value streams.
        out["Type"] = type_name
    for key in fields:
        value = record.get(key)
        if value not in (None, "", []):
            out[PROPERTY_NAMES[key]] = _value(value)
        elif key == "company_domain" and entity_type is not None and any(f.name == key for f in entity_type.fields):
            out[PROPERTY_NAMES[key]] = ""
    return out


def _id(entity_id: str) -> str:
    return "id-" + re.sub(r"[^A-Za-z0-9._-]+", "-", str(entity_id))


def _name(record: dict, fallback: str) -> str:
    return str(record.get("name") or record.get("title") or fallback)


def _element_type(type_name: str, record: dict) -> str:
    if type_name == "actors":
        kind = str(record.get("actor_kind") or "")
        return "BusinessRole" if kind == "Role" else "BusinessActor"
    if type_name == "tech_services":
        text = "%s %s" % (record.get("kind") or "", record.get("name") or "")
        if NETWORK.search(text):
            return "CommunicationNetwork"
        if SOFTWARE.search(text):
            return "SystemSoftware"
        return "Node"
    return ELEMENT_TYPES[type_name]


class Exported:
    """What the file holds, gathered before it is written."""

    def __init__(self) -> None:
        #: identifier, type, name, documentation, properties (the record's own fields).
        self.elements: List[Tuple[str, str, str, str, Dict[str, str]]] = []
        self.element_ids: set = set()
        #: identifier, type, source, target, name, access, properties (a flow's connection kind and protocol).
        self.relationships: List[Tuple[str, str, str, str, str, str, Dict[str, str]]] = []
        #: (kind, source, target) of an edge in a view to its relationship's identifier.
        self.by_edge: Dict[Tuple[str, str, str], str] = {}
        self.notes: List[str] = []

    def element(self, identifier: str, kind: str, name: str, documentation: str = "",
                properties: Optional[Dict[str, str]] = None) -> None:
        if identifier in self.element_ids:
            return
        self.element_ids.add(identifier)
        self.elements.append((identifier, kind, name, documentation, dict(properties or {})))

    def relationship(self, identifier: str, kind: str, source: str, target: str, name: str = "",
                     access: str = "", edge: Optional[Tuple[str, str, str]] = None,
                     properties: Optional[Dict[str, str]] = None) -> None:
        if source not in self.element_ids or target not in self.element_ids:
            return
        self.relationships.append((identifier, kind, source, target, name, access, dict(properties or {})))
        if edge is not None:
            self.by_edge[edge] = identifier


def _property_id(key: str) -> str:
    """The identifier of a property definition, from its name."""
    return "propid-" + re.sub(r"[^a-z0-9]+", "-", key.lower()).strip("-")


def gather(model: Model) -> Exported:
    out = Exported()
    for type_name, archimate in ELEMENT_TYPES.items():
        for entity_id, record in sorted(model.entities.get(type_name, {}).items()):
            documentation = str(record.get("description") or "")
            if type_name == "frameworks":
                documentation = ("A reference framework. " + documentation).strip()
            properties = record_properties(type_name, record)
            if type_name == "offered_interfaces":
                properties.update(record_properties(type_name, record, OFFERED_FIELDS))
            out.element(_id(entity_id), _element_type(type_name, record), _name(record, entity_id), documentation,
                        properties)
    left = sorted(t for t in model.entities if t not in ELEMENT_TYPES and t != "interfaces" and model.entities[t])
    if left:
        out.notes.append("no counterpart in ArchiMate: %s; left out" % ", ".join(left))

    # Reference fields: a capability's parent, an owner, a source of truth.
    for type_name in ELEMENT_TYPES:
        for entity_id, record in sorted(model.entities.get(type_name, {}).items()):
            parent = record.get("parent_capability_id")
            # Each carries the field it draws, so it comes back as that field
            # and not as whatever the reader would make of an association.
            if type_name == "capabilities" and parent:
                out.relationship(_id("rel-parent-%s-%s" % (parent, entity_id)), "Composition", _id(parent),
                                 _id(entity_id), edge=("parent_capability_id", str(parent), str(entity_id)),
                                 properties={"Field": "parent_capability_id"})
            for owner_field in ("owner_org_id", "data_owner_org_id", "requestor_org_id"):
                owner = record.get(owner_field)
                if owner:
                    out.relationship(_id("rel-owner-%s-%s" % (owner, entity_id)), "Association", _id(owner),
                                     _id(entity_id), "owns", edge=(owner_field, str(owner), str(entity_id)),
                                     properties={"Field": owner_field})
            offered_by = record.get("system_id")
            if type_name == "offered_interfaces" and offered_by:
                # Composed in the component that offers it, as ArchiMate
                # has an interface; the drawing joins the two in the
                # traffic's direction, so either way round is this line.
                identifier = _id("rel-offers-%s-%s" % (offered_by, entity_id))
                out.relationship(identifier, "Composition", _id(offered_by), _id(entity_id),
                                 edge=("offers", str(offered_by), str(entity_id)),
                                 properties={"Field": "system_id"})
                out.by_edge.setdefault(("offers", str(entity_id), str(offered_by)), identifier)
            sot = record.get("source_of_truth")
            if type_name == "data_assets" and sot:
                out.relationship(_id("rel-sot-%s-%s" % (sot, entity_id)), "Association", _id(sot), _id(entity_id),
                                 "source of truth", edge=("source_of_truth", str(sot), str(entity_id)),
                                 properties={"Field": "source_of_truth"})

    # Interfaces: a flow from the caller to the called, named, with its
    # protocol in the name for the eye and as a property for the reader,
    # and its connection kind as a property, so the flow comes back as the
    # connection it was and not as a name with a protocol in brackets.
    from .connections import kind_of, load_connections
    from .library import LibraryError

    try:
        catalog = load_connections(model.root)
    except LibraryError:
        catalog = {}
    for interface_id, record in sorted(model.entities.get("interfaces", {}).items()):
        source, target = record.get("source_system_id"), record.get("target_system_id")
        if not source or not target:
            continue
        # Through an offered interface, the flow ends at it on its owner's
        # side: the caller's traffic goes to the API, the topic's to its
        # readers. A landscape drawing the line to the box has no
        # relationship to draw it with, and leaves it off the view.
        offered = model.get("offered_interfaces", str(record.get("offered_interface_id") or "")) or {}
        owner = str(offered.get("system_id") or "")
        if owner and owner == str(target) and owner != str(source):
            target = offered["offered_interface_id"]
        elif owner and owner == str(source) and owner != str(target):
            source = offered["offered_interface_id"]
        label = str(record.get("name") or "")
        protocol = str(record.get("protocol") or "")
        name = " ".join(p for p in (label, "(%s)" % protocol if protocol and protocol != label else "") if p)
        properties: Dict[str, str] = {"Interface id": str(interface_id)}
        if protocol:
            properties["Protocol"] = protocol
        found = kind_of(record, catalog) if catalog else None
        if found:
            properties["Connection kind"] = found
        # What the kind proposes, as the record has it: the proposal was
        # written over the record's own values on the way back.
        properties.update(record_properties("interfaces", record, FLOW_FIELDS))
        out.relationship(_id(interface_id), "Flow", _id(source), _id(target), name,
                         edge=("interface", str(source), str(target)), properties=properties)

    # The relations of the schema.
    for relation_name, (kind, reverse) in RELATIONSHIPS.items():
        if not kind:
            continue
        relation = RELATION_TYPES.get(relation_name)
        if relation is None:
            continue
        for n, row in enumerate(model.relations.get(relation_name, []), 1):
            left, right = str(row.get(relation.left_column) or ""), str(row.get(relation.right_column) or "")
            if not left or not right:
                continue
            source, target = (right, left) if reverse else (left, right)
            qualifier = str(row.get(relation.qualifier) or "") if relation.qualifier else ""
            access = ACCESS.get(qualifier.lower(), "ReadWrite") if kind == "Access" else ""
            name = "" if kind == "Access" else qualifier
            # The row it is, by name and qualifier, so it comes back as that
            # row and not as what the reader would make of the relationship.
            properties = {"Relation": relation_name}
            if relation.qualifier and qualifier:
                properties[relation.qualifier.replace("_", " ").capitalize()] = qualifier
            out.relationship(_id("rel-%s-%s-%s" % (relation_name, left, right)), kind, _id(source), _id(target),
                             name, access, edge=(relation_name, left, right), properties=properties)
    return out


# ---------------------------------------------------------------------------
# views
# ---------------------------------------------------------------------------

class ViewNodes:
    def __init__(self, name: str, view_id: str) -> None:
        self.name = name
        self.view_id = view_id
        #: node id -> (x, y, w, h, parent id or None, element id or None, label)
        self.nodes: Dict[str, Tuple[float, float, float, float, Optional[str], Optional[str], str]] = {}
        self.order: List[str] = []
        self.connections: List[Tuple[str, str, str]] = []  # relationship identifier, source node, target node


def geometry(payload: dict) -> Optional[Dict[str, Tuple[float, float, float, float]]]:
    """Every node's box on the drawing the engine lays out, leaves and
    boundaries, as the app would without ELK or an organic pass; None
    when the drawing is one those would have to make."""
    m = default_metrics()
    if drawing_mode(payload).kind == "tiles":
        lay = layout_tiles(payload, 1240, m)
        boxes: Dict[str, Tuple[float, float, float, float]] = {}
        for tile in lay.all_tiles():
            boxes[tile.id] = (tile.x, tile.y, tile.w, tile.h)
        for band in lay.bands:
            boxes[band.id] = (band.x, band.y, band.w, band.h)
        return boxes
    prep = prepare(payload)
    mode = drawing_mode(payload, prep)
    if mode.kind == "packed":
        lay = layout_packed(payload, 1240, 871.4375, prep)
        boxes = {leaf: (x - w / 2, y - h / 2, w, h) for leaf, (x, y, w, h) in lay.leaves.items()}
        for group_id, (x1, y1, x2, y2) in lay.groups.items():
            boxes[group_id] = (x1, y1, x2 - x1, y2 - y1)
        return boxes
    if mode.kind == "wheel":
        lay = layout_wheel(payload, 1240, 871.4375, prep)
        return {leaf: (x - w / 2, y - h / 2, w, h) for leaf, (x, y, w, h) in lay.leaves.items()}
    lay = layout_layered(payload, 1240, 871.4375, prep, m)
    if is_ribbon(prep, lay, m):
        return None
    boxes = {leaf: (x - w / 2, y - h / 2, w, h) for leaf, (x, y, w, h) in lay.leaves.items()}
    memo: Dict[str, Tuple[float, float, float, float]] = {}
    for group in prep.groups:
        x1, y1, x2, y2 = group_body(prep, lay, group, memo)
        boxes[group.id] = (x1, y1, x2 - x1, y2 - y1)
    return boxes


def view_nodes(payload: dict, exported: Exported, title: str, view_id: str) -> Optional[ViewNodes]:
    boxes = geometry(payload)
    if boxes is None:
        return None
    out = ViewNodes(title, view_id)
    x0 = min((b[0] for b in boxes.values()), default=0.0)
    y0 = min((b[1] for b in boxes.values()), default=0.0)
    for element in payload.get("elements", []):
        data = element["data"]
        if data.get("source"):
            continue
        node_id = data["id"]
        box = boxes.get(node_id)
        if box is None:
            continue
        x, y, w, h = box
        element_id = None if data.get("isGroup") else _id(node_id)
        if element_id is not None and element_id not in exported.element_ids:
            element_id = None
        out.nodes[node_id] = (x - x0 + 20, y - y0 + 20, w, h, data.get("parent"), element_id, str(data.get("label") or ""))
        out.order.append(node_id)
    for element in payload.get("elements", []):
        data = element["data"]
        if not data.get("source"):
            continue
        key = (str(data.get("kind") or ""), str(data["source"]), str(data["target"]))
        identifier = exported.by_edge.get(key)
        if identifier and data["source"] in out.nodes and data["target"] in out.nodes:
            out.connections.append((identifier, data["source"], data["target"]))
    return out


def gather_views(model: Model, views: Sequence[View], palette, icons, components, exported: Exported) -> List[ViewNodes]:
    out: List[ViewNodes] = []
    for view in views:
        if view.kind in ("report", "timeline"):
            continue
        bound_views: List[Tuple[View, str]] = []
        if view.parameters:
            for parameter, value in render_targets(model, view):
                try:
                    bound_views.append((bind(view, {parameter: value}, model),
                                        "%s--%s" % (view.view_id, str(value).lower())))
                except ViewError as exc:
                    exported.notes.append("%s: %s" % (view.view_id, exc))
        else:
            bound_views.append((view, view.view_id))
        for bound, view_id in bound_views:
            try:
                graph = resolve(model, bound)
                payload = graph_payload(model, bound, palette, icons, components, graph=graph)
                nodes = view_nodes(payload, exported, bound.title, view_id)
            except (ViewError, Undrawable) as exc:
                exported.notes.append("%s: %s; left out" % (view_id, exc))
                continue
            if nodes is None:
                exported.notes.append("%s: laid out by the app in its browser; left out" % view_id)
                continue
            out.append(nodes)
    return out


# ---------------------------------------------------------------------------
# the file
# ---------------------------------------------------------------------------

def _f(value: float) -> str:
    return str(int(round(value)))


def render(model: Model, exported: Exported, views: Sequence[ViewNodes]) -> str:
    name = str(model.config.get("name") or "Architecture Model")
    out: List[str] = ['<?xml version="1.0" encoding="UTF-8"?>',
                      '<model xmlns=%s xmlns:xsi=%s identifier=%s>' % (quoteattr(NS), quoteattr(XSI),
                                                                        quoteattr(_id("model"))),
                      '  <name xml:lang="en">%s</name>' % escape(name),
                      '  <documentation xml:lang="en">Exported from the model by architecture-as-code. Edit the '
                      'model, not the export.</documentation>',
                      "  <elements>"]
    def write_properties(properties: Dict[str, str], indent: str) -> None:
        out.append("%s<properties>" % indent)
        for key, value in properties.items():
            out.append('%s  <property propertyDefinitionRef=%s>' % (indent, quoteattr(_property_id(key))))
            out.append('%s    <value xml:lang="en">%s</value>' % (indent, escape(value)))
            out.append("%s  </property>" % indent)
        out.append("%s</properties>" % indent)

    for identifier, kind, label, documentation, properties in exported.elements:
        out.append('    <element identifier=%s xsi:type=%s>' % (quoteattr(identifier), quoteattr(kind)))
        out.append('      <name xml:lang="en">%s</name>' % escape(label))
        if documentation:
            out.append('      <documentation xml:lang="en">%s</documentation>' % escape(documentation))
        if properties:
            write_properties(properties, "      ")
        out.append("    </element>")
    out.append("  </elements>")
    # The property definitions the elements and the relationships use, in
    # the order first used, so the same model is the same bytes.
    definitions: List[str] = []
    for *_rest, properties in exported.elements:
        for key in properties:
            if key not in definitions:
                definitions.append(key)
    for *_rest, properties in exported.relationships:
        for key in properties:
            if key not in definitions:
                definitions.append(key)
    if exported.relationships:
        out.append("  <relationships>")
        for identifier, kind, source, target, label, access, properties in exported.relationships:
            attrs = ' identifier=%s source=%s target=%s xsi:type=%s' % (
                quoteattr(identifier), quoteattr(source), quoteattr(target), quoteattr(kind))
            if access:
                attrs += " accessType=%s" % quoteattr(access)
            if label or properties:
                out.append("    <relationship%s>" % attrs)
                if label:
                    out.append('      <name xml:lang="en">%s</name>' % escape(label))
                if properties:
                    write_properties(properties, "      ")
                out.append("    </relationship>")
            else:
                out.append("    <relationship%s/>" % attrs)
        out.append("  </relationships>")
    if definitions:
        out.append("  <propertyDefinitions>")
        for key in definitions:
            out.append('    <propertyDefinition identifier=%s type="string">' % quoteattr(_property_id(key)))
            out.append('      <name xml:lang="en">%s</name>' % escape(key))
            out.append("    </propertyDefinition>")
        out.append("  </propertyDefinitions>")
    if views:
        out.append("  <views>")
        out.append("    <diagrams>")
        for view in views:
            out.append('      <view identifier=%s xsi:type="Diagram">' % quoteattr(_id("view-" + view.view_id)))
            out.append('        <name xml:lang="en">%s</name>' % escape(view.name))
            children: Dict[Optional[str], List[str]] = {}
            for node_id in view.order:
                children.setdefault(view.nodes[node_id][4], []).append(node_id)

            def emit(parent: Optional[str], indent: str) -> None:
                for node_id in children.get(parent, []):
                    x, y, w, h, _parent, element_id, label = view.nodes[node_id]
                    node_ref = quoteattr(_id("view-%s-%s" % (view.view_id, node_id)))
                    if element_id is not None:
                        out.append('%s<node identifier=%s elementRef=%s xsi:type="Element" x="%s" y="%s" w="%s" h="%s">'
                                   % (indent, node_ref, quoteattr(element_id), _f(x), _f(y), _f(w), _f(h)))
                    else:
                        out.append('%s<node identifier=%s xsi:type="Container" x="%s" y="%s" w="%s" h="%s">'
                                   % (indent, node_ref, _f(x), _f(y), _f(w), _f(h)))
                        out.append('%s  <label xml:lang="en">%s</label>' % (indent, escape(label)))
                    emit(node_id, indent + "  ")
                    out.append("%s</node>" % indent)

            emit(None, "        ")
            for n, (identifier, source, target) in enumerate(view.connections, 1):
                out.append('        <connection identifier=%s relationshipRef=%s xsi:type="Relationship" source=%s '
                           'target=%s/>' % (quoteattr(_id("view-%s-c%d" % (view.view_id, n))), quoteattr(identifier),
                                            quoteattr(_id("view-%s-%s" % (view.view_id, source))),
                                            quoteattr(_id("view-%s-%s" % (view.view_id, target)))))
            out.append("      </view>")
        out.append("    </diagrams>")
        out.append("  </views>")
    out.append("</model>")
    return "\n".join(out) + "\n"


def export_archimate(model: Model, views: Sequence[View], out_path: Path, palette=None, icons=None,
                     components=None) -> Tuple[Path, List[str]]:
    """Write the estate as an ArchiMate exchange file at `out_path`; the
    path and the notes (what was left out and why). With `palette`,
    `icons` and `components` the views are written too."""
    exported = gather(model)
    drawn: List[ViewNodes] = []
    if palette is not None and icons is not None and components is not None:
        drawn = gather_views(model, views, palette, icons, components, exported)
    text = render(model, exported, drawn)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8", newline="\n")
    return out_path, exported.notes
