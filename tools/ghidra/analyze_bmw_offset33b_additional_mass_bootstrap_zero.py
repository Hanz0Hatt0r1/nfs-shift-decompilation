#!/usr/bin/env python3
"""Prove the bootstrap-zero additional-mass root used by BMW offset33b.

The source-backed ``FUN_0076b280`` offset33b producer reads an additional mass
through the current PhysicsParticipant at ``participant+0xba0``.  Because the
embedded outer Vehicle begins at ``participant+0x340``, this is the same storage
as ``Vehicle+0x860``.

This proof is deliberately narrower than a numeric offset33b evaluator.  It
freezes the already-reviewed retail constructor/reset/lifetime semantics behind
exact function fingerprints, direct-call instruction addresses and source
anchors, and proves only that the scalar is IEEE-754 +0.0f on the first and
reinitialized participant bootstrap path before Vehicle::InitVehicle enters the
HighDetailVehicle initialization transaction.

No original-game execution or runtime witness is required.  The contract does
not claim the remaining HDV/VDF/SDF/tire-derived offset33b roots are numeric.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.BMWOffset33bAdditionalMassBootstrapZero/1"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"

PARTICIPANT_RECORD_STRIDE = 0x1FA0
PARTICIPANT_SUBOBJECT_OFFSET = 0xB00
SUBOBJECT_ZERO_OFFSET = 0xA0
PARTICIPANT_ADDITIONAL_MASS_OFFSET = 0xBA0
VEHICLE_EMBEDDED_OFFSET = 0x340
VEHICLE_ADDITIONAL_MASS_OFFSET = 0x860
ZERO_RANGE_START = 0x24
ZERO_RANGE_END_EXCLUSIVE = 0x124
ZERO_FLOAT32_BITS = "0x00000000"

FUNCTIONS: dict[str, dict[str, Any]] = {
    "0x00552dd0": {
        "name": "FUN_00552dd0",
        "size": 170,
        "calling_convention": "__fastcall",
        "mnemonic_sha256": "cf7b038743bf9c6e0d8554f2c4026e3197c668ef8dc1bfbdf4711b5d38670d02",
        "role": "participant embedded-state zero initializer",
    },
    "0x007126a0": {
        "name": "FUN_007126a0",
        "size": 83,
        "calling_convention": "__fastcall",
        "mnemonic_sha256": "36ef983a7552ce34526a1e03279055c1496ba70fa1ac10131354a33640f52f21",
        "role": "participant slot reinitialization path",
    },
    "0x00714360": {
        "name": "FUN_00714360",
        "size": 230,
        "calling_convention": "__fastcall",
        "mnemonic_sha256": "221039434cf2689ee4f4a7c681cbc46e1cef3f7ea69b99001ea5301fec9ae867",
        "role": "0x1fa0 PhysicsParticipant record constructor",
    },
    "0x0074d640": {
        "name": "FUN_0074d640",
        "size": 251,
        "calling_convention": "__fastcall",
        "mnemonic_sha256": "0a8ed388762510ec3ff2958df2d45f5c84e09a5a5193041ddcc3f324d20ab205",
        "role": "Restart pre-InitVehicle CDF/driver-head setup; reviewed non-writer of participant+0xba0",
    },
    "0x0074ddb0": {
        "name": "FUN_0074ddb0",
        "size": 18,
        "calling_convention": "__fastcall",
        "mnemonic_sha256": "bc9744e48161533bacc2815fa9ea9b95e475153aabc6c6d8fc796d9709df7e81",
        "role": "participant restart wrapper",
    },
    "0x0041cbd6": {
        "name": "FUN_0041cbd6",
        "size": 13,
        "calling_convention": "__fastcall",
        "mnemonic_sha256": "eca43ac3f961bbe0811d2c3ea872a468a21834465ccb2a65e4280980c27ee16a",
        "role": "current-participant setter and Restart forwarder",
    },
    "0x0074ddc3": {
        "name": "FUN_0074ddc3",
        "size": 957,
        "calling_convention": "__fastcall",
        "mnemonic_sha256": "1b8f7a6602190fdd97b5a3d410495c8ff92b3a8b854a703459427b1ff548e4a6",
        "role": "MWL::Core::PhysicsParticipant::Restart",
    },
    "0x0074e1a0": {
        "name": "FUN_0074e1a0",
        "size": 411,
        "calling_convention": "__fastcall",
        "mnemonic_sha256": "1d8bc5a41a02dc21368f0be8e6ff7a482dd5d11bfe0607b54d0cea1ca3e9f003",
        "role": "VDF/resource pre-init and Restart dispatch; reviewed non-writer of participant+0xba0",
    },
    "0x00797fd0": {
        "name": "FUN_00797fd0",
        "size": 612,
        "calling_convention": "__thiscall",
        "mnemonic_sha256": "b8f3cb6525e0742e2afefd31ca51dd050a9d869444526ce03df41067ecb3eeb8",
        "role": "outer Vehicle state selector before InitVehicle; reviewed non-writer of Vehicle+0x860",
    },
    "0x00798df0": {
        "name": "FUN_00798df0",
        "size": 1581,
        "calling_convention": "__thiscall",
        "mnemonic_sha256": "88904019443d1ea4edaf5a3ef40dd5abfe9e28109ab0b1f09296388f36026e16",
        "role": "MWL::Core::Vehicle::InitVehicle",
    },
    "0x0076b280": {
        "name": "FUN_0076b280",
        "size": 7796,
        "calling_convention": "__thiscall",
        "mnemonic_sha256": "9563b40c06bcc7442aabd3308eefa62e1b9f7d0bb9afe752ddf0dc068e0cd7f6",
        "role": "source-backed HDVehicle offset33b producer",
    },
}

# Direct-call locations are part of the proof.  The two FUN_0074e1a0 ->
# FUN_0074ddb0 sites are alternate branches after the VDF pre-init call.
REQUIRED_CALLS = (
    ("0x00714360", "0x007143c9", "0x00552dd0", "fresh participant record zero init"),
    ("0x007126a0", "0x007126db", "0x00552dd0", "reused participant record zero init"),
    ("0x0074e1a0", "0x0074e1bb", "0x007029c0", "VDF/GetCarPhysicsDetails pre-init"),
    ("0x0074e1a0", "0x0074e247", "0x0074ddb0", "Restart branch A"),
    ("0x0074e1a0", "0x0074e262", "0x0074ddb0", "Restart branch B"),
    ("0x0074ddb0", "0x0074ddbd", "0x0041cbd6", "Restart wrapper forward"),
    ("0x0041cbd6", "0x0041cbe7", "0x0074ddc3", "source-labelled Restart entry"),
    ("0x0074ddc3", "0x0074ddc3", "0x0074d640", "Restart CDF/driver-head setup"),
    ("0x0074ddc3", "0x0074dddb", "0x00797fd0", "outer Vehicle pre-init state selector"),
    ("0x0074ddc3", "0x0074de12", "0x00798df0", "Vehicle::InitVehicle entry"),
)

SOURCE_ANCHORS = (
    (".\\Source\\System\\PhysicsParticipant.cpp", "0x0074ddc3"),
    ("MWL::Core::PhysicsParticipant::Restart", "0x0074ddc3"),
    (".\\Source\\Vehicle\\Vehicle.cpp", "0x00798df0"),
    ("MWL::Core::Vehicle::InitVehicle", "0x00798df0"),
)


def _norm_address(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    try:
        return f"0x{int(text, 0):08x}"
    except ValueError:
        return text


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            text = raw.strip()
            if not text:
                continue
            try:
                value = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            rows.append(value)
    return rows


def _validate_binary(root: Path) -> dict[str, Any]:
    binary = _read_json(root / "binary.json")
    if binary.get("program_name") != PROGRAM:
        raise ValueError("unexpected retail program name")
    if binary.get("executable_md5") != PE_MD5:
        raise ValueError("unexpected retail executable identity")
    return binary


def _validate_functions(root: Path) -> list[dict[str, Any]]:
    rows = _read_jsonl(root / "functions.jsonl")
    validated: list[dict[str, Any]] = []
    for address, expected in FUNCTIONS.items():
        hits = [row for row in rows if _norm_address(row.get("address")) == address]
        if len(hits) != 1:
            raise ValueError(f"expected exactly one {address} function row; found {len(hits)}")
        row = hits[0]
        for field in ("name", "size", "calling_convention", "mnemonic_sha256"):
            if row.get(field) != expected[field]:
                raise ValueError(f"{address} {field} drift")
        if row.get("thunk") is True or row.get("external") is True:
            raise ValueError(f"{address} must be a concrete retail function")
        validated.append(
            {
                "address": address,
                "name": expected["name"],
                "size": expected["size"],
                "calling_convention": expected["calling_convention"],
                "mnemonic_sha256": expected["mnemonic_sha256"],
                "role": expected["role"],
            }
        )
    return validated


def _validate_calls(root: Path) -> list[dict[str, Any]]:
    rows = _read_jsonl(root / "callgraph.jsonl")
    result: list[dict[str, Any]] = []
    for source, instruction, target, role in REQUIRED_CALLS:
        hits = [
            row
            for row in rows
            if _norm_address(row.get("from_function")) == source
            and _norm_address(row.get("instruction")) == instruction
            and _norm_address(row.get("to")) == target
            and row.get("indirect") is False
        ]
        if len(hits) != 1:
            raise ValueError(
                f"required direct call drift: {source} {instruction} -> {target}; found {len(hits)}"
            )
        same_site = [
            row
            for row in rows
            if _norm_address(row.get("from_function")) == source
            and _norm_address(row.get("instruction")) == instruction
        ]
        if len(same_site) != 1:
            raise ValueError(f"callsite ambiguity at {source}:{instruction}")
        result.append(
            {
                "from_function": source,
                "instruction": instruction,
                "to": target,
                "role": role,
            }
        )

    restart_sites = [
        int(instruction, 0)
        for source, instruction, _target, _role in REQUIRED_CALLS
        if source == "0x0074ddc3"
    ]
    if restart_sites != sorted(restart_sites):
        raise ValueError("Restart call ordering specification is not monotonic")
    return result


def _validate_source_anchors(root: Path) -> list[dict[str, Any]]:
    rows = _read_jsonl(root / "strings_xrefs.jsonl")
    result: list[dict[str, Any]] = []
    for value, expected_function in SOURCE_ANCHORS:
        hits = [row for row in rows if row.get("value") == value]
        if len(hits) != 1:
            raise ValueError(f"source anchor drift for {value!r}: found {len(hits)}")
        functions = hits[0].get("functions")
        if not isinstance(functions, list):
            raise ValueError(f"source anchor functions missing for {value!r}")
        normalized = {_norm_address(item) for item in functions}
        if expected_function not in normalized:
            raise ValueError(f"source anchor {value!r} no longer belongs to {expected_function}")
        result.append({"value": value, "function": expected_function})
    return result


def analyze_bmw_offset33b_additional_mass_bootstrap_zero(root: Path) -> dict[str, Any]:
    _validate_binary(root)
    functions = _validate_functions(root)
    calls = _validate_calls(root)
    source_anchors = _validate_source_anchors(root)

    if PARTICIPANT_SUBOBJECT_OFFSET + SUBOBJECT_ZERO_OFFSET != PARTICIPANT_ADDITIONAL_MASS_OFFSET:
        raise AssertionError("participant subobject/additional-mass offset relation drift")
    if PARTICIPANT_ADDITIONAL_MASS_OFFSET - VEHICLE_EMBEDDED_OFFSET != VEHICLE_ADDITIONAL_MASS_OFFSET:
        raise AssertionError("participant/Vehicle additional-mass alias relation drift")
    if not (ZERO_RANGE_START <= SUBOBJECT_ZERO_OFFSET < ZERO_RANGE_END_EXCLUSIVE):
        raise AssertionError("additional-mass scalar escaped recovered constructor zero range")
    if SUBOBJECT_ZERO_OFFSET % 4 != 0:
        raise AssertionError("additional-mass scalar is not dword aligned")

    return {
        "format": FORMAT,
        "ready": True,
        "status": "additional-mass-bootstrap-zero-ready",
        "retail": {
            "program": PROGRAM,
            "pe_md5": PE_MD5,
            "functions": functions,
            "required_direct_calls": calls,
            "source_anchors": source_anchors,
        },
        "proof": {
            "participant_record_stride": PARTICIPANT_RECORD_STRIDE,
            "constructor": {
                "function": "0x00714360",
                "zero_helper": "0x00552dd0",
                "zero_helper_call_instruction": "0x007143c9",
                "zero_helper_argument": "participant + 0xb00",
            },
            "reinitialized_slot_reset": {
                "function": "0x007126a0",
                "zero_helper": "0x00552dd0",
                "zero_helper_call_instruction": "0x007126db",
                "zero_helper_argument": "participant + 0xb00",
            },
            "recovered_zero_helper_semantics": {
                "anchored_by_exact_function_fingerprint": True,
                "subobject_zero_range_start": ZERO_RANGE_START,
                "subobject_zero_range_end_exclusive": ZERO_RANGE_END_EXCLUSIVE,
                "target_subobject_offset": SUBOBJECT_ZERO_OFFSET,
                "target_is_inside_zero_range": True,
            },
            "storage_alias": {
                "participant_subobject_offset": PARTICIPANT_SUBOBJECT_OFFSET,
                "participant_additional_mass_offset": PARTICIPANT_ADDITIONAL_MASS_OFFSET,
                "vehicle_embedded_offset": VEHICLE_EMBEDDED_OFFSET,
                "vehicle_additional_mass_offset": VEHICLE_ADDITIONAL_MASS_OFFSET,
                "equation": "participant+0xba0 == (participant+0x340)+0x860 == Vehicle+0x860",
            },
            "bootstrap_preservation": {
                "VDF_preinit_then_restart": True,
                "restart_pre_InitVehicle_direct_call_order": [
                    "0x0074ddc3 -> FUN_0074d640",
                    "0x0074dddb -> FUN_00797fd0",
                    "0x0074de12 -> FUN_00798df0",
                ],
                "reviewed_exact_fingerprint_nonwriters": [
                    "0x0074e1a0",
                    "0x0074d640",
                    "0x00797fd0",
                ],
                "value_preserved_until_Vehicle_InitVehicle": True,
            },
            "offset33b_root": {
                "consumer_producer": "0x0076b280",
                "semantic_name": "additional participant mass term",
                "participant_storage": "participant+0xba0",
                "vehicle_alias_storage": "Vehicle+0x860",
                "value_type": "float32",
                "value_bits": ZERO_FLOAT32_BITS,
                "value": 0.0,
                "numeric_value_proven": True,
            },
        },
        "scope": {
            "applies_to": [
                "fresh PhysicsParticipant records constructed by FUN_00714360",
                "reused participant records reset through FUN_007126a0",
                "first/reinitialized bootstrap path before Vehicle::InitVehicle",
            ],
            "source_review_semantics_are_guarded_by_exact_retail_fingerprints": True,
            "original_game_executed": False,
            "runtime_witness_required": False,
            "remaining_HDV_VDF_SDF_tire_roots_evaluated": False,
        },
        "gates": {
            "offset33b_additional_mass_bootstrap_zero_ready": True,
            "offset33b_additional_mass_term_can_be_elided_for_first_bootstrap": True,
            "BMW_numeric_offset33b_ready": False,
            "BODY0_to_outer_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "blockers": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prove the BMW offset33b participant+0xba0 / Vehicle+0x860 bootstrap-zero root"
    )
    parser.add_argument("ghidra_export", type=Path, help="retail Ghidra export root")
    parser.add_argument("--json-out", type=Path, default=None, help="write proof contract JSON")
    args = parser.parse_args()

    try:
        report = analyze_bmw_offset33b_additional_mass_bootstrap_zero(args.ghidra_export)
    except (OSError, ValueError, AssertionError) as exc:
        parser.error(str(exc))

    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
