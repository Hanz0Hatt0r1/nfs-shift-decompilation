"""Exact scalar-reset dispatcher used by FUN_007b3f40.

Phase 482 reconstructs FUN_007b2210 separately from the outer execution
sequence. The function resets one scalar index. Builtin mode clears the logical
matrix row/column and RHS cell and restores the diagonal to 1.0. Provider mode
delegates the same selector to vtable +0x1c.
"""
from __future__ import annotations

from typing import Any

FORMAT = "SHIFT.SpecializedProviderScalarResetRuntime/1"

FUNCTION = {
    "name": "FUN_007b2210",
    "signature": "void __thiscall FUN_007b2210(void *this,int param_1)",
    "selector": "param_1",
}

BUILTIN_OPERATION = {
    "row_zero": {
        "loop_domain": "0..scalar_count-1",
        "address": "row_pointer[param_1][index]",
    },
    "column_zero": {
        "loop_domain": "0..scalar_count-1",
        "address": "row_pointer[index][param_1]",
    },
    "diagonal": {
        "address": "row_pointer[param_1][param_1]",
        "value": "1.0",
    },
    "rhs": {
        "address": "rhs[param_1]",
        "value": "0.0",
    },
}

PROVIDER_OPERATION = {
    "provider_pointer": "physics_system+0x48",
    "vtable_offset": 0x1C,
    "selector": "param_1",
    "dispatch": "provider vtable +0x1c(selector)",
}


def build_scalar_reset_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "function": dict(FUNCTION),
        "builtin": dict(BUILTIN_OPERATION),
        "provider": dict(PROVIDER_OPERATION),
        "provider_execution": {
            "condition": "physics_system+0x48 != 0",
            "callee": "provider reset function",
            "selector_propagation": True,
        },
        "source_call_count": 6,
        "source_call_sites": [
            {
                "source_line": 814124,
                "group": "JOINT/HINGE",
                "width": 3,
            },
            {
                "source_line": 814138,
                "group": "JOINT/HINGE_OR_SECONDARY",
                "width": 2,
            },
            {
                "source_line": 814150,
                "group": "BAR",
                "width": 1,
            },
        ],
        "semantics": {
            "selector": "scalar index supplied by caller",
            "provider": "delegates reset of the selected scalar to vtable +0x1c",
            "builtin": "symmetric row+column clear, diagonal seed and RHS clear",
        },
        "limitations": [
            "The selector's semantic ownership remains source-derived; it is not independently renamed as a matrix pivot.",
            "Provider reset internals remain represented by the already recovered reset profiles.",
            "No constraint coefficient meaning is assigned to the reset storage.",
        ],
        "status": "source-backed-specialized-provider-scalar-reset",
    }


def validate_scalar_reset_contract() -> dict[str, Any]:
    errors: list[str] = []

    if FUNCTION["signature"] != (
        "void __thiscall FUN_007b2210(void *this,int param_1)"
    ):
        errors.append("signature-mismatch")

    if PROVIDER_OPERATION["vtable_offset"] != 0x1C:
        errors.append("provider-reset-vtable-offset-mismatch")

    if len(build_scalar_reset_contract()["source_call_sites"]) != 3:
        errors.append("unexpected-callsite-group-count")

    if int(build_scalar_reset_contract()["source_call_count"]) != 6:
        errors.append("unexpected-source-call-count")

    return {
        "format": "SHIFT.SpecializedProviderScalarResetValidation/1",
        "version": 1,
        "ready": not errors,
        "errors": errors,
    }


__all__ = [
    "FORMAT",
    "FUNCTION",
    "BUILTIN_OPERATION",
    "PROVIDER_OPERATION",
    "build_scalar_reset_contract",
    "validate_scalar_reset_contract",
]
