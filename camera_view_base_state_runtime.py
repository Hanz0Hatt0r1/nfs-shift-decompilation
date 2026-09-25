"""Evidence-backed CCameraView base-state lifecycle.

Recovered from FUN_0081ac30, FUN_0081ac60, FUN_0081ac70, FUN_0081ae50,
FUN_0081aeb0 and FUN_0081af70.

The module exposes the exact base-view storage reset/copy/registration contract.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.CameraViewBaseStateRuntime/1"
BASE_COPY_DWORD_COUNT = 13


def reset_camera_view_base_state() -> dict[str, Any]:
    """Reproduce FUN_0081ac60's reset boundary."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "reset",
        "actions": [
            {
                "action": "write vtable",
                "value": "PTR_FUN_00b161f0",
            },
            {
                "action": "FUN_006383f0",
                "target": "base CCameraView state",
            },
        ],
        "evidence": {
            "function": "FUN_0081ac60",
            "vtable": "PTR_FUN_00b161f0",
            "base_reset_helper": "FUN_006383f0",
        },
    }


def describe_refcounted_base_constructor() -> dict[str, Any]:
    """Reproduce the initialization sequence in FUN_0081aeb0."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "constructor",
        "actions": [
            {"action": "set refcount vtable", "value": "MWL::Base::BRefCount::vftable"},
            {"action": "write +0x04", "value": 0},
            {"action": "write +0x08", "value": 1},
            {"action": "set temporary vtable", "value": "PTR_FUN_00aaa9a0"},
            {"action": "FUN_00533e70", "target": "+0x0c"},
            {"action": "set final vtable", "value": "PTR_FUN_00b16248"},
        ],
        "writes": {
            "+0x10": 0,
            "+0x14": 0,
            "+0x18": 0,
            "+0x1c": 0,
            "+0x20": 0,
            "+0x24": 0,
            "+0x28": 0,
            "+0x2c": 0,
            "+0x30": 0,
            "+0x34": 0,
            "+0x40": 0,
            "+0x44": 0x3F490FDB,
            "+0x48": 0x3FAAAAAB,
            "+0x4c": 0x3DCCCCCD,
            "+0x50": 0x443B8000,
        },
        "evidence": {
            "function": "FUN_0081aeb0",
            "projection_defaults": "FOV/AspectRatio/NearZ/FarZ at +0x44..+0x50",
        },
    }


def copy_camera_view_base_state(
    source_words: Mapping[int, Any],
) -> dict[str, Any]:
    """Reproduce FUN_0081ae50's thirteen-dword sequential copy."""
    offsets = [index * 4 for index in range(BASE_COPY_DWORD_COUNT)]
    missing = [offset for offset in offsets if offset not in source_words]
    if missing:
        raise ValueError(f"missing source base-state dwords at offsets: {missing}")

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "copy",
        "copy_count": BASE_COPY_DWORD_COUNT,
        "offsets": [f"+0x{offset:02x}" for offset in offsets],
        "values": {f"+0x{offset:02x}": source_words[offset] for offset in offsets},
        "evidence": {
            "function": "FUN_0081ae50",
            "range": ["+0x00", "+0x30"],
        },
    }


def copy_embedded_camera_state(
    *,
    source_base: int | str,
) -> dict[str, Any]:
    """Trace FUN_0081af70's embedded +0x10 state copy."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "embedded-copy",
        "action": "FUN_0081ae50",
        "destination": "this + 0x10",
        "source": f"{source_base}+0x10",
        "evidence": {
            "function": "FUN_0081af70",
            "nested_copy": "FUN_0081ae50",
        },
    }


def camera_view_base_property_registration() -> dict[str, Any]:
    """Reproduce FUN_0081ac70 property registrations."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "property-registration",
        "registration_object": "DAT_00b8dfac",
        "properties": [
            {"name": "Position", "type_id": 0x10, "offset": 0x10, "flags": 3},
            {"name": "Orientation", "type_id": 0x10, "offset": 0x1c, "flags": 3},
            {"name": "Velocity", "type_id": 0x10, "offset": 0x28, "flags": 3},
            {"name": "FOV", "property_symbol": "DAT_00b15fa0", "type_id": 10, "offset": 0x34, "flags": 3},
            {"name": "AspectRatio", "type_id": 10, "offset": 0x38, "flags": 3},
            {"name": "NearZ", "type_id": 10, "offset": 0x3c, "flags": 3},
            {"name": "FarZ", "property_symbol": "DAT_00b15f90", "type_id": 10, "offset": 0x40, "flags": 3},
        ],
        "evidence": {
            "function": "FUN_0081ac70",
            "registration_helper": "FUN_0063a280",
        },
    }
