"""Sketches: a diagram an architect builds by hand, written back as a query.

Every diagram here is a view, and a view is a query. That is right for the
twenty-odd standing questions, and wrong for the moment an architect wants
*this* picture: these nine things, drawn together, for a review on Thursday.
A sketch is that picture. It is a set of ids grown from the map, and what
this module does is write it back in the only form the repository keeps:

- as a view file whose scope is the explicit list of ids, so the diagram is
  a query like every other one, reviewable and regenerated on every render;
- or as a module, the entities rewritten as templates in the vocabulary of
  the shape that made them, so the next product gets the same part from the
  library instead of from a drawing.

Nothing in here draws. It produces the YAML text the rest of the engine
already knows how to read.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from pathlib import Path

from .archetype import ArchetypeError, substitute
from .loader import read_data_file
from .model import Model
from .modules import derive_needs
from .schema import ENTITY_TYPES, RELATION_TYPES


class SketchError(ValueError):
    pass


#: Fields that describe where a record came from, never what it is.
_META_FIELDS = {"_source_file", "_type", "archetype", "archetype_instance", "module"}

#: Relations that are implied by composition and never written into a part.
_IMPLIED_RELATIONS = {"product_includes_system"}

#: Relation to the template shorthand that stands for it: (relation, left
#: column, right column, shorthand key). The shorthand is what a person
#: would have written; a row is what the engine would have produced.
_SHORTHANDS = (
    ("system_uses_tech_service", "system_id", "tech_service_id", "uses"),
    ("system_governed_by_control", "system_id", "control_id", "controls"),
    ("system_subject_to_policy", "system_id", "policy_id", "policies"),
    ("data_governed_by_control", "data_asset_id", "control_id", "controls"),
    ("data_subject_to_policy", "data_asset_id", "policy_id", "policies"),
)

#: The vocabulary every shipped shape binds. A module written in these
#: tokens composes into any of them without being told anything more.
SHAPE_VOCABULARY = (
    "slug", "product_name", "name", "owner_org", "domain", "account", "region",
    "classification", "criticality", "vendor", "vendor_region",
)


# ---------------------------------------------------------------------------
# YAML out. The engine reads a YAML subset; this writes the same subset, so
# what it produces round-trips through `yamlish.loads` and reads like a file
# a person wrote.
# ---------------------------------------------------------------------------

_BARE = re.compile(r"^[A-Za-z0-9_./ -]+$")


def _scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "":
        return '""'
    if text.lower() in ("true", "false", "null", "yes", "no", "~") or text.strip() != text:
        return '"%s"' % text.replace('"', '\\"')
    if _BARE.match(text) and not text.isdigit() and not text.startswith(("-", " ")):
        return text
    return '"%s"' % text.replace("\\", "\\\\").replace('"', '\\"')


def _flow_list(items: Sequence[Any]) -> str:
    return "[%s]" % ", ".join(_scalar(item) for item in items)


def _key(key: Any) -> str:
    """A mapping key as written. A field name goes as it is; a key made from
    what a person typed -- a position on the canvas, keyed by a boundary
    named `Lending: Ops` -- is quoted when a reader would take it apart."""
    text = str(key)
    if (not text or text.strip() != text or ": " in text or text.endswith(":") or " #" in text
            or text[0] in "-?:,[]{}#&*!|>'\"%@`"):
        return '"%s"' % text.replace("\\", "\\\\").replace('"', '\\"')
    return text


def dump_yaml(value: Any, indent: int = 0) -> List[str]:
    """Lines of YAML for a dict, list or scalar, in the engine's subset."""
    pad = "  " * indent
    lines: List[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, dict):
                if not item:
                    lines.append("%s%s: {}" % (pad, _key(key)))
                    continue
                lines.append("%s%s:" % (pad, _key(key)))
                lines.extend(dump_yaml(item, indent + 1))
            elif isinstance(item, list):
                if not item:
                    lines.append("%s%s: []" % (pad, _key(key)))
                elif all(not isinstance(x, (dict, list)) for x in item):
                    lines.append("%s%s: %s" % (pad, _key(key), _flow_list(item)))
                else:
                    lines.append("%s%s:" % (pad, _key(key)))
                    lines.extend(dump_yaml(item, indent + 1))
            elif isinstance(item, str) and "\n" in item:
                # Literal, its last break stripped: the words come back as
                # they were written. Folded (`>`) joined a shape's name and
                # its caption into one line on the way back in.
                lines.append("%s%s: |-" % (pad, _key(key)))
                for part in item.rstrip("\n").split("\n"):
                    lines.append("%s  %s" % (pad, part) if part else "")
            else:
                lines.append("%s%s: %s" % (pad, _key(key), _scalar(item)))
        return lines
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                inner = dump_yaml(item, indent + 1)
                if inner:
                    lines.append("%s- %s" % (pad, inner[0].lstrip()))
                    lines.extend(inner[1:])
                else:
                    lines.append("%s- {}" % pad)
            elif isinstance(item, list):
                lines.append("%s- %s" % (pad, _flow_list(item)))
            else:
                lines.append("%s- %s" % (pad, _scalar(item)))
        return lines
    return ["%s%s" % (pad, _scalar(value))]


