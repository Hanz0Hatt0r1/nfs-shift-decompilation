import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1d_slot3_fun00765c40_wheel_7a8_alias_pe.py"
EVIDENCE = ROOT / "evidence" / "p1d_slot3_fun00765c40_wheel_7a8_alias_closure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_765c40_wheel_7a8", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pinned_wheel_7a8_alias_is_register_only_and_target_disjoint():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1D.Slot3Fun00765c40Wheel7a8AliasClosure/1"
    alias = data["wheel_alias"]
    assert alias["vehicle_relative_aliases"] == [
        "+0x0ba8",
        "+0x1628",
        "+0x20a8",
        "+0x2b28",
    ]
    assert alias["selected_slot3_alias"] == "HDVehicle+0x2b28 = wheel+0x7a8"
    assert alias["pointer_store_found"] is False
    assert alias["pointer_push_found"] is False
    assert alias["direct_call_count"] == 0
    writes = data["writes"]
    assert writes["per_wheel_offsets"] == ["+0x7a0 qword", "+0x7a8 qword"]
    assert writes["selected_slot3_vehicle_relative_offsets"] == [
        "+0x2b20 qword",
        "+0x2b28 qword",
    ]
    assert writes["selected_target_overlap"] is False


def test_global_alias_and_writer_gates_remain_fail_closed():
    gates = json.loads(EVIDENCE.read_text(encoding="utf-8"))["adjudication"]
    assert gates["fun00765c40_wheel_7a8_register_alias_subset_complete"] is True
    assert gates["fun00765c40_selected_slot3_wheel_7a8_alias_reached"] is True
    assert gates["fun00765c40_selected_slot3_wheel_7a8_pointer_escape_found"] is False
    assert gates["fun00765c40_wheel_7a8_selected_target_writer_found"] is False
    assert gates["other_fun00765c40_derived_aliases_ruled_out"] is False
    assert gates["machine_register_alias_storage_ruled_out"] is False
    assert gates["stored_or_escaped_aliases_ruled_out"] is False
    assert gates["slot3_writer_provenance_proven"] is False
    assert gates["p1_3d_complete"] is False
    assert gates["external_provider_count"] == 7


def test_machine_window_drift_fails_closed():
    module = load_module()
    with pytest.raises(ValueError, match="machine-window drift"):
        module.verify_window([], module.LOOP, "wheel+0x7a8 loop")


def test_unproven_handoff_fails_closed(tmp_path):
    module = load_module()
    handoff = tmp_path / "handoff.json"
    handoff.write_text(
        json.dumps(
            {
                "format": module.HANDOFF_FORMAT,
                "ready": True,
                "authority": {"retail_executable_sha256": module.PE_SHA256},
                "carrier": {"function": "FUN_00765c40", "receiver_domain": "HDVehicle"},
                "selected_slot3": {"absolute_target": "HDVehicle+0x28b8"},
                "adjudication": {"fun00765c40_exact_hdvehicle_carrier_handoff_complete": False},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="handoff is not complete"):
        module.load_handoff(handoff)
