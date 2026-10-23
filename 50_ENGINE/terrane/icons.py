"""The provider's or vendor's own mark for a node, where one may be shown.

A technology service carries the mark of the service it is: EKS, Key Vault,
Cloud SQL. A bought system carries its vendor's mark where the vendor lets
the mark travel: the Simple Icons collection carries Salesforce and
Snowflake; ServiceNow and Workday keep theirs home, and the technology line
under the name says the vendor in words instead. `web/icons/map.json` says
which file a word or a kind of component points at, longest matching word
first, so "microsoft sentinel" beats "microsoft"; `CREDITS.md` beside it
says whose each mark is and on what terms. A boundary carries the mark of
the kind of container it is where the provider publishes one: the AWS group
icons for a cloud, an account, a region and a subnet, Microsoft's for a
subscription, the corporate data center for the on-premises boundary.

The files live with the app, in `80_APP/web/icons/`, because the app
serves them and the static site copies them; the matching lives here so
`terrane render` can put the marks on its SVG without importing the app.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Optional

#: A key matches as whole words: "s3" in "Amazon S3", not in "s3x".
_WORD = r"(?<![a-z0-9])%s(?![a-z0-9])"

#: The app's `web/` folder, under the repository root.
WEB = Path("80_APP") / "web"


_SVG_TAG = re.compile(rb"<svg\b[^>]*>", re.S)
_VIEWBOX = re.compile(rb'viewBox="\s*[-\d.]+[\s,]+[-\d.]+[\s,]+([\d.]+)[\s,]+([\d.]+)\s*"')


def sized(svg: bytes, longest: int = 64) -> bytes:
    """A mark that says only its viewBox, given a width and height of the
    same shape, `longest` on its longer side. A canvas draws an image of no
    intrinsic size as if it were 300 by 150, so a Simple Icons or Google
    Cloud mark came out as a fragment; the AWS and Azure files say their
    size and drew whole. Applied where a mark is served or baked, so the
    files stay as their owners publish them. Anything else is returned as
    it came."""
    tag = _SVG_TAG.search(svg)
    if tag is None or re.search(rb"\swidth=", tag.group(0)):
        return svg
    box = _VIEWBOX.search(tag.group(0))
    if box is None:
        return svg
    w, h = float(box.group(1)), float(box.group(2))
    if w <= 0 or h <= 0:
        return svg
    scale = longest / max(w, h)
    size = b' width="%s" height="%s"' % (("%g" % (w * scale)).encode(), ("%g" % (h * scale)).encode())
    at = tag.start() + len(b"<svg")
    return svg[:at] + size + svg[at:]


def web_dir(root: Path) -> Optional[Path]:
    """Where the marks and the faces are: the app's `web/` beside the model's
    root, else beside the engine itself, for a model rendered from another
    folder with `--root`; None when neither has one, and a drawing then
    carries no marks."""
    if (Path(root) / WEB / "icons" / "map.json").is_file():
        return Path(root) / WEB
    from .shipped import shipped_web

    return shipped_web()


class IconMap:
    def __init__(self, web_dir: Path) -> None:
        self.root = Path(web_dir) / "icons"
        path = self.root / "map.json"
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        self.providers: Dict[str, dict] = data.get("providers") or {}
        self.vendors: Dict[str, str] = data.get("vendors") or {}
        self.groups: Dict[str, str] = data.get("groups") or {}
        self.sources: Dict[str, dict] = data.get("sources") or {}

    @staticmethod
    def _match(table: Dict[str, str], text: str) -> str:
        best_key, best_file = "", ""
        for key, file in table.items():
            if len(key) > len(best_key) and re.search(_WORD % re.escape(key), text):
                best_key, best_file = key, file
        return best_file

    def _served(self, file: str) -> str:
        """The path the app loads, or nothing when the file is not shipped."""
        return "icons/" + file if file and (self.root / file).exists() else ""

    def read(self, served: str) -> Optional[bytes]:
        """The bytes of a served path (`icons/aws/eks.svg`), for a painter
        that puts the mark inside the picture; None for nothing or a path
        that is not shipped."""
        if not served or not served.startswith("icons/"):
            return None
        path = self.root / served[len("icons/"):]
        return path.read_bytes() if path.is_file() else None

    def for_group(self, key: str) -> str:
        """The mark for a boundary, by the key the palette gives its kind:
        "AWS account", "public subnet", "on-prem". Nothing for a kind the
        provider draws as a plain labeled box."""
        return self._served(self.groups.get(str(key or ""), ""))

    def for_node(self, entity_type: str, record: dict) -> str:
        if entity_type == "tech_services":
            provider = str(record.get("cloud_provider") or "")
            text = " ".join(str(record.get(k) or "") for k in ("product", "service_name", "name")).lower()
            own = self.providers.get(provider)
            # A service of a known provider is looked up in that provider's
            # names; one of no provider (a vendor's own service) in every
            # provider's, since Microsoft publishes Entra's mark with Azure's.
            tables = [own] if own else list(self.providers.values())
            for table in tables:
                hit = self._match(table.get("names") or {}, text)
                if hit:
                    return self._served(hit)
            hit = self._match(self.vendors, text)
            if hit:
                return self._served(hit)
            if own:
                kind = str(record.get("component_type") or "")
                return self._served((own.get("kinds") or {}).get(kind, ""))
            return ""
        if entity_type == "systems":
            vendor = str(record.get("provider") or "").strip()
            hosting = str(record.get("hosting") or "")
            # A system of ours carries no vendor's mark, whatever its name
            # says; a bought one carries its vendor's where there is one.
            if vendor.lower() in ("", "in-house") and hosting not in ("SaaS", "External"):
                return ""
            text = (vendor + " " + str(record.get("name") or "")).lower()
            return self._served(self._match(self.vendors, text))
        return ""
