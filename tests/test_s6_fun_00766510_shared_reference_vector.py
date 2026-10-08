from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00766510_shared_reference_vector.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00766510_shared_reference_vector.hpp"
TEST = ROOT / "native_runtime/tests/fun_00766510_shared_reference_vector_check.cpp"
OWNER_PROOF = ROOT / "evidence/outer_vehicle_chassis_owner_join_retail.json"
PHASE746 = ROOT / "native_runtime/cmake/phase746.cmake"
PHASE747 = ROOT / "native_runtime/cmake/phase747.cmake"


def test_phase747_owner_chain_is_source_backed_and_dynamic() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun00766510SharedReferenceVector/1"
    assert payload["ready"] is True
    assert payload["source"]["decompiler_sha256"] == (
        "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    )
    owner = payload["owner_chain"]
    assert owner["hdvehicle_owner_record"] == "HDVehicle+0x3fe8"
    assert owner["actual_participant"] == "*([HDVehicle+0x3fe8])"
    assert owner["participant_source_offsets"] == ["0x16b4", "0x16b8", "0x16bc"]
    assert owner["participant_source_storage"] == "three f32 lanes"
    writer = payload["writer"]
    assert writer["function"] == "FUN_00713630"
    assert writer["value_is_immutable_setup_constant"] is False
    assert "modulo 3" in writer["scheduler"]


def test_phase747_reuses_existing_owner_proof_and_exact_transform() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    owner_proof = json.loads(OWNER_PROOF.read_text(encoding="utf-8"))
    assert payload["owner_chain"]["independent_owner_proof"] == (
        "SHIFT.OuterVehicleChassisOwnerJoin/1"
    )
    assert owner_proof["format"] == "SHIFT.OuterVehicleChassisOwnerJoin/1"

    header = HEADER.read_text(encoding="utf-8")
    assert "SHIFT.Fun00766510SharedReferenceVector/1" in header
    assert "kFun00766510VehicleOwnerRecordOffset = 0x3fe8u" in header
    assert "0x16b4u" in header and "0x16b8u" in header and "0x16bcu" in header
    assert "static_cast<double>(participant_source[axis])" in header
    assert "transform_fun_007af0a0_refresh" in header
    test = TEST.read_text(encoding="utf-8")
    assert "explicit_f32_to_f64_widening" in test
    assert "body_transform_native" in test


def test_phase747_scope_does_not_remove_contact_response_early() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    scope = payload["scope"]
    assert scope["external_provider_count_before"] == 7
    assert scope["external_provider_count_after"] == 7
    assert scope["provider_count_reduced"] is False
    assert scope["contact_response_provider_removed"] is False
    assert scope["participant_source_owner_closed"] is True
    assert scope["shared_reference_transform_internalized"] is True
    assert scope["participant_dynamic_writer_value_internalized"] is False
    assert scope["early_response_branch_fully_scheduled"] is False
    assert scope["auxiliary_pair_fully_scheduled"] is False


def test_phase747_cmake_chains_after_phase746() -> None:
    phase746 = PHASE746.read_text(encoding="utf-8")
    phase747 = PHASE747.read_text(encoding="utf-8")
    assert "include(${CMAKE_CURRENT_LIST_DIR}/phase747.cmake)" in phase746
    assert "shift_runtime_fun_00766510_shared_reference_vector_check" in phase747
