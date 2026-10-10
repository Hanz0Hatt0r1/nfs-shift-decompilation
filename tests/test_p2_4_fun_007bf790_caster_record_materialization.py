import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p2_4_fun_007bf790_caster_record_materialization.json"
HEADER = ROOT / "native_runtime/include/shift_fun_007bf790_caster_record_materialization.hpp"
CPP_TEST = ROOT / "native_runtime/tests/fun_007bf790_caster_record_materialization_check.cpp"
CMAKE = ROOT / "native_runtime/cmake/p2_4_fun_00765c40.cmake"
VEHICLE_RUNTIME = ROOT / "src/physics/vehicle_physics_runtime.py"
FRONTIER = ROOT / "src/physics/native_vehicle_external_provider_frontier_p2_4_current.py"


def test_caster_record_materialization_pins_exact_machine_spans() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun007bf790CasterRecordMaterialization/1"
    spans = payload["machine_spans"]
    assert spans["selected_caster_calls"] == {
        "start": "0x007bf983",
        "end_exclusive": "0x007bf9d3",
        "size": 80,
        "raw_byte_sha256": "12049fc9876432475c2ee2b34705372173dd2e6aec68842a42141ef3a30ea258",
    }
    assert spans["record_materializer"] == {
        "start": "0x007c5a20",
        "end_exclusive": "0x007c5aba",
        "size": 154,
        "raw_byte_sha256": "cf994c54d1a693fd2a1091fa553cc0da632082e25e3ba549143b9bf8443963f0",
    }
    assert spans["integer_conversion_boundary"] == "0x00901310"


def test_caster_record_materialization_uses_source_backed_caster_fields() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    fields = payload["source_fields"]
    assert fields["LeftCasterRange"] == "VehicleLoadData+0x1e8 vec3 f64"
    assert fields["LeftCasterSetting"] == "VehicleLoadData+0x3d8 f64"
    assert fields["RightCasterRange"] == "VehicleLoadData+0x200 vec3 f64"
    assert fields["RightCasterSetting"] == "VehicleLoadData+0x3e0 f64"
    assert fields["semantic_names_source_backed"] is True

    runtime = VEHICLE_RUNTIME.read_text(encoding="utf-8")
    for token in (
        'PropertyEvidence("LeftCasterRange", 0x1E8',
        'PropertyEvidence("LeftCasterSetting", 0x3D8',
        'PropertyEvidence("RightCasterRange", 0x200',
        'PropertyEvidence("RightCasterSetting", 0x3E0',
    ):
        assert token in runtime


def test_caster_record_materializer_preserves_boundary_and_zero_range_semantics() -> None:
    text = HEADER.read_text(encoding="utf-8")
    for token in (
        '"SHIFT.Fun007bf790CasterRecordMaterialization/1"',
        "0x007bf983u",
        "0x007bf9d3u",
        "0x007c5a20u",
        "0x007c5abau",
        "0x00901310u",
        "0x01e8u",
        "0x03d8u",
        "0x0200u",
        "0x03e0u",
        "0x1188u",
        "0x11d8u",
        "input.prior_count",
        "input.range[1] * input.range[1]",
        "input.range[0] * input.range[0]",
        "input.range[2] * input.range[2]",
        "convert_to_integer(input.range[2])",
        "convert_to_integer(input.setting)",
        "requested >= result.count",
        "kFun007bf790CasterDegreesToRadians",
        "fun_007bf790_caster_record_to_trig_writer_input",
    ):
        assert token in text
    assert "std::round" not in text
    assert "std::lround" not in text


def test_caster_record_materialization_is_compiled_and_keeps_frontier_fail_closed() -> None:
    cmake = CMAKE.read_text(encoding="utf-8")
    assert "shift_runtime_fun_007bf790_caster_record_materialization_check" in cmake
    assert "fun_007bf790_caster_record_materialization_check.cpp" in cmake

    cpp = CPP_TEST.read_text(encoding="utf-8")
    assert "conversion_inputs" in cpp
    assert "FUN_007bf790 conversion call order drift" in cpp
    assert "FUN_007bf790 caster record to FUN_00769640 handoff drift" in cpp

    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    limits = payload["limits"]
    assert limits["FUN_00901310_integer_conversion_internalized"] is False
    assert limits["FUN_00901310_rounding_semantics_promoted"] is False
    assert limits["caster_config_source_acquisition_internalized"] is False
    assert limits["positive_qword_producer_family_complete"] is False
    assert limits["FUN_007584f0_computed_payloads_complete"] is False
    assert limits["residual_producer_promotion_bit_set"] is False
    assert limits["complete_FUN_00765c40_internalized"] is False
    assert limits["top_level_provider_removed"] is False
    assert limits["external_provider_count_after"] == 7

    frontier = FRONTIER.read_text(encoding="utf-8")
    assert '"FUN_007584f0_computed_payloads"' in frontier
