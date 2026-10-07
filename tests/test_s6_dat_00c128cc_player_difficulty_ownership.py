from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/dat_00c128cc_player_difficulty_ownership.json"
SELECTED = ROOT / "evidence/bmw_offset33b_native_silverstone_session.json"
SELECTOR_H = ROOT / "native_runtime/include/shift_race_mode_player_difficulty.hpp"
MATERIALIZED_H = ROOT / "native_runtime/src/materialized_selected_session_race_mode.hpp"
SESSION_H = ROOT / "native_runtime/include/shift_native_vehicle_provider_session.hpp"
SESSION_CPP = ROOT / "native_runtime/src/native_vehicle_provider_session.cpp"
PROJECTION_H = ROOT / "native_runtime/include/shift_fun_007682c0_projection_state.hpp"


def test_pc_owner_chain_is_hash_locked_and_semantically_exact() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.DAT00c128ccPlayerDifficultyOwnership/1"
    assert payload["ready"] is True
    assert payload["platform_authority"] == "PC retail primary"
    assert payload["retail_program"]["pe_md5"] == "705af8b420e5eb1e3834ac43d5533c6b"
    semantic = payload["semantic_identity"]
    assert semantic["global"] == "DAT_00c128cc"
    assert semantic["race_mode_field"] == "RaceModeInfo+0x6c"
    assert semantic["reflection_name"] == "Player Difficulty (0-2)"
    assert semantic["valid_domain"] == [0, 1, 2]
    chain = payload["pc_owner_chain"]
    assert chain["race_mode_builder"]["function_sha256"] == (
        "4a0aaf95eb0b63161f35042c7164fd3b6c62ffce2c793671eb52cd9c252ccffb"
    )
    assert chain["change_race_mode_consumer"]["function_sha256"] == (
        "0fdfd115ce435f07172048099c7c8ae063842de2dcad60bfb06ca40cbba49fd4"
    )
    assert chain["global_snapshot_publisher"]["function_sha256"] == (
        "47bbffc6f5d332609171baba59e0c8f5fc44a1bff680c2ba22247110bdd72ee8"
    )


def test_selected_session_reuses_existing_policy_without_retail_inference() -> None:
    ownership = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    selected = json.loads(SELECTED.read_text(encoding="utf-8"))
    assert selected["format"] == "SHIFT.BMWOffset33bNativeSessionSelection/1"
    assert selected["selector"]["player_difficulty"] == 1
    assert selected["selector"]["source"] == "explicit-native-vertical-slice-policy"
    assert selected["selector"]["retail_live_session_selector_inferred"] is False
    assert ownership["selected_native_session"]["player_difficulty"] == 1
    assert ownership["selected_native_session"]["retail_live_session_selector_inferred"] is False
    scope = ownership["scope"]
    assert scope["DAT_00c128cc_is_immutable_process_global"] is False
    assert scope["profile_default_assumed_for_all_retail_sessions"] is False
    assert scope["selected_native_policy_claimed_as_retail_observation"] is False
    assert scope["xbox_360_recomp_substituted_for_pc_authority"] is False


def test_native_selector_is_fail_closed_and_materialized_to_difficulty_one() -> None:
    selector = SELECTOR_H.read_text(encoding="utf-8")
    materialized = MATERIALIZED_H.read_text(encoding="utf-8")
    assert "bool ready = false" in selector
    assert "player_difficulty < 0 || selector.player_difficulty > 2" in selector
    assert "RaceModeInfo Player Difficulty must be explicitly admitted" in selector
    assert "kMaterializedSelectedSessionPlayerDifficulty{true, 1}" in materialized
    assert "retail live session" in materialized.lower()


def test_top_level_late_motion_read_provider_is_removed() -> None:
    header = SESSION_H.read_text(encoding="utf-8")
    source = SESSION_CPP.read_text(encoding="utf-8")
    projection = PROJECTION_H.read_text(encoding="utf-8")
    assert "NativeVehicleMotionReadInputProvider" not in header
    assert "motion_read_input{}" not in header
    assert "RaceModePlayerDifficulty race_mode{}" in header
    assert "providers_.motion_read_input" not in source
    assert "providers_.race_mode" in source
    external = projection.split("struct Fun007682c0ExternalMachineInput", 1)[1].split("};", 1)[0]
    assert "angle_mode" not in external
    compose = projection.split("compose_fun_007682c0_machine_input", 1)[1]
    assert "const RaceModePlayerDifficulty& race_mode" in compose
    assert "input.angle_mode = race_mode.player_difficulty" in compose


def test_handoff_reduces_active_provider_count_to_seven() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    handoff = payload["native_handoff"]
    assert handoff["late_FUN_007682c0_provider_required"] is False
    assert handoff["session_selector_required"] is True
    assert handoff["active_external_provider_count_before"] == 8
    assert handoff["active_external_provider_count_after"] == 7
