"""A C4-PlantUML diagram read as a sketch.

Where a team drew its C4 diagrams before Mermaid had them, it drew them
with C4-PlantUML: `@startuml`, an `!include` of `C4_Container.puml`, then
`Person(alias, "label", "description")`, `System_Boundary(alias, "label")
{ ... }`, `Container(alias, "label", "technology", "description")` and
`Rel(from, to, "label", "technology")`, with `LAYOUT_WITH_LEGEND()`,
`SHOW_LEGEND()`, `$tags` and `$link` arguments, `'` comments and the rest
of PlantUML around it. Mermaid's C4 diagrams copied that vocabulary, so
this reads the PlantUML by bringing it to the form the C4 reader takes: the
directives, includes, layout macros, legends, notes and comments go, a
statement split over lines is joined, named arguments (`$descr="..."`)
take their positional place, a `RelIndex` loses its index, and the kind of
diagram is read off the include. The elements, boundaries and relations
then mean what they mean in a Mermaid C4 diagram: a person an actor, a
system or container a system, a database a data asset, a boundary the
domain, a `Rel` the connection with its technology as the protocol.
"""

from __future__ import annotations

import re
from typing import Dict, List, NamedTuple, Optional, Tuple

from .mermaid_import import C4_HEADER, ReadError, _document, _ident, _read_c4

#: Lines that say how to draw, not what there is.
SKIP = re.compile(r"^\s*(@start|@end|!|skinparam\b|hide\b|show\b|scale\b|header\b|footer\b|caption\b|"
                  r"left to right|top to bottom|LAYOUT_|SHOW_|HIDE_|SetDefault|Set[A-Z]\w*Header|AddProperty|"
                  r"WithoutPropertyHeader|Add[A-Z]\w*Tag\b|Lay_|Lay[A-Z]|autonumber\b|allowmixing\b|"
                  r"mainframe\b|sprite\b|newpage\b)", re.I)
INCLUDE = re.compile(r"^\s*!include(?:url|sub)?\s+.*?C4_(Context|Container|Component|Deployment|Dynamic|Sequence)", re.I)
STATEMENT = re.compile(r"^\s*(?P<kind>[A-Za-z_]+)\s*\((?P<args>.*)\)\s*(?P<open>\{)?\s*$", re.S)
NAMED = re.compile(r"^\s*\$(?P<name>\w+)\s*=\s*(?P<value>.*)$", re.S)
BLOCK_COMMENT = re.compile(r"/'.*?'/", re.S)
#: The line the export writes under an element with the record's own
#: fields: `' aac SYS_X: company_domain="Payments"; hosting="SaaS"`.
MARK = re.compile(r"^'\s*aac\s+(?P<alias>[A-Za-z0-9_]+):\s*(?P<fields>.*)$")
MARK_FIELD = re.compile(r'(\w+)="([^"]*)"')


class _Marks(NamedTuple):
    """What the export wrote under the macros: the fields per element, by
    the element's id, and a mark per `Rel` with the interface's id."""
    elements: Dict[str, Dict[str, str]]
    rels: List[Dict[str, str]]
#: The positional slots each kind of macro takes, by the words its macro
#: starts with; the rest of C4-PlantUML's named arguments are dropped.
SLOTS: Dict[str, Tuple[str, ...]] = {
    "person": ("alias", "label", "descr"), "system": ("alias", "label", "descr"),
    "container": ("alias", "label", "techn", "descr"), "component": ("alias", "label", "techn", "descr"),
    "node": ("alias", "label", "type", "descr"), "deployment_node": ("alias", "label", "type", "descr"),
    "boundary": ("alias", "label", "type"), "rel": ("from", "to", "label", "techn"), "birel": ("from", "to", "label", "techn"),
}


class PlantumlError(ReadError):
    pass


