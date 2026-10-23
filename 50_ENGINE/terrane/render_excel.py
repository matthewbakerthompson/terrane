"""The estate as an Excel workbook, written with the standard library.

The CSV export is what a tool reads; the workbook is what gets sent to a
person. `terrane export excel` writes one `.xlsx`: a contents sheet that says
what the model is and what each sheet holds, a sheet per entity type with
the columns the CSV export has (the systems first, so the spreadsheet
reader, handed the workbook back, finds the inventory on the first sheet
it knows), and a relations sheet with every row of every relation. The
header row is bold and frozen, the columns are sized to their text, and
the zip is written with one fixed timestamp and the parts in one order, so
the same model is the same bytes and the file sits under `70_ARTIFACTS/`
with the other exports.

A cell is text, since the inventory's values are names, ids and words;
nothing here is a number a sheet should add up.
"""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from xml.sax.saxutils import escape

from .compose import COMPOSE_KEY
from .connections import kind_of, load_connections
from .exports import _clean, _flatten
from .library import LibraryError
from .model import Model
from .schema import ENTITY_TYPES, RELATION_TYPES
from .shipped import shipped_root


def _kinds(root: Path) -> dict:
    """The connection kinds the interfaces sheet names, the estate's own
    after the shipped ones; none when the library cannot be read, since
    the workbook is not the place to say what is wrong with it."""
    try:
        return load_connections(root)
    except LibraryError:
        return {}

STAMP = (1980, 1, 1, 0, 0, 0)
NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
RNS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
#: What a sheet may be called: thirty-one characters, none of `[]:*?/\`.
BAD = re.compile(r"[\[\]:*?/\\]")
Sheet = Tuple[str, List[List[str]]]


def _column(index: int) -> str:
    letters = ""
    index += 1
    while index:
        index, rest = divmod(index - 1, 26)
        letters = chr(65 + rest) + letters
    return letters


def sheet_name(text: str) -> str:
    return BAD.sub("_", text)[:31] or "Sheet"


class _Strings:
    def __init__(self) -> None:
        self.order: List[str] = []
        self.index: Dict[str, int] = {}

    def __call__(self, text: str) -> int:
        if text not in self.index:
            self.index[text] = len(self.order)
            self.order.append(text)
        return self.index[text]


def _sheet_xml(rows: Sequence[Sequence[str]], strings: _Strings) -> str:
    widths: List[int] = []
    for row in rows:
        for i, text in enumerate(row):
            while len(widths) <= i:
                widths.append(0)
            widths[i] = max(widths[i], min(60, max(len(line) for line in str(text).split("\n")) if text else 0))
    out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
           '<worksheet xmlns="%s" xmlns:r="%s">' % (NS, RNS),
           '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" '
           'state="frozen"/></sheetView></sheetViews>']
    if widths:
        out.append("<cols>%s</cols>" % "".join(
            '<col min="%d" max="%d" width="%s" customWidth="1"/>' % (i + 1, i + 1, "%.1f" % (max(8, w) + 2))
            for i, w in enumerate(widths)))
    out.append("<sheetData>")
    for r, row in enumerate(rows, 1):
        cells = []
        for c, text in enumerate(row):
            text = str(text or "")
            if not text:
                continue
            style = ' s="1"' if r == 1 else ""
            cells.append('<c r="%s%d" t="s"%s><v>%d</v></c>' % (_column(c), r, style, strings(text)))
        out.append('<row r="%d">%s</row>' % (r, "".join(cells)))
    out.append("</sheetData></worksheet>")
    return "".join(out)


