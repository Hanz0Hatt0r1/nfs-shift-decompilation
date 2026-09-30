"""Native admission contract for the source-backed SDF logical workspace.

The contract joins the exact FUN_007b3820 pre-acceptance storage layout with
the FUN_007b3f40 provider-absent frame clear. It deliberately stops before
FUN_007ba2b0 body contributions, coupling kernels, solver dispatch, and
post-solve application.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from providers.specialized_provider_preacceptance_matrix_runtime import (
    validate_matrix_construction_contract,
)
from sdf_constraint_matrix_assembly_runtime import build_retail_matrix_storage
from sdf_constraint_solver_frame_runtime import describe_sdf_solver_frame_contract

FORMAT = "SHIFT.NativePhysicsWorkspaceBoundary/1"


def build_native_physics_workspace_boundary(
    scalar_count: int = 40,
) -> dict[str, Any]:
    n = int(scalar_count)
    if n <= 0:
        raise ValueError("scalar_count must be positive")

    preacceptance = validate_matrix_construction_contract()
    frame = describe_sdf_solver_frame_contract(
        solver_scalar_count=n,
        body_count=None,
    )
    layout = build_retail_matrix_storage(n)

    errors: list[str] = []
    if preacceptance.get("ready") is not True:
        errors.extend(
            f"preacceptance:{reason}"
            for reason in preacceptance.get("errors") or []
        )
    if frame.get("ready") is not True:
        errors.append("solver-frame:not-ready")
    if layout.get("matrix_double_count") != n * n:
        errors.append("layout:matrix-double-count")
    if layout.get("matrix_bytes") != n * n * 8:
        errors.append("layout:matrix-bytes")
    if layout.get("row_pointer_count") != n:
        errors.append("layout:row-pointer-count")
    if layout.get("row_pointer_bytes") != n * 4:
        errors.append("layout:row-pointer-bytes")

    row_indices = [int(v) for v in layout.get("row_indices") or []]
    expected_indices = [n * row for row in range(n)]
    if row_indices != expected_indices:
        errors.append("layout:row-index-formula")

    provider_absent = (
        frame.get("provider_branch", {})
        .get("provider_absent", {})
    )
    if "zero scalar_count x scalar_count doubles" not in str(
        provider_absent.get("matrix_clear", "")
    ):
        errors.append("frame:matrix-clear")
    if "zero scalar_count doubles" not in str(
        provider_absent.get("rhs_clear", "")
    ):
        errors.append("frame:rhs-clear")

    ready = not errors
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": errors,
        "scalar_count": n,
        "storage": {
            "matrix_double_count": n * n,
            "matrix_bytes": n * n * 8,
            "retail_row_pointer_count": n,
            "retail_row_pointer_bytes": n * 4,
            "native_row_indices": expected_indices,
            "rhs_scalar_count": n,
            "rhs_bytes": n * 8,
            "row_index_formula": "scalar_count * row",
            "retail_row_pointer_formula": (
                "matrix_base + row_index * 8"
            ),
        },
        "fixed_step": {
            "provider_bound": False,
            "provider_absent_clear_ready": ready,
            "matrix_clear": "zero full logical matrix pool",
            "rhs_clear": "zero full RHS vector",
            "body_contribution_execution": False,
            "constraint_coupling_execution": False,
            "solver_execution": False,
            "post_solve_execution": False,
        },
        "source": {
            "allocation": "FUN_007b3820",
            "matrix_initialization": "FUN_007b2010",
            "frame_entry": "FUN_007b3f40",
            "body_contributions": "FUN_007ba2b0",
            "builtin_solver": "FUN_007b0f20",
        },
        "limitations": [
            "Native row indices preserve retail 32-bit row-pointer geometry without fabricating retail addresses in a 64-bit process.",
            "Body contribution formulas are not executed by this boundary.",
            "Constraint coupling kernels are not executed by this boundary.",
            "No provider is selected or identified.",
            "No numerical solver or post-solve application is executed.",
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scalar-count", type=int, default=40)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)

    report = build_native_physics_workspace_boundary(args.scalar_count)
    payload = json.dumps(
        report,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["FORMAT", "build_native_physics_workspace_boundary"]
