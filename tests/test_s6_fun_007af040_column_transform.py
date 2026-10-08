from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_007af040_column_transform.json"
HEADER = ROOT / "native_runtime/include/shift_fun_007af040_column_transform.hpp"
TEST = ROOT / "native_runtime/tests/fun_007af040_column_transform_check.cpp"
PHASE747 = ROOT / "native_runtime/cmake/phase747.cmake"
PHASE748 = ROOT / "native_runtime/cmake/phase748.cmake"


def test_phase748_source_contract_is_exact() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun007af040ColumnTransform/1"
    assert payload["ready"] is True
    assert payload["source"]["definition_source_line"] == 810251
    assert payload["source"]["fun_00766510_call_source_line"] == 759615
    contract = payload["contract"]
    assert contract["explicit_scalar_narrowing"] == "f64 -> f32 before multiplication"
    assert contract["matrix_column_byte_offsets"] == ["0x04", "0x10", "0x1c"]
    assert contract["output_storage"] == "three f64 lanes widened from three f32 products"


def test_phase748_active_helper_preserves_source_rounding() -> None:
    header = HEADER.read_text(encoding="utf-8")
    test = TEST.read_text(encoding="utf-8")
    assert "SHIFT.Fun007af040ColumnTransform/1" in header
    assert "const float narrowed = static_cast<float>(scalar)" in header
    assert "matrix[1] * narrowed" in header
    assert "matrix[4] * narrowed" in header
    assert "matrix[7] * narrowed" in header
    assert "0x40490fdd" in test
    assert "0xc02df855" in test
    assert "0x3eaaaaac" in test


def test_phase748_scope_stays_narrow() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    scope = payload["scope"]
    assert scope["external_provider_count_before"] == 7
    assert scope["external_provider_count_after"] == 7
    assert scope["provider_count_reduced"] is False
    assert scope["contact_response_provider_removed"] is False
    assert scope["FUN_007af040_internalized"] is True
    assert scope["optional_branch_config_internalized"] is False


def test_phase748_cmake_chains_after_phase747() -> None:
    assert "include(${CMAKE_CURRENT_LIST_DIR}/phase748.cmake)" in PHASE747.read_text(encoding="utf-8")
    assert "shift_runtime_fun_007af040_column_transform_check" in PHASE748.read_text(encoding="utf-8")
