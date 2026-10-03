"""Low-level dynamic array iterator/growth contracts.

Recovered from FUN_00813080 (16-bit elements) and FUN_008166b0 (11-dword
elements). The implementation exposes the exact count/capacity checks,
copy-mode split, release boundary, and returned element address formula.

Optional retail memory summaries add an independent diagnostic/source cross-check
for the pointer passed to the shared release helper. They never change the
recovered growth actions or promote the helper to an operator-delete ABI.
"""

from __future__ import annotations

from typing import Any, Sequence

from camera_memory_release_evidence import build_camera_release_pointer_crosscheck
from memory_pool_runtime import release_helper_action

FORMAT = "SHIFT.CameraDynamicArrayRuntime/1"
MEMORY_CROSSCHECK_FORMAT = "SHIFT.CameraDynamicArrayMemoryCrosscheck/1"


def grow_uint16_array(
    *,
    element_stride: int,
    old_count: int,
    old_capacity: int,
    source_storage: Sequence[int],
    copy_memcpy_mode: bool,
    new_capacity: int,
    retail_static_summary: dict[str, Any] | None = None,
    retail_source_semantic_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Trace the growth branch of FUN_00813080."""
    stride = int(element_stride)
    count = int(old_count)
    capacity = int(old_capacity)
    new_cap = int(new_capacity)
    if count > capacity:
        raise ValueError("old_count cannot exceed old_capacity")
    if new_cap < count:
        raise ValueError("new_capacity cannot hold old_count")
    copied = list(source_storage[:count])
    copy_method = "memcpy_s" if copy_memcpy_mode else "elementwise_uint16"
    result = {
        "format": FORMAT,
        "version": 1,
        "operation": "grow-uint16",
        "old_count": count,
        "old_capacity": capacity,
        "new_capacity": new_cap,
        "copy_method": copy_method,
        "copied_elements": copied,
        "actions": [
            {
                "action": "FUN_0062ff00",
                "argument": 1,
            },
            {
                "action": copy_method,
                "element_stride": stride,
                "count": count,
            },
            {
                "action": "copy allocator bookkeeping",
                "new_count": new_cap,
            },
            release_helper_action(release_old_storage=True),
        ],
        "evidence": {
            "function": "FUN_00813080",
            "element_type": "uint16",
            "copy_flag": "param_1[0xb] bit0",
        },
    }
    memory_crosscheck = build_camera_release_pointer_crosscheck(
        retail_static_summary,
        retail_source_semantic_summary,
        caller="FUN_00813080",
        format_name=MEMORY_CROSSCHECK_FORMAT,
    )
    if memory_crosscheck is not None:
        result["memory_wrapper_evidence"] = memory_crosscheck
    return result


def next_uint16_element_address(
    *,
    element_stride: int,
    current_index: int,
    base_offset: int,
) -> dict[str, Any]:
    """Reproduce FUN_00813080's return formula."""
    stride = int(element_stride)
    index = int(current_index)
    base = int(base_offset)
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "next-uint16-address",
        "index": index,
        "address_offset": stride * index + base,
        "evidence": {"function": "FUN_00813080"},
    }


def grow_dword11_array(
    *,
    element_stride: int,
    old_count: int,
    old_capacity: int,
    source_storage: Sequence[Sequence[Any]],
    copy_memcpy_mode: bool,
    new_capacity: int,
    retail_static_summary: dict[str, Any] | None = None,
    retail_source_semantic_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Trace the growth branch of FUN_008166b0."""
    stride = int(element_stride)
    count = int(old_count)
    capacity = int(old_capacity)
    new_cap = int(new_capacity)
    if len(source_storage) < count:
        raise ValueError("source_storage does not cover old_count")
    if new_cap < count:
        raise ValueError("new_capacity cannot hold old_count")

    copied = []
    for index in range(count):
        row = list(source_storage[index])
        if len(row) != 11:
            raise ValueError("each source element must contain eleven dwords")
        copied.append(row)

    copy_method = "memcpy_s" if copy_memcpy_mode else "elementwise_11_dword"
    result = {
        "format": FORMAT,
        "version": 1,
        "operation": "grow-dword11",
        "old_count": count,
        "old_capacity": capacity,
        "new_capacity": new_cap,
        "copy_method": copy_method,
        "copied_elements": copied,
        "actions": [
            {"action": "FUN_0062ff00", "argument": 1},
            {
                "action": copy_method,
                "element_stride": stride,
                "count": count,
                "dwords_per_element": 11,
            },
            {"action": "copy allocator bookkeeping", "new_count": new_cap},
            release_helper_action(release_old_storage=True),
        ],
        "evidence": {
            "function": "FUN_008166b0",
            "element_type": "11 dwords",
            "copy_flag": "param_1[0xb] bit0",
        },
    }
    memory_crosscheck = build_camera_release_pointer_crosscheck(
        retail_static_summary,
        retail_source_semantic_summary,
        caller="FUN_008166b0",
        format_name=MEMORY_CROSSCHECK_FORMAT,
    )
    if memory_crosscheck is not None:
        result["memory_wrapper_evidence"] = memory_crosscheck
    return result


def next_dword11_element_address(
    *,
    element_stride: int,
    current_index: int,
    base_offset: int,
) -> dict[str, Any]:
    """Reproduce FUN_008166b0's return formula."""
    stride = int(element_stride)
    index = int(current_index)
    base = int(base_offset)
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "next-dword11-address",
        "index": index,
        "address_offset": stride * index + base,
        "evidence": {"function": "FUN_008166b0"},
    }
