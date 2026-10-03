"""Shared evidence-backed memory-pool helper contract for retail SHIFT.

The recovered helper cluster proves that FUN_00886900 participates in a retail
pool-allocation path and FUN_00886930 participates in a pool-free path. This
module centralizes those identities for reconstructed runtime contracts without
promoting either helper to compiler ``operator new``/``operator delete`` ABI
semantics.

A ``SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1`` artifact may promote independently
diagnostic-backed physical roles. A separate
``SHIFT-MEMORY-SOURCE-SEMANTIC-SUMMARY/1`` artifact may additionally identify a
stable source argument index, but only when the matching physical role is also
proven by the static summary.
"""
from __future__ import annotations

from typing import Any

FORMAT = "SHIFT.MemoryPoolRuntime/1"
STATIC_SUMMARY_FORMAT = "SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1"
SOURCE_SEMANTIC_SUMMARY_FORMAT = "SHIFT-MEMORY-SOURCE-SEMANTIC-SUMMARY/1"

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


def _validated_summary(
    summary: dict[str, Any] | None,
    *,
    argument_name: str,
    expected_format: str,
) -> dict[str, Any] | None:
    if summary is None:
        return None
    if not isinstance(summary, dict):
        raise TypeError(f"{argument_name} must be a mapping")
    if summary.get("format") != expected_format:
        raise ValueError(f"{argument_name} must use {expected_format}")
    return summary


def _validated_static_summary(summary: dict[str, Any] | None) -> dict[str, Any] | None:
    return _validated_summary(
        summary,
        argument_name="retail_static_summary",
        expected_format=STATIC_SUMMARY_FORMAT,
    )


def _validated_source_semantic_summary(
    summary: dict[str, Any] | None,
) -> dict[str, Any] | None:
    return _validated_summary(
        summary,
        argument_name="retail_source_semantic_summary",
        expected_format=SOURCE_SEMANTIC_SUMMARY_FORMAT,
    )


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
        str(value) for value in released_storage if isinstance(value, str) and value
    ]
    if not released_storage:
        released_proven = False

    return {
        "summary_present": True,
        "static_evidence_chain_complete": summary.get("static_evidence_chain_complete") is True,
        "allocation_size_role_proven": allocation_proven,
        "allocation_size_backend_function": (
            str(allocation.get("function"))
            if allocation_proven and allocation.get("function")
            else None
        ),
        "allocation_size_backend_storage": allocation_storage if allocation_proven else None,
        "released_pointer_role_proven": released_proven,
        "released_pointer_wrapper_storage": released_storage if released_proven else [],
        "release_byte_behavior_observed": summary_scope.get("release_byte_behavior_observed") is True,
        "release_byte_behavior": release_byte if release_byte else None,
    }


def _source_profile(
    summary: dict[str, Any],
    *,
    helper: str,
    profile_key: str,
    proven_role_name: str,
    top_level_flag: str,
) -> dict[str, Any]:
    default = {
        "profile_present": False,
        "source_role_proven": False,
        "source_argument_index": None,
        "proven_callsite_count": 0,
        "callers": [],
        "observed_source_expressions": [],
    }
    if summary.get(top_level_flag) is not True:
        return default
    if summary.get("semantic_profiles_consistent") is not True:
        return default

    for profile in summary.get("wrapper_profiles") or []:
        if not isinstance(profile, dict) or profile.get("wrapper") != helper:
            continue
        role = profile.get(profile_key)
        if not isinstance(role, dict):
            return {**default, "profile_present": True}
        index = role.get("source_argument_index")
        callsite_count = role.get("proven_callsite_count")
        proven_roles = profile.get("proven_source_roles")
        if not isinstance(proven_roles, list):
            proven_roles = []
        role_proven = bool(
            role.get("source_argument_index_consistent") is True
            and isinstance(index, int)
            and not isinstance(index, bool)
            and index >= 0
            and isinstance(callsite_count, int)
            and not isinstance(callsite_count, bool)
            and callsite_count >= 1
            and proven_role_name in proven_roles
        )
        callers = role.get("callers")
        if not isinstance(callers, list):
            callers = []
        expressions = role.get("observed_source_expressions")
        if not isinstance(expressions, list):
            expressions = []
        return {
            "profile_present": True,
            "source_role_proven": role_proven,
            "source_argument_index": index if role_proven else None,
            "proven_callsite_count": callsite_count if isinstance(callsite_count, int) else 0,
            "callers": [str(value) for value in callers if isinstance(value, str)],
            "observed_source_expressions": [
                str(value) for value in expressions if isinstance(value, str)
            ],
        }
    return default


