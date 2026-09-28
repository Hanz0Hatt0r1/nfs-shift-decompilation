"""Build a complete vehicle-BFF to pre-PhysX/provider handoff manifest.

This is an orchestration layer over the canonical vehicle physics bundle
extractor and the Phase 502 source-backed provider handoff contract. It keeps
resource extraction, parsed asset graph and pre-PhysX/provider validation as
separate nested evidence domains.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from vehicle_physics_bundle import extract_bundle
from prephysx_provider_handoff_runtime import build_prephysx_provider_handoff_contract
from vehicle_physics_participant_gate_runtime import build_vehicle_physics_participant_gate

FORMAT = "SHIFT.VehiclePhysicsPrePhysXHandoff/1"


def build_vehicle_physics_handoff(
    bff_path: str | Path,
    output_dir: str | Path,
    *,
    strict: bool = False,
) -> dict[str, Any]:
    bff_path = Path(bff_path)
    output_dir = Path(output_dir)    participant_gate = build_vehicle_physics_participant_gate()
    participant_registry_update = build_physics_participant_registry_update()
    bundle = extract_bundle(
        bff_path,
        output_dir,
        strict=strict,
    )

    profile = bundle.get("profile") or {}
    details = profile.get("details")
    if not isinstance(details, Mapping):
        return {
            "format": FORMAT,
            "version": 1,
            "status": "blocked",
            "ready": False,
            "bundle": bundle,
            "prephysx_provider_handoff": None,
            "participant_gate": participant_gate,
            "errors": ["vehicle-physics-profile-details-missing"],
        }

    sdf_report = details.get("sdf")
    if not isinstance(sdf_report, Mapping):
        return {
            "format": FORMAT,
            "version": 1,
            "status": "blocked",
            "ready": False,
            "bundle": bundle,
            "prephysx_provider_handoff": None,
            "participant_gate": participant_gate,
            "errors": ["sdf-report-missing-from-vehicle-profile"],
        }

    handoff = build_prephysx_provider_handoff_contract(sdf_report)
    ready = bool(bundle.get("ready")) and bool(handoff.get("ready"))
    errors = list(bundle.get("profile", {}).get("blockers") or [])
    errors.extend(handoff.get("errors") or [])

    output_dir.mkdir(parents=True, exist_ok=True)
    handoff_path = output_dir / "prephysx_provider_handoff.json"
    handoff_path.write_text(
        json.dumps(handoff, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    summary = handoff.get("selection") or {}
    counts = handoff.get("construction", {}).get("counts") or {}
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "ready-with-warnings" if bundle.get("ready") else "blocked",
        "ready": ready,
        "source": {
            "bff": str(bff_path),
            "bytes": bff_path.stat().st_size if bff_path.is_file() else None,
        },
        "bundle": bundle,
        "prephysx_provider_handoff": handoff,
        "participant_gate": participant_gate,
        "outputs": {
            "vehicle_physics_asset_graph": str(bundle.get("physics_profile")),
            "prephysx_provider_handoff": str(handoff_path),
        },
        "summary": {
            "solver_scalar_count": int(summary.get("solver_scalar_count", 0)),
            "same_dimension_provider_candidates": list(
                summary.get("same_dimension_candidates") or []
            ),
            "generic_fallback_available": bool(
                summary.get("generic_fallback_available")
            ),
            "body_count": int(counts.get("bodies", 0)),
            "runtime_constraint_count": int(counts.get("runtime_constraints", 0)),
            "sdf_body_count": int((bundle.get("profile", {}).get("summary") or {}).get("sdf_bodies", 0)),
            "participant_gate_ready": bool(participant_gate.get("ready")),
        },
        "errors": list(dict.fromkeys(errors)),
        "limitations": [
            "This command provides static/resource handoff only; no runtime provider acceptance is observed.",
            "Provider candidates are dimension-compatible candidates, not selected retail backends.",
            "No PhysX/provider C++ class identity or numeric equivalence is inferred.",
            "Participant creation/load ordering is source-backed; the runtime participant instance still requires capture.",
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the complete vehicle-BFF to pre-PhysX/provider handoff manifest"
    )
    parser.add_argument("bff", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)

    report = build_vehicle_physics_handoff(
        args.bff,
        args.output,
        strict=args.strict,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "vehicle_physics_handoff.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "solver_scalar_count": report["summary"]["solver_scalar_count"],
        "same_dimension_provider_candidates": report["summary"]["same_dimension_provider_candidates"],
        "errors": report["errors"],
        "participant_gate_ready": report["summary"]["participant_gate_ready"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["FORMAT", "build_vehicle_physics_handoff"]