def yaml_text(value: Any, header: Sequence[str] = ()) -> str:
    lines = ["# %s" % line if line else "#" for line in header]
    if lines:
        lines.append("")
    lines.extend(dump_yaml(value))
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# A sketch as a view.
# ---------------------------------------------------------------------------

def _locate(model: Model, ids: Iterable[str]) -> List[Tuple[str, str, dict]]:
    """(type, id, record) for every id, in the order given, refusing unknowns."""
    out: List[Tuple[str, str, dict]] = []
    seen = set()
    for raw in ids:
        entity_id = str(raw).strip()
        if not entity_id or entity_id in seen:
            continue
        seen.add(entity_id)
        found = model.find(entity_id)
        if found is None:
            raise SketchError("unknown entity %r" % entity_id)
        out.append((found[0], entity_id, found[1]))
    if not out:
        raise SketchError("a sketch needs at least one entity")
    return out


def view_from_sketch(
    model: Model,
    ids: Sequence[str],
    view_id: str,
    title: str,
    description: str = "",
    category: str = "Sketches",
    group_by: Sequence[str] = (),
    color_by: Optional[str] = None,
    layout: str = "LR",
    edges: Optional[Sequence[dict]] = None,
) -> dict:
    """The view data for a sketch: an explicit scope, and every edge between
    the things in it.

    The scope is a list of ids per type rather than a clever predicate on
    purpose. A sketch is a choice, and a choice written as `id_in` is one a
    reviewer can read without running anything. Generalizing it into a
    query is the architect's next move, in the editor, if the picture turns
    out to be a standing question.
    """
    located = _locate(model, ids)
    by_type: Dict[str, List[str]] = {}
    for type_name, entity_id, _record in located:
        by_type.setdefault(type_name, []).append(entity_id)
    if edges is None:
        edges = [{"via": "interfaces"}, {"via": "owner"}, {"via": "source_of_truth"}]
        edges += [{"via": name} for name in RELATION_TYPES]
    data: Dict[str, Any] = {
        "view_id": view_id,
        "title": title,
        "category": category,
        "kind": "diagram",
        "description": description.strip() or (
            "A sketch: %d things chosen by hand and drawn together. The scope is the "
            "list itself; widen it into a query when the picture becomes a standing "
            "question." % len(located)
        ),
        "layout": layout if layout in ("LR", "TB") else "LR",
        "node_label": "name",
        "renderers": ["mermaid"],
        "scope": {
            "include": [
                {"type": type_name, "where": {"id_in": sorted(listed)}}
                for type_name, listed in sorted(by_type.items())
            ]
        },
        "edges": list(edges),
    }
    if group_by:
        data["group_by"] = list(group_by)
    if color_by:
        data["style"] = {"color_by": color_by}
    data["limits"] = {"max_nodes": max(60, len(located) * 2)}
    return data


def view_text_from_sketch(model: Model, **kwargs) -> str:
    data = view_from_sketch(model, **kwargs)
    header = (
        "Written from a sketch in the app. The scope is an explicit list: this",
        "diagram is a choice, not a query, until someone widens it into one.",
    )
    return yaml_text(data, header)


# ---------------------------------------------------------------------------
# A sketch as a module.
# ---------------------------------------------------------------------------

def guess_slug(ids: Iterable[str]) -> Optional[str]:
    """The token the ids share: `SYS-SCREENING-GATEWAY`, `INT-SCREENING-…`
    give `screening`. None when they share nothing."""
    counts: Counter = Counter()
    for entity_id in ids:
        parts = str(entity_id).split("-")
        if len(parts) >= 3:
            counts[parts[1]] += 1
    if not counts:
        return None
    token, seen = counts.most_common(1)[0]
    return token.lower() if seen >= 2 or len(counts) == 1 else None


def _shape_of(model: Model, instance: dict):
    """The shape an instance is on: a shared one, or the shape of one behind
    a product assembled from parts."""
    archetype_id = str(instance.get("archetype") or "")
    return model.archetypes.get(archetype_id) or getattr(model, "composed", {}).get(archetype_id)


