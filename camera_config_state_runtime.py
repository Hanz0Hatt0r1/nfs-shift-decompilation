"""Evidence-backed CameraManager camera-config state machine.

Recovered directly from FUN_0080d880, FUN_0080d960, FUN_0080db30, and
FUN_0080dc60.

The configuration readers FUN_00806e70/FUN_00806ea0/FUN_00806e10/FUN_00806e40
remain opaque reflection helpers. This module preserves exact destination
offsets and branch ordering rather than inventing property names or units.
"""

from __future__ import annotations

from typing import Any, Mapping

FORMAT = "SHIFT.CameraConfigStateRuntime/1"

CONFIG_READS = (
    (0x08, "FUN_00806e70"),
    (0x14, "FUN_00806e70"),
    (0x20, "FUN_00806ea0"),
    (0x30, "FUN_00806ea0"),
    (0x60, "FUN_00806e70"),
    (0x6C, "FUN_00806e10"),
    (0x70, "FUN_00806e70"),
    (0x7C, "FUN_00806e70"),
    (0x40, "FUN_00806ea0"),
    (0x50, "FUN_00806ea0"),
    (0x88, "FUN_00806e10"),
    (0x8C, "FUN_00806e10"),
    (0x90, "FUN_00806e10"),
    (0x94, "FUN_00806e10"),
    (0x98, "FUN_00806e10"),
    (0x9C, "FUN_00806e10"),
    (0xA0, "FUN_00806e10"),
    (0xA4, "FUN_00806e10"),
)


def describe_camera_config_defaults() -> dict[str, Any]:
    """Reproduce FUN_0080d880's exact two-profile initialization."""
    profiles: list[dict[str, int]] = []
    first = {
        0x00: 0,
        0x08: 0,
        0x0C: 0,
        0x10: 0,
        0x14: 0,
        0x18: 0,
        0x1C: 0,
        0x20: 0x3F800000,
        0x24: 0,
        0x28: 0,
        0x2C: 0,
        0x60: 0,
        0x6C: 0,
        0x70: 0,
        0x74: 0,
        0x78: 0,
        0x88: 0x3F490FF9,
        0x90: 0x3F000000,
        0x98: 0x447A0000,
        0xA0: 0x3FAAA993,
    }
    second = {
        0x04: 0,
        0x14: 0,
        0x18: 0,
        0x1C: 0,
        0x30: 0,
        0x34: 0,
        0x38: 0,
        0x3C: 0,
        0x7C: 0,
        0x80: 0,
        0x84: 0,
        0x8C: 0x3F490FF9,
        0x94: 0x3F000000,
        0x9C: 0x447A0000,
        0xA4: 0x3FAAA993,
    }
    # The source writes an interleaved structure; merge only the destinations
    # actually touched by each loop iteration.
    profiles.append(first)
    profiles.append(second)
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "defaults",
        "profile_count": 2,
        "profiles": profiles,
        "tail_writes": {
            "+0x60": 0,
            "+0x64": 0,
            "+0x68": 0,
            "+0x6c": 0x3F800000,
            "+0xa8": 1,
            "+0xac": 1,
            "+0xb0": 0,
            "+0xb4": 0,
            "+0xb8": 0,
            "+0xbc": 1,
            "+0xc0": 0,
        },
        "evidence": {
            "function": "FUN_0080d880",
            "loop_iterations": 2,
            "profile_stride_words_in_internal_layout": 3,
        },
        "limitations": [
            "the two interleaved profile views are exposed as touched offsets, not reconstructed high-level records",
        ],
    }


def describe_reflected_camera_config(
    *,
    source_values: Mapping[int, Any],
    boolean_values: Mapping[int, Any] | None = None,
) -> dict[str, Any]:
    """Trace FUN_0080d960's reflection destinations without naming properties."""
    booleans = boolean_values or {}
    reads: list[dict[str, Any]] = []
    for offset, helper in CONFIG_READS:
        reads.append({
            "helper": helper,
            "source_property_ordinal": 0,
            "destination": f"+0x{offset:02x}",
            "value": source_values.get(offset),
        })

    bool_destinations: list[dict[str, Any]] = []
    for offset in (0xA8, 0xAC, 0xB0, 0xB4, 0xB8):
        bool_destinations.append({
            "helper": "FUN_00806e40",
            "destination": f"+0x{offset:02x}",
            "value": source_values.get(offset, booleans.get(offset)),
        })
    bool_destinations.append({
        "helper": "FUN_00806e40",
        "destination": "+0xbc",
        "expression": "source_value != 0",
        "value": bool(source_values.get(0xBC, booleans.get(0xBC, False))),
    })

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "load-reflected-config",
        "reads": reads,
        "flag_reads": bool_destinations,
        "object_links": [
            {"helper": "FUN_00806e40", "destination": "this"},
            {"helper": "FUN_00806e40", "destination": "this + 0x04"},
        ],
        "fallback_condition": {
            "expression": "(+0xa8 == 0) or (+0xac == 0)",
            "fallback": "FUN_0080d880",
        },
        "evidence": {
            "function": "FUN_0080d960",
            "reflection_helpers": [
                "FUN_00806e70",
                "FUN_00806ea0",
                "FUN_00806e10",
                "FUN_00806e40",
            ],
        },
    }


