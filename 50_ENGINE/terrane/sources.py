"""Sources: an export from another tool, brought into the model or held
against it, from the app's Settings.

Two kinds, kept apart because they answer different questions. A source that
**brings in** has its rows written as records through a mapping: which column
is which field, which of its words are the model's (AAC-15). A source that
**compares** is held against the model and what differs is listed, and
nothing is written either way: a CMDB export is this kind (AAC-06).

The mapping engine (`inventory.py`) does the work, the same one `terrane
import csv --map` runs. What this adds is what a person needs around it in
the app:

* an upload read into a table, a CSV or a sheet of an `.xlsx`;
* a suggestion of which column is which field, read off the column names,
  for the person to confirm: a suggestion is shown as one and changed in a
  click, and a value is never guessed (a word with no match holds its rows
  back, as it does on the command line);
* the words that need a match, field by field, each with how many rows say
  it;
* a preview of everything bringing it in would write -- the records, the rows
  held back and why, what is already in the model and left alone, and what
  the checks would newly say -- with nothing written;
* a source kept as a folder under `60_SOURCES`: the export, its mapping as a
  file the command line reads too, and a note of when it last came in.
"""

from __future__ import annotations

import copy
import csv
import datetime
import io
import json
import re
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple

from . import inventory, validate
from .excel_import import ExcelError, sheet_table
from .inventory import MappingError, fold, parse_mapping, slug
from .loader import read_data_file
from .schema import ENTITY_TYPES, field_map

SOURCES = "60_SOURCES"
MAPPING = "mapping.yaml"
NOTE = "source.yaml"

#: What an export brings in. Records a shape makes, and plans and decisions,
#: are authored in the model rather than exported from somewhere else.
KINDS = ("systems", "interfaces", "org_units", "data_assets", "tech_services", "actors",
         "capabilities", "processes", "controls", "policies")

#: Fields that hold a list, written as one by the importer (`LIST_FIELDS`).
_LIST_FIELDS = ("tags", "patterns")

#: How an export usually names a field, beyond the field's own name. Read
#: case and spacing aside. A suggestion only: the Columns step shows it and a
#: person changes it.
_SAID: Dict[str, Tuple[str, ...]] = {
    "name": ("application name", "application", "app name", "system name", "system", "title",
             "display name", "service name", "unit name", "department"),
    "description": ("summary", "short description", "purpose", "details"),
    "status": ("lifecycle status", "lifecycle", "lifecycle stage", "operational status", "state",
               "install status"),
    "criticality": ("business criticality", "importance"),
    "owner_org_id": ("owner", "owning department", "owning team", "owned by", "business unit",
                     "managed by group", "owning unit"),
    "hosting": ("hosted", "hosting model", "deployment"),
    "cloud_provider": ("cloud", "cloud provider"),
    "provider": ("vendor", "supplier", "manufacturer"),
    "environment": ("env",),
    "source_system_id": ("source", "source application", "source system", "from application"),
    "target_system_id": ("target", "target application", "target system", "to application"),
    "protocol": ("method", "transport"),
    "frequency": ("schedule",),
}

#: How an export names its own id for a row, which is kept for matching and
#: never made the model's id.
_CODES = ("id", "app id", "application id", "sys id", "ci id", "code", "number", "asset id",
          "app code", "interface id", "item id")


class SourceError(ValueError):
    """The upload or the source cannot be read as asked."""


class Table(NamedTuple):
    file: str
    sheet: Optional[str]
    sheets: List[str]
    header: List[str]
    rows: List[Dict[str, str]]


# ---------------------------------------------------------------------------
# Reading an upload.
# ---------------------------------------------------------------------------
def _decode(data: bytes) -> str:
    """A CSV's text: UTF-8 with or without its mark, else the Windows code
    page Excel saves a CSV in on most machines."""
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def read_table(name: str, data: bytes, sheet: Optional[str] = None) -> Table:
    """An upload as a table: its header and its rows, empty rows left out."""
    suffix = Path(name).suffix.lower()
    if suffix == ".xlsx":
        try:
            chosen, header, body, names = sheet_table(data, sheet)
        except ExcelError as exc:
            raise SourceError("%s: %s" % (name, exc)) from exc
        rows = [{h: (values[i] if i < len(values) else "") for i, h in enumerate(header) if h}
                for _number, values in body if any(values)]
        return Table(name, chosen, names, [h for h in header if h], rows)
    if suffix != ".csv":
        raise SourceError("%s: a source is a .csv or an .xlsx file" % name)
    reader = csv.reader(io.StringIO(_decode(data)))
    header = [h.strip() for h in next(reader, [])]
    if sum(1 for h in header if h) < 2:
        raise SourceError("%s: the first line is not a header of two columns or more" % name)
    rows = []
    for values in reader:
        if not any(v.strip() for v in values):
            continue
        rows.append({h: (values[i].strip() if i < len(values) else "") for i, h in enumerate(header) if h})
    return Table(name, None, [], [h for h in header if h], rows)


