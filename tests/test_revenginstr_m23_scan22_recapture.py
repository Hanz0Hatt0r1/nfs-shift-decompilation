import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.replay_revenginstr_m23_scan22_recapture import replay, validate_frozen
from tools.replay_revenginstr_m23_scan24_exact_root import (
    replay as replay_scan24,
    validate_frozen as validate_scan24_frozen,
)


def test_scan22_recapture_is_pinned_and_replays_fail_closed():
    evidence = ROOT / "evidence/revenginstr_m23_direct_call_replay"
    summary = validate_frozen(evidence)

    assert summary["caller_parameter_root_rows"] == 5
    assert summary["selected_caller_parameter_root_rows"] == 0
    assert summary["callee_cfg_rows"] == 4
    assert summary["callee_memory_store_access_rows"] == 12
    assert summary["interprocedural_status_counts"] == {
        "indirect_call": 18,
        "possible_aliasing_write": 4,
        "unknown_effect": 8,
    }
    assert summary["audit_v5_status_counts"] == {"store_not_dominating_load": 2}

    assert replay(evidence, Path(sys.executable).parent) == summary


def test_scan24_exact_root_screen_is_pinned_and_replays_fail_closed():
    evidence = ROOT / "evidence/revenginstr_m23_direct_call_replay"
    summary = validate_scan24_frozen(evidence)

    assert summary["function_entry"] == "00a271a0"
    assert summary["exact_root_callees"] == ["009eb3f0", "00a1d2c0"]
    assert summary["selected_parameter_store_rows"] == 4
    assert summary["selected_parameter_load_rows"] == 1
    assert summary["selected_field_pair_rows"] == 1
    assert summary["cfg_rows"] == 4
    assert summary["memory_store_access_rows"] == 17
    assert summary["interprocedural_status_counts"] == {
        "indirect_call": 3,
        "possible_aliasing_write": 1,
        "unknown_effect": 2,
    }
    assert summary["audit_v5_status_counts"] == {
        "possible_intervening_memory_effect": 1,
    }
    assert summary["negative_screen_counts"] == {
        "pcode_flow_rows": 69,
        "parameter_load_rows": 3,
        "parameter_field_store_rows": 0,
        "memory_store_access_rows": 2,
        "field_pair_rows": 0,
    }

    assert replay_scan24(evidence, Path(sys.executable).parent) == summary
