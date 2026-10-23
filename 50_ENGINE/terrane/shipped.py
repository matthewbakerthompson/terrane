"""Where the shipped folders are: beside the engine in its repository, or
inside the package when the engine is installed.

The views in `30_VIEWS/`, the library in `20_ARCHETYPES/` to `29_TYPES/`,
the marks and the faces in `80_APP/web/`, the quick-door examples in
`90_EXAMPLE/quick/`, and the landing zones in `10_MODEL/tech_services/` and
the answers in `10_MODEL/model.yaml` a sketch borrows from the sample, sit
beside the engine in the repository. A wheel built
from `pyproject.toml` carries copies of them under `terrane/shipped/`, laid out
the same way, so `terrane draw` and the marks on a drawing work from any
folder after `pip install`. Everything that used to reach two folders up
from the engine asks here instead, and the answer is the repository when
there is one and the copies when there is not.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

_ENGINE = Path(__file__).resolve().parent
_REPO = _ENGINE.parents[1]
_INSIDE = _ENGINE / "shipped"


def repo_root() -> Optional[Path]:
    """The repository the engine sits in, when it does: the folder two up
    with the views and the model's folder in it."""
    return _REPO if (_REPO / "30_VIEWS").is_dir() and (_REPO / "10_MODEL").is_dir() else None


def shipped_root() -> Path:
    """The folder holding the shipped views and library: the repository,
    else the copies inside the package."""
    repo = repo_root()
    return repo if repo is not None else _INSIDE


def shipped_web() -> Optional[Path]:
    """The app's `web/` folder with the marks and the faces, wherever it is;
    None when neither the repository nor the package has one."""
    for base in ((repo_root() or _REPO) / "80_APP" / "web", _INSIDE / "web"):
        if (base / "icons" / "map.json").is_file():
            return base
    return None


def shipped_app() -> Optional[Path]:
    """The app's server, wherever it is: `80_APP/app/server.py` in the
    repository, else the copy inside the package, which sits beside the
    copied `web/` as the repository's sits beside its own, so the server
    finds its pages the same way in both. None when neither has one."""
    for base in ((repo_root() or _REPO) / "80_APP" / "app", _INSIDE / "app"):
        if (base / "server.py").is_file():
            return base / "server.py"
    return None


def landing_zones_dir(root: Optional[Path] = None) -> Path:
    """The folder holding the platform services tagged `landing-zone`, which
    a product on a shipped shape binds its shared services to: the model's
    own technology services in a repository, the sample estate's copies in
    the package. A sketch with no technology services of its own borrows
    them (`terrane.quick`)."""
    return (root or shipped_root()) / "10_MODEL" / "tech_services"


def default_root() -> Path:
    """The model a command works on when told nothing: the repository the
    engine sits in, else the current folder, which is where an installed
    `terrane` is run from."""
    repo = repo_root()
    return repo if repo is not None else Path.cwd()


def example_path() -> Path:
    return shipped_root() / "90_EXAMPLE" / "quick" / "payments.yaml"


def sample_inventory() -> Path:
    """The spreadsheet an empty estate is pointed at to try an import on:
    an inventory as a portfolio tool exports it, which `terrane adopt` and
    the app's Import both read. A hint once named `../90_EXAMPLE/csv`, a
    folder of the repository's that no pip install has."""
    return shipped_root() / "90_EXAMPLE" / "quick" / "sample-inventory.xlsx"
