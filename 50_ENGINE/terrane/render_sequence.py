"""Mermaid sequence diagram renderer, for flows.

A flowchart shows what connects to what. A sequence diagram shows what happens
in what order, which is a different question and the one people ask about a
transaction: where does the time go, who is on the critical path, what happens
when step three is slow.

Only flows render this way. A view over systems has no order to it, and forcing
one would invent a sequence that is not in the model.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from .model import Model
from .schema import ENTITY_TYPES

_SAFE = re.compile(r"[^A-Za-z0-9_]")


def participant_id(raw: str) -> str:
    cleaned = _SAFE.sub("_", str(raw))
    return cleaned if cleaned and not cleaned[0].isdigit() else "p_" + cleaned


def _text(raw: str, limit: int = 46) -> str:
    """Mermaid sequence labels break on several characters even when quoted."""
    out = str(raw or "").strip()
    for needle, replacement in (("\n", " "), (":", " -"), (";", ","), ("#", "no."),
                                ("<", "("), (">", ")"), ("-->", "->")):
        out = out.replace(needle, replacement)
    out = re.sub(r"\s+", " ", out)
    if len(out) > limit:
        out = out[: limit - 1].rstrip() + "…"
    return out


def _sequence_key(value: object) -> Tuple[int, str]:
    """Order steps numerically where possible, so 10 precedes 100."""
    text = str(value or "")
    digits = re.match(r"\s*(\d+)", text)
    return (int(digits.group(1)) if digits else 10**9, text)


def steps_for(model: Model, flow_id: str) -> List[dict]:
    """Ordered hops for a flow, each resolved to its interface."""
    rows = [
        row for row in model.relation_rows("flow_step")
        if str(row.get("flow_id")) == flow_id
    ]
    rows.sort(key=lambda r: _sequence_key(r.get("sequence")))
    steps = []
    for row in rows:
        interface = model.get("interfaces", str(row.get("interface_id")))
        if interface is None:
            continue
        steps.append({"sequence": row.get("sequence"), "interface": interface})
    return steps


def participants(model: Model, steps: List[dict]) -> List[str]:
    """Every system a flow touches, in first-appearance order."""
    order: List[str] = []
    for step in steps:
        for key in ("source_system_id", "target_system_id"):
            system_id = str(step["interface"].get(key) or "")
            if system_id and system_id not in order:
                order.append(system_id)
    return order


def render(model: Model, flow_id: str) -> str:
    """One flow as a Mermaid sequence diagram."""
    flow = model.get("flows", flow_id)
    if flow is None:
        raise KeyError("unknown flow %r" % flow_id)

    steps = steps_for(model, flow_id)
    lines: List[str] = []
    lines.append("%% " + _text(flow.get("name") or flow_id, 90))
    lines.append("%% Generated from the model by `terrane render`. Do not edit by hand.")
    lines.append("sequenceDiagram")
    lines.append("  autonumber")

    if not steps:
        lines.append("  participant none as No steps recorded")
        return "\n".join(lines) + "\n"

    order = participants(model, steps)
    entry = order[0]

    # An actor that reaches the entry point leads the diagram, so it starts
    # where the transaction starts rather than at the first system.
    lead: Optional[str] = None
    for row in model.relation_rows("actor_uses_system"):
        if str(row.get("system_id")) == entry:
            actor = model.get("actors", str(row.get("actor_id")))
            if actor is not None:
                lead = str(row["actor_id"])
                lines.append(
                    "  actor %s as %s"
                    % (participant_id(lead), _text(actor.get("name") or lead, 30))
                )
                break

    for system_id in order:
        record = model.get("systems", system_id) or {}
        lines.append(
            "  participant %s as %s"
            % (participant_id(system_id), _text(record.get("name") or system_id, 30))
        )

    if lead:
        lines.append(
            "  %s->>%s: %s"
            % (participant_id(lead), participant_id(entry),
               _text(flow.get("trigger") or "starts", 40))
        )

    for step in steps:
        interface = step["interface"]
        source = str(interface.get("source_system_id"))
        target = str(interface.get("target_system_id"))
        style = str(interface.get("integration_style") or "Request-response")
        # A request-response hop returns; a feed does not, and drawing a reply
        # that never happens is the most common way these lie.
        arrow = "->>" if style == "Request-response" else "-)"
        lines.append(
            "  %s%s%s: %s"
            % (participant_id(source), arrow, participant_id(target),
               _text(interface.get("protocol") or interface.get("name") or "call", 30))
        )
        if style == "Request-response":
            lines.append(
                "  %s-->>%s: %s"
                % (participant_id(target), participant_id(source), "response")
            )

    latency = flow.get("target_latency")
    if latency:
        lines.append("  Note over %s: %s" % (participant_id(entry), _text(latency, 50)))
    return "\n".join(lines) + "\n"


def render_markdown(model: Model, flow_id: str, picture: str = "") -> str:
    """The flow's page: its facts, the drawing where there is one, the
    Mermaid, and the hops as a table."""
    flow = model.get("flows", flow_id) or {}
    parts: List[str] = ["# %s" % (flow.get("name") or flow_id), ""]
    if flow.get("description"):
        parts.extend([str(flow["description"]).strip(), ""])

    facts = []
    for key, label in (("trigger", "Trigger"), ("target_latency", "Target"),
                       ("criticality", "Criticality"), ("owner_org_id", "Owner")):
        if flow.get(key):
            facts.append("| %s | %s |" % (label, flow[key]))
    if facts:
        parts.extend(["| | |", "|---|---|"] + facts + [""])
    if picture:
        parts.append("![%s](%s)" % (str(flow.get("name") or flow_id).replace("]", ")"), picture))
        parts.append("")

    parts.extend(["```mermaid", render(model, flow_id).rstrip(), "```", ""])

    steps = steps_for(model, flow_id)
    if steps:
        parts.extend(["| # | From | To | Via |", "|---:|---|---|---|"])
        for step in steps:
            interface = step["interface"]
            source = model.get("systems", str(interface.get("source_system_id"))) or {}
            target = model.get("systems", str(interface.get("target_system_id"))) or {}
            parts.append(
                "| %s | %s | %s | `%s` %s, %s |"
                % (
                    step["sequence"],
                    source.get("name") or interface.get("source_system_id"),
                    target.get("name") or interface.get("target_system_id"),
                    interface["interface_id"],
                    interface.get("protocol") or "",
                    interface.get("integration_style") or "",
                )
            )
        parts.append("")

    parts.append(
        "%d step(s). Every hop is a recorded interface, so a hop that is not in "
        "the model cannot appear here." % len(steps)
    )
    return "\n".join(parts).rstrip() + "\n"


def all_flows(model: Model) -> List[str]:
    return sorted(str(f["flow_id"]) for f in model.all_of("flows"))
