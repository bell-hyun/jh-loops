"""Git worktree lifecycle. The orchestrator owns it (design §4, §6, §11)."""

from __future__ import annotations

import re
from pathlib import Path


def branch_name(number: int, title: str) -> str:
    """`agent/issue-<n>-<slug>` (design §10)."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40]
    return f"agent/issue-{number}-{slug}"


def create(repo_path: str, number: int, title: str) -> tuple[Path, str]:
    """Create a worktree + branch off the base. Returns (worktree_path, branch)."""
    raise NotImplementedError  # TODO: git worktree add


def cleanup(repo_path: str, worktree_path: Path, branch: str) -> None:
    """Remove the worktree AND delete the branch — fully clean (design §6, §11).

    Called on success after the PR push, and on any abnormal exit. Retries start
    from scratch; no partial work is reused.
    """
    raise NotImplementedError  # TODO: git worktree remove + git branch -D