def utf8_csv(data: bytes) -> bytes:
    """A CSV as the mapping engine reads it, UTF-8; any other file as it came."""
    return _decode(data).encode("utf-8")


def columns_of(table: Table) -> List[dict]:
    """Each column with what it holds: its first few different values, and
    how many rows fill it."""
    out = []
    for column in table.header:
        seen: "OrderedDict[str, int]" = OrderedDict()
        for row in table.rows:
            value = row.get(column, "")
            if value:
                seen[value] = seen.get(value, 0) + 1
        out.append({"column": column, "samples": list(seen)[:3], "distinct": len(seen),
                    "filled": sum(seen.values()),
                    # Enough to say which need a match; a column of free text
                    # (names, descriptions) is not matched word by word anyway.
                    "values": [[v, n] for v, n in list(seen.items())[:200]]})
    return out


# ---------------------------------------------------------------------------
# A suggestion, for a person to confirm.
# ---------------------------------------------------------------------------
def _said(text: str) -> str:
    return fold(re.sub(r"[_\-]+", " ", text))


def _target(header: str, kind: str, claimed: set) -> Optional[str]:
    """The field a column's name suggests for a record of `kind`, or None."""
    entity_type = ENTITY_TYPES[kind]
    said = _said(header)
    fields = field_map(entity_type)
    candidates = [entity_type.pk] + [f for f in fields if f not in ("archetype", "archetype_instance")]
    for name in candidates:
        own = _said(name)
        bare = _said(name[:-3]) if name.endswith("_id") else own
        if said in (own, bare) and name not in claimed:
            return name
    for name, words in _SAID.items():
        if name in fields and said in words and name not in claimed:
            return name
    # A column named for the kind is its name: "Interface Name" in an
    # integration list, "Control Title" in a control register.
    label = _said(entity_type.label)
    if said in (label + " name", label + " title") and "name" not in claimed:
        return "name"
    return None


def suggest(table: Table, model, kind: Optional[str] = None) -> dict:
    """Which kind of record each row is, which column is which field, which
    column is the export's own id, and how a row's id is made. Read off the
    column names alone; the person confirms each. Given a kind, the columns
    are read for that kind alone."""
    asked = kind if kind in KINDS else None
    best = None
    for candidate in ([asked] if asked else KINDS):
        claimed: set = set()
        columns: Dict[str, List[str]] = {}
        for header in table.header:
            target = _target(header, candidate, claimed)
            if target:
                claimed.add(target)
                columns[header] = [target]
        required = [f.name for f in ENTITY_TYPES[candidate].fields if f.required]
        score = (len(columns) + sum(2 for f in required if f in claimed), -KINDS.index(candidate))
        # Guessing the kind needs a name column; a kind the person chose is
        # read whatever its columns say.
        if (asked or "name" in claimed) and (best is None or score > best[0]):
            best = (score, candidate, columns)
    kind, columns = (best[1], best[2]) if best else ("systems", {})
    pk = ENTITY_TYPES[kind].pk
    code = next((h for h in table.header if h not in columns and _said(h) in _CODES), None)
    return {"kind": kind, "columns": columns, "code": code, "prefix": id_prefix(model, kind),
            "idFrom": "name" if any("name" in t for t in columns.values()) else ("code" if code else "name"),
            "pkMapped": any(pk in t for t in columns.values())}


def id_prefix(model, kind: str) -> str:
    """The prefix the model's ids of this kind already use, so imported
    records read like the rest: SYS- for systems in most estates."""
    entity_type = ENTITY_TYPES[kind]
    counts: Dict[str, int] = {}
    for record in model.all_of(kind):
        head = str(record.get(entity_type.pk) or "").split("-", 1)[0]
        if head:
            counts[head] = counts.get(head, 0) + 1
    if counts:
        return max(sorted(counts), key=lambda k: counts[k]) + "-"
    words = re.findall(r"[a-z]+", entity_type.label.lower())
    return ("".join(w[0] for w in words) if len(words) > 1 else words[0][:3]).upper() + "-"


