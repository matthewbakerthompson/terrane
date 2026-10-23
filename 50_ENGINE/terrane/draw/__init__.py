"""Drawing a view without a browser.

Every picture this repository has shown so far was drawn by the app, in a
browser, by Cytoscape and the layout code around it; the committed Mermaid
is a weaker rendering of the same model, and anything that wanted the real
picture needed Chrome. This package draws the same picture from Python: the
same payload the app receives, laid out by the same rules, painted as SVG
in the house conventions ([AAC-14](../../../00_METHOD/AAC-14_DIAGRAM_CONVENTIONS.md)).

The app is the spec for where things go. `packed` is a port of the app's
packing layout and `layered` of its layered one, `layoutHierarchy()` whole
with the dagre the browser ships ported beneath it (`dagre`), the direction
choice and the app's three-piece router; `router` is the Python answer to
ELK's routing on top of that placement, every line around the nodes and
boundaries, and the one the painter uses; `tiles` is the stylesheet's
arithmetic for the maps the app draws as HTML, Chrome's line breaking
included; `timeline` is the app's calendar of quarters and `sequence` the
flows the engine has always written as Mermaid, both drawn here as well; `tests/test_draw_packed.py`,
`test_draw_layered.py` and `test_draw_tiles.py` hold them equal to fixtures
read back from the running app. `svg` paints what the app paints, in the
faces the app ships, measured in the app's own browser
(`fonts/metrics.json`). `mode` decides, the way the app does, which layout a
view gets, and names what is not covered: the organic and concentric
layouts, and ELK, whose views are drawn on the dagre path the app itself
falls back to.
"""

from .layered import LayeredLayout, layout_layered
from .metrics import Metrics, default_metrics
from .mode import Mode, Undrawable, drawing_mode
from .packed import Layout, layout_packed, prepare
from .sequence import render_sequence_svg
from .svg import render_svg
from .tiles import TileLayout, layout_tiles
from .timeline import render_timeline_svg

__all__ = ["Layout", "LayeredLayout", "Metrics", "Mode", "TileLayout", "Undrawable", "default_metrics",
           "drawing_mode", "layout_layered", "layout_packed", "layout_tiles", "prepare", "render_sequence_svg",
           "render_svg", "render_timeline_svg"]
