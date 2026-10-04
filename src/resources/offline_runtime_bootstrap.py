"""One-command fail-closed SHIFT resource -> native bootstrap orchestration.

This module composes only existing source-backed Process 3 stages.  It does not
promote static scene bindings to runtime draw proof and it does not claim that a
vehicle participant/input/fixed-step runtime exists merely because its resource
and physics manifests are ready.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from offline_native_scene import build_native_scene_files
from offline_native_vehicle import build_native_vehicle_files
from offline_resource_loaders import load_track, load_vehicle
from offline_resource_pipeline import run_offline_pipeline
from offline_scene_ir import build_scene_ir
from retail_archive_admission import build_retail_archive_identity_admission

FORMAT = "SHIFT.OfflineRuntimeBootstrap/1"
TYPED_CLOSURE_FORMAT = "SHIFT.TypedResourceClosure/1"


def _load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _write(path: str | Path, value: Mapping[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _blocked_stage(format_name: str, reasons: Sequence[str]) -> dict[str, Any]:
    blockers = list(dict.fromkeys(str(reason) for reason in reasons if reason))
    return {
        "format": format_name,
        "version": 1,
        "status": "blocked",
        "ready": False,
        "blocking_reasons": blockers or ["upstream-not-ready"],
    }


def _prefix_blockers(prefix: str, report: Mapping[str, Any]) -> list[str]:
    reasons = report.get("blocking_reasons") or []
    if not reasons and report.get("ready") is not True:
        reasons = ["not-ready"]
    return [f"{prefix}:{reason}" for reason in reasons]


def _selected_typed_root(
    bootstrap: Mapping[str, Any],
    typed_closure: Mapping[str, Any],
    *,
    group: str,
    extension: str,
) -> tuple[Path | None, dict[str, Any] | None, list[str]]:
    blockers: list[str] = []
    if typed_closure.get("format") != TYPED_CLOSURE_FORMAT:
        return None, None, ["typed-resource-closure:invalid-format"]
    roots = bootstrap.get("roots") or {}
    group_roots = roots.get(group) if isinstance(roots, Mapping) else None
    root_id = (
        group_roots.get(extension)
        if isinstance(group_roots, Mapping)
        else None
    )
    if not isinstance(root_id, str) or not root_id:
        return None, None, [f"bootstrap-root-missing:{group}:{extension}"]

    hits = [
        row
        for row in (typed_closure.get("resources") or [])
        if isinstance(row, Mapping) and str(row.get("resource_id") or "") == root_id
    ]
    if len(hits) != 1:
        return None, None, [
            f"typed-root-" + ("missing" if not hits else f"ambiguous:{len(hits)}")
            + f":{root_id}"
        ]

    row = dict(hits[0])
    if row.get("identity_match") is not True:
        blockers.append(f"typed-root-identity-mismatch:{root_id}")
    output = row.get("output")
    if not output:
        blockers.append(f"typed-root-output-missing:{root_id}")
        path = None
    else:
        path = Path(str(output))
        if not path.is_file():
            blockers.append(f"typed-root-file-missing:{root_id}:{path}")
            path = None
    return path, row, blockers


def _blocked_native_vehicle(reasons: Sequence[str]) -> dict[str, Any]:
    report = _blocked_stage("SHIFT.OfflineNativeVehicleBuild/1", reasons)
    report["resource_ready"] = False
    report["participant_structural_ready"] = False
    report["participant_runtime_identity_evaluated"] = False
    report["participant_runtime_identity_ready"] = False
    report["runtime_physics_contract_ready"] = False
    report["native_vehicle_runtime_ready"] = False
    report["runtime_gate_blocking_reasons"] = ["native-vehicle-build-blocked"]
    return report


def build_offline_runtime_bootstrap(
    inputs: Sequence[str | Path],
    output_dir: str | Path,
    *,
    track: str,
    vehicle: str,
    decode_limit_per_archive: int = 0,
    root_consensus_path: str | Path | None = None,
    runtime_shader_admission_path: str | Path | None = None,
    participant_observation_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build the strongest currently provable track+vehicle native bootstrap."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    resources_dir = out / "resources"
    scene_ir_dir = out / "scene-ir"
    native_scene_dir = out / "native-scene"
    native_vehicle_dir = out / "native-vehicle"

    resource_pipeline = run_offline_pipeline(
        inputs,
        resources_dir,
        track=track,
        vehicle=vehicle,
        decode_limit_per_archive=decode_limit_per_archive,
    )
    catalog = _load(resources_dir / "resource_catalog.json")
    graph = _load(resources_dir / "dependency_graph.json")
    bootstrap = _load(resources_dir / "scene_vehicle_bootstrap.json")
    typed_closure = _load(resources_dir / "typed_resource_closure.json")
    retail_archive_admission = build_retail_archive_identity_admission(
        catalog,
        bootstrap,
        track=track,
        vehicle=vehicle,
    )
    _write(out / "retail_archive_identity_admission.json", retail_archive_admission)
    retail_archive_identity_ready = retail_archive_admission.get("ready") is True

    track_load = load_track(catalog, graph, track=track)
    vehicle_load = load_vehicle(catalog, graph, vehicle=vehicle)
    _write(out / "track_load.json", track_load)
    _write(out / "vehicle_load.json", vehicle_load)

    try:
        scene_ir = build_scene_ir(inputs, scene_ir_dir)
    except (OSError, RuntimeError, ValueError) as exc:
        scene_ir = _blocked_stage(
            "SHIFT.OfflineSceneIRMaterialization/1",
            [f"scene-ir-build-error:{type(exc).__name__}:{exc}"],
        )
        _write(scene_ir_dir / "scene_ir_materialization.json", scene_ir)

    sgb_path, sgb_root, sgb_blockers = _selected_typed_root(
        bootstrap,
        typed_closure,
        group="track_visual",
        extension=".sgb",
    )

    scene_gate_blockers: list[str] = []
    if not retail_archive_identity_ready:
        scene_gate_blockers.extend(
            _prefix_blockers("retail-archive-identity", retail_archive_admission)
        )
    if track_load.get("ready") is not True:
        scene_gate_blockers.extend(_prefix_blockers("track-load", track_load))
    if scene_ir.get("ready") is not True:
        scene_gate_blockers.extend(_prefix_blockers("scene-ir", scene_ir))
    scene_gate_blockers.extend(sgb_blockers)

    if not scene_gate_blockers and sgb_path is not None:
        try:
            native_scene = build_native_scene_files(
                sgb_path,
                scene_ir_dir,
                native_scene_dir,
                root_consensus_path=root_consensus_path,
                runtime_shader_admission_path=runtime_shader_admission_path,
            )
        except (OSError, RuntimeError, ValueError) as exc:
            native_scene = _blocked_stage(
                "SHIFT.OfflineNativeSceneBuild/1",
                [f"native-scene-build-error:{type(exc).__name__}:{exc}"],
            )
            native_scene["static_resource_ready"] = False
            native_scene["native_scene_runtime_ready"] = False
            _write(native_scene_dir / "native_scene_build.json", native_scene)
    else:
        native_scene = _blocked_stage(
            "SHIFT.OfflineNativeSceneBuild/1",
            scene_gate_blockers,
        )
        native_scene["static_resource_ready"] = False
        native_scene["native_scene_runtime_ready"] = False
        _write(native_scene_dir / "native_scene_build.json", native_scene)

    if retail_archive_identity_ready:
        try:
            vehicle_args = (
                resources_dir / "resource_catalog.json",
                resources_dir / "scene_vehicle_bootstrap.json",
                resources_dir / "vehicle_physics_bundle_report.json",
                native_vehicle_dir,
            )
            vehicle_kwargs: dict[str, Any] = {
                "typed_closure_path": resources_dir / "typed_resource_closure.json",
            }
            if participant_observation_path is not None:
                vehicle_kwargs["participant_observation_path"] = participant_observation_path
            native_vehicle = build_native_vehicle_files(
                *vehicle_args,
                **vehicle_kwargs,
            )
        except (OSError, RuntimeError, ValueError) as exc:
            native_vehicle = _blocked_native_vehicle(
                [f"native-vehicle-build-error:{type(exc).__name__}:{exc}"]
            )
            native_vehicle["participant_runtime_identity_evaluated"] = (
                participant_observation_path is not None
            )
            _write(native_vehicle_dir / "native_vehicle_build.json", native_vehicle)
    else:
        native_vehicle = _blocked_native_vehicle(
            _prefix_blockers("retail-archive-identity", retail_archive_admission)
        )
        _write(native_vehicle_dir / "native_vehicle_build.json", native_vehicle)

    resource_bootstrap_ready = resource_pipeline.get("resource_bootstrap_ready") is True
    track_load_ready = track_load.get("ready") is True
    vehicle_load_ready = vehicle_load.get("ready") is True
    scene_ir_ready = scene_ir.get("ready") is True
    static_scene_ready = native_scene.get("static_resource_ready") is True
    vehicle_resource_ready = native_vehicle.get("resource_ready") is True
    participant_structural_ready = native_vehicle.get("participant_structural_ready") is True
    participant_runtime_identity_evaluated = (
        native_vehicle.get("participant_runtime_identity_evaluated") is True
    )
    participant_runtime_identity_ready = (
        native_vehicle.get("participant_runtime_identity_ready") is True
    )
    vehicle_physics_manifest = native_vehicle.get("vehicle_physics_manifest") or {}
    physics_materialized_resources_ready = bool(
        isinstance(vehicle_physics_manifest, Mapping)
        and vehicle_physics_manifest.get("materialized_resources_ready") is True
    )
    runtime_scene_ready = native_scene.get("native_scene_runtime_ready") is True
    runtime_vehicle_ready = native_vehicle.get("native_vehicle_runtime_ready") is True
    runtime_ready = runtime_scene_ready and runtime_vehicle_ready

    offline_build_ready = all((
        resource_bootstrap_ready,
        retail_archive_identity_ready,
        track_load_ready,
        vehicle_load_ready,
        scene_ir_ready,
        static_scene_ready,
        vehicle_resource_ready,
        participant_structural_ready,
    ))

    blockers: list[str] = []
    if not resource_bootstrap_ready:
        blockers.extend(_prefix_blockers("resource-pipeline", resource_pipeline))
    if not retail_archive_identity_ready:
        blockers.extend(
            _prefix_blockers("retail-archive-identity", retail_archive_admission)
        )
    if not track_load_ready:
        blockers.extend(_prefix_blockers("track-load", track_load))
    if not vehicle_load_ready:
        blockers.extend(_prefix_blockers("vehicle-load", vehicle_load))
    if not scene_ir_ready:
        blockers.extend(_prefix_blockers("scene-ir", scene_ir))
    if not static_scene_ready:
        blockers.extend(_prefix_blockers("native-scene", native_scene))
    if not vehicle_resource_ready:
        blockers.extend(_prefix_blockers("native-vehicle", native_vehicle))
    if not participant_structural_ready:
        participant_boundary = native_vehicle.get("participant_boundary") or {}
        if isinstance(participant_boundary, Mapping):
            blockers.extend(_prefix_blockers("participant-boundary", participant_boundary))
        elif retail_archive_identity_ready:
            blockers.append("participant-boundary:not-ready")
    if not runtime_scene_ready:
        blockers.append("runtime-scene:runtime-proven-draw-admission-required")
    if not runtime_vehicle_ready:
        runtime_vehicle_blockers = native_vehicle.get("runtime_gate_blocking_reasons")
        if isinstance(runtime_vehicle_blockers, list) and runtime_vehicle_blockers:
            blockers.extend(
                "runtime-vehicle:" + str(reason)
                for reason in runtime_vehicle_blockers
            )
        else:
            blockers.append(
                "runtime-vehicle:participant-input-and-fixed-step-runtime-gates-required"
            )
    blockers = list(dict.fromkeys(blockers))

    if (
        not resource_bootstrap_ready
        or not retail_archive_identity_ready
        or not track_load_ready
        or not vehicle_load_ready
    ):
        status = "resource-blocked"
    elif not offline_build_ready:
        status = "offline-native-build-blocked"
    elif runtime_ready:
        status = "runtime-ready"
    else:
        status = "offline-native-build-ready-runtime-gated"

    artifacts = {
        "resource_pipeline": str(resources_dir / "pipeline_run.json"),
        "catalog": str(resources_dir / "resource_catalog.json"),
        "dependency_graph": str(resources_dir / "dependency_graph.json"),
        "bootstrap": str(resources_dir / "scene_vehicle_bootstrap.json"),
        "typed_resource_closure": str(resources_dir / "typed_resource_closure.json"),
        "retail_archive_identity_admission": str(
            out / "retail_archive_identity_admission.json"
        ),
        "vehicle_physics_bundle": str(
            resources_dir / "vehicle_physics_bundle_report.json"
        ),
        "track_load": str(out / "track_load.json"),
        "vehicle_load": str(out / "vehicle_load.json"),
        "scene_ir": str(scene_ir_dir / "scene_ir_materialization.json"),
        "native_scene": str(native_scene_dir / "native_scene_build.json"),
        "native_vehicle": str(native_vehicle_dir / "native_vehicle_build.json"),
        "participant_boundary": str(
            native_vehicle_dir / "native_physics_participant_boundary.json"
        ),
    }
    native_vehicle_artifacts = native_vehicle.get("artifacts") or {}
    if isinstance(native_vehicle_artifacts, Mapping):
        for name in ("vehicle_physics_manifest", "native_physics_manifest"):
            row = native_vehicle_artifacts.get(name)
            if isinstance(row, Mapping) and row.get("path"):
                artifacts[name] = str(row["path"])

    participant_runtime_artifact = (
        native_vehicle_artifacts.get("participant_runtime_evidence")
        if isinstance(native_vehicle_artifacts, Mapping)
        else None
    )
    if (
        isinstance(participant_runtime_artifact, Mapping)
        and participant_runtime_artifact.get("path")
    ):
        artifacts["participant_runtime_evidence"] = str(
            participant_runtime_artifact["path"]
        )

    if isinstance(vehicle_physics_manifest, Mapping):
        entries = vehicle_physics_manifest.get("entries") or {}
        sdf_entry = entries.get("sdf") if isinstance(entries, Mapping) else None
        if isinstance(sdf_entry, Mapping) and sdf_entry.get("materialized_path"):
            artifacts["vehicle_sdf"] = str(sdf_entry["materialized_path"])

    report = {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "offline_build_ready": offline_build_ready,
        "runtime_ready": runtime_ready,
        "track": track,
        "vehicle": vehicle,
        "inputs": [str(value) for value in inputs],
        "readiness": {
            "resource_bootstrap_ready": resource_bootstrap_ready,
            "retail_archive_identity_ready": retail_archive_identity_ready,
            "track_load_ready": track_load_ready,
            "vehicle_load_ready": vehicle_load_ready,
            "scene_ir_ready": scene_ir_ready,
            "static_scene_ready": static_scene_ready,
            "vehicle_resource_ready": vehicle_resource_ready,
            "vehicle_physics_materialized_resources_ready": (
                physics_materialized_resources_ready
            ),
            "vehicle_participant_structural_ready": participant_structural_ready,
            "vehicle_participant_runtime_identity_evaluated": (
                participant_runtime_identity_evaluated
            ),
            "vehicle_participant_runtime_identity_ready": (
                participant_runtime_identity_ready
            ),
            "vehicle_runtime_physics_contract_ready": (
                native_vehicle.get("runtime_physics_contract_ready") is True
            ),
            "runtime_scene_ready": runtime_scene_ready,
            "runtime_vehicle_ready": runtime_vehicle_ready,
        },
        "selected_track_sgb": sgb_root,
        "blocking_reasons": blockers,
        "stages": {
            "resource_pipeline": resource_pipeline,
            "retail_archive_identity_admission": retail_archive_admission,
            "track_load": track_load,
            "vehicle_load": vehicle_load,
            "scene_ir": scene_ir,
            "native_scene": native_scene,
            "native_vehicle": native_vehicle,
        },
        "artifacts": artifacts,
        "boundary": {
            "game_or_bff_inputs_to_offline_native_build_automated": True,
            "track_and_vehicle_names_are_high_level_inputs": True,
            "retail_archive_name_alone_is_admission_proof": False,
            "retail_archive_sha256_and_unique_occurrence_required": True,
            "byte_identical_archive_duplicates_collapsed": False,
            "scene_root_selected_by_bootstrap_resource_id": True,
            "scene_ir_legacy_dependency_hints_are_admission_proof": False,
            "exact_scene_resource_closure_required_by_native_scene_stage": True,
            "vehicle_physics_materialized_paths_require_exact_typed_closure": True,
            "vehicle_sdf_artifact_claims_body_semantics": False,
            "static_scene_promoted_to_runtime_draw_proof": False,
            "vehicle_participant_structural_boundary_required": True,
            "participant_runtime_identity_requires_exact_observation": True,
            "participant_runtime_observation_used": (
                participant_observation_path is not None
            ),
            "vehicle_resource_manifest_promoted_to_participant_identity": False,
            "shader_permutation_invented": False,
            "missing_dependency_substituted": False,
            "runtime_execution_claimed": runtime_ready,
        },
    }
    _write(out / "runtime_bootstrap.json", report)
    return report