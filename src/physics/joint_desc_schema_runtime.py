"""Source-backed JointDesc/JointLimitDesc schema for SHIFT physics resources.

The field names, offsets and opaque serializer type-ids come from the retail
registration functions FUN_007b9100 and FUN_007b95d0. Constructor defaults are
recorded only where FUN_007b9030 writes them explicitly.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.JointDescSchema/1"

JOINT_DESC_FIELDS = (
    {"name": "type", "xml_name": None, "offset": 0x10, "type_id": 3, "description": "Joint type (eJointType)."},
    {"name": "object1", "xml_name": "Object1", "offset": 0x14, "type_id": 0, "description": "Name of object to which the joint is connected."},
    {"name": "object2", "xml_name": "Object2", "offset": 0x18, "type_id": 0, "description": "Name of object to which the joint is connected."},
    {"name": "anchor1", "xml_name": "Anchor1", "offset": 0x1C, "type_id": 0x10, "description": "Joint Anchor position relative to Object 1."},
    {"name": "anchor2", "xml_name": "Anchor2", "offset": 0x28, "type_id": 0x10, "description": "Joint Anchor position relative to Object 2."},
    {"name": "axis1", "xml_name": "Axis1", "offset": 0x34, "type_id": 0x10, "description": "Joint Axis local to Object 1."},
    {"name": "axis2", "xml_name": "Axis2", "offset": 0x40, "type_id": 0x10, "description": "Joint Axis local to Object 2."},
    {"name": "normal1", "xml_name": "Normal1", "offset": 0x4C, "type_id": 0x10, "description": "Joint Normal local to Object 1."},
    {"name": "normal2", "xml_name": "Normal2", "offset": 0x58, "type_id": 0x10, "description": "Joint Normal local to Object 2."},
    {"name": "breakable", "xml_name": "Breakable", "offset": 0x64, "type_id": 2, "description": "Is this Joint Breakable?"},
    {"name": "limits_enabled", "xml_name": "LimitsEnabled", "offset": 0x68, "type_id": 2, "description": "Are limits enabled?"},
    {"name": "limit_min", "xml_name": "LimitMin", "offset": 0x6C, "type_id": 1, "description": "Maximum angular limit (Degrees, from normal)."},
    {"name": "limit_max", "xml_name": "LimitMax", "offset": 0x70, "type_id": 1, "description": "Minimum angular limit (Degrees, from normal)."},
    {"name": "break_limit", "xml_name": "BreakLimit", "offset": 0x74, "type_id": 3, "description": "Force threshold beyond which the Joint will break (eJointBreakForce)."},
)

JOINT_LIMIT_FIELDS = (
    {"name": "type", "xml_name": None, "offset": 0x10, "type_id": 3, "description": "Joint limit type"},
    {"name": "value", "xml_name": "Value", "offset": 0x14, "type_id": 10, "description": "Joint limit value"},
    {"name": "restitution", "xml_name": "Restitution", "offset": 0x18, "type_id": 10, "description": "Joint limit restitution"},
    {"name": "spring", "xml_name": "Spring", "offset": 0x1C, "type_id": 10, "description": "Joint limit spring"},
    {"name": "damping", "xml_name": "Damping", "offset": 0x20, "type_id": 10, "description": "Joint limit damping"},
)

EXPLICIT_CONSTRUCTOR_WRITES = {
    "type": {"offset": 0x10, "raw_u32": 1, "value": 1},
    "axis1": {"offset": 0x38, "raw_u32": 0x3F800000, "value": 1.0},
    "axis2": {"offset": 0x44, "raw_u32": 0x3F800000, "value": 1.0},
    "normal1": {"offset": 0x54, "raw_u32": 0x3F800000, "value": 1.0},
    "normal2": {"offset": 0x60, "raw_u32": 0x3F800000, "value": 1.0},
    "breakable": {"offset": 0x64, "raw_u32": 0, "value": 0},
    "limits_enabled": {"offset": 0x68, "raw_u32": 0, "value": 0},
    "limit_min": {"offset": 0x6C, "raw_u32": 0, "value": 0.0},
    "limit_max": {"offset": 0x70, "raw_u32": 0, "value": 0.0},
    "break_limit": {"offset": 0x74, "raw_u32": 0, "value": 0},
}


def build_joint_desc_schema() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "class": "JointDesc",
        "registration_function": "FUN_007b9100",
        "constructor": "FUN_007b9030",
        "fields": [dict(field) for field in JOINT_DESC_FIELDS],
        "explicit_constructor_writes": {
            name: dict(value) for name, value in EXPLICIT_CONSTRUCTOR_WRITES.items()
        },
        "registration": {
            "helper": "FUN_0063a280",
            "note": "type_id is preserved as the observed registration argument; it is not assigned a semantic C++ type name."
        },
        "evidence": {
            "source_file": ".\\Source\\Interface\\Interface.cpp",
            "class_strings": ["JointBase", "JointDesc", "JointDescManager"],
        },
        "status": "ready",
        "limitations": [
            "Serializer type-ids are kept opaque.",
            "Only constructor writes directly visible in FUN_007b9030 are represented as explicit defaults.",
            "No conversion of angular degree fields into radians is performed here.",
        ],
    }


def build_joint_limit_desc_schema() -> dict[str, Any]:
    return {
        "format": "SHIFT.JointLimitDescSchema/1",
        "version": 1,
        "class": "JointLimitDesc",
        "registration_function": "FUN_007b95d0",
        "fields": [dict(field) for field in JOINT_LIMIT_FIELDS],
        "registration": {
            "helper": "FUN_0063a280",
            "note": "type_id is preserved as the observed registration argument; it is not assigned a semantic C++ type name."
        },
        "evidence": {
            "source_file": ".\\Source\\Interface\\Interface.cpp",
            "class_strings": ["JointLimitDesc"],
        },
        "status": "ready",
        "limitations": [
            "Default values are not claimed unless directly recovered from a constructor.",
            "No physical-unit normalization is performed.",
        ],
    }


def validate_joint_desc_schema(schema: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    fields = schema.get("fields") or []
    offsets: list[int] = []
    names: set[str] = set()
    for field in fields:
        name = str(field.get("name"))
        offset = int(field.get("offset"))
        if name in names:
            errors.append(f"duplicate-field:{name}")
        names.add(name)
        if offset < 0x10 or offset > 0x74:
            errors.append(f"offset-out-of-range:{name}:{offset:#x}")
        offsets.append(offset)
    if offsets != sorted(offsets):
        errors.append("fields-not-in-offset-order")
    expected = {f["name"]: f["offset"] for f in JOINT_DESC_FIELDS}
    actual = {str(f["name"]): int(f["offset"]) for f in fields}
    if actual != expected:
        errors.append("field-offset-map-mismatch")
    return {"ready": not errors, "errors": errors}


def build_joint_desc_defaults() -> dict[str, Any]:
    schema = build_joint_desc_schema()
    defaults: dict[str, Any] = {}
    for field in schema["fields"]:
        item = schema["explicit_constructor_writes"].get(field["name"])
        if item is not None:
            defaults[field["name"]] = dict(item)
    return {
        "format": "SHIFT.JointDescExplicitDefaults/1",
        "version": 1,
        "constructor": "FUN_007b9030",
        "defaults": defaults,
        "derived_vectors": {
            "axis1": [0.0, 1.0, 0.0],
            "axis2": [0.0, 1.0, 0.0],
            "normal1": [0.0, 0.0, 1.0],
            "normal2": [0.0, 0.0, 1.0],
        },
        "derived_from": {
            "axis1": ["+0x38=1.0", "other components remain base-zeroed unless later written"],
            "axis2": ["+0x44=1.0", "other components remain base-zeroed unless later written"],
            "normal1": ["+0x54=1.0", "other components remain base-zeroed unless later written"],
            "normal2": ["+0x60=1.0", "other components remain base-zeroed unless later written"],
        },
        "status": "ready",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit source-backed SHIFT JointDesc schemas.")
    parser.add_argument("--joint", action="store_true", help="emit JointDesc schema")
    parser.add_argument("--limit", action="store_true", help="emit JointLimitDesc schema")
    parser.add_argument("--defaults", action="store_true", help="emit explicit JointDesc constructor defaults")
    args = parser.parse_args()

    if not (args.joint or args.limit or args.defaults):
        args.joint = True
        args.limit = True
        args.defaults = True

    payload: dict[str, Any] = {}
    if args.joint:
        payload["joint_desc"] = build_joint_desc_schema()
    if args.limit:
        payload["joint_limit_desc"] = build_joint_limit_desc_schema()
    if args.defaults:
        payload["joint_desc_defaults"] = build_joint_desc_defaults()
    payload["validation"] = validate_joint_desc_schema(payload["joint_desc"])
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["validation"]["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
