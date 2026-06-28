"""Agent backend registry (design §8).

Each backend is a command template with a `{prompt}` placeholder. Exact flags
(permissions / sandbox / completion signal) are TBD at implementation (design §13).
"""

from __future__ import annotations

from .base import AgentBackend

BACKENDS: dict[str, AgentBackend] = {
    "claude": AgentBackend(
        "claude", ["claude", "-p", "{prompt}", "--permission-mode", "acceptEdits"]
    ),
    "codex": AgentBackend("codex", ["codex", "exec", "{prompt}"]),
    "opencode": AgentBackend("opencode", ["opencode", "run", "{prompt}"]),
}


def get(name: str) -> AgentBackend:
    try:
        return BACKENDS[name]
    except KeyError:
        raise ValueError(
            f"unknown agent backend: {name!r} (choose from {', '.join(BACKENDS)})"
        ) from None
