"""Unified source-backed SDF solver frame contract."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from sdf_constraint_solver_frame_runtime import (
    describe_sdf_solver_frame_contract,
    derive_builtin_diagonal_reset_nodes,
)
from sdf_builtin_identity_reset_runtime import describe_identity_reset_contract
from sdf_post_solve_application_runtime import describe_post_solve_application_contract

FORMAT = "SHIFT.SDFFullFrameRuntime/1"


def describe_full_frame_contract(
    *,
    solver_scalar_count: int | None = None,
    body_count: int | None = None,
    runtime_flags_available: bool = False,
) -> dict[str, Any]:
    frame = describe_sdf_solver_frame_contract(
        solver_scalar_count=solver_scalar_count,
        body_count=body_count,
    )
    identity = describe_identity_reset_contract()
    post_solve = describe_post_solve_application_contract()

    runtime_dependencies = {
        "identity_reset_selector": {
            "available": bool(runtime_flags_available),
            "source": "runtime constraint sample +0x70 & 1",
            "function": "FUN_007b2210",
        },
        "provider_solve": {
            "provider_pointer": "physics-system +0x48",
            "reset_virtual_slot": "+0x1c",
            "solve_virtual_slot": "+0x18",
        },
    }

    return {
        "format": FORMAT,
        "version": 1,
        "status": "runtime-complete" if runtime_flags_available else "static-complete",
        "ready": (
            frame.get("ready") is True
            and identity.get("ready") is True
            and post_solve.get("ready") is True
        ),
        "static_stages": {
            "pre_solve": frame.get("pre_solve"),
            "matrix_storage": {
                "pool": "+0x154",
                "row_pointers": "+0x158",
                "row_indices": "+0x15c",
                "global_pool": "+0x38",
                "global_row_pointers": "+0x3c",
                "rhs": "+0x40",
            },
            "seed": {
                "function": "FUN_007ba2b0",
                "status": "source-backed",
            },
            "coupling": {
                "JOINT": "FUN_007bbb80",
                "HINGE": "FUN_007bb250",
                "BAR": "FUN_007bb6c0",
                "mixed_HINGE_BAR": "FUN_007bb250",
            },
            "identity_reset": identity.get("builtin_path"),
            "solve_dispatch": frame.get("solve_dispatch"),
            "post_solve": post_solve,
        },
        "runtime_dependencies": runtime_dependencies,
        "lifecycle": [
            "FUN_007b3f40 frame entry",
            "FUN_007b3ed0 constraint refresh",
            "FUN_007bb8d0 per-body reset",
            "FUN_007bc680 contribution build",
            "FUN_007ba570 global vector/matrix export",
            "FUN_007b2210 selected identity rows/columns",
            "provider vtable +0x18 or FUN_007b0f20 solve",
            "FUN_007b4110 solved-vector body application",
        ],
        "evidence": {
            "frame": "FUN_007b3f40",
            "seed": "FUN_007ba2b0",
            "joint_projection": "FUN_007bac60",
            "hinge_projection": "FUN_007bae40",
            "joint_matrix": "FUN_007bbb80",
            "hinge_matrix": "FUN_007bb250",
            "bar_matrix": "FUN_007bb6c0",
            "identity_reset": "FUN_007b2210",
            "post_solve": "FUN_007b4110",
        },
    }


def build_runtime_frame_plan(
    *,
    solver_scalar_count: int,
    body_count: int,
    runtime_record_domains: Sequence[Mapping[str, Any]] | None = None,
    runtime_flags_by_record: Mapping[int | str, int] | None = None,
) -> dict[str, Any]:
    """Build one deterministic frame plan from static record ranges plus optional runtime flags."""
    runtime_flags_available = runtime_flags_by_record is not None
    contract = describe_full_frame_contract(
        solver_scalar_count=solver_scalar_count,
        body_count=body_count,
        runtime_flags_available=runtime_flags_available,
    )

    if runtime_record_domains:
        order = [int(row["record_index"]) for row in runtime_record_domains]
        widths = [0 for _ in runtime_record_domains]
        bases: dict[int, int] = {}
        for row in runtime_record_domains:
            record_index = int(row["record_index"])
            bases[record_index] = int(row["scalar_base"])
            widths[order.index(record_index)] = int(row["width"])
        selection_input = {
            "order": order,
            "block_widths": widths,
            "solver_base_index_by_record": bases,
        }
        selected = derive_builtin_diagonal_reset_nodes(
            selection_input,
            runtime_flag_by_record=runtime_flags_by_record,
        )
    else:
        selected = {
            "status": "needs-runtime-record-domains",
            "ready": False,
            "selected_record_count": 0,
            "selected_records": [],
            "scalar_nodes": [],
            "unique_scalar_nodes": [],
            "unresolved": [
                "runtime record scalar ranges are required to map +0x70 selector flags to scalar nodes"
            ],
        }

    stages = [
        {"stage": "pre_solve", "ready": True},
        {"stage": "seed_matrix", "ready": True},
        {"stage": "numeric_constraint_coupling", "ready": True},
        {
            "stage": "identity_reset",
            "ready": selected.get("ready") is True,
            "runtime_dependent": True,
            "selected_scalar_nodes": selected.get("unique_scalar_nodes", []),
        },
        {"stage": "solve_dispatch", "ready": True},
        {"stage": "post_solve_application", "ready": True},
    ]
    return {
        "format": "SHIFT.SDFRuntimeFramePlan/1",
        "version": 1,
        "status": "ready",
        "ready": True,
        "runtime_flags_available": runtime_flags_available,
        "solver_scalar_count": int(solver_scalar_count),
        "body_count": int(body_count),
        "stages": stages,
        "identity_selector": selected,
        "contract": contract,
    }


__all__ = [
    "FORMAT",
    "describe_full_frame_contract",
    "build_runtime_frame_plan",
]
