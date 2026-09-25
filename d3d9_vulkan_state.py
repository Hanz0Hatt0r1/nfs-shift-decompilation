"""Conservative D3D9 fixed-function state -> Vulkan state normalization.

This module translates numeric D3D9 render/sampler state values only where the
corresponding Vulkan state is explicit and lossless. Unsupported/ambiguous modes
remain hard blockers.
"""
from __future__ import annotations

from typing import Any, Mapping

FORMAT = "SHIFT.D3D9VulkanState/1"

COMPARE = {
    1: "VK_COMPARE_OP_NEVER",
    2: "VK_COMPARE_OP_LESS",
    3: "VK_COMPARE_OP_EQUAL",
    4: "VK_COMPARE_OP_LESS_OR_EQUAL",
    5: "VK_COMPARE_OP_GREATER",
    6: "VK_COMPARE_OP_NOT_EQUAL",
    7: "VK_COMPARE_OP_GREATER_OR_EQUAL",
    8: "VK_COMPARE_OP_ALWAYS",
}

CULL = {
    1: "NONE",
    2: "FRONT",
    3: "BACK",
}

ADDRESS = {
    1: "VK_SAMPLER_ADDRESS_MODE_REPEAT",
    2: "VK_SAMPLER_ADDRESS_MODE_MIRRORED_REPEAT",
    3: "VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE",
    4: "VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_BORDER",
    5: "VK_SAMPLER_ADDRESS_MODE_MIRROR_CLAMP_TO_EDGE",
}

FILTER = {
    1: "VK_FILTER_NEAREST",
    2: "VK_FILTER_LINEAR",
    3: "VK_FILTER_LINEAR",
}

BLEND = {
    1: "VK_BLEND_FACTOR_ZERO",
    2: "VK_BLEND_FACTOR_ONE",
    3: "VK_BLEND_FACTOR_SRC_COLOR",
    4: "VK_BLEND_FACTOR_ONE_MINUS_SRC_COLOR",
    5: "VK_BLEND_FACTOR_SRC_ALPHA",
    6: "VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA",
    7: "VK_BLEND_FACTOR_DST_ALPHA",
    8: "VK_BLEND_FACTOR_ONE_MINUS_DST_ALPHA",
    9: "VK_BLEND_FACTOR_DST_COLOR",
    10: "VK_BLEND_FACTOR_ONE_MINUS_DST_COLOR",
    11: "VK_BLEND_FACTOR_SRC_ALPHA_SATURATE",
}


def _value(states: Mapping[Any, Any], key: int, default: Any = None) -> Any:
    return states.get(key, states.get(str(key), default))


def translate_render_states(states: Mapping[Any, Any]) -> dict[str, Any]:
    blockers: list[str] = []

    z_enable = _value(states, 7)
    z_write = _value(states, 14)
    z_func = _value(states, 23)
    alpha_blend = _value(states, 27)
    src_blend = _value(states, 19)
    dst_blend = _value(states, 20)
    cull_mode = _value(states, 22)
    color_write = _value(states, 168)

    if z_func is not None and z_func not in COMPARE:
        blockers.append(f"d3d9-vulkan-state:unsupported-zfunc:{z_func}")
    if cull_mode is not None and cull_mode not in CULL:
        blockers.append(f"d3d9-vulkan-state:unsupported-cullmode:{cull_mode}")
    for name, value in (("srcblend", src_blend), ("dstblend", dst_blend)):
        if value is not None and value not in BLEND:
            blockers.append(f"d3d9-vulkan-state:unsupported-{name}:{value}")

    color_mask = None
    if color_write is not None:
        if not isinstance(color_write, int) or color_write < 0 or color_write > 0xF:
            blockers.append(f"d3d9-vulkan-state:invalid-colorwrite-mask:{color_write}")
        else:
            color_mask = {
                "r": bool(color_write & 0x1),
                "g": bool(color_write & 0x2),
                "b": bool(color_write & 0x4),
                "a": bool(color_write & 0x8),
            }

    blend_enable = bool(alpha_blend) if alpha_blend is not None else False
    blend_state = {
        "enable": blend_enable,
        "src_factor": BLEND.get(src_blend) if src_blend is not None else None,
        "dst_factor": BLEND.get(dst_blend) if dst_blend is not None else None,
    }

    return {
        "format": FORMAT,
        "ready": not blockers,
        "status": "ready" if not blockers else "blocked",
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "depth": {
            "test_enable": bool(z_enable) if z_enable is not None else None,
            "write_enable": bool(z_write) if z_write is not None else None,
            "compare_op": COMPARE.get(z_func) if z_func is not None else None,
        },
        "raster": {
            "cull_mode": CULL.get(cull_mode) if cull_mode is not None else None,
            "front_face_policy": "runtime-capture-required",
        },
        "blend": blend_state,
        "color_write_mask": color_mask,
        "policy": {
            "alpha_test": "unsupported-until-shader-discard-evidence",
            "cull_front_face": "not-inferred",
            "blend_factor_source": "D3D9 state values",
            "allows_inference": False,
        },
    }


def translate_sampler_state(
    sampler_register: int,
    states: Mapping[Any, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    address_u = _value(states, 1)
    address_v = _value(states, 2)
    address_w = _value(states, 3)
    min_filter = _value(states, 6)
    mag_filter = _value(states, 5)

    for name, value, table in (
        ("address_u", address_u, ADDRESS),
        ("address_v", address_v, ADDRESS),
        ("address_w", address_w, ADDRESS),
        ("min_filter", min_filter, FILTER),
        ("mag_filter", mag_filter, FILTER),
    ):
        if value is not None and value not in table:
            blockers.append(
                f"d3d9-vulkan-state:unsupported-{name}:s{sampler_register}:{value}"
            )

    return {
        "format": FORMAT,
        "sampler_register": sampler_register,
        "ready": not blockers,
        "status": "ready" if not blockers else "blocked",
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "address_mode": {
            "u": ADDRESS.get(address_u),
            "v": ADDRESS.get(address_v),
            "w": ADDRESS.get(address_w),
        },
        "filter": {
            "min": FILTER.get(min_filter),
            "mag": FILTER.get(mag_filter),
        },
        "policy": {
            "border_color": "unsupported-until-captured-and-proven",
            "allows_inference": False,
        },
    }
