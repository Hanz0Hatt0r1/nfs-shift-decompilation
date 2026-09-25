"""Evidence-backed camera slot/service synchronization from SHIFT.exe.

FUN_0080e420 synchronizes one camera-slot state object. When the slot root is
non-null it calls FUN_0080db30(this, this+8, param_1), then iterates three
view records and invokes fixed vtable methods with fields at +0x90..+0xa8.
It also synchronizes several fields with the global camera service at +0x574.

No meaning is assigned to the vtable methods beyond their observed offsets.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

FORMAT = "SHIFT.CameraSlotSyncRuntime/1"
RECORD_COUNT = 3
RECORD_START = 0x98
RECORD_STRIDE = 0x04


@dataclass(frozen=True)
class CameraViewSyncRecord:
    source: Any
    field_0x90: Any = None
    field_0x98: Any = None
    field_0xa0: Any = None
    field_0xa8: Any = None


@dataclass(frozen=True)
class CameraServiceSyncState:
    service_present: bool = True
    key_0xd0: Any = None
    value_0xd4: bool = False
    key_0xd8: Any = None
    value_0xdc: bool = False
    value_0xe0: Any = None
    value_0xe4: Any = None
    value_0xe8: Any = None
    shadow_0xf4: Any = None
    shadow_0xf8: Any = None
    shadow_0xfc: Any = None
    value_0xec: Any = None
    value_0xf0: Any = None
    shadow_0x100: Any = None
    shadow_0x104: Any = None
    service_enabled_query: bool | None = None
    service_focus_query: bool | None = None


def describe_camera_slot_sync(
    *,
    slot_root_present: bool,
    trigger_value: Any,
    view_records: Sequence[CameraViewSyncRecord],
    service: CameraServiceSyncState,
) -> dict[str, Any]:
    """Trace FUN_0080e420 in source order."""
    if len(view_records) != RECORD_COUNT:
        raise ValueError(f"FUN_0080e420 iterates exactly {RECORD_COUNT} view records")

    actions: list[dict[str, Any]] = []
    if slot_root_present:
        actions.append({
            "action": "FUN_0080db30",
            "arguments": {
                "this": "this",
                "state": "this + 0x08",
                "trigger": trigger_value,
            },
        })
        for index, record in enumerate(view_records):
            base = RECORD_START + index * RECORD_STRIDE
            actions.extend([
                {"action": f"record[{index}] vtable +0x24()",
                 "source_field": f"+0x{index * 4:02x}"},
                {"action": f"record[{index}] vtable +0x6c()",
                 "source_field": f"+0x{index * 4:02x}"},
                {"action": f"record[{index}] vtable +0x70(field +0x{base - 0x08:02x})",
                 "argument": record.field_0x90},
                {"action": f"record[{index}] vtable +0x78(field +0x{base:02x})",
                 "argument": record.field_0x98},
                {"action": f"record[{index}] vtable +0x7c(field +0x{base + 8:02x})",
                 "argument": record.field_0xa0},
                {"action": f"record[{index}] vtable +0x74(field +0x{base + 16:02x})",
                 "argument": record.field_0xa8},
                {"action": f"record[{index}] vtable +0xa4(field +0x74)",
                 "argument": "this + 0x74"},
            ])

    service_actions: list[dict[str, Any]] = []
    if service.service_present:
        if (
            service.service_enabled_query is None
            or bool(service.service_enabled_query) != bool(service.value_0xd4)
        ):
            service_actions.append({
                "condition": "global service vtable +0x3c(+0xd0) disagrees with (+0xd4 != 0)",
                "query": "service vtable +0x3c(+0xd0)",
                "action_if_mismatch": "service vtable +0x34(+0xd0, +0xd4 != 0)",
            })
        if (
            service.service_focus_query is None
            or bool(service.service_focus_query) != bool(service.value_0xdc)
        ):
            service_actions.append({
                "condition": "global service vtable +0x40(+0xd8) disagrees with (+0xdc != 0)",
                "query": "service vtable +0x40(+0xd8)",
                "action_if_mismatch": "service vtable +0x38(+0xd8, +0xdc != 0)",
            })

        triple = (
            service.value_0xe0,
            service.value_0xe4,
            service.value_0xe8,
        )
        shadow_triple = (
            service.shadow_0xf4,
            service.shadow_0xf8,
            service.shadow_0xfc,
        )
        if triple == shadow_triple:
            service_actions.append({
                "condition": "+0xe0/+0xe4/+0xe8 equals +0xf4/+0xf8/+0xfc",
                "action": "service vtable +0x48()",
            })
        else:
            service_actions.extend([
                {
                    "condition": "+0xe0/+0xe4/+0xe8 differs from +0xf4/+0xf8/+0xfc",
                    "action": "service vtable +0x44(this + 0xe0)",
                },
                {
                    "action": "+0xf4/+0xf8/+0xfc = +0xe0/+0xe4/+0xe8",
                    "values": list(triple),
                },
            ])

        pair = (service.value_0xec, service.value_0xf0)
        shadow_pair = (service.shadow_0x100, service.shadow_0x104)
        if pair != shadow_pair:
            service_actions.extend([
                {
                    "condition": "+0xec/+0xf0 differs from +0x100/+0x104",
                    "action": "service vtable +0x4c(+0xec, +0xf0)",
                    "values": list(pair),
                },
                {
                    "action": "+0x100/+0x104 = +0xec/+0xf0",
                    "values": list(pair),
                },
            ])

    return {
        "format": FORMAT,
        "version": 1,
        "record_count": RECORD_COUNT,
        "record_start": RECORD_START,
        "record_stride": RECORD_STRIDE,
        "slot_root_present": bool(slot_root_present),
        "slot_actions": actions,
        "service_actions": service_actions,
        "evidence": {
            "sync_function": "FUN_0080e420",
            "nested_state_sync": "FUN_0080db30(this, this+8, param_1)",
            "view_record_root": "this + 0x98",
            "view_record_pointer_fields": "this + 0x00/+0x04/+0x08",
            "global_service": "FUN_0080bfb0() + 0x574",
            "enabled_key": "+0xd0",
            "enabled_flag": "+0xd4",
            "focus_key": "+0xd8",
            "focus_flag": "+0xdc",
            "triple": "+0xe0/+0xe4/+0xe8",
            "triple_shadow": "+0xf4/+0xf8/+0xfc",
            "pair": "+0xec/+0xf0",
            "pair_shadow": "+0x100/+0x104",
        },
        "limitations": [
            "vtable method meanings are unresolved",
            "FUN_0080db30 internals are unresolved",
            "the global service object is retained as an opaque interface",
        ],
    }
