"""A draw.io diagram read as a sketch.

The whiteboard of most architecture work is draw.io (diagrams.net): a
`.drawio` file is XML, one `<diagram>` per page, each an `mxGraphModel`
of cells, a vertex per box with a `style` string that says what shape it
is, an edge per arrow with its `source` and `target`, a container
(`swimlane`, `group`) holding what sits inside it, and the page's content
often deflated and base64-encoded in the `<diagram>` text. This reads it
the way the other readers read what a team already has.

A box is a system unless its shape says otherwise: a cylinder a data
asset, an actor figure or an ellipse an actor, a hexagon a capability, a
process shape a process, a parallelogram or a cloud provider's icon a
technology service (the provider named), a document a policy, a card a
product, an octagon a control. A container is the domain of what sits inside it, by its label,
and not a record of its own. An arrow is the connection the method has
between the two things it joins, the label on it, its own or a label cell
riding it, the name or the protocol as the other readers take it; an
arrow with a loose end is said and left out. Labels lose their HTML. Every
page is a view of the sketch over what it draws, and a thing drawn on two
pages is one record.
"""

from __future__ import annotations

import base64
import html
import re
import urllib.parse
import zlib
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree

from .mermaid_import import ReadError, _document, _ident, _merge, _protocol_like, _Read
from .schema import ENTITY_TYPES

TAGS = re.compile(r"<[^>]+>")
BREAKS = re.compile(r"<br\s*/?>|</div>|</p>", re.I)
#: Style words that say what a box is, first match wins; a word not here
#: leaves the box a system.
SHAPE_TYPES: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"shape=(cylinder|cylinder3|datastore|mxgraph\.flowchart\.database|mxgraph\.flowchart\.stored_data)\b"), "data_assets"),
    (re.compile(r"shape=(umlActor|actor|mxgraph\.basic\.person|mxgraph\.c4\.person|mxgraph\.archimate3\.(actor|role))\b"), "actors"),
    (re.compile(r"shape=(hexagon|mxgraph\.basic\.hexagon|mxgraph\.archimate3\.capability)\b"), "capabilities"),
    (re.compile(r"shape=(process|mxgraph\.flowchart\.process|mxgraph\.archimate3\.(process|function|event))\b"), "processes"),
    (re.compile(r"shape=(parallelogram|mxgraph\.(aws[34]?|azure|gcp2?|cisco|kubernetes|office|veeam)\.|"
                r"mxgraph\.archimate3\.(node|device|network|tech)|mxgraph\.flowchart\.internal_storage)"), "tech_services"),
    (re.compile(r"shape=(document|mxgraph\.flowchart\.document|note)\b"), "policies"),
    (re.compile(r"shape=(card|mxgraph\.flowchart\.card|mxgraph\.archimate3\.product)\b"), "products"),
    (re.compile(r"shape=mxgraph\.archimate3\.(businessObject|dataObject|artifact)\b"), "data_assets"),
    (re.compile(r"shape=mxgraph\.archimate3\.application\b"), "systems"),
    (re.compile(r"shape=(octagon|mxgraph\.basic\.octagon2?)\b"), "controls"),
]
ELLIPSE = re.compile(r"(^|;)ellipse(;|$)")
CONTAINER = re.compile(r"(^|;)(swimlane|group|container=1)(;|=|$)")
PROVIDER = re.compile(r"shape=mxgraph\.(aws[34]?|azure|gcp2?)\.")
PROVIDERS = {"aws": "AWS", "aws3": "AWS", "aws4": "AWS", "azure": "Azure", "gcp": "GCP", "gcp2": "GCP"}
EDGE_LABEL = re.compile(r"(^|;)edgeLabel(;|$)")


class DrawioError(ReadError):
    pass


def _clean(label: str) -> str:
    """A cell's label without its HTML: breaks to spaces, tags gone,
    entities read."""
    text = BREAKS.sub(" ", str(label or ""))
    text = TAGS.sub("", text)
    return " ".join(html.unescape(text).split())


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "page"


def _inflate(text: str) -> str:
    """The page's XML from the deflated, base64 text draw.io stores it
    as; the text itself when it is already XML."""
    stripped = text.strip()
    if not stripped:
        return ""
    if stripped.startswith("<"):
        return stripped
    try:
        raw = zlib.decompress(base64.b64decode(stripped), -15)
    except (ValueError, zlib.error) as exc:
        raise DrawioError("a page is neither XML nor the compressed text draw.io writes: %s" % exc) from exc
    return urllib.parse.unquote(raw.decode("utf-8"))


