"""The drawing as PowerPoint shapes, so a reviewer can move a box.

The review pack puts a picture on each slide, exact and fixed. The slide
most reviewers ask for next is the one they can edit: a box they can move
to make room for a comment, a name they can correct, a line that follows
the box. This paints the painter's `Scene` (`svg.py`) as DrawingML: every
boundary a rounded rectangle with its name in the corner, every node a
custom shape of the same outline the SVG drew, in the same fill and ink,
with four connection sites, top, left, bottom and right; every edge a
connector glued to the sites it left from and arrived at, one of
PowerPoint's own presets set to the route the router laid down, with its
arrow head and its label card. The sheet's inches come from the drawing's
pixels at the scale that fits the slide's picture box, so the shapes
stand where the picture would. What the diagram draws of its own on the
canvas is there too, stacked as the canvas stacks it: a frame, note, text
or shape of the same outline and fill as the picture's, and a line a path
through its turns with its heads.

What stays on the picture: the provider marks and type glyphs in a node's
corner (a mark is an SVG file, which a slide cannot hold), the legend and
the title block (the slide has its own), the rounding of a line's corners,
and the fan of a bundle on a packed map, whose curves a preset cannot
take and which go straight. A tile map is the app's HTML and has no
scene; its slide keeps the picture.

PowerPoint refuses a connector with a geometry of its own (the first cut
drew each route as a custom path and the file would not open), so an
edge is a straight connector or a bent one of up to five runs, placed by
its rotation, its flips and its adjustments (`connector`). It sizes a
shape's own coordinate space by its `path`, so a node's path is the shape
at a thousand units a pixel and its connection sites are guides of half
its width and height. Angles are in sixty-thousandths of a degree,
clockwise.
"""

from __future__ import annotations

import math
from typing import Callable, List, Sequence, Tuple
from xml.sax.saxutils import escape

from . import annotations as own_module
from .annotations import Own
from .shapes import HEADLESS, PILL_RADIUS
from .svg import (EDGE, INK_SOFT, Box, Point, Scene, SceneEdge, SceneNode, polygon_points, round_polygon_radius,
                  round_rect_radius)

EMU = 914400
#: A node's path is drawn at this many units a pixel.
K = 1000
CD4, CD2, CD3Q = 5400000, 10800000, 16200000
#: The four connection sites of every node: top, left, bottom, right, in
#: that order, so a connector's `idx` says which side it is glued to.
GUIDES = '<a:gdLst><a:gd name="cx" fmla="*/ w 1 2"/><a:gd name="cy" fmla="*/ h 1 2"/></a:gdLst>'
SITES = ('<a:cxnLst><a:cxn ang="16200000"><a:pos x="cx" y="0"/></a:cxn><a:cxn ang="10800000"><a:pos x="0" y="cy"/>'
         '</a:cxn><a:cxn ang="5400000"><a:pos x="cx" y="h"/></a:cxn><a:cxn ang="0"><a:pos x="w" y="cy"/></a:cxn>'
         '</a:cxnLst>')
TOP, LEFT, BOTTOM, RIGHT = 0, 1, 2, 3
FONT = "Calibri"
LABEL_FILL, LABEL_LINE, LABEL_INK = "FFFFFF", "CDD5E1", "3F4A5C"
#: The thinnest line a slide draws: half a point.
HAIRLINE = 6350


def _hex(color: str, fallback: str) -> str:
    text = str(color or "").strip().lstrip("#")
    if len(text) == 3:
        text = "".join(c * 2 for c in text)
    try:
        int(text, 16)
    except ValueError:
        return fallback
    return text.upper() if len(text) == 6 else fallback


def _color(color: str, fallback: str, alpha: float = 1.0) -> str:
    inner = '<a:alpha val="%d"/>' % int(round(alpha * 100000)) if alpha < 1 else ""
    return '<a:solidFill><a:srgbClr val="%s">%s</a:srgbClr></a:solidFill>' % (_hex(color, fallback), inner)


def _dash(style: str) -> str:
    if style == "dashed":
        return '<a:prstDash val="dash"/>'
    if style == "dotted":
        return '<a:prstDash val="sysDot"/>'
    return ""


