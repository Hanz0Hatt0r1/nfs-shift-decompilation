import pytest

from native_physics_participant_bridge import (
    FORMAT,
    OBSERVATION_FORMAT,
    build_native_physics_participant_bridge,
    build_participant_selection_observation,
)


def _selected():
    return build_participant_selection_observation(
        ordinal=3,
        pointer_present=True,
        phase_state=1,
        capture_source="runtime-slot-probe",
        capture_frame=17,
    )


def test_selected_observation_preserves_source_identity_without_pointer_value():
    report = _selected()

    assert report["format"] == OBSERVATION_FORMAT
    assert report["ready"] is True
    assert report["status"] == "selected"
    assert report["source_identity"] == {
        "selector_global": "DAT_00bbc600",
        "selector_function": "FUN_00410ef0",
        "pointer_slot": "IGPhaseVehicle+0x450",
        "ordinal_slot": "IGPhaseVehicle+0x454",
        "phase_state_slot": "IGPhaseVehicle+0x45c",
    }
    assert report["observation"] == {
        "ordinal": 3,
        "pointer_present": True,
        "phase_state": 1,
    }
    assert report["provenance"]["runtime_observed"] is True
    assert report["boundary"]["pointer_value_serialized"] is False
    assert report["boundary"]["selector_manager_registry_joined"] is False
    assert "pointer_value" not in str(report)


def test_ready_bridge_maps_only_ordinal_and_phase_state():
    bridge = build_native_physics_participant_bridge(_selected())

    assert bridge["format"] == FORMAT
    assert bridge["ready"] is True
    assert bridge["native_participant_ready"] is True
    assert bridge["native_participant_index"] == 3
    assert bridge["native_participant_phase_state"] == 1
    assert bridge["native_participant_mode"] == -1
    assert bridge["participant_pointer_observed"] is True
    assert bridge["source"]["selector_global"] == "DAT_00bbc600"
    assert bridge["source"]["participant_manager_global"] == "DAT_00c109e0"
    assert bridge["source"]["selector_manager_same_object_proven"] is False
    assert bridge["boundary"]["participant_pointer_transport"] == (
        "not-performed"
    )
    assert bridge["boundary"]["participant_mode_semantics_proven"] is False
    assert bridge["boundary"]["provider_identity_inferred"] is False
    assert bridge["boundary"]["provider_numerics_executed"] is False
    assert bridge["boundary"]["selector_manager_registry_joined"] is False


def test_waiting_observation_remains_blocked_for_native_participant():
    observation = build_participant_selection_observation(
        ordinal=-1,
        pointer_present=False,
        phase_state=0,
        capture_source="runtime-slot-probe",
        capture_frame=18,
    )
    bridge = build_native_physics_participant_bridge(observation)

    assert observation["status"] == "waiting"
    assert observation["ready"] is False
    assert bridge["status"] == "waiting"
    assert bridge["ready"] is False
    assert bridge["native_participant_ready"] is False
    assert bridge["native_participant_index"] == -1
    assert bridge["native_participant_phase_state"] == 0
    assert bridge["native_participant_mode"] == -1


def test_waiting_ordinal_with_pointer_is_rejected():
    with pytest.raises(
        ValueError,
        match="waiting ordinal -1 cannot carry",
    ):
        build_participant_selection_observation(
            ordinal=-1,
            pointer_present=True,
            phase_state=0,
            capture_source="runtime-slot-probe",
            capture_frame=0,
        )


def test_selected_ordinal_without_pointer_is_rejected():
    with pytest.raises(
        ValueError,
        match="requires pointer presence",
    ):
        build_participant_selection_observation(
            ordinal=0,
            pointer_present=False,
            phase_state=1,
            capture_source="runtime-slot-probe",
            capture_frame=0,
        )


def test_source_identity_mismatch_is_rejected():
    observation = _selected()
    observation["source_identity"]["selector_global"] = "DAT_BAD"

    with pytest.raises(
        ValueError,
        match="source mismatch: selector_global",
    ):
        build_native_physics_participant_bridge(observation)


def test_non_runtime_observation_is_rejected():
    observation = _selected()
    observation["provenance"]["runtime_observed"] = False

    with pytest.raises(
        ValueError,
        match="not runtime-observed",
    ):
        build_native_physics_participant_bridge(observation)


def test_unknown_negative_ordinal_is_rejected():
    with pytest.raises(
        ValueError,
        match="must be -1 or non-negative",
    ):
        build_participant_selection_observation(
            ordinal=-2,
            pointer_present=False,
            phase_state=0,
            capture_source="runtime-slot-probe",
            capture_frame=0,
        )
