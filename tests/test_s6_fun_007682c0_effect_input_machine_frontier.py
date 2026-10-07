from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTIER = ROOT / "evidence/fun_007682c0_effect_input_machine_frontier.json"
HEADER = ROOT / "native_runtime/include/shift_fun_007682c0_machine_magnitude.hpp"
SOURCE = ROOT / "native_runtime/src/fun_007682c0_machine_magnitude.cpp"


def test_pc_source_effect_inputs_are_finite_and_explicit() -> None:
    report = json.loads(FRONTIER.read_text(encoding="utf-8"))

    assert report["format"] == "SHIFT.Fun007682c0EffectInputMachineFrontier/1"
    assert report["ready"] is True
    assert report["platform_authority"] == "PC retail primary"
    assert report["source"]["sha256"] == (
        "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    )
    assert report["source"]["retail_executable_md5"] == "705af8b420e5eb1e3834ac43d5533c6b"
    assert report["source"]["xbox_360_recomp_used_as_primary_authority"] is False

    caller = report["caller_input_provenance"]
    assert caller["chassis_BODY_pointer"] == "HDVehicle+0x33a0"
    assert caller["load_factor"]["numerator_f64_fields"] == [
        "HDVehicle+0xb38",
        "HDVehicle+0x15b8",
        "HDVehicle+0x2038",
        "HDVehicle+0x2ab8",
    ]
    assert caller["load_factor"]["denominator"] == "BODY0+0x120 * 9.81"
    assert caller["load_factor"]["FUN_007682c0_param_2"] is True
    assert caller["steering_or_control_scalar"]["source"] == "HDVehicle+0x4068"
    assert caller["steering_or_control_scalar"]["FUN_007682c0_param_1"] is True
    assert caller["steering_or_control_scalar"]["physical_name_claimed"] is False

    effect = report["fun_007682c0_inputs"]
    assert effect["BODY0_motion_f64"] == ["+0x78", "+0x80", "+0x88"]
    assert effect["geometry_helper"] == "FUN_0075ada0"
    assert effect["response_helper"] == "FUN_007595d0"
    assert effect["global_angle_mode"] == "DAT_00c128cc"

    geometry = report["fun_0075ada0_inputs"]
    assert geometry["BODY0_planar_motion_f64_then_f32"] == ["+0x78", "+0x88"]
    assert geometry["vehicle_projection_fields_f32"] == [
        "HDVehicle+0x4084",
        "HDVehicle+0x408c",
    ]

    response = report["fun_007595d0_inputs"]
    assert response["BODY0_field_f64_then_f32"] == "+0x20"
    assert response["BODY0_scale_f64_then_f32"] == "+0x120"
    assert response["vehicle_scale_f32"] == "HDVehicle+0x4054"
    assert response["physical_field_names_claimed"] is False


def test_machine_frontier_freezes_x87_and_f32_checkpoints() -> None:
    report = json.loads(FRONTIER.read_text(encoding="utf-8"))
    machine = report["machine_checkpoints"]

    assert machine["FUN_007682c0"]["entry"] == "0x007682c0"
    assert machine["FUN_007682c0"]["mnemonic_sha256"] == (
        "f60c733cc0d0b3c755b3104953d1dc1d623d15f33978a6cbe50de7947b7f5d34"
    )
    assert machine["FUN_007682c0"]["sqrt_call"] == "0x00768300 -> 0x00900d30 (__CIsqrt)"
    assert machine["FUN_007682c0"]["speed_f32_store"] == "0x00768305"
    assert machine["FUN_007682c0"]["speed_factor_f32_store"] == "0x0076832c"
    assert machine["FUN_0075ada0"]["BODY0_x_f64_to_f32_store"] == "0x0075adb5"
    assert machine["FUN_0075ada0"]["BODY0_z_f64_to_f32_store"] == "0x0075adbb"
    assert machine["FUN_0075ada0"]["squared_planar_magnitude_f32_store"] == "0x0075add7"
    assert machine["FUN_0075ada0"]["planar_speed_f32_store"] == "0x0075ade2"
    assert machine["FUN_007595d0"]["response_machine_parity_complete"] is False
    assert machine["__CIsqrt"]["positive_path_fsqrt"] == "0x00900d6c"
    assert machine["__CIsqrt"]["host_std_sqrt_substitution_required"] is False


def test_native_magnitude_path_uses_x87_not_host_sqrt() -> None:
    report = json.loads(FRONTIER.read_text(encoding="utf-8"))
    header = HEADER.read_text(encoding="utf-8")
    source = SOURCE.read_text(encoding="utf-8")

    assert report["native_consumption"]["contract"] == "SHIFT.Fun007682c0MachineMagnitude/1"
    assert report["native_consumption"]["retail_x87_control_word"] == "0x027f"
    assert report["native_consumption"]["host_std_sqrt_used_for_retail_path"] is False

    assert "fun_007682c0_pc_x87_speed3d_f32" in header
    assert "fun_0075ada0_pc_x87_planar_speed_f32" in header
    assert "fun_007682c0_pc_machine_magnitude" in header
    assert "kRetailX87ControlWord = 0x027fu" in source
    assert '"fsqrt\\n\\t"' in source
    assert '"fstps %[sq]\\n\\t"' in source
    assert "std::sqrt" not in source
    assert "sqrt(" not in source


def test_frontier_advances_only_magnitude_not_response_or_effect_provider() -> None:
    report = json.loads(FRONTIER.read_text(encoding="utf-8"))
    handoff = report["handoff"]
    limits = report["limits"]

    assert handoff["FUN_007682c0_source_input_provenance_ready"] is True
    assert handoff["FUN_007682c0_machine_magnitude_ready"] is True
    assert handoff["FUN_0075ada0_machine_planar_magnitude_ready"] is True
    assert handoff["FUN_007595d0_source_inputs_ready"] is True
    assert handoff["FUN_007595d0_machine_response_parity_ready"] is False
    assert handoff["FUN_007682c0_effect_production_ready"] is False
    assert "FUN_007595d0" in handoff["next_exact_action"]

    assert limits["host_std_sqrt_may_replace_pc_x87_path"] is False
    assert limits["FUN_007595d0_source_formula_alone_closes_machine_parity"] is False
    assert limits["FUN_007682c0_effect_provider_removed"] is False
    assert limits["xbox_360_recomp_may_replace_pc_machine_evidence"] is False
