"""Extract the minimum caller-input candidates of specialized provider solvers.

Phase 472 joins read-before-write evidence (Phase 456) with the proven reset
storage domain (Phase 468). Workspace addresses first read by the solver are
classified as either reset-initialized or outside the reset domain.

Outside-reset workspace first reads are caller-input candidates, not asserted
matrix entries.
"""
from __future__ import annotations

from typing import Any

from specialized_provider_initial_state_runtime import (
    analyze_initial_state,
)
from specialized_provider_reset_profile_runtime import (
    extract_reset_profile,
)
from specialized_provider_storage_runtime import get_storage_layout

FORMAT = "SHIFT.SpecializedProviderInputFootprintRuntime/1"


def _reset_domain(
    reset_report: dict[str, Any],
) -> tuple[set[int], set[int]]:
    zero_addresses = {
        int(str(address), 16)
        for row in reset_report.get("rows") or []
        for address in row.get("zero_assignments") or []
    }
    unit_addresses = {
        int(str(row["diagonal_address"]), 16)
        for row in reset_report.get("rows") or []
        if row.get("diagonal_address") is not None
    }
    return zero_addresses | unit_addresses, unit_addresses


def _address(entry: dict[str, Any]) -> int:
    return int(str(entry["address"]), 16)


def extract_input_footprint(
    source: str,
    *,
    provider_id: int,
) -> dict[str, Any]:
    layout = get_storage_layout(provider_id)
    initial = analyze_initial_state(
        source,
        provider_id=provider_id,
    )
    reset = extract_reset_profile(
        source,
        provider_id=provider_id,
    )
    reset_domain, unit_addresses = _reset_domain(reset)

    errors = list(initial.get("errors") or [])
    errors.extend(reset.get("errors") or [])

    workspace_reads: list[dict[str, Any]] = []
    output_reads: list[dict[str, Any]] = []
    global_reads: list[dict[str, Any]] = []
    reset_workspace_reads: list[dict[str, Any]] = []
    caller_candidates: list[dict[str, Any]] = []
    malformed: list[dict[str, Any]] = []

    for entry in initial.get("first_read_addresses") or []:
        domain = str(entry.get("domain"))
        address_value = entry.get("address")
        if address_value is None:
            malformed.append(dict(entry))
            continue

        address = _address(entry)
        item = dict(entry)

        if domain == "workspace":
            if not (
                layout.factor_workspace_base
                <= address
                < layout.output_vector_base
            ):
                errors.append(
                    f"workspace-first-read-outside-workspace:{hex(address)}"
                )
                continue

            workspace_reads.append(item)
            if address in reset_domain:
                item["initialization"] = (
                    "reset-unit"
                    if address in unit_addresses
                    else "reset-zero"
                )
                reset_workspace_reads.append(item)
            else:
                item["initialization"] = "outside-reset-domain"
                item["input_role"] = "caller-input-candidate"
                caller_candidates.append(item)
            continue

        if domain == "output_vector":
            output_reads.append(item)
            item["initialization"] = "reset-zero"
            continue

        global_reads.append(item)
        item["initialization"] = "external-or-upstream"

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": provider_id,
        "function": initial.get("function"),
        "scalar_count": layout.scalar_count,
        "first_read_count": len(initial.get("first_read_addresses") or []),
        "workspace_first_reads": workspace_reads,
        "reset_workspace_first_reads": reset_workspace_reads,
        "caller_input_candidates": caller_candidates,
        "output_first_reads": output_reads,
        "global_first_reads": global_reads,
        "malformed_first_reads": malformed,
        "reset_domain_workspace_slots": sum(
            layout.factor_workspace_base
            <= address
            < layout.output_vector_base
            for address in reset_domain
        ),
        "reset_unit_diagonal_slots": len(unit_addresses),
        "ready": not errors,
        "errors": errors,
    }


def summarize_input_footprint(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider_id": report.get("provider_id"),
        "scalar_count": report.get("scalar_count"),
        "first_read_count": report.get("first_read_count"),
        "workspace_first_reads": len(
            report.get("workspace_first_reads") or []
        ),
        "reset_workspace_first_reads": len(
            report.get("reset_workspace_first_reads") or []
        ),
        "caller_input_candidates": len(
            report.get("caller_input_candidates") or []
        ),
        "output_first_reads": len(
            report.get("output_first_reads") or []
        ),
        "global_first_reads": len(
            report.get("global_first_reads") or []
        ),
        "malformed_first_reads": len(
            report.get("malformed_first_reads") or []
        ),
        "ready": bool(report.get("ready")),
    }


def validate_input_footprint(report: dict[str, Any]) -> dict[str, Any]:
    errors = list(report.get("errors") or [])
    scalar_count = int(report.get("scalar_count", 0))

    for index, entry in enumerate(
        report.get("caller_input_candidates") or []
    ):
        address = _address(entry)
        if not (
            entry.get("domain") == "workspace"
            and entry.get("initialization") == "outside-reset-domain"
        ):
            errors.append(
                f"caller-candidate-{index}-classification-invalid"
            )
        if (
            address
            < get_storage_layout(
                int(report.get("provider_id", -1))
            ).factor_workspace_base
            or address
            >= get_storage_layout(
                int(report.get("provider_id", -1))
            ).output_vector_base
        ):
            errors.append(
                f"caller-candidate-{index}-address-outside-workspace"
            )

    for entry in report.get("reset_workspace_first_reads") or []:
        address = _address(entry)
        if entry.get("initialization") not in {
            "reset-zero",
            "reset-unit",
        }:
            errors.append(
                f"reset-first-read-invalid-initialization:{hex(address)}"
            )

    for entry in report.get("output_first_reads") or []:
        if entry.get("initialization") != "reset-zero":
            errors.append(
                f"output-first-read-not-reset-zero:{entry.get('address')}"
            )

    if report.get("malformed_first_reads"):
        errors.append("malformed-first-read-present")

    if int(report.get("reset_unit_diagonal_slots", 0)) > scalar_count:
        errors.append("reset-unit-count-exceeds-scalar-count")

    return {
        "format": "SHIFT.SpecializedProviderInputFootprintValidation/1",
        "version": 1,
        "provider_id": report.get("provider_id"),
        "ready": not errors,
        "errors": errors,
    }


def build_input_footprint_contract(source: str) -> dict[str, Any]:
    providers: list[dict[str, Any]] = []
    for provider_id in (0, 1):
        report = extract_input_footprint(
            source,
            provider_id=provider_id,
        )
        report["summary"] = summarize_input_footprint(report)
        report["validation"] = validate_input_footprint(report)
        providers.append(report)

    return {
        "format": FORMAT,
        "version": 1,
        "source_file": "SHIFT.exe.c",
        "providers": providers,
        "classification": {
            "caller-input-candidate": "workspace first-read address not covered by reset zero/unit initialization",
            "reset-zero": "workspace/output first-read address covered by reset zero writes",
            "reset-unit": "workspace first-read address matching a reset 1.0 pivot seed",
            "external-or-upstream": "non-workspace/non-output first-read address",
        },
        "limitations": [
            "Caller-input candidates are storage-level candidates, not proven matrix entries.",
            "A reset-domain slot may still be overwritten by an upstream caller before solve; the static analysis alone cannot distinguish that case.",
            "Packed workspace aliases remain represented by absolute addresses plus any source-context metadata already present in Phase 456.",
        ],
        "status": "source-backed-provider-input-footprint",
    }


__all__ = [
    "FORMAT",
    "extract_input_footprint",
    "summarize_input_footprint",
    "validate_input_footprint",
    "build_input_footprint_contract",
]