def describe_camera_config_load(
    *,
    config_available: bool,
    config_handle: Any,
    variation_id: int,
) -> dict[str, Any]:
    """Trace FUN_0080db30's config-availability/variation gate."""
    if not config_available or int(variation_id) == 0:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "load",
            "status": "defaults",
            "actions": [
                {"action": "FUN_0080d880", "target": config_handle},
            ],
            "evidence": {
                "function": "FUN_0080db30",
                "availability_gate": "FUN_00806d70(FUN_00807030(),0)",
                "variation_gate": "param_2 != 0 and FUN_00806de0(...,param_2) != 0",
            },
        }

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "load",
        "status": "loaded",
        "actions": [
            {
                "action": "FUN_0080d960",
                "target": config_handle,
                "config_root": "FUN_00807030()",
            },
            *[
                {
                    "action": "FUN_00806e40",
                    "destination": f"+0x{offset:02x}",
                    "kind": "pointer",
                }
                for offset in range(0xD0, 0xF4, 4)
            ],
        ],
        "evidence": {
            "function": "FUN_0080db30",
            "config_root": "FUN_00807030()",
            "availability_check": "FUN_00806d70(root,0)",
            "variation_check": "FUN_00806de0(root,0,param_2)",
            "pointer_mirror_range": ["+0xd0", "+0xf0"],
        },
    }


def describe_camera_slot_reset(
    *,
    slot_base: int | str,
    camera_objects_present: bool,
) -> dict[str, Any]:
    """Reproduce FUN_0080dc60's reset ordering and raw state footprint."""
    base = slot_base
    actions: list[dict[str, Any]] = [
        {"action": "FUN_00403cc0", "target": f"{base}+0x2a80", "size": 0x100},
        {"action": "write", "offset": "+0x2690", "value": 0},
        {"action": "write", "offset": "+0x2a70", "value": 0},
        {"action": "write", "offset": "+0x2568", "value": 0},
        {
            "action": "FUN_00806d20",
            "condition": "FUN_00807020()",
            "arguments": ["FUN_00807030()", 0],
        },
        {"action": "FUN_0081c8f0", "target": f"{base}+0x20"},
        {"action": "FUN_0081c8f0", "target": f"{base}+0xbe0"},
        {"action": "FUN_0081caa0", "target": f"{base}+0x20", "profile_id": -1},
        {"action": "FUN_0081caa0", "target": f"{base}+0xbe0", "profile_id": -1},
    ]

    for source_offset in (0x17A0, 0x1A20, 0x1CA0, 0x2100):
        actions.append({
            "action": "camera-source.vtable +0x90(0)",
            "target": f"{base}+0x{source_offset:04x}",
            "condition": "source pointer is expected non-null",
        })

    raw_writes = {
        "+0x29e0": 0xFFFFFFFF,
        "+0x29e4": 0,
        "+0x29e8": 0xFFFFFFFF,
        "+0x29ec": 0,
        "+0x29f0": 3,
        "+0x29f4": 0,
        "+0x29f8": 0xFFFFFFFF,
        "+0x29fc": 0xFFFFFFFF,
        "+0x2a00": 0xFFFFFFFF,
        "+0x2a04": 0xFFFFFFFF,
        "+0x2a08": 0,
        "+0x2a0c": 0xFFFFFFFF,
        "+0x2a10": 0,
        "+0x2a14": 3,
        "+0x2a18": 0,
        "+0x2a1c": 0xFFFFFFFF,
        "+0x2a20": 0xFFFFFFFF,
        "+0x2a24": 0xFFFFFFFF,
        "+0x2a80": 0,
    }

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "slot-reset",
        "slot_base": base,
        "camera_objects_present": bool(camera_objects_present),
        "actions": actions,
        "raw_writes": raw_writes,
        "evidence": {
            "function": "FUN_0080dc60",
            "scratch_clear": "+0x2a80 size 0x100",
            "camera_state_reset": ["+0x2690", "+0x2a70", "+0x2568"],
            "profile_reset_targets": ["+0x20", "+0xbe0"],
            "camera_source_reset_targets": ["+0x17a0", "+0x1a20", "+0x1ca0", "+0x2100"],
        },
        "limitations": [
            "the four +0x90 source callbacks remain opaque vtable operations",
            "FUN_00806d20/FUN_00807020/FUN_00807030 service semantics remain unresolved",
        ],
    }
