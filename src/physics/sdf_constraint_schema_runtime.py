"""Source-backed SDF constraint descriptor schema from retail SHIFT.

FUN_007b42f0 registers the fields of the SDF constraint descriptor. The three
type-id 0x13 fields retain their source global identifiers because the retail
snapshot does not establish safe semantic names for them.
"""
from __future__ import annotations

import json

FORMAT = "SHIFT.SDFConstraintDescriptorSchema/1"

FIELDS = (
    {"name": "type", "label": None, "offset": 0x10, "type_id": 3},
    {"name": "label", "label": "Label", "offset": 0x14, "type_id": 0},
    {"name": "pos_body", "label": "Pos Body", "offset": 0x18, "type_id": 0},
    {"name": "neg_body", "label": "Neg Body", "offset": 0x1C, "type_id": 0},
    {"name": "copy_body", "label": "Copy Body", "offset": 0x20, "type_id": 0},
    {"name": "opaque_0", "label": None, "offset": 0x28, "type_id": 0x13, "source_global": "DAT_00afc8b8"},
    {"name": "opaque_1", "label": None, "offset": 0x40, "type_id": 0x13, "source_global": "DAT_00b0ce6c"},
    {"name": "opaque_2", "label": None, "offset": 0x58, "type_id": 0x13, "source_global": "DAT_00b0ce64"},
)

PARSER_FIELD_ALIASES = {
    "label": {"descriptor_offset": 0x14, "source_field": "Label"},
    "posbody": {"descriptor_offset": 0x18, "source_field": "Pos Body"},
    "negbody": {"descriptor_offset": 0x1C, "source_field": "Neg Body"},
    "copybody": {"descriptor_offset": 0x20, "source_field": "Copy Body"},
}


def build_sdf_constraint_descriptor_schema():
    return {
        "format": FORMAT,
        "version": 1,
        "class": "SDFConstraintDescriptor",
        "registration_function": "FUN_007b42f0",
        "registration_helper": "FUN_0063a280",
        "fields": [dict(field) for field in FIELDS],
        "parser_field_aliases": {key: dict(value) for key, value in PARSER_FIELD_ALIASES.items()},
        "evidence": {
            "source_file": ".\\Source\\Interface\\Interface.cpp",
            "registration_return": 1,
            "opaque_field_globals": {
                "0x28": "DAT_00afc8b8",
                "0x40": "DAT_00b0ce6c",
                "0x58": "DAT_00b0ce64",
            },
        },
        "status": "ready",
        "limitations": [
            "The three type-id 0x13 fields remain opaque because their semantic property strings are not safely recovered.",
            "No assumption is made that the parser-level 'pos' tuple/string field maps to one of these opaque descriptor slots.",
        ],
    }


def validate_sdf_constraint_descriptor_schema(schema):
    errors = []
    fields = schema.get("fields") or []
    expected = {field["name"]: (field["offset"], field["type_id"]) for field in FIELDS}
    actual = {}
    seen_offsets = set()
    for field in fields:
        name = str(field.get("name"))
        offset = int(field.get("offset"))
        type_id = int(field.get("type_id"))
        if offset in seen_offsets:
            errors.append(f"duplicate-offset:{offset:#x}")
        seen_offsets.add(offset)
        actual[name] = (offset, type_id)
    if actual != expected:
        errors.append("field-map-mismatch")
    if [int(field["offset"]) for field in fields] != sorted(int(field["offset"]) for field in fields):
        errors.append("fields-not-in-offset-order")
    return {"ready": not errors, "errors": errors}


def main():
    payload = build_sdf_constraint_descriptor_schema()
    payload["validation"] = validate_sdf_constraint_descriptor_schema(payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["validation"]["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
