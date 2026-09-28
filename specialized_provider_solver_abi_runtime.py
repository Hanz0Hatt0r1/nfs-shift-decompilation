"""Source-backed ABI and global-state contract for specialized provider solvers.

Phase 473 records the observed C-level entry shape of FUN_007c7200 and
FUN_007cdfc0 and contrasts it with the builtin solver's stack-based ABI.
"""
from __future__ import annotations

from typing import Any

from specialized_provider_runtime import get_provider
from specialized_provider_storage_runtime import get_storage_layout
from specialized_provider_row_storage_runtime import get_row_pointers

FORMAT = "SHIFT.SpecializedProviderSolverABIRuntime/1"

PROVIDER_SOLVER_ABI = {
    0: {
        "function": "FUN_007c7200",
        "signature": "void FUN_007c7200(void)",
        "abi": "void(void)",
        "global_state": True,
    },
    1: {
        "function": "FUN_007cdfc0",
        "signature": "void FUN_007cdfc0(void)",
        "abi": "void(void)",
        "global_state": True,
    },
}

BUILTIN_SOLVER_ABI = {
    "function": "FUN_007b0f20",
    "signature": "void FUN_007b0f20(void *solver_state, void **row_pointer_table, double *rhs, uint32 scalar_count)",
    "abi": "__thiscall",
    "stack_offsets": {
        "solver_state": "+0x04",
        "row_pointer_table": "+0x08",
        "rhs": "+0x0c",
        "scalar_count": "+0x10",
    },
}


def get_provider_solver_abi(provider_id: int) -> dict[str, Any]:
    try:
        return dict(PROVIDER_SOLVER_ABI[provider_id])
    except KeyError as exc:
        raise ValueError(f"unsupported provider id: {provider_id}") from exc


def build_global_state_contract(provider_id: int) -> dict[str, Any]:
    provider = get_provider(provider_id)
    layout = get_storage_layout(provider_id)
    pointers = get_row_pointers(provider_id)
    abi = get_provider_solver_abi(provider_id)

    return {
        "provider_id": provider_id,
        "function": abi["function"],
        "signature": abi["signature"],
        "abi": abi["abi"],
        "global_state": abi["global_state"],
        "state_regions": {
            "row_pointer_table": {
                "base": hex(layout.row_pointer_base),
                "entries": layout.scalar_count,
                "pointers": [hex(value) for value in pointers],
            },
            "factor_workspace": {
                "base": hex(layout.factor_workspace_base),
                "doubles": layout.factor_workspace_doubles,
                "bytes": layout.factor_workspace_bytes,
            },
            "output_vector": {
                "base": hex(layout.output_vector_base),
                "doubles": layout.output_vector_doubles,
                "bytes": layout.output_vector_bytes,
            },
        },
        "solve_function_address": hex(provider.solve_function),
    }


def validate_provider_solver_abi(provider_id: int) -> dict[str, Any]:
    errors: list[str] = []

    abi = get_provider_solver_abi(provider_id)
    provider = get_provider(provider_id)

    if abi["function"] != f"FUN_{provider.solve_function:08x}":
        errors.append(
            "function-name-address-contract-mismatch"
        )

    if abi["abi"] != "void(void)":
        errors.append("unexpected-provider-solver-abi")

    if abi["global_state"] is not True:
        errors.append("provider-solver-not-marked-global-state")

    layout = get_storage_layout(provider_id)
    pointers = get_row_pointers(provider_id)
    if len(pointers) != layout.scalar_count:
        errors.append("row-pointer-count-mismatch")

    return {
        "format": "SHIFT.SpecializedProviderSolverABIValidation/1",
        "version": 1,
        "provider_id": provider_id,
        "ready": not errors,
        "errors": errors,
    }


def build_solver_abi_contract() -> dict[str, Any]:
    providers: list[dict[str, Any]] = []
    for provider_id in (0, 1):
        entry = build_global_state_contract(provider_id)
        entry["validation"] = validate_provider_solver_abi(provider_id)
        providers.append(entry)

    return {
        "format": FORMAT,
        "version": 1,
        "providers": providers,
        "builtin_solver": dict(BUILTIN_SOLVER_ABI),
        "contrast": {
            "provider": "void(void), fixed global storage",
            "builtin": "__thiscall, explicit solver-state/row-table/RHS/scalar arguments",
        },
        "capture_implication": {
            "provider_entry": "read fixed provider storage regions; do not decode provider arguments from stack",
            "builtin_entry": "decode call stack according to FUN_007b0f20 ABI",
        },
        "limitations": [
            "The ABI contract is source-backed and does not assign a C++ class identity.",
            "Global state location is represented by fixed storage addresses already recovered in earlier phases.",
            "No physical matrix semantics are inferred from the function signature.",
        ],
        "status": "source-backed-specialized-provider-solver-abi",
    }


__all__ = [
    "FORMAT",
    "PROVIDER_SOLVER_ABI",
    "BUILTIN_SOLVER_ABI",
    "get_provider_solver_abi",
    "build_global_state_contract",
    "validate_provider_solver_abi",
    "build_solver_abi_contract",
]