def _source_role_evidence(summary: dict[str, Any] | None) -> dict[str, Any]:
    if summary is None:
        return {
            "summary_present": False,
            "semantic_profiles_consistent": False,
            "allocation_size": _source_profile(
                {},
                helper=CREATE_HELPER,
                profile_key="allocation_size",
                proven_role_name="allocation-size",
                top_level_flag="allocation_size_role_proven",
            ),
            "released_pointer": _source_profile(
                {},
                helper=RELEASE_HELPER,
                profile_key="released_pointer",
                proven_role_name="released-pointer",
                top_level_flag="released_pointer_role_proven",
            ),
            "release_byte_behavior": None,
        }

    release_byte = summary.get("release_byte_behavior")
    if not isinstance(release_byte, dict):
        release_byte = None
    return {
        "summary_present": True,
        "semantic_profiles_consistent": summary.get("semantic_profiles_consistent") is True,
        "allocation_size": _source_profile(
            summary,
            helper=CREATE_HELPER,
            profile_key="allocation_size",
            proven_role_name="allocation-size",
            top_level_flag="allocation_size_role_proven",
        ),
        "released_pointer": _source_profile(
            summary,
            helper=RELEASE_HELPER,
            profile_key="released_pointer",
            proven_role_name="released-pointer",
            top_level_flag="released_pointer_role_proven",
        ),
        "release_byte_behavior": release_byte,
    }


def build_memory_pool_contract(
    retail_static_summary: dict[str, Any] | None = None,
    retail_source_semantic_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Expose the strongest currently proven retail memory-pool boundary.

    With no summaries this returns the historical diagnostic-backed helper
    contract. Static retail evidence can promote physical roles. Source semantic
    evidence can additionally expose stable source argument indices, but only
    when the corresponding static physical role is independently proven.
    """
    static_summary = _validated_static_summary(retail_static_summary)
    source_summary = _validated_source_semantic_summary(retail_source_semantic_summary)
    static_evidence = _static_role_evidence(static_summary)
    source_evidence = _source_role_evidence(source_summary)

    allocation_size_proven = static_evidence["allocation_size_role_proven"] is True
    released_pointer_proven = static_evidence["released_pointer_role_proven"] is True
    allocation_source = source_evidence["allocation_size"]
    released_source = source_evidence["released_pointer"]
    allocation_source_index_proven = bool(
        allocation_size_proven and allocation_source["source_role_proven"] is True
    )
    released_source_index_proven = bool(
        released_pointer_proven and released_source["source_role_proven"] is True
    )

    status = "diagnostic-backed-pool-paths"
    if allocation_size_proven or released_pointer_proven:
        status = "instruction-diagnostic-backed-physical-roles"
    if allocation_source_index_proven or released_source_index_proven:
        status = "source-joined-semantic-roles"

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
            "allocation_size_source_argument_index_proven": allocation_source_index_proven,
            "released_pointer_source_argument_index_proven": released_source_index_proven,
            "allocator_abi_proven": False,
            "release_abi_proven": False,
            "operator_new_identity_proven": False,
            "operator_delete_identity_proven": False,
            "object_size_argument_proven": False,
            "pool_selector_argument_proven": False,
            "release_flag_argument_proven": False,
            "ownership_semantics_proven": False,
            "note": (
                "The helpers are proven participants in retail pool allocation/free paths. "
                "Static evidence may promote physical allocation-size/released-pointer roles; "
                "a separately validated source semantic summary may additionally expose stable "
                "source argument indices for those already-proven roles. Exact ABI, pool/delete "
                "selectors and ownership remain unresolved."
            ),
        },
    }

    if static_evidence["summary_present"]:
        contract["retail_static_evidence"] = {
            "format": STATIC_SUMMARY_FORMAT,
            "static_evidence_chain_complete": static_evidence[
                "static_evidence_chain_complete"
            ],
            "allocation_size": {
                "proven": allocation_size_proven,
                "backend_function": static_evidence["allocation_size_backend_function"],
                "backend_entry_storage": static_evidence["allocation_size_backend_storage"],
            },
            "released_pointer": {
                "proven": released_pointer_proven,
                "wrapper_input_storage": static_evidence[
                    "released_pointer_wrapper_storage"
                ],
            },
            "release_byte_behavior_observed": static_evidence[
                "release_byte_behavior_observed"
            ],
            "release_byte_behavior": static_evidence["release_byte_behavior"],
        }

    if source_evidence["summary_present"]:
        contract["retail_source_semantic_evidence"] = {
            "format": SOURCE_SEMANTIC_SUMMARY_FORMAT,
            "semantic_profiles_consistent": source_evidence[
                "semantic_profiles_consistent"
            ],
            "allocation_size": {
                "helper": CREATE_HELPER,
                "proven": allocation_source_index_proven,
                "source_argument_index": (
                    allocation_source["source_argument_index"]
                    if allocation_source_index_proven
                    else None
                ),
                "proven_callsite_count": allocation_source["proven_callsite_count"],
                "callers": allocation_source["callers"],
                "observed_source_expressions": allocation_source[
                    "observed_source_expressions"
                ],
            },
            "released_pointer": {
                "helper": RELEASE_HELPER,
                "proven": released_source_index_proven,
                "source_argument_index": (
                    released_source["source_argument_index"]
                    if released_source_index_proven
                    else None
                ),
                "proven_callsite_count": released_source["proven_callsite_count"],
                "callers": released_source["callers"],
                "observed_source_expressions": released_source[
                    "observed_source_expressions"
                ],
            },
            "release_byte_behavior": source_evidence["release_byte_behavior"],
        }

    return contract
