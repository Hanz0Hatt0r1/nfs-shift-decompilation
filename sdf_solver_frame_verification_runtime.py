"""Strict structural verifier for one SHIFT SDF solver frame."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.SDFSolverFrameVerificationRuntime/1"

EXPECTED_LIFECYCLE = [
    "FUN_007b3f40 frame entry",
    "FUN_007b3ed0 constraint refresh",
    "FUN_007bb8d0 per-body reset",
    "FUN_007bc680 contribution build",
    "FUN_007ba570 global vector/matrix export",
    "FUN_007b2210 selected identity rows/columns",
    "provider vtable +0x18 or FUN_007b0f20 solve",
    "FUN_007b4110 solved-vector body application",
]


def verify_solver_scalar_domain(
    *,
    solver_scalar_count: int,
    runtime_record_domains: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    n = int(solver_scalar_count)
    errors: list[str] = []
    ranges: list[dict[str, int]] = []
    covered: set[int] = set()

    for row in runtime_record_domains:
        record_index = int(row["record_index"])
        base = int(row["scalar_base"])
        width = int(row["width"])
        if width <= 0:
            errors.append(f"record:{record_index}:non-positive-width")
            continue
        if base < 0 or base + width > n:
            errors.append(f"record:{record_index}:range-out-of-domain")
        for node in range(base, base + width):
            if node in covered:
                errors.append(f"record:{record_index}:overlapping-node:{node}")
            covered.add(node)
        ranges.append({
            "record_index": record_index,
            "scalar_base": base,
            "width": width,
            "scalar_end": base + width,
        })

    if len(covered) != n:
        errors.append(f"coverage:{len(covered)}:{n}")

    return {
        "format": FORMAT,
        "version": 1,
        "status": "verified" if not errors else "blocked",
        "ready": not errors,
        "solver_scalar_count": n,
        "record_count": len(ranges),
        "covered_scalar_count": len(covered),
        "ranges": ranges,
        "errors": list(dict.fromkeys(errors)),
    }


def verify_identity_reset_selection(
    *,
    solver_scalar_count: int,
    runtime_record_domains: Sequence[Mapping[str, Any]],
    runtime_flags_by_record: Mapping[int | str, int] | None,
) -> dict[str, Any]:
    n = int(solver_scalar_count)
    flags = runtime_flags_by_record or {}
    errors: list[str] = []
    nodes: list[int] = []
    records: list[int] = []

    for row in runtime_record_domains:
        record_index = int(row["record_index"])
        base = int(row["scalar_base"])
        width = int(row["width"])
        flag = int(flags.get(record_index, flags.get(str(record_index), 0)))
        if flag & 1:
            records.append(record_index)
            nodes.extend(range(base, base + width))

    unique_nodes = list(dict.fromkeys(nodes))
    if any(node < 0 or node >= n for node in unique_nodes):
        errors.append("selected-node-out-of-domain")

    return {
        "format": "SHIFT.SDFIdentityResetVerification/1",
        "version": 1,
        "status": "verified" if not errors else "blocked",
        "ready": not errors,
        "runtime_flags_available": runtime_record_domains is not None and runtime_flags_by_record is not None,
        "selected_records": records,
        "selected_scalar_nodes": unique_nodes,
        "selected_scalar_count": len(unique_nodes),
        "errors": errors,
    }


def verify_frame_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    """Verify lifecycle, scalar-domain and identity-selection consistency."""
    errors: list[str] = []
    lifecycle = list(plan.get("contract", {}).get("lifecycle") or [])
    if lifecycle != EXPECTED_LIFECYCLE:
        errors.append("lifecycle-mismatch")

    n = int(plan.get("solver_scalar_count", 0))
    body_count = int(plan.get("body_count", 0))
    if n < 0:
        errors.append("negative-solver-scalar-count")
    if body_count < 0:
        errors.append("negative-body-count")

    identity = plan.get("identity_selector") or {}
    selected_nodes = [int(value) for value in identity.get("unique_scalar_nodes") or []]
    if any(node < 0 or node >= n for node in selected_nodes):
        errors.append("identity-node-out-of-domain")

    stage_names = [str(stage.get("stage")) for stage in plan.get("stages") or []]
    expected_stages = [
        "pre_solve",
        "seed_matrix",
        "numeric_constraint_coupling",
        "identity_reset",
        "solve_dispatch",
        "post_solve_application",
    ]
    if stage_names != expected_stages:
        errors.append("stage-name-mismatch")
    if identity.get("ready") is not False and not identity.get("unique_scalar_nodes") and plan.get("runtime_flags_available"):
        errors.append("runtime-flags-but-empty-reset-selection")

    return {
        "format": FORMAT,
        "version": 1,
        "status": "verified" if not errors else "blocked",
        "ready": not errors,
        "solver_scalar_count": n,
        "body_count": body_count,
        "errors": list(dict.fromkeys(errors)),
        "evidence": {
            "entry": "FUN_007b3f40",
            "pre_solve": "FUN_007bc680",
            "solve": "FUN_007b0f20",
            "post_solve": "FUN_007b4110",
        },
    }


def describe_solver_frame_verification_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "source-backed",
        "ready": True,
        "lifecycle": EXPECTED_LIFECYCLE,
        "checks": [
            "scalar-domain coverage and overlap",
            "identity-reset scalar-node range",
            "frame stage ordering",
            "body/scalar count sanity",
        ],
        "scope": "structural frame verification before numerical execution",
        "limitations": [
            "Does not claim numerical equivalence of provider backend.",
            "Does not replace the sparse solver's numerical execution.",
        ],
    }


__all__ = [
    "FORMAT",
    "EXPECTED_LIFECYCLE",
    "verify_solver_scalar_domain",
    "verify_identity_reset_selection",
    "verify_frame_plan",
    "describe_solver_frame_verification_contract",
]
