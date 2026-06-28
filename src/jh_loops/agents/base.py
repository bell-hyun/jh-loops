"""Agent backend abstraction (design §8).

dev/verify run on any of claude/codex/opencode via a command template. Output is
NOT parsed per backend: dev results are read from git state, verify results from
`verify-result.json` (see jh_loops.verify).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

PROMPT_PLACEHOLDER = "{prompt}"


@dataclass
class AgentBackend:
    name: str
    command: list[str]  # template; `{prompt}` is substituted at run time

    def __post_init__(self) -> None:
        if not any(PROMPT_PLACEHOLDER in arg for arg in self.command):
            raise ValueError(
                f"backend {self.name!r} command must contain {PROMPT_PLACEHOLDER!r}"
            )

    def build_command(self, prompt: str) -> list[str]:
        """Substitute the {prompt} placeholder in the command template."""
        return [arg.replace(PROMPT_PLACEHOLDER, prompt) for arg in self.command]

    def run(self, cwd: Path, prompt: str) -> int:
        """Run the agent to completion in `cwd`. Returns the process exit code.

        stdout/stderr are inherited, so the agent's progress is visible live.
        """
        return subprocess.run(self.build_command(prompt), cwd=str(cwd)).returncode
