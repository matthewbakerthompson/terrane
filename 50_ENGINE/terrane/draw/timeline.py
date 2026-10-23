"""A timeline drawn: dated things as bars on a calendar of quarters.

Time is the one axis a layout must not choose, so a timeline is not a
graph: it is a grid, the way the app draws it (`drawTimeline` in `app.js`)
and the way the Mermaid gantt in the artifacts says it. This paints that
grid as SVG from the same payload: years over quarters along the top, a
section per thing the view groups by (a work package under its roadmap's
name), a row per dated thing with its name and status on the left and a
bar from its first quarter to its last, and under the bar the undated
things its edges reach -- the systems it builds or changes -- as chips, a
filled dot for what it builds and a hollow one for what it changes. A bar
is drawn by status: solid in the accent for what is live, dashed for what
is planned, dotted for what is proposed, faded for what is retired.

The current quarter is marked only when the caller says what day it is:
the committed picture must be the same bytes tomorrow, and a column that
moved every three months would not be.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from xml.sax.saxutils import escape

from .metrics import Metrics, default_metrics
from .svg import IconLoader, attr, fmt, frame_sheet, text_el

#: The grid's measures: the label column, a quarter's width, the rows.
LABEL_W = 260
QUARTER_W = 84
YEAR_H = 20
QUARTER_H = 24
SECTION_H = 34
ROW_H = 44
CHIPS_H = 24
BAR_H = 26
#: The stylesheet's tokens the grid is drawn in.
ACCENT = "#0a6cff"
ACCENT_INK = "#ffffff"
ACCENT_2 = "#0548b8"
ACCENT_WASH = "#e8f1ff"
INK = "#10141f"
INK_2 = "#4a5368"
INK_3 = "#6b7489"
INK_700 = "#1f2740"
RULE = "#dce1ea"
SUNK = "#e9edf4"
SHEET = "#ffffff"
#: The dot on a chip is the system hue, the way the app's is.
SYSTEM = "#4338ca"


def quarter_index(text: object) -> Optional[int]:
    """`YYYY-Qn` as a count of quarters, or None for anything else."""
    s = str(text or "")
    if len(s) != 7 or s[4:6] != "-Q" or not s[:4].isdigit() or s[6] not in "1234":
        return None
    return int(s[:4]) * 4 + int(s[6]) - 1


def quarter_label(index: int) -> str:
    return "%d Q%d" % (index // 4, index % 4 + 1)


def quarter_of_day(date: str) -> Optional[int]:
    """The quarter a `YYYY-MM-DD` day is in, or None."""
    s = str(date or "")
    if len(s) < 7 or not s[:4].isdigit() or s[4] != "-" or not s[5:7].isdigit():
        return None
    return int(s[:4]) * 4 + (int(s[5:7]) - 1) // 3


def _plural(n: int, word: str) -> str:
    if n == 1:
        return word
    if word.endswith("y") and word[-2:-1] not in "aeiou":
        return word[:-1] + "ies"
    return word + "s"


def render_timeline_svg(payload: dict, *, metrics: Optional[Metrics] = None, sheet_: bool = True,
                        font_loader: Optional[IconLoader] = None, font_url_prefix: str = "",
                        model_name: str = "", date: str = "") -> str:
    """The view as a timeline sheet. `date` marks the current quarter; left
    out, nothing on the picture depends on the day it was made."""
    m = metrics or default_metrics()
    groups: Dict[str, str] = {}
    by_id: Dict[str, dict] = {}
    tasks: List[dict] = []
    for element in payload.get("elements", []):
        d = element["data"]
        if d.get("isGroup"):
            groups[d["id"]] = str(d.get("label") or "")
            continue
        if d.get("source"):
            continue
        by_id[d["id"]] = d
        a, b = quarter_index(d.get("start")), quarter_index(d.get("end"))
        if a is not None and b is not None and b >= a:
            tasks.append({"d": d, "a": a, "b": b})
    reached: Dict[str, List[dict]] = {}
    for element in payload.get("elements", []):
        d = element["data"]
        if not d.get("source"):
            continue
        to = by_id.get(d["target"])
        if to is None or quarter_index(to.get("start")) is not None:
            continue
        reached.setdefault(d["source"], []).append({
            "id": to["id"], "label": str(to.get("label") or ""),
            "verb": str(d.get("label") or "").lower() or "touches"})

    out: List[str] = []
    if not tasks:
        out.append(text_el(0, 14, "Nothing in this view carries a start and end quarter, so there is nothing to place.",
                           13, 400, INK_2))
        extent = (0.0, 0.0, 620.0, 24.0)
        return frame_sheet(payload, m, "\n".join(out), extent, "timeline", "", sheet=sheet_, pad=28,
                     font_loader=font_loader, font_url_prefix=font_url_prefix, model_name=model_name, date=date,
                     legend=[])

    now = quarter_of_day(date) if date else None
    first = min(t["a"] for t in tasks)
    last = max(t["b"] for t in tasks)
    if now is not None and first - 2 <= now <= last + 2:
        first, last = min(first, now), max(last, now)
    else:
        now = None
    span = last - first + 1

    def col_x(q: int) -> float:
        return LABEL_W + (q - first) * QUARTER_W

    width = LABEL_W + span * QUARTER_W

    # Years over quarters.
    out.append('<line x1="0" y1="%s" x2="%s" y2="%s" stroke="%s"/>' % (
        fmt(YEAR_H + QUARTER_H), fmt(width), fmt(YEAR_H + QUARTER_H), RULE))
    q = first
    while q <= last:
        year = q // 4
        until = min(last, year * 4 + 3)
        out.append(text_el((col_x(q) + col_x(until) + QUARTER_W) / 2, 14, str(year), 12, 600, INK, anchor="middle"))
        q = until + 1
    for q in range(first, last + 1):
        x = col_x(q)
        if q == now:
            out.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s"/>' % (
                fmt(x), fmt(YEAR_H), fmt(QUARTER_W), fmt(QUARTER_H), ACCENT_WASH))
        out.append(text_el(x + QUARTER_W / 2, YEAR_H + 16, "Q%d" % (q % 4 + 1), 11, 700 if q == now else 500,
                           ACCENT_2 if q == now else INK_3, anchor="middle"))

    # Sections and rows.
    y = YEAR_H + QUARTER_H + 6
    sections: Dict[str, List[dict]] = {}
    for t in tasks:
        sections.setdefault(str(t["d"].get("parent") or ""), []).append(t)
    rows_total = 0
    body_top = y
    kind = str(tasks[0]["d"].get("entityType") or "")
    named = [t for t in (payload.get("legend") or {}).get("types", []) if t.get("key") == kind]
    what = named[0]["label"] if named else "item"
    for key in sorted(sections, key=lambda k: groups.get(k, "").lower()):
        lst = sorted(sections[key], key=lambda t: (t["a"], t["d"].get("label", "").lower()))
        start, end = min(t["a"] for t in lst), max(t["b"] for t in lst)
        out.append('<line x1="0" y1="%s" x2="%s" y2="%s" stroke="%s"/>' % (fmt(y), fmt(width), fmt(y), RULE))
        out.append(text_el(0, y + 20, groups.get(key) or "—", 13, 700, INK))
        out.append(text_el(m.width(groups.get(key) or "—", "Geist", 700, 13) + 12, y + 20,
                           "%d %s · %s%s" % (len(lst), _plural(len(lst), what), quarter_label(start),
                                                   (" to " + quarter_label(end)) if end != start else ""),
                           10, 400, INK_3))
        y += SECTION_H
        for t in lst:
            d = t["d"]
            # The quarter cells, ruled, the current one washed.
            for q in range(first, last + 1):
                x = col_x(q)
                if q == now:
                    out.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s"/>' % (
                        fmt(x), fmt(y), fmt(QUARTER_W), fmt(ROW_H), ACCENT_WASH))
                out.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s"/>' % (
                    fmt(x), fmt(y), fmt(x), fmt(y + ROW_H), RULE if q % 4 == 0 else SUNK))
            label = str(d.get("label") or "")
            status = str(d.get("status") or "")
            # The name on up to two lines, the status and quarters under it.
            name_lines = m.wrap(label, LABEL_W - 16, "Geist", 600, 12.5)[:2]
            if len(name_lines) == 2 and m.width(name_lines[1], "Geist", 600, 12.5) > LABEL_W - 16:
                name_lines[1] = m.fit(name_lines[1], LABEL_W - 16, "Geist", 600, 12.5)
            if len(name_lines) == 1:
                out.append(text_el(0, y + 18, name_lines[0], 12.5, 600, INK))
            else:
                out.append(text_el(0, y + 14, name_lines[0], 12.5, 600, INK))
                out.append(text_el(0, y + 27, name_lines[1], 12.5, 600, INK))
            when = "%s%s" % (d.get("start"), (" to " + str(d.get("end"))) if d.get("end") != d.get("start") else "")
            out.append(text_el(0, y + (32 if len(name_lines) == 1 else 40),
                               m.fit("%s · %s" % (status, when) if status else when, LABEL_W - 16, "Geist", 400, 10),
                               10, 400, INK_3))
            under = reached.get(d["id"], [])
            builds = sum(1 for u in under if u["verb"] == "builds")
            changes = len(under) - builds
            words = []
            if builds:
                words.append("%d built" % builds)
            if changes:
                words.append("%d changed" % changes)
            bar_text = " · ".join(words) if words else label
            x1, x2 = col_x(t["a"]) + 3, col_x(t["b"]) + QUARTER_W - 3
            by = y + (ROW_H - BAR_H) / 2
            low = status.lower()
            if low == "active":
                fill, stroke, dash_, ink, opacity = ACCENT, ACCENT, "", ACCENT_INK, ""
            elif low == "planned":
                fill, stroke, dash_, ink, opacity = SHEET, INK_700, ' stroke-dasharray="6 3"', INK, ""
            elif low == "proposed":
                fill, stroke, dash_, ink, opacity = SHEET, INK_3, ' stroke-dasharray="2 2"', INK_2, ""
            else:
                fill, stroke, dash_, ink, opacity = ACCENT, ACCENT, "", ACCENT_INK, ' opacity="0.5"'
            out.append('<g class="bar" data-id="%s"%s><title>%s</title>' % (attr(d["id"]), opacity, escape(
                "%s: %s%s" % (label, when, (", " + status) if status else ""))))
            out.append('<rect x="%s" y="%s" width="%s" height="%s" rx="6" fill="%s" stroke="%s" stroke-width="1.5"%s/>'
                       % (fmt(x1), fmt(by), fmt(x2 - x1), fmt(BAR_H), fill, stroke, dash_))
            out.append(text_el((x1 + x2) / 2, by + BAR_H / 2 + 3.5, m.fit(bar_text, x2 - x1 - 16, "Geist", 500, 10),
                               10, 500, ink, anchor="middle"))
            out.append("</g>")
            y += ROW_H
            rows_total += 1
            if under:
                # The chips wrap within the quarters' width, two lines at most;
                # what does not fit is counted rather than run off the sheet.
                cx = LABEL_W + 14
                lines_used = 1
                shown: List[dict] = []
                more_w = m.width("and 99 more", "Geist", 500, 10) + 8
                for u in under:
                    label_w = m.width(u["label"], "Geist", 400, 10)
                    if cx + label_w + 30 > width - (more_w if len(shown) + 1 < len(under) else 0):
                        if lines_used >= 2:
                            break
                        lines_used += 1
                        cx = LABEL_W + 14
                        y += CHIPS_H
                    shown.append(u)
                    out.append('<g class="chip" data-id="%s"><title>%s</title>' % (attr(u["id"]), escape(
                        "%s: %s" % (u["label"], u["verb"]))))
                    out.append('<rect x="%s" y="%s" width="%s" height="16" rx="8" fill="%s"/>' % (
                        fmt(cx), fmt(y + 2), fmt(label_w + 24), SUNK))
                    if u["verb"] == "changes":
                        out.append('<circle cx="%s" cy="%s" r="3" fill="none" stroke="%s" stroke-width="1.5"/>' % (
                            fmt(cx + 9), fmt(y + 10), SYSTEM))
                    else:
                        out.append('<circle cx="%s" cy="%s" r="3.5" fill="%s"/>' % (fmt(cx + 9), fmt(y + 10), SYSTEM))
                    out.append(text_el(cx + 17, y + 13.5, u["label"], 10, 400, INK_2))
                    out.append("</g>")
                    cx += label_w + 30
                if len(under) > len(shown):
                    out.append(text_el(cx, y + 13.5, "and %d more" % (len(under) - len(shown)), 10, 500, ACCENT_2))
                y += CHIPS_H
    out.append('<line x1="0" y1="%s" x2="%s" y2="%s" stroke="%s"/>' % (fmt(y), fmt(width), fmt(y), RULE))
    # The vertical rules through the header, after the rows so they sit on top.
    for q in range(first, last + 1):
        x = col_x(q)
        out.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s"/>' % (
            fmt(x), fmt(YEAR_H), fmt(x), fmt(YEAR_H + QUARTER_H), RULE if q % 4 == 0 else SUNK))

    legend = [
        {"cap": "bars", "keys": [
            {"kind": "box", "fill": ACCENT, "stroke": ACCENT, "dash": "solid", "text": "Active"},
            {"kind": "box", "fill": SHEET, "stroke": INK_700, "dash": "dashed", "text": "Planned"},
            {"kind": "box", "fill": SHEET, "stroke": INK_3, "dash": "dotted", "text": "Proposed"},
        ]},
        {"cap": "under a bar", "keys": [
            {"kind": "dot", "fill": SYSTEM, "stroke": SYSTEM, "text": "builds"},
            {"kind": "dot", "fill": "none", "stroke": SYSTEM, "text": "changes"},
        ]},
    ]
    if now is not None:
        legend[0]["keys"].append({"kind": "box", "fill": ACCENT_WASH, "stroke": "#cfe0ff", "dash": "solid",
                                  "text": "this quarter"})
    facts = "%d %s · %d %s" % (rows_total, _plural(rows_total, what), span, _plural(span, "quarter"))
    extent = (0.0, 0.0, float(width), float(y))
    return frame_sheet(payload, m, "\n".join(out), extent, "timeline", facts, sheet=sheet_, pad=28,
                 font_loader=font_loader, font_url_prefix=font_url_prefix, model_name=model_name, date=date,
                 legend=legend)
