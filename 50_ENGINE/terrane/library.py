"""Where the library is read from: the shipped folders, and an organization's
own beside them.

Each layer of the library is a numbered folder at the repository root -- the
shapes, connection kinds, component types, blocks, patterns, parts and build
types -- with ids global within the layer. An organization that wanted
patterns of its own had to edit the shipped files or fork them, and every
release of the method's library was then a merge. `library_paths` in
`10_MODEL/model.yaml` names folders of the organization's own, each holding
any of the same layer folders, read after the shipped ones and in the order
listed.

A record in a later library stands in for one read before it only when it
says so, with `replaces:` and its own id. Any other id already taken is the
error it always was, naming both files. The silent shadow -- the
organization's file winning because it happened to be read second -- is the
outcome the rule exists to make impossible: the catalog would describe one
record and every product would be built from the other.

A second estate kept inside the repository is a root of its own, with
its own model and
views and no copy of the shipped library: `shipped_library` in its
`model.yaml` names the repository it sits in, and the shipped layers are
read from there, before any library of the estate's own. A copy of
the library beside it would be a second library that drifts from the first,
and the estate would stop proving what it is there to prove, that one
library builds both.

An estate in a repository of its own, with terrane installed from pip,
has no repository above it to name: `shipped_library: package` reads the
shipped layers from the installed package instead, so every person on the
estate builds from the library of the terrane they pinned, and an upgrade
is a change to the pin rather than a copy to merge.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Tuple, Type

from .loader import load_folder, read_data_file

#: Every layer folder, in the order the library reads up: shapes, then what
#: they are made of.
LAYER_FOLDERS = (
    "20_ARCHETYPES", "24_CONNECTIONS", "25_COMPONENTS", "26_BLOCKS", "27_PATTERNS",
    "28_MODULES", "29_TYPES",
)

#: The key in `10_MODEL/model.yaml`.
SETTING = "library_paths"

#: The key in an estate's `10_MODEL/model.yaml` naming the repository whose
#: shipped library it is built from.
SHIPPED = "shipped_library"

#: What `shipped_library` says for the library inside the installed package.
PACKAGE = "package"

#: The key a record says it stands in for an earlier one with.
REPLACES = "replaces"


class LibraryError(ValueError):
    """Raised when a component type or block is malformed or dangling, or the
    libraries `model.yaml` names cannot be read."""


class LibraryRoot(NamedTuple):
    path: Path
    #: As `library_paths` names it, or "" for the shipped library.
    name: str

    @property
    def label(self) -> str:
        return self.name or "the shipped library"


#: model.yaml's `library_paths`, by the file's identity: the loaders ask for
#: the roots several times a request, and the answer only changes with the
#: file.
_SETTINGS: Dict[Tuple[str, int, int], List[str]] = {}

#: model.yaml's `shipped_library`, the same way.
_SHIPPED: Dict[Tuple[str, int, int], str] = {}


def _config_key(root: Path) -> Optional[Tuple[str, int, int]]:
    config = Path(root) / "10_MODEL" / "model.yaml"
    if not config.is_file():
        return None
    stat = config.stat()
    return (str(config.resolve()), stat.st_mtime_ns, stat.st_size)


def shipped_name(root: Path) -> str:
    """What `shipped_library` names, as written and normalized, or "" when
    the estate names none. The name alone, unresolved: the export of a
    revision reads it to fetch that library from the same revision before
    `shipped_root` goes looking for it."""
    root = Path(root)
    key = _config_key(root)
    if key is None:
        return ""
    if key not in _SHIPPED:
        data = read_data_file(Path(key[0])) or {}
        raw = data.get(SHIPPED) if isinstance(data, dict) else None
        if raw in (None, ""):
            _SHIPPED[key] = ""
        elif isinstance(raw, str) and raw.strip():
            _SHIPPED[key] = Path(raw.strip()).as_posix()
        else:
            raise LibraryError(
                "10_MODEL/model.yaml: %s is a folder, not %r" % (SHIPPED, raw)
            )
    return _SHIPPED[key]


def shipped_root(root: Path) -> Path:
    """Where the shipped library is read from: the root itself, or the
    repository an estate inside it names with `shipped_library`.

    Only an enclosing folder is taken. The reason a named library must sit
    inside the repository holds here too -- a library CI never sees is one a
    review of the model cannot review -- and an estate that held layer
    folders of its own and named another library as well would be read from
    one and look as if it were read from the other, so that is refused too.
    """
    root = Path(root)
    named = shipped_name(root)
    if not named:
        return root
    if named == PACKAGE:
        own = [layer for layer in LAYER_FOLDERS if (root / layer).is_dir()]
        if own:
            raise LibraryError(
                "10_MODEL/model.yaml: %s is %r, and this estate holds %s of its own; a "
                "library of the estate's own goes in a folder `%s` names"
                % (SHIPPED, PACKAGE, ", ".join(own), SETTING)
            )
        # The repository when terrane runs from a clone of it, the copies
        # inside the wheel when it is installed: the same library either way.
        from .shipped import shipped_root as installed

        return installed().resolve()
    path = (root / named).resolve()
    if path not in root.resolve().parents:
        raise LibraryError(
            "10_MODEL/model.yaml: %s names %r, which does not hold this estate; an estate "
            "is read with the library of the repository it sits in" % (SHIPPED, named)
        )
    if not any((path / layer).is_dir() for layer in LAYER_FOLDERS):
        raise LibraryError(
            "10_MODEL/model.yaml: %s names %r, which holds none of %s"
            % (SHIPPED, named, ", ".join(LAYER_FOLDERS))
        )
    own = [layer for layer in LAYER_FOLDERS if (root / layer).is_dir()]
    if own:
        raise LibraryError(
            "10_MODEL/model.yaml: %s names %r, and this estate holds %s of its own; a "
            "library of the estate's own goes in a folder `%s` names"
            % (SHIPPED, named, ", ".join(own), SETTING)
        )
    return path


def from_package(root: Path) -> bool:
    """Whether the estate reads the shipped library from the installed
    package, which no revision of the estate's own repository holds."""
    try:
        return shipped_name(root) == PACKAGE
    except LibraryError:
        return False


