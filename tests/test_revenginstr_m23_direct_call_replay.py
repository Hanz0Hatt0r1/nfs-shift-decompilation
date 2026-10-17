from pathlib import Path

from tools.replay_revenginstr_m23_direct_call_audit import validate_frozen


def test_frozen_m23_direct_call_replay_evidence_is_complete_and_fail_closed():
    root = Path(__file__).resolve().parents[1]
    summary = validate_frozen(root / "evidence/revenginstr_m23_direct_call_replay")

    assert summary == {"artifacts": 312, "candidates": 13, "bytes": 4069654}
