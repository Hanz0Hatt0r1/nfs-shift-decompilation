"""Exact TrackingCamera/collection constructor boundary FUN_008167f0."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.TrackingCameraConstructorRuntime/1"
SPLINE_RECORD_STRIDE = 0x24
SPLINE_NODE_COUNT = 0x80
SPLINE_ALLOCATION_BYTES = 4 + SPLINE_NODE_COUNT * SPLINE_RECORD_STRIDE


def tracking_camera_constructor_layout() -> dict[str, Any]:
    """Expose the raw constructor writes and nested constructor calls."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "constructor-layout",
        "refcount": {
            "vtable_initial": "MWL::Base::BRefCount::vftable",
            "+0x04": 0,
            "+0x08": 1,
            "temporary_vtable": "PTR_FUN_00aaa9a0",
            "base_initializer": "FUN_00533e70(+0x0c)",
            "intermediate_object_vtable": "PTR_FUN_00b15bdc",
            "final_vtable": "PTR_FUN_00b16158",
            "final_aux_vtable": "PTR_LAB_00b16138",
        },
        "nested_initializers": [
            "+0x14",
            "+0x48",
            "+0x7c",
            "+0xb0",
            "+0xe4",
            "+0x118",
            "+0x1b0",
        ],
        "raw_initializers": {
            "+0x244": 0x7FFFFFFF,
            "+0x258": 0,
            "+0x2c0": 0xFFFFFFFF,
            "+0x2c4": 0xFFFFFFFF,
            "+0x2c8": 0,
            "+0x2cc": 0,
            "+0x2d0": 0x3F800000,
            "+0x2d4": 0,
            "+0x2d8": 0,
            "+0x2dc": 0,
            "+0x2e0": 0,
            "+0x2e4": 0,
            "+0x2e8": 0x3F800000,
            "+0x2ec": 0,
            "+0x2f0": 0,
            "+0x2f4": 0,
            "+0x2f8": 0,
            "+0x2fc": 0xFFFFFFFF,
            "+0x300": 0xFFFFFFFF,
            "+0x304": 0,
            "+0x308": 0,
            "+0x30c": 0x3F800000,
            "+0x310": 0,
            "+0x314": 0,
            "+0x318": 0,
            "+0x31c": 0,
            "+0x320": 0,
            "+0x324": 0,
            "+0x328": 0,
            "+0x32c": 0,
            "+0x330": 0,
            "+0x334": 0,
            "+0x338": 0,
            "+0x33c": 0,
            "+0x340": 0,
            "+0x344": 0,
            "+0x348": 0,
            "+0x34c": 0,
            "+0x350": 0,
            "+0x354": 0,
            "+0x358": 0,
            "+0x35c": 0,
            "+0x360": 0,
            "+0x364": 0,
            "+0x368": 0,
            "+0x36c": 0,
            "+0x370": 0,
            "+0x374": 0,
        },
        "byte_initializers": {
            "+0x231": 0,
            "+0x241": 0,
            "+0x265": 0,
            "+0x266": 1,
            "+0x310": 0,
            "+0x368": 0,
            "+0x370": 0,
        },
        "sentinels": {
            "+0x244": 0x7FFFFFFF,
            "+0x2c0": 0xFFFFFFFF,
            "+0x2c4": 0xFFFFFFFF,
            "+0x2fc": 0xFFFFFFFF,
            "+0x300": 0xFFFFFFFF,
            "+0x378": 0xFFFFFFFF,
            "+0x37c": 0xFFFFFFFF,
        },
        "global_camera_block": {
            "destination_offset": "+0x270",
            "dword_count": 16,
            "source": "_DAT_00b88a40.._DAT_00b88a7c",
        },
        "spline_pools": {
            "pool_count": 2,
            "node_count_each": SPLINE_NODE_COUNT,
            "record_stride": SPLINE_RECORD_STRIDE,
            "allocation_bytes_each": SPLINE_ALLOCATION_BYTES,
            "first_array_field": "+0x358",
            "second_array_field": "+0x360",
            "record_constructor": "FUN_00821970",
        },
        "action": {
            "constructor": "FUN_008167f0",
            "input_registry": "FUN_00812c00",
            "shake_first": {
                "initializer": "FUN_00823a80",
                "rate_bits": 0x40C00000,
            },
            "shake_second": {
                "initializer": "FUN_00823a80",
                "rate_bits": 0x41800000,
            },
        },
    }


