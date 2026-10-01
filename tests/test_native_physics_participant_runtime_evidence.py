import json

import pytest

from native_physics_participant_boundary import (
    build_native_physics_participant_boundary,
)
from native_physics_participant_runtime_evidence import (
    FORMAT,
    OBSERVATION_FORMAT,
    build_native_physics_participant_runtime_evidence,
    build_native_physics_participant_runtime_evidence_file,
)


def _observation():
    return {
        "format": OBSERVATION_FORMAT,
        "version": 1,
        "ready": True,
        "verification_scope": "synthetic-regression-fixture",
        "manager_registry": {
            "global_instance": "DAT_00c109e0",
            "participant_pointer_token": "0x12345678",
            "registry_index": 7,
            "registry_index_source": "PhysicsParticipant+0x3c",
            "registry_index_source_offset": 0x3C,
            "participant_descriptor_type": 3,
        },
        "selector": {
            "global_instance": "DAT_00bbc600",
            "candidate_ready_offset": 0x74,
            "candidate_ready_value": 0,
        },
        "igphasevehicle_selection": {
            "participant_pointer_token": "0x12345678",
            "selector_ordinal": 2,
            "process_state": 1,
            "pointer_slot": "IGPhaseVehicle+0x450",
            "ordinal_slot": "IGPhaseVehicle+0x454",
            "state_slot": "IGPhaseVehicle+0x45c",
        },
        "join": {
            "same_participant_pointer_proven": True,
            "manager_registry_identity_observed": True,
            "igphasevehicle_selection_observed": True,
        },
    }


def test_runtime_observation_promotes_instance_without_equating_indices():
    boundary = build_native_physics_participant_boundary()
    report = build_native_physics_participant_runtime_evidence(
        boundary,
        _observation(),
    )

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["participant_instance_ready"] is True
    assert report["registry_selector_identity_join_proven"] is True
    assert report["participant_registry_index"] == 7
    assert report["selector_ordinal"] == 2
    assert report["participant_process_state"] == 1
    assert report["participant_index"] == -1
    assert report["participant_mode"] == -1
    assert report["participant_pointer_token"] == "0x12345678"
    assert (
        report["join_evidence"]["registry_index_equals_selector_ordinal"]
        is False
    )
    assert report["boundary"]["selected_provider_proven"] is False
    assert report["boundary"]["numeric_physics_equivalence_proven"] is False


def test_pointer_join_mismatch_fails_closed():
    observation = _observation()
    observation["igphasevehicle_selection"][
        "participant_pointer_token"
    ] = "0x87654321"

    with pytest.raises(ValueError, match="selected participant differ"):
        build_native_physics_participant_runtime_evidence(
            build_native_physics_participant_boundary(),
            observation,
        )


def test_missing_independent_join_proof_fails_closed():
    observation = _observation()
    observation["join"]["same_participant_pointer_proven"] = False

    with pytest.raises(ValueError, match="same participant pointer"):
        build_native_physics_participant_runtime_evidence(
            build_native_physics_participant_boundary(),
            observation,
        )


def test_selector_candidate_must_be_runtime_ready():
    observation = _observation()
    observation["selector"]["candidate_ready_value"] = 1

    with pytest.raises(ValueError, match="candidate is not ready"):
        build_native_physics_participant_runtime_evidence(
            build_native_physics_participant_boundary(),
            observation,
        )


def test_structural_boundary_must_remain_unresolved_before_promotion():
    boundary = build_native_physics_participant_boundary()
    boundary["participant_registry_index"] = 7

    with pytest.raises(ValueError, match="registry index must be unresolved"):
        build_native_physics_participant_runtime_evidence(
            boundary,
            _observation(),
        )


def test_file_builder_freezes_input_hashes(tmp_path):
    boundary_path = tmp_path / "boundary.json"
    observation_path = tmp_path / "observation.json"
    output_path = tmp_path / "runtime-evidence.json"

    boundary_path.write_text(
        json.dumps(build_native_physics_participant_boundary()),
        encoding="utf-8",
    )
    observation_path.write_text(
        json.dumps(_observation()),
        encoding="utf-8",
    )

    report = build_native_physics_participant_runtime_evidence_file(
        boundary_path,
        observation_path,
        output_path,
    )
    written = json.loads(output_path.read_text(encoding="utf-8"))

    assert report["ready"] is True
    assert len(report["provenance"]["structural_boundary_sha256"]) == 64
    assert len(report["provenance"]["runtime_observation_sha256"]) == 64
    assert written["participant_registry_index"] == 7
    assert written["selector_ordinal"] == 2
