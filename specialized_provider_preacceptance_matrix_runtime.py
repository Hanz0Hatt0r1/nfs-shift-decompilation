"""Source-backed pre-acceptance matrix construction contract.

Phase 484 models the part of FUN_007b3820 that rebuilds the logical solver
matrix before any provider +0x14 acceptance test runs.
"""
from __future__ import annotations

from typing import Any

FORMAT = "SHIFT.SpecializedProviderPreAcceptanceMatrixRuntime/1"

MATRIX_BUILD = {
    "function": "FUN_007b3820",
    "scalar_count_source": "FUN_007b1b60(param_1)",
    "scalar_count_destination": "physics_system+0x34",
    "matrix_pool_allocation": {
        "allocator": "FUN_00638340",
        "size": "scalar_count * scalar_count * 8",
        "flags": 7,
        "destination": "physics_system+0x38",
    },
    "row_pointer_allocation": {
        "allocator": "FUN_008868d0",
        "size": "scalar_count * 4",
        "destination": "physics_system+0x3c",
    },
    "row_pointer_formula": (
        "row_pointer[row] = matrix_base + scalar_count * row * 8"
    ),
    "initialization": {
        "function": "FUN_007b2010",
        "arguments": (
            "physics_system",
            "physics_system+0x3c",
            "physics_system+0x34",
        ),
        "matrix_action": "zero every matrix double",
        "body_action": "FUN_007ba2b0(body, row_pointer_table)",
    },
    "acceptance": {
        "first_provider_slot": 0,
        "function": "vtable +0x14",
        "argument": "physics_system+0x3c",
    },
}


def build_matrix_construction_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "contract": dict(MATRIX_BUILD),
        "order": [
            "derive scalar count with FUN_007b1b60",
            "allocate scalar_count^2 doubles for matrix pool",
            "allocate scalar_count row pointers",
            "populate contiguous row pointers",
            "FUN_007b2010 zeroes matrix and populates per-BODY contributions",
            "provider vtable +0x14 acceptance receives current row-pointer table",
        ],
        "domain": {
            "matrix": "pre-selection logical matrix storage",
            "provider_workspace": "not yet rebound",
            "provider_output": "not yet rebound",
        },
        "status": "source-backed-preacceptance-matrix-build",
        "limitations": [
            "FUN_007ba2b0 body contribution semantics remain opaque here.",
            "This phase does not infer which exact matrix cells each body/constraint contributes.",
            "The matrix is rebuilt before provider selection; later provider fixed workspace is a separate storage domain.",
        ],
    }


def validate_matrix_construction_contract() -> dict[str, Any]:
    errors: list[str] = []

    if MATRIX_BUILD["scalar_count_destination"] != "physics_system+0x34":
        errors.append("scalar-count-destination-mismatch")
    if MATRIX_BUILD["matrix_pool_allocation"]["size"] != (
        "scalar_count * scalar_count * 8"
    ):
        errors.append("matrix-allocation-size-mismatch")
    if MATRIX_BUILD["row_pointer_allocation"]["size"] != "scalar_count * 4":
        errors.append("row-pointer-allocation-size-mismatch")
    if "row_pointer[row]" not in MATRIX_BUILD["row_pointer_formula"]:
        errors.append("row-pointer-formula-mismatch")
    if MATRIX_BUILD["initialization"]["function"] != "FUN_007b2010":
        errors.append("matrix-init-function-mismatch")
    if MATRIX_BUILD["acceptance"]["argument"] != "physics_system+0x3c":
        errors.append("acceptance-argument-mismatch")

    return {
        "format": "SHIFT.SpecializedProviderPreAcceptanceMatrixValidation/1",
        "version": 1,
        "ready": not errors,
        "errors": errors,
    }


__all__ = [
    "FORMAT",
    "MATRIX_BUILD",
    "build_matrix_construction_contract",
    "validate_matrix_construction_contract",
]
