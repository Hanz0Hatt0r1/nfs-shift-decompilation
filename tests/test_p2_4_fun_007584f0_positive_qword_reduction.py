import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p2_4_fun_007584f0_positive_qword_reduction.json"
HEADER = ROOT / "native_runtime/include/shift_fun_007584f0_positive_qword_reduction.hpp"
PERSISTENT = ROOT / "native_runtime/include/shift_fun_007584f0_persistent_write_stage.hpp"
FRONTIER = ROOT / "src/physics/native_vehicle_external_provider_frontier_p2_4_current.py"


def test_positive_qword_reduction_pins_exact_retail_span_and_formula() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun007584f0PositiveQwordReduction/1"
    machine = payload["machine_reduction"]
    assert machine["start"] == "0x007586f9"
    assert machine["end_exclusive"] == "0x00758731"
    assert machine["size"] == 56
    assert machine["raw_byte_sha256"] == (
        "c8f5e51aeeb6a14a947ba7c5c1d44ec8b3c687765377ba8b01254c15c38e9b0f"
    )
    assert machine["numerator"] == "A[1]*B[1] + A[0]*B[0] + A[2]*B[2]"
    assert machine["denominator"] == "A[1]*C[1] + A[0]*C[0] + A[2]*C[2]"
    assert machine["result"] == "numerator / denominator"
    assert machine["accumulation_component_order"] == [1, 0, 2]


def test_positive_qword_reduction_keeps_vector_producers_fail_closed() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    limits = payload["limits"]
    assert limits["A_B_C_vector_construction_internalized"] is False
    assert limits["x87_extended_precision_bit_parity_claimed"] is False
    assert limits["positive_qword_producer_family_complete"] is False
    assert limits["FUN_007584f0_computed_payloads_complete"] is False
    assert limits["residual_producer_promotion_bit_set"] is False
    assert limits["complete_FUN_00765c40_internalized"] is False
    assert limits["top_level_provider_removed"] is False
    assert limits["external_provider_count_after"] == 7

    frontier = FRONTIER.read_text(encoding="utf-8")
    assert '"FUN_007584f0_computed_payloads"' in frontier


def test_positive_qword_reduction_header_preserves_retail_order_and_geometry() -> None:
    text = HEADER.read_text(encoding="utf-8")
    assert '"SHIFT.Fun007584f0PositiveQwordReduction/1"' in text
    assert "0x007586f9u" in text
    assert "0x00758731u" in text
    assert "0x0075873bu" in text
    assert "input.a[1] * input.b[1]" in text
    assert "input.a[0] * input.b[0]" in text
    assert "input.a[2] * input.b[2]" in text
    assert "input.a[1] * input.c[1]" in text
    assert "input.a[0] * input.c[0]" in text
    assert "input.a[2] * input.c[2]" in text
    assert "numerator / denominator" in text
    assert "0x0d40u" in text
    assert "0x0a80u" in text
    assert "0x17c0u" in text
    assert "std::isfinite" in text


def test_existing_persistent_stage_remains_branch_and_destination_owner() -> None:
    text = PERSISTENT.read_text(encoding="utf-8")
    assert "load_terms[wheel] <= 0.0 ? 0.0 : computed.positive_branch_values[wheel]" in text
    assert "0x0d40u, 0x17c0u" in text
    assert "computed_arithmetic" not in text
