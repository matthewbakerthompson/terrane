"""A Structurizr DSL workspace read as a sketch.

Where a team took up C4 in earnest, what they keep is not a Mermaid
diagram but a Structurizr workspace: `person`, `softwareSystem`,
`container` and `component` statements in a `model` block, relationships
written `a -> b "description" "technology"`, groups and nested blocks, and
a `views` block that says how to look at it. The engine exports the same
dialect (`render_structurizr`); this reads it back, and reads the hand
written ones too.

A `person` is an actor; a `softwareSystem`, a `container` and a
`component` are systems, tagged `External` or `Existing System` hosted
externally, a container whose tag or technology says database a data
asset. An element with a block of children is the boundary of what is
inside -- a software system with containers is their domain, as a C4
`System_Boundary` is -- and is not a box of its own, so a relationship
that names it is left out and said. A `group` is a domain too. A
relationship is the connection two such things have here, its description
the interface's name or the actor's interaction, its technology the
protocol, a tag naming a connection kind the kind; `->` at the start of a line inside an element's block is from
that element. The `views`, `configuration`, deployment and style blocks,
`!include`, `!docs` and the other directives are skipped, since they say
how to look and not what there is; hierarchical identifiers (`bank.web`)
are read by their last segment.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from .connections import find_kind, kinds_for_reading
from .mermaid_import import ReadError, _document, _ident, _operation, _Read  # noqa: F401
from .schema import ENTITY_TYPES

ELEMENTS = {"person": "actors", "softwaresystem": "systems", "container": "systems", "component": "systems"}
#: Blocks and statements that say how to look at the model, not what is in it.
SKIP = {"views", "configuration", "styles", "style", "theme", "themes", "branding", "terminology", "users",
        "deploymentenvironment", "deploymentnode", "infrastructurenode", "containerinstance",
        "softwaresysteminstance", "properties", "perspectives", "systemlandscape", "systemcontext",
        "dynamic", "deployment", "filtered", "custom", "image", "animation", "include", "exclude", "autolayout",
        "element", "relationship", "archetypes"}
DATABASE = re.compile(r"\b(database|db|sql|postgres|postgresql|oracle|mongo|mongodb|dynamo|dynamodb|cosmos|redis)\b",
                      re.I)
EXTERNAL = re.compile(r"\b(external|existing system)\b", re.I)
Token = Tuple[str, bool]  # text, quoted


class StructurizrError(ReadError):
    pass


def _tokens(line: str) -> List[Token]:
    """The line's words: quoted strings whole and unquoted, braces on
    their own, bare words as they are; a `//` or `#` comment ends it."""
    out: List[Token] = []
    i, n = 0, len(line)
    while i < n:
        ch = line[i]
        if ch.isspace():
            i += 1
            continue
        if ch == '"':
            j = i + 1
            buf: List[str] = []
            while j < n and line[j] != '"':
                if line[j] == "\\" and j + 1 < n:
                    buf.append(line[j + 1])
                    j += 2
                    continue
                buf.append(line[j])
                j += 1
            out.append(("".join(buf).strip(), True))
            i = j + 1
            continue
        if ch in "{}":
            out.append((ch, False))
            i += 1
            continue
        if line.startswith("//", i) or ch == "#":
            break
        j = i
        while j < n and not line[j].isspace() and line[j] not in '{}"':
            j += 1
        out.append((line[i:j], False))
        i = j
    return out


def _last(identifier: str) -> str:
    return identifier.rsplit(".", 1)[-1]


def sketch_from_structurizr(text: str, name: str = "Imported from Structurizr") -> Tuple[dict, List[str]]:
    """The workspace as a sketch document, and the notes: what was read as
    what, and any line left out with the reason."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    read = _Read()
    kinds = kinds_for_reading()
    read.direction = "TB"
    read.source = "a Structurizr DSL workspace: an element per statement, a relationship per connection"
    read.group_word = "a group, or a system with containers, per domain"
    scopes: List[dict] = []
    skip_depth = 0
    children: Dict[str, int] = {}
    seen_anything = False
    # What the engine's own workspace says in `properties` blocks, by the
    # element it is under or the relationship: the record's type, id and
    # fields, a line's interface id and pinned values, a row's relation
    # and qualifier, a field's name. Applied after the read, over the
    # tags and the groups.
    element_marks: Dict[str, Dict[str, str]] = {}
    rel_marks: Dict[Tuple[str, str, str], Dict[str, str]] = {}

    def domain() -> str:
        for scope in reversed(scopes):
            if scope.get("domain"):
                return str(scope["domain"])
        return ""

    def element() -> Optional[str]:
        for scope in reversed(scopes):
            if scope.get("mid"):
                return str(scope["mid"])
        return None

    for number, raw in enumerate(text.splitlines(), 1):
        toks = _tokens(raw)
        if not toks:
            continue
        if skip_depth:
            skip_depth += sum(1 for t, q in toks if not q and t == "{") - sum(1 for t, q in toks if not q and t == "}")
            continue
        if toks[0] == ("}", False):
            if scopes:
                scopes.pop()
            continue
        opens = toks[-1] == ("{", False)
        body = toks[:-1] if opens else toks
        bare = [t for t, q in body if not q]
        strings = [t for t, q in body if q]
        if scopes and scopes[-1].get("properties"):
            # A `"key" "value"` line of a properties block: an `aac.` key is
            # the export's own word for the element or the relationship the
            # block sits under; any other property is left alone.
            if len(strings) >= 2 and strings[0].startswith("aac."):
                for scope in reversed(scopes[:-1]):
                    if scope.get("rel"):
                        rel_marks.setdefault(scope["rel"], {})[strings[0][4:]] = strings[1]
                        break
                    if scope.get("mid"):
                        element_marks.setdefault(str(scope["mid"]), {})[strings[0][4:]] = strings[1]
                        break
            if opens:
                skip_depth = 1
            continue
        if scopes and scopes[-1].get("rel") and not opens and "->" not in bare:
            continue  # a relationship block's own lines (tags, url): nothing here reads them
        if "->" in bare:
            at = next(i for i, (t, q) in enumerate(body) if not q and t == "->")
            source = body[at - 1][0] if at > 0 and not body[at - 1][1] else None
            if source is None or source == "this":
                source = element()
                if source is None:
                    read.notes.append("line %d: a relationship from nothing; left out" % number)
                    if opens:
                        skip_depth = 1
                    continue
            if at + 1 >= len(body) or body[at + 1][1]:
                read.notes.append("line %d: a relationship to nothing; left out" % number)
                if opens:
                    skip_depth = 1
                continue
            target = body[at + 1][0]
            target = element() if target == "this" else target
            after = [t for t, q in body[at + 2:] if q]
            description = after[0] if after else ""
            technology = after[1] if len(after) > 1 else ""
            for end in (source, target):
                if _last(end) not in read.nodes:
                    read.notes.append("line %d: %r was never declared; read as a system" % (number, end))
                    read.node(_last(end), domain())
            read.links.append((_last(source), _last(str(target)), description, technology))
            # The third string is the relationship's tags; one naming a
            # connection kind is the kind, as the engine's own workspace
            # writes it. Other tags are styling, and are left alone.
            for word in (after[2] if len(after) > 2 else "").split(","):
                kind = find_kind(word, kinds)
                if kind is not None:
                    read.link_kinds[(_last(source), _last(str(target)))] = kind.connection_id
            seen_anything = True
            if opens:
                # A relationship's block holds tags, a url and properties;
                # the block is a scope, so a properties block in it says
                # what the line is.
                scopes.append({"rel": (_last(source), _last(str(target)), description)})
            continue
        if len(body) >= 3 and body[1] == ("=", False) and not body[0][1]:
            mid, keyword, args = body[0][0], body[2][0].lower(), [t for t, q in body[3:] if q]
        else:
            mid, keyword, args = None, body[0][0].lower(), strings
        if keyword == "workspace":
            read.title = args[0] if args else ""
            scopes.append({})
            seen_anything = True
            continue
        if keyword == "model":
            scopes.append({})
            continue
        if keyword == "group":
            scopes.append({"domain": args[0] if args else "group"})
            read.any_group = True
            continue
        if keyword in ELEMENTS:
            type_name = ELEMENTS[keyword]
            label = args[0] if args else (mid or keyword)
            if keyword in ("person", "softwaresystem"):
                description = args[1] if len(args) > 1 else ""
                technology = ""
                tags = args[2] if len(args) > 2 else ""
            else:
                description = args[1] if len(args) > 1 else ""
                technology = args[2] if len(args) > 2 else ""
                tags = args[3] if len(args) > 3 else ""
            mid = _last(mid) if mid else re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") or keyword
            parent = element()
            if parent:
                children[parent] = children.get(parent, 0) + 1
            entry = read.node(mid, domain())
            entry["type"] = type_name
            entry["label"] = label
            if technology:
                description = (description + " " if description else "") + "Built with %s." % technology
            entry["description"] = description.strip()
            if keyword == "person":
                entry["kind"] = "Person"
                entry["external"] = "No" if EXTERNAL.search(tags) else "Yes"
            else:
                entry["external"] = "External" if EXTERNAL.search(tags) else ""
                if keyword in ("container", "component") and (DATABASE.search(tags) or DATABASE.search(technology)):
                    entry["type"] = "data_assets"
            seen_anything = True
            if opens:
                # An element with a block is the boundary of what is inside.
                scopes.append({"domain": label, "mid": mid})
                read.any_group = True
            continue
        if keyword == "properties" and opens:
            scopes.append({"properties": True})
            continue
        if keyword in ("description", "technology", "tags", "url"):
            mid = element()
            if mid and strings:
                entry = read.nodes[mid]
                if keyword == "description":
                    entry["description"] = (strings[0] + (" " + entry["description"] if entry["description"] else "")).strip()
                elif keyword == "technology":
                    entry["description"] = (entry["description"] + " " if entry["description"] else "") + \
                        "Built with %s." % strings[0]
                elif keyword == "tags":
                    if EXTERNAL.search(strings[0]):
                        entry["external"] = "No" if entry["type"] == "actors" else "External"
                    if entry["type"] == "systems" and DATABASE.search(strings[0]):
                        entry["type"] = "data_assets"
            continue
        if keyword in SKIP or keyword.startswith("!"):
            if opens:
                skip_depth = 1
            continue
        read.notes.append("line %d: could not read %r; left out" % (number, raw.strip()))
        if opens:
            skip_depth = 1
    for mid, marks in element_marks.items():
        entry = read.nodes.get(mid)
        if entry is None:
            continue
        if marks.get("type") in ENTITY_TYPES:
            entry["type"] = marks["type"]
        if "company_domain" in marks:
            entry["domain"] = marks["company_domain"]
        if marks.get("actor_kind"):
            entry["kind"] = marks["actor_kind"]
        if entry["type"] == "systems" and marks.get("hosting"):
            entry["external"] = marks["hosting"]
        if entry["type"] == "actors" and marks.get("internal"):
            entry["external"] = marks["internal"]
    for (a, b, description), marks in rel_marks.items():
        read.link_marks.setdefault((_ident(a), _ident(b), description), []).append(marks)
    if not seen_anything:
        raise StructurizrError("nothing to read: no `workspace`, no element and no relationship")

    # An element with children is their boundary, not a box: it leaves the
    # nodes, and a relationship that named it has nowhere to go.
    boundaries = {mid for mid, n in children.items() if n}
    for mid in boundaries:
        read.nodes.pop(mid, None)
        read.order.remove(mid)
    kept = []
    for a, b, description, technology in read.links:
        if a in boundaries or b in boundaries:
            read.notes.append("%s -> %s: %s has containers and is drawn as their boundary, not as a box; the "
                              "relationship is left out" % (a, b, a if a in boundaries else b))
            continue
        kept.append((a, b, description, technology))
    read.links = kept
    doc, notes = _document(read, name)
    notes[0] = notes[0].replace("from the Mermaid", "from the workspace")
    return doc, notes
