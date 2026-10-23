"""The house diagram palette.

Taken from the method's hand-drawn diagrams: a light tinted fill, a saturated
stroke of the same hue, and slate `#0f172a` text throughout. Keeping generated
diagrams on the same palette is what stops the model-driven output from looking
like it came from a different organization than the hand-drawn set it replaces.

`10_MODEL/model.yaml` may override or extend any bucket under `palette:`.

Three bases. `classic` is that house palette and what every export is drawn
in unless the estate says otherwise; `stone` and `graphite` are the app's two
tones, each a whole palette of its own: a hue per entity type, a ramp for
free-text values, the boundary tints and the ink, tuned to the shell around
them, so a drawing reads as part of the page rather than pasted onto it. An
estate picks its base with `palette: {base: stone}`; any bucket it names on
top replaces the base's in every tone, and a section named for a tone
(`stone:` or `graphite:`) replaces it in that tone alone. The app asks for its
tone by name, so the same estate can be read in either.
"""

from __future__ import annotations

import zlib
from typing import Dict, NamedTuple

INK = "#0f172a"
#: Ink for the deepest ordinal tints, where slate on a strong fill goes muddy.
DEEP_INK = "#0b1020"


class Swatch(NamedTuple):
    fill: str
    stroke: str
    ink: str = INK


#: Visually distinct hues for style keys with no named bucket. Which one a key
#: gets is a function of the key itself, never of what was drawn before it.
RAMP = (
    Swatch("#eef2ff", "#6366f1"),
    Swatch("#dcfce7", "#16a34a"),
    Swatch("#fef3c7", "#f59e0b"),
    Swatch("#cffafe", "#06b6d4"),
    Swatch("#fae8ff", "#a855f7"),
    Swatch("#fee2e2", "#dc2626"),
    Swatch("#fff7ed", "#ea580c"),
    Swatch("#fdf2f8", "#db2777"),
    Swatch("#f1f5f9", "#64748b"),
)

def _spread(named: Dict[str, Swatch], values, offset: int = 0, ramp: tuple = RAMP) -> None:
    """Give one closed enumeration a distinct hue per value.

    A view colors by a single field, so distinctness only has to hold inside
    one enumeration. Doing it this way means the same value is the same color
    on every diagram, which the hashed fallback cannot promise.

    Values overlap between enumerations -- "Public" is a network zone and a
    classification, "On-prem" is a zone and a cloud provider -- and a string
    can carry only one color. Whoever named it first keeps it, and the rest of
    this enumeration picks around that hue rather than landing on it.
    """
    taken = {named[value].stroke for value in values if value in named}
    slot = offset
    for value in values:
        if value in named:
            continue
        for _ in range(len(ramp)):
            candidate = ramp[slot % len(ramp)]
            slot += 1
            if candidate.stroke not in taken:
                named[value] = candidate
                taken.add(candidate.stroke)
                break
        else:  # pragma: no cover - only if an enum outgrows the ramp
            named[value] = ramp[slot % len(ramp)]


#: Named buckets for the dimensions views most often color by. Everything the
#: schema enumerates is named here: an enum is a closed set, so leaving it to
#: the hashed fallback risks two of its values landing on one hue in the same
#: diagram, which is a legend that cannot be read.
NAMED: Dict[str, Swatch] = {
    # criticality
    "High": Swatch("#fee2e2", "#dc2626"),
    "Medium": Swatch("#fef3c7", "#f59e0b"),
    "Low": Swatch("#dcfce7", "#16a34a"),
    # status
    "Active": Swatch("#dcfce7", "#16a34a"),
    "Planned": Swatch("#eef2ff", "#6366f1"),
    "Proposed": Swatch("#cffafe", "#06b6d4"),
    "Deprecated": Swatch("#fef3c7", "#f59e0b"),
    "Retired": Swatch("#f1f5f9", "#64748b"),
    # entity type
    "systems": Swatch("#eef2ff", "#6366f1"),
    "interfaces": Swatch("#cffafe", "#06b6d4"),
    "data_assets": Swatch("#dcfce7", "#16a34a"),
    "tech_services": Swatch("#fff7ed", "#ea580c"),
    "capabilities": Swatch("#fae8ff", "#a855f7"),
    "org_units": Swatch("#f1f5f9", "#64748b"),
    "products": Swatch("#fdf2f8", "#db2777"),
    "actors": Swatch("#fef3c7", "#f59e0b"),
    "flows": Swatch("#fdf2f8", "#db2777"),
    "controls": Swatch("#fee2e2", "#dc2626"),
    "policies": Swatch("#cffafe", "#06b6d4"),
    "default": Swatch("#f1f5f9", "#64748b"),
}