def workbook_bytes(sheets: Sequence[Sheet]) -> bytes:
    """A workbook of the sheets given, each a name and its rows of text."""
    strings = _Strings()
    names: List[str] = []
    parts: List[Tuple[str, str]] = []
    for n, (name, rows) in enumerate(sheets, 1):
        clean = sheet_name(name)
        while clean in names:
            clean = sheet_name(clean[:28] + " %d" % n)
        names.append(clean)
        parts.append(("xl/worksheets/sheet%d.xml" % n, _sheet_xml(rows, strings)))
    workbook = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
                '<workbook xmlns="%s" xmlns:r="%s"><sheets>' % (NS, RNS)]
    rels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
    types = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
             '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
             '<Default Extension="xml" ContentType="application/xml"/>',
             '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.'
             'spreadsheetml.sheet.main+xml"/>',
             '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.'
             'spreadsheetml.styles+xml"/>',
             '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.'
             'spreadsheetml.sharedStrings+xml"/>']
    for n, name in enumerate(names, 1):
        workbook.append('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (escape(name, {'"': "&quot;"}), n, n))
        rels.append('<Relationship Id="rId%d" Type="%s/worksheet" Target="worksheets/sheet%d.xml"/>' % (n, RNS, n))
        types.append('<Override PartName="/xl/worksheets/sheet%d.xml" ContentType="application/vnd.openxmlformats-'
                     'officedocument.spreadsheetml.worksheet+xml"/>' % n)
    workbook.append("</sheets></workbook>")
    rels.append('<Relationship Id="rId%d" Type="%s/styles" Target="styles.xml"/>' % (len(names) + 1, RNS))
    rels.append('<Relationship Id="rId%d" Type="%s/sharedStrings" Target="sharedStrings.xml"/>' % (len(names) + 2, RNS))
    rels.append("</Relationships>")
    types.append("</Types>")
    shared = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
              '<sst xmlns="%s" count="%d" uniqueCount="%d">' % (NS, len(strings.order), len(strings.order))]
    for text in strings.order:
        # A string that starts or ends with a space keeps it; the attribute says so.
        space = ' xml:space="preserve"' if text != text.strip() else ""
        shared.append("<si><t%s>%s</t></si>" % (space, escape(text)))
    shared.append("</sst>")
    styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<styleSheet xmlns="%s"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
              '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
              '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/>'
              '</fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
              '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
              '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
              '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>'
              '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>' % NS)
    root_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 '<Relationship Id="rId1" Type="%s/officeDocument" Target="xl/workbook.xml"/></Relationships>' % RNS)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, text in [("[Content_Types].xml", "".join(types)), ("_rels/.rels", root_rels),
                           ("xl/workbook.xml", "".join(workbook)), ("xl/_rels/workbook.xml.rels", "".join(rels)),
                           ("xl/styles.xml", styles), ("xl/sharedStrings.xml", "".join(shared))] + parts:
            info = zipfile.ZipInfo(name, date_time=STAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, text)
    return buffer.getvalue()


def estate_sheets(model: Model) -> List[Sheet]:
    """The workbook's sheets: a contents page, the systems, every other
    type that has records, and the relations."""
    name = str(model.config.get("name") or "Architecture Model")
    typed: List[Sheet] = []
    kinds = _kinds(model.root)
    order = ["systems"] + [t for t in ENTITY_TYPES if t != "systems"]
    for type_name in order:
        entity_type = ENTITY_TYPES[type_name]
        records = model.all_of(type_name)
        if not records:
            continue
        columns = [entity_type.pk] + [f.name for f in entity_type.fields if f.name != entity_type.pk]
        if type_name == "interfaces":
            # Each connection's kind, read off its style and protocol: the
            # one word a reviewer changes to change both.
            columns.append("kind")
        rows: List[List[str]] = [list(columns)]
        for record in sorted(records, key=lambda r: str(r[entity_type.pk])):
            clean = _clean(record)
            if type_name == "interfaces":
                clean["kind"] = kind_of(record, kinds) or ""
            rows.append([_flatten(clean.get(c)) for c in columns])
        typed.append((type_name, rows))
    relation_rows: List[List[str]] = [["relation", "from", "to", "qualifier", "value"]]
    for relation, spec in RELATION_TYPES.items():
        for row in sorted(model.relation_rows(relation), key=lambda r: (str(r[spec.left_column]), str(r[spec.right_column]))):
            relation_rows.append([relation, _flatten(row.get(spec.left_column)), _flatten(row.get(spec.right_column)),
                                  spec.qualifier or "", _flatten(row.get(spec.qualifier)) if spec.qualifier else ""])
    contents: List[List[str]] = [["Sheet", "Holds", "Rows"],
                                 ["Contents", "%s, exported by architecture-as-code; edit the model, not the workbook." % name, ""]]
    for type_name, rows in typed:
        contents.append([type_name, ENTITY_TYPES[type_name].label, str(len(rows) - 1)])
    contents.append(["relations", "every row of every relation: the relation, its two ends, and the qualifier where it has one",
                     str(len(relation_rows) - 1)])
    return [("Contents", contents)] + typed + [("relations", relation_rows)]