def kind_fields(kind: str) -> List[dict]:
    """What the Columns step offers for a kind: each field with its words,
    whether it is required, and what it points at."""
    entity_type = ENTITY_TYPES[kind]
    out = [{"name": entity_type.pk, "required": False, "enum": None, "ref": None, "pk": True}]
    for field in entity_type.fields:
        if field.name in ("archetype", "archetype_instance"):
            continue
        out.append({"name": field.name, "required": field.required, "enum": list(field.enum or []) or None,
                    "ref": field.ref, "pk": False})
    return out


# ---------------------------------------------------------------------------
# The words a field needs matched, and the names a reference needs found.
# ---------------------------------------------------------------------------
def _names_index(model, kind: str) -> Dict[str, str]:
    entity_type = ENTITY_TYPES[kind]
    index: Dict[str, str] = {}
    for record in model.all_of(kind):
        entity_id = str(record.get(entity_type.pk) or "")
        for key in (entity_id, record.get("name"), record.get("cmdb_ci_sys_id")):
            if key:
                index.setdefault(fold(key), entity_id)
    return index


def words_needed(table: Table, kind: str, columns: Dict[str, List[str]], model) -> dict:
    """Field by field, the export's words for a field with a fixed list of
    the model's words, each with how many rows say it and the model's word
    it already is, if any; and for a field that points at a record, which of
    the export's names the model holds and which it does not."""
    fields = field_map(ENTITY_TYPES[kind])
    words, refs = [], []
    for column, targets in columns.items():
        counts: "OrderedDict[str, int]" = OrderedDict()
        for row in table.rows:
            value = row.get(column, "")
            if value:
                counts[value] = counts.get(value, 0) + 1
        for target in targets:
            field = fields.get(target)
            if field is None:
                continue
            if field.enum:
                by_fold = {fold(e): e for e in field.enum}
                words.append({"field": target, "column": column, "enum": list(field.enum),
                              "words": [{"word": w, "rows": n, "same": by_fold.get(fold(w), "")}
                                        for w, n in counts.items()]})
            elif field.ref and field.ref in ENTITY_TYPES:
                index = _names_index(model, field.ref)
                found = [w for w in counts if fold(w) in index]
                refs.append({"field": target, "column": column, "kind": field.ref,
                             "found": len(found), "missing": [w for w in counts if fold(w) not in index]})
    return {"words": words, "refs": refs}


# ---------------------------------------------------------------------------
# The mapping, as data and as the file kept beside the export.
# ---------------------------------------------------------------------------
def build_mapping(table: Table, kind: str, columns: Dict[str, List[str]], code: Optional[str] = None,
                  values: Optional[Dict[str, Dict[str, str]]] = None,
                  defaults: Optional[Dict[str, str]] = None, prefix: Optional[str] = None,
                  units_from: Optional[str] = None, description: str = "") -> dict:
    """What a person chose, as a mapping the engine checks and applies.
    `units_from` names the column whose names become org units as well, the
    way the sample makes its departments."""
    if kind not in ENTITY_TYPES:
        raise SourceError("%s is not a kind of record the model holds" % kind)
    entity_type = ENTITY_TYPES[kind]
    mapped = {c: [t for t in ts if t] for c, ts in (columns or {}).items() if c in table.header and any(ts)}
    spec: "OrderedDict[str, object]" = OrderedDict()
    spec["file"] = table.file
    if table.sheet:
        spec["sheet"] = table.sheet
    if code and code in table.header and code not in mapped:
        spec["code"] = code
    if not any(entity_type.pk in ts for ts in mapped.values()):
        named = any("name" in ts for ts in mapped.values())
        spec["id"] = OrderedDict([("prefix", prefix or "%s-" % entity_type.label.split()[0][:3].upper()),
                                  ("from", "name" if named or not spec.get("code") else "code")])
    spec["columns"] = OrderedDict((c, ts[0] if len(ts) == 1 else ts) for c, ts in mapped.items())
    ignore = [h for h in table.header if h not in mapped and h != spec.get("code")]
    if ignore:
        spec["ignore"] = ignore
    fields = field_map(entity_type)
    kept_values: "OrderedDict[str, Dict[str, str]]" = OrderedDict()
    for field_name, table_of in (values or {}).items():
        field = fields.get(field_name)
        lines = OrderedDict((w, m) for w, m in table_of.items()
                            if m is not None and not (field and field.enum and m and fold(w) == fold(m)))
        if lines:
            kept_values[field_name] = lines
    if kept_values:
        spec["values"] = kept_values
    kept_defaults = OrderedDict((f, v) for f, v in (defaults or {}).items() if v)
    if kept_defaults:
        spec["defaults"] = kept_defaults
    data: "OrderedDict[str, object]" = OrderedDict()
    if description:
        data["description"] = description
    if units_from and units_from in table.header and kind != "org_units":
        units: "OrderedDict[str, object]" = OrderedDict()
        units["file"] = table.file
        if table.sheet:
            units["sheet"] = table.sheet
        units["id"] = OrderedDict([("prefix", "ORG-"), ("from", "name")])
        units["columns"] = OrderedDict([(units_from, "name")])
        units["defaults"] = OrderedDict([("status", "Active")])
        data["org_units"] = units
    data[kind] = spec
    return data


