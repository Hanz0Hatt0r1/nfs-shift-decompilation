"""Exact spline storage/interpolation runtime reconstructed from SHIFT.exe.

Recovered from FUN_00821970, FUN_008219d0, FUN_00821b30, FUN_00821be0,
FUN_00821d90, FUN_00821f30, FUN_00822130 and FUN_00822220.

A spline record is 0x24 bytes:
  +0x10..+0x18 = vec3
  +0x1c         = scalar
  +0x20         = scalar
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

FORMAT = "SHIFT.SplineStorageRuntime/1"
RECORD_STRIDE = 0x24


@dataclass(frozen=True)
class SplineRecord:
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)  # +0x10
    scalar_1c: float = 1.0  # +0x1c
    scalar_20: float = 0.0  # +0x20


def spline_record_defaults() -> dict[str, Any]:
    """Reproduce FUN_00821970."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "record-defaults",
        "record_size": RECORD_STRIDE,
        "writes": {
            "+0x10": 0.0,
            "+0x14": 0.0,
            "+0x18": 0.0,
            "+0x1c": 1.0,
            "+0x20": 0.0,
        },
        "evidence": {"function": "FUN_00821970"},
    }


def spline_property_registration() -> dict[str, Any]:
    """Reproduce FUN_008219d0 while preserving unresolved global property names."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "property-registration",
        "registration_object": "DAT_00b8e110",
        "properties": [
            {
                "name_symbol": "DAT_00afc8b8",
                "type_id": 0x10,
                "offset": 0x10,
                "flags": 2,
            },
            {
                "name": "MovementRate",
                "type_id": 1,
                "offset": 0x1c,
                "flags": 2,
            },
            {
                "name_symbol": "DAT_00b15fa0",
                "type_id": 1,
                "offset": 0x20,
                "flags": 2,
            },
        ],
        "evidence": {"function": "FUN_008219d0", "registration_helper": "FUN_0063a280"},
    }


def map_spline_index(
    *,
    index: int,
    count: int,
    mode: int,
    mirror_decision: int | None = None,
) -> dict[str, Any]:
    """Reproduce FUN_00821b30 modes 0..3."""
    n = int(count)
    i = int(index)
    m = int(mode)
    if n <= 0:
        raise ValueError("spline count must be positive")
    if m == 0:
        mapped = 0 if i < 0 else min(i, n - 1)
        return {"format": FORMAT, "version": 1, "mode": m, "mapped": mapped}
    if m == 1:
        mapped = i % n
        return {"format": FORMAT, "version": 1, "mode": m, "mapped": mapped}
    if m not in (2, 3):
        raise ValueError("mode must be 0, 1, 2, or 3")
    if n == 1:
        raise ValueError("mirror mapping divides by count-1")
    decision = int(mirror_decision) if mirror_decision is not None else 0
    remainder = i % (n - 1)
    mapped = remainder if (decision & 1) == 0 else (n - 1 - remainder)
    return {
        "format": FORMAT,
        "version": 1,
        "mode": m,
        "mapped": mapped,
        "mirror_decision": decision,
        "evidence": {
            "function": "FUN_00821b30",
            "mirror_helper_chain": ["FUN_009011e0", "FUN_00901310"],
        },
    }


def cubic_scalar_interpolation(
    records: Sequence[SplineRecord],
    *,
    index: int,
    t: float,
    mode: int,
) -> dict[str, Any]:
    """Reproduce FUN_00821be0 including edge attenuation and 0.1 floor."""
    if not records:
        raise ValueError("records cannot be empty")
    mapped = [
        map_spline_index(index=index + delta, count=len(records), mode=mode)["mapped"]
        for delta in (-1, 0, 1, 2)
    ]
    values = [records[i].scalar_1c for i in mapped]
    x = float(t)
    value = (
        ((x * x * x - x * x) * 0.5 * values[3])
        + (((x * x * 4.0 + x) - x * x * x * 3.0) * 0.5 * values[2])
        + (((x * x * 2.0 - x) - x * x * x) * 0.5 * values[0])
        + (((2.0 - x * x * 5.0) + x * x * x * 3.0) * 0.5 * values[1])
    )

    edge_factor: float | None = None
    if int(index) < 1:
        x = max(0.0, min(1.0, x))
        y = (1.0 - x) ** 16
        edge_factor = 1.0 - y
        value *= edge_factor
    elif int(index) >= len(records) - 2:
        x = max(0.0, min(1.0, x))
        y = x ** 16
        edge_factor = 1.0 - y
        value *= edge_factor

    value = max(0.1, value)
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "scalar-interpolation",
        "mapped_indices": mapped,
        "input_values": values,
        "t": float(t),
        "edge_factor": edge_factor,
        "value": value,
        "evidence": {
            "function": "FUN_00821be0",
            "source_offset": "+0x1c",
            "minimum_return": 0.1,
            "edge_power": 16,
        },
    }


def scalar_20_interpolation_contract(
    records: Sequence[SplineRecord],
    *,
    index: float,
    t: float,
    mode: int,
    fallback: float,
) -> dict[str, Any]:
    """Trace FUN_00821d90; the source calls the cubic helper for its side effect path."""
    if not records:
        raise ValueError("records cannot be empty")
    indices = [
        map_spline_index(index=int(index) + d, count=len(records), mode=mode)["mapped"]
        for d in (-1, 0, 1, 2)
    ]
    values = [records[i].scalar_20 for i in indices]
    replaced = [v if v > 0.0 else float(fallback) for v in values]
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "scalar-20-interpolation",
        "mapped_indices": indices,
        "effective_values": replaced,
        "actions": [
            {
                "action": "FUN_008218b0",
                "arguments": {
                    "values": replaced,
                    "t": float(t),
                },
                "return_consumed": False,
            }
        ],
        "evidence": {
            "function": "FUN_00821d90",
            "source_offset": "+0x20",
            "nonpositive_fallback": "param_4",
        },
    }


def resize_spline_records(
    records: Sequence[SplineRecord],
    new_count: int,
) -> dict[str, Any]:
    """Reproduce FUN_00821f30's release/reallocation/default construction boundary."""
    count = int(new_count)
    if count < 0:
        raise ValueError("new_count must be non-negative")
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "resize",
        "old_count": len(records),
        "new_count": count,
        "record_stride": RECORD_STRIDE,
        "actions": [
            {"action": "release-old-record-array", "helper": "FUN_00886930 or vtable slot 0"},
            {"action": "write +0x10", "value": count},
            {
                "action": "allocate",
                "bytes": 4 + count * RECORD_STRIDE,
                "helper": "FUN_008868c0",
            },
            {
                "action": "construct records",
                "count": count,
                "constructor": "FUN_00821970",
            },
        ],
        "evidence": {"function": "FUN_00821f30", "array_pointer": "+0x14"},
    }


