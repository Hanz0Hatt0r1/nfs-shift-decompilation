"""Join the source-backed pre-PhysX construction and provider handoff contracts.

Phase 502 is a composition/consistency layer. It validates that the already
recovered SDF construction plan, pre-acceptance storage, provider selector,
provider vtables and post-selection rebinding agree on their shared offsets and
dimensions. It does not identify PhysX SDK classes or infer runtime acceptance.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from physics_constraint_construction_runtime import (
    build_prephysx_construction_plan,
)
from rigid_body_sdf_runtime import describe_sdf_pre_physx_build
from physics_provider_backend_runtime import (
    build_fun_007b3820_backend_contract,
)
from specialized_provider_acceptance_handoff_runtime import (
    build_handoff_boundary_contract,
    validate_handoff_boundary,
)
from specialized_provider_dispatch_boundary_runtime import (
    build_dispatch_boundary_contract,
    validate_dispatch_boundary,
)
from specialized_provider_runtime import get_provider
from specialized_provider_storage_runtime import get_storage_layout
from specialized_provider_vtable_lifecycle_runtime import (
    build_vtable_lifecycle_contract,
    validate_vtable_contract,
)

FORMAT = "SHIFT.PrePhysXProviderHandoffRuntime/1"


def _component_errors(report: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    for name in ("construction", "sdf_prephysx", "acceptance", "dispatch", "vtable"):
        component = report.get(name) or {}
        if component.get("ready") is False:
            errors.append(f"{name}-not-ready")
        validation = component.get("validation")
        if isinstance(validation, Mapping) and validation.get("ready") is False:
            errors.append(f"{name}-validation-not-ready")
    for provider in report.get("providers") or []:
        if provider.get("validation", {}).get("ready") is False:
            errors.append(
                f"provider-{provider.get('provider_id')}-validation-not-ready"
            )
    return errors


def _provider_compatibility(solver_scalar_count: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for provider_id in (0, 1):
        layout = get_storage_layout(provider_id)
        provider = get_provider(provider_id)
        rows.append({
            "provider_id": provider_id,
            "scalar_count": layout.scalar_count,
            "workspace_doubles": layout.factor_workspace_doubles,
            "same_solver_dimension": layout.scalar_count == solver_scalar_count,
            "selection_probe_required": True,
            "provider_pointer": "physics_system+0x48",
            "vtable": hex(provider.vtable_address),
        })
    return rows


def build_prephysx_provider_handoff_contract(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    construction = build_prephysx_construction_plan(report)
    sdf_prephysx = describe_sdf_pre_physx_build(report)
    backend = build_fun_007b3820_backend_contract()
    acceptance = build_handoff_boundary_contract()
    acceptance_validation = validate_handoff_boundary()
    dispatch = build_dispatch_boundary_contract()
    dispatch_validation = validate_dispatch_boundary()
    vtable = build_vtable_lifecycle_contract()
    vtable_provider_validation = [
        validate_vtable_contract(provider_id)
        for provider_id in (0, 1)
    ]

    # Keep validation adjacent to the component that owns it.
    acceptance = dict(acceptance)
    acceptance["validation"] = acceptance_validation
    dispatch = dict(dispatch)
    dispatch["validation"] = dispatch_validation
    vtable = dict(vtable)
    for provider, validation in zip(
        vtable.get("providers") or [],
        vtable_provider_validation,
    ):
        provider["validation"] = validation

    solver_scalar_count = int(
        (construction.get("counts") or {}).get("solver_scalar_count", 0)
    )
    compatibility = _provider_compatibility(solver_scalar_count)
    compatible = [
        row["provider_id"]
        for row in compatibility
        if row["same_solver_dimension"]
    ]

    errors = _component_errors({
        "construction": construction,
        "sdf_prephysx": sdf_prephysx,
        "acceptance": acceptance,
        "dispatch": dispatch,
        "vtable": vtable,
    })
    if (
        construction.get("ready") is True
        and sdf_prephysx.get("ready") is True
        and construction.get("counts", {}).get("solver_scalar_count")
        != sdf_prephysx.get("counts", {}).get("solver_scalar_nodes")
    ):
        errors.append("construction-sdf-scalar-count-mismatch")

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if not errors else "blocked",
        "ready": not errors,
        "construction": construction,
        "sdf_prephysx": sdf_prephysx,
        "provider_backend": backend,
        "acceptance": acceptance,
        "dispatch": dispatch,
        "vtable": vtable,
        "providers": compatibility,
        "selection": {
            "solver_scalar_count": solver_scalar_count,
            "same_dimension_candidates": compatible,
            "generic_fallback_available": True,
            "runtime_acceptance_required": True,
            "runtime_acceptance_argument": "physics_system+0x3c",
        },
        "boundary": {
            "pre_selection_matrix_rows": "physics_system+0x3c",
            "pre_selection_rhs": "physics_system+0x40",
            "pre_selection_scalar_count": "physics_system+0x34",
            "provider_state": "physics_system+0x48",
            "provider_row_pointer": "physics_system+0x3c",
            "provider_output_vector": "physics_system+0x40",
            "provider_factor_workspace": "physics_system+0x44",
            "provider_workspace_size": "per-body+0xa8",
        },
        "errors": list(dict.fromkeys(errors)),
        "limitations": [
            "Provider compatibility is dimension-based only; +0x14 acceptance remains a runtime predicate.",
            "The pre-selection logical matrix and provider packed workspace remain separate storage domains.",
            "Concrete PhysX/provider C++ class identities remain unresolved.",
            "No physical units or numerical solver equivalence are inferred.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the source-backed pre-PhysX/provider handoff contract"
    )
    parser.add_argument("input", type=Path, help="parsed RigidBodySDFRuntime JSON")
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()
    report = json.loads(args.input.read_text(encoding="utf-8"))
    contract = build_prephysx_provider_handoff_contract(report)
    payload = json.dumps(contract, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0 if contract["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["FORMAT", "build_prephysx_provider_handoff_contract"]
