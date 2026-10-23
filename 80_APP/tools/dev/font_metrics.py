"""The app's faces measured in the app's browser, for the Python painter.

A drawing made without a browser still has to wrap a name and fit a
technology line, and the only honest ruler is the one the app uses: Chrome's
`measureText` on the faces `styles.css` ships. This opens the app in a
headless Chrome, waits for the fonts, and measures every glyph and every
pair of printable ASCII glyphs at 100px, so `terrane.draw.metrics` can measure a
string at any size by summing advances and kerning. Run it when a face or a
weight is added to `80_APP/web/fonts/`.

    python 80_APP/tools/dev/font_metrics.py --url http://127.0.0.1:8031
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from chrome import Chrome  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TARGET = REPO / "50_ENGINE" / "terrane" / "draw" / "fonts" / "metrics.json"

#: The faces the painter sets type in. Weight 700 is the title block's.
FACES = [("Geist", 400), ("Geist", 500), ("Geist", 600), ("Geist", 700),
         ("Geist Mono", 400), ("Geist Mono", 500)]

MEASURE = r"""
(async function (faces) {
  var chars = [];
  for (var c = 0x20; c <= 0x7e; c++) chars.push(String.fromCharCode(c));
  for (var c = 0xa0; c <= 0xff; c++) chars.push(String.fromCharCode(c));
  "–—‘’“”•…→".split("").forEach(function (c) { chars.push(c); });
  var pairs = [];
  for (var a = 0x21; a <= 0x7e; a++) pairs.push(String.fromCharCode(a));
  var canvas = document.createElement("canvas");
  var ctx = canvas.getContext("2d");
  var out = {};
  for (var i = 0; i < faces.length; i++) {
    var family = faces[i][0], weight = faces[i][1];
    var spec = weight + " 100px \"" + family + "\"";
    await document.fonts.load(spec);
    ctx.font = spec + ", monospace";
    var advance = {};
    chars.forEach(function (ch) { advance[ch] = Math.round(ctx.measureText(ch).width * 100) / 100; });
    var kern = {};
    for (var p = 0; p < pairs.length; p++) {
      for (var q = 0; q < pairs.length; q++) {
        var ab = pairs[p] + pairs[q];
        var k = ctx.measureText(ab).width - advance[pairs[p]] - advance[pairs[q]];
        if (Math.abs(k) >= 0.05) kern[ab] = Math.round(k * 100) / 100;
      }
    }
    var m = ctx.measureText("Hg");
    out[family + "/" + weight] = {
      advance: advance, kern: kern,
      ascent: Math.round((m.fontBoundingBoxAscent || 0) * 100) / 100,
      descent: Math.round((m.fontBoundingBoxDescent || 0) * 100) / 100,
      loaded: document.fonts.check(spec),
    };
  }
  return out;
})(%s)
"""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--url", default="http://127.0.0.1:8020")
    parser.add_argument("--out", default=str(TARGET))
    args = parser.parse_args(argv)
    with Chrome() as browser:
        page = browser.page(args.url.rstrip("/") + "/", init_script="")
        page.wait_for("document.readyState === 'complete'", timeout=60, settle=0.5)
        faces = page.evaluate(MEASURE % json.dumps(FACES), await_promise=True)
    missing = [name for name, face in faces.items() if not face["loaded"]]
    if missing:
        raise SystemExit("faces not loaded by the page, so these are fallback metrics: %s" % ", ".join(missing))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {"size": 100, "source": "Chrome measureText on the faces in 80_APP/web/fonts", "faces": {}}
    for name, face in faces.items():
        data["faces"][name] = {
            "ascent": face["ascent"], "descent": face["descent"],
            "advance": face["advance"], "kern": face["kern"],
        }
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(data, indent=0, sort_keys=True, ensure_ascii=False) + "\n")
    for name, face in faces.items():
        print("%-16s %4d glyphs %5d kern pairs  ascent %.1f descent %.1f" % (
            name, len(face["advance"]), len(face["kern"]), face["ascent"], face["descent"]))
    print("->", out.relative_to(REPO))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
