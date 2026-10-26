"""The levels an estate is read at, and the way between them.

A large estate is read landscape, domain, system, and where a system runs,
and each of those is already a view about one thing: a view with a
`parameters` entry is drawn for any subject it is told. What was missing was
the way between them. A box on one drawing did not say which drawings are
about it, and a drawing about one system did not say what it sits in.

This module answers both from the views themselves, so nothing names a view
here and an estate's own views take part as soon as they are written:

- `diagrams_of`: the views about a record (a parameter of its type), about
  what contains it (a product that includes a system, a capability's parent,
  a data asset's source of truth), and about a value it carries (a view whose
  parameter is a `field`, such as the landscape of one business domain).
- `way_up`: the levels above a view about one thing, following each view's
  `up`, each bound to what the subject sits in.
- `across`: the other views about the same subject, for the tabs beside its
  picker.

Every listed view is bound and resolved, so a count goes beside it and a
view that would draw the subject alone says so instead of opening empty.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from .model import Model
from .query import Parameter, View, ViewError, bind, field_values, render_targets, resolve
from .schema import ENTITY_TYPES, RELATION_TYPES

#: Fields whose name is not the word for them, where a level is named after
#: the field: "Its business domain", not "Its company domain".
FIELD_WORDS = {"company_domain": "business domain"}


def field_words(field: str) -> str:
    if field in FIELD_WORDS:
        return FIELD_WORDS[field]
    words = field[:-3] if field.endswith("_id") else field
    return words.replace("_", " ")


def subject_parameter(view: View) -> Optional[Parameter]:
    """The parameter a view is about, when it has one a picker can offer: a
    record of a type, or a value of a field. A bare name names neither."""
    for param in view.parameters:
        if param.type or param.field:
            return param
    return None


def views_about(views: Sequence[View], type_name: str = "", field: str = "") -> List[Tuple[View, Parameter]]:
    """The views about one record of a type, or about one value of a field,
    in the order the views are listed."""
    out = []
    for view in views:
        param = subject_parameter(view)
        if param is None:
            continue
        if (type_name and param.type == type_name) or (field and param.field == field):
            out.append((view, param))
    return out


def short_title(view: View, param: Parameter) -> str:
    """A view's title without its subject: "{system} — Architecture" is
    "Architecture" in a list that already says which system."""
    token = "{%s}" % param.name
    rest = view.title.replace(token, "").strip(" —–-:·")
    return rest or view.title.replace(token, param.name.replace("_", " "))


def _readable(model: Model, param: Parameter, value: str) -> str:
    if param.type:
        record = model.get(param.type, value)
        if record is not None:
            return str(record.get("name") or value)
    return value


def drawn(model: Model, view: View, param: Optional[Parameter], value: str = "") -> dict:
    """One view bound to one subject, as a list shows it: its title, how many
    boxes it draws, and why it cannot be drawn, if it cannot."""
    entry: Dict[str, Any] = {
        "viewId": view.view_id,
        "kind": view.kind,
        "description": view.description,
        "parameter": param.name if param else "",
        "value": value,
        "label": _readable(model, param, value) if param else view.title,
        "short": short_title(view, param) if param else view.title,
        "title": view.title,
        "nodes": 0,
        "problem": "",
    }
    try:
        bound = bind(view, {param.name: value}, model) if param else view
        entry["title"] = bound.title
        entry["nodes"] = len(resolve(model, bound).nodes)
    except ViewError as exc:
        entry["problem"] = str(exc)
    return entry


def containers(model: Model, type_name: str, record: dict) -> List[Tuple[str, str, str]]:
    """What a record sits in, as (type, id, words): the records whose
    `*_includes_*` relation names it (a product including a system), and the
    records its reference fields name (a capability's parent, a data asset's
    source of truth). The owner is not one: an org unit owns, it does not
    contain, and nothing is drawn about one."""
    pk = ENTITY_TYPES[type_name].pk
    entity_id = str(record.get(pk) or "")
    out: List[Tuple[str, str, str]] = []
    for name, spec in RELATION_TYPES.items():
        if spec.right != type_name or "_includes_" not in name:
            continue
        for row in model.relation_rows(name):
            if str(row.get(spec.right_column) or "") == entity_id and row.get(spec.left_column):
                out.append((spec.left, str(row[spec.left_column]), ENTITY_TYPES[spec.left].label))
    for spec in ENTITY_TYPES[type_name].fields:
        target = record.get(spec.name)
        if spec.ref and target and spec.ref != "org_units" and not isinstance(target, (list, dict)):
            out.append((spec.ref, str(target), field_words(spec.name)))
    seen = set()
    unique = []
    for item in out:
        if (item[0], item[1]) not in seen:
            seen.add((item[0], item[1]))
            unique.append(item)
    return unique


def diagrams_of(model: Model, views: Sequence[View], entity_id: str) -> List[dict]:
    """The views a person can open from one box, in groups: about it, about
    each thing it sits in, and about each value it carries that a view is
    drawn for. A group with no view is left out; a box with none of them has
    an empty list, which the app says plainly."""
    found = model.find(entity_id)
    if found is None:
        return []
    type_name, record = found
    groups: List[dict] = []
    about = [drawn(model, view, param, entity_id) for view, param in views_about(views, type_name=type_name)]
    if about:
        groups.append({"kind": "about", "head": "About it", "name": str(record.get("name") or entity_id),
                       "subject": entity_id, "items": about})
    for other_type, other_id, words in containers(model, type_name, record):
        listed = views_about(views, type_name=other_type)
        other = model.get(other_type, other_id)
        if not listed or other is None:
            continue
        name = str(other.get("name") or other_id)
        groups.append({"kind": "contains", "head": "Its %s" % words, "name": name, "subject": other_id,
                       "items": [drawn(model, view, param, other_id) for view, param in listed]})
    for field in _fields_drawn(views):
        value = record.get(field)
        if value in (None, "") or isinstance(value, (list, dict)):
            continue
        # Only the views drawn for that value: a capability's domain is
        # Originations, a word no system carries, and a landscape of the
        # systems in it would open on nothing.
        items = [drawn(model, view, param, str(value)) for view, param in views_about(views, field=field)
                 if str(value) in subject_choices(model, view, param)]
        if items:
            groups.append({"kind": "field", "head": "Its %s" % field_words(field), "name": str(value),
                           "subject": str(value), "items": items})
    return groups


def _fields_drawn(views: Sequence[View]) -> List[str]:
    out: List[str] = []
    for view in views:
        param = subject_parameter(view)
        if param is not None and param.field and param.field not in out:
            out.append(param.field)
    return out


def boundary_diagrams(model: Model, views: Sequence[View], field: str, value: str) -> List[dict]:
    """The views about one value of a field, for a boundary that is that
    value: the Servicing boundary on the landscape opens Servicing's own."""
    if not value or field not in _fields_drawn(views):
        return []
    return [drawn(model, view, param, value) for view, param in views_about(views, field=field)
            if value in subject_choices(model, view, param)]


