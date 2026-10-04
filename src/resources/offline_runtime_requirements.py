"""Describe remaining native-runtime evidence gates after offline bootstrap.

This module is diagnostic only. It translates already-produced Process 3
bootstrap artifacts plus *prevalidated* explicit runtime inputs into an exact
requirements ledger. It never validates files itself, creates evidence, or
substitutes an explicit path for a conflicting proven pipeline artifact.
"""
from __future__ import annotations

from typing import Any, Mapping

FORMAT = "SHIFT.OfflineNativeRuntimeRequirements/1"
BOOTSTRAP_FORMAT = "SHIFT.OfflineRuntimeBootstrap/1"
RUNTIME_SCENE_HANDOFF_FORMAT = "SHIFT.RendererNativeSceneHandoff/1"
VALIDATED_INPUT_FORMAT = "SHIFT.OfflineValidatedRuntimeInput/1"

READY = "READY"
MISSING = "MISSING"
AMBIGUOUS = "AMBIGUOUS"
RUNTIME_EVIDENCE_REQUIRED = "RUNTIME-EVIDENCE REQUIRED"
CLASSIFICATIONS = (READY, MISSING, AMBIGUOUS, RUNTIME_EVIDENCE_REQUIRED)

_RUNTIME_EVIDENCE_NAMES = {
    "participant_boundary",
    "camera_state",
    "solver_frame",
    "generated_body_constraint_frame",
    "constraint_sample_relation_frame",
    "constraint_relation_reset_frame",
    "post_solve_projection",
}


def _artifact_path(bootstrap: Mapping[str, Any], name: str) -> str | None:
    artifacts = bootstrap.get("artifacts") or {}
    if not isinstance(artifacts, Mapping):
        return None
    text = str(artifacts.get(name) or "").strip()
    return text or None


def _vehicle_artifact_path(bootstrap: Mapping[str, Any], name: str) -> str | None:
    stages = bootstrap.get("stages") or {}
    vehicle = stages.get("native_vehicle") if isinstance(stages, Mapping) else None
    if not isinstance(vehicle, Mapping):
        return None
    artifacts = vehicle.get("artifacts") or {}
    row = artifacts.get(name) if isinstance(artifacts, Mapping) else None
    if not isinstance(row, Mapping):
        return None
    text = str(row.get("path") or "").strip()
    return text or None


def _runtime_scene_artifact(
    runtime_scene_handoff: Mapping[str, Any] | None,
) -> tuple[bool, str | None]:
    if runtime_scene_handoff is None:
        return False, None
    if runtime_scene_handoff.get("format") != RUNTIME_SCENE_HANDOFF_FORMAT:
        raise ValueError(
            f"runtime_scene_handoff must be {RUNTIME_SCENE_HANDOFF_FORMAT}"
        )
    if (
        runtime_scene_handoff.get("ready") is not True
        or runtime_scene_handoff.get("scene_set_ready") is not True
    ):
        return False, None
    artifacts = runtime_scene_handoff.get("artifacts") or {}
    if not isinstance(artifacts, Mapping):
        return False, None
    text = str(artifacts.get("scene_set_dir") or "").strip()
    return (bool(text), text or None)


