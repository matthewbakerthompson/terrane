"""Import an existing inventory into the model.

The inverse of `terrane export csv`. This is the answer to "we already have a
spreadsheet / a Collibra extract / a CMDB dump, and we are not retyping it":
point the importer at metamodel v2 CSVs and it writes the model files. An
inventory in its own words -- its columns, its values, its codes -- comes in
through a mapping that says what each is in ours (`inventory.py`, AAC-15).

Two decisions worth knowing about:

* **Import is additive by default and never silently overwrites.** A row whose
  id already exists is reported as a conflict and skipped unless `--overwrite`
  is passed. An import that quietly replaced hand-authored detail with a thin
  CMDB row would be the worst possible default. That goes for files as well
  as rows: a reference set lands in `<type>.yaml` only when there is none, and
  is added to its own file beside it otherwise, and relations are added to
  `imported_relations.yaml` rather than written over it. Both used to be
  written whole, so a second import -- or a first one into a model that kept
  the shipped org units -- replaced every record in the file.
* **What is left out is said.** A column that is not a field of the type, and
  a row with no id, are listed in `skipped`, because an inventory exported
  from somewhere else always has columns this model does not, and finding out
  by their absence is finding out late.
* **Blank columns are dropped rather than written as empty.** An imported file
  should read like something a person would have written, not a wall of empty
  keys, or nobody will ever edit it by hand afterward.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Sequence

from .model import Model
from .schema import ENTITY_TYPES, FIELD_ALIASES, RELATION_TYPES, EntityType

#: Reference sets are small and change as a group, so they land in one file
#: each. Everything else gets a file per record, for clean diffs and ownership.
GROUPED = {"org_units", "capabilities", "tech_services", "policies", "controls"}

#: Fields that hold a list, written as a flow sequence so the file reads the
#: way a person would have written it, and accepted as a `;` string on the
#: way in because that is how a CSV carries one.
LIST_FIELDS = ("tags", "patterns")


class ImportError_(ValueError):
    """The import source could not be read."""


class Outcome(NamedTuple):
    written: List[Path]
    imported: Dict[str, int]
    skipped: List[str]
    conflicts: List[str]
    #: Rows a mapping could not place, by field and value: written by no one
    #: until the mapping says what they are.
    held: List[str] = []


def _yaml_scalar(value: str) -> str:
    text = str(value)
    if text == "":
        return '""'
    if text.lower() in ("true", "false", "null", "yes", "no", "on", "off", "~"):
        return '"%s"' % text
    # Quote anything that could be misread as structure, a number, or a date.
    if text[0] in "-?:,[]{}#&*!|>'\"%@`" or ": " in text or text != text.strip():
        return '"%s"' % text.replace('"', '\\"')
    if text.replace(".", "", 1).replace("-", "", 1).isdigit():
        return '"%s"' % text
    return text


def _render_record(record: dict, entity_type: EntityType, indent: str = "") -> List[str]:
    """Serialize one record, primary key first, in metamodel field order."""
    lines: List[str] = []
    order = [entity_type.pk] + [f.name for f in entity_type.fields if f.name != entity_type.pk]
    for key in order:
        value = record.get(key)
        if value in (None, ""):
            continue
        if key in LIST_FIELDS and isinstance(value, str) and value:
            items = [t.strip() for t in value.replace(";", ",").split(",") if t.strip()]
            lines.append("%s%s: [%s]" % (indent, key, ", ".join(items)))
            continue
        lines.append("%s%s: %s" % (indent, key, _yaml_scalar(value)))
    return lines


def _read_csv(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


#: Fields that describe how an entity was *generated* rather than what it is.
#: A CSV export is a flattened snapshot of the resolved model, so these cannot
#: round-trip: an imported row carrying `archetype` would otherwise be read back
#: as an archetype instance and expanded a second time. Import produces plain
#: entities, and the archetype linkage is re-established by hand if wanted.
DERIVED_FIELDS = ("archetype", "archetype_instance")


def _unknown_columns(path: Path, entity_type: EntityType) -> List[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        header = next(csv.reader(handle), [])
    aliases = FIELD_ALIASES.get(entity_type.name, {})
    known = {f.name for f in entity_type.fields} | {entity_type.pk}
    return [c.strip() for c in header
            if c.strip() and aliases.get(c.strip(), c.strip()) not in known]


def _append_relation_rows(text: str, name: str, block: List[str]) -> str:
    """Rows added to one relation's list in a file of relations, or the
    relation added at the end, every line already there left as it was."""
    import re

    lines = text.rstrip("\n").splitlines()
    key = re.compile(r"^%s:\s*(#.*)?$" % re.escape(name))
    start = next((i for i, line in enumerate(lines) if key.match(line)), None)
    if start is None:
        return "\n".join(lines + ["", "%s:" % name] + block) + "\n"
    # The relation's rows run to the next line at the margin; the new ones go
    # after its last row, ahead of any blank line or comment that follows.
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].strip() and not lines[i][:1].isspace()), len(lines))
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    lines[end:end] = block
    return "\n".join(lines) + "\n"


def _clean_row(row: dict, entity_type: EntityType) -> dict:
    aliases = FIELD_ALIASES.get(entity_type.name, {})
    known = {f.name for f in entity_type.fields} | {entity_type.pk}
    out: Dict[str, str] = {}
    for key, value in row.items():
        if key is None:
            continue
        key = aliases.get(key.strip(), key.strip())
        if key not in known or key in DERIVED_FIELDS:
            continue
        value = (value or "").strip()
        if value:
            out[key] = value
    return out


def import_csv(
    root: Path,
    source: Path,
    model: Model,
    overwrite: bool = False,
    only: Optional[Sequence[str]] = None,
    mapping: Optional[Path] = None,
) -> Outcome:
    """Read metamodel v2 CSVs from `source` and write model files under `root`.

    Given a `mapping`, the files in `source` are an inventory in its own
    words, and the mapping says which column is which field, which value is
    which of ours and how a code becomes an id (`inventory.py`). What it
    makes is written exactly as a v2 row would be, so every guarantee above
    holds for it too; relation CSVs are read only without one.
    """
    root = Path(root)
    source = Path(source)
    if not source.is_dir():
        raise ImportError_("import source is not a directory: %s" % source)

    written: List[Path] = []
    imported: Dict[str, int] = {}
    skipped: List[str] = []
    conflicts: List[str] = []
    held: List[str] = []
    wanted = set(only) if only else None

    batches: List[tuple] = []
    if mapping is not None:
        from . import inventory

        mapped = inventory.apply(inventory.load_mapping(mapping), source, model, only)
        skipped.extend(mapped.skipped)
        conflicts.extend(mapped.conflicts)
        held.extend(mapped.held)
        batches = [(name, mapped.origins[name], mapped.rows[name])
                   for name in ENTITY_TYPES if mapped.rows.get(name)]
    else:
        for type_name, entity_type in ENTITY_TYPES.items():
            if wanted and type_name not in wanted:
                continue
            path = source / ("%s.csv" % type_name)
            if not path.exists():
                continue
            unknown = _unknown_columns(path, entity_type)
            if unknown:
                skipped.append(
                    "%s: %s %s not a field of a %s, so %s left out"
                    % (path.name, ", ".join(unknown), "is" if len(unknown) == 1 else "are",
                       entity_type.label, "it was" if len(unknown) == 1 else "they were")
                )
            raw_rows = [_clean_row(r, entity_type) for r in _read_csv(path)]
            rows = [r for r in raw_rows if r.get(entity_type.pk)]
            if len(rows) < len(raw_rows):
                skipped.append(
                    "%s: %d row(s) with no %s" % (path.name, len(raw_rows) - len(rows), entity_type.pk)
                )
            if rows:
                batches.append((type_name, path.name, rows))

    from . import records as records_module

    for type_name, origin, rows in batches:
        entity_type = ENTITY_TYPES[type_name]
        folder = root / "10_MODEL" / entity_type.folder
        keep: List[dict] = []
        replaced = 0
        for row in rows:
            entity_id = row[entity_type.pk]
            existing = model.find(entity_id)
            if existing is None:
                if type_name not in GROUPED and (folder / ("%s.yaml" % entity_id)).exists():
                    conflicts.append(
                        "%s %s: %s.yaml already exists and holds something else"
                        % (entity_type.label, entity_id, entity_id)
                    )
                    continue
                keep.append(row)
                continue
            if not overwrite:
                conflicts.append(
                    "%s %s already in the model (%s)"
                    % (entity_type.label, entity_id, existing[1].get("_source_file", ""))
                )
                continue
            home = records_module.home_of(existing[0], existing[1])
            if existing[0] != type_name or home.kind not in ("own", "shared"):
                # A record another import writes, or a shape makes, is not this
                # import's to replace: the next run of that would put it back.
                conflicts.append(
                    "%s %s is not replaced: %s"
                    % (entity_type.label, entity_id,
                       home.note or "the id is a %s" % existing[0])
                )
                continue
            values = {k: v for k, v in row.items() if k != entity_type.pk}
            if home.kind == "own":
                body = ["# Imported from %s." % origin]
                body.extend(_render_record(row, entity_type))
                home.path.write_text("\n".join(body) + "\n", encoding="utf-8")
            else:
                before = home.path.read_text(encoding="utf-8-sig")
                home.path.write_text(
                    records_module.replace_item(before, type_name, entity_id, values), encoding="utf-8"
                )
            written.append(home.path)
            replaced += 1
        if not keep and not replaced:
            continue

        folder.mkdir(parents=True, exist_ok=True)

        if type_name in GROUPED and keep:
            target = folder / ("%s.yaml" % type_name)
            if target.exists():
                # The set already has a file -- the shipped one, or another
                # import's -- and it is not this import's to write over.
                target = folder / ("imported_%s.yaml" % type_name)
            if target.exists():
                current = target.read_text(encoding="utf-8-sig")
                for row in sorted(keep, key=lambda r: r[entity_type.pk]):
                    values = {k: v for k, v in row.items() if k != entity_type.pk}
                    current = records_module.append_item(current, type_name, row[entity_type.pk], values)
                target.write_text(current, encoding="utf-8")
            else:
                lines = [
                    "# Imported from %s. Reference set: these change as a group, so"
                    % origin,
                    "# they share a file. Edit freely; the importer will not overwrite.",
                ]
                for row in sorted(keep, key=lambda r: r[entity_type.pk]):
                    block = _render_record(row, entity_type, indent="  ")
                    lines.append("")
                    lines.append("- " + block[0].strip())
                    lines.extend(block[1:])
                target.write_text("\n".join(lines) + "\n", encoding="utf-8")
            written.append(target)
        else:
            for row in keep:
                body = ["# Imported from %s." % origin]
                body.extend(_render_record(row, entity_type))
                target = folder / ("%s.yaml" % row[entity_type.pk])
                target.write_text("\n".join(body) + "\n", encoding="utf-8")
                written.append(target)

        imported[type_name] = len(keep) + replaced

    relation_rows: Dict[str, List[dict]] = {}
    rel_dir = source / "relations"
    if mapping is None and rel_dir.is_dir():
        for name, spec in RELATION_TYPES.items():
            path = rel_dir / ("%s.csv" % name)
            if not path.exists():
                continue
            columns = [spec.left_column, spec.right_column] + (
                [spec.qualifier] if spec.qualifier else []
            )
            rows = []
            for raw in _read_csv(path):
                row = {c: (raw.get(c) or "").strip() for c in columns}
                if row[spec.left_column] and row[spec.right_column]:
                    rows.append({k: v for k, v in row.items() if v})
            if rows:
                relation_rows[name] = rows

    if relation_rows:
        folder = root / "10_MODEL" / "relations"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / "imported_relations.yaml"
        held: Dict[str, List[dict]] = {}
        if target.exists():
            from .loader import read_data_file

            data = read_data_file(target) or {}
            if isinstance(data, dict):
                held = {k: list(v or []) for k, v in data.items()}

        def row_lines(spec, row):
            out, first = [], True
            for column in [spec.left_column, spec.right_column] + (
                [spec.qualifier] if spec.qualifier else []
            ):
                if column not in row:
                    continue
                prefix = "  - " if first else "    "
                out.append("%s%s: %s" % (prefix, column, _yaml_scalar(row[column])))
                first = False
            return out

        if target.exists():
            text = target.read_text(encoding="utf-8-sig")
        else:
            text = (
                "# Imported relations. Relationship truth lives in rows, not in\n"
                "# semicolon-separated columns on the entity.\n"
            )
        added_any = False
        for name in sorted(relation_rows):
            spec = RELATION_TYPES[name]
            already = [{k: str(v) for k, v in r.items()} for r in held.get(name, [])]
            fresh = [r for r in relation_rows[name] if r not in already]
            if not fresh:
                continue
            block: List[str] = []
            for row in fresh:
                block.extend(row_lines(spec, row))
            text = _append_relation_rows(text, name, block)
            imported[name] = len(fresh)
            added_any = True
        if added_any:
            target.write_text(text, encoding="utf-8")
            written.append(target)

    return Outcome(written=written, imported=imported, skipped=skipped,
                   conflicts=conflicts, held=held)