#: Offsets are chosen so that no enumeration starts where another one does,
#: which keeps two dimensions drawn side by side from looking like one.
_ENUMS = (
    (("Person", "Role", "Organization", "External system", "Regulator", "Device"), 0),
    (("Edge", "Public", "Private-App", "Private-Data", "Shared-Services", "On-prem"), 3),
    (("AWS", "Azure", "GCP", "On-prem", "SaaS", "External"), 6),
    (("Business", "Application", "Data", "Technology", "Governance"), 2),
    (("Contextual", "Conceptual", "Logical", "Physical"), 4),
    (("Direct", "Core", "Enable"), 2),
    (("Differentiating", "Essential", "Advantage", "Parity", "Commodity"), 5),
    (("L0", "L1", "L2", "L3"), 0),
    (("Public", "Internal", "Confidential", "Restricted"), 1),
    (("Production", "UAT", "Test", "Dev"), 5),
    (("Tier 1", "Tier 2", "Tier 3"), 0),
    (("Request-response", "Event", "Batch"), 3),
    (("Multi-region", "Multi-AZ", "Single-AZ", "Single-node"), 1),
    (("Preventive", "Detective", "Corrective"), 7),
    (("Continuous", "Per event", "Daily", "Weekly", "Monthly", "Quarterly", "Annually"), 2),
)
for _values, _offset in _ENUMS:
    _spread(NAMED, _values, _offset)


#: The encoding rule, stated once: **hue belongs to the entity type.** A
#: system is indigo on every diagram, a data asset green, a control red. The
#: dimension a view colors by gets a second channel instead of a second hue,
#: because the first version of this palette handed the same nine hues to
#: every dimension and "green" came to mean Low criticality, Active status
#: and data asset at once -- which is what made the legend unreadable.
#:
#: Fills sit at L≈90 rather than L≈96, so the fill carries the hue and the
#: stroke does not have to. Strokes stay saturated for the 1.5px border.
TYPE_SWATCHES: Dict[str, Swatch] = {
    "systems": Swatch("#c7d6ff", "#4338ca"),
    # What a system offers shares the system's hue, lighter, the way a
    # value stream's stages share the stream's: an API is read with the
    # service behind it and drawn beside it, and its shape says it is not
    # the service.
    "offered_interfaces": Swatch("#e6ecff", "#6366f1"),
    "products": Swatch("#fbcfe8", "#be185d"),
    "interfaces": Swatch("#a5f3fc", "#0e7490"),
    "data_assets": Swatch("#a7f3d0", "#047857"),
    "tech_services": Swatch("#fed7aa", "#c2410c"),
    "capabilities": Swatch("#ddd6fe", "#6d28d9"),
    "value_streams": Swatch("#e9d5ff", "#9333ea"),
    "value_stream_stages": Swatch("#f3e8ff", "#a855f7"),
    "org_units": Swatch("#cbd5e1", "#334155"),
    "actors": Swatch("#fde68a", "#b45309"),
    "flows": Swatch("#fbcfe8", "#db2777"),
    "controls": Swatch("#fca5a5", "#b91c1c"),
    "policies": Swatch("#fecaca", "#dc2626"),
    "frameworks": Swatch("#d9f99d", "#4d7c0f"),
    "processes": Swatch("#bae6fd", "#0369a1"),
    # Change. The roadmap and the work package under it share a hue at two
    # lightnesses, the way a value stream and its stages do, because they are
    # a container and its contents and are read together. A change request is
    # a different kind of thing -- a decision rather than a plan -- so it gets
    # its own hue. That yellow sits close to the actors' amber; the two never
    # share a diagram, and the legend names both.
    "roadmaps": Swatch("#99f6e4", "#0f766e"),
    "work_packages": Swatch("#ccfbf1", "#0d9488"),
    "architecture_change_requests": Swatch("#fef08a", "#a16207"),
    "default": Swatch("#e2e8f0", "#475569"),
}

