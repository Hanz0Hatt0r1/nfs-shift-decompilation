from __future__ import annotations

import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "bind_bmw_offset33b_native_session_selector.py"
SPEC = importlib.util.spec_from_file_location("bmw_offset33b_native_selector", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

FAMILY_PATH = ROOT / "evidence" / "bmw_offset33b_selector_complete_numeric.json"
SILVERSTONE_PATH = ROOT / "evidence" / "bmw_offset33b_native_silverstone_session.json"


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_committed_silverstone_selection_rebuilds_exactly():
    report = MODULE.bind_native_session_selector(
        _load(FAMILY_PATH),
        physics_mode="normal",
        player_difficulty=1,
    )
    assert report == _load(SILVERSTONE_PATH)
    assert report["handoff"]["BMW_numeric_offset33b_ready"] is True
    assert report["handoff"]["BODY0_to_outer_vehicle_root_numeric_matrix_ready"] is True
    assert report["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert report["handoff"]["vehicle_world_transform_ready"] is False
    assert report["scope"]["native_session_policy_is_retail_session_observation"] is False
    assert report["scope"]["retail_drift_mode_default_inferred"] is False


def test_all_six_retail_domain_selectors_resolve_uniquely():
    family = _load(FAMILY_PATH)
    translations = set()
    for mode in MODULE.VALID_MODES:
        for difficulty in MODULE.VALID_DIFFICULTIES:
            report = MODULE.bind_native_session_selector(
                family,
                physics_mode=mode,
                player_difficulty=difficulty,
                session_target="test",
            )
            selected = report["selected_numeric"]
            assert selected["use_drift_cgheight_scale"] is (mode == "drift")
            assert selected["player_difficulty"] == difficulty
            translations.add(tuple(selected["BODY0_to_outer_vehicle_root_translation_decimal"]))
    assert len(translations) == 3


def test_invalid_selector_values_fail_closed():
    family = _load(FAMILY_PATH)
    with pytest.raises(ValueError, match="physics_mode"):
        MODULE.bind_native_session_selector(
            family,
            physics_mode="unknown",
            player_difficulty=1,
        )
    with pytest.raises(ValueError, match="player_difficulty"):
        MODULE.bind_native_session_selector(
            family,
            physics_mode="normal",
            player_difficulty=3,
        )
    with pytest.raises(ValueError, match="player_difficulty"):
        MODULE.bind_native_session_selector(
            family,
            physics_mode="normal",
            player_difficulty=True,
        )


def test_family_cannot_preclaim_singular_numeric_gate():
    family = _load(FAMILY_PATH)
    family["handoff"]["BMW_numeric_offset33b_ready"] = True
    with pytest.raises(ValueError, match="preclaims BMW_numeric_offset33b_ready"):
        MODULE.bind_native_session_selector(
            family,
            physics_mode="normal",
            player_difficulty=1,
        )


def test_duplicate_selector_row_fails_closed():
    family = _load(FAMILY_PATH)
    family["selector_family"][5] = deepcopy(family["selector_family"][4])
    with pytest.raises(ValueError, match="duplicate selector-family row"):
        MODULE.bind_native_session_selector(
            family,
            physics_mode="normal",
            player_difficulty=1,
        )


def test_translation_must_remain_negative_offset33b():
    family = _load(FAMILY_PATH)
    family["selector_family"][1]["BODY0_to_outer_vehicle_root_translation"][1] += 0.1
    with pytest.raises(ValueError, match="translation is not -offset33b"):
        MODULE.bind_native_session_selector(
            family,
            physics_mode="normal",
            player_difficulty=1,
        )


def test_matrix_translation_must_match_selected_translation():
    family = _load(FAMILY_PATH)
    family["selector_family"][1]["BODY0_to_outer_vehicle_root_row_vector_matrix"][3][1] += 0.1
    with pytest.raises(ValueError, match="matrix translation disagreement"):
        MODULE.bind_native_session_selector(
            family,
            physics_mode="normal",
            player_difficulty=1,
        )


def test_cli_surface_requires_both_selector_dimensions(tmp_path):
    out = tmp_path / "selection.json"
    assert MODULE.main([
        str(FAMILY_PATH),
        "--physics-mode", "drift",
        "--player-difficulty", "2",
        "--session-target", "fixture",
        "--json-out", str(out),
    ]) == 0
    report = _load(out)
    assert report["selector"]["physics_mode"] == "drift"
    assert report["selector"]["player_difficulty"] == 2
    assert report["session_target"] == "fixture"