#: What `compose` may say in a cell: the provider, the parts and a title.
#: Blocks, bindings, patterns and relations written out by hand are not
#: cells, and are said and left out rather than flattened into something
#: that would read back as a string.
COMPOSE_CELLS = ("provider", "modules", "title")


def module_text(entries) -> Optional[str]:
    """The parts of a product as one cell: `id`, `id as alias` for a part
    used under another name, `id (k=v, k=v)` for what it is bound with;
    None when an entry is not a part written that way."""
    words: List[str] = []
    for entry in entries:
        if isinstance(entry, str):
            words.append(entry)
            continue
        if not isinstance(entry, dict) or not entry.get("module") or set(entry) - {"module", "as", "with"}:
            return None
        word = str(entry["module"])
        if entry.get("as") and entry["as"] != entry["module"]:
            word += " as %s" % entry["as"]
        bound = entry.get("with") or {}
        if bound:
            if not isinstance(bound, dict) or any(isinstance(v, (dict, list)) for v in bound.values()):
                return None
            word += " (%s)" % ", ".join("%s=%s" % (k, v) for k, v in bound.items())
        words.append(word)
    return ";".join(words)


def record_cells(record: dict, where: str, notes: Optional[List[str]] = None) -> Dict[str, str]:
    """A record as its cells, by column: a field a column; a mapping, the
    answers under `parameters` or a product's `compose`, a dotted column
    per key (`parameters.account`, `compose.provider`); the parts under
    `modules` one cell; a list of words one cell with `;` between. What is
    not a cell is said in `notes` and left out, so nothing reads back as
    a string that was a structure."""
    cells: Dict[str, str] = {}

    def say(path: str, why: str = "") -> None:
        if notes is not None:
            notes.append("%s: %s is not a cell%s; left out" % (where, path, why))

    def put(column: str, value) -> None:
        if value is None or value == "" or value == [] or value == {}:
            return
        leaf = column.rsplit(".", 1)[-1]
        if leaf == "modules" and isinstance(value, list):
            text = module_text(value)
            if text is None:
                say(column, " (a part is `module`, `as` and `with`)")
            else:
                cells[column] = text
            return
        if isinstance(value, dict):
            for key, inner in value.items():
                if column == COMPOSE_KEY and key not in COMPOSE_CELLS:
                    say("%s.%s" % (column, key))
                    continue
                put("%s.%s" % (column, str(key)), inner)
            return
        if isinstance(value, list):
            if any(isinstance(v, (dict, list)) for v in value):
                say(column)
                return
            cells[column] = ";".join(str(v) for v in value)
            return
        cells[column] = _flatten(value)

    for key, value in record.items():
        if str(key).startswith("_"):
            continue
        put(str(key), value)
    return cells


#: A page of the sketch as a row: what it shows, by type or by id, and
#: which lines; or the shipped view it uses, with what in `with.<name>`
#: columns. Styling and limits are the method's defaults either way, and a
#: row with a view id alone names a shipped view.
VIEW_COLUMNS = ["view_id", "use", "title", "kind", "layout", "group_by", "description", "types", "nodes", "edges"]