def named_paths(root: Path) -> List[str]:
    key = _config_key(root)
    if key is None:
        return []
    if key not in _SETTINGS:
        data = read_data_file(Path(key[0])) or {}
        raw = data.get(SETTING) if isinstance(data, dict) else None
        if raw in (None, ""):
            named: List[str] = []
        elif isinstance(raw, str):
            named = [raw]
        elif isinstance(raw, list) and all(isinstance(item, str) for item in raw):
            named = list(raw)
        else:
            raise LibraryError(
                "10_MODEL/model.yaml: %s is a list of folders, not %r" % (SETTING, raw)
            )
        # As a person would write it back: `./ours/` and `ours` are one name.
        _SETTINGS[key] = [Path(n.strip()).as_posix() for n in named if n.strip()]
    return list(_SETTINGS[key])


def library_roots(root: Path) -> List[LibraryRoot]:
    """The shipped library, then each folder `library_paths` names.

    A named folder that is not there, lies outside the repository, or holds
    a folder no layer is called, is refused rather than skipped: each way
    the organization's library would quietly not be read, and a typo would
    look like an empty library.
    """
    root = Path(root)
    shipped = shipped_root(root)
    roots = [LibraryRoot(shipped, "")]
    seen = {root.resolve(), shipped.resolve()}
    for name in named_paths(root):
        path = root / name
        if path.resolve() != root.resolve() and root.resolve() not in path.resolve().parents:
            # A library beside the checkout is one CI never sees, and a
            # review of the model could not review it.
            raise LibraryError(
                "10_MODEL/model.yaml: %s names %r, which is outside the repository; "
                "a library is reviewed where the model is" % (SETTING, name)
            )
        if not path.is_dir():
            raise LibraryError(
                "10_MODEL/model.yaml: %s names %r, which is not a folder in the repository"
                % (SETTING, name)
            )
        if path.resolve() in seen:
            raise LibraryError(
                "10_MODEL/model.yaml: %s names %r twice, or names the shipped library; "
                "each library is read once" % (SETTING, name)
            )
        seen.add(path.resolve())
        for child in sorted(path.iterdir(), key=lambda p: p.name.lower()):
            if child.is_dir() and not child.name.startswith((".", "_")) and child.name not in LAYER_FOLDERS:
                raise LibraryError(
                    "%s/%s is not a layer of the library, so nothing in it would be read; "
                    "the layers are %s" % (name, child.name, ", ".join(LAYER_FOLDERS))
                )
        roots.append(LibraryRoot(path, name))
    return roots


