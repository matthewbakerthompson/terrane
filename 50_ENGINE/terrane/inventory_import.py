"""A spreadsheet of systems read as a sketch.

Before a diagram, most practices have a list: a CSV or a tab-separated
export of the application inventory, one row per thing, with whatever
columns the spreadsheet grew. This reads such a file as a sketch by its
headers, so the list becomes a model and the model becomes pictures. A
column is known by its name, spelled loosely: `name` (or `system`,
`application`, `title`), `id` (or `key`, `identifier`), `type` (or `kind`,
`category`), `domain` (or `business domain`, `area`), `description` (or
`notes`, `purpose`), `owner`, `hosting` (or `provider`, `cloud`), `status`,
`criticality` (or `tier`), and the columns that say what a row connects to:
`calls`, `depends on`, `uses`, `connects to`, `integrates with`,
`downstream`, `sends to` for connections from the row, `called by`,
`upstream`, `used by` for connections to it, and `reads` and `writes` for
the data. A connection names other rows by name or id, several separated
by semicolons, commas or pipes; one that names nothing in the file is
said and left out. The type column decides what a row is by its words: a
database or a dataset a data asset, a person, actor, role or user an
actor, a capability a capability, a process a process, a product a
product, a service, platform or infrastructure a technology service, and
anything else, or nothing, a system. Columns the method has no field for
are said once and left out, so nothing is lost quietly.
"""

from __future__ import annotations

import csv
import io
import re
from typing import Dict, List, Optional, Tuple

from .mermaid_import import ReadError, _document, _protocol_like, _Read

COLUMNS: Dict[str, Tuple[str, ...]] = {
    "name": ("name", "system", "application", "app", "title", "component", "asset"),
    "id": ("id", "key", "identifier", "system_id", "app_id", "code", "ref"),
    "type": ("type", "kind", "category", "class", "entity_type", "asset_type"),
    "domain": ("domain", "business_domain", "company_domain", "area", "line_of_business", "lob", "function"),
    "description": ("description", "notes", "purpose", "summary", "what_it_does"),
    "owner": ("owner", "owning_team", "team", "org_unit", "business_owner", "owner_org"),
    "hosting": ("hosting", "provider", "cloud", "cloud_provider", "platform", "hosted_on", "location"),
    "status": ("status", "lifecycle", "state"),
    "criticality": ("criticality", "tier", "service_tier", "importance", "business_criticality"),
    "vendor": ("vendor", "supplier", "product_vendor"),
    "out": ("calls", "depends_on", "uses", "connects_to", "integrates_with", "downstream", "sends_to", "talks_to",
            "dependencies", "interfaces_to", "consumes"),
    "in": ("called_by", "upstream", "used_by", "depended_on_by", "receives_from", "consumed_by"),
    "reads": ("reads", "reads_from", "data_read"),
    "writes": ("writes", "writes_to", "data_written", "masters"),
}
TYPE_WORDS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\b(database|db|data ?set|data ?store|data ?asset|table|file|document store|lake|warehouse)\b", re.I), "data_assets"),
    (re.compile(r"\b(person|actor|user|role|customer|employee|team member|persona|stakeholder)\b", re.I), "actors"),
    (re.compile(r"\bcapabilit", re.I), "capabilities"),
    (re.compile(r"\b(process|procedure|workflow)\b", re.I), "processes"),
    (re.compile(r"\bproduct\b", re.I), "products"),
    (re.compile(r"\b(service|platform|infrastructure|infra|middleware|network|runtime|queue|broker|cluster)\b", re.I), "tech_services"),
]
SPLIT = re.compile(r"\s*[;|,]\s*")
HOSTING_WORDS = re.compile(r"\b(aws|azure|gcp|google|on[- ]?prem|saas|external|vendor|cloud)\b", re.I)


class InventoryError(ReadError):
    pass


def _norm(header: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(header or "").strip().lower()).strip("_")


def _rows(text: str) -> Tuple[List[str], List[List[str]]]:
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(text), dialect)
    rows = [row for row in reader if any(cell.strip() for cell in row)]
    if not rows:
        raise InventoryError("the file has no rows")
    return [cell.strip() for cell in rows[0]], [[cell.strip() for cell in row] for row in rows[1:]]