def _pt(x: float, y: float) -> str:
    return '<a:pt x="%d" y="%d"/>' % (int(round(x)), int(round(y)))


def _move(x: float, y: float) -> str:
    return "<a:moveTo>%s</a:moveTo>" % _pt(x, y)


def _line(x: float, y: float) -> str:
    return "<a:lnTo>%s</a:lnTo>" % _pt(x, y)


def _quad(cx: float, cy: float, x: float, y: float) -> str:
    return "<a:quadBezTo>%s%s</a:quadBezTo>" % (_pt(cx, cy), _pt(x, y))


def _arc(wr: float, hr: float, start: int, sweep: int) -> str:
    return '<a:arcTo wR="%d" hR="%d" stAng="%d" swAng="%d"/>' % (int(round(wr)), int(round(hr)), start, sweep)


def node_path(shape: str, w: float, h: float) -> str:
    """The node's outline as a DrawingML path, for a node `w` by `h`
    pixels: the same shapes `shape_path` draws, corner for corner, in a
    space of a thousand units a pixel. The outline is worked out in pixels
    first, since a corner's cut and a curve's radius are fixed pixel
    sizes; the first cut was taken in path units and came out a thousandth
    of a pixel wide, a square corner."""
    pts: List[Point]
    if shape in ("round-rectangle", "pill"):
        r = min(PILL_RADIUS, w / 2, h / 2) if shape == "pill" else round_rect_radius(w, h)
        pts = [(r, 0), (w - r, 0), (w, h - r), (r, h), (0, r)]
        parts = [_move(r * K, 0), _line((w - r) * K, 0), _arc(r * K, r * K, CD3Q, CD4), _line(w * K, (h - r) * K),
                 _arc(r * K, r * K, 0, CD4), _line(r * K, h * K), _arc(r * K, r * K, CD4, CD4), _line(0, r * K),
                 _arc(r * K, r * K, CD2, CD4)]
    elif shape == "rectangle":
        parts = [_move(0, 0), _line(w * K, 0), _line(w * K, h * K), _line(0, h * K)]
    elif shape == "ellipse":
        parts = [_move(0, h * K / 2), _arc(w * K / 2, h * K / 2, CD2, CD2), _arc(w * K / 2, h * K / 2, 0, CD2)]
    elif shape == "barrel":
        # Cytoscape's barrel, as `barrel_path` has it: the top and bottom
        # edges curve down into the sides.
        h_off, w_off, f = min(15, 0.05 * h), min(100, 0.25 * w), 0.05 * w
        steps = [(0, h_off), (f, 0, w_off, 0), (w - w_off, 0), (w - f, 0, w, h_off), (w, h - h_off),
                 (w - f, h, w - w_off, h), (w_off, h), (f, h, 0, h - h_off)]
        parts = []
        for i, step in enumerate(steps):
            if len(step) == 2:
                parts.append((_move if i == 0 else _line)(step[0] * K, step[1] * K))
            else:
                parts.append(_quad(step[0] * K, step[1] * K, step[2] * K, step[3] * K))
    else:
        pts = polygon_points(shape, w / 2, h / 2, w, h)
        if shape.startswith("round-"):
            radius = round_polygon_radius(w, h)
            parts = []
            n = len(pts)
            for i in range(n):
                p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
                d1 = math.hypot(p1[0] - p0[0], p1[1] - p0[1]) or 1
                d2 = math.hypot(p2[0] - p1[0], p2[1] - p1[1]) or 1
                r = min(radius, d1 / 2, d2 / 2)
                a = (p1[0] - (p1[0] - p0[0]) / d1 * r, p1[1] - (p1[1] - p0[1]) / d1 * r)
                b = (p1[0] + (p2[0] - p1[0]) / d2 * r, p1[1] + (p2[1] - p1[1]) / d2 * r)
                parts.append((_move if i == 0 else _line)(a[0] * K, a[1] * K))
                parts.append(_quad(p1[0] * K, p1[1] * K, b[0] * K, b[1] * K))
        else:
            parts = [(_move if i == 0 else _line)(x * K, y * K) for i, (x, y) in enumerate(pts)]
    return '<a:path w="%d" h="%d">%s<a:close/></a:path>' % (int(round(w * K)), int(round(h * K)), "".join(parts))


