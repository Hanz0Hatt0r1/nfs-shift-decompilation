from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00766510_primary_response_post_application.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00766510_primary_response_post_application.hpp"
PHASE742_HEADER = ROOT / "native_runtime/include/shift_fun_00766510_primary_response_application.hpp"


def test_phase743_evidence_freezes_exact_pc_post_application_block() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun00766510PrimaryResponsePostApplication/1"
    assert payload["ready"] is True
    assert payload["platform_authority"] == "PC retail primary"
    assert payload["pc_source"]["source_line_start"] == 759689
    assert payload["pc_source"]["source_line_end"] == 759695
    assert payload["pc_machine"]["post_application_span"]["raw_byte_sha256"] == (
        "300ede8cca6353c0ccc96993161d299a67e337b5482c4ae40025e163069c07d7"
    )
    assert payload["pc_machine"]["fun_00753650_span"]["raw_byte_sha256"] == (
        "01a753b9668434bc769f1c9304931f0067e502e26f93097275e4c1b3469202ab"
    )
    assert payload["pc_machine"]["fun_00753650_x87_control_word"] == "0x027f"
    assert payload["pc_machine"]["fun_00753650_subtract_opcode"] == "de e9"


def test_phase743_native_contract_preserves_x87_order_and_offsets() -> None:
    header = HEADER.read_text(encoding="utf-8")
    assert "SHIFT.Fun00766510PrimaryResponsePostApplication/1" in header
    assert "kFun00766510CallerReferenceVectorOffset = 0x3b08u" in header
    assert "kFun00766510CallerCrossAccumulatorXOffset = 0x40a0u" in header
    assert "kFun00766510CallerCrossAccumulatorYOffset = 0x40a8u" in header
    assert "kFun00766510CallerCrossAccumulatorZOffset = 0x40b0u" in header
    assert "kFun00753650RetailX87ControlWord = 0x027fu" in header
    assert '".byte 0xde, 0xe9' in header
    assert "fun_00753650_pc_x87_cross" in header
    assert "execute_fun_00766510_primary_response_post_application" in header
    assert "caller_cross_accumulator[component] +=" in header
    assert "auxiliary_accumulator[component] +=" in header


def test_phase743_composes_after_phase742_without_overclaiming_provider_closure() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    native = payload["native_composition"]
    assert native["phase742_input"] == "transformed_response / local_120"
    assert native["cross_order"] == "caller_reference_vector cross transformed_response"
    assert native["caller_cross_accumulator_offsets"] == ["0x40a0", "0x40a8", "0x40b0"]

    scope = payload["scope"]
    assert scope["external_provider_count_before"] == 7
    assert scope["external_provider_count_after"] == 7
    assert scope["provider_count_reduced"] is False
    assert scope["complete_FUN_00766510_internalized"] is False
    assert scope["contact_response_provider_removed"] is False
    assert scope["caller_reference_owner_closed"] is False
    assert scope["incoming_auxiliary_accumulator_owner_closed"] is False
    assert scope["physical_semantics_invented"] is False

    phase742 = PHASE742_HEADER.read_text(encoding="utf-8")
    assert "execute_fun_00766510_primary_response_application" in phase742
