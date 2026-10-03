"""Fail-closed static contract for the SDF provider dispatch boundary.

This module composes already recovered static facts without requiring game
execution.  It deliberately distinguishes a proven virtual slot from the
runtime-selected concrete implementation behind that slot.
"""
from __future__ import annotations

import json
from typing import Any

FORMAT = "SHIFT.ProviderDispatchStaticContract/1"
EVIDENCE_STATES = ("proven", "verified", "inferred", "ambiguous", "unknown")

PHYSICS_SYSTEM_PROVIDER_OFFSET = 0x48
PROVIDER_SELECTOR = 0x007D2E70
BUILTIN_SOLVER = 0x007B0F20

PROVIDERS: dict[int, dict[str, Any]] = {
    0: {
        "selector_global": "DAT_00c23da8",
        "vtable": 0x00B0FC5C,
        "slots": {
            0x14: 0x007C6E50,
            0x18: 0x007C7200,
            0x1C: 0x007D3150,
            0x20: 0x007D43C0,
        },
    },
    1: {
        "selector_global": "DAT_00c23dac",
        "vtable": 0x00B0FC8C,
        "slots": {
            0x14: 0x007CDB40,
            0x18: 0x007CDFC0,
            0x1C: 0x007D48A0,
            0x20: 0x007D5600,
        },
    },
}

SLOT_ROLES = {
    0x14: "acceptance",
    0x18: "solve",
    0x1C: "per-scalar-reset",
    0x20: "cleanup",
}

DISPATCH_SITES: dict[str, dict[str, Any]] = {
    "FUN_007b3820.acceptance": {
        "function": 0x007B3820,
        "provider_base": "selected candidate from FUN_007d2e70(index)",
        "vtable_slot": 0x14,
        "arguments": ["physics_system+0x3c"],
        "evidence_state": "proven",
        "instruction_address": None,
        "instruction_evidence_state": "unknown",
    },
    "FUN_007b3f40.cleanup": {
        "function": 0x007B3F40,
        "provider_base": "physics_system+0x48",
        "vtable_slot": 0x20,
        "arguments": [],
        "evidence_state": "proven",
        "instruction_address": None,
        "instruction_evidence_state": "unknown",
    },
    "FUN_007b2210.reset": {
        "function": 0x007B2210,
        "provider_base": "physics_system+0x48",
        "vtable_slot": 0x1C,
        "arguments": ["constraint scalar selector"],
        "evidence_state": "proven",
        "instruction_address": None,
        "instruction_evidence_state": "unknown",
    },
    "FUN_007b3f40.solve": {
        "function": 0x007B3F40,
        "provider_base": "physics_system+0x48",
        "vtable_slot": 0x18,
        "arguments": [],
        "evidence_state": "proven",
        "instruction_address": None,
        "instruction_evidence_state": "unknown",
    },
}


def concrete_targets_for_slot(slot: int) -> tuple[int, ...]:
    """Return the exact shipped-PE implementations for a proven provider slot."""
    if slot not in SLOT_ROLES:
        raise ValueError(f"unsupported provider vtable slot: 0x{slot:x}")
    return tuple(PROVIDERS[index]["slots"][slot] for index in sorted(PROVIDERS))


def dispatch_site_contract(name: str) -> dict[str, Any]:
    if name not in DISPATCH_SITES:
        raise KeyError(name)
    site = DISPATCH_SITES[name]
    slot = int(site["vtable_slot"])
    return {
        **site,
        "function": hex(int(site["function"])),
        "vtable_slot": hex(slot),
        "slot_role": SLOT_ROLES[slot],
        "conditional_targets": [hex(value) for value in concrete_targets_for_slot(slot)],
        "target_set_evidence_state": "verified",
        "target_selection": "runtime-dependent provider identity",
    }


