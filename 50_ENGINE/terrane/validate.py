"""Model quality gates.

Errors block a merge. Warnings are reported and do not. The split matters: a
gate that fails on everything gets switched off within a month, so only
referential and identity problems are fatal. Completeness problems that a human
must chase (an unowned system, a system nothing connects to) are warnings with a
count, which is the number worth putting on a governance dashboard.
"""

from __future__ import annotations

import re
from typing import Dict, List, NamedTuple, Optional, Sequence, Set, Tuple

from .adoption import candidates as shape_candidates
from .archetype import (
    ArchetypeError,
    effective_bind,
    has_landing_zone,
    landing_zone_gaps,
    landing_zone_index,
    resolve_kind,
    zone_binds,
)
from .blocks import LibraryError, load_blocks, load_components, load_patterns
from .answers import PATTERNS_KEY, EstateError, adopted_patterns, pattern_adoption
from .connections import load_connections, overlaps as connection_overlaps
from .model import Model
from .loader import load_folder
from .build_types import (
    BuildTypeError,
    check_build_types,
    conformance,
    load_build_types,
    uses_by_build_types,
)
from .modules import ModuleError, load_modules, members_of, uses_of
from .estate import from_the_package
from .places import problems as place_problems
from .query import View, ViewError, bind, render_targets, resolve
from .schema import ENTITY_TYPES, RELATION_TYPES, field_map

ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*(-[A-Z0-9]+)+$")

#: Prefix each entity type's ids are expected to use, following the
#: `P-{ORG}-{NNN}` shape the method's id policy sets out.
ID_PREFIXES = {
    "systems": "SYS-",
    "interfaces": "INT-",
    "offered_interfaces": "OI-",
    "data_assets": "DA-",
    "tech_services": "TS-",
    "capabilities": "CAP-",
    "org_units": "ORG-",
    "products": "PRD-",
    "policies": "POL-",
    "controls": "CTL-",
}


class Finding(NamedTuple):
    severity: str  # "error" or "warning"
    code: str
    message: str
    where: str = ""

    def format(self) -> str:
        prefix = "ERROR" if self.severity == "error" else "warn "
        location = " (%s)" % self.where if self.where else ""
        return "%s %-22s %s%s" % (prefix, self.code, self.message, location)


