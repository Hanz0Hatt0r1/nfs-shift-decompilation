"""Bulk spline collection synchronization from FUN_008176f0.

This module isolates the proven record-copy/rebase mechanics. The executable
copies only five fields from each 0x24-byte spline record and maintains two
destination arrays with independent cursors. A camera collection entry keeps
the original spline allocation pointer/count/length while its referenced
spline is rebound to the assembled destination window and FUN_008226a0
recomputes length. The complex scalar-window normalization remains an explicit
callback boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.SplineBulkSyncRuntime/1"
RECORD_STRIDE = 0x24
COPIED_OFFSETS = (0x10, 0x14, 0x18, 0x1C, 0x20)


@dataclass(frozen=True)
class SplineRecordPayload:
    values: Mapping[int, Any]

    def copy_payload(self) -> dict[int, Any]:
        missing = [offset for offset in COPIED_OFFSETS if offset not in self.values]
        if missing:
            raise ValueError(f"missing spline record fields: {missing}")
        return {offset: self.values[offset] for offset in COPIED_OFFSETS}


@dataclass(frozen=True)
class ReferencedSpline:
    spline_id: int
    records: Sequence[SplineRecordPayload]
    length: Any
    allocation_pointer: Any


@dataclass
class BulkSyncState:
    first_cursor: int = 0   # +0x35c
    second_cursor: int = 0  # +0x364
    first_base: Any = None  # +0x358
    second_base: Any = None # +0x360


def copy_spline_records(
    records: Sequence[SplineRecordPayload],
    *,
    destination_base: int,
    cursor: int,
) -> tuple[list[dict[str, Any]], int]:
    """Copy the five source fields with the source 0x24 record stride."""
    outputs: list[dict[str, Any]] = []
    current = int(cursor)
    for source_index, record in enumerate(records):
        payload = record.copy_payload()
        outputs.append({
            "source_index": source_index,
            "destination_index": current,
            "destination_address": int(destination_base) + current * RECORD_STRIDE,
            "fields": payload,
        })
        current += 1
    return outputs, current


def append_referenced_spline(
    state: BulkSyncState,
    *,
    referenced: ReferencedSpline,
    destination: str,
) -> tuple[BulkSyncState, dict[str, Any]]:
    """Append one referenced spline into first or second assembled collection."""
    is_first = str(destination) == "first"
    base = state.first_base if is_first else state.second_base
    cursor = state.first_cursor if is_first else state.second_cursor
    if base is None:
        raise ValueError("destination base pointer is required")

    copied, new_cursor = copy_spline_records(
        referenced.records,
        destination_base=int(base),
        cursor=cursor,
    )
    updated = BulkSyncState(
        first_cursor=new_cursor if is_first else state.first_cursor,
        second_cursor=state.second_cursor if is_first else new_cursor,
        first_base=state.first_base,
        second_base=state.second_base,
    )
    return updated, {
        "format": FORMAT,
        "version": 1,
        "operation": "append-referenced-spline",
        "destination": str(destination),
        "spline_id": int(referenced.spline_id),
        "record_count": len(referenced.records),
        "copied": copied,
        "cursor_before": cursor,
        "cursor_after": new_cursor,
        "evidence": {
            "function": "FUN_008176f0",
            "record_stride": RECORD_STRIDE,
            "copied_fields": [f"+0x{o:02x}" for o in COPIED_OFFSETS],
        },
    }


def rebase_referenced_spline(
    *,
    destination_base: int,
    destination_cursor: int,
    referenced: ReferencedSpline,
    saved_pointer: Any = None,
    saved_count: Any = None,
    saved_length: Any = None,
) -> dict[str, Any]:
    """Trace the saved-pointer/count/length writes before FUN_008226a0."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "rebase-referenced-spline",
        "spline_id": int(referenced.spline_id),
        "writes_to_collection_entry": {
            "saved_pointer": saved_pointer if saved_pointer is not None else referenced.allocation_pointer,
            "saved_count": saved_count if saved_count is not None else len(referenced.records),
            "saved_length": saved_length if saved_length is not None else referenced.length,
        },
        "writes_to_spline": {
            "+0x14": int(destination_base) + int(destination_cursor) * RECORD_STRIDE,
            "+0x10": int(destination_cursor) - len(referenced.records),
            "+0x18": referenced.length,
        },
        "actions": [
            {
                "action": "FUN_008226a0",
                "spline_id": int(referenced.spline_id),
            }
        ],
        "evidence": {
            "function": "FUN_008176f0",
            "destination_base_field": "+0x358",
            "destination_cursor_field": "+0x35c",
            "saved_pointer": "collection entry +4/+7",
            "saved_count": "collection entry +5/+8",
            "saved_length": "collection entry +6/+9",
        },
    }



