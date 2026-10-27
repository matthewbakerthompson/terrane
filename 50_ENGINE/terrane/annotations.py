"""What a diagram draws of its own: `annotations:` in its file.

A diagram drawn on the canvas holds three kinds of thing. A record is the
estate's, drawn as its type draws it; a view placed on it is a boundary;
and everything else -- shapes, text, notes, frames and free lines -- is the
diagram's own, kept in its file and never in the model. This module reads
that last list and says what is wrong with it; `terrane.draw.annotations`
draws it, as the app's `canvas/engine.js` does, from the same numbers.

Each item is a mapping:

    - {key: org, role: frame, label: AWS Organization, at: [20, 74], size: [792, 624]}
    - {key: guardrails, role: note, in: [org], at: [546, 492], size: [226, 70],
       label: "Guardrails: every account is denied the regions but eu-west-2",
       look: {fill: yellow}}
    - {key: line-1, role: line, from: TS-NET-VPC-LENDING, to: guardrails}

`key` names it and never changes, so renaming a frame orphans nothing;
`in` is the frames it sits in by key, outermost first, and `at` its corner
in the innermost of them, or on the sheet when it is in none. The sheet's
corner is where the drawing's positions start (`terrane.draw.arranged`), so
a note drawn beside a box stays beside it. A line's ends are each a record
on the drawing by id, a key of this list, or a point `[x, y]` on the sheet;
a straight line may bend at points of the sheet on its way, `via: [[x, y],
...]`, while a square or a curved one turns by itself. An end on a box may
be held at a point of its outline, `from_at` or `to_at: [across, down]`,
shares of the box from its top left corner.
A shape, a note or text may be turned about its middle, `rotate` degrees
clockwise; a frame is not, since what sits in it would turn too.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence

from .icons import is_mark, mark_file

#: What an item of the diagram's own is.
ROLES = ("shape", "text", "note", "frame", "line")

#: The shapes the canvas's Shapes menu draws, in its order.
SHAPES = ("rectangle", "rounded", "ellipse", "diamond", "hexagon", "cylinder", "cloud", "document", "person",
          "callout")

#: The fills a person picks from, in Illustrated, the look of the diagram's
#: own: the app's own picture language (the Diagrams page's pictures), every
#: one edged in ink. White is the pictures' paper, stone their mute, mint
#: their wash and accent their one strong color, which carries its words in
#: paper; a drawing has one thing it is about, and accent is for that.
FILLS = {
    "yellow": "#fbefc6", "mint": "#b7dad3", "lavender": "#dcd7f0", "rose": "#f2d2cb", "white": "#fffdf8",
    "stone": "#e1dacd", "accent": "#0f766e",
}
#: The words on a fill that is not light enough for ink.
WORDS_ON = {"accent": "#fffdf8"}
#: How heavy an edge is drawn, by a look's `weight`, in pixels: M when it
#: says nothing.
WEIGHTS = {"s": 1.0, "m": 1.25, "l": 2.0}
#: The most a look's own corners are rounded by, a radius in pixels.
MOST_CORNERS = 32
#: What a look says, in the order the file writes it (V16's Style tab).
LOOK_KEYS = ("fill", "line", "text", "icon", "opacity", "weight", "corners", "shadow")
#: What only a box with a fill and an edge has: a line and text have none.
BOX_LOOKS = ("opacity", "weight", "corners")

#: How a diagram draws its own (V16): Illustrated, the app's own picture
#: language, or Icon tiles, every shape a tile of its color with an icon and
#: its words under it, as the clouds draw their reference architectures. A
#: diagram says which under `look:` in its file, and is Illustrated when it
#: says nothing.
LOOKS = ("illustrated", "tiles")
DEFAULT_LOOK = "illustrated"
#: The icon a shape carries as a tile when it names none of its own:
#: `canvas/own-icons.js` has them all.
KIND_ICONS = {"rectangle": "box", "rounded": "box", "ellipse": "circle", "diamond": "diamond",
              "hexagon": "hexagon", "cylinder": "database", "cloud": "cloud", "document": "file-text",
              "person": "user", "callout": "message-square"}

#: An outline drawn solid, dashed or not at all; the words small, middling
#: or large, in pixels.
OUTLINES = ("solid", "dashed", "none")
TEXT_SIZES = {"s": 11, "m": 13, "l": 16}

#: A line's arrowheads: at its end, at both, or none.
ENDS = ("end", "both", "none")

#: How a line runs between its ends: straight; square, across or down the
#: middle of the gap between them and along to each; or curved through the
#: same turns (`terrane.draw.annotations.square`).
ROUTES = ("straight", "square", "curved")

_KEYS = {
    "line": {"key", "role", "label", "from", "to", "ends", "route", "look", "via", "from_at", "to_at"},
    "box": {"key", "role", "label", "in", "at", "size", "shape", "look", "rotate"},
}
#: What may be turned: a frame is not, since what sits in it would turn too.
TURNS = ("shape", "note", "text")


class AnnotationError(ValueError):
    """Something in a diagram's `annotations` that cannot be drawn."""


