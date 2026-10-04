from __future__ import annotations

import pytest

from bmw_body0_vhf_world_matrix_composition_runtime import (
    ProvenBody0BindFrame,
    ProvenVhfBindFrame,
)
from bmw_vehicle_world_matrix_runtime_handoff_runtime import (
    build_handoff,
    contract,
)
from global_vehicle_body_owner_selection_runtime import (
    blocked_current_retail_handoff,
    synthetic_positive_handoff,
)


def _vhf() -> tuple[float, ...]:
    return (
        0.0, 2.0, 0.0, 0.0,
        -1.0, 0.0, 0.0, 0.0,
        0.0, 0.0, 0.5, 0.0,
        5.0, 6.0, 7.0, 1.0,
    )


def _body_bind() -> tuple[float, ...]:
    return (
        1.0, 0.0, 0.0, 0.0,
        0.0, 2.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        1.0, 2.0, 3.0, 1.0,
    )


def _basis() -> tuple[float, ...]:
    return (
        1.0, 0.0, 0.0,
        0.0, 1.0, 0.0,
        0.0, 0.0, 1.0,
    )


def _positive_kwargs() -> dict[str, object]:
    return {
        "identity": synthetic_positive_handoff(),
        "body_index": 0,
        "origin": (10.0, 20.0, 30.0),
        "basis": _basis(),
        "vhf_bind": ProvenVhfBindFrame(True, _vhf()),
        "body0_bind": ProvenBody0BindFrame(True, True, 0, False, _body_bind()),
    }


def test_phase705_composes_existing_identity_and_world_matrix_boundaries() -> None:
    result = build_handoff(**_positive_kwargs())
    assert result["body_index"] == 0
    assert result["vehicle_world_matrix"] == pytest.approx(
        (
            0.0, 1.0, 0.0, 0.0,
            -1.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.5, 0.0,
            14.0, 22.0, 34.0, 1.0,
        ),
        abs=1.0e-5,
    )


def test_phase705_current_retail_identity_fails_before_bind_promotion() -> None:
    kwargs = _positive_kwargs()
    kwargs["identity"] = blocked_current_retail_handoff()
    kwargs["body0_bind"] = ProvenBody0BindFrame(False, False, 0, False, _body_bind())
    with pytest.raises(ValueError, match="not retail-ready"):
        build_handoff(**kwargs)


def test_phase705_selection_must_match_supplied_persistent_pose() -> None:
    kwargs = _positive_kwargs()
    kwargs["body_index"] = 9
    with pytest.raises(ValueError, match="does not match supplied persistent pose"):
        build_handoff(**kwargs)


def test_phase705_preserves_phase704_bind_gate() -> None:
    kwargs = _positive_kwargs()
    kwargs["body0_bind"] = ProvenBody0BindFrame(False, False, 0, False, _body_bind())
    with pytest.raises(ValueError, match="proven-static"):
        build_handoff(**kwargs)


def test_phase705_contract_keeps_current_retail_and_scheduling_closed() -> None:
    payload = contract()
    assert payload["format"] == "SHIFT.NativeBMWVehicleWorldMatrixRuntimeHandoff/1"
    assert payload["phase703_identity_admission_reused"] is True
    assert payload["phase700_runtime_pose_handoff_reused_by_native"] is True
    assert payload["phase704_composition_reused"] is True
    assert payload["current_retail_identity_ready"] is False
    assert payload["current_retail_BODY0_bind_ready"] is False
    assert payload["current_retail_world_matrix_ready"] is False
    assert payload["read_only_runtime_handoff"] is True
    assert payload["phase646_matrix_output"] is True
    assert payload["live_vulkan_buffer_mutation_enabled"] is False
    assert payload["fixed_step_auto_schedule"] is False
    assert payload["original_game_executed"] is False
    assert payload["new_runtime_capture_required"] is False
