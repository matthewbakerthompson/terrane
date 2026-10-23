"""A view as SVG, from the model, with no browser in the loop.

    python 80_APP/tools/render_svg.py application-landscape tiered-architecture
    python 80_APP/tools/render_svg.py --out site/svg --embed-fonts --all

Each view is laid out the way the app lays it out (`terrane.draw`) and painted
as the sheet the app's PNG button exports: title, drawing, legend, footer.
`--embed-fonts` carries Geist inside the file so it reads the same wherever
it is opened; without it the picture names the face and falls back to the
system's. `--date` writes the day on the sheet, which the committed output
never does. Every map and the layered diagrams are drawn, a tile map
wrapped to the sheet's width; a view the app lays out organically is
reported and skipped, and a view the app would hand to ELK is drawn on the
dagre path the app itself falls back to, which the sheet's `data-layout`
attribute says. `terrane render` writes the same pictures for every view under
`70_ARTIFACTS/svg/` with the faces named and no date, and CI holds those
fresh; this tool is for a sheet of another size, embedded fonts, a dated
title block or one subject.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_DIR.parent
WEB_DIR = APP_DIR / "web"

sys.path.insert(0, str(REPO_ROOT / "50_ENGINE"))
sys.path.insert(0, str(APP_DIR / "app"))

import server  # noqa: E402

from terrane.draw import Undrawable, render_svg  # noqa: E402
from terrane.icons import IconMap  # noqa: E402

icon_loader = IconMap(WEB_DIR).read


def font_loader(name: str):
    path = WEB_DIR / "fonts" / name
    return path.read_bytes() if path.is_file() else None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("views", nargs="*", help="view ids; a subject as view=... p_<name>=<id> in one argument")
    parser.add_argument("--all", action="store_true", help="every map and diagram the Python layout covers")
    parser.add_argument("--out", default=str(APP_DIR / "tools" / "dev" / "out"))
    parser.add_argument("--embed-fonts", action="store_true")
    parser.add_argument("--no-sheet", action="store_true", help="the drawing alone, without title block or legend")
    parser.add_argument("--sheet", default="1240x871.4375", help="the sheet the layout fits, WxH")
    parser.add_argument("--date", default="", help="a date for the title block; the committed output carries none")
    args = parser.parse_args(argv)

    width, height = (float(v) for v in args.sheet.lower().split("x"))
    model, views = server._load_all()
    overview = server.api_overview({}, None)
    wanted = list(args.views)
    if args.all or not wanted:
        # A view that takes a subject has no drawing without one.
        wanted = [v.view_id for v in views if v.kind in ("map", "diagram") and not getattr(v, "parameters", None)]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    drawn = 0
    for item in wanted:
        if "=" in item:
            # `view=product-architecture&p_product=PRD-X`, or the subject
            # alone after the view id: `product-architecture&p_product=PRD-X`.
            query = {}
            for part in item.split("&"):
                k, _, v = part.partition("=")
                if not v:
                    k, v = "view", k
                query[k] = [v]
            view_id = query.get("view", [item])[0]
        else:
            query = {"view": [item]}
            view_id = item
        payload = server.api_graph(query, None)
        try:
            svg = render_svg(
                payload, sheet_width=width, sheet_height=height, icon_loader=icon_loader,
                font_loader=font_loader if args.embed_fonts else None, sheet=not args.no_sheet,
                model_name=str(overview.get("modelName") or ""), date=args.date,
            )
        except Undrawable as exc:
            print("%-26s skipped: %s" % (view_id, exc))
            continue
        subject = "".join("--" + v[0] for k, v in sorted(query.items()) if k.startswith("p_"))
        path = out / (view_id + subject + ".svg")
        path.write_text(svg, encoding="utf-8")
        drawn += 1
        print("%-26s %6.0f KB  -> %s" % (view_id + subject, len(svg) / 1024, path))
    return 0 if drawn else 1


if __name__ == "__main__":
    raise SystemExit(main())
