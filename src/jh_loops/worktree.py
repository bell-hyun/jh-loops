"""Git worktree lifecycle. The orchestrator owns it (design §4, §6, §11)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


def branch_name(number: int, title: str) -> str:
    """`agent/issue-<n>-<slug>` (design §10)."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40]
    return f"agent/issue-{number}-{slug}"


def _git(
    repo_path: str, *args: str, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_path), *args],
        check=check, capture_output=True, text=True,
    )


def worktrees_dir(repo_path: str) -> Path:
    """Where worktrees live: a sibling of the repo so they never pollute it."""
    return Path(repo_path).resolve().parent / ".jh-loops-worktrees"


def create(
    repo_path: str, number: int, title: str, base_branch: str = "main"
) -> tuple[Path, str]:
    """Create a worktree + new branch off `base_branch`. Returns (path, branch).

    The orchestrator should `cleanup` defensively before calling this so a stale
    worktree from a hard crash doesn't block a retry (design §11).
    """
    branch = branch_name(number, title)
    path = worktrees_dir(repo_path) / f"issue-{number}"
    path.parent.mkdir(parents=True, exist_ok=True)
    _git(repo_path, "worktree", "add", "-b", branch, str(path), base_branch)
    return path, branch


def cleanup(repo_path: str, worktree_path: Path, branch: str) -> None:
    """Remove the worktree AND delete the branch — fully clean (design §6, §11).

    Idempotent: safe to call when the worktree or branch is already gone (cleanup
    runs on success and on any abnormal exit). Retries start from scratch.
    """
    _git(repo_path, "worktree", "remove", "--force", str(worktree_path), check=False)
    _git(repo_path, "branch", "-D", branch, check=False)
    _git(repo_path, "worktree", "prune", check=False)


def push(repo_path: str, branch: str) -> None:
    """Push the work branch to origin (design §10)."""
    _git(repo_path, "push", "-u", "origin", branch)


def commits_ahead(repo_path: str, base_branch: str, branch: str) -> int:
    """How many commits `branch` is ahead of `base_branch` (0 -> nothing to PR)."""
    out = _git(repo_path, "rev-list", "--count", f"{base_branch}..{branch}").stdout
    return int(out.strip() or "0")
