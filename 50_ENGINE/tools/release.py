"""Publish the package to PyPI from this machine: a release, by hand.

    python tools/release.py                 (from 50_ENGINE) every check, the sdist and wheel built and proved, nothing sent
    python tools/release.py --upload --test the same, then those two sent to TestPyPI, nothing tagged
    python tools/release.py --upload        the same, then those two sent to PyPI and the commit tagged

A release is made on a machine, in this order, stopping at the first thing
that fails:

1. the version in `terrane/__init__.py` is not on PyPI yet, and the tag
   `v<version>` is free or already on this commit (PyPI never takes a
   version back, so a mistake is fixed by the next one);
2. both estates pass the gate, zero errors;
3. `tools/wheel_check.py` builds the sdist, the wheel from the sdist, and
   proves the wheel from an empty folder;
4. `twine check --strict` reads both files' metadata as PyPI will.

An upload also wants the working tree clean and HEAD to be what origin/main
has, so what is on PyPI is a commit anyone can check out; a dry run says
when it is not and goes on. With `--upload`, `twine upload` sends the sdist
and the wheel step 3 proved, and `v<version>` is tagged on HEAD and pushed. twine reads the
credentials from `~/.pypirc` or TWINE_USERNAME / TWINE_PASSWORD, or asks:
the user name is `__token__` and the password a PyPI API token (a TestPyPI
one with `--test`: the two indexes have separate accounts). The first
upload creates the project, so that token has to be scoped to the whole
account; swap it for one scoped to `terrane` afterward. Try a version on
TestPyPI first (`pip install --index-url https://test.pypi.org/simple/
terrane`): neither index ever takes a version back.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
REPO = ENGINE.parent
NAME = "terrane"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wheel_check  # noqa: E402


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=str(REPO), capture_output=True, text=True, check=True).stdout.strip()


def _version() -> str:
    text = (ENGINE / "terrane" / "__init__.py").read_text(encoding="utf-8")
    return re.search(r'^__version__ = "([^"]+)"$', text, re.M).group(1)


#: The index a release goes to: where it is looked up, and where twine sends it.
INDEXES = {
    "PyPI": ("https://pypi.org", "https://upload.pypi.org/legacy/"),
    "TestPyPI": ("https://test.pypi.org", "https://test.pypi.org/legacy/"),
}


def _on_pypi(version: str, index: str = "PyPI") -> bool:
    # A 404 is a version (or a project) the index has never seen; any other
    # answer that is not 200 is not one to guess past.
    url = "%s/pypi/%s/%s/json" % (INDEXES[index][0], NAME, version)
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return response.status == 200
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return False
        raise


def _run(args: list, cwd: Path = ENGINE) -> bool:
    return subprocess.run(args, cwd=str(cwd)).returncode == 0


def _stop(message: str) -> int:
    print("release stopped: " + message, file=sys.stderr)
    return 1


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check, build, prove and (with --upload) publish the package to PyPI.")
    parser.add_argument("--upload", action="store_true", help="upload the proved sdist and wheel and tag the commit")
    parser.add_argument("--test", action="store_true", help="TestPyPI instead of PyPI, and nothing tagged")
    args = parser.parse_args(argv)
    index = "TestPyPI" if args.test else "PyPI"
    version = _version()
    tag = "v" + version
    print("%s %s, tag %s" % (NAME, version, tag))

    _git("fetch", "--quiet", "origin", "main", "--tags")
    head = _git("rev-parse", "HEAD")
    unpublishable = []
    if _git("status", "--porcelain"):
        unpublishable.append("the working tree has changes")
    if head != _git("rev-parse", "origin/main"):
        unpublishable.append("HEAD is not origin/main")
    if unpublishable and args.upload:
        return _stop("; ".join(unpublishable) + ". A release is a commit on main, pushed.")
    for reason in unpublishable:
        print("(an upload would stop here: %s)" % reason)

    if _on_pypi(version, index):
        return _stop("%s %s is already on %s; raise __version__ in terrane/__init__.py." % (NAME, version, index))
    tagged = subprocess.run(["git", "rev-parse", "-q", "--verify", "refs/tags/%s^{commit}" % tag], cwd=str(REPO),
                            capture_output=True, text=True).stdout.strip()
    if tagged and tagged != head:
        return _stop("%s already tags %s, not HEAD." % (tag, tagged[:7]))
    print("%s is not on %s, and %s is %s" % (version, index, tag, "on HEAD" if tagged else "free"))

    if not _run([sys.executable, "-m", "terrane", "validate"]):
        return _stop("the sample estate fails the gate.")
    if not _run([sys.executable, "-m", "terrane", "--root", "../90_EXAMPLE/thurman-health", "validate"]):
        return _stop("the second estate fails the gate.")
    print("both estates pass the gate")

    try:
        wheel_check.main()
    except (AssertionError, subprocess.CalledProcessError) as error:
        return _stop("the wheel check failed: %s" % error)
    # Both, by name: `dist/` keeps what earlier checks proved, and only this
    # version's two files are what the check just built.
    files = [REPO / "dist" / ("%s-%s.tar.gz" % (NAME, version)),
             REPO / "dist" / ("%s-%s-py3-none-any.whl" % (NAME, version))]
    for made in files:
        if not made.is_file():
            return _stop("the wheel check built no %s." % made.name)
    wheel = files[1]
    if not _run([sys.executable, "-m", "twine", "check", "--strict"] + [str(f) for f in files]):
        return _stop("twine does not pass the sdist or the wheel (pip install twine, if it is not installed).")

    if not args.upload:
        print("ready: %s and %s, proved; nothing was sent. --upload sends them and tags %s."
              % (files[0].name, wheel.name, tag))
        return 0
    if not _run([sys.executable, "-m", "twine", "upload", "--repository-url", INDEXES[index][1]]
                + [str(f) for f in files]):
        return _stop("the upload failed; nothing is tagged.")
    if args.test:
        print("on TestPyPI: %s/project/%s/%s/ (nothing tagged). Try it in a fresh environment:\n"
              "  pip install --index-url https://test.pypi.org/simple/ %s==%s"
              % (INDEXES[index][0], NAME, version, NAME, version))
        return 0
    if not tagged:
        _git("tag", "-a", tag, "-m", "%s %s" % (NAME, version))
    if not _run(["git", "push", "origin", tag], cwd=REPO):
        return _stop("%s is on PyPI, but pushing %s failed; push it by hand." % (wheel.name, tag))
    print("released: https://pypi.org/project/%s/%s/ and %s pushed" % (NAME, version, tag))
    return 0


if __name__ == "__main__":
    sys.exit(main())
