"""Exact CameraConfigManager property and default-data XML registration.

Recovered from FUN_00810710, FUN_0080f9d0, FUN_0080fa40, FUN_0080fb40
and FUN_0080fbb0.
"""

from __future__ import annotations

from typing import Any, Mapping

FORMAT = "SHIFT.CameraConfigRegistrationRuntime/1"


def camera_config_manager_registration() -> dict[str, Any]:
    """Reproduce FUN_00810710's reflected property surface."""
    properties = [
        ("FreeLookYawLimits", 0x0F, 0x2B8),
        ("FreeLookPitchLimits", 0x0F, 0x2C0),
        ("RotateChaseCamPitchLimits", 0x0F, 0x2C8),
        ("Camera configs", 6, 0x10),
        ("DefaultStaticCamData", 6, 0x78),
        ("DefaultTrackingCamData", 6, 0x168),
    ]
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "camera-config-registration",
        "registration_object": "DAT_00b8de24",
        "properties": [
            {"name": name, "type_id": type_id, "offset": offset, "flags": 2}
            for name, type_id, offset in properties
        ],
        "callbacks": {
            "Camera configs": {
                "save": "FUN_00810530",
                "load": "FUN_00810180",
            },
            "DefaultStaticCamData": {
                "save": "FUN_0080f9d0",
                "load": "FUN_0080fa40",
            },
            "DefaultTrackingCamData": {
                "save": "FUN_0080fb40",
                "load": "FUN_0080fbb0",
            },
        },
        "container_factory": "FUN_00408320(type=0xbfa72c)",
        "element_registration": "FUN_006420b0",
        "evidence": {"function": "FUN_00810710"},
    }


def describe_default_camera_data_save(
    *,
    data_offset: int,
    vtable_name: str,
    class_name: str = "funcpropdata",
) -> dict[str, Any]:
    """Trace FUN_0080f9d0 / FUN_0080fb40 shared save contract."""
    if int(data_offset) not in (0x78, 0x168):
        raise ValueError("default camera data offset must be 0x78 or 0x168")
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "default-camera-save",
        "data_offset": int(data_offset),
        "actions": [
            {"action": "allocate", "bytes": 0x50, "constructor": "FUN_0063e650"},
            {"action": "FUN_0063c0d0", "target": "param_2 +0x84"},
            {
                "action": f"camera-data.vtable +0x04 ({vtable_name})",
                "target_offset": int(data_offset),
                "class_name": class_name,
            },
            {"action": "FUN_00640dd0", "target": f"param_2.{data_offset:#x}"},
            {"action": "FUN_00631740", "value": ""},
        ],
        "evidence": {
            "function": "FUN_0080f9d0" if data_offset == 0x78 else "FUN_0080fb40",
            "funcpropdata_bytes": 0x50,
        },
    }


def describe_default_camera_data_load(
    *,
    data_offset: int,
    root_present: bool,
    class_resolved: bool,
    property_apply_success: bool,
    finalize_success: bool,
) -> dict[str, Any]:
    """Trace FUN_0080fa40 / FUN_0080fbb0."""
    if int(data_offset) not in (0x78, 0x168):
        raise ValueError("default camera data offset must be 0x78 or 0x168")
    if not root_present:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "default-camera-load",
            "status": "root-missing",
            "actions": [],
        }
    actions = [
        {"action": "FUN_0063c6d0", "path": "DAT_00aaad1c -> DAT_00aaadbc"},
        {"action": "read class", "helper": "FUN_0063d360"},
        {"action": "read secondary", "helper": "FUN_0063d360"},
    ]
    if not class_resolved:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "default-camera-load",
            "status": "class-unresolved",
            "actions": actions,
        }
    actions.extend([
        {"action": "FUN_0063fd20", "result": "resolved class"},
        {"action": "FUN_00640c60"},
        {"action": "FUN_0063eaf0"},
        {
            "action": "FUN_006408f0",
            "destination": f"+0x{int(data_offset):x}",
            "success": bool(property_apply_success),
        },
    ])
    if not property_apply_success:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "default-camera-load",
            "status": "property-apply-failed",
            "actions": actions,
        }
    actions.append({
        "action": "camera-data.vtable +0x28",
        "success": bool(finalize_success),
    })
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "default-camera-load",
        "status": "loaded" if finalize_success else "finalize-failed",
        "data_offset": int(data_offset),
        "actions": actions,
        "evidence": {
            "function": "FUN_0080fa40" if data_offset == 0x78 else "FUN_0080fbb0",
            "class_attr": "class",
            "secondary_attr": "DAT_00aaadb0",
        },
    }


def describe_camera_config_defaults_reference() -> dict[str, Any]:
    """Expose manager fields which point at default camera data."""
    reg = camera_config_manager_registration()
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "default-camera-references",
        "references": [
            {
                "name": row["name"],
                "offset": row["offset"],
                "type_id": row["type_id"],
            }
            for row in reg["properties"]
            if row["name"] in ("DefaultStaticCamData", "DefaultTrackingCamData")
        ],
        "evidence": {"function": "FUN_00810710"},
    }
