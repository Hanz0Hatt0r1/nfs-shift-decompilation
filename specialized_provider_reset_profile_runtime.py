"""Extract the static reset profile for specialized provider workspaces.

Phase 466 decodes the provider-specific reset helpers that seed each pivot
workspace with a unit diagonal and zero related storage. Phase 479 hardens the
parser so nested switch braces do not truncate the function.
"""
from __future__ import annotations

import re
from typing import Any

from specialized_provider_row_storage_runtime import get_row_pointers
from specialized_provider_storage_runtime import get_storage_layout

FORMAT = "SHIFT.SpecializedProviderResetProfileRuntime/1"

RESET_FUNCTIONS = {
    0: "FUN_007d3150",
    1: "FUN_007d48a0",
}

CASE_RE = re.compile(
    r"^\s*case\s+(0x[0-9A-Fa-f]+|\d+):\s*$",
    re.M,
)
ASSIGN_RE = re.compile(
    r"(?:_)?DAT_([0-9A-Fa-f]+)\s*=\s*([^;]+);"
)
CLEAR_RE = re.compile(
    r"FUN_0040cec0\(&DAT_([0-9A-Fa-f]+),0,(0x[0-9A-Fa-f]+|\d+)\);"
)


def _balanced_function_body(source: str, start: int) -> str:
    open_brace = source.find("{", start)
    if open_brace < 0:
        raise ValueError("function opening brace not found")

    depth = 0
    in_string = False
    escape = False
    for index in range(open_brace, len(source)):
        char = source[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]

    raise ValueError("function closing brace not found")


def _extract_function_block(source: str, function_name: str) -> str:
    marker = re.search(
        rf"void {re.escape(function_name)}\([^\n]+\)\n",
        source,
    )
    if marker is None:
        raise ValueError(f"reset function not found: {function_name}")
    return _balanced_function_body(source, marker.start())


def _case_blocks(function_block: str) -> list[tuple[int, str]]:
    matches = list(CASE_RE.finditer(function_block))
    cases: list[tuple[int, str]] = []

    for index, match in enumerate(matches):
        case = int(match.group(1), 0)
        start = match.end()
        end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(function_block)
        )
        cases.append((case, function_block[start:end]))
    return cases


def extract_reset_profile(
    source: str,
    *,
    provider_id: int,
) -> dict[str, Any]:
    try:
        function_name = RESET_FUNCTIONS[provider_id]
    except KeyError as exc:
        raise ValueError(f"unsupported provider id: {provider_id}") from exc

    layout = get_storage_layout(provider_id)
    pointers = get_row_pointers(provider_id)
    function_block = _extract_function_block(source, function_name)
    cases = _case_blocks(function_block)

    errors: list[str] = []
    if len(cases) != layout.scalar_count:
        errors.append(
            f"case-count:expected={layout.scalar_count}:actual={len(cases)}"
        )

    case_values = [case for case, _body in cases]
    if case_values != list(range(len(case_values))):
        errors.append("case-order-not-sequential")

    rows: list[dict[str, Any]] = []
    for case, body in cases:
        assignments = [
            (int(address, 16), value.strip())
            for address, value in ASSIGN_RE.findall(body)
        ]
        one_addresses = [
            address
            for address, value in assignments
            if value == "0x3ff0000000000000"
        ]
        zero_addresses = [
            address
            for address, value in assignments
            if value == "0"
        ]
        clears = [
            {
                "base": hex(int(address, 16)),
                "bytes": int(size, 0),
            }
            for address, size in CLEAR_RE.findall(body)
        ]

        if len(one_addresses) != 1:
            errors.append(
                f"case-{case}-unit-diagonal-count:{len(one_addresses)}"
            )
            diagonal_address = None
            diagonal_offset = None
        else:
            diagonal_address = one_addresses[0]
            if 0 <= case < len(pointers):
                diagonal_offset = diagonal_address - pointers[case]
                if diagonal_offset != case * 8:
                    errors.append(
                        f"case-{case}-diagonal-geometry:"
                        f"expected={hex(pointers[case] + case * 8)}:"
                        f"actual={hex(diagonal_address)}"
                    )
            else:
                diagonal_offset = None

        rows.append(
            {
                "pivot_index": case,
                "diagonal_address": (
                    None
                    if diagonal_address is None
                    else hex(diagonal_address)
                ),
                "diagonal_offset": diagonal_offset,
                "zero_assignment_count": len(zero_addresses),
                "zero_assignments": [
                    hex(address)
                    for address in zero_addresses
                ],
                "bulk_clear_count": len(clears),
                "bulk_clears": clears,
            }
        )

    rows.sort(key=lambda row: int(row["pivot_index"]))

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": provider_id,
        "reset_function": function_name,
        "scalar_count": layout.scalar_count,
        "rows": rows,
        "ready": not errors,
        "errors": errors,
    }


