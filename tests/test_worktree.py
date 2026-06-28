"""Tests for jh_loops.worktree (design §6, §10, §11).

Integration tests against a throwaway git repo in a temp dir (git is required).
Runs under pytest, or standalone (`python3 tests/test_worktree.py`).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from jh_loops import worktree  # noqa: E402


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True)
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "tester")
    (repo / "README.md").write_text("hi\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "init")


def test_branch_name_slug():
    assert worktree.branch_name(12, "Fix the Thing (v2)!!") == "agent/issue-12-fix-the-thing-v2"
    assert worktree.branch_name(7, "Add cool Feature!") == "agent/issue-7-add-cool-feature"


def test_create_then_cleanup():
    tmp = Path(tempfile.mkdtemp())
    try:
        repo = tmp / "repo"
        _init_repo(repo)

        path, branch = worktree.create(str(repo), 7, "Add cool Feature!")
        assert branch == "agent/issue-7-add-cool-feature"
        assert path.exists()
        assert (path / ".git").exists()  # a linked worktree
        assert (path / "README.md").exists()  # checked out from base
        assert branch in _git(repo, "branch", "--list", branch)

        worktree.cleanup(str(repo), path, branch)
        assert not path.exists()
        assert _git(repo, "branch", "--list", branch).strip() == ""
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_cleanup_is_idempotent():
    tmp = Path(tempfile.mkdtemp())
    try:
        repo = tmp / "repo"
        _init_repo(repo)
        # Nothing created — cleanup on an absent worktree/branch must not raise.
        worktree.cleanup(str(repo), tmp / "does-not-exist", "agent/issue-99-nope")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_commits_ahead_counts_new_commits():
    tmp = Path(tempfile.mkdtemp())
    try:
        repo = tmp / "repo"
        _init_repo(repo)
        path, branch = worktree.create(str(repo), 3, "feature")
        assert worktree.commits_ahead(str(repo), "main", branch) == 0
        (path / "new.txt").write_text("x\n")
        _git(path, "add", "-A")
        _git(path, "commit", "-m", "work")
        assert worktree.commits_ahead(str(repo), "main", branch) == 1
        worktree.cleanup(str(repo), path, branch)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_push_builds_git_args():
    calls = []

    class FakeCompleted:
        stdout = ""

    original = worktree._git
    worktree._git = lambda repo, *args, check=True: calls.append((repo, args)) or FakeCompleted()
    try:
        worktree.push("/repo", "agent/issue-3-x")
    finally:
        worktree._git = original
    assert calls[0] == ("/repo", ("push", "-u", "origin", "agent/issue-3-x"))


if __name__ == "__main__":
    import traceback

    cases = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for case in cases:
        try:
            case()
            print(f"PASS {case.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {case.__name__}")
            traceback.print_exc()
    print(f"\n{len(cases) - failed}/{len(cases)} passed")
    sys.exit(1 if failed else 0)