def _q(value) -> str:
    """A scalar in double quotes, which every YAML reader takes as text:
    an export's own words are often `Yes`, `01` or `1.50`."""
    return json.dumps(str(value), ensure_ascii=False)


def render_mapping(data: dict) -> str:
    """The mapping as the file kept beside the export, every word of the
    export's quoted."""
    lines = ["# Which column of the export is which field, and which of its words are",
             "# the model's. Written by Settings > Sources; `terrane import csv --map`",
             "# reads the same file. The format is in AAC-15."]
    if data.get("description"):
        lines += ["", "description: %s" % _q(data["description"])]
    for kind, spec in data.items():
        if kind == "description":
            continue
        lines += ["", "%s:" % kind]
        for key in ("file", "sheet", "code"):
            if spec.get(key):
                lines.append("  %s: %s" % (key, _q(spec[key])))
        if spec.get("id"):
            lines.append("  id: {prefix: %s, from: %s}" % (_q(spec["id"]["prefix"]), spec["id"]["from"]))
        if spec.get("columns"):
            lines.append("  columns:")
            for column, target in spec["columns"].items():
                said = "[%s]" % ", ".join(target) if isinstance(target, list) else target
                lines.append("    %s: %s" % (_q(column), said))
        if spec.get("ignore"):
            lines.append("  ignore: [%s]" % ", ".join(_q(c) for c in spec["ignore"]))
        for key in ("values", "defaults"):
            if not spec.get(key):
                continue
            lines.append("  %s:" % key)
            for field_name, value in spec[key].items():
                if isinstance(value, dict):
                    lines.append("    %s:" % field_name)
                    for theirs, ours in value.items():
                        lines.append("      %s: %s" % (_q(theirs), _q(ours)))
                else:
                    lines.append("    %s: %s" % (field_name, _q(value)))
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# The preview: everything bringing it in would write, with nothing written.
# ---------------------------------------------------------------------------
class Preview(NamedTuple):
    added: Dict[str, List[dict]]
    present: Dict[str, List[str]]
    held: List[str]
    conflicts: List[str]
    skipped: List[str]
    findings: List[validate.Finding]
    held_rows: int = 0

    def as_dict(self) -> dict:
        return {
            "added": {k: [{kk: vv for kk, vv in r.items() if not kk.startswith("_")} for r in rows]
                      for k, rows in self.added.items()},
            "present": self.present,
            "held": self.held,
            "heldRows": self.held_rows,
            "conflicts": self.conflicts,
            "skipped": self.skipped,
            "findings": [{"severity": f.severity, "code": f.code, "message": f.message} for f in self.findings],
            "counts": {k: len(v) for k, v in self.added.items()},
        }


def _finding_key(finding: validate.Finding) -> tuple:
    return finding.severity, finding.code, finding.message, finding.where