def summarize_reset_profile(report: dict[str, Any]) -> dict[str, Any]:
    rows = report.get("rows") or []
    return {
        "provider_id": report.get("provider_id"),
        "reset_function": report.get("reset_function"),
        "scalar_count": report.get("scalar_count"),
        "cases": len(rows),
        "unit_diagonal_cases": sum(
            row.get("diagonal_address") is not None
            for row in rows
        ),
        "zero_assignment_count": sum(
            int(row.get("zero_assignment_count", 0))
            for row in rows
        ),
        "bulk_clear_count": sum(
            int(row.get("bulk_clear_count", 0))
            for row in rows
        ),
        "ready": bool(report.get("ready")),
    }


def validate_reset_profile(report: dict[str, Any]) -> dict[str, Any]:
    errors = list(report.get("errors") or [])
    scalar_count = int(report.get("scalar_count", 0))
    rows = report.get("rows") or []

    if len(rows) != scalar_count:
        errors.append(
            f"row-count:expected={scalar_count}:actual={len(rows)}"
        )

    pivots = [int(row.get("pivot_index", -1)) for row in rows]
    if pivots != list(range(scalar_count)):
        errors.append("pivot-case-order-mismatch")

    for row in rows:
        pivot = int(row["pivot_index"])
        if row.get("diagonal_address") is None:
            errors.append(f"pivot-{pivot}-missing-unit-diagonal")

    return {
        "format": "SHIFT.SpecializedProviderResetProfileValidation/1",
        "version": 1,
        "provider_id": report.get("provider_id"),
        "ready": not errors,
        "errors": errors,
    }


def build_reset_profile_contract(source: str) -> dict[str, Any]:
    providers: list[dict[str, Any]] = []
    for provider_id in (0, 1):
        report = extract_reset_profile(
            source,
            provider_id=provider_id,
        )
        report["summary"] = summarize_reset_profile(report)
        report["validation"] = validate_reset_profile(report)
        providers.append(report)

    return {
        "format": FORMAT,
        "version": 1,
        "source_file": "SHIFT.exe.c",
        "providers": providers,
        "semantics": {
            "unit_diagonal": "source case writes the IEEE-754 binary64 value 1.0 exactly once",
            "zero_assignments": "direct storage locations written to zero",
            "bulk_clears": "FUN_0040cec0 base/byte-size calls recorded without semantic naming",
        },
        "limitations": [
            "A unit-diagonal reset does not prove that the workspace is the solver's input matrix.",
            "Zeroed storage can include staging/output-related cells and is not assigned a matrix meaning here.",
            "No provider class name or physical unit is inferred.",
        ],
        "status": "source-backed-specialized-provider-reset-profile",
    }


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()

    contract = build_reset_profile_contract(
        args.source.read_text(encoding="utf-8")
    )
    print(json.dumps(contract, indent=2, sort_keys=True))
    ready = all(
        provider["validation"]["ready"]
        for provider in contract["providers"]
    )
    raise SystemExit(0 if ready else 2)
