"""The Python drawing of a view as a PNG, for putting beside the app's.

    python 80_APP/tools/dev/svg_shot.py --url http://127.0.0.1:8031 application-landscape

Opens `/api/svg?view=...` in a headless Chrome and saves the sheet at 2x as
`out/<view>.py.png`; `layout_fixture.py` saves the app's own export of the
same view as `out/<view>.app.png`, so the two pictures can be read side by
side. Any query the endpoint takes can follow the view in the argument:
`vendor-exposure&labels=on`.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from chrome import Chrome  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--url", default="http://127.0.0.1:8020")
    parser.add_argument("--scale", type=float, default=2.0)
    parser.add_argument("views", nargs="+")
    args = parser.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    base = args.url.rstrip("/")
    with Chrome(width=1600, height=1200) as browser:
        for item in args.views:
            # An SVG file on disk, such as a committed picture, is shot as it
            # is; anything else is a view asked of the running app.
            if Path(item).is_file():
                view = Path(item).stem
                url = Path(item).resolve().as_uri()
            else:
                view = item.split("&")[0]
                url = base + "/api/svg?view=" + item
                # A refusal comes back as JSON; say why rather than shoot it.
                with urllib.request.urlopen(url, timeout=120) as response:
                    kind = response.headers.get("Content-Type", "")
                    if "json" in kind:
                        print(view, json.loads(response.read().decode("utf-8")).get("error"))
                        continue
            page = browser.page(url)
            page.wait_for("document.readyState === 'complete' && document.documentElement.getAttribute('viewBox')",
                          timeout=60, settle=1.0)
            size = page.evaluate("document.documentElement.getAttribute('viewBox').split(' ').slice(2).map(Number)")
            png = page.screenshot(size[0], size[1], args.scale)
            path = OUT / (view + ".py.png")
            path.write_bytes(png)
            print("%-26s %4.0fx%-4.0f -> %s" % (view, size[0], size[1], path))
            page.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
