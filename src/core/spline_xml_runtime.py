"""Evidence-backed XML callbacks for the spline runtime.

Recovered directly from FUN_00821e80, FUN_00822770 and FUN_008228d0.
The generic XML/property helpers remain opaque; this module captures their
exact ordering, offsets, callback registration and per-record stride.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

FORMAT = "SHIFT.SplineXmlRuntime/1"
RECORD_STRIDE = 0x24


def describe_spline_xml_property_registration() -> dict[str, Any]:
    """Reproduce FUN_008228d0's three property registrations."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "property-registration",
        "registration_object": "DAT_00b8e138",
        "properties": [
            {"name": "NumNodes", "type_id": 3, "offset": 0x10, "flags": 2},
            {"name": "Length", "type_id": 1, "offset": 0x18, "flags": 2},
            {"name": "nodes", "type_id": 6, "offset": 0x14, "flags": 2},
        ],
        "factory_lookup": {
            "helper": "FUN_00408320",
            "type_id": "0xbfa72c",
        },
        "callbacks": {
            "load": "FUN_00821e80",
            "save": "FUN_00822770",
        },
        "evidence": {
            "function": "FUN_008228d0",
            "registration_helper": "FUN_0063a280",
            "container_registration": "FUN_006420b0",
        },
    }


def describe_spline_xml_load(
    *,
    node_count: int,
    existing_record_count: int,
    root_present: bool,
    element_key: str = "elements",
) -> dict[str, Any]:
    """Trace FUN_00821e80's load callback setup."""
    count = int(node_count)
    existing = int(existing_record_count)
    actions: list[dict[str, Any]] = [
        {
            "action": "FUN_0063e9b0",
            "source": f"param_2 + 0x84.{element_key}",
        },
        {
            "action": "allocate funcpropdata",
            "bytes": 0x50,
            "helper": "FUN_008868c0",
            "constructor": "FUN_0063e650",
            "fallback": "null",
        },
        {
            "action": "FUN_0063c0d0",
            "destination": "funcpropdata",
        },
    ]
    if not root_present:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "spline-xml-load",
            "status": "root-unavailable",
            "node_count": count,
            "existing_record_count": existing,
            "actions": actions,
            "evidence": {"function": "FUN_00821e80"},
        }

    if existing:
        actions.append({
            "action": "iterate existing records",
            "count": existing,
            "stride": RECORD_STRIDE,
            "record_offset": "+0x24 * index",
            "deserialize_vtable_slot": "+0x04",
        })
    actions.append({
        "action": "FUN_00631740",
        "result": "return-object string reset",
    })
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "spline-xml-load",
        "status": "prepared",
        "node_count": count,
        "existing_record_count": existing,
        "actions": actions,
        "evidence": {
            "function": "FUN_00821e80",
            "funcpropdata_bytes": 0x50,
            "record_stride": RECORD_STRIDE,
            "record_deserializer": "record.vtable +0x04",
        },
        "limitations": [
            "the generic FUN_0063c0d0/FUN_00640dd0 property transfer is intentionally opaque",
        ],
    }


def describe_spline_xml_save(
    *,
    node_count: int,
    records: Sequence[Mapping[str, Any]],
    class_names: Sequence[str],
    secondary_attributes: Sequence[str],
    all_class_conversions_succeed: bool = True,
    all_record_application_succeeds: bool = True,
) -> dict[str, Any]:
    """Trace FUN_00822770's per-record save callback."""
    count = int(node_count)
    if count < 0:
        raise ValueError("node_count must be non-negative")
    if len(records) < count:
        raise ValueError("records must contain at least node_count entries")
    if len(class_names) < count or len(secondary_attributes) < count:
        raise ValueError("class_names and secondary_attributes must cover node_count")

    actions: list[dict[str, Any]] = [
        {
            "action": "FUN_0063d390",
            "source": "param_4 + 0x8c.elements",
            "result_count": count,
        },
        {
            "action": "FUN_0063c6d0",
            "path": ["DAT_00aaad1c", "DAT_00aaadbc"],
        },
        {
            "action": "FUN_00821f30",
            "node_count": count,
        },
    ]
    status = "ok"
    for index in range(count):
        class_name = str(class_names[index])
        secondary = str(secondary_attributes[index])
        actions.append({
            "action": "read record attributes",
            "index": index,
            "record_offset": index * RECORD_STRIDE,
            "class": class_name,
            "secondary": secondary,
        })
        if not all_class_conversions_succeed:
            actions.append({
                "action": "abort",
                "index": index,
                "reason": "FUN_0063fd20 or class-object conversion failed",
            })
            status = "failed"
            break
        actions.extend([
            {
                "action": "FUN_00630fe0",
                "index": index,
                "secondary": secondary,
            },
            {
                "action": "FUN_00640c60",
                "index": index,
            },
            {
                "action": "FUN_0063eaf0",
                "index": index,
            },
        ])
        if not all_record_application_succeeds:
            actions.append({
                "action": "abort",
                "index": index,
                "reason": "FUN_006408f0 returned zero",
            })
            status = "failed"
            break
        actions.append({
            "action": "FUN_006408f0",
            "index": index,
            "record_offset": index * RECORD_STRIDE,
            "class_name": class_name,
        })
    if status == "ok":
        actions.append({
            "action": "fallback-length-rebuild",
            "condition": "Length +0x18 == 0",
            "helper": "FUN_008226a0",
        })
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "spline-xml-save",
        "status": status,
        "node_count": count,
        "actions": actions,
        "evidence": {
            "function": "FUN_00822770",
            "record_stride": RECORD_STRIDE,
            "class_attribute": "class",
            "secondary_attribute": "DAT_00aaadb0",
        },
        "limitations": [
            "the concrete class-id conversion and FUN_006408f0 application are opaque",
        ],
    }


def describe_spline_runtime_size(
    *,
    node_count: int,
) -> dict[str, Any]:
    """Expose the exact allocation formula used by FUN_00821f30 for ordinary sizes."""
    count = int(node_count)
    if count < 0:
        raise ValueError("node_count must be non-negative")
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "runtime-size",
        "node_count": count,
        "record_stride": RECORD_STRIDE,
        "allocation_formula": "4 + node_count * 0x24",
        "bytes": 4 + count * RECORD_STRIDE,
        "evidence": {"function": "FUN_00821f30"},
    }
