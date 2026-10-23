"""A correction written into a record's own file, the file otherwise left
as it is.

The model's files are written by hand, with the reasons above the records
in comments, and a reviewer's correction is one cell of one record. The
engine's YAML writer would make the file whole again without its
comments, so a correction is written where the field is: the record's
entry found by its id line, the field's lines replaced, or the field
added at the end of the entry; then the file is read back and the record
checked before the change stands, and put back as it was when it does
not. What cannot be found that way is said and left as it is.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .loader import ModelFileError, read_data_file
from .sketch import dump_yaml


class CorrectError(ValueError):
    pass


def words(value: Any) -> List[str]:
    """A list field as the list it is, whether written as one or as the
    `;` or `,` string a spreadsheet cell holds."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [t.strip() for t in str(value).replace(";", ",").split(",") if t.strip()]


def text_of(value: Any) -> str:
    """A value as the text a cell would hold, so two spellings of one
    value compare equal: a list in any order, a bool as Yes or No."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (list, tuple)):
        return ";".join(sorted(str(v) for v in value))
    return str(value).strip()


def typed_like(given: Any, like: Any) -> Any:
    """What a cell says, as the kind of value the field holds now: a list
    where the field is one, a bool where it is one, a number where it is
    one, else the text, since a description may hold a semicolon and is
    no list for it."""
    if not isinstance(given, str):
        return given
    text = given.strip()
    if isinstance(like, bool):
        return text.lower() in ("yes", "true", "1", "y")
    if isinstance(like, int):
        try:
            return int(text)
        except ValueError:
            return text
    if isinstance(like, float):
        try:
            return float(text)
        except ValueError:
            return text
    if isinstance(like, (list, tuple)):
        return words(text)
    return text


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _entry(lines: List[str], pk: str, entity_id: str) -> Tuple[int, int, int]:
    """The record's entry: the index of its id line, the index after its
    last line, and the indent its keys sit at. The id must be the first
    line of the entry (`- system_id: X` in a list, `system_id: X` at the
    top of a file of one), which is how every file of the model is laid
    out; one laid out otherwise is said and left as it is."""
    pattern = re.compile(r"^(\s*)(-\s+)?%s:\s*['\"]?%s['\"]?\s*(#.*)?$" % (re.escape(pk), re.escape(entity_id)))
    for i, line in enumerate(lines):
        m = pattern.match(line)
        if m is None:
            continue
        item_indent = len(m.group(1))
        if m.group(2) is None and item_indent > 0:
            raise CorrectError("the id of %s is not the first line of its entry in the file" % entity_id)
        key_indent = item_indent + (len(m.group(2)) if m.group(2) else 0)
        end = i + 1
        while end < len(lines):
            text = lines[end]
            if not text.strip() or text.lstrip().startswith("#"):
                end += 1
                continue
            indent = _indent(text)
            if indent < key_indent or (m.group(2) and indent == item_indent and text.lstrip().startswith("- ")):
                break
            end += 1
        while end > i + 1 and (not lines[end - 1].strip() or lines[end - 1].lstrip().startswith("#")):
            end -= 1
        return i, end, key_indent
    raise CorrectError("no entry for %s in its file" % entity_id)


def _field_span(lines: List[str], first: int, end: int, key_indent: int, key: str) -> Optional[Tuple[int, int]]:
    """Where the field sits in the entry: its line and the lines indented
    under it (a folded description, a block list); None when the entry
    does not have it."""
    pattern = re.compile(r"^ {%d}%s:(\s|$)" % (key_indent, re.escape(key)))
    for i in range(first + 1, end):
        if pattern.match(lines[i]):
            j = i + 1
            while j < end and (not lines[j].strip() or _indent(lines[j]) > key_indent):
                j += 1
            while j > i + 1 and not lines[j - 1].strip():
                j -= 1
            return i, j
    return None


def revise(path: Path, pk: str, entity_id: str, changes: Dict[str, Any]) -> None:
    """Write `changes`, field to new value, into the record's entry in
    its file, and nothing else in the file; refused, with the file as it
    was, when the entry cannot be found or the change does not read back."""
    path = Path(path)
    original = path.read_text(encoding="utf-8-sig")
    newline = "\r\n" if "\r\n" in original else "\n"
    lines = original.splitlines()
    first, end, key_indent = _entry(lines, pk, entity_id)
    pad = " " * key_indent
    for key, value in changes.items():
        rendered = [pad + line if line else line for line in dump_yaml({key: value})]
        span = _field_span(lines, first, end, key_indent, key)
        if span is not None:
            lines[span[0]:span[1]] = rendered
            end += len(rendered) - (span[1] - span[0])
        else:
            lines[end:end] = rendered
            end += len(rendered)
    path.write_text(newline.join(lines) + newline, encoding="utf-8")
    try:
        data = read_data_file(path)
    except ModelFileError as exc:
        path.write_text(original, encoding="utf-8")
        raise CorrectError("the file did not read back after the change (%s)" % exc) from exc
    records = data if isinstance(data, list) else [data]
    record = next((r for r in records if isinstance(r, dict) and str(r.get(pk)) == entity_id), None)
    if record is None or any(text_of(record.get(k)) != text_of(v) for k, v in changes.items()):
        path.write_text(original, encoding="utf-8")
        raise CorrectError("the change to %s did not read back as written" % entity_id)


def _children(lines: List[str], first: int, end: int, fallback: int) -> int:
    """The indent the lines under `first` sit at, read off the first one
    that is neither blank nor a comment; `fallback` when there is none."""
    for i in range(first + 1, end):
        if lines[i].strip() and not lines[i].lstrip().startswith("#"):
            return _indent(lines[i])
    return fallback


def revise_override(path: Path, pk: str, instance_id: str, record_id: str, changes: Dict[str, Any]) -> None:
    """Write `changes` for a record a shape made under the product's
    `overrides`, into the product's entry and nothing else in the file:
    the field within the record's own override entry when there is one,
    the entry under `overrides:` when there is not, and the block itself
    when the product has none. The method keeps what reality says
    differently from the shape there, so a reviewer's correction to a
    system the shape made lands where the next render reads it. Refused,
    with the file as it was, when the product's entry cannot be found or
    the change does not read back."""
    path = Path(path)
    original = path.read_text(encoding="utf-8-sig")
    newline = "\r\n" if "\r\n" in original else "\n"
    lines = original.splitlines()
    first, end, key_indent = _entry(lines, pk, instance_id)
    block = _field_span(lines, first, end, key_indent, "overrides")
    if block is None:
        pad = " " * key_indent
        lines[end:end] = [pad + line if line else line for line in dump_yaml({"overrides": {record_id: changes}})]
    else:
        start, stop = block
        inner = _children(lines, start, stop, key_indent + 2)
        entry = _field_span(lines, start, stop, inner, record_id)
        if entry is None:
            pad = " " * inner
            lines[stop:stop] = [pad + line if line else line for line in dump_yaml({record_id: changes})]
        else:
            e_first, e_end = entry
            field_indent = _children(lines, e_first, e_end, inner + 2)
            pad = " " * field_indent
            for key, value in changes.items():
                rendered = [pad + line if line else line for line in dump_yaml({key: value})]
                span = _field_span(lines, e_first, e_end, field_indent, key)
                if span is not None:
                    lines[span[0]:span[1]] = rendered
                    e_end += len(rendered) - (span[1] - span[0])
                else:
                    lines[e_end:e_end] = rendered
                    e_end += len(rendered)
    path.write_text(newline.join(lines) + newline, encoding="utf-8")
    try:
        data = read_data_file(path)
    except ModelFileError as exc:
        path.write_text(original, encoding="utf-8")
        raise CorrectError("the file did not read back after the change (%s)" % exc) from exc
    records = data if isinstance(data, list) else [data]
    record = next((r for r in records if isinstance(r, dict) and str(r.get(pk)) == instance_id), None)
    held = (record.get("overrides") or {}).get(record_id) if isinstance(record, dict) else None
    if not isinstance(held, dict) or any(text_of(held.get(k)) != text_of(v) for k, v in changes.items()):
        path.write_text(original, encoding="utf-8")
        raise CorrectError("the override of %s under %s did not read back as written" % (record_id, instance_id))


def revise_row(path: Path, relation: str, left_column: str, left: str, right_column: str, right: str,
               qualifier: str, value: Any) -> None:
    """Write a relation row's qualifier into its file, and nothing else in
    the file: the row found under the relation's key by its two ends, the
    qualifier's line replaced or added after the ends. Refused, with the
    file as it was, when the row cannot be found or the change does not
    read back."""
    path = Path(path)
    original = path.read_text(encoding="utf-8-sig")
    newline = "\r\n" if "\r\n" in original else "\n"
    lines = original.splitlines()
    section = re.compile(r"^%s:\s*(#.*)?$" % re.escape(relation))
    start = re.compile(r"^(\s*)-\s+%s:\s*['\"]?%s['\"]?\s*(#.*)?$" % (re.escape(left_column), re.escape(left)))
    partner = re.compile(r"^\s*%s:\s*['\"]?%s['\"]?\s*(#.*)?$" % (re.escape(right_column), re.escape(right)))
    in_section = False
    for i, line in enumerate(lines):
        if not line.startswith((" ", "\t", "#", "-")) and line.strip():
            in_section = bool(section.match(line))
            continue
        if not in_section:
            continue
        m = start.match(line)
        if m is None:
            continue
        item_indent = len(m.group(1))
        key_indent = item_indent + 2
        end = i + 1
        while end < len(lines):
            text_ = lines[end]
            if not text_.strip() or text_.lstrip().startswith("#"):
                end += 1
                continue
            if _indent(text_) < key_indent:
                break
            end += 1
        while end > i + 1 and (not lines[end - 1].strip() or lines[end - 1].lstrip().startswith("#")):
            end -= 1
        if not any(partner.match(lines[j]) for j in range(i + 1, end)):
            continue
        pad = " " * key_indent
        rendered = [pad + l if l else l for l in dump_yaml({qualifier: value})]
        span = _field_span(lines, i, end, key_indent, qualifier)
        if span is not None:
            lines[span[0]:span[1]] = rendered
        else:
            lines[end:end] = rendered
        path.write_text(newline.join(lines) + newline, encoding="utf-8")
        try:
            data = read_data_file(path)
        except ModelFileError as exc:
            path.write_text(original, encoding="utf-8")
            raise CorrectError("the file did not read back after the change (%s)" % exc) from exc
        rows = (data or {}).get(relation) if isinstance(data, dict) else None
        found = next((r for r in (rows or []) if isinstance(r, dict) and str(r.get(left_column)) == left
                      and str(r.get(right_column)) == right), None)
        if found is None or text_of(found.get(qualifier)) != text_of(value):
            path.write_text(original, encoding="utf-8")
            raise CorrectError("the change to the %s row %s -> %s did not read back as written" % (relation, left, right))
        return
    raise CorrectError("no %s row %s -> %s in its file" % (relation, left, right))

