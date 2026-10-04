from offline_runtime_requirements import (
    AMBIGUOUS,
    MISSING,
    READY,
    RUNTIME_EVIDENCE_REQUIRED,
    build_runtime_requirements,
)


def _bootstrap():
    return {
        "format": "SHIFT.OfflineRuntimeBootstrap/1",
        "offline_build_ready": True,
        "runtime_ready": False,
        "track": "Silverstone_Era3_GrandPrix",
        "vehicle": "BMW_M3_E36",
        "readiness": {},
        "artifacts": {},
        "stages": {},
    }


def _evidence_row():
    return {
        "binding_index": 17,
        "draw_order": 4,
        "register": 7,
        "sampler": "shadowMap",
        "sampler_type": "sampler2D",
        "reason": "snapshot-content-not-captured",
        "expected_d3d9_resource_type": "texture2d",
        "required_snapshot_path_count": 1,
        "stage_binding_observation_count": 1,
        "typed_resource_creation_observation_count": 1,
        "valid_snapshot_observation_count": 0,
        "snapshot_status_counts": {"missing": 1},
        "snapshot_path_counts": [0],
        "capture_frames": [120],
        "capture_draw_indices": [9],
        "requested_texture_stage": 7,
    }


def _handoff(*, reasons=None, rows=None, count=None, capture_required=True):
    evidence_rows = [_evidence_row()] if rows is None else rows
    requirement_count = len(evidence_rows) if count is None else count
    return {
        "format": "SHIFT.RendererNativeSceneHandoff/1",
        "status": "blocked",
        "ready": False,
        "scene_set_ready": False,
        "blocking_reasons": reasons or [
            "phase590:runtime-evidence-required:binding-17:s7:"
            "sampler2D:snapshot-content-not-captured"
        ],
        "boundary": {
            "capture_observation_required": capture_required,
            "capture_observation_requirement_count": requirement_count,
        },
        "existing_capture_completion": {
            "runtime_evidence_required": evidence_rows,
        },
    }


def _scene_row(report):
    return next(
        row for row in report["requirements"] if row["name"] == "scene_set"
    )


def _section_scene(report, section):
    return next(row for row in report[section] if row["name"] == "scene_set")


def test_exact_phase641_snapshot_frontier_classifies_scene_as_runtime_evidence_required():
    report = build_runtime_requirements(
        _bootstrap(),
        runtime_scene_handoff=_handoff(),
    )

    scene = _scene_row(report)
    assert scene["classification"] == RUNTIME_EVIDENCE_REQUIRED
    assert scene["runtime_evidence_required"] == [_evidence_row()]
    assert scene["runtime_evidence_reasons"] == [
        "binding-17:s7:sampler2D:snapshot-content-not-captured"
    ]

    section = _section_scene(report, "RUNTIME-EVIDENCE REQUIRED")
    assert section["runtime_evidence_required"] == [_evidence_row()]
    assert section["reasons"] == [
        "binding-17:s7:sampler2D:snapshot-content-not-captured"
    ]
    assert all(row["name"] != "scene_set" for row in report[MISSING])
    assert "runtime-evidence-required:scene_set" in report["blocking_reasons"]
    assert report["boundary"][
        "runtime_scene_capture_observation_frontier_consumed"
    ] is True


def test_capture_required_flag_without_exact_rows_stays_missing():
    report = build_runtime_requirements(
        _bootstrap(),
        runtime_scene_handoff=_handoff(rows=[]),
    )

    scene = _scene_row(report)
    assert scene["classification"] == MISSING
    assert "runtime_evidence_required" not in scene
    assert report["boundary"][
        "runtime_scene_capture_observation_frontier_consumed"
    ] is False


def test_capture_requirement_count_mismatch_stays_missing():
    report = build_runtime_requirements(
        _bootstrap(),
        runtime_scene_handoff=_handoff(count=2),
    )

    assert _scene_row(report)["classification"] == MISSING
    assert "runtime-evidence-required:scene_set" not in report["blocking_reasons"]


def test_scene_identity_ambiguity_precedes_snapshot_evidence_request():
    report = build_runtime_requirements(
        _bootstrap(),
        runtime_scene_handoff=_handoff(
            reasons=[
                "phase590:scene-external-capture:binding-17:scene-draw-ambiguous:2",
                "phase590:runtime-evidence-required:binding-17:s7:"
                "sampler2D:snapshot-content-not-captured",
            ],
        ),
    )

    scene = _scene_row(report)
    assert scene["classification"] == AMBIGUOUS
    assert "runtime_evidence_required" not in scene
    assert _section_scene(report, AMBIGUOUS)["reasons"][0].endswith(
        "scene-draw-ambiguous:2"
    )


def test_validated_explicit_scene_can_satisfy_capture_frontier_without_stale_evidence():
    validated = {
        "scene_set": {
            "format": "SHIFT.OfflineValidatedRuntimeInput/1",
            "name": "scene_set",
            "ready": True,
            "artifact": "/workspace/proven-scene",
            "source": "validated explicit runtime input",
            "validation": {"ready": True},
        }
    }
    report = build_runtime_requirements(
        _bootstrap(),
        runtime_scene_handoff=_handoff(),
        validated_runtime_inputs=validated,
    )

    scene = _scene_row(report)
    assert scene["classification"] == READY
    assert scene["satisfied"] is True
    assert scene["artifact"] == "/workspace/proven-scene"
    assert "runtime_evidence_required" not in scene
    assert "runtime_evidence_reasons" not in scene
