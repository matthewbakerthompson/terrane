"""A Visio drawing read as a sketch.

The diagram most architecture practices have on file is a Visio one: a
`.vsdx`, which is a zip of XML, a page per `visio/pages/pageN.xml`, a
shape per box with the master it was dragged from (`Rectangle`,
`Database`, `Actor`, `Dynamic connector`), its text, and its position and
size; a `Connect` per end of a connector, saying which shape it is glued
to. This reads it the way the other readers read what a team already has.

A shape is a system unless its master or its name says otherwise: a
database, cylinder or data store a data asset, an actor, person, user or
stick figure an actor, a hexagon a capability, a document a policy, a
server, cloud, network, router or switch a technology service; a
container, swimlane, group or cross-functional band is the domain of the
shapes inside it, by its text and their position, and not a record of its
own; a shape with no text is decoration. A connector is the connection
the method has between the two shapes it is glued to, its text the name
or the protocol; one glued at one end only is said and left out. Every
page is a view of the sketch over what it draws, and a thing drawn on two
pages is one record. Text loses its formatting runs.
"""

from __future__ import annotations

import io
import re
import zipfile
from typing import Dict, List, Tuple
from xml.etree import ElementTree

from .mermaid_import import ReadError, _document, _merge, _protocol_like, _Read
from .schema import ENTITY_TYPES

NS = "{http://schemas.microsoft.com/office/visio/2012/main}"
REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
#: What a master's or a shape's name says a shape is, first match wins.
TYPE_WORDS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\b(database|cylinder|data ?store|stored data|direct data|data ?set|disk)\b", re.I), "data_assets"),
    (re.compile(r"\b(actor|person|user|stick figure|people|customer|role)\b", re.I), "actors"),
    (re.compile(r"\bhexagon\b", re.I), "capabilities"),
    (re.compile(r"\b(business process|procedure|workflow)\b", re.I), "processes"),
    (re.compile(r"\b(document|policy)\b", re.I), "policies"),
    (re.compile(r"\b(server|cloud|network|router|switch|firewall|load balancer|cluster|infrastructure)\b", re.I),
     "tech_services"),
]
CONTAINER = re.compile(r"\b(container|swimlane|group|cross[- ]functional|band|lane|boundary|zone)\b", re.I)
CONNECTOR = re.compile(r"\b(connector|line|arrow)\b", re.I)


class VisioError(ReadError):
    pass


class Shape:
    def __init__(self, shape_id: str, name: str, master: str, text: str, x: float, y: float, w: float, h: float,
                 parent: str) -> None:
        self.id, self.name, self.master, self.text = shape_id, name, master, text
        self.x, self.y, self.w, self.h, self.parent = x, y, w, h, parent

    def holds(self, other: "Shape") -> bool:
        return (self.w > 0 and self.h > 0 and abs(other.x - self.x) <= self.w / 2
                and abs(other.y - self.y) <= self.h / 2 and (other.w * other.h) < (self.w * self.h))


def _text(shape: ElementTree.Element) -> str:
    node = shape.find(NS + "Text")
    return " ".join("".join(node.itertext()).split()) if node is not None else ""


def _cell(shape: ElementTree.Element, name: str) -> float:
    for cell in shape.findall(NS + "Cell"):
        if cell.get("N") == name:
            try:
                return float(cell.get("V") or 0)
            except ValueError:
                return 0.0
    return 0.0


def _shapes(parent: ElementTree.Element, masters: Dict[str, str], out: List[Shape], above: str = "",
            origin: Tuple[float, float] = (0.0, 0.0)) -> None:
    shapes = parent.find(NS + "Shapes")
    if shapes is None:
        return
    for node in shapes.findall(NS + "Shape"):
        shape_id = node.get("ID") or ""
        master = masters.get(node.get("Master") or "", "")
        x, y = origin[0] + _cell(node, "PinX"), origin[1] + _cell(node, "PinY")
        w, h = _cell(node, "Width"), _cell(node, "Height")
        shape = Shape(shape_id, node.get("NameU") or node.get("Name") or "", master, _text(node), x, y, w, h, above)
        out.append(shape)
        # A group's children sit in its own coordinates, from its corner.
        _shapes(node, masters, out, shape_id, (x - w / 2, y - h / 2))


def pages(data: bytes) -> List[Tuple[str, List[Shape], List[Tuple[str, str, str]]]]:
    """Every page of the file: its name, its shapes, and its connections
    as (connector shape, from shape, to shape) read off the `Connect`
    elements, begin end to end end."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise VisioError("not a .vsdx: %s" % exc) from exc
    names = set(archive.namelist())
    if "visio/pages/pages.xml" not in names:
        raise VisioError("not a Visio drawing: no visio/pages/pages.xml in the file")
    masters: Dict[str, str] = {}
    if "visio/masters/masters.xml" in names:
        for master in ElementTree.fromstring(archive.read("visio/masters/masters.xml")).iter(NS + "Master"):
            masters[master.get("ID") or ""] = master.get("NameU") or master.get("Name") or ""
    rels: Dict[str, str] = {}
    if "visio/pages/_rels/pages.xml.rels" in names:
        for rel in ElementTree.fromstring(archive.read("visio/pages/_rels/pages.xml.rels")).iter(REL + "Relationship"):
            rels[rel.get("Id") or ""] = rel.get("Target") or ""
    out = []
    index = ElementTree.fromstring(archive.read("visio/pages/pages.xml"))
    for i, page in enumerate(index.iter(NS + "Page"), 1):
        name = page.get("Name") or page.get("NameU") or "Page-%d" % i
        rel = page.find(NS + "Rel")
        rel_id = rel.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id") if rel is not None else ""
        target = rels.get(rel_id or "", "page%d.xml" % i)
        member = "visio/pages/" + target.split("/")[-1]
        if member not in names:
            continue
        root = ElementTree.fromstring(archive.read(member))
        shapes: List[Shape] = []
        _shapes(root, masters, shapes)
        ends: Dict[str, Dict[str, str]] = {}
        connects = root.find(NS + "Connects")
        for connect in connects.findall(NS + "Connect") if connects is not None else []:
            which = "from" if (connect.get("FromCell") or "").startswith("Begin") else "to"
            ends.setdefault(connect.get("FromSheet") or "", {})[which] = connect.get("ToSheet") or ""
        links = [(c, e.get("from", ""), e.get("to", "")) for c, e in ends.items()]
        out.append((name, shapes, links))
    if not out:
        raise VisioError("no page in the drawing")
    return out


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "page"


def _kind(shape: Shape) -> str:
    """What a shape is, by the master it was dragged from first and its own
    name second: the text a person typed into a box is never read for its
    type, since "Authorization switch" is not a network switch and "the PCI
    zone" is not a zone."""
    for words in (shape.master, shape.name):
        if not words:
            continue
        if CONTAINER.search(words):
            return "container"
        if CONNECTOR.search(words):
            return "connector"
        for pattern, type_name in TYPE_WORDS:
            if pattern.search(words):
                return type_name
        if shape.master:
            # A shape with a master is what the master says; its own name
            # (`Process.12`) only repeats the master with a number.
            break
    return "systems"


