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
on the drawing by id, a key of this list, or a point `[x, y]` on the sheet.
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

#: What an item of the diagram's own is.
ROLES = ("shape", "text", "note", "frame", "line")

#: The shapes the canvas's Shapes menu draws, in its order.
SHAPES = ("rectangle", "rounded", "ellipse", "diamond", "hexagon", "cylinder", "cloud", "document", "person",
          "callout")

#: The six fills a person picks from, each with the edge it is drawn with.
FILLS = {
    "yellow": ("#fdf0b8", "#d9bd4f"), "mint": ("#d9efe5", "#6fae92"), "lavender": ("#e7e3f7", "#9289c9"),
    "rose": ("#f9e1dc", "#d48f84"), "white": ("#ffffff", "#a39c8d"), "stone": ("#ece7dd", "#a39c8d"),
}

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
    "line": {"key", "role", "label", "from", "to", "ends", "route", "look"},
    "box": {"key", "role", "label", "in", "at", "size", "shape", "look"},
}


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
        look = item.get("look", {})
        if not isinstance(look, dict):
            raise AnnotationError("%s: look is a mapping of fill, line and text" % at)
        wrong = sorted(set(look) - {"fill", "line", "text"})
        if wrong:
            raise AnnotationError("%s: look has %s; it has fill, line and text" % (at, ", ".join(wrong)))
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
