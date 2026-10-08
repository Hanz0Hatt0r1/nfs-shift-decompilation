from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00766510_primary_caller_accumulator.json"
BODY_HEADER = ROOT / "native_runtime/include/shift_body_accumulator_primitives.hpp"
BODY_SOURCE = ROOT / "native_runtime/src/body_accumulator_primitives.cpp"
PRIMARY_HEADER = ROOT / "native_runtime/include/shift_fun_00766510_primary_response_application.hpp"
PRIMARY_TEST = ROOT / "native_runtime/tests/fun_00766510_primary_response_application_check.cpp"
PHASE745 = ROOT / "native_runtime/cmake/phase745.cmake"
PHASE746 = ROOT / "native_runtime/cmake/phase746.cmake"


def test_phase746_pc_source_and_machine_spans_are_frozen() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun00766510PrimaryCallerAccumulator/1"
    assert payload["ready"] is True
    assert payload["platform_authority"] == "PC retail primary"
    source = payload["source"]
    assert source["fun_00753650_source_line"] == 749322
    assert source["primary_application_source_lines"] == [759686, 759692]
    assert source["machine_span"]["raw_byte_sha256"] == (
        "3e1bb93c36162aa474335af341f6f7d24d21183c644a309acd8dd2c2de9a84c7"
    )
    assert source["cross_and_caller_store_span"]["raw_byte_sha256"] == (
        "5813de173dee954d843b69c1b0bf9491863f1094b858509bdf0f03d01183be2a"
    )


def test_phase746_active_native_contract_uses_explicit_fun_00753650() -> None:
    body_header = BODY_HEADER.read_text(encoding="utf-8")
    body_source = BODY_SOURCE.read_text(encoding="utf-8")
    primary = PRIMARY_HEADER.read_text(encoding="utf-8")
    test = PRIMARY_TEST.read_text(encoding="utf-8")

    assert 'kBodyCrossProductSourceFunction =\n    "FUN_00753650"' in body_header
    assert "execute_fun_00753650_cross_product" in body_header
    assert "execute_fun_00753650_cross_product" in body_source
    assert "execute_fun_00753650_cross_product(" in body_source
    assert "SHIFT.Fun00766510PrimaryResponseApplication/2" in primary
    assert "kFun00766510CallerAccumulatorOffsets" in primary
    assert "0x40a0u" in primary and "0x40a8u" in primary and "0x40b0u" in primary
    assert "caller_accumulator_delta = execute_fun_00753650_cross_product" in primary
    assert "body_accumulator.angular[component] -" not in primary
    assert "caller_accumulator_delta_native" in test


def test_phase746_scope_does_not_overclaim_whole_fun_00766510() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    inventory = payload["whole_function_accumulator_inventory"]
    assert inventory["direct_FUN_00753650_add_sites_in_FUN_00766510"] == 4
    assert inventory["auxiliary_FUN_00758fc0_calls"] == 2
    assert inventory["final_transformed_vector_add_site"] == 1
    assert inventory["this_phase_closes_only_primary_0x38f0_0x3950_direct_site"] is True

    scope = payload["scope"]
    assert scope["external_provider_count_before"] == 7
    assert scope["external_provider_count_after"] == 7
    assert scope["provider_count_reduced"] is False
    assert scope["contact_response_provider_removed"] is False
    assert scope["whole_40a0_accumulator_internalized"] is False
    assert scope["primary_direct_accumulator_delta_internalized"] is True
    assert scope["physical_semantics_invented"] is False


def test_phase746_cmake_chains_after_phase745() -> None:
    phase745 = PHASE745.read_text(encoding="utf-8")
    phase746 = PHASE746.read_text(encoding="utf-8")
    assert "include(${CMAKE_CURRENT_LIST_DIR}/phase746.cmake)" in phase745
    assert "Phase 746" in phase746
