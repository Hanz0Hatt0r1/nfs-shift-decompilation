#!/usr/bin/env python3
"""Verify exact arguments of all direct worker-reachable loader calls.

The callsite set comes from the merged Controller #1 loader-reachability frontier.
This verifier uses authoritative retail PE bytes only. It closes the direct
literal/NULL loader-argument sub-surface, not indirect/manual/native resolution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

FORMAT = "SHIFT.P1D.Controller1LoaderArgumentFlow/1"
EXPECTED_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
IMAGE_BASE = 0x00400000

LITERALS = {
    0x00B36D0C: "mscoree.dll",
    0x00B384CC: "KERNEL32.DLL",
    0x00B41740: "kernel32.dll",
    0x00B42154: "USER32.DLL",
    0x00B384B4: ".mixcrt",
}

ANCHORS = {
    0x0090748B: "680c6db300",
    0x00907490: "ff15d061aa00",
    0x0090A9C8: "33db",
    0x0090A9E2: "53",
    0x0090A9E3: "ff15d061aa00",
    0x0090A9E9: "8b703c",
    0x0090A9F2: "0fb74614",
    0x0090A9F6: "8d7c3018",
    0x0090A9FD: "68b484b300",
    0x0090AA12: "83c728",
    0x0090AA5B: "68cc84b300",
    0x0090AA60: "ff15d061aa00",
    0x0090AAD2: "68cc84b300",
    0x0090AAD7: "ff15d061aa00",
    0x0090ABC4: "68cc84b300",
    0x0090ABC9: "ff15d061aa00",
    0x00918A11: "684017b400",
    0x00918A16: "ff15d061aa00",
    0x0091C09B: "685421b400",
    0x0091C0A0: "ff150063aa00",
}

CALLS = [
    {"function": "FUN_0090748b", "callsite": "0x00907490", "api": "GetModuleHandleA", "argument_kind": "literal", "argument": "mscoree.dll", "argument_address": "0x00b36d0c"},
    {"function": "FUN_0090a9bb", "callsite": "0x0090a9e3", "api": "GetModuleHandleA", "argument_kind": "null-current-module", "argument": None, "argument_address": None},
    {"function": "FUN_0090aa27", "callsite": "0x0090aa60", "api": "GetModuleHandleA", "argument_kind": "literal", "argument": "KERNEL32.DLL", "argument_address": "0x00b384cc"},
    {"function": "FUN_0090aa9e", "callsite": "0x0090aad7", "api": "GetModuleHandleA", "argument_kind": "literal", "argument": "KERNEL32.DLL", "argument_address": "0x00b384cc"},
    {"function": "FUN_0090abb8", "callsite": "0x0090abc9", "api": "GetModuleHandleA", "argument_kind": "literal", "argument": "KERNEL32.DLL", "argument_address": "0x00b384cc"},
    {"function": "___crtInitCritSecAndSpinCount", "callsite": "0x00918a16", "api": "GetModuleHandleA", "argument_kind": "literal", "argument": "kernel32.dll", "argument_address": "0x00b41740"},
    {"function": "FUN_0091c073", "callsite": "0x0091c0a0", "api": "LoadLibraryA", "argument_kind": "literal", "argument": "USER32.DLL", "argument_address": "0x00b42154"},
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sections(data: bytes):
    if data[:2] != b"MZ":
        raise ValueError("not a PE image")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("invalid PE signature")
    count = struct.unpack_from("<H", data, pe + 6)[0]
    opt_size = struct.unpack_from("<H", data, pe + 20)[0]
    table = pe + 24 + opt_size
    out = []
    for i in range(count):
        off = table + i * 40
        virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from("<IIII", data, off + 8)
        out.append((virtual_address, max(virtual_size, raw_size), raw_pointer, raw_size))
    return out


def va_offset(data: bytes, mapped, va: int) -> int:
    rva = va - IMAGE_BASE
    for base, span, raw_pointer, raw_size in mapped:
        if base <= rva < base + span:
            delta = rva - base
            if delta >= raw_size:
                raise ValueError(f"VA 0x{va:08x} has no raw bytes")
            return raw_pointer + delta
    raise ValueError(f"VA 0x{va:08x} is not mapped")


def read_va(data: bytes, mapped, va: int, size: int) -> bytes:
    off = va_offset(data, mapped, va)
    return data[off:off + size]


def read_c_string(data: bytes, mapped, va: int, limit: int = 128) -> str:
    off = va_offset(data, mapped, va)
    end = data.find(b"\0", off, off + limit)
    if end < 0:
        raise ValueError(f"unterminated string at 0x{va:08x}")
    return data[off:end].decode("ascii")


def analyze(executable: Path) -> dict:
    digest = sha256(executable)
    if digest != EXPECTED_SHA256:
        raise ValueError(f"unexpected retail PE SHA-256: {digest}")
    data = executable.read_bytes()
    mapped = sections(data)

    verified_anchors = []
    for va, hex_bytes in ANCHORS.items():
        expected = bytes.fromhex(hex_bytes)
        actual = read_va(data, mapped, va, len(expected))
        if actual != expected:
            raise ValueError(f"machine drift at 0x{va:08x}: {actual.hex()} != {hex_bytes}")
        verified_anchors.append({"address": f"0x{va:08x}", "bytes": hex_bytes})

    verified_literals = []
    for va, expected in LITERALS.items():
        actual = read_c_string(data, mapped, va)
        if actual != expected:
            raise ValueError(f"string drift at 0x{va:08x}: {actual!r} != {expected!r}")
        verified_literals.append({"address": f"0x{va:08x}", "value": expected})

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
        "surface": {
            "worker_reachable_direct_loader_call_count": 7,
            "calls": CALLS,
            "literal_module_argument_count": 6,
            "null_current_module_argument_count": 1,
        },
        "current_module_pe_walk": {
            "function": "FUN_0090a9bb",
            "loader_call": "0x0090a9e3 GetModuleHandleA(NULL)",
            "null_proof": "0x0090a9c8 xor ebx,ebx; 0x0090a9e2 push ebx",
            "e_lfanew_read": "0x0090a9e9 mov esi,[eax+0x3c]",
            "section_count_read": "0x0090a9ee cmp word [esi+0x6],bx",
            "optional_header_size_read": "0x0090a9f2 movzx eax,word [esi+0x14]",
            "first_section_materialization": "0x0090a9f6 lea edi,[eax+esi+0x18]",
            "section_name": ".mixcrt",
            "section_name_push": "0x0090a9fd push 0x00b384b4",
            "section_stride": "0x0090aa12 add edi,0x28",
            "export_directory_0x78_access_present": False,
            "role": "current-module section-table lookup, not PE export-directory resolution",
        },
        "machine_anchors": {
            "byte_windows": verified_anchors,
            "literal_strings": verified_literals,
        },
        "adjudication": {
            "all_worker_reachable_direct_loader_arguments_proven": True,
            "direct_loader_literal_or_null_surface_complete": True,
            "current_module_section_walk_is_export_resolver": False,
            "direct_loader_argument_surface_supports_apc_resolution": False,
            "indirect_loader_calls_ruled_out": False,
            "nonliteral_generated_module_names_ruled_out": False,
            "manual_export_walking_overall_ruled_out": False,
            "native_or_syscall_apc_injection_ruled_out": False,
            "controller1_thread_handle_join_complete": False,
            "controller1_timing_exhaustive": False,
            "p1_3d_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "Only the seven already-proven direct worker-reachable GetModuleHandleA/LoadLibraryA callsites are covered.",
            "Indirect loader calls, generated/nonliteral module names, alternate module-base acquisition and manual export walking outside these callsites remain open.",
            "The GetProcAddress target-name surface is governed by the separate merged direct argument-flow proof.",
            "No result changes Controller #1 target-thread identity or timing-exhaustiveness gates."
        ],
        "next_step": "Continue indirect/manual/native resolution and target-thread identity. The direct loader + direct named GetProcAddress path is now exact and non-APC."
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
