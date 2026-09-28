"""Provider-neutral execution contract for SHIFT FUN_007b3820.

This module models the exact retail control-flow around the two provider slots.
It does not claim concrete PhysX/provider classes. A provider implementation is
an injected backend that exposes methods corresponding to the observed vtable
offsets.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, Callable

FORMAT = "SHIFT.PhysicsProviderBackendRuntime/1"

VTABLE = {
    "replace_primary_storage": 0x04,
    "replace_aux_storage": 0x08,
    "reset_allocation_state": 0x0C,
    "acceptance_probe": 0x14,
    "finalize": 0x2C,
}

@dataclass(frozen=True)
class ProviderSlot:
    selector_index: int
    global_slot: str
    vtable: str | None = None

@dataclass(frozen=True)
class ProviderCall:
    slot_index: int
    vtable_offset: int
    method: str
    args: tuple[Any, ...]
    result: Any = None

@dataclass
class ProviderExecution:
    selected_slot: int | None
    accepted: bool
    scalar_count: int
    primary_storage: Any
    graph_storage: Any
    aux_storage: Any
    secondary_domain: int
    calls: list[ProviderCall] = field(default_factory=list)
    fallback: bool = False

class ProviderBackend(Protocol):
    def call(self, vtable_offset: int, *args: Any) -> Any:
        ...

def provider_slots() -> tuple[ProviderSlot, ProviderSlot]:
    return (
        ProviderSlot(0, "DAT_00c23da8", "PTR_FUN_00b0fc5c"),
        ProviderSlot(1, "DAT_00c23dac", "PTR_FUN_00b0fc8c"),
    )

def _method_name(offset: int) -> str:
    for name, value in VTABLE.items():
        if value == offset:
            return name
    return f"vtable+0x{offset:x}"

def run_provider_selection(
    *,
    scalar_count: int,
    initial_row_table: Any,
    old_matrix: Any,
    old_row_table: Any,
    backends: tuple[ProviderBackend | None, ProviderBackend | None],
    release_matrix: Callable[[Any], None],
    release_rows: Callable[[Any], None],
) -> ProviderExecution:
    """Mirror FUN_007b3820's provider probe/rebind sequence."""
    if scalar_count < 0:
        raise ValueError("scalar_count must be non-negative")
    if len(backends) != 2:
        raise ValueError("exactly two provider slots are supported")

    calls: list[ProviderCall] = []

    for slot in provider_slots():
        backend = backends[slot.selector_index]
        if backend is None:
            continue

        accepted = bool(backend.call(VTABLE["acceptance_probe"], initial_row_table))
        calls.append(
            ProviderCall(
                slot.selector_index,
                VTABLE["acceptance_probe"],
                _method_name(VTABLE["acceptance_probe"]),
                (initial_row_table,),
                accepted,
            )
        )
        if not accepted:
            continue

        release_matrix(old_matrix)
        release_rows(old_row_table)

        row_storage = backend.call(VTABLE["reset_allocation_state"])
        calls.append(
            ProviderCall(
                slot.selector_index,
                VTABLE["reset_allocation_state"],
                _method_name(VTABLE["reset_allocation_state"]),
                (),
                row_storage,
            )
        )

        graph_storage = backend.call(VTABLE["replace_primary_storage"])
        calls.append(
            ProviderCall(
                slot.selector_index,
                VTABLE["replace_primary_storage"],
                _method_name(VTABLE["replace_primary_storage"]),
                (),
                graph_storage,
            )
        )

        aux_storage = backend.call(VTABLE["replace_aux_storage"])
        calls.append(
            ProviderCall(
                slot.selector_index,
                VTABLE["replace_aux_storage"],
                _method_name(VTABLE["replace_aux_storage"]),
                (),
                aux_storage,
            )
        )

        secondary_domain = int(backend.call(VTABLE["finalize"]))
        calls.append(
            ProviderCall(
                slot.selector_index,
                VTABLE["finalize"],
                _method_name(VTABLE["finalize"]),
                (),
                secondary_domain,
            )
        )

        return ProviderExecution(
            selected_slot=slot.selector_index,
            accepted=True,
            scalar_count=scalar_count,
            primary_storage=row_storage,
            graph_storage=graph_storage,
            aux_storage=aux_storage,
            secondary_domain=secondary_domain,
            calls=calls,
            fallback=False,
        )

    return ProviderExecution(
        selected_slot=None,
        accepted=False,
        scalar_count=scalar_count,
        primary_storage=None,
        aux_storage=None,
        secondary_domain=scalar_count * scalar_count,
        calls=calls,
        fallback=True,
    )

