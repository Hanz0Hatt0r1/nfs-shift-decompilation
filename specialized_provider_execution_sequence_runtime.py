"""Exact source-level execution sequence inside FUN_007b3f40.

Phase 483 corrects the lifecycle model: FUN_007b2210 resets each active
constraint scalar, and provider mode delegates that selector to vtable +0x1c.
"""
from __future__ import annotations

from typing import Any

FORMAT = "SHIFT.SpecializedProviderExecutionSequenceRuntime/1"

SEQUENCE = (
    {
        "index": 0,
        "stage": "backend-branch",
        "function": "FUN_007b3f40",
        "condition": "physics_system+0x48 == 0",
        "builtin_action": "zero matrix rows through physics_system+0x3c and zero rhs through +0x40",
        "provider_action": "call provider vtable +0x20 cleanup",
    },
    {
        "index": 1,
        "stage": "common-preparation",
        "function": "FUN_007b3ed0",
        "count_source": None,
        "stride": None,
    },
    {
        "index": 2,
        "stage": "body-preparation",
        "function": "FUN_007bb8d0",
        "count_source": "physics_system+0x10",
        "stride": 0x170,
        "object_base": "physics_system+0x14",
    },
    {
        "index": 3,
        "stage": "body-preparation",
        "function": "FUN_007bc680",
        "count_source": "physics_system+0x10",
        "stride": 0x170,
        "object_base": "physics_system+0x14",
    },
    {
        "index": 4,
        "stage": "body-preparation",
        "function": "FUN_007ba570",
        "count_source": "physics_system+0x10",
        "stride": 0x170,
        "object_base": "physics_system+0x14",
        "extra_args": (
            "physics_system+0x40",
            "physics_system+0x44",
        ),
    },
    {
        "index": 5,
        "stage": "joint-hinge-scalar-reset-dispatch",
        "function": "FUN_007b2210",
        "count_source": "physics_system+0x18",
        "stride": 0xA0,
        "object_base": "physics_system+0x1c",
        "width": "3 when (record+0x70 & 1) != 0",
        "reset_dispatch": "FUN_007b2210(selector)",
        "provider_reset": "vtable +0x1c(selector)",
        "builtin_reset": "row/column clear + diagonal 1.0 + rhs zero",
    },
    {
        "index": 6,
        "stage": "secondary-scalar-reset-dispatch",
        "function": "FUN_007b2210",
        "count_source": "physics_system+0x20",
        "stride": 0xA0,
        "object_base": "physics_system+0x24",
        "width": "2 when (record+0x70 & 1) != 0",
        "reset_dispatch": "FUN_007b2210(selector)",
        "provider_reset": "vtable +0x1c(selector)",
        "builtin_reset": "row/column clear + diagonal 1.0 + rhs zero",
    },
    {
        "index": 7,
        "stage": "bar-scalar-reset-dispatch",
        "function": "FUN_007b2210",
        "count_source": "physics_system+0x28",
        "stride": 0xB8,
        "object_base": "physics_system+0x2c",
        "width": "1 when (record+0x70 & 1) != 0",
        "reset_dispatch": "FUN_007b2210(selector)",
        "provider_reset": "vtable +0x1c(selector)",
        "builtin_reset": "row/column clear + diagonal 1.0 + rhs zero",
    },
    {
        "index": 8,
        "stage": "backend-dispatch",
        "function": "FUN_007b3f40",
        "condition": "physics_system+0x48 != 0",
        "provider_action": "call provider vtable +0x18 solve",
        "builtin_action": "otherwise call FUN_007b0f20(this=physics_system+0x4c, +0x3c, +0x40, +0x34)",
    },
)


def build_execution_sequence() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "function": "FUN_007b3f40",
        "source_line": 814057,
        "steps": [dict(step) for step in SEQUENCE],
        "branching": {
            "provider_selected": "physics_system+0x48 != 0",
            "provider_cleanup": "vtable +0x20",
            "provider_scalar_reset": "vtable +0x1c via FUN_007b2210",
            "provider_solve": "vtable +0x18",
            "builtin_reset": "zero matrix/rhs inline",
            "builtin_solve": "FUN_007b0f20",
        },
        "loop_domains": {
            "BODY": {
                "count_field": "+0x10",
                "stride": "0x170",
            },
            "JOINT/HINGE": {
                "count_field": "+0x18",
                "stride": "0xa0",
            },
            "BAR": {
                "count_field": "+0x28",
                "stride": "0xb8",
            },
        },
        "status": "source-backed-provider-execution-sequence",
    }


def validate_execution_sequence() -> dict[str, Any]:
    errors: list[str] = []
    if [step["index"] for step in SEQUENCE] != list(range(len(SEQUENCE))):
        errors.append("step-index-order-mismatch")

    if SEQUENCE[0]["provider_action"] != "call provider vtable +0x20 cleanup":
        errors.append("provider-cleanup-boundary-mismatch")
    if SEQUENCE[-1]["provider_action"] != "call provider vtable +0x18 solve":
        errors.append("provider-solve-boundary-mismatch")

    expected = {
        "BODY": (0x10, 0x170),
        "JOINT/HINGE": (0x18, 0xA0),
        "BAR": (0x28, 0xB8),
    }
    for name, (count_field, stride) in expected.items():
        domain = next(
            domain
            for domain in build_execution_sequence()["loop_domains"]
            if domain == name
        )
        entry = build_execution_sequence()["loop_domains"][domain]
        observed_field = int(entry["count_field"].replace("+0x", ""), 16)
        observed_stride = int(entry["stride"], 16)
        if observed_field != count_field:
            errors.append(f"{name}-count-field-mismatch")
        if observed_stride != stride:
            errors.append(f"{name}-stride-mismatch")

    return {
        "format": "SHIFT.SpecializedProviderExecutionSequenceValidation/1",
        "version": 1,
        "ready": not errors,
        "errors": errors,
    }


def build_execution_sequence_contract() -> dict[str, Any]:
    validation = validate_execution_sequence()
    return {
        "format": FORMAT,
        "version": 1,
        "function": "FUN_007b3f40",
        "sequence": build_execution_sequence(),
        "validation": validation,
        "interpretation": {
            "provider_path": "cleanup + common preparation + per-scalar FUN_007b2210 reset dispatch + solve",
            "builtin_path": "inline matrix/rhs clear + common preparation + per-scalar FUN_007b2210 row/column reset + builtin solve",
        },
        "limitations": [
            "Common preparation callees are identified by function address only.",
            "FUN_007b2210 is represented by exact call topology and reset semantics; coefficient population remains separate.",
            "No timing, thread scheduling, or C++ class identity is inferred.",
        ],
    }


__all__ = [
    "FORMAT",
    "SEQUENCE",
    "build_execution_sequence",
    "validate_execution_sequence",
    "build_execution_sequence_contract",
]
