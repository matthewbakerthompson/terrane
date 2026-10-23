"""A person's working copy of an estate: the clone, and the governance it is
checked against beside it.

An organization keeps its estate in a repository of its own, in Azure DevOps
or wherever its code is, and everyone on it works in a clone. `terrane
connect URL` makes that clone, and fetches the governance repository the
estate's `model.yaml` pins into `.terrane/governance/`, checked out at the
pinned revision and read, never written. Run in a clone made some other way
-- from Azure DevOps's own page, from an editor -- it does the second part
alone.

Everything goes through `git` itself, so signing in is git's: the credential
manager that ships with Git for Windows already knows Azure DevOps and
GitHub, and terrane holds no password or token. `.terrane/` is the person's
own and is never committed; it is named in the clone's `.git/info/exclude`,
which needs no change to the repository, so an estate whose `.gitignore`
predates it is no different.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List, NamedTuple, Optional

from .estate import DEFAULT_INDEX, GOVERNANCE, _config

#: The person's own folder in a clone: never committed.
WORKSPACE = ".terrane"
GOVERNANCE_DIR = Path(WORKSPACE) / "governance"


class WorkspaceError(RuntimeError):
    """git is missing, a clone or a fetch failed, or the folder is not an estate."""


class Connected(NamedTuple):
    root: Path
    cloned: bool
    governance: Optional[Path]
    governance_ref: str
    governance_commit: str
    notes: List[str]


def _git(args: List[str], cwd: Optional[Path] = None) -> str:
    if shutil.which("git") is None:
        raise WorkspaceError("git is not on the path; terrane works through git, and signs in with it")
    # core.longpaths: the estate's generated folders are deep, and Windows
    # refuses the paths without it.
    run = subprocess.run(["git", "-c", "core.longpaths=true", *args], cwd=str(cwd) if cwd else None,
                         capture_output=True, text=True)
    if run.returncode != 0:
        said = (run.stderr or run.stdout).strip().splitlines()
        raise WorkspaceError("git %s failed: %s" % (args[0], said[-1] if said else "exit %d" % run.returncode))
    return run.stdout.strip()


def _name_of(url: str) -> str:
    """The folder a clone of `url` goes in, as git names it."""
    tail = url.rstrip("/\\").replace("\\", "/").rsplit("/", 1)[-1]
    return tail[:-4] if tail.endswith(".git") else tail


def _exclude(root: Path) -> None:
    """Keep `.terrane/` out of every commit from this clone, without a change
    to the repository the others would have to review."""
    exclude = Path(_git(["rev-parse", "--git-path", "info/exclude"], root))
    exclude = exclude if exclude.is_absolute() else root / exclude
    line = WORKSPACE + "/"
    have = exclude.read_text(encoding="utf-8").splitlines() if exclude.is_file() else []
    if line not in have:
        exclude.parent.mkdir(parents=True, exist_ok=True)
        with exclude.open("a", encoding="utf-8", newline="\n") as f:
            if have and have[-1] != "":
                f.write("\n")
            f.write("# The person's own terrane workspace: never committed.\n%s\n" % line)


def governance_pin(root: Path) -> Optional[dict]:
    pin = _config(root).get(GOVERNANCE)
    if isinstance(pin, dict) and str(pin.get("repository") or "").strip() and str(pin.get("ref") or "").strip():
        return {"repository": str(pin["repository"]).strip(), "ref": str(pin["ref"]).strip(),
                "index": str(pin.get("index") or DEFAULT_INDEX)}
    return None


def governance_index(root: Path) -> Optional[Path]:
    """The governance index this clone fetched for the estate's pin, or None
    when there is no pin, no fetch yet, or no index where the pin says."""
    pin = governance_pin(root)
    if pin is None:
        return None
    path = Path(root) / GOVERNANCE_DIR / pin["index"]
    return path if path.is_file() else None


def fetch_governance(root: Path) -> Optional[tuple]:
    """Fetch the pinned governance repository into `.terrane/governance/` at
    the pinned revision; (path, commit) or None when the estate pins none.
    A clone already there is fetched and moved to the pin, so a raised pin
    is one `terrane connect` away; it is the person's read-only copy, and a
    change made in it is overwritten."""
    root = Path(root)
    pin = governance_pin(root)
    if pin is None:
        return None
    target = root / GOVERNANCE_DIR
    if not (target / ".git").exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        _git(["clone", "--quiet", "--no-checkout", pin["repository"], str(target)])
    else:
        _git(["remote", "set-url", "origin", pin["repository"]], target)
        _git(["fetch", "--quiet", "--tags", "--force", "origin"], target)
    ref = pin["ref"]
    # A tag or a commit as written, else a branch of that name on the remote.
    for candidate in (ref, "origin/" + ref):
        try:
            commit = _git(["rev-parse", "--verify", "--quiet", candidate + "^{commit}"], target)
            break
        except WorkspaceError:
            continue
    else:
        raise WorkspaceError("the governance repository has no revision %r (governance.ref in 10_MODEL/model.yaml)"
                             % ref)
    _git(["-c", "advice.detachedHead=false", "checkout", "--quiet", "--force", commit], target)
    return target, commit


def connect(url: str = "", into: Optional[Path] = None, here: Optional[Path] = None) -> Connected:
    """Clone the estate at `url` into `into` (default: a folder named as git
    names it, in the current one), or take the clone `here` when there is no
    url; then fetch the governance it pins."""
    notes: List[str] = []
    if url:
        target = Path(into) if into else Path.cwd() / _name_of(url)
        if target.exists() and any(target.iterdir()):
            raise WorkspaceError("%s is already there and not empty; name another folder with --into" % target)
        _git(["clone", "--quiet", url, str(target)])
        cloned = True
    else:
        # The clone's top, wherever in it the person stood.
        target = Path(_git(["rev-parse", "--show-toplevel"], Path(here or Path.cwd())))
        cloned = False
    target = target.resolve()
    if not (target / "10_MODEL" / "model.yaml").is_file():
        raise WorkspaceError("%s is a clone with no estate in it (no 10_MODEL/model.yaml); `terrane init` starts one"
                             % target)
    _exclude(target)
    fetched = fetch_governance(target)
    pin = governance_pin(target)
    if fetched is None:
        notes.append("the estate pins no governance repository; `governance:` in 10_MODEL/model.yaml names one")
        return Connected(target, cloned, None, "", "", notes)
    path, commit = fetched
    if governance_index(target) is None:
        notes.append("the governance repository at %s has no %s" % (pin["ref"], pin["index"]))
    return Connected(target, cloned, path, pin["ref"], commit, notes)
