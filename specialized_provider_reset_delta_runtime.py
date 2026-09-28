"""Measure provider pre-solve state relative to the proven reset baseline.

Phase 469 consumes the Phase 462 provider capture schema and Phase 466/468 reset
profiles. It labels observed pre-solve storage as unchanged reset state,
reset-slot deviation, or population outside the reset domain.

The analyzer remains storage-level; it does not infer logical matrix semantics.
"""
from __future__ import annotations

import math
from typing import Any, Mapping

from specialized_provider_capture_runtime import normalize_provider_capture
from specialized_provider_reset_cleanup_equivalence_runtime import (
    compare_reset_cleanup,
)
from specialized_provider_reset_domain_runtime import extract_reset_domain
from specialized_provider_storage_runtime import get_storage_layout

FORMAT = "SHIFT.SpecializedProviderResetDeltaRuntime/1"


def _value_map(
    values: list[float],
    *,
    base_address: int,
) -> dict[int, float]:
    return {
        int(base_address) + index * 8: float(value)
        for index, value in enumerate(values)
    }


def _outside_workspace(
    address: int,
    *,
    layout: Any,
) -> bool:
    return not (
        layout.factor_workspace_base
        <= address
        < layout.output_vector_base
    )


def _classify_change(
    address: int,
    value: float,
    *,
    expected: float | None,
    reset_domain: set[int],
    reset_unit: set[int],
    region: str,
    abs_tol: float,
    rel_tol: float,
) -> str:
    if expected is not None:
        delta = abs(value - expected)
        scale = max(abs(value), abs(expected))
        if delta <= abs_tol + rel_tol * scale:
            return "unchanged-reset-state"

        if address in reset_unit:
            return "reset-unit-slot-deviation"
        return "reset-zero-slot-deviation"

    if region == "workspace":
        return "outside-reset-domain-nonzero"

    return "output-nonzero"


def compare_capture_to_reset(
    source: str,
    capture: Mapping[str, Any],
    *,
    provider_id: int,
    abs_tol: float = 0.0,
    rel_tol: float = 0.0,
) -> dict[str, Any]:
    normalized = normalize_provider_capture(capture)
    layout = get_storage_layout(provider_id)
    if normalized["provider_id"] != provider_id:
        raise ValueError("provider id mismatch")

    reset_domain_report = extract_reset_domain(
        source,
        provider_id=provider_id,
    )
    reset_equivalence = compare_reset_cleanup(
        source,
        provider_id=provider_id,
    )
    zero_addresses = {
        int(str(address), 16)
        for address in reset_domain_report["zero_addresses"]
    }
    unit_addresses = {
        int(str(address), 16)
        for address in reset_domain_report["unit_diagonal_addresses"]
    }
    reset_domain = {
        int(str(address), 16)
        for address in reset_domain_report["touched_addresses"]
    }

    workspace_values = _value_map(
        normalized["workspace"],
        base_address=layout.factor_workspace_base,
    )
    output_values = _value_map(
        normalized["output_vector"],
        base_address=layout.output_vector_base,
    )

    expected_by_address = {
        address: 0.0
        for address in reset_domain
    }
    expected_by_address.update({
        address: 1.0
        for address in unit_addresses
    })

    categories: dict[str, list[dict[str, Any]]] = {
        "unchanged-reset-state": [],
        "reset-zero-slot-deviation": [],
        "reset-unit-slot-deviation": [],
        "outside-reset-domain-nonzero": [],
        "output-nonzero": [],
    }

    workspace_expected = {
        address: expected_by_address[address]
        for address in expected_by_address
        if layout.factor_workspace_base <= address < layout.output_vector_base
    }
    for address, value in sorted(workspace_values.items()):
        expected = workspace_expected.get(address)
        if expected is None and math.isclose(
            value,
            0.0,
            abs_tol=abs_tol,
            rel_tol=rel_tol,
        ):
            continue

        category = _classify_change(
            address,
            value,
            expected=expected,
            reset_domain=reset_domain,
            reset_unit=unit_addresses,
            region="workspace",
            abs_tol=abs_tol,
            rel_tol=rel_tol,
        )
        categories[category].append({
            "address": hex(address),
            "observed": value,
            "expected": expected,
        })

    for address, value in sorted(output_values.items()):
        category = _classify_change(
            address,
            value,
            expected=0.0,
            reset_domain=reset_domain,
            reset_unit=set(),
            region="output",
            abs_tol=abs_tol,
            rel_tol=rel_tol,
        )
        if category != "unchanged-reset-state":
            categories[category].append({
                "address": hex(address),
                "observed": value,
                "expected": 0.0,
            })

    nonzero_outside_reset = [
        entry
        for entry in categories["outside-reset-domain-nonzero"]
        if not math.isclose(
            float(entry["observed"]),
            0.0,
            abs_tol=abs_tol,
            rel_tol=rel_tol,
        )
    ]

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": provider_id,
        "scalar_count": layout.scalar_count,
        "capture_stage": normalized["stage"],
        "reset_function": reset_domain_report["reset_function"],
        "cleanup_reset_equivalent": bool(
            reset_equivalence.get(
                "reset_zero_cleanup_exact_match"
            )
        ),
        "reset_domain_workspace_slots": sum(
            layout.factor_workspace_base <= address < layout.output_vector_base
            for address in reset_domain
        ),
        "reset_domain_output_slots": sum(
            layout.output_vector_base
            <= address
            < layout.output_vector_base + layout.output_vector_bytes
            for address in reset_domain
        ),
        "categories": categories,
        "counts": {
            category: len(entries)
            for category, entries in categories.items()
        },
        "outside_reset_nonzero_count": len(nonzero_outside_reset),
        "reset_state_equivalent": all(
            not entries
            for category, entries in categories.items()
            if category != "outside-reset-domain-nonzero"
        )
        and not nonzero_outside_reset,
        "reset_zero_domain_ready": bool(reset_domain_report.get("ready")),
        "cleanup_reset_equivalent": bool(
            reset_equivalence.get("reset_zero_cleanup_exact_match")
        ),
        "ready": bool(
            normalized.get("ready")
            and reset_domain_report.get("ready")
        ),
        "errors": list(reset_domain_report.get("errors") or []),
    }


