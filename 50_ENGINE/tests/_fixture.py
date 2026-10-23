"""Shared test fixture.

The shipped model is empty, so tests cannot read the repository's own
`10_MODEL/`. Each run builds a throwaway copy of the repository, seeds it from
`90_EXAMPLE/csv`, and points the tests at that. Nothing under test ever touches
the real working tree.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import importer, model as model_module, records  # noqa: E402
from terrane.library import SETTING as LIBRARY_PATHS  # noqa: E402
from terrane.loader import read_data_file  # noqa: E402
from terrane.query import load_views  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
EXAMPLE_CSV = REPO / "90_EXAMPLE" / "csv"

#: Folders a sandbox needs to behave like the real repository.
_COPIED = (
    "20_ARCHETYPES", "24_CONNECTIONS", "25_COMPONENTS", "26_BLOCKS", "27_PATTERNS", "28_MODULES", "29_TYPES", "30_VIEWS",
    "50_ENGINE", "90_EXAMPLE",
)

#: Nothing under test reads these, and copying them is not free: installing the
#: Mermaid parse check puts thousands of files under `50_ENGINE/tools`, which
#: turned a two-minute suite into one that did not finish. The second example
#: estate is read where it lies (`test_second_estate.py`), so no sandbox
#: carries a copy of it.
_SKIP = shutil.ignore_patterns("node_modules", "__pycache__", "*.pyc", "site", "thurman-health")


def laid_on(fixture: dict) -> tuple:
    """The sheet the app laid a captured drawing out on, width and height:
    what the page recorded when it laid it out, since a subject bar or a
    note takes the top of the sheet afterward; for a capture older than
    that record, the width it was captured at and the nominal sheet's
    height. The wheel and the organic layout are placed about the sheet's
    middle, so a sheet 33 pixels taller moved every box of theirs 17."""
    sheet = (fixture.get("layout") or {}).get("sheet")
    if sheet:
        return float(sheet[0]), float(sheet[1])
    return float(fixture["container"]["w"]), 871.4375


def laid_in(fixture: dict) -> tuple:
    """The sheet's own rectangle when the app laid a captured drawing out,
    fractions and all, which is what the layered layout measures: Product
    Architecture turns on the 904.6-pixel sheet it was laid out on and not
    on the 861.6 its subject bar leaves. For a capture older than that
    record, the container as it was captured."""
    rect = (fixture.get("layout") or {}).get("rect")
    if rect:
        return float(rect[0]), float(rect[1])
    return float(fixture["container"]["w"]), float(fixture["container"]["h"])


def remove_scratch(folder: Path, prefix: str) -> None:
    """Remove a folder a test made with `tempfile.mkdtemp(prefix=prefix)`,
    and refuse anything else.

    On 2026-10-18 a test's `shutil.rmtree(root.parents[1], ignore_errors=True)`,
    run against an old `terrane/diff.py` whose path sat a level higher, emptied
    most of AppData\\Local, and `ignore_errors` hid that the target was wrong.
    So the folder is checked before it goes: directly in the temp folder,
    under the prefix the test chose. A raise rather than an `assert`, which
    `python -O` would strip. Once the check passes, what is left to ignore
    is Windows holding a file a moment longer, which costs a stray temp
    folder and nothing more."""
    folder = Path(folder)
    if not (prefix and folder.parent == Path(tempfile.gettempdir())
            and folder.name.startswith(prefix) and folder.name != prefix and not folder.is_symlink()):
        raise RuntimeError("refusing to remove %s: not a %s* folder made in %s"
                           % (folder, prefix, tempfile.gettempdir()))
    shutil.rmtree(folder, ignore_errors=True)


class Sandbox:
    """A throwaway copy of the repository, optionally seeded."""

    def __init__(self, seed: bool = False) -> None:
        self.seed = seed
        self.tmp: Path | None = None
        self.root: Path | None = None

    def __enter__(self) -> Path:
        self.tmp = Path(tempfile.mkdtemp(prefix="aac-test-"))
        self.root = self.tmp / "repo"
        self.root.mkdir()
        for folder in _COPIED:
            shutil.copytree(REPO / folder, self.root / folder, ignore=_SKIP)
        (self.root / "10_MODEL").mkdir()
        shutil.copy(REPO / "10_MODEL" / "model.yaml", self.root / "10_MODEL" / "model.yaml")
        _shipped_library_only(self.root / "10_MODEL" / "model.yaml")
        if self.seed:
            importer.import_csv(self.root, EXAMPLE_CSV, model_module.load(self.root))
        return self.root

    def __exit__(self, *exc) -> None:
        if self.tmp is not None:
            remove_scratch(self.tmp, "aac-test-")


def _shipped_library_only(config: Path) -> None:
    """A sandbox reads the shipped library and nothing an organization added.

    The tests hold the engine to the sample, whatever the model holds; an
    organization's `library_paths` named folders the sandbox does not copy,
    and every sandbox refused to load. A test of the organization's library
    names one of its own (`test_own_library.py`)."""
    text = config.read_text(encoding="utf-8-sig")
    data = read_data_file(config) or {}
    if isinstance(data, dict) and LIBRARY_PATHS in data:
        data.pop(LIBRARY_PATHS)
        config.write_text(records.rewrite(text, data), encoding="utf-8", newline="\n")


#: A single seeded sandbox shared by the read-only test classes. Building it
#: once keeps the suite quick; nothing that uses it writes to it.
_SHARED: Sandbox | None = None
_SHARED_ROOT: Path | None = None


def setup_shared() -> Path:
    global _SHARED, _SHARED_ROOT
    if _SHARED_ROOT is None:
        _SHARED = Sandbox(seed=True)
        _SHARED_ROOT = _SHARED.__enter__()
    return _SHARED_ROOT


def teardown_shared() -> None:
    global _SHARED, _SHARED_ROOT
    if _SHARED is not None:
        _SHARED.__exit__(None, None, None)
    _SHARED, _SHARED_ROOT = None, None


def seeded_root() -> Path:
    return setup_shared()


def seeded_model():
    """A freshly loaded model from the shared seeded sandbox."""
    return model_module.load(seeded_root())


def drawable(model, view):
    """A view ready to resolve, or None when there is nothing to draw.

    A parameterized view has no single graph: it is one per subject. Tests that
    sweep every view want the one `render_for` would draw first, and binding it
    here keeps that detail out of every one of them. A subject view whose
    selection is empty in the seed -- the seed's products carry no `archetype`,
    so a view of products on a shape selects none -- yields None, and a sweep
    skips it rather than binding nothing.
    """
    from terrane.query import bind, render_targets

    if not view.parameters:
        return view
    targets = render_targets(model, view)
    if not targets:
        return None
    return bind(view, dict(targets), model)


def seeded_views():
    return load_views(seeded_root() / "30_VIEWS")
