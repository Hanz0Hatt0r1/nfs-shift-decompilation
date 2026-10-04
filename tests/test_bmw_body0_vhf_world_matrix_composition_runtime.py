from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from bmw_body0_vhf_world_matrix_composition_runtime import (
    ProvenBody0BindFrame,
    ProvenVhfBindFrame,
    compose,
    contract,
)

ROOT = Path(__file__).resolve().parents[1]
PROCESS1_TOOL = ROOT / "tools/ghidra/build_bmw_body0_vhf_bind_frame_frontier.py"


def _process1_module():
    spec = importlib.util.spec_from_file_location("body0_vhf_process1", PROCESS1_TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _fixture() -> tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
    vhf = (
        0.0, 2.0, 0.0, 0.0,
        -1.0, 0.0, 0.0, 0.0,
        0.0, 0.0, 0.5, 0.0,
        5.0, 6.0, 7.0, 1.0,
    )
    body_bind = (
        1.0, 0.0, 0.0, 0.0,
        0.0, 2.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        1.0, 2.0, 3.0, 1.0,
    )
    origin = (10.0, 20.0, 30.0)
    basis = (
        1.0, 0.0, 0.0,
        0.0, 1.0, 0.0,
        0.0, 0.0, 1.0,
    )
    return vhf, body_bind, origin, basis


def test_phase704_matches_merged_process1_composition_order() -> None:
    process1 = _process1_module()
    vhf, body_bind, origin, basis = _fixture()
    result = compose(
        body_index=0,
        origin=origin,
        basis=basis,
        vhf_bind=ProvenVhfBindFrame(True, vhf),
        body0_bind=ProvenBody0BindFrame(True, True, 0, False, body_bind),
    )
    expected = process1.compose_body0_pose_to_vhf_world_matrix(
        vhf, body_bind, origin, basis
    )
    assert result["vehicle_world_matrix"] == pytest.approx(expected, abs=1.0e-5)
    assert result["body0_runtime_row"] == pytest.approx(
        process1.body_pose_row_matrix(origin, basis), abs=1.0e-6
    )


def test_phase704_fails_closed_without_static_bind_witness() -> None:
    vhf, body_bind, origin, basis = _fixture()
    with pytest.raises(ValueError, match="proven-static"):
        compose(
            body_index=0,
            origin=origin,
            basis=basis,
            vhf_bind=ProvenVhfBindFrame(True, vhf),
            body0_bind=ProvenBody0BindFrame(False, False, 0, False, body_bind),
        )


def test_phase704_rejects_identity_assumption_and_wrong_body() -> None:
    vhf, body_bind, origin, basis = _fixture()
    with pytest.raises(ValueError, match="identity assumption"):
        compose(
            body_index=0,
            origin=origin,
            basis=basis,
            vhf_bind=ProvenVhfBindFrame(True, vhf),
            body0_bind=ProvenBody0BindFrame(True, True, 0, True, body_bind),
        )
    with pytest.raises(ValueError, match="BODY 0"):
        compose(
            body_index=9,
            origin=origin,
            basis=basis,
            vhf_bind=ProvenVhfBindFrame(True, vhf),
            body0_bind=ProvenBody0BindFrame(True, True, 0, False, body_bind),
        )


def test_phase704_rejects_singular_and_nonfinite_inputs() -> None:
    vhf, body_bind, origin, basis = _fixture()
    singular = list(body_bind)
    singular[0] = 0.0
    with pytest.raises(ValueError, match="singular"):
        compose(
            body_index=0,
            origin=origin,
            basis=basis,
            vhf_bind=ProvenVhfBindFrame(True, vhf),
            body0_bind=ProvenBody0BindFrame(True, True, 0, False, tuple(singular)),
        )
    with pytest.raises(ValueError, match="non-finite"):
        compose(
            body_index=0,
            origin=(float("nan"), 0.0, 0.0),
            basis=basis,
            vhf_bind=ProvenVhfBindFrame(True, vhf),
            body0_bind=ProvenBody0BindFrame(True, True, 0, False, body_bind),
        )


def test_phase704_contract_keeps_current_retail_and_live_renderer_closed() -> None:
    payload = contract()
    assert payload["format"] == "SHIFT.NativeBMWBody0VHFWorldMatrixComposition/1"
    assert payload["process1_contract"] == "SHIFT.BMWBody0VHFBindFrameFrontier/1"
    assert payload["current_retail_BODY0_bind_frame_proven"] is False
    assert payload["current_retail_world_matrix_ready"] is False
    assert payload["phase645_VHF_bind_required"] is True
    assert payload["phase700_selected_BODY_pose_required"] is True
    assert payload["phase646_output_matrix_float32"] is True
    assert payload["identity_bind_assumption_allowed"] is False
    assert payload["live_vulkan_buffer_mutation_enabled"] is False
    assert payload["fixed_step_auto_schedule"] is False
    assert payload["original_game_executed"] is False
    assert payload["new_runtime_capture_required"] is False