#: Dimensions with an order. Highest first. Drawn as steps of one hue: the
#: strongest value gets the deepest tint and the heaviest border, and the
#: legend lists them in this order rather than alphabetically.
ORDINAL: Dict[str, tuple] = {
    "criticality": ("High", "Medium", "Low"),
    "risk_level": ("High", "Medium", "Low"),
    "classification": ("Restricted", "Confidential", "Internal", "Public"),
    "data_classification": ("Restricted", "Confidential", "Internal", "Public"),
    "data_classification_supported": ("Restricted", "Confidential", "Internal", "Public"),
    "service_tier": ("Tier 1", "Tier 2", "Tier 3"),
    "resilience": ("Multi-region", "Multi-AZ", "Single-AZ", "Single-node"),
    "capability_level": ("L0", "L1", "L2", "L3"),
    "capability_tier": ("Direct", "Core", "Enable"),
    "strategic_importance": ("Differentiating", "Essential", "Advantage", "Parity", "Commodity"),
}

#: Status is a lifecycle, and a lifecycle is a border style: solid for what
#: runs, dashed for what is agreed and not built, dotted for what is only
#: drafted, and a fade for what is on the way out.
STATUS_STYLE: Dict[str, dict] = {
    "Active": {"dash": "solid"},
    "Planned": {"dash": "dashed"},
    "Proposed": {"dash": "dotted"},
    "Deprecated": {"dash": "solid", "faded": True},
    "Retired": {"dash": "solid", "faded": True, "gray": True},
}

#: Border weights for ordinal steps, strongest first. A two-value enumeration
#: takes the ends; a five-value one takes them all.
_WEIGHTS = (2.6, 1.9, 1.4, 1.1, 1.0)
#: How far toward the stroke the fill is pulled per ordinal step.
_TINTS = (0.34, 0.18, 0.07, 0.0, 0.0)


class NodeStyle(NamedTuple):
    fill: str
    stroke: str
    ink: str
    #: Border width in px; the second channel for ordinal dimensions.
    width: float
    #: solid, dashed or dotted; the second channel for status.
    dash: str
    #: Drawn at reduced opacity: deprecated and retired things.
    faded: bool


def _hex(color: str) -> tuple:
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def _mix(a: str, b: str, t: float) -> str:
    """`t` of the way from color a to color b, in RGB."""
    ra, ga, ba = _hex(a)
    rb, gb, bb = _hex(b)
    return "#%02x%02x%02x" % (
        round(ra + (rb - ra) * t), round(ga + (gb - ga) * t), round(ba + (bb - ba) * t)
    )


def role_of(dimension: str | None) -> str:
    """What kind of thing a view is coloring by, which decides the channel."""
    if not dimension:
        return "none"
    if dimension == "type":
        return "type"
    if dimension == "status":
        return "status"
    if dimension in ORDINAL:
        return "ordinal"
    return "nominal"


def legend_order(dimension: str | None, values) -> list:
    """The values in the order a legend should list them."""
    present = {str(v) for v in values}
    if dimension in ORDINAL:
        ordered = [v for v in ORDINAL[dimension] if v in present]
        return ordered + sorted(present - set(ordered))
    if dimension == "status":
        ordered = [v for v in STATUS_STYLE if v in present]
        return ordered + sorted(present - set(ordered))
    return sorted(present)