def view_rows(views) -> List[List[str]]:
    """The sketch's views as the rows of the `views` sheet."""
    found: List[Dict[str, str]] = []
    for view in views or []:
        if isinstance(view, str):
            found.append({"view_id": view})
            continue
        if not isinstance(view, dict):
            continue
        if view.get("use"):
            cells = {"use": str(view["use"])}
            for key, value in (view.get("with") or {}).items():
                cells["with.%s" % key] = _flatten(value)
            found.append(cells)
            continue
        if not view.get("view_id"):
            continue
        types: List[str] = []
        nodes: List[str] = []
        for include in ((view.get("scope") or {}).get("include") or []):
            if not isinstance(include, dict) or not include.get("type"):
                continue
            where = include.get("where") if isinstance(include.get("where"), dict) else {}
            id_in = where.get("id_in") if where else None
            if id_in:
                nodes.extend(str(i) for i in id_in)
            else:
                # A filter other than the ids is not a cell; the page shows the type.
                types.append(str(include["type"]))
        edges: List[str] = []
        for edge in view.get("edges") or []:
            if isinstance(edge, dict) and edge.get("via"):
                edges.append("%s (%s)" % (edge["via"], edge["label"]) if edge.get("label") else str(edge["via"]))
        grouped = view.get("group_by") or ""
        found.append({"view_id": str(view["view_id"]), "title": str(view.get("title") or ""),
                      "kind": str(view.get("kind") or "diagram"), "layout": str(view.get("layout") or ""),
                      # Several levels of grouping are a `;` list, as every list cell is.
                      "group_by": ";".join(str(g) for g in grouped) if isinstance(grouped, (list, tuple)) else str(grouped),
                      "description": str(view.get("description") or ""),
                      "types": ";".join(types), "nodes": ";".join(nodes), "edges": ";".join(edges)})
    extra: List[str] = []
    for cells in found:
        for key in cells:
            if key not in VIEW_COLUMNS and key not in extra:
                extra.append(key)
    columns = VIEW_COLUMNS + extra
    return [list(columns)] + [[cells.get(c, "") for c in columns] for cells in found]


def sketch_sheets(doc: dict, notes: Optional[List[str]] = None, root: Optional[Path] = None) -> List[Sheet]:
    """A sketch's own records as sheets: what a drawing said, and nothing
    the quick door filled in to draw it. A sheet per type present, the id
    first and then every column any record of the type has, in the order
    they first appear (`record_cells`); the relations as the estate's
    workbook has them; the views. What is not a cell is said in `notes`;
    `root` is the estate whose connection kinds the interfaces sheet goes
    by, the shipped ones alone when the sketch is nobody's estate."""
    typed: List[Sheet] = []
    kinds = _kinds(root if root is not None else shipped_root())
    order = ["systems"] + [t for t in ENTITY_TYPES if t != "systems"]
    for type_name in order:
        records = [r for r in (doc.get(type_name) or []) if isinstance(r, dict)]
        if not records:
            continue
        pk = ENTITY_TYPES[type_name].pk
        columns: List[str] = [pk]
        cells_of: List[Tuple[str, Dict[str, str]]] = []
        for record in sorted(records, key=lambda r: str(r.get(pk, ""))):
            cells = record_cells(record, "sheet %r: %s" % (type_name, record.get(pk, "")), notes)
            if type_name == "interfaces":
                kind = kind_of(record, kinds)
                if kind:
                    cells["kind"] = kind
            for column in cells:
                if column not in columns:
                    columns.append(column)
            cells_of.append((str(record.get(pk, "")), cells))
        rows: List[List[str]] = [list(columns)]
        for _entity_id, cells in cells_of:
            rows.append([cells.get(c, "") for c in columns])
        typed.append((type_name, rows))
    relation_rows: List[List[str]] = [["relation", "from", "to", "qualifier", "value"]]
    for relation, rows in (doc.get("relations") or {}).items():
        spec = RELATION_TYPES.get(relation)
        if spec is None:
            continue
        for row in rows:
            relation_rows.append([relation, _flatten(row.get(spec.left_column)), _flatten(row.get(spec.right_column)),
                                  spec.qualifier or "", _flatten(row.get(spec.qualifier)) if spec.qualifier else ""])
    views = view_rows(doc.get("views"))
    name = str((doc.get("model") or {}).get("name") or "A sketch")
    # The sketch's own words about itself, its name first: read back, they
    # title the pictures as the sketch did, not as the file is called.
    model_rows: List[List[str]] = [["key", "value"]]
    for key, value in (doc.get("model") or {}).items():
        if isinstance(value, (dict, list)):
            if notes is not None:
                notes.append("sheet 'model': %s is not a cell; left out" % key)
            continue
        model_rows.append([str(key), _flatten(value)])
    contents: List[List[str]] = [["Sheet", "Holds", "Rows"],
                                 ["Contents", "%s: what the drawing said, as records; nothing filled in to draw it." % name, ""],
                                 ["model", "the sketch's own words about itself, its name first", str(len(model_rows) - 1)]]
    for type_name, rows in typed:
        contents.append([type_name, ENTITY_TYPES[type_name].label, str(len(rows) - 1)])
    if len(relation_rows) > 1:
        contents.append(["relations", "every connection the drawing had that the method has a relation for",
                         str(len(relation_rows) - 1)])
    if len(views) > 1:
        contents.append(["views", "the pages: what each shows, by type or by id, and which lines; a row with a view id "
                                  "alone names a shipped view", str(len(views) - 1)])
    out: List[Sheet] = [("Contents", contents), ("model", model_rows)] + typed
    if len(relation_rows) > 1:
        out.append(("relations", relation_rows))
    if len(views) > 1:
        out.append(("views", views))
    return out