def site(node: SceneNode, at: Point) -> int:
    """Which side of the node a point near its border is on."""
    dx = (at[0] - node.x) / (node.w / 2 or 1)
    dy = (at[1] - node.y) / (node.h / 2 or 1)
    if abs(dy) >= abs(dx):
        return TOP if dy < 0 else BOTTOM
    return LEFT if dx < 0 else RIGHT


class _Sheet:
    """Pixels of the drawing to EMUs on the slide: the drawing's extent fit
    into the box, kept in aspect and centered, as the picture is."""

    def __init__(self, extent: Box, box: Box) -> None:
        dx1, dy1, dx2, dy2 = extent
        dw, dh = max(dx2 - dx1, 1.0), max(dy2 - dy1, 1.0)
        bx, by, bw, bh = box
        self.scale = min(bw / dw, bh / dh)  # inches a pixel
        self.ox = bx + (bw - dw * self.scale) / 2 - dx1 * self.scale
        self.oy = by + (bh - dh * self.scale) / 2 - dy1 * self.scale

    def x(self, px: float) -> int:
        return int(round((self.ox + px * self.scale) * EMU))

    def y(self, px: float) -> int:
        return int(round((self.oy + px * self.scale) * EMU))

    def size(self, px: float) -> int:
        return max(1, int(round(px * self.scale * EMU)))

    def extent(self, px: float) -> int:
        """A length that may be nothing: a straight connector's box is as
        thin as its line is straight."""
        return max(0, int(round(px * self.scale * EMU)))

    def line(self, px: float) -> int:
        return max(HAIRLINE, self.size(px))

    def font(self, px: float) -> int:
        """A text size in hundredths of a point, never under a point."""
        return max(100, int(round(px * self.scale * 72 * 100)))


def _run(text: str, size: int, color: str, bold: bool, face: str = FONT) -> str:
    return ('<a:r><a:rPr lang="en-US" sz="%d"%s dirty="0">%s<a:latin typeface="%s"/></a:rPr><a:t>%s</a:t></a:r>'
            % (size, ' b="1"' if bold else "", _color(color, "0F172A"), face, escape(text)))


#: A hard shadow, as the app's pictures cast one under a shape or a note:
#: ink, unblurred, down and right, so its distance is the diagonal of the
#: offset (a square root, the one call the painter's rule allows).
def _hard_shadow(sheet: "_Sheet") -> str:
    return ('<a:effectLst><a:outerShdw blurRad="0" dist="%d" dir="2700000" algn="tl" rotWithShape="0">'
            '<a:srgbClr val="%s"/></a:outerShdw></a:effectLst>'
            % (sheet.size(math.sqrt(2 * own_module.SHADOW * own_module.SHADOW)), _hex(own_module.INK, "2E2A25")))


def _paragraph(runs: str, align: str) -> str:
    return '<a:p><a:pPr algn="%s"/>%s</a:p>' % (align, runs)


def _boundary_xml(shape_id: int, b, sheet: _Sheet) -> str:
    x1, y1, x2, y2 = b.box
    w, h = x2 - x1, y2 - y1
    radius = round_rect_radius(w, h)
    adj = int(round(radius / max(min(w, h), 1) * 100000))
    text = " ".join(b.lines)
    return ('<p:sp><p:nvSpPr><p:cNvPr id="%d" name="%s"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            '<p:spPr><a:xfrm><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
            '<a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val %d"/></a:avLst></a:prstGeom>'
            '%s<a:ln w="%d">%s%s</a:ln></p:spPr>'
            '<p:txBody><a:bodyPr wrap="square" lIns="%d" tIns="%d" rIns="%d" bIns="0" anchor="t"/><a:lstStyle/>%s'
            '</p:txBody></p:sp>'
            % (shape_id, escape("Boundary %s" % b.id), sheet.x(x1), sheet.y(y1), sheet.size(w), sheet.size(h), adj,
               _color(b.fill, "F3F5FB"), sheet.line(b.width), _color(b.stroke, "8F9BB5"), _dash(b.dash),
               sheet.size(12), sheet.size(6), sheet.size(6),
               _paragraph(_run(text, sheet.font(11), b.ink, True), "l")))


