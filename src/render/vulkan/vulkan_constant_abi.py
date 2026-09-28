"""Vulkan-side layout for the proven SHIFT D3D9 float c-register ABI.

The neutral RenderCommand keeps stage + register_index explicit. Vulkan maps vertex
and pixel banks to separate descriptor bindings so they cannot alias accidentally.
"""
from __future__ import annotations

from typing import Any, Mapping

FORMAT = "SHIFT.VulkanConstantBufferLayout/1"
REGISTER_BYTES = 16
MAX_REGISTERS = 256
STAGE_BINDINGS = {"vertex": 14, "pixel": 15}


def build_vulkan_constant_layout(render_command: Mapping[str, Any]) -> dict[str, Any]:
    if render_command.get("format") != "SHIFT.RenderCommand/1":
        return {
            "format": FORMAT,
            "status": "invalid",
            "ready": False,
            "blocking_reasons": ["render-command:invalid-format"],
        }

    stage_ranges: dict[str, set[int]] = {"vertex": set(), "pixel": set()}
    reasons: list[str] = []
    for submesh in render_command.get("submeshes", []) or []:
        for row in submesh.get("constant_commands", []) or []:
            stage = str(row.get("stage") or "").lower()
            if stage not in stage_ranges:
                reasons.append(f"vulkan-constants:unsupported-stage:{stage or 'missing'}")
                continue
            try:
                start = int(row.get("register_index"))
                count = int(row.get("register_count"))
            except (TypeError, ValueError):
                reasons.append("vulkan-constants:register-range-invalid")
                continue
            if start < 0 or count <= 0 or start + count > MAX_REGISTERS:
                reasons.append(f"vulkan-constants:register-range-invalid:{stage}:{start}")
                continue
            for register in range(start, start + count):
                stage_ranges[stage].add(register)

    return {
        "format": FORMAT,
        "status": "ready" if not reasons else "invalid",
        "ready": not reasons,
        "blocking_reasons": list(dict.fromkeys(reasons)),
        "descriptor_set": 0,
        "register_bytes": REGISTER_BYTES,
        "max_registers": MAX_REGISTERS,
        "stages": {
            stage: {
                "descriptor_binding": STAGE_BINDINGS[stage],
                "registers": sorted(stage_ranges[stage]),
                "buffer_size": MAX_REGISTERS * REGISTER_BYTES,
                "register_offset_formula": "register_index * 16",
            }
            for stage in stage_ranges
        },
        "abi": {
            "source": "SHIFT.RenderCommand/1 constant_commands",
            "d3d9_register_stride_bytes": REGISTER_BYTES,
            "allows_stage_aliasing": False,
        },
    }