def change_sheets(d) -> List[Sheet]:
    """What changed between two revisions (`terrane.diff.Diff`) as sheets: what
    was added, what was removed, each field that changed with its value
    before and after, the relation rows added and removed, the views, the
    shapes and the parts; a sheet only where there is something to say,
    and a contents page that says so. The change log a governance board
    is sent, read off the model's own terms rather than off a git diff."""
    sheets_: List[Sheet] = []
    contents: List[List[str]] = [["Sheet", "Holds", "Rows"],
                                 ["Contents", "What changed from %s to %s, by architecture-as-code." % (d.since, d.until), ""]]

    def sheet(name: str, holds: str, rows: List[List[str]]) -> None:
        if len(rows) > 1:
            sheets_.append((name, rows))
            contents.append([name, holds, str(len(rows) - 1)])

    sheet("added", "every record added, by type", [["type", "id", "name"]] + [[t, i, n] for t, i, n in d.added])
    sheet("removed", "every record removed, by type", [["type", "id", "name"]] + [[t, i, n] for t, i, n in d.removed])
    sheet("changed", "every field that changed, with its value before and after",
          [["type", "id", "name", "field", "before", "after"]]
          + [[t, i, n, c.field, c.before, c.after] for t, i, n, changes in d.changed for c in changes])
    rows: List[List[str]] = [["change", "relation", "from", "to", "qualifier", "value"]]
    for word, bucket in (("added", d.relations_added), ("removed", d.relations_removed)):
        for relation, rel_rows in bucket.items():
            spec = RELATION_TYPES.get(relation)
            for row in rel_rows:
                if spec is not None:
                    rows.append([word, relation, _flatten(row.get(spec.left_column)), _flatten(row.get(spec.right_column)),
                                 spec.qualifier or "", _flatten(row.get(spec.qualifier)) if spec.qualifier else ""])
                else:
                    ends = list(row.values())
                    rows.append([word, relation, _flatten(ends[0] if ends else ""), _flatten(ends[1] if len(ends) > 1 else ""), "", ""])
    sheet("relations", "every relation row added or removed", rows)
    rows = [["change", "view", "title or field", "before", "after"]]
    rows += [["added", v, title, "", ""] for v, title in d.views_added]
    rows += [["removed", v, title, "", ""] for v, title in d.views_removed]
    rows += [["changed", v, c.field, c.before, c.after] for v, _title, changes in d.views_changed for c in changes]
    sheet("views", "the views added, removed and changed", rows)
    rows = [["change", "what", "id", "before", "after"]]
    rows += [["changed", "shape", i, before, after] for i, before, after in d.shapes_changed]
    rows += [["added", "part", p, "", ""] for p in d.parts_added]
    rows += [["removed", "part", p, "", ""] for p in d.parts_removed]
    sheet("library", "the shapes whose version moved and the parts added or removed", rows)
    if not sheets_:
        contents.append(["", "nothing changed", "0"])
    return [("Contents", contents)] + sheets_


def export_changes(d, out_path: Path) -> Path:
    """Write what changed as one workbook at `out_path`."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(workbook_bytes(change_sheets(d)))
    return out_path


def export_excel(model: Model, out_path: Path) -> Path:
    """Write the estate as one workbook at `out_path`."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(workbook_bytes(estate_sheets(model)))
    return out_path