class Cell:
    def __init__(self, cell_id: str, label: str, style: str, parent: str, source: str, target: str,
                 vertex: bool, edge: bool, kind: str = "", marks: Optional[Dict[str, str]] = None) -> None:
        self.id, self.label, self.style, self.parent = cell_id, label, style, parent
        self.source, self.target, self.vertex, self.edge = source, target, vertex, edge
        #: The connection kind the wrapping object names, as the export writes it on a line.
        self.kind = kind
        #: What the export wrote on the wrapping object as `aac_*` attributes:
        #: a box's type, id and fields, a line's interface id and its own
        #: values; empty on a page drawn by hand.
        self.marks: Dict[str, str] = dict(marks or {})


def pages(text: str) -> List[Tuple[str, List[Cell]]]:
    """Every page of the file: its name and its cells, in order."""
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as exc:
        raise DrawioError("not XML: %s" % exc) from exc
    tag = root.tag.rsplit("}", 1)[-1]
    if tag == "mxGraphModel":
        return [("Page-1", _cells(root))]
    if tag != "mxfile":
        raise DrawioError("not a draw.io file: the root is <%s>, not <mxfile>" % tag)
    out: List[Tuple[str, List[Cell]]] = []
    for i, diagram in enumerate(root.iter("diagram"), 1):
        name = diagram.attrib.get("name") or "Page-%d" % i
        model = diagram.find("mxGraphModel")
        if model is None:
            inner = _inflate(diagram.text or "")
            if not inner:
                continue
            try:
                model = ElementTree.fromstring(inner)
            except ElementTree.ParseError as exc:
                raise DrawioError("page %r: not XML once inflated: %s" % (name, exc)) from exc
        out.append((name, _cells(model)))
    if not out:
        raise DrawioError("no page in the file")
    return out


def _cells(model: ElementTree.Element) -> List[Cell]:
    cells: List[Cell] = []
    root = model.find("root")
    if root is None:
        return cells
    for node in root:
        tag = node.tag.rsplit("}", 1)[-1]
        kind = ""
        marks: Dict[str, str] = {}
        if tag == "mxCell":
            cell_node, label = node, node.attrib.get("value", "")
        else:
            # A `UserObject` or `object` wraps the cell and carries the label,
            # on a line the connection's kind, and what the export wrote as
            # `aac_*` attributes.
            cell_node = node.find("mxCell")
            if cell_node is None:
                continue
            label = node.attrib.get("label", node.attrib.get("value", ""))
            kind = node.attrib.get("kind", "")
            marks = {key[len("aac_"):]: value for key, value in node.attrib.items() if key.startswith("aac_")}
        attrs = cell_node.attrib
        cells.append(Cell(node.attrib.get("id") or attrs.get("id", ""), _clean(label), attrs.get("style", ""),
                          attrs.get("parent", ""), attrs.get("source", ""), attrs.get("target", ""),
                          attrs.get("vertex") == "1", attrs.get("edge") == "1", kind, marks))
    return cells


def _type_of(style: str) -> Tuple[str, str]:
    """The entity type a box's style says, and the provider when the
    style is a cloud provider's icon."""
    for pattern, type_name in SHAPE_TYPES:
        if pattern.search(style):
            provider = PROVIDER.search(style)
            return type_name, PROVIDERS.get(provider.group(1), "") if provider else ""
    if ELLIPSE.search(style):
        return "actors", ""
    return "systems", ""


