"""Tests for jh_loops.agents (backend adapter, design §8).

Runs under pytest, or standalone (`python3 tests/test_agents.py`).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from jh_loops import agents  # noqa: E402
from jh_loops.agents import base  # noqa: E402


def test_registry_has_three_backends():
    assert set(agents.BACKENDS) == {"claude", "codex", "opencode"}


def test_get_known():
    assert agents.get("claude").name == "claude"


def test_get_unknown_raises():
    try:
        agents.get("nope")
    except ValueError:
        return
    raise AssertionError("expected ValueError for unknown backend")


def test_build_command_substitutes_and_drops_placeholder():
    for name in agents.BACKENDS:
        cmd = agents.get(name).build_command("DO THE THING")
        assert "DO THE THING" in cmd
        assert all("{prompt}" not in arg for arg in cmd)
        assert cmd[0] == name


def test_post_init_requires_placeholder():
    try:
        base.AgentBackend("bad", ["tool", "arg"])
    except ValueError:
        return
    raise AssertionError("expected ValueError when template lacks {prompt}")


def test_run_invokes_subprocess_with_cwd_and_returns_code():
    captured = {}

    class FakeCompleted:
        returncode = 42

    def fake_run(cmd, cwd=None):
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        return FakeCompleted()

    original = base.subprocess.run
    base.subprocess.run = fake_run
    try:
        backend = base.AgentBackend("x", ["tool", "--flag", "{prompt}"])
        rc = backend.run(Path("/work/tree"), "hello world")
    finally:
        base.subprocess.run = original

    assert rc == 42
    assert captured["cmd"] == ["tool", "--flag", "hello world"]
    assert captured["cwd"] == "/work/tree"


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
