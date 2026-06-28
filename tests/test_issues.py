"""Tests for jh_loops.issues.parse (design §7).

Runs under pytest, or standalone (`python3 tests/test_issues.py`) since the
package isn't installed in every environment.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from jh_loops.issues import Issue, parse  # noqa: E402


def _issue(body: str) -> Issue:
    return Issue(number=1, title="t", body=body, labels=["agent"])


def test_well_formed():
    body = """\
## 목적 (Why)
As a user, I want X, so that Y.

## 상세 (What / Context)
context

## Depends-on
- #12
- #15

## Acceptance Criteria
- [ ] 사용자가 X 하면 Y가 보인다
- [ ] `npm test` 통과
"""
    p = parse(_issue(body))
    assert p.depends_on == [12, 15]
    assert p.acceptance_criteria == ["사용자가 X 하면 Y가 보인다", "`npm test` 통과"]
    assert p.has_ac_section is True


def test_no_depends_on_section():
    p = parse(_issue("## Acceptance Criteria\n- [ ] do thing\n"))
    assert p.depends_on == []
    assert p.has_ac_section is True
    assert p.acceptance_criteria == ["do thing"]


def test_no_ac_section():
    p = parse(_issue("## 목적\nhi\n## Depends-on\n- #2\n"))
    assert p.has_ac_section is False
    assert p.acceptance_criteria == []
    assert p.depends_on == [2]


def test_empty_depends_on_with_placeholder_and_comment():
    body = """\
## Depends-on
<!-- 없으면 비워두세요 -->
-

## Acceptance Criteria
- [ ] thing
"""
    assert parse(_issue(body)).depends_on == []


def test_comments_are_ignored():
    body = """\
## Depends-on
<!-- example: - #99 -->
- #3

## Acceptance Criteria
<!-- - [ ] commented out -->
- [x] real item
"""
    p = parse(_issue(body))
    assert p.depends_on == [3]
    assert p.acceptance_criteria == ["real item"]


def test_dedupe_and_order_preserved():
    p = parse(_issue("## Depends-on\n- #5 and also #5\n- #8\n"))
    assert p.depends_on == [5, 8]


def test_heading_level_tolerance():
    body = "### Depends-on\n- #7\n### Acceptance Criteria\n- [ ] thing\n"
    p = parse(_issue(body))
    assert p.depends_on == [7]
    assert p.has_ac_section is True
    assert p.acceptance_criteria == ["thing"]


def test_ac_items_do_not_bleed_into_next_section():
    body = "## Acceptance Criteria\n- [ ] ac one\n## Notes\n- [ ] not an ac\n"
    assert parse(_issue(body)).acceptance_criteria == ["ac one"]


def test_empty_body():
    p = parse(_issue(""))
    assert p.depends_on == []
    assert p.acceptance_criteria == []
    assert p.has_ac_section is False


def test_checkbox_variants_and_empty_items_skipped():
    body = """\
## Acceptance Criteria
- [ ] alpha
* [x] beta
- [ ]
- [ ]
"""
    assert parse(_issue(body)).acceptance_criteria == ["alpha", "beta"]


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
