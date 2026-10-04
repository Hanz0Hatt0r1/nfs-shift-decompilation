#!/usr/bin/env python3
"""Prove the real PhysicsParticipant additional-mass root is zero at first bootstrap.

This proof intentionally supersedes neither the historical invalid manager-record
claim nor its fail-closed correction contract.  It follows the actual pointer
stored in the 0x1fa0 manager record:

    record[0] -> separately allocated 0x2b90 PhysicsParticipant
              -> embedded Vehicle at +0x340
              -> participant+0xba0 == Vehicle+0x860

The allocation is requested through FUN_00886900 with flag 0x20.  The retail
allocator path preserves that flag to FUN_00657ab0, where flag 0x20 executes a
full memset(dst, 0, size).  Exact retail fingerprints and direct-call sites freeze
that reviewed semantic path.  Constructors and the Restart pre-InitVehicle lane
are also fingerprinted; the reviewed retail bodies do not write the target byte
range before FUN_0076df50 reads it into HDVehicle+0x3428.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.BMWOffset33bActualAdditionalMassBootstrapZero/1"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"

ACTUAL_PARTICIPANT_SIZE = 0x2B90
ALLOCATION_ZERO_FLAG = 0x20
VEHICLE_OFFSET = 0x340
PARTICIPANT_ADDITIONAL_MASS_OFFSET = 0xBA0
VEHICLE_ADDITIONAL_MASS_OFFSET = 0x860
TARGET_WIDTH = 4
ZERO_FLOAT32_BITS = "0x00000000"

FUNCTIONS: dict[str, tuple[str, int, str, str, str]] = {
    "0x00637f50": ("FUN_00637f50", 201, "__thiscall", "8128655d31353bd8084be8a320b63eefa2f03e415c3741a1f0a71eccea2cde09", "fallback pool allocation preserving flags"),
    "0x00638020": ("FUN_00638020", 433, "__fastcall", "2d0b31bf22e4ac3e1b689e51396471f5c0d696f82128bab1aac22c86c9fc847d", "pool allocator dispatch preserving flags"),
    "0x006382b0": ("FUN_006382b0", 70, "__fastcall", "91d57a9d31e5d0426b92ea28bc5930e989a72aa41f654791964e8b949198cd6f", "default-pool allocator dispatch"),
    "0x00657ab0": ("FUN_00657ab0", 371, "__thiscall", "f450f33b4ea6112b4a297bfc3fdf3cce9428edcf1c3375bb5f518e4e7383127a", "allocator implementation: flag 0x20 zero-fills allocation"),
    "0x007125e0": ("FUN_007125e0", 185, "__fastcall", "d0d7c65693b7f3ef34ea399789518ef8c2aee61543bfe0473ddad54f4333adf0", "manager record creates separately allocated PhysicsParticipant"),
    "0x0072ed20": ("FUN_0072ed20", 1161, "__fastcall", "d6eb0ccddc64f5df669ab82e905efdfb9484f70d4201110e8eb35148f19908ff", "actual PhysicsParticipant constructor"),
    "0x0074d640": ("FUN_0074d640", 251, "__fastcall", "0a8ed388762510ec3ff2958df2d45f5c84e09a5a5193041ddcc3f324d20ab205", "Restart pre-vehicle CDF/driver-head setup; target non-writer"),
    "0x0074ddc3": ("FUN_0074ddc3", 957, "__fastcall", "1b8f7a6602190fdd97b5a3d410495c8ff92b3a8b854a703459427b1ff548e4a6", "PhysicsParticipant::Restart ordering"),
    "0x0076b280": ("FUN_0076b280", 7796, "__thiscall", "9563b40c06bcc7442aabd3308eefa62e1b9f7d0bb9afe752ddf0dc068e0cd7f6", "HDVehicle offset33b producer"),
    "0x0076df50": ("FUN_0076df50", 1548, "__thiscall", "73a0d9d46d5d1bfd58068d2f72e91b77cf8c31cadb27745ba75b646901834dda", "HDVehicle init reads actual participant+0xba0 into HDVehicle+0x3428"),
    "0x00797fd0": ("FUN_00797fd0", 612, "__thiscall", "b8f3cb6525e0742e2afefd31ca51dd050a9d869444526ce03df41067ecb3eeb8", "Vehicle state selector before InitVehicle; target non-writer"),
    "0x00798df0": ("FUN_00798df0", 1581, "__thiscall", "88904019443d1ea4edaf5a3ef40dd5abfe9e28109ab0b1f09296388f36026e16", "Vehicle::InitVehicle; reaches HDVehicle read before later vehicle-load init"),
    "0x0079bfd0": ("FUN_0079bfd0", 445, "__fastcall", "06e730897a4a85d93a5f33765fd15b0c52708fb2c864c290804024b109a3d950", "base Vehicle constructor; target non-writer"),
    "0x0079c1c0": ("FUN_0079c1c0", 497, "__fastcall", "6759f1781d58bf38b72e2fa45ab24fc12bccf46bde95d90c4c57e2a0d600c39c", "embedded Vehicle constructor"),
    "0x00886900": ("FUN_00886900", 36, "__cdecl", "0b7980ff4fb7fb304f0e8a0a7e6c414fbbb9bfc12d04a09e8ee23211a9b80e1a", "allocation wrapper preserving 0x20 flag"),
    "0x00a62690": ("FUN_00a62690", 57, "__fastcall", "f188a9584cad4fcfd979c93925f4dbbf9bb5aa8bcea333566326148156e9c9dd", "Vehicle::InitVehicle early system setup; target non-writer"),
}

REQUIRED_CALLS = (
    ("0x007125e0", "0x00712617", "0x00886900", "allocate 0x2b90 actual participant with reviewed 0x20 flag"),
    ("0x007125e0", "0x0071262b", "0x0072ed20", "construct actual participant in returned allocation"),
    ("0x0072ed20", "0x0072ed57", "0x0079c1c0", "construct embedded Vehicle at actual+0x340"),
    ("0x0079c1c0", "0x0079c1e1", "0x0079bfd0", "run base Vehicle constructor"),
    ("0x00886900", "0x00886911", "0x00638020", "explicit-pool allocation path"),
    ("0x00886900", "0x0088691f", "0x006382b0", "default-pool allocation path"),
    ("0x006382b0", "0x006382e9", "0x00638020", "default pool joins common allocator"),
    ("0x00638020", "0x0063807c", "0x00657ab0", "primary pool allocation"),
    ("0x00637f50", "0x00637fa7", "0x00657ab0", "fallback pool allocation"),
    ("0x00657ab0", "0x00657be7", "0x009015b0", "flag-0x20 memset zero-fill"),
    ("0x0074ddc3", "0x0074ddc3", "0x0074d640", "Restart CDF/driver-head setup"),
    ("0x0074ddc3", "0x0074dddb", "0x00797fd0", "pre-InitVehicle state selector"),
    ("0x0074ddc3", "0x0074de12", "0x00798df0", "Vehicle::InitVehicle entry"),
    ("0x00798df0", "0x00798e3e", "0x00a62690", "early Vehicle system setup"),
    ("0x00798df0", "0x00798f9c", "0x0076df50", "HDVehicle init before later Vehicle load initialization"),
    ("0x0076df50", "0x0076e270", "0x0076b280", "offset33b producer after additional-mass copy"),
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
        if row.get("name") != name:
            raise ValueError(f"{address} name drift")
        if row.get("size") != size:
            raise ValueError(f"{address} size drift")
        if row.get("calling_convention") != cc:
            raise ValueError(f"{address} calling convention drift")
        if row.get("mnemonic_sha256") != fingerprint:
            raise ValueError(f"{address} mnemonic fingerprint drift")
        if row.get("thunk") is True or row.get("external") is True:
            raise ValueError(f"{address} must remain a concrete retail function")
        out.append({"address": address, "name": name, "size": size, "calling_convention": cc, "mnemonic_sha256": fingerprint, "role": role})
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

    if PARTICIPANT_ADDITIONAL_MASS_OFFSET - VEHICLE_OFFSET != VEHICLE_ADDITIONAL_MASS_OFFSET:
        raise AssertionError("participant/Vehicle target alias drift")
    if PARTICIPANT_ADDITIONAL_MASS_OFFSET + TARGET_WIDTH > ACTUAL_PARTICIPANT_SIZE:
        raise AssertionError("target escaped actual participant allocation")
    if ALLOCATION_ZERO_FLAG != 0x20:
        raise AssertionError("allocator zero-fill flag drift")

    return {
        "format": FORMAT,
        "ready": True,
        "status": "actual-additional-mass-bootstrap-zero-ready",
        "retail": {"program": PROGRAM, "pe_md5": PE_MD5, "functions": functions, "required_direct_calls": calls},
        "object_graph": {
            "manager_record_holds_pointer_at_offset": 0,
            "actual_participant_allocation_size": ACTUAL_PARTICIPANT_SIZE,
            "embedded_vehicle_offset": VEHICLE_OFFSET,
            "participant_additional_mass_offset": PARTICIPANT_ADDITIONAL_MASS_OFFSET,
            "vehicle_additional_mass_offset": VEHICLE_ADDITIONAL_MASS_OFFSET,
            "alias_expression": "actual_participant+0xba0 == embedded_vehicle+0x860",
            "manager_record_plus_0xba0_is_not_the_proven_storage": True,
        },
        "allocation_proof": {
            "allocation_site": "0x00712617",
            "wrapper": "0x00886900",
            "requested_size": ACTUAL_PARTICIPANT_SIZE,
            "requested_flags": ALLOCATION_ZERO_FLAG,
            "primary_allocator": "0x00638020",
            "default_pool_allocator": "0x006382b0",
            "fallback_allocator": "0x00637f50",
            "zero_fill_implementation": "0x00657ab0",
            "zero_fill_callsite": "0x00657be7",
            "zero_fill_target": "0x009015b0",
            "zero_fill_condition": "allocation_flags & 0x20 != 0",
            "zero_fill_operation": "memset(allocation, 0, requested_size)",
        },
        "lifetime_proof": {
            "constructor_chain": ["0x007125e0", "0x0072ed20", "0x0079c1c0", "0x0079bfd0"],
            "pre_initvehicle_reviewed_nonwriters": ["0x0074d640", "0x00797fd0", "0x00a62690"],
            "initvehicle": "0x00798df0",
            "additional_mass_reader": "0x0076df50",
            "reader_semantics": "float(actual_participant+0xba0) -> double HDVehicle+0x3428",
            "offset33b_producer": "0x0076b280",
        },
        "proven_value": {
            "storage": "actual_participant+0xba0 / embedded_vehicle+0x860",
            "type": "float32",
            "bits": ZERO_FLOAT32_BITS,
            "value": 0.0,
            "scope": "fresh actual PhysicsParticipant first bootstrap before FUN_0076df50 read",
        },
        "handoff": {
            "offset33b_actual_additional_mass_bootstrap_zero_ready": True,
            "offset33b_additional_mass_term_can_be_elided_for_first_bootstrap": True,
            "BMW_numeric_offset33b_ready": False,
            "BODY0_to_outer_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "scope": {
            "retracted_manager_record_zero_claim_reused": False,
            "allocator_zero_fill_assumed_without_fingerprint": False,
            "reinitialized_or_reused_actual_participant_lifetime_proven": False,
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
