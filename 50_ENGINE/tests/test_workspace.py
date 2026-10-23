"""`terrane connect`: a person's clone of an estate, and the governance it
pins fetched beside it.

Two bare repositories in a temporary folder stand in for an organization's
Azure DevOps project: a governance repository with two tagged revisions of
its index, and an estate started by `terrane init` that pins the first.
Nothing here reaches a network, and each test removes exactly the folder it
made.
"""

from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import __version__, cli  # noqa: E402
from terrane.estate import init_estate  # noqa: E402
from terrane.workspace import (  # noqa: E402
    GOVERNANCE_DIR, WorkspaceError, connect, governance_index, governance_pin,
)

GIT = ["git", "-c", "user.name=terrane-test", "-c", "user.email=terrane-test@example.com",
       "-c", "init.defaultBranch=main", "-c", "core.longpaths=true"]


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(GIT + list(args), cwd=str(cwd), capture_output=True, text=True, check=True).stdout.strip()


@unittest.skipIf(shutil.which("git") is None, "git is not installed")
class _Remotes(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="aac-connect-"))
        self.addCleanup(shutil.rmtree, self.tmp, onerror=self._writable)
        self.governance_remote = self._governance()
        self.estate_remote = self._estate("v1.0.0")

    @staticmethod
    def _writable(func, path, _info) -> None:
        # git marks its pack files read-only, and Windows will not remove
        # those until they are writable again; this is the tree the test made.
        import os
        import stat

        os.chmod(path, stat.S_IWRITE)
        func(path)

    def _governance(self) -> Path:
        work = self.tmp / "governance-work"
        work.mkdir()
        git("init", "-q", cwd=work)
        (work / "index").mkdir()
        for tag, patterns in (("v1.0.0", ["PAT-001"]), ("v1.1.0", ["PAT-001", "PAT-002"])):
            index = {"format": "governance-index/1", "patterns": [{"id": p} for p in patterns]}
            (work / "index" / "governance.v1.json").write_text(json.dumps(index), encoding="utf-8")
            git("add", "-A", cwd=work)
            git("commit", "-qm", "governance " + tag, cwd=work)
            git("tag", tag, cwd=work)
        remote = self.tmp / "governance.git"
        git("clone", "-q", "--bare", str(work), str(remote), cwd=self.tmp)
        return remote

    def _estate(self, ref: str) -> Path:
        work = self.tmp / "estate-work"
        work.mkdir()
        git("init", "-q", cwd=work)
        (work / "README.md").write_text("# Contoso architecture\n", encoding="utf-8")
        init_estate(work, "Contoso Architecture", __version__, repository=str(self.governance_remote), ref=ref)
        git("add", "-A", cwd=work)
        git("commit", "-qm", "the estate", cwd=work)
        remote = self.tmp / "contoso-architecture.git"
        git("clone", "-q", "--bare", str(work), str(remote), cwd=self.tmp)
        return remote


class TestConnect(_Remotes):
    def test_a_clone_and_its_governance_at_the_pinned_revision(self) -> None:
        done = connect(str(self.estate_remote), into=self.tmp / "mine")
        self.assertTrue(done.cloned)
        self.assertEqual(done.root, (self.tmp / "mine").resolve())
        self.assertEqual(done.governance_ref, "v1.0.0")
        self.assertEqual(done.governance_commit, git("rev-parse", "v1.0.0^{commit}", cwd=self.governance_remote))
        index = governance_index(done.root)
        self.assertEqual([p["id"] for p in json.loads(index.read_text(encoding="utf-8"))["patterns"]], ["PAT-001"])
        # The person's workspace never shows up as a change to commit.
        self.assertEqual(git("status", "--porcelain", cwd=done.root), "")
        self.assertTrue((done.root / GOVERNANCE_DIR / ".git").exists())

    def test_a_raised_pin_moves_the_governance_copy(self) -> None:
        done = connect(str(self.estate_remote), into=self.tmp / "mine")
        config = done.root / "10_MODEL" / "model.yaml"
        config.write_text(config.read_text(encoding="utf-8").replace('ref: "v1.0.0"', 'ref: "v1.1.0"'),
                          encoding="utf-8")
        again = connect(here=done.root)
        self.assertFalse(again.cloned)
        self.assertEqual(again.governance_commit, git("rev-parse", "v1.1.0^{commit}", cwd=self.governance_remote))
        patterns = json.loads(governance_index(done.root).read_text(encoding="utf-8"))["patterns"]
        self.assertEqual([p["id"] for p in patterns], ["PAT-001", "PAT-002"])

    def test_a_clone_made_elsewhere_is_connected_where_it_is(self) -> None:
        theirs = self.tmp / "from-the-web-page"
        git("clone", "-q", str(self.estate_remote), str(theirs), cwd=self.tmp)
        done = connect(here=theirs)
        self.assertFalse(done.cloned)
        self.assertIsNotNone(governance_index(theirs))

    def test_a_revision_the_governance_does_not_have_is_named(self) -> None:
        done = connect(str(self.estate_remote), into=self.tmp / "mine")
        config = done.root / "10_MODEL" / "model.yaml"
        config.write_text(config.read_text(encoding="utf-8").replace('ref: "v1.0.0"', 'ref: "v9.9.9"'),
                          encoding="utf-8")
        with self.assertRaises(WorkspaceError) as caught:
            connect(here=done.root)
        self.assertIn("v9.9.9", str(caught.exception))

    def test_a_folder_already_there_is_not_cloned_into(self) -> None:
        (self.tmp / "taken").mkdir()
        (self.tmp / "taken" / "notes.txt").write_text("mine\n", encoding="utf-8")
        with self.assertRaises(WorkspaceError):
            connect(str(self.estate_remote), into=self.tmp / "taken")

    def test_a_repository_with_no_estate_is_refused(self) -> None:
        with self.assertRaises(WorkspaceError) as caught:
            connect(str(self.governance_remote), into=self.tmp / "not-an-estate")
        self.assertIn("terrane init", str(caught.exception))

    def test_the_command(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            code = cli.main(["connect", str(self.estate_remote), "--into", str(self.tmp / "mine")])
        self.assertEqual(code, 0, out.getvalue())
        self.assertIn("governance", out.getvalue())
        self.assertIn("v1.0.0", out.getvalue())
        self.assertEqual(governance_pin(self.tmp / "mine")["ref"], "v1.0.0")


if __name__ == "__main__":
    unittest.main()
