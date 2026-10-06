#!/usr/bin/env python3
"""Materialize the selected fresh-primary BMW InitVehicle render-root delta.

This proof is deliberately scoped to the native Silverstone+BMW vertical-slice
session policy: one fresh process bootstrap, one selected BMW participant, and
retail role/index 0 (the role that FUN_0074ddc3 promotes to DAT_00c10b30/34).
It proves only the three numeric FUN_00795d60 delta fields.  It does not infer a
retail-session default and it does not promote the outer->VHF numeric matrix.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.BMWRenderRootDeltaNativeSession/1"
DB_FORMAT = "SHIFT.GhidraEvidenceDatabase/1"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
SESSION = "Silverstone+BMW_M3_E36"
ROLE = 0
DELTA_OFFSETS = ["+0x19c", "+0x1a0", "+0x1a4"]
GLOBAL_TRIPLE = [0x00C16AB0, 0x00C16AB8, 0x00C16AC0]
GLOBAL_WRITER = "0x0078ef00"
GLOBAL_WRITER_CALLERS = {"0x0074bfd0", "0x00794a30", "0x0079b2d0"}

EXPECTED_FUNCTIONS: dict[str, tuple[str, int, str, str]] = {
    "FUN_007125e0": ("0x007125e0", 185, "__fastcall", "d0d7c65693b7f3ef34ea399789518ef8c2aee61543bfe0473ddad54f4333adf0"),
    "FUN_00715240": ("0x00715240", 308, "__fastcall", "3fd2dd8c13015fa5e6e0e7e9927e093b1eb7538869da1bac90ab282b3c726afe"),
    "FUN_0072ed20": ("0x0072ed20", 1161, "__fastcall", "d6eb0ccddc64f5df669ab82e905efdfb9484f70d4201110e8eb35148f19908ff"),
    "FUN_0041cbd6": ("0x0041cbd6", 13, "__fastcall", "eca43ac3f961bbe0811d2c3ea872a468a21834465ccb2a65e4280980c27ee16a"),
    "FUN_0074ddb0": ("0x0074ddb0", 18, "__fastcall", "bc9744e48161533bacc2815fa9ea9b95e475153aabc6c6d8fc796d9709df7e81"),
    "FUN_0074ddc3": ("0x0074ddc3", 957, "__fastcall", "1b8f7a6602190fdd97b5a3d410495c8ff92b3a8b854a703459427b1ff548e4a6"),
    "FUN_0074e1a0": ("0x0074e1a0", 411, "__fastcall", "1d8bc5a41a02dc21368f0be8e6ff7a482dd5d11bfe0607b54d0cea1ca3e9f003"),
    "FUN_0078ef00": ("0x0078ef00", 1538, "__fastcall", "f981daa8164768121875faef1a053d93a6f78e6a3901a73aa32904b875ddb8e1"),
    "FUN_00795d60": ("0x00795d60", 8797, "__fastcall", "c587cae5d3d8f99afed40fe0c059c8c60bc9cc45d9ee644f5e90e2e1f5a8eb14"),
    "FUN_00797fd0": ("0x00797fd0", 612, "__thiscall", "b8f3cb6525e0742e2afefd31ca51dd050a9d869444526ce03df41067ecb3eeb8"),
    "FUN_00798df0": ("0x00798df0", 1581, "__thiscall", "88904019443d1ea4edaf5a3ef40dd5abfe9e28109ab0b1f09296388f36026e16"),
    "FUN_0079bfd0": ("0x0079bfd0", 445, "__fastcall", "06e730897a4a85d93a5f33765fd15b0c52708fb2c864c290804024b109a3d950"),
    "FUN_0079c1c0": ("0x0079c1c0", 497, "__fastcall", "6759f1781d58bf38b72e2fa45ab24fc12bccf46bde95d90c4c57e2a0d600c39c"),
}

REQUIRED_EDGES = {
    ("0x007125e0", "0x0072ed20"),
    ("0x0072ed20", "0x0079c1c0"),
    ("0x00715240", "0x007125e0"),
    ("0x00715240", "0x0074e1a0"),
    ("0x0074e1a0", "0x0074ddb0"),
    ("0x0074ddb0", "0x0041cbd6"),
    ("0x0041cbd6", "0x0074ddc3"),
    ("0x0074ddc3", "0x00797fd0"),
    ("0x0074ddc3", "0x00798df0"),
    ("0x00798df0", "0x00795d60"),
    ("0x0078ef00", "0x007afd20"),
}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def _function_map(path: Path) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for row in _iter_jsonl(path):
        name = str(row.get("name") or "")
        if name in EXPECTED_FUNCTIONS:
            result[name] = row
    return result


def _validate_functions(path: Path) -> dict[str, dict[str, Any]]:
    rows = _function_map(path)
    missing = sorted(set(EXPECTED_FUNCTIONS) - set(rows))
    if missing:
        raise ValueError(f"missing retail functions: {', '.join(missing)}")
    out: dict[str, dict[str, Any]] = {}
    for name, (address, size, cc, fingerprint) in EXPECTED_FUNCTIONS.items():
        row = rows[name]
        if str(row.get("address")).lower() != address:
            raise ValueError(f"{name}: address drift")
        if int(row.get("size", -1)) != size:
            raise ValueError(f"{name}: size drift")
        if row.get("calling_convention") != cc:
            raise ValueError(f"{name}: calling convention drift")
        if row.get("mnemonic_sha256") != fingerprint:
            raise ValueError(f"{name}: mnemonic fingerprint drift")
        out[name] = {"address": address, "size": size, "calling_convention": cc, "mnemonic_sha256": fingerprint}
    return out


def _validate_callgraph(path: Path) -> dict[str, Any]:
    edges: set[tuple[str, str]] = set()
    writer_callers: set[str] = set()
    for row in _iter_jsonl(path):
        src = str(row.get("from_function") or "").lower()
        dst = str(row.get("to") or "").lower()
        if src and dst and row.get("indirect") is not True:
            edges.add((src, dst))
            if dst == GLOBAL_WRITER:
                writer_callers.add(src)
    missing = sorted(REQUIRED_EDGES - edges)
    if missing:
        raise ValueError(f"required lifecycle/callgraph edges missing: {missing}")
    if writer_callers != GLOBAL_WRITER_CALLERS:
        raise ValueError(f"FUN_0078ef00 direct-caller set drift: {sorted(writer_callers)}")
    pre_init = {
        "0x007125e0", "0x00715240", "0x0072ed20", "0x0041cbd6",
        "0x0074ddb0", "0x0074ddc3", "0x0074e1a0", "0x00797fd0", "0x00798df0",
    }
    if writer_callers & pre_init:
        raise ValueError("global render-origin writer appears in pre-InitVehicle chain")
    return {
        "required_edges_ready": True,
        "global_writer": GLOBAL_WRITER,
        "global_writer_direct_callers": sorted(writer_callers),
        "pre_InitVehicle_chain_contains_global_writer": False,
    }


def _function_text(source: str, name: str) -> str:
    marker = name + "("
    search_from = 0
    pos = -1
    start = -1
    while True:
        candidate = source.find(marker, search_from)
        if candidate < 0:
            break
        line_start = source.rfind("\n", 0, candidate) + 1
        # Ghidra top-level definitions start at column zero; ordinary calls are indented.
        if line_start < len(source) and not source[line_start].isspace():
            pos = candidate
            start = line_start
            break
        search_from = candidate + len(marker)
    if pos < 0:
        raise ValueError(f"decompile definition missing {name}")
    brace = source.find("{", pos)
    semicolon = source.find(";", pos, brace if brace >= 0 else len(source))
    if brace < 0 or semicolon >= 0:
        raise ValueError(f"decompile malformed {name}")
    depth = 0
    for i in range(brace, len(source)):
        c = source[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
    raise ValueError(f"decompile unterminated {name}")


def _require_patterns(text: str, patterns: list[str], label: str) -> None:
    for pattern in patterns:
        if re.search(pattern, text, re.S) is None:
            raise ValueError(f"{label}: required source pattern missing: {pattern}")


def _validate_source(path: Path) -> dict[str, Any]:
    source = path.read_text(encoding="utf-8", errors="replace")
    ctor = _function_text(source, "FUN_0079bfd0")
    restart = _function_text(source, "FUN_0074ddc3")
    setter = _function_text(source, "FUN_00797fd0")
    init = _function_text(source, "FUN_00798df0")
    producer = _function_text(source, "FUN_00795d60")
    manager = _function_text(source, "FUN_00715240")
    writer = _function_text(source, "FUN_0078ef00")

    _require_patterns(ctor, [
        r"param_1\[0x67\]\s*=\s*0;",
        r"param_1\[0x68\]\s*=\s*0;",
        r"param_1\[0x69\]\s*=\s*0;",
    ], "Vehicle base constructor")
    _require_patterns(setter, [r"0x234\)\s*=\s*param_1;"], "FUN_00797fd0 role setter")
    _require_patterns(restart, [
        r"FUN_00797fd0\([^;]+\*\(int \*\)\(iVar1 \+ 0x10\)[^;]+;",
        r"if\s*\(\*\(int \*\)\(iVar1 \+ 0x10\)\s*==\s*0\)\s*\{[^}]*DAT_00c10b34\s*=",
        r"FUN_00798df0\(",
    ], "Restart primary-role chain")
    _require_patterns(init, [r"FUN_00795d60\(this,param_1,local_2390,\*\(void \*\*\)\(\(int\)this \+ 0x1d00\),param_1\);"], "InitVehicle producer call")
    _require_patterns(producer, [
        r"if\s*\(\*\(int \*\)\(\(int\)param_1 \+ 0x234\)\s*==\s*0\)\s*\{",
        r"local_3c\s*=\s*local_28\s*-\s*\(float\)_DAT_00c16ab0;",
        r"local_38\s*=\s*\*\(float \*\)\(\(int\)param_1 \+ 0x1a0\)\s*-\s*\(float\)_DAT_00c16ab8;",
        r"local_34\s*=\s*\*\(float \*\)\(\(int\)param_1 \+ 0x1a4\)\s*-\s*\(float\)_DAT_00c16ac0;",
        r"\+ 0x19c\)\s*=\s*local_3c;",
        r"\+ 0x1a0\)\s*=\s*local_38;",
        r"\+ 0x1a4\)\s*=\s*local_34;",
    ], "FUN_00795d60 primary-role override")
    _require_patterns(manager, [r"FUN_007125e0\(piVar5\);\s*FUN_0074e1a0\(piVar5\);"], "manager fresh construction order")
    _require_patterns(writer, [r"FUN_007afd20\([^;]+\(double \*\)&DAT_00c16ab0[^;]+;"], "global render-origin writer")
    return {
        "constructor_zero_offsets": DELTA_OFFSETS,
        "role_storage_offset": "+0x234",
        "restart_role_source": "RestartInfo+0x10",
        "role_zero_promotes_primary_slot": "DAT_00c10b30/DAT_00c10b34",
        "primary_override_formula": [
            "delta.x = old_delta.x - DAT_00c16ab0",
            "delta.y = old_delta.y - DAT_00c16ab8",
            "delta.z = old_delta.z - DAT_00c16ac0",
        ],
        "fresh_construct_before_restart": True,
    }


def _pe_zero_fill(path: Path, addresses: list[int]) -> dict[str, Any]:
    data = path.read_bytes()
    if hashlib.md5(data).hexdigest() != PE_MD5:
        raise ValueError("retail SHIFT.exe MD5 drift")
    if len(data) < 0x100 or data[:2] != b"MZ":
        raise ValueError("not a PE image")
    peoff = struct.unpack_from("<I", data, 0x3C)[0]
    if data[peoff:peoff + 4] != b"PE\0\0":
        raise ValueError("PE signature missing")
    _, nsects, _, _, _, opt_size, _ = struct.unpack_from("<HHIIIHH", data, peoff + 4)
    opt = peoff + 24
    magic = struct.unpack_from("<H", data, opt)[0]
    if magic != 0x10B:
        raise ValueError("expected 32-bit PE32 retail image")
    image_base = struct.unpack_from("<I", data, opt + 28)[0]
    sectoff = opt + opt_size
    sections = []
    for index in range(nsects):
        off = sectoff + index * 40
        name = data[off:off + 8].rstrip(b"\0").decode("ascii", "replace")
        virtual_size, virtual_address, raw_size, raw_ptr = struct.unpack_from("<IIII", data, off + 8)
        sections.append((name, virtual_size, virtual_address, raw_size, raw_ptr))
    proof = []
    for va in addresses:
        rva = va - image_base
        found = None
        for name, virtual_size, virtual_address, raw_size, raw_ptr in sections:
            if virtual_address <= rva < virtual_address + virtual_size:
                delta = rva - virtual_address
                found = (name, virtual_size, virtual_address, raw_size, raw_ptr, delta)
                break
        if found is None:
            raise ValueError(f"global {va:#x} is outside PE sections")
        name, virtual_size, virtual_address, raw_size, raw_ptr, delta = found
        if name != ".data" or delta < raw_size:
            raise ValueError(f"global {va:#x} is not in .data zero-fill tail")
        proof.append({
            "address": f"0x{va:08x}",
            "section": name,
            "section_rva": f"0x{virtual_address:x}",
            "virtual_size": virtual_size,
            "raw_size": raw_size,
            "offset_within_section": delta,
            "initial_value": 0.0,
            "provenance": "PE loader zero-fill beyond SizeOfRawData and within VirtualSize",
        })
    return {"md5": PE_MD5, "image_base": f"0x{image_base:08x}", "zero_fill_globals": proof}


def analyze(db: Path, source_c: Path, pe_image: Path, *, role_index: int, fresh_process_bootstrap: bool, session_target: str) -> dict[str, Any]:
    manifest = _load_json(db / "manifest.json")
    binary = _load_json(db / "binary.json")
    if manifest.get("format") != DB_FORMAT or manifest.get("program") != PROGRAM:
        raise ValueError("Ghidra manifest identity drift")
    if binary.get("format") != DB_FORMAT or binary.get("program_name") != PROGRAM or binary.get("executable_md5") != PE_MD5:
        raise ValueError("Ghidra binary identity drift")
    if role_index != ROLE:
        raise ValueError("this proof only admits explicit native primary role/index 0")
    if not fresh_process_bootstrap:
        raise ValueError("fresh process bootstrap is required; restart/reuse is not proven numeric here")
    if str(session_target).strip() != SESSION:
        raise ValueError(f"session_target must be exactly {SESSION}")

    functions = _validate_functions(db / "functions.jsonl")
    callgraph = _validate_callgraph(db / "callgraph.jsonl")
    source = _validate_source(source_c)
    pe = _pe_zero_fill(pe_image, GLOBAL_TRIPLE)

    delta = [0.0, 0.0, 0.0]
    return {
        "format": FORMAT,
        "version": 1,
        "status": "selected-bmw-fresh-primary-render-root-delta-materialized",
        "ready": True,
        "BLOCKER": "BMW-render-root-delta-numeric-materialization",
        "INPUT": {
            "retail_program": PROGRAM,
            "retail_md5": PE_MD5,
            "ghidra_database": DB_FORMAT,
            "session_target": SESSION,
            "native_policy": {
                "fresh_process_bootstrap": True,
                "restart_role_index": ROLE,
                "source": "explicit-native-vertical-slice-policy",
                "retail_live_session_default_inferred": False,
            },
        },
        "OUTPUT": "exact selected-session numeric outerVehicle +0x19c/+0x1a0/+0x1a4",
        "CONSUMER": "S2 finite M_outer_to_vhf_root evaluation, then S3 SHIFT.BMWBody0BindFrameProof/1",
        "subject": {"vehicle": "BMW_M3_E36", "session_target": SESSION},
        "delta_local": {
            "offsets": DELTA_OFFSETS,
            "values_xyz": delta,
            "producer": "FUN_00795d60",
            "branch": "outerVehicle+0x234 == 0",
            "role_index": ROLE,
            "formula": "constructor_zero_delta - process-start-zero global render-origin triple",
        },
        "provenance": {
            "functions": functions,
            "source_witness": source,
            "callgraph": callgraph,
            "pe_image": pe,
            "ordering": [
                "FUN_007125e0 owner allocation/construction",
                "FUN_0072ed20 -> FUN_0079c1c0 -> FUN_0079bfd0 zeros delta",
                "FUN_0074e1a0 -> FUN_0074ddb0 -> FUN_0041cbd6 -> FUN_0074ddc3 Restart",
                "FUN_00797fd0 stores explicit role 0 at Vehicle+0x234 and promotes primary slot",
                "FUN_00798df0 Vehicle::InitVehicle -> FUN_00795d60",
                "FUN_00795d60 primary-role override evaluates 0 - 0 for all three components",
            ],
        },
        "handoff": {
            "selected_BMW_render_root_delta_numeric_ready": True,
            "outer_vehicle_root_to_VHF_relation_numeric_matrix_ready": False,
            "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "limits": {
            "scope_is_fresh_process_first_primary_participant": True,
            "restart_after_runtime_global_origin_updates_proven": False,
            "nonzero_restart_role_proven_numeric": False,
            "retail_live_session_role_default_inferred": False,
            "native_policy_is_retail_session_observation": False,
            "geometry_branch_values_used": False,
            "runtime_capture_used": False,
            "original_game_executed": False,
            "outer_to_vhf_numeric_matrix_preclaimed": False,
        },
        "NEXT_STEP": "consume exact BMW VHF root matrix and evaluate finite M_outer_to_vhf_root under SHIFT.OuterVehicleBMWVHFRootRelation/1",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("source_c", type=Path)
    parser.add_argument("pe_image", type=Path)
    parser.add_argument("--role-index", type=int, required=True)
    parser.add_argument("--fresh-process-bootstrap", action="store_true")
    parser.add_argument("--session-target", default=SESSION)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    report = analyze(
        args.ghidra_export,
        args.source_c,
        args.pe_image,
        role_index=args.role_index,
        fresh_process_bootstrap=args.fresh_process_bootstrap,
        session_target=args.session_target,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
