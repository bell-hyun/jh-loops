"""Agent backend abstraction (design §8).

dev/verify run on any of claude/codex/opencode via a command template. Output is
NOT parsed per backend: dev results are read from git state, verify results from
`verify-result.json` (see jh_loops.verify).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class AgentBackend:
    name: str
    command: list[str]  # template; `{prompt}` is substituted at run time

    def run(self, cwd: Path, prompt: str) -> int:
        """Run the agent to completion in `cwd`. Returns the process exit code."""
        raise NotImplementedError  # TODO: subprocess (stream output via rich)
