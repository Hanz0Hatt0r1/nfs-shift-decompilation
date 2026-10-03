"""Shared evidence-backed memory-pool helper contract for retail SHIFT.

The class/lifecycle evidence pipeline proves that FUN_00886900 participates in a
pool-allocation path and FUN_00886930 participates in a pool-free path.  This
module centralizes those retail identities for reconstructed runtime contracts
without promoting either helper to compiler ``operator new``/``operator delete``
ABI semantics.

When a ``SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1`` artifact is supplied, the
contract may additionally expose the independently diagnostic-backed physical
roles ``allocation-size`` and ``released-pointer``.  Those roles still do not
prove the complete helper ABI, pool selector, delete kind, or ownership policy.
"""
from __future__ import annotations

from typing import Any

FORMAT = "SHIFT.MemoryPoolRuntime/1"
STATIC_SUMMARY_FORMAT = "SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1"

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


def _validated_static_summary(summary: dict[str, Any] | None) -> dict[str, Any] | None:
    if summary is None:
        return None
    if not isinstance(summary, dict):
        raise TypeError("retail_static_summary must be a mapping")
    if summary.get("format") != STATIC_SUMMARY_FORMAT:
        raise ValueError(
            "retail_static_summary must use " + STATIC_SUMMARY_FORMAT
        )
    return summary


def _static_role_evidence(summary: dict[str, Any] | None) -> dict[str, Any]:
    """Extract only role claims explicitly promoted by the static summary."""
    if summary is None:
        return {
            "summary_present": False,
            "static_evidence_chain_complete": False,
            "allocation_size_role_proven": False,
            "allocation_size_backend_function": None,
            "allocation_size_backend_storage": None,
            "released_pointer_role_proven": False,
            "released_pointer_wrapper_storage": [],
            "release_byte_behavior_observed": False,
            "release_byte_behavior": None,
        }

    roles = summary.get("proven_physical_roles")
    if not isinstance(roles, dict):
        roles = {}
    allocation = roles.get("allocation_size")
    if not isinstance(allocation, dict):
        allocation = {}
    released = roles.get("released_pointer_wrapper")
    if not isinstance(released, dict):
        released = {}
    release_byte = summary.get("release_byte_behavior")
    if not isinstance(release_byte, dict):
        release_byte = {}
    summary_scope = summary.get("scope")
    if not isinstance(summary_scope, dict):
        summary_scope = {}

    allocation_proven = allocation.get("proven") is True
    allocation_storage = allocation.get("entry_storage")
    if not isinstance(allocation_storage, str) or not allocation_storage:
        allocation_storage = None
        allocation_proven = False

    released_proven = released.get("proven") is True
    released_storage = released.get("wrapper_input_storage")
    if not isinstance(released_storage, list):
        released_storage = []
    released_storage = [
        str(value) for value in released_storage
        if isinstance(value, str) and value
    ]
    if not released_storage:
        released_proven = False

    return {
        "summary_present": True,
        "static_evidence_chain_complete": summary.get("static_evidence_chain_complete") is True,
        "allocation_size_role_proven": allocation_proven,
        "allocation_size_backend_function": (
            str(allocation.get("function")) if allocation_proven and allocation.get("function") else None
        ),
        "allocation_size_backend_storage": allocation_storage if allocation_proven else None,
        "released_pointer_role_proven": released_proven,
        "released_pointer_wrapper_storage": released_storage if released_proven else [],
        "release_byte_behavior_observed": summary_scope.get("release_byte_behavior_observed") is True,
        "release_byte_behavior": release_byte if release_byte else None,
    }


def build_memory_pool_contract(
    retail_static_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Expose the strongest currently proven retail memory-pool boundary.

    Without an optional retail static summary this returns the historical
    diagnostic-backed helper contract.  With a validated summary it additionally
    admits only the physical argument roles that the summary itself marks proven.
    """
    summary = _validated_static_summary(retail_static_summary)
    role_evidence = _static_role_evidence(summary)
    allocation_size_proven = role_evidence["allocation_size_role_proven"] is True
    released_pointer_proven = role_evidence["released_pointer_role_proven"] is True

    status = "diagnostic-backed-pool-paths"
    if allocation_size_proven or released_pointer_proven:
        status = "instruction-diagnostic-backed-physical-roles"

    contract = {
        "format": FORMAT,
        "version": 1,
        "status": status,
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
            "allocation_size_argument_role_proven": allocation_size_proven,
            "released_pointer_argument_role_proven": released_pointer_proven,
            "allocator_abi_proven": False,
            "release_abi_proven": False,
            "operator_new_identity_proven": False,
            "operator_delete_identity_proven": False,
            # `allocation-size` is not automatically the C++ object size. The
            # original key remains false until that stronger relationship is proven.
            "object_size_argument_proven": False,
            "pool_selector_argument_proven": False,
            "release_flag_argument_proven": False,
            "ownership_semantics_proven": False,
            "note": (
                "The helpers are proven participants in retail pool allocation/free "
                "paths. Optional retail static evidence can promote diagnostic-backed "
                "physical allocation-size and released-pointer roles, while exact ABI, "
                "pool/delete selectors and ownership remain unresolved."
            ),
        },
    }

    if role_evidence["summary_present"]:
        contract["retail_static_evidence"] = {
            "format": STATIC_SUMMARY_FORMAT,
            "static_evidence_chain_complete": role_evidence[
                "static_evidence_chain_complete"
            ],
            "allocation_size": {
                "proven": allocation_size_proven,
                "backend_function": role_evidence["allocation_size_backend_function"],
                "backend_entry_storage": role_evidence["allocation_size_backend_storage"],
            },
            "released_pointer": {
                "proven": released_pointer_proven,
                "wrapper_input_storage": role_evidence[
                    "released_pointer_wrapper_storage"
                ],
            },
            "release_byte_behavior_observed": role_evidence[
                "release_byte_behavior_observed"
            ],
            "release_byte_behavior": role_evidence["release_byte_behavior"],
        }

    return contract
