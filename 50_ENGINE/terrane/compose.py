"""Composing a shape from parts.

An archetype is composed from modules on blocks, and until now writing one
meant writing the file. This turns a choice into the file: which modules,
with what bound; which blocks, with what the landing zone already provides;
which patterns; which of the shape vocabulary the instance will be asked
for. The text it writes is the text a person would have written, in the
order the shipped shapes use, so it reads as one of them and is edited like
one of them.

Nothing here expands. The archetype editor previews and saves the text
through the same door as a typed one.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .blocks import load_blocks, load_components, load_patterns
from .archetype import landing_zone_index, resolve_kind
from .loader import load_folder
from .schema import ENTITY_TYPES
from .modules import ModuleError, load_modules, members_of, module_entries
from .sketch import yaml_text
from .yamlish import _strip_comment


class ComposeError(ValueError):
    pass


#: The shape vocabulary: what every shipped shape asks an instance for, with
#: the defaults the shipped shapes use. A composed shape asks for the subset
#: the composer ticked, and every module template can rely on the names.
VOCABULARY: Sequence[dict] = (
    {"name": "slug", "required": True,
     "description": "Short lower-case token used in identifiers, e.g. lending"},
    {"name": "product_name", "required": True,
     "description": "Human-readable product name, carried onto every entity name"},
    {"name": "owner_org", "required": True, "description": "Owning org unit id, e.g. ORG-DIGITAL"},
    {"name": "domain", "required": True, "description": "Company domain, for the business-facing views"},
    {"name": "account", "required": True, "description": "The workload account the product lands in"},
    {"name": "region", "default": "eu-west-2"},
    {"name": "criticality", "default": "High"},
    {"name": "classification", "default": "Restricted"},
    {"name": "vendor", "required": True, "description": "Vendor name, carried onto the vendor system as provider"},
    {"name": "vendor_region", "default": "eu-west-1",
     "description": "Where the vendor processes our data. A data residency answer."},
    {"name": "caller_system", "required": True,
     "description": "The system that calls the vendor in line, e.g. SYS-AUTH-SWITCH"},
)

_VOCABULARY_BY_NAME = {p["name"]: p for p in VOCABULARY}

#: What a provider is called on the entities that carry a hosting field.
_HOSTING = {"AWS": "AWS", "Azure": "Azure", "GCP": "GCP"}


def entity_defaults_for(provider: Optional[str], parameters: Sequence[str]) -> Dict[str, Dict[str, Any]]:
    """The `entity_defaults` a shape with these parameters would carry.

    The same block the shipped shapes have, derived rather than retyped: the
    fields every generated entity has in common, with a token wherever the
    shape has a parameter for it and nothing where it does not.
    """
    has = set(parameters)
    hosting = _HOSTING.get(provider or "", provider or "")
    all_defaults: Dict[str, Any] = {"status": "Planned"}
    if "domain" in has:
        all_defaults["company_domain"] = "{domain}"
    systems: Dict[str, Any] = {}
    if "owner_org" in has:
        systems["owner_org_id"] = "{owner_org}"
    if "criticality" in has:
        systems["criticality"] = "{criticality}"
    if hosting:
        systems["hosting"] = hosting
        systems["cloud_provider"] = hosting
    systems["environment"] = "Production"
    if "account" in has:
        systems["cloud_account"] = "{account}"
    if "region" in has:
        systems["region"] = "{region}"
    if "classification" in has:
        systems["data_classification_supported"] = "{classification}"
    systems.update({"togaf_layer": "Application", "architecture_domain": "Application",
                    "abstraction_level": "Physical"})
    interfaces: Dict[str, Any] = {}
    if "owner_org" in has:
        interfaces["owner_org_id"] = "{owner_org}"
    interfaces.update({"protocol": "HTTPS", "direction": "Outbound", "frequency": "Realtime",
                       "integration_style": "Request-response"})
    if "classification" in has:
        interfaces["data_classification"] = "{classification}"
    interfaces.update({"togaf_layer": "Application", "architecture_domain": "Application"})
    # What the service part offers: the product's owner and classification,
    # as its connections have, and no protocol, which the part says.
    offered: Dict[str, Any] = {}
    if "owner_org" in has:
        offered["owner_org_id"] = "{owner_org}"
    if "classification" in has:
        offered["data_classification"] = "{classification}"
    offered.update({"togaf_layer": "Application", "architecture_domain": "Application"})
    tech_services: Dict[str, Any] = {}
    if "owner_org" in has:
        tech_services["owner_org_id"] = "{owner_org}"
    if hosting:
        tech_services["cloud_provider"] = hosting
    if "account" in has:
        tech_services["cloud_account"] = "{account}"
    if "region" in has:
        tech_services["region"] = "{region}"
    tech_services.update({"togaf_layer": "Technology", "architecture_domain": "Technology"})
    out = {"all": all_defaults, "systems": systems, "interfaces": interfaces,
           "offered_interfaces": offered}
    if provider:
        out["tech_services"] = tech_services
    return out


def blocks_needed(module) -> List[str]:
    """The blocks a module's templates run on, by the `runs_on` shorthand in
    its templates and in its parameter defaults: `stateless-service` or
    `public-api-tier.dns` both name the block."""
    found: List[str] = []

    def note(value: Any) -> None:
        for item in (value if isinstance(value, list) else [value]):
            if not isinstance(item, str) or not item or item.startswith("{") or item.startswith("TS-"):
                continue
            block = item.split(".")[0]
            if block not in found:
                found.append(block)

    for templates in module.provides.values():
        for template in templates:
            note(template.get("runs_on"))
    for param in module.parameters:
        if param.name == "runs_on" and param.default is not None:
            note(param.default)
    return found


def archetype_from_parts(
    root,
    archetype_id: str,
    title: str,
    description: str,
    parameters: Sequence[str],
    modules: Sequence[dict] = (),
    blocks: Sequence[dict] = (),
    patterns: Sequence[str] = (),
    provider: Optional[str] = None,
    applies_to: str = "products",
    extra_parameters: Sequence[dict] = (),
    bind: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """The archetype data for a choice of parts.

    `modules` are `{module, with}` entries; `blocks` are `{block, bind}`
    entries with `bind` mapping a component to the shared service that
    already provides it. `parameters` names the vocabulary the shape asks
    for; anything a chosen module still needs and the shape does not bind is
    added as a required parameter, so the instance is asked rather than the
    expansion failing.
    """
    if not archetype_id or not title:
        raise ComposeError("a shape needs an archetype_id and a title")
    if not description.strip():
        raise ComposeError("a shape needs a description; it is what the New form shows")
    library_modules = load_modules(root)
    components = load_components(root)
    library_blocks = load_blocks(root, components)
    library_patterns = load_patterns(root, library_blocks)

    chosen_modules: List[dict] = []
    chosen_aliases = set()
    for entry in modules:
        module_id = str(entry.get("module") or "").strip()
        if not module_id:
            continue
        module = library_modules.get(module_id)
        if module is None:
            raise ComposeError("unknown module %r" % module_id)
        item: Dict[str, Any] = {"module": module_id}
        bound = {k: v for k, v in (entry.get("with") or {}).items() if str(v).strip()}
        if bound:
            item["with"] = bound
        chosen_modules.append(item)
        chosen_aliases.add(module_id)
        # A kit stands for its members: choosing `vendor-baseline` is choosing
        # the tenancy, the gateway and the vault, and anything that requires
        # one of those is satisfied.
        chosen_aliases.update(members_of(module, library_modules))
    for member in sorted(chosen_aliases):
        for needed in library_modules[member].requires:
            if needed not in chosen_aliases:
                raise ComposeError(
                    "%s requires %s; add it, or leave %s out" % (member, needed, member)
                )

    chosen_blocks: List[dict] = []
    for entry in blocks:
        block_id = str(entry.get("block") or "").strip()
        if not block_id:
            continue
        block = library_blocks.get(block_id)
        if block is None:
            raise ComposeError("unknown block %r" % block_id)
        provided = {p.component for p in block.provides}
        # Not `bind`: that is the shape-level map this function takes, and a
        # local of the same name here once shadowed it, so the composer
        # checked kinds against the last block's binds and wrote those out as
        # the shape's.
        component_binds = {}
        for component, service in (entry.get("bind") or {}).items():
            if not str(service).strip():
                continue
            if component not in provided:
                raise ComposeError("block %s has no component %r" % (block_id, component))
            component_binds[component] = str(service).strip()
        item = {"block": block_id}
        # A block on another cloud than the shape's: multi-cloud is one
        # product whose blocks resolve against different providers.
        block_provider = str(entry.get("provider") or "").strip()
        if block_provider and block_provider != (provider or ""):
            item["provider"] = block_provider
        if component_binds:
            item["bind"] = component_binds
        chosen_blocks.append(item)
    if chosen_blocks and not provider and any("provider" not in b for b in chosen_blocks):
        raise ComposeError("a shape built on blocks needs a provider to resolve them against")
    chosen_block_ids = {b["block"] for b in chosen_blocks}
    for item in chosen_modules:
        module = library_modules[item["module"]]
        bound_runs_on = (item.get("with") or {}).get("runs_on")
        needed = blocks_needed(module) if bound_runs_on is None else [
            str(x).split(".")[0] for x in (bound_runs_on if isinstance(bound_runs_on, list) else [bound_runs_on])
            if isinstance(x, str) and not x.startswith("TS-") and not x.startswith("{")
        ]
        for block_id in needed:
            if block_id not in chosen_block_ids:
                raise ComposeError(
                    "%s runs on the %s block; add the block, or bind the part's runs_on to something else"
                    % (item["module"], block_id)
                )

    for pattern_id in patterns:
        if pattern_id not in library_patterns:
            raise ComposeError("unknown pattern %r" % pattern_id)

    # Every kind a chosen part names has to be bound somewhere: on a block
    # the composer chose, or under `bind`. The composer cannot invent the
    # service, so it is told which kind is missing rather than which part.
    zone = {str(k): str(v) for k, v in (bind or {}).items() if str(v).strip()}
    for item in chosen_blocks:
        for kind, service in (item.get("bind") or {}).items():
            zone.setdefault(str(kind), str(service))
    landing = landing_zone_index(
        record for _path, record in load_folder(Path(root) / "10_MODEL" / "tech_services")
        if isinstance(record, dict)
    )
    for member in sorted(chosen_aliases):
        for param in library_modules[member].parameters:
            if not param.component or param.default is not None or param.component in zone:
                continue
            found, candidates = resolve_kind(param.component, provider or "", landing)
            if found:
                continue
            raise ComposeError(
                "%s: %r is of kind `%s`, which %s; bind it on a block, or under `bind`"
                % (member, param.name, param.component,
                   "the landing zone has %s for" % " and ".join(candidates)
                   if candidates else "no landing-zone service is")
            )

    # The parameters: the vocabulary ticked, then whatever a chosen module
    # still needs, then anything the composer added by hand.
    names: List[str] = []
    listed: List[dict] = []
    for name in parameters:
        spec = _VOCABULARY_BY_NAME.get(name)
        if spec is None:
            continue
        if name in names:
            continue
        names.append(name)
        listed.append({k: v for k, v in spec.items()})
    for extra in extra_parameters:
        name = str(extra.get("name") or "").strip()
        if not name or name in names:
            continue
        names.append(name)
        item = {"name": name}
        if extra.get("default") not in (None, ""):
            item["default"] = extra["default"]
        else:
            item["required"] = True
        if extra.get("description"):
            item["description"] = str(extra["description"])
        listed.append(item)
    for item in chosen_modules:
        module = library_modules[item["module"]]
        bound = set((item.get("with") or {}).keys())
        for param in module.parameters:
            if param.component:
                continue  # bound by the shape, not asked of the instance
            if param.estate:
                # Answered by the estate, in model.yaml, not asked of every
                # product assembled with the part; lifting it here made the
                # merchant portal's datastore ask its product who stewards data.
                continue
            if param.required and param.name not in bound and param.name not in names:
                names.append(param.name)
                listed.append({
                    "name": param.name, "required": True,
                    "description": param.description or ("Needed by the %s part" % module.name),
                })
        # And what the part reads from the shape without asking. Declared on
        # the part, so this is a lookup rather than a guess at the templates.
        for member in members_of(module, library_modules):
            for need in library_modules[member].needs:
                if need not in names:
                    names.append(need)
                    listed.append({
                        "name": need, "required": True,
                        "description": "Needed by the %s part" % library_modules[member].name,
                    })

    data: Dict[str, Any] = {
        "archetype_id": archetype_id,
        "title": title,
        "version": "0.1.0",
        "applies_to": applies_to,
    }
    if patterns:
        data["patterns"] = list(patterns)
    data["description"] = description.strip() + "\n"
    data["parameters"] = listed
    data["defaults"] = {"architecture_domain": "Business", "togaf_layer": "Business",
                        "abstraction_level": "Conceptual"}
    if provider:
        data["provider"] = provider
    data["entity_defaults"] = entity_defaults_for(provider, names)
    if chosen_blocks:
        data["blocks"] = chosen_blocks
    if bind:
        data["bind"] = {str(k): str(v) for k, v in bind.items() if str(v).strip()}
    if chosen_modules:
        data["modules"] = chosen_modules
    return data


def archetype_text_from_parts(root, **kwargs) -> str:
    data = archetype_from_parts(root, **kwargs)
    header = (
        "Composed in the app from the library: the parts, the blocks they run on,",
        "and the vocabulary the instance is asked for. Edit freely; this is the file.",
    )
    return yaml_text(data, header)


# ---------------------------------------------------------------------------
# A project assembled from parts, with no shape.
# ---------------------------------------------------------------------------

#: The key on an instance that composes it inline: the parts it is made of
#: and the provider they resolve against, where a product on a shape says
#: `archetype`. A project is assembled from chunks of the library the way a
#: shape is, and written as one file, because the second project like it is
#: when the shape is worth naming.
COMPOSE_KEY = "compose"

#: What `compose` may say. Anything else is a mistake worth naming.
_COMPOSE_KEYS = {"provider", "modules", "blocks", "bind", "patterns", "relations", "title"}

#: The defaulted vocabulary every assembled product answers, asked or not.
_ALWAYS_ANSWERED = {"region", "criticality", "classification"}


def composed_id(instance_id: str) -> str:
    """The id of the shape of one behind an assembled instance. It is what
    every entity the instance makes carries as `archetype`, so a reader can
    tell a product assembled from parts from one on a shared shape."""
    return "compose:%s" % instance_id


def is_composed(archetype_id: Any) -> bool:
    return str(archetype_id or "").startswith("compose:")


def blocks_for_parts(parts: Sequence[dict], library_modules) -> List[str]:
    """The blocks a choice of parts runs on, in order of first mention: what
    each part's templates and `runs_on` defaults name, or what the entry's
    own `with: {runs_on: ...}` names instead."""
    needed: List[str] = []

    def note(block_id: str) -> None:
        if block_id and block_id not in needed:
            needed.append(block_id)

    for entry in parts:
        module = library_modules.get(str(entry.get("module") or ""))
        if module is None:
            continue
        bound = (entry.get("with") or {}).get("runs_on")
        for member_id in members_of(module, library_modules):
            member = library_modules[member_id]
            if bound is None or member_id != module.module_id:
                for block_id in blocks_needed(member):
                    note(block_id)
            else:
                for item in (bound if isinstance(bound, list) else [bound]):
                    if isinstance(item, str) and item and not item.startswith("TS-") and not item.startswith("{"):
                        note(item.split(".")[0])
    return needed


def borrowed_blocks(provider, needed: Sequence[str], archetypes, library_blocks, landing) -> List[dict]:
    """The block entries an assembled project runs on.

    For each block the parts run on: the entry the provider's shipped shape
    uses, binds and all, so a project assembled on Azure lands on the same
    cluster and gateway as a product on the Azure shape, and gets its own
    hostname and firewall policy for the same reasons. Where no shape on
    that provider uses the block, each component is bound to the one
    landing-zone service of its kind, and created per project where the
    zone has none.
    """
    shapes = sorted(
        (a for a in archetypes if str(getattr(a, "provider", "") or "") == str(provider or "")),
        key=lambda a: a.archetype_id,
    )
    out: List[dict] = []
    for block_id in needed:
        entry: Optional[dict] = None
        for shape in shapes:
            for raw in shape.blocks:
                if str(raw.get("block")) == block_id and not raw.get("provider") and not raw.get("as"):
                    entry = {"block": block_id}
                    if raw.get("bind"):
                        entry["bind"] = {str(k): str(v) for k, v in raw["bind"].items()}
                    break
            if entry is not None:
                break
        if entry is None:
            entry = {"block": block_id}
            block = library_blocks.get(block_id)
            binds: Dict[str, str] = {}
            for provided in (block.provides if block is not None else ()):
                found, _candidates = resolve_kind(provided.component, provider or "", landing)
                if found:
                    binds[provided.component] = found
            if binds:
                entry["bind"] = binds
        out.append(entry)
    return out


def inline_shape(root, instance: dict, instance_type: str = "products", archetypes=()) -> Any:
    """The shape of one behind an instance that says `compose:`.

    The parts come from the instance; the vocabulary it is asked for is what
    it answered under `parameters`, plus whatever the parts need; the blocks
    are the ones the parts run on, bound the way the provider's shape binds
    them; the entity defaults are the ones every composed shape carries.
    What comes back is an archetype like any other, and `expand` does the
    rest, so overrides, exclusions and extras on the instance work exactly
    as they do on a shape. Refused, by name, for the same things a composed
    shape is refused for: an unknown part, a part without what it requires,
    a kind the landing zone cannot answer.
    """
    from .archetype import parse_archetype  # the shape type; a late import keeps this module light

    spec = instance.get(COMPOSE_KEY)
    pk = ENTITY_TYPES[instance_type].pk
    instance_id = str(instance.get(pk) or "")
    where = instance_id or "<instance>"
    if not isinstance(spec, dict):
        raise ComposeError("%s: `compose` must be a mapping with the parts under `modules`" % where)
    if instance.get("archetype"):
        raise ComposeError(
            "%s: says both `archetype` and `compose`; a product is on a shape or assembled "
            "from parts, not both" % where
        )
    unknown = sorted(k for k in spec if k not in _COMPOSE_KEYS)
    if unknown:
        raise ComposeError(
            "%s: `compose` does not take %s; it takes %s"
            % (where, ", ".join(unknown), ", ".join(sorted(_COMPOSE_KEYS)))
        )
    try:
        parts = module_entries(spec.get("modules"), where)
    except ModuleError as exc:
        raise ComposeError(str(exc))
    if not parts:
        raise ComposeError("%s: `compose` names no parts under `modules`" % where)
    provider = str(spec.get("provider") or "").strip() or None

    given = dict(instance.get("parameters") or {})
    library_modules = load_modules(root)
    # The vocabulary: what the instance answered; the three every product
    # carries whether answered or not, so the entities get a criticality, a
    # classification and a region; and whatever else a part needs that has
    # a house default, so a part that needs the vendor's region gets it
    # rather than a refusal.
    needed = set()
    for entry in parts:
        module = library_modules.get(str(entry.get("module") or ""))
        if module is None:
            continue
        for member_id in members_of(module, library_modules):
            needed.update(library_modules[member_id].needs)
    names = [
        p["name"] for p in VOCABULARY
        if p["name"] in given
        or ("default" in p and (p["name"] in _ALWAYS_ANSWERED or p["name"] in needed))
    ]
    extra = [{"name": k, "default": v} for k, v in given.items() if k not in _VOCABULARY_BY_NAME]
    components = load_components(root)
    library_blocks = load_blocks(root, components)
    blocks = spec.get("blocks")
    if blocks is None:
        landing = landing_zone_index(
            record for _path, record in load_folder(Path(root) / "10_MODEL" / "tech_services")
            if isinstance(record, dict)
        )
        blocks = borrowed_blocks(
            provider, blocks_for_parts(parts, library_modules), archetypes, library_blocks, landing
        )
    name = str(instance.get("name") or instance_id)
    data = archetype_from_parts(
        root,
        archetype_id=composed_id(instance_id),
        title=str(spec.get("title") or "%s (assembled)" % name),
        description=(
            "The shape of one behind %s: the parts it was assembled from, on the "
            "blocks they run on, bound the way the %s landing zone binds them. "
            "Not a file in 20_ARCHETYPES; it lives in the product's own `compose` block."
            % (name, provider or "shared")
        ),
        parameters=names,
        modules=parts,
        blocks=list(blocks or []),
        patterns=_listed_str(spec.get("patterns")),
        provider=provider,
        applies_to=instance_type,
        extra_parameters=extra,
        bind={str(k): str(v) for k, v in (spec.get("bind") or {}).items()},
    )
    if spec.get("relations"):
        data["relations"] = spec["relations"]
    return parse_archetype(data, None)


def _listed_str(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [v.strip() for v in value.replace(";", ",").split(",") if v.strip()]
    return [str(v).strip() for v in value if str(v).strip()]


#: The order a product file reads in: the record, then how it was assembled,
#: then what it says beyond that.
_ASSEMBLED_FIELD_ORDER = (
    "name", "description", "status", "owner_org_id", "criticality", "product_category",
    "build_type", "company_domain", "company_subdomain", "launch_date", "tags",
)

#: The comment an assembled file opens with when nobody has written one.
ASSEMBLED_HEADER = (
    "Assembled in the app from parts of the library, with no shape: the",
    "`compose` block is the whole architecture. `terrane validate` is the gate.",
)


def shaped_header(archetype_id: str) -> tuple:
    """The comment a product on a shape opens with when nobody has written one."""
    return (
        "On shape %s: its answers, and where this product differs." % archetype_id,
        "`terrane validate` is the gate.",
    )


def shaped_text(
    instance_type: str,
    instance_id: str,
    values: Dict[str, Any],
    archetype_id: str,
    parameters: Dict[str, Any],
    choose: Optional[Dict[str, Any]] = None,
    without: Sequence[str] = (),
    modules: Sequence[dict] = (),
    overrides: Optional[Dict[str, Any]] = None,
    exclude: Sequence[str] = (),
    extra: Optional[Dict[str, Any]] = None,
    note: str = "",
    header: Optional[Sequence[str]] = None,
    slot_defaults: Optional[Dict[str, str]] = None,
    ids: Optional[Dict[str, str]] = None,
) -> str:
    """The file for a product on a shape, in the order a reader wants it:
    what it is, the shape and its answers, where it chooses or does without,
    the names it keeps from before the shape,
    what it tells the parts it keeps, and what it says beyond them. The same
    keys `expand` reads. A choice equal to the shape's default is not
    written, so a product on the defaults says nothing about them."""
    pk = ENTITY_TYPES[instance_type].pk
    data: Dict[str, Any] = {pk: instance_id}
    for field in _ASSEMBLED_FIELD_ORDER:
        if values.get(field) not in (None, "", []):
            data[field] = values[field]
    for key, value in values.items():
        if key not in data and value not in (None, "", []) and key != pk:
            data[key] = value
    data["archetype"] = archetype_id
    data["parameters"] = {k: v for k, v in parameters.items() if v not in (None, "")}
    defaults = slot_defaults or {}
    chosen = {str(k): str(v) for k, v in (choose or {}).items() if str(v).strip()}
    differing = {k: v for k, v in chosen.items() if k not in defaults or defaults[k] != v}
    if differing:
        data["choose"] = differing
    dropped = [str(x) for x in without if str(x).strip()]
    if dropped:
        data["without"] = dropped
    kept = {str(k): str(v) for k, v in (ids or {}).items() if str(v).strip()}
    if kept:
        data["ids"] = kept
    parts = []
    for entry in modules or ():
        item: Dict[str, Any] = {"module": entry["module"]}
        if entry.get("as") and entry["as"] != entry["module"]:
            item["as"] = entry["as"]
        bound = {k: v for k, v in (entry.get("with") or {}).items() if v not in (None, "", [])}
        if bound:
            item["with"] = bound
        parts.append(item)
    if parts:
        data["modules"] = parts
    if overrides:
        data["overrides"] = overrides
    if exclude:
        data["exclude"] = list(exclude)
    if extra:
        data["extra"] = extra
    lines = list(header) if header else list(shaped_header(archetype_id))
    if note:
        lines.extend(["", note])
    return yaml_text(data, lines)


def assembled_text(
    instance_type: str,
    instance_id: str,
    values: Dict[str, Any],
    compose: Dict[str, Any],
    parameters: Dict[str, Any],
    overrides: Optional[Dict[str, Any]] = None,
    exclude: Sequence[str] = (),
    extra: Optional[Dict[str, Any]] = None,
    note: str = "",
    header: Optional[Sequence[str]] = None,
) -> str:
    """The file for a project assembled from parts, in the order a reader
    wants it: what it is, what it is made of, what it answers, and what it
    says beyond the parts. The same keys `expand` reads, so the text written
    is the text loaded. `header` is the comment the file opens with, when a
    person wrote one worth keeping; otherwise the house one."""
    pk = ENTITY_TYPES[instance_type].pk
    data: Dict[str, Any] = {pk: instance_id}
    for field in _ASSEMBLED_FIELD_ORDER:
        if values.get(field) not in (None, "", []):
            data[field] = values[field]
    for key, value in values.items():
        if key not in data and value not in (None, "", []) and key != pk:
            data[key] = value
    block: Dict[str, Any] = {}
    if compose.get("provider"):
        block["provider"] = compose["provider"]
    parts = []
    for entry in compose.get("modules") or []:
        item: Dict[str, Any] = {"module": entry["module"]}
        if entry.get("as") and entry["as"] != entry["module"]:
            item["as"] = entry["as"]
        bound = {k: v for k, v in (entry.get("with") or {}).items() if v not in (None, "", [])}
        if bound:
            item["with"] = bound
        parts.append(item)
    block["modules"] = parts
    for key in ("blocks", "bind", "patterns", "relations", "title"):
        if compose.get(key):
            block[key] = compose[key]
    data[COMPOSE_KEY] = block
    data["parameters"] = {k: v for k, v in parameters.items() if v not in (None, "")}
    if overrides:
        data["overrides"] = overrides
    if exclude:
        data["exclude"] = list(exclude)
    if extra:
        data["extra"] = extra
    lines = list(header) if header else list(ASSEMBLED_HEADER)
    if note:
        lines.extend(["", note])
    return yaml_text(data, lines)


# ---------------------------------------------------------------------------
# A save that keeps what a person wrote beside the data.
# ---------------------------------------------------------------------------

_KEY_AT = {}


def _key_re(indent: int):
    if indent not in _KEY_AT:
        _KEY_AT[indent] = re.compile(r"^ {%d}([^\s#\-][^:]*):(?:\s|$)" % indent)
    return _KEY_AT[indent]


class _Block:
    __slots__ = ("lead", "key", "head", "body")

    def __init__(self, lead, key, head, body):
        self.lead, self.key, self.head, self.body = lead, key, head, body

    def lines(self):
        return list(self.lead) + [self.head] + list(self.body)

    def data(self):
        """The lines that are data, trailing comments off, so two blocks that
        say the same thing compare equal whatever was written beside them."""
        return [_strip_comment(line).rstrip() for line in [self.head] + list(self.body)
                if line.strip() and not line.lstrip().startswith("#")]


def _blocks(lines, indent: int):
    """The lines before the first key at this indent, and a block per key:
    the comment and blank lines above it, the key line, and what follows to
    the next key at the same indent."""
    key_re = _key_re(indent)
    head = []
    blocks = {}
    order = []
    pending = []
    current = None
    for line in lines:
        m = key_re.match(line)
        if m:
            key = m.group(1).strip()
            current = _Block(pending, key, line, [])
            pending = []
            if key not in blocks:
                order.append(key)
            blocks[key] = current
        elif current is None and indent == 0:
            # Above the first key of the file is its header; inside a body,
            # a comment above the first key belongs to that key.
            head.append(line)
        elif current is None:
            pending.append(line)
        elif line.strip() == "" or line.lstrip().startswith("#"):
            # A comment or a blank between keys belongs to the key below; one
            # inside a body, with data after it, stays in the body.
            pending.append(line)
        else:
            current.body.extend(pending)
            pending = []
            current.body.append(line)
    if current is not None:
        current.body.extend(pending)
    else:
        head.extend(pending)
    return head, [(key, blocks[key]) for key in order]


def _is_mapping(block: _Block, indent: int) -> bool:
    data = [line for line in block.body if line.strip() and not line.lstrip().startswith("#")]
    return bool(data) and all(_key_re(indent + 2).match(line) or len(line) - len(line.lstrip()) > indent + 2 for line in data) \
        and bool(_key_re(indent + 2).match(data[0]))


def _merge(new_blocks, old_blocks, indent: int):
    old = dict(old_blocks)
    out = []
    for key, block in new_blocks:
        before = old.get(key)
        if before is None:
            out.extend(block.lines())
        elif before.data() == block.data():
            out.extend(before.lines())
        else:
            out.extend(before.lead if before.lead else block.lead)
            out.append(block.head)
            if _is_mapping(block, indent) and _is_mapping(before, indent):
                _h1, inner_new = _blocks(block.body, indent + 2)
                _h2, inner_old = _blocks(before.body, indent + 2)
                out.extend(_merge(inner_new, inner_old, indent + 2))
            else:
                out.extend(block.body)
    return out


def keep_comments(new_text: str, old_text: str) -> str:
    """The file as the panel would write it, with what a person wrote beside
    the data put back. A key whose data did not change keeps its lines as
    they were, the comments inside them included; one whose data changed
    keeps the comment written above it and takes the new lines; a key the
    new file does not have goes, and its comments with it; a new key comes
    as written. Mappings merge key by key at every depth, so the remark
    above one override survives a change to another. The header above the
    data is the new text's, which the caller already carried over."""
    new_head, new_blocks = _blocks(new_text.splitlines(), 0)
    _old_head, old_blocks = _blocks(old_text.splitlines(), 0)
    lines = list(new_head) + _merge(new_blocks, old_blocks, 0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines) + "\n"
