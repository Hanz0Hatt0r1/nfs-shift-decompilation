"""Extract zero-baseline cleanup coverage for specialized provider storage.

Phase 467 decodes the provider teardown/cleanup helpers that clear packed
workspace and output-vector state. Coverage is represented as exact bulk-clear
intervals plus direct zero assignments inside the known provider regions.

Direct zero assignments are counted as one solver double only when their address
falls inside the provider workspace/output regions; outside those regions they
remain address-only evidence.
"""
from __future__ import annotations

import re
from typing import Any

from specialized_provider_row_storage_runtime import get_row_pointers
from specialized_provider_storage_runtime import get_storage_layout

FORMAT = "SHIFT.SpecializedProviderZeroBaselineRuntime/1"

CLEANUP_FUNCTIONS = {
    0: "FUN_007d43c0",
    1: "FUN_007d5600",
}

BULK_CLEAR_RE = re.compile(
    r"FUN_0040cec0\(&DAT_([0-9A-Fa-f]+),0,(0x[0-9A-Fa-f]+|\d+)\);"
)
DIRECT_ZERO_RE = re.compile(
    r"(?:_)?DAT_([0-9A-Fa-f]+)\s*=\s*0;"
)


def _extract_function_body(source: str, function_name: str) -> str:
    marker = re.search(
        rf"void {re.escape(function_name)}\(void\)\n",
        source,
    )
    if marker is None:
        raise ValueError(f"cleanup function not found: {function_name}")

    tail = source[marker.start():]
    end = tail.find("\n}\n")
    if end < 0:
        raise ValueError(
            f"cleanup function closing boundary not found: {function_name}"
        )
    return tail[: end + 3]


def _interval_coverage(
    intervals: list[tuple[int, int]],
    *,
    start: int,
    end: int,
) -> tuple[list[tuple[int, int]], int]:
    clipped: list[tuple[int, int]] = []
    for address, size in intervals:
        interval_start = max(int(address), int(start))
        interval_end = min(int(address) + int(size), int(end))
        if interval_start < interval_end:
            clipped.append((interval_start, interval_end))

    clipped.sort()
    merged: list[tuple[int, int]] = []
    for interval_start, interval_end in clipped:
        if not merged or interval_start > merged[-1][1]:
            merged.append((interval_start, interval_end))
        elif interval_end > merged[-1][1]:
            previous_start, _ = merged[-1]
            merged[-1] = (previous_start, interval_end)

    return merged, sum(end - start for start, end in merged)


def _coverage_for_region(
    bulk: list[tuple[int, int]],
    direct: list[int],
    *,
    start: int,
    end: int,
) -> dict[str, Any]:
    merged, bulk_covered_bytes = _interval_coverage(
        bulk,
        start=start,
        end=end,
    )

    direct_addresses = sorted(
        {
            int(address)
            for address in direct
            if start <= int(address) < end
            and (int(address) - start) % 8 == 0
        }
    )

    covered_slots = {
        address
        for interval_start, interval_end in merged
        for address in range(interval_start, interval_end, 8)
        if interval_start <= address < interval_end
    }
    covered_slots.update(direct_addresses)

    total_bytes = int(end) - int(start)
    total_doubles = total_bytes // 8
    return {
        "start": hex(start),
        "end": hex(end),
        "bytes": total_bytes,
        "doubles": total_doubles,
        "bulk_clear_interval_count": len(merged),
        "bulk_covered_bytes": bulk_covered_bytes,
        "bulk_covered_doubles": bulk_covered_bytes // 8,
        "direct_zero_slot_count": len(direct_addresses),
        "covered_doubles": len(covered_slots),
        "uncovered_doubles": total_doubles - len(covered_slots),
        "coverage_ratio": (
            len(covered_slots) / total_doubles
            if total_doubles
            else 1.0
        ),
        "merged_intervals": [
            {
                "start": hex(interval_start),
                "end": hex(interval_end),
                "bytes": interval_end - interval_start,
            }
            for interval_start, interval_end in merged
        ],
        "direct_zero_addresses": [
            hex(address)
            for address in direct_addresses
        ],
    }