def _node_xml(shape_id: int, n: SceneNode, sheet: _Sheet) -> str:
    alpha = 0.55 if n.faded else 1.0
    paragraphs = _paragraph(_run(n.label, sheet.font(12), n.ink, True), "ctr")
    if n.tech:
        paragraphs += _paragraph(_run(n.tech, sheet.font(8), INK_SOFT, False), "ctr")
    inset = sheet.size(4)
    return ('<p:sp><p:nvSpPr><p:cNvPr id="%d" name="%s"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            '<p:spPr><a:xfrm><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
            '<a:custGeom><a:avLst/>%s<a:ahLst/>%s<a:rect l="0" t="0" r="w" b="h"/><a:pathLst>%s</a:pathLst></a:custGeom>'
            '%s<a:ln w="%d">%s%s</a:ln></p:spPr>'
            '<p:txBody><a:bodyPr wrap="square" lIns="%d" tIns="%d" rIns="%d" bIns="%d" anchor="ctr">'
            '<a:normAutofit/></a:bodyPr><a:lstStyle/>%s</p:txBody></p:sp>'
            % (shape_id, escape(n.label or n.id), sheet.x(n.x - n.w / 2), sheet.y(n.y - n.h / 2), sheet.size(n.w),
               sheet.size(n.h), GUIDES, SITES, node_path(n.shape, n.w, n.h),
               _color(n.fill, "FFFFFF", alpha), sheet.line(n.width), _color(n.stroke, "8F9BB5", alpha), _dash(n.dash),
               inset, inset, inset, inset, paragraphs))


#: Two points closer than this, in pixels, are one; a run shorter is none.
EPS = 0.5
BENT = {2: "bentConnector2", 3: "bentConnector3", 4: "bentConnector4", 5: "bentConnector5"}


def _runs(pts: Sequence[Point]) -> Tuple[List[Point], List[str]]:
    """The route as axis-aligned runs: consecutive points closer than
    `EPS` are one, and a run that keeps the direction of the one before it
    is folded into it; the kind of each run, `h`, `v`, or `x` for one that
    is neither."""
    points: List[Point] = []
    for p in pts:
        if not points or abs(p[0] - points[-1][0]) > EPS or abs(p[1] - points[-1][1]) > EPS:
            points.append(p)
    kinds: List[str] = []
    kept: List[Point] = points[:1]
    for p in points[1:]:
        a = kept[-1]
        dx, dy = abs(p[0] - a[0]), abs(p[1] - a[1])
        kind = "h" if dy <= EPS else "v" if dx <= EPS else "x"
        if kinds and kinds[-1] == kind and kind != "x":
            kept[-1] = p
        else:
            kept.append(p)
            kinds.append(kind)
    return kept, kinds


