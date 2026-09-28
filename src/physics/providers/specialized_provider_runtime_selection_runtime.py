"""Provider runtime selection/hand-off contract.

This layer joins the already proven dispatch, selector provenance, execution
sequence, and source-shape contracts. It does not choose a provider for a retail
frame; it records the alternatives and the evidence needed to validate an
observed selection.
"""
from __future__ import annotations

from typing import Any

from specialized_provider_dispatch_boundary_runtime import (
    build_dispatch_boundary_contract,
)
from specialized_provider_execution_sequence_runtime import (
    build_execution_sequence_contract,
)
from specialized_provider_scalar_selector_provenance_runtime import (
    build_selector_provenance_report,
)
from specialized_provider_source_shape_runtime import (
    build_source_shape_contract,
)

FORMAT = "SHIFT.SpecializedProviderRuntimeSelection/1"


def build_runtime_selection_contract(source: str) -> dict[str, Any]:
    dispatch = build_dispatch_boundary_contract()
    execution = build_execution_sequence_contract()
    selector = build_selector_provenance_report()
    source_shape = build_source_shape_contract(source)

    validations = {
        "dispatch": dispatch.get("validation", {}),
        "execution": execution.get("validation", {}),
        "selector": selector.get("validation", {}),
        "source_shape": {
            "ready": all(
                provider.get("validation", {}).get("ready") is True
                for provider in source_shape.get("providers", [])
            )
        },
    }
    ready = all(
        bool(report.get("ready")) is True
        for report in validations.values()
    )

    return {
        "format": FORMAT,
        "version": 1,
        "selection": dispatch.get("selection", {}),
        "execution": execution.get("execution", {}),
        "selector_provenance": selector.get("contract", {}),
        "source_shape": source_shape,
        "validation": validations,
        "ready": ready,
        "limitations": [
            "Provider identity for a captured frame must come from runtime observation; this contract does not infer it.",
            "Selector values are captured/provenance inputs, not semantic matrix coordinates.",
            "Source-shape metadata describes retail source structure only and does not replace numeric runtime capture.",
        ],
    }


def validate_runtime_selection(
    report: dict[str, Any],
    *,
    observed_provider_id: int | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    validation = report.get("validation") or {}
    for name, item in validation.items():
        if item.get("ready") is not True:
            errors.append(f"{name}-validation-not-ready")

    if observed_provider_id is not None and observed_provider_id not in (0, 1):
        errors.append(f"observed-provider-out-of-domain:{observed_provider_id}")

    return {
        "format": "SHIFT.SpecializedProviderRuntimeSelectionValidation/1",
        "version": 1,
        "observed_provider_id": observed_provider_id,
        "ready": not errors,
        "errors": errors,
    }


__all__ = [
    "FORMAT",
    "build_runtime_selection_contract",
    "validate_runtime_selection",
]
