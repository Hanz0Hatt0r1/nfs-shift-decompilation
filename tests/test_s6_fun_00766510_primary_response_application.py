from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00766510_primary_response_application.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00766510_primary_response_application.hpp"
PHASE741 = ROOT / "native_runtime/cmake/phase741.cmake"
PHASE742 = ROOT / "native_runtime/cmake/phase742.cmake"


def test_phase742_evidence_freezes_exact_primary_application_only() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun00766510PrimaryResponseApplication/1"
    assert payload["ready"] is True
    assert payload["platform_authority"] == "PC retail primary"
    source = payload["pc_source"]
    assert source["response_builder_source_line"] == 759686
    assert source["response_transform_source_line"] == 759687
    assert source["response_application_source_line"] == 759688
    machine = payload["pc_machine"]
    assert machine["transform_and_application_span"]["start"] == "0x00766fb2"
    assert machine["transform_and_application_span"]["end_exclusive"] == "0x00766fd6"
    assert machine["transform_and_application_span"]["raw_byte_sha256"] == (
        "db2e2358db25f5cc7a6d869e2a346fc40b0562702c79a32ea4245b4d4ea7dc57"
    )
    assert machine["builder_through_application_span"]["raw_byte_sha256"] == (
        "cc9944a9c145e66a5db6bc6f4fc5aadb8d4d9a245f6e740a8aac3bd256a5bbde"
    )

    ownership = payload["ownership"]
    assert ownership["body_pointer"] == "HDVehicle+0x33a0"
    assert ownership["selected_bmw_body_index"] == 0
    assert ownership["application_point"] == "HDVehicle+0x38f0"
    assert ownership["response_table"] == "HDVehicle+0x3950"

    scope = payload["scope"]
    assert scope["external_provider_count_before"] == 7
    assert scope["external_provider_count_after"] == 7
    assert scope["provider_count_reduced"] is False
    assert scope["primary_response_application_internalized"] is True
    assert scope["complete_FUN_00766510_internalized"] is False
    assert scope["contact_response_provider_removed"] is False


def test_phase742_native_helper_reuses_existing_exact_primitives_in_source_order() -> None:
    text = HEADER.read_text(encoding="utf-8")
    assert "SHIFT.Fun00766510PrimaryResponseApplication/1" in text
    assert "kFun00766510BodyPointerOffset = 0x33a0u" in text
    assert "kFun00766510BodyBasisOffset = 0xd4u" in text
    assert "kFun00766510ApplicationPointOffset = 0x38f0u" in text
    assert "kFun00766510ResponseTableOffset = 0x3950u" in text
    assert "kFun00766510SelectedBmwBodyIndex = 0u" in text
    assert "input.response.response_vector" in text

    transform = text.index("transform_fun_007aefb0_refresh")
    apply = text.index("apply_fun_007baa70_body_accumulator")
    assert transform < apply
    assert "transform_fun_00766510" not in text
    assert "apply_fun_00766510" not in text


def test_phase742_xbox_is_corroboration_not_pc_precision_authority() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    xbox = payload["xbox_crosscheck"]
    assert xbox["recomp_partition"] == "nfs_shift_recomp.220.cpp"
    assert "corroboration" in xbox["role"]
    assert xbox["pc_precision_inferred_from_xbox"] is False


def test_phase742_cmake_chains_after_phase741() -> None:
    phase741 = PHASE741.read_text(encoding="utf-8")
    phase742 = PHASE742.read_text(encoding="utf-8")
    assert "include(${CMAKE_CURRENT_LIST_DIR}/phase742.cmake)" in phase741
    assert "shift_runtime_fun_00766510_primary_response_application_check" in phase742
