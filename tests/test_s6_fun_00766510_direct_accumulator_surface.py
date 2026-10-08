from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00766510_direct_accumulator_surface_native.json"
OWNER = ROOT / "evidence/fun_00766510_direct_caller_accumulator_surface.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00766510_direct_accumulator_surface.hpp"
PHASE752 = ROOT / "native_runtime/cmake/phase752.cmake"
PHASE753 = ROOT / "native_runtime/cmake/phase753.cmake"


def test_phase753_consumes_closed_direct_surface() -> None:
    native = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    owner = json.loads(OWNER.read_text(encoding="utf-8"))
    assert native["format"] == "SHIFT.Fun00766510DirectAccumulatorSurface/1"
    assert native["ready"] is True
    assert native["authority"]["ownership_contract"] == owner["format"]
    assert owner["ready"] is True
    assert owner["adjudication"]["four_direct_caller_cross_product_sites_closed"] is True
    assert owner["adjudication"]["whole_caller_accumulator_closed"] is False


def test_phase753_pins_four_direct_sites() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["accumulator"]["offsets"] == ["+0x40a0", "+0x40a8", "+0x40b0"]
    assert payload["accumulator"]["direct_site_count"] == 4
    assert [site["source_line"] for site in payload["direct_sites"]] == [
        759558, 759621, 759692, 759732
    ]
    assert [site["conditional"] for site in payload["direct_sites"]] == [
        True, True, False, True
    ]


def test_phase753_does_not_reorder_unresolved_accumulator_schedule() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    native = payload["native_contract"]
    scope = payload["scope"]
    assert native["fun_00753650_cross_product_primitive_reused"] is True
    assert native["source_computed_delta_applied_one_site_at_a_time"] is True
    assert native["four_sites_batched_or_reordered"] is False
    assert scope["auxiliary_pair_scheduling_internalized"] is False
    assert scope["final_transformed_vector_add_internalized"] is False
    assert scope["whole_caller_accumulator_closed"] is False
    assert scope["contact_response_provider_removed"] is False
    assert scope["external_provider_count_after"] == 7

    header = HEADER.read_text(encoding="utf-8")
    assert "apply_fun_00766510_direct_accumulator_delta" in header
    assert "does not batch/reorder all four direct" in header


def test_phase753_cmake_is_chained_after_phase752() -> None:
    assert "include(${CMAKE_CURRENT_LIST_DIR}/phase753.cmake)" in PHASE752.read_text(encoding="utf-8")
    assert "shift_runtime_fun_00766510_direct_accumulator_surface_check" in PHASE753.read_text(encoding="utf-8")
