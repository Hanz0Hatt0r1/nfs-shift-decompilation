"""Evidence-backed camera-data and area primitive ABI.

Recovered from FUN_0081e6c0, FUN_0081e6f0, FUN_0081e710, FUN_0081e750,
FUN_0081e780, FUN_0081e820, FUN_0081e880 and FUN_0081e920.

Sphere and box area objects are kept separate. The distance helpers expose
opaque math/helper results rather than assigning gameplay names.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.CameraDataAreaPrimitivesRuntime/1"


def describe_camera_data_copy(
    *,
    destination: str,
    source: str,
) -> dict[str, Any]:
    """Trace FUN_0081e6c0."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "camera-data-copy",
        "actions": [
            {
                "action": "FUN_0081af70",
                "destination": destination,
                "source": source,
            },
            {
                "action": "FUN_0081d180",
                "destination": f"{destination}+0x80",
                "source": f"{source}+0x80",
            },
        ],
        "evidence": {
            "function": "FUN_0081e6c0",
            "base_copy": "FUN_0081af70",
            "extended_copy": "FUN_0081d180",
        },
    }


def describe_camera_data_external_update(
    *,
    destination: str,
    update_source: Any,
) -> dict[str, Any]:
    """Trace FUN_0081e6f0."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "camera-data-external-update",
        "actions": [
            {
                "action": "FUN_00702520",
                "destination": f"{destination}+0x10",
                "source": update_source,
            }
        ],
        "evidence": {
            "function": "FUN_0081e6f0",
            "destination_offset": "+0x10",
        },
    }


def describe_area_base_constructor() -> dict[str, Any]:
    """Trace FUN_0081e710's refcounted base constructor."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "area-base-constructor",
        "actions": [
            {"action": "set refcount vtable", "value": "MWL::Base::BRefCount::vftable"},
            {"action": "write +0x04", "value": 0},
            {"action": "write +0x08", "value": 1},
            {"action": "set temporary vtable", "value": "PTR_FUN_00aaa9a0"},
            {"action": "FUN_00533e70", "target": "+0x0c"},
            {"action": "set final vtable", "value": "PTR_FUN_00b164b0"},
        ],
        "evidence": {
            "function": "FUN_0081e710",
            "base_vtable": "PTR_FUN_00b164b0",
        },
    }


def describe_sphere_constructor() -> dict[str, Any]:
    """Trace FUN_0081e750."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "sphere-constructor",
        "actions": [
            {"action": "FUN_0081e710"},
            {"action": "write vtable", "value": "PTR_FUN_00b16500"},
        ],
        "writes": {
            "+0x10": 0,
            "+0x14": 0,
            "+0x18": 0,
            "+0x1c": 0,
        },
        "evidence": {
            "function": "FUN_0081e750",
            "vtable": "PTR_FUN_00b16500",
        },
    }


def sphere_property_registration() -> dict[str, Any]:
    """Trace FUN_0081e780."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "sphere-property-registration",
        "registration_object": "DAT_00b8e06c",
        "properties": [
            {"name": "Centre", "type_id": 0x10, "offset": 0x10, "flags": 3},
            {"name": "Radius", "type_id": 1, "offset": 0x1c, "flags": 3},
        ],
        "evidence": {
            "function": "FUN_0081e780",
            "registration_helper": "FUN_0063a280",
        },
    }


def sphere_distance_contract(
    *,
    sqrt_result: float,
    radius: float,
) -> dict[str, Any]:
    """Expose FUN_0081e820's exact return arithmetic."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "sphere-distance",
        "result": float(sqrt_result) - float(radius),
        "inputs": {
            "sqrt_result": float(sqrt_result),
            "radius": float(radius),
        },
        "evidence": {
            "function": "FUN_0081e820",
            "radius_offset": "+0x1c",
            "sqrt_helper": "__CIsqrt",
        },
        "limitations": [
            "the source of the sqrt operand is hidden by the decompiler prototype",
        ],
    }


def describe_box_constructor() -> dict[str, Any]:
    """Trace FUN_0081e880's property-bearing base constructor."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "box-property-registration",
        "registration_object": "DAT_00b8e094",
        "properties": [
            {"name": "XForm", "type_id": 0x1D, "offset": 0x10, "flags": 3},
            {"name": "Dimensions", "type_id": 0x10, "offset": 0x50, "flags": 3},
        ],
        "evidence": {
            "function": "FUN_0081e880",
            "registration_helper": "FUN_0063a280",
        },
    }


def describe_box_distance_helper(
    *,
    transform_words: Sequence[Any],
    query: Any,
) -> dict[str, Any]:
    """Trace FUN_0081e920's local transform copy and distance helper."""
    if len(transform_words) != 3:
        raise ValueError("transform_words requires exactly three values")
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "box-distance",
        "actions": [
            {
                "action": "copy +0x40/+0x44/+0x48",
                "values": list(transform_words),
            },
            {
                "action": "FUN_00702520",
                "source": list(transform_words),
                "query": query,
            },
        ],
        "evidence": {
            "function": "FUN_0081e920",
            "source_offsets": ["+0x40", "+0x44", "+0x48"],
        },
        "limitations": [
            "FUN_00702520 result semantics are unresolved",
        ],
    }