def connector(pts: Sequence[Point]) -> Tuple[str, int, bool, bool, Box, List[int]]:
    """The preset connector that draws this route, as PowerPoint stores one:
    its preset, its rotation, its flips, the box of its unrotated geometry
    (x, y, w, h in pixels) and its adjustments in hundred-thousandths.

    PowerPoint refuses a connector with a geometry of its own, so a route
    is one of the presets: a straight line, or an elbow of two to five
    axis-aligned runs. A preset's path always leaves its first corner
    along the horizontal and arrives at the opposite corner, so a route
    that leaves along the vertical is the same preset turned a quarter
    clockwise, and one that arrives above or to the left of where it left
    is flipped. Each bend sits at an adjustment measured from the start
    along the run it ends. A route with more runs than the presets have,
    one that is not axis-aligned (a curve, a free edge), or one that comes
    back to the line it left on, is drawn straight; a reviewer who moves a
    box gets PowerPoint's own elbows either way."""
    points, kinds = _runs(pts)
    q0, qn = points[0], points[-1]
    vx, vy = min(q0[0], qn[0]), min(q0[1], qn[1])
    vw, vh = abs(qn[0] - q0[0]), abs(qn[1] - q0[1])
    straight = ("straightConnector1", 0, qn[0] < q0[0], qn[1] < q0[1], (vx, vy, vw, vh), [])
    n = len(kinds)
    if n < 2 or n > 5 or "x" in kinds or vw <= EPS or vh <= EPS:
        return straight
    if kinds[0] == "h":
        rot, box = 0, (vx, vy, vw, vh)
        flip_h, flip_v = qn[0] < q0[0], qn[1] < q0[1]
        first = 0  # the first bend is measured along x
    else:
        # Turned a quarter clockwise: the unrotated box has the visual
        # height for its width, about the same center, and the first corner
        # of the geometry lands top right; flipped horizontally it lands
        # bottom right, vertically top left.
        rot = 5400000
        cx, cy = vx + vw / 2, vy + vh / 2
        box = (cx - vh / 2, cy - vw / 2, vh, vw)
        flip_h, flip_v = qn[1] < q0[1], qn[0] > q0[0]
        first = 1
    # Each bend sits at the end of its run, measured from the start along
    # the axis the run follows, which alternates from the first.
    adjustments = []
    for i in range(n - 2):
        axis = (first + i) % 2
        extent = vw if axis == 0 else vh
        adjustments.append(int(round(abs(points[i + 1][axis] - q0[axis]) / extent * 100000)))
    return BENT[n], rot, flip_h, flip_v, box, adjustments


def _edge_xml(shape_id: int, e: SceneEdge, source_id: int, source: SceneNode, target_id: int, target: SceneNode,
              sheet: _Sheet, layered: bool) -> str:
    pts = e.points
    prst, rot, flip_h, flip_v, (bx, by, bw, bh), adjustments = connector(pts)
    xfrm = "".join([' rot="%d"' % rot if rot else "", ' flipH="1"' if flip_h else "", ' flipV="1"' if flip_v else ""])
    adj = "".join('<a:gd name="adj%d" fmla="val %d"/>' % (i + 1, a) for i, a in enumerate(adjustments))
    return ('<p:cxnSp><p:nvCxnSpPr><p:cNvPr id="%d" name="%s"/><p:cNvCxnSpPr>'
            '<a:stCxn id="%d" idx="%d"/><a:endCxn id="%d" idx="%d"/></p:cNvCxnSpPr><p:nvPr/></p:nvCxnSpPr>'
            '<p:spPr><a:xfrm%s><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
            '<a:prstGeom prst="%s"><a:avLst>%s</a:avLst></a:prstGeom><a:noFill/>'
            '<a:ln w="%d" cap="rnd">%s%s<a:round/>%s</a:ln>'
            '</p:spPr></p:cxnSp>'
            % (shape_id, escape("Connector %s" % e.id), source_id, site(source, pts[0]), target_id,
               site(target, pts[-1]), xfrm, sheet.x(bx), sheet.y(by), sheet.extent(bw), sheet.extent(bh), prst, adj,
               sheet.line(1.6 if layered else 1.3), _color(EDGE, "7B8798", 1.0 if layered else 0.45), _dash(e.style),
               "" if e.kind in HEADLESS else '<a:tailEnd type="triangle" w="med" len="med"/>'))


def _label_xml(shape_id: int, e: SceneEdge, sheet: _Sheet) -> str:
    x1, y1, x2, y2 = e.label_box
    return ('<p:sp><p:nvSpPr><p:cNvPr id="%d" name="%s"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            '<p:spPr><a:xfrm><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>%s<a:ln w="%d">%s</a:ln></p:spPr>'
            '<p:txBody><a:bodyPr wrap="none" lIns="0" tIns="0" rIns="0" bIns="0" anchor="ctr"/><a:lstStyle/>%s'
            '</p:txBody></p:sp>'
            % (shape_id, escape("Label %s" % e.id), sheet.x(x1), sheet.y(y1), sheet.size(x2 - x1), sheet.size(y2 - y1),
               _color(LABEL_FILL, LABEL_FILL, 0.96), HAIRLINE, _color(LABEL_LINE, LABEL_LINE),
               _paragraph(_run(e.label, sheet.font(10), LABEL_INK, False), "ctr")))


