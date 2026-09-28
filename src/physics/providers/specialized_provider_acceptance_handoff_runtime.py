"""Model the acceptance-to-provider storage handoff boundary.

Phase 483 makes explicit that provider acceptance consumes the currently bound
physics-system row table before provider selection/rebind. After acceptance,
vtable accessors replace the matrix-row, output and auxiliary storage pointers
used by the frame runtime.

This contract keeps pre-selection logical storage and provider fixed storage
as distinct evidence domains.
"""
from __future__ import annotations

from typing import Any

from specialized_provider_runtime import get_provider
from specialized_provider_storage_runtime import get_storage_layout

FORMAT = "SHIFT.SpecializedProviderAcceptanceProviderHandoffRuntime/1"

PRE_SELECTION = {
    "matrix_rows_pointer": "physics_system+0x3c",
    "rhs_pointer": "physics_system+0x40",
    "scalar_count": "physics_system+0x34",
    "acceptance_vtable_offset": 0x14,
}

POST_SELECTION = {
    "provider_pointer": "physics_system+0x48",
    "row_pointer_accessor": 0x0C,
    "output_vector_accessor": 0x04,
    "factor_workspace_accessor": 0x08,
    "workspace_size_accessor": 0x2C,
    "row_pointer_destination": "physics_system+0x3c",
    "output_vector_destination": "physics_system+0x40",
    "factor_workspace_destination": "physics_system+0x44",
    "workspace_size_destination": "per-body+0xa8",
}


def build_provider_handoff(provider_id: int) -> dict[str, Any]:
    provider = get_provider(provider_id)
    layout = get_storage_layout(provider_id)
    return {
        "provider_id": provider_id,
        "provider_vtable": hex(provider.vtable_address),
        "acceptance": {
            "function": hex(provider.acceptance_function),
            "input_rows": PRE_SELECTION["matrix_rows_pointer"],
            "input_scalar_count": PRE_SELECTION["scalar_count"],
            "vtable_offset": hex(PRE_SELECTION["acceptance_vtable_offset"]),
        },
        "rebind": {
            "provider_pointer": POST_SELECTION["provider_pointer"],
            "row_pointer": {
                "vtable_offset": hex(POST_SELECTION["row_pointer_accessor"]),
                "destination": POST_SELECTION["row_pointer_destination"],
                "static_base": hex(layout.row_pointer_base),
            },
            "output_vector": {
                "vtable_offset": hex(POST_SELECTION["output_vector_accessor"]),
                "destination": POST_SELECTION["output_vector_destination"],
                "static_base": hex(layout.output_vector_base),
            },
            "factor_workspace": {
                "vtable_offset": hex(POST_SELECTION["factor_workspace_accessor"]),
                "destination": POST_SELECTION["factor_workspace_destination"],
                "static_base": hex(layout.factor_workspace_base),
            },
            "workspace_size": {
                "vtable_offset": hex(POST_SELECTION["workspace_size_accessor"]),
                "destination": POST_SELECTION["workspace_size_destination"],
                "doubles": layout.factor_workspace_doubles,
            },
        },
        "scalar_count": layout.scalar_count,
    }


def build_handoff_boundary_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "pre_selection": dict(PRE_SELECTION),
        "providers": [
            build_provider_handoff(0),
            build_provider_handoff(1),
        ],
        "sequence": [
            "current physics-system row table is evaluated by provider +0x14 acceptance",
            "accepted provider replaces physics-system +0x3c/+0x40/+0x44 bindings through +0x0c/+0x04/+0x08",
            "workspace-size +0x2c result is propagated to per-body +0xa8",
            "later FUN_007b3f40 provider cleanup +0x20 and solve +0x18 operate on fixed provider global storage",
        ],
        "domain_separation": {
            "acceptance_input": "pre-selection physics-system matrix row table",
            "provider_factor_workspace": "post-selection provider static packed workspace",
            "provider_output_vector": "post-selection provider static output vector",
            "logical_identity": "not assumed equal across the two domains",
        },
        "limitations": [
            "The handoff contract records pointer rebinding, not the allocator implementation behind the returned storage.",
            "Acceptance success is independent from provider numerical factorization semantics.",
            "No claim is made that the pre-selection logical matrix and provider packed workspace share a cell-for-cell layout.",
        ],
        "status": "source-backed-acceptance-provider-handoff",
    }


def validate_handoff_boundary() -> dict[str, Any]:
    errors: list[str] = []

    for provider_id in (0, 1):
        provider = get_provider(provider_id)
        if provider.acceptance_function == provider.solve_function:
            errors.append(
                f"provider-{provider_id}-acceptance-solve-collision"
            )
        layout = get_storage_layout(provider_id)
        if layout.factor_workspace_base >= layout.output_vector_base:
            errors.append(
                f"provider-{provider_id}-workspace-before-output-boundary-invalid"
            )

    if PRE_SELECTION["matrix_rows_pointer"] != "physics_system+0x3c":
        errors.append("preselection-row-pointer-boundary-mismatch")
    if POST_SELECTION["provider_pointer"] != "physics_system+0x48":
        errors.append("provider-pointer-boundary-mismatch")

    return {
        "format": "SHIFT.SpecializedProviderAcceptanceProviderHandoffValidation/1",
        "version": 1,
        "ready": not errors,
        "errors": errors,
    }


__all__ = [
    "FORMAT",
    "PRE_SELECTION",
    "POST_SELECTION",
    "build_provider_handoff",
    "build_handoff_boundary_contract",
    "validate_handoff_boundary",
]
