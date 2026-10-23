"""A report drawn: the table it always was, on the sheet.

Eleven of the views answer a question with a set rather than a structure,
and the engine writes each as a Markdown table while the app shows an
HTML one; neither is a picture, so the review pack had no slide for the
registers a board asks about and the Python door returned nothing for
them. This paints the same table as SVG on the same sheet as every other
drawing: a column for each end of the relationship, the name over the id,
the relationship between them, and the detail where any row has one; a
column that says the same thing on every row says it once above the
table, as the app's does. A report with no relationships is the set
itself, one row per thing. Rows alternate in tint, the header carries a
rule, and a long report is paged for a deck, so many rows a sheet, while
the committed picture holds the whole table at its full height.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from ..matrix import mark_rank, matrix_of
from .metrics import Metrics, default_metrics
from .svg import IconLoader, attr, fmt, frame_sheet, text_el

#: The table's measures, in the sheet's pixels.
TABLE_W = 1184.0
CELL_PAD_X = 10.0
CELL_PAD_Y = 8.0
LINE_H = 15.0
ID_H = 14.0
HEADER_H = 30.0
MAX_LINES = 3
#: Rows a page holds, for a deck: eight make a sheet about as wide as it is
#: tall twice over, which is the slide's picture box, so the type on the
#: slide is eight points and reads; sixteen made it four and did not.
ROWS_PER_PAGE = 8
INK = "#0f172a"
INK_2 = "#334155"
INK_SOFT = "#5b6577"
RULE = "#c9d0dc"
STRIPE = "#f4f6fb"
MONO = "'Geist Mono', ui-monospace, monospace"


class Row:
    def __init__(self, cells: Sequence[Tuple[str, str]]) -> None:
        #: Each cell as (text, small text under it), in column order.
        self.cells = list(cells)


def table_of(graph) -> Tuple[List[str], List[Row], List[str]]:
    """The report as columns, rows and the lines said once above the
    table (a column that is the same on every row)."""
    by_key = {node.key: node for node in graph.nodes}

    def side(key: str) -> Tuple[str, str]:
        node = by_key.get(key)
        return (node.label, key) if node is not None else (key, "")

    if not graph.edges:
        rows = [Row([(str(i), ""), (node.label, ""), (node.key, "")])
                for i, node in enumerate(sorted(graph.nodes, key=lambda n: n.label.lower()), 1)]
        return ["", "Entity", "Id"], rows, []
    labeled = any(edge.label for edge in graph.edges)
    columns = ["From", "Relationship", "To"] + (["Detail"] if labeled else [])
    ordered = sorted(graph.edges, key=lambda e: (str(e.kind), side(e.source)[0].lower()))
    rows = []
    for edge in ordered:
        cells = [side(edge.source), (str(edge.kind or "").replace("_", " "), ""), side(edge.target)]
        if labeled:
            cells.append((str(edge.label or ""), ""))
        rows.append(Row(cells))
    said: List[str] = []
    if len(rows) > 1:
        for i in range(len(columns) - 1, -1, -1):
            values = {row.cells[i][0] for row in rows}
            if len(values) == 1 and next(iter(values)):
                said.insert(0, "%s, on every row: %s" % (columns[i], next(iter(values))))
                columns.pop(i)
                for row in rows:
                    row.cells.pop(i)
    return columns, rows, said


def pages(graph, per_page: int = ROWS_PER_PAGE) -> List[Tuple[int, int]]:
    """The row ranges a deck shows the report in, (first, last) 1-based. A
    grid is one page: cut, it would lose the columns its rows are read
    against."""
    grid = matrix_of(graph)
    if grid is not None:
        count = sum(len(g.rows) for g in grid.groups)
        return [(1, count)] if count else [(0, 0)]
    _columns, rows, _said = table_of(graph)
    if not rows:
        return [(0, 0)]
    return [(start + 1, min(start + per_page, len(rows))) for start in range(0, len(rows), per_page)]


def _widths(columns: Sequence[str]) -> List[float]:
    """Each column's share of the table, by what it holds."""
    shares = {"From": 0.3, "To": 0.3, "Relationship": 0.16, "Detail": 0.24, "": 0.05, "Entity": 0.55, "Id": 0.4}
    weights = [shares.get(c, 0.2) for c in columns]
    total = sum(weights)
    return [TABLE_W * w / total for w in weights]


