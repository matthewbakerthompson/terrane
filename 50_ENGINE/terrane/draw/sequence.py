"""A flow drawn as a sequence diagram.

A flowchart shows what connects to what; a sequence diagram shows what
happens in what order, which is the question people ask about a
transaction. The engine has written flows as Mermaid sequence diagrams
since the start; this paints the same flow as SVG, from the same steps:
every participant across the top, a lifeline down from each, one message
per recorded hop in the flow's order with the hop's number and its
protocol, a reply drawn back only where the interface is request-response
(a feed does not reply, and a reply that never happens is the usual lie),
the actor that starts it where the model knows one, and the flow's target
latency as a note under the system it starts at.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from ..palette import Palette
from ..render_sequence import participants, steps_for
from .metrics import Metrics, default_metrics
from .shapes import SHAPE_KEYS
from .svg import EDGE, IconLoader, attr, escape, fmt, frame_sheet, text_el

#: The measures of the drawing: a participant's box, the gap between two,
#: the room a hop takes, a reply's.
BOX_W_MIN, BOX_W_MAX, BOX_H = 120, 190, 48
GAP = 56
TOP = 0
FIRST_HOP = BOX_H + 44
HOP_H = 46
REPLY_H = 26
INK = "#10141f"
INK_2 = "#4a5368"
INK_3 = "#6b7489"
ACCENT = "#0a6cff"
LIFELINE = "#8f9bb5"
NOTE_FILL, NOTE_STROKE, NOTE_INK = "#fef3c7", "#b45309", "#1c1917"


def _sequence_number(value: object) -> str:
    text = str(value or "")
    digits = re.match(r"\s*(\d+)", text)
    return digits.group(1) if digits else text


def render_sequence_svg(model, flow_id: str, palette: Palette, *, metrics: Optional[Metrics] = None,
                        sheet_: bool = True, font_loader: Optional[IconLoader] = None, font_url_prefix: str = "",
                        model_name: str = "", date: str = "") -> str:
    """One flow as a sequence diagram on its sheet."""
    m = metrics or default_metrics()
    flow = model.get("flows", flow_id)
    if flow is None:
        raise KeyError("unknown flow %r" % flow_id)
    steps = steps_for(model, flow_id)
    payload = {"viewId": flow_id, "title": str(flow.get("name") or flow_id),
               "description": str(flow.get("description") or "")}
    out: List[str] = []
    if not steps:
        out.append(text_el(0, 14, "No steps are recorded for this flow, so there is nothing to sequence.", 13, 400,
                           INK_2))
        return frame_sheet(payload, m, "\n".join(out), (0.0, 0.0, 560.0, 24.0), "sequence", "", sheet=sheet_, pad=28,
                     font_loader=font_loader, font_url_prefix=font_url_prefix, model_name=model_name, date=date,
                     legend=[])

    order = participants(model, steps)
    entry = order[0]
    lead: Optional[str] = None
    for row in model.relation_rows("actor_uses_system"):
        if str(row.get("system_id")) == entry and model.get("actors", str(row.get("actor_id"))) is not None:
            lead = str(row["actor_id"])
            break
    columns: List[Tuple[str, str, str]] = []  # id, label, entity type
    if lead:
        actor = model.get("actors", lead) or {}
        columns.append((lead, str(actor.get("name") or lead), "actors"))
    for system_id in order:
        record = model.get("systems", system_id) or {}
        columns.append((system_id, str(record.get("name") or system_id), "systems"))

    # Each participant's box is as wide as its name wants, within reason,
    # and the lifelines are a gap apart.
    widths: Dict[str, float] = {}
    lines_of: Dict[str, List[str]] = {}
    for pid, label, _t in columns:
        lines = m.wrap(label, BOX_W_MAX - 24, "Geist", 600, 12)[:2]
        widest = max(m.width(line, "Geist", 600, 12) for line in lines)
        widths[pid] = max(BOX_W_MIN, min(BOX_W_MAX, widest + 28))
        lines_of[pid] = lines
    x_of: Dict[str, float] = {}
    x = 0.0
    for pid, _label, _t in columns:
        x_of[pid] = x + widths[pid] / 2
        x += widths[pid] + GAP

    # The messages, top to bottom.
    messages: List[dict] = []
    y = FIRST_HOP
    if lead:
        messages.append({"from": lead, "to": entry, "y": y, "text": str(flow.get("trigger") or "starts"),
                         "kind": "call", "number": ""})
        y += HOP_H
    for step in steps:
        interface = step["interface"]
        source, target = str(interface.get("source_system_id")), str(interface.get("target_system_id"))
        style = str(interface.get("integration_style") or "Request-response")
        request = style == "Request-response"
        messages.append({"from": source, "to": target, "y": y,
                         # The protocol, as the estate writes it; the name where a sketch
                         # said what the call does and not how; "call" where neither.
                         "text": str(interface.get("protocol") or interface.get("name") or "call"),
                         "kind": "call" if request else "event", "number": _sequence_number(step.get("sequence")),
                         "interface": str(interface.get("interface_id") or "")})
        y += HOP_H
        if request:
            messages.append({"from": target, "to": source, "y": y - HOP_H + REPLY_H, "text": "response",
                             "kind": "reply", "number": ""})
            y += REPLY_H
    latency = str(flow.get("target_latency") or "")
    note_h = 0
    if latency:
        note_lines = m.wrap(latency, 220, "Geist", 400, 11)[:3]
        note_h = 14 + 15 * len(note_lines)
    bottom = y + 12 + (note_h + 12 if latency else 0)

    # Lifelines first, under everything.
    for pid, _label, _t in columns:
        cx = x_of[pid]
        out.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="1" stroke-dasharray="5 4"/>' % (
            fmt(cx), fmt(BOX_H), fmt(cx), fmt(bottom), LIFELINE))
    # The participants.
    for pid, label, etype in columns:
        sw = palette.type_swatch(etype)
        cx, w = x_of[pid], widths[pid]
        out.append('<g class="participant" data-id="%s" data-type="%s"><title>%s</title>' % (
            attr(pid), attr(etype), escape(label)))
        if etype == "actors":
            out.append('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="%s" stroke="%s" stroke-width="1.6"/>' % (
                fmt(cx), fmt(BOX_H / 2), fmt(w / 2), fmt(BOX_H / 2), sw.fill, sw.stroke))
        else:
            out.append('<rect x="%s" y="0" width="%s" height="%s" rx="8" fill="%s" stroke="%s" stroke-width="1.6"/>' % (
                fmt(cx - w / 2), fmt(w), fmt(BOX_H), sw.fill, sw.stroke))
        lines = lines_of[pid]
        top = BOX_H / 2 - len(lines) * 12 / 2
        for i, line in enumerate(lines):
            out.append(text_el(cx, top + i * 12 + 10.3, line, 12, 600, sw.ink, anchor="middle"))
        out.append("</g>")
    # The messages.
    for msg in messages:
        x1, x2, my = x_of[msg["from"]], x_of[msg["to"]], msg["y"]
        reply = msg["kind"] == "reply"
        event = msg["kind"] == "event"
        color = INK_3 if reply else EDGE
        dash = ' stroke-dasharray="5 3"' if reply else ""
        out.append('<g class="message" data-kind="%s"%s>' % (msg["kind"], (' data-interface="%s"' % attr(msg["interface"])) if msg.get("interface") else ""))
        if abs(x1 - x2) < 1:
            # A system calling itself: a small loop out to the right and back.
            out.append('<path d="M%s %s h30 v18 h-24" fill="none" stroke="%s" stroke-width="1.6"%s/>' % (
                fmt(x1), fmt(my), color, dash))
            tip = (x1 + 6, my + 18)
            head = (x1 + 14, my + 18)
            direction = -1
        else:
            direction = 1 if x2 > x1 else -1
            end = x2 - direction * 10
            out.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="1.6"%s/>' % (
                fmt(x1), fmt(my), fmt(end), fmt(my), color, dash))
            tip, head = (x2 - direction * 1.5, my), (end, my)
        if event or reply:
            out.append('<path d="M%s %s L%s %s L%s %s" fill="none" stroke="%s" stroke-width="1.6"/>' % (
                fmt(head[0]), fmt(head[1] - 5), fmt(tip[0]), fmt(tip[1]), fmt(head[0]), fmt(head[1] + 5), color))
        else:
            out.append('<path d="M%s %s L%s %s L%s %s Z" fill="%s"/>' % (
                fmt(head[0]), fmt(head[1] - 5), fmt(tip[0]), fmt(tip[1]), fmt(head[0]), fmt(head[1] + 5), color))
        mid_x = (x1 + x2) / 2 if abs(x1 - x2) >= 1 else x1 + 44
        label_y = my - 6 if abs(x1 - x2) >= 1 else my + 12
        out.append(text_el(mid_x, label_y, msg["text"], 11 if not reply else 10, 500 if not reply else 400,
                           INK_2 if not reply else INK_3, anchor="middle" if abs(x1 - x2) >= 1 else "start"))
        if msg["number"]:
            bx = x1 + direction * 16
            out.append('<circle cx="%s" cy="%s" r="8.5" fill="%s"/>' % (fmt(bx), fmt(my), ACCENT))
            out.append(text_el(bx, my + 3.2, msg["number"], 9, 700, "#ffffff", anchor="middle"))
        out.append("</g>")
    # The target, as a note under the system the flow starts at.
    if latency:
        cx = x_of[entry]
        nw = 240
        ny = y + 12
        out.append('<g class="note"><rect x="%s" y="%s" width="%s" height="%s" rx="3" fill="%s" stroke="%s" stroke-width="1"/>' % (
            fmt(cx - nw / 2), fmt(ny), fmt(nw), fmt(note_h), NOTE_FILL, NOTE_STROKE))
        for i, line in enumerate(m.wrap(latency, nw - 20, "Geist", 400, 11)[:3]):
            out.append(text_el(cx, ny + 14 + i * 15 + 4, line, 11, 400, NOTE_INK, anchor="middle"))
        out.append("</g>")

    kinds = {msg["kind"] for msg in messages}
    line_keys = [{"kind": "line", "dash": "solid", "text": "call"}]
    if "reply" in kinds:
        line_keys.append({"kind": "line", "dash": "dashed", "text": "response"})
    if "event" in kinds:
        line_keys.append({"kind": "line", "dash": "solid", "text": "event or feed, no reply", "open": True})
    type_keys = []
    if lead:
        sw = palette.type_swatch("actors")
        type_keys.append({"kind": "shape", "type": "actors", "fill": sw.fill, "stroke": sw.stroke, "dash": "solid",
                          "width": 1.4, "text": "actor"})
    sw = palette.type_swatch("systems")
    type_keys.append({"kind": "shape", "type": "systems", "fill": sw.fill, "stroke": sw.stroke, "dash": "solid",
                      "width": 1.4, "text": "system · %d" % len(order)})
    legend = [{"cap": "type", "keys": type_keys}, {"cap": "lines", "keys": line_keys}]
    facts = "%d steps · %d participants" % (len(steps), len(columns))
    extent = (-(widths[columns[0][0]] / 2) - 8, -8.0, x - GAP + 8, bottom + 8)
    return frame_sheet(payload, m, "\n".join(out), extent, "sequence", facts, sheet=sheet_, pad=28,
                 font_loader=font_loader, font_url_prefix=font_url_prefix, model_name=model_name, date=date,
                 legend=legend)


__all__ = ["render_sequence_svg", "SHAPE_KEYS"]
