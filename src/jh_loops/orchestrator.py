"""The main loop: one tick = one issue, steps 1->6 (design §4).

The orchestrator is deterministic glue (design §2). Only the fuzzy work
(dev, verify) is delegated to LLM CLI agents.
"""

from __future__ import annotations

from . import agents, github, issues, prompts, selection, verify, worktree
from .config import Config
from .labels import Label
from .verify import VerifyResult


def _log(msg: str) -> None:
    # Plain stdout for now; the rich presentation layer lives in cli.py (design §12.1).
    print(f"[jh-loops] {msg}")


def _pr_title(issue: issues.Issue) -> str:
    return f"{issue.title} (#{issue.number})"


def _pr_body(issue: issues.Issue, result: VerifyResult) -> str:
    lines = [f"Closes #{issue.number}", "", "## Acceptance Criteria"]
    for item in result.items:
        lines.append(f"- [{'x' if item.passed else ' '}] {item.ac}")
    return "\n".join(lines)


def _escalate(config: Config, number: int, result: VerifyResult | None) -> None:
    """Hand the issue to a human: comment, add needs-human, release the claim."""
    if result is None:
        reason = "verification produced no usable verify-result.json"
    else:
        failed = ", ".join(i.ac for i in verify.failures(result)) or "unknown"
        reason = f"unmet acceptance criteria: {failed}"
    github.comment(
        config.repo,
        number,
        f"jh-loops: handing off to a human after {config.max_rounds} rounds — {reason}.",
    )
    github.add_label(config.repo, number, Label.NEEDS_HUMAN)
    github.remove_label(config.repo, number, Label.IN_PROGRESS)


def tick(config: Config) -> bool:
    """Process one issue end to end (design §4). Returns True if one was handled,
    False if nothing was actionable.

    1. poll & select   2. claim        3. worktree
    4. dev             5. verify <-> 4 (<= max_rounds)   6. PR

    Any exception after claim -> release the claim and fully clean the worktree
    (design §6); the issue is left for a future tick to retry from scratch.
    """
    repo = config.repo
    issue = selection.select_next(github.list_open_issues(repo), repo)
    if issue is None:
        _log("no actionable issue")
        return False

    parsed = issues.parse(issue)
    backend = agents.get(config.agent)
    branch = worktree.branch_name(issue.number, issue.title)
    _log(f"working #{issue.number}: {issue.title}")

    github.add_label(repo, issue.number, Label.IN_PROGRESS)  # 2. claim
    worktree_path = None
    try:
        # 3. worktree — defensively clear any stale state first (design §11).
        stale = worktree.worktrees_dir(config.work_root) / f"issue-{issue.number}"
        worktree.cleanup(config.work_root, stale, branch)
        worktree_path, branch = worktree.create(
            config.work_root, issue.number, issue.title, config.base_branch
        )

        # 4-5. dev <-> verify, capped at max_rounds (design §9).
        result: VerifyResult | None = None
        fails = None
        for round_num in range(1, config.max_rounds + 1):
            _log(f"round {round_num}/{config.max_rounds}")
            backend.run(worktree_path, prompts.dev_prompt(issue, parsed, fails))
            backend.run(worktree_path, prompts.verify_prompt(issue, parsed))
            try:
                result = verify.read_result(worktree_path)
            except (FileNotFoundError, ValueError, KeyError):
                result, fails = None, None
                continue
            if result.passed:
                break
            fails = verify.failures(result)

        if result is None or not result.passed:
            _log("escalating to needs-human (criteria unmet)")
            _escalate(config, issue.number, result)
            worktree.cleanup(config.work_root, worktree_path, branch)
            return True

        if worktree.commits_ahead(config.work_root, config.base_branch, branch) == 0:
            _log("escalating to needs-human (verify passed but no commits)")
            _escalate(config, issue.number, result)
            worktree.cleanup(config.work_root, worktree_path, branch)
            return True

        # 6. PR (design §10): push, open PR (no auto-merge), in-progress -> in-review.
        worktree.push(config.work_root, branch)
        url = github.create_pr(
            repo, branch, config.base_branch, _pr_title(issue), _pr_body(issue, result)
        )
        github.add_label(repo, issue.number, Label.IN_REVIEW)
        github.remove_label(repo, issue.number, Label.IN_PROGRESS)
        _log(f"opened PR: {url}")
        worktree.cleanup(config.work_root, worktree_path, branch)
        return True
    except Exception:
        _log("abnormal exit — releasing claim and cleaning up")
        github.remove_label(repo, issue.number, Label.IN_PROGRESS)
        if worktree_path is not None:
            worktree.cleanup(config.work_root, worktree_path, branch)
        raise


def _interval_seconds(interval: str) -> int:
    units = {"s": 1, "m": 60, "h": 3600}
    if interval and interval[-1] in units:
        return int(interval[:-1]) * units[interval[-1]]
    return int(interval)


def run(config: Config) -> None:
    """Loop forever, one tick per interval. single-flight (no overlapping ticks)
    is enforced externally via cron + flock (design §5); this is a simple driver."""
    import time

    seconds = _interval_seconds(config.interval)
    while True:
        try:
            tick(config)
        except Exception as exc:  # keep the loop alive across tick failures
            _log(f"tick error: {exc}")
        time.sleep(seconds)
