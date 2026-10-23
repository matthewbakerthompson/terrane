"""Impact analysis: what else is affected if this changes.

The question an architect is actually asked is never "what does the estate look
like". It is "we are retiring the mainframe, what breaks", or "this vendor is
going away, what stops working", or "we need an outage on that database, who do
I tell". A model that holds every dependency and cannot answer those is a
drawing with extra steps.

Two things make the answer useful rather than merely correct:

* **Direction matters.** Depending on something is not the same as being
  depended on by it. A blast radius is the downstream set; a prerequisite list
  is the upstream set. Merging them produces a number nobody can act on.
* **Distance matters.** Everything is eventually connected. A result that does
  not say how far away something is, and does not weaken with distance, is
  indistinguishable from "the whole estate", which is the answer people already
  had.
"""

from __future__ import annotations

from typing import Dict, List, NamedTuple, Optional, Sequence, Set, Tuple

from .model import Model
from .schema import ENTITY_TYPES, RELATION_TYPES

#: Which end of each relation depends on which.
#:
#: `forward` means the left column depends on the right: a system depends on the
#: technology service it runs on. `reverse` means the right depends on the left:
#: a capability is realized by a system, so the capability is what breaks when
#: the system goes, not the other way round.
#:
#: Getting one of these backwards produces a confident answer pointing the wrong
#: way, which is worse than no answer at all. They are listed rather than
#: assumed for that reason.
DEPENDENCY_DIRECTION = {
    "system_uses_tech_service": "forward",
    "product_includes_system": "forward",
    "tech_service_connects_to": "forward",
    "interface_transports_data_asset": "forward",
    # A capability is realized by what implements it.
    "system_realizes_capability": "reverse",
    "product_realizes_capability": "reverse",
    # A control is enforced by what it governs, the same way a capability is
    # realized by what implements it: retire the system and the control has
    # lost an enforcement point, which is what an audit wants to hear about.
    "system_governed_by_control": "reverse",
    "data_governed_by_control": "reverse",
    "capability_governed_by_control": "reverse",
    # A policy runs the other way. The subject is obliged by it, so when the
    # policy changes the subject has work to do; retiring the subject does
    # nothing to the policy.
    "system_subject_to_policy": "forward",
    "data_subject_to_policy": "forward",
    "capability_subject_to_policy": "forward",
}

#: How an integration style decides which end depends on which.
#:
#: A caller depends on what it calls, so a request-response edge runs source ->
#: target. A consumer depends on what feeds it, so an event or batch edge runs
#: the other way: the receiver is the one that breaks when the sender stops.
STYLE_DIRECTION = {
    "Request-response": "forward",
    "Event": "reverse",
    "Batch": "reverse",
}


class Hop(NamedTuple):
    entity_id: str
    entity_type: str
    name: str
    distance: int
    #: Why this was reached: the relation, and the entity it was reached from.
    via: str
    from_id: str
    direction: str  # "downstream" or "upstream"

    @property
    def confidence(self) -> str:
        """Consequence weakens with distance, and saying so is the point."""
        if self.distance == 1:
            return "direct"
        if self.distance == 2:
            return "likely"
        return "possible"


class Impact(NamedTuple):
    root: str
    root_name: str
    root_type: str
    downstream: List[Hop]
    upstream: List[Hop]
    notes: List[str]

    def counts(self) -> Dict[str, int]:
        return {"downstream": len(self.downstream), "upstream": len(self.upstream)}


def _edges(model: Model) -> List[Tuple[str, str, str]]:
    """Every dependency edge as (dependent, depended_on, relation).

    Direction is normalized here so the traversal never has to think about it:
    the first element always needs the second.
    """
    edges: List[Tuple[str, str, str]] = []

    def add(a: str, b: str, relation: str, direction: str) -> None:
        if direction == "reverse":
            a, b = b, a
        edges.append((str(a), str(b), relation))

    for name, spec in RELATION_TYPES.items():
        direction = DEPENDENCY_DIRECTION.get(name)
        for row in model.relation_rows(name):
            left, right = row.get(spec.left_column), row.get(spec.right_column)
            if not (left and right):
                continue
            if name == "system_reads_writes":
                # A reader depends on the data. A writer is what the data
                # depends on. ReadWrite is genuinely both.
                operation = str(row.get("operation") or "Read")
                if operation in ("Read", "ReadWrite"):
                    add(left, right, "%s (read)" % name, "forward")
                if operation in ("Write", "ReadWrite"):
                    add(left, right, "%s (write)" % name, "reverse")
                continue
            if direction is None:
                continue
            add(left, right, name, direction)

    for record in model.all_of("interfaces"):
        src = record.get("source_system_id")
        dst = record.get("target_system_id")
        if not (src and dst):
            continue
        style = str(record.get("integration_style") or "Request-response")
        label = "%s %s" % (record.get("protocol") or "call", style.lower())
        add(src, dst, label, STYLE_DIRECTION.get(style, "forward"))

    # What a system offers goes when the system does; and whoever uses an
    # interface someone offers depends on it, whichever way the traffic runs:
    # a caller on the API, a reader on the topic, a sender on the listener.
    # Without these the ledger's request queue had nothing depending on it
    # and six systems putting requests on it.
    for record in model.all_of("offered_interfaces"):
        if record.get("system_id"):
            add(record["offered_interface_id"], record["system_id"], "offered by", "forward")
    for record in model.all_of("interfaces"):
        offered = model.get("offered_interfaces", str(record.get("offered_interface_id") or ""))
        owner = str((offered or {}).get("system_id") or "")
        src, dst = str(record.get("source_system_id") or ""), str(record.get("target_system_id") or "")
        if not offered or owner not in (src, dst) or src == dst:
            continue
        add(dst if owner == src else src, offered["offered_interface_id"], "goes through", "forward")

    # A data asset depends on the system that masters it.
    for record in model.all_of("data_assets"):
        owner = record.get("source_of_truth")
        if owner:
            add(record["data_asset_id"], owner, "source of truth", "forward")

    # A control gives effect to a policy, so it changes when the policy does.
    for record in model.all_of("controls"):
        policy = record.get("policy_id")
        if policy:
            add(record["control_id"], policy, "gives effect to", "forward")

    return edges


