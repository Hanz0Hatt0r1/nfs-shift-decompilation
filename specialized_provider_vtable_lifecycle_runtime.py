"""Exact specialized-provider vtable lifecycle mapping.

The table words are recovered from PE .rdata. Slot roles are paired with the
previously identified provider functions, while the +0x00 destructor wrappers
are linked to their shutdown routines from the retail source.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from specialized_provider_runtime import get_provider
from specialized_provider_storage_runtime import get_storage_layout

FORMAT = "SHIFT.SpecializedProviderVTableLifecycleRuntime/1"


@dataclass(frozen=True)
class VTableLifecycle:
    provider_id: int
    vtable_address: int
    slots: dict[int, int]
    shutdown_function: int
    reset_function: int
    cleanup_function: int


PROVIDER0_VTABLE = VTableLifecycle(
    provider_id=0,
    vtable_address=0x00B0FC5C,
    slots={
        0x00: 0x007D3120,
        0x04: 0x007D2EB0,
        0x08: 0x007D2EC0,
        0x0C: 0x007D2ED0,
        0x10: 0x007C6E30,
        0x14: 0x007C6E50,
        0x18: 0x007C7200,
        0x1C: 0x007D3150,
        0x20: 0x007D43C0,
        0x24: 0x007D2EE0,
        0x28: 0x007D2EF0,
        0x2C: 0x007D2F00,
    },
    shutdown_function=0x007C6E10,
    reset_function=0x007D3150,
    cleanup_function=0x007D43C0,
)

PROVIDER1_VTABLE = VTableLifecycle(
    provider_id=1,
    vtable_address=0x00B0FC8C,
    slots={
        0x00: 0x007D4870,
        0x04: 0x007D2F10,
        0x08: 0x007D2F20,
        0x0C: 0x007D2F30,
        0x10: 0x007CDB20,
        0x14: 0x007CDB40,
        0x18: 0x007CDFC0,
        0x1C: 0x007D48A0,
        0x20: 0x007D5600,
        0x24: 0x007D2F40,
        0x28: 0x007D2F50,
        0x2C: 0x007D2F60,
    },
    shutdown_function=0x007CDB00,
    reset_function=0x007D48A0,
    cleanup_function=0x007D5600,
)


def get_vtable_lifecycle(provider_id: int) -> VTableLifecycle:
    if provider_id == 0:
        return PROVIDER0_VTABLE
    if provider_id == 1:
        return PROVIDER1_VTABLE
    raise ValueError(f"unsupported provider id: {provider_id}")


SLOT_ROLES = {
    0x00: "destructor-wrapper",
    0x04: "output-vector-accessor",
    0x08: "factor-workspace-accessor",
    0x0C: "row-pointer-accessor",
    0x10: "scalar-count-check",
    0x14: "acceptance-check",
    0x18: "solve",
    0x1C: "reset",
    0x20: "cleanup",
    0x24: "workspace-size-accessor",
    0x28: "scalar-count-accessor",
    0x2C: "workspace-size-finalize-accessor",
}


def build_vtable_contract(provider_id: int) -> dict[str, Any]:
    lifecycle = get_vtable_lifecycle(provider_id)
    layout = get_storage_layout(provider_id)
    provider = get_provider(provider_id)

    slots = [
        {
            "offset": hex(offset),
            "role": SLOT_ROLES[offset],
            "function": hex(address),
        }
        for offset, address in sorted(lifecycle.slots.items())
    ]

    return {
        "provider_id": provider_id,
        "vtable_address": hex(lifecycle.vtable_address),
        "slot_count": len(lifecycle.slots),
        "slots": slots,
        "lifecycle_functions": {
            "shutdown": hex(lifecycle.shutdown_function),
            "reset": hex(lifecycle.reset_function),
            "cleanup": hex(lifecycle.cleanup_function),
            "solve": hex(provider.solve_function),
        },
        "storage_constants": {
            "workspace_doubles": layout.factor_workspace_doubles,
            "scalar_count": layout.scalar_count,
            "output_doubles": layout.output_vector_doubles,
        },
    }


def validate_vtable_contract(provider_id: int) -> dict[str, Any]:
    lifecycle = get_vtable_lifecycle(provider_id)
    provider = get_provider(provider_id)
    errors: list[str] = []

    if len(lifecycle.slots) != 12:
        errors.append("unexpected-vtable-slot-count")

    required_roles = {
        0x00: "destructor-wrapper",
        0x18: "solve",
        0x1C: "reset",
        0x20: "cleanup",
    }
    for offset, role in required_roles.items():
        if SLOT_ROLES[offset] != role:
            errors.append(f"slot-role-mismatch:{hex(offset)}")
        if offset not in lifecycle.slots:
            errors.append(f"missing-slot:{hex(offset)}")

    if lifecycle.slots[0x18] != provider.solve_function:
        errors.append("solve-slot-function-mismatch")
    if lifecycle.slots[0x1C] != lifecycle.reset_function:
        errors.append("reset-slot-function-mismatch")
    if lifecycle.slots[0x20] != lifecycle.cleanup_function:
        errors.append("cleanup-slot-function-mismatch")

    return {
        "format": "SHIFT.SpecializedProviderVTableLifecycleValidation/1",
        "version": 1,
        "provider_id": provider_id,
        "ready": not errors,
        "errors": errors,
    }


def build_vtable_lifecycle_contract() -> dict[str, Any]:
    providers = []
    for provider_id in (0, 1):
        entry = build_vtable_contract(provider_id)
        entry["validation"] = validate_vtable_contract(provider_id)
        providers.append(entry)

    return {
        "format": FORMAT,
        "version": 1,
        "providers": providers,
        "slot_roles": {
            hex(offset): role
            for offset, role in SLOT_ROLES.items()
        },
        "source_basis": {
            "vtable": "PE .rdata 32-bit function pointers",
            "shutdown_wrapper": "retail source shows +0x00 wrapper invoking provider shutdown",
            "solve/reset/cleanup": "vtable words match independently recovered provider functions",
        },
        "limitations": [
            "Only slot roles supported by existing provider evidence are named.",
            "The +0x00 destructor wrapper is linked to shutdown by source inspection, not by C++ type inference.",
            "No undocumented provider class name or physical meaning is inferred.",
        ],
        "status": "source-backed-provider-vtable-lifecycle",
    }


__all__ = [
    "FORMAT",
    "VTableLifecycle",
    "PROVIDER0_VTABLE",
    "PROVIDER1_VTABLE",
    "SLOT_ROLES",
    "get_vtable_lifecycle",
    "build_vtable_contract",
    "validate_vtable_contract",
    "build_vtable_lifecycle_contract",
]
