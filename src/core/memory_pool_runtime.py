"""Shared evidence-backed memory-pool helper contract for retail SHIFT.

The class/lifecycle evidence pipeline proves that FUN_00886900 participates in a
pool-allocation path and FUN_00886930 participates in a pool-free path.  This
module centralizes those retail identities for reconstructed runtime contracts
without promoting either helper to compiler ``operator new``/``operator delete``
ABI semantics.
"""
from __future__ import annotations

from typing import Any

FORMAT = "SHIFT.MemoryPoolRuntime/1"

CREATE_HELPER = "FUN_00886900"
RELEASE_HELPER = "FUN_00886930"

CREATE_DIRECT_CALLEES = ("FUN_00638020", "FUN_006382b0")
CREATE_DIAGNOSTIC_PATH = (CREATE_HELPER, "FUN_00638020")
CREATE_DIAGNOSTIC_FUNCTION = "FUN_00638020"
CREATE_DIAGNOSTIC = "Unable to allocate %d bytes of memory from the pool (%s)"

RELEASE_THUNK = "thunk_FUN_0064f3a0"
RELEASE_BACKEND = "FUN_0064f3a0"
RELEASE_DIAGNOSTIC_FUNCTION = "FUN_00657c30"
RELEASE_DIAGNOSTIC_PATH = (
    RELEASE_HELPER,
    RELEASE_THUNK,
    RELEASE_BACKEND,
    RELEASE_DIAGNOSTIC_FUNCTION,
)
RELEASE_DIAGNOSTIC = "Error freeing small alloc (no head) '0x%p' from pool: '%s'\n"


def _helper_record(key: str, helper: str, fields: dict[str, Any]) -> dict[str, Any]:
    if key in fields:
        raise ValueError(f"{key} is reserved for the retail helper identity")
    return {key: helper, **fields}


def create_helper_action(**fields: Any) -> dict[str, Any]:
    """Return an action record that preserves the retail create-helper identity."""
    return _helper_record("action", CREATE_HELPER, fields)


def release_helper_action(**fields: Any) -> dict[str, Any]:
    """Return an action record that preserves the retail release-helper identity."""
    return _helper_record("action", RELEASE_HELPER, fields)


def release_helper_function(**fields: Any) -> dict[str, Any]:
    """Return a function-keyed release record used by existing runtime contracts."""
    return _helper_record("function", RELEASE_HELPER, fields)


def build_memory_pool_contract() -> dict[str, Any]:
    """Expose the strongest currently proven retail memory-pool boundary."""
    return {
        "format": FORMAT,
        "version": 1,
        "status": "diagnostic-backed-pool-paths",
        "helpers": {
            "create": CREATE_HELPER,
            "release": RELEASE_HELPER,
        },
        "allocation_path": {
            "helper": CREATE_HELPER,
            "direct_callees": list(CREATE_DIRECT_CALLEES),
            "diagnostic_path": list(CREATE_DIAGNOSTIC_PATH),
            "diagnostic_function": CREATE_DIAGNOSTIC_FUNCTION,
            "diagnostic": CREATE_DIAGNOSTIC,
            "evidence_kind": "bounded-direct-call-path-to-exact-retail-diagnostic",
        },
        "free_path": {
            "helper": RELEASE_HELPER,
            "diagnostic_path": list(RELEASE_DIAGNOSTIC_PATH),
            "thunk": RELEASE_THUNK,
            "backend": RELEASE_BACKEND,
            "diagnostic_function": RELEASE_DIAGNOSTIC_FUNCTION,
            "diagnostic": RELEASE_DIAGNOSTIC,
            "evidence_kind": "bounded-direct-call-path-to-exact-retail-diagnostic",
        },
        "scope": {
            "pool_allocation_path_proven": True,
            "pool_free_path_proven": True,
            "allocator_abi_proven": False,
            "release_abi_proven": False,
            "operator_new_identity_proven": False,
            "operator_delete_identity_proven": False,
            "object_size_argument_proven": False,
            "pool_selector_argument_proven": False,
            "ownership_semantics_proven": False,
            "note": (
                "The helpers are proven participants in retail pool allocation/free "
                "paths. Exact ABI, argument meanings and ownership remain unresolved."
            ),
        },
    }
