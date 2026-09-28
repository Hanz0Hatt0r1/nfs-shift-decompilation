"""Parse exact FUN_007b2210 direct CALL sites from a retail PE disassembly.

Phase 495 keeps the source/disassembly callsite attribution reproducible. The
parser consumes objdump-style Intel disassembly for FUN_007b3f40 and emits call
and return addresses for direct calls to FUN_007b2210.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.SpecializedProviderScalarResetCallsiteExtractorRuntime/1"

CALL_RE = re.compile(
    r"^s*([0-9A-Fa-f]+):s*"
    r"((?:[0-9A-Fa-f]{2}s+)+)"
    r"calls+0x([0-9A-Fa-f]+)s*$"
)

DEFAULT_TARGET = 0x007B2210
DEFAULT_FUNCTION_START = 0x007B3F40
DEFAULT_FUNCTION_END = 0x007B410A


def parse_direct_calls(
    disassembly: str,
    *,
    target_address: int = DEFAULT_TARGET,
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    for line in disassembly.splitlines():
        match = CALL_RE.match(line)
        if match is None:
            continue

        call_address = int(match.group(1), 16)
        machine_bytes = bytes.fromhex(match.group(2))
        destination = int(match.group(3), 16)

        if destination != int(target_address):
            continue

        calls.append(
            {
                "call_address": call_address,
                "instruction_size": len(machine_bytes),
                "return_address": call_address + len(machine_bytes),
                "destination": destination,
            }
        )

    return calls


def extract_scalar_reset_callsites(
    disassembly: str,
    *,
    target_address: int = DEFAULT_TARGET,
    function_start: int = DEFAULT_FUNCTION_START,
    function_end: int = DEFAULT_FUNCTION_END,
) -> dict[str, Any]:
    calls = [
        call
        for call in parse_direct_calls(
            disassembly,
            target_address=target_address,
        )
        if int(function_start) <= int(call["call_address"]) < int(function_end)
    ]

    return {
        "format": FORMAT,
        "version": 1,
        "function": "FUN_007b3f40",
        "function_start": hex(int(function_start)),
        "function_end": hex(int(function_end)),
        "target_function": "FUN_007b2210",
        "target_address": hex(int(target_address)),
        "calls": calls,
        "call_count": len(calls),
        "return_addresses": [
            hex(int(call["return_address"]))
            for call in calls
        ],
        "ready": bool(calls),
        "status": "extracted" if calls else "no-target-calls-found",
    }


def compare_extracted_callsites(
    extracted: Mapping[str, Any],
    expected_return_addresses: Sequence[int],
) -> dict[str, Any]:
    observed = [
        int(str(address), 16)
        for address in extracted.get("return_addresses") or []
    ]
    expected = [int(address) for address in expected_return_addresses]

    return {
        "format": "SHIFT.SpecializedProviderScalarResetCallsiteExtractionComparison/1",
        "version": 1,
        "ready": observed == expected,
        "observed": [hex(address) for address in observed],
        "expected": [hex(address) for address in expected],
        "mismatch_count": sum(
            left != right
            for left, right in zip(observed, expected)
        )
        + abs(len(observed) - len(expected)),
    }


def validate_extracted_callsite_contract(
    extracted: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []

    calls = list(extracted.get("calls") or [])
    if not calls:
        errors.append("no-call-sites")

    for index, call in enumerate(calls):
        call_address = int(call["call_address"])
        instruction_size = int(call["instruction_size"])
        return_address = int(call["return_address"])
        destination = int(call["destination"])

        if instruction_size <= 0:
            errors.append(f"call-{index}-invalid-instruction-size")
        if return_address != call_address + instruction_size:
            errors.append(f"call-{index}-return-address-mismatch")
        if destination != DEFAULT_TARGET:
            errors.append(f"call-{index}-destination-mismatch")

    return {
        "format": "SHIFT.SpecializedProviderScalarResetCallsiteExtractionValidation/1",
        "version": 1,
        "ready": not errors,
        "call_count": len(calls),
        "errors": errors,
    }


def build_extractor_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "input": {
            "kind": "objdump Intel disassembly",
            "function": "FUN_007b3f40",
            "target": "FUN_007b2210",
        },
        "algorithm": {
            "instruction": "match direct call rel32 lines",
            "return_address": "call address + encoded instruction length",
            "scope": "function start inclusive, function end exclusive",
        },
        "defaults": {
            "target_address": hex(DEFAULT_TARGET),
            "function_start": hex(DEFAULT_FUNCTION_START),
            "function_end": hex(DEFAULT_FUNCTION_END),
        },
        "status": "source-and-binary-backed-callsite-extractor",
    }


__all__ = [
    "FORMAT",
    "CALL_RE",
    "DEFAULT_TARGET",
    "DEFAULT_FUNCTION_START",
    "DEFAULT_FUNCTION_END",
    "parse_direct_calls",
    "extract_scalar_reset_callsites",
    "compare_extracted_callsites",
    "validate_extracted_callsite_contract",
    "build_extractor_contract",
]