class Palette:
    """Resolves style keys to swatches, assigning ramp colors as needed."""

    def __init__(self, overrides: Dict[str, dict] | None = None, tone: str | None = None) -> None:
        config = overrides if isinstance(overrides, dict) else {}
        # The tone asked for wins, then the estate's base, then classic: an
        # export with nothing said is drawn exactly as it always was.
        name = tone if tone in BASES else (config.get("base") if config.get("base") in BASES else "classic")
        base = BASES[name]
        #: Which base this is: classic, stone or graphite.
        self.tone = name
        self.ink = base.ink
        self.ramp = base.ramp
        self.depth_fills = base.depth_fills
        self.boundary_stroke = base.boundary_stroke
        self.boundary_ink = base.boundary_ink
        self.named: Dict[str, Swatch] = dict(base.named)
        self.types: Dict[str, Swatch] = dict(base.types)
        # The estate's own buckets apply in every tone; a section named for
        # this tone applies on top, so an organization can keep its systems
        # blue everywhere and still give Graphite a darker blue.
        own = config.get(name)
        for layer in (config, own if isinstance(own, dict) else {}):
            for key, value in layer.items():
                if isinstance(value, dict) and "fill" in value and "stroke" in value:
                    swatch = Swatch(value["fill"], value["stroke"], value.get("ink", self.ink))
                    self.named[key] = swatch
                    if key in self.types:
                        self.types[key] = swatch
        #: Collision-free colors for one diagram's free-text keys, from `assign`.
        self._assigned: Dict[str, Swatch] = {}

    def type_swatch(self, entity_type: str) -> Swatch:
        return self.types.get(entity_type, self.types["default"])

    def node_style(self, entity_type: str, dimension: str | None, value) -> NodeStyle:
        """How one node is drawn: its type's hue, plus the dimension's channel.

        An ordinal value deepens the tint and thickens the border; a status
        sets the border style; anything nominal changes nothing, because the
        boundary it is grouped under already says it and a second hue would
        only collide with the type's.
        """
        base = self.type_swatch(entity_type)
        value = "" if value is None else str(value)
        role = role_of(dimension)
        if role == "ordinal":
            levels = ORDINAL[dimension]
            if value in levels:
                steps = len(levels)
                index = levels.index(value)
                # Spread the available steps across the weight table so the
                # strongest value is always the heaviest and the weakest the
                # lightest, whatever the enumeration's length.
                slot = round(index * (len(_WEIGHTS) - 1) / max(steps - 1, 1))
                return NodeStyle(
                    fill=_mix(base.fill, base.stroke, _TINTS[slot]),
                    stroke=base.stroke,
                    ink=base.ink,
                    width=_WEIGHTS[slot],
                    dash="solid",
                    faded=False,
                )
            return NodeStyle(base.fill, base.stroke, base.ink, 1.1, "solid", False)
        if role == "status":
            style = STATUS_STYLE.get(value, {"dash": "solid"})
            gray = self.types["default"]
            if style.get("gray"):
                return NodeStyle(gray.fill, gray.stroke, gray.ink, 1.1, "solid", True)
            return NodeStyle(
                base.fill, base.stroke, base.ink, 1.4, style["dash"], bool(style.get("faded"))
            )
        return NodeStyle(base.fill, base.stroke, base.ink, 1.4, "solid", False)
    def assign(self, keys) -> None:
        """Settle the colors for one diagram's key set, avoiding collisions.

        The hashed fallback is stable but not injective, so two free-text
        values can land on one hue. Inside a single diagram that is a legend
        nobody can read. Keys are settled in sorted order and named ones never
        move, so the outcome depends on the set and not on the drawing order.
        """
        present = {str(key) for key in keys}
        wanted = sorted(present - set(self.named))
        # Only the named colors this diagram actually uses are spoken for.
        # Reserving every named color would leave nothing to hand out, since
        # the named buckets between them cover the whole ramp.
        taken = {self.named[key].stroke for key in present & set(self.named)}
        ramp = self.ramp
        for key in wanted:
            start = zlib.crc32(key.encode("utf-8")) % len(ramp)
            for step in range(len(ramp)):
                candidate = ramp[(start + step) % len(ramp)]
                if candidate.stroke not in taken:
                    self._assigned[key] = candidate
                    taken.add(candidate.stroke)
                    break
            else:
                # More categories than hues. Reusing one beats dropping a node.
                self._assigned[key] = ramp[start]

    def swatch(self, key: str) -> Swatch:
        """The color for a style key.

        Ramp colors used to be handed out in encounter order, which made the
        color of a box depend on which diagrams had been drawn before it: one
        palette renders every view, so `terrane render` and the app disagreed about
        the same view, and inserting a view changed the colors in later ones.
        A key now hashes to its slot, so a value is the same color everywhere
        and adding a new one never recolors the others. Two keys can land on
        one hue; the legend is what disambiguates them.
        """
        if key in self.named:
            return self.named[key]
        if key in self._assigned:
            return self._assigned[key]
        return self.ramp[zlib.crc32(str(key).encode("utf-8")) % len(self.ramp)]

    def used(self, keys) -> Dict[str, Swatch]:
        return {key: self.swatch(key) for key in keys}


