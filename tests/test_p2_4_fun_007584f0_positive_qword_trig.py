import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p2_4_fun_007584f0_positive_qword_trig.json"
HEADER = ROOT / "native_runtime/include/shift_fun_007584f0_positive_qword_trig.hpp"
PHASE748 = ROOT / "native_runtime/include/shift_fun_00713630_reference_source.hpp"
FRONTIER = ROOT / "src/physics/native_vehicle_external_provider_frontier_p2_4_current.py"


def test_positive_qword_trig_pins_exact_retail_span_and_order() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun007584f0PositiveQwordTrig/1"
    span = payload["machine_span"]
    assert span == {
        "start": "0x00758560",
        "end_exclusive": "0x0075858b",
        "size": 43,
        "raw_byte_sha256": "65d14dcffa1b71078029c5675f57374bb9c3f1a2fb46cc5ca25d55f0d765a27f",
    }
    seq = payload["retail_sequence"]
    assert seq["absolute_source_offsets"] == ["0x0738", "0x11b8"]
    assert seq["cosine_call_site"] == "0x0075856f"
    assert seq["sine_call_site"] == "0x00758580"
    assert seq["wrapper_call_order"] == ["FCOS", "FSIN"]
    assert seq["f64_to_f32_spill_before_wrappers"] is True


def test_positive_qword_trig_reuses_phase748_x87_helpers() -> None:
    header = HEADER.read_text(encoding="utf-8")
    phase748 = PHASE748.read_text(encoding="utf-8")
    assert '"SHIFT.Fun007584f0PositiveQwordTrig/1"' in header
    assert "static_cast<float>(angle_f64)" in header
    cos_pos = header.index("fun_00713630_retail_cos_f32(angle_f32)")
    sin_pos = header.index("fun_00713630_retail_sin_f32(angle_f32)")
    assert cos_pos < sin_pos
    assert "const unsigned short retail_control = 0x027fu" in phase748
    assert '"flds %1; fcos; fstps %0"' in phase748
    assert '"flds %1; fsin; fstps %0"' in phase748


def test_positive_qword_trig_pins_source_geometry_without_aliasing_load_terms() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    boundary = payload["ownership_boundary"]
    assert boundary["trig_source_is_FUN_00765c40_load_term"] is False
    assert boundary["source_writer"] == "FUN_00769640"
    assert boundary["source_writer_internalized"] is False
    assert boundary["source_acquisition_internalized"] is False

    header = HEADER.read_text(encoding="utf-8")
    assert "0x0738u" in header
    assert "0x0a80u" in header
    assert "fun_007584f0_trig_source_offset(1u) == 0x11b8u" in header


def test_positive_qword_trig_keeps_family_promotion_fail_closed() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    limits = payload["limits"]
    assert limits["positive_qword_producer_family_complete"] is False
    assert limits["FUN_007584f0_computed_payloads_complete"] is False
    assert limits["residual_producer_promotion_bit_set"] is False
    assert limits["complete_FUN_00765c40_internalized"] is False
    assert limits["top_level_provider_removed"] is False
    assert limits["external_provider_count_after"] == 7

    frontier = FRONTIER.read_text(encoding="utf-8")
    assert '"FUN_007584f0_computed_payloads"' in frontier
