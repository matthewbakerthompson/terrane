"""An ArchiMate model read as a sketch.

What an architecture practice has most often is not a diagram but an
ArchiMate model: a file Archi saves (`.archimate`, its own XML) or the
Open Group's exchange format (`.xml`, what every ArchiMate tool exports),
holding the elements, the relationships between them and the views that
show a subset of each. This reads both as one sketch, so the pictures the
engine draws come from the model the practice already keeps.

The elements become records of the method's types: a business actor an
actor (a role an actor of kind Role), an application component a system,
a data or business object a data asset, a capability a capability, a
business process or function a process, a product a product, a value
stream a value stream, a work package a work package, a principle a
policy, a requirement or constraint a control, and a node, device, system
software, technology service or network a technology service, and an
application interface an offered interface, of the component that composes
it (or aggregates it, or is assigned it in an older model). A grouping
is the domain of what it composes or aggregates, in the model or by
nesting in a view, and not a record of its own. A service stands for the
element that realizes it, an interface where one is assigned it, so a
relationship to the service lands on what offers it; one nothing realizes
is said and left out. A flow, a triggering or a serving between a
component and an interface is a connection through it. Junctions, goals, drivers, assessments, plateaus, gaps and the other
motivation and implementation elements have no counterpart here and are
said with their count.

A relationship is the connection two such things have here, chosen by its
kind: serving the other way round, since what serves is what is used; flow
and triggering between systems an interface; realization what a system
realizes; access what a system reads or writes, by its access type;
assignment of a component to a node where it runs; composition and
aggregation a product's systems or a capability's parent; association
whatever the method has between the two. A relationship the method lacks
between those two types is said and left out, as the other readers say.

Every view of the model becomes a view of the sketch, written out: the
elements it shows and the connections among them, grouped by domain where
the view nests things, and the whole model is one more view beside them.
"""

from __future__ import annotations

import re
from typing import Dict, List, NamedTuple, Optional, Tuple
from xml.etree import ElementTree

from .mermaid_import import TYPE_PREFIX, ReadError, _document, _entity_id, _ident, _Read  # noqa: F401
from .schema import ENTITY_TYPES as ENTITY_TYPES_BY_NAME

#: ArchiMate element type (lower case, no prefix) to the sketch's type and,
#: for an actor, its kind.
ELEMENT_TYPES: Dict[str, Tuple[str, str]] = {
    "businessactor": ("actors", "Person"), "businessrole": ("actors", "Role"),
    "businesscollaboration": ("actors", "Organization"), "stakeholder": ("actors", "Person"),
    "applicationcomponent": ("systems", ""), "applicationcollaboration": ("systems", ""),
    "dataobject": ("data_assets", ""), "businessobject": ("data_assets", ""), "artifact": ("data_assets", ""),
    "capability": ("capabilities", ""),
    "businessprocess": ("processes", ""), "businessfunction": ("processes", ""),
    "businessinteraction": ("processes", ""),
    "product": ("products", ""), "valuestream": ("value_streams", ""), "workpackage": ("work_packages", ""),
    "principle": ("policies", ""), "requirement": ("controls", ""), "constraint": ("controls", ""),
    "node": ("tech_services", ""), "device": ("tech_services", ""), "systemsoftware": ("tech_services", ""),
    "technologyservice": ("tech_services", ""), "communicationnetwork": ("tech_services", ""),
    "technologycollaboration": ("tech_services", ""), "facility": ("tech_services", ""),
    "equipment": ("tech_services", ""), "path": ("tech_services", ""),
    "applicationinterface": ("offered_interfaces", ""),
}
#: What is the domain of what it holds, not a record.
GROUPINGS = {"grouping", "location"}
#: What stands for the element that realizes or offers it.
STAND_INS = {"applicationservice", "applicationfunction", "applicationprocess",
             "applicationinteraction", "applicationevent", "businessservice", "businessinterface", "businessevent",
             "technologyinterface", "technologyfunction", "technologyprocess", "technologyevent",
             "technologyinteraction"}