# ---------------------------------------------------------------------------
# Boundaries, drawn the way the provider draws them.
# ---------------------------------------------------------------------------
#
# A reader of AWS diagrams knows a dashed teal box is a region and a green
# one a public subnet before reading the name; Azure's reader knows the blue
# box is the subscription. The boundaries here used to be one tint deepening
# with depth, which kept hue for entity types but told that reader nothing.
# Each boundary now carries the convention of the provider it belongs to:
# the AWS group shapes' colors and line styles, Azure's blues, Google's
# dashed project. Hue still means entity type on the nodes: these are pale
# fills and thin strokes on containers, and the legend names each kind.


class BoundaryStyle(NamedTuple):
    fill: str
    stroke: str
    #: solid, dashed or dotted.
    dash: str
    #: The name's color.
    ink: str
    #: The kind word written before the value: "region eu-west-2".
    word: str
    #: How the legend names the kind: "AWS region", "public subnet".
    key: str


#: The depth tint, for a boundary that is not a cloud container: a domain, a
#: value stream, an entity type.
_DEPTH_FILLS = ("#f3f5fb", "#e7ebf6", "#dbe1f0", "#cfd7ea")

#: Field names that mean the same container.
_KIND_ALIASES = {"hosting": "cloud_provider"}

#: What the account level is called, by provider.
_ACCOUNT_WORD = {"AWS": "account", "Azure": "subscription", "GCP": "project", "SaaS": "tenancy"}

_PROVIDER_BOX = {
    "AWS": ("#fbfcfd", "#232f3e", "solid", "#232f3e"),
    "Azure": ("#f7fbfe", "#0078d4", "solid", "#1b4b7a"),
    "GCP": ("#f8fbff", "#4285f4", "solid", "#1a4f9e"),
    "On-prem": ("#f4f5f7", "#5f6b7a", "solid", "#3f4a5c"),
    "SaaS": ("#fcfbf7", "#9a8f6a", "dashed", "#6b6246"),
}

_ACCOUNT_BOX = {
    "AWS": ("#fdf6fa", "#c7257e", "solid", "#8b1a58"),
    "Azure": ("#f7fbfe", "#0078d4", "dashed", "#1b4b7a"),
    "GCP": ("#f8fbff", "#4285f4", "dashed", "#1a4f9e"),
    "SaaS": ("#fcfbf7", "#9a8f6a", "dashed", "#6b6246"),
}