def validate_contract() -> dict[str, Any]:
    errors: list[str] = []

    if tuple(sorted(PROVIDERS)) != (0, 1):
        errors.append("provider-domain-must-be-exactly-0-1")

    vtables = [int(PROVIDERS[index]["vtable"]) for index in sorted(PROVIDERS)]
    if len(set(vtables)) != 2:
        errors.append("provider-vtables-must-be-distinct")

    required_slots = set(SLOT_ROLES)
    for index, provider in PROVIDERS.items():
        slots = set(provider["slots"])
        if not required_slots.issubset(slots):
            missing = sorted(required_slots - slots)
            errors.append(
                f"provider-{index}-missing-slots:"
                + ",".join(hex(value) for value in missing)
            )

    for name, site in DISPATCH_SITES.items():
        state = site.get("evidence_state")
        instruction_state = site.get("instruction_evidence_state")
        if state not in EVIDENCE_STATES:
            errors.append(f"{name}:invalid-evidence-state")
        if instruction_state not in EVIDENCE_STATES:
            errors.append(f"{name}:invalid-instruction-evidence-state")
        if site.get("instruction_address") is None and instruction_state != "unknown":
            errors.append(f"{name}:missing-instruction-address-must-remain-unknown")
        slot = int(site["vtable_slot"])
        if slot not in required_slots:
            errors.append(f"{name}:unsupported-slot")
        if len(set(concrete_targets_for_slot(slot))) != 2:
            errors.append(f"{name}:target-set-must-contain-two-distinct-provider-targets")

    return {
        "format": "SHIFT.ProviderDispatchStaticContractValidation/1",
        "ready": not errors,
        "errors": errors,
    }


def targeted_instruction_export_plan() -> dict[str, Any]:
    """Freeze the narrow next export needed to turn callsite VA state into verified."""
    functions = sorted({int(site["function"]) for site in DISPATCH_SITES.values()})
    return {
        "format": "SHIFT.ProviderDispatchInstructionExportPlan/1",
        "functions": [hex(value) for value in functions],
        "required_observations": [
            {
                "function": hex(int(site["function"])),
                "provider_base": site["provider_base"],
                "vtable_slot": hex(int(site["vtable_slot"])),
                "current_state": site["instruction_evidence_state"],
            }
            for site in DISPATCH_SITES.values()
        ],
        "acceptance_rule": (
            "promote an instruction callsite only when the exported instruction/p-code "
            "shows the same provider base and exact vtable displacement"
        ),
        "fail_closed": True,
    }


def build_contract() -> dict[str, Any]:
    validation = validate_contract()
    return {
        "format": FORMAT,
        "version": 1,
        "evidence_policy": {
            "states": list(EVIDENCE_STATES),
            "offset_pattern_proves_object_identity": False,
            "callgraph_adjacency_proves_semantics": False,
            "runtime_selected_target_promoted_to_unique_target": False,
        },
        "provider_storage": {
            "physics_system_offset": hex(PHYSICS_SYSTEM_PROVIDER_OFFSET),
            "writer": "FUN_007b3820",
            "selector": hex(PROVIDER_SELECTOR),
            "selector_domain": [0, 1],
            "null_after_domain": True,
            "evidence_state": "proven",
        },
        "providers": [
            {
                "selector_index": index,
                "selector_global": provider["selector_global"],
                "vtable": hex(int(provider["vtable"])),
                "slots": {
                    hex(slot): {
                        "role": SLOT_ROLES[slot],
                        "target": hex(int(target)),
                        "evidence_state": "verified",
                    }
                    for slot, target in sorted(provider["slots"].items())
                },
            }
            for index, provider in sorted(PROVIDERS.items())
        ],
        "dispatch_sites": {
            name: dispatch_site_contract(name)
            for name in DISPATCH_SITES
        },
        "builtin_fallback": {
            "condition": "physics_system+0x48 == NULL",
            "target": hex(BUILTIN_SOLVER),
            "evidence_state": "proven",
        },
        "graph_effect": {
            "FUN_007b3f40_cleanup_targets": [hex(v) for v in concrete_targets_for_slot(0x20)],
            "FUN_007b2210_reset_targets": [hex(v) for v in concrete_targets_for_slot(0x1C)],
            "FUN_007b3f40_solve_targets": [hex(v) for v in concrete_targets_for_slot(0x18)],
            "unique_runtime_target_known_statically": False,
            "conditional_target_set_closed": True,
        },
        "native_port_handoff": {
            "ready_for_dispatch_interface": True,
            "provider_selection_must_remain_dynamic": True,
            "builtin_fallback_required": True,
            "provider_algorithms_out_of_scope": True,
        },
        "unresolved_blockers": [
            "exact instruction VAs for the four indirect dispatch callsites are not frozen in this contract",
            "runtime-selected provider identity is intentionally not predicted statically",
            "retail C++ class names and inheritance remain unknown",
        ],
        "targeted_export_plan": targeted_instruction_export_plan(),
        "validation": validation,
    }


def main() -> int:
    contract = build_contract()
    print(json.dumps(contract, indent=2, sort_keys=True))
    return 0 if contract["validation"]["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
