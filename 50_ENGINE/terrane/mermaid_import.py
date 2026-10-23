"""A Mermaid diagram read as a sketch: the on-ramp for the diagrams people
already have.

Most architecture diagrams in a repository today are Mermaid: flowcharts, a
box per thing, an arrow per connection, a subgraph per area; and, where a
team took up C4, context and container diagrams, a person, a system or a
container per statement, a relation per `Rel`, a boundary per block. Each
is a model with the vocabulary left off, and this reads both as one. A
node becomes a thing of the kind its shape or its statement says -- a
cylinder or a `SystemDb` a data asset, a circle or a `Person` an actor, a
hexagon a capability, anything else a system -- an arrow or a `Rel`
becomes the relation two such things have here -- an interface between
systems, a read or a write of a data asset, an actor using a system -- and
a subgraph or a boundary becomes the domain the things in it belong to.
What comes out is a sketch file (`terrane.quick`) a person can read, correct
and keep, and the drawing is the same code's; nothing is drawn from the
Mermaid directly, since the point is to arrive at a model.

The grammar read is the part of each diagram that drawings of systems
use. Flowcharts: `flowchart` or `graph` with a direction, nodes with any
of the common bracket shapes, links with or without a label in either
spelling, chains, `&` groups, nested subgraphs, comments; styling and
interaction statements are skipped. C4: `C4Context`, `C4Container`,
`C4Component`, `C4Dynamic` and `C4Deployment`; `Person`, `System`,
`Container`, `Component` and their `Db`, `Queue` and `_Ext` forms with a
label, a technology and a description; `Rel` in every direction, `BiRel`
and `Rel_Back`; the boundaries; `title`; the `Update...` styling
statements are skipped. Sequence diagrams: participants and actors,
messages with every arrowhead, the dotted reply, notes, `title`; the
blocks (`loop`, `alt`, `par`) are read through and their keywords skipped,
as are activations and `autonumber`. A sequence diagram is a flow, not a
set of boxes, and comes out as one: the systems, the interfaces each
message crosses, and the steps in order. What cannot be read is reported
with its line, not guessed at.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from .draw.shapes import edge_word
from .schema import ENTITY_TYPES, RELATION_TYPES

HEADER = re.compile(r"^\s*(flowchart|graph)\s+(LR|RL|TB|TD|BT)\s*$", re.I)
C4_HEADER = re.compile(r"^\s*(C4Context|C4Container|C4Component|C4Dynamic|C4Deployment)\s*$", re.I)
SEQ_HEADER = re.compile(r"^\s*sequenceDiagram\s*$", re.I)
#: A sequence diagram's participant, and a message between two.
SEQ_PARTICIPANT = re.compile(r"^(?P<kind>participant|actor)\s+(?P<id>[A-Za-z0-9_.-]+)(?:\s+as\s+(?P<label>.+))?$", re.I)
#: The sender is matched shortest-first, since a greedy id would swallow
#: the first dash of `-->>` and leave `fraud-` as a participant.
SEQ_MESSAGE = re.compile(
    r"^(?P<a>[A-Za-z0-9_.-]+?)\s*(?P<arrow>-->>|->>|--\)|-\)|-->|->|--x|-x)\s*[+-]?\s*(?P<b>[A-Za-z0-9_.-]+)\s*:\s*(?P<text>.*)$")
SEQ_NOTE = re.compile(r"^Note\s+(?:over|left of|right of)\s+(?P<who>[A-Za-z0-9_.,\s-]+?)\s*:\s*(?P<text>.*)$", re.I)
SEQ_SKIP = re.compile(r"^(autonumber|loop|alt|else|opt|par|and|critical|option|break|rect|end|activate|deactivate|box|"
                      r"link|links|create|destroy|properties|details)\b", re.I)
LATENCY_WORDS = re.compile(r"\b(ms|millisecond|second|minute|hour|day|latency|under|within|end to end)\b", re.I)
#: A Mermaid block inside Markdown, and the headings above it.
FENCE = re.compile(r"^[ \t]*```+[ \t]*\{?mermaid\}?[^\n]*\n(.*?)^[ \t]*```+", re.M | re.S)
HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$", re.M)
SUBGRAPH = re.compile(r"^\s*subgraph\s+(.+?)\s*$", re.I)
SKIP = re.compile(r"^\s*(classDef|style|linkStyle|click|direction)\b", re.I)
#: `class A,B,C name`: the one styling statement that says what a thing is,
#: when the class is named after a type, as the engine's own are.
CLASS = re.compile(r"^\s*class\s+(?P<ids>[A-Za-z0-9_.:,\s-]+?)\s+(?P<name>[A-Za-z0-9_-]+)\s*$", re.I)
#: What a class name says a node is, by the words in it.
CLASS_WORDS = {
    "system": "systems", "actor": "actors", "person": "actors", "people": "actors", "user": "actors",
    "data": "data_assets", "database": "data_assets", "db": "data_assets", "datastore": "data_assets",
    "store": "data_assets", "capability": "capabilities", "process": "processes", "control": "controls",
    "policy": "policies", "framework": "frameworks", "tech": "tech_services", "technology": "tech_services",
    "platform": "tech_services", "product": "products", "org": "org_units", "team": "org_units",
    "flow": "flows", "package": "work_packages", "stream": "value_streams", "roadmap": "roadmaps",
    "change": "architecture_change_requests",
}
#: A node: its id, then any of the bracket shapes with its text. A quoted
#: text is taken whole first, since it may hold brackets of its own
#: (`["Rewards API<br/>[AKS]"]`), then the shapes as the lazy match.
_SHAPES = (("[[", "]]"), ("[(", ")]"), ("((", "))"), ("([", "])"), ("{{", "}}"), ("[/", "/]"), ("[\\", "\\]"),
           ("[/", "\\]"), ("[\\", "/]"), (">", "]"), ("[", "]"), ("(", ")"), ("{", "}"))
_QUOTED = r'"(?:[^"\\]|\\.)*"'
NODE = re.compile(
    r"\s*(?P<id>[A-Za-z0-9_.:-]+)\s*(?P<shape>"
    + "|".join(re.escape(o) + r"\s*" + _QUOTED + r"\s*" + re.escape(c) for o, c in _SHAPES)
    + "|" + "|".join(re.escape(o) + r".*?" + re.escape(c) for o, c in _SHAPES)
    + r")?")
#: A link, with the label in the bar spelling; the inline spelling is
#: rewritten to this one first.
LINK = re.compile(r"\s*(?P<arrow>(?:<)?(?:-\.+-|==+|--+)(?:>|x|o)?)\s*(?:\|(?P<label>[^|]*)\|)?\s*")
INLINE_LABEL = re.compile(r"(--|==|-\.)\s*([^-=.|>][^|>]*?)\s*(--+>|==+>|\.-+>|--+|==+|\.-+)")

#: What a bracket shape says a node is.
SHAPE_TYPES = (
    ("[(", "data_assets"),
    ("((", "actors"),
    ("{{", "capabilities"),
)
#: The prefix each type's ids carry in the method's own estate, so an id
#: that arrives with it (`SYS_CORE_LEDGER`, the engine's own Mermaid) is
#: not given it twice, and one that does not (`web`) is.
TYPE_PREFIX = {
    "systems": "SYS", "interfaces": "INT", "data_assets": "DA", "tech_services": "TS", "capabilities": "CAP",
    "frameworks": "FW", "value_streams": "VS", "value_stream_stages": "VS", "org_units": "ORG", "policies": "POL",
    "controls": "CTL", "actors": "ACT", "flows": "FLOW", "processes": "P", "products": "PRD", "roadmaps": "RDM",
    "work_packages": "WP", "architecture_change_requests": "ACR", "offered_interfaces": "OI",
}
#: The words on a line between a system and an interface it offers. Any
#: other line between the two is a connection through the interface.
OFFER_WORDS = {"offers", "offered by", "exposes", "exposed by", "provides", "provided by", "publishes"}

#: A C4 statement: the element or relation, and its arguments.
C4_STATEMENT = re.compile(r"^\s*(?P<kind>[A-Za-z_]+)\s*\((?P<args>.*)\)\s*(?P<open>\{)?\s*$")
C4_ELEMENTS = {
    "Person": ("actors", "Yes"), "Person_Ext": ("actors", "No"),
    "System": ("systems", ""), "System_Ext": ("systems", "External"),
    "SystemDb": ("data_assets", ""), "SystemDb_Ext": ("data_assets", "External"),
    "SystemQueue": ("systems", ""), "SystemQueue_Ext": ("systems", "External"),
    "Container": ("systems", ""), "Container_Ext": ("systems", "External"),
    "ContainerDb": ("data_assets", ""), "ContainerDb_Ext": ("data_assets", "External"),
    "ContainerQueue": ("systems", ""), "ContainerQueue_Ext": ("systems", "External"),
    "Component": ("systems", ""), "Component_Ext": ("systems", "External"),
    "ComponentDb": ("data_assets", ""), "ComponentDb_Ext": ("data_assets", "External"),
    "ComponentQueue": ("systems", ""), "ComponentQueue_Ext": ("systems", "External"),
    "Deployment_Node": ("systems", ""), "Node": ("systems", ""), "Node_L": ("systems", ""), "Node_R": ("systems", ""),
}
C4_BOUNDARIES = {"Enterprise_Boundary", "System_Boundary", "Container_Boundary", "Boundary"}
C4_RELATIONS = re.compile(r"^(Bi)?Rel(_Back|_Neighbor|_U|_D|_L|_R|_Up|_Down|_Left|_Right|_Back_Neighbor)?$")
C4_SKIP = re.compile(r"^Update[A-Za-z]*$")


class ReadError(ValueError):
    """A diagram that cannot be read as a sketch, with the line that says so."""


class MermaidError(ReadError):
    pass


def _unquote(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1]
    return text.replace("<br/>", " ").replace("<br>", " ").replace("#quot;", '"').strip()


def _ident(mermaid_id: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "-", mermaid_id.upper()).strip("-") or "X"


def _minted(a: str, b: str, n: int = 1) -> str:
    """The id a connection gets when nothing named it: the two ends, each
    without its system prefix where it carries the method's own id, since
    the estate names its interfaces `INT-AUTH-LEDGER` and a reviewer's line
    drawn in an export read back as `INT-SYS-CRM-SYS-STATEMENTS`. A
    sketch's own ids, `api` and `fraud`, are kept whole; a second line
    between the same two ends gets a number."""
    def short(end: str) -> str:
        ident = _ident(end)
        return ident[4:] if ident.startswith("SYS-") and len(ident) > 4 else ident

    return "INT-%s-%s%s" % (short(a), short(b), "" if n == 1 else "-%d" % n)


def _entity_id(type_name: str, mermaid_id: str) -> str:
    """The id a thing gets in the sketch: the method's prefix for its type
    and the Mermaid id, unless the Mermaid id already carries the prefix."""
    ident = _ident(mermaid_id)
    prefix = TYPE_PREFIX.get(type_name) or type_name[:3].upper()
    return ident if ident.startswith(prefix + "-") else "%s-%s" % (prefix, ident)


def _type_from_class(name: str) -> Optional[str]:
    """The entity type a class name says, or None. The engine names its
    classes `s_<type>__<style>`; a hand-written diagram says `database`,
    `person` or `system`."""
    low = name.lower()
    if low.startswith("s_") and "__" in low:
        inner = low[2:].split("__", 1)[0]
        if inner in ENTITY_TYPES:
            return inner
    for token in re.split(r"[^a-z]+", low):
        if token in ENTITY_TYPES:
            return token
        if token in CLASS_WORDS:
            return CLASS_WORDS[token]
    return None


def _statements(text: str) -> List[Tuple[int, str]]:
    out = []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split("%%", 1)[0].rstrip()
        if not line.strip():
            continue
        # A semicolon ends a statement, except inside a quoted label, where
        # it is punctuation (`"Business Support; Sales and Service"`).
        pieces, buf, quoted = [], [], False
        for ch in line:
            if ch == '"':
                quoted = not quoted
            if ch == ";" and not quoted:
                pieces.append("".join(buf))
                buf = []
            else:
                buf.append(ch)
        pieces.append("".join(buf))
        for piece in pieces:
            if piece.strip():
                out.append((number, piece.strip()))
    return out


def _split_args(text: str) -> List[str]:
    """A C4 argument list, split on the commas outside quotes; the named
    `$tags=` and `$link=` arguments are left out."""
    out: List[str] = []
    current: List[str] = []
    quote = ""
    for ch in text:
        if quote:
            current.append(ch)
            if ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
            current.append(ch)
        elif ch == ",":
            out.append("".join(current))
            current = []
        else:
            current.append(ch)
    out.append("".join(current))
    return [_unquote(a) for a in out if not a.strip().startswith("$")]


class _Read:
    """What a diagram read as: the nodes by Mermaid id, in order, the
    links, the direction, whether anything was grouped, and the notes."""

    def __init__(self) -> None:
        self.nodes: Dict[str, dict] = {}
        self.order: List[str] = []
        self.links: List[Tuple[str, str, str, str]] = []  # from, to, label, technology
        #: What another diagram in the same file already said a thing is,
        #: by its id without prefix: a cylinder in the flowchart is a data
        #: asset when the sequence diagram names it as a participant.
        self.kinds: Dict[str, str] = {}
        #: The connection kind a relation was tagged with, by its two ends
        #: as written: what the C4-PlantUML export puts on a `Rel`.
        self.link_kinds: Dict[Tuple[str, str], str] = {}
        #: What the C4-PlantUML export wrote under a `Rel`, by its two ends
        #: and its label as written: the interface's id, so the estate's own
        #: page comes back as its own interfaces and not as sixty-four new
        #: ones; the kind it was of; and the record's own values for what
        #: the kind proposes, so the proposal is not written over them; or the row a
        #: line draws with its qualifier, the field it draws, or that it was
        #: derived. A list per key, taken in order, since two lines of one
        #: pair on a page (a Read row and the source of truth) share a key.
        self.link_marks: Dict[Tuple[str, str, str], List[Dict[str, str]]] = {}
        #: The pairs a flowchart joins with an open line (`---`), no head:
        #: no traffic, so between a system and an interface, the system
        #: offering it, as the engine's own Mermaid draws it.
        self.open_links: set = set()
        self.notes: List[str] = []
        self.direction = "LR"
        self.any_group = False
        self.title = ""
        self.source = "a Mermaid flowchart: a box per thing, an arrow per connection"
        #: What grouped the things, said in the view's description when
        #: anything was grouped; the flowchart reader says it in `source`.
        self.group_word = ""

    def node(self, mid: str, domain: str) -> dict:
        entry = self.nodes.get(mid)
        if entry is None:
            entry = {"type": self.kinds.get(_ident(mid), "systems"), "label": mid, "domain": domain,
                     "description": "", "external": ""}
            self.nodes[mid] = entry
            self.order.append(mid)
        if not entry["domain"] and domain:
            entry["domain"] = domain
        return entry


def _read_flowchart(statements: List[Tuple[int, str]], header: "re.Match[str]",
                    kinds: Optional[Dict[str, str]] = None) -> _Read:
    read = _Read()
    read.kinds = dict(kinds or {})
    read.direction = "TB" if header.group(2).upper() in ("TB", "TD", "BT") else "LR"
    subgraphs: List[str] = []
    classed: Dict[str, str] = {}

    def node(mid: str, shape: Optional[str]) -> str:
        entry = read.node(mid, subgraphs[-1] if subgraphs else "")
        if shape:
            for opening, type_name in SHAPE_TYPES:
                if shape.startswith(opening):
                    entry["type"] = type_name
                    break
            inner = shape
            for opening, closing in _SHAPES:
                if inner.startswith(opening) and inner.endswith(closing):
                    inner = inner[len(opening):-len(closing)]
                    break
            if inner.startswith(">") and inner.endswith("]"):
                inner = inner[1:-1]
            # The engine writes the technology line under the name in
            # brackets; a name is the name.
            label = re.sub(r"\s*\[[^\]]*\]\s*$", "", _unquote(inner)).strip()
            if label:
                entry["label"] = label
        return mid

    for number, statement in statements[1:]:
        if SKIP.match(statement):
            continue
        classed_match = CLASS.match(statement)
        if classed_match:
            type_name = _type_from_class(classed_match.group("name"))
            if type_name:
                for mid in re.split(r"[,\s]+", classed_match.group("ids").strip()):
                    if mid:
                        classed[mid] = type_name
            continue
        sub = SUBGRAPH.match(statement)
        if sub:
            title = sub.group(1)
            bracket = re.match(r"^([A-Za-z0-9_.:-]+)\s*\[(.*)\]$", title)
            subgraphs.append(_unquote(bracket.group(2)) if bracket else _unquote(title))
            read.any_group = True
            continue
        if statement.lower() == "end":
            if subgraphs:
                subgraphs.pop()
            continue
        line = INLINE_LABEL.sub(lambda m: "%s%s|%s|" % (m.group(1), m.group(3), m.group(2).strip()), statement)
        pos = 0
        groups: List[List[str]] = []
        pending: List[Tuple[str, str]] = []
        while pos < len(line):
            group: List[str] = []
            while True:
                m = NODE.match(line, pos)
                if not m or not m.group("id"):
                    break
                group.append(node(m.group("id"), m.group("shape")))
                pos = m.end()
                amp = re.match(r"\s*&\s*", line[pos:])
                if not amp:
                    break
                pos += amp.end()
            if not group:
                read.notes.append("line %d: could not read %r; left out" % (number, line[pos:].strip()))
                break
            groups.append(group)
            if pos >= len(line):
                break
            link = LINK.match(line, pos)
            if not link or not link.group("arrow"):
                read.notes.append("line %d: could not read %r; left out" % (number, line[pos:].strip()))
                break
            pending.append((link.group("arrow"), _unquote(link.group("label") or "")))
            pos = link.end()
        for i, (arrow, label) in enumerate(pending):
            if i + 1 >= len(groups):
                break
            # A code on the arrow (`HTTPS`, `gRPC`, `ISO 8583`) is the
            # protocol; words (`Posts the authorization`) are what the
            # connection is called, as the C4, sequence, draw.io and Visio
            # readers have it. The first flowchart reader filed both as
            # the protocol, and a workbook of such a drawing said so.
            name, technology = ("", label) if _protocol_like(label) else (label, "")
            for a in groups[i]:
                for b in groups[i + 1]:
                    if arrow.startswith("<"):
                        read.links.append((b, a, name, technology))
                    read.links.append((a, b, name, technology))
                    if not arrow.startswith("<") and arrow[-1:] in ("-", "="):
                        read.open_links.add((a, b))
    for mid, type_name in classed.items():
        if mid in read.nodes:
            read.nodes[mid]["type"] = type_name
    if read.any_group:
        read.source += ", a subgraph per domain"
    return read


def _read_c4(statements: List[Tuple[int, str]], header: "re.Match[str]",
             kinds: Optional[Dict[str, str]] = None) -> _Read:
    read = _Read()
    read.kinds = dict(kinds or {})
    read.direction = "TB"
    kind_name = header.group(1)
    read.source = "a Mermaid %s diagram: an element per statement, a Rel per connection" % kind_name
    read.group_word = "a boundary per domain"
    boundaries: List[str] = []
    for number, statement in statements[1:]:
        if statement == "}":
            if boundaries:
                boundaries.pop()
            continue
        if statement == "{":
            continue
        if statement.lower().startswith("title "):
            read.title = statement[len("title "):].strip()
            continue
        m = C4_STATEMENT.match(statement)
        if not m:
            read.notes.append("line %d: could not read %r; left out" % (number, statement))
            continue
        kind, args = m.group("kind"), _split_args(m.group("args"))
        if C4_SKIP.match(kind):
            continue
        if kind in C4_BOUNDARIES:
            boundaries.append(args[1] if len(args) > 1 and args[1] else (args[0] if args else ""))
            read.any_group = True
            continue
        if kind in C4_ELEMENTS:
            if not args:
                read.notes.append("line %d: %s with no alias; left out" % (number, kind))
                continue
            type_name, mark = C4_ELEMENTS[kind]
            entry = read.node(args[0], boundaries[-1] if boundaries else "")
            # What another diagram, or a tag on the macro, already said a
            # thing is outranks the macro's own word: C4 has no capability,
            # and a `System` tagged `capabilities` is one.
            entry["type"] = read.kinds.get(_ident(args[0]), type_name)
            entry["label"] = args[1] if len(args) > 1 and args[1] else args[0]
            # Person and System take (alias, label, descr); a Container, a
            # Component and a node take a technology before the description.
            if kind.startswith(("Person", "System")):
                technology, description = "", args[2] if len(args) > 2 else ""
                if kind.startswith("Person"):
                    entry["kind"] = "Person"
            else:
                technology = args[2] if len(args) > 2 else ""
                description = args[3] if len(args) > 3 else ""
            if technology and "Queue" in kind:
                description = (description + " A queue." if description else "A queue.")
            if technology:
                description = (description + " " if description else "") + "Built with %s." % technology
            entry["description"] = description.strip()
            entry["external"] = mark
            if m.group("open"):
                # A deployment node holds what runs on it.
                boundaries.append(entry["label"])
                read.any_group = True
            continue
        relation = C4_RELATIONS.match(kind)
        if relation:
            if len(args) < 2:
                read.notes.append("line %d: %s with fewer than two ends; left out" % (number, kind))
                continue
            a, b = args[0], args[1]
            label = args[2] if len(args) > 2 else ""
            technology = args[3] if len(args) > 3 else ""
            for end in (a, b):
                if end not in read.nodes:
                    read.notes.append("line %d: %s names %r, which no statement declared; read as a system" % (
                        number, kind, end))
                    read.node(end, boundaries[-1] if boundaries else "")
            if relation.group(2) and relation.group(2).startswith("_Back"):
                # Rel_Back(a, b) draws the arrow back to a: b is the one acting.
                a, b = b, a
            read.links.append((a, b, label, technology))
            if relation.group(1):
                read.links.append((b, a, label, technology))
            continue
        read.notes.append("line %d: %s is not a statement this reads; left out" % (number, kind))
    return read


def _protocol_like(text: str) -> bool:
    """Whether a message's text reads as a protocol rather than as what
    the call does: one token (`HTTPS`, `gRPC`, `Kafka`), or capitals and
    digits (`ISO 8583`, `JSON/HTTPS`)."""
    text = text.strip()
    if not text or len(text) > 24:
        return False
    if " " not in text:
        return True
    return bool(re.match(r"^[A-Z0-9][A-Z0-9 /.+-]*$", text))


def _sequence_doc(statements: List[Tuple[int, str]], name: str,
                  kinds: Optional[Dict[str, str]] = None) -> Tuple[dict, List[str]]:
    """A Mermaid sequence diagram as a sketch: the participants as systems,
    an `actor` as an actor, each message between two systems as an
    interface and a step of one flow in the diagram's order, a message from
    an actor as the actor using the system and, first of all, the flow's
    trigger; a dotted message straight back is the reply of the step before
    it, which makes that step request-response, and an open arrow (`-)`) an
    event. A note over a participant that speaks of time is the flow's
    target latency; any other note goes into its description. The engine
    writes its flows as sequence diagrams of exactly this shape, so what it
    writes it reads."""
    notes: List[str] = []
    nodes: Dict[str, dict] = {}
    order: List[str] = []
    title = ""
    steps: List[dict] = []          # {a, b, text, style}
    uses: List[Tuple[str, str, str]] = []
    touches: List[Tuple[str, str, str]] = []  # system, data asset, operation
    said: List[str] = []
    latency = ""
    known = dict(kinds or {})

    def node(mid: str, kind: str = "systems", label: str = "") -> dict:
        entry = nodes.get(mid)
        if entry is None:
            # A participant another diagram in the file drew as a cylinder
            # is the data asset it is there, not a system here.
            entry = {"type": known.get(_ident(mid), kind) if kind == "systems" else kind, "label": label or mid}
            nodes[mid] = entry
            order.append(mid)
        elif label:
            entry["label"] = label
        if kind == "actors":
            entry["type"] = kind
        return entry

    for number, statement in statements[1:]:
        if statement.lower().startswith("title "):
            title = statement[len("title "):].strip()
            continue
        if statement.lower().startswith("title:"):
            title = statement[len("title:"):].strip()
            continue
        if SEQ_SKIP.match(statement):
            continue
        who = SEQ_PARTICIPANT.match(statement)
        if who:
            node(who.group("id"), "actors" if who.group("kind").lower() == "actor" else "systems",
                 _unquote(who.group("label") or ""))
            continue
        note = SEQ_NOTE.match(statement)
        if note:
            text = _unquote(note.group("text"))
            if LATENCY_WORDS.search(text) and not latency:
                latency = text
            elif text:
                said.append(text)
            continue
        message = SEQ_MESSAGE.match(statement)
        if not message:
            notes.append("line %d: could not read %r; left out" % (number, statement))
            continue
        a, b, arrow = message.group("a"), message.group("b"), message.group("arrow")
        text = _unquote(message.group("text"))
        node(a)
        node(b)
        dotted = arrow.startswith("--")
        if dotted:
            # A dotted message straight back is the reply to the step before.
            if steps and steps[-1]["a"] == b and steps[-1]["b"] == a:
                steps[-1]["style"] = "Request-response"
                continue
            if nodes[a]["type"] == "systems" and nodes[b]["type"] == "actors":
                continue  # the answer shown to the person; the model draws it from the step
            notes.append("line %d: a dotted message that answers no step before it; read as a step" % number)
        style = "Event" if arrow.endswith(")") else "Request-response"
        ta, tb = nodes[a]["type"], nodes[b]["type"]
        if ta == "systems" and tb == "data_assets":
            touches.append((a, b, _operation(text)))
            continue
        if ta == "data_assets" and tb == "systems":
            touches.append((b, a, _operation(text or "read")))
            continue
        if "data_assets" in (ta, tb):
            notes.append("line %d: a data asset and an actor have no relation here; left out" % number)
            continue
        if ta == "actors" and tb == "systems":
            uses.append((a, b, text))
            continue
        if ta == "systems" and tb == "actors":
            notes.append("line %d: a system telling an actor something is not a step of a flow; left out" % number)
            continue
        if ta == "actors" and tb == "actors":
            notes.append("line %d: two actors talking is not a step of a flow; left out" % number)
            continue
        steps.append({"a": a, "b": b, "text": text, "style": style})

    flow_name = title or name
    # The title names the flow; failing one, the heading or file it came
    # from; failing both, the one word.
    flow_id = "FLOW-" + (_ident(title) if title else (_ident(name) if name != "Imported from Mermaid" else "IMPORTED"))
    doc: dict = {"model": {"name": flow_name}}
    ids: Dict[str, str] = {}
    by_type: Dict[str, List[dict]] = {}
    for mid in order:
        entry = nodes[mid]
        entity_id = _entity_id(entry["type"], mid)
        ids[mid] = entity_id
        record = {ENTITY_TYPES[entry["type"]].pk: entity_id, "name": entry["label"]}
        if entry["type"] == "actors":
            # Mermaid's `actor` is the stick figure: a person. The context
            # view groups actors by kind, and an actor of no kind leaves it
            # with no boundaries, which is the one shape not drawn here.
            record["actor_kind"] = "Person"
        by_type.setdefault(entry["type"], []).append(record)
    for type_name in ("actors", "systems", "data_assets"):
        if by_type.get(type_name):
            doc[type_name] = by_type[type_name]
    interfaces: List[dict] = []
    seen: Dict[Tuple[str, str, str], str] = {}
    counts: Dict[Tuple[str, str], int] = {}
    flow_steps: List[dict] = []
    # A hop whose words name a connection kind is of that kind, as an
    # arrow of a flowchart is; the arrow's own style yields to the kind's,
    # since the words named the kind outright.
    from .connections import find_kind, kinds_for_reading

    kinds = kinds_for_reading()
    of_kind: Dict[str, int] = {}
    for i, step in enumerate(steps):
        key = (step["a"], step["b"], step["text"])
        interface_id = seen.get(key)
        if interface_id is None:
            n = counts.get((step["a"], step["b"]), 0) + 1
            counts[(step["a"], step["b"])] = n
            interface_id = _minted(step["a"], step["b"], n)
            seen[key] = interface_id
            interface = {"interface_id": interface_id, "source_system_id": ids[step["a"]],
                         "target_system_id": ids[step["b"]], "integration_style": step["style"]}
            if step["text"]:
                kind = find_kind(step["text"], kinds)
                if kind is not None:
                    interface.update(kind.defaults())
                    of_kind[kind.connection_id] = of_kind.get(kind.connection_id, 0) + 1
                else:
                    # `HTTPS` or `ISO 8583` is the protocol, which is what the
                    # engine's own sequence diagrams say on a hop; `Score the
                    # transaction` is what the call does, and is the name.
                    interface["protocol" if _protocol_like(step["text"]) else "name"] = step["text"]
            interfaces.append(interface)
        flow_steps.append({"flow_id": flow_id, "interface_id": interface_id, "sequence": (i + 1) * 10})
    for kind_id, n in sorted(of_kind.items()):
        notes.append("%d hop(s) of the kind %s, from the words on the arrows; proposed as the kind proposes, %s over %s" % (
            n, kind_id, kinds[kind_id].integration_style, kinds[kind_id].protocols[0]))
    if interfaces:
        doc["interfaces"] = interfaces
    flow: dict = {"flow_id": flow_id, "name": flow_name}
    if uses:
        flow["trigger"] = uses[0][2] or "starts"
    if latency:
        flow["target_latency"] = latency
    if said:
        flow["description"] = " ".join(said)
    doc["flows"] = [flow]
    relations: Dict[str, List[dict]] = {}
    if uses:
        seen_uses = set()
        rows = []
        for a, b, text in uses:
            if (a, b) in seen_uses:
                continue
            seen_uses.add((a, b))
            row = {"actor_id": ids[a], "system_id": ids[b]}
            if text:
                row["interaction"] = text
            rows.append(row)
        relations["actor_uses_system"] = rows
    if touches:
        rows = []
        for system, asset, operation in touches:
            row = {"system_id": ids[system], "data_asset_id": ids[asset], "operation": operation}
            if row not in rows:
                rows.append(row)
        relations["system_reads_writes"] = rows
    if flow_steps:
        relations["flow_step"] = flow_steps
    doc["relations"] = relations
    # The flow is drawn as a sequence diagram on its own; the context and
    # the landscape show what it runs across.
    doc["views"] = ["system-context", "application-landscape"] if by_type.get("actors") else ["application-landscape"]
    counted = ", ".join("%d %s" % (len(v), k.replace("_", " ")) for k, v in by_type.items())
    notes.insert(0, "read %s and %d step(s) of one flow from the Mermaid; the ids are made from the diagram's own" % (
        counted, len(flow_steps)))
    if not flow_steps:
        notes.append("no message between two systems: the flow has no steps and is not drawn")
    return doc, notes


def _operation(label: str) -> str:
    low = label.lower()
    reads, writes = "read" in low, "write" in low or "stores" in low or "saves" in low
    if reads and not writes:
        return "Read"
    if writes and not reads:
        return "Write"
    return "ReadWrite"


def sketch_from_markdown(text: str, name: str = "Imported from Mermaid") -> Tuple[dict, List[str]]:
    """Every Mermaid block in a Markdown file, read and merged into one
    sketch: the things by id, so the system a flowchart draws and the
    participant a sequence diagram names are one record; the connections
    and the steps as they come; one view per flowchart or C4 block, named
    after the heading above it, and the context and the landscape once
    where a sequence diagram asked for them. The first top-level heading
    names the model. A block that cannot be read is said with its line and
    left out, and the rest still come through."""
    blocks: List[Tuple[int, str, str]] = []
    for match in FENCE.finditer(text):
        before = text[:match.start()]
        headings = HEADING.findall(before)
        heading = headings[-1][1].strip() if headings else ""
        blocks.append((before.count("\n") + 2, heading, match.group(1)))
    if not blocks:
        raise MermaidError("no ```mermaid block in the Markdown")
    top = next((h.strip() for level, h in HEADING.findall(text) if len(level) == 1), "")
    merged: dict = {"model": {"name": top or name}}
    notes: List[str] = []
    # Two readings: the first learns what each block makes of an id, so a
    # thing drawn as a cylinder in one block and named bare in another is
    # one data asset and not a data asset and a system; the second reads
    # every block knowing that.
    kinds: Dict[str, str] = {}
    for _line, heading, block in blocks:
        try:
            doc, _notes = sketch_from_mermaid(block, name=heading)
        except MermaidError:
            continue
        for type_name in ("data_assets", "actors", "capabilities"):
            for record in doc.get(type_name) or []:
                kinds.setdefault(str(record[ENTITY_TYPES[type_name].pk]).split("-", 1)[-1], type_name)
    for i, (line, heading, block) in enumerate(blocks, 1):
        try:
            doc, block_notes = sketch_from_mermaid(block, name=heading or "Diagram %d" % i, kinds=kinds)
        except MermaidError as exc:
            notes.append("block %d (line %d): %s; left out" % (i, line, exc))
            continue
        notes.extend("block %d: %s" % (i, n) for n in block_notes)
        _merge(merged, doc, i, own=len(blocks) > 1)
    if len(merged) == 1:
        raise MermaidError("no Mermaid block in the Markdown could be read; " + "; ".join(notes))
    return merged, notes


def _merge(merged: dict, doc: dict, index: int, own: bool = False) -> None:
    """One block's sketch folded into the whole: records by id, a later
    block filling what an earlier one left out and never overwriting it;
    relation rows once; the block's own view renamed so each keeps one.
    With `own`, the block's view is narrowed to the things the block
    itself drew: a view scoped by type would show every record of the
    merged sketch, so the first page of a drawing carried the second
    page's things."""
    for key, value in doc.items():
        if key == "model":
            continue
        if key == "views":
            views = merged.setdefault("views", [])
            for view in value:
                if isinstance(view, str):
                    if view not in views:
                        views.append(view)
                    continue
                view = dict(view)
                if view.get("view_id") == "imported":
                    view["view_id"] = "imported-%d" % index
                if own and isinstance(view.get("scope"), dict) and view["scope"].get("include"):
                    view["scope"] = dict(view["scope"])
                    view["scope"]["include"] = [
                        {"type": inc["type"], "where": {"id_in": [
                            str(r[ENTITY_TYPES[inc["type"]].pk]) for r in doc.get(inc["type"]) or []]}}
                        if isinstance(inc, dict) and inc.get("type") in ENTITY_TYPES and "where" not in inc else inc
                        for inc in view["scope"]["include"]]
                if not any(isinstance(v, dict) and v.get("view_id") == view["view_id"] for v in views):
                    views.append(view)
            continue
        if key == "relations":
            relations = merged.setdefault("relations", {})
            for relation, rows in value.items():
                existing = relations.setdefault(relation, [])
                for row in rows:
                    if row not in existing:
                        existing.append(row)
            continue
        pk = ENTITY_TYPES[key].pk
        records = merged.setdefault(key, [])
        by_id = {str(r.get(pk)): r for r in records}
        for record in value:
            seen = by_id.get(str(record.get(pk)))
            if seen is None:
                records.append(record)
                by_id[str(record.get(pk))] = record
            else:
                for field, held in record.items():
                    seen.setdefault(field, held)