def normalize_spline_scalar_window(
    values: Sequence[float],
) -> dict[str, Any]:
    """Reproduce the scalar extrema/boundary search in FUN_008176f0.

    The source computes the global maximum across +0x1c of every record,
    then finds the first descending edge from the left and the first descending
    edge from the right. When the inclusive span exceeds three records, the
    whole span's +0x1c values are overwritten with that global maximum.
    """
    vals = [float(v) for v in values]
    n = len(vals)
    if n == 0:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "scalar-window-normalize",
            "status": "empty",
            "global_max": -1.0,
            "left": -1,
            "right": -1,
            "written_indices": [],
            "values_after": [],
            "evidence": {"function": "FUN_008176f0"},
        }

    global_max = max(vals)

    left = -1
    for i in range(n):
        if vals[i] < -1.0:
            left = i
            break
        if i > 0 and vals[i] < vals[i - 1]:
            left = i
            break

    right = -1
    for i in range(n - 1, -1, -1):
        if vals[i] < -1.0:
            right = i
            break
        if i < n - 1 and vals[i] < vals[i + 1]:
            right = i
            break

    after = list(vals)
    written: list[int] = []
    if left != -1 and right != -1 and (right - left + 1) > 3:
        for i in range(left, right + 1):
            after[i] = global_max
            written.append(i)
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "scalar-window-normalize",
        "status": "updated" if written else "unchanged",
        "global_max": global_max,
        "left": left,
        "right": right,
        "written_indices": written,
        "values_after": after,
        "evidence": {
            "function": "FUN_008176f0",
            "source_offset": "+0x1c",
            "global_extrema": "max",
            "minimum_span": 4,
        },
    }

def describe_bulk_sync(
    *,
    first_splines: Sequence[ReferencedSpline],
    second_splines: Sequence[ReferencedSpline],
    first_base: int,
    second_base: int,
    active_entry_flags: Sequence[bool],
    scalar_window_result: Any = None,
) -> dict[str, Any]:
    """Trace the deterministic part of FUN_008176f0 for two spline channels."""
    if len(active_entry_flags) == 0:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "bulk-sync",
            "status": "empty-collection",
            "first_cursor": 0,
            "second_cursor": 0,
        }

    state = BulkSyncState(
        first_cursor=0,
        second_cursor=0,
        first_base=int(first_base),
        second_base=int(second_base),
    )
    actions: list[dict[str, Any]] = []
    first_results = []
    second_results = []

    for active in active_entry_flags:
        if not active:
            continue
        for spline in first_splines:
            state, trace = append_referenced_spline(
                state,
                referenced=spline,
                destination="first",
            )
            first_results.append(trace)
        for spline in second_splines:
            state, trace = append_referenced_spline(
                state,
                referenced=spline,
                destination="second",
            )
            second_results.append(trace)

    actions.append({
        "action": "FUN_008226a0",
        "spline_channel": "first",
        "count": len(first_splines),
    })
    actions.append({
        "action": "FUN_008226a0",
        "spline_channel": "second",
        "count": len(second_splines),
    })

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "bulk-sync",
        "status": "updated",
        "first_cursor": state.first_cursor,
        "second_cursor": state.second_cursor,
        "first_results": first_results,
        "second_results": second_results,
        "actions": actions,
        "scalar_window_result": scalar_window_result,
        "evidence": {
            "function": "FUN_008176f0",
            "neighbor_selector": "FUN_00816c00",
            "first_base": "+0x358",
            "first_cursor": "+0x35c",
            "second_base": "+0x360",
            "second_cursor": "+0x364",
            "record_stride": RECORD_STRIDE,
            "activation_flag": "entry.byte +0x0d",
        },
        "limitations": [
            "the executable's long scalar-window extrema/flattening pass is preserved as scalar_window_result",
            "candidate enumeration through FUN_00546290/FUN_0054ed00 is external to this boundary",
        ],
    }
