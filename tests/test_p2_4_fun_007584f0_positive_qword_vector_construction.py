import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p2_4_fun_007584f0_positive_qword_vector_construction.json"
HEADER = ROOT / "native_runtime/include/shift_fun_007584f0_positive_qword_vector_construction.hpp"
REDUCTION = ROOT / "native_runtime/include/shift_fun_007584f0_positive_qword_reduction.hpp"
FRONTIER = ROOT / "src/physics/native_vehicle_external_provider_frontier_p2_4_current.py"


def test_vector_construction_pins_caller_and_helper_machine_spans() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun007584f0PositiveQwordVectorConstruction/1"
    spans = payload["machine_spans"]
    assert spans["axis_transform_setup"] == {
        "start": "0x0075850c",
        "end_exclusive": "0x0075853c",
        "size": 48,
        "raw_byte_sha256": "2f8a8303545bad3b90e57c80dcac011a78d6370dc0cc1e044e44d114b2842925",
    }
    assert spans["loop_vector_construction"]["start"] == "0x0075858b"
    assert spans["loop_vector_construction"]["end_exclusive"] == "0x007586f9"
    assert spans["loop_vector_construction"]["size"] == 366
    assert spans["loop_vector_construction"]["raw_byte_sha256"] == (
        "e261e763d2d493ad9f3f59242b4a7ee5d90a066ff5b59fafba8aad56a06dc270"
    )

    helpers = payload["helper_machine_contracts"]
    assert helpers["vec3_add"]["entry"] == "0x00753590"
    assert helpers["vec3_scale"]["entry"] == "0x007535f0"
    assert helpers["vec3_cross"]["entry"] == "0x00753650"
    assert helpers["body_frame_transform"]["entry"] == "0x007aefb0"
    assert helpers["body_frame_transform"]["component_accumulation_order"] == [1, 0, 2]


def test_vector_construction_pins_positional_source_layout() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    layout = payload["source_layout"]
    assert layout["selected_body_pointer"] == "HDVehicle+0x33a0"
    assert layout["selected_body_transform_base"] == "+0x0d4"
    assert layout["loop_stride"] == "0x0a80"
    assert layout["loop_indices"] == [0, 1]
    assert layout["vector_8a0"] == "+0x8a0 vec3 f64"
    assert layout["vector_888"] == "+0x888 vec3 f64"
    assert layout["vector_8d0"] == "+0x8d0 vec3 f64"
    assert layout["load_b38"] == "+0xb38 f64"
    assert layout["index_zero_factor_global"] == "0x00aa9afc f32"
    assert layout["scale_global"] == "0x00aadd68 f64"
    assert layout["add_global"] == "0x00b09138 f64"
    assert layout["cross_scale_global"] == "0x00b03df8 f64"


def test_vector_construction_header_preserves_recovered_arithmetic() -> None:
    text = HEADER.read_text(encoding="utf-8")
    assert '"SHIFT.Fun007584f0PositiveQwordVectorConstruction/1"' in text
    for token in (
        "0x0075850cu",
        "0x0075853cu",
        "0x0075858bu",
        "0x007586f9u",
        "0x33a0u",
        "0x08a0u",
        "0x0888u",
        "0x08d0u",
        "0x0818u",
        "0x07f0u",
        "0x07e8u",
        "0x0b38u",
        "0x0900u",
        "0x00aa9afcu",
        "0x00aadd68u",
        "0x00b09138u",
        "0x00b03df8u",
        "fun_007584f0_transform_vec3",
        "fun_007584f0_cross_vec3",
        "input.scalar_818 + input.add_b09138",
        "input.loop_index == 0u",
        "input.vector_8d0",
        "input.cross_scale_b03df8",
    ):
        assert token in text
    assert "std::cos" not in text
    assert "std::sin" not in text
    assert "cosine_f32" in text
    assert "sine_f32" in text


def test_vector_construction_remains_fail_closed_on_source_acquisition_and_trig() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    limits = payload["limits"]
    assert limits["HDVehicle_and_BODY_source_acquisition_internalized"] is False
    assert limits["x87_cosine_sine_wrappers_internalized"] is False
    assert limits["source_field_owner_lifetimes_proven"] is False
    assert limits["positive_qword_producer_family_complete"] is False
    assert limits["FUN_007584f0_computed_payloads_complete"] is False
    assert limits["residual_producer_promotion_bit_set"] is False
    assert limits["complete_FUN_00765c40_internalized"] is False
    assert limits["top_level_provider_removed"] is False
    assert limits["external_provider_count_after"] == 7

    frontier = FRONTIER.read_text(encoding="utf-8")
    assert '"FUN_007584f0_computed_payloads"' in frontier
    assert '"SHIFT.Fun007584f0PositiveQwordReduction/1"' in REDUCTION.read_text(encoding="utf-8")