def _split_named(text: str) -> Tuple[List[str], Dict[str, str]]:
    """The arguments as written, the positional ones in order and the
    named ones by name, split on the commas outside quotes."""
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
    positional: List[str] = []
    named: Dict[str, str] = {}
    for arg in out:
        m = NAMED.match(arg)
        if m:
            named[m.group("name").lower()] = m.group("value").strip()
        else:
            positional.append(arg.strip())
    return positional, named


def _slots(kind: str) -> Optional[Tuple[str, ...]]:
    low = kind.lower()
    if low.startswith("deployment_node"):
        return SLOTS["deployment_node"]
    for word in ("person", "system", "container", "component", "node", "birel", "rel"):
        if low.startswith(word) or (word == "boundary" and low.endswith("boundary")):
            return SLOTS[word]
    if low.endswith("boundary"):
        return SLOTS["boundary"]
    return None


def _normalize(kind: str, args: str) -> Tuple[str, str]:
    """The macro as the C4 reader takes it: the kind without its index
    variant and the arguments positional, in their slots."""
    positional, named = _split_named(args)
    if kind.lower() in ("relindex", "rel_index"):
        kind = "Rel"
        positional = positional[1:]
    slots = _slots(kind)
    if slots is None:
        return kind, ", ".join(positional)
    values = list(positional[:len(slots)])
    while len(values) < len(slots) and any(name in named for name in slots[len(values):]):
        values.append("")
    for i, name in enumerate(slots):
        if i < len(values) and not values[i] and name in named:
            values[i] = named[name]
    while values and not values[-1]:
        values.pop()
    return kind, ", ".join(values)


def to_mermaid(text: str) -> Tuple[str, List[str]]:
    """The C4-PlantUML text as a Mermaid C4 diagram, and the notes."""
    mermaid, notes, _kinds = to_mermaid_with_kinds(text)
    return mermaid, notes


def to_mermaid_with_kinds(text: str) -> Tuple[str, List[str], Dict[str, str]]:
    """The C4-PlantUML text as a Mermaid C4 diagram, the notes, and what
    the `$tags` on the macros say an element is: a tag naming one of the
    method's types (`$tags="capabilities"`, which the export writes for
    what C4 has no word for) is the element's type, keyed by its alias
    the way the C4 reader keys it."""
    mermaid, notes, kinds, _links, _marks = _translate(text)
    return mermaid, notes, kinds


def _translate(text: str) -> Tuple[str, List[str], Dict[str, str], Dict[Tuple[str, str], str], _Marks]:
    """`to_mermaid_with_kinds`, the connection kind each `Rel` was tagged
    with, by its two ends as written (the export tags a Rel of a kind with
    the kind's id; a tag naming no kind is a styling tag), and the fields
    the export wrote under each element in a `' aac` comment, by the
    element's id."""
    from .connections import kinds_for_reading
    from .schema import ENTITY_TYPES

    connections = kinds_for_reading()
    kinds: Dict[str, str] = {}
    links: Dict[Tuple[str, str], str] = {}
    marks = _Marks({}, [])
    notes: List[str] = []
    text = BLOCK_COMMENT.sub("", text)
    header = "C4Context"
    lines: List[str] = []
    skipping = ""
    pending = ""
    for raw in text.splitlines():
        line = raw.strip()
        marked = MARK.match(line)
        if marked:
            fields = dict(MARK_FIELD.findall(marked.group("fields")))
            if marked.group("alias") == "rel":
                marks.rels.append(fields)
            else:
                marks.elements[_ident(marked.group("alias"))] = fields
            continue
        if pending:
            line = pending + " " + line
            pending = ""
        if not line or line.startswith("'"):
            continue
        if skipping:
            if line.lower().startswith(skipping):
                skipping = ""
            continue
        low = line.lower()
        if low.startswith("legend"):
            skipping = "endlegend"
            continue
        if low.startswith("note") and not low.startswith("note:") and low.rstrip(":") != "note":
            if ":" not in line:
                skipping = "end note"
            continue
        include = INCLUDE.match(line)
        if include:
            kind = include.group(1).capitalize()
            header = "C4" + ("Dynamic" if kind == "Sequence" else kind)
            continue
        if SKIP.match(line):
            continue
        if line in ("{", "}") or low.startswith("title "):
            lines.append(line)
            continue
        # A macro split over lines: join until its brackets balance.
        if line.count("(") > line.count(")"):
            pending = line
            continue
        m = STATEMENT.match(line)
        if not m:
            lines.append(line)  # the C4 reader will say what it could not read
            continue
        positional, named = _split_named(m.group("args"))
        tag = named.get("tags", "").strip().strip("\"'")
        is_rel = m.group("kind").lower().startswith(("rel", "birel"))
        if tag and is_rel and len(positional) >= 2:
            # A tag naming no kind is a styling tag, as C4-PlantUML teams
            # use them (`$tags="legacy"`), and is left alone without a
            # word: a note on every styled line would bury the real ones.
            if tag in connections:
                links[(positional[0].strip().strip("\"'"), positional[1].strip().strip("\"'"))] = tag
        elif tag in ENTITY_TYPES and positional:
            kinds[_ident(positional[0].strip().strip("\"'"))] = tag
        kind, args = _normalize(m.group("kind"), m.group("args"))
        lines.append("%s(%s)%s" % (kind, args, " {" if m.group("open") else ""))
    if pending:
        notes.append("a statement never closed its bracket: %r; left out" % pending[:60])
    return "\n".join([header] + lines) + "\n", notes, kinds, links, marks