def _normalized_artifact(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _validated_inputs(
    value: Mapping[str, Mapping[str, Any]] | None,
) -> dict[str, Mapping[str, Any]]:
    if value is None:
        return {}
    rows: dict[str, Mapping[str, Any]] = {}
    for raw_name, raw in value.items():
        name = str(raw_name)
        if not isinstance(raw, Mapping):
            raise ValueError(f"validated runtime input {name!r} must be an object")
        if raw.get("format") != VALIDATED_INPUT_FORMAT:
            raise ValueError(
                f"validated runtime input {name!r} must be {VALIDATED_INPUT_FORMAT}"
            )
        if str(raw.get("name") or "") != name:
            raise ValueError(f"validated runtime input name mismatch for {name!r}")
        rows[name] = raw
    return rows


def _default_classification(row: Mapping[str, Any]) -> str:
    if row.get("satisfied") is True:
        return READY
    name = str(row.get("name") or "")
    if name in _RUNTIME_EVIDENCE_NAMES:
        return RUNTIME_EVIDENCE_REQUIRED
    return MISSING


def _scene_runtime_evidence_required(
    runtime_scene_handoff: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    """Return only the exact Phase 641 capture-observation frontier.

    A generic blocked scene or a zero Phase 590 candidate count is not enough to
    claim runtime evidence. Phase 641 emits both an explicit boundary flag and
    the exact per-binding/register evidence rows after it has already observed
    the typed D3D9 resource without usable snapshot content. Consume only that
    self-consistent contract here.
    """
    if runtime_scene_handoff is None or runtime_scene_handoff.get("ready") is True:
        return []
    boundary = runtime_scene_handoff.get("boundary") or {}
    completion = runtime_scene_handoff.get("existing_capture_completion") or {}
    if not isinstance(boundary, Mapping) or not isinstance(completion, Mapping):
        return []
    if boundary.get("capture_observation_required") is not True:
        return []

    raw_rows = completion.get("runtime_evidence_required") or []
    if not isinstance(raw_rows, list):
        return []
    rows = [dict(row) for row in raw_rows if isinstance(row, Mapping)]
    if not rows or len(rows) != len(raw_rows):
        return []

    try:
        expected_count = int(boundary.get("capture_observation_requirement_count"))
    except (TypeError, ValueError):
        return []
    if expected_count != len(rows):
        return []
    return rows


def _scene_blocker_classification(
    runtime_scene_handoff: Mapping[str, Any] | None,
    runtime_evidence_required: list[Mapping[str, Any]],
) -> str | None:
    if runtime_scene_handoff is None or runtime_scene_handoff.get("ready") is True:
        return None
    reasons = [
        str(reason).lower()
        for reason in runtime_scene_handoff.get("blocking_reasons") or []
    ]
    # Identity ambiguity remains a stronger blocker than missing runtime bytes.
    # Never hide it behind an evidence request.
    if any("ambiguous" in reason or "multiple-" in reason for reason in reasons):
        return AMBIGUOUS
    if runtime_evidence_required:
        return RUNTIME_EVIDENCE_REQUIRED
    return None


def _runtime_evidence_reason(row: Mapping[str, Any]) -> str:
    binding = row.get("binding_index")
    register = row.get("register")
    sampler_type = str(row.get("sampler_type") or "unknown")
    reason = str(row.get("reason") or "runtime-observation-required")
    return f"binding-{binding}:s{register}:{sampler_type}:{reason}"


def _apply_validated_input(
    row: dict[str, Any],
    validated: Mapping[str, Any] | None,
) -> None:
    row["explicit_input_supplied"] = validated is not None
    row["explicit_input_validated"] = False
    row["explicit_validation"] = None
    if validated is None:
        return

    validation = validated.get("validation") or {}
    if isinstance(validation, Mapping):
        row["explicit_validation"] = dict(validation)
    if validated.get("ready") is not True:
        row["explicit_validation_blocking_reasons"] = list(
            validated.get("blocking_reasons") or ["not-ready"]
        )
        return

    row["explicit_input_validated"] = True
    explicit_artifact = _normalized_artifact(validated.get("artifact"))
    proven_artifact = _normalized_artifact(row.get("artifact"))
    if row.get("satisfied") is True:
        # A validated explicit input may confirm a proven artifact, but it may
        # never override a different one. Preserve the proven artifact so the
        # profile builder can also fail closed on the same conflict.
        if (
            explicit_artifact is not None
            and proven_artifact is not None
            and explicit_artifact != proven_artifact
        ):
            row["classification"] = AMBIGUOUS
            row["ambiguity_reasons"] = [
                "validated-explicit-conflicts-with-proven-artifact"
            ]
        return

    row["satisfied"] = True
    row["artifact"] = explicit_artifact
    row["source"] = str(
        validated.get("source") or "validated explicit runtime input"
    )
    row["artifact_origin"] = "explicit-validated"
    row["classification"] = READY
    # Explicit, independently validated scene/resource input may satisfy a
    # missing capture-derived frontier. Do not leave stale evidence diagnostics
    # attached to a row that is now READY.
    row.pop("runtime_evidence_required", None)
    row.pop("runtime_evidence_reasons", None)


def _section_row(row: Mapping[str, Any]) -> dict[str, Any]:
    value = {
        "name": row.get("name"),
        "artifact": row.get("artifact"),
        "source": row.get("source"),
    }
    reasons = (
        row.get("ambiguity_reasons")
        or row.get("runtime_evidence_reasons")
        or row.get("explicit_validation_blocking_reasons")
    )
    if reasons:
        value["reasons"] = list(reasons)
    evidence = row.get("runtime_evidence_required")
    if isinstance(evidence, list) and evidence:
        value["runtime_evidence_required"] = [
            dict(item) for item in evidence if isinstance(item, Mapping)
        ]
    return value


def build_runtime_requirements(
    bootstrap: Mapping[str, Any],
    *,
    runtime_scene_handoff: Mapping[str, Any] | None = None,
    validated_runtime_inputs: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return exact runtime requirements without promoting unvalidated paths."""
    if bootstrap.get("format") != BOOTSTRAP_FORMAT:
        raise ValueError(f"bootstrap must be {BOOTSTRAP_FORMAT}")

    readiness = bootstrap.get("readiness") or {}
    if not isinstance(readiness, Mapping):
        readiness = {}

    validated = _validated_inputs(validated_runtime_inputs)
    physics_ready = readiness.get("vehicle_runtime_physics_contract_ready") is True
    participant_ready = (
        readiness.get("vehicle_participant_runtime_identity_ready") is True
    )
    handoff_scene_ready, handoff_scene_artifact = _runtime_scene_artifact(
        runtime_scene_handoff
    )
    bootstrap_scene_ready = readiness.get("runtime_scene_ready") is True
    scene_ready = bootstrap_scene_ready or handoff_scene_ready
    scene_artifact = handoff_scene_artifact if handoff_scene_ready else None
    scene_source = (
        "runtime-proven renderer native scene handoff"
        if handoff_scene_ready
        else "runtime-proven draw admission"
    )
    scene_runtime_evidence = _scene_runtime_evidence_required(runtime_scene_handoff)

    rows: list[dict[str, Any]] = [
        {
            "name": "scene_set",
            "expected_format": "SHIFT.NativeSceneVulkanSet/1",
            "satisfied": scene_ready,
            "artifact": scene_artifact,
            "artifact_origin": "proven-pipeline" if scene_ready else None,
            "source": scene_source,
        },
        {
            "name": "physics_manifest",
            "expected_format": "SHIFT.BMWM3VehiclePhysicsResourceManifest/1",
            "satisfied": physics_ready,
            "artifact": (
                _vehicle_artifact_path(bootstrap, "native_physics_manifest")
                if physics_ready else None
            ),
            "artifact_origin": "proven-pipeline" if physics_ready else None,
            "source": "exact offline vehicle physics compatibility manifest",
        },
        {
            "name": "participant_boundary",
            "expected_format": "SHIFT.NativePhysicsParticipantRuntimeEvidence/1",
            "satisfied": participant_ready,
            "artifact": (
                _artifact_path(bootstrap, "participant_runtime_evidence")
                if participant_ready else None
            ),
            "artifact_origin": "proven-pipeline" if participant_ready else None,
            "source": "exact runtime participant observation join",
        },
        {
            "name": "camera_state",
            "expected_format": "SHIFT.NativeCameraStateBridge/1",
            "satisfied": False,
            "artifact": None,
            "artifact_origin": None,
            "source": "external proven runtime evidence",
        },
        {
            "name": "solver_frame",
            "expected_format": "SHIFT.NativeBuiltinSolverFramePacket/1",
            "packet_magic": "SBFR",
            "satisfied": False,
            "artifact": None,
            "artifact_origin": None,
            "source": "external proven runtime evidence",
        },
        {
            "name": "generated_body_constraint_frame",
            "expected_format": "SHIFT.NativeGeneratedBodyConstraintFramePacket/1",
            "packet_magic": "GBCF",
            "satisfied": False,
            "artifact": None,
            "artifact_origin": None,
            "source": "external proven runtime evidence",
        },
        {
            "name": "constraint_sample_relation_frame",
            "expected_format": "SHIFT.NativeConstraintSampleRelationFramePacket/1",
            "packet_magic": "CSRF",
            "satisfied": False,
            "artifact": None,
            "artifact_origin": None,
            "source": "external proven runtime evidence",
        },
        {
            "name": "constraint_relation_reset_frame",
            "expected_format": "SHIFT.NativeConstraintRelationResetFramePacket/1",
            "packet_magic": "CRRF",
            "satisfied": False,
            "artifact": None,
            "artifact_origin": None,
            "source": "external proven runtime evidence",
        },
        {
            "name": "post_solve_projection",
            "expected_format": "SHIFT.NativePostSolveBodyProjectionPacket/1",
            "packet_magic": "SBPS",
            "satisfied": False,
            "artifact": None,
            "artifact_origin": None,
            "source": "external proven runtime evidence",
        },
        {
            "name": "input_binding",
            "expected_format": "SHIFT.NativeRuntimeInputScript/1 or interactive input",
            "satisfied": False,
            "artifact": None,
            "artifact_origin": None,
            "source": "external runtime choice/evidence",
        },
    ]

    scene_classification = _scene_blocker_classification(
        runtime_scene_handoff,
        scene_runtime_evidence,
    )
    for row in rows:
        row["classification"] = _default_classification(row)
        if row["name"] == "scene_set" and scene_classification is not None:
            row["classification"] = scene_classification
            if scene_classification == AMBIGUOUS:
                row["ambiguity_reasons"] = list(
                    runtime_scene_handoff.get("blocking_reasons") or []
                )
            elif scene_classification == RUNTIME_EVIDENCE_REQUIRED:
                row["runtime_evidence_required"] = [
                    dict(item) for item in scene_runtime_evidence
                ]
                row["runtime_evidence_reasons"] = [
                    _runtime_evidence_reason(item)
                    for item in scene_runtime_evidence
                ]
        _apply_validated_input(row, validated.get(str(row["name"])))

    known = {str(row["name"]) for row in rows}
    unknown_validated = sorted(set(validated) - known)
    if unknown_validated:
        raise ValueError(
            "unknown validated runtime inputs: " + ", ".join(unknown_validated)
        )

    sections: dict[str, list[dict[str, Any]]] = {
        classification: [] for classification in CLASSIFICATIONS
    }
    for row in rows:
        classification = str(row.get("classification") or MISSING)
        if classification not in sections:
            raise ValueError(f"unknown requirement classification: {classification}")
        sections[classification].append(_section_row(row))

    satisfied = [str(row["name"]) for row in rows if row.get("satisfied") is True]
    missing = [str(row["name"]) for row in rows if row.get("satisfied") is not True]
    blocking = [
        str(row["name"])
        for row in rows
        if row.get("classification") != READY
    ]
    ready = not blocking
    blocking_reasons: list[str] = []
    for row in rows:
        name = str(row["name"])
        classification = row.get("classification")
        if classification == READY:
            continue
        # Retain the historical generic blocker for compatibility while adding
        # a precise diagnostic reason below it.
        blocking_reasons.append(f"runtime-requirement-missing:{name}")
        if classification == AMBIGUOUS:
            blocking_reasons.append(f"runtime-requirement-ambiguous:{name}")
        elif classification == RUNTIME_EVIDENCE_REQUIRED:
            blocking_reasons.append(f"runtime-evidence-required:{name}")

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "offline_build_ready": bootstrap.get("offline_build_ready") is True,
        "runtime_ready_claimed_by_bootstrap": bootstrap.get("runtime_ready") is True,
        "track": bootstrap.get("track"),
        "vehicle": bootstrap.get("vehicle"),
        "requirements": rows,
        "READY": sections[READY],
        "MISSING": sections[MISSING],
        "AMBIGUOUS": sections[AMBIGUOUS],
        "RUNTIME-EVIDENCE REQUIRED": sections[RUNTIME_EVIDENCE_REQUIRED],
        "summary": {
            "requirement_count": len(rows),
            "satisfied_count": len(satisfied),
            "missing_count": len(missing),
            "blocking_count": len(blocking),
            "satisfied": satisfied,
            "missing": missing,
            "blocking": blocking,
            "classification_counts": {
                key: len(sections[key]) for key in CLASSIFICATIONS
            },
        },
        "blocking_reasons": list(dict.fromkeys(blocking_reasons)),
        "boundary": {
            "diagnostic_only": True,
            "runtime_scene_handoff_format": RUNTIME_SCENE_HANDOFF_FORMAT,
            "runtime_scene_handoff_accepted": handoff_scene_ready,
            "runtime_scene_capture_observation_frontier_consumed": bool(
                scene_runtime_evidence
            ),
            "runtime_scene_capture_observation_requires_exact_frontier": True,
            "validated_runtime_input_format": VALIDATED_INPUT_FORMAT,
            "validated_explicit_input_may_override_proven_artifact": False,
            "unvalidated_explicit_path_is_ready": False,
            "missing_evidence_synthesized": False,
            "artifact_substitution_allowed": False,
            "static_scene_promoted_to_runtime_scene": False,
            "structural_participant_promoted_to_runtime_identity": False,
            "vertical_slice_launcher_validation_still_required": True,
            "original_game_execution_required": False,
        },
    }