JUNCTIONS = {"junction", "andjunction", "orjunction"}
#: The method's id prefixes, for an identifier the engine itself wrote; a
#: prefix two types share (`VS`) reads as the first of them.
BY_PREFIX: Dict[str, str] = {}
for _type_name, _prefix in TYPE_PREFIX.items():
    BY_PREFIX.setdefault(_prefix, _type_name)
#: Archi's own access types, by number; the exchange format spells them.
ACCESS_NUMBERS = {"0": "Write", "1": "Read", "2": "Access", "3": "ReadWrite"}
ACCESS_WORDS = {"read": "reads", "write": "writes", "readwrite": "reads and writes", "access": "reads and writes"}


class ArchimateError(ReadError):
    pass


class Elem(NamedTuple):
    id: str
    type: str
    name: str
    documentation: str
    #: The element's properties by their name, lower case: the engine's own
    #: export puts the record's domain, hosting and kind there.
    properties: Dict[str, str] = {}


class Rel(NamedTuple):
    id: str
    type: str
    source: str
    target: str
    name: str
    #: Read, Write, ReadWrite or Access for an access relationship; else "".
    access: str
    #: The relationship's properties by their name, lower case: the engine's
    #: own export puts a flow's protocol and connection kind there.
    properties: Dict[str, str] = {}


class View(NamedTuple):
    name: str
    #: Element ids in the order the view places them.
    elements: List[str]
    #: Element id to the name of the group or grouping it is nested in.
    nested: Dict[str, str]
    #: Relationship ids the view draws.
    relationships: List[str]


class Model(NamedTuple):
    name: str
    elements: Dict[str, Elem]
    relationships: List[Rel]
    views: List[View]
    #: What the model says of itself; the engine's own export says so here.
    documentation: str = ""


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _xsi_type(node: ElementTree.Element) -> str:
    """The element's type as the file says it (`ApplicationComponent`,
    `archimate:ServingRelationship`), lower case, prefix off."""
    for key, value in node.attrib.items():
        if _local(key) == "type":
            return value.rsplit(":", 1)[-1].strip().lower()
    return ""


def _text(node: Optional[ElementTree.Element]) -> str:
    return " ".join((node.text or "").split()) if node is not None else ""


def _child(node: ElementTree.Element, name: str) -> Optional[ElementTree.Element]:
    for child in node:
        if _local(child.tag) == name:
            return child
    return None


def parse(text: str) -> Model:
    """The model in the file, whichever of the two formats it is in."""
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as exc:
        raise ArchimateError("not XML: %s" % exc) from exc
    if _local(root.tag) != "model":
        raise ArchimateError("not an ArchiMate model: the root is <%s>, not <model>" % _local(root.tag))
    if _child(root, "elements") is not None or "identifier" in root.attrib:
        return _parse_exchange(root)
    if any(_local(child.tag) == "folder" for child in root):
        return _parse_archi(root)
    raise ArchimateError("not an ArchiMate model: neither the exchange format's <elements> nor Archi's <folder>s")


