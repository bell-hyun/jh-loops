"""Thin wrappers over the `gh` CLI: issues, labels, PRs (design layer 2).

All GitHub state lives here; the orchestrator holds no cross-tick state (design §2).
"""

from __future__ import annotations

import json
import subprocess

from .issues import Issue


def _gh(*args: str) -> str:
    """Run `gh` and return stdout, raising on failure."""
    return subprocess.run(
        ["gh", *args], check=True, capture_output=True, text=True
    ).stdout


def list_open_issues(repo: str) -> list[Issue]:
    """All open issues, oldest first (design §5 selection order)."""
    out = _gh(
        "issue", "list", "--repo", repo, "--state", "open",
        "--json", "number,title,body,labels", "--limit", "200",
    )
    raw = json.loads(out)
    issues = [
        Issue(
            number=i["number"],
            title=i["title"],
            body=i.get("body") or "",
            labels=[lbl["name"] for lbl in i.get("labels", [])],
        )
        for i in raw
    ]
    issues.sort(key=lambda i: i.number)  # oldest -> newest
    return issues


def is_closed(repo: str, number: int) -> bool:
    """Whether an issue is closed (used to resolve Depends-on, design §5)."""
    data = json.loads(
        _gh("issue", "view", str(number), "--repo", repo, "--json", "state")
    )
    return data.get("state") == "CLOSED"


def create_label(repo: str, name: str, color: str, description: str) -> None:
    """Create (or update, via --force) a label in a target repo (design §6)."""
    _gh(
        "label", "create", name, "--repo", repo,
        "--color", color, "--description", description, "--force",
    )


def add_label(repo: str, number: int, label: str) -> None:
    _gh("issue", "edit", str(number), "--repo", repo, "--add-label", label)


def remove_label(repo: str, number: int, label: str) -> None:
    _gh("issue", "edit", str(number), "--repo", repo, "--remove-label", label)


def comment(repo: str, number: int, body: str) -> None:
    _gh("issue", "comment", str(number), "--repo", repo, "--body", body)


def create_pr(repo: str, head: str, base: str, title: str, body: str) -> str:
    """Open a PR (no auto-merge, design §10). Returns the PR URL."""
    return _gh(
        "pr", "create", "--repo", repo,
        "--head", head, "--base", base,
        "--title", title, "--body", body,
    ).strip()
