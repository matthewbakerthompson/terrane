"""The encoding the app draws with, as data: the same tables `app.js` holds.

Shape and hue belong to the entity type; the view's dimension is a border
weight and tint, a border style, or the boundary; a component's category is
a glyph in the corner, a provider's mark takes the corner where one may
travel, and a type with neither says itself with its own small mark. These
tables are copied from the app rather than shared with it because the app
is plain browser JavaScript with no build step; `tests/test_draw_packed.py`
checks the two agree on the polygons Cytoscape reported.
"""

from __future__ import annotations

from typing import Dict, Sequence

#: Node boxes are sized from the label at 12px Geist 600: the average glyph
#: width and the line height of that face at that size, plus the padding the
#: box wants. Calibrated in the app rather than measured, so the Python side
#: must use the same numbers rather than its own measurement.
LABEL_WIDTH = 132
TECH_H = 11
TECH_CHAR_W = 4.6
FAN_PX = 12
CHAR_W = 6.8
LINE_H = 16
PAD_X = 28
PAD_Y = 20
TECH_FONT = 8

#: The boundary name is 11px Geist 600, sized at 6.1px an advance, 12px in
#: from the left border; the layout and the stylesheet count the same room.
TITLE_CHAR = 6.1

#: The compound padding in the stylesheet, which the layout must match.
LAYOUT = {"nodesep": 26, "ranksep": 48, "edgesep": 14, "gapX": 24, "gapY": 20,
          "boundaryPad": 24, "boundaryLabel": 0}

#: Nested boundaries tint progressively so containment reads as containment.
BOUNDARY_FILL = ("#f3f5fb", "#e7ebf6", "#dbe1f0", "#cfd7ea")

SHAPES: Dict[str, str] = {
    "systems": "round-rectangle",
    # What a system offers is the one pill, as `SHAPES` in app.js has it.
    "offered_interfaces": "pill",
    "products": "round-tag",
    "capabilities": "hexagon",
    "data_assets": "barrel",
    "tech_services": "rhomboid",
    "org_units": "rectangle",
    "interfaces": "tag",
    "actors": "ellipse",
    "flows": "round-tag",
    "value_streams": "round-tag",
    "value_stream_stages": "round-tag",
    "controls": "octagon",
    "policies": "cut-rectangle",
    "frameworks": "rectangle",
    "processes": "pentagon",
    "roadmaps": "round-octagon",
    "work_packages": "round-diamond",
    "architecture_change_requests": "diamond",
}

#: An offered interface's box, as `pillBox()` sizes it: the text measure of
#: any node with less padding, and round ends of this radius at most.
PILL_PAD_X = 20
PILL_PAD_Y = 8
PILL_RADIUS = 14

#: Edge kinds drawn with no head: an offered interface joined to the system
#: offering it is part of the system, not traffic to it.
HEADLESS = {"offers"}

#: Shapes with a corner to put a mark in.
CORNERED = {"round-rectangle", "rectangle", "round-tag", "tag", "cut-rectangle", "barrel"}

#: Cytoscape's unit polygons, as its renderer reports them: x, y pairs in
#: [-1, 1], scaled by half the node's width and height. Rectangles, barrels
#: and cut rectangles are drawn from their own geometry, not from these.
POLYGONS: Dict[str, Sequence[float]] = {
    "diamond": (0, 1, 1, 0, 0, -1, -1, 0),
    "round-diamond": (0, 1, 1, 0, 0, -1, -1, 0),
    "hexagon": (-0.5, -1, -1, 0, -0.5, 1, 0.5, 1, 1, 0, 0.5, -1),
    "octagon": (-0.41421356237309503, -1, -1, -0.41421356237309503, -1, 0.41421356237309503,
                -0.41421356237309503, 1, 0.41421356237309503, 1, 1, 0.41421356237309503,
                1, -0.41421356237309503, 0.41421356237309503, -1),
    "round-octagon": (-0.41421356237309503, -1, -1, -0.41421356237309503, -1, 0.41421356237309503,
                      -0.41421356237309503, 1, 0.41421356237309503, 1, 1, 0.41421356237309503,
                      1, -0.41421356237309503, 0.41421356237309503, -1),
    "pentagon": (0, -1, -1, -0.2360679774997897, -0.6180339887498949, 1,
                 0.6180339887498949, 1, 1, -0.2360679774997897),
    "rhomboid": (-1, -1, 0.333, -1, 1, 1, -0.333, 1),
    "tag": (-1, -1, 0.25, -1, 1, 0, 0.25, 1, -1, 1),
    "round-tag": (-1, -1, 0.25, -1, 1, 0, 0.25, 1, -1, 1),
    "triangle": (0, -1, -1, 1, 1, 1),
    "rectangle": (-1, -1, -1, 1, 1, 1, 1, -1),
}

