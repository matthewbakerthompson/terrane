"""Component types and building blocks: the modular layer below archetypes.

A component type is the vocabulary — a load balancer, a queue, a key vault —
with a category, a shape, and what each cloud calls it. Too small to design
with on its own: nobody assembles a workload by picking forty services.

A building block is the handful that always arrive together, with the relations
between them. Five or six blocks compose a workload, and the same block appears
in the AWS archetype, the Azure one, and freehand in a design review — so when
the WAF requirement changes it changes in one place.

Neither names a vendor. The block says *a public web tier*; resolving it
against AWS gives CloudFront, AWS WAF and an ALB, and against Azure gives Front
Door, Azure WAF and an Application Gateway. That is what makes a cloud
migration a re-parameterization rather than a redrawing, and it is TOGAF's
architecture-versus-solution building block distinction doing actual work.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Sequence

from .library import LibraryError, load_layer
from .schema import ENTITY_TYPES

COMPONENTS_DIR = "25_COMPONENTS"
BLOCKS_DIR = "26_BLOCKS"
PATTERNS_DIR = "27_PATTERNS"

#: The shapes a component type can declare. Each maps to a Mermaid bracket
#: pair in the renderer and a Cytoscape shape in the app; a name outside this
#: set would draw as a plain rectangle and nobody would know why.
SHAPES = ("rectangle", "cylinder", "hexagon", "rhomboid", "round-tag")

#: A pattern's lifecycle. A block carries no status because composition does
#: not expire; a decision does, and saying where it is in its life is most of
#: what a review board wants from a catalog.
PATTERN_STATUS = ("Candidate", "Approved", "Deprecated", "Retired")

_SAFE = re.compile(r"[^A-Za-z0-9]+")


class ComponentType(NamedTuple):
    component_type_id: str
    name: str
    category: str
    #: The entity type an instance of this becomes: a tech service, usually,
    #: or a system where the thing has users of its own.
    applies_to: str
    description: str
    shape: str
    #: What each provider calls it. The solution building block half.
    providers: Dict[str, str]
    #: Fields worth pre-filling. A load balancer lives at the edge, and having
    #: to remember that every time is how the field ends up empty.
    defaults: Dict[str, str]
    source_file: Optional[Path] = None
    #: The library it was read from, "" for the shipped one, and the file it
    #: stands in for when it says `replaces` (`library.load_layer`).
    library: str = ""
    replaced: str = ""


class Provided(NamedTuple):
    component: str
    #: Overrides for this one appearance, where a block needs to say something
    #: the component type cannot know.
    values: Dict[str, str] = {}


class BuildingBlock(NamedTuple):
    building_block_id: str
    name: str
    category: str
    description: str
    provides: Sequence[Provided]
    #: (from, to) pairs of component ids inside the block.
    relations: Sequence[tuple]
    defaults: Dict[str, str]
    source_file: Optional[Path] = None
    library: str = ""
    replaced: str = ""


def parse_component(data: dict, source: Optional[Path] = None) -> ComponentType:
    if not isinstance(data, dict) or "component_type_id" not in data:
        raise LibraryError("%s: missing component_type_id" % (source or "<component>"))
    applies_to = str(data.get("applies_to") or "tech_services")
    if applies_to not in ENTITY_TYPES:
        raise LibraryError(
            "component %s: applies_to names an unknown entity type %r"
            % (data["component_type_id"], applies_to)
        )
    return ComponentType(
        component_type_id=str(data["component_type_id"]),
        name=str(data.get("name") or data["component_type_id"]),
        category=str(data.get("category") or "Other"),
        applies_to=applies_to,
        description=str(data.get("description") or "").strip(),
        shape=str(data.get("shape") or "rectangle"),
        providers=dict(data.get("providers") or {}),
        defaults=dict(data.get("defaults") or {}),
        source_file=source,
    )


def parse_block(data: dict, source: Optional[Path] = None) -> BuildingBlock:
    if not isinstance(data, dict) or "building_block_id" not in data:
        raise LibraryError("%s: missing building_block_id" % (source or "<block>"))
    provides: List[Provided] = []
    for raw in data.get("provides") or []:
        if isinstance(raw, str):
            provides.append(Provided(component=raw))
            continue
        if not isinstance(raw, dict) or "component" not in raw:
            raise LibraryError(
                "block %s: every entry under `provides` names a component"
                % data["building_block_id"]
            )
        values = {k: v for k, v in raw.items() if k != "component"}
        provides.append(Provided(component=str(raw["component"]), values=values))

    relations = []
    for raw in data.get("relations") or []:
        if not isinstance(raw, dict) or "from" not in raw or "to" not in raw:
            raise LibraryError(
                "block %s: a relation needs `from` and `to`" % data["building_block_id"]
            )
        relations.append((str(raw["from"]), str(raw["to"])))

    return BuildingBlock(
        building_block_id=str(data["building_block_id"]),
        name=str(data.get("name") or data["building_block_id"]),
        category=str(data.get("category") or "Other"),
        description=str(data.get("description") or "").strip(),
        provides=provides,
        relations=relations,
        defaults=dict(data.get("defaults") or {}),
        source_file=source,
    )


def load_components(root: Path) -> Dict[str, ComponentType]:
    return load_layer(
        root, COMPONENTS_DIR, parse_component, lambda c: c.component_type_id, "component type"
    )


def load_blocks(root: Path, components: Optional[Dict[str, ComponentType]] = None):
    """Every block, checked against the components it claims to be made of.

    A block naming a component that does not exist would expand into an entity
    with no type and no defaults, which is worse than refusing to load.
    """
    known = components if components is not None else load_components(root)
    out: Dict[str, BuildingBlock] = load_layer(
        root, BLOCKS_DIR, parse_block, lambda b: b.building_block_id, "building block"
    )
    # Checked once every library is read: a block of the organization's may
    # be made of a component type of its own.
    for block in out.values():
        names = {p.component for p in block.provides}
        for provided in block.provides:
            if provided.component not in known:
                raise LibraryError(
                    "block %s provides unknown component type %r"
                    % (block.building_block_id, provided.component)
                )
            # A block says what a product runs on; the applications a
            # product is made of are parts in 28_MODULES. A block that
            # provided a document platform expanded into a system with a
            # technology-service id and a service category, which the
            # schema refused one field at a time; refused here, it says why.
            if known[provided.component].applies_to != "tech_services":
                raise LibraryError(
                    "block %s provides %r, which is an application type; a block "
                    "composes technology services, and an application is a part in 28_MODULES"
                    % (block.building_block_id, provided.component)
                )
        for source, target in block.relations:
            for end in (source, target):
                if end not in names:
                    raise LibraryError(
                        "block %s relates %r, which it does not provide"
                        % (block.building_block_id, end)
                    )
    return out


class Pattern(NamedTuple):
    """A building block plus the decision.

    The block says what arrives together. The pattern says what it is for,
    what it costs and when not to use it, and that paragraph is what an
    architecture review board actually governs.
    """

    pattern_id: str
    name: str
    status: str
    category: str
    #: The building blocks it is made of. At least one.
    blocks: Sequence[str]
    intent: str
    #: What it costs. A pattern with no stated cost is a sales pitch.
    consequences: str
    #: The cases it is wrong for. The paragraph a review board reads first.
    when_not_to_use: str
    #: Controls in the register the pattern is designed to meet.
    satisfies: Sequence[str]
    owner_org_id: str
    decision_ref: str
    #: The method's reference pattern this one implements, by id (PAT-002
    #: and so on). The method says what a well-governed integration of this
    #: kind must capture and which standards it satisfies; the pattern here
    #: says which blocks the house builds it from and when not to. One
    #: field, so the two are a click apart rather than a memory test.
    method_ref: str = ""
    source_file: Optional[Path] = None
    library: str = ""
    replaced: str = ""


def _listed(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [v.strip() for v in value.replace(";", ",").split(",") if v.strip()]
    return [str(v).strip() for v in value if str(v).strip()]


def parse_pattern(data: dict, source: Optional[Path] = None) -> Pattern:
    if not isinstance(data, dict) or "pattern_id" not in data:
        raise LibraryError("%s: missing pattern_id" % (source or "<pattern>"))
    pattern_id = str(data["pattern_id"])
    for key in ("intent", "consequences", "when_not_to_use"):
        if not str(data.get(key) or "").strip():
            raise LibraryError(
                "pattern %s has no %s; a pattern without the decision is a preference"
                % (pattern_id, key)
            )
    status = str(data.get("status") or "Candidate")
    if status not in PATTERN_STATUS:
        raise LibraryError(
            "pattern %s has status %r, expected one of %s"
            % (pattern_id, status, ", ".join(PATTERN_STATUS))
        )
    made_of = _listed(data.get("blocks"))
    if not made_of:
        raise LibraryError("pattern %s names no building block" % pattern_id)
    return Pattern(
        pattern_id=pattern_id,
        name=str(data.get("name") or pattern_id),
        status=status,
        category=str(data.get("category") or "Other"),
        blocks=made_of,
        intent=str(data["intent"]).strip(),
        consequences=str(data["consequences"]).strip(),
        when_not_to_use=str(data["when_not_to_use"]).strip(),
        satisfies=_listed(data.get("satisfies")),
        owner_org_id=str(data.get("owner_org_id") or ""),
        decision_ref=str(data.get("decision_ref") or ""),
        method_ref=str(data.get("method_ref") or ""),
        source_file=source,
    )


def check_pattern(pattern: Pattern, blocks: Dict[str, BuildingBlock]) -> None:
    """A pattern made of a block that does not exist is a decision about
    nothing, so it is refused rather than loaded."""
    for block_id in pattern.blocks:
        if block_id not in blocks:
            raise LibraryError(
                "pattern %s is made of unknown building block %r"
                % (pattern.pattern_id, block_id)
            )


def load_patterns(
    root: Path, blocks: Optional[Dict[str, BuildingBlock]] = None
) -> Dict[str, Pattern]:
    known = blocks if blocks is not None else load_blocks(root)
    out: Dict[str, Pattern] = load_layer(
        root, PATTERNS_DIR, parse_pattern, lambda p: p.pattern_id, "pattern"
    )
    for pattern in out.values():
        check_pattern(pattern, known)
    return out


def slug(text: str) -> str:
    return _SAFE.sub("-", str(text)).strip("-").lower()


def entity_id(prefix: str, name: str, component: str) -> str:
    return "%s-%s-%s" % (prefix, slug(name).upper(), slug(component).upper())


def expand(
    block: BuildingBlock,
    name: str,
    components: Dict[str, ComponentType],
    provider: Optional[str] = None,
    prefix: str = "TS",
) -> dict:
    """One block, instantiated for one thing.

    Precedence, tightest first: what the block says about this appearance, then
    what the block says generally, then what the component type says about
    itself. The component knows most about what it is; the block knows most
    about why it is here.

    `provider` resolves the solution half. Without one the entity carries the
    architecture building block and no product name, which is the honest state
    for a design that has not chosen a cloud yet.
    """
    entities: Dict[str, List[dict]] = {}
    created: Dict[str, str] = {}

    for provided in block.provides:
        component = components[provided.component]
        record = dict(component.defaults)
        record.update(block.defaults)
        record.update(provided.values)

        pk = ENTITY_TYPES[component.applies_to].pk
        this_id = record.pop("id", None) or entity_id(prefix, name, component.component_type_id)
        record[pk] = this_id
        record.setdefault("name", "%s %s" % (name, component.name))
        record.setdefault("description", component.description)
        record["component_type"] = component.component_type_id
        record.setdefault("service_category", component.category)
        record.setdefault("status", "Planned")
        if provider:
            product = component.providers.get(provider)
            record.setdefault("provider", provider)
            if product:
                record.setdefault("product", product)

        entities.setdefault(component.applies_to, []).append(record)
        created[component.component_type_id] = this_id

    relations: Dict[str, List[dict]] = {}
    for source, target in block.relations:
        # Both ends are components of this block, so both exist by now.
        relations.setdefault("tech_service_connects_to", []).append({
            "from_tech_service_id": created[source],
            "to_tech_service_id": created[target],
        })

    return {
        "block": block.building_block_id,
        "entities": entities,
        "relations": relations,
        "ids": created,
    }
