#!/usr/bin/env python3
"""Prove the Vehicle term in the BMW offset33b Y reference starts at zero.

The HDVehicle offset33b producer retains the manager record, dereferences its
record[0] PhysicsParticipant pointer, and reads actual_participant+0x500.  The
embedded Vehicle begins at actual_participant+0x340, so that read aliases
Vehicle+0x1c0.  The exact retail base Vehicle constructor FUN_0079bfd0 writes
its dword index 0x70 (byte offset 0x1c0) to zero.

This contract proves only that constructor term.  The effective graphical-offset
value subtracted from it remains a resource/init root for the numeric evaluator.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.BMWOffset33bVehicleReferenceYBootstrapZero/1"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"

VEHICLE_OFFSET = 0x340
ACTUAL_PARTICIPANT_REFERENCE_Y_OFFSET = 0x500
VEHICLE_REFERENCE_Y_OFFSET = 0x1C0
VEHICLE_REFERENCE_Y_DWORD_INDEX = 0x70
ZERO_FLOAT32_BITS = "0x00000000"

FUNCTIONS: dict[str, tuple[str, int, str, str, str]] = {
    "0x007125e0": ("FUN_007125e0", 185, "__fastcall", "d0d7c65693b7f3ef34ea399789518ef8c2aee61543bfe0473ddad54f4333adf0", "manager record creates actual PhysicsParticipant"),
    "0x0072ed20": ("FUN_0072ed20", 1161, "__fastcall", "d6eb0ccddc64f5df669ab82e905efdfb9484f70d4201110e8eb35148f19908ff", "actual PhysicsParticipant constructor"),
    "0x0074d640": ("FUN_0074d640", 251, "__fastcall", "0a8ed388762510ec3ff2958df2d45f5c84e09a5a5193041ddcc3f324d20ab205", "Restart pre-Vehicle setup; reviewed target non-writer"),
    "0x0074ddc3": ("FUN_0074ddc3", 957, "__fastcall", "1b8f7a6602190fdd97b5a3d410495c8ff92b3a8b854a703459427b1ff548e4a6", "PhysicsParticipant::Restart ordering"),
    "0x0076b280": ("FUN_0076b280", 7796, "__thiscall", "9563b40c06bcc7442aabd3308eefa62e1b9f7d0bb9afe752ddf0dc068e0cd7f6", "HDVehicle offset33b producer and actual+0x500 reader"),
    "0x0076df50": ("FUN_0076df50", 1548, "__thiscall", "73a0d9d46d5d1bfd58068d2f72e91b77cf8c31cadb27745ba75b646901834dda", "HDVehicle init retains manager record before offset33b producer"),
    "0x00797fd0": ("FUN_00797fd0", 612, "__thiscall", "b8f3cb6525e0742e2afefd31ca51dd050a9d869444526ce03df41067ecb3eeb8", "Vehicle state selector before InitVehicle; reviewed target non-writer"),
    "0x00798df0": ("FUN_00798df0", 1581, "__thiscall", "88904019443d1ea4edaf5a3ef40dd5abfe9e28109ab0b1f09296388f36026e16", "Vehicle::InitVehicle ordering"),
    "0x0079bfd0": ("FUN_0079bfd0", 445, "__fastcall", "06e730897a4a85d93a5f33765fd15b0c52708fb2c864c290804024b109a3d950", "base Vehicle constructor writes dword 0x70 / byte 0x1c0 = zero"),
    "0x0079c1c0": ("FUN_0079c1c0", 497, "__fastcall", "6759f1781d58bf38b72e2fa45ab24fc12bccf46bde95d90c4c57e2a0d600c39c", "embedded Vehicle constructor"),
    "0x00a62690": ("FUN_00a62690", 57, "__fastcall", "f188a9584cad4fcfd979c93925f4dbbf9bb5aa8bcea333566326148156e9c9dd", "early Vehicle::InitVehicle setup; reviewed target non-writer"),
}

REQUIRED_CALLS = (
    ("0x007125e0", "0x0071262b", "0x0072ed20", "construct actual participant"),
    ("0x0072ed20", "0x0072ed57", "0x0079c1c0", "construct embedded Vehicle at actual+0x340"),
    ("0x0079c1c0", "0x0079c1e1", "0x0079bfd0", "run base Vehicle constructor"),
    ("0x0074ddc3", "0x0074ddc3", "0x0074d640", "Restart pre-Vehicle setup"),
    ("0x0074ddc3", "0x0074dddb", "0x00797fd0", "pre-InitVehicle state selector"),
    ("0x0074ddc3", "0x0074de12", "0x00798df0", "Vehicle::InitVehicle entry"),
    ("0x00798df0", "0x00798e3e", "0x00a62690", "early Vehicle system setup"),
    ("0x00798df0", "0x00798f9c", "0x0076df50", "HDVehicle init before later Vehicle load initialization"),
    ("0x0076df50", "0x0076e270", "0x0076b280", "offset33b producer"),
)


def _norm_address(value: Any) -> str:
    try:
        return f"0x{int(str(value), 0):08x}"
    except (TypeError, ValueError):
        return str(value or "").strip().lower()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            raw = raw.strip()
            if not raw:
                continue
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            rows.append(value)
    return rows


def _validate_binary(root: Path) -> None:
    binary = _read_json(root / "binary.json")
    if binary.get("program_name") != PROGRAM:
        raise ValueError("unexpected retail program name")
    if binary.get("executable_md5") != PE_MD5:
        raise ValueError("unexpected retail executable identity")


def _validate_functions(root: Path) -> list[dict[str, Any]]:
    rows = _read_jsonl(root / "functions.jsonl")
    out: list[dict[str, Any]] = []
    for address, expected in FUNCTIONS.items():
        name, size, cc, fingerprint, role = expected
        hits = [r for r in rows if _norm_address(r.get("address")) == address]
        if len(hits) != 1:
            raise ValueError(f"expected exactly one function row for {address}; found {len(hits)}")
        row = hits[0]
        checks = {
            "name": name,
            "size": size,
            "calling_convention": cc,
            "mnemonic_sha256": fingerprint,
        }
        for field, value in checks.items():
            if row.get(field) != value:
                raise ValueError(f"{address} {field} drift")
        if row.get("thunk") is True or row.get("external") is True:
            raise ValueError(f"{address} must remain a concrete retail function")
        out.append({"address": address, **checks, "role": role})
    return out


def _validate_calls(root: Path) -> list[dict[str, str]]:
    rows = _read_jsonl(root / "callgraph.jsonl")
    out: list[dict[str, str]] = []
    for source, instruction, target, role in REQUIRED_CALLS:
        hits = [
            r for r in rows
            if _norm_address(r.get("from_function")) == source
            and _norm_address(r.get("instruction")) == instruction
            and _norm_address(r.get("to")) == target
            and r.get("indirect") is False
        ]
        if len(hits) != 1:
            raise ValueError(f"required direct call drift: {source}:{instruction} -> {target}; found {len(hits)}")
        same_site = [r for r in rows if _norm_address(r.get("from_function")) == source and _norm_address(r.get("instruction")) == instruction]
        if len(same_site) != 1:
            raise ValueError(f"callsite ambiguity at {source}:{instruction}")
        out.append({"from_function": source, "instruction": instruction, "to": target, "role": role})
    return out


def analyze(root: Path) -> dict[str, Any]:
    _validate_binary(root)
    functions = _validate_functions(root)
    calls = _validate_calls(root)

    if ACTUAL_PARTICIPANT_REFERENCE_Y_OFFSET - VEHICLE_OFFSET != VEHICLE_REFERENCE_Y_OFFSET:
        raise AssertionError("actual-participant/Vehicle reference-Y alias drift")
    if VEHICLE_REFERENCE_Y_DWORD_INDEX * 4 != VEHICLE_REFERENCE_Y_OFFSET:
        raise AssertionError("Vehicle reference-Y dword index drift")

    return {
        "format": FORMAT,
        "ready": True,
        "status": "vehicle-reference-y-bootstrap-zero-ready",
        "retail": {"program": PROGRAM, "pe_md5": PE_MD5, "functions": functions, "required_direct_calls": calls},
        "object_graph": {
            "embedded_vehicle_offset": VEHICLE_OFFSET,
            "actual_participant_read_offset": ACTUAL_PARTICIPANT_REFERENCE_Y_OFFSET,
            "vehicle_field_offset": VEHICLE_REFERENCE_Y_OFFSET,
            "alias_expression": "actual_participant+0x500 == embedded_vehicle+0x1c0",
        },
        "constructor_proof": {
            "actual_participant_constructor": "0x0072ed20",
            "embedded_vehicle_constructor": "0x0079c1c0",
            "base_vehicle_constructor": "0x0079bfd0",
            "reviewed_store": "Vehicle dword[0x70] / byte+0x1c0 = 0",
            "stored_type": "float32-compatible zero dword",
            "stored_bits": ZERO_FLOAT32_BITS,
        },
        "offset33b_join": {
            "hdvehicle_init": "0x0076df50",
            "manager_record_retained_at_hdvehicle_offset": 0x3FE8,
            "producer": "0x0076b280",
            "producer_receiver_resolution": "**(HDVehicle+0x3fe8) == actual_participant",
            "producer_read": "float(actual_participant+0x500)",
            "effective_expression_before_numeric_resource_join": "0.0 - effective_graphical_offset_y",
            "reduced_expression": "-effective_graphical_offset_y",
            "effective_graphical_offset_y_numeric_value_proven": False,
        },
        "handoff": {
            "offset33b_vehicle_reference_y_bootstrap_zero_ready": True,
            "offset33b_reference_y_reduced_to_negative_graphical_offset": True,
            "BMW_numeric_offset33b_ready": False,
            "BODY0_to_outer_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "scope": {
            "fresh_first_bootstrap_only": True,
            "additional_mass_zero_proven_by_this_contract": False,
            "effective_graphical_offset_y_numeric_value_proven": False,
            "remaining_resource_roots_evaluated": False,
            "original_game_executed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_root", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = analyze(args.ghidra_root)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