def analyze(
    model: Model,
    entity_id: str,
    max_distance: int = 3,
    include_types: Optional[Sequence[str]] = None,
) -> Impact:
    """Walk the dependency graph out from one entity, both directions."""
    found = model.find(entity_id)
    if found is None:
        raise KeyError("unknown entity %r" % entity_id)
    root_type, root = found

    edges = _edges(model)
    # `depends_on[a]` = things a needs. `depended_on_by[b]` = things that need b.
    depends_on: Dict[str, List[Tuple[str, str]]] = {}
    depended_on_by: Dict[str, List[Tuple[str, str]]] = {}
    for src, dst, rel in edges:
        depends_on.setdefault(src, []).append((dst, rel))
        depended_on_by.setdefault(dst, []).append((src, rel))

    keep = set(include_types) if include_types else None

    def walk(adjacency: Dict[str, List[Tuple[str, str]]], direction: str) -> List[Hop]:
        seen: Set[str] = {entity_id}
        hops: List[Hop] = []
        frontier: List[Tuple[str, int]] = [(entity_id, 0)]
        while frontier:
            current, distance = frontier.pop(0)
            if distance >= max_distance:
                continue
            for other, relation in adjacency.get(current, []):
                if other in seen:
                    continue
                seen.add(other)
                located = model.find(other)
                if located is None:
                    continue
                other_type, record = located
                if keep and other_type not in keep:
                    # Still traversed through, just not reported: a dependency
                    # that runs through a subnet still reaches what is beyond it.
                    frontier.append((other, distance + 1))
                    continue
                hops.append(
                    Hop(
                        entity_id=other,
                        entity_type=other_type,
                        name=str(record.get("name") or other),
                        distance=distance + 1,
                        via=relation,
                        from_id=current,
                        direction=direction,
                    )
                )
                frontier.append((other, distance + 1))
        return sorted(hops, key=lambda h: (h.distance, h.entity_type, h.name.lower()))

    downstream = walk(depended_on_by, "downstream")
    upstream = walk(depends_on, "upstream")

    notes: List[str] = []
    if not downstream and not upstream:
        notes.append(
            "Nothing connects to this. Either it is genuinely standalone, or the "
            "model is incomplete -- check the graph.orphan warnings."
        )
    critical = [h for h in downstream if h.entity_type == "systems"
                and str(model.get("systems", h.entity_id).get("criticality")) == "High"]
    if critical:
        notes.append(
            "%d High-criticality system(s) downstream: %s"
            % (len(critical), ", ".join(h.entity_id for h in critical[:6]))
        )
    caps = [h for h in downstream if h.entity_type == "capabilities"]
    if caps:
        notes.append(
            "Business capabilities affected: %s" % ", ".join(sorted(h.name for h in caps))
        )
    return Impact(
        root=entity_id,
        root_name=str(root.get("name") or entity_id),
        root_type=root_type,
        downstream=downstream,
        upstream=upstream,
        notes=notes,
    )


def to_payload(impact: Impact) -> dict:
    """JSON shape for the app and the static export."""
    def hop(h: Hop) -> dict:
        return {
            "id": h.entity_id,
            "type": h.entity_type,
            "name": h.name,
            "distance": h.distance,
            "confidence": h.confidence,
            "via": h.via,
            "fromId": h.from_id,
        }

    return {
        "root": impact.root,
        "rootName": impact.root_name,
        "rootType": impact.root_type,
        "downstream": [hop(h) for h in impact.downstream],
        "upstream": [hop(h) for h in impact.upstream],
        "counts": impact.counts(),
        "notes": impact.notes,
    }


def format_text(impact: Impact) -> str:
    """Terminal rendering, for `terrane impact`."""
    lines: List[str] = []
    lines.append("%s  (%s)" % (impact.root_name, impact.root))
    lines.append("")
    lines.append("Affected if this changes  -- %d" % len(impact.downstream))
    if not impact.downstream:
        lines.append("  nothing")
    for h in impact.downstream:
        lines.append(
            "  %-9s %-34s %-13s via %s" % (h.confidence, h.entity_id, h.entity_type, h.via)
        )
    lines.append("")
    lines.append("This depends on  -- %d" % len(impact.upstream))
    if not impact.upstream:
        lines.append("  nothing")
    for h in impact.upstream:
        lines.append(
            "  %-9s %-34s %-13s via %s" % (h.confidence, h.entity_id, h.entity_type, h.via)
        )
    for note in impact.notes:
        lines.append("")
        lines.append("! %s" % note)
    return "\n".join(lines)
