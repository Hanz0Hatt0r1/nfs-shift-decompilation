"""High-level fail-closed native vehicle resource build from offline SHIFT assets.

This stage deliberately separates resource readiness from runtime compatibility.
The generic vehicle physics manifest is valid for any source-backed vehicle
resource set accepted by the offline pipeline.  The current native runtime
physics compatibility adapter remains BMW M3 E36-only until its contract is
proven for additional vehicles.  The source-backed participant registry ABI is
materialized here without inventing a concrete runtime participant identity.
An optional already-proven runtime participant observation may be joined to that
structural boundary, but input binding and fixed-step scheduling remain separate
runtime gates.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from native_physics_participant_boundary import (
    FORMAT as PARTICIPANT_BOUNDARY_FORMAT,
    build_native_physics_participant_boundary,
)
from native_physics_participant_runtime_evidence import (
    FORMAT as PARTICIPANT_RUNTIME_EVIDENCE_FORMAT,
    build_native_physics_participant_runtime_evidence,
)
from offline_native_resource_handoff import (
    BMW_COMPAT_FORMAT,
    PHYSICS_MANIFEST_FORMAT,
    build_bmw_m3_runtime_compat_manifest,
    build_vehicle_physics_resource_manifest,
)
from selected_archive_materialization import materialize_selected_archive
from typed_physics_resource_materialization import (
    attach_typed_physics_materializations,
)

FORMAT = "SHIFT.OfflineNativeVehicleBuild/1"
ARCHIVE_MATERIALIZATION_FORMAT = "SHIFT.RetailArchiveMaterialization/1"


def _load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _blocked_participant_runtime_evidence(reason: str) -> dict[str, Any]:
    return {
        "format": PARTICIPANT_RUNTIME_EVIDENCE_FORMAT,
        "version": 1,
        "status": "blocked",
        "ready": False,
        "blocking_reasons": [reason],
        "registry_selector_identity_join_proven": False,
        "participant_instance_ready": False,
        "boundary": {
            "native_state_runtime_instance_admission": False,
            "selected_runtime_instance_proven": False,
            "selected_provider_proven": False,
            "numeric_physics_equivalence_proven": False,
        },
    }


def _blocked_archive_materialization(reason: str) -> dict[str, Any]:
    return {
        "format": ARCHIVE_MATERIALIZATION_FORMAT,
        "version": 1,
        "status": "blocked",
        "ready": False,
        "role": "vehicle_primary",
        "blocking_reasons": [reason],
        "path": None,
        "sha256": None,
        "bytes": None,
        "boundary": {
            "exact_selected_occurrence_required": True,
            "basename_fallback_used": False,
            "archive_order_used": False,
            "canonical_retail_identity_claimed_here": False,
        },
    }


def build_native_vehicle(
    catalog: Mapping[str, Any],
    bootstrap: Mapping[str, Any],
    physics_bundle: Mapping[str, Any],
    *,
    typed_closure: Mapping[str, Any] | None = None,
    participant_observation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the strongest vehicle resource artifact supported by current proof."""
    generic = build_vehicle_physics_resource_manifest(catalog, bootstrap, physics_bundle)
    if typed_closure is not None:
        generic = attach_typed_physics_materializations(generic, typed_closure)
    compatibility = build_bmw_m3_runtime_compat_manifest(generic)
    participant_boundary = build_native_physics_participant_boundary()

    resource_ready = generic.get("ready") is True
    runtime_physics_contract_ready = compatibility.get("ready") is True
    participant_structural_ready = participant_boundary.get("ready") is True
    participant_runtime_identity_evaluated = participant_observation is not None

    participant_runtime_evidence: dict[str, Any] | None = None
    if participant_observation is not None:
        if not participant_structural_ready:
            participant_runtime_evidence = _blocked_participant_runtime_evidence(
                "participant-structural-boundary-not-ready"
            )
        else:
            try:
                participant_runtime_evidence = (
                    build_native_physics_participant_runtime_evidence(
                        participant_boundary,
                        participant_observation,
                    )
                )
            except (TypeError, ValueError) as exc:
                participant_runtime_evidence = _blocked_participant_runtime_evidence(
                    f"runtime-evidence-join-error:{type(exc).__name__}:{exc}"
                )

    participant_runtime_identity_ready = bool(
        isinstance(participant_runtime_evidence, Mapping)
        and participant_runtime_evidence.get("ready") is True
        and participant_runtime_evidence.get("participant_instance_ready") is True
        and participant_runtime_evidence.get("registry_selector_identity_join_proven") is True
    )

    blockers: list[str] = []
    if not resource_ready:
        blockers.extend(
            "resource:" + str(reason)
            for reason in generic.get("blocking_reasons") or ["not-ready"]
        )
    if not runtime_physics_contract_ready:
        blockers.extend(
            "runtime-physics:" + str(reason)
            for reason in compatibility.get("blocking_reasons") or ["not-ready"]
        )
    if not participant_structural_ready:
        blockers.extend(
            "participant-boundary:" + str(reason)
            for reason in participant_boundary.get("blocking_reasons") or ["not-ready"]
        )
    blockers = list(dict.fromkeys(blockers))

    runtime_gate_blockers: list[str] = []
    if not runtime_physics_contract_ready:
        runtime_gate_blockers.append("runtime-physics-contract-not-ready")
    if not participant_structural_ready:
        runtime_gate_blockers.append("participant-structural-boundary-not-ready")
    if not participant_runtime_identity_evaluated:
        runtime_gate_blockers.append("participant-runtime-observation-required")
    elif not participant_runtime_identity_ready:
        runtime_reasons = (
            participant_runtime_evidence.get("blocking_reasons")
            if isinstance(participant_runtime_evidence, Mapping)
            else None
        ) or ["not-ready"]
        runtime_gate_blockers.extend(
            "participant-runtime-identity:" + str(reason)
            for reason in runtime_reasons
        )
    runtime_gate_blockers.extend((
        "input-binding-runtime-evidence-required",
        "fixed-step-runtime-evidence-required",
    ))
    runtime_gate_blockers = list(dict.fromkeys(runtime_gate_blockers))

    if not resource_ready:
        status = "resource-blocked"
    elif not participant_structural_ready:
        status = "participant-structural-blocked"
    elif runtime_physics_contract_ready:
        status = "runtime-physics-contract-ready"
    else:
        status = "resource-ready-runtime-physics-blocked"

    materialized_physics_resources: dict[str, dict[str, Any]] = {}
    generic_entries = generic.get("entries") or {}
    if isinstance(generic_entries, Mapping):
        for kind, raw in generic_entries.items():
            if not isinstance(raw, Mapping) or not raw.get("materialized_path"):
                continue
            materialized_physics_resources[str(kind)] = {
                "resource_id": raw.get("resource_id"),
                "path": raw.get("path"),
                "materialized_path": raw.get("materialized_path"),
                "sha256": raw.get("materialized_sha256"),
            }

    return {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "resource_ready": resource_ready,
        "participant_structural_ready": participant_structural_ready,
        "participant_runtime_identity_evaluated": participant_runtime_identity_evaluated,
        "participant_runtime_identity_ready": participant_runtime_identity_ready,
        "runtime_physics_contract_ready": runtime_physics_contract_ready,
        "native_vehicle_runtime_ready": False,
        "vehicle": bootstrap.get("vehicle"),
        "source_archive": generic.get("source_archive"),
        "blocking_reasons": blockers,
        "runtime_gate_blocking_reasons": runtime_gate_blockers,
        "vehicle_physics_manifest": generic,
        "materialized_physics_resources": materialized_physics_resources,
        "participant_boundary": participant_boundary,
        "participant_runtime_evidence": participant_runtime_evidence,
        "native_physics_compatibility": compatibility,
        "boundary": {
            "generic_resource_manifest_format": PHYSICS_MANIFEST_FORMAT,
            "participant_structural_boundary_format": PARTICIPANT_BOUNDARY_FORMAT,
            "participant_runtime_evidence_format": PARTICIPANT_RUNTIME_EVIDENCE_FORMAT,
            "current_runtime_physics_manifest_format": BMW_COMPAT_FORMAT,
            "typed_resource_closure_evaluated": typed_closure is not None,
            "typed_physics_materializations_ready": (
                generic.get("materialized_resources_ready") is True
            ),
            "non_bmw_runtime_compatibility_invented": False,
            "participant_structural_boundary_evaluated": True,
            "participant_runtime_identity_evaluated": participant_runtime_identity_evaluated,
            "participant_runtime_observation_used": participant_observation is not None,
            "participant_instance_invented": False,
            "body_semantics_claimed_by_materialization_handoff": False,
            "input_binding_evaluated": False,
            "fixed_step_schedule_evaluated": False,
            "runtime_execution_claimed": False,
            "missing_resource_synthesis": False,
            "provenance_gate_bypass": False,
        },
    }