def own_root(root: Path) -> LibraryRoot:
    """Where the app writes a new part or shape: the first library
    `library_paths` names, or the shipped one when it names none. A save
    never edits the shipped library while the model keeps one of its own."""
    roots = library_roots(root)
    return roots[1] if len(roots) > 1 else roots[0]


def shown(root: Path, path: Any) -> str:
    """A file as a message names it: from the repository root, with forward
    slashes on every platform."""
    if path is None:
        return ""
    # From the estate's root first, then from the repository whose library
    # an estate reads, so a shipped file is named the same from either.
    for base in (Path(root), _shipped_quietly(root)):
        try:
            return Path(path).resolve().relative_to(base.resolve()).as_posix()
        except ValueError:
            continue
    return str(path)


def _shipped_quietly(root: Path) -> Path:
    """`shipped_root`, for naming a file in a message: a setting that is
    wrong is the load's to report, not the message's."""
    try:
        return shipped_root(Path(root))
    except LibraryError:
        return Path(root)


def library_of(root: Path, path: Any) -> str:
    """The name of the library a file was read from: "" for the shipped one."""
    if path is None:
        return ""
    resolved = Path(path).resolve()
    for base in reversed(library_roots(root)):
        if base.name and base.path.resolve() in resolved.parents:
            return base.name
    return ""


def load_layer(
    root: Path,
    folder: str,
    parse: Callable[[Any, Path], Any],
    id_of: Callable[[Any], str],
    what: str,
    error: Type[Exception] = LibraryError,
) -> Dict[str, Any]:
    """Every record of one layer, the shipped library's first, each named
    library's after, keyed by id in reading order.

    A record that replaces another takes its place in that order, so a kind
    the catalog lists third is still listed third once an organization has
    rewritten it. Each record comes back with `library` set to where it was
    read from and, for a replacement, `replaced` to the file it stands in for.
    """
    try:
        roots = library_roots(root)
    except LibraryError as exc:
        raise error(str(exc))
    out: Dict[str, Any] = {}
    held: Dict[str, Tuple[Path, int]] = {}
    for index, base in enumerate(roots):
        for path, data in load_folder(base.path / folder):
            record = parse(data, path)
            key = id_of(record)
            claim = data.get(REPLACES) if isinstance(data, dict) else None
            claim = "" if claim is None else str(claim).strip()
            if claim:
                if claim != key:
                    raise error(
                        "%s: %s %s says it replaces %r, but a replacement keeps the id of what "
                        "it replaces, so that everything naming it is given this one. Give it "
                        "the id %s to replace that one, or drop `replaces` to add it beside"
                        % (shown(root, path), what, key, claim, claim)
                    )
                if key not in held:
                    raise error(
                        "%s: %s %s replaces nothing; no library read before %s has one by that id"
                        % (shown(root, path), what, key, base.label)
                    )
                earlier, earlier_index = held[key]
                if earlier_index == index:
                    raise error(
                        "%s %s is in %s and in %s, both in %s; a record replaces one from a "
                        "library read before its own, never one beside it"
                        % (what, key, shown(root, earlier), shown(root, path), base.label)
                    )
                record = record._replace(library=base.name, replaced=shown(root, earlier))
            elif key in held:
                earlier, earlier_index = held[key]
                hint = ""
                if earlier_index < index:
                    hint = (
                        "; the second may stand in for the first only by saying `%s: %s`"
                        % (REPLACES, key)
                    )
                raise error(
                    "duplicate %s %r in %s and %s%s"
                    % (what, key, shown(root, earlier), shown(root, path), hint)
                )
            elif base.name:
                record = record._replace(library=base.name)
            out[key] = record
            held[key] = (path, index)
    return out


def summary(root: Path, layers: Dict[str, Dict[str, Any]]) -> List[Tuple[str, Dict[str, Tuple[int, int]]]]:
    """For each named library, by layer, how many records it adds and how
    many it replaces: what the catalog index says about the libraries read.
    `layers` maps a layer's plural name to its loaded records."""
    out = []
    for base in library_roots(root)[1:]:
        counts: Dict[str, Tuple[int, int]] = {}
        for layer, records in layers.items():
            mine = [r for r in records.values() if getattr(r, "library", "") == base.name]
            if mine:
                replaced = sum(1 for r in mine if getattr(r, "replaced", ""))
                counts[layer] = (len(mine) - replaced, replaced)
        out.append((base.name, counts))
    return out
