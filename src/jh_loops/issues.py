"""Issue model and body parsing for Depends-on / Acceptance Criteria (design §7)."""

from __future__ import annotations

import re
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


_HEADING_RE = re.compile(r"^ {0,3}#{1,6}\s+(.*\S)\s*$")
_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_ISSUE_REF_RE = re.compile(r"#(\d+)")
_AC_ITEM_RE = re.compile(r"^\s*[-*]\s+\[[ xX]\]\s+(.*\S)\s*$")


def _split_sections(body: str) -> list[tuple[str, str]]:
    """Split a markdown body into (normalized_heading, section_text) pairs.

    A section runs from its heading line until the next heading (any level) or EOF.
    Headings are lowercased/stripped so callers can match them case-insensitively.
    """
    sections: list[tuple[str, list[str]]] = []
    for line in body.splitlines():
        m = _HEADING_RE.match(line)
        if m:
            sections.append((m.group(1).strip().lower(), []))
        elif sections:
            sections[-1][1].append(line)
    return [(heading, "\n".join(lines)) for heading, lines in sections]


def _section(sections: list[tuple[str, str]], keyword: str) -> str | None:
    """Text of the first section whose heading starts with `keyword` (lowercased)."""
    for heading, text in sections:
        if heading.startswith(keyword):
            return text
    return None


def parse(issue: Issue) -> ParsedIssue:
    """Parse the `## Depends-on` and `## Acceptance Criteria` sections (design §7).

    - Depends-on: `#<n>` references inside the section, de-duplicated, order kept.
      Absent section -> no dependencies.
    - Acceptance Criteria: `- [ ]` / `- [x]` checklist items (text only). Absent
      heading -> has_ac_section=False (caller marks needs-spec, design §5).

    HTML comments are stripped before scanning, so commented-out examples in the
    issue template don't leak into the result.
    """
    sections = _split_sections(issue.body or "")

    dep_text = _section(sections, "depends-on")
    if dep_text is None:
        depends_on: list[int] = []
    else:
        refs = _ISSUE_REF_RE.findall(_COMMENT_RE.sub("", dep_text))
        depends_on = list(dict.fromkeys(int(n) for n in refs))  # dedupe, keep order

    ac_text = _section(sections, "acceptance criteria")
    has_ac_section = ac_text is not None
    acceptance_criteria: list[str] = []
    if ac_text is not None:
        for line in _COMMENT_RE.sub("", ac_text).splitlines():
            m = _AC_ITEM_RE.match(line)
            if m:
                acceptance_criteria.append(m.group(1).strip())

    return ParsedIssue(
        depends_on=depends_on,
        acceptance_criteria=acceptance_criteria,
        has_ac_section=has_ac_section,
    )