def interpolate_position(
    records: Sequence[SplineRecord],
    *,
    index: int,
    t: float,
    mode: int,
) -> dict[str, Any]:
    """Reproduce FUN_00822130's four-record vec3 cubic interpolation."""
    if not records:
        raise ValueError("records cannot be empty")
    mapped = [
        map_spline_index(index=index + d, count=len(records), mode=mode)["mapped"]
        for d in (-1, 0, 1, 2)
    ]
    p = [records[i].position for i in mapped]
    x = float(t)
    x2 = x * x
    x3 = x2 * x
    f4 = (x2 * 2.0 - x - x3) * 0.5
    f3 = (2.0 - x2 * 5.0 + x3 * 3.0) * 0.5
    f2 = (x2 * 4.0 + x - x3 * 3.0) * 0.5
    f1 = (x3 - x2) * 0.5
    result = [
        f4 * p[0][axis] + f3 * p[1][axis] + f2 * p[2][axis] + f1 * p[3][axis]
        for axis in range(3)
    ]
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "position-interpolation",
        "mapped_indices": mapped,
        "value": result,
        "basis_coefficients": [f4, f3, f2, f1],
        "evidence": {"function": "FUN_00822130", "source_offset": "+0x10"},
    }


def normalize_spline_parameter(
    *,
    segment_index: float,
    parameter: float,
    count: int,
    mode: int,
) -> dict[str, Any]:
    """Reproduce FUN_00822220's parameter normalization then return mapped state."""
    idx = float(segment_index)
    t = float(parameter)
    while t < 0.0:
        idx -= 1.0
        t += 1.0
    while t > 1.0:
        idx += 1.0
        t -= 1.0

    mapped = map_spline_index(
        index=int(idx),
        count=count,
        mode=mode,
    )["mapped"]
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "parameter-normalization",
        "segment_index": idx,
        "parameter": t,
        "mapped_index": mapped,
        "evidence": {
            "function": "FUN_00822220",
            "normalization": "while t<0 decrement index; while t>1 increment index",
        },
    }
