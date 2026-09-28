"""Global bootstrap/teardown lifecycle for the specialized provider globals.

Phase 478 ties the provider objects to their global initialization and atexit
destruction functions recovered from SHIFT.exe.c. The selector-driven reset functions are invoked per active scalar through
FUN_007b2210 on the frame solver path.
"""
from __future__ import annotations

from typing import Any

from specialized_provider_runtime import get_provider
from specialized_provider_vtable_lifecycle_runtime import get_vtable_lifecycle

FORMAT = "SHIFT.SpecializedProviderGlobalLifecycleRuntime/1"

PROVIDER_GLOBALS = {
    0: {
        "global_object": "DAT_00c23da8",
        "init_function": "FUN_00a8ca80",
        "init_source_line": 1420501,
        "teardown_function": "FUN_00aa3800",
        "teardown_source_line": 1431065,
    },
    1: {
        "global_object": "DAT_00c23dac",
        "init_function": "FUN_00a8caa0",
        "init_source_line": 1420511,
        "teardown_function": "FUN_00aa3810",
        "teardown_source_line": 1431074,
    },
}


def build_provider_global_lifecycle(provider_id: int) -> dict[str, Any]:
    if provider_id not in PROVIDER_GLOBALS:
        raise ValueError(f"unsupported provider id: {provider_id}")

    provider = get_provider(provider_id)
    lifecycle = get_vtable_lifecycle(provider_id)
    data = PROVIDER_GLOBALS[provider_id]

    return {
        "provider_id": provider_id,
        "global_object": data["global_object"],
        "vtable_address": hex(lifecycle.vtable_address),
        "init": {
            "function": data["init_function"],
            "source_line": data["init_source_line"],
            "effect": f"construct provider global and install vtable {hex(lifecycle.vtable_address)}",
        },
        "runtime": {
            "selector_global": provider.selector_global,
            "solve_function": hex(provider.solve_function),
            "reset_function": hex(lifecycle.reset_function),
            "cleanup_function": hex(lifecycle.cleanup_function),
            "shutdown_function": hex(lifecycle.shutdown_function),
        },
        "teardown": {
            "function": data["teardown_function"],
            "source_line": data["teardown_source_line"],
            "effect": f"call provider shutdown {hex(lifecycle.shutdown_function)}",
        },
    }


def validate_provider_global_lifecycle(provider_id: int) -> dict[str, Any]:
    errors: list[str] = []
    entry = build_provider_global_lifecycle(provider_id)
    lifecycle = get_vtable_lifecycle(provider_id)

    if entry["runtime"]["solve_function"] != hex(lifecycle.slots[0x18]):
        errors.append("global-solve-vtable-mismatch")
    if entry["runtime"]["reset_function"] != hex(lifecycle.slots[0x1C]):
        errors.append("global-reset-vtable-mismatch")
    if entry["runtime"]["cleanup_function"] != hex(lifecycle.slots[0x20]):
        errors.append("global-cleanup-vtable-mismatch")
    if entry["runtime"]["shutdown_function"] != hex(
        lifecycle.shutdown_function
    ):
        errors.append("global-shutdown-mismatch")

    if not entry["init"]["function"].startswith("FUN_00a8ca"):
        errors.append("unexpected-init-function")
    if not entry["teardown"]["function"].startswith("FUN_00aa38"):
        errors.append("unexpected-teardown-function")

    return {
        "format": "SHIFT.SpecializedProviderGlobalLifecycleValidation/1",
        "version": 1,
        "provider_id": provider_id,
        "ready": not errors,
        "errors": errors,
    }


def build_global_lifecycle_contract() -> dict[str, Any]:
    providers = []
    for provider_id in (0, 1):
        entry = build_provider_global_lifecycle(provider_id)
        entry["validation"] = validate_provider_global_lifecycle(provider_id)
        providers.append(entry)

    return {
        "format": FORMAT,
        "version": 1,
        "providers": providers,
        "global_order": [
            "global initialization function constructs provider",
            "provider global installs recovered vtable",
            "physics runtime may select provider through DAT_00c23da8/00c23dac",
            "frame execution consumes provider +0x20 cleanup and +0x18 solve when selected",
            "global atexit teardown calls provider shutdown",
        ],
        "reset_boundary": {
            "function": {
                0: "FUN_007d3150",
                1: "FUN_007d48a0",
            },
            "vtable_slot": "+0x1c",
            "status": "per-scalar frame reset delegated by FUN_007b2210",
            "frame_loop_callsite": "FUN_007b3f40 -> FUN_007b2210 -> provider vtable +0x1c",
        },
        "source_basis": {
            "provider0_init": "FUN_00a8ca80 -> FUN_007d2f70(&DAT_00c23da8)",
            "provider1_init": "FUN_00a8caa0 -> FUN_007cd980(&DAT_00c23dac)",
            "provider0_teardown": "FUN_00aa3800 -> FUN_007c6e10(&DAT_00c23da8)",
            "provider1_teardown": "FUN_00aa3810 -> FUN_007cdb00(&DAT_00c23dac)",
        },
        "limitations": [
            "The selector-driven reset API is not assigned a runtime frequency without a direct callsite or capture.",
            "Global bootstrap order outside the two provider calls is not modeled.",
            "No C++ class hierarchy or semantic provider name is inferred.",
        ],
        "status": "source-backed-specialized-provider-global-lifecycle",
    }


__all__ = [
    "FORMAT",
    "PROVIDER_GLOBALS",
    "build_provider_global_lifecycle",
    "validate_provider_global_lifecycle",
    "build_global_lifecycle_contract",
]
