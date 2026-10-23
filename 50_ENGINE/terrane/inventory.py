"""An inventory read through a mapping, for `terrane import csv --map`.

A real inventory -- a ServiceNow export, a portfolio tool's, a spreadsheet --
has its own column names, its own values (`Tier 1`, `Retired - pending`) and
its own ids (`APP001`, a sys_id). Until this, it was shaped into metamodel v2
CSVs by hand or by a script nobody kept. A mapping says the same thing once,
in a file that sits beside the inventory and is reviewed like the rest of the
model: which column is which field, which of its values is which of ours, and
how its codes become ids. The format is in AAC-15; a sample is in
`60_SOURCES/inventory/`.

What it does not do is guess.

* A value the mapping does not place and the metamodel does not list, a
  reference to nothing the model or the import holds, a required field left
  empty: each holds its row back and says so, grouped by field and value, so
  the answer is one line in the mapping and a second run. A held row is not
  written at all, rather than written without the field, because the second
  run would find it already in the model and leave the fix out.
* Two rows that make the same id and say different things are a conflict, and
  neither is written: which of them is the real one is the guess. Two that say
  the same thing are one record, which is how a file of applications also
  yields the departments that own them.
* A reference is resolved by an exact id, name or inventory code, ignoring
  case and spacing only. A name two records share resolves to neither.
* A mapping that is wrong in itself -- a field the type does not have, a value
  mapped to something the metamodel does not list, a column the file does not
  have -- is refused whole before anything is read, with every problem in one
  message, rather than discovered row by row.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Sequence, Set, Tuple

from .loader import read_data_file
from .model import Model
from .schema import ENTITY_TYPES, EntityType, field_map

ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*(-[A-Z0-9]+)+$")
_PREFIX = re.compile(r"^[A-Z][A-Z0-9]*-?$")

#: The keys a type's entry may have. Anything else is a typo, and a typo in a
#: mapping is a column silently not read.
TYPE_KEYS = ("file", "sheet", "code", "id", "columns", "ignore", "values", "defaults")
ID_FROM = ("name", "code")

#: Made by expanding a shape, never brought in; the plain importer drops them
#: for the same reason (`importer.DERIVED_FIELDS`).
_DERIVED = ("archetype", "archetype_instance")

#: How many rows a report line names before it counts the rest.
_NAMED = 5


class MappingError(ValueError):
    """The mapping cannot be applied as written; nothing has been read or written."""


class TypeMap(NamedTuple):
    entity_type: EntityType
    file: str
    code: Optional[str]
    prefix: Optional[str]
    id_from: Optional[str]
    columns: Dict[str, List[str]]
    ignore: List[str]
    #: Field to {inventory value, case and spacing folded: model value}. A
    #: model value of "" leaves the field empty, which is a decision too.
    values: Dict[str, Dict[str, str]]
    defaults: Dict[str, str]
    #: The sheet of a workbook the rows are on; None for a CSV, or for the
    #: first sheet with a header row.
    sheet: Optional[str] = None


class Mapped(NamedTuple):
    rows: Dict[str, List[dict]]
    #: The inventory file each type was read from, for the written file's header.
    origins: Dict[str, str]
    skipped: List[str]
    held: List[str]
    conflicts: List[str]
    #: How many rows the held lines hold back, for a count beside them.
    held_rows: int = 0


def fold(value: object) -> str:
    """Case and spacing set aside, and nothing else: `Tier  1` is `tier 1`."""
    return " ".join(str(value).split()).casefold()


def slug(value: str) -> str:
    """`Policy Administration` as `POLICY-ADMINISTRATION`; accents dropped,
    anything not a letter or a digit a separator."""
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Z0-9]+", "-", text.upper()).strip("-")


def _scalar(value: object, where: str, problems: List[str]) -> Optional[str]:
    """A mapping's key or value as text, or a problem when YAML has already
    turned it into something else."""
    if isinstance(value, bool):
        problems.append(
            "%s: %s is read by YAML as %s; quote it (\"Yes\", \"No\", \"On\", \"Off\")"
            % (where, value, "true" if value else "false"))
        return None
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        problems.append("%s: expected a single value" % where)
        return None
    return str(value).strip()


def _named_list(items: Sequence[str]) -> str:
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return "%s or %s" % (", ".join(items[:-1]), items[-1])


#: What YAML 1.1 reads as something other than text. A mapping is mostly
#: other systems' values, and those are exactly the words that do it: an
#: unquoted `Yes:` was the boolean true to PyYAML and the text "Yes" to the
#: bundled reader, so the same mapping was refused locally and accepted in CI.
_BOOLEAN = {"yes", "no", "on", "off", "true", "false"}
_NULL = {"~", "null"}
_NUMBER = re.compile(
    r"^[-+]?(?:0b[01_]+|0x[0-9a-fA-F_]+|[0-9][0-9_]*(?::[0-5]?[0-9])*(?:\.[0-9_]*)?(?:[eE][-+]?[0-9]+)?"
    r"|\.[0-9_]+(?:[eE][-+]?[0-9]+)?|\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN))$")
#: The one kind of number both readers give back as the digits written.
_PLAIN_INTEGER = re.compile(r"^-?(?:0|[1-9][0-9]*)$")
_QUOTED = re.compile(r"\"(?:[^\"\\]|\\.)*\"|'(?:[^']|'')*'")
_FLOW = re.compile(r"[\[\]{},]|:(?=\s|$)")


def _unmarked(text: str) -> str:
    """A scalar without the `- ` that makes it a list item."""
    text = text.strip()
    while text.startswith("-") and text[1:2] in ("", " "):
        text = text[1:].strip()
    return text


def _unquoted_words(text: str) -> List[str]:
    """Every unquoted word in a mapping that a YAML reader may take for a
    boolean, a null or a number, read off the text so that both readers
    refuse the same file: a mapping that means one thing to one parser and
    another to the next is not one to apply."""
    from .yamlish import _strip_comment

    problems: List[str] = []
    block_indent: Optional[int] = None
    for number, line in enumerate(text.splitlines(), start=1):
        indent = len(line) - len(line.lstrip())
        if block_indent is not None:
            if not line.strip() or indent > block_indent:
                continue
            block_indent = None
        code = _QUOTED.sub('"q"', _strip_comment(line)).strip()
        if not code:
            continue
        if re.search(r"(?:^|:\s|-\s)[|>][-+0-9]*$", code):
            block_indent = indent
        parts = re.split(r":(?=\s|$)", code, maxsplit=1)
        if len(parts) == 2 and not _unmarked(code).startswith(("[", "{")):
            key, value = _unmarked(parts[0]), _unmarked(parts[1])
        else:
            key, value = "", _unmarked(code)
        words = [(key, True)] if key else []
        if value.startswith(("[", "{")):
            words.extend((piece.strip(), False) for piece in _FLOW.split(value) if piece.strip())
        elif value and not re.match(r"^[|>][-+0-9]*$", value):
            words.append((value, False))
        for word, is_key in words:
            if word.lower() in _BOOLEAN:
                problems.append("line %d: %s is a boolean to one YAML reader and text to another; "
                                "quote it (\"%s\")" % (number, word, word))
            elif word.lower() in _NULL and is_key:
                problems.append("line %d: %s is read as nothing; quote it (\"%s\")" % (number, word, word))
            elif _NUMBER.match(word) and not _PLAIN_INTEGER.match(word):
                problems.append("line %d: %s may be read as a number and come back as other digits; "
                                "quote it (\"%s\")" % (number, word, word))
    return problems


def load_mapping(path: Path) -> Dict[str, TypeMap]:
    """The mapping file, checked against the metamodel; raises `MappingError`
    naming every problem at once."""
    path = Path(path)
    if not path.is_file():
        raise MappingError("no mapping file at %s" % path)
    unquoted = _unquoted_words(path.read_text(encoding="utf-8-sig"))
    if unquoted:
        # Read before the structure is checked: what the rest would say
        # depends on which reader read it.
        raise MappingError("%s cannot be applied:\n%s" % (
            path.name, "\n".join("  - %s" % p for p in unquoted)))
    return parse_mapping(read_data_file(path), path.name)


def parse_mapping(data: object, label: str = "the mapping") -> Dict[str, TypeMap]:
    """A mapping given as data, checked as a file's is: the app's Sources
    builds one from what a person chose, and the file it keeps is this
    written out."""
    if not isinstance(data, dict):
        raise MappingError("%s: a mapping is a list of kinds of record, each with its columns" % label)
    problems: List[str] = []
    out: Dict[str, TypeMap] = {}
    for key, spec in data.items():
        key = str(key)
        if key == "description":
            continue
        entity_type = ENTITY_TYPES.get(key)
        if entity_type is None:
            problems.append("%s is not a kind of record the model holds" % key)
            continue
        if not isinstance(spec, dict):
            problems.append("%s: expected file, id, columns, values and the like under it" % key)
            continue
        type_map = _type_map(entity_type, spec, problems)
        if type_map is not None:
            out[key] = type_map
    if not out and not problems:
        problems.append("it names no kind of record to import")
    if problems:
        raise MappingError("%s cannot be applied:\n%s" % (
            label, "\n".join("  - %s" % p for p in problems)))
    return out


def _type_map(entity_type: EntityType, spec: dict, problems: List[str]) -> Optional[TypeMap]:
    name = entity_type.name
    fields = field_map(entity_type)
    pk = entity_type.pk
    before = len(problems)
    for key in spec:
        if key not in TYPE_KEYS:
            problems.append("%s: %s is not something a mapping says (%s)"
                            % (name, key, ", ".join(TYPE_KEYS)))

    file_name = _scalar(spec.get("file", "%s.csv" % name), "%s file" % name, problems) or ""
    sheet = _scalar(spec.get("sheet"), "%s sheet" % name, problems) or None
    if sheet and not file_name.lower().endswith(".xlsx"):
        problems.append("%s: a sheet is named, and %s is not a workbook" % (name, file_name))
    code = _scalar(spec.get("code"), "%s code" % name, problems) or None

    columns: Dict[str, List[str]] = {}
    claimed: Dict[str, str] = {}
    raw_columns = spec.get("columns") or {}
    if not isinstance(raw_columns, dict):
        problems.append("%s columns: expected `inventory column: field` lines" % name)
        raw_columns = {}
    for column, targets in raw_columns.items():
        column = _scalar(column, "%s columns" % name, problems)
        if not column:
            continue
        targets = targets if isinstance(targets, list) else [targets]
        kept: List[str] = []
        for target in targets:
            target = _scalar(target, "%s columns %s" % (name, column), problems)
            if not target:
                continue
            if target in _DERIVED:
                problems.append("%s columns %s: %s is made by a shape, not imported" % (name, column, target))
            elif target != pk and target not in fields:
                problems.append("%s columns %s: %s is not a field of a %s" % (name, column, target, entity_type.label))
            elif target in claimed:
                problems.append("%s: %s is filled from both %s and %s" % (name, target, claimed[target], column))
            else:
                claimed[target] = column
                kept.append(target)
        if kept:
            columns[column] = kept

    ignore: List[str] = []
    raw_ignore = spec.get("ignore") or []
    for column in raw_ignore if isinstance(raw_ignore, list) else [raw_ignore]:
        column = _scalar(column, "%s ignore" % name, problems)
        if not column:
            continue
        if column in columns or column == code:
            problems.append("%s: %s is both read and ignored" % (name, column))
        ignore.append(column)

    prefix: Optional[str] = None
    id_from: Optional[str] = None
    rule = spec.get("id")
    if rule is not None:
        if not isinstance(rule, dict):
            problems.append("%s id: expected `{prefix: ..., from: name}`" % name)
        else:
            for key in rule:
                if key not in ("prefix", "from"):
                    problems.append("%s id: %s is not part of an id rule (prefix, from)" % (name, key))
            prefix = _scalar(rule.get("prefix"), "%s id prefix" % name, problems) or ""
            id_from = _scalar(rule.get("from", "name"), "%s id from" % name, problems) or "name"
            if not _PREFIX.match(prefix):
                problems.append("%s id: prefix %r is not upper case letters and digits, like SYS-" % (name, prefix))
            prefix = prefix if prefix.endswith("-") else prefix + "-"
            if id_from not in ID_FROM:
                problems.append("%s id: from is name or code, not %s" % (name, id_from))
            elif id_from == "code" and not code:
                problems.append("%s id: from code, and no code column is named" % name)
            elif id_from == "name" and "name" not in claimed:
                problems.append("%s id: from name, and no column is mapped to name" % name)
            if pk in claimed:
                problems.append("%s: %s is both a column (%s) and an id rule; say it once"
                                % (name, pk, claimed[pk]))
    elif pk not in claimed:
        problems.append("%s: no way to make a %s; add `id: {prefix: ..., from: name}` or map a column to it"
                        % (name, pk))

    values: Dict[str, Dict[str, str]] = {}
    raw_values = spec.get("values") or {}
    if not isinstance(raw_values, dict):
        problems.append("%s values: expected a list of fields, each with `inventory value: model value` lines" % name)
        raw_values = {}
    for field_name, table in raw_values.items():
        field_name = str(field_name)
        field = fields.get(field_name)
        if field is None or field_name == pk:
            problems.append("%s values: %s is not a field of a %s whose values can be mapped"
                            % (name, field_name, entity_type.label))
            continue
        if not isinstance(table, dict):
            problems.append("%s values %s: expected `inventory value: model value` lines" % (name, field_name))
            continue
        folded: Dict[str, str] = {}
        for theirs, ours in table.items():
            where = "%s values %s" % (name, field_name)
            theirs = _scalar(theirs, where, problems)
            ours = _scalar(ours, "%s %s" % (where, theirs), problems)
            if theirs is None or ours is None:
                continue
            if ours and field.enum and ours not in field.enum:
                problems.append("%s: %r is mapped to %r, which is not %s"
                                % (where, theirs, ours, _named_list(field.enum)))
                continue
            if ours and field.ref and not ID_PATTERN.match(ours):
                problems.append("%s: %r is mapped to %r, which is not an id" % (where, theirs, ours))
                continue
            key = fold(theirs)
            if key in folded and folded[key] != ours:
                problems.append("%s: %r is mapped twice, to %r and %r"
                                % (where, theirs, folded[key], ours))
                continue
            folded[key] = ours
        values[field_name] = folded

    defaults: Dict[str, str] = {}
    raw_defaults = spec.get("defaults") or {}
    if not isinstance(raw_defaults, dict):
        problems.append("%s defaults: expected `field: value` lines" % name)
        raw_defaults = {}
    for field_name, value in raw_defaults.items():
        field_name = str(field_name)
        field = fields.get(field_name)
        if field is None or field_name == pk or field_name in _DERIVED:
            problems.append("%s defaults: %s is not a field of a %s" % (name, field_name, entity_type.label))
            continue
        value = _scalar(value, "%s defaults %s" % (name, field_name), problems)
        if not value:
            continue
        if field.enum and value not in field.enum:
            problems.append("%s defaults %s: %r is not %s" % (name, field_name, value, _named_list(field.enum)))
            continue
        if field.ref and not ID_PATTERN.match(value):
            problems.append("%s defaults %s: %r is not an id" % (name, field_name, value))
            continue
        defaults[field_name] = value

    if len(problems) > before:
        return None
    return TypeMap(entity_type, file_name, code, prefix, id_from, columns, ignore, values, defaults, sheet)


# ---------------------------------------------------------------------------
# Applying it.
# ---------------------------------------------------------------------------


class _Row(NamedTuple):
    type_name: str
    entity_id: str
    labels: List[str]  # how the report names it: its code, or its file and line
    raw: Dict[str, str]  # field to the inventory's own value, unmapped
    code: str


def _read(path: Path, sheet: Optional[str] = None) -> Tuple[List[str], List[Tuple[int, Dict[str, str]]]]:
    """A file's header and its rows, each with the line or row number a
    person would look for it at. A workbook is read a sheet at a time."""
    if path.suffix.lower() == ".xlsx":
        from .excel_import import ExcelError, sheet_table

        try:
            _name, header, body, _names = sheet_table(path.read_bytes(), sheet)
        except ExcelError as exc:
            raise MappingError("%s: %s" % (path.name, exc)) from exc
        rows = [(number, {h: (values[i] if i < len(values) else "") for i, h in enumerate(header) if h})
                for number, values in body if any(v for v in values)]
        return header, rows
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = [h.strip() for h in next(reader, [])]
        rows = []
        for number, values in enumerate(reader, start=2):
            if not any(v.strip() for v in values):
                continue
            rows.append((number, {h: (values[i].strip() if i < len(values) else "")
                                  for i, h in enumerate(header) if h}))
    return header, rows


def _rows_named(labels: Sequence[str]) -> str:
    labels = sorted(set(labels), key=lambda s: (len(s), s))
    if len(labels) > _NAMED:
        return "%s and %d more" % (", ".join(labels[:_NAMED]), len(labels) - _NAMED)
    return ", ".join(labels)


def apply(mapping: Dict[str, TypeMap], source: Path, model: Model,
          only: Optional[Sequence[str]] = None) -> Mapped:
    """Every row of every file the mapping names, as a metamodel v2 record,
    or reported as held, skipped or in conflict."""
    source = Path(source)
    wanted = {k: v for k, v in mapping.items() if not only or k in only}

    # Keyed by file and sheet: two kinds may read one sheet, or two sheets
    # of one workbook.
    files: Dict[Tuple[str, Optional[str]], Tuple[List[str], List[Tuple[int, Dict[str, str]]]]] = {}
    problems: List[str] = []
    for type_name, type_map in wanted.items():
        key = (type_map.file, type_map.sheet)
        if key not in files:
            path = source / type_map.file
            if not path.is_file():
                problems.append("%s: %s is not in %s" % (type_name, type_map.file, source))
                continue
            files[key] = _read(path, type_map.sheet)
        header = files[key][0]
        missing = [c for c in list(type_map.columns) + ([type_map.code] if type_map.code else [])
                   if c not in header]
        if missing:
            problems.append("%s: %s has no %s column%s (it has %s)" % (
                type_name, type_map.file, _named_list(["%r" % c for c in missing]),
                "s" if len(missing) > 1 else "", ", ".join(h for h in header if h)))
    if problems:
        raise MappingError("the mapping and the inventory do not agree:\n%s"
                           % "\n".join("  - %s" % p for p in problems))

    skipped: List[str] = []
    for (file_name, sheet), (header, _rows) in files.items():
        read = set()
        for type_map in wanted.values():
            if (type_map.file, type_map.sheet) == (file_name, sheet):
                read.update(type_map.columns)
                read.update(type_map.ignore)
                if type_map.code:
                    read.add(type_map.code)
        left = [h for h in header if h and h not in read]
        if left:
            skipped.append("%s: %s %s in neither columns nor ignore, so %s left out" % (
                file_name, ", ".join(left), "is" if len(left) == 1 else "are",
                "it was" if len(left) == 1 else "they were"))

    # Ids first: a reference is resolved against what the whole import holds.
    rows: List[_Row] = []
    for type_name, type_map in wanted.items():
        entity_type = type_map.entity_type
        nameless = 0
        for number, values in files[(type_map.file, type_map.sheet)][1]:
            raw: Dict[str, str] = {}
            for column, targets in type_map.columns.items():
                for target in targets:
                    raw[target] = values.get(column, "")
            code = values.get(type_map.code, "") if type_map.code else ""
            if type_map.prefix is not None:
                basis = code if type_map.id_from == "code" else raw.get("name", "")
                tail = slug(basis)
                entity_id = type_map.prefix + tail if tail else ""
            else:
                entity_id = raw.pop(entity_type.pk, "")
            if not entity_id:
                nameless += 1
                continue
            rows.append(_Row(type_name, entity_id, [code or "%s line %d" % (type_map.file, number)],
                             raw, code))
        if nameless and type_map.prefix is None:
            skipped.append("%s: %d row(s) with no %s" % (type_map.file, nameless, entity_type.pk))
        elif nameless:
            skipped.append("%s: %d row(s) with no %s to make a %s from" % (
                type_map.file, nameless, type_map.id_from, entity_type.pk))

    conflicts: List[str] = []
    excluded: Set[str] = set()
    by_id: Dict[Tuple[str, str], List[_Row]] = {}
    for row in rows:
        by_id.setdefault((row.type_name, row.entity_id), []).append(row)
    merged: List[_Row] = []
    for (type_name, entity_id), group in by_id.items():
        distinct = {tuple(sorted(r.raw.items())) + (r.code,) for r in group}
        labels = [label for r in group for label in r.labels]
        if len(distinct) > 1:
            excluded.add(entity_id)
            conflicts.append(
                "%s %s: %d rows make this id and say different things (%s); neither is imported"
                % (ENTITY_TYPES[type_name].label, entity_id, len(group), _rows_named(labels)))
            continue
        merged.append(group[0]._replace(labels=labels))

    # A later export of the same inventory, after an application was renamed
    # there or its id changed here, makes another id for something the model
    # holds. Its code is the sure key: the row is the model's record, it is
    # not made a second time, and what names it finds the record.
    known: List[Tuple[_Row, List[str]]] = []
    for row in list(merged):
        if not row.code or "cmdb_ci_sys_id" not in field_map(ENTITY_TYPES[row.type_name]):
            continue
        pk = ENTITY_TYPES[row.type_name].pk
        held_by = sorted(str(r[pk]) for r in model.all_of(row.type_name)
                         if fold(r.get("cmdb_ci_sys_id") or "") == fold(row.code) and str(r[pk]) != row.entity_id)
        if held_by:
            merged.remove(row)
            known.append((row, held_by))
            conflicts.append("%s %s: %s is already %s in the model, so it is not made a second time" % (
                ENTITY_TYPES[row.type_name].label, row.entity_id, row.code, " and ".join(held_by)))

    index = _index(wanted, merged, model, known)

    # A row held back takes the rows that name it with it, so this runs
    # until nothing more is held; a chain is as long as the references are deep.
    held_ids: Set[str] = set()
    while True:
        out, reasons = _map_rows(wanted, merged, index, excluded, excluded | held_ids)
        newly = {r.entity_id for r in merged
                 if r.entity_id not in excluded and (r.type_name, r.entity_id) not in out} - held_ids
        if not newly:
            break
        held_ids |= newly

    held: List[str] = []
    for (type_name, field_name, text), labels in sorted(reasons.items()):
        held.append("%s %s: %s (%s)" % (
            ENTITY_TYPES[type_name].label, field_name, text, _rows_named(labels)))

    result: Dict[str, List[dict]] = {}
    for (type_name, _entity_id), record in out.items():
        result.setdefault(type_name, []).append(record)
    origins = {k: v.file for k, v in wanted.items()}
    return Mapped(result, origins, skipped, held, conflicts, len(held_ids))


def _index(wanted: Dict[str, TypeMap], rows: Sequence[_Row], model: Model,
           known: Sequence[Tuple[_Row, List[str]]] = ()) -> Dict[str, Dict[str, Set[str]]]:
    """Per kind of record, every key a reference may use -- id, name, an
    inventory code -- to the ids it could mean. A row the model already
    holds under another id is known by its name and code as that id."""
    index: Dict[str, Dict[str, Set[str]]] = {}

    def add(type_name: str, key: object, entity_id: str) -> None:
        if key in (None, ""):
            return
        index.setdefault(type_name, {}).setdefault(fold(key), set()).add(entity_id)

    for type_name, entity_type in ENTITY_TYPES.items():
        for record in model.all_of(type_name):
            entity_id = str(record[entity_type.pk])
            add(type_name, entity_id, entity_id)
            add(type_name, record.get("name"), entity_id)
            add(type_name, record.get("cmdb_ci_sys_id"), entity_id)
    for row in rows:
        add(row.type_name, row.entity_id, row.entity_id)
        add(row.type_name, row.raw.get("name"), row.entity_id)
        add(row.type_name, row.code, row.entity_id)
    for row, ids in known:
        for entity_id in ids:
            add(row.type_name, row.raw.get("name"), entity_id)
            add(row.type_name, row.code, entity_id)
    return index


def _map_rows(wanted, rows, index, excluded, unavailable):
    """The rows not `excluded` as records, and the reasons for the rest. A
    reference to an id in `unavailable` -- in conflict, or held -- holds
    the row that makes it."""
    out: Dict[Tuple[str, str], dict] = {}
    reasons: Dict[Tuple[str, str, str], List[str]] = {}

    def hold(row: _Row, field_name: str, text: str) -> None:
        reasons.setdefault((row.type_name, field_name, text), []).extend(row.labels)

    for row in rows:
        if row.entity_id in excluded:
            continue
        type_map: TypeMap = wanted[row.type_name]
        entity_type = type_map.entity_type
        fields = field_map(entity_type)
        record: Dict[str, str] = {entity_type.pk: row.entity_id}
        held: Set[str] = set()
        if type_map.prefix is None and not ID_PATTERN.match(row.entity_id):
            hold(row, entity_type.pk, "%r is not an id in the model's form; give the type an id rule"
                 % row.entity_id)
            continue
        raw = dict(row.raw)
        if row.code and "cmdb_ci_sys_id" in fields and "cmdb_ci_sys_id" not in raw:
            # The inventory's own id, kept where the drift report looks for it.
            raw["cmdb_ci_sys_id"] = row.code
        for field_name in list(raw) + [f for f in type_map.defaults if f not in raw]:
            field = fields[field_name]
            theirs = raw.get(field_name, "")
            value = theirs
            table = type_map.values.get(field_name)
            mapped = bool(theirs) and table is not None and fold(theirs) in table
            if mapped:
                value = table[fold(theirs)]
            if not value:
                value = type_map.defaults.get(field_name, "")
            if not value:
                continue
            if field.enum:
                canonical = next((e for e in field.enum if fold(e) == fold(value)), None)
                if canonical is None:
                    hold(row, field_name, "%r is not %s, and the mapping does not say which it is"
                         % (value, _named_list(field.enum)))
                    held.add(field_name)
                    continue
                value = canonical
            elif field.ref:
                target = ENTITY_TYPES[field.ref]
                ids = index.get(field.ref, {}).get(fold(value), set())
                live = ids - unavailable
                if len(live) == 1:
                    value = next(iter(live))
                else:
                    if len(live) > 1:
                        text = "%r names more than one %s (%s)" % (value, target.label, ", ".join(sorted(live)))
                    elif ids:
                        text = "%r is a %s this import holds back" % (value, target.label)
                    else:
                        text = "%r is no %s in the model or in this import" % (value, target.label)
                    hold(row, field_name, text)
                    held.add(field_name)
                    continue
            record[field_name] = value
        for field in entity_type.fields:
            # A field already reported for its value is not reported empty too.
            if field.required and not record.get(field.name) and field.name not in held:
                hold(row, field.name, "empty, and the mapping gives no default")
                held.add(field.name)
        if not held:
            out[(row.type_name, row.entity_id)] = record
    return out, reasons
