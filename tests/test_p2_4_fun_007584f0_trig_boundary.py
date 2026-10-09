import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p2_4_fun_007584f0_trig_boundary.json"
HEADER = ROOT / "native_runtime/include/shift_fun_007584f0_trig_boundary.hpp"
VECTOR = ROOT / "native_runtime/include/shift_fun_007584f0_positive_qword_vector_construction.hpp"
FRONTIER = ROOT / "src/physics/native_vehicle_external_provider_frontier_p2_4_current.py"


def test_trig_boundary_pins_exact_caller_and_wrapper_machine_spans() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun007584f0TrigBoundary/1"
    caller = payload["caller_surface"]
    assert caller["start"] == "0x00758560"
    assert caller["end_exclusive"] == "0x0075858b"
    assert caller["size"] == 43
    assert caller["raw_byte_sha256"] == (
        "65d14dcffa1b71078029c5675f57374bb9c3f1a2fb46cc5ca25d55f0d765a27f"
    )
    assert caller["source"].endswith("+ 0x0738] qword")
    assert caller["call_order"] == ["0x00900b10 cosine", "0x00900c40 sine"]

    wrappers = payload["wrapper_machine_contracts"]
    assert wrappers["cosine"]["raw_byte_sha256"] == (
        "0de3a2479ceb44dc4eeb1eba23ab27c53407c3fd7eb2052f7fc9a7df1790dbbd"
    )
    assert wrappers["sine"]["raw_byte_sha256"] == (
        "cae7003b4b9682164685955c7aa4c877b523f3ed0a72844b3b0c1d71312fb81f"
    )
    assert wrappers["cosine"]["core_instruction"] == "FCOS"
    assert wrappers["sine"]["core_instruction"] == "FSIN"
    assert wrappers["cosine"]["range_fallback_present"] is True
    assert wrappers["sine"]["fp_environment_checks_present"] is True


def test_trig_boundary_header_preserves_f32_source_and_call_order() -> None:
    text = HEADER.read_text(encoding="utf-8")
    assert '"SHIFT.Fun007584f0TrigBoundary/1"' in text
    for token in (
        "0x00758560u",
        "0x0075858bu",
        "0x0738u",
        "0x00900b10u",
        "0x00900c40u",
        "const float source_f32 = static_cast<float>(source_qword)",
        "result.cosine_f32 = cosine_wrapper(source_f32)",
        "result.sine_f32 = sine_wrapper(source_f32)",
    ):
        assert token in text
    assert text.index("cosine_wrapper(source_f32)") < text.index("sine_wrapper(source_f32)")
    assert "std::cos" not in text
    assert "std::sin" not in text


def test_trig_boundary_feeds_existing_vector_f32_inputs() -> None:
    text = VECTOR.read_text(encoding="utf-8")
    assert "float cosine_f32 = 0.0f" in text
    assert "float sine_f32 = 0.0f" in text
    assert "static_cast<double>(input.cosine_f32)" in text
    assert "static_cast<double>(input.sine_f32)" in text


def test_trig_boundary_keeps_x87_wrappers_and_source_ownership_fail_closed() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    limits = payload["limits"]
    assert limits["x87_cosine_wrapper_formula_internalized"] is False
    assert limits["x87_sine_wrapper_formula_internalized"] is False
    assert limits["fp_environment_behavior_internalized"] is False
    assert limits["range_reduction_fallback_internalized"] is False
    assert limits["HDVehicle_source_acquisition_internalized"] is False
    assert limits["positive_qword_producer_family_complete"] is False
    assert limits["FUN_007584f0_computed_payloads_complete"] is False
    assert limits["residual_producer_promotion_bit_set"] is False
    assert limits["complete_FUN_00765c40_internalized"] is False
    assert limits["top_level_provider_removed"] is False
    assert limits["external_provider_count_after"] == 7

    frontier = FRONTIER.read_text(encoding="utf-8")
    assert '"FUN_007584f0_computed_payloads"' in frontier
