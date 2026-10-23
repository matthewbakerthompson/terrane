"""Archetype definition and expansion.

An archetype is a reusable shape: the systems, interfaces, data assets and
relations that a particular kind of product or service always brings with it.
An instance supplies parameters and, where reality differs, overrides and
exclusions. Expanding an instance produces ordinary entities that the rest of
the engine cannot distinguish from hand-written ones, except by the
`archetype_instance` field that records where they came from.

An archetype can be built on building blocks. A block says what always arrives
together; the archetype says which of those parts the landing zone already
provides (`bind`) and which are created for this product. That is what makes
a change to a block reach every archetype at once, and it is why the WAF
ruleset and the DNS record -- the two things the first hand-written version of
the AWS shape forgot -- arrive without anyone listing them.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Set, Tuple

from .blocks import BuildingBlock, ComponentType
from .blocks import entity_id as block_entity_id
from .library import load_layer
from .modules import Module, ModuleError, _listed, module_entries
from .schema import ENTITY_TYPES, RELATION_TYPES

_TOKEN = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)((?:\|[a-z_]+)*)\}")

#: The library, as expansion needs it: component types, blocks, and modules.
#: A two-tuple of the first two is still accepted, and a fourth element -- the
#: landing zone by provider and kind, from `landing_zone_index` -- lets a part
#: parameter that names a kind resolve without the shape binding it. A fifth,
#: the estate's `answers` from `model.yaml`, is what a parameter marked
#: `estate` takes when the product does not say.
Library = Tuple[Dict[str, ComponentType], Dict[str, BuildingBlock], Dict[str, Module]]

#: The tag a shared technology service carries to say a part may resolve to
#: it. The per-product network primitives -- a NAT gateway, a subnet -- are
#: of the same kinds as the landing zone's services and must not be found
#: by a part asking for "the private egress here", so the marker is opt-in.
#: It is also what a shape writes under a block's `bind` for a component the
#: landing zone provides: `api-gateway: landing-zone`. The shapes used to name
#: the sample's own services there, so an estate building on them had to hold
#: records under the sample's ids.
LANDING_ZONE_TAG = "landing-zone"

#: Providers that mean "nowhere in particular": a SaaS identity provider is
#: the same service on every cloud, and resolves for any shape.
NEUTRAL_PROVIDERS = ("", "SaaS", "External")


def landing_zone_index(services) -> Dict[Tuple[str, str], List[str]]:
    """(provider, component type) -> the landing-zone services of that kind.

    Provider is the record's `cloud_provider`, or "" for a neutral one. Only
    services tagged `landing-zone` are listed, and only ones with a component
    type: a kind can only resolve to something that says what kind it is. A
    service that is two kinds -- Key Vault holds the keys as well as the
    secrets -- says so under `answers_for`, and is listed under each.
    """
    out: Dict[Tuple[str, str], List[str]] = {}
    for record in services:
        if LANDING_ZONE_TAG not in _listed(record.get("tags")):
            continue
        kind = str(record.get("component_type") or "")
        if not kind:
            continue
        provider = str(record.get("cloud_provider") or "")
        if provider in NEUTRAL_PROVIDERS:
            provider = ""
        for each in [kind] + [k for k in _listed(record.get("answers_for")) if k != kind]:
            out.setdefault((provider, each), []).append(str(record["tech_service_id"]))
    for ids in out.values():
        ids.sort()
    return out


def resolve_kind(
    kind: str, provider: str, zone: Dict[Tuple[str, str], List[str]]
) -> Tuple[Optional[str], List[str]]:
    """The one landing-zone service of `kind` for `provider`, or why not.

    The provider's own services first; a neutral service only where the
    provider has none of that kind. Returns (service, candidates): one
    service and its single-item list when it resolves, None and the
    candidates when there are none or several.
    """
    candidates = list(zone.get((str(provider or ""), kind), []))
    if not candidates:
        candidates = list(zone.get(("", kind), []))
    if len(candidates) == 1:
        return candidates[0], candidates
    return None, candidates


def has_landing_zone(provider: str, zone: Dict[Tuple[str, str], List[str]]) -> bool:
    """Whether the model records any landing zone on `provider` at all.

    The provider's own tagged services only. A neutral identity provider is
    the same service on every cloud, and it is not a landing zone on any of
    them: an all-Azure estate that tags its Entra ID is still waiting for an
    AWS one, and the AWS shapes should say they wait rather than fail.
    """
    wanted = "" if str(provider or "") in NEUTRAL_PROVIDERS else str(provider)
    return any(p == wanted for p, _kind in zone)


def is_kind(value: Any, components) -> bool:
    """A value in `uses` or a part's `with` that names a kind, not a service.

    Ids are upper case (`TS-AZURE-APIM`) and component types lower case
    (`api-gateway`), so the two cannot be mistaken for each other.
    """
    return isinstance(value, str) and value in components


def resolve_uses(
    wanted: Sequence[str],
    provider: str,
    bind: Dict[str, str],
    zone: Dict[Tuple[str, str], List[str]],
    components,
    where: str,
) -> List[str]:
    """`uses` with each kind replaced by the service that is that kind here:
    what the shape binds it to by hand, else the one landing-zone service of
    it on the provider. A service id passes through as written."""
    out: List[str] = []
    for item in wanted:
        if not is_kind(item, components):
            out.append(item)
            continue
        if item in bind:
            out.append(bind[item])
            continue
        found, candidates = resolve_kind(item, provider, zone)
        if found:
            out.append(found)
            continue
        if candidates:
            raise ArchetypeError(
                "%s uses `%s`, and the %s landing zone has %s; say which under `bind: {%s: ...}`"
                % (where, item, provider or "shared", " and ".join(candidates), item)
            )
        raise ArchetypeError(
            "%s uses `%s`, and no landing-zone service of that kind exists for %s; tag one "
            "`landing-zone`, or add `bind: {%s: TS-...}` to the shape"
            % (where, item, provider or "any provider", item)
        )
    return out


def landing_providers(archetypes) -> List[str]:
    """The providers shapes land on: each shape's own, neutral ones excluded.

    A landing zone is measured against these rather than against every
    provider with a tagged service: the on-prem data center is one service
    tagged `vpc`, and nothing lands there.
    """
    return sorted({
        str(a.provider) for a in archetypes
        if a.provider and str(a.provider) not in NEUTRAL_PROVIDERS
    })


class LandingZoneGap(NamedTuple):
    """A kind the parts name that one provider's landing zone cannot answer."""

    provider: str
    kind: str
    #: (module id, parameter name) for each part that asks, in module order.
    asked_by: Sequence[Tuple[str, str]]
    #: Shapes on the provider that bind the kind by hand, and so compose.
    bound_by: Sequence[str]


