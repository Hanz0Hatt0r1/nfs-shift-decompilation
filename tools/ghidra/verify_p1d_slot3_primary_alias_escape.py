#!/usr/bin/env python3
"""Verify the primary selected-wheel alias handoff around FUN_00758b50/FUN_00755950.

This is a hash-locked retail PE proof. It closes only the one-hop alias escape
from the proven primary wheel loop into FUN_00755950 and that consumer's sole
callee. It does not claim global interprocedural alias exhaustion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

FORMAT = "SHIFT.P1D.P13DSlot3PrimaryAliasEscape/1"
EXPECTED_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
IMAGE_BASE = 0x00400000

ANCHORS = {
    0x00758B98: "8bf9",                # mov edi,ecx
    0x00758BB4: "8db748080000",        # lea esi,[edi+0x848]
    0x00758BE0: "8d8fd4000000",        # lea ecx,[edi+0xd4]
    0x00758BEF: "8d4d80",              # lea ecx,[ebp-0x80]
    0x00758C19: "81c1d4000000",        # add ecx,0xd4
    0x00758C31: "8d4d80",              # lea ecx,[ebp-0x80]
    0x00758CCF: "8d8eb8fbffff",        # lea ecx,[esi-0x448]
    0x00758D7D: "81c6800a0000",        # add esi,0xa80
    0x00755956: "8bd1",                # mov edx,ecx
    0x00755958: "dd8238050000",        # fld qword [edx+0x538]
    0x00755964: "8d8a80000000",        # lea ecx,[edx+0x80]
    0x0075596A: "dd9228050000",        # fst qword [edx+0x528]
    0x00755975: "dd9230050000",        # fst qword [edx+0x530]
    0x00755988: "dd9a48050000",        # fstp qword [edx+0x548]
}

CALLS = {
    0x00758BE6: 0x007AEFB0,
    0x00758BF2: 0x00753590,
    0x00758C1F: 0x007AEFB0,
    0x00758C34: 0x00753590,
    0x00758C71: 0x00900D30,
    0x00758D6B: 0x00755950,
    0x00755983: 0x007555B0,
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def pe_sections(data: bytes) -> list[tuple[int, int, int, int]]:
    if data[:2] != b"MZ":
        raise ValueError("not a PE image")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe+4] != b"PE\0\0":
        raise ValueError("invalid PE signature")
    num = struct.unpack_from("<H", data, pe + 6)[0]
    opt_size = struct.unpack_from("<H", data, pe + 20)[0]
    sec = pe + 24 + opt_size
    rows = []
    for i in range(num):
        off = sec + i * 40
        virtual_size, virtual_address, raw_size, raw_ptr = struct.unpack_from("<IIII", data, off + 8)
        rows.append((virtual_address, max(virtual_size, raw_size), raw_ptr, raw_size))
    return rows


def read_va(data: bytes, sections: list[tuple[int, int, int, int]], va: int, size: int) -> bytes:
    rva = va - IMAGE_BASE
    for vaddr, span, raw_ptr, raw_size in sections:
        if vaddr <= rva < vaddr + span:
            delta = rva - vaddr
            if delta + size > raw_size:
                raise ValueError(f"VA 0x{va:08x} crosses raw section boundary")
            return data[raw_ptr + delta: raw_ptr + delta + size]
    raise ValueError(f"VA 0x{va:08x} not mapped")


def rel32_target(site: int, raw: bytes) -> int:
    if len(raw) != 5 or raw[0] != 0xE8:
        raise ValueError(f"0x{site:08x} is not rel32 CALL")
    disp = struct.unpack_from("<i", raw, 1)[0]
    return site + 5 + disp


def analyze(executable: Path) -> dict:
    digest = sha256(executable)
    if digest != EXPECTED_SHA256:
        raise ValueError(f"unexpected retail PE SHA-256: {digest}")
    data = executable.read_bytes()
    sections = pe_sections(data)

    verified_anchors = []
    for va, hex_bytes in ANCHORS.items():
        expected = bytes.fromhex(hex_bytes)
        actual = read_va(data, sections, va, len(expected))
        if actual != expected:
            raise ValueError(f"anchor drift at 0x{va:08x}: {actual.hex()} != {hex_bytes}")
        verified_anchors.append({"address": f"0x{va:08x}", "bytes": hex_bytes})

    verified_calls = []
    for site, target in CALLS.items():
        raw = read_va(data, sections, site, 5)
        actual_target = rel32_target(site, raw)
        if actual_target != target:
            raise ValueError(f"call target drift at 0x{site:08x}: 0x{actual_target:08x}")
        verified_calls.append({"site": f"0x{site:08x}", "target": f"0x{target:08x}", "bytes": raw.hex()})

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": digest,
            "machine_bytes_adjudicate": True,
        },
        "primary_loop": {
            "function": "FUN_00758b50",
            "vehicle_root_capture": "0x00758b98 EDI=entry ECX=HDVehicle",
            "loop_seed": "0x00758bb4 ESI=HDVehicle+0x848",
            "loop_stride": "0x00758d7d ESI+=0xa80",
            "selected_wheel_materialization": "0x00758ccf ECX=ESI-0x448=HDVehicle+0x400+slot*0xa80",
            "selected_wheel_direct_call": "0x00758d6b -> FUN_00755950",
            "other_direct_calls_in_per_wheel_body": [
                {"site": "0x00758be6", "target": "FUN_007aefb0", "receiver": "external/body object +0xd4, not wheel root"},
                {"site": "0x00758bf2", "target": "FUN_00753590", "receiver": "stack local EBP-0x80"},
                {"site": "0x00758c1f", "target": "FUN_007aefb0", "receiver": "[HDVehicle+0x33a0]+0xd4"},
                {"site": "0x00758c34", "target": "FUN_00753590", "receiver": "stack local EBP-0x80"},
                {"site": "0x00758c71", "target": "__CIsqrt", "receiver": "not a thiscall wheel receiver"}
            ],
            "exact_selected_wheel_root_forwarded_to_other_direct_callee": False,
        },
        "consumer": {
            "function": "FUN_00755950",
            "entry_root_copy": "0x00755956 EDX=ECX",
            "target_read": "0x00755958 fld qword [EDX+0x538]",
            "direct_writes": [
                "0x0075596a qword [EDX+0x528]",
                "0x00755975 qword [EDX+0x530]",
                "0x00755988 qword [EDX+0x548]"
            ],
            "writes_overlap_target_0x538_0x53f": False,
            "only_direct_callee": "0x00755983 -> FUN_007555b0",
            "callee_receiver": "0x00755964 ECX=EDX+0x80",
            "exact_wheel_root_forwarded_to_callee": False,
        },
        "machine_anchors": {
            "byte_windows": verified_anchors,
            "rel32_calls": verified_calls,
        },
        "adjudication": {
            "primary_loop_exact_wheel_root_one_hop_forwarding_complete": True,
            "primary_loop_exact_wheel_root_only_direct_target_is_FUN_00755950": True,
            "FUN_00755950_target_field_is_read_only": True,
            "FUN_00755950_exact_wheel_root_does_not_escape_to_direct_callee": True,
            "global_interprocedural_wheel_alias_surface_complete": False,
            "escaped_alias_store_surface_complete": False,
            "slot3_writer_provenance_proven": False,
            "p1_3d_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only direct one-hop forwarding from the primary FUN_00758b50 per-wheel loop and FUN_00755950 itself.",
            "Other lifecycle functions, indirect calls, stored aliases and callbacks remain outside this proof.",
            "The target +0x538 field is proven read-only only within FUN_00755950, not globally."
        ],
        "next_step": "Trace selected-wheel aliases emitted by other proven lifecycle functions or stored/escaped before calls; keep indirect/callback and custom copy/init carriers fail-closed."
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("executable", type=Path)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    try:
        payload = analyze(a.executable)
    except ValueError as exc:
        p.error(str(exc))
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if a.output:
        a.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
