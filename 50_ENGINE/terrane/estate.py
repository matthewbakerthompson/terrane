"""An estate in a repository of its own: the views it is drawn with, the
versions it is checked with, and the files `terrane init` starts it from.

An organization's architecture lives in a repository it owns, in Azure
DevOps or wherever its code is, and every person who works on it installs
terrane with pip and works in a clone. Nothing of terrane's sits in that
repository. `10_MODEL/model.yaml` says where the rest comes from:

    shipped_library: package        # the shipped library, from the installed terrane
    shipped_views: package          # the shipped views, before the estate's own
    requires_terrane: ">=1.0.0,<1.1"
    governance:
      repository: https://dev.azure.com/org/project/_git/governance
      ref: v1.0.0

The pin is what keeps many people on one estate drawing the same thing: a
person on another terrane is told so by `terrane validate` before their change
goes anywhere, and moving the estate to a new release is a change to the pin,
reviewed like any other. The governance pin names the organization's own
governance repository and the revision the estate is checked against. Its
shape is checked here; reading the index it names, and checking the
estate's references against it, is the governance check, not yet written.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .library import PACKAGE, SHIPPED
from .loader import read_data_file
from .places import with_places
from .query import VIEW_CATEGORIES, View, ViewError, load_views

VIEWS = "30_VIEWS"
CONFIG = Path("10_MODEL") / "model.yaml"

#: The key in `model.yaml` that reads the shipped views from the package.
SHIPPED_VIEWS = "shipped_views"
#: The key a view says it stands in for a shipped one with.
REPLACES = "replaces"
#: The key in `model.yaml` naming the terrane versions the estate is checked with.
REQUIRES = "requires_terrane"
#: The key in `model.yaml` pinning the organization's governance repository.
GOVERNANCE = "governance"
DEFAULT_INDEX = "index/governance.v1.json"

_CLAUSE = re.compile(r"^\s*(>=|<=|==|!=|>|<)\s*(\d+(?:\.\d+)*)\s*$")


def _config(root: Path) -> Dict[str, Any]:
    data = read_data_file(Path(root) / CONFIG) if (Path(root) / CONFIG).is_file() else None
    return data if isinstance(data, dict) else {}


def _installed_root() -> Path:
    from .shipped import shipped_root

    return shipped_root()


# -- views ---------------------------------------------------------------


def _replaces(view: View) -> str:
    if view.source_file is None:
        return ""
    data = read_data_file(Path(view.source_file))
    items = data if isinstance(data, list) else [data]
    for item in items:
        if isinstance(item, dict) and item.get("view_id") == view.view_id:
            return str(item.get(REPLACES) or "").strip()
    return ""


def _shipped_setting(root: Path) -> Optional[List[str]]:
    """The shipped views the estate leaves out, when it reads the shipped
    views at all; None when it does not. `shipped_views: package` takes
    them all, `{from: package, without: [...]}` all but those named."""
    setting = _config(root).get(SHIPPED_VIEWS)
    if setting in (None, "", False):
        return None
    if setting == PACKAGE:
        return []
    if isinstance(setting, dict) and setting.get("from") == PACKAGE and set(setting) <= {"from", "without"}:
        without = setting.get("without") or []
        if isinstance(without, str):
            without = [without]
        if isinstance(without, list) and all(isinstance(v, str) and v.strip() for v in without):
            return [v.strip() for v in without]
    raise ViewError("10_MODEL/model.yaml: %s is %r; it is %r, or {from: %s, without: [view ids]}"
                    % (SHIPPED_VIEWS, setting, PACKAGE, PACKAGE))


def _shipped_views(root: Path) -> Optional[List[View]]:
    """The shipped views the estate reads, the ones it leaves out taken off;
    None when it reads none, or is the repository that holds them."""
    without = _shipped_setting(root)
    if without is None:
        return None
    home = _installed_root()
    if home.resolve() == Path(root).resolve():
        return None
    shipped = load_views(home / VIEWS)
    known = {v.view_id for v in shipped}
    unknown = [v for v in without if v not in known]
    if unknown:
        # A misspelled name would leave the view in, and the estate would
        # think it had taken it out.
        raise ViewError("10_MODEL/model.yaml: %s.without names %s, which %s no shipped view"
                        % (SHIPPED_VIEWS, ", ".join(unknown), "is" if len(unknown) == 1 else "are"))
    return [v for v in shipped if v.view_id not in set(without)]


def views_of(root: Path) -> List[View]:
    """The views an estate is drawn with: its own `30_VIEWS`, after the
    shipped views when `shipped_views` says so.

    An estate's view with a shipped view's id stands in for it only when it
    says `replaces:` with that id, as a record does in a library; any other
    reuse of a shipped id is refused, naming the file. The silent shadow --
    a view of the estate's own hiding a shipped one because it was read
    second -- would leave everyone else's copy of terrane describing a view
    nobody draws. A shipped view the estate has no use for is left out by
    name, under `without`, rather than replaced by an empty one.
    """
    root = Path(root)
    own = load_views(root / VIEWS)
    shipped = _shipped_views(root)
    if shipped is None:
        return own
    shipped_ids = {v.view_id for v in shipped}
    replaced = set()
    for view in own:
        says = _replaces(view)
        where = view.source_file.name if view.source_file else view.view_id
        if says and says != view.view_id:
            raise ViewError("%s: view %r says %s: %r; a view replaces the shipped view of its own id"
                            % (where, view.view_id, REPLACES, says))
        if view.view_id in shipped_ids:
            if not says:
                raise ViewError("%s: %r is the id of a shipped view; to stand in for it, the view says "
                                "`%s: %s`, and to add a view of your own, it takes another id"
                                % (where, view.view_id, REPLACES, view.view_id))
            replaced.add(view.view_id)
        elif says:
            raise ViewError("%s: view %r replaces %r, which is not a shipped view" % (where, view.view_id, says))
    order = {name: index for index, name in enumerate(VIEW_CATEGORIES)}
    merged = [v for v in shipped if v.view_id not in replaced] + list(own)
    # Merged again with the shipped views in the list: a diagram of the
    # estate's own may place one of them.
    return with_places(sorted(merged, key=lambda v: (order.get(v.category, len(order)), v.title.lower(), v.view_id)))


def is_shipped_view(root: Path, view_id: str) -> bool:
    """Whether `view_id` is a shipped view the estate reads from the package,
    so a save of it writes a view that replaces it."""
    try:
        shipped = _shipped_views(root)
    except ViewError:
        return False
    return any(v.view_id == view_id for v in shipped or [])


def from_the_package(root: Path, view: View) -> bool:
    """Whether a view the estate draws is a shipped one read from the
    installed terrane, which the estate did not write and cannot edit."""
    if view.source_file is None or _config(root).get(SHIPPED_VIEWS) in (None, "", False):
        return False
    home = (_installed_root() / VIEWS).resolve()
    if home.parent == Path(root).resolve():
        return False
    return home in Path(view.source_file).resolve().parents


# -- the pins --------------------------------------------------------------


def _version(text: str) -> Tuple[int, ...]:
    return tuple(int(part) for part in text.split("."))


def _compare(a: Tuple[int, ...], b: Tuple[int, ...]) -> int:
    width = max(len(a), len(b))
    a, b = a + (0,) * (width - len(a)), b + (0,) * (width - len(b))
    return (a > b) - (a < b)


def version_accepted(spec: str, version: str) -> Optional[bool]:
    """Whether `version` meets every comma-separated clause of `spec`
    (`>=`, `>`, `<=`, `<`, `==`, `!=` on dotted numbers); None when the
    spec cannot be read."""
    clauses = [c for c in str(spec).split(",") if c.strip()]
    if not clauses:
        return None
    try:
        have = _version(version)
    except ValueError:
        return None
    for clause in clauses:
        m = _CLAUSE.match(clause)
        if not m:
            return None
        op, want = m.group(1), _version(m.group(2))
        c = _compare(have, want)
        ok = {">=": c >= 0, ">": c > 0, "<=": c <= 0, "<": c < 0, "==": c == 0, "!=": c != 0}[op]
        if not ok:
            return False
    return True


def problems(root: Path) -> List[Tuple[str, str]]:
    """What is wrong with the estate's pins and sources, as (code, message):
    a terrane outside the pin, a pin that cannot be read, a governance pin
    missing its repository or revision, a shipped setting with no meaning."""
    from . import __version__

    config = _config(root)
    out: List[Tuple[str, str]] = []
    spec = config.get(REQUIRES)
    if spec not in (None, ""):
        spec = str(spec)
        accepted = version_accepted(spec, __version__)
        if accepted is None:
            out.append(("estate.requires", "%s is %r, which is not a version range terrane reads "
                                            "(clauses like >=1.10.0 and <1.11, comma-separated)" % (REQUIRES, spec)))
        elif not accepted:
            out.append(("estate.requires", "this estate is checked with terrane %s, and this is terrane %s; "
                                            "install a version in range (pip install \"terrane%s\") or raise the "
                                            "pin in a change of its own" % (spec, __version__, spec.replace(" ", ""))))
    try:
        _shipped_views(root)
    except ViewError as exc:
        out.append(("estate.shipped_views", str(exc).replace("10_MODEL/model.yaml: ", "")))
    pin = config.get(GOVERNANCE)
    if pin not in (None, ""):
        if not isinstance(pin, dict):
            out.append(("estate.governance", "%s is %r; it is a mapping with a repository and a ref" % (GOVERNANCE, pin)))
        else:
            for key in ("repository", "ref"):
                if not str(pin.get(key) or "").strip():
                    out.append(("estate.governance", "%s has no %s; the estate is checked against one "
                                                      "revision of one repository" % (GOVERNANCE, key)))
            index = str(pin.get("index") or DEFAULT_INDEX)
            if index.startswith(("/", "\\")) or ".." in Path(index).parts:
                out.append(("estate.governance", "%s.index is %r; it is a path inside the governance "
                                                  "repository" % (GOVERNANCE, index)))
    return out


def pins(root: Path) -> Dict[str, str]:
    """The pins as said, for `terrane stats`: what the estate is read with."""
    config = _config(root)
    out: Dict[str, str] = {}
    if config.get(SHIPPED):
        out["library"] = "the installed terrane" if config.get(SHIPPED) == PACKAGE else str(config.get(SHIPPED))
    try:
        without = _shipped_setting(root)
    except ViewError:
        without = None
    if without is not None:
        out["shipped views"] = "the installed terrane" + (", without %s" % ", ".join(without) if without else "")
    if config.get(REQUIRES):
        out["terrane"] = str(config.get(REQUIRES))
    pin = config.get(GOVERNANCE)
    if isinstance(pin, dict) and pin.get("repository"):
        out["governance"] = "%s at %s" % (pin.get("repository"), pin.get("ref") or "(no ref)")
    return out


# -- terrane init --------------------------------------------------------------


class InitError(ValueError):
    """The folder already holds an estate, or a part of one."""


def default_requirement(version: str) -> str:
    """The minor release this terrane is: `>=1.10.0,<1.11` for 1.10.0. Any
    release of the minor draws the same; the next minor is a change to make
    on purpose."""
    parts = version.split(".")
    major, minor = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
    return ">=%s,<%d.%d" % (version, major, minor + 1)


def _quoted(text: str) -> str:
    return '"%s"' % str(text).replace("\\", "\\\\").replace('"', '\\"')


def _model_yaml(name: str, requirement: str, repository: str, ref: str) -> str:
    lines = [
        "# The estate's settings. The records are the folders beside this file,",
        "# the views of the estate's own are in 30_VIEWS, and `terrane validate` is the",
        "# gate: run it before every push.",
        "name: %s" % _quoted(name),
        "description: >",
        "  %s: the application, data and technology landscape, kept as files." % name,
        "sample_estate: false",
        "",
        "# The shipped library and the shipped views are read from the installed",
        "# terrane, and the estate is checked with the versions below: everyone",
        "# working on it installs a terrane in range, and raising the pin is a",
        "# change reviewed like any other.",
        "shipped_library: %s" % PACKAGE,
        "shipped_views: %s" % PACKAGE,
        "# To leave shipped views out, name them:",
        "# shipped_views: {from: %s, without: [harvested-estate, change-evidence-chain]}" % PACKAGE,
        "requires_terrane: %s" % _quoted(requirement),
        "",
        "# A library of the estate's own, read after the shipped one:",
        "# library_paths: [library]",
    ]
    if repository:
        lines += [
            "",
            "# The organization's governance repository and the revision this estate",
            "# is checked against; moving to a newer revision is a change of its own.",
            "governance:",
            "  repository: %s" % _quoted(repository),
            "  ref: %s" % _quoted(ref),
        ]
    return "\n".join(lines) + "\n"


def _readme(name: str) -> str:
    return "\n".join([
        "# %s" % name,
        "",
        "The architecture estate, kept as files and read by terrane",
        "(`pip install terrane`): the records under `10_MODEL/`, the views of the",
        "estate's own under `30_VIEWS/`, and the shipped library and views from",
        "the terrane `10_MODEL/model.yaml` pins.",
        "",
        "```bash",
        "terrane validate          # the gate: zero errors before a change goes up",
        "terrane stats             # what the estate holds, and what it is read with",
        "terrane render            # every view as Mermaid and SVG, under 70_ARTIFACTS/",
        "terrane draw --views      # the shipped views",
        "```",
        "",
        "What terrane writes from the model, under `70_ARTIFACTS/` and",
        "`40_SCHEMAS/`, is rebuilt on demand and not committed, so two people's",
        "pictures never conflict. A change is a branch and a pull request, and",
        "the review is the pull request.",
        "",
    ])


#: Credentials are never committed, and never kept beside the model either:
#: a connection names where its secret lives (an environment variable, a
#: secrets manager), not the secret. These lines go into every estate's
#: ignore file, the owner's own included, as the net under that rule.
SECRET_PATTERNS = (".env", ".env.*", "!.env.example", "*.pem", "*.key", "*.pfx", "*.p12",
                   "secrets.yaml", "secrets.yml", ".secrets/")
_SECRETS_BLOCK = "\n".join([
    "# Credentials never belong in the repository. A connection names where its",
    "# secret lives (an environment variable, a secrets manager), not the secret.",
] + list(SECRET_PATTERNS) + [""])

_GITIGNORE = "\n".join([
    "# What terrane writes from the model: rebuilt on demand, never committed,"
    "# so two people's pictures never conflict.",
    "70_ARTIFACTS/",
    "40_SCHEMAS/",
    "",
    "# Each person's own: the governance copy `terrane connect` fetches.",
    ".terrane/",
    "",
    "__pycache__/",
    ".venv/",
    "",
]) + "\n" + _SECRETS_BLOCK


def guard_secrets(path: Path) -> bool:
    """The credential lines added to an ignore file that lacks any of them,
    under its own lines; True when the file was changed. An Azure DevOps or
    GitHub repository often starts with an ignore file of its own, and
    keeping it as it was left it without them."""
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    have = {line.strip() for line in text.splitlines()}
    if all(p in have for p in SECRET_PATTERNS):
        return False
    missing = [p for p in SECRET_PATTERNS if p not in have]
    block = "\n".join(_SECRETS_BLOCK.splitlines()[:2] + missing) + "\n"
    path.write_text(text + ("" if not text or text.endswith("\n") else "\n") + ("\n" if text else "") + block,
                    encoding="utf-8", newline="\n")
    return True

_VIEWS_README = "\n".join([
    "# Views of this estate's own",
    "",
    "The shipped views come from the installed terrane (`terrane draw --views` lists",
    "them). A view here is read after them; one with a shipped view's id stands",
    "in for it only when it says `replaces:` with that id.",
    "",
])


def init_estate(folder: Path, name: str, version: str, repository: str = "", ref: str = "",
                requirement: str = "") -> Tuple[List[Path], List[Path]]:
    """Write a new estate into `folder`, and say what was written and what
    was already there and left alone. A folder that already holds an estate,
    or views or library layers of one, is refused rather than mixed into."""
    from .library import LAYER_FOLDERS

    folder = Path(folder)
    if (folder / CONFIG).exists():
        raise InitError("%s already holds an estate (%s)" % (folder, CONFIG.as_posix()))
    taken = [p for p in ("10_MODEL", VIEWS) + tuple(LAYER_FOLDERS) if (folder / p).exists()]
    if taken:
        raise InitError("%s already holds %s; an estate is started in a folder without them"
                        % (folder, ", ".join(taken)))
    if bool(repository) != bool(ref):
        raise InitError("a governance pin is a repository and a ref together")
    if not name.strip():
        raise InitError("an estate has a name")
    requirement = requirement or default_requirement(version)
    if version_accepted(requirement, version) is None:
        raise InitError("%r is not a version range terrane reads" % requirement)
    files = {
        CONFIG: _model_yaml(name.strip(), requirement, repository, ref),
        Path(VIEWS) / "README.md": _VIEWS_README,
        Path("README.md"): _readme(name.strip()),
        Path(".gitignore"): _GITIGNORE,
    }
    written, kept = [], []
    for rel, text in files.items():
        path = folder / rel
        if path.exists():
            # An Azure DevOps or GitHub repository starts with a README and
            # often a .gitignore; they are the owner's, and stay as they are,
            # save that an ignore file gains the credential lines it lacks.
            if rel == Path(".gitignore") and guard_secrets(path):
                written.append(path)
                continue
            kept.append(path)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        written.append(path)
    return written, kept
