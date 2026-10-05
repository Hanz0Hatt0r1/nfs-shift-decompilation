import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "src" / "runtime" / "bmw_offset33b_runtime_selector.py"
PROOF = ROOT / "evidence" / "bmw_offset33b_selector_complete_numeric.json"
SPEC = importlib.util.spec_from_file_location("bmw_offset33b_runtime_selector", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _proof():
    return json.loads(PROOF.read_text(encoding="utf-8"))


def test_binds_normal_difficulty_one_to_exact_proven_matrix():
    report = MODULE.bind_selector_file(
        PROOF,
        player_difficulty=1,
        use_drift_cgheight_scale=False,
    )
    assert report["format"] == "SHIFT.BMWOffset33bRuntimeSelectorBinding/1"
    assert report["ready"] is True
    assert report["selector"] == {
        "player_difficulty": 1,
        "use_drift_cgheight_scale": False,
        "cgheight_scale": 0.6,
    }
    assert report["BODY0_to_outer_vehicle_root_translation"] == pytest.approx(
        [0.0, -0.004956085581085581, -0.01147086247086247]
    )
    assert report["BODY0_to_outer_vehicle_root_row_vector_matrix"][3] == pytest.approx(
        [0.0, -0.004956085581085581, -0.01147086247086247, 1.0]
    )
    assert report["handoff"]["race_mode_selector_bound_to_native_bootstrap"] is True
    assert report["handoff"]["BMW_numeric_offset33b_ready_for_bound_session"] is True
    assert report["handoff"]["BODY0_to_outer_vehicle_root_numeric_matrix_ready_for_bound_session"] is True
    assert report["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert report["handoff"]["vehicle_world_transform_ready"] is False


def test_binds_all_six_admitted_selectors_without_assuming_default():
    proof = _proof()
    translations = set()
    for drift in (False, True):
        for difficulty in (0, 1, 2):
            report = MODULE.bind_selector_family(
                proof,
                player_difficulty=difficulty,
                use_drift_cgheight_scale=drift,
            )
            translations.add(
                tuple(report["BODY0_to_outer_vehicle_root_translation"])
            )
            assert report["scope"]["selector_default_assumed"] is False
    assert len(translations) == 3


def test_rejects_difficulty_three():
    with pytest.raises(MODULE.SelectorBindingError, match="one of 0, 1, 2"):
        MODULE.bind_selector_family(
            _proof(),
            player_difficulty=3,
            use_drift_cgheight_scale=False,
        )


def test_rejects_duplicate_selector_row():
    proof = _proof()
    proof["selector_family"][1]["player_difficulty"] = 0
    with pytest.raises(MODULE.SelectorBindingError, match="duplicate selector row"):
        MODULE.bind_selector_family(
            proof,
            player_difficulty=0,
            use_drift_cgheight_scale=False,
        )


def test_rejects_matrix_translation_drift():
    proof = _proof()
    proof["selector_family"][0]["BODY0_to_outer_vehicle_root_row_vector_matrix"][3][1] += 1.0
    with pytest.raises(MODULE.SelectorBindingError, match="matrix/translation mismatch"):
        MODULE.bind_selector_family(
            proof,
            player_difficulty=0,
            use_drift_cgheight_scale=False,
        )


def test_rejects_upstream_outer_vehicle_vhf_preclaim():
    proof = _proof()
    proof["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] = True
    with pytest.raises(MODULE.SelectorBindingError, match="preclaims outer Vehicle->VHF"):
        MODULE.bind_selector_family(
            proof,
            player_difficulty=1,
            use_drift_cgheight_scale=False,
        )
