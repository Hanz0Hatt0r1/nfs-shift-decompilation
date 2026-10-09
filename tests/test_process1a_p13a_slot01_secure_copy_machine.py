import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1a_slot01_secure_copy_machine.py"
EVIDENCE = ROOT / "evidence" / "p1a_p13a_slot01_nearest_secure_copy_machine_proof.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1a_secure_copy", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_machine_verifier_pins_copy_targets_and_backing_pointer_flow():
    module = load_module()
    assert module.RETAIL_SHA256 == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert module.EXPECTED_CALL_TARGETS[0x0063124D] == 0x00906FB6
    assert module.EXPECTED_CALL_TARGETS[0x0063179C] == 0x00900DEA
    assert module.EXPECTED_BYTES[0x006310FE] == "8d4806"
    assert module.EXPECTED_BYTES[0x0063110E] == "890f"
    assert module.EXPECTED_BYTES[0x00631247] == "8b0f"
    assert module.EXPECTED_BYTES[0x00631796] == "8b03"


def test_nearest_game_side_receivers_are_exactly_bounded():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    proof = payload["nearest_branch_proof"]
    assert proof["FUN_0070fae0_receivers"] == [
        "object+0x370",
        "object+0x374",
        "object+0x378",
        "object+0x37c",
        "object+0x380",
        "stack-local string object fed from object+0x380",
    ]
    assert proof["FUN_00647820_receiver"] == "containing object+0x24"
    assert proof["copy_destination_domain"] == "separately allocated string backing storage reached through [string_object]"
    assert proof["writes_inline_wheel_target_bytes"] is False
    assert set(proof["targets_rejected"]) == {
        "HDVehicle+0x938",
        "HDVehicle+0x13b8",
        "wheel-local +0x538",
    }


def test_only_nearest_secure_copy_subset_closes():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.P1A.P13ASlot01NearestSecureCopyMachineProof/1"
    adj = payload["adjudication"]
    assert adj["nearest_named_secure_copy_branches_rejected_as_slot01_target_writers"] is True
    assert adj["all_named_copy_paths_exhausted"] is False
    assert adj["inline_or_custom_bulk_copy_ruled_out"] is False
    assert adj["indirect_copy_dispatch_ruled_out"] is False
    assert adj["slot0_selected_root_alias_callee_bulk_copy_complete"] is False
    assert adj["slot1_selected_root_alias_callee_bulk_copy_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