class Report(NamedTuple):
    findings: List[Finding]

    @property
    def errors(self) -> List[Finding]:
        return [f for f in self.findings if f.severity == "error"]

    @property
    def warnings(self) -> List[Finding]:
        return [f for f in self.findings if f.severity == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors


def _check_ids(model: Model) -> List[Finding]:
    findings: List[Finding] = []
    for type_name, entity_type in ENTITY_TYPES.items():
        prefix = ID_PREFIXES.get(type_name)
        for record in model.all_of(type_name):
            entity_id = str(record[entity_type.pk])
            where = record.get("_source_file", "")
            if not ID_PATTERN.match(entity_id):
                findings.append(
                    Finding(
                        "error",
                        "id.format",
                        "%s %r is not UPPER-CASE-HYPHENATED" % (entity_type.label, entity_id),
                        where,
                    )
                )
            elif prefix and not entity_id.startswith(prefix):
                findings.append(
                    Finding(
                        "warning",
                        "id.prefix",
                        "%s %r does not start with %r" % (entity_type.label, entity_id, prefix),
                        where,
                    )
                )
    return findings


def _check_fields(model: Model) -> List[Finding]:
    findings: List[Finding] = []
    for type_name, entity_type in ENTITY_TYPES.items():
        fields = field_map(entity_type)
        known = set(fields) | {entity_type.pk, "_type", "_source_file"}
        for record in model.all_of(type_name):
            entity_id = str(record[entity_type.pk])
            where = record.get("_source_file", "")
            for field in entity_type.fields:
                value = record.get(field.name)
                if field.required and value in (None, ""):
                    findings.append(
                        Finding(
                            "error",
                            "field.required",
                            "%s %s is missing %s" % (entity_type.label, entity_id, field.name),
                            where,
                        )
                    )
                if field.enum and value not in (None, "") and str(value) not in field.enum:
                    findings.append(
                        Finding(
                            "error",
                            "field.enum",
                            "%s %s has %s=%r, expected one of %s"
                            % (entity_type.label, entity_id, field.name, value, ", ".join(field.enum)),
                            where,
                        )
                    )
            for key in record:
                if key.startswith("_") or key in known:
                    continue
                findings.append(
                    Finding(
                        "warning",
                        "field.unknown",
                        "%s %s carries unrecognized field %r"
                        % (entity_type.label, entity_id, key),
                        where,
                    )
                )
    return findings


def _check_references(model: Model) -> List[Finding]:
    findings: List[Finding] = []
    for type_name, entity_type in ENTITY_TYPES.items():
        for field in entity_type.fields:
            if not field.ref:
                continue
            for record in model.all_of(type_name):
                value = record.get(field.name)
                if value in (None, ""):
                    continue
                if model.get(field.ref, str(value)) is None:
                    findings.append(
                        Finding(
                            "error",
                            "ref.dangling",
                            "%s %s.%s points at %r, which is not a known %s"
                            % (
                                entity_type.label,
                                record[entity_type.pk],
                                field.name,
                                value,
                                field.ref,
                            ),
                            record.get("_source_file", ""),
                        )
                    )
    for name, spec in RELATION_TYPES.items():
        for row in model.relation_rows(name):
            for column, target in (
                (spec.left_column, spec.left),
                (spec.right_column, spec.right),
            ):
                value = row.get(column)
                if value and model.get(target, str(value)) is None:
                    findings.append(
                        Finding(
                            "error",
                            "ref.dangling",
                            "relation %s row references %s=%r, which is not a known %s"
                            % (name, column, value, target),
                            str(row.get("_source", "")),
                        )
                    )
    return findings


def _check_connectivity(model: Model) -> List[Finding]:
    findings: List[Finding] = []
    for record in model.all_of("systems"):
        system_id = str(record["system_id"])
        if str(record.get("status")) in ("Retired",):
            continue
        if not model.neighbors(system_id):
            findings.append(
                Finding(
                    "warning",
                    "graph.orphan",
                    "system %s has no interfaces, services, data or capabilities recorded"
                    % system_id,
                    record.get("_source_file", ""),
                )
            )
    for record in model.all_of("interfaces"):
        if record.get("source_system_id") == record.get("target_system_id"):
            findings.append(
                Finding(
                    "warning",
                    "graph.self_loop",
                    "interface %s connects %s to itself"
                    % (record["interface_id"], record.get("source_system_id")),
                    record.get("_source_file", ""),
                )
            )
    return findings


def _check_offered(model: Model) -> List[Finding]:
    """A connection through an offered interface, against the interface.

    The interface's own system is one end of every connection through it:
    the one called, or the one publishing. A connection naming another
    system's API between two systems that offer neither is the record of a
    door nobody at either end opens, and is refused. A protocol that differs
    from the interface's is said and left: an API can take a webhook as well
    as a call, but not an MQ message."""
    findings: List[Finding] = []
    for record in model.all_of("interfaces"):
        offered_id = str(record.get("offered_interface_id") or "")
        offered = model.get("offered_interfaces", offered_id) if offered_id else None
        if offered is None:
            # Unset, or dangling, which the reference check says.
            continue
        where = record.get("_source_file", "")
        owner = str(offered.get("system_id") or "")
        ends = (str(record.get("source_system_id") or ""), str(record.get("target_system_id") or ""))
        if owner and owner not in ends:
            findings.append(Finding(
                "error", "interface.offered_by",
                "interface %s goes through %s, which %s offers, and joins %s and %s"
                % (record["interface_id"], offered_id, owner, ends[0], ends[1]), where))
        said, offers = str(record.get("protocol") or ""), str(offered.get("protocol") or "")
        if said and offers and said.lower() != offers.lower():
            findings.append(Finding(
                "warning", "interface.unlike_offered",
                "interface %s says %s and goes through %s, which is %s"
                % (record["interface_id"], said, offered_id, offers), where))
    return findings


def _check_governance(model: Model) -> List[Finding]:
    """Completeness checks that map to the governance dashboard."""
    findings: List[Finding] = []
    # Only a model that holds a control register can be asked which systems
    # record none of it. Without one the warning would fire on every system
    # in every model, and a warning that always fires is one nobody reads.
    has_register = bool(model.all_of("controls"))
    governed = {
        str(row.get("system_id"))
        for row in model.relation_rows("system_governed_by_control")
    }
    for record in model.all_of("systems"):
        system_id = str(record["system_id"])
        where = record.get("_source_file", "")
        if (
            has_register
            and system_id not in governed
            and str(record.get("data_classification_supported")) == "Restricted"
            and str(record.get("status")) in ("Active", "Planned")
        ):
            findings.append(
                Finding(
                    "warning",
                    "governance.no_control",
                    "system %s handles Restricted data and records no control" % system_id,
                    where,
                )
            )
        if not record.get("cmdb_ci_sys_id"):
            findings.append(
                Finding(
                    "warning",
                    "cmdb.unlinked",
                    "system %s has no cmdb_ci_sys_id" % system_id,
                    where,
                )
            )
        if str(record.get("criticality")) == "High" and not record.get("service_tier"):
            findings.append(
                Finding(
                    "warning",
                    "governance.tier",
                    "system %s is High criticality with no service_tier" % system_id,
                    where,
                )
            )
    for record in model.all_of("data_assets"):
        if str(record.get("pii_flag")) == "Yes" and not record.get("classification"):
            findings.append(
                Finding(
                    "warning",
                    "governance.classification",
                    "data asset %s holds PII with no classification" % record["data_asset_id"],
                    record.get("_source_file", ""),
                )
            )
    return findings


#: A planning quarter, which is the only date shape the change entities use.
#: Written this way it also sorts, so a comparison of two of them is sound
#: rather than lucky; anything else is reported instead of being compared.
_QUARTER = re.compile(r"^\d{4}-Q[1-4]$")


def _check_change(model: Model) -> List[Finding]:
    """The change side: what is scheduled, on whose decision, and when.

    Every check here is silent in a model that records no work packages, the
    same way the governance checks are silent without a control register. A
    warning that fires on every model is one nobody reads.
    """
    findings: List[Finding] = []
    packages = model.all_of("work_packages")

    for record in list(packages) + model.all_of("roadmaps"):
        entity_type = ENTITY_TYPES[record["_type"]]
        entity_id = str(record[entity_type.pk])
        where = record.get("_source_file", "")
        start, end = str(record.get("start_date") or ""), str(record.get("end_date") or "")
        for value in (start, end):
            if value and not _QUARTER.match(value):
                findings.append(
                    Finding(
                        "warning",
                        "change.quarter",
                        "%s %s has date %r, which is not a YYYY-Qn quarter"
                        % (entity_type.label, entity_id, value),
                        where,
                    )
                )
        # Only compared when both are quarters, because a comparison of two
        # strings of unknown shape would answer confidently and wrongly.
        if _QUARTER.match(start) and _QUARTER.match(end) and end < start:
            findings.append(
                Finding(
                    "error",
                    "change.dates",
                    "%s %s ends in %s, before it starts in %s"
                    % (entity_type.label, entity_id, end, start),
                    where,
                )
            )

    if not packages:
        return findings

    scheduled = {
        str(row.get("system_id"))
        for row in model.relation_rows("work_package_affects_system")
    }
    for record in model.all_of("systems"):
        if str(record.get("status")) != "Planned":
            continue
        system_id = str(record["system_id"])
        if system_id not in scheduled:
            findings.append(
                Finding(
                    "warning",
                    "change.unscheduled",
                    "system %s is planned and no work package delivers it" % system_id,
                    record.get("_source_file", ""),
                )
            )

    # A work package that names no change request was funded without going to
    # the board. That is a thing that happens, and making it visible is most
    # of the point of holding a change register at all.
    for record in packages:
        if not record.get("change_request_id"):
            findings.append(
                Finding(
                    "warning",
                    "change.no_decision",
                    "work package %s names no change request"
                    % record["work_package_id"],
                    record.get("_source_file", ""),
                )
            )

    # A work package on a decision that said no. `change.no_decision` is the
    # package that never went to the board; this is the one that went, was
    # told to wait or not to, and is scheduled anyway. An undecided request is
    # not a finding -- a proposal in flight has work planned behind it by
    # design -- and neither is a package that has itself been retired.
    decisions = {
        str(r["change_request_id"]): str(r.get("governance_decision") or "")
        for r in model.all_of("architecture_change_requests")
    }
    for record in packages:
        request = str(record.get("change_request_id") or "")
        decision = decisions.get(request, "")
        status = str(record.get("status") or "")
        if decision in ("Rejected", "Deferred") and status not in ("Deprecated", "Retired"):
            findings.append(
                Finding(
                    "warning",
                    "change.against_decision",
                    "work package %s is %s on %s, which the board %s"
                    % (record["work_package_id"], status.lower() or "scheduled",
                       request, decision.lower()),
                    record.get("_source_file", ""),
                )
            )
    return findings


def _nothing_of_its_kind(model: Model, view: View) -> List[str]:
    """The kinds of thing a view shows, when the model holds none of any of
    them: a capability map in an estate that has not brought its capability
    map in yet. That is a model being built a layer at a time, which is how
    every adoption goes, and it was an error -- thirty-five of them the day an
    estate imported its first three systems. Empty when any of them exist,
    because then a view that draws nothing is a filter that matches nothing,
    which is a fault; and empty for a view that pins, since a pin names a
    thing that should be there."""
    clauses = view.scope.get("include") or []
    kinds = [str(c.get("type")) for c in clauses if isinstance(c, dict) and c.get("type")]
    if not kinds or view.scope.get("pin"):
        return []
    if any(model.all_of(kind) for kind in kinds if kind in ENTITY_TYPES):
        return []
    return list(dict.fromkeys(kinds))


def _check_views(model: Model, views: Sequence[View]) -> List[Finding]:
    findings: List[Finding] = []
    # An empty model is a starting point, not a defect. A view that matches
    # nothing only means something once there is something to match.
    empty_model = not any(model.entities.values())
    by_id = {(view.own or view).view_id: (view.own or view) for view in views}
    for view in views:
        # A place naming a view that is not here draws the diagram without
        # it, which nobody looking at the picture would know to miss.
        for problem in place_problems(view, by_id):
            findings.append(
                Finding(
                    "error",
                    "view.place",
                    "view %s %s" % (view.view_id, problem),
                    str(view.source_file or ""),
                )
            )
        # A pin or a hide is a person's decision about one drawing, written
        # by id; when the thing goes, the decision is left behind, and the
        # view still draws, so nothing else would notice.
        for key, verb in (("pin", "pins"), ("hide", "hides")):
            named = view.scope.get(key) or []
            for entity_id in named if isinstance(named, list) else [named]:
                entity_id = str(entity_id)
                if "{" not in entity_id and model.find(entity_id) is None:
                    findings.append(
                        Finding(
                            "warning",
                            "view.stale_pin",
                            "view %s %s %s, which the model does not hold"
                            % (view.view_id, verb, entity_id),
                            str(view.source_file or ""),
                        )
                    )
        if view.parameters:
            # A parameterized view has no single graph: validate the one
            # `render_for` would draw first. One whose selection is empty --
            # an onboarding view in a model with no product on a shape yet --
            # has nothing to draw and nothing wrong with it; it is reported as
            # a selection, not bound to nothing and reported as a fault.
            targets = render_targets(model, view)
            if not targets:
                findings.append(
                    Finding(
                        "warning",
                        "view.no_subjects",
                        "view %s takes %s and render_for selects nothing yet"
                        % (view.view_id, ", ".join(p.name for p in view.parameters)),
                        str(view.source_file or ""),
                    )
                )
                continue
        try:
            graph = resolve(model, bind(
                view,
                dict(render_targets(model, view)) if view.parameters else None,
                model,
            ))
        except ViewError as exc:
            waiting = [] if empty_model else _nothing_of_its_kind(model, view)
            if waiting:
                findings.append(
                    Finding(
                        "warning",
                        "view.nothing_yet",
                        "view %s draws %s, and the model holds none yet"
                        % (view.view_id, _spoken(k.replace("_", " ") for k in waiting)),
                        str(view.source_file or ""),
                    )
                )
                continue
            if not empty_model and from_the_package(model.root, view):
                # The estate did not write a shipped view and cannot edit
                # one; that it draws nothing here is news, not a fault of the
                # estate's, and the gate would otherwise fail on a view
                # nobody on it could change.
                findings.append(
                    Finding(
                        "warning",
                        "view.shipped_nothing",
                        "%s; it is shipped with terrane, and `shipped_views: {from: package, without: [%s]}` "
                        "leaves it out" % (exc, view.view_id),
                        str(view.source_file or ""),
                    )
                )
                continue
            findings.append(
                Finding(
                    "warning" if empty_model else "error",
                    "view.unresolvable",
                    str(exc),
                    str(view.source_file or ""),
                )
            )
            continue
        limit = int(view.limits.get("max_nodes", 0) or 0)
        # An offered interface drawn on its owner is not one of the limit's
        # boxes: the integration diagram's six APIs read as six truncations.
        counted = sum(1 for node in graph.nodes if node.entity_type != "offered_interfaces")
        if limit and counted >= limit:
            findings.append(
                Finding(
                    "warning",
                    "view.truncated",
                    "view %s hit its max_nodes limit of %d" % (view.view_id, limit),
                    str(view.source_file or ""),
                )
            )
        # Only a view that asked for edges and got none is suspect. A view with
        # no `edges` clause is a catalog on purpose, and warning about it just
        # trains people to ignore warnings.
        if view.edges and not graph.edges:
            findings.append(
                Finding(
                    "warning",
                    "view.no_edges",
                    "view %s declares edges but renders none; check the `via` fields"
                    % view.view_id,
                    str(view.source_file or ""),
                )
            )
    return findings


def _spoken(items) -> str:
    """"a", "a and b", "a, b and c": a list the way a finding reads it out."""
    items = [str(i) for i in items]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _check_connections(model: Model) -> List[Finding]:
    """The connection kinds, against each other and the library's patterns.
    A kind's pattern is held the way a product's is, since every interface
    proposed from the kind carries it."""
    try:
        kinds = load_connections(model.root)
    except LibraryError as exc:
        return [Finding("error", "connection.invalid", str(exc))]
    if not kinds:
        return []
    findings = [Finding("error", "connection.overlap", message) for message in connection_overlaps(kinds)]
    try:
        patterns = load_patterns(model.root)
    except LibraryError:
        # Said once already, by the library check.
        return findings
    for kind in kinds.values():
        where = str(kind.source or "")
        for pattern_id in kind.patterns:
            pattern = patterns.get(pattern_id)
            if pattern is None:
                findings.append(Finding(
                    "error", "connection.unknown_pattern",
                    "connection kind %s applies %r, which is not in 27_PATTERNS"
                    % (kind.connection_id, pattern_id), where))
            elif pattern.status in ("Deprecated", "Retired"):
                findings.append(Finding(
                    "warning", "connection.deprecated_pattern",
                    "connection kind %s proposes every new connection with %s, which is %s"
                    % (kind.connection_id, pattern_id, pattern.status.lower()), where))
    return findings


def _check_library(model: Model) -> List[Finding]:
    """The component types, blocks and patterns, and what the model says
    about them.

    Nothing under `10_MODEL/` reads the library, so a broken block file used
    to surface only when somebody opened the app. A library CI does not check
    is a library that breaks on the day it is needed.
    """
    findings: List[Finding] = []
    try:
        components = load_components(model.root)
        blocks = load_blocks(model.root, components)
        patterns = load_patterns(model.root, blocks)
        modules = load_modules(model.root)
    except (LibraryError, ModuleError) as exc:
        return [Finding("error", "library.invalid", str(exc))]

    controls = {str(c["control_id"]) for c in model.all_of("controls")}
    org_units = {str(o["org_unit_id"]) for o in model.all_of("org_units")}
    # Who owns a pattern and which controls it meets are the estate's, in
    # model.yaml; the shipped patterns name neither, so an estate that is
    # not the sample hears about its own answers and nobody else's. They
    # used to name the card issuer's, and the health system heard fifty-one
    # warnings about a register it never had.
    config_file = str(model.root / "10_MODEL" / "model.yaml")
    try:
        adoption = pattern_adoption(model.config)
        patterns = adopted_patterns(patterns, model.config)
    except EstateError as exc:
        findings.append(Finding("error", "pattern.adoption", str(exc), config_file))
        adoption = {}
    for pattern_id in sorted(set(adoption) - set(patterns)):
        findings.append(
            Finding(
                "error",
                "pattern.unknown",
                "`%s` in model.yaml says who owns %r, which is not in 27_PATTERNS"
                % (PATTERNS_KEY, pattern_id),
                config_file,
            )
        )
    for pattern in patterns.values():
        where = str(pattern.source_file or "")
        for control_id in pattern.satisfies:
            # Only a model holding a register can say a control is missing
            # from it.
            if controls and control_id not in controls:
                findings.append(
                    Finding(
                        "warning",
                        "pattern.unknown_control",
                        "pattern %s satisfies %r here, which is not in the register"
                        % (pattern.pattern_id, control_id),
                        where,
                    )
                )
        if pattern.owner_org_id and org_units and pattern.owner_org_id not in org_units:
            findings.append(
                Finding(
                    "warning",
                    "pattern.unknown_owner",
                    "pattern %s is owned by %r here, which is not a known org unit"
                    % (pattern.pattern_id, pattern.owner_org_id),
                    where,
                )
            )
    # A product claiming a pattern the library does not hold is the adoption
    # report lying, so it is an error rather than a warning. A product on a
    # pattern the board has deprecated is a finding, so it is a warning: the
    # count of those going down is what a pattern retirement looks like.
    # Interfaces are held to the same two rules: three of the method's
    # patterns are about how two systems talk, and the interface is the
    # record that knows.
    for type_name, pk, label in (
        ("products", "product_id", "product"),
        ("interfaces", "interface_id", "interface"),
    ):
        for record in model.all_of(type_name):
            for pattern_id in model.list_of(record, "patterns"):
                if pattern_id not in patterns:
                    findings.append(
                        Finding(
                            "error",
                            "pattern.unknown",
                            "%s %s applies %r, which is not in 27_PATTERNS"
                            % (label, record[pk], pattern_id),
                            record.get("_source_file", ""),
                        )
                    )
                elif patterns[pattern_id].status in ("Deprecated", "Retired"):
                    findings.append(
                        Finding(
                            "warning",
                            "pattern.deprecated",
                            "%s %s applies %s, which is %s"
                            % (label, record[pk], pattern_id,
                               patterns[pattern_id].status.lower()),
                            record.get("_source_file", ""),
                        )
                    )

    # What a shape composes it has to be able to bind. Every part says what
    # it needs from the shape; checked here, a shape that binds no `vendor`
    # fails on `terrane validate` with the part's name, rather than on the day an
    # instance is expanded.
    # A kind is a component type. A service whose kind the library does not
    # hold still draws -- the category falls back -- but it can never answer
    # for a part, and a misspelled `kms` on the one tagged service is exactly
    # the gap nothing else would find.
    for record in model.all_of("tech_services"):
        named = [str(record.get("component_type") or "")] + model.list_of(record, "answers_for")
        for kind in named:
            if kind and kind not in components:
                findings.append(
                    Finding(
                        "error",
                        "library.unknown_kind",
                        "technology service %s says it is a `%s`, which is not a component type"
                        % (record["tech_service_id"], kind),
                        record.get("_source_file", ""),
                    )
                )

    services = {str(s["tech_service_id"]) for s in model.all_of("tech_services")}
    landing = landing_zone_index(model.all_of("tech_services"))
    for archetype in model.archetypes.values():
        where = str(archetype.source_file or archetype.archetype_id)
        bound = {p.name for p in archetype.parameters}
        bound |= {"instance_id", "name", ENTITY_TYPES[archetype.applies_to].pk}
        composed: List[Tuple[str, str]] = []
        for entry in archetype.modules:
            composed.append((str(entry.get("module")), "composes"))
        for slot in archetype.slots:
            for option in slot.options:
                composed.append((str(option), "offers in slot %s" % slot.name))
        # The landing zone the shape describes, by kind. A contradiction
        # between two blocks is a finding here rather than an expansion error.
        try:
            zone = effective_bind(archetype)
        except ArchetypeError as exc:
            findings.append(Finding("error", "library.bind_conflict", str(exc), where))
            zone = dict(archetype.bind)
        provider = archetype.provider or ""
        has_zone = has_landing_zone(provider, landing)
        waiting_for: List[str] = []
        # What a block binds to the landing zone rather than to a service by
        # id: the kind has to be one, and the zone has to answer it, or the
        # first product on the shape fails to expand.
        try:
            to_zone = zone_binds(archetype)
        except ArchetypeError:
            to_zone = []
        for kind, block in to_zone:
            if kind not in components:
                findings.append(
                    Finding(
                        "error",
                        "library.bind_kind",
                        "archetype %s binds %r on block %s to the landing zone, which is not "
                        "a component type" % (archetype.archetype_id, kind, block),
                        where,
                    )
                )
                continue
            found, candidates = resolve_kind(kind, provider, landing)
            if found:
                continue
            if not has_zone:
                if kind not in waiting_for:
                    waiting_for.append(kind)
                continue
            findings.append(
                Finding(
                    "error",
                    "library.ambiguous_kind" if candidates else "library.unbound_component",
                    "archetype %s binds `%s` on block %s to the landing zone, and the %s landing "
                    "zone has %s"
                    % (archetype.archetype_id, kind, block, provider or "shared",
                       "%s; say which under `bind`" % " and ".join(candidates) if candidates
                       else "none of that kind; tag one `landing-zone`"),
                    where,
                )
            )
        for kind, service in sorted(zone.items()):
            if kind not in components:
                findings.append(
                    Finding(
                        "error",
                        "library.bind_kind",
                        "archetype %s binds %r, which is not a component type"
                        % (archetype.archetype_id, kind),
                        where,
                    )
                )
            if services and service not in services:
                if not has_zone:
                    # An estate on one cloud keeps the other clouds' shapes,
                    # and the services those bind are ones it has no reason
                    # to hold. The healthcare estate, all Azure, had eleven
                    # errors from the AWS and Google shapes for exactly
                    # that; the shape is waiting, as it is on an empty model.
                    if kind not in waiting_for:
                        waiting_for.append(kind)
                    continue
                findings.append(
                    Finding(
                        "error",
                        "library.bind_unknown",
                        "archetype %s binds %s to %r, which is not a known technology service"
                        % (archetype.archetype_id, kind, service),
                        where,
                    )
                )
        for module_id, how in composed:
            if module_id not in modules:
                findings.append(
                    Finding(
                        "error",
                        "library.unknown_part",
                        "archetype %s %s %r, which is not in 28_MODULES"
                        % (archetype.archetype_id, how, module_id),
                        where,
                    )
                )
                continue
            for member in members_of(modules[module_id], modules):
                missing = [n for n in modules[member].needs if n not in bound]
                if missing:
                    findings.append(
                        Finding(
                            "error",
                            "library.unbound_need",
                            "archetype %s %s %s, which needs {%s} from the shape, "
                            "and the shape binds no such parameter"
                            % (archetype.archetype_id, how, member, "}, {".join(missing)),
                            where,
                        )
                    )
                # A kind the part names that the shape binds nowhere and the
                # part does not default is the AWS-on-Azure mistake, caught
                # before any instance is expanded.
                for param in modules[member].parameters:
                    if not param.component or param.default is not None:
                        continue
                    if param.component in zone or param.name in bound:
                        continue
                    found, candidates = resolve_kind(param.component, archetype.provider, landing)
                    if found:
                        continue
                    if not has_zone:
                        if param.component not in waiting_for:
                            waiting_for.append(param.component)
                        continue
                    if len(candidates) > 1:
                        findings.append(
                            Finding(
                                "error",
                                "library.ambiguous_kind",
                                "archetype %s %s %s, whose %r is of kind `%s`, and the %s "
                                "landing zone has %s; say which under `bind: {%s: ...}`"
                                % (archetype.archetype_id, how, member, param.name,
                                   param.component, archetype.provider or "shared",
                                   " and ".join(candidates), param.component),
                                where,
                            )
                        )
                        continue
                    findings.append(
                        Finding(
                            "error",
                            "library.unbound_component",
                            "archetype %s %s %s, whose %r is of kind `%s`, and no landing-zone "
                            "service of that kind exists for %s; tag one `landing-zone` or add "
                            "`bind: {%s: TS-...}`"
                            % (archetype.archetype_id, how, member, param.name,
                               param.component, archetype.provider or "any provider",
                               param.component),
                            where,
                        )
                    )
        if waiting_for:
            # No landing zone recorded on this provider at all: the shape is
            # waiting for one, which is where a new estate starts, and a
            # product put on it would fail to expand and say so then. One
            # finding per shape naming every kind, where there used to be an
            # error per part -- twenty-five on an empty model.
            findings.append(
                Finding(
                    "warning",
                    "library.no_landing_zone",
                    "archetype %s needs a landing zone on %s -- %s -- and the model records "
                    "none yet; tag those technology services `landing-zone` when they are added"
                    % (archetype.archetype_id, provider or "a neutral provider",
                       ", ".join(sorted(waiting_for))),
                    where,
                )
            )

    # What each landing zone cannot answer, ahead of any shape asking. The
    # error above fires once a shape composes the part; this is the same
    # fact one step earlier -- the kinds the parts name that a provider's
    # tagged services do not cover -- so the onboarding that would stop on
    # it is told before it starts. A warning: a gap in a landing zone is a
    # fact about the estate, not a fault in the library, and a shape that
    # binds the kind by hand composes fine and is named as where the fix is.
    for gap in landing_zone_gaps(modules, model.archetypes.values(), landing):
        askers = _spoken("%s (%s)" % pair for pair in gap.asked_by)
        by_hand = ""
        if gap.bound_by:
            by_hand = ", and %s bind%s it by hand" % (
                _spoken(gap.bound_by), "s" if len(gap.bound_by) == 1 else "")
        findings.append(
            Finding(
                "warning",
                "library.landing_zone_gap",
                "the %s landing zone answers for no `%s`; %s ask%s for one%s; tag a "
                "service of that kind on %s `landing-zone`, or every shape there binds it"
                % (gap.provider, gap.kind, askers, "s" if len(gap.asked_by) == 1 else "",
                   by_hand, gap.provider),
            )
        )

    # A hand-authored product whose systems are, by category, what a shape's
    # required parts would make. Not a fault -- the shape came after the
    # product -- but a product that is a handful of answers away from being
    # on one, which is the modular layer's whole offer. Two shapes fitting
    # equally well are two findings; the product is one or the other.
    for candidate in shape_candidates(model, model.archetypes.values(), modules):
        lacking = ""
        if candidate.missing_optional:
            lacking = " (no %s, which %s optional)" % (
                _spoken(a for a, _c in candidate.missing_optional),
                "is" if len(candidate.missing_optional) == 1 else "are")
        findings.append(
            Finding(
                "warning",
                "library.shape_candidate",
                "product %s has the systems of %s's %s%s and is not on a shape"
                % (candidate.product_id, candidate.archetype_id,
                   _spoken(a for a, _c in candidate.covered), lacking),
                str(model.get("products", candidate.product_id).get("_source_file", "")),
            )
        )

    # A part nothing composes is either waiting for its shape or forgotten,
    # and the library could not tell which until it could say so.
    used = uses_of(modules, list(model.archetypes.values()) + list(model.composed.values()))
    for module_id in _parts_named_by_instances(model):
        if module_id in used:
            used[module_id].append("an instance")
    # A part a build type requires, includes or offers is composed by that
    # type: the application parts live there until a product picks them.
    try:
        uses_by_build_types(used, load_build_types(model.root), modules)
    except BuildTypeError:
        pass
    for module_id, by in sorted(used.items()):
        if not by:
            findings.append(
                Finding(
                    "warning",
                    "library.unused_part",
                    "module %s is composed by no shape, kit, slot or instance" % module_id,
                    str(modules[module_id].source_file or ""),
                )
            )
    return findings


def _parts_named_by_instances(model: Model) -> Set[str]:
    """Module ids that instance files add under `modules`.

    Read off the files rather than the loaded model, because expansion
    consumes that key: the record in memory no longer says which parts it
    asked for, only which entities it got.
    """
    named: Set[str] = set()
    for entity_type in ENTITY_TYPES.values():
        folder = model.root / "10_MODEL" / entity_type.folder
        if not folder.exists():
            continue
        for _path, record in load_folder(folder):
            if not isinstance(record, dict) or not (record.get("archetype") or record.get("compose")):
                continue
            composed = record.get("compose") if isinstance(record.get("compose"), dict) else {}
            for entry in list(record.get("modules") or []) + list(composed.get("modules") or []):
                module_id = entry.get("module") if isinstance(entry, dict) else entry
                if module_id:
                    named.add(str(module_id))
            for value in (record.get("choose") or {}).values():
                if value and str(value) != "none":
                    named.add(str(value))
    return named


def _check_build_types(model: Model) -> List[Finding]:
    """The build types, and how far each product is from its standard.

    A type that names a part the library lacks, or a shape on another
    provider, is an error: the panel would offer something that cannot be
    built. A product that departs from its type is a warning, one per
    departure, because a deviation is a finding for a design review rather
    than a broken model.
    """
    findings: List[Finding] = []
    try:
        types = load_build_types(model.root)
        modules = load_modules(model.root)
    except (BuildTypeError, ModuleError) as exc:
        return [Finding("error", "types.invalid", str(exc))]
    for problem, where in check_build_types(types, modules, model.archetypes.values()):
        findings.append(Finding("error", "types.invalid", problem, where))
    for record in model.all_of("products"):
        type_id = str(record.get("build_type") or "")
        if not type_id:
            continue
        product_id = str(record.get("product_id"))
        where = record.get("_source_file", "")
        build_type = types.get(type_id)
        if build_type is None:
            findings.append(
                Finding("error", "types.unknown",
                        "product %s is a %r, which is not in 29_TYPES" % (product_id, type_id), where)
            )
            continue
        parts = model.parts.get(product_id, [])
        fit = conformance(build_type, parts, modules)
        for part in fit.missing:
            findings.append(
                Finding("warning", "types.missing_required",
                        "product %s is a %s without %s, which every %s has"
                        % (product_id, type_id, part, type_id), where)
            )
        for part in fit.dropped:
            findings.append(
                Finding("warning", "types.deviation",
                        "product %s is a %s without %s, which the type includes unless there is a reason"
                        % (product_id, type_id, part), where)
            )
        for part in fit.unlisted:
            findings.append(
                Finding("warning", "types.unlisted_part",
                        "product %s is a %s with %s, which the type neither includes nor offers"
                        % (product_id, type_id, part), where)
            )
    return findings


def _check_estate(model: Model) -> List[Finding]:
    """The estate's pins: a terrane outside `requires_terrane` is an error,
    since a change checked by another release can pass here and fail for
    everyone else; and a pin that cannot be read is one nobody is held to."""
    from .estate import problems

    return [Finding("error", code, message, "10_MODEL/model.yaml") for code, message in problems(model.root)]


def run(model: Model, views: Optional[Sequence[View]] = None) -> Report:
    findings: List[Finding] = []
    findings.extend(_check_estate(model))
    findings.extend(_check_ids(model))
    findings.extend(_check_fields(model))
    findings.extend(_check_references(model))
    findings.extend(_check_connectivity(model))
    findings.extend(_check_offered(model))
    findings.extend(_check_governance(model))
    findings.extend(_check_change(model))
    findings.extend(_check_library(model))
    findings.extend(_check_connections(model))
    findings.extend(_check_build_types(model))
    if views:
        findings.extend(_check_views(model, views))
    for warning in model.warnings:
        findings.append(Finding("warning", "model.load", warning))
    return Report(findings=findings)


def summarize(report: Report) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for finding in report.findings:
        counts[finding.code] = counts.get(finding.code, 0) + 1
    return counts