def render_table_svg(graph, *, metrics: Optional[Metrics] = None, sheet_: bool = True,
                     font_loader: Optional[IconLoader] = None, font_url_prefix: str = "", model_name: str = "",
                     date: str = "", rows_from: int = 1, rows_to: Optional[int] = None) -> str:
    """The report as a table on its sheet; `rows_from` and `rows_to`
    (1-based, inclusive) cut one page of it for a deck. A report that asks
    for a grid under `style.matrix` is drawn as one, whole."""
    grid = matrix_of(graph)
    if grid is not None:
        return render_matrix_svg(graph, grid, metrics=metrics, sheet_=sheet_, font_loader=font_loader,
                                 font_url_prefix=font_url_prefix, model_name=model_name, date=date)
    m = metrics or default_metrics()
    view = graph.view
    columns, all_rows, said = table_of(graph)
    rows = all_rows[rows_from - 1:rows_to] if all_rows else []
    widths = _widths(columns)
    out: List[str] = []
    y = 0.0
    for line in said:
        out.append(text_el(0, y + 12, line, 12, 500, INK_2))
        y += 20
    if said:
        y += 6
    # The header.
    x = 0.0
    out.append('<rect x="0" y="%s" width="%s" height="%s" fill="%s"/>' % (fmt(y), fmt(TABLE_W), fmt(HEADER_H), STRIPE))
    for column, width in zip(columns, widths):
        out.append(text_el(x + CELL_PAD_X, y + 19, column.upper() if column else "", 10.5, 600, INK_2,
                           extra=' letter-spacing="0.06em"'))
        x += width
    y += HEADER_H
    out.append('<line x1="0" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="1.2"/>' % (fmt(y), fmt(TABLE_W), fmt(y), RULE))
    if not rows:
        out.append(text_el(CELL_PAD_X, y + 22, "Nothing in the model answers this report yet.", 12, 400, INK_SOFT))
        y += 36
    for index, row in enumerate(rows):
        wrapped: List[Tuple[List[str], str]] = []
        for (text, small), width in zip(row.cells, widths):
            lines = m.wrap(text, width - 2 * CELL_PAD_X, "Geist", 500, 12)[:MAX_LINES] if text else []
            if len(lines) == MAX_LINES and len(m.wrap(text, width - 2 * CELL_PAD_X, "Geist", 500, 12)) > MAX_LINES:
                lines[-1] = m.fit(lines[-1] + "…", width - 2 * CELL_PAD_X, "Geist", 500, 12)
            wrapped.append((lines, small))
        tallest = max((len(lines) * LINE_H + (ID_H if small else 0) for lines, small in wrapped), default=LINE_H)
        height = tallest + 2 * CELL_PAD_Y
        if index % 2 == 1:
            out.append('<rect x="0" y="%s" width="%s" height="%s" fill="%s"/>' % (fmt(y), fmt(TABLE_W), fmt(height), STRIPE))
        x = 0.0
        out.append('<g class="row" data-row="%d">' % (rows_from + index))
        for (lines, small), width in zip(wrapped, widths):
            ty = y + CELL_PAD_Y + 11
            for line in lines:
                out.append(text_el(x + CELL_PAD_X, ty, line, 12, 500 if small else 400, INK))
                ty += LINE_H
            if small:
                out.append(text_el(x + CELL_PAD_X, ty - 1, m.fit(small, width - 2 * CELL_PAD_X, "Geist Mono", 400, 10),
                                   10, 400, INK_SOFT, family=MONO))
            x += width
        out.append("</g>")
        y += height
        out.append('<line x1="0" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="0.6"/>' % (fmt(y), fmt(TABLE_W), fmt(y), RULE))
    extent = (0.0, 0.0, TABLE_W, y)
    total = len(all_rows)
    if rows and (rows_from > 1 or (rows_to is not None and rows_to < total)):
        facts = "rows %d–%d of %d" % (rows_from, rows_from + len(rows) - 1, total)
    else:
        facts = "%d row%s" % (total, "" if total == 1 else "s")
    if graph.edges:
        facts += " · %d entities" % len(graph.nodes)
    payload = {"viewId": view.view_id, "title": view.title, "description": view.description, "kind": "report",
               "legend": []}
    return frame_sheet(payload, m, "\n".join(out), extent, "table", facts, sheet=sheet_, pad=28,
                       font_loader=font_loader, font_url_prefix=font_url_prefix, model_name=model_name, date=date,
                       legend=[])


