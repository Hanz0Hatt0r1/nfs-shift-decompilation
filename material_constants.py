"""Deterministic D3D9-style material constant register packing.

The packer consumes already-reflected SHIFT.MaterialUniformBinding/1 records.
Only proven float/vector constants are serialized into 16-byte c-register slots;
matrix orientation and non-float CTAB types remain explicit blockers.
"""
from __future__ import annotations

from typing import Any


FORMAT = "SHIFT.MaterialConstantPayload/1"
REGISTER_WIDTH = 4


def _flatten_value(value: Any) -> list[float] | None:
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, (list, tuple)):
        flat: list[float] = []
        for item in value:
            if isinstance(item, (list, tuple)):
                nested = _flatten_value(item)
                if nested is None:
                    return None
                flat.extend(nested)
            elif isinstance(item, (int, float)):
                flat.append(float(item))
            else:
                return None
        return flat
    return None


def _type_component_width(ctab_type: str) -> int | None:
    label = str(ctab_type or "").lower()
    if label == "float":
        return 1
    if label in {"float2", "float3", "float4"}:
        return int(label[-1])
    return None


def pack_material_constant_payload(uniform_binding: dict[str, Any]) -> dict[str, Any]:
    """Pack proven float/vector material uniforms into 16-byte register slots."""
    if uniform_binding.get("format") not in (None, "SHIFT.MaterialUniformBinding/1"):
        return {
            "format": FORMAT,
            "ready": False,
            "blocking_reasons": ["uniform-binding:invalid-format"],
            "register_count": 0,
            "registers": [],
            "bindings": [],
            "ubo_binding": 14,
            "matrix_packing": "blocked-until-orientation-proven",
        }

    reasons: list[str] = []
    register_values: dict[int, list[float]] = {}
    binding_reports: list[dict[str, Any]] = []

    for binding in uniform_binding.get("bindings", []) or []:
        name = binding.get("name")
        try:
            register_index = int(binding.get("register_index"))
            register_count = int(binding.get("register_count"))
        except (TypeError, ValueError):
            binding_reports.append({
                "name": name,
                "status": "blocked",
                "reason": "register-range-invalid",
            })
            reasons.append("uniform-payload:register-range-invalid:" + str(name))
            continue

        if binding.get("register_set") != 2:
            binding_reports.append({
                "name": name,
                "status": "blocked",
                "reason": "unexpected-register-set",
            })
            reasons.append("uniform-payload:unexpected-register-set:" + str(name))
            continue
        if register_index < 0 or register_count <= 0:
            binding_reports.append({
                "name": name,
                "status": "blocked",
                "reason": "register-range-invalid",
            })
            reasons.append("uniform-payload:register-range-invalid:" + str(name))
            continue

        ctab_type = str(binding.get("ctab_type") or "")
        width = _type_component_width(ctab_type)
        if width is None:
            binding_reports.append({
                "name": name,
                "status": "blocked",
                "reason": f"unsupported-ctab-type:{ctab_type or 'missing'}",
            })
            reasons.append(
                "uniform-payload:unsupported-ctab-type:"
                + str(name)
                + ":"
                + (ctab_type or "missing")
            )
            continue

        values = _flatten_value(binding.get("value"))
        if values is None or not values:
            binding_reports.append({
                "name": name,
                "status": "blocked",
                "reason": "value-missing-or-numeric-invalid",
            })
            reasons.append("uniform-payload:value-invalid:" + str(name))
            continue

        expected_components = width * register_count
        if len(values) > expected_components:
            binding_reports.append({
                "name": name,
                "status": "blocked",
                "reason": "value-exceeds-register-range",
                "value_components": len(values),
                "capacity_components": register_count * REGISTER_WIDTH,
            })
            reasons.append("uniform-payload:value-exceeds-register-range:" + str(name))
            continue

        capacity = register_count * REGISTER_WIDTH
        padded = values + [0.0] * (capacity - len(values))
        binding_reports.append({
            "name": name,
            "status": "ready",
            "ctab_type": ctab_type,
            "register_index": register_index,
            "register_count": register_count,
            "component_count": len(values),
            "component_width": width,
            "registers": list(range(register_index, register_index + register_count)),
        })

        for offset in range(register_count):
            reg = register_index + offset
            chunk = padded[offset * REGISTER_WIDTH:(offset + 1) * REGISTER_WIDTH]
            existing = register_values.get(reg)
            if existing is None:
                register_values[reg] = chunk
            elif existing != chunk:
                reasons.append(f"uniform-payload:register-conflict:{reg}")

    registers = [
        {
            "register_index": reg,
            "values": values,
            "byte_offset": reg * 16,
            "byte_size": 16,
        }
        for reg, values in sorted(register_values.items())
    ]

    return {
        "format": FORMAT,
        "ready": not reasons and all(
            item.get("status") == "ready" for item in binding_reports
        ),
        "blocking_reasons": list(dict.fromkeys(reasons)),
        "register_count": len(registers),
        "registers": registers,
        "bindings": binding_reports,
        "ubo_binding": 14,
        "matrix_packing": "blocked-until-orientation-proven",
    }
