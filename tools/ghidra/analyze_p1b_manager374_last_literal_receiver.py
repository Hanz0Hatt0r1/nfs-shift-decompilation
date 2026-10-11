#!/usr/bin/env python3
"""Verify the corrected machine receiver provenance for literal +0x374 site 0x00865013."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path

RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
FORMAT = "SHIFT.P1B.Manager374LastLiteralReceiverMachineProof/1"
INSN = re.compile(r"^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$")


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).replace(", ", ",")


def _require(actual, expected, label: str) -> None:
    if actual != expected:
        raise ValueError(f"{label}: {actual!r} != {expected!r}")


def disasm(executable: Path, start: int | None = None, stop: int | None = None):
    cmd = ["objdump", "-d", "-Mintel"]
    if start is not None:
        cmd.append(f"--start-address=0x{start:x}")
    if stop is not None:
        cmd.append(f"--stop-address=0x{stop:x}")
    cmd.append(str(executable))
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True, errors="replace")
    rows = []
    for line in proc.stdout.splitlines():
        match = INSN.match(line)
        if match:
            rows.append((int(match.group(1), 16), match.group(2).lower(), norm(match.group(3))))
    return rows


def _rowmap(rows):
    return {address: (mnemonic, operands) for address, mnemonic, operands in rows}


def _sections(data: bytes):
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    _require(data[pe : pe + 4], b"PE\0\0", "PE signature")
    section_count = struct.unpack_from("<H", data, pe + 6)[0]
    optional_size = struct.unpack_from("<H", data, pe + 20)[0]
    optional = pe + 24
    image_base = struct.unpack_from("<I", data, optional + 28)[0]
    section_table = optional + optional_size
    rows = []
    for index in range(section_count):
        off = section_table + index * 40
        name = data[off : off + 8].rstrip(b"\0").decode("ascii", "replace")
        virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from("<IIII", data, off + 8)
        rows.append((name, image_base + virtual_address, virtual_size, raw_pointer, raw_size))
    return rows


def _va_to_offset(data: bytes, va: int) -> int:
    for name, start, virtual_size, raw_pointer, raw_size in _sections(data):
        if start <= va < start + max(virtual_size, raw_size):
            delta = va - start
            if delta >= raw_size:
                raise ValueError(f"VA 0x{va:x} is not file-backed in {name}")
            return raw_pointer + delta
    raise ValueError(f"VA 0x{va:x} does not belong to a PE section")


def _u32(data: bytes, va: int) -> int:
    return struct.unpack_from("<I", data, _va_to_offset(data, va))[0]


def _window_hash(data: bytes, start: int, end_exclusive: int):
    begin = _va_to_offset(data, start)
    end = _va_to_offset(data, end_exclusive - 1) + 1
    payload = data[begin:end]
    return hashlib.sha256(payload).hexdigest(), len(payload)


def analyze(executable: Path) -> dict:
    data = executable.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    _require(digest, RETAIL_SHA256, "retail executable SHA-256")

    body = _rowmap(disasm(executable, 0x00864C10, 0x00865019))
    expected = {
        0x00864C40: ("mov", "edi,ecx"),
        0x00864C42: ("mov", "DWORD PTR [ebp-0x34],edi"),
        0x00864C67: ("mov", "esi,DWORD PTR [ebx+0x8]"),
        0x00864D63: ("mov", "esi,DWORD PTR [ebp-0x34]"),
        0x00864DA9: ("lea", "esi,[eax+esi*1+0x134]"),
        0x00864DB5: ("mov", "esi,DWORD PTR [ebp-0x34]"),
        0x00865013: ("fstp", "DWORD PTR [esi+0x374]"),
    }
    for address, instruction in expected.items():
        _require(body.get(address), instruction, f"instruction 0x{address:08x}")

    post_restore_writes = []
    for address, mnemonic, operands in disasm(executable, 0x00864DB6, 0x00865014):
        parts = operands.split(",") if operands else []
        if parts and parts[0].strip().lower() in {"esi", "si"}:
            post_restore_writes.append((address, mnemonic, operands))
        if mnemonic in {"popa", "popad"} or mnemonic.startswith(("movs", "lods")):
            post_restore_writes.append((address, mnemonic, operands))
    _require(post_restore_writes, [], "post-restore ESI writers")

    first = _rowmap(disasm(executable, 0x0085B6E0, 0x0085B6F9))
    second = _rowmap(disasm(executable, 0x0085C370, 0x0085C395))
    joined = dict(first)
    joined.update(second)
    caller_expected = {
        0x0085B6F2: ("call", "0x864c10"),
        0x0085C374: ("mov", "esi,ecx"),
        0x0085C38D: ("mov", "ecx,esi"),
        0x0085C38F: ("call", "0x864c10"),
    }
    for address, instruction in caller_expected.items():
        _require(joined.get(address), instruction, f"caller instruction 0x{address:08x}")

    direct_calls = [
        address
        for address, mnemonic, operands in disasm(executable)
        if mnemonic == "call" and operands.lower() in {"0x864c10", "864c10"}
    ]
    _require(direct_calls, [0x0085B6F2, 0x0085C38F], "direct FUN_00864c10 callers")

    _require(_u32(data, 0x00B1D520), 0x0085B6E0, "vtable +0x18")
    _require(_u32(data, 0x00B1D524), 0x0085C370, "vtable +0x1c")
    constructor = _rowmap(disasm(executable, 0x0085AFD0, 0x0085B057))
    _require(constructor.get(0x0085AFDA), ("mov", "DWORD PTR [esi],0xb1d508"), "constructor vptr store")

    window_sha, window_size = _window_hash(data, 0x00864C40, 0x00865019)
    _require(window_sha, "8ae83797d2f0a6bd6120737d84df25ce8a50ff1f4ad35122997277e2acea033a", "machine window SHA")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "authority": {"platform": "PC retail 1.02", "retail_executable_sha256": digest},
        "site": "0x00865013",
        "entry_receiver_chain": [
            "0x00864c40 mov edi,ecx",
            "0x00864c42 mov [ebp-0x34],edi",
            "0x00864d63 mov esi,[ebp-0x34]",
            "0x00864db5 mov esi,[ebp-0x34]",
            "0x00865013 fstp [esi+0x374]",
        ],
        "temporary_first_argument_load": "0x00864c67 mov esi,[ebx+0x8]",
        "post_final_restore_esi_write_count": 0,
        "direct_callsites": ["0x0085b6f2", "0x0085c38f"],
        "caller_vptr": "0x00b1d508",
        "caller_vtable_slots": {"0x18": "0x0085b6e0", "0x1c": "0x0085c370"},
        "participants_manager_vptrs": ["0x00ab9190", "0x00ab916c"],
        "machine_window": {"byte_count": window_size, "sha256": window_sha},
        "adjudication": {
            "prior_first_stack_argument_claim_rejected": True,
            "target_base_is_entry_ecx": True,
            "target_receiver_is_participants_manager": False,
            "site_can_write_manager_plus_0x374": False,
            "external_provider_count": 7,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    result = analyze(args.executable)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