def _read_page(name: str, cells: List[Cell], kinds: Dict[str, str]) -> _Read:
    read = _Read()
    read.kinds = dict(kinds)
    read.marked = False  # whether any cell carried the export's own marks
    read.title = name
    read.source = "a draw.io diagram: a box per thing, an arrow per connection"
    read.group_word = "a container per domain"
    # What the export wrote of the diagram's own (`aac_own`), a note or a
    # frame drawn on the canvas, is not a record: read as one, a note came
    # back a system and a frame a domain.
    own = [c for c in cells if c.marks.get("own")]
    if own:
        cells = [c for c in cells if not c.marks.get("own")]
        read.notes.append("page %r: %d of the diagram's own shapes, notes and lines, drawn on it and not records, "
                          "are not read" % (name, len(own)))
    by_id = {c.id: c for c in cells}
    containers = {c.id: c.label for c in cells if c.vertex and CONTAINER.search(c.style) and c.label}

    def domain_of(cell: Cell) -> str:
        parent = by_id.get(cell.parent)
        hops = 0
        while parent is not None and hops < 12:
            if parent.id in containers:
                return containers[parent.id]
            parent = by_id.get(parent.parent)
            hops += 1
        return ""

    mids: Dict[str, str] = {}
    taken: Dict[str, int] = {}
    for cell in cells:
        if not cell.vertex or cell.id in containers or EDGE_LABEL.search(cell.style):
            continue
        if not cell.label:
            continue  # a decorative box with no name is not a thing
        if cell.marks.get("id") and cell.marks.get("type") in ENTITY_TYPES:
            # The export's own box: the record's type, id and fields over
            # what the label, the shape and the container would say. The
            # estate's export read back was 168 new systems before, and a
            # data asset in the "Data Asset" band was of that domain.
            mid = cell.marks["id"]
            mids[cell.id] = mid
            entry = read.node(mid, cell.marks.get("company_domain", ""))
            entry["domain"] = cell.marks.get("company_domain", "")
            entry["type"] = cell.marks["type"]
            entry["label"] = cell.label
            if cell.marks.get("actor_kind"):
                entry["kind"] = cell.marks["actor_kind"]
            if entry["type"] == "systems" and cell.marks.get("hosting"):
                entry["external"] = cell.marks["hosting"]
            if entry["type"] == "actors" and cell.marks.get("internal"):
                entry["external"] = cell.marks["internal"]
            read.marked = True
            continue
        base = re.sub(r"[^A-Z0-9]+", "-", cell.label.upper()).strip("-") or "X"
        n = taken.get(base, 0) + 1
        taken[base] = n
        mid = base if n == 1 else "%s-%d" % (base, n)
        mids[cell.id] = mid
        type_name, provider = _type_of(cell.style)
        entry = read.node(mid, domain_of(cell))
        if mid not in read.kinds and type_name != "systems":
            entry["type"] = type_name
        elif mid in read.kinds:
            entry["type"] = read.kinds[mid]
        entry["label"] = cell.label
        if type_name == "actors":
            entry["kind"] = "Person"
        if provider:
            entry["description"] = "On %s." % provider
    if containers:
        read.any_group = True
    # The label riding an edge: a label cell whose parent is the edge.
    riding: Dict[str, str] = {}
    for cell in cells:
        if cell.vertex and EDGE_LABEL.search(cell.style) and cell.label and cell.parent in by_id:
            riding.setdefault(cell.parent, cell.label)
    for cell in cells:
        if not cell.edge:
            continue
        a, b = mids.get(cell.source), mids.get(cell.target)
        if a is None or b is None:
            what = "no source" if not cell.source else "no target" if not cell.target else "an end that is not a thing"
            read.notes.append("page %r: an arrow%s has %s; left out" % (name, " %r" % cell.label if cell.label else "", what))
            continue
        label = cell.label or riding.get(cell.id, "")
        # A code on the arrow (`gRPC`, `ISO 8583`) is the protocol; words are
        # what the connection is called, as the flowchart reader takes them.
        if label and _protocol_like(label):
            read.links.append((a, b, "", label))
            said = ""
        else:
            read.links.append((a, b, label, ""))
            said = label
        if cell.kind:
            read.link_kinds[(a, b)] = cell.kind
        if any(cell.marks.get(k) for k in ("interface_id", "relation", "derived", "field")):
            # The export's own line: the interface's id and its record's
            # values, the row it draws, the field it draws, or that it was
            # derived, as the C4-PlantUML export puts them under a Rel.
            read.link_marks.setdefault((_ident(a), _ident(b), said), []).append(dict(cell.marks))
            read.marked = True
    return read


def sketch_from_drawio(text: str, name: str = "Imported from draw.io") -> Tuple[dict, List[str]]:
    """The sketch a draw.io file reads as, and the notes."""
    all_pages = pages(text)
    merged: dict = {"model": {"name": name}}
    notes: List[str] = []
    # Two readings, as the Markdown reader does: the first learns what each
    # page makes of a name, so a cylinder on one page and a plain box with
    # the same name on another are one data asset.
    kinds: Dict[str, str] = {}
    for page_name, cells in all_pages:
        read = _read_page(page_name, cells, {})
        for mid, entry in read.nodes.items():
            if entry["type"] != "systems":
                kinds.setdefault(mid, entry["type"])
    written = 0
    marked = False
    for i, (page_name, cells) in enumerate(all_pages, 1):
        read = _read_page(page_name, cells, kinds)
        marked = marked or getattr(read, "marked", False)
        if not read.order:
            notes.append("page %r draws nothing with a name; left out" % page_name)
            continue
        doc, page_notes = _document(read, page_name)
        notes.extend(page_notes[1:])  # the summary is written once, below, for every page
        view = doc["views"][0]
        view["view_id"] = _slug(page_name) if len(all_pages) > 1 else "imported"
        view["title"] = page_name if len(all_pages) > 1 else name
        _merge(merged, doc, i, own=len(all_pages) > 1)
        written += 1
    if written == 0:
        raise DrawioError("no page draws a thing with a name: nothing to read as a sketch")
    if len(all_pages) > 1:
        merged["model"]["name"] = name
    counts = ", ".join("%d %s" % (len(merged[t]), t.replace("_", " ")) for t in ENTITY_TYPES if merged.get(t))
    notes.insert(0, "read %s across %d page(s) of the draw.io file; %s" % (
        counts, written, "the ids and types are the file's own where the export wrote them, made from the labels "
                         "otherwise" if marked else "the ids are made from the labels"))
    return merged, notes
