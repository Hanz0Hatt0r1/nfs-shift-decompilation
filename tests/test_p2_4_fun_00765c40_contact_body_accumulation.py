import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p2_4_fun_00765c40_contact_body_accumulation.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_contact_body_accumulation.hpp"
CMAKE = ROOT / "native_runtime/cmake/p2_4_fun_00765c40.cmake"
DOC = ROOT / "docs/P2_4_FUN_00765C40_CONTACT_BODY_ACCUMULATION.md"


def test_contact_body_accumulation_contract_is_exact_and_fail_closed() -> None:
    payload = json.loads(EVIDENCE.read_text())
    assert payload["format"] == "SHIFT.Fun00765c40ContactBodyAccumulation/1"
    assert payload["ready"] is True

    surface = payload["retail_surface"]
    assert surface["caller_function"] == "FUN_00765c40"
    assert surface["call_site"] == "0x00766365"
    assert surface["callee"] == "FUN_007baa70"
    assert surface["receiver"] == "[HDVehicle+0x33a0] selected BODY0"
    assert surface["contact_slot_count"] == 12
    assert surface["inside_contact_sweep"] is True
    assert surface["per_slot_predicate_proven"] is False
    assert surface["point_or_lever_arm_producer_proven"] is False
    assert surface["contribution_producer_proven"] is False

    native = payload["native_consumption"]
    assert native["twelve_ordered_entries"] is True
    assert native["per_slot_apply_is_explicit_input"] is True
    assert native["entry_vec3_inputs_are_explicit"] is True
    assert native["existing_fun_007baa70_primitive_reused"] is True
    assert native["false_slots_preserve_body_state"] is True
    assert native["predicate_internalized"] is False
    assert native["entry_input_producers_internalized"] is False

    scope = payload["scope"]
    assert scope["complete_FUN_00765c40_internalized"] is False
    assert scope["top_level_FUN_00765c40_provider_removed"] is False
    assert scope["external_provider_count_after"] == 7


def test_native_header_pins_contact_domain_and_proven_primitive() -> None:
    text = HEADER.read_text()
    assert "SHIFT.Fun00765c40ContactBodyAccumulation/1" in text
    assert "0x00766365u" in text
    assert "kFun00765c40ContactArraySlotCount" in text
    assert "if (!entry.apply)" in text
    assert "apply_fun_007baa70_body_accumulator" in text


def test_stable_p2_4_cmake_and_docs_keep_provider_fail_closed() -> None:
    cmake = CMAKE.read_text()
    assert "shift_runtime_fun_00765c40_contact_body_accumulation_check" in cmake
    assert "native-physics-phase" not in cmake

    doc = DOC.read_text()
    assert "external provider count: remains 7" in doc
    assert "per-slot source predicate: remains external" in doc
    assert "per-slot vec3 producer arithmetic: remains external" in doc