def _parse_exchange(root: ElementTree.Element) -> Model:
    name = _text(_child(root, "name")) or "ArchiMate model"
    definitions: Dict[str, str] = {}
    for node in root.iter():
        if _local(node.tag) == "propertyDefinition" and "identifier" in node.attrib:
            definitions[node.attrib["identifier"]] = _text(_child(node, "name")).lower()

    def properties_of(node: ElementTree.Element) -> Dict[str, str]:
        properties: Dict[str, str] = {}
        for prop in node.iter():
            if _local(prop.tag) == "property" and prop.attrib.get("propertyDefinitionRef"):
                key = definitions.get(prop.attrib["propertyDefinitionRef"], prop.attrib["propertyDefinitionRef"])
                properties[key] = _text(_child(prop, "value"))
        return properties

    elements: Dict[str, Elem] = {}
    for node in root.iter():
        if _local(node.tag) == "element" and "identifier" in node.attrib:
            elements[node.attrib["identifier"]] = Elem(
                node.attrib["identifier"], _xsi_type(node), _text(_child(node, "name")),
                _text(_child(node, "documentation")), properties_of(node))
    relationships: List[Rel] = []
    for node in root.iter():
        if _local(node.tag) == "relationship" and "identifier" in node.attrib:
            kind = _xsi_type(node)
            relationships.append(Rel(node.attrib["identifier"], kind, node.attrib.get("source", ""),
                                     node.attrib.get("target", ""), _text(_child(node, "name")),
                                     node.attrib.get("accessType", "") if kind == "access" else "",
                                     properties_of(node)))
    views: List[View] = []
    for node in root.iter():
        if _local(node.tag) != "view":
            continue
        shown: List[str] = []
        nested: Dict[str, str] = {}
        rel_ids: List[str] = []

        def walk(parent: ElementTree.Element, group: str) -> None:
            for child in parent:
                tag = _local(child.tag)
                if tag == "node":
                    ref = child.attrib.get("elementRef", "")
                    inner = group
                    if ref:
                        shown.append(ref)
                        if group:
                            nested[ref] = group
                        elem = elements.get(ref)
                        if elem is not None and elem.type in GROUPINGS:
                            inner = elem.name
                    elif _xsi_type(child) in ("container", "group"):
                        inner = _text(_child(child, "label")) or group
                    walk(child, inner)
                elif tag == "connection" and child.attrib.get("relationshipRef"):
                    rel_ids.append(child.attrib["relationshipRef"])
                else:
                    walk(child, group)

        walk(node, "")
        views.append(View(_text(_child(node, "name")) or "View", shown, nested, rel_ids))
    return Model(name, elements, relationships, views, _text(_child(root, "documentation")))


def _parse_archi(root: ElementTree.Element) -> Model:
    name = root.attrib.get("name") or "ArchiMate model"
    elements: Dict[str, Elem] = {}
    relationships: List[Rel] = []
    diagrams: List[ElementTree.Element] = []
    for node in root.iter():
        if _local(node.tag) != "element" or "id" not in node.attrib:
            continue
        kind = _xsi_type(node)
        if kind.endswith("relationship"):
            kind = kind[:-len("relationship")]
            # Archi keeps a property as `<property key="..." value="..."/>`.
            properties = {str(p.attrib.get("key", "")).lower(): str(p.attrib.get("value", ""))
                          for p in node if _local(p.tag) == "property" and p.attrib.get("key")}
            relationships.append(Rel(node.attrib["id"], kind, node.attrib.get("source", ""),
                                     node.attrib.get("target", ""), node.attrib.get("name", ""),
                                     ACCESS_NUMBERS.get(node.attrib.get("accessType", "0"), "Write")
                                     if kind == "access" else "", properties))
        elif kind == "archimatediagrammodel":
            diagrams.append(node)
        elif kind in ("sketchmodel", "canvasmodel"):
            continue
        else:
            # Archi keeps an element's properties as `<property key="..." value="..."/>` too.
            element_properties = {str(p.attrib.get("key", "")).lower(): str(p.attrib.get("value", ""))
                                  for p in node if _local(p.tag) == "property" and p.attrib.get("key")}
            elements[node.attrib["id"]] = Elem(node.attrib["id"], kind, node.attrib.get("name", ""),
                                               _text(_child(node, "documentation")), element_properties)
    views: List[View] = []
    for diagram in diagrams:
        shown: List[str] = []
        nested: Dict[str, str] = {}
        rel_ids: List[str] = []

        def walk(parent: ElementTree.Element, group: str) -> None:
            for child in parent:
                tag = _local(child.tag)
                if tag == "child":
                    kind = _xsi_type(child)
                    inner = group
                    ref = child.attrib.get("archimateElement", "")
                    if ref:
                        shown.append(ref)
                        if group:
                            nested[ref] = group
                        elem = elements.get(ref)
                        if elem is not None and elem.type in GROUPINGS:
                            inner = elem.name
                    elif kind == "group":
                        inner = child.attrib.get("name") or group
                    walk(child, inner)
                elif tag == "sourceConnection" and child.attrib.get("archimateRelationship"):
                    rel_ids.append(child.attrib["archimateRelationship"])

        walk(diagram, "")
        views.append(View(diagram.attrib.get("name") or "View", shown, nested, rel_ids))
    return Model(name, elements, relationships, views, _text(_child(root, "purpose")))


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "view"


