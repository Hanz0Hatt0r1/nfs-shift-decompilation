from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/selected_session_angle_mode.json"
UPSTREAM = ROOT / "evidence/bmw_offset33b_native_silverstone_session.json"
HEADER = ROOT / "native_runtime/include/shift_selected_session_angle_mode.hpp"
PROJECTION = ROOT / "native_runtime/include/shift_fun_007682c0_projection_state.hpp"


def test_selected_session_angle_mode_joins_existing_native_policy_to_pc_semantics() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    upstream = json.loads(UPSTREAM.read_text(encoding="utf-8"))

    assert payload["format"] == "SHIFT.SelectedSessionAngleMode/1"
    assert payload["ready"] is True
    assert payload["platform_authority"] == (
        "PC retail semantics + explicit native session policy"
    )
    selected = payload["selected_session"]
    assert selected["upstream_contract"] == "SHIFT.BMWOffset33bNativeSessionSelection/1"
    assert selected["session_target"] == upstream["session_target"] == "Silverstone+BMW_M3_E36"
    assert selected["player_difficulty"] == upstream["selector"]["player_difficulty"] == 1
    assert selected["validated_against_retail_selector_domain"] is True
    assert selected["retail_live_session_selector_inferred"] is False


def test_pc_race_mode_copy_and_fun_007682c0_compare_are_hash_locked() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    retail = payload["retail_semantics"]
    effect = payload["fun_007682c0"]

    assert retail["profile_source"] == "profile/options+0x10f4"
    assert retail["race_mode_field"] == "RaceModeInfo+0x6c"
    assert retail["global_field"] == "DAT_00c128cc"
    assert retail["selected_offset_mapping"] == "RaceModeInfo+0x6c -> DAT_00c128cc"
    assert retail["staging_copy_machine_span"]["raw_byte_sha256"] == (
        "c95afe1b680a83e8f7433b123c8492e27d0f86afdeab8ec6d1a40bd8ef6e9e0d"
    )
    assert effect["mode_compare_machine_span"]["raw_byte_sha256"] == (
        "07b08ea3ea6f1db6cfa6012c097fcab3e88ddab1c68675b1151e87329f642c0b"
    )
    assert effect["valid_retail_domain"] == [0, 1, 2]
    assert effect["selected_native_value"] == 1
    assert effect["selected_branch"] == "DAT_00c128cc <= 1"


def test_late_external_input_no_longer_accepts_angle_mode() -> None:
    header = HEADER.read_text(encoding="utf-8")
    projection = PROJECTION.read_text(encoding="utf-8")
    external_struct = projection.split(
        "struct Fun007682c0ExternalMachineInput", 1
    )[1].split("};", 1)[0]

    assert "kSelectedSessionPlayerDifficulty = 1" in header
    assert "retail live-session default" in header
    assert "angle_mode" not in external_struct
    assert "bool caller_gate_open" in external_struct
    compose = projection.split("compose_fun_007682c0_machine_input", 1)[1]
    assert "input.angle_mode = selected_session_fun_007682c0_angle_mode()" in compose


def test_scope_keeps_retail_live_value_and_e0_gate_fail_closed() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    scope = payload["scope"]
    assert scope["retail_live_session_difficulty_observed"] is False
    assert scope["retail_default_difficulty_inferred"] is False
    assert scope["native_vertical_slice_policy_reused"] is True
    assert scope["retail_selector_domain_and_storage_semantics_proven"] is True
    assert scope["HDVehicle_0xe0_caller_gate_internalized"] is False
    assert scope["provider_count_reduced"] is False
    assert scope["active_external_provider_count"] == 8
    assert scope["xbox_360_recomp_substituted_for_pc_authority"] is False
    assert scope["runtime_capture_required"] is False
