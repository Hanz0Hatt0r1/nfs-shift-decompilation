#!/usr/bin/env python3
"""Prove the retail cPhysicsManager +0x388 writer and its initial value.

This proof joins exact file-backed SHIFT.exe instruction bytes, frozen Ghidra
function/callgraph exports, the decompiler C export, and the already-positive
source-backed Physics Manager owner contract.  It deliberately stops before
assigning physical time units or admitting the final retail scheduler cadence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.PhysicsManagerRateWriterProvenance/1"
OWNER_FORMAT = "SHIFT.PhysicsManagerSchedulerEntryOwner/1"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
PE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
WRITER = 0x0070F170
WRITER_NAME = "FUN_0070f170"
WRITER_MNEMONIC_SHA256 = "1256ccf2a09a822d5160f1389b6b9bf580159cb20bc6fc4cce105fda5c50ce90"
WRITER_RAW_SHA256 = "4c29b7b6f7d37b36b1e96a50ce6a988ec8fbee58e4e9192d3b3b775d43159cae"
CONSTRUCTOR = 0x0070FAE0
CONSTRUCTOR_NAME = "FUN_0070fae0"
CONSTRUCTOR_MNEMONIC_SHA256 = "072f0f9df5e4b00b2ff7cdbf991923afacaa82bcdac508310f3eb0a3e5941859"
ACCESSOR_MUTATOR = 0x00714560
ACCESSOR_MUTATOR_NAME = "FUN_00714560"
ACCESSOR_MUTATOR_MNEMONIC_SHA256 = "0fdfd115ce435f07172048099c7c8ae063842de2dcad60bfb06ca40cbba49fd4"
MANAGER_VTABLE = 0x00B04524
RATE_OFFSET = 0x388
INITIAL_RATE = 0xB4

EXPECTED_CALLERS = {
    (0x0070FAE0, 0x0070FC68),
    (0x00710A70, 0x00710C1C),
    (0x007117E0, 0x00711813),
    (0x007119C0, 0x00711B37),
    (0x00714560, 0x00714578),
}

MACHINE_FRAGMENTS = {
    "writer_param_float_load": (0x0070F173, "db4508"),
    "writer_param_integer_load": (0x0070F176, "8b4508"),
    "writer_plus_0x388_store": (0x0070F179, "898188030000"),
    "writer_plus_0x38c_reciprocal_store": (0x0070F18F, "d9998c030000"),
    "writer_divide_by_30": (0x0070F197, "dc350020ab00"),
    "writer_plus_0x390_rate_over_30_store": (0x0070F1A3, "d99190030000"),
    "writer_reciprocal_rate_over_30": (0x0070F1A9, "def9"),
    "writer_plus_0x394_reciprocal_store": (0x0070F1AB, "d99994030000"),
    "writer_ret_stack4": (0x0070F1B2, "c20400"),
    "constructor_save_receiver": (0x0070FAFD, "8bf1"),
    "constructor_install_manager_vtable": (0x0070FB13, "c7062445b000"),
    "constructor_push_initial_rate_180": (0x0070FC3D, "68b4000000"),
    "constructor_restore_receiver_for_writer": (0x0070FC60, "8bce"),
    "constructor_call_writer": (0x0070FC68, "e803f5ffff"),
    "accessor_mutator_push_rate": (0x0071456E, "50"),
    "accessor_mutator_call_accessor": (0x00714571, "e81ab9ffff"),
    "accessor_mutator_receiver_from_accessor": (0x00714576, "8bc8"),
    "accessor_mutator_call_writer": (0x00714578, "e8f3abffff"),
}


@dataclass(frozen=True)
class Section:
    va: int
    virtual_size: int
    raw_size: int
    raw_pointer: int


@dataclass(frozen=True)
class PE:
    data: bytes
    image_base: int
    sections: tuple[Section, ...]

    def read(self, address: int, size: int) -> bytes:
        rva = address - self.image_base
        for section in self.sections:
            if section.va <= rva < section.va + max(section.virtual_size, section.raw_size):
                delta = rva - section.va
                if delta + size > section.raw_size:
                    raise ValueError(f"VA 0x{address:08x} is not fully file-backed")
                offset = section.raw_pointer + delta
                payload = self.data[offset : offset + size]
                if len(payload) != size:
                    raise ValueError(f"VA 0x{address:08x} read truncated")
                return payload
        raise ValueError(f"VA 0x{address:08x} is not mapped")


def _parse_pe(data: bytes) -> PE:
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise ValueError("not a PE/MZ image")
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe_offset : pe_offset + 4] != b"PE\0\0":
        raise ValueError("missing PE signature")
    file_header = pe_offset + 4
    machine, count, _ts, _sym, _syms, optional_size, _flags = struct.unpack_from(
        "<HHIIIHH", data, file_header
    )
    if machine != 0x14C:
        raise ValueError(f"expected PE i386 machine 0x014c, got 0x{machine:04x}")
    optional = file_header + 20
    magic = struct.unpack_from("<H", data, optional)[0]
    if magic != 0x10B:
        raise ValueError(f"expected PE32 optional header, got 0x{magic:04x}")
    image_base = struct.unpack_from("<I", data, optional + 28)[0]
    table = optional + optional_size
    sections: list[Section] = []
    for index in range(count):
        offset = table + index * 40
        virtual_size, va, raw_size, raw_pointer = struct.unpack_from("<IIII", data, offset + 8)
        sections.append(Section(va, virtual_size, raw_size, raw_pointer))
    return PE(data, image_base, tuple(sections))


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_no}: expected JSON object")
        rows.append(value)
    return rows


def _norm(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None
    token = value.strip().lower()
    if token.startswith("fun_"):
        token = token[4:]
    if token.startswith("0x"):
        token = token[2:]
    try:
        return int(token, 16)
    except ValueError:
        return None


def _function_index(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for row in rows:
        address = _norm(row.get("address"))
        if address is not None:
            result[address] = row
    return result


def _validate_function(
    functions: Mapping[int, Mapping[str, Any]],
    address: int,
    name: str,
    mnemonic_sha256: str,
) -> dict[str, Any]:
    row = functions.get(address)
    if not isinstance(row, Mapping):
        raise ValueError(f"required function 0x{address:08x} missing")
    if row.get("name") != name or row.get("mnemonic_sha256") != mnemonic_sha256:
        raise ValueError(f"{name}: function identity/fingerprint drift")
    return dict(row)


def _direct_callers(callgraph: list[dict[str, Any]]) -> list[dict[str, Any]]:
    found: set[tuple[int, int]] = set()
    rows: list[dict[str, Any]] = []
    for row in callgraph:
        if _norm(row.get("to")) != WRITER or row.get("indirect") is not False:
            continue
        source = _norm(row.get("from_function"))
        instruction = _norm(row.get("instruction"))
        if source is None or instruction is None:
            raise ValueError("writer callgraph row missing source/instruction")
        found.add((source, instruction))
        rows.append(
            {
                "from_function": f"0x{source:08x}",
                "from_name": row.get("from_name"),
                "instruction": f"0x{instruction:08x}",
                "to": f"0x{WRITER:08x}",
            }
        )
    if found != EXPECTED_CALLERS:
        raise ValueError(
            "FUN_0070f170 direct-caller surface drift: "
            f"expected={sorted(EXPECTED_CALLERS)}, found={sorted(found)}"
        )
    return sorted(rows, key=lambda row: row["instruction"])


def _extract_function_body(source: str, signature: str) -> str:
    start = source.find(signature)
    if start < 0:
        raise ValueError(f"decompiler function signature missing: {signature}")
    brace = source.find("{", start)
    if brace < 0:
        raise ValueError(f"decompiler function body missing: {signature}")
    depth = 0
    for index in range(brace, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise ValueError(f"unterminated decompiler function body: {signature}")


def _validate_decompiler(source: str) -> dict[str, Any]:
    writer = _extract_function_body(source, "void __thiscall FUN_0070f170(void *this,int param_1)")
    writer_required = (
        "*(int *)((int)this + 0x388) = param_1;",
        "*(float *)((int)this + 0x38c) = 1.0 / (float)param_1;",
        "fVar1 = (float)param_1 / 30.0;",
        "*(float *)((int)this + 0x390) = fVar1;",
        "*(float *)((int)this + 0x394) = 1.0 / fVar1;",
    )
    for text in writer_required:
        if text not in writer:
            raise ValueError(f"writer decompiler contract drift: {text}")

    constructor = _extract_function_body(source, "undefined4 * __fastcall FUN_0070fae0(undefined4 *param_1)")
    if "FUN_0070f170(param_1,0xb4);" not in constructor:
        raise ValueError("constructor no longer calls rate writer with 0xb4")

    mutator = _extract_function_body(source, "undefined4 __thiscall FUN_00714560(void *this,int param_1)")
    accessor_pos = mutator.find("this_00 = (void *)FUN_0070fe90();")
    writer_pos = mutator.find("FUN_0070f170(this_00,uVar1);")
    if accessor_pos < 0 or writer_pos <= accessor_pos:
        raise ValueError("accessor-return -> rate-writer decompiler join drift")

    return {
        "writer_contract_verified": True,
        "constructor_calls_writer_with_180": True,
        "accessor_return_flows_to_writer_receiver": True,
    }


def _validate_owner(owner_path: Path) -> dict[str, Any]:
    owner = _read_json(owner_path)
    if owner.get("format") != OWNER_FORMAT or owner.get("ready") is not True:
        raise ValueError(f"owner evidence must be positive {OWNER_FORMAT}")
    if owner.get("owner") != "MWL::Core::cPhysicsManager":
        raise ValueError("Physics Manager owner drift")
    scheduler = owner.get("scheduler_entry")
    provenance = owner.get("provenance")
    if not isinstance(scheduler, Mapping) or not isinstance(provenance, Mapping):
        raise ValueError("owner evidence missing scheduler/provenance")
    if _norm(scheduler.get("vtable_address")) != MANAGER_VTABLE:
        raise ValueError("Physics Manager vtable address drift")
    if provenance.get("retail_pe_md5") != PE_MD5:
        raise ValueError("owner evidence retail PE identity drift")
    if provenance.get("source_manager_contract") != "SHIFT.PhysicsManagerRuntime/1":
        raise ValueError("source-backed Physics Manager contract missing")
    return {
        "format": OWNER_FORMAT,
        "owner": owner["owner"],
        "vtable": f"0x{MANAGER_VTABLE:08x}",
        "source_manager_contract": provenance["source_manager_contract"],
        "verified": True,
    }


def analyze(
    pe_path: Path,
    decompiler_path: Path,
    functions_path: Path,
    callgraph_path: Path,
    owner_path: Path,
) -> dict[str, Any]:
    pe_bytes = pe_path.read_bytes()
    md5 = hashlib.md5(pe_bytes).hexdigest()
    sha256 = hashlib.sha256(pe_bytes).hexdigest()
    if md5 != PE_MD5 or sha256 != PE_SHA256:
        raise ValueError(f"retail SHIFT.exe identity drift: md5={md5} sha256={sha256}")
    image = _parse_pe(pe_bytes)
    if image.image_base != 0x00400000:
        raise ValueError(f"SHIFT.exe image base drift: 0x{image.image_base:08x}")

    fragments: dict[str, Any] = {}
    for name, (address, expected_hex) in MACHINE_FRAGMENTS.items():
        expected = bytes.fromhex(expected_hex)
        actual = image.read(address, len(expected))
        if actual != expected:
            raise ValueError(
                f"{name} bytes drift at 0x{address:08x}: expected={expected_hex} actual={actual.hex()}"
            )
        fragments[name] = {
            "address": f"0x{address:08x}",
            "bytes": expected_hex,
            "verified": True,
        }

    writer_raw = image.read(WRITER, 69)
    if hashlib.sha256(writer_raw).hexdigest() != WRITER_RAW_SHA256:
        raise ValueError("FUN_0070f170 raw function bytes drift")
    constant_30 = struct.unpack("<d", image.read(0x00AB2000, 8))[0]
    if constant_30 != 30.0:
        raise ValueError(f"writer divisor constant drift: {constant_30!r}")

    functions = _function_index(_read_jsonl(functions_path))
    writer_function = _validate_function(
        functions, WRITER, WRITER_NAME, WRITER_MNEMONIC_SHA256
    )
    constructor_function = _validate_function(
        functions, CONSTRUCTOR, CONSTRUCTOR_NAME, CONSTRUCTOR_MNEMONIC_SHA256
    )
    mutator_function = _validate_function(
        functions, ACCESSOR_MUTATOR, ACCESSOR_MUTATOR_NAME, ACCESSOR_MUTATOR_MNEMONIC_SHA256
    )
    if writer_function.get("calling_convention") != "__thiscall":
        raise ValueError("FUN_0070f170 calling convention drift")
    parameters = writer_function.get("parameters")
    if not isinstance(parameters, list) or len(parameters) != 2:
        raise ValueError("FUN_0070f170 physical parameter surface drift")
    if parameters[0].get("storage") != "ECX:4 (auto)" or parameters[1].get("storage") != "Stack[0x4]:4":
        raise ValueError("FUN_0070f170 physical parameter storage drift")

    callers = _direct_callers(_read_jsonl(callgraph_path))
    decompiler = _validate_decompiler(decompiler_path.read_text(encoding="utf-8", errors="strict"))
    owner = _validate_owner(owner_path)

    return {
        "format": FORMAT,
        "ready": True,
        "status": "cPhysicsManager-plus-0x388-writer-and-initial-value-proven",
        "retail_image": {
            "program": "SHIFT.exe",
            "md5": md5,
            "sha256": sha256,
            "image_base": f"0x{image.image_base:08x}",
        },
        "source_backed_object_join": owner,
        "writer": {
            "function": WRITER_NAME,
            "address": f"0x{WRITER:08x}",
            "calling_convention": writer_function["calling_convention"],
            "parameters": parameters,
            "mnemonic_sha256": WRITER_MNEMONIC_SHA256,
            "raw_function_sha256": WRITER_RAW_SHA256,
            "direct_integer_value_dependency": {
                "source": "Stack[0x4]:4 param_1",
                "source_load_instruction": "0x0070f176",
                "store_instruction": "0x0070f179",
                "receiver": "ECX",
                "displacement": RATE_OFFSET,
                "displacement_hex": "0x388",
                "proven": True,
            },
            "derived_fields": {
                "plus_0x38c": "1.0 / float(param_1)",
                "plus_0x390": "float(param_1) / 30.0",
                "plus_0x394": "1.0 / (float(param_1) / 30.0)",
                "constant_30_address": "0x00ab2000",
                "constant_30_value": constant_30,
                "machine_relationships_proven": True,
            },
        },
        "machine_fragments": fragments,
        "constructor_receiver_join": {
            "function": CONSTRUCTOR_NAME,
            "address": f"0x{CONSTRUCTOR:08x}",
            "mnemonic_sha256": constructor_function["mnemonic_sha256"],
            "source_receiver_saved_to_ESI": "0x0070fafd",
            "source_backed_vtable_installed_on_ESI": "0x0070fb13",
            "vtable": f"0x{MANAGER_VTABLE:08x}",
            "initial_value_push": "0x0070fc3d",
            "initial_value": INITIAL_RATE,
            "writer_receiver_restored_from_ESI": "0x0070fc60",
            "writer_call": "0x0070fc68",
            "decompiler_same_receiver_call": "FUN_0070f170(param_1,0xb4)",
            "cPhysicsManager_receiver_to_writer_proven": True,
        },
        "accessor_receiver_join": {
            "function": ACCESSOR_MUTATOR_NAME,
            "address": f"0x{ACCESSOR_MUTATOR:08x}",
            "mnemonic_sha256": mutator_function["mnemonic_sha256"],
            "accessor_call": "0x00714571",
            "receiver_transfer": "0x00714576 MOV ECX,EAX",
            "writer_call": "0x00714578",
            "decompiler_accessors_then_writer": decompiler["accessor_return_flows_to_writer_receiver"],
            "accessor_return_to_writer_receiver_proven": True,
        },
        "direct_callers": callers,
        "decompiler_crosscheck": decompiler,
        "adjudication": {
            "FUN_0070f170_is_cPhysicsManager_plus_0x388_writer": True,
            "plus_0x388_stored_value_is_writer_integer_param1": True,
            "constructor_initializes_plus_0x388_to_180": True,
            "writer_derives_reciprocal_and_rate_over_30_fields": True,
            "plus_0x388_semantic_role_is_integer_step_rate_candidate": True,
            "plus_0x388_physical_units_proven": False,
            "normal_outer_quantum_proven": False,
            "retail_fixed_step_quantum_proven": False,
            "retail_cadence_admitted": False,
        },
        "blocking_reasons": [
            "rate-field-physical-time-units-not-yet-joined",
            "normal-outer-update-quantum-to-accumulator-not-yet-joined",
            "retail-fixed-step-cadence-equation-not-yet-published",
        ],
        "next_exact_question": (
            "join this proven integer rate=180 to FUN_00712450 accumulator scaling, "
            "FUN_00710780 normal outer input, and FUN_00713050 rate*accumulator / 1.0/rate "
            "loop to derive the exact retail substep cadence before changing native runtime timing"
        ),
        "limits": {
            "field_named_frequency_from_offset_only": False,
            "seconds_unit_assumed": False,
            "rendered_frame_equivalence_assumed": False,
            "host_1_60_promoted": False,
            "runtime_capture_used": False,
            "original_game_executed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("shift_exe", type=Path)
    parser.add_argument("decompiler_c", type=Path)
    parser.add_argument("functions_jsonl", type=Path)
    parser.add_argument("callgraph_jsonl", type=Path)
    parser.add_argument("physics_manager_owner", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = analyze(
        args.shift_exe,
        args.decompiler_c,
        args.functions_jsonl,
        args.callgraph_jsonl,
        args.physics_manager_owner,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"status: {report['status']}")
    print(f"ready: {str(report['ready']).lower()}")
    print(f"initial_rate: {report['constructor_receiver_join']['initial_value']}")
    print(
        "retail_cadence_admitted: "
        f"{str(report['adjudication']['retail_cadence_admitted']).lower()}"
    )
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
