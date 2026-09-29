"""Translate typed BMT render state into evidence-backed native pipeline state."""
from __future__ import annotations

from typing import Any, Mapping

from d3d9_vulkan_state import BLEND, BLEND_OP, COMPARE
from material_cull_state import translate_bmt_cull

FORMAT = "SHIFT.MaterialPipelineState/1"

# Retail engine-enum -> D3D9 tables recovered from SHIFT.exe:
#   FUN_0083f630 / DAT_00b8ecf4 : test function
#   FUN_0083f650 / DAT_00b8ed38 : blend factor
#   FUN_0083f670 / DAT_00b8eda8 : blend operation
#   FUN_0083f690 / DAT_00b8edd4 : stencil operation
TEST_TO_D3D9 = tuple(range(1, 9))
BLEND_TO_D3D9 = tuple(range(1, 12))
BLEND_OP_TO_D3D9 = (1, 3, 4, 5, 2)
STENCIL_OP_TO_D3D9 = tuple(range(1, 9))

# FUN_00839d70 initializes this state before per-material XML/BMT overrides.
DEFAULTS = {
    "cull": 2,  # EBFCT_ANTICLOCKWISE
    "depth_enabled": True,
    "depth_function": 3,  # ETF_LESS_THAN_OR_EQUAL
    "depth_write_enabled": True,
    "alpha_test_enabled": False,
    "alpha_test_function": 7,  # ETF_PASS
    "alpha_test_value": 0.0,
    "alpha_blend_enabled": False,
    "source_blend": 1,  # EBF_ONE
    "dest_blend": 0,  # EBF_ZERO
    "blend_op": 0,  # EBO_ADD
    "separate_alpha": False,
    "alpha_source_blend": 1,
    "alpha_dest_blend": 0,
    "alpha_blend_op": 0,
    "stencil_enabled": False,
    "stencil_test_mask": 0xFFFFFFFF,
    "stencil_test_ref": 0,
    "stencil_test_function": 7,  # ETF_PASS
    "stencil_write_mask": 0xFFFFFFFF,
    "stencil_fail_op": 0,  # ESO_NO_CHANGE
    "stencil_zfail_op": 0,
    "stencil_pass_op": 0,
    "stencil_two_sided": False,
}


def _enum_index(value: Any, default: int, label: str, blockers: list[str]) -> int:
    if value is None:
        return default
    if isinstance(value, Mapping):
        status = value.get("status")
        index = value.get("engine_enum_index")
        if status == "known" and isinstance(index, int):
            return index
        blockers.append(f"material-pipeline:{label}-enum-unresolved")
        return default
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    blockers.append(f"material-pipeline:{label}-enum-invalid")
    return default


def _bool(value: Any, default: bool, label: str, blockers: list[str]) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    blockers.append(f"material-pipeline:{label}-bool-invalid")
    return default


def _d3d_lookup(
    index: int,
    table: tuple[int, ...],
    label: str,
    blockers: list[str],
) -> int:
    if 0 <= index < len(table):
        return table[index]
    blockers.append(f"material-pipeline:{label}-index-out-of-range:{index}")
    return table[0]


