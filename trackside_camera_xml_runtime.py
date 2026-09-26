"""Exact Trackside Cams XML serializer boundary from FUN_00812260.

The handler:
- counts existing entries in +0x48 whose type discriminator +0xec is not 1;
- creates the shared 0x50-byte funcpropdata object;
- serializes only entries whose +0xec matches DAT_00c259f0;
- when DAT_00c259f0 == 1 and an entry is TrackingCamera (RTTI DAT_00c25fb8),
  temporarily subtracts the non-type1 count from SplineID +0xf8 before the
  vtable+4 serializer and restores it afterwards;
- when DAT_00c259f0 != 1, invalidates SplineID to -1 when it is below the
  rebasing cutoff, then serializes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.TracksideCameraXmlRuntime/1"
TYPE_OFFSET = 0xEC
SPLINE_ID_OFFSET = 0xF8
TARGET_SPLINE_ID_OFFSET = 0xFC
TRACKING_RTTI = "DAT_00c25fb8"


@dataclass(frozen=True)
class TracksideEntry:
    type_discriminator: int
    is_tracking_camera: bool
    spline_id: int = -1
    target_spline_id: int = -1
    name: str | None = None


def count_non_type1(entries: Sequence[TracksideEntry]) -> int:
    """Reproduce the first +0x48 scan in FUN_00812260."""
    return sum(1 for entry in entries if int(entry.type_discriminator) != 1)


def serialize_trackside_entries(
    *,
    entries: Sequence[TracksideEntry],
    global_type: int,
    serializer_success: Mapping[int, bool] | None = None,
    shared_type_object: Any = None,
) -> dict[str, Any]:
    """Reproduce FUN_00812260 source ordering and temporary SplineID mutation."""
    count = count_non_type1(entries)
    results: list[dict[str, Any]] = []
    success = serializer_success or {}
    for index, entry in enumerate(entries):
        if int(entry.type_discriminator) != int(global_type):
            continue

        mutated_spline = int(entry.spline_id)
        temporary_spline: int | None = None
        invalidated = False
        restored_spline: int | None = None

        if int(global_type) == 1:
            if entry.is_tracking_camera:
                temporary_spline = int(entry.spline_id) - count
                mutated_spline = temporary_spline
        else:
            if entry.is_tracking_camera and count <= int(entry.spline_id):
                mutated_spline = -1
                invalidated = True

        serialized = bool(success.get(index, True))
        row = {
            "index": index,
            "type_discriminator": int(entry.type_discriminator),
            "is_tracking_camera": bool(entry.is_tracking_camera),
            "original_spline_id": int(entry.spline_id),
            "serialized_spline_id": mutated_spline,
            "target_spline_id": int(entry.target_spline_id),
            "temporary_subtraction": temporary_spline,
            "invalidated": invalidated,
            "restored_spline_id": int(entry.spline_id) if temporary_spline is not None else None,
            "serializer_called": serialized,
            "actions": [
                {
                    "action": "entry.vtable +0x04",
                    "result": f"class-data[{index}]",
                },
                {
                    "action": "FUN_00640dd0",
                    "arguments": {
                        "entry": index,
                        "funcpropdata": shared_type_object,
                    },
                },
            ],
        }
        if temporary_spline is not None:
            row["actions"].insert(
                1,
                {
                    "action": "temporary write +0xf8",
                    "value": temporary_spline,
                    "restore_after": int(entry.spline_id),
                },
            )
            row["actions"].append(
                {
                    "action": "restore +0xf8",
                    "value": int(entry.spline_id),
                }
            )
        results.append(row)

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "trackside-xml-save",
        "status": "ok",
        "global_type": int(global_type),
        "non_type1_count": count,
        "record_type_offset": TYPE_OFFSET,
        "spline_id_offset": SPLINE_ID_OFFSET,
        "target_spline_id_offset": TARGET_SPLINE_ID_OFFSET,
        "tracking_rtti": TRACKING_RTTI,
        "funcpropdata": {
            "bytes": 0x50,
            "object": shared_type_object,
        },
        "serialized": results,
        "evidence": {
            "function": "FUN_00812260",
            "list_field": "+0x48",
            "xml_elements": "param_2 +0x84.elements",
            "record_serializer": "vtable +0x04",
            "xml_writer": "FUN_00640dd0",
        },
        "limitations": [
            "FUN_00640dd0/XML object conversion remains opaque",
            "the temporary SplineID rebasing is the only TrackingCamera field mutated here",
        ],
    }


def describe_trackside_xml_setup(
    *,
    existing_entries: Sequence[TracksideEntry],
    root_available: bool,
) -> dict[str, Any]:
    """Expose FUN_00812260 setup before the per-entry serializer loop."""
    count = count_non_type1(existing_entries)
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "trackside-xml-setup",
        "root_available": bool(root_available),
        "non_type1_count": count,
        "actions": [
            {
                "action": "scan +0x14",
                "purpose": "obtain iterator backing state",
            },
            {
                "action": "scan +0x48",
                "count_condition": "+0xec != 1",
                "count": count,
            },
            {
                "action": "FUN_0063e9b0",
                "path": "param_2+0x84.elements",
            },
            {
                "action": "FUN_008868c0",
                "bytes": 0x50,
            },
            {
                "action": "FUN_0063e650",
                "condition": "allocation succeeded",
            },
            {
                "action": "FUN_0063c0d0",
                "purpose": "attach funcpropdata",
            },
        ],
        "evidence": {"function": "FUN_00812260"},
    }