_REGION_BOX = {
    "AWS": ("#f5fbfb", "#00a4a6", "dashed", "#0b6e70"),
    "Azure": ("#f8fafc", "#7a8699", "dotted", "#4b5563"),
    "GCP": ("#f8fafc", "#5f6368", "dotted", "#3c4043"),
}

_ZONE_BOX = {
    "AWS": ("#f6f9fd", "#147eba", "dashed", "#0f5f8c"),
    "Azure": ("#f8fafc", "#7a8699", "dashed", "#4b5563"),
    "GCP": ("#f6fbf7", "#34a853", "dashed", "#1e7a3a"),
}

#: Network tiers, by what the tier is: a public one is green on AWS, a
#: private one blue, a shared-services one the VPC purple, the data center
#: gray. Azure and Google draw every subnet alike, in their own blue.
_PUBLIC_TIERS = {"Public", "Edge", "DMZ"}
_SHARED_TIERS = {"Shared-Services", "Shared", "Hub"}
_ONPREM_TIERS = {"On-prem", "On-premise", "On-premises", "Datacenter"}


def _tier_box(value: str, provider: str):
    if value in _ONPREM_TIERS:
        return ("#f4f5f7", "#5f6b7a", "solid", "#3f4a5c", "on-prem")
    if provider == "AWS":
        if value in _PUBLIC_TIERS:
            return ("#f3f7e9", "#7aa116", "solid", "#4f6a0e", "public subnet")
        if value in _SHARED_TIERS:
            return ("#f4f0ff", "#8c4fff", "solid", "#5b2fb0", "shared services")
        return ("#eef5fb", "#147eba", "solid", "#0f5f8c", "private subnet")
    if provider == "Azure":
        return ("#f1f6fb", "#5b9bd5", "solid", "#2f5d8a", "Azure subnet")
    if provider == "GCP":
        return ("#f1f6ff", "#4285f4", "solid", "#1a4f9e", "GCP subnet")
    if provider == "SaaS":
        return ("#fcfbf7", "#9a8f6a", "dashed", "#6b6246", "vendor tenancy")
    if value in _PUBLIC_TIERS:
        return ("#f3f7e9", "#7aa116", "solid", "#4f6a0e", "public tier")
    return ("#eef5fb", "#147eba", "solid", "#0f5f8c", "private tier")


def boundary_style(kind: str, value: str, provider: str, depth: int = 1,
                   palette: "Palette | None" = None) -> BoundaryStyle:
    """How one boundary is drawn: by the kind of container it is (the field
    the view grouped by), the provider it belongs to, and for a network
    tier the tier itself. Anything that is not a cloud container keeps the
    depth tint, in the palette's own tints when one is given: a provider's
    box is the provider's convention in every tone, a domain is the page's."""
    kind = _KIND_ALIASES.get(kind, kind)
    value = str(value or "")
    provider = str(provider or "")
    if kind == "cloud_provider":
        box = _PROVIDER_BOX.get(value)
        if box:
            return BoundaryStyle(box[0], box[1], box[2], box[3], "", value)
    elif kind == "cloud_account":
        box = _ACCOUNT_BOX.get(provider, ("#f8fafc", "#8f9bb5", "solid", "#3b4a6b"))
        word = _ACCOUNT_WORD.get(provider, "account")
        return BoundaryStyle(box[0], box[1], box[2], box[3], word, ("%s %s" % (provider, word)).strip())
    elif kind == "region":
        box = _REGION_BOX.get(provider, ("#f8fafc", "#8f9bb5", "dashed", "#3b4a6b"))
        return BoundaryStyle(box[0], box[1], box[2], box[3], "region", ("%s region" % provider).strip())
    elif kind == "availability_zone":
        box = _ZONE_BOX.get(provider, ("#f8fafc", "#8f9bb5", "dashed", "#3b4a6b"))
        return BoundaryStyle(box[0], box[1], box[2], box[3], "zone", ("%s availability zone" % provider).strip())
    elif kind == "network_zone":
        fill, stroke, dash, ink, key = _tier_box(value, provider)
        return BoundaryStyle(fill, stroke, dash, ink, "", key)
    fills = palette.depth_fills if palette is not None else _DEPTH_FILLS
    fill = fills[min(max(depth, 1) - 1, len(fills) - 1)]
    if palette is not None:
        return BoundaryStyle(fill, palette.boundary_stroke, "solid", palette.boundary_ink, "", "")
    return BoundaryStyle(fill, "#8f9bb5", "solid", "#3b4a6b", "", "")


