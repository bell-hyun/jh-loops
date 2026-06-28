"""Label vocabulary and lifecycle (design §6)."""

from __future__ import annotations

from enum import Enum


class Label(str, Enum):
    AGENT = "agent"  # opt-in; only issues carrying this are considered (design §5)
    IN_PROGRESS = "in-progress"  # claimed by the loop
    IN_REVIEW = "in-review"  # PR opened, awaiting human merge
    NEEDS_SPEC = "needs-spec"  # missing/unparseable Depends-on or AC — sticky
    NEEDS_HUMAN = "needs-human"  # human-only, incl. 3-round failure — sticky


# An issue carrying any of these is skipped during selection (design §5).
SKIP_LABELS: frozenset[str] = frozenset(
    {Label.IN_PROGRESS, Label.IN_REVIEW, Label.NEEDS_SPEC, Label.NEEDS_HUMAN}
)
