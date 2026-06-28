"""The main loop: one tick = one issue, steps 1->6 (design §4).

The orchestrator is deterministic glue (design §2.4). Only the fuzzy work
(dev, verify) is delegated to LLM CLI agents.
"""

from __future__ import annotations

from . import agents, github, selection, verify, worktree
from .config import Config
from .labels import Label


def tick(config: Config) -> None:
    """Process a single issue end to end. No-op if nothing is actionable.

    1. poll & select   (selection.select_next)
    2. claim           (add in-progress)
    3. worktree        (worktree.create)
    4. dev             (agent backend, role=dev)
    5. verify <-> 4    (agent backend, role=verify; max config.max_rounds)
    6. PR              (github.create_pr; in-progress -> in-review)

    Abnormal exit at any point after claim -> cleanup: remove in-progress,
    remove worktree, delete branch (design §6). The issue is left for a future
    tick to retry from scratch.
    """
    raise NotImplementedError  # TODO: wire steps 1-6 with try/finally cleanup


def run(config: Config) -> None:
    """Loop entry. single-flight (no overlapping ticks) is enforced externally,
    e.g. cron + flock (design §5)."""
    raise NotImplementedError  # TODO: interval scheduling around tick()


# Helpers below are intentionally referenced by tick() once implemented; kept as
# named seams so the control flow stays readable and testable.
_ = (agents, github, selection, verify, worktree, Config, Label)
