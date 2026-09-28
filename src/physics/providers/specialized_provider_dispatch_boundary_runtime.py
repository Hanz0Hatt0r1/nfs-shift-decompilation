"""Source-backed provider dispatch boundary around FUN_007b3820/FUN_007b3f40.

Phase 476 records the exact transition from provider selection to provider
execution. It keeps selection/rebinding, cleanup, common physics preparation and
provider solve as separate events.
"""
from __future__ import annotations

from typing import Any

from specialized_provider_runtime import get_provider
from specialized_provider_storage_runtime import get_storage_layout
from specialized_provider_vtable_lifecycle_runtime import get_vtable_lifecycle

FORMAT = "SHIFT.SpecializedProviderDispatchBoundaryRuntime/1"

SELECTION = {
    "function": "FUN_007b3820",
    "source_line": 813669,
    "selector_function": "FUN_007d2e70",
    "selector_argument": "provider slot index",
    "provider_state_offset": "+0x48",
    "acceptance_vtable_offset": 0x14,
    "row_pointer_vtable_offset": 0x0C,
    "output_vector_vtable_offset": 0x04,
    "factor_workspace_vtable_offset": 0x08,
    "workspace_size_vtable_offset": 0x2C,
}

EXECUTION = {
    "function": "FUN_007b3f40",
    "source_line": 814057,
    "provider_state_offset": "+0x48",
    "cleanup_vtable_offset": 0x20,
    "solve_vtable_offset": 0x18,
    "builtin_solver": "FUN_007b0f20",
    "builtin_state": "+0x4c",
}

COMMON_PREP_STAGES = (
    "FUN_007b3ed0",
    "FUN_007bb8d0 per BODY",
    "FUN_007bc680 per BODY",
    "FUN_007ba570 per BODY",
    "constraint relation updates",
)


def build_provider_selection_boundary() -> dict[str, Any]:
    return {
        "function": SELECTION["function"],
        "source_line": SELECTION["source_line"],
        "selector_function": SELECTION["selector_function"],
        "provider_candidates": [
            {
                "slot": provider_id,
                "global_slot": get_provider(provider_id).selector_global,
                "vtable": hex(get_provider(provider_id).vtable_address),
                "scalar_count": get_storage_layout(provider_id).scalar_count,
            }
            for provider_id in (0, 1)
        ],
        "state_rebind": {
            "provider_pointer": SELECTION["provider_state_offset"],
            "row_pointer": "physics_system+0x3c",
            "output_vector": "physics_system+0x40",
            "factor_workspace": "physics_system+0x44",
            "workspace_size": "per-body +0xa8",
        },
        "vtable_offsets": {
            "acceptance": hex(SELECTION["acceptance_vtable_offset"]),
            "row_pointer": hex(SELECTION["row_pointer_vtable_offset"]),
            "output_vector": hex(SELECTION["output_vector_vtable_offset"]),
            "factor_workspace": hex(SELECTION["factor_workspace_vtable_offset"]),
            "workspace_size": hex(SELECTION["workspace_size_vtable_offset"]),
        },
    }


def build_provider_execution_boundary() -> dict[str, Any]:
    return {
        "function": EXECUTION["function"],
        "source_line": EXECUTION["source_line"],
        "provider_pointer": EXECUTION["provider_state_offset"],
        "provider_path": [
            {
                "event": "provider-cleanup",
                "vtable_offset": hex(EXECUTION["cleanup_vtable_offset"]),
            },
            {
                "event": "common-preparation",
                "calls": list(COMMON_PREP_STAGES),
            },
            {
                "event": "per-scalar-reset-dispatch",
                "function": "FUN_007b2210",
                "provider_vtable_offset": "0x1c",
                "selector": "param_1",
            },
            {
                "event": "provider-solve",
                "vtable_offset": hex(EXECUTION["solve_vtable_offset"]),
            },
        ],
        "builtin_path": {
            "condition": "provider pointer is null",
            "solver": EXECUTION["builtin_solver"],
            "solver_state": EXECUTION["builtin_state"],
        },
    }


def validate_dispatch_boundary() -> dict[str, Any]:
    errors: list[str] = []

    for provider_id in (0, 1):
        lifecycle = get_vtable_lifecycle(provider_id)
        provider = get_provider(provider_id)

        if lifecycle.slots.get(0x18) != provider.solve_function:
            errors.append(
                f"provider-{provider_id}-solve-slot-mismatch"
            )
        if lifecycle.slots.get(0x20) != lifecycle.cleanup_function:
            errors.append(
                f"provider-{provider_id}-cleanup-slot-mismatch"
            )

    if SELECTION["acceptance_vtable_offset"] != 0x14:
        errors.append("selection-acceptance-offset-mismatch")
    if EXECUTION["cleanup_vtable_offset"] != 0x20:
        errors.append("execution-cleanup-offset-mismatch")
    if EXECUTION["solve_vtable_offset"] != 0x18:
        errors.append("execution-solve-offset-mismatch")

    return {
        "format": "SHIFT.SpecializedProviderDispatchBoundaryValidation/1",
        "version": 1,
        "ready": not errors,
        "errors": errors,
    }


def build_dispatch_boundary_contract() -> dict[str, Any]:
    validation = validate_dispatch_boundary()
    return {
        "format": FORMAT,
        "version": 1,
        "selection": build_provider_selection_boundary(),
        "execution": build_provider_execution_boundary(),
        "validation": validation,
        "source_order": [
            "FUN_007b3820 provider selection/rebind",
            "provider pointer stored at physics_system+0x48",
            "FUN_007b3f40 provider-cleanup +0x20 when provider is active",
            "common body/constraint preparation",
            "provider-solve +0x18 when provider is active",
            "otherwise builtin FUN_007b0f20",
        ],
        "interpretation": {
            "provider_cleanup": "provider storage cleanup performed at solve orchestration entry",
            "provider_solve": "parameterless provider function operating on fixed global state",
            "reset_slot_+0x1c": "per-scalar reset delegated by FUN_007b2210 before provider solve",
        },
        "limitations": [
            "This contract records dispatch order and storage boundaries, not the numeric provider algorithm.",
            "The common preparation calls are source identifiers only; their full semantics remain outside this phase.",
            "No C++ provider class hierarchy or physical matrix meaning is inferred.",
        ],
        "status": "source-backed-provider-dispatch-boundary",
    }


__all__ = [
    "FORMAT",
    "SELECTION",
    "EXECUTION",
    "COMMON_PREP_STAGES",
    "build_provider_selection_boundary",
    "build_provider_execution_boundary",
    "validate_dispatch_boundary",
    "build_dispatch_boundary_contract",
]
