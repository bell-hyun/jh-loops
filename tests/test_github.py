"""Tests for jh_loops.github gh wrappers (design layer 2).

`_gh` is swapped for a fake, so no network / no real `gh` is needed. Runs under
pytest, or standalone (`python3 tests/test_github.py`).
"""

from __future__ import annotations

import json
import sys
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from jh_loops import github  # noqa: E402


@contextmanager
def patch_gh(fake):
    """Swap github._gh for `fake`, capturing calls; restore afterwards."""
    original = github._gh
    github._gh = fake
    try:
        yield
    finally:
        github._gh = original


def recorder(return_value=""):
    """A fake _gh that records call args and returns a fixed value."""
    calls: list[tuple[str, ...]] = []

    def fake(*args):
        calls.append(args)
        return return_value

    fake.calls = calls
    return fake


def test_is_closed_true():
    fake = recorder('{"state": "CLOSED"}')
    with patch_gh(fake):
        assert github.is_closed("o/r", 5) is True
    assert fake.calls[0] == ("issue", "view", "5", "--repo", "o/r", "--json", "state")


def test_is_closed_false_when_open():
    fake = recorder('{"state": "OPEN"}')
    with patch_gh(fake):
        assert github.is_closed("o/r", 5) is False


def test_create_label():
    fake = recorder()
    with patch_gh(fake):
        github.create_label("o/r", "agent", "1f6feb", "opt-in")
    assert fake.calls[0] == (
        "label", "create", "agent", "--repo", "o/r",
        "--color", "1f6feb", "--description", "opt-in", "--force",
    )


def test_add_label():
    fake = recorder()
    with patch_gh(fake):
        github.add_label("o/r", 7, "in-progress")
    assert fake.calls[0] == (
        "issue", "edit", "7", "--repo", "o/r", "--add-label", "in-progress",
    )


def test_remove_label():
    fake = recorder()
    with patch_gh(fake):
        github.remove_label("o/r", 7, "in-progress")
    assert fake.calls[0] == (
        "issue", "edit", "7", "--repo", "o/r", "--remove-label", "in-progress",
    )


def test_comment():
    fake = recorder()
    with patch_gh(fake):
        github.comment("o/r", 7, "blocked: see #3")
    assert fake.calls[0] == (
        "issue", "comment", "7", "--repo", "o/r", "--body", "blocked: see #3",
    )


def test_create_pr_returns_url():
    fake = recorder("https://github.com/o/r/pull/3\n")
    with patch_gh(fake):
        url = github.create_pr("o/r", "agent/issue-7-x", "main", "title", "body")
    assert url == "https://github.com/o/r/pull/3"
    assert fake.calls[0] == (
        "pr", "create", "--repo", "o/r",
        "--head", "agent/issue-7-x", "--base", "main",
        "--title", "title", "--body", "body",
    )


def test_list_open_issues_sorts_and_normalizes():
    payload = json.dumps([
        {"number": 5, "title": "b", "body": None, "labels": [{"name": "agent"}]},
        {"number": 2, "title": "a", "body": "x", "labels": []},
    ])
    fake = recorder(payload)
    with patch_gh(fake):
        issues = github.list_open_issues("o/r")
    assert [i.number for i in issues] == [2, 5]  # oldest -> newest
    assert issues[0].body == "x"
    assert issues[1].body == ""  # None -> ""
    assert issues[1].labels == ["agent"]


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
