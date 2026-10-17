from __future__ import annotations

from tools.replay_revenginstr_state_machine_scan22 import validate_frozen


def test_scan22_state_machine_audit_replays_fail_closed() -> None:
    assert validate_frozen() == {
        "program_id": "nfs-shift:SHIFT.exe",
        "function_count": 1,
        "pcode_operations": 169,
        "parameter_load_rows": 12,
        "memory_store_rows": 3,
        "unresolved_store_rows": 0,
        "candidate_count": 0,
    }
