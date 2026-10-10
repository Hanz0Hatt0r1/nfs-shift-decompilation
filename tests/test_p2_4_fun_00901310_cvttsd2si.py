import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p2_4_fun_00901310_cvttsd2si.json"
UPSTREAM = ROOT / "evidence/p1a_p13a_slot01_deeper_hdvehicle_root_tranche.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00901310_cvttsd2si.hpp"
CASTER = ROOT / "native_runtime/include/shift_fun_007bf790_caster_record_materialization.hpp"
CPP_TEST = ROOT / "native_runtime/tests/fun_00901310_cvttsd2si_check.cpp"
CMAKE = ROOT / "native_runtime/cmake/p2_4_fun_00765c40.cmake"
FRONTIER = ROOT / "src/physics/native_vehicle_external_provider_frontier_p2_4_current.py"


def test_fun00901310_uses_existing_machine_proof() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun00901310Cvttsd2si/1"
    machine = payload["machine_contract"]
    assert machine["entry"] == "0x00901310"
    assert machine["x87_spill"] == {
        "site": "0x00901322",
        "bytes": "dd1c24",
        "instruction": "FSTP qword ptr [ESP]",
    }
    assert machine["conversion"] == {
        "site": "0x00901325",
        "bytes": "f20f2c0424",
        "instruction": "CVTTSD2SI EAX,qword ptr [ESP]",
    }
    assert machine["receiver_required"] is False
    assert machine["non_stack_destination_present"] is False
    assert machine["returned_value_register"] == "EAX"

    upstream = json.loads(UPSTREAM.read_text(encoding="utf-8"))
    row = next(
        item for item in upstream["candidate_adjudication"]
        if item["function"] == "FUN_00901310"
    )
    assert row["class"] == "x87-to-int-runtime-helper"
    assert any("CVTTSD2SI" in item for item in row["evidence"])
    byte_map = {
        item["site"]: item["bytes"]
        for item in upstream["verified_byte_windows"]
    }
    assert byte_map["0x00901322"] == "dd1c24"
    assert byte_map["0x00901325"] == "f20f2c0424"


def test_fun00901310_header_models_value_semantics_without_unsafe_casts() -> None:
    text = HEADER.read_text(encoding="utf-8")
    for token in (
        '"SHIFT.Fun00901310Cvttsd2si/1"',
        "0x00901310u",
        "0x00901322u",
        "0x00901325u",
        "std::trunc(value)",
        "std::isfinite(value)",
        "kFun00901310IntegerIndefinite",
        "truncated < kInt32Min",
        "truncated > kInt32Max",
    ):
        assert token in text
    assert "std::round" not in text
    assert "std::lround" not in text


def test_caster_materializer_has_native_conversion_overload() -> None:
    text = CASTER.read_text(encoding="utf-8")
    assert '#include "shift_fun_00901310_cvttsd2si.hpp"' in text
    assert "execute_fun_00901310_cvttsd2si(value)" in text
    assert "materialize_fun_007bf790_caster_records(" in text

    cpp = CPP_TEST.read_text(encoding="utf-8")
    assert "2147483647.9" in cpp
    assert "2147483648.0" in cpp
    assert "-2147483648.9" in cpp
    assert "-2147483649.0" in cpp
    assert "quiet_NaN" in cpp
    assert "materialize_fun_007bf790_caster_records(caster_input)" in cpp


def test_fun00901310_target_is_compiled_and_frontier_stays_fail_closed() -> None:
    cmake = CMAKE.read_text(encoding="utf-8")
    assert "shift_runtime_fun_00901310_cvttsd2si_check" in cmake
    assert "fun_00901310_cvttsd2si_check.cpp" in cmake

    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    native = payload["native_contract"]
    assert native["eax_value_semantics_internalized"] is True
    assert native["caster_materializer_callback_required"] is False

    limits = payload["limits"]
    assert limits["mxcsr_exception_status_flags_internalized"] is False
    assert limits["floating_point_exception_delivery_internalized"] is False
    assert limits["caster_config_source_acquisition_internalized"] is False
    assert limits["positive_qword_producer_family_complete"] is False
    assert limits["FUN_007584f0_computed_payloads_complete"] is False
    assert limits["residual_producer_promotion_bit_set"] is False
    assert limits["complete_FUN_00765c40_internalized"] is False
    assert limits["top_level_provider_removed"] is False
    assert limits["external_provider_count_after"] == 7

    frontier = FRONTIER.read_text(encoding="utf-8")
    assert '"FUN_007584f0_computed_payloads"' in frontier