def sketch_from_plantuml(text: str, name: str = "Imported from PlantUML") -> Tuple[dict, List[str]]:
    """The sketch a C4-PlantUML diagram reads as, and the notes."""
    if "@startuml" not in text and not INCLUDE.search(text) and "Rel(" not in text:
        raise PlantumlError("not a C4-PlantUML diagram: no @startuml, no C4 include and no Rel")
    mermaid, pre_notes, kinds, links, marks = _translate(text)
    from .mermaid_import import _statements

    statements = _statements(mermaid)
    header = C4_HEADER.match(statements[0][1])
    assert header is not None
    read = _read_c4(statements, header, kinds)
    read.link_kinds = links
    # What the export wrote under each element, over what the picture alone
    # said: the boundary was the view's grouping and not the domain, `_Ext`
    # is External whatever the record said, every Person a person, and the
    # "Built with" sentence the export's own. The estate's own page read
    # back "corrected" seven systems and eight actors before.
    for mid, entry in read.nodes.items():
        mark = marks.elements.get(_ident(mid))
        if not mark:
            continue
        if "company_domain" in mark:
            entry["domain"] = mark["company_domain"]
        if "hosting" in mark and entry.get("type") == "systems":
            entry["external"] = mark["hosting"]
        if "internal" in mark and entry.get("type") == "actors":
            entry["external"] = mark["internal"]
        if "actor_kind" in mark:
            entry["kind"] = mark["actor_kind"]
        if mark.get("technology"):
            suffix = "Built with %s." % mark["technology"]
            if str(entry.get("description") or "").endswith(suffix):
                entry["description"] = str(entry["description"])[:-len(suffix)].strip()
    for fields in marks.rels:
        if fields.get("source") and fields.get("target") and (
                fields.get("interface_id") or fields.get("relation") or fields.get("derived") or fields.get("field")):
            key = (_ident(fields["source"]), _ident(fields["target"]), fields.get("label", ""))
            read.link_marks.setdefault(key, []).append(
                {k: v for k, v in fields.items() if k not in ("source", "target", "label")})
    read.source = "a C4-PlantUML diagram: an element per macro, a Rel per connection"
    read.notes[:0] = pre_notes
    if not read.order:
        raise PlantumlError("no element declared: nothing to read as a sketch")
    doc, notes = _document(read, name)
    notes[0] = notes[0].replace("from the Mermaid", "from the PlantUML")
    return doc, notes
