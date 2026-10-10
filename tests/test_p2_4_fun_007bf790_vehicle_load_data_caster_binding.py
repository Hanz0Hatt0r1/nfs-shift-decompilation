import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p2_4_fun_007bf790_vehicle_load_data_caster_binding.json"
OWNER = ROOT / "evidence/fun_007618f0_vehicle_load_data_ownership.json"
HEADER = ROOT / "native_runtime/include/shift_fun_007bf790_vehicle_load_data_caster_binding.hpp"
CPP_TEST = ROOT / "native_runtime/tests/fun_007bf790_vehicle_load_data_caster_binding_check.cpp"
CMAKE = ROOT / "native_runtime/cmake/p2_4_fun_00765c40.cmake"
CDF = ROOT / "src/physics/vehicle_cdf_runtime.py"
PHYSICS = ROOT / "src/physics/vehicle_physics_runtime.py"
FRONTIER = ROOT / "src/physics/native_vehicle_external_provider_frontier_p2_4_current.py"


def test_vehicle_load_data_caster_binding_joins_existing_owner_and_cdf_contracts() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun007bf790VehicleLoadDataCasterBinding/1"
    provenance = payload["owner_provenance"]
    assert provenance["owner"] == "HDVehicle"
    assert provenance["vehicle_load_data_pointer_offset"] == "0x66b4"
    assert provenance["allocation_size"] == "0x3848"
    assert provenance["allocation_constructor"] == "FUN_007c3170"
    assert provenance["selected_bmw_resource_path"] == (
        "vehicles\\physics\\chassis\\bmw_m3_e36.cdf"
    )
    assert provenance["selected_bmw_cdf_sha256"] == (
        "bbee83f0d2fdcbfc2bbd62ddb2a10bf6fed71bb1b4fa78f303a4730d038b970d"
    )

    owner = json.loads(OWNER.read_text(encoding="utf-8"))
    assert owner["format"] == "SHIFT.Fun007618f0VehicleLoadDataOwnership/1"
    assert owner["source_owner"]["HDVehicle_pointer_offset"] == "0x66b4"
    assert owner["source_owner"]["allocation_size"] == "0x3848"


def test_vehicle_load_data_caster_binding_pins_exact_caster_offsets() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    layout = payload["caster_layout"]
    assert layout["left_range_offsets"] == ["0x1e8", "0x1f0", "0x1f8"]
    assert layout["left_setting_offset"] == "0x3d8"
    assert layout["right_range_offsets"] == ["0x200", "0x208", "0x210"]
    assert layout["right_setting_offset"] == "0x3e0"
    assert layout["scalar_encoding"] == "little-endian IEEE-754 f64"
    assert layout["minimum_snapshot_size"] == "0x3e8"

    cdf = CDF.read_text(encoding="utf-8")
    assert '("LeftCasterRange", 0x1e8, 0x1f0, 0x1f8, 0x3d8)' in cdf
    assert '("RightCasterRange", 0x200, 0x208, 0x210, 0x3e0)' in cdf

    physics = PHYSICS.read_text(encoding="utf-8")
    assert 'PropertyEvidence("LeftCasterRange", 0x1E8' in physics
    assert 'PropertyEvidence("LeftCasterSetting", 0x3D8' in physics
    assert 'PropertyEvidence("RightCasterRange", 0x200' in physics
    assert 'PropertyEvidence("RightCasterSetting", 0x3E0' in physics


def test_vehicle_load_data_binding_uses_explicit_little_endian_reads() -> None:
    text = HEADER.read_text(encoding="utf-8")
    for token in (
        '"SHIFT.Fun007bf790VehicleLoadDataCasterBinding/1"',
        "0x66b4u",
        "0x3848u",
        "kVehicleLoadDataCasterMinimumSize",
        "view.bytes[offset + lane]",
        "lane * 8u",
        "std::memcpy(&value, &bits",
        "kFun007bf790LeftCasterRangeOffset + 0x00u",
        "kFun007bf790LeftCasterRangeOffset + 0x08u",
        "kFun007bf790LeftCasterRangeOffset + 0x10u",
        "kFun007bf790RightCasterRangeOffset + 0x00u",
        "kFun007bf790RightCasterRangeOffset + 0x08u",
        "kFun007bf790RightCasterRangeOffset + 0x10u",
        "kFun007bf790LeftCasterSettingOffset",
        "kFun007bf790RightCasterSettingOffset",
        "materialize_fun_007bf790_caster_records(",
    ):
        assert token in text
    assert "reinterpret_cast<const double" not in text


def test_vehicle_load_data_binding_is_compiled_and_fail_closed() -> None:
    cmake = CMAKE.read_text(encoding="utf-8")
    assert "shift_runtime_fun_007bf790_vehicle_load_data_caster_binding_check" in cmake
    assert "fun_007bf790_vehicle_load_data_caster_binding_check.cpp" in cmake

    cpp = CPP_TEST.read_text(encoding="utf-8")
    assert "VehicleLoadData short caster snapshot failed open" in cpp
    assert "VehicleLoadData null caster snapshot failed open" in cpp
    assert "VehicleLoadData non-finite caster source failed open" in cpp
    assert "materialize_fun_007bf790_caster_records_from_vehicle_load_data" in cpp

    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    native = payload["native_contract"]
    assert native["vehicle_load_data_byte_snapshot_binding_internalized"] is True
    assert native["opaque_caster_scalar_inputs_required"] is False

    limits = payload["limits"]
    assert limits["HDVehicle_pointer_dereference_internalized"] is False
    assert limits["VehicleLoadData_snapshot_lifetime_internalized"] is False
    assert limits["retail_CDF_binary_decode_internalized_in_native_runtime"] is False
    assert limits["selected_BMW_caster_numeric_values_promoted"] is False
    assert limits["positive_qword_producer_family_complete"] is False
    assert limits["FUN_007584f0_computed_payloads_complete"] is False
    assert limits["residual_producer_promotion_bit_set"] is False
    assert limits["complete_FUN_00765c40_internalized"] is False
    assert limits["top_level_provider_removed"] is False
    assert limits["external_provider_count_after"] == 7

    frontier = FRONTIER.read_text(encoding="utf-8")
    assert '"FUN_007584f0_computed_payloads"' in frontier