#: One monochrome glyph per component category, 16x16, stroked.
GLYPH_PATHS: Dict[str, str] = {
    "Application": "M2 3.5h12v9H2z M2 6.5h12",
    "Compute": "M4.5 4.5h7v7h-7z M8 2v2.5 M8 11.5V14 M2 8h2.5 M11.5 8H14",
    "Data": "M8 3c3.3 0 5 .9 5 2s-1.7 2-5 2-5-.9-5-2 1.7-2 5-2z M3 5v6c0 1.1 1.7 2 5 2s5-.9 5-2V5",
    "Integration": "M2 5.5h9l-2.5-2.5 M14 10.5H5l2.5 2.5",
    "Network": "M8 3.5a1.5 1.5 0 1 0 0 .01 M3.5 12.5a1.5 1.5 0 1 0 0 .01 M12.5 12.5a1.5 1.5 0 1 0 0 .01 M8 5v3 M8 8l-4 3.5 M8 8l4 3.5",
    "Operations": "M2.5 11a5.5 5.5 0 0 1 11 0 M8 11l2.5-4",
    "Security": "M8 2l5 2v4c0 3-2.2 5.2-5 6-2.8-.8-5-3-5-6V4z",
    "Storage": "M2 5h12v6H2z M11 8h1",
    "AI": "M8 2.5l1.4 3.6L13 7.5l-3.6 1.4L8 12.5 6.6 8.9 3 7.5l3.6-1.4z M12.5 2v2 M11.5 3h2",
    "Enterprise": "M3 13.5V4.5l5-2 5 2v9 M6 7h1 M9 7h1 M6 9.5h1 M9 9.5h1 M7 13.5v-2h2v2",
}

#: The type's own mark, for the corner of a node with no provider mark and
#: no component glyph: Lucide's, 24x24, drawn in the node's stroke.
TYPE_ICON_BODIES: Dict[str, str] = {
    "systems": '<rect width="18" height="18" x="3" y="3" rx="2"/>',
    "products": '<path d="M11 21.73a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73z"/><path d="M12 22V12"/><polyline points="3.29 7 12 12 20.71 7"/><path d="m7.5 4.27 9 5.15"/>',
    "interfaces": '<path d="m16 3 4 4-4 4"/><path d="M20 7H4"/><path d="m8 21-4-4 4-4"/><path d="M4 17h16"/>',
    "data_assets": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5V19A9 3 0 0 0 21 19V5"/><path d="M3 12A9 3 0 0 0 21 12"/>',
    "tech_services": '<rect width="20" height="8" x="2" y="2" rx="2" ry="2"/><rect width="20" height="8" x="2" y="14" rx="2" ry="2"/><line x1="6" x2="6.01" y1="6" y2="6"/><line x1="6" x2="6.01" y1="18" y2="18"/>',
    "org_units": '<path d="M10 12h4"/><path d="M10 8h4"/><path d="M14 21v-3a2 2 0 0 0-4 0v3"/><path d="M6 10H4a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-2"/><path d="M6 21V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v16"/>',
    "policies": '<path d="M15 12h-5"/><path d="M15 8h-5"/><path d="M19 17V5a2 2 0 0 0-2-2H4"/><path d="M8 21h12a2 2 0 0 0 2-2v-1a1 1 0 0 0-1-1H11a1 1 0 0 0-1 1v1a2 2 0 1 1-4 0V5a2 2 0 1 0-4 0v2a1 1 0 0 0 1 1h3"/>',
    "frameworks": '<path d="M12 5v16"/><path d="M20.001 19A2 2 0 0022 17V5a2 2 0 00-1.999-2L16 3.002A5 5 0 0012 5a5 5 0 00-4-2H4a2 2 0 00-2 2v12a2 2 0 001.999 2H8a5 5 0 014 2 5 5 0 014-2z"/>',
    "value_streams": '<circle cx="6" cy="19" r="3"/><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/><circle cx="18" cy="5" r="3"/>',
    "value_stream_stages": '<path d="M12 13v8"/><path d="M12 3v3"/><path d="M18.172 6a2 2 0 0 1 1.414.586l2.06 2.06a1.207 1.207 0 0 1 0 1.708l-2.06 2.06a2 2 0 0 1-1.414.586H4a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1z"/>',
    "flows": '<circle cx="6" cy="19" r="3"/><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/><circle cx="18" cy="5" r="3"/>',
}