def sketch_from_archimate(text: str, name: str = "Imported from ArchiMate") -> Tuple[dict, List[str]]:
    """The sketch an ArchiMate model reads as, and the notes."""
    model = parse(text)
    read = _Read()
    read.title = model.name if model.name != "ArchiMate model" else name
    read.source = "an ArchiMate model: a record per element, a connection per relationship"
    read.group_word = "the groupings as domains"
    notes = read.notes
    elements = model.elements

    # A service or an interface stands for the element that realizes or
    # offers it; the first realizer or assigner wins, a component before
    # anything else.
    stand_in: Dict[str, str] = {}
    for rel in model.relationships:
        target = elements.get(rel.target)
        if target is None or target.type not in STAND_INS or rel.source not in elements:
            continue
        if rel.type in ("realization", "assignment") and elements[rel.source].type not in STAND_INS:
            current = stand_in.get(rel.target)
            if current is None or (elements[rel.source].type in ELEMENT_TYPES
                                   and elements[current].type not in ELEMENT_TYPES):
                stand_in[rel.target] = rel.source

    def resolve(element_id: str) -> Optional[str]:
        seen = set()
        while element_id in stand_in and element_id not in seen:
            seen.add(element_id)
            element_id = stand_in[element_id]
        return element_id if element_id in elements and elements[element_id].type in ELEMENT_TYPES else None

    # The domain of a thing: the grouping that composes or aggregates it.
    domain: Dict[str, str] = {}
    for rel in model.relationships:
        source = elements.get(rel.source)
        if source is not None and source.type in GROUPINGS and rel.type in ("composition", "aggregation"):
            if rel.target in elements and rel.target not in domain:
                domain[rel.target] = source.name
    for view in model.views:
        for element_id, group in view.nested.items():
            domain.setdefault(element_id, group)

    # Records, in the model's order, with ids made from the names, or kept
    # where the engine itself wrote the file.
    exported = "architecture-as-code" in model.documentation
    mids: Dict[str, str] = {}
    taken: Dict[str, int] = {}
    left_out: Dict[str, int] = {}
    for element in elements.values():
        if element.type in ELEMENT_TYPES:
            type_name, kind = ELEMENT_TYPES[element.type]
            # In a file the engine exported the identifiers are the method's
            # own ids: keep them, and the type each names, so the model
            # comes back as it went out (an org unit is a business actor in
            # ArchiMate and an org unit here). Any other file's identifiers
            # are opaque, and the id is made from the name.
            own = _ident(element.id[3:] if element.id.lower().startswith("id-") else element.id)
            own_type = BY_PREFIX.get(own.split("-", 1)[0]) if exported and "-" in own else None
            said_type = str(element.properties.get("type") or "")
            if exported and said_type in ENTITY_TYPES_BY_NAME:
                own_type = said_type  # the property outranks the prefix two types share
            if own_type is not None:
                type_name, kind = own_type, kind if own_type == "actors" else ""
                base = own
            else:
                base = _ident(element.name or element.id)
            n = taken.get(base, 0) + 1
            taken[base] = n
            mid = base if n == 1 else "%s-%d" % (base, n)
            mids[element.id] = mid
            # The record's own fields, where the export wrote them as
            # properties, over the grouping: the export groups by type, and
            # a system's domain read back as "System".
            props = {key.replace(" ", "_"): value for key, value in element.properties.items()}
            entry = read.node(mid, props["company_domain"] if "company_domain" in props else domain.get(element.id, ""))
            if "company_domain" in props:
                entry["domain"] = props["company_domain"]
            entry["type"] = type_name
            entry["label"] = element.name or element.id
            entry["description"] = element.documentation
            if props.get("actor_kind"):
                kind = props["actor_kind"]
            if kind:
                entry["kind"] = kind
            if type_name == "systems" and props.get("hosting"):
                entry["external"] = props["hosting"]
            if type_name == "actors" and props.get("internal"):
                entry["external"] = props["internal"]
        elif element.type in GROUPINGS:
            read.any_group = True
        elif element.type in STAND_INS and element.id in stand_in:
            continue
        else:
            left_out[element.type] = left_out.get(element.type, 0) + 1

    # Links: the connection each relationship is here.
    skipped: Dict[str, int] = {}
    for rel in model.relationships:
        source, target = elements.get(rel.source), elements.get(rel.target)
        if source is None or target is None:
            continue
        if source.type in GROUPINGS or target.type in GROUPINGS:
            continue  # the domain, already read
        if source.type in JUNCTIONS or target.type in JUNCTIONS:
            skipped["through a junction"] = skipped.get("through a junction", 0) + 1
            continue
        a, b = resolve(rel.source), resolve(rel.target)
        if a is None or b is None:
            if (source.type in STAND_INS and rel.source not in stand_in) or (
                    target.type in STAND_INS and rel.target not in stand_in):
                skipped["to a service nothing realizes"] = skipped.get("to a service nothing realizes", 0) + 1
            elif source.type in ELEMENT_TYPES or target.type in ELEMENT_TYPES:
                skipped["to an element with no counterpart here"] = skipped.get(
                    "to an element with no counterpart here", 0) + 1
            continue
        if a == b:
            continue  # a component realizing its own service
        ta, tb = ELEMENT_TYPES[elements[a].type][0], ELEMENT_TYPES[elements[b].type][0]
        ma, mb = mids[a], mids[b]
        kind = rel.type
        props = {key.replace(" ", "_"): value for key, value in rel.properties.items()}
        if props.get("field") or props.get("relation"):
            # The export's own line: the field it draws, or the row it is
            # with its qualifier, over what the reader would make of the
            # relationship's kind, name and ends.
            read.links.append((ma, mb, rel.name, ""))
            mark = {"field": props["field"]} if props.get("field") else {
                key: value for key, value in props.items() if key not in ("field",)}
            read.link_marks.setdefault((_ident(ma), _ident(mb), rel.name), []).append(mark)
            continue
        if kind == "serving":
            # What serves is what is used: the arrow runs from the user.
            read.links.append((mb, ma, rel.name, ""))
        elif kind in ("flow", "triggering"):
            if ta == "systems" and tb == "systems" or kind == "flow":
                # The engine's own export says the protocol and the kind as
                # properties; the name then drops the protocol it carries
                # in brackets for the eye, so it reads back as the name.
                protocol = rel.properties.get("protocol", "")
                label = rel.name
                if protocol and label.endswith("(%s)" % protocol):
                    label = label[:-len("(%s)" % protocol)].strip()
                read.links.append((ma, mb, label, protocol))
                if rel.properties.get("connection kind"):
                    read.link_kinds[(ma, mb)] = rel.properties["connection kind"]
                if props.get("interface_id"):
                    # The flow's id and the record's own values for what the
                    # kind proposes: every flow read back as a new interface
                    # before, and the proposal over the record's values.
                    mark = {"interface_id": props["interface_id"]}
                    if props.get("connection_kind"):
                        mark["kind"] = props["connection_kind"]
                    for key in ("integration_style", "auth_method", "frequency", "direction", "patterns"):
                        if props.get(key):
                            mark[key] = props[key]
                    read.link_marks.setdefault((_ident(ma), _ident(mb), label), []).append(mark)
            else:
                skipped["triggering between %s" % ta.replace("_", " ")] = skipped.get(
                    "triggering between %s" % ta.replace("_", " "), 0) + 1
        elif kind == "realization":
            word = "supports" if ta == "processes" and tb == "capabilities" else rel.name
            read.links.append((ma, mb, word, ""))
        elif kind == "access":
            read.links.append((ma, mb, ACCESS_WORDS.get(rel.access.lower(), "reads and writes"), ""))
        elif kind in ("composition", "aggregation", "assignment") and ta == "systems" \
                and tb == "offered_interfaces":
            # The component the interface is part of: the system offering it.
            read.links.append((ma, mb, rel.name, ""))
            read.link_marks.setdefault((_ident(ma), _ident(mb), rel.name), []).append({"field": "system_id"})
        elif kind == "assignment":
            if ta == "tech_services" and tb in ("systems", "tech_services"):
                read.links.append((mb, ma, "runs on", ""))  # the node is where the component runs
            else:
                read.links.append((ma, mb, rel.name or "uses", ""))
        elif kind in ("composition", "aggregation"):
            if ta == "capabilities" and tb == "capabilities":
                read.links.append((mb, ma, "", ""))  # the child names its parent
            elif ta == "products" and tb == "systems":
                read.links.append((ma, mb, "includes", ""))
            elif ta == tb:
                skipped["%s of %s" % (kind, ta.replace("_", " "))] = skipped.get(
                    "%s of %s" % (kind, ta.replace("_", " ")), 0) + 1
            else:
                read.links.append((ma, mb, rel.name, ""))
        elif kind == "association":
            read.links.append((ma, mb, rel.name, ""))
        else:
            skipped[kind] = skipped.get(kind, 0) + 1

    if not read.order:
        raise ArchimateError("no element of the model has a counterpart here: %s" % (
            ", ".join("%d %s" % (n, t) for t, n in sorted(left_out.items())) or "the model is empty"))
    doc, notes = _document(read, name)
    notes[0] = notes[0].replace("from the Mermaid; the ids are made from the diagram's own",
                                "from the ArchiMate model; the ids are %s" % (
                                    "the model's own, which the engine wrote" if exported else "made from the names"))
    for kind, n in sorted(left_out.items()):
        notes.append("%d %s element(s) have no counterpart here; left out" % (n, kind))
    for what, n in sorted(skipped.items()):
        notes.append("%d relationship(s) %s; left out" % (n, what))

    # The model's own views, each written out over what it shows.
    whole = doc["views"][0]
    whole["view_id"] = "whole-model"
    whole["title"] = "%s, whole" % read.title
    ids = {mid: _entity_id(read.nodes[mid]["type"], mid) for mid in read.order}
    used: Dict[str, int] = {}
    for view in model.views:
        shown: Dict[str, List[str]] = {}
        seen = set()
        for element_id in view.elements:
            resolved = resolve(element_id)
            if resolved is None or resolved in seen:
                continue
            seen.add(resolved)
            mid = mids[resolved]
            shown.setdefault(read.nodes[mid]["type"], []).append(ids[mid])
        count = sum(len(v) for v in shown.values())
        if count < 2:
            notes.append("view %r shows %d thing(s) with a counterpart here; not written" % (view.name, count))
            continue
        view_id = _slug(view.name)
        n = used.get(view_id, 0) + 1
        used[view_id] = n
        if n > 1:
            view_id = "%s-%d" % (view_id, n)
        written = {
            "view_id": view_id, "title": view.name, "kind": "diagram", "layout": "LR",
            "description": "An ArchiMate view of the model: the %d element(s) it shows and the connections among "
                           "them." % count,
            "node_label": "name", "renderers": ["mermaid"],
            "scope": {"include": [{"type": t, "where": {"id_in": v}} for t, v in shown.items()]},
            "edges": list(whole["edges"]),
            "style": {"color_by": "type"},
            "limits": {"max_nodes": max(60, count)},
        }
        if any(mids.get(resolve(e) or "", "") and domain.get(resolve(e) or "") for e in view.elements):
            written["group_by"] = "company_domain"
        doc["views"].append(written)
    doc["views"] = doc["views"][1:] + doc["views"][:1]  # the model's own views first, the whole last
    notes.append("%d view(s) of the model written out as views of the sketch" % (len(doc["views"]) - 1))
    return doc, notes