def sketch_from_mermaid(text: str, name: str = "Imported from Mermaid",
                        kinds: Optional[Dict[str, str]] = None) -> Tuple[dict, List[str]]:
    """The Mermaid diagram as a sketch document, and the notes: what was
    read as what, and any line left out with the reason. A Markdown file
    holding Mermaid blocks is read block by block into one sketch. `kinds`
    says what another diagram already made of an id (`LEDGER` is a data
    asset), for a block read beside others."""
    if FENCE.search(text):
        return sketch_from_markdown(text, name)
    statements = _statements(text)
    if not statements:
        raise MermaidError("nothing to read: the file has no statements")
    first_no, first = statements[0]
    header = HEADER.match(first)
    c4 = C4_HEADER.match(first)
    if SEQ_HEADER.match(first):
        return _sequence_doc(statements, name, kinds)
    if header:
        read = _read_flowchart(statements, header, kinds)
    elif c4:
        read = _read_c4(statements, c4, kinds)
    else:
        raise MermaidError("line %d: expected `flowchart LR` (or TB, RL, BT), `graph ...`, a C4 diagram "
                           "(`C4Context`, `C4Container`, ...) or `sequenceDiagram`, got %r" % (first_no, first))
    return _document(read, name)


def _owner_field(type_name: str) -> Optional[str]:
    fields = {f.name for f in ENTITY_TYPES[type_name].fields}
    for candidate in ("owner_org_id", "data_owner_org_id", "requestor_org_id"):
        if candidate in fields:
            return candidate
    return None


