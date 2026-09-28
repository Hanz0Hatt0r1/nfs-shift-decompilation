"""Classify specialized-provider assignment templates from contextual dependencies.

Phase 451 captures recurring structural update forms such as
destination-minus-source-times-factor without embedding the retail arithmetic.
The destination and ordered dependency references come from Phase 450.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from specialized_provider_contextual_dependency_runtime import (
    build_contextual_dependency_contract,
)
from specialized_provider_operator_signature_runtime import (
    extract_operator_signatures,
    SOLVER_SPECS,
)
from specialized_provider_storage_runtime import get_storage_layout

FORMAT = "SHIFT.SpecializedProviderUpdateTemplateRuntime/1"


def _reference_address(reference: dict[str, Any]) -> int | None:
    address = reference.get("address")
    if address is None:
        return None
    return int(str(address), 16)


def _same_storage_location(
    lhs: dict[str, Any],
    rhs: dict[str, Any],
) -> bool:
    lhs_address = _reference_address(lhs)
    rhs_address = _reference_address(rhs)
    if lhs_address is None or rhs_address is None:
        return False
    return lhs_address == rhs_address


def classify_template(
    destination: dict[str, Any],
    rhs: list[dict[str, Any]],
    operator: str,
) -> str:
    if operator == "subtract-product":
        if rhs and _same_storage_location(destination, rhs[0]):
            return "self-subtract-product"
        return "subtract-product"

    if operator == "subtract-product-then-scale":
        if rhs and _same_storage_location(destination, rhs[0]):
            return "self-subtract-product-then-scale"
        return "subtract-product-then-scale"

    if operator == "scale-or-product-by-pivot":
        return "scale-or-product-by-pivot"

    return operator


def _operator_by_source_line(
    source: str,
    *,
    provider_id: int,
) -> dict[tuple[int, int], str]:
    report = extract_operator_signatures(
        source,
        provider_id=provider_id,
    )
    return {
        (
            int(item["pivot_index"]),
            int(item["source_line"]),
        ): str(item["operator"])
        for item in report.get("assignments") or []
    }


def extract_update_templates(
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
    operator_map = _operator_by_source_line(
        source,
        provider_id=provider_id,
    )

    errors = list(provider_report.get("errors") or [])
    templates: list[dict[str, Any]] = []

    for assignment in provider_report.get("assignments") or []:
        pivot = int(assignment["pivot_index"])
        source_line = int(assignment["source_line"])
        operator = operator_map.get((pivot, source_line))
        if operator is None:
            errors.append(
                f"missing-operator:pivot={pivot}:line={source_line}"
            )
            continue

        destination = dict(assignment["destination"])
        rhs = [dict(reference) for reference in assignment.get("rhs") or []]
        template = classify_template(destination, rhs, operator)

        workspace_rhs = [
            reference
            for reference in rhs
            if reference.get("domain") == "workspace"
        ]
        output_rhs = [
            reference
            for reference in rhs
            if reference.get("domain") == "output_vector"
        ]
        global_rhs = [
            reference
            for reference in rhs
            if reference.get("domain") not in {
                "workspace",
                "output_vector",
            }
        ]

        templates.append(
            {
                "pivot_index": pivot,
                "source_line": source_line,
                "loop_index": assignment.get("loop_index"),
                "operator": operator,
                "template": template,
                "destination": destination,
                "rhs": rhs,
                "rhs_roles": {
                    "workspace": workspace_rhs,
                    "output_vector": output_rhs,
                    "global": global_rhs,
                },
            }
        )

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": provider_id,
        "function": provider_report.get("function"),
        "scalar_count": layout.scalar_count,
        "assignments": templates,
        "ready": not errors,
        "errors": errors,
    }


def summarize_update_templates(report: dict[str, Any]) -> dict[str, Any]:
    templates = Counter(
        str(item.get("template"))
        for item in report.get("assignments") or []
    )
    self_updates = sum(
        count
        for name, count in templates.items()
        if name.startswith("self-")
    )
    return {
        "provider_id": report.get("provider_id"),
        "scalar_count": report.get("scalar_count"),
        "assignments": len(report.get("assignments") or []),
        "template_counts": dict(sorted(templates.items())),
        "self_update_assignments": self_updates,
        "ready": bool(report.get("ready")),
    }


def validate_update_templates(report: dict[str, Any]) -> dict[str, Any]:
    errors = list(report.get("errors") or [])
    scalar_count = int(report.get("scalar_count", 0))

    for index, assignment in enumerate(report.get("assignments") or []):
        pivot = int(assignment.get("pivot_index", -1))
        if pivot < 0 or pivot >= scalar_count:
            errors.append(f"assignment-{index}-pivot-out-of-range")

        if not assignment.get("template"):
            errors.append(f"assignment-{index}-missing-template")

        if assignment.get("operator") in {
            "subtract-product",
            "subtract-product-then-scale",
        }:
            rhs = assignment.get("rhs") or []
            if not rhs:
                errors.append(
                    f"assignment-{index}-subtract-template-without-rhs"
                )

        destination = assignment.get("destination") or {}
        if destination.get("domain") == "workspace" and not destination.get(
            "unique", False
        ):
            if not destination.get("candidates"):
                errors.append(
                    f"assignment-{index}-ambiguous-workspace-destination-without-candidates"
                )

    return {
        "format": "SHIFT.SpecializedProviderUpdateTemplateValidation/1",
        "version": 1,
        "provider_id": report.get("provider_id"),
        "ready": not errors,
        "errors": errors,
        "assignments": len(report.get("assignments") or []),
    }


def build_update_template_contract(source: str) -> dict[str, Any]:
    providers: list[dict[str, Any]] = []
    for provider_id in (0, 1):
        report = extract_update_templates(
            source,
            provider_id=provider_id,
        )
        report["summary"] = summarize_update_templates(report)
        report["validation"] = validate_update_templates(report)
        providers.append(report)

    return {
        "format": FORMAT,
        "version": 1,
        "source_file": "SHIFT.exe.c",
        "providers": providers,
        "scope": {
            "representation": "assignment template signature",
            "self_update": "destination absolute address equals first RHS reference address",
            "numeric_expression": "omitted",
        },
        "limitations": [
            "Template classification describes source-visible dependency shape, not mathematical semantics.",
            "A self-update identifies repeated storage in the source expression; it does not by itself prove a Schur-complement role.",
            "Packed workspace aliasing remains represented through Phase 449 candidate lists.",
        ],
        "status": "source-backed-update-template-signatures",
    }


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()

    contract = build_update_template_contract(
        args.source.read_text(encoding="utf-8")
    )
    print(json.dumps(contract, indent=2, sort_keys=True))
    ready = all(
        provider["validation"]["ready"]
        for provider in contract["providers"]
    )
    raise SystemExit(0 if ready else 2)