def _fill(color: str, opacity: float = 1.0) -> str:
    return "<a:noFill/>" if not color or color == "none" else _color(color, "FFFFFF", opacity)


def own_path(shape: str, w: float, h: float) -> str:
    """A shape of the diagram's own as a DrawingML path, from the same
    fractions of its box the picture draws it by (`annotations.PATHS`)."""
    parts = []
    for op in own_module.PATHS.get(shape) or own_module.PATHS["rectangle"]:
        if op[0] == "Z":
            parts.append("<a:close/>")
            continue
        pts = [(op[i] * w * K, op[i + 1] * h * K) for i in range(1, len(op), 2)]
        if op[0] == "M":
            parts.append(_move(*pts[0]))
        elif op[0] == "L":
            parts.append(_line(*pts[0]))
        elif op[0] == "Q":
            parts.append(_quad(pts[0][0], pts[0][1], pts[1][0], pts[1][1]))
        else:
            parts.append("<a:cubicBezTo>%s%s%s</a:cubicBezTo>" % (_pt(*pts[0]), _pt(*pts[1]), _pt(*pts[2])))
    return '<a:path w="%d" h="%d">%s</a:path>' % (int(round(w * K)), int(round(h * K)), "".join(parts))


def _own_xml(shape_id: int, o: Own, sheet: _Sheet) -> str:
    """A frame, note, text or shape of the diagram's own: its outline, its
    fill and edge, and its words where the canvas sets them, a frame's name
    in its corner, a note's at its top, a shape's in its middle."""
    if o.look == "tiles" and o.role == "shape" and o.tint:
        return _tile_xml(shape_id, o, sheet)
    x1, y1, x2, y2 = o.box
    w, h = x2 - x1, y2 - y1
    if o.corners:
        # roundRect's adjustment is the radius over the shorter side, at most
        # a half.
        geometry = ('<a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val %d"/></a:avLst></a:prstGeom>'
                    % min(50000, int(round(o.corners / max(min(w, h), 1) * 100000))))
    elif o.role == "shape" and o.shape != "rounded":
        geometry = ('<a:custGeom><a:avLst/><a:gdLst/><a:ahLst/><a:cxnLst/><a:rect l="0" t="0" r="w" b="h"/>'
                    '<a:pathLst>%s</a:pathLst></a:custGeom>' % own_path(o.shape, w, h))
    else:
        geometry = '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
    edge = ("<a:ln><a:noFill/></a:ln>" if o.edge == "none" else '<a:ln w="%d">%s%s</a:ln>' % (
        sheet.line(o.weight), _color(o.edge, "A39C8D"), _dash("dashed" if o.dashed else "")))
    px, py = own_module.PADDING.get(o.role, (8, 8))
    middle = o.role == "shape"
    ink = own_module.TEXT_INK if o.role == "text" else o.words
    lines = o.label.split("\n") if o.label else [""]
    if middle:
        # The name in the display face, bold; the rest a caption under it.
        caption = own_module.CAPTION_INK if o.words == own_module.INK else o.words
        kept = [p for p in lines if p.strip()] or [""]
        paragraphs = _paragraph(_run(kept[0], sheet.font(o.size), ink, True, "Libre Franklin"), "ctr") + "".join(
            _paragraph(_run(p, sheet.font(o.size - own_module.CAPTION_STEP), caption, False), "ctr") for p in kept[1:])
    else:
        paragraphs = "".join(_paragraph(_run(line, sheet.font(o.size), ink, o.role == "frame"), "l") for line in lines)
    return ('<p:sp><p:nvSpPr><p:cNvPr id="%d" name="%s"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            '<p:spPr><a:xfrm%s><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></a:xfrm>%s%s%s</p:spPr>'
            '<p:txBody><a:bodyPr wrap="square" lIns="%d" tIns="%d" rIns="%d" bIns="%d" anchor="%s"/><a:lstStyle/>%s'
            '</p:txBody></p:sp>'
            % (shape_id, escape("%s %s" % (o.role.capitalize(), o.key)),
               # Clockwise, in sixty-thousandths of a degree, about its middle.
               ' rot="%d"' % int(round((o.rotate % 360) * 60000)) if o.rotate else "", sheet.x(x1), sheet.y(y1),
               sheet.size(w),
               sheet.size(h), geometry, _fill(o.fill, o.opacity), edge + (_hard_shadow(sheet) if o.shadow else ""),
               sheet.size(px), sheet.size(py), sheet.size(px),
               sheet.size(py), "ctr" if middle else "t", paragraphs))


