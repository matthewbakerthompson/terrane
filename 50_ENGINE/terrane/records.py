"""Where a record lives, and how to change it there.

Six hundred of the records in this model share a file with others: the
capability map, the register, each landing zone's technology services, the
systems the business layer harvested. The app's form used to write every save
to `<folder>/<ID>.yaml`, which for any of those made a second copy of the
record beside the first, and the next load refused the model for holding a
duplicate. A record is changed where it is, or moved somewhere on purpose, and
this module is the one place that knows how.

What it will not do is rewrite a file around one record. A record in a shared
file is found by its id, its lines are replaced, and every other line of the
file -- the other records, the comments between them -- is left as it was. A
field whose value did not change keeps its lines too, so a description wrapped
by hand over three lines is not rewritten as one because somebody changed the
owner.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Tuple

from .compose import _blocks
from .importer import LIST_FIELDS, _yaml_scalar
from .loader import ModelFileError, parse_data_text, read_data_file
from .schema import ENTITY_TYPES, EntityType

#: The types an import may let go of. The business-layer import harvests
#: systems and data assets the estate did not hold, and leaves alone any id it
#: finds outside its own file, so moving one out is how it is promoted. The
#: rest of what it brings -- capabilities, processes, the register -- it
#: rewrites whole every run, and an edit made here would be undone without a
#: trace.
PROMOTABLE = ("systems", "data_assets")

#: Fields the entity form never shows, so a save that does not mention them
#: has not cleared them. The old writer dropped them, which quietly took a
#: product off its shape the first time someone corrected its name.
UNASKED = ("archetype", "archetype_instance", "module")


class Home(NamedTuple):
    """Where a record lives and what saving it means.

    `kind` is one of:

    * `own` -- a file of its own; the file is rewritten.
    * `shared` -- one record of several in a hand-written file; its lines
      are replaced in place.
    * `harvested` -- one record of several in a file an import writes; a save
      moves it into a file of its own, which the import then leaves alone.
    * `imported` -- one record of several in a file an import rewrites whole;
      it is changed at the source and imported again, not here.
    * `generated` -- made by a shape; it is changed on the instance.
    """

    kind: str
    path: Optional[Path]
    note: str = ""


_SHAPES: Dict[Tuple[str, int, int], bool] = {}


def _holds_a_list(path: Path) -> bool:
    """Whether a file holds several records, remembered while the file is
    unchanged. Asked once per record -- and the hosted copy bakes every
    record's inspector -- the capability map was parsed once per
    capability."""
    try:
        stat = path.stat()
    except OSError:
        return False
    key = (str(path), stat.st_mtime_ns, stat.st_size)
    if key not in _SHAPES:
        try:
            _SHAPES[key] = isinstance(read_data_file(path), list)
        except ModelFileError:
            _SHAPES[key] = False
    return _SHAPES[key]


def home_of(type_name: str, record: dict) -> Home:
    if record.get("archetype_instance"):
        return Home(
            "generated", None,
            "Made by %s. Change it there and it is made again." % record["archetype_instance"],
        )
    source_file = record.get("_source_file")
    if not source_file:
        return Home("generated", None, "It has no file of its own.")
    path = Path(str(source_file))
    if not _holds_a_list(path):
        return Home("own", path)
    origin = str(record.get("source") or "").strip()
    if not origin:
        return Home("shared", path)
    if type_name in PROMOTABLE:
        return Home(
            "harvested", path,
            "Harvested from the %s into %s, which the import rewrites. Saving moves it "
            "into a file of its own, which the import leaves alone; it keeps saying where "
            "it came from until somebody clears its source." % (origin[:1].lower() + origin[1:], path.name),
        )
    return Home(
        "imported", path,
        "Imported from the %s, which is where it is changed: %s is rewritten by every "
        "import, so an edit made here would be undone by the next one."
        % (origin[:1].lower() + origin[1:], path.name),
    )


# ---------------------------------------------------------------------------
# Writing a record's lines.
# ---------------------------------------------------------------------------


def _as_list(value: Any) -> List[str]:
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [t.strip() for t in str(value).replace(";", ",").split(",") if t.strip()]


def _plain(value: Any) -> Any:
    """What a value says, for comparing a form's answer with a file's. A form
    sends `3` as text and a folded description arrives with its newline."""
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value]
    if value is None:
        return ""
    return " ".join(str(value).split())


def check_fields(entity_type: EntityType, values: Dict[str, Any]) -> None:
    known = {f.name for f in entity_type.fields} | {entity_type.pk}
    unknown = sorted(k for k in values if k not in known and not str(k).startswith("_"))
    if unknown:
        raise ValueError("%s has no field(s): %s" % (entity_type.label, ", ".join(unknown)))


def field_lines(key: str, value: Any) -> List[str]:
    """The lines one field is written as, or none for an empty one."""
    if value in (None, "", [], {}):
        return []
    if key in LIST_FIELDS or isinstance(value, (list, tuple)):
        items = _as_list(value)
        return ["%s: [%s]" % (key, ", ".join(items))] if items else []
    text = " ".join(str(value).split()) if isinstance(value, str) else value
    return ["%s: %s" % (key, _yaml_scalar(text))]


def record_lines(type_name: str, entity_id: str, values: Dict[str, Any]) -> List[str]:
    """A record as a mapping, key first, in metamodel field order."""
    entity_type = ENTITY_TYPES[type_name]
    check_fields(entity_type, values)
    lines = ["%s: %s" % (entity_type.pk, _yaml_scalar(entity_id))]
    for spec in entity_type.fields:
        if spec.name != entity_type.pk:
            lines.extend(field_lines(spec.name, values.get(spec.name)))
    return lines


def merge_record(old_lines: Sequence[str], type_name: str, entity_id: str,
                 values: Dict[str, Any]) -> List[str]:
    """The record's new lines, written over its old ones.

    A field whose value did not change keeps its lines as they were, comments
    and wrapping included; a changed one is written fresh under whatever was
    written above it; one the form left empty goes; a new one is added after
    the rest in field order. The mapping's own header comments stay.
    """
    entity_type = ENTITY_TYPES[type_name]
    check_fields(entity_type, values)
    wanted = dict(values)
    wanted[entity_type.pk] = entity_id
    known = {f.name for f in entity_type.fields}
    head, blocks = _blocks(list(old_lines), 0)
    out: List[str] = list(head)
    seen = set()
    for key, block in blocks:
        seen.add(key)
        if key not in wanted and (key not in known or key in UNASKED):
            # A key the form never offers is not the form's to drop: a product's
            # `archetype`, its `modules` and `overrides`, the part that made it.
            out.extend(block.lines())
            continue
        try:
            before = parse_data_text("\n".join([block.head] + list(block.body)), "the record")
            old_value = before.get(key) if isinstance(before, dict) else None
        except ModelFileError:
            old_value = None
        new_value = wanted.get(key)
        if old_value is not None and _plain(old_value) == _plain(new_value):
            out.extend(block.lines())
            continue
        fresh = field_lines(key, new_value)
        if not fresh:
            continue
        out.extend(block.lead)
        out.extend(fresh)
    for spec in entity_type.fields:
        if spec.name not in seen and spec.name != entity_type.pk:
            out.extend(field_lines(spec.name, wanted.get(spec.name)))
    while out and not out[-1].strip():
        out.pop()
    return out


# ---------------------------------------------------------------------------
# One record inside a file of several.
# ---------------------------------------------------------------------------


def _spans(lines: Sequence[str]) -> List[Tuple[int, int]]:
    """Where each top-level list item starts and ends, end exclusive and
    trailing blank lines left outside it. An item runs from its `- ` to the
    next line written at the left margin, which is the next item or the
    comment above it."""
    spans: List[Tuple[int, int]] = []
    start = None
    for index, line in enumerate(lines):
        at_margin = bool(line.strip()) and not line[:1].isspace()
        if at_margin and start is not None:
            spans.append((start, index))
            start = None
        if at_margin and (line.startswith("- ") or line.rstrip() == "-"):
            start = index
    if start is not None:
        spans.append((start, len(lines)))
    trimmed = []
    for begin, end in spans:
        while end > begin + 1 and not lines[end - 1].strip():
            end -= 1
        trimmed.append((begin, end))
    return trimmed


def find_item(text: str, pk: str, entity_id: str) -> Optional[Tuple[int, int]]:
    lines = text.splitlines()
    for begin, end in _spans(lines):
        try:
            data = parse_data_text("\n".join(lines[begin:end]), "the item")
        except ModelFileError:
            continue
        if isinstance(data, list) and data and isinstance(data[0], dict):
            if str(data[0].get(pk)) == str(entity_id):
                return begin, end
    return None


def _dedent(item: Sequence[str]) -> List[str]:
    """A list item as the mapping it is: `- key: v` and `  key: v` become
    `key: v`."""
    out = []
    for index, line in enumerate(item):
        if index == 0:
            out.append(line[2:] if line.startswith("- ") else line[1:])
        else:
            out.append(line[2:] if line.startswith("  ") else line.lstrip())
    return out


def _indent(mapping: Sequence[str]) -> List[str]:
    out = []
    for index, line in enumerate(mapping):
        if index == 0:
            out.append("- " + line)
        else:
            out.append(("  " + line) if line.strip() else "")
    return out


def item_lines(text: str, type_name: str, entity_id: str) -> List[str]:
    """The record's own lines inside a shared file, as a mapping."""
    pk = ENTITY_TYPES[type_name].pk
    span = find_item(text, pk, entity_id)
    if span is None:
        raise KeyError(entity_id)
    return _dedent(text.splitlines()[span[0]:span[1]])


