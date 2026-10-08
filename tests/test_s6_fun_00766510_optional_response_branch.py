from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00766510_optional_response_native.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00766510_optional_response_branch.hpp"
TEST = ROOT / "native_runtime/tests/fun_00766510_optional_response_branch_check.cpp"
PHASE750 = ROOT / "native_runtime/cmake/phase750.cmake"
PHASE751 = ROOT / "native_runtime/cmake/phase751.cmake"
PROCESS1 = ROOT / "evidence/fun_00766510_optional_response_branch_ownership.json"


def test_phase751_consumes_positive_process1_contract() -> None:
    native = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    owner = json.loads(PROCESS1.read_text(encoding="utf-8"))
    assert native["format"] == "SHIFT.Fun00766510OptionalResponseBranch/1"
    assert native["ready"] is True
    assert native["authority"]["ownership_contract"] == owner["format"]
    assert owner["ready"] is True
    assert owner["adjudication"]["optional_branch_owner_closed"] is True
    assert owner["adjudication"]["contact_response_provider_removable_now"] is False


def test_phase751_pins_setup_owned_optional_block() -> None:
    setup = json.loads(EVIDENCE.read_text(encoding="utf-8"))["setup_contract"]
    assert setup["gate_offset"] == "+0x3bc8"
    assert setup["mutable_initial_offset"] == "+0x3bd0"
    assert setup["coefficient_offsets"] == [
        "+0x3bd8", "+0x3be0", "+0x3be8", "+0x3bf0", "+0x3bf8",
        "+0x3c00", "+0x3c08", "+0x3c10", "+0x3c30",
    ]
    assert setup["derived_shape_offsets"] == [
        "+0x3c18", "+0x3c20", "+0x3c28", "+0x3c38"
    ]
    assert setup["curve_offset"] == "+0x3c40"
    assert setup["application_vector"] == ["+0x3c60", "+0x3c68", "+0x3c70"]


def test_phase751_preserves_mutable_3bd0_without_inventing_arithmetic() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    mutable = payload["persistent_mutable"]
    assert mutable["offset"] == "+0x3bd0"
    assert mutable["setup_constant"] is False
    assert mutable["writer_arithmetic_internalized"] is False
    assert mutable["source_computed_results_are_explicit_inputs"] is True
    assert len(mutable["writer_surface"]) == 5

    header = HEADER.read_text(encoding="utf-8")
    test = TEST.read_text(encoding="utf-8")
    assert "Fun00766510OptionalMutableWriteSource" in header
    assert "source_computed_value" in header
    assert "instead of inventing increment/clamp/reset formulas" in header
    assert "Fun0076ed60StateLoad" in test


def test_phase751_internalizes_only_exact_runtime_gate() -> None:
    gate = json.loads(EVIDENCE.read_text(encoding="utf-8"))["runtime_gate"]
    assert gate["formula"] == "+0x3bc8 != 0 and local_50 < 0"
    assert gate["internalized"] is True
    assert gate["coefficient_polynomial_internalized"] is False
    assert gate["curve_scaled_negative_result_path_internalized"] is False

    header = HEADER.read_text(encoding="utf-8")
    assert "setup.gate_enabled && local_50 < 0.0" in header


def test_phase751_remains_fail_closed_for_provider_removal() -> None:
    scope = json.loads(EVIDENCE.read_text(encoding="utf-8"))["scope"]
    assert scope["optional_branch_setup_consumed_by_process2"] is True
    assert scope["persistent_writer_surface_consumed_by_process2"] is True
    assert scope["body_scalar_path_internalized"] is False
    assert scope["body_apply_internalized"] is False
    assert scope["caller_accumulator_internalized"] is False
    assert scope["diagnostic_tail_internalized"] is False
    assert scope["contact_response_provider_removed"] is False
    assert scope["external_provider_count_before"] == 7
    assert scope["external_provider_count_after"] == 7


def test_phase751_cmake_is_chained_after_phase750() -> None:
    phase750 = PHASE750.read_text(encoding="utf-8")
    phase751 = PHASE751.read_text(encoding="utf-8")
    assert "include(${CMAKE_CURRENT_LIST_DIR}/phase751.cmake)" in phase750
    assert "shift_runtime_fun_00766510_optional_response_branch_check" in phase751