def _read_page(name: str, shapes: List[Shape], links: List[Tuple[str, str, str]], kinds: Dict[str, str]) -> _Read:
    read = _Read()
    read.kinds = dict(kinds)
    read.title = name
    read.source = "a Visio drawing: a shape per thing, a connector per connection"
    read.group_word = "a container per domain"
    by_id = {s.id: s for s in shapes}
    kind_of = {s.id: _kind(s) for s in shapes}
    containers = [s for s in shapes if kind_of[s.id] == "container" and s.text]
    connector_ids = {c for c, _, _ in links} | {s.id for s in shapes if kind_of[s.id] == "connector"}

    def domain_of(shape: Shape) -> str:
        parent = by_id.get(shape.parent)
        if parent is not None and parent.text and kind_of[parent.id] in ("container", "systems"):
            return parent.text
        inside = [c for c in containers if c.id != shape.id and c.holds(shape)]
        if inside:
            return min(inside, key=lambda c: c.w * c.h).text
        return ""

    mids: Dict[str, str] = {}
    taken: Dict[str, int] = {}
    for shape in shapes:
        if shape.id in connector_ids or kind_of[shape.id] == "container" or not shape.text:
            continue
        # A group with children is a boundary for them, not a box of its own.
        if any(o.parent == shape.id for o in shapes):
            continue
        base = re.sub(r"[^A-Z0-9]+", "-", shape.text.upper()).strip("-") or "X"
        n = taken.get(base, 0) + 1
        taken[base] = n
        mid = base if n == 1 else "%s-%d" % (base, n)
        mids[shape.id] = mid
        entry = read.node(mid, domain_of(shape))
        type_name = kind_of[shape.id]
        if mid in read.kinds:
            entry["type"] = read.kinds[mid]
        elif type_name != "systems":
            entry["type"] = type_name
        entry["label"] = shape.text
        if entry["type"] == "actors":
            entry["kind"] = "Person"
    if containers or any(s.parent for s in shapes):
        read.any_group = True
    for connector, source, target in links:
        a, b = mids.get(source), mids.get(target)
        label = by_id[connector].text if connector in by_id else ""
        if a is None or b is None:
            read.notes.append("page %r: a connector%s is glued at one end only; left out"
                              % (name, " %r" % label if label else ""))
            continue
        if label and _protocol_like(label):
            read.links.append((a, b, "", label))
        else:
            read.links.append((a, b, label, ""))
    return read


def sketch_from_visio(data: bytes, name: str = "Imported from Visio") -> Tuple[dict, List[str]]:
    """The sketch a Visio drawing reads as, and the notes."""
    all_pages = pages(data)
    merged: dict = {"model": {"name": name}}
    notes: List[str] = []
    kinds: Dict[str, str] = {}
    for page_name, shapes, links in all_pages:
        read = _read_page(page_name, shapes, links, {})
        for mid, entry in read.nodes.items():
            if entry["type"] != "systems":
                kinds.setdefault(mid, entry["type"])
    written = 0
    for i, (page_name, shapes, links) in enumerate(all_pages, 1):
        read = _read_page(page_name, shapes, links, kinds)
        if not read.order:
            notes.append("page %r draws nothing with a name; left out" % page_name)
            continue
        doc, page_notes = _document(read, page_name)
        notes.extend(page_notes[1:])
        view = doc["views"][0]
        view["view_id"] = _slug(page_name) if len(all_pages) > 1 else "imported"
        view["title"] = page_name if len(all_pages) > 1 else name
        _merge(merged, doc, i, own=len(all_pages) > 1)
        written += 1
    if written == 0:
        raise VisioError("no page draws a thing with a name: nothing to read as a sketch")
    if len(all_pages) > 1:
        merged["model"]["name"] = name
    counts = ", ".join("%d %s" % (len(merged[t]), t.replace("_", " ")) for t in ENTITY_TYPES if merged.get(t))
    notes.insert(0, "read %s across %d page(s) of the Visio drawing; the ids are made from the shapes' text" % (
        counts, written))
    return merged, notes


def sketch_from_visio_file(path) -> Tuple[dict, List[str]]:
    from pathlib import Path

    path = Path(path)
    return sketch_from_visio(path.read_bytes(), name=path.stem.replace("-", " ").replace("_", " "))