def replace_item(text: str, type_name: str, entity_id: str, values: Dict[str, Any]) -> str:
    pk = ENTITY_TYPES[type_name].pk
    lines = text.splitlines()
    span = find_item(text, pk, entity_id)
    if span is None:
        raise KeyError(entity_id)
    old = _dedent(lines[span[0]:span[1]])
    # A comment written inside the item above its first key belongs with the
    # key line, which a list item cannot put above itself; it stays where it is.
    new = _indent(merge_record(old, type_name, entity_id, values))
    lines[span[0]:span[1]] = new
    return "\n".join(lines) + "\n"


def remove_item(text: str, type_name: str, entity_id: str) -> str:
    """The file without the record, and without the blank line that kept it
    from its neighbor, so two removals in a row do not leave a gap."""
    pk = ENTITY_TYPES[type_name].pk
    lines = text.splitlines()
    span = find_item(text, pk, entity_id)
    if span is None:
        raise KeyError(entity_id)
    begin, end = span
    while begin > 0 and not lines[begin - 1].strip():
        begin -= 1
    del lines[begin:end]
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines) + "\n"


def append_item(text: str, type_name: str, entity_id: str, values: Dict[str, Any]) -> str:
    lines = text.rstrip("\n").splitlines() if text.strip() else []
    if lines:
        lines.append("")
    lines.extend(_indent(record_lines(type_name, entity_id, values)))
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# A whole file of nested data, rewritten by value.
# ---------------------------------------------------------------------------

