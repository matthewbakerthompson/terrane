"""Measuring text in the app's faces, without the app's browser.

A drawing has to wrap a name and fit a technology line, and the honest ruler
is the one the app uses: Chrome's `measureText` on the faces `styles.css`
ships. `fonts/metrics.json` is that ruler read once, by
`80_APP/tools/dev/font_metrics.py`: every glyph's advance and every pair's
kerning at 100px, for each face and weight the painter sets type in. A
string's width is the sum, scaled to the size asked for; Chrome's own
metrics scale linearly, so the sum is what the canvas would have said to
within the rounding of the file.

The box a node gets is not measured this way. The app sizes it from a
calibrated average glyph width (`shapes.CHAR_W`) because Cytoscape cannot
size a node to its own text, and the layout must use the same estimate to
land on the same geometry. Measurement is for what goes inside the box.
"""

from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import Dict, List, Optional

_PATH = Path(__file__).resolve().parent / "fonts" / "metrics.json"


class Metrics:
    def __init__(self, data: Optional[dict] = None) -> None:
        if data is None:
            data = json.loads(_PATH.read_text(encoding="utf-8"))
        self.size = float(data.get("size") or 100)
        self.faces: Dict[str, dict] = data.get("faces") or {}

    def face(self, family: str, weight: int) -> dict:
        """The face measured, or the nearest weight of the family, or the
        first face there is: a wrong width beats no width."""
        key = "%s/%d" % (family, weight)
        if key in self.faces:
            return self.faces[key]
        same = sorted(
            (abs(int(k.rsplit("/", 1)[1]) - weight), k) for k in self.faces if k.startswith(family + "/")
        )
        if same:
            return self.faces[same[0][1]]
        if self.faces:
            return self.faces[sorted(self.faces)[0]]
        return {"advance": {}, "kern": {}, "ascent": 101, "descent": 30}

    def width(self, text: str, family: str, weight: int, size: float) -> float:
        face = self.face(family, weight)
        advance = face.get("advance") or {}
        kern = face.get("kern") or {}
        fallback = advance.get("n", 55.0)
        total = 0.0
        previous = ""
        for ch in str(text):
            total += advance.get(ch, fallback)
            if previous:
                total += kern.get(previous + ch, 0.0)
            previous = ch
        return total * size / self.size

    def ascent(self, family: str, weight: int, size: float) -> float:
        return float(self.face(family, weight).get("ascent", 101)) * size / self.size

    def descent(self, family: str, weight: int, size: float) -> float:
        return float(self.face(family, weight).get("descent", 30)) * size / self.size

    def wrap(self, text: str, max_width: float, family: str, weight: int, size: float) -> List[str]:
        """Cytoscape's `text-wrap: wrap`: a line wider than the limit is
        broken at spaces, word by word; a word wider than the limit on its
        own is left to overflow rather than broken."""
        out: List[str] = []
        for line in str(text or "").split("\n"):
            if self.width(line, family, weight, size) <= max_width:
                out.append(line)
                continue
            current = ""
            for word in line.split():
                probe = word if not current else current + " " + word
                if self.width(probe, family, weight, size) <= max_width:
                    current = probe
                else:
                    if current:
                        out.append(current)
                    current = word
            if current:
                out.append(current)
        return out or [""]

    def fit(self, text: str, max_width: float, family: str, weight: int, size: float) -> str:
        """The app's `fitText`: the text, or as much of it as fits with an
        ellipsis after it."""
        text = str(text or "")
        if self.width(text, family, weight, size) <= max_width:
            return text
        cut = text
        while len(cut) > 1 and self.width(cut + "…", family, weight, size) > max_width:
            cut = cut[:-1]
        return cut + "…"


@functools.lru_cache(maxsize=1)
def default_metrics() -> Metrics:
    return Metrics()
