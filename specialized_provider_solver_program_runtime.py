"""Assemble the complete evidence-backed specialized provider solver program.

Phase 455 joins the previously reconstructed layers into one per-provider
program bundle. The bundle keeps pivot geometry, execution schedule, packed
workspace aliases, update relations, output-vector schedule and the older solver
IR as separate evidence layers while providing one readiness gate for consumers.
"""
from __future__ import annotations

from typing import Any

from specialized_provider_acceptance_factor_separation_runtime import (
    compare_acceptance_and_factor,
)
from specialized_provider_execution_schedule_runtime import (
    extract_execution_schedule,
)
from specialized_provider_solver_ir_runtime import build_solver_ir
from specialized_provider_source_context_resolver_runtime import (
    build_source_context_contract,
)
from specialized_provider_storage_runtime import get_storage_layout
from specialized_provider_update_relations_runtime import (
    extract_update_relations,
)
from specialized_provider_workspace_alias_runtime import build_alias_map
from specialized_provider_output_schedule_runtime import (
    extract_output_schedule,
)

FORMAT = "SHIFT.SpecializedProviderSolverProgramRuntime/1"


def _provider_source_context(
    contract: dict[str, Any],
    provider_id: int,
) -> dict[str, Any]:
    for provider in contract.get("providers") or []:
        if int(provider.get("provider_id", -1)) == provider_id:
            return provider
    raise ValueError(f"source context contract missing provider {provider_id}")


def build_solver_program(
    source: str,
    *,
    provider_id: int,
) -> dict[str, Any]:
    layout = get_storage_layout(provider_id)

    solver_ir = build_solver_ir(
        source,
        provider_id=provider_id,
    )
    execution_schedule = extract_execution_schedule(
        source,
        provider_id=provider_id,
    )
    update_relations = extract_update_relations(
        source,
        provider_id=provider_id,
    )
    output_schedule = extract_output_schedule(
        source,
        provider_id=provider_id,
    )
    acceptance_factor = compare_acceptance_and_factor(
        source,
        provider_id=provider_id,
    )
    alias_map = build_alias_map(provider_id)
    source_context = _provider_source_context(
        build_source_context_contract(),
        provider_id,
    )

    errors: list[str] = []

    for name, report in (
        ("solver_ir", solver_ir),
        ("execution_schedule", execution_schedule),
        ("update_relations", update_relations),
        ("output_schedule", output_schedule),
        ("acceptance_factor", acceptance_factor),
        ("alias_map", alias_map),
    ):
        if report.get("ready") is not True:
            errors.append(f"{name}-not-ready")
        validation = report.get("validation")
        if validation is not None and validation.get("ready") is not True:
            errors.append(f"{name}-validation-not-ready")

    if source_context.get("diagonal_resolution_unique") is not True:
        errors.append("source-context-diagonal-resolution-not-unique")

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": provider_id,
        "function": solver_ir.get("function"),
        "scalar_count": layout.scalar_count,
        "evidence": {
            "solver_ir": solver_ir,
            "execution_schedule": execution_schedule,
            "update_relations": update_relations,
            "output_schedule": output_schedule,
            "acceptance_factor": acceptance_factor,
            "workspace_alias_map": alias_map,
            "source_context": source_context,
        },
        "readiness": {
            "pivot_geometry": solver_ir.get("pivot_count") == layout.scalar_count,
            "execution_blocks": len(execution_schedule.get("blocks") or [])
            == layout.scalar_count,
            "update_relations": update_relations.get("ready") is True,
            "output_schedule": output_schedule.get("ready") is True,
            "acceptance_factor_separation": acceptance_factor.get("ready")
            is True,
            "workspace_alias_map": alias_map.get("ready") is True,
            "source_context": source_context.get("diagonal_resolution_unique")
            is True,
        },
        "ready": not errors,
        "errors": errors,
    }


