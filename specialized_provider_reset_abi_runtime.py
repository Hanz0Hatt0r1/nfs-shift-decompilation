"""Exact reset-dispatch ABI for the specialized provider vtables.

The reset slots at vtable +0x1c point to switch-based functions taking one
32-bit selector. Phase 475 makes that selector-to-case mapping explicit.
"""
from __future__ import annotations

import re
from typing import Any

from specialized_provider_runtime import get_provider
from specialized_provider_storage_runtime import get_storage_layout
from specialized_provider_vtable_lifecycle_runtime import get_vtable_lifecycle

FORMAT = "SHIFT.SpecializedProviderResetABIRuntime/1"

RESET_ABI = {
    0: {
        "function": "FUN_007d3150",
        "signature": "void FUN_007d3150(undefined4 param_1)",
        "selector": "param_1",
        "case_min": 0,
        "case_max": 39,
    },
    1: {
        "function": "FUN_007d48a0",
        "signature": "void FUN_007d48a0(undefined4 param_1)",
        "selector": "param_1",
        "case_min": 0,
        "case_max": 33,
    },
}

HEADER_RE = re.compile(
    r"^void\s+(FUN_[0-9A-Fa-f]{8})\(undefined4\s+param_1\)\n",
    re.M,
)
CASE_RE = re.compile(
    r"^\s*case\s+(0x[0-9A-Fa-f]+|\d+):\s*$",
    re.M,
)
DEFAULT_RE = re.compile(
    r"^\s*default:\s*$",
    re.M,
)


def get_reset_abi(provider_id: int) -> dict[str, Any]:
    try:
        return dict(RESET_ABI[provider_id])
    except KeyError as exc:
        raise ValueError(f"unsupported provider id: {provider_id}") from exc


def parse_reset_dispatch(
    source: str,
    *,
    provider_id: int,
) -> dict[str, Any]:
    abi = get_reset_abi(provider_id)
    layout = get_storage_layout(provider_id)
    lifecycle = get_vtable_lifecycle(provider_id)

    marker = re.search(
        rf"^void\s+{re.escape(abi['function'])}\(undefined4\s+param_1\)\n",
        source,
        re.M,
    )
    errors: list[str] = []
    if marker is None:
        return {
            "format": FORMAT,
            "version": 1,
            "provider_id": provider_id,
            "function": abi["function"],
            "cases": [],
            "ready": False,
            "errors": ["reset-function-header-not-found"],
        }

    tail = source[marker.start():]
    end = tail.find("\n}\n")
    if end < 0:
        errors.append("reset-function-closing-boundary-not-found")
        body = tail
    else:
        body = tail[: end + 3]

    header = HEADER_RE.search(body)
    if header is None:
        errors.append("reset-function-signature-not-parsed")

    cases = [
        int(value, 0)
        for value in CASE_RE.findall(body)
    ]
    cases.sort()

    expected = list(range(abi["case_min"], abi["case_max"] + 1))
    if cases != expected:
        errors.append(
            f"case-domain-mismatch:expected={expected[0]}..{expected[-1]}:"
            f"actual={cases}"
        )

    if DEFAULT_RE.search(body):
        errors.append("unexpected-default-case")

    if lifecycle.slots.get(0x1C) != {
        0: 0x007D3150,
        1: 0x007D48A0,
    }[provider_id]:
        errors.append("reset-vtable-slot-mismatch")

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": provider_id,
        "function": abi["function"],
        "signature": abi["signature"],
        "selector": abi["selector"],
        "vtable_offset": "0x1c",
        "vtable_function": hex(lifecycle.slots[0x1C]),
        "scalar_count": layout.scalar_count,
        "case_min": abi["case_min"],
        "case_max": abi["case_max"],
        "case_count": len(cases),
        "cases": cases,
        "has_default": DEFAULT_RE.search(body) is not None,
        "ready": not errors,
        "errors": errors,
    }


def validate_reset_dispatch(report: dict[str, Any]) -> dict[str, Any]:
    errors = list(report.get("errors") or [])
    scalar_count = int(report.get("scalar_count", 0))
    case_count = int(report.get("case_count", 0))

    if case_count != scalar_count:
        errors.append(
            f"case-count-does-not-equal-scalar-count:{case_count}:{scalar_count}"
        )

    cases = [
        int(value)
        for value in report.get("cases") or []
    ]
    if cases != list(range(scalar_count)):
        errors.append("reset-case-order-not-sequential")

    if report.get("has_default"):
        errors.append("reset-default-case-present")

    return {
        "format": "SHIFT.SpecializedProviderResetABIValidation/1",
        "version": 1,
        "provider_id": report.get("provider_id"),
        "ready": not errors,
        "errors": errors,
    }


def build_reset_abi_contract(source: str) -> dict[str, Any]:
    providers: list[dict[str, Any]] = []
    for provider_id in (0, 1):
        report = parse_reset_dispatch(
            source,
            provider_id=provider_id,
        )
        report["validation"] = validate_reset_dispatch(report)
        providers.append(report)

    return {
        "format": FORMAT,
        "version": 1,
        "source_file": "SHIFT.exe.c",
        "providers": providers,
        "dispatch": {
            "vtable_slot": "+0x1c",
            "selector_parameter": "param_1",
            "provider0_domain": "0..39",
            "provider1_domain": "0..33",
            "default_case": "absent",
        },
        "limitations": [
            "The selector is recorded as an opaque 32-bit parameter; its semantic name remains unresolved.",
            "Case number is proven to select one reset block but is not independently named as a matrix pivot.",
            "No C++ class hierarchy or physical unit is inferred.",
        ],
        "status": "source-backed-specialized-provider-reset-abi",
    }


__all__ = [
    "FORMAT",
    "RESET_ABI",
    "get_reset_abi",
    "parse_reset_dispatch",
    "validate_reset_dispatch",
    "build_reset_abi_contract",
]