def landing_zone_gaps(modules, archetypes, zone) -> List[LandingZoneGap]:
    """What each landing zone cannot answer, ahead of any shape asking.

    A shape composing a part whose kind resolves to nothing is refused; this
    is the same fact one step earlier, so the onboarding that would stop on
    it is told before it starts. A parameter with a default does not ask the
    landing zone. A kind a shape binds by hand is still a gap -- the next
    shape on that provider has to bind it too -- and the shapes that do are
    named, since the bind is where the fix already is. Two tagged services
    of one kind is an ambiguity, reported elsewhere, not a gap.

    A provider with no landing zone at all has no gaps, only a wait, and
    `library.no_landing_zone` says so once per shape. Listing every kind on
    it as well told an all-Azure estate twenty-two times that AWS and Google
    Cloud lacked things it never meant to have.
    """
    shapes = list(archetypes)
    asked: Dict[str, List[Tuple[str, str]]] = {}
    for module in sorted(modules.values(), key=lambda m: m.module_id):
        for param in module.parameters:
            if param.component and param.default is None:
                asked.setdefault(param.component, []).append((module.module_id, param.name))
    gaps: List[LandingZoneGap] = []
    for provider in landing_providers(shapes):
        if not has_landing_zone(provider, zone):
            continue
        for kind in sorted(asked):
            found, candidates = resolve_kind(kind, provider, zone)
            if found or candidates:
                continue
            bound_by: List[str] = []
            for shape in shapes:
                if str(shape.provider) != provider:
                    continue
                try:
                    binds = effective_bind(shape)
                except ArchetypeError:
                    binds = dict(shape.bind)
                if kind in binds:
                    bound_by.append(shape.archetype_id)
            gaps.append(LandingZoneGap(provider, kind, tuple(asked[kind]), tuple(sorted(bound_by))))
    return gaps


#: Keys on a block entry that steer the expansion rather than land on the
#: entities it creates.
_BLOCK_ENTRY_KEYS = ("block", "as", "id", "name", "provider", "bind")

#: Keys on a template that are shorthand for relations, not fields: what a
#: system runs on, and which controls and policies govern a system or a
#: data asset. The governance links arrive with the part that way, rather
#: than being a second thing to remember after the diagram is drawn.
_TEMPLATE_SHORTHANDS = ("runs_on", "uses", "controls", "policies")

_GOVERNANCE_ROWS = {
    ("systems", "controls"): ("system_governed_by_control", "system_id", "control_id"),
    ("systems", "policies"): ("system_subject_to_policy", "system_id", "policy_id"),
    ("data_assets", "controls"): ("data_governed_by_control", "data_asset_id", "control_id"),
    ("data_assets", "policies"): ("data_subject_to_policy", "data_asset_id", "policy_id"),
}


class ArchetypeError(ValueError):
    """An archetype or one of its instances is malformed."""


class Parameter(NamedTuple):
    name: str
    required: bool = False
    default: Any = None
    description: str = ""
    #: Answered by the estate: the value under `answers` in `model.yaml` of
    #: the same name, ahead of the default, when the product does not say.
    #: For the things a shape needs from the estate around it -- who stewards
    #: the data, where it lands -- which it used to default to the sample's.
    estate: bool = False


class Slot(NamedTuple):
    """One place a shape varies: a need, and the parts that can fill it.

    Two vendor shapes existed because one reached the vendor over a private
    path and the other over the public internet, and the composition had no
    way to say "here, choose." A slot is that sentence. The shape names the
    default; an instance chooses under `choose`; a part is either always in
    the shape or an option in one of its slots, never both.
    """

    name: str
    description: str
    options: Sequence[str]
    default: Optional[str] = None
    #: Whether an instance may leave it empty by choosing `none`.
    optional: bool = False
    #: What the shape answers for an option from its own parameters, keyed
    #: by option: ``{"webhook-inbound": {"consumer_system": "{upstream_system}"}}``.
    #: A listed part is answered under `modules`; a part that is a choice has
    #: nowhere else to be answered, and a product on the default should not
    #: have to say what the shape already knows.
    answers: Dict[str, Dict[str, Any]] = {}


class Archetype(NamedTuple):
    archetype_id: str
    title: str
    description: str
    version: str
    applies_to: str
    parameters: Sequence[Parameter]
    defaults: Dict[str, Any]
    provides: Dict[str, List[dict]]
    relations: Dict[str, List[dict]]
    source_file: Optional[Path] = None
    #: Patterns from `27_PATTERNS/` that every instance of this shape applies.
    #: The product carries them, so adoption can be read off the model.
    patterns: Sequence[str] = ()
    #: The cloud every block resolves against, unless a block entry says.
    provider: str = ""
    #: What every entity the shape creates has in common, by entity type,
    #: with `all` for the fields shared by every type. A template then says
    #: only what makes it different, which is what keeps one reviewable.
    entity_defaults: Dict[str, Dict[str, Any]] = {}
    #: Building blocks the shape is built on. Each entry names a block and,
    #: under `bind`, the components the landing zone already provides.
    blocks: Sequence[dict] = ()
    #: Whether every system the shape provides is included in the product.
    #: On by default: an archetype applied to a product describes its parts.
    include_systems: bool = True
    #: Modules the shape is composed from, in order. Each entry names a
    #: module, optionally an alias and the parameter values it is given.
    modules: Sequence[dict] = ()
    #: Where the shape varies. Resolved before the instance's own additions,
    #: so an added part can `require` whatever was chosen.
    slots: Sequence[Slot] = ()
    #: The landing zone, by kind: component type id to the shared service that
    #: is that kind here. A part parameter with a `component` resolves through
    #: this, so the same part binds Secrets Manager on the AWS shape and Key
    #: Vault on the Azure one without either being written into the part. The
    #: binds on the shape's blocks count too; this map wins where both speak.
    bind: Dict[str, str] = {}
    #: The library it was read from, "" for the shipped one, and the file it
    #: stands in for when it says `replaces` (`library.load_layer`).
    library: str = ""
    replaced: str = ""


def _apply_filters(value: str, filters: str) -> str:
    for name in [f for f in filters.split("|") if f]:
        if name == "upper":
            value = value.upper()
        elif name == "lower":
            value = value.lower()
        elif name == "slug":
            value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
        elif name == "title":
            value = value.title()
        elif name == "stem":
            # An id without its type prefix: SYS-CRM -> CRM. What a spoke's
            # interface id is built from.
            value = value.split("-", 1)[1] if "-" in value else value
        else:
            raise ArchetypeError("unknown template filter %r" % name)
    return value


def substitute(value: Any, bindings: Dict[str, Any]) -> Any:
    """Replace `{param}` and `{param|filter}` tokens throughout a structure."""
    if isinstance(value, str):
        def replace(match: "re.Match[str]") -> str:
            key = match.group(1)
            if key not in bindings:
                raise ArchetypeError("no value bound for template token {%s}" % key)
            bound = bindings[key]
            return _apply_filters("" if bound is None else str(bound), match.group(2))

        # A string that is exactly one token keeps the bound value's type.
        whole = _TOKEN.fullmatch(value)
        if whole is not None and not whole.group(2):
            key = whole.group(1)
            if key not in bindings:
                raise ArchetypeError("no value bound for template token {%s}" % key)
            return bindings[key]
        return _TOKEN.sub(replace, value)
    if isinstance(value, list):
        return [substitute(item, bindings) for item in value]
    if isinstance(value, dict):
        return {k: substitute(v, bindings) for k, v in value.items()}
    return value


def _filled(value: Any, bindings: Dict[str, Any], where: str) -> Any:
    """`substitute`, with the part and the instance named in the failure.

    Worth the wrapper since `each` began taking mappings. A list of four roles
    with the third one missing its `interaction` is an easy thing to write, and
    "no value bound for template token {interaction}" on its own does not say
    which part, which product, or which of the four.
    """
    try:
        return substitute(value, bindings)
    except ArchetypeError as exc:
        raise ArchetypeError("%s: %s" % (where, exc))


