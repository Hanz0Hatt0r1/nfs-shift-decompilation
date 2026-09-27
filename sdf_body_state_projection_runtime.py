"""Source-backed SDF body-state projection and post-solve application."""
from __future__ import annotations

from typing import Any

FORMAT = "SHIFT.SDFBodyStateProjectionRuntime/2"


def describe_sdf_body_state_projection_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 2,
        "status": "execution-contract",
        "ready": True,
        "pre_solve_entry": {
            "function": "FUN_007bc680",
            "source_line": 820081,
            "purpose": "build per-body solver-vector/matrix contributions before FUN_007ba570 export",
        },
        "residual_state": {
            "angular": ["+0x48", "+0x50", "+0x58"],
            "axis": ["+0x18", "+0x20", "+0x28"],
            "linear": ["+0x60", "+0x68", "+0x70"],
            "inverse_scalar": "+0x90",
            "body_frame": "+0xb0",
        },
        "pre_solve_call_order": [
            "FUN_007aefb0",
            "FUN_007bac60",
            "FUN_007bae40",
            "FUN_007bb090",
            "FUN_007bbb80",
            "FUN_007bb250",
            "FUN_007bb6c0",
        ],
        "post_solve_entry": {
            "function": "FUN_007b4110",
            "source_line": 814168,
            "purpose": "consume solved scalar vector +0x40 and apply the result to runtime body accumulators",
        },
        "post_solve_projection": {
            "solver_vector": "PhysicsSystem +0x40",
            "joint": {
                "sample_stride": 0xA0,
                "sample_base_offset": "+0x7c",
                "scalar_base_offset": "+0x30",
                "width": 3,
                "positive_body_pointer": "+0x78",
                "negative_body_pointer": "+0x80",
                "positive_point_pointer": "+0x7c +0x18",
                "negative_point_pointer": "+0x84 +0x18",
                "positive_apply": "FUN_007baa70",
                "negative_apply": "FUN_007baaf0",
            },
            "hinge": {
                "sample_stride": 0xA0,
                "sample_base_offset": "+0x7c",
                "scalar_base_offset": "+0x94",
                "width": 2,
                "positive_body_pointer": "+0x78",
                "negative_body_pointer": "+0x80",
                "updates": [
                    "+0x48/+0x50/+0x58 on positive body",
                    "-(+0x48/+0x50/+0x58) on negative body",
                ],
                "component_rule": "solved[base]*sample angular row + solved[base+1]*sample linear row",
            },
            "bar": {
                "sample_stride": 0xB8,
                "sample_base_offset": "+0x7c",
                "scalar_base_offset": "+0x30",
                "width": 1,
                "positive_body_pointer": "+0x78",
                "negative_body_pointer": "+0x80",
                "vector_source": "+0x40/+0x48/+0x50",
                "point_source": "+0x18",
                "positive_apply": "FUN_007baa70",
                "negative_apply": "FUN_007baaf0",
            },
        },
        "solver_reset": {
            "function": "FUN_007b2210",
            "source_line": 812551,
            "builtin": "zero selected matrix row and column, set diagonal to 1.0, zero RHS",
            "provider": "physics provider vtable +0x1c",
        },
        "storage": {
            "solver_vector_contribution": "+0x150",
            "solver_matrix_contribution": "+0x154",
            "row_pointers": "+0x158",
            "row_indices": "+0x15c",
        },
        "evidence": {
            "frame_entry": "FUN_007bc680",
            "post_solve": "FUN_007b4110",
            "joint_projection": "FUN_007bac60",
            "hinge_projection": "FUN_007bae40",
            "bar_projection": "FUN_007bb090",
        },
        "limitations": [
            "The post-solve accumulator channels remain raw body-state storage; no unit labels are assigned.",
            "Provider vtable implementations are still opaque.",
        ],
    }


def describe_sdf_post_solve_order() -> dict[str, Any]:
    return {
        "format": "SHIFT.SDFPostSolveOrder/1",
        "version": 1,
        "ready": True,
        "order": [
            "global matrix/vector preparation",
            "FUN_007b3ed0",
            "FUN_007bb8d0 per body",
            "FUN_007bc680 per body",
            "FUN_007ba570 per body",
            "FUN_007b2210 selected scalar rows",
            "provider vtable +0x18 or FUN_007b0f20",
            "FUN_007b4110 solved-vector application",
        ],
        "source_lines": {
            "frame_entry": 814057,
            "post_solve": 814168,
        },
    }
