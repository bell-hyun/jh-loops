"""Issue model and body parsing for Depends-on / Acceptance Criteria (design §7)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Issue:
    number: int
    title: str
    body: str
    labels: list[str]


@dataclass
class ParsedIssue:
    depends_on: list[int]  # referenced issue numbers from the `## Depends-on` section
    acceptance_criteria: list[str]  # checklist items from `## Acceptance Criteria`
    has_ac_section: bool  # False -> caller marks needs-spec (design §5)


def parse(issue: Issue) -> ParsedIssue:
    """Parse the `## Depends-on` and `## Acceptance Criteria` sections of the body.

    - Depends-on: `#<n>` references; absent section -> no dependencies.
    - Acceptance Criteria: `- [ ]` / `- [x]` items; absent section -> has_ac_section=False.
    """
    raise NotImplementedError  # TODO
