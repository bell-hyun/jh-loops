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

# Metadata used by `jh-loops init` to create the set in a target repo.
# Keep in sync with conventions/labels.sh.
LABEL_SPECS: list[tuple[Label, str, str]] = [
    (Label.AGENT, "1f6feb", "Autonomous agent may work this issue (opt-in)"),
    (Label.IN_PROGRESS, "fbca04", "Claimed by the loop; in progress"),
    (Label.IN_REVIEW, "0e8a16", "PR opened; awaiting human review/merge"),
    (Label.NEEDS_SPEC, "d93f0b", "Missing/unparseable Depends-on or AC (sticky)"),
    (Label.NEEDS_HUMAN, "b60205", "Needs a human; incl. 3-round failure (sticky)"),
]