def _bindings_for(model: Model, record: dict) -> Dict[str, Any]:
    """What the shape bound when it made this record, if a shape made it."""
    instance = _instance_source(model, record)
    if not instance:
        return {}
    archetype = _shape_of(model, instance)
    bindings: Dict[str, Any] = {}
    if archetype is not None:
        for param in archetype.parameters:
            if param.default is not None:
                bindings[param.name] = param.default
    bindings.update(instance.get("parameters") or {})
    if instance.get("name"):
        bindings.setdefault("name", instance["name"])
    # The same instance bindings expansion adds, so a default written as
    # `status: "{status}"` folds to what the instance said and the field is
    # dropped from the template the way a literal default's was.
    if instance.get("status"):
        bindings.setdefault("status", instance["status"])
    return bindings


def _instance_source(model: Model, record: dict) -> dict:
    """The instance file as written, parameters and all.

    The loaded record keeps what the instance *is*; what it was *told* lives
    only in its file, so that is read back here.
    """
    instance_id = record.get("archetype_instance")
    if not instance_id:
        return {}
    found = model.find(str(instance_id))
    if found is None:
        return {}
    _type, instance = found
    source = instance.get("_source_file")
    if not source:
        return dict(instance)
    try:
        raw = read_data_file(Path(source))
    except Exception:  # noqa: BLE001 - a missing file means no bindings, not a crash
        return dict(instance)
    if isinstance(raw, dict):
        merged = dict(instance)
        merged.update(raw)
        return merged
    return dict(instance)


def _entity_defaults_for(model: Model, record: dict, type_name: str) -> Dict[str, Any]:
    """The shape's `entity_defaults` folded for this type, as templates."""
    instance = _instance_source(model, record)
    archetype = _shape_of(model, instance) if instance else None
    if archetype is None:
        return {}
    defaults = dict(getattr(archetype, "entity_defaults", {}) or {})
    folded: Dict[str, Any] = {}
    folded.update(defaults.get("all") or {})
    folded.update(defaults.get(type_name) or {})
    return folded


def _folded(template: Any, bindings: Dict[str, Any]) -> Any:
    """A shape default with its tokens filled in, or None where one is unbound.

    The other direction from tokenizing. `status: "{status}"` folds to what
    the instance said, and comparing that to the record is what lets the
    field be dropped -- turning every "Planned" in a description back into
    `{status}` is not something anyone wants done to a description.
    """
    try:
        return substitute(template, bindings)
    except ArchetypeError:
        return None


def _tokenize(value: Any, tokens: Sequence[Tuple[str, str]]) -> Any:
    """Replace bound values with their tokens, longest value first."""
    if isinstance(value, str):
        out = value
        for bound, token in tokens:
            out = out.replace(bound, token)
        return out
    if isinstance(value, list):
        return [_tokenize(item, tokens) for item in value]
    return value


def _token_table(bindings: Dict[str, Any]) -> List[Tuple[str, str]]:
    table: List[Tuple[str, str]] = []
    values = {}
    for name, value in bindings.items():
        if isinstance(value, str):
            values.setdefault(value, name)
    for name, value in bindings.items():
        if not isinstance(value, str) or len(value) < 3:
            continue
        # `name` is the instance's name, which every shape also binds as
        # `product_name`; the token a person would write is the latter.
        if name == "name" and values.get(value) != name:
            continue
        # `status` is bound so a shape default folds, not so that the word
        # "Planned" in a description turns into a token.
        if name == "status":
            continue
        upper = value.upper()
        if upper != value:
            table.append((upper, "{%s|upper}" % name))
        table.append((value, "{%s}" % name))
    # Longest bound value first, so `prod-lending` goes before `lending`.
    table.sort(key=lambda pair: -len(pair[0]))
    return table