def _tile_xml(shape_id: int, o: Own, sheet: _Sheet) -> str:
    """A shape as Icon tiles draw it: the tile, light at the top and deep
    at the foot, and its words under it, set past the tile's foot and left to
    run either side of it."""
    x1, y1, x2, y2 = own_module.tile_box(o.box)
    side = x2 - x1
    corners = own_module.TILE_ROUND if o.corners is None else o.corners
    radius = min(50000, int(round(corners / max(side, 1) * 100000)))
    def stop(color: str, fallback: str) -> str:
        if o.opacity >= 1:
            return '<a:srgbClr val="%s"/>' % _hex(color, fallback)
        return '<a:srgbClr val="%s"><a:alpha val="%d"/></a:srgbClr>' % (_hex(color, fallback),
                                                                        int(round(o.opacity * 100000)))

    fill = ('<a:gradFill rotWithShape="1"><a:gsLst><a:gs pos="0">%s</a:gs><a:gs pos="100000">%s</a:gs></a:gsLst>'
            '<a:lin ang="5400000" scaled="0"/></a:gradFill>' % (stop(o.tint[0], "6E7683"), stop(o.tint[1], "3B4049")))
    kept = [p for p in o.label.split("\n") if p.strip()] or [""]
    paragraphs = _paragraph(_run(kept[0], sheet.font(o.size), own_module.TILE_INK, True), "ctr") + "".join(
        _paragraph(_run(p, sheet.font(o.size - own_module.CAPTION_STEP), own_module.TILE_CAPTION, False), "ctr")
        for p in kept[1:])
    return ('<p:sp><p:nvSpPr><p:cNvPr id="%d" name="%s"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            '<p:spPr><a:xfrm%s><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
            '<a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val %d"/></a:avLst></a:prstGeom>%s'
            '<a:ln><a:noFill/></a:ln></p:spPr>'
            '<p:txBody><a:bodyPr wrap="none" lIns="0" tIns="%d" rIns="0" bIns="0" anchor="t"/><a:lstStyle/>%s'
            '</p:txBody></p:sp>'
            % (shape_id, escape("Shape %s" % o.key),
               ' rot="%d"' % int(round((o.rotate % 360) * 60000)) if o.rotate else "", sheet.x(x1), sheet.y(y1),
               sheet.size(side), sheet.size(side), radius, fill,
               sheet.size(side + (o.box[3] - y2) + own_module.TILE_GAP), paragraphs))