def _listed(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [v.strip() for v in value.replace(";", ",").split(",") if v.strip()]
    return [str(v).strip() for v in value if str(v).strip()]


def unroll(template: dict, bindings: Dict[str, Any], where: str = "") -> List[dict]:
    """One template per item of a list, or the template itself.

    A template with `each` is a hub-and-spoke shape: the same interface, or
    relation, once for every spoke. `each` names a list-valued parameter as a
    token (`"{spokes}"`) or is a list. Each copy sees `item`, the list entry
    (a string, or the keys of a mapping entry), and `index`, from 1. Nothing
    else about the template changes, so `{item|upper}` and `{item|slug}` do
    what they do everywhere.
    """
    if "each" not in template:
        return [template]
    spec = template["each"]
    items = substitute(spec, bindings) if isinstance(spec, str) else spec
    if items is None or items == "":
        items = []
    if isinstance(items, str):
        items = _listed(items)
    if not isinstance(items, list):
        raise ArchetypeError("%s: `each` needs a list, not %r" % (where or "template", items))
    out: List[dict] = []
    for index, item in enumerate(items, start=1):
        local = dict(bindings)
        local["index"] = index
        if isinstance(item, dict):
            local.update(item)
            local["item"] = item.get("id") or item.get("system_id") or item.get("name") or str(index)
        else:
            local["item"] = item
        copy = {k: v for k, v in template.items() if k != "each"}
        out.append(_filled(copy, local, where or "template"))
    return out


def parse_archetype(data: dict, source: Optional[Path] = None) -> Archetype:
    if not isinstance(data, dict) or "archetype_id" not in data:
        raise ArchetypeError("%s: missing archetype_id" % (source or "<archetype>"))
    where = source or data["archetype_id"]
    params: List[Parameter] = []
    for raw in data.get("parameters") or []:
        if isinstance(raw, str):
            params.append(Parameter(name=raw, required=True))
            continue
        if not isinstance(raw, dict) or "name" not in raw:
            raise ArchetypeError("%s: each parameter needs a name" % where)
        params.append(
            Parameter(
                name=raw["name"],
                required=bool(raw.get("required", "default" not in raw)),
                default=raw.get("default"),
                description=raw.get("description", "") or "",
                estate=bool(raw.get("estate", False)),
            )
        )
    provides = data.get("provides") or {}
    for entity_type in provides:
        if entity_type not in ENTITY_TYPES:
            raise ArchetypeError(
                "%s: provides unknown entity type %r" % (where, entity_type)
            )
    entity_defaults = data.get("entity_defaults") or {}
    if not isinstance(entity_defaults, dict):
        raise ArchetypeError("%s: entity_defaults must be a mapping" % where)
    for key, value in entity_defaults.items():
        if key != "all" and key not in ENTITY_TYPES:
            raise ArchetypeError(
                "%s: entity_defaults names unknown entity type %r" % (where, key)
            )
        if not isinstance(value, dict):
            raise ArchetypeError("%s: entity_defaults.%s must be a mapping" % (where, key))
    blocks: List[dict] = []
    for raw in data.get("blocks") or []:
        if isinstance(raw, str):
            raw = {"block": raw}
        if not isinstance(raw, dict) or not raw.get("block"):
            raise ArchetypeError("%s: every entry under `blocks` names a block" % where)
        if raw.get("bind") is not None and not isinstance(raw["bind"], dict):
            raise ArchetypeError(
                "%s: block %s: `bind` maps a component to a tech service id, or to `%s`"
                % (where, raw["block"], LANDING_ZONE_TAG)
            )
        blocks.append(dict(raw))
    modules = _module_entries(data.get("modules"), where)
    slots: List[Slot] = []
    always = {str(e.get("as") or e.get("module")) for e in modules}
    for raw in data.get("slots") or []:
        if not isinstance(raw, dict) or not raw.get("name"):
            raise ArchetypeError("%s: every slot needs a name" % where)
        name = str(raw["name"])
        if any(s.name == name for s in slots):
            raise ArchetypeError("%s: slot %s is declared twice" % (where, name))
        options = _listed(raw.get("options"))
        if not options:
            raise ArchetypeError("%s: slot %s offers no options" % (where, name))
        for option in options:
            if option in always:
                raise ArchetypeError(
                    "%s: slot %s offers %s, which the shape already composes under "
                    "`modules`; a part is either always there or a choice, not both"
                    % (where, name, option)
                )
        default = raw.get("default")
        default = None if default in (None, "") else str(default)
        if default is not None and default not in options:
            raise ArchetypeError(
                "%s: slot %s defaults to %r, which is not one of its options (%s)"
                % (where, name, default, ", ".join(options))
            )
        given = raw.get("with") or {}
        if not isinstance(given, dict) or not all(isinstance(v, dict) for v in given.values()):
            raise ArchetypeError(
                "%s: slot %s: `with` maps an option to the parameters the shape answers for it"
                % (where, name)
            )
        for option in given:
            if str(option) not in options:
                raise ArchetypeError(
                    "%s: slot %s answers for %r, which is not one of its options (%s)"
                    % (where, name, option, ", ".join(options))
                )
        slots.append(Slot(
            name=name,
            description=str(raw.get("description") or ""),
            options=options,
            default=default,
            optional=bool(raw.get("optional", False)),
            answers={str(k): dict(v) for k, v in given.items()},
        ))
    bind = data.get("bind") or {}
    if not isinstance(bind, dict) or not all(
        isinstance(k, str) and isinstance(v, str) and v for k, v in bind.items()
    ):
        raise ArchetypeError(
            "%s: `bind` maps a component type to the shared service that is that kind here"
            % where
        )
    return Archetype(
        archetype_id=data["archetype_id"],
        title=data.get("title") or data["archetype_id"],
        description=data.get("description", "") or "",
        version=str(data.get("version", "1.0.0")),
        applies_to=data.get("applies_to", "products"),
        parameters=params,
        defaults=data.get("defaults") or {},
        provides={k: list(v or []) for k, v in provides.items()},
        relations={k: list(v or []) for k, v in (data.get("relations") or {}).items()},
        source_file=source,
        patterns=_listed(data.get("patterns")),
        provider=str(data.get("provider") or ""),
        entity_defaults={k: dict(v) for k, v in entity_defaults.items()},
        blocks=blocks,
        include_systems=bool(data.get("include_systems", True)),
        modules=modules,
        slots=slots,
        bind={str(k): str(v) for k, v in bind.items()},
    )


def _module_entries(raw_entries, where) -> List[dict]:
    """Normalize a `modules` list. The rule lives with the modules, since a
    kit's members are written the same way; here it only changes the error."""
    try:
        return module_entries(raw_entries, where)
    except ModuleError as exc:
        raise ArchetypeError(str(exc))


#: The shapes' folder, in the shipped library and in each of the
#: organization's.
ARCHETYPES_DIR = "20_ARCHETYPES"


def load_archetypes(root: Path) -> Dict[str, Archetype]:
    """Every shape, the organization's after the shipped ones. Takes the
    repository root, as every other layer's loader does: given the folder,
    it read one library and could not know there was another."""
    if Path(root).name == ARCHETYPES_DIR:
        # The old call, which would now look for 20_ARCHETYPES/20_ARCHETYPES,
        # find nothing and report no shapes at all.
        raise ArchetypeError(
            "load_archetypes takes the repository root, not its %s folder" % ARCHETYPES_DIR
        )
    return load_layer(
        root, ARCHETYPES_DIR, parse_archetype, lambda a: str(a.archetype_id), "archetype",
        ArchetypeError,
    )


class Expansion(NamedTuple):
    instance: dict
    entities: Dict[str, List[dict]]
    relations: Dict[str, List[dict]]
    #: (entity_id, excluded_id) pairs dropped because they pointed at an
    #: excluded entity. Surfaced by the loader so exclusions stay visible.
    dropped_dependents: List[Tuple[str, str]] = []
    #: Block alias to component to the tech service that stands for it, bound
    #: or created. The preview shows it; nothing else needs it.
    block_ids: Dict[str, Dict[str, str]] = {}
    #: The module aliases that were applied, in order, after `without`.
    modules_applied: List[str] = []
    #: Slot name to the module that filled it, or "" for an optional slot
    #: the instance left empty.
    choices: Dict[str, str] = {}


def _expand_blocks(
    archetype: Archetype,
    bindings: Dict[str, Any],
    entity_defaults: Dict[str, Dict[str, Any]],
    library: Optional[Library],
    instance_id: str,
) -> Tuple[Dict[str, List[dict]], List[dict], Dict[str, Dict[str, str]]]:
    """Every block the shape is built on, resolved for one instance.

    A bound component creates nothing: the landing zone provides it, and the
    id under `bind` is what the systems run on -- or, where the shape says
    `landing-zone`, the one landing-zone service of that kind on the
    provider. Everything else is created for this instance, named from the
    block's `id` (the slug by default) and resolved to the provider's product
    where the component knows one.
    """
    if not archetype.blocks:
        return {}, [], {}
    if library is None:
        raise ArchetypeError(
            "archetype %s is built on blocks, and expansion was given no library"
            % archetype.archetype_id
        )
    components, blocks = library[0], library[1]
    zone: Dict[Tuple[str, str], List[str]] = library[3] if len(library) > 3 else {}
    entities: Dict[str, List[dict]] = {}
    connects: List[dict] = []
    ids: Dict[str, Dict[str, str]] = {}
    created_ids: Dict[str, str] = {}

    for raw in archetype.blocks:
        entry = substitute(dict(raw), bindings)
        block_id = str(entry["block"])
        block = blocks.get(block_id)
        if block is None:
            raise ArchetypeError(
                "archetype %s is built on unknown building block %r"
                % (archetype.archetype_id, block_id)
            )
        alias = str(entry.get("as") or block_id)
        if alias in ids:
            raise ArchetypeError(
                "archetype %s uses block %s twice; give the second an `as`"
                % (archetype.archetype_id, block_id)
            )
        base = str(entry.get("id") or bindings.get("slug") or instance_id)
        label = str(entry.get("name") or bindings.get("name") or instance_id)
        provider = str(entry.get("provider") or archetype.provider or "")
        bound = {str(k): str(v) for k, v in (entry.get("bind") or {}).items()}
        provided_names = {p.component for p in block.provides}
        for component_name in bound:
            if component_name not in provided_names:
                raise ArchetypeError(
                    "archetype %s binds %r, which block %s does not provide"
                    % (archetype.archetype_id, component_name, block_id)
                )
            if bound[component_name] != LANDING_ZONE_TAG:
                continue
            found, candidates = resolve_kind(component_name, provider, zone)
            if not found:
                raise ArchetypeError(
                    "%s: archetype %s binds %s on block %s to the landing zone, and the %s "
                    "landing zone has %s; %s"
                    % (instance_id, archetype.archetype_id, component_name, block_id,
                       provider or "shared",
                       " and ".join(candidates) if candidates else "none of that kind",
                       "say which under `bind`" if candidates
                       else "tag one `landing-zone` with `component_type: %s`" % component_name)
                )
            bound[component_name] = found
        values = {k: v for k, v in entry.items() if k not in _BLOCK_ENTRY_KEYS}

        resolved: Dict[str, str] = {}
        for provided in block.provides:
            component = components[provided.component]
            if provided.component in bound:
                resolved[provided.component] = bound[provided.component]
                continue
            type_name = component.applies_to
            pk = ENTITY_TYPES[type_name].pk
            prefix = "TS" if type_name == "tech_services" else "SYS"
            this_id = block_entity_id(prefix, base, component.component_type_id)
            if this_id in created_ids:
                raise ArchetypeError(
                    "archetype %s would create %s twice, from blocks %s and %s; "
                    "bind one of them to a shared service"
                    % (archetype.archetype_id, this_id, created_ids[this_id], block_id)
                )
            created_ids[this_id] = block_id
            # Tightest last: the component knows what it is, the shape knows
            # where it is, the block knows what zone it sits in, and the entry
            # knows about this one appearance.
            record: Dict[str, Any] = dict(component.defaults)
            record.update(entity_defaults.get("all", {}))
            record.update(entity_defaults.get(type_name, {}))
            record.update(block.defaults)
            record.update(provided.values)
            record.update(values)
            record[pk] = this_id
            record.setdefault("name", "%s %s" % (label, component.name))
            record.setdefault("description", component.description)
            record["component_type"] = component.component_type_id
            if type_name == "tech_services":
                record.setdefault("service_category", component.category)
            record.setdefault("status", "Planned")
            if provider:
                record.setdefault("provider", provider)
                product = component.providers.get(provider)
                if product:
                    record.setdefault("product", product)
            entities.setdefault(type_name, []).append(record)
            resolved[provided.component] = this_id
        ids[alias] = resolved

        for source, target in block.relations:
            # A connection between two shared services is a fact about the
            # landing zone, not about this product, and repeating it once per
            # instance would only produce duplicate-row warnings.
            if source in bound and target in bound:
                continue
            connects.append({
                "from_tech_service_id": resolved[source],
                "to_tech_service_id": resolved[target],
            })
    return entities, connects, ids


def _resolve_runs_on(
    archetype: Archetype, system_id: str, wanted: List[str], block_ids: Dict[str, Dict[str, str]]
) -> List[str]:
    """`runs_on` names a block, for every part of it, or `block.component`."""
    out: List[str] = []
    for item in wanted:
        alias, _, component = str(item).partition(".")
        if alias not in block_ids:
            raise ArchetypeError(
                "%s in archetype %s runs on %r, which is not a block the shape is built on"
                % (system_id, archetype.archetype_id, item)
            )
        if component:
            if component not in block_ids[alias]:
                raise ArchetypeError(
                    "%s in archetype %s runs on %r, but block %s has no component %r"
                    % (system_id, archetype.archetype_id, item, alias, component)
                )
            out.append(block_ids[alias][component])
        else:
            out.extend(block_ids[alias].values())
    return out


def _compose_modules(
    archetype: Archetype,
    instance: dict,
    bindings: Dict[str, Any],
    library: Optional[Library],
    instance_id: str,
) -> Tuple[
    List[Tuple[str, dict]], Dict[str, List[dict]], List[str], List[str], Set[str], Dict[str, str]
]:
    """Every module the product ends up with, expanded against its bindings.

    The order is the shape's parts, then what its slots resolve to, then the
    instance's additions, so a chosen or added part can `require` anything the
    shape already has. Entries are merged by alias first -- an instance entry
    with the same alias as a shape's merges its `with` over it, and that holds
    for a kit too, which is how a product re-binds a kit's vault -- and only
    then is a kit flattened to its members in place, under their own aliases.
    A kit is a name for a group, not a namespace, so `requires:
    [vendor-tenancy]` keeps working whether the tenancy came alone or inside
    `vendor-baseline`.

    `without` drops aliases: a kit's alias drops every member under it, and a
    part that fills a slot cannot be dropped at all, because a slot is changed
    by choosing, not by removing what was chosen. Dropping what another kept
    module requires is refused, because the dangling reference that would
    leave is worse than the refusal.

    Every part's `needs` is checked against what it can see before a single
    template is read, so a shape that binds no `vendor` is refused with the
    part's name rather than with a token from inside a template.
    """
    if library is None or len(library) < 3:
        if archetype.modules or archetype.slots or instance.get("modules"):
            raise ArchetypeError(
                "archetype %s is composed from modules, and expansion was given no library"
                % archetype.archetype_id
            )
        return [], {}, [], [], set(), {}
    modules: Dict[str, Module] = library[2]
    bind = effective_bind(archetype)
    zone: Dict[Tuple[str, str], List[str]] = library[3] if len(library) > 3 else {}
    answers: Dict[str, Any] = library[4] if len(library) > 4 else {}

    choices = _choose(archetype, instance, instance_id)
    slot_of = {module_id: name for name, module_id in choices.items() if module_id}
    # A chosen part arrives with what its slot answers for it; the instance's
    # own entry for the part is merged after, so its answer wins.
    answered = {option: given for slot in archetype.slots for option, given in slot.answers.items()}
    chosen_entries: List[dict] = []
    for module_id in choices.values():
        if not module_id:
            continue
        entry: dict = {"module": module_id}
        if answered.get(module_id):
            entry["with"] = dict(answered[module_id])
        chosen_entries.append(entry)
    listed: List[dict] = (
        list(archetype.modules) + chosen_entries + _module_entries(instance.get("modules"), instance_id)
    )

    # 1. Merge by alias, kits still folded.
    raw_entries: Dict[str, dict] = {}
    raw_order: List[str] = []
    for raw in listed:
        alias = str(raw.get("as") or raw["module"])
        if alias in raw_entries:
            merged = dict(raw_entries[alias])
            merged_with = dict(merged.get("with") or {})
            merged_with.update(raw.get("with") or {})
            merged["with"] = merged_with
            raw_entries[alias] = merged
        else:
            raw_entries[alias] = dict(raw)
            raw_order.append(alias)

    # 2. Flatten kits, in order, remembering which kit each leaf sits under.
    entries: Dict[str, dict] = {}
    order: List[str] = []
    members_under: Dict[str, Set[str]] = {}
    brought_by: Dict[str, str] = {}

    def place(raw: dict, chain: Tuple[str, ...]) -> None:
        alias = str(raw.get("as") or raw["module"])
        if alias in entries:
            # A direct entry naming a member a kit already brought re-binds
            # it: that is how a product gives the baseline's vault another
            # value without restating the kit. Two kits bringing the same
            # member, or a kit bringing what the shape listed on its own
            # first, is an ambiguity rather than a re-binding, and refused.
            if not chain and alias in brought_by:
                merged = dict(entries[alias])
                merged_with = dict(merged.get("with") or {})
                merged_with.update(raw.get("with") or {})
                merged["with"] = merged_with
                entries[alias] = merged
                return
            raise ArchetypeError(
                "%s: archetype %s composes %s twice%s; give one of them an `as`"
                % (instance_id, archetype.archetype_id, alias,
                   " (once through kit %s)" % chain[-1] if chain else "")
            )
        entries[alias] = raw
        order.append(alias)
        if chain:
            brought_by[alias] = chain[-1]
        for kit in chain:
            members_under[kit].add(alias)

    def flatten(raw: dict, outer: Dict[str, Any], chain: Tuple[str, ...]) -> None:
        module = modules.get(str(raw["module"]))
        if module is None:
            raise ArchetypeError(
                "%s: archetype %s is composed from unknown module %r"
                % (instance_id, archetype.archetype_id, raw["module"])
            )
        if not module.is_kit:
            place(raw, chain)
            return
        alias = str(raw.get("as") or raw["module"])
        if alias in members_under or alias in entries:
            raise ArchetypeError(
                "%s: archetype %s composes kit %s twice; give the second an `as`"
                % (instance_id, archetype.archetype_id, alias)
            )
        members_under[alias] = set()
        local = _bind_part(
            module, raw, outer, instance_id, alias, bind, zone, archetype.provider, answers
        )
        for member in module.modules:
            resolved = dict(member)
            if member.get("with"):
                resolved["with"] = substitute(dict(member["with"]), local)
            flatten(resolved, local, chain + (alias,))

    for alias in raw_order:
        flatten(raw_entries[alias], bindings, ())
    if not order:
        return [], {}, [], [], set(), choices

    without = {str(x) for x in _listed(instance.get("without"))}
    for name in list(without):
        if name in members_under:
            without.discard(name)
            without |= members_under[name]
    for name in sorted(without):
        if name in slot_of:
            slot = next(s for s in archetype.slots if s.name == slot_of[name])
            raise ArchetypeError(
                "%s: %s fills slot %s of archetype %s and is not dropped with `without`; "
                "choose another option (one of %s%s) under `choose`"
                % (instance_id, name, slot.name, archetype.archetype_id,
                   ", ".join(o for o in slot.options if o != name),
                   ", or none" if slot.optional else "")
            )
    unknown = sorted(without - set(order))
    if unknown:
        raise ArchetypeError(
            "%s: without names %s, which archetype %s is not composed from"
            % (instance_id, ", ".join(unknown), archetype.archetype_id)
        )
    kept = [alias for alias in order if alias not in without]
    for alias in sorted(without):
        if not modules[str(entries[alias]["module"])].optional:
            raise ArchetypeError(
                "%s: %s is not optional in archetype %s and cannot be dropped"
                % (instance_id, alias, archetype.archetype_id)
            )
    for alias in kept:
        module = modules[str(entries[alias]["module"])]
        for needed in module.requires:
            if needed not in kept:
                raise ArchetypeError(
                    "%s: module %s requires %s, which is not part of this product%s"
                    % (instance_id, alias, needed,
                       " (dropped by `without`)" if needed in without else "")
                )

    # What a dropped module would have produced. Those ids are treated like
    # exclusions, so a relation the shape wrote against a part that is not
    # there goes with it, reported, instead of dangling.
    dropped_ids: Set[str] = set()
    for alias in without:
        module = modules[str(entries[alias]["module"])]
        local = dict(bindings)
        local["alias"] = alias
        for param in module.parameters:
            local.setdefault(param.name, param.default)
        local.update(entries[alias].get("with") or {})
        for type_name, listed_templates in module.provides.items():
            pk = ENTITY_TYPES[type_name].pk
            for template in listed_templates:
                try:
                    dropped_ids.add(str(substitute(template.get(pk), local)))
                except ArchetypeError:
                    continue

    templates: List[Tuple[str, dict]] = []
    relations: Dict[str, List[dict]] = {}
    patterns: List[str] = []
    for alias in kept:
        entry = entries[alias]
        module = modules[str(entry["module"])]
        local = _bind_part(
            module, entry, bindings, instance_id, alias, bind, zone, archetype.provider, answers
        )
        where = "%s: module %s" % (instance_id, alias)
        for type_name, listed_templates in module.provides.items():
            for template in listed_templates:
                for record in unroll(dict(template), local, where):
                    record = _filled(record, local, where)
                    record["module"] = alias
                    templates.append((type_name, record))
        for relation_name, rows in module.relations.items():
            for row in rows:
                for unrolled in unroll(dict(row), local, where):
                    relations.setdefault(relation_name, []).append(
                        _filled(unrolled, local, where)
                    )
        for pattern in module.patterns:
            if pattern not in patterns:
                patterns.append(pattern)
    return templates, relations, patterns, kept, dropped_ids, choices


def effective_bind(archetype: Archetype) -> Dict[str, str]:
    """The landing zone as the shape describes it, by kind.

    A component bound on one of the shape's blocks is the same fact as a kind
    bound on the shape, so both count and neither has to be repeated. Two
    blocks binding the same kind to different services is a contradiction
    about the landing zone and is refused; the shape's own `bind` wins over a
    block's, because it was written to.

    Only what is bound by hand: a kind bound to `landing-zone` is left out,
    since it is whatever the landing zone answers, and that is the next
    thing a part's parameter asks anyway (`zone_binds` lists them).
    """
    out: Dict[str, str] = {}
    from_block: Dict[str, str] = {}
    for raw in archetype.blocks:
        block_id = str(raw.get("block"))
        for kind, service in (raw.get("bind") or {}).items():
            kind, service = str(kind), str(service)
            if kind in out and out[kind] != service and kind not in archetype.bind:
                raise ArchetypeError(
                    "archetype %s binds %s to %s on block %s and to %s on block %s; "
                    "say which under `bind`"
                    % (archetype.archetype_id, kind, out[kind], from_block[kind],
                       service, block_id)
                )
            out[kind] = service
            from_block[kind] = block_id
    out.update(archetype.bind)
    return {kind: service for kind, service in out.items() if service != LANDING_ZONE_TAG}


def zone_binds(archetype: Archetype) -> List[Tuple[str, str]]:
    """(kind, block) for each component a block binds to `landing-zone`, in
    the order written, unless the shape binds the kind by hand as well."""
    by_hand = effective_bind(archetype)
    out: List[Tuple[str, str]] = []
    for raw in archetype.blocks:
        for kind, service in (raw.get("bind") or {}).items():
            if str(service) == LANDING_ZONE_TAG and str(kind) not in by_hand:
                out.append((str(kind), str(raw.get("as") or raw.get("block"))))
    return out


def _bind_part(
    module: Module,
    entry: dict,
    outer: Dict[str, Any],
    instance_id: str,
    alias: str,
    bind: Optional[Dict[str, str]] = None,
    zone: Optional[Dict[Tuple[str, str], List[str]]] = None,
    provider: str = "",
    answers: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """The bindings one part sees: the shape's, its own parameters, and the
    `with` it was composed with -- checked against what it says it needs.

    A parameter resolves in this order: what the entry's `with` says, then a
    shape parameter of the same name, then -- for a parameter that names a
    kind -- what the shape binds that kind to, then the one landing-zone
    service of that kind on the shape's provider, then -- for one marked
    `estate` -- the estate's answer of that name, then the part's own
    default. A kind that resolves to nothing, or to more than one thing, is
    refused by kind with the line to add, which is the sentence the shape
    author needs; an estate question nobody answered is refused the same way.
    """
    bind = bind or {}
    zone = zone or {}
    answers = answers or {}
    local = dict(outer)
    local["alias"] = alias
    supplied = substitute(dict(entry.get("with") or {}), outer)
    for param in module.parameters:
        if param.name in supplied:
            local[param.name] = supplied.pop(param.name)
        elif param.name in local:
            # The shape binds it already, under the same name.
            continue
        elif param.component and param.component in bind:
            local[param.name] = bind[param.component]
        elif param.component and resolve_kind(param.component, provider, zone)[0]:
            local[param.name] = resolve_kind(param.component, provider, zone)[0]
        elif param.component and param.default is None:
            _found, candidates = resolve_kind(param.component, provider, zone)
            if len(candidates) > 1:
                raise ArchetypeError(
                    "%s: module %s: %r is of kind `%s`, and the %s landing zone has %s; "
                    "say which under `bind: {%s: ...}`"
                    % (instance_id, alias, param.name, param.component,
                       provider or "shared", " and ".join(candidates), param.component)
                )
            raise ArchetypeError(
                "%s: module %s: %r is of kind `%s`, and no landing-zone service of that kind "
                "exists for %s; tag one `landing-zone`, add `bind: {%s: TS-...}` to the shape, "
                "or `with: {%s: TS-...}` on the instance"
                % (instance_id, alias, param.name, param.component, provider or "any provider",
                   param.component, param.name)
            )
        elif param.estate and param.name in answers:
            local[param.name] = answers[param.name]
        elif param.required and param.estate:
            raise ArchetypeError(
                "%s: module %s asks the estate for %r%s; answer it under `answers` in "
                "model.yaml, or `with: {%s: ...}` on the product"
                % (instance_id, alias, param.name,
                   " (%s)" % param.description.strip().rstrip(".") if param.description else "",
                   param.name)
            )
        elif param.required:
            raise ArchetypeError(
                "%s: module %s requires parameter %r" % (instance_id, alias, param.name)
            )
        else:
            local[param.name] = substitute(param.default, outer)
    if supplied:
        raise ArchetypeError(
            "%s: module %s does not declare parameter(s) %s"
            % (instance_id, alias, ", ".join(sorted(supplied)))
        )
    missing = [name for name in module.needs if name not in local]
    if missing:
        raise ArchetypeError(
            "%s: module %s needs %s from the shape, and nothing binds %s"
            % (instance_id, alias, ", ".join(module.needs),
               " or ".join("{%s}" % m for m in missing))
        )
    return local


def _choose(archetype: Archetype, instance: dict, instance_id: str) -> Dict[str, str]:
    """Resolve every slot to a module id, or to "" for an optional slot left
    empty. What the instance says under `choose` wins; the slot's default
    stands otherwise; a required slot with neither is refused."""
    chosen = instance.get("choose") or {}
    if not isinstance(chosen, dict):
        raise ArchetypeError("%s: `choose` maps a slot name to one of its options" % instance_id)
    slots = {slot.name: slot for slot in archetype.slots}
    unknown = sorted(set(chosen) - set(slots))
    if unknown:
        raise ArchetypeError(
            "%s: choose names %s, which archetype %s has no slot for%s"
            % (instance_id, ", ".join(unknown), archetype.archetype_id,
               " (slots: %s)" % ", ".join(slots) if slots else "")
        )
    out: Dict[str, str] = {}
    for slot in archetype.slots:
        value = chosen.get(slot.name, slot.default)
        if value in (None, "", "none"):
            if not slot.optional:
                raise ArchetypeError(
                    "%s: archetype %s asks for a choice of %s (one of %s)"
                    % (instance_id, archetype.archetype_id, slot.name, ", ".join(slot.options))
                )
            out[slot.name] = ""
            continue
        value = str(value)
        if value not in slot.options:
            raise ArchetypeError(
                "%s: %r is not an option for slot %s of archetype %s (one of %s%s)"
                % (instance_id, value, slot.name, archetype.archetype_id,
                   ", ".join(slot.options), ", or none" if slot.optional else "")
            )
        out[slot.name] = value
    return out


def expand(
    instance: dict,
    archetype: Archetype,
    instance_type: str,
    library: Optional[Library] = None,
) -> Expansion:
    """Apply an archetype to one instance record."""
    entity_type = ENTITY_TYPES[instance_type]
    instance_id = instance.get(entity_type.pk)
    if not instance_id:
        raise ArchetypeError("archetype instance is missing %s" % entity_type.pk)

    supplied = dict(instance.get("parameters") or {})
    answers: Dict[str, Any] = library[4] if library is not None and len(library) > 4 else {}
    bindings: Dict[str, Any] = {}
    for param in archetype.parameters:
        if param.name in supplied:
            bindings[param.name] = supplied.pop(param.name)
        elif param.estate and param.name in answers:
            bindings[param.name] = answers[param.name]
        elif param.required and param.estate:
            raise ArchetypeError(
                "%s: archetype %s asks the estate for %r%s; answer it under `answers` in "
                "model.yaml, or under `parameters` on the product"
                % (instance_id, archetype.archetype_id, param.name,
                   " (%s)" % param.description.strip().rstrip(".") if param.description else "")
            )
        elif param.required:
            raise ArchetypeError(
                "%s: archetype %s requires parameter %r"
                % (instance_id, archetype.archetype_id, param.name)
            )
        else:
            bindings[param.name] = param.default
    if supplied:
        raise ArchetypeError(
            "%s: archetype %s does not declare parameter(s) %s"
            % (instance_id, archetype.archetype_id, ", ".join(sorted(supplied)))
        )
    bindings.setdefault("instance_id", instance_id)
    bindings[entity_type.pk] = instance_id
    bindings.setdefault("name", instance.get("name", instance_id))
    # The instance's own status, so a shape can say `status: "{status}"` under
    # `entity_defaults` and a planned product gets planned parts. The two
    # vendor shapes hardcoded Planned and Active respectively, and the first
    # planned product on the second one came out with four live systems.
    bindings.setdefault("status", instance.get("status"))

    # `ids` maps what the shape makes to what the estate already calls it;
    # overrides and exclusions may be written against the kept names.
    renames = _renames(instance, str(instance_id))
    estate_name = {new: old for old, new in renames.items()}
    overrides = {estate_name.get(str(k), str(k)): v for k, v in (instance.get("overrides") or {}).items()}
    excluded = {estate_name.get(str(x), str(x)) for x in (instance.get("exclude") or [])}
    # Tracked separately: `excluded` must stay intact for the whole expansion so
    # that interfaces and relations pointing at a dropped entity are dropped too.
    unused_excludes = set(excluded)
    seen_ids: set = set()

    resolved_instance = dict(archetype.defaults)
    resolved_instance.update({k: v for k, v in instance.items() if k not in _INSTANCE_KEYS})
    resolved_instance = substitute(resolved_instance, bindings)
    resolved_instance["archetype"] = archetype.archetype_id

    # The patterns a product applies: the archetype's first, then whatever
    # the instance adds, each once. Adoption is read off this field, so it is
    # settled here rather than left for a reader to combine.
    entity_defaults = substitute(archetype.entity_defaults, bindings)
    block_entities, block_connections, block_ids = _expand_blocks(
        archetype, bindings, entity_defaults, library, str(instance_id)
    )
    module_templates, module_relations, module_patterns, modules_applied, dropped_ids, choices = (
        _compose_modules(archetype, instance, bindings, library, str(instance_id))
    )
    # A dropped part cascades like an exclusion, without needing to be named
    # in `exclude` as well.
    excluded |= dropped_ids

    applied = list(archetype.patterns)
    for own in module_patterns + _listed(instance.get("patterns")):
        if own not in applied:
            applied.append(own)
    if applied:
        resolved_instance["patterns"] = applied

    # Every template the shape produces, with the defaults folded in: what the
    # blocks created, what the modules bring, and what the archetype lists
    # itself. All of it goes through the same exclusion and override
    # handling, so an instance can drop a module-created system exactly as
    # it drops a listed one.
    def folded(type_name: str, template: dict) -> dict:
        merged: Dict[str, Any] = {}
        merged.update(entity_defaults.get("all", {}))
        merged.update(entity_defaults.get(type_name, {}))
        merged.update(template)
        # A template says `field: null` to take a default away: a vendor
        # tenancy has no deployment unit of ours, whatever the shape's
        # other systems have in common.
        merged = {k: v for k, v in merged.items() if v is not None}
        return substitute(merged, bindings)

    templates: List[Tuple[str, dict]] = []
    for type_name, records in block_entities.items():
        for record in records:
            templates.append((type_name, record))
    for type_name, record in module_templates:
        templates.append((type_name, folded(type_name, record)))
    for type_name, listed in archetype.provides.items():
        for template in listed:
            for unrolled in unroll(dict(template), bindings, "%s: archetype %s" % (instance_id, archetype.archetype_id)):
                templates.append((type_name, folded(type_name, unrolled)))

    # The cascade, run until nothing more drops: what points at an excluded
    # entity goes, and so does what points at that. It stopped one step out,
    # and excluding a product's store dropped the data asset mastered in it
    # while the API's read-write row to the asset stayed and dangled. Run in
    # waves rather than in the order the shape lists things, so what goes
    # does not depend on which part came first, and each entity is said to
    # go for the nearest thing it pointed at, an exclusion before a
    # dependent. The shorthands name what a system runs on and what governs
    # it: the row they make goes, the system stays.
    went_with: Dict[str, str] = {}
    wave_of: Dict[str, int] = {str(gone): 0 for gone in excluded}
    wave = 0
    while True:
        wave += 1
        found: Dict[str, str] = {}
        for type_name, record in templates:
            record_id = str(record.get(ENTITY_TYPES[type_name].pk))
            if record_id in wave_of or record_id in found:
                continue
            pointed = sorted(
                {str(v) for k, v in record.items()
                 if k not in _TEMPLATE_SHORTHANDS and str(v) in wave_of},
                key=lambda gone: (wave_of[gone], gone),
            )
            if pointed:
                found[record_id] = pointed[0]
        if not found:
            break
        for record_id, because in found.items():
            wave_of[record_id] = wave
            went_with[record_id] = because

    entities: Dict[str, List[dict]] = {}
    dropped_dependents: List[Tuple[str, str]] = []
    shorthand_rows: List[dict] = []
    governance_rows: List[Tuple[str, dict]] = []
    # `uses` may name a kind where it names a service: `secrets-manager`
    # rather than the sample's Key Vault. Without a library there are no
    # kinds to know, and every entry is taken as the id it was written as.
    components = library[0] if library is not None else {}
    zone_of: Dict[Tuple[str, str], List[str]] = (
        library[3] if library is not None and len(library) > 3 else {}
    )
    by_hand = effective_bind(archetype) if components else {}
    for type_name, record in templates:
        pk = ENTITY_TYPES[type_name].pk
        record_id = record.get(pk)
        if not record_id:
            raise ArchetypeError(
                "%s: archetype %s provides a %s without %s"
                % (instance_id, archetype.archetype_id, type_name, pk)
            )
        runs_on = _listed(record.pop("runs_on", None))
        uses = _listed(record.pop("uses", None))
        governed = {
            "controls": _listed(record.pop("controls", None)),
            "policies": _listed(record.pop("policies", None)),
        }
        if record_id in excluded:
            unused_excludes.discard(record_id)
            continue
        # An entity that points at something excluded goes with it: an
        # interface to a system that does not exist is worse than no edge.
        if str(record_id) in went_with:
            dropped_dependents.append((record_id, went_with[str(record_id)]))
            continue
        override = overrides.get(record_id)
        if isinstance(override, dict):
            record.update(substitute(dict(override), bindings))
        record["archetype"] = archetype.archetype_id
        record["archetype_instance"] = instance_id
        seen_ids.add(record_id)
        entities.setdefault(type_name, []).append(record)
        if runs_on or uses:
            if type_name != "systems":
                raise ArchetypeError(
                    "%s: archetype %s puts runs_on/uses on a %s; only a system runs on "
                    "something" % (instance_id, archetype.archetype_id, type_name)
                )
            uses = resolve_uses(
                uses, archetype.provider, by_hand, zone_of, components,
                "%s: %s in archetype %s" % (instance_id, record_id, archetype.archetype_id),
            )
            for service_id in _resolve_runs_on(archetype, record_id, runs_on, block_ids) + uses:
                shorthand_rows.append({"system_id": record_id, "tech_service_id": service_id})
        for kind, ids in governed.items():
            if not ids:
                continue
            spec = _GOVERNANCE_ROWS.get((type_name, kind))
            if spec is None:
                raise ArchetypeError(
                    "%s: archetype %s puts `%s` on a %s; only systems and data assets are "
                    "governed" % (instance_id, archetype.archetype_id, kind, type_name)
                )
            relation_name, left, right = spec
            for governing_id in ids:
                governance_rows.append((relation_name, {left: record_id, right: governing_id}))

    # And a relation row naming anything that went goes with it.
    excluded |= set(went_with)
    relations: Dict[str, List[dict]] = {}
    seen_rows: Set[Tuple[str, str, str]] = set()

    def add_row(relation_name: str, row: dict) -> None:
        """Collect one relation row, dropping an exact repeat.

        The repeat is real: a block, a `uses` shorthand and a module can each
        produce the same `system_uses_tech_service` row, and the model would
        report all but the first as duplicates.

        The key comes off the relation's own declared columns, the way
        `Model._add_relation` builds its own. It used to be guessed from a
        precedence list of likely column names, which silently discarded rows
        it should have kept: in an `actor_uses_system` row both halves of the
        key resolved to `system_id`, so a second actor on the same system was
        dropped as a repeat of the first, and the qualifier -- what the actor
        actually does there -- was not part of the key at all.
        """
        if any(str(v) in excluded for v in row.values()):
            return
        spec = RELATION_TYPES.get(relation_name)
        if spec is None:
            # Not a relation the metamodel knows. Loading the model will refuse
            # it by name, which is a better error than anything guessed here.
            key = (relation_name, repr(sorted((str(k), str(v)) for k, v in row.items())), "")
        else:
            key = (
                relation_name,
                str(row.get(spec.left_column, "")),
                "%s\x00%s" % (
                    row.get(spec.right_column, ""),
                    row.get(spec.qualifier, "") if spec.qualifier else "",
                ),
            )
        if key in seen_rows:
            return
        seen_rows.add(key)
        row = dict(row)
        row["archetype_instance"] = instance_id
        relations.setdefault(relation_name, []).append(row)

    for row in block_connections:
        add_row("tech_service_connects_to", row)
    for row in shorthand_rows:
        add_row("system_uses_tech_service", row)
    for relation_name, row in governance_rows:
        add_row(relation_name, row)
    for relation_name, rows in module_relations.items():
        for row in rows:
            add_row(relation_name, row)
    for relation_name, listed in archetype.relations.items():
        for template in listed:
            for unrolled in unroll(dict(template), bindings, "%s: archetype %s" % (instance_id, archetype.archetype_id)):
                add_row(relation_name, substitute(unrolled, bindings))

    # Anything declared inline on the instance is merged in as-is.
    extra = instance.get("extra") or {}
    for type_name, records in (extra.items() if isinstance(extra, dict) else []):
        if type_name == "relations":
            for relation_name, rows in (records or {}).items():
                relations.setdefault(relation_name, []).extend(
                    [dict(r) for r in (rows or [])]
                )
            continue
        if type_name not in ENTITY_TYPES:
            raise ArchetypeError(
                "%s: extra declares unknown entity type %r" % (instance_id, type_name)
            )
        for record in records or []:
            record = dict(record)
            record["archetype_instance"] = instance_id
            entities.setdefault(type_name, []).append(record)

    # Every system the instance ends up with is part of the product, the
    # ones the instance added under `extra` included: a system added to a
    # product by hand is no less its part than one the shape made.
    if archetype.include_systems and instance_type == "products":
        for record in entities.get("systems", []):
            add_row(
                "product_includes_system",
                {"product_id": str(instance_id), "system_id": str(record["system_id"])},
            )

    unknown_overrides = sorted(set(overrides) - seen_ids)
    if unknown_overrides:
        raise ArchetypeError(
            "%s: override targets not produced by archetype %s: %s"
            % (instance_id, archetype.archetype_id, ", ".join(unknown_overrides))
        )
    if unused_excludes:
        raise ArchetypeError(
            "%s: exclude targets not produced by archetype %s: %s"
            % (instance_id, archetype.archetype_id, ", ".join(sorted(unused_excludes)))
        )

    if renames:
        unknown = sorted(set(renames) - seen_ids)
        if unknown:
            raise ArchetypeError(
                "%s: ids renames %s, which archetype %s does not make"
                % (instance_id, ", ".join(unknown), archetype.archetype_id)
            )
        taken = sorted(set(renames.values()) & (seen_ids - set(renames)))
        if taken:
            raise ArchetypeError(
                "%s: ids renames onto %s, which archetype %s makes as well"
                % (instance_id, ", ".join(taken), archetype.archetype_id)
            )
        entities = _rename_deep(entities, renames)
        relations = _rename_deep(relations, renames)
        dropped_dependents = _rename_deep(dropped_dependents, renames)
        block_ids = _rename_deep(block_ids, renames)

    return Expansion(
        resolved_instance, entities, relations, dropped_dependents, block_ids, modules_applied,
        choices,
    )


def _renames(instance: dict, instance_id: str) -> Dict[str, str]:
    """`ids`: an id the shape makes to the id the estate already uses for
    it. A shape written after a product names things its own way; the
    processes, controls and flows that point at the product's systems do
    not, so a move keeps the estate's names rather than renaming what points
    at them."""
    raw = instance.get("ids") or {}
    if not isinstance(raw, dict) or not all(
        isinstance(k, str) and isinstance(v, str) and v.strip() for k, v in raw.items()
    ):
        raise ArchetypeError(
            "%s: `ids` maps an id the shape makes to the id the estate uses for it" % instance_id
        )
    out = {str(k): str(v).strip() for k, v in raw.items()}
    if len(set(out.values())) != len(out):
        raise ArchetypeError("%s: `ids` renames two ids onto one" % instance_id)
    return out


def _rename_deep(value, renames: Dict[str, str]):
    """Every string equal to a renamed id, wherever it sits: a record's own
    id, the systems an interface joins, a data asset's system of record, a
    relation row's columns."""
    if isinstance(value, str):
        return renames.get(value, value)
    if isinstance(value, dict):
        return {k: _rename_deep(v, renames) for k, v in value.items()}
    if isinstance(value, list):
        return [_rename_deep(v, renames) for v in value]
    if isinstance(value, tuple):
        return tuple(_rename_deep(v, renames) for v in value)
    if isinstance(value, set):
        return {_rename_deep(v, renames) for v in value}
    return value


#: Keys consumed by expansion rather than carried onto the resulting entity.
_INSTANCE_KEYS = {
    "archetype", "parameters", "overrides", "exclude", "extra", "patterns", "modules", "without",
    "choose", "compose", "ids",
}
