"""Source-backed pre-acceptance matrix construction contract.

Phase 484 models the part of FUN_007b3820 that rebuilds the logical solver
matrix before any provider +0x14 acceptance test runs. An optional
SHIFT-MEMORY-SOURCE-SEMANTIC-SUMMARY/1 artifact can independently cross-check
that FUN_008868d0 source argument 0 is the diagnostic-backed allocation-size
role without changing the original source-backed matrix contract.
"""
from __future__ import annotations

from typing import Any

FORMAT = "SHIFT.SpecializedProviderPreAcceptanceMatrixRuntime/1"
MEMORY_SOURCE_SUMMARY_FORMAT = "SHIFT-MEMORY-SOURCE-SEMANTIC-SUMMARY/1"
ROW_POINTER_ALLOCATOR = "FUN_008868d0"
ROW_POINTER_ALLOCATOR_CALLER = "FUN_007b3820"
ROW_POINTER_SIZE_ARGUMENT_INDEX = 0

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
        "allocator": ROW_POINTER_ALLOCATOR,
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


def _validated_memory_source_summary(
    summary: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if summary is None:
        return None
    if not isinstance(summary, dict):
        raise TypeError("memory_source_semantic_summary must be a mapping")
    if summary.get("format") != MEMORY_SOURCE_SUMMARY_FORMAT:
        raise ValueError(
            "memory_source_semantic_summary must use " + MEMORY_SOURCE_SUMMARY_FORMAT
        )
    return summary


def _row_pointer_memory_crosscheck(
    summary: dict[str, Any] | None,
) -> dict[str, Any]:
    if summary is None:
        return {
            "summary_present": False,
            "allocator": ROW_POINTER_ALLOCATOR,
            "expected_source_argument_index": ROW_POINTER_SIZE_ARGUMENT_INDEX,
            "profile_present": False,
            "allocation_size_role_proven": False,
            "source_argument_index": None,
            "source_argument_index_matches_contract": False,
            "matrix_builder_caller_observed": False,
            "proven_callsite_count": 0,
            "crosscheck_ready": False,
            "blockers": ["memory_source_semantic_summary_not_supplied"],
        }

    profile: dict[str, Any] | None = None
    for row in summary.get("wrapper_profiles") or []:
        if isinstance(row, dict) and row.get("wrapper") == ROW_POINTER_ALLOCATOR:
            profile = row
            break

    blockers: list[str] = []
    if summary.get("allocation_size_role_proven") is not True:
        blockers.append("allocation_size_role_not_proven")
    if summary.get("semantic_profiles_consistent") is not True:
        blockers.append("semantic_profiles_inconsistent")
    if profile is None:
        blockers.append("row_pointer_allocator_profile_missing")
        return {
            "summary_present": True,
            "allocator": ROW_POINTER_ALLOCATOR,
            "expected_source_argument_index": ROW_POINTER_SIZE_ARGUMENT_INDEX,
            "profile_present": False,
            "allocation_size_role_proven": False,
            "source_argument_index": None,
            "source_argument_index_matches_contract": False,
            "matrix_builder_caller_observed": False,
            "proven_callsite_count": 0,
            "crosscheck_ready": False,
            "blockers": blockers,
        }

    allocation = profile.get("allocation_size")
    if not isinstance(allocation, dict):
        allocation = {}
        blockers.append("allocation_size_profile_missing")
    proven_roles = profile.get("proven_source_roles")
    if not isinstance(proven_roles, list):
        proven_roles = []

    index = allocation.get("source_argument_index")
    index_consistent = allocation.get("source_argument_index_consistent") is True
    callsite_count = allocation.get("proven_callsite_count")
    callers = allocation.get("callers")
    if not isinstance(callers, list):
        callers = []
    callers = [str(value) for value in callers if isinstance(value, str)]

    role_proven = bool(
        summary.get("allocation_size_role_proven") is True
        and summary.get("semantic_profiles_consistent") is True
        and index_consistent
        and isinstance(index, int)
        and not isinstance(index, bool)
        and index >= 0
        and isinstance(callsite_count, int)
        and not isinstance(callsite_count, bool)
        and callsite_count >= 1
        and "allocation-size" in proven_roles
    )
    if not index_consistent:
        blockers.append("allocation_size_source_index_not_consistent")
    if not isinstance(index, int) or isinstance(index, bool) or index < 0:
        blockers.append("allocation_size_source_index_invalid")
    if not isinstance(callsite_count, int) or isinstance(callsite_count, bool) or callsite_count < 1:
        blockers.append("allocation_size_proven_callsite_missing")
    if "allocation-size" not in proven_roles:
        blockers.append("allocation_size_role_marker_missing")

    index_matches = bool(role_proven and index == ROW_POINTER_SIZE_ARGUMENT_INDEX)
    if role_proven and not index_matches:
        blockers.append("allocation_size_source_index_mismatch")
    caller_observed = ROW_POINTER_ALLOCATOR_CALLER in callers
    if role_proven and not caller_observed:
        blockers.append("matrix_builder_caller_not_observed")

    ready = bool(role_proven and index_matches and caller_observed)
    return {
        "summary_present": True,
        "allocator": ROW_POINTER_ALLOCATOR,
        "expected_source_argument_index": ROW_POINTER_SIZE_ARGUMENT_INDEX,
        "profile_present": True,
        "allocation_size_role_proven": role_proven,
        "source_argument_index": index if role_proven else None,
        "source_argument_index_matches_contract": index_matches,
        "matrix_builder_caller_observed": caller_observed,
        "proven_callsite_count": callsite_count if isinstance(callsite_count, int) else 0,
        "callers": callers,
        "observed_source_expressions": [
            str(value)
            for value in (allocation.get("observed_source_expressions") or [])
            if isinstance(value, str)
        ],
        "crosscheck_ready": ready,
        "blockers": blockers,
    }


def build_matrix_construction_contract(
    memory_source_semantic_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary = _validated_memory_source_summary(memory_source_semantic_summary)
    memory_crosscheck = _row_pointer_memory_crosscheck(summary)
    status = "source-backed-preacceptance-matrix-build"
    if memory_crosscheck["crosscheck_ready"] is True:
        status = "source-and-diagnostic-backed-preacceptance-matrix-build"

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
        "memory_wrapper_evidence": memory_crosscheck,
        "status": status,
        "limitations": [
            "FUN_007ba2b0 body contribution semantics remain opaque here.",
            "This phase does not infer which exact matrix cells each body/constraint contributes.",
            "The matrix is rebuilt before provider selection; later provider fixed workspace is a separate storage domain.",
            "The optional memory cross-check proves the allocation-size role of source argument 0, not the complete FUN_008868d0 allocator ABI or its remaining parameter roles.",
        ],
    }


def validate_matrix_construction_contract(
    memory_source_semantic_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
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

    summary = _validated_memory_source_summary(memory_source_semantic_summary)
    memory_crosscheck = _row_pointer_memory_crosscheck(summary)
    return {
        "format": "SHIFT.SpecializedProviderPreAcceptanceMatrixValidation/1",
        "version": 1,
        "ready": not errors,
        "errors": errors,
        "memory_crosscheck_requested": summary is not None,
        "row_pointer_allocation_size_crosschecked": (
            memory_crosscheck["crosscheck_ready"] is True
        ),
        "memory_crosscheck_blockers": memory_crosscheck["blockers"],
    }


__all__ = [
    "FORMAT",
    "MEMORY_SOURCE_SUMMARY_FORMAT",
    "MATRIX_BUILD",
    "ROW_POINTER_ALLOCATOR",
    "build_matrix_construction_contract",
    "validate_matrix_construction_contract",
]
