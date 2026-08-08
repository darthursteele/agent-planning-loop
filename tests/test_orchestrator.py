"""Dry-run tests for orchestrator.py using the mock agent (no real CLI calls).

Run with: python3 -m pytest tests/ -v   (or plain: python3 tests/test_orchestrator.py)
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "tests" / "config.mock.yaml"


def run_orchestrator(max_rounds: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "orchestrator.py"),
            "--goal",
            "build a toy CLI tool",
            "--config",
            str(CONFIG),
            "--max-rounds",
            str(max_rounds),
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=60,
    )


def test_converges_and_approves_within_cap():
    # mock reviewer requests changes round 1, approves round 2 -> success
    # with a cap of 2 or more rounds.
    result = run_orchestrator(max_rounds=2)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "approved after round 2" in result.stdout


def test_escalates_when_cap_hit_before_approval():
    # cap of 1 round: reviewer only ever gets to request_changes, never
    # reaches round 2's approval -> escalation path, non-zero exit.
    result = run_orchestrator(max_rounds=1)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "Escalating" in result.stdout
    assert "mock blocking issue" in result.stdout


if __name__ == "__main__":
    test_converges_and_approves_within_cap()
    print("test_converges_and_approves_within_cap: OK")
    test_escalates_when_cap_hit_before_approval()
    print("test_escalates_when_cap_hit_before_approval: OK")