def summarize_solver_program(report: dict[str, Any]) -> dict[str, Any]:
    evidence = report.get("evidence") or {}
    update_relations = evidence.get("update_relations") or {}
    output_schedule = evidence.get("output_schedule") or {}
    alias_map = evidence.get("workspace_alias_map") or {}

    update_summary = update_relations.get("summary") or {}
    output_summary = output_schedule.get("summary") or {}
    alias_summary = alias_map.get("summary") or {}

    return {
        "provider_id": report.get("provider_id"),
        "scalar_count": report.get("scalar_count"),
        "update_relations": int(update_summary.get("relations", 0)),
        "self_update_relations": int(
            update_summary.get("self_update_relations", 0)
        ),
        "output_assignments": int(
            output_summary.get("output_assignment_count", 0)
        ),
        "output_dependency_edges": int(
            output_summary.get("output_dependency_edge_count", 0)
        ),
        "workspace_alias_addresses": int(
            alias_summary.get("unique_storage_addresses", 0)
        ),
        "workspace_alias_collisions": int(
            alias_summary.get("collision_address_count", 0)
        ),
        "ready": bool(report.get("ready")),
    }


def validate_solver_program(report: dict[str, Any]) -> dict[str, Any]:
    errors = list(report.get("errors") or [])
    readiness = report.get("readiness") or {}

    required = (
        "pivot_geometry",
        "execution_blocks",
        "update_relations",
        "output_schedule",
        "acceptance_factor_separation",
        "workspace_alias_map",
        "source_context",
    )
    for name in required:
        if readiness.get(name) is not True:
            errors.append(f"readiness-{name}-false")

    evidence = report.get("evidence") or {}
    scalar_count = int(report.get("scalar_count", 0))

    execution = evidence.get("execution_schedule") or {}
    if len(execution.get("blocks") or []) != scalar_count:
        errors.append("execution-block-count-mismatch")

    output = evidence.get("output_schedule") or {}
    for assignment in output.get("assignments") or []:
        index = int((assignment.get("destination") or {}).get("index", -1))
        if index < 0 or index >= scalar_count:
            errors.append("output-destination-out-of-domain")

    aliases = evidence.get("workspace_alias_map") or {}
    if int(aliases.get("scalar_count", -1)) != scalar_count:
        errors.append("alias-map-scalar-count-mismatch")

    return {
        "format": "SHIFT.SpecializedProviderSolverProgramValidation/1",
        "version": 1,
        "provider_id": report.get("provider_id"),
        "ready": not errors,
        "errors": errors,
    }


def build_solver_program_contract(source: str) -> dict[str, Any]:
    providers: list[dict[str, Any]] = []
    for provider_id in (0, 1):
        report = build_solver_program(
            source,
            provider_id=provider_id,
        )
        report["summary"] = summarize_solver_program(report)
        report["validation"] = validate_solver_program(report)
        providers.append(report)

    return {
        "format": FORMAT,
        "version": 1,
        "source_file": "SHIFT.exe.c",
        "providers": providers,
        "layers": [
            "SHIFT.SpecializedProviderSolverIRRuntime/1",
            "SHIFT.SpecializedProviderExecutionScheduleRuntime/1",
            "SHIFT.SpecializedProviderUpdateRelationsRuntime/1",
            "SHIFT.SpecializedProviderOutputScheduleRuntime/1",
            "SHIFT.SpecializedProviderAcceptanceFactorSeparationRuntime/1",
            "SHIFT.SpecializedProviderWorkspaceAliasRuntime/1",
            "SHIFT.SpecializedProviderSourceContextResolverRuntime/1",
        ],
        "limitations": [
            "The bundle is an evidence container, not a drop-in numeric provider implementation.",
            "All numeric RHS expressions remain outside the repository.",
            "Provider class identity, physical units and final BMW provider selection remain capture-gated.",
        ],
        "status": "source-backed-specialized-provider-solver-program",
    }


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()

    contract = build_solver_program_contract(
        args.source.read_text(encoding="utf-8")
    )
    print(json.dumps(contract, indent=2, sort_keys=True))
    ready = all(
        provider["validation"]["ready"]
        for provider in contract["providers"]
    )
    raise SystemExit(0 if ready else 2)
