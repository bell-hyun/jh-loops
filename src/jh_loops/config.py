"""Run configuration (design §3, §9)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    repo: str  # "owner/name"
    agent: str  # "claude" | "codex" | "opencode"
    interval: str = "10m"
    max_rounds: int = 3  # dev<->verify cap (design §9)
    base_branch: str = "main"
    work_root: str = "."  # local checkout the loop runs against
