import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p2_4_fun_0075cfb0_load_store_surface.json"
HEADER = ROOT / "native_runtime/include/shift_fun_0075cfb0_load_store_surface.hpp"
FRONTIER = ROOT / "src/physics/native_vehicle_external_provider_frontier_p2_4_current.py"


def test_load_store_surface_pins_retail_sites_and_wheel_destinations() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun0075cfb0LoadStoreSurface/1"
    assert payload["machine_store_surface"]["entry"] == "0x0075cfb0"
    assert payload["machine_store_surface"]["entry_initialization_store"].startswith(
        "0x0075d001"
    )
    assert payload["machine_store_surface"]["runtime_stores"] == [
        "0x0075ff25 FST qword [ESI+0x738]",
        "0x0075ff3e FSTP qword [ESI+0x738]",
    ]
    assert payload["wheel_layout"]["hdvehicle_offsets"] == [
        "0x0b38",
        "0x15b8",
        "0x2038",
        "0x2ab8",
    ]


def test_load_store_surface_preserves_opaque_qword_contract() -> None:
    text = HEADER.read_text(encoding="utf-8")
    assert '"SHIFT.Fun0075cfb0LoadStoreSurface/1"' in text
    assert "std::uint64_t qword_bits" in text
    assert "kFun0075cfb0WheelLoadFieldOffset = 0x0738u" in text
    assert "0x0075d001u" in text
    assert "0x0075ff25u" in text
    assert "0x0075ff3eu" in text
    assert "std::isfinite" not in text


def test_load_store_surface_does_not_promote_unresolved_wheel_job_formula() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    limits = payload["limits"]
    assert limits["FUN_0075cfb0_producer_arithmetic_internalized"] is False
    assert limits["store_branch_predicates_internalized"] is False
    assert limits["producer_family_independently_proven"] is False
    assert limits["residual_producer_promotion_bit_set"] is False
    assert limits["complete_FUN_00765c40_internalized"] is False
    assert limits["top_level_provider_removed"] is False
    assert limits["external_provider_count_after"] == 7

    frontier = FRONTIER.read_text(encoding="utf-8")
    assert '"wheel_job_formula_FUN_0075cfb0"' in frontier