def build_native_vehicle_files(
    catalog_path: str | Path,
    bootstrap_path: str | Path,
    physics_bundle_path: str | Path,
    output_dir: str | Path,
    *,
    typed_closure_path: str | Path | None = None,
    participant_observation_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build and persist generic plus runtime-compatible vehicle artifacts."""
    catalog = _load(catalog_path)
    bootstrap = _load(bootstrap_path)
    physics_bundle = _load(physics_bundle_path)
    typed_closure = (
        _load(typed_closure_path)
        if typed_closure_path is not None
        else None
    )
    observation: dict[str, Any] | None = None
    observation_load_error: str | None = None
    observation_path = (
        Path(participant_observation_path)
        if participant_observation_path is not None
        else None
    )
    if observation_path is not None:
        try:
            observation = _load(observation_path)
        except (OSError, ValueError) as exc:
            observation_load_error = (
                f"runtime-observation-load-error:{type(exc).__name__}:{exc}"
            )

    report = build_native_vehicle(
        catalog,
        bootstrap,
        physics_bundle,
        typed_closure=typed_closure,
        participant_observation=observation,
    )

    if observation_path is not None and observation_load_error is not None:
        report["participant_runtime_identity_evaluated"] = True
        report["participant_runtime_identity_ready"] = False
        report["participant_runtime_evidence"] = (
            _blocked_participant_runtime_evidence(observation_load_error)
        )
        report["runtime_gate_blocking_reasons"] = [
            (
                "participant-runtime-identity:" + observation_load_error
                if reason == "participant-runtime-observation-required"
                else reason
            )
            for reason in report.get("runtime_gate_blocking_reasons") or []
        ]
        boundary = dict(report.get("boundary") or {})
        boundary["participant_runtime_identity_evaluated"] = True
        boundary["participant_runtime_observation_used"] = True
        report["boundary"] = boundary

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    archive_materialization: dict[str, Any] | None
    try:
        archive_materialization = materialize_selected_archive(
            catalog,
            bootstrap,
            selected_key="vehicle",
            role="vehicle_primary",
            output_dir=out / "retail-archives",
        )
    except (OSError, ValueError) as exc:
        archive_materialization = _blocked_archive_materialization(
            f"selected-archive-join-error:{type(exc).__name__}:{exc}"
        )

    boundary = dict(report.get("boundary") or {})
    boundary["vehicle_archive_materialization_evaluated"] = (
        archive_materialization is not None
    )
    boundary["vehicle_archive_materialization_ready"] = bool(
        isinstance(archive_materialization, Mapping)
        and archive_materialization.get("ready") is True
    )
    boundary["vehicle_archive_materialization_claims_body_semantics"] = False
    report["boundary"] = boundary
    report["vehicle_archive_materialization"] = archive_materialization

    if isinstance(archive_materialization, Mapping) and archive_materialization.get("ready") is not True:
        archive_blockers = [
            "vehicle-archive-materialization:" + str(reason)
            for reason in archive_materialization.get("blocking_reasons") or ["not-ready"]
        ]
        report["blocking_reasons"] = list(dict.fromkeys(
            list(report.get("blocking_reasons") or []) + archive_blockers
        ))
        report["resource_ready"] = False
        report["status"] = "resource-blocked"

    paths: dict[str, Path] = {
        "vehicle_physics_manifest": out / "vehicle_physics_resource_manifest.json",
        "participant_boundary": out / "native_physics_participant_boundary.json",
        "build": out / "native_vehicle_build.json",
    }
    compatibility = report["native_physics_compatibility"]
    if compatibility.get("ready") is True:
        paths["native_physics_manifest"] = out / "native_physics_manifest.json"
    if isinstance(archive_materialization, Mapping) and archive_materialization.get("ready") is True:
        archive_path = Path(str(archive_materialization.get("path") or ""))
        if archive_path.is_file():
            paths["vehicle_archive"] = archive_path

    paths["vehicle_physics_manifest"].write_text(
        json.dumps(
            report["vehicle_physics_manifest"],
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    paths["participant_boundary"].write_text(
        json.dumps(
            report["participant_boundary"],
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    participant_runtime_evidence = report.get("participant_runtime_evidence")
    if isinstance(participant_runtime_evidence, Mapping):
        participant_runtime_evidence = dict(participant_runtime_evidence)
        provenance = {
            "structural_boundary_sha256": _sha256(paths["participant_boundary"]),
        }
        if observation_path is not None and observation_path.is_file():
            provenance["runtime_observation_sha256"] = _sha256(observation_path)
        participant_runtime_evidence["provenance"] = provenance
        report["participant_runtime_evidence"] = participant_runtime_evidence
        paths["participant_runtime_evidence"] = (
            out / "native_physics_participant_runtime_evidence.json"
        )
        paths["participant_runtime_evidence"].write_text(
            json.dumps(
                participant_runtime_evidence,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ) + "\n",
            encoding="utf-8",
        )

    if "native_physics_manifest" in paths:
        paths["native_physics_manifest"].write_text(
            json.dumps(compatibility, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    persisted = dict(report)
    persisted["artifacts"] = {
        name: {"path": str(path), "sha256": _sha256(path)}
        for name, path in paths.items()
        if name != "build" and path.is_file()
    }
    paths["build"].write_text(
        json.dumps(persisted, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return persisted
