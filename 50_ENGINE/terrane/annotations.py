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
...]`, while a square or a curved one turns by itself, or keeps the turns in
its `via` where its stretches were moved by hand. An end on a box may
be held at a point of its outline, `from_at` or `to_at: [across, down]`,
shares of the box from its top left corner.
A shape, a note or text may be turned about its middle, `rotate` degrees
clockwise; a frame is not, since what sits in it would turn too.

A swimlane (V16) is a pool and its lanes. The pool is a box with its name
in a band across its top, its lanes stacked across it (`runs: across`, the
default) or side by side down it (`runs: down`), each lane's name in a
column at its left (`names: left`) or a band at its top (`names: top`).
Each lane sits in the pool, `in` ending with the pool's key, and what is
drawn in a lane sits in it as in a frame, never in the pool itself. A lane
may stand for a record, `stands_for` an actor's or an org unit's id: its
name is then the record's, and the record's page lists the diagram.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence

from .icons import is_mark, mark_file

#: What an item of the diagram's own is.
ROLES = ("shape", "text", "note", "frame", "line", "pool", "lane")
#: What holds what sits in it, by `in`: a frame, a swimlane's pool, a lane.
CONTAINERS = ("frame", "pool", "lane")
#: A swimlane's lanes stacked across it, or side by side down it; and each
#: lane's name in a column at its left, or a band at its top.
RUNS = ("across", "down")
NAMES = ("left", "top")

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
LOOK_KEYS = ("fill", "line", "text", "icon", "opacity", "weight", "corners", "shadow",
             "bold", "italic", "underline", "strike", "align", "list")
#: A link's address: on the web or for email (V16's words toolbar, its last
#: button), the canvas's LINK in canvas/canvas.js.
LINK = re.compile(r"(https?://|mailto:)\S+")
#: How the words are set, all of them (V16's words toolbar): bold, italic,
#: underlined, struck through, and a note's or text's lines as a list. Each
#: is `true`, or left out.
WORD_LOOKS = ("bold", "italic", "underline", "strike", "list")
#: Where the words sit across their box: a shape's in the middle and the
#: rest's at the left when the look says nothing.
ALIGNS = ("left", "center", "right")
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
OUTLINES = ("solid", "dashed", "dotted", "none")
#: How heavy a line is drawn, by its look's `weight`, in pixels: M when it
#: says nothing, as every line was.
LINE_WEIGHTS = {"s": 1.0, "m": 1.5, "l": 2.5}
#: A square line's turns: sharp, or rounded as maxGraph rounds them.
LINE_TURNS = ("sharp", "rounded")
#: What a line says at its start and its end, beside its middle's `label`.
LABEL_PLACES = ("start", "end")
TEXT_SIZES = {"s": 11, "m": 13, "l": 16}

#: A line's arrowheads: at its end, at both, or none.
ENDS = ("end", "both", "none")
#: The head an end of a line may have (V16), in the order its panel offers
#: them: plain ones, UML's, crow's foot's and ArchiMate's. `heads` says one
#: for each end, in place of `ends`.
HEADS = ("none", "arrow", "open-arrow", "dot",
         "inherits", "made-of", "has", "depends-on",
         "one", "many", "one-or-many", "none-or-one", "none-or-many",
         "serving", "triggering", "flow", "realization", "assignment", "access")

#: How a line runs between its ends: straight; square, across or down the
#: middle of the gap between them and along to each; or curved through the
#: same turns (`terrane.draw.annotations.square`).
ROUTES = ("straight", "square", "curved")

_KEYS = {
    "line": {"key", "role", "label", "from", "to", "ends", "route", "look", "via", "from_at", "to_at", "layer",
             "labels", "turns", "heads"},
    "box": {"key", "role", "label", "in", "at", "size", "shape", "look", "rotate", "link", "group", "layer"},
}
#: What a swimlane's pool and lanes have beside a box's own.
_ROLE_KEYS = {"pool": {"runs", "names"}, "lane": {"stands_for"}}
#: What may be turned: a frame is not, since what sits in it would turn too.
TURNS = ("shape", "note", "text")


class AnnotationError(ValueError):
    """Something in a diagram's `annotations` that cannot be drawn."""


def _pair(value: Any) -> bool:
    return (isinstance(value, (list, tuple)) and len(value) == 2
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value))


def heads_of(item: Mapping) -> Tuple[str, str]:
    """A line's heads at its start and its end: its `heads`, an end they do
    not name having none; or else its `ends`, an arrow at its end, at both
    or at neither."""
    heads = item.get("heads")
    if isinstance(heads, dict):
        return str(heads.get("start") or "none"), str(heads.get("end") or "none")
    ends = str(item.get("ends") or "end")
    return ("arrow" if ends == "both" else "none"), ("none" if ends == "none" else "arrow")


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
        allowed = _KEYS["line" if role == "line" else "box"] | _ROLE_KEYS.get(role, set())
        extra = sorted(set(item) - allowed)
        if extra:
            raise AnnotationError("%s has %s, which %s does not" % (at, ", ".join(extra), "a line" if role == "line"
                                                                     else "a " + role))
        if "label" in item and not isinstance(item["label"], (str, int, float)):
            raise AnnotationError("%s: label is words" % at)
        # The drawing layer it is on, by its key in the diagram's `layers:`
        # (the view checks that it names one).
        if "layer" in item and not (isinstance(item["layer"], str) and item["layer"].strip()):
            raise AnnotationError("%s: layer is the key of one of the diagram's drawing layers" % at)
        if role == "line":
            for end in ("from", "to"):
                v = item.get(end)
                if not (_pair(v) or (isinstance(v, str) and v.strip())):
                    raise AnnotationError("%s: %s is a record's id, a key of this list, or a point [x, y]" % (at, end))
            if item.get("ends", "end") not in ENDS:
                raise AnnotationError("%s: ends is one of %s" % (at, ", ".join(ENDS)))
            # A head at each end (V16), said in place of its ends.
            if "heads" in item:
                heads = item["heads"]
                if (not isinstance(heads, dict) or not heads or set(heads) - {"start", "end"}
                        or not all(v in HEADS for v in heads.values())):
                    raise AnnotationError("%s: heads is the head at its start and at its end, {start: ..., end: ...}, "
                                          "each one of %s" % (at, ", ".join(HEADS)))
                if "ends" in item:
                    raise AnnotationError("%s: a line says its heads by heads or by ends, not both" % at)
            if item.get("route", "straight") not in ROUTES:
                raise AnnotationError("%s: route is one of %s" % (at, ", ".join(ROUTES)))
            if item.get("turns", "sharp") not in LINE_TURNS:
                raise AnnotationError("%s: turns is %s" % (at, " or ".join(LINE_TURNS)))
            # Its words at its start and its end (V16); its middle's are its label.
            if "labels" in item:
                labels = item["labels"]
                if (not isinstance(labels, dict) or not labels or set(labels) - set(LABEL_PLACES)
                        or not all(isinstance(v, str) and v.strip() and len(v) <= 120 for v in labels.values())):
                    raise AnnotationError("%s: labels is its words at its start and its end, {start: ..., end: ...}, "
                                          "each up to 120 characters; its middle's are its label" % at)
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
            if role == "pool" and item.get("runs", "across") not in RUNS:
                raise AnnotationError("%s: runs is %s" % (at, " or ".join(RUNS)))
            if role == "pool" and item.get("names", "left") not in NAMES:
                raise AnnotationError("%s: names is where each lane's name sits, %s" % (at, " or ".join(NAMES)))
            if "stands_for" in item and not (isinstance(item["stands_for"], str) and item["stands_for"].strip()):
                raise AnnotationError("%s: stands_for is the id of the record the lane stands for" % at)
            # The group it is picked and moved with, by its key in the
            # diagram's `groups:` (the view checks that it names one).
            if "group" in item and not (isinstance(item["group"], str) and item["group"].strip()):
                raise AnnotationError("%s: group is the key of one of the diagram's groups" % at)
            # Where it links to: an address on the web or for email, and no
            # other kind, so no file can carry a script to run on a click.
            if "link" in item and not (isinstance(item["link"], str) and len(item["link"]) <= 2000
                                       and LINK.fullmatch(item["link"])):
                raise AnnotationError("%s: link is an address on the web or for email, starting https://, "
                                      "http:// or mailto:" % at)
        check_look(item.get("look", {}), at, role)
        seen[key] = role
        out.append(dict(item, key=key))
    for item in out:
        inside = item.get("in", [])
        for frame in inside:
            if seen.get(frame) not in CONTAINERS:
                raise AnnotationError("%s: %s is in %s, which is not a frame, a swimlane or a lane of this diagram"
                                      % (where, item["key"], frame))
        # A lane sits in its pool, and what is drawn in a swimlane in one of
        # its lanes: the pool itself holds only them.
        holder = seen.get(inside[-1]) if inside else None
        if item["role"] == "lane" and holder != "pool":
            raise AnnotationError("%s: %s is a lane, and sits in a swimlane: in ends with the swimlane's key"
                                  % (where, item["key"]))
        if item["role"] != "lane" and holder == "pool":
            raise AnnotationError("%s: %s sits in the swimlane %s itself; what is drawn in a swimlane sits in one "
                                  "of its lanes" % (where, item["key"], inside[-1]))
    return out


def check_look(look: Any, at: str, role: Any = None) -> None:
    """What a look may say, and for a role what that kind can take; a saved
    style, which no one kind wears, is checked with no role."""
    if not isinstance(look, dict):
        raise AnnotationError("%s: look is a mapping of %s" % (at, ", ".join(LOOK_KEYS)))
    wrong = sorted(set(look) - set(LOOK_KEYS))
    if wrong:
        raise AnnotationError("%s: look has %s; it has %s" % (at, ", ".join(wrong), ", ".join(LOOK_KEYS)))
    # A line has how heavy it is drawn, and no fill to show or corners.
    if role in ("line", "text"):
        boxed = [k for k in (("opacity", "corners") if role == "line" else BOX_LOOKS) + ("shadow",) if k in look]
        if boxed:
            raise AnnotationError("%s: look has %s, which a %s does not have" % (at, ", ".join(boxed), role))
    # A swimlane is drawn as the canvas draws one; its words' size is all
    # its look has.
    if role in ("pool", "lane"):
        drawn = sorted(set(look) - {"text"})
        if drawn:
            raise AnnotationError("%s: look has %s, which a swimlane's %s does not take; it has text" % (
                at, ", ".join(drawn), role))
    if "shadow" in look and role is not None and role not in ("shape", "note"):
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
    # How the words are set (V16's words toolbar), for all of them.
    if role == "line":
        worded = [k for k in WORD_LOOKS + ("align",) if k in look]
        if worded:
            raise AnnotationError("%s: look has %s, which a line's words do not take" % (at, ", ".join(worded)))
    if role == "frame":
        named = [k for k in ("bold", "align", "list") if k in look]
        if named:
            raise AnnotationError("%s: look has %s, which a frame's name on its tab does not take: it is bold "
                                  "already, at its left, on one line" % (at, ", ".join(named)))
    if "list" in look and role == "shape":
        raise AnnotationError("%s: look has list, which a note's or text's words take, not a shape's" % at)
    for k in WORD_LOOKS:
        if k in look and look[k] is not True:
            raise AnnotationError("%s: look.%s is true, or left out" % (at, k))
    if "align" in look and look["align"] not in ALIGNS:
        raise AnnotationError("%s: look.align is one of %s" % (at, ", ".join(ALIGNS)))


def read_styles(raw: Any, where: str) -> tuple:
    """Looks kept by name (V16's saved styles), a diagram's or the
    estate's: each a name of up to 40 characters and a look, checked as a
    look is; an icon says what a shape is, not how it looks, and is no part
    of one."""
    if raw in (None, []):
        return ()
    if not isinstance(raw, list):
        raise AnnotationError("%s is a list, each a name and a look" % where)
    out, seen = [], set()
    for i, style in enumerate(raw):
        name = style.get("name") if isinstance(style, dict) else None
        if (not isinstance(style, dict) or set(style) - {"name", "look"} or not isinstance(name, str)
                or not name.strip() or len(name.strip()) > 40):
            raise AnnotationError("%s: the %d. is a name of up to 40 characters and a look" % (where, i + 1))
        name = name.strip()
        if name.lower() in seen:
            raise AnnotationError("%s: %s is the name of two" % (where, name))
        seen.add(name.lower())
        look = style.get("look") or {}
        if isinstance(look, dict) and "icon" in look:
            raise AnnotationError("%s: %s has an icon, which says what a shape is, not how it looks" % (where, name))
        check_look(look, "%s: %s" % (where, name))
        out.append({"name": name, "look": dict(look)})
    return tuple(out)


def estate_styles(config: Any) -> tuple:
    """The looks every diagram of the estate offers by name: `saved_styles`
    in model.yaml, saved from a shape's Style tab for every diagram."""
    return read_styles((config or {}).get("saved_styles"), "model.yaml: saved_styles")


def follow_names(items: List[Dict[str, Any]], model: Any) -> List[Dict[str, Any]]:
    """Each lane that stands for a record named as the record is now: its
    label in the file is what it was called when it was chosen, kept for a
    record that is gone."""
    for item in items:
        if item.get("role") == "lane" and item.get("stands_for"):
            found = model.find(str(item["stands_for"]))
            if found is not None and found[1].get("name"):
                item["label"] = str(found[1]["name"])
    return items


#: Where the estate's records sit among a diagram's drawing layers: an
#: entry of `layers:` with this key and no name.
ESTATE_LAYER = "estate"


def layer_home(layers: Sequence[Dict[str, Any]]) -> str:
    """The drawing layer what names none is on: the one just above the
    estate's records, where the canvas has always drawn its own, else the
    top one."""
    keys = [str(layer["key"]) for layer in layers]
    at = keys.index(ESTATE_LAYER) if ESTATE_LAYER in keys else len(keys)
    drawing = [k for k in keys if k != ESTATE_LAYER]
    return keys[at - 1] if at > 0 else drawing[0]


def by_layer(items: List[Dict[str, Any]], layers: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The diagram's own as its drawing layers draw it (V16): a hidden
    layer's left out, and what sits in one of them with it; the rest bottom
    layer first, in the list's order within a layer; and what is on a layer
    under the estate's records marked `_under`, to be drawn under them. What
    sits in a frame or a swimlane goes by the layer of the outermost thing
    it sits in, as the canvas moves it."""
    if not layers:
        return items
    keys = [str(layer["key"]) for layer in layers]
    if ESTATE_LAYER not in keys:
        keys.append(ESTATE_LAYER)
    rank = {k: i for i, k in enumerate(keys)}
    hidden = {str(layer["key"]) for layer in layers if layer.get("hidden")}
    home = layer_home(layers)
    by_key = {str(i.get("key")): i for i in items}

    def layer_of(item: Dict[str, Any]) -> str:
        inside = list(item.get("in") or [])
        top = by_key.get(str(inside[0]), item) if inside else item
        named = top.get("layer")
        return str(named) if named in rank and named != ESTATE_LAYER else home

    kept = [dict(item) for item in items if layer_of(item) not in hidden]
    kept.sort(key=lambda item: -rank[layer_of(item)])
    for item in kept:
        if rank[layer_of(item)] > rank[ESTATE_LAYER]:
            item["_under"] = True
    return kept


def frames_of(items: Sequence[Dict[str, Any]]) -> List[str]:
    """The keys of the frames, in the list's order."""
    return [str(a["key"]) for a in items if a.get("role") == "frame"]
