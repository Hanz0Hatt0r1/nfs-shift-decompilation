import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/build_p1d_slot3_fun00765c40_carrier_handoff.py"
OWNERSHIP = ROOT / "evidence/fun_00765c40_residual_ownership_frontier.json"
WRITES = ROOT / "evidence/fun_00765c40_direct_machine_write_surface.json"
WHEEL = ROOT / "evidence/fun_00752fa0_wheel_state_machine_proof.json"
TAIL = ROOT / "evidence/fun_007584f0_machine_side_effect_proof.json"
EVIDENCE = ROOT / "evidence/p1d_slot3_fun00765c40_carrier_handoff.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_765c40_handoff", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_builder_reproduces_checked_handoff():
    module = load_module()
    got = module.build(OWNERSHIP, WRITES, WHEEL, TAIL)
    expected = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert got == expected


def test_slot3_target_remains_disjoint_and_global_gates_fail_closed():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["carrier"]["function"] == "FUN_00765c40"
    assert data["carrier"]["direct_callsite"] == "0x0076d12b"
    assert data["carrier"]["receiver_domain"] == "HDVehicle"
    assert data["carrier"]["previous_p1d_exact_carrier_count"] == 15
    assert data["carrier"]["expanded_p1d_exact_carrier_count"] == 16
    assert data["write_surface"]["direct_target_overlap"] is False
    assert data["write_surface"]["fun00752fa0_target_overlap"] is False
    assert data["write_surface"]["fun007584f0_target_overlap"] is False
    gates = data["adjudication"]
    assert gates["fun00765c40_exact_hdvehicle_carrier_handoff_complete"] is True
    assert gates["fun00765c40_selected_slot3_writer_found"] is False
    assert gates["source_storage_replay_for_16_carriers_complete"] is False
    assert gates["runtime_generated_pointer_stores_ruled_out"] is False
    assert gates["stored_or_escaped_aliases_ruled_out"] is False
    assert gates["slot3_writer_provenance_proven"] is False
    assert gates["p1_3d_complete"] is False
    assert gates["external_provider_count"] == 7


def test_incomplete_upstream_side_effect_surface_fails_closed(tmp_path):
    module = load_module()
    payload = json.loads(OWNERSHIP.read_text(encoding="utf-8"))
    payload["side_effect_surface"]["callee_mediated_object_side_effects_closed"] = False
    path = tmp_path / "bad_ownership.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError):
        module.build(path, WRITES, WHEEL, TAIL)


def test_overlap_detection_is_not_offset_equality_only():
    module = load_module()
    assert module.overlaps(0x28B8, 8) is True
    assert module.overlaps(0x28B4, 8) is True
    assert module.overlaps(0x28C0, 8) is False
    assert module.overlaps(0x29F0, 8) is False
