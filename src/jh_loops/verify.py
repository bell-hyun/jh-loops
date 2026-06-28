"""Verify-result contract (design §8).

The verify agent writes `verify-result.json` in the worktree root; the
orchestrator reads ONLY that file, so verification is backend-agnostic.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

RESULT_FILENAME = "verify-result.json"


@dataclass
class VerifyItem:
    ac: str
    passed: bool
    evidence: str


@dataclass
class VerifyResult:
    passed: bool
    items: list[VerifyItem]


def read_result(worktree_path: Path) -> VerifyResult:
    """Read and validate `verify-result.json` from the worktree root."""
    data = json.loads((worktree_path / RESULT_FILENAME).read_text())
    items = [
        VerifyItem(ac=i["ac"], passed=bool(i["pass"]), evidence=i.get("evidence", ""))
        for i in data.get("items", [])
    ]
    return VerifyResult(passed=bool(data["pass"]), items=items)


def failures(result: VerifyResult) -> list[VerifyItem]:
    """Failed AC items, fed into the next dev round (design §9)."""
    return [i for i in result.items if not i.passed]
