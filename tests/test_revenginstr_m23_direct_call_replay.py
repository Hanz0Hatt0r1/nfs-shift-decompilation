import sys
from pathlib import Path

from tools.replay_revenginstr_m23_direct_call_audit import replay, validate_frozen


def test_frozen_m23_direct_call_replay_evidence_is_complete_and_fail_closed():
    root = Path(__file__).resolve().parents[1]
    summary = validate_frozen(root / "evidence/revenginstr_m23_direct_call_replay")

    assert summary == {"artifacts": 354, "candidates": 13, "bytes": 4262531}

    replay_summary = replay(
        root / "evidence/revenginstr_m23_direct_call_replay",
        Path(sys.executable).parent,
    )
    assert replay_summary["artifacts"] == 354
    assert replay_summary["candidates"] == 13
    assert replay_summary["replayed_candidates"] == 13
    assert replay_summary["replayed_screening_roots"] == 158
