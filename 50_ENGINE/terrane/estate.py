"""An estate in a repository of its own: the views it is drawn with, the
versions it is checked with, the files `terrane init` starts it from, and
the copy of the sample estate `terrane init --sample` makes.

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
from .shipped import HOME
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


def _refuse_taken(folder: Path, also: Sequence[str] = ()) -> None:
    from .library import LAYER_FOLDERS

    if (folder / CONFIG).exists():
        raise InitError("%s already holds an estate (%s)" % (folder, CONFIG.as_posix()))
    names = dict.fromkeys(("10_MODEL", VIEWS) + tuple(LAYER_FOLDERS) + tuple(also))
    taken = [p for p in names if (folder / p).exists()]
    if taken:
        raise InitError("%s already holds %s; an estate is started in a folder without them"
                        % (folder, ", ".join(taken)))


def _requirement(requirement: str, version: str) -> str:
    requirement = requirement or default_requirement(version)
    if version_accepted(requirement, version) is None:
        raise InitError("%r is not a version range terrane reads" % requirement)
    return requirement


def init_estate(folder: Path, name: str, version: str, repository: str = "", ref: str = "",
                requirement: str = "") -> Tuple[List[Path], List[Path]]:
    """Write a new estate into `folder`, and say what was written and what
    was already there and left alone. A folder that already holds an estate,
    or views or library layers of one, is refused rather than mixed into."""
    folder = Path(folder)
    _refuse_taken(folder)
    if bool(repository) != bool(ref):
        raise InitError("a governance pin is a repository and a ref together")
    if not name.strip():
        raise InitError("an estate has a name")
    requirement = _requirement(requirement, version)
    files = {
        CONFIG: _model_yaml(name.strip(), requirement, repository, ref),
        Path(VIEWS) / "README.md": _VIEWS_README,
        Path("README.md"): _readme(name.strip()),
        Path(".gitignore"): _GITIGNORE,
    }
    return _write_files(folder, files)


def _write_files(folder: Path, files: Dict[Path, str]) -> Tuple[List[Path], List[Path]]:
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


# -- terrane init --sample -------------------------------------------------------

#: The sample estate beside its settings: the records, and the sources its
#: pages read -- the inventory kept as a source, the CMDB export the drift
#: page compares against, the aliases a harvested record's refusal names.
SAMPLE_FOLDERS = ("10_MODEL", "60_SOURCES")
#: The key in `model.yaml` that says the model is the sample estate.
SAMPLE = "sample_estate"


def _sample_yaml(text: str, version: str, requirement: str) -> str:
    """The sample's settings for a copy of it: every one it has, with the
    paragraph on what it is in the repository (where `terrane refresh` seeds
    the engine's tests from it) swapped for what the copy is, and the lines
    an estate of one's own has, which read the shipped library and views
    from the installed terrane. The description is the copy's own too: the
    repository's is written to outlast `terrane clear`, and names the app's
    folder. Swapped by key, not by line, so a sample whose settings are
    reworded still copies."""
    from .compose import _blocks

    head, blocks = _blocks(text.splitlines(), 0)
    lines = list(head)
    for key, block in blocks:
        if key == "description":
            lines += list(block.lead) + [
                "description: >",
                "  A made-up card issuer's application, data and technology landscape: the",
                "  sample estate terrane ships with, here to show what a full estate draws.",
            ]
        elif key == SAMPLE:
            lines += [
                "",
                "# Copied out of terrane %s by `terrane init --sample`: a copy of its own," % version,
                "# to open in the app and change. An estate of your own starts empty, with",
                "# `terrane init`.",
                "%s: true" % SAMPLE,
                "",
                "# The shipped library and the shipped views are read from the installed",
                "# terrane, and the sample is checked with the release it was copied from.",
                "%s: %s" % (SHIPPED, PACKAGE),
                "%s: %s" % (SHIPPED_VIEWS, PACKAGE),
                "%s: %s" % (REQUIRES, _quoted(requirement)),
            ]
        elif key not in (SHIPPED, SHIPPED_VIEWS, REQUIRES, GOVERNANCE):
            lines += block.lines()
    return "\n".join(lines).rstrip("\n") + "\n"


def _sample_readme(version: str) -> str:
    return "\n".join([
        "# The sample estate",
        "",
        "A made-up card issuer, here to show what a full estate draws, copied out of",
        "terrane %s by `terrane init --sample`. The records are under `10_MODEL/`," % version,
        "the inventory and the CMDB export the app's Sources and Drift pages read",
        "are under `60_SOURCES/`, and the shipped library and views come from the",
        "installed terrane, as `10_MODEL/model.yaml` says.",
        "",
        "```bash",
        "terrane app               # the app on this folder; a first visit offers a two-minute tour",
        "terrane validate          # the gate: no errors, and the warnings the sample is there to show",
        "terrane render            # every view as Mermaid and SVG, under 70_ARTIFACTS/",
        "```",
        "",
        "The copy is yours to change. A fresh one is `terrane init --sample` into",
        "another folder, and an estate of your own starts empty, with `terrane init`.",
        "",
        "The comments in its files were written in terrane's repository, and the",
        "folders they name, `00_METHOD/` and `50_ENGINE/` among them, are there:",
        "%s." % HOME,
        "",
    ])


def init_sample(folder: Path, version: str, requirement: str = "",
                source: Optional[Path] = None) -> Tuple[List[Path], List[Path]]:
    """Copy the sample estate into `folder`, out of the installed terrane
    (in a clone, out of the repository), with settings that read the shipped
    library and views from the package as an estate `terrane init` starts
    does; and say, as `init_estate` does, what was written and what was
    kept. The package's own copy is never opened in place: the app writes
    where it reads, and an edit there would land in site-packages and go
    with the next upgrade."""
    source = Path(source) if source is not None else _installed_root()
    folder = Path(folder)
    if not _config(source).get(SAMPLE):
        raise InitError("%s holds no sample estate: its %s does not say %s: true"
                        % (source, CONFIG.as_posix(), SAMPLE))
    where = folder.resolve()
    for home in [Path(__file__).resolve().parent] + [(source / name).resolve() for name in SAMPLE_FOLDERS]:
        if where == home or home in where.parents:
            raise InitError("%s is inside %s; the sample is copied out, into a folder of your own" % (folder, home))
    _refuse_taken(folder, SAMPLE_FOLDERS)
    requirement = _requirement(requirement, version)
    written: List[Path] = []
    for name in SAMPLE_FOLDERS:
        if not (source / name).is_dir():
            continue
        # File by file rather than copytree, which hands the package's
        # modes on: from a read-only install (a system Python, a container
        # image) the app could not have saved a record into the copy.
        for path in sorted((source / name).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                target = folder / path.relative_to(source)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(path.read_bytes())
        written.append(folder / name)
    text = (source / CONFIG).read_text(encoding="utf-8-sig")
    (folder / CONFIG).write_text(_sample_yaml(text, version, requirement), encoding="utf-8", newline="\n")
    more, kept = _write_files(folder, {
        Path(VIEWS) / "README.md": _VIEWS_README,
        Path("README.md"): _sample_readme(version),
        Path(".gitignore"): _GITIGNORE,
    })
    return written + more, kept
