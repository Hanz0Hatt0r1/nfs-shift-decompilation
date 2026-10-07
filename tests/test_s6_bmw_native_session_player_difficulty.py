from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/bmw_native_session_player_difficulty.json"
SESSION = ROOT / "evidence/bmw_offset33b_native_silverstone_session.json"
HEADER = ROOT / "native_runtime/include/shift_bmw_native_session_player_difficulty.hpp"
PROJECTION = ROOT / "native_runtime/include/shift_fun_007682c0_projection_state.hpp"
PROVIDER_HEADER = ROOT / "native_runtime/include/shift_native_vehicle_provider_session.hpp"
PROVIDER_SOURCE = ROOT / "native_runtime/src/native_vehicle_provider_session.cpp"


def test_selected_native_policy_matches_existing_session_selection() -> None:
    proof = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    selected = json.loads(SESSION.read_text(encoding="utf-8"))

    assert proof["format"] == "SHIFT.BMWNativeSessionPlayerDifficulty/1"
    assert proof["ready"] is True
    assert proof["session_target"] == selected["session_target"] == "Silverstone+BMW_M3_E36"
    assert proof["selected_player_difficulty"] == selected["selector"]["player_difficulty"] == 1
    assert selected["selector"]["source"] == "explicit-native-vertical-slice-policy"
    assert selected["selector"]["validated_against_retail_selector_domain"] is True
    assert selected["selector"]["retail_live_session_selector_inferred"] is False


def test_retail_mapping_is_source_backed_without_using_initialization_default() -> None:
    proof = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    mapping = proof["retail_mapping"]
    provenance = proof["retail_profile_provenance"]
    scope = proof["scope"]

    assert mapping["source_field"] == "RaceModeInfo+0x6c"
    assert mapping["destination_global"] == "DAT_00c128cc"
    assert mapping["consumer"] == "FUN_007682c0"
    assert provenance["valid_values"] == [0, 1, 2]
    assert provenance["profile_offset_hex"] == "0x10f4"
    assert provenance["initialization_value"] == 1
    assert provenance["mutable_after_initialization"] is True
    assert provenance["mutation_function"] == "FUN_00d3b190"
    assert provenance["initialization_value_used_as_selected_session_proof"] is False
    assert scope["native_policy_is_retail_live_session_observation"] is False
    assert scope["retail_default_inferred"] is False


def test_runtime_has_no_selected_session_late_angle_provider() -> None:
    helper = HEADER.read_text(encoding="utf-8")
    projection = PROJECTION.read_text(encoding="utf-8")
    provider_header = PROVIDER_HEADER.read_text(encoding="utf-8")
    provider_source = PROVIDER_SOURCE.read_text(encoding="utf-8")

    assert "kBmwNativeSilverstonePlayerDifficulty = 1" in helper
    assert "selected_bmw_native_session_player_difficulty()" in helper
    assert "selected_bmw_native_session_player_difficulty()" in projection
    assert "input.angle_mode = selected_bmw_native_session_player_difficulty()" in projection
    assert "Fun007682c0ExternalMachineInput" not in projection
    assert "NativeVehicleMotionReadInputProvider" not in provider_header
    assert "motion_read_input{}" not in provider_header
    assert "providers_.motion_read_input" not in provider_source