# ---- a report drawn as a grid ---------------------------------------------

#: The grid's measures, in the sheet's pixels.
NAME_W = 300.0
TOTAL_W = 64.0
GRID_HEAD_H = 56.0
GRID_ROW_H = 26.0
GROUP_H = 30.0
#: The capability hue of the house palette, for the counts: what is counted
#: is capabilities, and a count is that hue at a depth that grows with it.
COUNT_FILL = "#ddd6fe"
COUNT_STROKE = "#6d28d9"
MARK_LIGHT = "#9aa3b5"


def _mark_el(cx: float, cy: float, mark: str) -> str:
    """How firmly, as a ring: filled for governed by, an ink ring for aligned
    to, a pale ring for informed by. Anything else the model says reads as
    the ink ring, and the key names it."""
    if mark == "Governed by":
        return '<circle cx="%s" cy="%s" r="4.5" fill="%s"/>' % (fmt(cx), fmt(cy), INK)
    stroke = MARK_LIGHT if mark == "Informed by" else INK
    return '<circle cx="%s" cy="%s" r="4" fill="#ffffff" stroke="%s" stroke-width="1.6"/>' % (fmt(cx), fmt(cy), stroke)


def _count_el(m: Metrics, x: float, cy: float, count: int) -> Tuple[str, float]:
    from ..palette import _mix
    label = str(count)
    w = max(20.0, m.width(label, "Geist", 600, 10.5) + 12)
    depth = 0.0 if count < 4 else (0.22 if count < 10 else 0.45)
    fill = _mix(COUNT_FILL, COUNT_STROKE, depth) if depth else _mix(COUNT_FILL, "#ffffff", 0.4)
    ink = "#ffffff" if depth > 0.4 else INK
    return ('<rect x="%s" y="%s" width="%s" height="16" rx="8" fill="%s" stroke="%s" stroke-width="1"/>'
            % (fmt(x), fmt(cy - 8), fmt(w), fill, COUNT_STROKE)
            + text_el(x + w / 2, cy + 3.8, label, 10.5, 600, ink, anchor="middle")), w