def initialize_spline_pool(
    *,
    allocation_succeeded: bool,
    record_constructor_succeeded: bool = True,
) -> dict[str, Any]:
    """Trace one of FUN_008167f0's two 0x1204-byte spline pools."""
    if not allocation_succeeded:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "spline-pool-init",
            "status": "allocation-failed",
            "bytes": SPLINE_ALLOCATION_BYTES,
            "record_count": SPLINE_NODE_COUNT,
        }
    if not record_constructor_succeeded:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "spline-pool-init",
            "status": "record-construction-failed",
            "bytes": SPLINE_ALLOCATION_BYTES,
            "record_count": SPLINE_NODE_COUNT,
        }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "spline-pool-init",
        "status": "initialized",
        "bytes": SPLINE_ALLOCATION_BYTES,
        "record_count": SPLINE_NODE_COUNT,
        "record_stride": SPLINE_RECORD_STRIDE,
        "header_bytes": 4,
        "actions": [
            {
                "action": "FUN_008868c0",
                "bytes": SPLINE_ALLOCATION_BYTES,
            },
            {
                "action": "write pool count",
                "value": SPLINE_NODE_COUNT,
            },
            {
                "action": "construct records",
                "constructor": "FUN_00821970",
                "count": SPLINE_NODE_COUNT,
                "stride": SPLINE_RECORD_STRIDE,
            },
        ],
        "evidence": {
            "function": "FUN_008167f0",
            "allocation_formula": "4 + 0x80 * 0x24",
        },
    }


def describe_tracking_camera_constructor_complete(
    *,
    first_pool_allocated: bool = True,
    second_pool_allocated: bool = True,
    first_pool_records_ok: bool = True,
    second_pool_records_ok: bool = True,
) -> dict[str, Any]:
    """Compose the exact outer constructor order and pool results."""
    first_pool = initialize_spline_pool(
        allocation_succeeded=first_pool_allocated,
        record_constructor_succeeded=first_pool_records_ok,
    )
    second_pool = initialize_spline_pool(
        allocation_succeeded=second_pool_allocated,
        record_constructor_succeeded=second_pool_records_ok,
    )
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "tracking-camera-constructor",
        "status": (
            "loaded"
            if second_pool["status"] == "initialized"
            else "partial"
        ),
        "layout": tracking_camera_constructor_layout(),
        "pools": {
            "first": first_pool,
            "second": second_pool,
        },
        "actions": [
            {"action": "FUN_00812c00"},
            {"action": "FUN_00823a80", "target": "+0x84", "rate_bits": 0x40C00000},
            {"action": "FUN_00823ab0", "target": "+0x84"},
            {"action": "FUN_00823a80", "target": "+0xd8", "rate_bits": 0x41800000},
            {"action": "FUN_00823ab0", "target": "+0xd8"},
            {"action": "initialize first spline pool", "result": first_pool},
            {"action": "initialize second spline pool", "result": second_pool},
        ],
        "evidence": {
            "function": "FUN_008167f0",
            "spline_record_constructor": "FUN_00821970",
            "input_factory": "FUN_00812c00",
        },
    }


def describe_tracking_constructor_copy(
    source: Mapping[int, Any],
) -> dict[str, Any]:
    """Trace the constructor-visible global camera block copy."""
    offsets = [0x270 + i * 4 for i in range(16)]
    missing = [offset for offset in offsets if offset not in source]
    if missing:
        raise ValueError(f"missing source globals: {missing}")
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "global-camera-block-copy",
        "destination_range": ["+0x270", "+0x2ac"],
        "values": {f"+0x{offset:02x}": source[offset] for offset in offsets},
        "evidence": {
            "function": "FUN_008167f0",
            "source": "_DAT_00b88a40.._DAT_00b88a7c",
            "dword_count": 16,
        },
    }