def _value_above(model: Model, above: Parameter, record: Optional[Tuple[str, dict]],
                 param: Optional[Parameter], value: str) -> str:
    """What a level above is drawn for, read off the subject: the value of the
    field it takes, or the record of its type the subject sits in."""
    if above.field:
        if record is not None:
            got = record[1].get(above.field)
            return "" if got in (None, "") or isinstance(got, (list, dict)) else str(got)
        return value if param is not None and param.field == above.field else ""
    if above.type and record is not None:
        for other_type, other_id, _words in containers(model, record[0], record[1]):
            if other_type == above.type:
                return other_id
    return ""


def way_up(model: Model, views: Sequence[View], view: View, supplied: Dict[str, str]) -> List[dict]:
    """The levels above a view about one thing, outermost first, each bound to
    what the subject sits in: for a system's architecture, the application
    landscape and then its domain's landscape. A level the subject has no
    value for (a system no domain names) is passed over, and the chain goes
    on above it; a view `up` names that is not here ends it."""
    by_id = {v.view_id: v for v in views}
    param = subject_parameter(view)
    value = str(supplied.get(param.name) or "") if param is not None else ""
    record = None
    if param is not None and param.type and value:
        found = model.find(value)
        record = found if found is not None and found[0] == param.type else None
    levels: List[dict] = []
    seen = {view.view_id}
    current = view
    while current.up and current.up in by_id and current.up not in seen:
        above = by_id[current.up]
        seen.add(above.view_id)
        above_param = subject_parameter(above)
        if above_param is not None:
            bound_to = _value_above(model, above_param, record, param, value)
            if bound_to:
                levels.append(drawn(model, above, above_param, bound_to))
        elif not above.parameters:
            levels.append(drawn(model, above, None))
        current = above
    return list(reversed(levels))


def across(views: Sequence[View], view: View) -> List[dict]:
    """The views about the same kind of subject as this one, this one marked:
    a system's architecture beside its hub, its processes and its
    governance."""
    param = subject_parameter(view)
    if param is None:
        return []
    listed = views_about(views, type_name=param.type or "", field=param.field or "")
    if len(listed) < 2:
        return []
    return [{"viewId": other.view_id, "parameter": other_param.name, "short": short_title(other, other_param),
             "description": other.description, "current": other.view_id == view.view_id}
            for other, other_param in listed]


def subject_choices(model: Model, view: View, param: Parameter) -> List[str]:
    """What a picker offers for a parameter that is a field's value: the
    values `render_for` draws it for when it says so, else every value the
    field takes."""
    spec = view.render_for or {}
    if spec.get("field") == param.field and spec.get("type") in ENTITY_TYPES:
        return [value for _name, value in render_targets(model, view)]
    return field_values(model, param.field or "")
