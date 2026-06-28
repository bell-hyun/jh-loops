"""Prompts handed to the dev and verify agents (design §4, §8)."""

from __future__ import annotations

from .issues import Issue, ParsedIssue
from .verify import RESULT_FILENAME, VerifyItem


def _ac_block(parsed: ParsedIssue) -> str:
    return "\n".join(f"- {ac}" for ac in parsed.acceptance_criteria)


def dev_prompt(
    issue: Issue, parsed: ParsedIssue, failures: list[VerifyItem] | None = None
) -> str:
    """Instruct a dev agent. It works in the worktree (cwd) and commits; the
    orchestrator opens the PR, not the agent (design §4, §10)."""
    parts = [
        f"You are implementing GitHub issue #{issue.number}: {issue.title}",
        "",
        "Work in the current directory (a dedicated git worktree). Implement the "
        "change and COMMIT your work with git. Do not open a pull request.",
        "",
        "## Issue",
        issue.body.strip() or "(no description)",
        "",
        "## Acceptance Criteria (your contract)",
        _ac_block(parsed),
    ]
    if failures:
        parts += [
            "",
            "## A previous attempt failed these criteria — fix them:",
            "\n".join(f"- {f.ac}: {f.evidence}" for f in failures),
        ]
    return "\n".join(parts)


def verify_prompt(issue: Issue, parsed: ParsedIssue) -> str:
    """Instruct a verify agent. Output is read back only via `verify-result.json`,
    so this is backend-agnostic (design §8)."""
    schema = (
        '{"pass": <bool>, "items": [{"ac": "<text>", '
        '"pass": <bool>, "evidence": "<what you observed>"}]}'
    )
    return "\n".join(
        [
            f"You are verifying work for GitHub issue #{issue.number}: {issue.title}",
            "",
            "Check EACH acceptance criterion below against the code in the current "
            "directory. Run whatever commands the criteria mention. Judge "
            "objectively and do not change any code.",
            "",
            "## Acceptance Criteria",
            _ac_block(parsed),
            "",
            f"Then write your verdict to `{RESULT_FILENAME}` in this directory as JSON:",
            schema,
            "",
            "Top-level `pass` is true only if every item passed.",
        ]
    )
