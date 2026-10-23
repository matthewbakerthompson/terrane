"""An Excel workbook read as the spreadsheet of systems it is.

The inventory most practices keep is an `.xlsx`, not a CSV: a zip of XML
with the strings in `xl/sharedStrings.xml`, a sheet per
`xl/worksheets/sheetN.xml`, each cell holding its column letter and row in
`r="B2"` and its value in `<v>` (a shared-string index when `t="s"`, a
number or a date's serial otherwise) or inline in `<is><t>`; a cell whose
style is a date format holds a serial, and is read as the date it shows,
since a reviewer who types a date gets a number from Excel. This reads
the workbook with the standard library and hands the sheet that holds the
inventory to the spreadsheet reader (`inventory_import`) as the CSV it
would have been: the first sheet whose header row the reader recognizes,
rows above the header (a title, a note) skipped, the other sheets said
and left alone. Everything the CSV reader does with the columns, the type
words and the connections, it does here too.

A workbook written in the method's own vocabulary is read as the records
it holds instead: a sheet named after an entity type, or headed by the
type's id column, is that type's records, each column a field of the type
and the columns it has no field for said once and left alone; a sheet
named `relations`, or headed `relation, from, to`, is the relation rows,
a row the method has no relation for, or that names an id on no sheet,
said and left out; a sheet named `views`, or headed `view_id`, is the
pages, each a row saying what it shows by type or by id and which lines,
a view id alone for a shipped view, or `use` and `with.<name>` for a
shipped view on a subject. A dotted column is a key of a mapping, so a
product on a shape or assembled from parts is a row like any other: its
answers in `parameters.<name>`, what it is assembled on in
`compose.provider`, its parts in one `modules` cell. Nothing is guessed
from type words
or connection columns, since the sheets already say what each row is. It
is the workbook `terrane draw file --excel` and `terrane export excel` write, so a
drawing turned into a workbook turns back into the same drawing.
"""

from __future__ import annotations

import csv
import datetime
import io
import re
import zipfile
from typing import Dict, List, Optional, Sequence, Tuple
from xml.etree import ElementTree

from .compose import COMPOSE_KEY
from .connections import find_kind, kind_of, kinds_for_reading
from .inventory_import import InventoryError, _norm, columns_of, sketch_from_inventory
from .schema import ENTITY_TYPES, RELATION_TYPES

#: The composition a record may carry beside its fields: a shape's answers
#: under `parameters`, the parts added to a shape under `modules`, and a
#: product assembled from parts under `compose`.
COMPOSITION = ("parameters", "modules", COMPOSE_KEY)
PART = re.compile(r"^(\S+?)(?:\s+as\s+(\S+))?(?:\s*\((.*)\))?$")

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
RID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
CELL_REF = re.compile(r"^([A-Z]+)(\d+)$")


class ExcelError(InventoryError):
    pass


def _column(letters: str) -> int:
    index = 0
    for letter in letters:
        index = index * 26 + (ord(letter) - ord("A") + 1)
    return index - 1


def _shared_strings(archive: zipfile.ZipFile, names: set) -> List[str]:
    if "xl/sharedStrings.xml" not in names:
        return []
    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    # A rich-text string is several runs; the text is all of them.
    return ["".join(t.text or "" for t in item.iter(NS + "t")) for item in root.iter(NS + "si")]


#: Excel's built-in number formats that show a date, and the ones that show
#: a time of day as well; a custom format is a date when its code, quoted
#: text and color codes aside, spells a year or a day.
DATE_FORMATS = set(range(14, 23)) | set(range(27, 37)) | set(range(45, 48)) | set(range(50, 59))
TIME_FORMATS = {18, 19, 20, 21, 22, 45, 46, 47}
EPOCH = datetime.date(1899, 12, 30)