def boundary_label(kind: str, value: str, provider: str) -> str:
    """The name on the box: the kind word, then the value, the way an AWS
    diagram writes "Region" over its name. A tier or a provider is its own
    word."""
    style = boundary_style(kind, value, provider)
    return ("%s %s" % (style.word, value)).strip() if style.word else str(value)


# ---------------------------------------------------------------------------
# The bases: classic, and the app's two tones.
# ---------------------------------------------------------------------------
#
# A tone is a whole palette, not the classic one recolored. Each entity type
# keeps a hue of its own -- the rule above holds in every tone -- but the hues
# are chosen for the page they sit on: Stone's are earth and print inks beside
# warm grays, Graphite's cleaner and a step more saturated beside neutral ones.
# The tone's accent is the system hue in each, so the most common box on any
# drawing is the color the chrome already uses: teal in Stone, amber in
# Graphite. The types that are read together share a hue at two lightnesses,
# as they do in classic (a value stream and its stages, a roadmap and its work
# packages); the ones that meet on a drawing are kept apart by hue, not only
# by lightness, because a legend of two blues is a legend nobody reads.


class Base(NamedTuple):
    """One whole palette: what a tone draws with."""
    ink: str
    deep_ink: str
    ramp: tuple
    named: Dict[str, Swatch]
    types: Dict[str, Swatch]
    #: The tints a plain boundary deepens through, lightest first, and the
    #: line and name it is drawn with.
    depth_fills: tuple
    boundary_stroke: str
    boundary_ink: str


def _tone(ink: str, deep_ink: str, ramp, types, semantic, depth_fills, boundary_stroke: str,
          boundary_ink: str) -> Base:
    """A tone's palette from its pairs of (fill, stroke). Every swatch carries
    the tone's own ink. The named buckets are the semantic ones given, then
    each type's hue under its own name, so a view colored by type agrees with
    one drawn by type, then every enumeration spread over the tone's ramp at
    the offsets classic uses."""
    def swatch(pair) -> Swatch:
        return Swatch(pair[0], pair[1], ink)
    ramp = tuple(swatch(pair) for pair in ramp)
    types = {key: swatch(pair) for key, pair in types.items()}
    named = {key: swatch(pair) for key, pair in semantic.items()}
    for key, value in types.items():
        named.setdefault(key, value)
    for values, offset in _ENUMS:
        _spread(named, values, offset, ramp)
    return Base(ink, deep_ink, ramp, named, types, tuple(depth_fills), boundary_stroke, boundary_ink)


_STONE_TYPES = {
    "systems": ("#cfe6e1", "#0f766e"),
    "offered_interfaces": ("#e8f3f0", "#2b8f84"),
    "products": ("#efd3df", "#9c3d66"),
    "interfaces": ("#d8dbef", "#4b53a0"),
    "data_assets": ("#dfe8c9", "#56781e"),
    "tech_services": ("#f2d9c6", "#b4532a"),
    "capabilities": ("#e6d7ea", "#7a4a87"),
    "value_streams": ("#eadff0", "#8e5aa3"),
    "value_stream_stages": ("#f3ebf6", "#a47bb5"),
    "org_units": ("#e3ded6", "#5e564c"),
    "actors": ("#f2e3bd", "#9a6b12"),
    "flows": ("#f3d7d5", "#a8474a"),
    "controls": ("#f1d1ca", "#a33a2a"),
    "policies": ("#f6e0d8", "#b65a44"),
    "frameworks": ("#dde3ea", "#4a6278"),
    "processes": ("#d3e3f2", "#2a6496"),
    "roadmaps": ("#e8dacb", "#7b5130"),
    "work_packages": ("#f2e8dc", "#9a6e4a"),
    "architecture_change_requests": ("#f1e6b2", "#8c7410"),
    "default": ("#e5e1d9", "#6b6358"),
}

