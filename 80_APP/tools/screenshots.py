"""Re-captures the README's screenshots from the running app.

A drawing is taken the way the PNG button takes it: the app's own export
of the whole graph, white ground, at 2x, the button's call made directly
on the drawing, so the file is what a reader of the app would have saved,
not a picture of the browser. A report is a table, and the Assemble panel
a panel: those are captured as the stage on the page. The rail is folded
first because the sheet's aspect is what steers a layout's direction, and
the README shows the drawing at the width it gets when the rail is away.

    python 80_APP/app/server.py                      # the app, on 8020
    python 80_APP/app/server.py --root 90_EXAMPLE/thurman-health --port 8021
    python 80_APP/tools/screenshots.py [--url http://127.0.0.1:8020]
        [--estate-url http://127.0.0.1:8021] [name ...]

Drives the Chrome or Edge already on the machine through the engine's own
driver (`terrane.draw.browser`; `TERRANE_CHROME` overrides the path); nothing is
installed. Names select a subset; none means all. This is what
`screenshots.mjs` did with puppeteer until round thirty-four.

The healthcare estate's pictures come from a second app opened on it with
`--root`. The model that app says it serves is checked against the shot's
`estate` before anything is taken, so the sample, served on the wrong
port, is refused rather than saved under the hospital's name.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import time
import urllib.request
from pathlib import Path
from typing import Callable, List, Optional

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "50_ENGINE"))

from terrane.draw.browser import Chrome, Page  # noqa: E402

OUT = REPO / "docs" / "screenshots"
INIT = ('localStorage.setItem("aac.rail.shut", "1"); localStorage.setItem("aac.insp.shut", "0"); '
        'localStorage.setItem("aac.tour", "taken");')
SETTLED = '/[0-9]+%/.test((document.getElementById("zoomPct") || {}).textContent || "")'


def prepare_assembly(page: Page) -> None:
    """The Assemble panel, mid-assembly: the Azure shape's chunks plus a
    worker, with the drawing they make. Driven rather than linked, since an
    assembly is not a URL until it is written."""
    # The panel's own address, once the overview has loaded (the sidebar's
    # layers are drawn from it); then the panel, once its own fetches are
    # back. The home page's button that used to open it is gone: the
    # Diagrams page is about diagrams, and a product is made from New.
    page.wait_for('document.querySelectorAll("#viewList .shelf").length > 0', timeout=30)
    page.evaluate('window.location.hash = "assemble"')
    page.wait_for('!!document.getElementById("asm_shape")', timeout=30, settle=1.2)
    select(page, "asm_shape", "azure-digital-product")
    time.sleep(0.6)
    for field, text in (("asm_name", "Dealer Finance Desk"), ("asm_domain", "Lending"),
                        ("asm_account", "azure-lending-prod")):
        type_into(page, field, text)
    select(page, "asm_owner", "ORG-LENDING")
    page.evaluate('(function () { var box = document.getElementById("chunk_async-worker"); '
                  'if (box && !box.checked) box.click(); })()')
    time.sleep(2.5)
    # Typing into the account field scrolled the panel to it; the picture is
    # of the three panes from the top.
    page.evaluate('document.getElementById("dataPanel").scrollTop = 0')
    time.sleep(0.3)


def select(page: Page, element_id: str, value: str) -> None:
    """Pick an option the way a person does: the value set and the events
    a select fires on a change."""
    page.evaluate('(function () { var s = document.getElementById(%r); s.value = %r; '
                  's.dispatchEvent(new Event("input", { bubbles: true })); '
                  's.dispatchEvent(new Event("change", { bubbles: true })); })()' % (element_id, value))


def type_into(page: Page, element_id: str, text: str) -> None:
    """Type into a field: focused and emptied, then the text inserted as
    keystrokes are, so whatever listens to input hears it."""
    page.evaluate('(function () { var i = document.getElementById(%r); i.focus(); i.value = ""; '
                  'i.dispatchEvent(new Event("input", { bubbles: true })); })()' % element_id)
    page.send("Input.insertText", text=text)
    page.evaluate('document.getElementById(%r).dispatchEvent(new Event("change", { bubbles: true }))' % element_id)


SHOTS = [
    # What the README shows, in the order it shows it. `hash` is the app's
    # own deep link, so the capture is the same picture a reader lands on.
    {"name": "onboarding-installment-lending", "hash": "view=onboarding&p_product=PRD-INSTALLMENT-LENDING"},
    {"name": "application-landscape", "hash": "view=application-landscape"},
    {"name": "network-topology", "hash": "view=network-topology"},
    {"name": "system-context", "hash": "view=system-context"},
    # The switch rather than the ledger: the ledger's governance is
    # fifty-six entities, which is a finding, and the README wants a picture
    # a reader can take in.
    {"name": "system-governance", "hash": "view=system-governance&p_system=SYS-AUTH-SWITCH"},
    {"name": "control-coverage", "hash": "view=control-coverage", "kind": "report"},
    {"name": "assemble", "hash": "", "kind": "assemble", "prepare": prepare_assembly},
    # The second estate: where the health system runs, and the interface
    # engine every HL7 feed goes through, drawn by views written for the card
    # issuer and not changed.
    {"name": "thurman-hosting-estate", "hash": "view=hosting-estate", "estate": "Thurman Health"},
    {"name": "thurman-interface-engine", "hash": "view=hub-and-spoke&p_system=SYS-INTERFACE-ENGINE",
     "estate": "Thurman Health"},
]


def served_model(base: str) -> str:
    """The name of the model an app says it serves."""
    with urllib.request.urlopen(base + "/api/overview", timeout=30) as response:
        if response.status != 200:
            raise RuntimeError("%s answered %s" % (base, response.status))
        return str(json.loads(response.read().decode("utf-8")).get("modelName") or "")


def settled(page: Page) -> None:
    """The zoom readout is the last thing `drawGraph` writes, after the fit."""
    page.wait_for(SETTLED, timeout=30, settle=0.6)


def drawing_png(page: Page) -> bytes:
    """The picture the PNG button exports, composed by the app itself."""
    settled(page)
    data_url = page.evaluate('window.__aacDrawingPng(2)', await_promise=True)
    return base64.b64decode(data_url.split(",", 1)[1])


def stage_png(page: Page, ready_selector: str) -> bytes:
    """A report or a panel is not a drawing: the stage, title and all, once
    what it shows is on the page."""
    page.wait_for('!!document.querySelector(%r)' % ready_selector, timeout=30, settle=0.4)
    rect = page.evaluate('(function () { var r = document.querySelector("main.stage").getBoundingClientRect(); '
                         'return [r.left, r.top, r.width, r.height]; })()')
    x, y, w, h = (float(v) for v in rect)
    result = page.send("Page.captureScreenshot", format="png", captureBeyondViewport=True,
                       clip={"x": x, "y": y, "width": w, "height": h, "scale": 1})
    return base64.b64decode(result["data"])


def capture(page: Page, kind: str) -> bytes:
    if kind == "report":
        return stage_png(page, "#dataPanel table tbody tr")
    if kind == "timeline":
        return stage_png(page, ".tl-bar")
    if kind == "assemble":
        return stage_png(page, ".asm-edit")
    return drawing_png(page)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="re-capture the README's screenshots from the running app")
    parser.add_argument("--url", default="http://127.0.0.1:8020")
    parser.add_argument("--estate-url", default="http://127.0.0.1:8021",
                        help="the app opened on the second estate with --root")
    parser.add_argument("--out", default=str(OUT), help="where the pictures go; docs/screenshots by default")
    parser.add_argument("names", nargs="*", help="a subset by name; none means all")
    args = parser.parse_args(argv)
    wanted = [s for s in SHOTS if not args.names or s["name"] in args.names]
    if not wanted:
        print("no such screenshot; the names are " + ", ".join(s["name"] for s in SHOTS))
        return 2
    estate_url = args.estate_url.rstrip("/")
    for estate in sorted({s["estate"] for s in wanted if s.get("estate")}):
        serving = served_model(estate_url)
        if serving != estate:
            raise SystemExit("%s serves %r, not %r; start it with --root 90_EXAMPLE/thurman-health, or pass "
                             "--estate-url" % (estate_url, serving, estate))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with Chrome(width=1600, height=1000) as browser:
        for shot in wanted:
            base = estate_url if shot.get("estate") else args.url.rstrip("/")
            page = browser.page(base + "/#" + shot["hash"], init_script=INIT)
            page.wait_for('document.readyState === "complete"', timeout=60, settle=0.5)
            prepare: Optional[Callable[[Page], None]] = shot.get("prepare")
            if prepare:
                prepare(page)
            kind = shot.get("kind", "diagram")
            target = out / (shot["name"] + ".png")
            target.write_bytes(capture(page, kind))
            print("%-32s %-8s %d bytes" % (shot["name"], {"report": "table", "assemble": "panel"}.get(kind, "drawing"),
                                           target.stat().st_size))
            browser.close_page(page)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
