"""A PNG from an SVG, by whatever the machine has.

The engine runs on a bare interpreter and ships no rasterizer. Two things
can make a PNG of a drawing: a Chrome or an Edge on the machine, driven
headless (`terrane.draw.browser`), and `resvg-py` where it is installed. The
browser comes first when both are there, since it sets the picture in the
faces inside it, which resvg cannot; `TERRANE_PNG=resvg` or `TERRANE_PNG=browser`
picks one, and `TERRANE_CHROME` names the browser. Where there is neither, the
refusal says both ways.
"""

from __future__ import annotations

import atexit
import os
from pathlib import Path
from typing import Dict, Optional, Tuple

from .browser import Rasterizer, browser_path


class NoRasterizer(RuntimeError):
    pass


def _resvg():
    try:
        import resvg_py  # type: ignore
    except ImportError:
        return None
    return resvg_py


def _choose(prefer: str) -> str:
    """The means: the browser's name (`chrome`, `msedge`, `google-chrome`)
    or `resvg-py`; refused with both ways when the machine has neither."""
    prefer = (prefer or os.environ.get("TERRANE_PNG") or "").strip().lower()
    browser = browser_path()
    resvg = _resvg()
    if prefer == "resvg" and resvg is not None:
        return "resvg-py"
    if prefer == "browser" and browser:
        return Path(browser).stem
    if browser:
        return Path(browser).stem
    if resvg is not None:
        return "resvg-py"
    raise NoRasterizer("no Chrome or Edge was found on this machine (set TERRANE_CHROME to one) and resvg-py is not "
                       "installed (pip install resvg-py)")


class LazyRasterizer:
    """SVG text to PNG bytes at `scale` device pixels per CSS pixel, by the
    means the machine has: chosen when made, so a command can say which,
    and opened on first use, so a command that draws nothing launches
    nothing. Close it, or use it as a context manager."""

    def __init__(self, scale: float = 2.0, prefer: str = "") -> None:
        self.scale = scale
        self.means = _choose(prefer)
        self._browser: Optional[Rasterizer] = None

    def __call__(self, svg_text: str) -> bytes:
        if self.means == "resvg-py":
            resvg = _resvg()
            return bytes(resvg.svg_to_bytes(svg_string=svg_text, zoom=self.scale))
        if self._browser is None:
            self._browser = Rasterizer(scale=self.scale).__enter__()
        return self._browser(svg_text)

    def close(self) -> None:
        if self._browser is not None:
            self._browser.__exit__(None, None, None)
            self._browser = None

    def __enter__(self) -> "LazyRasterizer":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


class SharedRasterizer:
    """The process's one rasterizer for a scale and a means, handed to
    every run of drawings and never closed by them: `terrane draw --png`
    called twice from a notebook launched two browsers, and the suite a
    few dozen. `close` is a courtesy that keeps the browser; the process
    closes it at exit, and a browser that has gone away is opened again
    on the next picture."""

    def __init__(self, inner: LazyRasterizer) -> None:
        self._inner = inner

    @property
    def means(self) -> str:
        return self._inner.means

    @property
    def scale(self) -> float:
        return self._inner.scale

    def __call__(self, svg_text: str) -> bytes:
        try:
            return self._inner(svg_text)
        except (ConnectionError, OSError, RuntimeError):
            self._inner.close()
            return self._inner(svg_text)

    def close(self) -> None:
        pass

    def __enter__(self) -> "SharedRasterizer":
        return self

    def __exit__(self, *exc) -> None:
        pass


_SHARED: Dict[Tuple[float, str], SharedRasterizer] = {}


def _close_shared() -> None:
    for shared in _SHARED.values():
        shared._inner.close()
    _SHARED.clear()


atexit.register(_close_shared)


def open_rasterizer(scale: float = 2.0, prefer: str = "") -> SharedRasterizer:
    """The rasterizer for a run of drawings, one per scale and means for
    the whole process (`SharedRasterizer`); `NoRasterizer` when the
    machine has no way to make a PNG."""
    inner = LazyRasterizer(scale=scale, prefer=prefer)
    key = (float(scale), inner.means)
    if key not in _SHARED:
        _SHARED[key] = SharedRasterizer(inner)
    return _SHARED[key]