def preview(model, views: Sequence, folder: Path, data: dict, before=None) -> Preview:
    """What bringing the export in would write and what the checks would
    newly say, from the mapping engine's own reading, with nothing written:
    the records are added to a copy of the model held in memory and the
    checks run on that. `before` is the model's own report, when the caller
    has it."""
    maps = parse_mapping(data, "the mapping")
    mapped = inventory.apply(maps, Path(folder), model)
    added: Dict[str, List[dict]] = {}
    present: Dict[str, List[str]] = {}
    for kind, rows in mapped.rows.items():
        pk = ENTITY_TYPES[kind].pk
        for row in rows:
            if model.find(str(row[pk])) is not None:
                present.setdefault(kind, []).append(str(row[pk]))
            else:
                added.setdefault(kind, []).append(dict(row))
    candidate = copy.copy(model)
    candidate.entities = {kind: dict(records) for kind, records in model.entities.items()}
    candidate._adjacent = None
    for kind, rows in added.items():
        pk = ENTITY_TYPES[kind].pk
        for row in rows:
            record = dict(row)
            for name in _LIST_FIELDS:
                if isinstance(record.get(name), str):
                    record[name] = [t.strip() for t in record[name].replace(";", ",").split(",") if t.strip()]
            record["_type"] = kind
            record["_source_file"] = "%s (not yet written)" % Path(folder).name
            candidate.entities[kind][str(record[pk])] = record
    report = before if before is not None else validate.run(model, views)
    known = {_finding_key(f) for f in report.findings}
    findings = [f for f in validate.run(candidate, views).findings if _finding_key(f) not in known]
    return Preview(added, present, mapped.held, mapped.conflicts, mapped.skipped, findings, mapped.held_rows)


# ---------------------------------------------------------------------------
# Kept sources.
# ---------------------------------------------------------------------------
def folder_of(root: Path) -> Path:
    return Path(root) / SOURCES


def _title(name: str) -> str:
    return re.sub(r"[_\-]+", " ", name).strip().capitalize()


def _cmdb_exports(folder: Path) -> List[Path]:
    """The CSVs in a folder that read as a CMDB export: a sys_id column."""
    out = []
    for path in sorted(folder.glob("*.csv")):
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                header = [h.strip().lower() for h in next(csv.reader(handle), [])]
        except (OSError, UnicodeDecodeError):
            continue
        if "sys_id" in header:
            out.append(path)
    return out


def list_sources(root: Path) -> List[dict]:
    """Every kept source: a folder of `60_SOURCES` with a mapping brings in,
    and one holding a CMDB export compares."""
    base = folder_of(root)
    out: List[dict] = []
    if not base.is_dir():
        return out
    for folder in sorted(p for p in base.iterdir() if p.is_dir()):
        note = {}
        if (folder / NOTE).is_file():
            try:
                note = read_data_file(folder / NOTE) or {}
            except Exception:  # a note that does not read is no reason to hide the source
                note = {}
        mapping = folder / MAPPING
        if mapping.is_file():
            try:
                data = read_data_file(mapping) or {}
            except Exception:
                data = {}
            kinds = [k for k in data if k in ENTITY_TYPES]
            files: List[str] = []
            for kind in kinds:
                name = str((data.get(kind) or {}).get("file") or "%s.csv" % kind)
                if name not in files:
                    files.append(name)
            out.append({"id": folder.name, "name": str(note.get("name") or _title(folder.name)),
                        "kind": "brings in", "files": files, "makes": kinds,
                        "description": str(data.get("description") or ""),
                        "last": note.get("last") or None,
                        "simple": len(files) == 1 and len([k for k in kinds if k != "org_units"]) == 1})
            continue
        exports = _cmdb_exports(folder)
        if exports:
            out.append({"id": folder.name,
                        "name": str(note.get("name") or ("ServiceNow CMDB" if folder.name == "servicenow"
                                                          else _title(folder.name))),
                        "kind": "compares", "files": [p.name for p in exports], "makes": [],
                        "description": "", "last": note.get("last") or None, "simple": False,
                        "export": "%s/%s/%s" % (SOURCES, folder.name, exports[0].name)})
    return out


def compare_counts(model, root: Path, source: dict) -> dict:
    """A comparing source's differences, from the reconciliation the Drift
    tab and `terrane cmdb drift` run; nothing is written."""
    from .cmdb import load_field_sot, read_ci_export, reconcile

    path = Path(root) / source["export"]
    rows = read_ci_export(path)
    sot = folder_of(root) / source["id"] / "field_sot.yaml"
    result = reconcile(model, rows, field_sot=load_field_sot(sot) if sot.is_file() else {},
                       export_path=source["export"])
    return {"records": len(rows), "counts": dict(result.counts)}