def columns_of(headers: List[str]) -> Tuple[Dict[str, int], List[str]]:
    """Which column plays which part, by its header; the headers that play
    none, to say."""
    found: Dict[str, int] = {}
    unknown: List[str] = []
    for index, header in enumerate(headers):
        key = _norm(header)
        part = next((p for p, names in COLUMNS.items() if key in names), None)
        if part is None or part in found:
            if key:
                unknown.append(header)
            continue
        found[part] = index
    if "name" not in found and "id" not in found:
        raise InventoryError("no name column: the headers are %s; one of name, system, application, title, id or key "
                             "says what a row is" % ", ".join(headers))
    return found, unknown


def _type_of(text: str) -> str:
    for pattern, type_name in TYPE_WORDS:
        if pattern.search(text):
            return type_name
    return "systems"


def sketch_from_inventory(text: str, name: str = "Imported from a spreadsheet") -> Tuple[dict, List[str]]:
    """The sketch a CSV or tab-separated inventory reads as, and the notes."""
    headers, rows = _rows(text)
    found, unknown = columns_of(headers)
    read = _Read()
    read.title = name
    read.source = "a spreadsheet: a row per thing, the type and the connections read off the columns"
    read.group_word = "the domain column as the domain"

    def cell(row: List[str], part: str) -> str:
        index = found.get(part)
        return row[index] if index is not None and index < len(row) else ""

    mids: Dict[str, str] = {}  # by lower-cased name and by id
    taken: Dict[str, int] = {}
    entries: List[Tuple[str, List[str]]] = []
    for number, row in enumerate(rows, 2):
        label = cell(row, "name") or cell(row, "id")
        if not label:
            read.notes.append("row %d has no name; left out" % number)
            continue
        base = re.sub(r"[^A-Z0-9]+", "-", (cell(row, "id") or label).upper()).strip("-") or "X"
        n = taken.get(base, 0) + 1
        taken[base] = n
        mid = base if n == 1 else "%s-%d" % (base, n)
        mids[label.lower()] = mid
        if cell(row, "id"):
            mids[cell(row, "id").lower()] = mid
        mids[mid.lower()] = mid
        domain = cell(row, "domain")
        entry = read.node(mid, domain)
        entry["type"] = _type_of(cell(row, "type"))
        entry["label"] = label
        description = cell(row, "description")
        extras = []
        for part in ("status", "criticality", "owner", "vendor"):
            value = cell(row, part)
            if value:
                extras.append("%s: %s" % (part.replace("_", " "), value))
        if extras:
            description = (description + " " if description else "") + "; ".join(extras) + "."
        entry["description"] = description
        if entry["type"] == "actors":
            entry["kind"] = "Person"
        hosting = cell(row, "hosting")
        if hosting and entry["type"] == "systems":
            entry["external"] = "External" if re.search(r"\b(saas|external|vendor)\b", hosting, re.I) else ""
            if not entry["external"]:
                entry["description"] = (entry["description"] + " " if entry["description"] else "") + "Hosted on %s." % hosting
        entries.append((mid, row))
        if domain:
            read.any_group = True

    def targets(value: str) -> List[str]:
        return [v for v in SPLIT.split(value) if v] if value else []

    missing: Dict[str, int] = {}
    for mid, row in entries:
        for part, forward in (("out", True), ("in", False)):
            for other in targets(cell(row, part)):
                other_mid = mids.get(other.lower())
                if other_mid is None:
                    missing[other] = missing.get(other, 0) + 1
                    continue
                link = (mid, other_mid, "", "") if forward else (other_mid, mid, "", "")
                if link not in read.links:
                    read.links.append(link)
        for part, word in (("reads", "reads"), ("writes", "writes")):
            for other in targets(cell(row, part)):
                other_mid = mids.get(other.lower())
                if other_mid is None:
                    missing[other] = missing.get(other, 0) + 1
                    continue
                if read.nodes[other_mid]["type"] == "systems":
                    read.nodes[other_mid]["type"] = "data_assets"  # what is read or written is data
                read.links.append((mid, other_mid, word, ""))
    for other, n in sorted(missing.items()):
        read.notes.append("%r is named by %d row(s) and is no row of the file; left out" % (other, n))
    if unknown:
        read.notes.append("columns the method has no field for, left out: %s" % ", ".join(unknown))
    if not read.order:
        raise InventoryError("no row with a name: nothing to read as a sketch")
    doc, notes = _document(read, name)
    notes[0] = notes[0].replace("from the Mermaid; the ids are made from the diagram's own",
                                "from the spreadsheet; the ids are made from the id column, else the names")
    return doc, notes
