"""Tests for jh_loops.orchestrator.tick (design §4).

Every side-effecting dependency (github / worktree / agent / verify) is faked,
so the test exercises the control flow only — no network, no git, no agents.
Runs under pytest, or standalone (`python3 tests/test_orchestrator.py`).
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from jh_loops import agents, github, orchestrator, selection, verify, worktree  # noqa: E402
from jh_loops.config import Config  # noqa: E402
from jh_loops.issues import Issue  # noqa: E402
from jh_loops.labels import Label  # noqa: E402
from jh_loops.verify import VerifyItem, VerifyResult  # noqa: E402


@contextmanager
def patch(*assignments):
    """assignments: (obj, name, value). Sets, then restores on exit."""
    saved = [(o, n, getattr(o, n)) for o, n, _ in assignments]
    for o, n, v in assignments:
        setattr(o, n, v)
    try:
        yield
    finally:
        for o, n, v in saved:
            setattr(o, n, v)


PASS = VerifyResult(passed=True, items=[VerifyItem("thing", True, "ok")])
FAIL = VerifyResult(passed=False, items=[VerifyItem("thing", False, "nope")])

ISSUE = Issue(
    number=7,
    title="Do X",
    body="## Acceptance Criteria\n- [ ] thing\n",
    labels=["agent"],
)


def drive(*, issue=ISSUE, verify_seq=(PASS,), commits=1, pr_raises=False):
    """Run one tick with all dependencies faked. Returns (outcome, events).

    outcome is True/False on normal return, or the raised exception instance.
    """
    events: list[tuple] = []
    seq = list(verify_seq)
    idx = {"i": 0}

    def read_result(_path):
        i = min(idx["i"], len(seq) - 1)
        idx["i"] += 1
        item = seq[i]
        if item == "raise":
            raise FileNotFoundError
        return item

    class FakeBackend:
        def run(self, _cwd, prompt):
            events.append(("verify_run",) if "verifying" in prompt else ("dev_run",))
            return 0

    def create_pr(_repo, head, _base, _title, _body):
        events.append(("create_pr", head))
        if pr_raises:
            raise RuntimeError("boom")
        return "http://pr/1"

    assignments = [
        (selection, "select_next", lambda _issues, _repo: issue),
        (github, "list_open_issues", lambda _repo: [issue] if issue else []),
        (github, "add_label", lambda _r, n, lbl: events.append(("add_label", n, lbl))),
        (github, "remove_label", lambda _r, n, lbl: events.append(("remove_label", n, lbl))),
        (github, "comment", lambda _r, n, _b: events.append(("comment", n))),
        (github, "create_pr", create_pr),
        (agents, "get", lambda _name: FakeBackend()),
        (verify, "read_result", read_result),
        (worktree, "cleanup", lambda _rp, _wp, _b: events.append(("cleanup",))),
        (worktree, "create", lambda rp, n, t, base="main": (Path("/fake/wt"), worktree.branch_name(n, t))),
        (worktree, "push", lambda _rp, b: events.append(("push", b))),
        (worktree, "commits_ahead", lambda _rp, _base, _b: commits),
    ]
    with patch(*assignments):
        try:
            outcome = orchestrator.tick(Config(repo="o/r", agent="claude"))
        except Exception as exc:  # noqa: BLE001
            outcome = exc
    return outcome, events


def _count(events, name):
    return sum(1 for e in events if e[0] == name)


def _has(events, *needle):
    return needle in events


def test_idle_when_nothing_actionable():
    outcome, events = drive(issue=None)
    assert outcome is False
    assert events == []  # never claimed


def test_happy_path_opens_pr_and_transitions_labels():
    outcome, events = drive(verify_seq=(PASS,))
    assert outcome is True
    assert events[0] == ("add_label", 7, Label.IN_PROGRESS)  # claim first
    assert _count(events, "dev_run") == 1
    assert _count(events, "verify_run") == 1
    assert _has(events, "push", "agent/issue-7-do-x")
    assert _has(events, "create_pr", "agent/issue-7-do-x")
    assert _has(events, "add_label", 7, Label.IN_REVIEW)
    assert _has(events, "remove_label", 7, Label.IN_PROGRESS)
    assert _count(events, "comment") == 0  # no escalation
    # in-review only after the PR is created
    assert events.index(("add_label", 7, Label.IN_REVIEW)) > events.index(
        ("create_pr", "agent/issue-7-do-x")
    )


def test_escalates_after_max_rounds():
    outcome, events = drive(verify_seq=(FAIL, FAIL, FAIL))
    assert outcome is True
    assert _count(events, "dev_run") == 3  # config.max_rounds
    assert _count(events, "verify_run") == 3
    assert _has(events, "comment", 7)
    assert _has(events, "add_label", 7, Label.NEEDS_HUMAN)
    assert _has(events, "remove_label", 7, Label.IN_PROGRESS)
    assert _count(events, "create_pr") == 0  # no PR


def test_passes_on_second_round():
    outcome, events = drive(verify_seq=(FAIL, PASS))
    assert outcome is True
    assert _count(events, "dev_run") == 2
    assert _has(events, "create_pr", "agent/issue-7-do-x")
    assert _count(events, "comment") == 0


def test_escalates_when_verify_passes_but_no_commits():
    outcome, events = drive(verify_seq=(PASS,), commits=0)
    assert outcome is True
    assert _count(events, "create_pr") == 0
    assert _has(events, "add_label", 7, Label.NEEDS_HUMAN)
    assert _has(events, "remove_label", 7, Label.IN_PROGRESS)


def test_abnormal_exit_releases_claim_and_cleans_up():
    outcome, events = drive(verify_seq=(PASS,), pr_raises=True)
    assert isinstance(outcome, RuntimeError)
    assert _has(events, "remove_label", 7, Label.IN_PROGRESS)
    assert _count(events, "cleanup") >= 1
    assert not _has(events, "add_label", 7, Label.IN_REVIEW)


def test_interval_seconds():
    assert orchestrator._interval_seconds("30s") == 30
    assert orchestrator._interval_seconds("10m") == 600
    assert orchestrator._interval_seconds("2h") == 7200
    assert orchestrator._interval_seconds("45") == 45


if __name__ == "__main__":
    import traceback

    cases = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for case in cases:
        try:
            case()
            print(f"PASS {case.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {case.__name__}")
            traceback.print_exc()
    print(f"\n{len(cases) - failed}/{len(cases)} passed")
    sys.exit(1 if failed else 0)