def keep(root: Path, name: str, files: Dict[str, bytes], data: dict) -> Path:
    """A source kept: its export and its mapping in a folder of `60_SOURCES`
    named for it. A source of the same name is replaced; another source's
    folder is never written into."""
    name = " ".join(str(name or "").split())
    if not name:
        raise SourceError("a kept source has a name")
    base = folder_of(root)
    stem = slug(name).lower() or "source"
    folder = base / stem
    n = 2
    # A folder that is another source's, or holds files and no note of whose
    # they are (the shipped sample), is left alone.
    while folder.exists() and str(_read_note(folder).get("name") or "") != name:
        folder = base / ("%s-%d" % (stem, n))
        n += 1
    folder.mkdir(parents=True, exist_ok=True)
    for file_name, data_bytes in files.items():
        (folder / Path(file_name).name).write_bytes(data_bytes)
    (folder / MAPPING).write_text(render_mapping(data), encoding="utf-8", newline="\n")
    note = _read_note(folder)
    note["name"] = name
    _write_note(folder, note)
    return folder


def _read_note(folder: Path) -> dict:
    if (folder / NOTE).is_file():
        try:
            return dict(read_data_file(folder / NOTE) or {})
        except Exception:
            return {}
    return {}


def _write_note(folder: Path, note: dict) -> None:
    lines = ["# What Settings > Sources keeps about this source: its name, and when it",
             "# last came in and what it brought.",
             "name: %s" % _q(note.get("name") or _title(folder.name))]
    last = note.get("last") or {}
    if last:
        lines.append("last:")
        lines.append("  when: %s" % _q(last.get("when", "")))
        added = last.get("added") or {}
        if added:
            lines.append("  added:")
            for kind, count in added.items():
                lines.append("    %s: %d" % (kind, int(count)))
        lines.append("  held: %d" % int(last.get("held") or 0))
    (folder / NOTE).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def note_run(folder: Path, imported: Dict[str, int], held: int, when: Optional[str] = None) -> None:
    """When a kept source last came in and what it brought."""
    note = _read_note(folder)
    note["last"] = {"when": when or datetime.date.today().isoformat(),
                    "added": {k: v for k, v in imported.items() if v}, "held": held}
    _write_note(folder, note)


def choice_of(data: dict) -> Optional[dict]:
    """A kept mapping as the choices the Columns and Words steps show, for a
    mapping those steps could have written: one file, one kind, and the org
    units made from one of its columns. None for any other, which is shown
    as the file it is."""
    kinds = [k for k in data if k in ENTITY_TYPES]
    main = [k for k in kinds if k != "org_units"] or kinds
    if len(main) != 1:
        return None
    kind = main[0]
    spec = data.get(kind) or {}
    units = data.get("org_units") if kind != "org_units" else None
    units_from = None
    if units:
        cols = units.get("columns") or {}
        named = [c for c, t in cols.items() if t == "name"]
        if units.get("file") != spec.get("file") or len(cols) != 1 or not named:
            return None
        units_from = named[0]
    columns = {str(c): (list(t) if isinstance(t, list) else [t]) for c, t in (spec.get("columns") or {}).items()}
    rule = spec.get("id") or {}
    return {"kind": kind, "file": spec.get("file"), "sheet": spec.get("sheet"), "columns": columns,
            "code": spec.get("code"), "prefix": rule.get("prefix"),
            "values": {f: {str(k): str(v) for k, v in (t or {}).items()} for f, t in (spec.get("values") or {}).items()},
            "defaults": {f: str(v) for f, v in (spec.get("defaults") or {}).items()}, "unitsFrom": units_from}


def mapping_of(root: Path, source_id: str) -> Tuple[Path, dict]:
    """A kept source's folder and its mapping as data, checked."""
    folder = folder_of(root) / source_id
    path = folder / MAPPING
    if not path.is_file() or folder.parent != folder_of(root):
        raise SourceError("no source %r with a mapping" % source_id)
    inventory.load_mapping(path)
    return folder, read_data_file(path) or {}


__all__ = ["KINDS", "MappingError", "Preview", "SourceError", "Table", "build_mapping", "columns_of",
           "compare_counts", "id_prefix", "keep", "kind_fields", "list_sources", "mapping_of", "note_run",
           "preview", "read_table", "render_mapping", "suggest", "utf8_csv", "words_needed"]