#: The legend's key for each shape, on a 20x14 tile: the on-screen legend's.
SHAPE_KEYS: Dict[str, str] = {
    "round-rectangle": '<rect x="1" y="1" width="18" height="12" rx="2.5"/>',
    "pill": '<rect x="1" y="2.5" width="18" height="9" rx="4.5"/>',
    "rectangle": '<rect x="1" y="1" width="18" height="12"/>',
    "round-tag": '<path d="M1 3a2 2 0 0 1 2-2h11l5 6-5 6H3a2 2 0 0 1-2-2z"/>',
    "hexagon": '<path d="M5 1h10l4 6-4 6H5L1 7z"/>',
    "barrel": '<path d="M3 1h14c1.5 0 2 1 2 2v8c0 1-.5 2-2 2H3c-1.5 0-2-1-2-2V3c0-1 .5-2 2-2z"/>',
    "rhomboid": '<path d="M5 1h14l-4 12H1z"/>',
    "tag": '<path d="M1 1h13l5 6-5 6H1z"/>',
    "ellipse": '<ellipse cx="10" cy="7" rx="9" ry="6"/>',
    "octagon": '<path d="M6 1h8l5 4v4l-5 4H6l-5-4V5z"/>',
    "cut-rectangle": '<path d="M4 1h12l3 3v6l-3 3H4l-3-3V4z"/>',
    "pentagon": '<path d="M10 1l9 5.5-3.5 6.5h-11L1 6.5z"/>',
    "round-octagon": '<path d="M6 1h8a5 5 0 0 1 5 4v4a5 5 0 0 1-5 4H6a5 5 0 0 1-5-4V5a5 5 0 0 1 5-4z"/>',
    "diamond": '<path d="M10 1l9 6-9 6-9-6z"/>',
    "round-diamond": '<path d="M8.5 1.6a2 2 0 0 1 3 0l6.9 4.6a1.2 1.2 0 0 1 0 1.6l-6.9 4.6a2 2 0 0 1-3 0L1.6 7.8a1.2 1.2 0 0 1 0-1.6z"/>',
}

#: Relation kinds said as words, the way the app's legend says them.
EDGE_WORDS: Dict[str, str] = {
    "interface": "calls", "system_uses_tech_service": "runs on", "sot": "masters",
    "tech_service_connects_to": "connects to", "owner": "owns",
    "system_realizes_capability": "realizes", "product_includes_system": "includes",
    "system_reads_writes": "reads / writes", "actor_uses_system": "uses",
    "policy_id": "gives effect to", "control_id": "governed by",
    "offers": "offers",
}

RELATION_PHRASES: Dict[str, str] = {
    "interfaces": "calls",
    "system_governed_by_control": "governed by",
    "system_subject_to_policy": "subject to",
    "data_governed_by_control": "governed by",
    "data_subject_to_policy": "subject to",
    "capability_governed_by_control": "governed by",
    "process_uses_system": "uses",
    "process_uses_data_asset": "uses",
    "process_supports_capability": "supports",
    "process_governed_by_control": "governed by",
    "process_subject_to_policy": "subject to",
    "stage_crosses_capability": "needs",
    "work_package_changes_system": "changes",
    "work_package_builds_system": "builds",
}


def edge_word(kind: str) -> str:
    if kind in EDGE_WORDS:
        return EDGE_WORDS[kind]
    if kind in RELATION_PHRASES:
        return RELATION_PHRASES[kind]
    text = str(kind or "")
    if text.endswith("_id"):
        text = text[:-3]
    return text.replace("_", " ")


def key_label(value: str) -> str:
    """A node with no value for the dimension is drawn plain and said plainly."""
    return "not recorded" if value == "default" else str(value).replace("_", " ")


def shape_of(entity_type: str) -> str:
    return SHAPES.get(entity_type, "round-rectangle")