_UNREAD = object()


def _same(a: Any, b: Any) -> bool:
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_same(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    if isinstance(a, (dict, list, tuple)) or isinstance(b, (dict, list, tuple)):
        return False
    return _plain(a) == _plain(b)


def _value_of(block, indent: int) -> Any:
    lines = [block.head] + list(block.body)
    text = "\n".join(line[indent:] if line[:indent].strip() == "" else line for line in lines)
    try:
        data = parse_data_text(text, "a block")
    except ModelFileError:
        return _UNREAD
    return data.get(block.key, _UNREAD) if isinstance(data, dict) else _UNREAD


def _merged(blocks, new: Dict[str, Any], indent: int) -> List[str]:
    from .sketch import dump_yaml

    old = dict(blocks)
    out: List[str] = []
    for key, value in new.items():
        before = old.get(key)
        fresh = dump_yaml({key: value}, indent // 2)
        if before is None:
            out.extend(fresh)
            continue
        was = _value_of(before, indent)
        if was is not _UNREAD and _same(was, value):
            out.extend(before.lines())
            continue
        out.extend(before.lead)
        if isinstance(value, dict) and value and isinstance(was, dict) and was:
            out.append(before.head)
            _head, inner = _blocks(before.body, indent + 2)
            out.extend(_merged(inner, value, indent + 2))
        else:
            out.extend(fresh)
    return out


def rewrite(old_text: str, new: Dict[str, Any]) -> str:
    """A mapping file rewritten to hold `new`, by value rather than by line:
    a key whose value is the same keeps every line it had, a folded
    description and the comment beside an expansion rule included; a changed
    mapping is merged key by key at every depth; a changed list or scalar is
    written fresh under the comment above it; a key `new` lacks goes. The
    header above the first key stays. This is what lets the app change one
    line of a view somebody wrote by hand without reflowing the rest."""
    head, blocks = _blocks(old_text.splitlines(), 0)
    lines = list(head) + _merged(blocks, new, 0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines) + "\n"


def holds_one_list(path: Path) -> bool:
    try:
        return isinstance(read_data_file(path), list)
    except ModelFileError:
        return False


# ---------------------------------------------------------------------------
# Changing records, one or many, without writing anything yet.
# ---------------------------------------------------------------------------


class Refused(ValueError):
    """A record that cannot be changed here, with the reason in words."""


#: What the app writes above a harvested record it moved into a file of its
#: own, so the next reader knows why the file is there.
MOVED_HEADER = (
    "# Moved out of %s the first time it was edited in the app. The",
    "# business-layer import leaves alone a record outside that file. Clear",
    "# `source` when its owner confirms it, which takes it off the",
    "# harvested-estate drawing.",
)


def own_file(root: Path, type_name: str, entity_id: str) -> Path:
    return Path(root) / "10_MODEL" / ENTITY_TYPES[type_name].folder / ("%s.yaml" % entity_id)


def _text_of(path: Path, files: Dict[Path, Tuple[Optional[str], str]]) -> str:
    if path in files:
        return files[path][1]
    return path.read_text(encoding="utf-8-sig")


def _put(path: Path, before: Optional[str], after: str, files: Dict[Path, Tuple[Optional[str], str]]) -> None:
    """Record a file's new text, keeping what it held before the first change."""
    first = files[path][0] if path in files else before
    files[path] = (first, after)


def change(root: Path, type_name: str, entity_id: str, record: dict, values: Dict[str, Any],
           files: Dict[Path, Tuple[Optional[str], str]]) -> Tuple[Path, Optional[str]]:
    """Change one record where it lives, into `files` (path to its text
    before and after) rather than onto the disk, so many changes to one
    shared file are made on the one text and written once. Returns the file
    the record lives in afterward and a sentence when it moved there.

    The rules are `home_of`'s: a file of its own is merged, a shared file
    has the record's lines replaced, a harvested record moves into a file of
    its own, and one a shape made or an import rewrites is `Refused`."""
    home = home_of(type_name, record)
    if home.kind in ("imported", "generated"):
        raise Refused(home.note)
    before = _text_of(home.path, files)
    if home.kind == "own":
        after = "\n".join(merge_record(before.splitlines(), type_name, entity_id, values)) + "\n"
        _put(home.path, before, after, files)
        return home.path, None
    if home.kind == "shared":
        _put(home.path, before, replace_item(before, type_name, entity_id, values), files)
        return home.path, None
    target = own_file(root, type_name, entity_id)
    if target.exists() or target in files:
        raise Refused("%s would move to %s, which already exists" % (entity_id, target.name))
    lines = merge_record(item_lines(before, type_name, entity_id), type_name, entity_id, values)
    shared = home.path.relative_to(Path(root) / "10_MODEL").as_posix()
    header = [MOVED_HEADER[0] % shared] + list(MOVED_HEADER[1:])
    _put(target, None, "\n".join(header + lines) + "\n", files)
    _put(home.path, before, remove_item(before, type_name, entity_id), files)
    return target, "Moved out of %s into a file of its own, so the next import leaves it alone." % home.path.name


class Batch(NamedTuple):
    """What setting one field on many records would write, and to which."""

    #: Each file touched, with its text before (None for a new file) and after.
    files: Dict[Path, Tuple[Optional[str], str]]
    #: The records changed, by id.
    changed: List[str]
    #: The harvested records moved into a file of their own, by id.
    moved: List[str]
    #: The records that already said it.
    unchanged: List[str]
    #: The records it cannot change here, by id, with why.
    refused: List[Tuple[str, str]]


def settable_value(model, type_name: str, field: str, value: Any) -> Any:
    """The value a field can be set to on many records at once, checked:
    a field the type declares and a person sets, one of the field's words
    where it has a list, a record of the right type where it names one.
    Raises `Refused` saying which."""
    entity_type = ENTITY_TYPES.get(type_name)
    if entity_type is None:
        raise Refused("%r is not a kind of record" % type_name)
    spec = next((f for f in entity_type.fields if f.name == field), None)
    if spec is None or field == entity_type.pk:
        raise Refused("a %s has no field %s" % (entity_type.label, field))
    if field in UNASKED:
        raise Refused("%s is set by the shape a record is made on, not here" % field)
    if value in (None, "", []):
        raise Refused("a value to set %s to" % field)
    if field in LIST_FIELDS:
        return [str(v).strip() for v in (value if isinstance(value, (list, tuple)) else [value]) if str(v).strip()]
    text = str(value).strip()
    if spec.enum and text not in spec.enum:
        raise Refused("%s is not one of a %s's %s: %s" % (text, entity_type.label, field, ", ".join(spec.enum)))
    if spec.ref and model.get(spec.ref, text) is None:
        raise Refused("%s is not a %s here" % (text, ENTITY_TYPES[spec.ref].label))
    return text


def set_many(model, root: Path, type_name: str, ids: Sequence[str], field: str, value: Any) -> Batch:
    """One field set on many records, each changed where it lives, with
    nothing written: the caller writes `files` and puts them back if the
    model does not load afterward. A list field (`tags`) has the value
    added to what each record holds rather than put in its place, since a
    tag set on many records is one more tag on each."""
    value = settable_value(model, type_name, field, value)
    entity_type = ENTITY_TYPES[type_name]
    declared = {f.name for f in entity_type.fields}
    files: Dict[Path, Tuple[Optional[str], str]] = {}
    changed: List[str] = []
    moved: List[str] = []
    unchanged: List[str] = []
    refused: List[Tuple[str, str]] = []
    for entity_id in dict.fromkeys(str(i) for i in ids):
        record = model.get(type_name, entity_id)
        if record is None:
            refused.append((entity_id, "not a %s here" % entity_type.label))
            continue
        current = record.get(field)
        if field in LIST_FIELDS:
            have = _as_list(current) if current not in (None, "") else []
            wanted = have + [v for v in value if v not in have]
            if wanted == have:
                unchanged.append(entity_id)
                continue
            new_value: Any = wanted
        else:
            if _plain(current) == _plain(value):
                unchanged.append(entity_id)
                continue
            new_value = value
        values = {k: v for k, v in record.items() if k in declared and k != entity_type.pk}
        values[field] = new_value
        # Tried on a copy of what has been planned, so a refusal halfway
        # through a shared file leaves that file's earlier changes standing.
        trial = dict(files)
        try:
            _path, note = change(root, type_name, entity_id, record, values, trial)
        except Refused as exc:
            refused.append((entity_id, str(exc)))
            continue
        except KeyError:
            refused.append((entity_id, "no longer where it was read from; reload and try again"))
            continue
        files.clear()
        files.update(trial)
        changed.append(entity_id)
        if note:
            moved.append(entity_id)
    return Batch(files, changed, moved, unchanged, refused)