def render_matrix_svg(graph, grid, *, metrics: Optional[Metrics] = None, sheet_: bool = True,
                      font_loader: Optional[IconLoader] = None, font_url_prefix: str = "", model_name: str = "",
                      date: str = "") -> str:
    """A report's `style.matrix` as the grid the app shows: the rows down the
    side in their groups, the columns across the top, a ring for the mark
    and a count in each cell, the totals at the ends."""
    m = metrics or default_metrics()
    view = graph.view
    columns = list(grid.columns)
    col_w = (TABLE_W - NAME_W - TOTAL_W) / max(1, len(columns))
    out: List[str] = []
    # The header: each column's name over its kind.
    out.append('<rect x="0" y="0" width="%s" height="%s" fill="%s"/>' % (fmt(TABLE_W), fmt(GRID_HEAD_H), STRIPE))
    for i, column in enumerate(columns):
        cx = NAME_W + col_w * i + col_w / 2
        lines = m.wrap(column.label, col_w - 6, "Geist", 600, 10.5)[:2]
        top = GRID_HEAD_H - 14 - (len(lines) - 1) * 12 - (12 if column.detail else 0)
        for k, line in enumerate(lines):
            out.append(text_el(cx, top + k * 12, line, 10.5, 600, INK, anchor="middle"))
        if column.detail:
            out.append(text_el(cx, GRID_HEAD_H - 10, m.fit(column.detail, col_w - 6, "Geist", 400, 9.5),
                               9.5, 400, INK_SOFT, anchor="middle"))
    out.append(text_el(TABLE_W - 8, GRID_HEAD_H - 12, "Placed", 10.5, 600, INK_2, anchor="end"))
    y = GRID_HEAD_H
    out.append('<line x1="0" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="1.2"/>'
               % (fmt(y), fmt(TABLE_W), fmt(y), RULE))
    rows = 0
    for group in grid.groups:
        if group.name:
            out.append(text_el(CELL_PAD_X, y + GROUP_H - 9, group.name, 12.5, 700, INK))
            y += GROUP_H
        for row in group.rows:
            cy = y + GRID_ROW_H / 2
            name = m.fit(row.label, NAME_W - 2 * CELL_PAD_X - 26, "Geist", 400, 12)
            out.append('<g class="row" data-row="%s">' % attr(row.key))
            out.append(text_el(CELL_PAD_X, cy + 4, name, 12, 400, INK))
            if row.size:
                out.append(text_el(CELL_PAD_X + m.width(name, "Geist", 400, 12) + 6, cy + 4, str(row.size),
                                   10.5, 400, INK_SOFT))
            for i, column in enumerate(columns):
                cell = grid.cells.get((row.key, column.key))
                cx = NAME_W + col_w * i + col_w / 2
                if cell is None:
                    out.append('<circle cx="%s" cy="%s" r="1.5" fill="%s"/>' % (fmt(cx), fmt(cy), RULE))
                    continue
                parts: List[str] = []
                widths: List[float] = []
                if cell.mark:
                    parts.append("mark")
                    widths.append(10.0)
                if cell.count:
                    _el, w = _count_el(m, 0, cy, cell.count)
                    parts.append("count")
                    widths.append(w)
                span = sum(widths) + 4 * (len(widths) - 1)
                x = cx - span / 2
                for part, w in zip(parts, widths):
                    if part == "mark":
                        out.append(_mark_el(x + 5, cy, cell.mark))
                    else:
                        out.append(_count_el(m, x, cy, cell.count)[0])
                    x += w + 4
            out.append(text_el(TABLE_W - 8, cy + 4, str(row.total) if row.total else "—", 11.5, 600,
                               INK if row.total else INK_SOFT, anchor="end"))
            out.append("</g>")
            y += GRID_ROW_H
            rows += 1
            out.append('<line x1="0" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="0.6"/>'
                       % (fmt(y), fmt(TABLE_W), fmt(y), RULE))
    # The columns' totals, and a key for the two things a cell says.
    out.append(text_el(CELL_PAD_X, y + 19, "Placed in each", 11, 600, INK_2))
    for i, column in enumerate(columns):
        cx = NAME_W + col_w * i + col_w / 2
        out.append(text_el(cx, y + 19, str(column.total) if column.total else "—", 11.5, 600,
                           INK if column.total else INK_SOFT, anchor="middle"))
    y += 30
    x = CELL_PAD_X
    for mark in sorted({cell.mark for cell in grid.cells.values() if cell.mark}, key=lambda k: (mark_rank(k), k)):
        out.append(_mark_el(x + 5, y + 12, mark))
        out.append(text_el(x + 14, y + 16, mark, 11, 400, INK_2))
        x += 24 + m.width(mark, "Geist", 400, 11) + 10
    out.append(_count_el(m, x, y + 12, 8)[0])
    out.append(text_el(x + 28, y + 16, "capabilities placed in it", 11, 400, INK_2))
    y += 26
    extent = (0.0, 0.0, TABLE_W, y)
    facts = "%d rows · %d columns" % (rows, len(columns))
    payload = {"viewId": view.view_id, "title": view.title, "description": view.description, "kind": "report",
               "legend": []}
    return frame_sheet(payload, m, "\n".join(out), extent, "table", facts, sheet=sheet_, pad=28,
                       font_loader=font_loader, font_url_prefix=font_url_prefix, model_name=model_name, date=date,
                       legend=[])
