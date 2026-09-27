"""Source-backed body-state projection and constraint-coupling contract."""
from __future__ import annotations

from typing import Any

FORMAT = "SHIFT.SDFBodyStateProjectionRuntime/1"


def describe_sdf_body_state_projection_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "execution-contract",
        "ready": True,
        "entry": "FUN_007bc680",
        "residual_state": {
            "accumulator_1": "+0x48",
            "accumulator_2": "+0x50",
            "accumulator_3": "+0x58",
            "state_axis_1": "+0x18",
            "state_axis_2": "+0x20",
            "state_axis_3": "+0x28",
            "inverse_scalar": "+0x90",
            "linear_1": "+0x60",
            "linear_2": "+0x68",
            "linear_3": "+0x70",
            "body_frame": "+0xb0",
        },
        "constraint_projection_equations": {
            "JOINT": {
                "source_function": "FUN_007bac60",
                "sample_stride": 0x40,
                "scalar_base_field": "+0x30",
                "body_accumulator_base": "+0x150",
                "cross_product_terms": {
                    "d2": "sample[+0x28]*body[+0x20] - sample[+0x20]*body[+0x28]",
                    "d3": "body[+0x28]*sample[+0x18] - sample[+0x28]*body[+0x18]",
                    "d5": "sample[+0x20]*body[+0x18] - body[+0x20]*sample[+0x18]",
                },
                "output_components": [
                    "lane0 = sign * d4",
                    "lane1 = sign * d6",
                    "lane2 = sign * d2",
                ],
                "destination_layout": "opaque; do not alias to body +0x158 pointer-table storage",
                "sign_source": "sample +0x34: zero => add, nonzero => subtract",
            },
            "HINGE": {
                "source_function": "FUN_007bae40",
                "sample_stride": 0xA0,
                "scalar_base_field": "+0x94",
                "body_accumulator_base": "+0x150",
                "frame_terms": [
                    "sample rows +0x48/+0x50/+0x58",
                    "sample rows +0x60/+0x68/+0x70",
                ],
                "side_zero": "add transformed velocity terms to primary accumulator",
                "side_nonzero": "transform sample through body +0xd4 and subtract transformed terms",
            },
            "BAR": {
                "source_function": "FUN_007bb090",
                "sample_stride": 0x60,
                "scalar_base_field": "+0x30",
                "body_accumulator_base": "+0x150",
                "cross_product_terms": {
                    "d3": "body[+0x20]*sample[+0x28] - body[+0x28]*sample[+0x20]",
                    "d5": "body[+0x28]*sample[+0x18] - sample[+0x28]*body[+0x18]",
                    "d4": "sample[+0x20]*body[+0x18] - body[+0x20]*sample[+0x18]",
                },
                "output_components": [
                    "primary lane = sign * d3",
                ],
                "destination_layout": "opaque; do not alias to body +0x158 pointer-table storage",
                "sign_source": "sample +0x34: zero => add, nonzero => subtract with +0x48 correction term",
            },
        },
        "pre_coupling": [
            {
                "function": "FUN_007aefb0",
                "purpose": "transform residual accumulator triplet through the body frame",
            },
            {
                "function": "FUN_007bac60",
                "purpose": "apply transformed body state to JOINT sampled rows and primary accumulator",
            },
            {
                "function": "FUN_007bae40",
                "purpose": "apply transformed body state to HINGE sampled rows and primary accumulator",
            },
            {
                "function": "FUN_007bb090",
                "purpose": "apply transformed body state to BAR sampled rows and primary accumulator",
            },
        ],
        "coupling": [
            {
                "function": "FUN_007bb250",
                "scope": "HINGE-HINGE",
                "result_storage": "+0x158 row-pointer table",
                "value_source": "+0x150 primary accumulator",
                "side_rule": "equal sample-side flags add; differing flags subtract",
            },
            {
                "function": "FUN_007bb6c0",
                "scope": "BAR-BAR",
                "result_storage": "+0x158 row-pointer table",
                "value_source": "+0x150 primary accumulator",
                "side_rule": "equal sample-side flags add; differing flags subtract",
            },
        ],
        "state_transforms": {
            "residual_equations": {
                "x": "+0x48 - (+0x40*+0x20 - +0x38*+0x28)",
                "y": "+0x50 - (+0x30*+0x28 - +0x40*+0x18)",
                "z": "+0x58 - (+0x38*+0x18 - +0x30*+0x20)",
            },
            "linear_projection": "multiply +0x60/+0x68/+0x70 by +0x90 before joint/hinge/bar accumulation",
        },
        "call_order": [
            "FUN_007aefb0",
            "FUN_007bac60",
            "FUN_007bae40",
            "FUN_007bb090",
            "FUN_007bbb80",
            "FUN_007bb250",
            "FUN_007bb6c0",
        ],
        "storage": {
            "primary_accumulator": "+0x150",
            "secondary_accumulator": "+0x154",
            "row_pointer_table": "+0x158",
            "row_index_vector": "+0x15c",
        },
        "evidence": {
            "entry": "FUN_007bc680",
            "joint_accumulator_helper": "FUN_007bac60",
            "hinge_accumulator_helper": "FUN_007bae40",
            "bar_accumulator_helper": "FUN_007bb090",
            "hinge_coupling_helper": "FUN_007bb250",
            "bar_coupling_helper": "FUN_007bb6c0",
        },
        "limitations": [
            "Accumulator channels remain storage coordinates; no unsupported force/torque units are assigned.",
            "JOINT/HINGE destination slots remain opaque until the direct function-body slice is available.",
            "FUN_007bbb80, FUN_007bb250 and FUN_007bb6c0 retain their concrete numerical side effects outside this metadata contract.",
            "Provider-specific solver behavior remains separate.",
        ],
    }
