"""High-level fail-closed native vehicle resource build from offline SHIFT assets.

This stage deliberately separates resource readiness from runtime compatibility.
The generic vehicle physics manifest is valid for any source-backed vehicle
resource set accepted by the offline pipeline.  The current native runtime
physics compatibility adapter remains BMW M3 E36-only until its contract is
proven for additional vehicles.  The source-backed participant registry ABI is
also materialized here without inventing a concrete runtime participant identity.
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
from offline_native_resource_handoff import (
    BMW_COMPAT_FORMAT,
    PHYSICS_MANIFEST_FORMAT,
    build_bmw_m3_runtime_compat_manifest,
    build_vehicle_physics_resource_manifest,
)

FORMAT = "SHIFT.OfflineNativeVehicleBuild/1"


def _load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_native_vehicle(
    catalog: Mapping[str, Any],
    bootstrap: Mapping[str, Any],
    physics_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the strongest vehicle resource artifact supported by current proof."""
    generic = build_vehicle_physics_resource_manifest(catalog, bootstrap, physics_bundle)
    compatibility = build_bmw_m3_runtime_compat_manifest(generic)
    participant_boundary = build_native_physics_participant_boundary()

    resource_ready = generic.get("ready") is True
    runtime_physics_contract_ready = compatibility.get("ready") is True
    participant_structural_ready = participant_boundary.get("ready") is True

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

    if not resource_ready:
        status = "resource-blocked"
    elif not participant_structural_ready:
        status = "participant-structural-blocked"
    elif runtime_physics_contract_ready:
        status = "runtime-physics-contract-ready"
    else:
        status = "resource-ready-runtime-physics-blocked"

    return {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "resource_ready": resource_ready,
        "participant_structural_ready": participant_structural_ready,
        "runtime_physics_contract_ready": runtime_physics_contract_ready,
        "native_vehicle_runtime_ready": False,
        "vehicle": bootstrap.get("vehicle"),
        "source_archive": generic.get("source_archive"),
        "blocking_reasons": blockers,
        "vehicle_physics_manifest": generic,
        "participant_boundary": participant_boundary,
        "native_physics_compatibility": compatibility,
        "boundary": {
            "generic_resource_manifest_format": PHYSICS_MANIFEST_FORMAT,
            "participant_structural_boundary_format": PARTICIPANT_BOUNDARY_FORMAT,
            "current_runtime_physics_manifest_format": BMW_COMPAT_FORMAT,
            "non_bmw_runtime_compatibility_invented": False,
            "participant_structural_boundary_evaluated": True,
            "participant_runtime_identity_evaluated": False,
            "participant_instance_invented": False,
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
) -> dict[str, Any]:
    """Build and persist generic plus runtime-compatible vehicle artifacts."""
    report = build_native_vehicle(
        _load(catalog_path),
        _load(bootstrap_path),
        _load(physics_bundle_path),
    )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {
        "vehicle_physics_manifest": out / "vehicle_physics_resource_manifest.json",
        "participant_boundary": out / "native_physics_participant_boundary.json",
        "build": out / "native_vehicle_build.json",
    }
    compatibility = report["native_physics_compatibility"]
    if compatibility.get("ready") is True:
        paths["native_physics_manifest"] = out / "native_physics_manifest.json"

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