def _document(read: _Read, name: str) -> Tuple[dict, List[str]]:
    """The sketch document for what a diagram read as, and the notes: the
    one builder behind every reader, so a flowchart, a C4 diagram and a
    Structurizr workspace come out as the same kind of sketch. The things
    are records of their type; a connection is whatever the method has
    between two such types -- an interface between systems, a reference
    field (a control's policy, a capability's parent, a data asset's source
    of truth, an owner), or a relation of the schema, chosen by the words
    on the arrow where more than one would do, its qualifier taken from the
    label where it has one -- and one the method lacks is said and left
    out."""
    title = read.title or name
    nodes, order, links, notes = read.nodes, read.order, read.links, read.notes
    # The connection kinds of the method's library: an arrow whose words
    # name one is of that kind, and an arrow that says a protocol one kind
    # alone carries takes that kind's style, so the drawing's connections
    # are the estate's kinds and the connections page counts them.
    from .connections import find_kind, kind_by_protocol, kinds_for_reading

    kinds = kinds_for_reading()
    of_kind: Dict[str, int] = {}
    styled: Dict[str, int] = {}

    doc: dict = {"model": {"name": title}}
    ids: Dict[str, str] = {}
    records: Dict[str, dict] = {}
    by_type: Dict[str, List[dict]] = {}
    for mid in order:
        entry = nodes[mid]
        type_name = entry["type"]
        entity_id = _entity_id(type_name, mid)
        ids[mid] = entity_id
        record = {ENTITY_TYPES[type_name].pk: entity_id, "name": entry["label"]}
        if entry.get("description"):
            record["description"] = entry["description"]
        if entry["domain"] and "company_domain" in {f.name for f in ENTITY_TYPES[type_name].fields}:
            record["company_domain"] = entry["domain"]
        if entry.get("kind"):
            record["actor_kind"] = entry["kind"]
        if entry.get("external"):
            if type_name == "actors":
                record["internal"] = entry["external"]
            elif type_name == "systems":
                record["hosting"] = entry["external"]
        records[mid] = record
        by_type.setdefault(type_name, []).append(record)
    for type_name in ENTITY_TYPES:
        if by_type.get(type_name):
            doc[type_name] = by_type[type_name]

    interfaces: List[dict] = []
    relations: Dict[str, List[dict]] = {}
    vias: List[Tuple[str, Optional[str]]] = []
    seen_interfaces: Dict[Tuple[str, str], int] = {}

    # An offered interface and the system that offers it, found before the
    # lines are read, since a line through it needs its owner whichever
    # comes first: the line the export marks as the interface's own field,
    # one worded as offering it, or, drawn with one system and no words,
    # that system. One nothing offers is said and left out, with its lines.
    doors = {mid for mid in order if nodes[mid]["type"] == "offered_interfaces"}
    owner_of: Dict[str, str] = {}
    owner_lines: set = set()
    for a, b, label, technology in links if doors else []:
        if (a in doors) == (b in doors):
            continue
        door, other = (a, b) if a in doors else (b, a)
        if nodes[other]["type"] != "systems":
            continue
        queue = read.link_marks.get((_ident(a), _ident(b), label or "")) or []
        said = (label or technology or "").strip().lower()
        if (queue and queue[0].get("field") == "system_id") or said in OFFER_WORDS \
                or (a, b) in read.open_links:
            owner_of.setdefault(door, other)
            owner_lines.add((a, b, label or ""))
    for door in sorted(doors - set(owner_of)):
        touching = {other for a, b, _label, _tech in links for d, other in ((a, b), (b, a))
                    if d == door and other in nodes and nodes[other]["type"] == "systems"}
        if len(touching) == 1:
            owner_of[door] = touching.pop()
    for door in sorted(doors):
        if door in owner_of:
            records[door]["system_id"] = ids[owner_of[door]]
        else:
            notes.append("%s: an offered interface no system offers; left out, with its lines" % door)
            by_type["offered_interfaces"].remove(records[door])
    if doors and not by_type.get("offered_interfaces"):
        doc.pop("offered_interfaces", None)
        by_type.pop("offered_interfaces", None)

    def via(name_: str, qualifier: Optional[str] = None) -> None:
        if not any(v == name_ for v, _q in vias):
            vias.append((name_, qualifier))

    def add_row(relation, row: dict) -> None:
        rows = relations.setdefault(relation.name, [])
        if row not in rows:
            rows.append(row)
        via(relation.name, relation.qualifier)

    def pick(candidates, text: str):
        low = text.lower()
        for candidate in candidates:
            if edge_word(candidate.name).lower() == low:
                return candidate
        return candidates[0]

    for a, b, label, technology in links:
        ta, tb = nodes[a]["type"], nodes[b]["type"]
        text = label or technology
        # What an export wrote under the line outranks what the line's
        # ends and words suggest: a derived line is no row, and a row comes
        # back as the row it was, qualifier and all, where a line with no
        # label read as ReadWrite over a Read row.
        key = (_ident(a), _ident(b), label or "")
        queue = read.link_marks.get(key) or []
        line_mark = queue[0] if queue else None
        if line_mark and line_mark.get("derived"):
            queue.pop(0)
            continue
        if line_mark and line_mark.get("field"):
            # A line drawing a record's field (a data asset's source of
            # truth): the field set on whichever end has it, no row.
            field = line_mark["field"]
            if field == "system_id" and doors:
                pass  # an offered interface's own line, read before the loop
            else:
                if field in {f.name for f in ENTITY_TYPES[tb].fields}:
                    records[b][field] = ids[a]
                elif field in {f.name for f in ENTITY_TYPES[ta].fields}:
                    records[a][field] = ids[b]
                queue.pop(0)
                via(field)
                continue
        if line_mark and line_mark.get("relation") in RELATION_TYPES:
            spec = RELATION_TYPES[line_mark["relation"]]
            # Forward first: a relation between two things of one type
            # (a technology service connecting to another) fits both ways,
            # and the reversed fit won, so the row came back to front.
            if (ta, tb) == (spec.left, spec.right):
                ends: Optional[Tuple[str, str]] = (ids[a], ids[b])
            elif (ta, tb) == (spec.right, spec.left):
                ends = (ids[b], ids[a])
            else:
                ends = None
            if ends is not None:
                queue.pop(0)
                row = {spec.left_column: ends[0], spec.right_column: ends[1]}
                if spec.qualifier:
                    row[spec.qualifier] = line_mark.get(spec.qualifier, "")
                add_row(spec, row)
                continue
        fields_a = {f.name for f in ENTITY_TYPES[ta].fields}
        fields_b = {f.name for f in ENTITY_TYPES[tb].fields}
        # A line between a system and an interface: its owner's own line,
        # read already, or a connection through it, between the line's
        # other end and the owner, running the line's way.
        through = ""
        ea, eb = a, b
        if doors and (a in doors) != (b in doors) and {ta, tb} == {"systems", "offered_interfaces"}:
            door = a if a in doors else b
            if (a, b, label or "") in owner_lines or door not in owner_of:
                if queue and queue[0].get("field") == "system_id":
                    queue.pop(0)
                continue
            owner = owner_of[door]
            ea, eb = (owner, b) if a == door else (a, owner)
            if ea == eb:
                continue  # the owner's line, drawn twice
            through = ids[door]
            ta = tb = "systems"
        elif doors and (a in doors and a not in owner_of or b in doors and b not in owner_of):
            continue
        if ta == "systems" and tb == "systems":
            n = seen_interfaces.get((ea, eb), 0) + 1
            seen_interfaces[(ea, eb)] = n
            mark = dict(queue.pop(0)) if queue and queue[0].get("interface_id") else {}
            given = mark.pop("interface_id", "")
            was = mark.pop("kind", "")
            interface = {"interface_id": given or _minted(ea, eb, n),
                         "source_system_id": ids[ea], "target_system_id": ids[eb]}
            if through:
                interface["offered_interface_id"] = through
            if label:
                interface["name"] = label
            if technology and technology.lower() != "calls":
                interface["protocol"] = technology
            tagged = kinds.get(read.link_kinds.get((a, b), ""))
            # On a line the export wrote, the tag alone names the kind: a
            # view labels a line by its integration style, and "Event"
            # named a kind and read as a re-tag.
            kind = tagged if mark else (find_kind(label, kinds) or find_kind(technology, kinds) or tagged)
            if mark and (kind is None or kind.connection_id == was):
                # The export's own line, tagged as it was: the record's
                # values stand, and the kind proposes nothing over them.
                # Re-tagged by hand, the new kind proposes as it would to a
                # sketch, the way the workbook's kind column works.
                # Not counted among the connections "from the words on the
                # arrows": the record's own values are nobody's proposal, and
                # a whole export read back printed a note per kind per page.
                for key, value in mark.items():
                    interface[key] = [w.strip() for w in value.split(";") if w.strip()] if key == "patterns" else value
            elif kind is not None:
                proposal = kind.defaults()
                said = str(interface.get("protocol") or "")
                if said and said.lower() in (p.lower() for p in kind.protocols):
                    # The arrow said which of the kind's protocols; the
                    # proposal's first is for an arrow that said none.
                    proposal.pop("protocol", None)
                interface.update(proposal)
                of_kind[kind.connection_id] = of_kind.get(kind.connection_id, 0) + 1
            elif technology:
                carrier = kind_by_protocol(technology, kinds)
                if carrier is not None:
                    interface["integration_style"] = carrier.integration_style
                    styled[carrier.connection_id] = styled.get(carrier.connection_id, 0) + 1
            interfaces.append(interface)
            via("interfaces", "protocol")
            continue
        if ta == tb == "capabilities":
            records[a]["parent_capability_id"] = ids[b]
            via("parent_capability_id")
            continue
        if ta == "org_units" and _owner_field(tb):
            records[b][_owner_field(tb)] = ids[a]
            via("owner")
            continue
        if tb == "org_units" and _owner_field(ta):
            records[a][_owner_field(ta)] = ids[b]
            via("owner")
            continue
        if ta == "systems" and tb == "data_assets" and text.lower() in ("masters", "source of truth", "sot"):
            records[b]["source_of_truth"] = ids[a]
            via("source_of_truth")
            continue
        if ta == "data_assets" and tb == "systems":
            # A cylinder feeding a box is the box reading it.
            relation = RELATION_TYPES["system_reads_writes"]
            add_row(relation, {relation.left_column: ids[b], relation.right_column: ids[a],
                               relation.qualifier: _operation(text or "read")})
            continue
        if ENTITY_TYPES[tb].pk in fields_a:
            records[a][ENTITY_TYPES[tb].pk] = ids[b]
            via(ENTITY_TYPES[tb].pk)
            continue
        if ENTITY_TYPES[ta].pk in fields_b:
            records[b][ENTITY_TYPES[ta].pk] = ids[a]
            via(ENTITY_TYPES[ta].pk)
            continue
        forward = [r for r in RELATION_TYPES.values() if r.left == ta and r.right == tb]
        backward = [r for r in RELATION_TYPES.values() if r.left == tb and r.right == ta]
        if forward:
            relation = pick(forward, text)
            row = {relation.left_column: ids[a], relation.right_column: ids[b]}
            drawn_forward = True
        elif backward and (not text or text.lower().endswith(" by")):
            # An arrow drawn the other way round says so in the passive
            # (`supported by`); without the words it is a connection the
            # method does not have in that direction.
            relation = pick(backward, text)
            row = {relation.left_column: ids[b], relation.right_column: ids[a]}
            drawn_forward = False
        else:
            notes.append("%s -> %s: no relation here joins %s to %s; left out" % (
                a, b, ta.replace("_", " "), tb.replace("_", " ")))
            continue
        word = edge_word(relation.name).lower()
        if relation.qualifier:
            # The words on the arrow are the qualifier's value, `uses` and
            # `Primary` alike: what the author wrote is what the row says.
            if text:
                row[relation.qualifier] = _operation(text) if relation.name == "system_reads_writes" else text
            elif relation.name == "system_reads_writes":
                row[relation.qualifier] = "ReadWrite"
        elif text and text.lower() != word and drawn_forward and _protocol_like(text) and text != text.lower():
            # A code on an arrow (`gRPC`) is a fact the relation has no field
            # for, and dropping it silently would make the sketch look
            # complete when it is not; a phrase (`supported by`, `enforces`)
            # is the view's wording for the relation itself.
            notes.append("%s -> %s: %s carries no label; %r not kept" % (
                a, b, relation.name.replace("_", " "), text))
        add_row(relation, row)
    for kind_id, n in sorted(of_kind.items()):
        notes.append("%d connection(s) of the kind %s, from the words on the arrows; proposed as the kind proposes, "
                     "%s over %s" % (n, kind_id, kinds[kind_id].integration_style, kinds[kind_id].protocols[0]))
    for kind_id, n in sorted(styled.items()):
        notes.append("%d arrow(s) saying a protocol only the kind %s carries; read as %s" % (
            n, kind_id, kinds[kind_id].integration_style))
    if interfaces:
        doc["interfaces"] = interfaces
    if relations:
        doc["relations"] = relations
    view: dict = {
        "view_id": "imported", "title": title, "kind": "diagram", "layout": read.direction,
        "description": "Read from %s%s." % (read.source, ", " + read.group_word if read.any_group
                                             and read.group_word else ""),
        "node_label": "name", "renderers": ["mermaid"],
        "scope": {"include": [{"type": t} for t in ENTITY_TYPES if by_type.get(t)]},
        "edges": [],
        "style": {"color_by": "type"},
        "limits": {"max_nodes": max(60, len(order))},
    }
    if read.any_group:
        view["group_by"] = "company_domain"
    for name_, qualifier in vias:
        edge = {"via": name_}
        if qualifier:
            edge["label"] = qualifier
        view["edges"].append(edge)
    doc["views"] = [view]
    counts = ", ".join("%d %s" % (len(v), k.replace("_", " ")) for k, v in by_type.items())
    notes.insert(0, "read %s and %d connection(s) from the Mermaid; the ids are made from the diagram's own" % (
        counts, len(links)))
    return doc, notes
