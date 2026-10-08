import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p2_4_fun_00765c40_optional_body_accumulator_sweep.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_optional_body_accumulator_sweep.hpp"
CMAKE = ROOT / "native_runtime/cmake/p2_4_fun_00765c40.cmake"
DOC = ROOT / "docs/P2_4_FUN_00765C40_OPTIONAL_BODY_ACCUMULATOR_SWEEP.md"


def test_optional_body_accumulator_sweep_contract_is_exact_and_fail_closed() -> None:
    payload = json.loads(EVIDENCE.read_text())
    assert payload["format"] == "SHIFT.Fun00765c40OptionalBodyAccumulatorSweep/1"
    assert payload["ready"] is True

    surface = payload["retail_surface"]
    assert surface["caller_function"] == "FUN_00765c40"
    assert surface["loop_call_site"] == "0x007664f2"
    assert surface["callee"] == "FUN_007baa70"
    assert surface["receiver"] == "[HDVehicle+0x33a0] selected BODY0"
    assert surface["entry_count"] == 4
    assert surface["final_residual_stage"] is True
    assert surface["enabled_condition_proven"] is False
    assert surface["point_or_lever_arm_producer_proven"] is False
    assert surface["contribution_producer_proven"] is False

    semantics = payload["body_accumulator_semantics"]
    assert semantics["angular_offsets"] == ["+0x48", "+0x50", "+0x58"]
    assert semantics["linear_offsets"] == ["+0x60", "+0x68", "+0x70"]
    assert semantics["angular_update"] == "angular += point_or_lever_arm x contribution"
    assert semantics["linear_update"] == "linear += contribution"

    native = payload["native_consumption"]
    assert native["enabled_is_explicit_input"] is True
    assert native["four_entry_inputs_are_explicit"] is True
    assert native["existing_fun_007baa70_primitive_reused"] is True
    assert native["disabled_path_preserves_body_state"] is True
    assert native["enabled_path_applies_exactly_four_entries"] is True
    assert native["predicate_internalized"] is False
    assert native["entry_input_producers_internalized"] is False

    scope = payload["scope"]
    assert scope["complete_FUN_00765c40_internalized"] is False
    assert scope["top_level_FUN_00765c40_provider_removed"] is False
    assert scope["external_provider_count_after"] == 7


def test_native_header_reuses_proven_body_primitive_and_final_stage_order() -> None:
    text = HEADER.read_text()
    assert "SHIFT.Fun00765c40OptionalBodyAccumulatorSweep/1" in text
    assert "kFun00765c40OptionalBodyAccumulatorEntryCount = 4u" in text
    assert "0x007664f2u" in text
    assert "apply_fun_007baa70_body_accumulator" in text
    assert "OptionalBodyAccumulatorSweep" in text
    assert "if (!input.enabled)" in text


def test_stable_p2_4_cmake_and_docs_keep_provider_fail_closed() -> None:
    cmake = CMAKE.read_text()
    assert "shift_runtime_fun_00765c40_optional_body_accumulator_sweep_check" in cmake
    assert "native-physics-phase" not in cmake

    doc = DOC.read_text()
    assert "external provider count: remains 7" in doc
    assert "enabling predicate: still external" in doc
    assert "four entry input producers: still external" in doc
