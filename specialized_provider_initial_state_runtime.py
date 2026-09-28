"""Analyze read-before-write requirements of specialized-provider solver state.

Phase 456 uses the Phase 450 contextual assignment stream and the actual
absolute storage addresses to determine which workspace/output locations are
read before they are written during solver execution.

This is an address-level liveness/initial-state analysis. It deliberately avoids
assigning semantic matrix meaning to packed storage aliases.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from specialized_provider_contextual_dependency_runtime import (
    build_contextual_dependency_contract,
)
from specialized_provider_storage_runtime import get_storage_layout

FORMAT = "SHIFT.SpecializedProviderInitialStateRuntime/1"


def _address(reference: dict[str, Any]) -> int | None:
    value = reference.get("address")
    if value is None:
        return None
    return int(str(value), 16)


def analyze_initial_state(
    source: str,
    *,
    provider_id: int,
) -> dict[str, Any]:
    layout = get_storage_layout(provider_id)
    contextual = build_contextual_dependency_contract(source)
    provider_report = next(
        report
        for report in contextual["providers"]
        if int(report["provider_id"]) == provider_id
    )

    errors = list(provider_report.get("errors") or [])
    written: set[tuple[str, int]] = set()
    first_reads: dict[tuple[str, int], dict[str, Any]] = {}
    events: list[dict[str, Any]] = []

    for assignment in provider_report.get("assignments") or []:
        pivot = int(assignment["pivot_index"])
        source_line = int(assignment["source_line"])
        destination = dict(assignment["destination"])
        destination_address = _address(destination)

        reads: list[dict[str, Any]] = []
        for reference in assignment.get("rhs") or []:
            address = _address(reference)
            domain = str(reference.get("domain"))
            if address is None:
                reads.append(
                    {
                        "domain": domain,
                        "availability": "unknown-address",
                    }
                )
                continue

            key = (domain, address)
            availability = (
                "previously-written"
                if key in written
                else "preexisting-or-external"
            )
            item = dict(reference)
            item["availability"] = availability
            reads.append(item)

            if availability == "preexisting-or-external":
                first_reads.setdefault(
                    key,
                    {
                        "domain": domain,
                        "address": hex(address),
                        "first_pivot": pivot,
                        "first_source_line": source_line,
                    },
                )

        events.append(
            {
                "pivot_index": pivot,
                "source_line": source_line,
                "loop_index": assignment.get("loop_index"),
                "destination": destination,
                "rhs_reads": reads,
            }
        )

        if destination_address is not None:
            written.add(
                (
                    str(destination.get("domain")),
                    destination_address,
                )
            )

    workspace_initial = [
        value
        for (domain, _address_value), value in sorted(first_reads.items())
        if domain == "workspace"
    ]
    output_initial = [
        value
        for (domain, _address_value), value in sorted(first_reads.items())
        if domain == "output_vector"
    ]
    global_initial = [
        value
        for (domain, _address_value), value in sorted(first_reads.items())
        if domain not in {"workspace", "output_vector"}
    ]

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": provider_id,
        "function": provider_report.get("function"),
        "scalar_count": layout.scalar_count,
        "assignment_count": len(events),
        "events": events,
        "first_read_addresses": list(first_reads.values()),
        "initial_state": {
            "workspace_addresses": workspace_initial,
            "output_vector_addresses": output_initial,
            "global_addresses": global_initial,
        },
        "ready": not errors,
        "errors": errors,
    }


def summarize_initial_state(report: dict[str, Any]) -> dict[str, Any]:
    initial = report.get("initial_state") or {}
    workspace = initial.get("workspace_addresses") or []
    output = initial.get("output_vector_addresses") or []
    global_values = initial.get("global_addresses") or []

    return {
        "provider_id": report.get("provider_id"),
        "scalar_count": report.get("scalar_count"),
        "assignments": report.get("assignment_count"),
        "first_read_addresses": len(report.get("first_read_addresses") or []),
        "workspace_preexisting_or_external": len(workspace),
        "output_preexisting_or_external": len(output),
        "global_preexisting_or_external": len(global_values),
        "ready": bool(report.get("ready")),
    }


def validate_initial_state(report: dict[str, Any]) -> dict[str, Any]:
    errors = list(report.get("errors") or [])
    scalar_count = int(report.get("scalar_count", 0))

    seen_first: set[tuple[str, str]] = set()
    for entry in report.get("first_read_addresses") or []:
        domain = str(entry.get("domain"))
        address = str(entry.get("address"))
        key = (domain, address)
        if key in seen_first:
            errors.append(
                f"duplicate-first-read:{domain}:{address}"
            )
        seen_first.add(key)

    for event in report.get("events") or []:
        pivot = int(event.get("pivot_index", -1))
        if pivot < 0 or pivot >= scalar_count:
            errors.append(f"event-{event.get('source_line')}-pivot-out-of-range")

        for reference in event.get("rhs_reads") or []:
            availability = reference.get("availability")
            if availability == "unknown-address":
                errors.append(
                    f"event-{event.get('source_line')}-unknown-rhs-address"
                )

    return {
        "format": "SHIFT.SpecializedProviderInitialStateValidation/1",
        "version": 1,
        "provider_id": report.get("provider_id"),
        "ready": not errors,
        "errors": errors,
        "events": len(report.get("events") or []),
        "first_reads": len(report.get("first_read_addresses") or []),
    }


def build_initial_state_contract(source: str) -> dict[str, Any]:
    providers: list[dict[str, Any]] = []
    for provider_id in (0, 1):
        report = analyze_initial_state(
            source,
            provider_id=provider_id,
        )
        report["summary"] = summarize_initial_state(report)
        report["validation"] = validate_initial_state(report)
        providers.append(report)

    return {
        "format": FORMAT,
        "version": 1,
        "source_file": "SHIFT.exe.c",
        "providers": providers,
        "scope": {
            "analysis": "absolute-address read-before-write",
            "availability": "previously-written vs preexisting-or-external",
            "semantic_ownership": "unresolved",
        },
        "limitations": [
            "A preexisting-or-external address is not necessarily a solver input; it may be a runtime-generated intermediate established by an earlier caller.",
            "Address reuse through packed aliases is tracked by absolute address, not guessed logical row/column ownership.",
            "No physical matrix meaning or coefficient semantics are inferred.",
        ],
        "status": "source-backed-read-before-write-analysis",
    }


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()

    contract = build_initial_state_contract(
        args.source.read_text(encoding="utf-8")
    )
    print(json.dumps(contract, indent=2, sort_keys=True))
    ready = all(
        provider["validation"]["ready"]
        for provider in contract["providers"]
    )
    raise SystemExit(0 if ready else 2)
