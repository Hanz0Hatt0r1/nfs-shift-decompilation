"""Exact global camera/object factory map from FUN_00823990 and FUN_00823a60.

The executable resolves a global type identifier, selects an allocation size,
constructs the corresponding runtime object, and returns it. The identifier
symbols are preserved exactly; known constructor associations are linked to
already recovered modules without inventing new class names.
"""

from __future__ import annotations

from typing import Any, Mapping

FORMAT = "SHIFT.CameraGlobalFactoryRuntime/1"


FACTORY_ENTRIES = {
    "DAT_00c25e60": {
        "allocation_bytes": 0x280,
        "constructor": "FUN_00814f60",
        "constructor_role": "opaque-camera-object",
    },
    "DAT_00c25f0c": {
        "allocation_bytes": 0xBC0,
        "constructor": "FUN_0081cba0",
        "constructor_role": "CCameraView constructor",
    },
    "DAT_00c25fa8": {
        "allocation_bytes": 0x460,
        "constructor": "FUN_0081fac0",
        "constructor_role": "TrackingCamera data/class constructor",
    },
    "DAT_00c25e70": {
        "allocation_bytes": 0xF0,
        "constructor": "FUN_00813300",
        "constructor_role": "static camera copy constructor",
        "source": "camera service +0x310",
    },
    "DAT_00c25fb8": {
        "allocation_bytes": 0x150,
        "constructor": "FUN_0081f990",
        "constructor_role": "TrackingCamera data copy constructor",
        "source": "camera service +0x400",
    },
}


def resolve_factory_entry(type_symbol: str) -> dict[str, Any]:
    """Reproduce the dispatch table in FUN_00823990."""
    key = str(type_symbol)
    entry = FACTORY_ENTRIES.get(key)
    if entry is None:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "factory-dispatch",
            "status": "unsupported",
            "type_symbol": key,
            "object": None,
            "evidence": {
                "function": "FUN_00823990",
                "fallback": "return NULL",
            },
        }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "factory-dispatch",
        "status": "supported",
        "type_symbol": key,
        "allocation_bytes": entry["allocation_bytes"],
        "constructor": entry["constructor"],
        "constructor_role": entry["constructor_role"],
        "source": entry.get("source"),
        "evidence": {
            "function": "FUN_00823990",
        },
    }


def instantiate_factory_entry(
    type_symbol: str,
    *,
    allocation_succeeded: bool,
    constructor_succeeded: bool,
    source_available: bool = True,
) -> dict[str, Any]:
    """Trace allocation/source/constructor branches without executing opaque constructors."""
    dispatch = resolve_factory_entry(type_symbol)
    if dispatch["status"] != "supported":
        return dispatch
    if not allocation_succeeded:
        return {
            **dispatch,
            "status": "allocation-failed",
            "object": None,
            "actions": [
                {
                    "action": "FUN_008868c0",
                    "bytes": dispatch["allocation_bytes"],
                }
            ],
        }
    if dispatch.get("source") and not source_available:
        return {
            **dispatch,
            "status": "source-unavailable",
            "object": None,
        }
    if not constructor_succeeded:
        return {
            **dispatch,
            "status": "constructor-failed",
            "object": None,
        }
    return {
        **dispatch,
        "status": "constructed",
        "object": {
            "type_symbol": dispatch["type_symbol"],
            "constructor": dispatch["constructor"],
        },
        "actions": [
            {
                "action": "FUN_008868c0",
                "bytes": dispatch["allocation_bytes"],
            },
            {
                "action": dispatch["constructor"],
                "source": dispatch.get("source"),
            },
        ],
    }


def resolve_factory_name(
    *,
    global_name: Any,
    resolved_type_symbol: str | None,
) -> dict[str, Any]:
    """Reproduce FUN_00823a60's global-name resolution boundary."""
    if resolved_type_symbol is None:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "factory-name-resolution",
            "status": "unresolved",
            "global_name": global_name,
            "actions": [
                {"action": "FUN_0080cc60"},
                {"action": "thunk_FUN_00d8cf00"},
            ],
        }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "factory-name-resolution",
        "status": "resolved",
        "global_name": global_name,
        "resolved_type_symbol": resolved_type_symbol,
        "actions": [
            {"action": "FUN_0080cc60"},
            {
                "action": "thunk_FUN_00d8cf00",
                "result": resolved_type_symbol,
            },
            {
                "action": "FUN_00823990",
                "type_symbol": resolved_type_symbol,
            },
        ],
        "evidence": {
            "function": "FUN_00823a60",
            "resolver_root": "FUN_0080cc60",
        },
    }