def _pair(value: Any) -> bool:
    return (isinstance(value, (list, tuple)) and len(value) == 2
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value))


def read(raw: Any, where: str) -> List[Dict[str, Any]]:
    """The list as the file has it, checked: every item a mapping of what an
    item has, each key once, every frame it sits in one of the list's
    frames, every end a record id, a key or a point. Refused with the first
    thing wrong, said as a person would fix it."""
    if raw in (None, "", []):
        return []
    if not isinstance(raw, list):
        raise AnnotationError("%s is a list of what the diagram draws of its own" % where)
    seen: Dict[str, str] = {}
    out: List[Dict[str, Any]] = []
    for i, item in enumerate(raw):
        at = "%s item %d" % (where, i + 1)
        if not isinstance(item, dict):
            raise AnnotationError("%s is not a mapping" % at)
        key = str(item.get("key") or "").strip()
        if not key:
            raise AnnotationError("%s has no key" % at)
        at = "%s: %s" % (where, key)
        if key in seen:
            raise AnnotationError("%s is the key of two items" % at)
        role = item.get("role")
        if role not in ROLES:
            raise AnnotationError("%s has role %r; it is one of %s" % (at, role, ", ".join(ROLES)))
        allowed = _KEYS["line" if role == "line" else "box"]
        extra = sorted(set(item) - allowed)
        if extra:
            raise AnnotationError("%s has %s, which %s does not" % (at, ", ".join(extra), "a line" if role == "line"
                                                                     else "a " + role))
        if "label" in item and not isinstance(item["label"], (str, int, float)):
            raise AnnotationError("%s: label is words" % at)
        if role == "line":
            for end in ("from", "to"):
                v = item.get(end)
                if not (_pair(v) or (isinstance(v, str) and v.strip())):
                    raise AnnotationError("%s: %s is a record's id, a key of this list, or a point [x, y]" % (at, end))
            if item.get("ends", "end") not in ENDS:
                raise AnnotationError("%s: ends is one of %s" % (at, ", ".join(ENDS)))
            if item.get("route", "straight") not in ROUTES:
                raise AnnotationError("%s: route is one of %s" % (at, ", ".join(ROUTES)))
            for end, held in (("from", "from_at"), ("to", "to_at")):
                if held not in item:
                    continue
                v = item[held]
                if not _pair(v) or not all(0 <= x <= 1 for x in v):
                    raise AnnotationError("%s: %s is where on its box the end is held, [across, down], each from "
                                          "0 to 1" % (at, held))
                if not isinstance(item.get(end), str):
                    raise AnnotationError("%s: %s holds an end on a box, and %s is a point" % (at, held, end))
            if "via" in item:
                via = item["via"]
                if not isinstance(via, list) or not via or not all(_pair(p) for p in via):
                    raise AnnotationError("%s: via is the points it bends at, [[x, y], ...]" % at)
                if item.get("route", "straight") != "straight":
                    raise AnnotationError("%s: a %s line turns by itself; via is for a straight one" % (
                        at, item.get("route")))
        else:
            if not _pair(item.get("at")):
                raise AnnotationError("%s: at is its corner, [x, y]" % at)
            size = item.get("size")
            if not _pair(size) or size[0] <= 0 or size[1] <= 0:
                raise AnnotationError("%s: size is [width, height], both more than nought" % at)
            if role == "shape" and item.get("shape", "rectangle") not in SHAPES:
                raise AnnotationError("%s: shape is one of %s" % (at, ", ".join(SHAPES)))
            inside = item.get("in", [])
            if not isinstance(inside, list) or not all(isinstance(k, str) for k in inside):
                raise AnnotationError("%s: in is the keys of the frames it sits in, outermost first" % at)
            if "rotate" in item:
                turn = item["rotate"]
                if role not in TURNS:
                    raise AnnotationError("%s: a %s is not turned, since what sits in it would turn too" % (at, role))
                if isinstance(turn, bool) or not isinstance(turn, (int, float)) or not -360 < turn < 360:
                    raise AnnotationError("%s: rotate is degrees clockwise about its middle, more than -360 "
                                          "and less than 360" % at)
        look = item.get("look", {})
        if not isinstance(look, dict):
            raise AnnotationError("%s: look is a mapping of %s" % (at, ", ".join(LOOK_KEYS)))
        wrong = sorted(set(look) - set(LOOK_KEYS))
        if wrong:
            raise AnnotationError("%s: look has %s; it has %s" % (at, ", ".join(wrong), ", ".join(LOOK_KEYS)))
        if role in ("line", "text"):
            boxed = [k for k in BOX_LOOKS + ("shadow",) if k in look]
            if boxed:
                raise AnnotationError("%s: look has %s, which a %s does not have" % (at, ", ".join(boxed), role))
        if "shadow" in look and role not in ("shape", "note"):
            raise AnnotationError("%s: look has shadow, which a %s does not cast" % (at, role))
        if "opacity" in look and (isinstance(look["opacity"], bool) or not isinstance(look["opacity"], int)
                                  or not 10 <= look["opacity"] <= 100):
            raise AnnotationError("%s: look.opacity is how much of its fill shows, a whole percent from 10 to 100" % at)
        if "weight" in look and look["weight"] not in WEIGHTS:
            raise AnnotationError("%s: look.weight is how heavy its edge is, one of %s" % (at, ", ".join(WEIGHTS)))
        if "corners" in look and (isinstance(look["corners"], bool) or not isinstance(look["corners"], (int, float))
                                  or not 0 <= look["corners"] <= MOST_CORNERS):
            raise AnnotationError("%s: look.corners is the radius its corners are rounded by, from 0 to %d"
                                  % (at, MOST_CORNERS))
        if "shadow" in look and look["shadow"] != "none":
            raise AnnotationError("%s: look.shadow is none, or left out for the shadow its kind casts" % at)
        if "icon" in look and not (isinstance(look["icon"], str) and (re.fullmatch(r"[a-z0-9-]+", look["icon"])
                                                                       or is_mark(look["icon"]))):
            raise AnnotationError("%s: look.icon is the name of an icon, or a provider's mark as aws/lambda, as the "
                                  "canvas's picker names one" % at)
        if is_mark(look.get("icon")) and mark_file(look["icon"]) is None:
            raise AnnotationError("%s: look.icon names %s, which is no mark the app ships" % (at, look["icon"]))
        if "fill" in look and look["fill"] not in FILLS:
            raise AnnotationError("%s: look.fill is one of %s" % (at, ", ".join(FILLS)))
        if "line" in look and look["line"] not in OUTLINES:
            raise AnnotationError("%s: look.line is one of %s" % (at, ", ".join(OUTLINES)))
        if "text" in look and look["text"] not in TEXT_SIZES:
            raise AnnotationError("%s: look.text is one of %s" % (at, ", ".join(TEXT_SIZES)))
        seen[key] = role
        out.append(dict(item, key=key))
    for item in out:
        for frame in item.get("in", []):
            if seen.get(frame) != "frame":
                raise AnnotationError("%s: %s is in %s, which is not a frame of this diagram"
                                      % (where, item["key"], frame))
    return out


def frames_of(items: Sequence[Dict[str, Any]]) -> List[str]:
    """The keys of the frames, in the list's order."""
    return [str(a["key"]) for a in items if a.get("role") == "frame"]