def _own_line_xml(take: Callable[[], int], o: Own, sheet: _Sheet) -> List[str]:
    """A line of the diagram's own as a path of its own, through the turns
    the picture draws it by, with its heads; and its words on a card at its
    middle. A line is a path here, not a connector: PowerPoint refuses a
    connector with a geometry of its own, and the canvas's line follows no
    preset."""
    pts = list(o.points)
    bx1, by1 = min(p[0] for p in pts), min(p[1] for p in pts)
    w, h = max(max(p[0] for p in pts) - bx1, EPS), max(max(p[1] for p in pts) - by1, EPS)
    rel = [((x - bx1) * K, (y - by1) * K) for x, y in pts]
    parts = [_move(*rel[0])]
    if o.route == "curved" and len(rel) > 2:
        # A quadratic through each turn to the middle of the next piece, as
        # the picture draws maxGraph's curve.
        for i in range(1, len(rel) - 2):
            parts.append(_quad(rel[i][0], rel[i][1], (rel[i][0] + rel[i + 1][0]) / 2, (rel[i][1] + rel[i + 1][1]) / 2))
        parts.append(_quad(rel[-2][0], rel[-2][1], rel[-1][0], rel[-1][1]))
    else:
        parts.extend(_line(x, y) for x, y in rel[1:])
    heads = ('<a:headEnd type="triangle" w="sm" len="sm"/>' if o.ends == "both" else "") + (
        "" if o.ends == "none" else '<a:tailEnd type="triangle" w="sm" len="sm"/>')
    out = [('<p:sp><p:nvSpPr><p:cNvPr id="%d" name="%s"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            '<p:spPr><a:xfrm><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
            '<a:custGeom><a:avLst/><a:gdLst/><a:ahLst/><a:cxnLst/><a:rect l="0" t="0" r="w" b="h"/>'
            '<a:pathLst><a:path w="%d" h="%d" fill="none">%s</a:path></a:pathLst></a:custGeom><a:noFill/>'
            '<a:ln w="%d" cap="rnd">%s%s<a:round/>%s</a:ln></p:spPr></p:sp>'
            % (take(), escape("Line %s" % o.key), sheet.x(bx1), sheet.y(by1), sheet.extent(w), sheet.extent(h),
               int(round(w * K)), int(round(h * K)), "".join(parts), sheet.line(1.5), _color(o.edge, "5B6577"),
               _dash("dashed" if o.dashed else ""), heads))]
    if o.label:
        cx, cy = own_module._halfway(pts)
        # The card's width from the words at Geist's average width, as the
        # slide has no measure of its own; a little room either way.
        lw, lh = len(o.label) * o.size * 0.56 + 8, o.size + 6
        out.append('<p:sp><p:nvSpPr><p:cNvPr id="%d" name="%s"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
                   '<p:spPr><a:xfrm><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
                   '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>%s<a:ln w="%d">%s</a:ln></p:spPr>'
                   '<p:txBody><a:bodyPr wrap="none" lIns="0" tIns="0" rIns="0" bIns="0" anchor="ctr"/><a:lstStyle/>%s'
                   '</p:txBody></p:sp>'
                   % (take(), escape("Label %s" % o.key), sheet.x(cx - lw / 2), sheet.y(cy - lh / 2),
                      sheet.size(lw), sheet.size(lh), _color("FFFDF8", "FFFDF8"), HAIRLINE, _color("2E2A25", "2E2A25"),
                      _paragraph(_run(o.label, sheet.font(o.size), own_module.INK, False), "ctr")))
    return out


def slide_shapes(scene: Scene, box: Box, first_id: int) -> List[str]:
    """The scene as slide shapes, one XML element each, in drawing order:
    boundaries, then edges with their labels, then nodes; `box` is where
    they go on the slide, in inches, and the ids run up from `first_id`."""
    sheet = _Sheet(scene.extent, box)
    out: List[str] = []
    next_id = first_id

    def take() -> int:
        nonlocal next_id
        next_id += 1
        return next_id - 1

    # The diagram's own goes where the canvas stacks it: a frame on the bare
    # sheet under everything, one in a boundary on it, the rest over all.
    def own_layer(layer: object) -> None:
        for o in scene.own:
            if o.role != "line" and o.layer == layer and not (o.look == "tiles" and o.role == "shape"):
                out.append(_own_xml(take(), o, sheet))

    own_layer("under")
    for index, b in enumerate(scene.boundaries):
        out.append(_boundary_xml(take(), b, sheet))
        own_layer(index)
    node_ids = {n.id: take() for n in scene.nodes}
    by_id = {n.id: n for n in scene.nodes}
    node_xml = {n.id: _node_xml(node_ids[n.id], n, sheet) for n in scene.nodes}
    for e in scene.edges:
        if e.source not in by_id or e.target not in by_id or len(e.points) < 2:
            continue
        out.append(_edge_xml(take(), e, node_ids[e.source], by_id[e.source], node_ids[e.target], by_id[e.target],
                             sheet, scene.layered))
        if e.label and e.label_box is not None:
            out.append(_label_xml(take(), e, sheet))
    for n in scene.nodes:
        out.append(node_xml[n.id])
    own_layer("over")
    for o in scene.own:
        if o.role == "line" and len(o.points) >= 2:
            out.extend(_own_line_xml(take, o, sheet))
    # As tiles, every tile over the lines, its words under it unbroken.
    for o in scene.own:
        if o.look == "tiles" and o.role == "shape":
            out.append(_own_xml(take(), o, sheet))
    return out