def module_from_sketch(
    model: Model,
    ids: Sequence[str],
    module_id: str,
    name: str,
    description: str,
    category: str = "Other",
    slug: Optional[str] = None,
    product_name: Optional[str] = None,
    optional: bool = True,
) -> Tuple[dict, dict]:
    """A module whose templates are these entities, written in the vocabulary
    of the shape that made them.

    For a generated entity the shape's bindings are known, so every bound
    value becomes its token and every field the shape's `entity_defaults`
    would supply is dropped: the module says only what makes its entities
    different, which is the rule the shipped modules follow. For a
    hand-authored entity only `slug` and `product_name` can be tokenized,
    and the fields stay as they are.

    Returns the module data and a report: the tokens used, what was dropped,
    and what was recovered from relations.
    """
    located = _locate(model, ids)
    chosen = {entity_id for _t, entity_id, _r in located}
    if not module_id or not name:
        raise SketchError("a module needs a module_id and a name")
    if not description.strip():
        raise SketchError("a module needs a description; it is what the form shows")

    # One set of tokens for the whole part. A sketch that spans two products
    # gets the first product's vocabulary, which the report says.
    bindings: Dict[str, Any] = {}
    for _type, _id, record in located:
        bindings = _bindings_for(model, record)
        if bindings:
            break
    if slug:
        bindings["slug"] = slug
    if product_name:
        bindings["product_name"] = product_name
    if "slug" not in bindings:
        guessed = guess_slug(chosen)
        if guessed:
            bindings["slug"] = guessed
    tokens = _token_table(bindings)
    used: Counter = Counter()

    def tok(value: Any) -> Any:
        before = value
        after = _tokenize(value, tokens)
        if after != before:
            for _bound, token in tokens:
                if isinstance(after, str) and token in after:
                    used[token] += 1
                elif isinstance(after, list) and any(isinstance(x, str) and token in x for x in after):
                    used[token] += 1
        return after

    # Relations among and out of the chosen things, as shorthands where the
    # engine has one, as rows otherwise.
    shorthand_rows: Dict[str, Dict[str, List[str]]] = {}
    relation_rows: Dict[str, List[dict]] = {}
    recovered = 0
    for relation_name, spec in RELATION_TYPES.items():
        if relation_name in _IMPLIED_RELATIONS:
            continue
        shorthand = next((s for s in _SHORTHANDS if s[0] == relation_name), None)
        for row in model.relation_rows(relation_name):
            left = str(row.get(spec.left_column) or "")
            right = str(row.get(spec.right_column) or "")
            if left not in chosen:
                continue
            if shorthand is not None and right not in chosen:
                # A system using a platform service, or governed by a control
                # outside the sketch: written on the template.
                shorthand_rows.setdefault(left, {}).setdefault(shorthand[3], []).append(right)
                recovered += 1
                continue
            if right not in chosen:
                continue
            kept = {spec.left_column: tok(left), spec.right_column: tok(right)}
            if spec.qualifier and row.get(spec.qualifier):
                kept[spec.qualifier] = row[spec.qualifier]
            relation_rows.setdefault(relation_name, []).append(kept)
            recovered += 1

    provides: Dict[str, List[dict]] = {}
    dropped: Counter = Counter()
    for type_name, entity_id, record in located:
        spec = ENTITY_TYPES[type_name]
        defaults = _entity_defaults_for(model, record, type_name)
        template: Dict[str, Any] = {}
        for field in spec.fields:
            key = field.name
            value = record.get(key)
            if key in _META_FIELDS or value in (None, "", []):
                continue
            if key in defaults and (
                _tokenize(value, tokens) == _tokenize(defaults[key], tokens)
                or _folded(defaults[key], bindings) == value
            ):
                dropped[key] += 1
                continue
            template[key] = tok(value)
        # The primary key first, then the name: the order a person writes.
        ordered: Dict[str, Any] = {spec.pk: template.pop(spec.pk, tok(entity_id))}
        if "name" in template:
            ordered["name"] = template.pop("name")
        ordered.update(template)
        for key, listed in (shorthand_rows.get(entity_id) or {}).items():
            ordered[key] = sorted(set(tok(x) for x in listed))
        provides.setdefault(type_name, []).append(ordered)

    parameters = []
    for token in sorted(used):
        param = token.strip("{}").split("|")[0]
        if param in ("slug", "product_name", "name"):
            continue
        if any(p["name"] == param for p in parameters):
            continue
        parameters.append({
            "name": param,
            "required": True,
            "description": "Bound by the shape this part is composed into, or by the instance.",
        })

    # What the part reads from the shape rather than asking for: the slug,
    # the product name, whatever the tokenizer wrote in from the bindings.
    # Declared, so the part loads, and so `terrane validate` can refuse a shape
    # that cannot supply them. Derived from the templates just written, which
    # is the one place the answer is certain.
    needs = derive_needs({
        "module_id": module_id, "parameters": parameters,
        "provides": provides, "relations": relation_rows,
    })

    data: Dict[str, Any] = {
        "module_id": module_id,
        "name": name,
        "category": category or "Other",
        "description": description.strip(),
        "optional": bool(optional),
    }
    if parameters:
        data["parameters"] = parameters
    if needs:
        data["needs"] = needs
    data["provides"] = provides
    if relation_rows:
        data["relations"] = relation_rows

    report = {
        "tokens": sorted(used),
        "slug": bindings.get("slug"),
        "dropped": dict(dropped),
        "recovered": recovered,
        "entities": len(located),
        "generatedFrom": next(
            (str(r.get("archetype_instance")) for _t, _i, r in located if r.get("archetype_instance")),
            None,
        ),
    }
    return data, report


def module_text_from_sketch(model: Model, **kwargs) -> Tuple[str, dict]:
    data, report = module_from_sketch(model, **kwargs)
    header = [
        "Written from a sketch in the app, in the vocabulary of the shape that",
        "made these entities. Fields the shape's entity_defaults supply were",
        "dropped; what is left is what makes this part different.",
    ]
    if report["tokens"]:
        header.append("")
        header.append("Tokens: " + ", ".join(report["tokens"]))
    return yaml_text([data], header), report