def _date_styles(archive: zipfile.ZipFile, names: set) -> List[str]:
    """For each cell style (an `s` index into `cellXfs`), "date", "time"
    or "": a reviewer who types a date into a cell gets a serial number
    with a date format from Excel, and the serial is not the date."""
    if "xl/styles.xml" not in names:
        return []
    root = ElementTree.fromstring(archive.read("xl/styles.xml"))
    custom: Dict[int, str] = {}
    for fmt in root.iter(NS + "numFmt"):
        try:
            custom[int(fmt.get("numFmtId") or "")] = fmt.get("formatCode") or ""
        except ValueError:
            continue
    out: List[str] = []
    xfs = root.find(NS + "cellXfs")
    for xf in (xfs.findall(NS + "xf") if xfs is not None else []):
        try:
            fmt_id = int(xf.get("numFmtId") or "0")
        except ValueError:
            fmt_id = 0
        if fmt_id in custom:
            code = re.sub(r'"[^"]*"|\[[^\]]*\]|\\.', "", custom[fmt_id]).lower()
            if "y" in code or "d" in code:
                out.append("time" if ("h" in code or "s" in code) else "date")
            else:
                out.append("")
        elif fmt_id in TIME_FORMATS:
            out.append("time")
        elif fmt_id in DATE_FORMATS:
            out.append("date")
        else:
            out.append("")
    return out


