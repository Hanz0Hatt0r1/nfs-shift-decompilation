from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p2_4_fun_007584f0_persistent_write_stage.json"
PROOF = ROOT / "evidence/fun_007584f0_machine_side_effect_proof.json"
HEADER = ROOT / "native_runtime/include/shift_fun_007584f0_persistent_write_stage.hpp"
TEST = ROOT / "native_runtime/tests/fun_007584f0_persistent_write_stage_check.cpp"
CMAKE = ROOT / "native_runtime/cmake/p2_4_fun_00765c40.cmake"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_p2_4_write_stage_consumes_machine_proof_without_arithmetic_claim() -> None:
    native = _json(EVIDENCE)
    proof = _json(PROOF)
    assert native["format"] == "SHIFT.Fun007584f0PersistentWriteStage/1"
    assert native["ready"] is True
    assert native["authority"]["machine_proof"] == proof["format"]
    assert proof["ready"] is True
    assert proof["adjudication"]["persistent_object_write_surface_complete"] is True
    contract = native["native_contract"]
    assert contract["branch_and_write_semantics_internalized"] is True
    assert contract["positive_branch_arithmetic_internalized"] is False
    assert contract["FUN_00783a30_arithmetic_internalized"] is False
    assert contract["source_computed_values_are_explicit_inputs"] is True


def test_p2_4_write_stage_pins_exact_persistent_destinations() -> None:
    writes = _json(EVIDENCE)["persistent_writes"]
    assert writes["wheel_values"]["offsets"] == ["+0x0d40", "+0x17c0"]
    assert writes["wheel_values"]["wheel_indices"] == [0, 1]
    assert writes["wheel_values"]["stride"] == "0x0a80"
    assert writes["filtered_value"]["offset"] == "+0x3420"
    assert writes["filtered_value"]["width"] == "float"

    proof_offsets = []
    for row in _json(PROOF)["persistent_object_writes"]:
        proof_offsets.extend(row.get("hdvehicle_offsets", []))
        if "hdvehicle_offset" in row:
            proof_offsets.append(row["hdvehicle_offset"])
    assert proof_offsets == ["+0x0d40", "+0x17c0", "+0x3420"]


def test_p2_4_write_stage_internalizes_zero_branch_only_when_load_nonpositive() -> None:
    header = HEADER.read_text(encoding="utf-8")
    native_test = TEST.read_text(encoding="utf-8")
    assert "load_terms[wheel] <= 0.0 ? 0.0" in header
    assert "computed.positive_branch_values[wheel]" in header
    assert "state.filtered_value = computed.interpolation_result" in header
    assert "non-positive load must write zero qword" in native_test
    assert "positive load must preserve computed qword" in native_test
    assert "zero load must take alternate zero branch" in native_test


def test_p2_4_write_stage_remains_fail_closed_for_provider_removal() -> None:
    scope = _json(EVIDENCE)["scope"]
    assert scope["FUN_007584f0_persistent_write_stage_internalized"] is True
    assert scope["complete_FUN_007584f0_internalized"] is False
    assert scope["complete_FUN_00765c40_internalized"] is False
    assert scope["top_level_FUN_00765c40_provider_removed"] is False
    assert scope["external_provider_count_before"] == 7
    assert scope["external_provider_count_after"] == 7


def test_p2_4_write_stage_is_chained_into_stable_blocker_cmake() -> None:
    cmake = CMAKE.read_text(encoding="utf-8")
    assert "shift_runtime_fun_007584f0_persistent_write_stage_check" in cmake
    assert "phase754" not in cmake.lower()