def build_fun_007b3820_backend_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "function": "FUN_007b3820",
        "selector": "FUN_007d2e70",
        "slots": [
            {
                "selector_index": slot.selector_index,
                "global_slot": slot.global_slot,
                "vtable": slot.vtable,
            }
            for slot in provider_slots()
        ],
        "vtable": {
            f"0x{offset:x}": {
                "method": method,
                "observed_use": {
                    "acceptance_probe": "physics_system+0x3c",
                    "reset_allocation_state": "result -> physics_system+0x3c",
                    "replace_primary_storage": "result -> physics_system+0x40",
                    "replace_aux_storage": "result -> physics_system+0x44",
                    "finalize": "result -> per-body +0xa8 workspace size",
                }[method],
            }
            for method, offset in VTABLE.items()
        },
        "accepted_provider_transition": [
            "probe slot 0 then slot 1",
            "release old matrix and old row table",
            "call +0x0c and replace physics_system+0x3c",
            "call +0x04 and replace physics_system+0x40",
            "call +0x08 and replace physics_system+0x44",
            "call +0x2c and use result as per-body +0xa8 workspace size",
        ],
        "fallback_transition": {
            "selector_after_slot_1": "null",
            "path": "FUN_007b2010 -> FUN_007b1360",
            "secondary_domain": "scalar_count * scalar_count",
        },
        "workspace_domain": {
            "provider_return_2c_equals_vtable_24": True,
            "provider0_value": 1190,
            "provider1_value": 746,
            "observed_destination": "per_body+0xa8",
        },
        "provider_identity": {
            "slot_0_init_vtable": "PTR_FUN_00b0fc5c",
            "slot_1_init_vtable": "PTR_FUN_00b0fc8c",
            "semantic_class_names": "unresolved",
        },
        "status": "source-backed-provider-neutral",
        "limitations": [
            "Provider acceptance is runtime-dependent.",
            "Concrete provider class identities remain unresolved.",
            "The +0x2c return is observed as the same workspace-size value returned by +0x24 in the shipped PE.",
        ],
    }

def summarize_execution(execution: ProviderExecution) -> dict[str, Any]:
    return {
        "format": FORMAT.replace("/1", "Execution/1"),
        "selected_slot": execution.selected_slot,
        "accepted": execution.accepted,
        "fallback": execution.fallback,
        "scalar_count": execution.scalar_count,
        "secondary_domain": execution.secondary_domain,
        "primary_storage": execution.primary_storage,
        "graph_storage": execution.graph_storage,
        "aux_storage": execution.aux_storage,
        "call_trace": [
            {
                "slot_index": call.slot_index,
                "vtable_offset": call.vtable_offset,
                "method": call.method,
                "args": list(call.args),
                "result": call.result,
            }
            for call in execution.calls
        ],
        "state_updates": {
            "physics_system+0x3c": execution.primary_storage,
            "physics_system+0x40": execution.graph_storage if not execution.fallback else None,
            "physics_system+0x44": execution.aux_storage if not execution.fallback else None,
            "per_body+0xa8": execution.secondary_domain,
        },
    }

if __name__ == "__main__":
    import json
    print(json.dumps(build_fun_007b3820_backend_contract(), indent=2, sort_keys=True))
