from __future__ import annotations

from tools.replay_revenginstr_m5_effect_ir import validate_frozen


def test_scan22_effect_ir_v2_replays_with_exact_memory_operations() -> None:
    summary = validate_frozen()

    assert summary == {
        "program_id": "nfs-shift:SHIFT.exe",
        "function_entry": "00a277d0",
        "effect_functions": 1,
        "effects": 60,
        "effects_by_kind": {
            "direct_call": 6,
            "indirect_call": 9,
            "memory_read": 27,
            "memory_write": 3,
            "parameter_field_read": 12,
            "parameter_field_write": 2,
            "return_op": 1,
        },
        "summary_functions": 1,
        "summary_claims": 18,
        "summary_claims_by_kind": {
            "direct_call": 4,
            "indirect_call": 1,
            "memory_read": 1,
            "memory_write": 1,
            "parameter_field_read": 8,
            "parameter_field_write": 2,
            "return_op": 1,
        },
    }
