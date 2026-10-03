"""Shared fail-closed release-pointer evidence for camera runtime contracts.

The helper consumes the same independent retail static and source-semantic
summaries as ``memory_pool_runtime``. It only reports a camera callsite ready
when the released-pointer physical role, source argument index, and exact caller
all agree. It never promotes release ABI, delete-kind, flag, or ownership
semantics.
"""

from __future__ import annotations

from typing import Any

from memory_pool_runtime import build_memory_pool_contract

FORMAT = "SHIFT.CameraReleasePointerCrosscheck/1"
RELEASE_HELPER = "FUN_00886930"
RELEASED_POINTER_ROLE = "released-pointer"
RELEASED_POINTER_SOURCE_ARGUMENT_INDEX = 0


def build_camera_release_pointer_crosscheck(
    retail_static_summary: dict[str, Any] | None,
    retail_source_semantic_summary: dict[str, Any] | None,
    *,
    caller: str,
    format_name: str = FORMAT,
) -> dict[str, Any] | None:
    """Cross-check one camera callsite against the proven release-pointer role."""
    if retail_static_summary is None and retail_source_semantic_summary is None:
        return None
    if not isinstance(caller, str) or not caller:
        raise ValueError("caller must be a non-empty function name")
    if not isinstance(format_name, str) or not format_name:
        raise ValueError("format_name must be a non-empty string")

    contract = build_memory_pool_contract(
        retail_static_summary,
        retail_source_semantic_summary,
    )
    static_evidence = contract.get("retail_static_evidence")
    if not isinstance(static_evidence, dict):
        static_evidence = {}
    source_evidence = contract.get("retail_source_semantic_evidence")
    if not isinstance(source_evidence, dict):
        source_evidence = {}

    static_role = static_evidence.get("released_pointer")
    if not isinstance(static_role, dict):
        static_role = {}
    source_role = source_evidence.get("released_pointer")
    if not isinstance(source_role, dict):
        source_role = {}

    physical_role_proven = static_role.get("proven") is True
    source_role_proven = source_role.get("proven") is True
    source_index = source_role.get("source_argument_index")

    callers = source_role.get("callers")
    if not isinstance(callers, list):
        callers = []
    callers = [str(value) for value in callers if isinstance(value, str)]

    expressions = source_role.get("observed_source_expressions")
    if not isinstance(expressions, list):
        expressions = []
    expressions = [str(value) for value in expressions if isinstance(value, str)]

    blockers: list[str] = []
    if not physical_role_proven:
        blockers.append("released_pointer_physical_role_not_proven")
    if not source_role_proven:
        blockers.append("released_pointer_source_role_not_proven")
    if (
        source_role_proven
        and source_index != RELEASED_POINTER_SOURCE_ARGUMENT_INDEX
    ):
        blockers.append("released_pointer_source_index_mismatch")
    if source_role_proven and caller not in callers:
        blockers.append("release_caller_not_observed")

    ready = not blockers
    return {
        "format": format_name,
        "helper": RELEASE_HELPER,
        "role": RELEASED_POINTER_ROLE,
        "caller": caller,
        "expected_source_argument_index": RELEASED_POINTER_SOURCE_ARGUMENT_INDEX,
        "observed_source_argument_index": source_index if source_role_proven else None,
        "physical_role_proven": physical_role_proven,
        "source_role_proven": source_role_proven,
        "caller_observed": caller in callers if source_role_proven else False,
        "proven_callsite_count": source_role.get("proven_callsite_count", 0),
        "observed_callers": callers,
        "observed_source_expressions": expressions,
        "ready": ready,
        "blockers": blockers,
        "scope": {
            "release_helper_identity_preserved": True,
            "released_pointer_role_crosschecked": ready,
            "release_abi_proven": False,
            "release_flag_role_proven": False,
            "delete_kind_role_proven": False,
            "ownership_semantics_proven": False,
        },
    }


__all__ = [
    "FORMAT",
    "RELEASE_HELPER",
    "RELEASED_POINTER_ROLE",
    "RELEASED_POINTER_SOURCE_ARGUMENT_INDEX",
    "build_camera_release_pointer_crosscheck",
]
