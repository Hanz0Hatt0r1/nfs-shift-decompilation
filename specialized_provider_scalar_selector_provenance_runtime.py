"""Constraint-to-scalar selector provenance for FUN_007b2210.

Phase 484 records exactly which constraint-record fields produce the scalar
selector passed to the per-scalar reset dispatcher. It does not rename those
fields as matrix coordinates.
"""
from __future__ import annotations

from typing import Any

FORMAT = "SHIFT.SpecializedProviderScalarSelectorProvenanceRuntime/1"

GROUPS = (
    {
        "group": "JOINT/HINGE",
        "source_line": 814124,
        "record_base": "physics_system+0x1c",
        "record_stride": 0xA0,
        "enabled_flag": "record+0x70 & 1",
        "selector_expression": "*(int *)(*(int *)(record+0x7c)+0x30)",
        "source_field_path": ("+0x7c", "+0x30"),
        "width": 3,
        "selector_calls": (
            "selector",
            "selector+1",
            "selector+2",
        ),
    },
    {
        "group": "SECONDARY",
        "source_line": 814138,
        "record_base": "physics_system+0x24",
        "record_stride": 0xA0,
        "enabled_flag": "record+0x70 & 1",
        "selector_expression": "*(int *)(*(int *)(record+0x7c)+0x94)",
        "source_field_path": ("+0x7c", "+0x94"),
        "width": 2,
        "selector_calls": (
            "selector",
            "selector+1",
        ),
    },
    {
        "group": "BAR",
        "source_line": 814150,
        "record_base": "physics_system+0x2c",
        "record_stride": 0xB8,
        "enabled_flag": "record+0x70 & 1",
        "selector_expression": "*(int *)(*(int *)(record+0x7c)+0x30)",
        "source_field_path": ("+0x7c", "+0x30"),
        "width": 1,
        "selector_calls": (
            "selector",
        ),
    },
)


def build_selector_provenance_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "dispatcher": {
            "function": "FUN_007b2210",
            "selector_parameter": "param_1",
            "provider_delegate": "vtable +0x1c(param_1)",
        },
        "groups": [dict(group) for group in GROUPS],
        "preconditions": {
            "enabled_constraint": "record+0x70 bit 0 must be set before selector is used",
            "selector_domain": "caller is expected to provide an in-domain scalar selector; FUN_007b2210 itself performs no bounds check",
        },
        "derived_widths": {
            "JOINT/HINGE": 3,
            "SECONDARY": 2,
            "BAR": 1,
        },
        "storage_relation": {
            "constraint_record_strides": {
                "JOINT/HINGE": "0xa0",
                "SECONDARY": "0xa0",
                "BAR": "0xb8",
            },
            "selector_sources": {
                "JOINT/HINGE": "(record+0x7c)->+0x30",
                "SECONDARY": "(record+0x7c)->+0x94",
                "BAR": "(record+0x7c)->+0x30",
            },
        },
        "limitations": [
            "The +0x30/+0x94 fields are recorded as selector sources only; no C++ field names are invented.",
            "The selector's semantic identity remains unresolved beyond its role as the FUN_007b2210 argument.",
            "No matrix row/column or physical quantity is inferred from the selector.",
        ],
        "status": "source-backed-scalar-selector-provenance",
    }


def validate_selector_provenance_contract() -> dict[str, Any]:
    errors: list[str] = []

    expected = {
        "JOINT/HINGE": (0xA0, 3, 814124),
        "SECONDARY": (0xA0, 2, 814138),
        "BAR": (0xB8, 1, 814150),
    }

    if len(GROUPS) != 3:
        errors.append("unexpected-selector-group-count")

    for group in GROUPS:
        name = group["group"]
        stride, width, line = expected[name]
        if group["record_stride"] != stride:
            errors.append(f"{name}-stride-mismatch")
        if group["width"] != width:
            errors.append(f"{name}-width-mismatch")
        if group["source_line"] != line:
            errors.append(f"{name}-source-line-mismatch")
        if len(group["selector_calls"]) != width:
            errors.append(f"{name}-selector-call-count-mismatch")

    return {
        "format": "SHIFT.SpecializedProviderScalarSelectorProvenanceValidation/1",
        "version": 1,
        "ready": not errors,
        "errors": errors,
    }


def build_selector_provenance_report() -> dict[str, Any]:
    validation = validate_selector_provenance_contract()
    return {
        "format": FORMAT,
        "version": 1,
        "contract": build_selector_provenance_contract(),
        "validation": validation,
    }


__all__ = [
    "FORMAT",
    "GROUPS",
    "build_selector_provenance_contract",
    "validate_selector_provenance_contract",
    "build_selector_provenance_report",
]
