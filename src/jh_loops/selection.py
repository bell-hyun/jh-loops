"""Pick the next actionable issue (design §5)."""

from __future__ import annotations

from . import github, issues
from .issues import Issue
from .labels import Label, SKIP_LABELS


def is_actionable(issue: Issue, repo: str) -> bool:
    """Eligible iff (design §5):
    - has the `agent` opt-in label,
    - carries none of SKIP_LABELS,
    - has an `## Acceptance Criteria` section (else it'd be needs-spec),
    - every `## Depends-on` reference is closed.
    """
    if Label.AGENT not in issue.labels:
        return False
    if any(lbl in SKIP_LABELS for lbl in issue.labels):
        return False
    parsed = issues.parse(issue)
    if not parsed.has_ac_section:
        return False
    return all(github.is_closed(repo, dep) for dep in parsed.depends_on)


def select_next(open_issues: list[Issue], repo: str) -> Issue | None:
    """First actionable issue, oldest -> newest. None if the queue is empty.

    Dep-blocked issues carry no label and are simply re-evaluated next tick;
    needs-spec / needs-human are sticky and skipped until a human clears them.
    """
    for issue in open_issues:  # caller passes oldest-first (github.list_open_issues)
        if is_actionable(issue, repo):
            return issue
    return None
