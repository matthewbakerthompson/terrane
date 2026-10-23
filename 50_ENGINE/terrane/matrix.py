"""A report drawn as a grid: one kind of thing down the side, another across
the top, and in each cell what joins them.

The frameworks matrix is the case that asked for it: every capability domain
against every framework, in one view, so that where each framework lands can
be seen at once rather than in a landscape per framework. A cell carries two
things, kept apart because they answer different questions. The **mark** is a
link between the row and the column themselves, with its qualifier: Payments
is governed by PCI DSS. The **count** is how many things under the row are
linked to the column by another relation: eighteen of the capabilities inside
Payments are placed in BIAN. A row counts what sits under it by walking a
reference field up, so the domains need not repeat their children's links.

Declared on a report view under `style.matrix`:

    style:
      matrix:
        rows: {capability_level: L0}       # which of the view's things are rows
        group: capability_tier             # rows are sectioned by this field
        columns: frameworks                # the entity type across the top
        roll_up: parent_capability_id      # what a row counts under it
        mark: capability_aligns_to_framework
        count: capability_references_framework

Computed from the resolved graph alone, so the app, the SVG drawing and the
Markdown table are the same grid.
"""

from __future__ import annotations

from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple

from .palette import ORDINAL
from .schema import ENTITY_TYPES


class Column(NamedTuple):
    key: str
    label: str
    #: A second line under the name, from the column's `kind_field`.
    detail: str
    total: int


class Row(NamedTuple):
    key: str
    label: str
    #: How many things sit under the row, for the reader to weigh a count by.
    size: int
    total: int


class Group(NamedTuple):
    name: str
    rows: Sequence[Row]


class Cell(NamedTuple):
    #: The qualifier on the link between the row and the column, or "".
    mark: str
    #: How many things under the row are linked to the column.
    count: int


class Matrix(NamedTuple):
    columns: Sequence[Column]
    groups: Sequence[Group]
    cells: Dict[Tuple[str, str], Cell]
    #: The relation kinds, for a legend: what a mark is and what is counted.
    mark: str
    count: str

    def as_dict(self) -> dict:
        return {
            "columns": [c._asdict() for c in self.columns],
            "groups": [{"name": g.name, "rows": [r._asdict() for r in g.rows]} for g in self.groups],
            "cells": [{"row": r, "column": c, "mark": cell.mark, "count": cell.count}
                      for (r, c), cell in sorted(self.cells.items())],
            "mark": self.mark,
            "count": self.count,
            "marks": sorted({cell.mark for cell in self.cells.values() if cell.mark}),
        }


def spec_of(view) -> Optional[dict]:
    spec = (getattr(view, "style", None) or {}).get("matrix")
    return spec if isinstance(spec, dict) else None


def _wanted(record: dict, rows: dict) -> bool:
    for field, expected in (rows or {}).items():
        allowed = expected if isinstance(expected, (list, tuple)) else [expected]
        if str(record.get(field) or "") not in [str(v) for v in allowed]:
            return False
    return True


def _group_order(field: str, values: Sequence[str]) -> List[str]:
    order = list(ORDINAL.get(field, ()))
    for entity_type in ENTITY_TYPES.values():
        for spec in entity_type.fields:
            if spec.name == field and getattr(spec, "enum", None):
                order = order or list(spec.enum)
    known = [v for v in order if v in values]
    return known + sorted(v for v in values if v not in known)


def matrix_of(graph) -> Optional[Matrix]:
    """The grid a view's `style.matrix` asks for, or None when it asks for
    none."""
    spec = spec_of(graph.view)
    if spec is None:
        return None
    columns_type = str(spec.get("columns") or "")
    roll_up = str(spec.get("roll_up") or "")
    mark_kind = str(spec.get("mark") or "")
    count_kind = str(spec.get("count") or "")
    group_field = str(spec.get("group") or "")
    by_key = {node.key: node for node in graph.nodes}
    column_nodes = [n for n in graph.nodes if n.entity_type == columns_type]
    row_nodes = [n for n in graph.nodes if n.entity_type != columns_type and _wanted(n.record, spec.get("rows"))]
    row_keys = {n.key for n in row_nodes}

    def row_of(key: str) -> Optional[str]:
        """The row a thing counts toward: itself when it is one, else the
        first row up its chain of `roll_up`."""
        seen = set()
        while key and key not in seen:
            if key in row_keys:
                return key
            seen.add(key)
            node = by_key.get(key)
            key = str(node.record.get(roll_up) or "") if node is not None and roll_up else ""
        return None

    marks: Dict[Tuple[str, str], str] = {}
    counted: Dict[Tuple[str, str], set] = {}
    column_keys = {n.key for n in column_nodes}
    for edge in graph.edges:
        a, b = edge.source, edge.target
        if b in row_keys and a in column_keys:
            a, b = b, a
        if a in column_keys and b not in column_keys:
            a, b = b, a
        if b not in column_keys:
            continue
        if str(edge.kind) == mark_kind and a in row_keys:
            marks[(a, b)] = str(edge.label or "")
        elif str(edge.kind) == count_kind:
            row = row_of(a)
            if row is not None:
                counted.setdefault((row, b), set()).add(a)

    cells: Dict[Tuple[str, str], Cell] = {}
    for key in set(marks) | set(counted):
        cells[key] = Cell(marks.get(key, ""), len(counted.get(key, ())))
    size: Dict[str, int] = {}
    for node in graph.nodes:
        row = row_of(node.key) if node.key not in row_keys else None
        if row is not None:
            size[row] = size.get(row, 0) + 1

    def column_total(key: str) -> int:
        return sum(cell.count for (r, c), cell in cells.items() if c == key)

    kind_field = str(spec.get("column_detail") or "")
    columns = [Column(n.key, n.label, str(n.record.get(kind_field) or "") if kind_field else "", column_total(n.key))
               for n in column_nodes]
    # The most used first, then the ones only committed to, by name: the
    # left of the grid is where the estate's vocabulary actually comes from.
    columns.sort(key=lambda c: (-c.total, -sum(1 for (r, k) in cells if k == c.key), c.label.lower()))

    grouped: Dict[str, List[Row]] = {}
    for node in row_nodes:
        name = str(node.record.get(group_field) or "") if group_field else ""
        total = sum(cell.count for (r, c), cell in cells.items() if r == node.key)
        grouped.setdefault(name, []).append(Row(node.key, node.label, size.get(node.key, 0), total))
    groups = [Group(name, sorted(grouped[name], key=lambda r: r.label.lower()))
              for name in _group_order(group_field, list(grouped))]
    return Matrix(columns, groups, cells, mark_kind, count_kind)


#: How a mark reads in a key, strongest first. A mark the model holds that is
#: not here reads as itself, after these.
MARK_ORDER = ("Governed by", "Aligned to", "Informed by")


def mark_rank(mark: str) -> int:
    return MARK_ORDER.index(mark) if mark in MARK_ORDER else len(MARK_ORDER)
