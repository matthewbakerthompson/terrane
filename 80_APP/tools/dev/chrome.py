"""The headless browser driver lives in the engine now, as `terrane.draw.browser`,
where `terrane render --png` and `terrane draw --png` shoot each drawing with it.
This name stays for the capture scripts beside it, which import `Chrome`
from here; nothing else is here."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "50_ENGINE"))

from terrane.draw.browser import CHROMES, Chrome, Page, browser_path, find_chrome  # noqa: E402,F401