def extract_zero_baseline_profile(
    source: str,
    *,
    provider_id: int,
) -> dict[str, Any]:
    try:
        function_name = CLEANUP_FUNCTIONS[provider_id]
    except KeyError as exc:
        raise ValueError(f"unsupported provider id: {provider_id}") from exc

    layout = get_storage_layout(provider_id)
    body = _extract_function_body(source, function_name)

    bulk = [
        (int(address, 16), int(size, 0))
        for address, size in BULK_CLEAR_RE.findall(body)
    ]
    direct = [
        int(address, 16)
        for address in DIRECT_ZERO_RE.findall(body)
    ]

    workspace = _coverage_for_region(
        bulk,
        direct,
        start=layout.factor_workspace_base,
        end=layout.output_vector_base,
    )
    output = _coverage_for_region(
        bulk,
        direct,
        start=layout.output_vector_base,
        end=layout.output_vector_base + layout.output_vector_bytes,
    )

    pointers = get_row_pointers(provider_id)
    row_coverage: list[dict[str, Any]] = []
    for row, row_start in enumerate(pointers):
        row_end = (
            pointers[row + 1]
            if row + 1 < len(pointers)
            else layout.output_vector_base
        )
        row_region = _coverage_for_region(
            bulk,
            direct,
            start=row_start,
            end=row_end,
        )
        row_region["row"] = row
        row_region["row_pointer"] = hex(row_start)
        row_coverage.append(row_region)

    errors: list[str] = []
    if len(pointers) != layout.scalar_count:
        errors.append(
            f"row-pointer-count:expected={layout.scalar_count}:actual={len(pointers)}"
        )

    if output["uncovered_doubles"] != 0:
        errors.append("output-vector-not-fully-cleared")

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": provider_id,
        "cleanup_function": function_name,
        "scalar_count": layout.scalar_count,
        "bulk_clear_count": len(bulk),
        "direct_zero_assignment_count": len(direct),
        "workspace": workspace,
        "output_vector": output,
        "row_coverage": row_coverage,
        "ready": not errors,
        "errors": errors,
    }


def summarize_zero_baseline(report: dict[str, Any]) -> dict[str, Any]:
    workspace = report.get("workspace") or {}
    output = report.get("output_vector") or {}
    return {
        "provider_id": report.get("provider_id"),
        "cleanup_function": report.get("cleanup_function"),
        "scalar_count": report.get("scalar_count"),
        "bulk_clear_count": report.get("bulk_clear_count"),
        "direct_zero_assignment_count": report.get(
            "direct_zero_assignment_count"
        ),
        "workspace_covered_doubles": workspace.get("covered_doubles"),
        "workspace_total_doubles": workspace.get("doubles"),
        "workspace_uncovered_doubles": workspace.get("uncovered_doubles"),
        "workspace_coverage_ratio": workspace.get("coverage_ratio"),
        "output_covered_doubles": output.get("covered_doubles"),
        "output_total_doubles": output.get("doubles"),
        "output_coverage_ratio": output.get("coverage_ratio"),
        "ready": bool(report.get("ready")),
    }


def validate_zero_baseline(report: dict[str, Any]) -> dict[str, Any]:
    errors = list(report.get("errors") or [])
    scalar_count = int(report.get("scalar_count", 0))
    row_coverage = report.get("row_coverage") or []

    if len(row_coverage) != scalar_count:
        errors.append(
            f"row-coverage-count:expected={scalar_count}:actual={len(row_coverage)}"
        )

    workspace = report.get("workspace") or {}
    output = report.get("output_vector") or {}

    for name, region in (("workspace", workspace), ("output_vector", output)):
        doubles = int(region.get("doubles", 0))
        covered = int(region.get("covered_doubles", 0))
        uncovered = int(region.get("uncovered_doubles", 0))
        if covered + uncovered != doubles:
            errors.append(f"{name}-coverage-partition-mismatch")

    if int(output.get("uncovered_doubles", 0)) != 0:
        errors.append("output-vector-baseline-incomplete")

    return {
        "format": "SHIFT.SpecializedProviderZeroBaselineValidation/1",
        "version": 1,
        "provider_id": report.get("provider_id"),
        "ready": not errors,
        "errors": errors,
        "rows": len(row_coverage),
    }


def build_zero_baseline_contract(source: str) -> dict[str, Any]:
    providers: list[dict[str, Any]] = []
    for provider_id in (0, 1):
        report = extract_zero_baseline_profile(
            source,
            provider_id=provider_id,
        )
        report["summary"] = summarize_zero_baseline(report)
        report["validation"] = validate_zero_baseline(report)
        providers.append(report)

    return {
        "format": FORMAT,
        "version": 1,
        "source_file": "SHIFT.exe.c",
        "providers": providers,
        "scope": {
            "bulk_zero": "exact FUN_0040cec0 base/size intervals",
            "direct_zero": "direct DAT_xxxxxxxx = 0 stores; treated as one double only inside known provider storage regions",
            "baseline": "cleanup-time zero coverage, before subsequent reset/solve state",
        },
        "limitations": [
            "Cleanup coverage proves only that these storage locations are cleared by the cleanup function.",
            "It does not prove that every uncovered workspace slot is semantically live or input-bearing.",
            "The 8-byte direct-zero interpretation is applied only inside provider solver storage regions whose solve accesses are already established as binary64.",
        ],
        "status": "source-backed-specialized-provider-zero-baseline",
    }


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()

    contract = build_zero_baseline_contract(
        args.source.read_text(encoding="utf-8")
    )
    print(json.dumps(contract, indent=2, sort_keys=True))
    ready = all(
        provider["validation"]["ready"]
        for provider in contract["providers"]
    )
    raise SystemExit(0 if ready else 2)
