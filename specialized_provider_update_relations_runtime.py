"""Build normalized update relations from specialized-provider assignment evidence.

Phase 452 groups Phase 451 templates into reconstruction-friendly relations:
normalized-factor writes, self-subtract-product updates, forward RHS updates,
and unresolved generic assignments. Numeric coefficients and proprietary
expression text remain outside the IR.
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
from specialized_provider_update_template_runtime import classify_template
from specialized_provider_storage_runtime import get_storage_layout

FORMAT = "SHIFT.SpecializedProviderUpdateRelationsRuntime/1"


def _operator_map(source: str, provider_id: int) -> dict[tuple[int, int], str]:
    report = extract_operator_signatures(
        source,
        provider_id=provider_id,
    )
    return {
        (int(item["pivot_index"]), int(item["source_line"])): str(item["operator"])
        for item in report.get("assignments") or []
    }


def _address(reference: dict[str, Any]) -> int | None:
    value = reference.get("address")
    if value is None:
        return None
    return int(str(value), 16)


def _is_same_address(
    lhs: dict[str, Any],
    rhs: dict[str, Any],
) -> bool:
    left = _address(lhs)
    right = _address(rhs)
    return left is not None and right is not None and left == right


def _relation_kind(
    destination: dict[str, Any],
    rhs: list[dict[str, Any]],
    operator: str,
) -> str:
    template = classify_template(destination, rhs, operator)

    if template == "self-subtract-product":
        return "self-update"
    if template == "self-subtract-product-then-scale":
        return "self-update-then-scale"
    if operator in {"subtract-product", "subtract-product-then-scale"}:
        return "subtractive-update"
    if operator in {"scale-or-product-by-pivot", "product"}:
        return "normalized-factor"
    if destination.get("domain") == "output_vector":
        return "rhs-update"
    return "other"


def _build_relation(
    assignment: dict[str, Any],
    operator: str,
) -> dict[str, Any]:
    destination = dict(assignment["destination"])
    rhs = [dict(reference) for reference in assignment.get("rhs") or []]
    kind = _relation_kind(destination, rhs, operator)

    relation: dict[str, Any] = {
        "pivot_index": int(assignment["pivot_index"]),
        "source_line": int(assignment["source_line"]),
        "loop_index": assignment.get("loop_index"),
        "kind": kind,
        "operator": operator,
        "destination": destination,
        "rhs": rhs,
    }

    if kind == "normalized-factor":
        workspace_rhs = [
            reference
            for reference in rhs
            if reference.get("domain") == "workspace"
        ]
        if len(workspace_rhs) == 1:
            relation["factor_source"] = workspace_rhs[0]
            relation["factor_source_count"] = 1
        else:
            relation["factor_source_count"] = len(workspace_rhs)

    if kind in {"self-update", "self-update-then-scale"}:
        if rhs and _is_same_address(destination, rhs[0]):
            relation["self_reference"] = rhs[0]
            relation["update_terms"] = rhs[1:]
        else:
            relation["update_terms"] = rhs

    return relation


def extract_update_relations(
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
    operators = _operator_map(source, provider_id)
    errors = list(provider_report.get("errors") or [])

    relations: list[dict[str, Any]] = []
    for assignment in provider_report.get("assignments") or []:
        key = (
            int(assignment["pivot_index"]),
            int(assignment["source_line"]),
        )
        operator = operators.get(key)
        if operator is None:
            errors.append(
                f"missing-operator:pivot={key[0]}:line={key[1]}"
            )
            continue
        relations.append(
            _build_relation(
                assignment,
                operator,
            )
        )

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": provider_id,
        "function": provider_report.get("function"),
        "scalar_count": layout.scalar_count,
        "relations": relations,
        "ready": not errors,
        "errors": errors,
    }


def summarize_update_relations(report: dict[str, Any]) -> dict[str, Any]:
    counts = Counter(
        str(relation.get("kind"))
        for relation in report.get("relations") or []
    )
    factor_relations = [
        relation
        for relation in report.get("relations") or []
        if relation.get("kind") == "normalized-factor"
        and relation.get("factor_source_count") == 1
    ]
    self_updates = [
        relation
        for relation in report.get("relations") or []
        if relation.get("kind") in {
            "self-update",
            "self-update-then-scale",
        }
    ]
    return {
        "provider_id": report.get("provider_id"),
        "scalar_count": report.get("scalar_count"),
        "relations": len(report.get("relations") or []),
        "relation_counts": dict(sorted(counts.items())),
        "single-source-factor_relations": len(factor_relations),
        "self_update_relations": len(self_updates),
        "ready": bool(report.get("ready")),
    }


def validate_update_relations(report: dict[str, Any]) -> dict[str, Any]:
    errors = list(report.get("errors") or [])
    scalar_count = int(report.get("scalar_count", 0))

    for index, relation in enumerate(report.get("relations") or []):
        pivot = int(relation.get("pivot_index", -1))
        if pivot < 0 or pivot >= scalar_count:
            errors.append(f"relation-{index}-pivot-out-of-range")

        kind = str(relation.get("kind"))
        if kind == "normalized-factor":
            count = int(relation.get("factor_source_count", 0))
            if count < 1:
                errors.append(
                    f"relation-{index}-factor-without-workspace-source"
                )

        if kind in {"self-update", "self-update-then-scale"}:
            if not relation.get("self_reference"):
                errors.append(
                    f"relation-{index}-self-update-without-self-reference"
                )

        destination = relation.get("destination") or {}
        if destination.get("domain") == "workspace" and not destination.get(
            "unique", False
        ):
            if not destination.get("candidates"):
                errors.append(
                    f"relation-{index}-ambiguous-destination-without-candidates"
                )

    return {
        "format": "SHIFT.SpecializedProviderUpdateRelationsValidation/1",
        "version": 1,
        "provider_id": report.get("provider_id"),
        "ready": not errors,
        "errors": errors,
        "relations": len(report.get("relations") or []),
    }


def build_update_relation_contract(source: str) -> dict[str, Any]:
    providers: list[dict[str, Any]] = []
    for provider_id in (0, 1):
        report = extract_update_relations(
            source,
            provider_id=provider_id,
        )
        report["summary"] = summarize_update_relations(report)
        report["validation"] = validate_update_relations(report)
        providers.append(report)

    return {
        "format": FORMAT,
        "version": 1,
        "source_file": "SHIFT.exe.c",
        "providers": providers,
        "relation_policy": {
            "normalized-factor": "multiplicative update associated with pivot-local scale",
            "self-update": "destination address repeated as first RHS reference",
            "subtractive-update": "subtractive product shape without proven self-reference",
            "rhs-update": "output-vector destination",
            "other": "preserved without semantic reinterpretation",
        },
        "limitations": [
            "The relation is structural and uses source-visible dependencies; it is not a semantic matrix equation.",
            "Self-reference is identified by absolute address equality only.",
            "Alias candidates remain unresolved for ambiguous packed addresses.",
            "Numeric coefficients and proprietary expression text are omitted.",
        ],
        "status": "source-backed-update-relations",
    }


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()

    contract = build_update_relation_contract(
        args.source.read_text(encoding="utf-8")
    )
    print(json.dumps(contract, indent=2, sort_keys=True))
    ready = all(
        provider["validation"]["ready"]
        for provider in contract["providers"]
    )
    raise SystemExit(0 if ready else 2)