def summarize_reset_delta(report: Mapping[str, Any]) -> dict[str, Any]:
    counts = report.get("counts") or {}
    return {
        "provider_id": report.get("provider_id"),
        "scalar_count": report.get("scalar_count"),
        "capture_stage": report.get("capture_stage"),
        "reset_domain_workspace_slots": report.get(
            "reset_domain_workspace_slots"
        ),
        "reset_domain_output_slots": report.get(
            "reset_domain_output_slots"
        ),
        "reset_zero_slot_deviations": int(
            counts.get("reset-zero-slot-deviation", 0)
        ),
        "reset_unit_slot_deviations": int(
            counts.get("reset-unit-slot-deviation", 0)
        ),
        "outside_reset_domain_nonzero": int(
            counts.get("outside-reset-domain-nonzero", 0)
        ),
        "output_nonzero": int(counts.get("output-nonzero", 0)),
        "reset_state_equivalent": bool(
            report.get("reset_state_equivalent")
        ),
        "ready": bool(report.get("ready")),
    }


def validate_reset_delta(report: Mapping[str, Any]) -> dict[str, Any]:
    errors = list(report.get("errors") or [])
    scalar_count = int(report.get("scalar_count", 0))

    if int(report.get("reset_domain_output_slots", 0)) != scalar_count:
        errors.append("output-reset-domain-count-mismatch")

    categories = report.get("categories") or {}
    for category in (
        "reset-zero-slot-deviation",
        "reset-unit-slot-deviation",
        "outside-reset-domain-nonzero",
        "output-nonzero",
    ):
        for entry in categories.get(category) or []:
            address = int(str(entry["address"]), 16)
            if not math.isfinite(float(entry["observed"])):
                errors.append(
                    f"{category}-nonfinite:{hex(address)}"
                )

    return {
        "format": "SHIFT.SpecializedProviderResetDeltaValidation/1",
        "version": 1,
        "provider_id": report.get("provider_id"),
        "ready": not errors,
        "errors": errors,
    }


def build_reset_delta_contract(
    source: str,
    capture: Mapping[str, Any],
    *,
    provider_id: int,
    abs_tol: float = 0.0,
    rel_tol: float = 0.0,
) -> dict[str, Any]:
    report = compare_capture_to_reset(
        source,
        capture,
        provider_id=provider_id,
        abs_tol=abs_tol,
        rel_tol=rel_tol,
    )
    report["summary"] = summarize_reset_delta(report)
    report["validation"] = validate_reset_delta(report)
    return report


__all__ = [
    "FORMAT",
    "compare_capture_to_reset",
    "summarize_reset_delta",
    "validate_reset_delta",
    "build_reset_delta_contract",
]
