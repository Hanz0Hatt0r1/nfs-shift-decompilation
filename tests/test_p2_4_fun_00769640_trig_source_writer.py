import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p2_4_fun_00769640_trig_source_writer.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00769640_trig_source_writer.hpp"
FRONTIER = ROOT / "src/physics/native_vehicle_external_provider_frontier_p2_4_current.py"


def test_fun_00769640_writer_pins_exact_retail_span_and_formula() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun00769640TrigSourceWriter/1"
    span = payload["machine_span"]
    assert span == {
        "start": "0x00769c05",
        "end_exclusive": "0x00769c2d",
        "size": 40,
        "raw_byte_sha256": "4ec2458e9f056d77b30baae9dbfe9a20b9e56d6069f19155d9542966709fa26d",
    }
    writer = payload["retail_writer"]
    assert writer["selected_record_indices"] == [12, 13]
    assert writer["destination_offsets"] == ["0x0738", "0x11b8"]
    assert writer["formula"] == "base_value + int32_coefficient * slope_value"
    assert writer["instruction_order"] == [
        "FILD int32_coefficient",
        "FMUL slope_qword",
        "FADD base_qword",
        "FST destination_qword",
    ]


def test_fun_00769640_writer_pins_hdvehicle_table_geometry() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    caller = payload["caller_provenance"]
    assert caller["FUN_0076b280_first_physical_stack_argument"] == "HDVehicle+0x4330"
    assert caller["FUN_0076b280_forwards_argument_to_FUN_00769640"] is True
    assert caller["FUN_00769640_table_root"] == "HDVehicle+0x4330"

    writer = payload["retail_writer"]
    assert writer["absolute_base_value_offsets"] == ["0x54b8", "0x5508"]
    assert writer["absolute_slope_value_offsets"] == ["0x54c0", "0x5510"]
    assert writer["absolute_coefficient_offsets"] == ["0x54cc", "0x551c"]

    header = HEADER.read_text(encoding="utf-8")
    for literal in ("0x4330u", "0x54b8u", "0x54c0u", "0x54ccu", "0x5508u", "0x5510u", "0x551cu"):
        assert literal in header


def test_fun_00769640_writer_internalizes_arithmetic_but_not_table_lifetime() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    native = payload["native_contract"]
    assert native["writer_formula_internalized"] is True
    assert native["record_selection_internalized"] is True
    assert native["table_layout_internalized"] is True
    assert native["destination_geometry_internalized"] is True
    assert native["x87_extended_precision_bit_parity_claimed"] is False

    ownership = payload["ownership_boundary"]
    assert ownership["hdvehicle_4330_pointer_provenance_proven"] is True
    assert ownership["table_value_acquisition_internalized"] is False
    assert ownership["table_value_lifetime_internalized"] is False
    assert ownership["FUN_00769640_complete"] is False


def test_fun_00769640_writer_keeps_p2_4_promotion_fail_closed() -> None:
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