def build_material_pipeline_state(
    render_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    state = dict(render_state or {})
    blockers: list[str] = []

    unmapped_groups = state.get("unmapped_groups") or []
    if unmapped_groups:
        blockers.append("material-pipeline:unmapped-bmt-state-group")

    cull = translate_bmt_cull(state.get("cull"))
    blockers.extend(cull.get("blocking_reasons") or [])

    depth = state.get("depth")
    if depth is not None and not isinstance(depth, Mapping):
        blockers.append("material-pipeline:depth-state-invalid")
        depth = {}
    depth = dict(depth or {})
    if depth.get("unmapped_fields"):
        blockers.append("material-pipeline:depth-fields-unmapped")

    depth_enabled = _bool(
        depth.get("enabled"),
        DEFAULTS["depth_enabled"],
        "depth-enabled",
        blockers,
    )
    depth_write = _bool(
        depth.get("write_enabled"),
        DEFAULTS["depth_write_enabled"],
        "depth-write-enabled",
        blockers,
    )
    depth_index = _enum_index(
        depth.get("function"),
        DEFAULTS["depth_function"],
        "depth-function",
        blockers,
    )
    depth_d3d = _d3d_lookup(
        depth_index,
        TEST_TO_D3D9,
        "depth-function",
        blockers,
    )
    depth_vk = COMPARE.get(depth_d3d)
    if depth_vk is None:
        blockers.append(
            f"material-pipeline:depth-vulkan-compare-missing:{depth_d3d}"
        )

    alpha_test = state.get("alpha_test")
    if alpha_test is not None and not isinstance(alpha_test, Mapping):
        blockers.append("material-pipeline:alpha-test-state-invalid")
        alpha_test = {}
    alpha_test = dict(alpha_test or {})
    if alpha_test.get("unmapped_fields"):
        blockers.append("material-pipeline:alpha-test-fields-unmapped")
    alpha_test_enabled = _bool(
        alpha_test.get("enabled"),
        DEFAULTS["alpha_test_enabled"],
        "alpha-test-enabled",
        blockers,
    )
    alpha_test_index = _enum_index(
        alpha_test.get("function"),
        DEFAULTS["alpha_test_function"],
        "alpha-test-function",
        blockers,
    )
    alpha_test_d3d = _d3d_lookup(
        alpha_test_index,
        TEST_TO_D3D9,
        "alpha-test-function",
        blockers,
    )
    alpha_test_vk = COMPARE.get(alpha_test_d3d)
    alpha_test_value = alpha_test.get(
        "value_normalized",
        DEFAULTS["alpha_test_value"],
    )
    if not isinstance(alpha_test_value, (int, float)) or isinstance(
        alpha_test_value, bool
    ):
        blockers.append("material-pipeline:alpha-test-value-invalid")
        alpha_test_value = DEFAULTS["alpha_test_value"]
    alpha_test_value = float(alpha_test_value)
    if alpha_test_enabled:
        blockers.append(
            "material-pipeline:alpha-test-enabled-requires-shader-discard"
        )

    blend = state.get("alpha_blend")
    if blend is not None and not isinstance(blend, Mapping):
        blockers.append("material-pipeline:alpha-blend-state-invalid")
        blend = {}
    blend = dict(blend or {})
    if blend.get("unmapped_fields"):
        blockers.append("material-pipeline:alpha-blend-fields-unmapped")

    blend_enabled = _bool(
        blend.get("enabled"),
        DEFAULTS["alpha_blend_enabled"],
        "alpha-blend-enabled",
        blockers,
    )
    src_index = _enum_index(
        blend.get("source_blend"),
        DEFAULTS["source_blend"],
        "source-blend",
        blockers,
    )
    dst_index = _enum_index(
        blend.get("dest_blend"),
        DEFAULTS["dest_blend"],
        "dest-blend",
        blockers,
    )
    op_index = _enum_index(
        blend.get("blend_op"),
        DEFAULTS["blend_op"],
        "blend-op",
        blockers,
    )
    src_d3d = _d3d_lookup(
        src_index, BLEND_TO_D3D9, "source-blend", blockers
    )
    dst_d3d = _d3d_lookup(
        dst_index, BLEND_TO_D3D9, "dest-blend", blockers
    )
    op_d3d = _d3d_lookup(
        op_index, BLEND_OP_TO_D3D9, "blend-op", blockers
    )
    src_vk = BLEND.get(src_d3d)
    dst_vk = BLEND.get(dst_d3d)
    op_vk = BLEND_OP.get(op_d3d)
    if src_vk is None:
        blockers.append(
            f"material-pipeline:source-blend-vulkan-missing:{src_d3d}"
        )
    if dst_vk is None:
        blockers.append(
            f"material-pipeline:dest-blend-vulkan-missing:{dst_d3d}"
        )
    if op_vk is None:
        blockers.append(
            f"material-pipeline:blend-op-vulkan-missing:{op_d3d}"
        )

    blockers = list(dict.fromkeys(blockers))
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if not blockers else "blocked",
        "ready": not blockers,
        "blocking_reasons": blockers,
        "evidence_status": "retail-static",
        "cull": cull,
        "depth": {
            "enabled": depth_enabled,
            "write_enabled": depth_write,
            "engine_compare_index": depth_index,
            "d3d9_compare_value": depth_d3d,
            "vulkan_compare_op": depth_vk,
        },
        "alpha_test": {
            "enabled": alpha_test_enabled,
            "engine_compare_index": alpha_test_index,
            "d3d9_compare_value": alpha_test_d3d,
            "vulkan_compare_op": alpha_test_vk,
            "reference": alpha_test_value,
            "execution": (
                "requires-shader-discard"
                if alpha_test_enabled else "disabled"
            ),
        },
        "blend": {
            "enabled": blend_enabled,
            "source_engine_index": src_index,
            "dest_engine_index": dst_index,
            "op_engine_index": op_index,
            "source_d3d9_value": src_d3d,
            "dest_d3d9_value": dst_d3d,
            "op_d3d9_value": op_d3d,
            "vulkan_src_factor": src_vk,
            "vulkan_dst_factor": dst_vk,
            "vulkan_op": op_vk,
            # Separate-alpha defaults false in FUN_00839d70. No corpus
            # Resource IDs for the separate-alpha override fields are known yet.
            "separate_alpha": False,
        },
        "vulkan_cull_mode": cull.get("vulkan_cull_mode"),
        "vulkan_depth_test_enable": depth_enabled,
        "vulkan_depth_write_enable": depth_write,
        "vulkan_depth_compare_op": depth_vk,
        "vulkan_blend_enable": blend_enabled,
        "vulkan_src_color_blend_factor": src_vk,
        "vulkan_dst_color_blend_factor": dst_vk,
        "vulkan_color_blend_op": op_vk,
        "vulkan_src_alpha_blend_factor": src_vk,
        "vulkan_dst_alpha_blend_factor": dst_vk,
        "vulkan_alpha_blend_op": op_vk,
        "policy": {
            "alpha_test": "fail-closed-when-enabled",
            "depth_bias": "blocked-if-present-as-unmapped-field",
            "separate_alpha": "blocked-if-present-as-unmapped-field",
            "stencil": "blocked-if-present-as-unmapped-group",
            "allows_inference": False,
        },
        "evidence": {
            "defaults_function": "FUN_00839d70",
            "test_lookup_function": "FUN_0083f630",
            "test_lookup_table_va": "0x00b8ecf4",
            "blend_lookup_function": "FUN_0083f650",
            "blend_lookup_table_va": "0x00b8ed38",
            "blend_op_lookup_function": "FUN_0083f670",
            "blend_op_lookup_table_va": "0x00b8eda8",
        },
    }


__all__ = [
    "FORMAT",
    "TEST_TO_D3D9",
    "BLEND_TO_D3D9",
    "BLEND_OP_TO_D3D9",
    "STENCIL_OP_TO_D3D9",
    "DEFAULTS",
    "build_material_pipeline_state",
]