def _as_date(text: str, style: str) -> Optional[str]:
    """A serial number as the ISO date (and time, for a time format) it
    stands for; None when the text is no serial."""
    try:
        serial = float(text)
    except ValueError:
        return None
    if serial < 1 or serial > 2958465:  # before 1900 or after 9999: no date Excel shows
        return None
    day = EPOCH + datetime.timedelta(days=int(serial))
    if style == "time":
        seconds = int(round((serial - int(serial)) * 86400))
        return "%s %02d:%02d" % (day.isoformat(), seconds // 3600, (seconds % 3600) // 60)
    return day.isoformat()


def _cell_text(cell: ElementTree.Element, shared: List[str], date_styles: Sequence[str] = ()) -> str:
    kind = cell.get("t") or ""
    if kind == "inlineStr":
        return "".join(t.text or "" for t in cell.iter(NS + "t")).strip()
    value = cell.find(NS + "v")
    text = (value.text or "") if value is not None else ""
    if kind == "s":
        try:
            return shared[int(text)].strip()
        except (ValueError, IndexError):
            return ""
    if kind == "b":
        return "Yes" if text.strip() == "1" else "No"
    if kind == "e":
        return ""  # a formula's #N/A or #REF! is no value a reviewer meant
    try:
        style = date_styles[int(cell.get("s") or "0")] if date_styles else ""
    except (ValueError, IndexError):
        style = ""
    if style and not kind:
        shown = _as_date(text.strip(), style)
        if shown is not None:
            return shown
    # A number: an integer written as one, the way a person typed it.
    if re.fullmatch(r"-?\d+\.0+", text.strip()):
        text = text.strip().split(".")[0]
    return text.strip()


def sheets(data: bytes) -> List[Tuple[str, List[List[str]]]]:
    """Every sheet of the workbook: its name and its rows, each a list of
    cell texts with the gaps filled, in the workbook's order."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ExcelError("not an .xlsx: %s" % exc) from exc
    names = set(archive.namelist())
    if "xl/workbook.xml" not in names:
        raise ExcelError("not an Excel workbook: no xl/workbook.xml in the file")
    shared = _shared_strings(archive, names)
    date_styles = _date_styles(archive, names)
    rels: Dict[str, str] = {}
    if "xl/_rels/workbook.xml.rels" in names:
        for rel in ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels")).iter(PKG_REL + "Relationship"):
            rels[rel.get("Id") or ""] = rel.get("Target") or ""
    out: List[Tuple[str, List[List[str]]]] = []
    workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    for n, sheet in enumerate(workbook.iter(NS + "sheet"), 1):
        name = sheet.get("name") or "Sheet%d" % n
        target = rels.get(sheet.get(RID) or "", "worksheets/sheet%d.xml" % n)
        member = target.lstrip("/") if target.startswith("/") else "xl/" + target
        if member not in names:
            continue
        rows: List[List[str]] = []
        for row in ElementTree.fromstring(archive.read(member)).iter(NS + "row"):
            cells: List[str] = []
            for cell in row.findall(NS + "c"):
                m = CELL_REF.match(cell.get("r") or "")
                index = _column(m.group(1)) if m else len(cells)
                while len(cells) < index:
                    cells.append("")
                text = _cell_text(cell, shared, date_styles)
                if len(cells) == index:
                    cells.append(text)
                else:
                    cells[index] = text
            rows.append(cells)
        out.append((name, rows))
    if not out:
        raise ExcelError("no sheet in the workbook")
    return out


def _header_row(rows: List[List[str]]) -> Optional[int]:
    """The index of the first row the spreadsheet reader knows as a header,
    skipping a title or a note above it; None when no row is one."""
    for index, row in enumerate(rows[:20]):
        headers = [c for c in row if c]
        if len(headers) < 2:
            continue
        try:
            found, _unknown = columns_of(row)
        except InventoryError:
            continue
        # A header plays at least two parts: a row of a contents page that
        # happens to say "system" in one cell is not one.
        if len(found) >= 2:
            return index
    return None


def header_index(rows: List[List[str]]) -> Optional[int]:
    """The first row of an export that reads as a header: two cells or more
    with something under it. A title or a note above the table is one cell,
    and is passed over. Unlike `_header_row`, nothing about the words is
    assumed, since an export names its columns its own way."""
    for index, row in enumerate(rows[:20]):
        if sum(1 for c in row if str(c).strip()) >= 2 and any(
                any(str(c).strip() for c in later) for later in rows[index + 1:index + 6]):
            return index
    return None


def sheet_table(data: bytes, sheet: Optional[str] = None
                ) -> Tuple[str, List[str], List[Tuple[int, List[str]]], List[str]]:
    """One sheet of a workbook as a table: the sheet's name, its header, its
    rows each with the row number Excel shows, and every sheet's name. The
    sheet asked for by name, else the first with a header row; an error
    names the sheets when neither is there."""
    found = sheets(data)
    names = [name for name, _rows in found]
    if sheet:
        chosen = [(n, r) for n, r in found if n == sheet]
        if not chosen:
            raise ExcelError("the workbook has no sheet named %r (it has %s)" % (sheet, ", ".join(names)))
    else:
        chosen = [(n, r) for n, r in found if header_index(r) is not None][:1]
        if not chosen:
            raise ExcelError("no sheet of the workbook has a header row (%s)" % ", ".join(names))
    name, rows = chosen[0]
    at = header_index(rows)
    if at is None:
        raise ExcelError("the sheet %r has no header row" % name)
    header = [str(c).strip() for c in rows[at]]
    body = [(at + 2 + i, [str(c).strip() for c in row]) for i, row in enumerate(rows[at + 1:])]
    return name, header, body, names


def grid_text(rows: List[List[str]]) -> str:
    """The rows as the CSV the spreadsheet reader takes."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()


#: A sheet's name, the row its header is on, and its rows from the header down.
Located = Tuple[str, int, List[List[str]]]
Typed = Dict[str, Located]
PARTS = re.compile(r"\s*[;|]\s*")
EDGE = re.compile(r"^(\S+)\s*(?:\((.+)\))?$")


def _column_key(header: str) -> str:
    """A header as a key, the dots kept: `compose.provider` is key
    `provider` of the mapping under `compose`."""
    return ".".join(_norm(part) for part in str(header or "").split("."))


def _pairs(text: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for word in text.split(","):
        if "=" in word:
            key, value = word.split("=", 1)
            if key.strip():
                out[key.strip()] = value.strip()
    return out


def parse_modules(text: str) -> List[dict]:
    """The parts a cell names, as the entries `compose` and `modules` take:
    `id`, `id as alias`, `id (k=v, k=v)`."""
    entries: List[dict] = []
    for word in PARTS.split(text):
        m = PART.match(word.strip()) if word.strip() else None
        if m is None:
            continue
        entry: dict = {"module": m.group(1)}
        if m.group(2):
            entry["as"] = m.group(2)
        if m.group(3) and _pairs(m.group(3)):
            entry["with"] = _pairs(m.group(3))
        entries.append(entry)
    return entries


def _set(record: dict, key: str, text: str) -> None:
    """A dotted key set as the nested mapping it names; a `modules` leaf
    as the parts it lists."""
    parts = key.split(".")
    target = record
    for part in parts[:-1]:
        inner = target.get(part)
        if not isinstance(inner, dict):
            inner = {}
            target[part] = inner
        target = inner
    target[parts[-1]] = parse_modules(text) if parts[-1] == "modules" else text


def typed_sheets(all_sheets: List[Tuple[str, List[List[str]]]]) -> Tuple[Typed, Optional[Located], Optional[Located],
                                                                           Optional[Located], List[str]]:
    """The sheets written in the method's own vocabulary: by entity type,
    the sheet's name, the row its header is on and its rows from the header
    down, for a sheet named after a type whose header holds the type's id
    column, or one whose first header cell is a type's id column; the
    relations sheet, named so or headed `relation, from, to`; the views
    sheet, named so or headed `view_id`; the model sheet, named so and
    headed `key, value`; and the names of the sheets that are none of
    these, a second sheet of one type among them."""
    pks = {et.pk: name for name, et in ENTITY_TYPES.items()}
    typed: Typed = {}
    relations = None
    views = None
    model = None
    others: List[str] = []
    for sheet_name, rows in all_sheets:
        header_at = next((i for i, row in enumerate(rows) if any(c.strip() for c in row)), None)
        if header_at is None:
            others.append(sheet_name)
            continue
        header = [_norm(c) for c in rows[header_at]]
        key = _norm(sheet_name)
        type_name = None
        if key in ENTITY_TYPES and ENTITY_TYPES[key].pk in header:
            type_name = key
        elif header and header[0] in pks:
            type_name = pks[header[0]]
        if type_name is not None:
            if type_name in typed:
                others.append(sheet_name)
            else:
                typed[type_name] = (sheet_name, header_at, rows[header_at:])
        elif relations is None and (key == "relations" or header[:3] == ["relation", "from", "to"]):
            relations = (sheet_name, header_at, rows[header_at:])
        elif views is None and (key == "views" or header[:1] == ["view_id"]):
            views = (sheet_name, header_at, rows[header_at:])
        elif model is None and key == "model" and header[:2] == ["key", "value"]:
            model = (sheet_name, header_at, rows[header_at:])
        else:
            others.append(sheet_name)
    return typed, relations, views, model, others


def _views_from_sheet(located: Located, ids: Dict[str, str], notes: List[str]) -> List[object]:
    """The pages the views sheet names: a row with a view id alone is a
    shipped view by its id, a row with `use` a shipped view on a subject,
    with what the `with.<name>` columns say; any other row is a diagram of
    the records it lists, by type or by id, with the lines it names. An id on no sheet
    and a type the method lacks are said and left out, and a page left
    with nothing to show is left out itself."""
    sheet_name, header_at, rows = located
    keys = [_column_key(c) for c in rows[0]]

    def cell(row: List[str], key: str) -> str:
        index = keys.index(key) if key in keys else -1
        return row[index].strip() if 0 <= index < len(row) else ""

    def parts(text: str) -> List[str]:
        return [p for p in PARTS.split(text) if p] if text else []

    pages: List[object] = []
    for offset, row in enumerate(rows[1:], 2):
        if not any(c.strip() for c in row):
            continue
        view_id = cell(row, "view_id")
        if cell(row, "use"):
            # A shipped view on a subject: what it is used with sits in the
            # `with.<name>` columns.
            bound = {k.split(".", 1)[1]: cell(row, k) for k in keys if k.startswith("with.") and cell(row, k)}
            pages.append({"use": cell(row, "use"), "with": bound} if bound else {"use": cell(row, "use")})
            continue
        if not view_id:
            notes.append("sheet %r: row %d has no view_id and no use; left out" % (sheet_name, header_at + offset))
            continue
        if not any(cell(row, k) for k in keys if k != "view_id"):
            pages.append(view_id)
            continue
        include: List[dict] = []
        listed = parts(cell(row, "types"))
        unknown = [t for t in listed if t not in ENTITY_TYPES]
        if unknown:
            notes.append("sheet %r: %s: no type called %s; left out" % (
                sheet_name, view_id, ", ".join(repr(t) for t in unknown)))
        by_type: Dict[str, List[str]] = {}
        missing: List[str] = []
        for entity_id in parts(cell(row, "nodes")):
            type_name = ids.get(entity_id)
            if type_name is None:
                missing.append(entity_id)
            elif entity_id not in by_type.setdefault(type_name, []):
                by_type[type_name].append(entity_id)
        if missing:
            notes.append("sheet %r: %s: on no sheet, left out: %s" % (
                sheet_name, view_id, ", ".join(repr(i) for i in missing)))
        for type_name in ENTITY_TYPES:
            if type_name in listed:
                include.append({"type": type_name})
            elif type_name in by_type:
                include.append({"type": type_name, "where": {"id_in": by_type[type_name]}})
        if not include:
            notes.append("sheet %r: %s shows nothing on the sheets; left out" % (sheet_name, view_id))
            continue
        edges: List[dict] = []
        for word in parts(cell(row, "edges")):
            m = EDGE.match(word)
            if m is None:
                continue
            edge = {"via": m.group(1)}
            if m.group(2):
                edge["label"] = m.group(2).strip()
            edges.append(edge)
        shown = sum(len(v) for v in by_type.values())
        view: dict = {
            "view_id": view_id, "title": cell(row, "title") or view_id, "kind": cell(row, "kind") or "diagram",
            "layout": cell(row, "layout") or "LR",
            "description": cell(row, "description") or "Read from the views sheet of a workbook.",
            "node_label": "name", "renderers": ["mermaid"],
            "scope": {"include": include}, "edges": edges, "style": {"color_by": "type"},
            "limits": {"max_nodes": max(60, shown)},
        }
        if cell(row, "group_by"):
            levels = parts(cell(row, "group_by"))
            view["group_by"] = levels if len(levels) > 1 else levels[0]
        pages.append(view)
    return pages


def _apply_kind(record: dict, word: str, kinds: dict, sheet_name: str, notes: List[str]) -> bool:
    """The kind column of the interfaces sheet: a word that names a kind
    sets the style and the protocol that define it when the row's own say
    another kind, and proposes the rest too (authentication, frequency,
    direction, patterns) for a row that had neither; a row whose fields
    already say that kind is left as it is, and a word naming no kind is
    said and left. True when the row changed."""
    found = find_kind(word, kinds)
    if found is None:
        notes.append("sheet %r: %s: no connection kind called %r; the kinds are %s; left as written" % (
            sheet_name, record.get("interface_id"), word, ", ".join(sorted(kinds)) or "none"))
        return False
    if kind_of(record, kinds) == found.connection_id:
        return False
    if not record.get("integration_style") and not record.get("protocol"):
        for key, value in found.defaults().items():
            record.setdefault(key, value)
    else:
        record["integration_style"] = found.integration_style
        record["protocol"] = found.protocols[0]
    return True


def _sketch_from_typed(typed: Typed, relations: Optional[Located], views_sheet: Optional[Located],
                       model_sheet: Optional[Located], others: List[str], name: str) -> Tuple[dict, List[str]]:
    """The sketch the typed sheets hold: the records as written, the
    relation rows whose ends are on the sheets, the pages the views sheet
    names, else one view of everything, and the sketch's own words about
    itself from the model sheet, the file's name standing in for its own
    when the sheet is missing."""
    model: dict = {}
    if model_sheet is not None:
        for row in model_sheet[2][1:]:
            if len(row) > 1 and row[0].strip() and row[1].strip():
                model[row[0].strip()] = row[1].strip()
    model.setdefault("name", name)
    doc: dict = {"model": model}
    kinds = kinds_for_reading()
    notes: List[str] = []
    ids: Dict[str, str] = {}  # every id read, to its type
    any_domain = False
    for type_name in ENTITY_TYPES:
        if type_name not in typed:
            continue
        sheet_name, header_at, rows = typed[type_name]
        entity_type = ENTITY_TYPES[type_name]
        fields = {f.name for f in entity_type.fields} | {entity_type.pk} | set(COMPOSITION)
        if type_name == "interfaces":
            fields.add("kind")  # the one word for a connection's style and protocol
        keys = [_column_key(c) for c in rows[0]]
        unknown = [c for c, k in zip(rows[0], keys) if k and k.split(".")[0] not in fields]
        if unknown:
            notes.append("sheet %r: columns a %s has no field for, left alone: %s" % (
                sheet_name, entity_type.label, ", ".join(repr(c) for c in unknown)))
        records: List[dict] = []
        kinded = 0
        for offset, row in enumerate(rows[1:], 2):
            if not any(c.strip() for c in row):
                continue
            record: dict = {}
            for k, v in zip(keys, row):
                if v.strip() and k.split(".")[0] in fields:
                    _set(record, k, v.strip())
            word = str(record.pop("kind", "") or "") if type_name == "interfaces" else ""
            entity_id = record.get(entity_type.pk)
            if not entity_id:
                notes.append("sheet %r: row %d has no %s; left out" % (sheet_name, header_at + offset, entity_type.pk))
                continue
            if entity_id in ids:
                notes.append("sheet %r: row %d says %s twice; the second left out" % (
                    sheet_name, header_at + offset, entity_id))
                continue
            ids[entity_id] = type_name
            any_domain = any_domain or bool(record.get("company_domain"))
            if word and _apply_kind(record, word, kinds, sheet_name, notes):
                kinded += 1
            records.append(record)
        if kinded:
            notes.append("sheet %r: %d interface(s) given their kind from the kind column" % (sheet_name, kinded))
        if records:
            doc[type_name] = records
    if not ids:
        raise ExcelError("the sheets in the method's own vocabulary (%s) hold no row with an id" % ", ".join(
            repr(s) for s, _h, _r in typed.values()))

    by_relation: Dict[str, List[dict]] = {}
    total = 0
    if relations is not None:
        sheet_name, header_at, rows = relations
        keys = [_norm(c) for c in rows[0]]

        def cell(row: List[str], key: str) -> str:
            index = keys.index(key) if key in keys else -1
            return row[index].strip() if 0 <= index < len(row) else ""

        unknown_relations: Dict[str, int] = {}
        dangling: Dict[str, int] = {}
        for offset, row in enumerate(rows[1:], 2):
            if not any(c.strip() for c in row):
                continue
            spec = RELATION_TYPES.get(_norm(cell(row, "relation")))
            if spec is None:
                word = cell(row, "relation") or "(blank)"
                unknown_relations[word] = unknown_relations.get(word, 0) + 1
                continue
            left, right = cell(row, "from"), cell(row, "to")
            if not left or not right:
                notes.append("sheet %r: row %d names one end only; left out" % (sheet_name, header_at + offset))
                continue
            missing = [end for end in (left, right) if end not in ids]
            if missing:
                for end in missing:
                    dangling[end] = dangling.get(end, 0) + 1
                continue
            if ids[left] != spec.left or ids[right] != spec.right:
                notes.append("sheet %r: row %d joins %s to %s, and %s joins %s to %s; left out" % (
                    sheet_name, header_at + offset, ids[left].replace("_", " "), ids[right].replace("_", " "),
                    spec.name, spec.left.replace("_", " "), spec.right.replace("_", " ")))
                continue
            record = {spec.left_column: left, spec.right_column: right}
            if spec.qualifier:
                # The tool's own sheet says the qualifier's name in one column
                # and its value in the next; a person's sheet names the column
                # after the qualifier.
                value = cell(row, "value") or cell(row, spec.qualifier)
                if value:
                    record[spec.qualifier] = value
            bucket = by_relation.setdefault(spec.name, [])
            if record not in bucket:
                bucket.append(record)
                total += 1
        for word, n in sorted(unknown_relations.items()):
            notes.append("sheet %r: %r is no relation of the method; %d row(s) left out" % (sheet_name, word, n))
        for end, n in sorted(dangling.items()):
            notes.append("sheet %r: %r is named by %d row(s) and is on no sheet; left out" % (sheet_name, end, n))
    if by_relation:
        doc["relations"] = {r: by_relation[r] for r in RELATION_TYPES if r in by_relation}

    present = [t for t in ENTITY_TYPES if t in doc]
    # An interface is a line between two systems, not a box of its own: the
    # sketch's interfaces draw through `via: interfaces`, and a scope that
    # took every type present put the Visio sample's one interface on the
    # sheet as a cyan node beside the systems it joins.
    boxes = [t for t in present if t != "interfaces"]
    edges: List[dict] = []
    if "interfaces" in doc:
        edges.append({"via": "interfaces", "label": "protocol"})
    for relation_name in doc.get("relations", {}):
        edge = {"via": relation_name}
        if RELATION_TYPES[relation_name].qualifier:
            edge["label"] = RELATION_TYPES[relation_name].qualifier
        edges.append(edge)
    # A field that names a record on another sheet is a line too, the way
    # an arrow to a policy or a parent capability is when drawn.
    pk_fields = {ENTITY_TYPES[t].pk for t in present} | {"parent_capability_id", "source_of_truth"}
    for type_name in boxes:
        own = ENTITY_TYPES[type_name].pk
        for record in doc[type_name]:
            for key in record:
                if key != own and key in pk_fields and {"via": key} not in edges:
                    edges.append({"via": key})
    view: dict = {
        "view_id": "imported", "title": name, "kind": "diagram", "layout": "LR",
        "description": "Read from a workbook in the method's own vocabulary: a sheet per type of record, "
                       "the relations on a sheet of their own.",
        "node_label": "name", "renderers": ["mermaid"],
        "scope": {"include": [{"type": t} for t in boxes]},
        "edges": edges,
        "style": {"color_by": "type"},
        "limits": {"max_nodes": max(60, len(ids))},
    }
    if any_domain:
        view["group_by"] = "company_domain"
    pages = _views_from_sheet(views_sheet, ids, notes) if views_sheet is not None else []
    # The pages the workbook names, else one picture of everything.
    doc["views"] = pages or [view]
    counts = ", ".join("%d %s" % (len(doc[t]), t.replace("_", " ")) for t in present)
    read_sheets = [typed[t][0] for t in typed] + [s[0] for s in (relations, views_sheet, model_sheet) if s is not None]
    notes.insert(0, "read %s and %d relation row(s) from %d sheet(s) in the method's own vocabulary (%s)%s" % (
        counts, total, len(read_sheets), ", ".join(repr(s) for s in read_sheets),
        "; left alone: %s" % ", ".join(repr(s) for s in others) if others else ""))
    return doc, notes


def sketch_from_excel(data: bytes, name: str = "Imported from a workbook") -> Tuple[dict, List[str]]:
    """The sketch an Excel workbook reads as, and the notes: the records of
    a workbook in the method's own vocabulary, else the inventory sheet
    read by its headers and the sheets left alone."""
    all_sheets = sheets(data)
    typed, relations, views_sheet, model_sheet, others = typed_sheets(all_sheets)
    if typed:
        return _sketch_from_typed(typed, relations, views_sheet, model_sheet, others, name)
    chosen = None
    for sheet_name, rows in all_sheets:
        header = _header_row(rows)
        if header is not None:
            chosen = (sheet_name, rows[header:])
            break
    if chosen is None:
        raise ExcelError("no sheet has a header row the spreadsheet reader knows (a name or application column "
                         "with a type, domain or connection column beside it); the sheets are %s"
                         % ", ".join(repr(s) for s, _ in all_sheets))
    sheet_name, rows = chosen
    doc, notes = sketch_from_inventory(grid_text(rows), name=name)
    others = [s for s, _ in all_sheets if s != sheet_name]
    notes.insert(1, "sheet %r of the workbook read%s" % (
        sheet_name, "; left alone: %s" % ", ".join(repr(s) for s in others) if others else ""))
    return doc, notes
