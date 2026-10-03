"""Build the canonical BMW + Silverstone playable scene from the existing corpus.

Phase 644 removes the manual vehicle-render handoff in front of the Phase 643
composite scene builder. Phase 645 closes the real-corpus transform gap: Phase
533 material slices carry no instance matrix, so the canonical BMW body matrix
is recovered from the retail VHF hierarchy, identity-checked against the golden
body MEB, converted to the SVWT/D3D row-vector convention, and attached to the
material-slice set before Phase 643.

No archive is selected by order or fuzzy name. Missing/duplicated canonical
archives and missing/conflicting VHF identity remain explicit blockers.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from bmw_body_material_admission import (
    DEFAULT_GOLDEN,
    build_bmw_body_material_admission,
    write_bmw_body_material_admission,
)
from bmw_vhf_body_world_transform import (
    apply_bmw_vhf_body_world_transform,
    build_bmw_vhf_body_world_transform,
)
from native_playable_scene_vulkan_set import build_native_playable_scene_vulkan_set
from offline_resource_pipeline import MaterializedArchive, materialize_bff_inputs

FORMAT = "SHIFT.NativePlayableSceneBootstrap/1"
TARGET_VEHICLE = "BMW_M3_E36"
REQUIRED_ARCHIVES = {
    "primary": "BMW_M3_E36.bff",
    "cockpit": "BMW_M3_E36_Cockpit.bff",
    "render": "RENDER.bff",
}


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _archive_basename(row: MaterializedArchive) -> str:
    if row.member:
        return PurePosixPath(row.member).name
    return row.path.name


def _select_archive(
    rows: Sequence[MaterializedArchive],
    expected: str,
) -> tuple[MaterializedArchive | None, list[str]]:
    hits = [
        row
        for row in rows
        if _archive_basename(row).casefold() == expected.casefold()
    ]
    if len(hits) == 1:
        return hits[0], []
    if not hits:
        return None, [f"playable-scene-corpus:archive-missing:{expected}"]
    return None, [
        f"playable-scene-corpus:archive-ambiguous:{expected}:{len(hits)}"
    ]


def _source_record(row: MaterializedArchive) -> dict[str, Any]:
    return {
        "archive": _archive_basename(row),
        "source": row.source,
        "member": row.member,
        "source_kind": "zip-member" if row.member is not None else "filesystem-bff",
    }


def _blocked(
    *,
    vehicle: str,
    track_scene_set: Path,
    output_dir: Path,
    blockers: Sequence[str],
    archive_sources: Mapping[str, Any] | None = None,
    admission: Mapping[str, Any] | None = None,
    vhf_transform: Mapping[str, Any] | None = None,
    composition: Mapping[str, Any] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    result = {
        "format": FORMAT,
        "version": 1,
        "status": "blocked",
        "ready": False,
        "scene_set_ready": False,
        "vehicle": vehicle,
        "track_scene_set": str(track_scene_set),
        "blocking_reasons": list(dict.fromkeys(str(reason) for reason in blockers)),
        "archive_sources": dict(archive_sources or {}),
        "stages": {
            "vehicle_material_admission": (
                dict(admission) if isinstance(admission, Mapping) else None
            ),
            "vehicle_vhf_body_world_transform": (
                dict(vhf_transform) if isinstance(vhf_transform, Mapping) else None
            ),
            "scene_composition": (
                dict(composition) if isinstance(composition, Mapping) else None
            ),
        },
        "artifacts": {
            "vehicle_material_admission": None,
            "vehicle_material_slice_set": None,
            "vehicle_material_slice_set_with_vhf_transform": None,
            "vehicle_vhf_body_world_transform": None,
            "scene_set_dir": None,
            "scene_composition": None,
        },
        "boundary": {
            "canonical_bff_selection_is_exact_basename": True,
            "archive_order_is_selection_authority": False,
            "manual_vehicle_material_slice_handoff_required": False,
            "manual_vehicle_bff_path_handoff_required": False,
            "phase643_composite_scene_consumed": False,
            "vhf_body_world_transform_consumed": False,
            "persistent_BODY_pose_consumed": False,
            "phase700_runtime_pose_handoff_consumed": False,
            "dynamic_vehicle_world_transform_claimed": False,
        },
    }
    if persist and output_dir.exists() and output_dir.is_dir():
        _write(output_dir / "playable_scene_bootstrap.json", result)
    return result


def build_native_playable_scene_bootstrap(
    inputs: Sequence[str | Path],
    track_scene_set: str | Path,
    output_dir: str | Path,
    *,
    vehicle: str,
    golden_manifest: str | Path | None = None,
    environment_cube_dds: str | Path | None = None,
    validator: str | None = None,
) -> dict[str, Any]:
    """Materialize canonical BMW render evidence and build the Phase 643 scene."""
    track_root = Path(track_scene_set).resolve()
    out = Path(output_dir).resolve()

    # Never let orchestration cleanup or diagnostics mutate its prepared track
    # input when the caller supplies overlapping source/output paths.
    if out == track_root or out in track_root.parents or track_root in out.parents:
        return _blocked(
            vehicle=vehicle,
            track_scene_set=track_root,
            output_dir=out,
            blockers=["playable-scene-bootstrap:output-overlaps-track-scene-set"],
            persist=False,
        )

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    if str(vehicle).casefold() != TARGET_VEHICLE.casefold():
        return _blocked(
            vehicle=vehicle,
            track_scene_set=track_root,
            output_dir=out,
            blockers=[f"playable-scene-bootstrap:unsupported-vehicle:{vehicle}"],
        )

    admission_dir = out / "vehicle-material-admission"
    scene_dir = out / "native-playable-scene"
    golden = (
        Path(golden_manifest)
        if golden_manifest is not None
        else Path(__file__).resolve().parents[2] / DEFAULT_GOLDEN
    )
    transformed_slice_set = out / "vehicle-material-slice-set-with-vhf-transform.json"
    vhf_transform_path = out / "vehicle-vhf-body-world-transform.json"

    archive_sources: dict[str, Any] = {}
    admission: Mapping[str, Any] | None = None
    vhf_transform: Mapping[str, Any] | None = None
    composition: Mapping[str, Any] | None = None
    blockers: list[str] = []

    try:
        with materialize_bff_inputs(inputs) as rows:
            selected: dict[str, MaterializedArchive] = {}
            for role, expected in REQUIRED_ARCHIVES.items():
                row, reasons = _select_archive(rows, expected)
                blockers.extend(reasons)
                if row is not None:
                    selected[role] = row
                    archive_sources[role] = _source_record(row)

            if blockers:
                return _blocked(
                    vehicle=vehicle,
                    track_scene_set=track_root,
                    output_dir=out,
                    blockers=blockers,
                    archive_sources=archive_sources,
                )

            primary = selected["primary"].path
            supplemental = [selected["cockpit"].path, selected["render"].path]
            try:
                admission = build_bmw_body_material_admission(
                    primary,
                    golden,
                    supplemental_bffs=supplemental,
                )
            except Exception as exc:
                blockers.append(
                    "playable-scene-bootstrap:vehicle-material-admission-failed:"
                    f"{type(exc).__name__}:{exc}"
                )
            else:
                write_bmw_body_material_admission(dict(admission), admission_dir)
                if admission.get("ready") is not True:
                    blockers.extend(
                        "playable-scene-bootstrap:vehicle-material:"
                        + str(reason)
                        for reason in admission.get("blocking_reasons") or ["not-ready"]
                    )

            source_slice_set = admission_dir / "material_slice_set.json"
            if not blockers and not source_slice_set.is_file():
                blockers.append(
                    "playable-scene-bootstrap:vehicle-material-slice-set-missing"
                )

            transformed_payload: Mapping[str, Any] | None = None
            if not blockers:
                try:
                    vhf_transform = build_bmw_vhf_body_world_transform(
                        primary,
                        golden,
                    )
                    _write(vhf_transform_path, vhf_transform)
                    transformed_payload = apply_bmw_vhf_body_world_transform(
                        source_slice_set,
                        vhf_transform,
                    )
                    _write(transformed_slice_set, transformed_payload)
                except Exception as exc:
                    blockers.append(
                        "playable-scene-bootstrap:vehicle-vhf-transform-failed:"
                        f"{type(exc).__name__}:{exc}"
                    )

            if not blockers:
                try:
                    composition = build_native_playable_scene_vulkan_set(
                        track_root,
                        transformed_slice_set,
                        scene_dir,
                        source_bffs=[primary, *supplemental],
                        environment_cube_dds=environment_cube_dds,
                        validator=validator,
                    )
                except Exception as exc:
                    blockers.append(
                        "playable-scene-bootstrap:phase643-failed:"
                        f"{type(exc).__name__}:{exc}"
                    )
                else:
                    if composition.get("ready") is not True:
                        blockers.extend(
                            "playable-scene-bootstrap:phase643:"
                            + str(reason)
                            for reason in composition.get("blocking_reasons") or ["not-ready"]
                        )
    except Exception as exc:
        blockers.append(
            "playable-scene-bootstrap:corpus-materialization-failed:"
            f"{type(exc).__name__}:{exc}"
        )

    blockers = list(dict.fromkeys(blockers))
    ready = (
        not blockers
        and isinstance(admission, Mapping)
        and admission.get("ready") is True
        and isinstance(vhf_transform, Mapping)
        and vhf_transform.get("ready") is True
        and isinstance(composition, Mapping)
        and composition.get("ready") is True
    )
    if not ready:
        return _blocked(
            vehicle=vehicle,
            track_scene_set=track_root,
            output_dir=out,
            blockers=blockers or ["playable-scene-bootstrap:not-ready"],
            archive_sources=archive_sources,
            admission=admission,
            vhf_transform=vhf_transform,
            composition=composition,
        )

    result = {
        "format": FORMAT,
        "version": 1,
        "status": "ready",
        "ready": True,
        "scene_set_ready": True,
        "vehicle": vehicle,
        "track_scene_set": str(track_root),
        "blocking_reasons": [],
        "archive_sources": archive_sources,
        "stages": {
            "vehicle_material_admission": dict(admission),
            "vehicle_vhf_body_world_transform": dict(vhf_transform),
            "scene_composition": dict(composition),
        },
        "artifacts": {
            "vehicle_material_admission": str(admission_dir / "admission.json"),
            "vehicle_material_slice_set": str(admission_dir / "material_slice_set.json"),
            "vehicle_material_slice_set_with_vhf_transform": str(transformed_slice_set),
            "vehicle_vhf_body_world_transform": str(vhf_transform_path),
            "scene_set_dir": str(scene_dir),
            "scene_composition": str(scene_dir / "playable_scene_composition.json"),
        },
        "boundary": {
            "canonical_bff_selection_is_exact_basename": True,
            "archive_order_is_selection_authority": False,
            "manual_vehicle_material_slice_handoff_required": False,
            "manual_vehicle_bff_path_handoff_required": False,
            "phase533_complete_body_admission_required": True,
            "phase645_vhf_body_world_transform_required": True,
            "vhf_body_world_transform_consumed": True,
            "phase643_composite_scene_consumed": True,
            "track_and_vehicle_share_one_native_scene_set": True,
            "persistent_BODY_pose_consumed": False,
            "phase700_runtime_pose_handoff_consumed": False,
            "dynamic_vehicle_world_transform_claimed": False,
        },
    }
    _write(out / "playable_scene_bootstrap.json", result)
    return result