_GRAPHITE_TYPES = {
    "systems": ("#f6dcbc", "#b45a0e"),
    "offered_interfaces": ("#fbeedf", "#c47a36"),
    "products": ("#f4d3da", "#b2324a"),
    # Interfaces take the yellow: they are lines far more often than boxes,
    # and the actors, which stand beside systems on every context diagram,
    # need a hue well away from the systems' amber. Yellow beside amber
    # read as one warm color at diagram size.
    "interfaces": ("#f6ecb4", "#8f7300"),
    "data_assets": ("#cdeadb", "#187a4c"),
    "tech_services": ("#cce6e8", "#16707a"),
    "capabilities": ("#e4daf6", "#6b45b8"),
    "value_streams": ("#ecdcf4", "#8a45b0"),
    "value_stream_stages": ("#f4eaf9", "#a06ec4"),
    "org_units": ("#e2e2df", "#4a4b4f"),
    "actors": ("#dce5f6", "#3b5ba5"),
    "flows": ("#f4d2e3", "#b0306e"),
    "controls": ("#f6cfcb", "#b3261e"),
    "policies": ("#f8e0d8", "#c2533a"),
    "frameworks": ("#e3ebc4", "#5f7a12"),
    "processes": ("#d3e8f6", "#1f6fa3"),
    "roadmaps": ("#dadcf1", "#3f4a9a"),
    "work_packages": ("#e8e9f7", "#5c67b5"),
    "architecture_change_requests": ("#efe0c9", "#8a5a1c"),
    "default": ("#e4e4e0", "#5f5e59"),
}


def _semantic(types: dict, amber: str, blue: str) -> dict:
    """Criticality and status in a tone's own hues: the red it gives
    controls for High, its yellow for Medium and for what is on the way out,
    its data green for Low and for what runs, a blue for what is planned.
    Which type holds the yellow and the blue differs by tone, so it is said."""
    return {
        "High": types["controls"], "Medium": types[amber], "Low": types["data_assets"],
        "Active": types["data_assets"], "Planned": types[blue], "Proposed": types["processes"],
        "Deprecated": types[amber], "Retired": types["default"],
    }


def _ramp(types: dict, order) -> list:
    return [types[key] for key in order]


#: The order a tone hands out hues to free-text values: the most distinct
#: first, so a diagram with three values never gets two neighbors.
_RAMP_ORDER = ("systems", "tech_services", "capabilities", "data_assets", "actors", "interfaces", "flows",
               "processes", "default")

BASES: Dict[str, Base] = {
    "classic": Base(INK, DEEP_INK, RAMP, NAMED, TYPE_SWATCHES, _DEPTH_FILLS, "#8f9bb5", "#3b4a6b"),
    "stone": _tone("#24201b", "#1a1714", _ramp(_STONE_TYPES, _RAMP_ORDER), _STONE_TYPES,
                   _semantic(_STONE_TYPES, "actors", "interfaces"),
                   ("#f2eee7", "#e9e3d9", "#dfd8cc", "#d5cdbf"), "#9c9284", "#4a4238"),
    "graphite": _tone("#1c1d20", "#121315", _ramp(_GRAPHITE_TYPES, _RAMP_ORDER), _GRAPHITE_TYPES,
                      _semantic(_GRAPHITE_TYPES, "interfaces", "actors"),
                      ("#f3f3f0", "#e9e9e5", "#dfdfda", "#d4d4cf"), "#9a9a94", "#3e3f43"),
}

#: The app's tones, in the order its setting lists them; the first is the
#: one a page opens in when the estate names none.
TONES = ("stone", "graphite")
