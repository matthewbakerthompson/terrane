"""A view placed on another as a boundary, kept in step with it.

A diagram drawn on the canvas places what the estate already draws: Network
Topology as the ground two new systems stand on, rather than the same
thirty-three network parts selected again by hand on every diagram that
needs them. The diagram's file says `places: [{view: network-topology}]`,
and each time views are loaded the placed view's scope, lines and
boundaries are read from that view as it is now. Change the network there,
and every diagram it is placed on follows; nothing is copied into the file.

A place can leave some of the placed view out (`leave_out`, a field and the
values whose records stay off this diagram: the accounts nobody here needs)
or keep only some of it (`only`), and `parts: false` keeps the boundaries
without the view's own boxes, so only what was placed inside them is drawn.
What the view expands, pins and hides is its own business and is not
carried over: a placed view is the ground, not the drawing. Nor are its
positions: where the placed view's boxes sit on this diagram is this
diagram's `positions`, so arranging them here moves nothing anywhere else.

The view that places keeps its own fields under `own`, so the merge can be
made again from them whenever the list of views grows (the estate's own
views are read before the shipped ones they may place), and never twice.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence

#: The keys a place may have. Anything else is refused by the schema.
PLACE_KEYS = ("view", "only", "leave_out", "parts")


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(v) for v in value]
    return [str(value)]


def places_of(view) -> List[dict]:
    """The view's places, each a mapping with a `view`; anything else in the
    list is left for validation to name."""
    found = []
    for place in getattr(view, "places", ()) or ():
        if isinstance(place, dict) and str(place.get("view") or "").strip():
            found.append(place)
    return found


def _narrow_where(where: dict, only: dict, leave_out: dict) -> Optional[dict]:
    """A clause's `where` with this place's limits added. A field the clause
    already filters on is narrowed in the same key, since a `where` holds a
    key once: `cloud_account: [a, b]` kept only to `a` is `cloud_account: a`.
    None when the limit cannot be said in one key (a field the clause asks
    `exists` of); the caller then excludes instead."""
    out = dict(where or {})
    for field, values in (only or {}).items():
        wanted = _as_list(values)
        if field not in out:
            out[field] = wanted
            continue
        have = out[field]
        if isinstance(have, dict) and "not" in have:
            out[field] = [v for v in wanted if v not in set(_as_list(have["not"]))]
        elif isinstance(have, dict):
            return None
        else:
            out[field] = [v for v in _as_list(have) if v in set(wanted)]
    for field, values in (leave_out or {}).items():
        gone = _as_list(values)
        if not gone:
            continue
        if field not in out:
            out[field] = {"not": gone}
            continue
        have = out[field]
        if isinstance(have, dict) and "not" in have:
            out[field] = {"not": _as_list(have["not"]) + [v for v in gone if v not in set(_as_list(have["not"]))]}
        elif isinstance(have, dict):
            return None
        else:
            out[field] = [v for v in _as_list(have) if v not in set(gone)]
    return out


def placed_clauses(target, place: dict) -> List[dict]:
    """The placed view's `include`, limited as the place says."""
    if place.get("parts") is False:
        return []
    only = place.get("only") if isinstance(place.get("only"), dict) else {}
    leave_out = place.get("leave_out") if isinstance(place.get("leave_out"), dict) else {}
    out = []
    for clause in target.scope.get("include") or []:
        if not isinstance(clause, dict):
            continue
        where = _narrow_where(clause.get("where") or {}, only, leave_out)
        if where is None:
            # Said as an exclusion instead: the same records stay off, and
            # it is the one place a placed limit can reach the diagram's
            # own boxes, which is said in the method.
            where = clause.get("where") or {}
        merged = {k: v for k, v in clause.items() if k != "where"}
        if where:
            merged["where"] = where
        out.append(merged)
    return out


def _merged(base, by_id: Dict[str, Any]):
    """The view `base` with each view it places merged in."""
    targets = []
    for place in places_of(base):
        target = by_id.get(str(place["view"]))
        # An unknown view, one placing itself, or one that places others is
        # named by validation (view.unknown_place, view.nested_place); the
        # diagram draws without it rather than refusing to load.
        if target is None or target.view_id == base.view_id or places_of(target):
            continue
        targets.append((target, place))
    if not targets:
        return base._replace(own=base)

    scope = {k: v for k, v in base.scope.items()}
    include = list(base.scope.get("include") or [])
    for target, place in targets:
        include.extend(placed_clauses(target, place))
    if include:
        scope["include"] = include

    edges = list(base.edges)
    seen = {str(e.get("via")) for e in edges if isinstance(e, dict)}
    for target, _place in targets:
        for edge in target.edges:
            via = str(edge.get("via")) if isinstance(edge, dict) else ""
            if via and via not in seen:
                seen.add(via)
                edges.append(edge)

    first = targets[0][0]
    # The boundaries are the placed view's unless the diagram groups by
    # something of its own; with them come its direction and the order its
    # values are laid out in, which were chosen for those boundaries.
    grouped = bool(base.group_by)
    style = {}
    for target, _place in reversed(targets):
        style.update(target.style or {})
    style.update(base.style or {})
    return base._replace(
        scope=scope,
        edges=edges,
        group_by=base.group_by if grouped else first.group_by,
        layout=base.layout if grouped else first.layout,
        lanes=base.lanes if grouped else first.lanes,
        group_direction=base.group_direction or (None if grouped else first.group_direction),
        style=style,
        own=base,
    )


def with_places(views: Iterable[Any]) -> List[Any]:
    """Every view, each one that places another merged with it as that view
    is now. Made from each view's own fields, so it may be run again on a
    longer list and gives the same answer for the same views."""
    own = [getattr(v, "own", None) or v for v in views]
    by_id = {v.view_id: v for v in own}
    return [_merged(v, by_id) if places_of(v) else v for v in own]


def attach(view, views: Sequence[Any]):
    """One view merged against a list it is not in yet: the canvas's
    unsaved drawing, previewed against the estate's views."""
    by_id = {(getattr(v, "own", None) or v).view_id: (getattr(v, "own", None) or v) for v in views}
    base = getattr(view, "own", None) or view
    by_id[base.view_id] = base
    return _merged(base, by_id) if places_of(base) else base


def problems(view, by_id: Dict[str, Any]) -> List[str]:
    """What is wrong with a view's places, in words, for validation."""
    out = []
    raw = getattr(getattr(view, "own", None) or view, "places", ()) or ()
    for index, place in enumerate(raw):
        if not isinstance(place, dict) or not str(place.get("view") or "").strip():
            out.append("place %d names no view" % (index + 1))
            continue
        name = str(place["view"])
        target = by_id.get(name)
        if target is None:
            out.append("places %s, which is not a view here" % name)
        elif target.view_id == view.view_id:
            out.append("places itself")
        elif places_of(getattr(target, "own", None) or target):
            out.append("places %s, which places others; a placed view is placed as it is drawn on its own"
                       % name)
    return out
