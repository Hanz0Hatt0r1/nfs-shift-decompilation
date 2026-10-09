#!/usr/bin/env python3
"""Prove the worker-reachable direct GetProcAddress names from retail SHIFT.exe.

This is direct PC-retail machine evidence.  It validates the exact executable
hash, resolves the PE import table entry used by the recovered calls, verifies
small byte windows that encode each name argument/call sequence, and reads the
referenced NUL-terminated API name directly from .rdata.

The proof is intentionally narrow: it closes only the pinned direct named
GetProcAddress surface.  Hashed/generated names, manual export walking,
indirect resolver mechanisms and native/syscall APC injection remain open.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

FORMAT = "SHIFT.P1D.Controller1GetProcRetailMachineProof/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
GETPROC_IAT_VA = 0x00AA62FC
APC_NAMES = {
    "QueueUserAPC",
    "NtQueueApcThread",
    "NtQueueApcThreadEx",
    "ZwQueueApcThread",
    "RtlQueueApcWow64Thread",
    "SetWaitableTimerEx",
}

CALLS = [
    {
        "function": "0x0090748b",
        "callsite": "0x009074a0",
        "window_va": "0x0090749a",
        "window_hex": "68fc6cb30050ff15fc62aa00",
        "name_va": "0x00b36cfc",
        "name": "CorExitProcess",
        "argument_form": "push-imm32",
        "resolver_form": "direct-iat-call",
    },
    {
        "function": "0x0090aa27",
        "callsite": "0x0090aa7b",
        "window_va": "0x0090aa75",
        "window_hex": "68bc84b30056ff15fc62aa00",
        "name_va": "0x00b384bc",
        "name": "EncodePointer",
        "argument_form": "push-imm32",
        "resolver_form": "direct-iat-call",
    },
    {
        "function": "0x0090aa9e",
        "callsite": "0x0090aaf2",
        "window_va": "0x0090aaec",
        "window_hex": "68dc84b30056ff15fc62aa00",
        "name_va": "0x00b384dc",
        "name": "DecodePointer",
        "argument_form": "push-imm32",
        "resolver_form": "direct-iat-call",
    },
    {
        "function": "0x0090abb8",
        "callsite": "0x0090abfd",
        "window_va": "0x0090abef",
        "window_hex": "68bc84b300ff75e48b1dfc62aa00ffd3",
        "name_va": "0x00b384bc",
        "name": "EncodePointer",
        "argument_form": "push-imm32",
        "resolver_form": "register-ebx-loaded-from-getproc-iat-in-window",
    },
    {
        "function": "0x0090abb8",
        "callsite": "0x0090ac0d",
        "window_va": "0x0090ac05",
        "window_hex": "68dc84b300ff75e4ffd3",
        "name_va": "0x00b384dc",
        "name": "DecodePointer",
        "argument_form": "push-imm32",
        "resolver_form": "register-ebx-reuse",
        "resolver_seed_va": "0x0090abf7",
        "resolver_seed_hex": "8b1dfc62aa00",
    },
    {
        "function": "0x009189cd",
        "callsite": "0x00918a26",
        "window_va": "0x00918a20",
        "window_hex": "681817b40050ff15fc62aa00",
        "name_va": "0x00b41718",
        "name": "InitializeCriticalSectionAndSpinCount",
        "argument_form": "push-imm32",
        "resolver_form": "direct-iat-call",
    },
    {
        "function": "0x0091c073",
        "callsite": "0x0091c0bc",
        "window_va": "0x0091c0b0",
        "window_hex": "8b35fc62aa00684821b40057ffd6",
        "name_va": "0x00b42148",
        "name": "MessageBoxA",
        "argument_form": "push-imm32",
        "resolver_form": "register-esi-loaded-from-getproc-iat-in-window",
    },
    {
        "function": "0x0091c073",
        "callsite": "0x0091c0d9",
        "window_va": "0x0091c0cc",
        "window_hex": "c704243821b40057a3fc29c300ffd6",
        "name_va": "0x00b42138",
        "name": "GetActiveWindow",
        "argument_form": "mov-[esp]-imm32-then-push-module",
        "resolver_form": "register-esi-reuse",
        "resolver_seed_va": "0x0091c0b0",
        "resolver_seed_hex": "8b35fc62aa00",
    },
    {
        "function": "0x0091c073",
        "callsite": "0x0091c0ee",
        "window_va": "0x0091c0e1",
        "window_hex": "c704242421b40057a3002ac300ffd6",
        "name_va": "0x00b42124",
        "name": "GetLastActivePopup",
        "argument_form": "mov-[esp]-imm32-then-push-module",
        "resolver_form": "register-esi-reuse",
        "resolver_seed_va": "0x0091c0b0",
        "resolver_seed_hex": "8b35fc62aa00",
    },
    {
        "function": "0x0091c073",
        "callsite": "0x0091c123",
        "window_va": "0x0091c11d",
        "window_hex": "680821b40057ffd6",
        "name_va": "0x00b42108",
        "name": "GetUserObjectInformationA",
        "argument_form": "push-imm32",
        "resolver_form": "register-esi-reuse",
        "resolver_seed_va": "0x0091c0b0",
        "resolver_seed_hex": "8b35fc62aa00",
    },
    {
        "function": "0x0091c073",
        "callsite": "0x0091c13b",
        "window_va": "0x0091c135",
        "window_hex": "68f020b40057ffd6",
        "name_va": "0x00b420f0",
        "name": "GetProcessWindowStation",
        "argument_form": "push-imm32",
        "resolver_form": "register-esi-reuse",
        "resolver_seed_va": "0x0091c0b0",
        "resolver_seed_hex": "8b35fc62aa00",
    },
]


class PEImage:
    def __init__(self, data: bytes):
        self.data = data
        if data[:2] != b"MZ":
            raise ValueError("not an MZ executable")
        self.pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
        if data[self.pe_offset:self.pe_offset + 4] != b"PE\0\0":
            raise ValueError("missing PE signature")
        coff = self.pe_offset + 4
        self.section_count = struct.unpack_from("<H", data, coff + 2)[0]
        optional_size = struct.unpack_from("<H", data, coff + 16)[0]
        optional = coff + 20
        magic = struct.unpack_from("<H", data, optional)[0]
        if magic != 0x10B:
            raise ValueError(f"expected PE32 optional header, got 0x{magic:x}")
        self.image_base = struct.unpack_from("<I", data, optional + 28)[0]
        self.data_directory = optional + 96
        section_table = optional + optional_size
        self.sections = []
        for index in range(self.section_count):
            off = section_table + index * 40
            name = data[off:off + 8].split(b"\0", 1)[0].decode("ascii", "replace")
            virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from("<IIII", data, off + 8)
            self.sections.append({
                "name": name,
                "rva": virtual_address,
                "virtual_size": virtual_size,
                "raw_size": raw_size,
                "raw_pointer": raw_pointer,
            })

    def rva_to_offset(self, rva: int) -> int:
        for section in self.sections:
            span = max(section["virtual_size"], section["raw_size"])
            if section["rva"] <= rva < section["rva"] + span:
                return section["raw_pointer"] + (rva - section["rva"])
        raise ValueError(f"RVA not mapped by PE sections: 0x{rva:08x}")

    def va_to_offset(self, va: int) -> int:
        return self.rva_to_offset(va - self.image_base)

    def bytes_at_va(self, va: int, size: int) -> bytes:
        off = self.va_to_offset(va)
        return self.data[off:off + size]

    def c_string_at_va(self, va: int, limit: int = 256) -> str:
        off = self.va_to_offset(va)
        end = self.data.find(b"\0", off, off + limit)
        if end < 0:
            raise ValueError(f"unterminated string at VA 0x{va:08x}")
        return self.data[off:end].decode("ascii")

    def import_map(self) -> dict[int, tuple[str, str]]:
        import_rva, _ = struct.unpack_from("<II", self.data, self.data_directory + 8)
        if not import_rva:
            return {}
        imports: dict[int, tuple[str, str]] = {}
        desc_off = self.rva_to_offset(import_rva)
        while True:
            original_first_thunk, timestamp, forwarder, name_rva, first_thunk = struct.unpack_from(
                "<IIIII", self.data, desc_off
            )
            if not any((original_first_thunk, timestamp, forwarder, name_rva, first_thunk)):
                break
            name_off = self.rva_to_offset(name_rva)
            name_end = self.data.index(b"\0", name_off)
            dll = self.data[name_off:name_end].decode("ascii")
            thunk_rva = original_first_thunk or first_thunk
            index = 0
            while True:
                thunk_off = self.rva_to_offset(thunk_rva + index * 4)
                value = struct.unpack_from("<I", self.data, thunk_off)[0]
                if value == 0:
                    break
                iat_va = self.image_base + first_thunk + index * 4
                if value & 0x80000000:
                    symbol = f"ordinal:{value & 0xffff}"
                else:
                    ibn_off = self.rva_to_offset(value) + 2
                    ibn_end = self.data.index(b"\0", ibn_off)
                    symbol = self.data[ibn_off:ibn_end].decode("ascii")
                imports[iat_va] = (dll, symbol)
                index += 1
            desc_off += 20
        return imports


def analyze(exe: Path) -> dict:
    raw = exe.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != RETAIL_SHA256:
        raise ValueError(f"retail SHA-256 mismatch: {digest}")
    pe = PEImage(raw)
    imports = pe.import_map()
    import_identity = imports.get(GETPROC_IAT_VA)

    rows = []
    for spec in CALLS:
        window = bytes.fromhex(spec["window_hex"])
        window_va = int(spec["window_va"], 16)
        actual = pe.bytes_at_va(window_va, len(window))
        name_va = int(spec["name_va"], 16)
        actual_name = pe.c_string_at_va(name_va)
        seed_expected = spec.get("resolver_seed_hex")
        seed_match = True
        seed_actual = None
        if seed_expected:
            expected = bytes.fromhex(seed_expected)
            seed_actual = pe.bytes_at_va(int(spec["resolver_seed_va"], 16), len(expected))
            seed_match = seed_actual == expected
        row = dict(spec)
        row.update({
            "actual_window_hex": actual.hex(),
            "window_match": actual == window,
            "actual_name": actual_name,
            "name_match": actual_name == spec["name"],
            "resolver_seed_actual_hex": None if seed_actual is None else seed_actual.hex(),
            "resolver_seed_match": seed_match,
            "apc_name": actual_name in APC_NAMES,
        })
        rows.append(row)

    all_machine_matches = all(
        row["window_match"] and row["name_match"] and row["resolver_seed_match"]
        for row in rows
    )
    apc_rows = [row for row in rows if row["apc_name"]]
    import_proven = import_identity is not None and import_identity[1] == "GetProcAddress"

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": digest,
            "evidence_kind": "direct PE32 bytes + import table + referenced .rdata strings",
        },
        "resolver_import": {
            "iat_va": f"0x{GETPROC_IAT_VA:08x}",
            "dll": None if import_identity is None else import_identity[0],
            "name": None if import_identity is None else import_identity[1],
            "getprocaddress_identity_proven": import_proven,
        },
        "surface": {
            "worker": "0x00662880",
            "function_count": len({row["function"] for row in rows}),
            "call_count": len(rows),
            "calls": rows,
            "resolved_names": [row["actual_name"] for row in rows],
            "apc_name_call_count": len(apc_rows),
        },
        "adjudication": {
            "all_11_machine_windows_match": all_machine_matches and len(rows) == 11,
            "getprocaddress_iat_identity_proven": import_proven,
            "all_11_exact_names_non_apc": all_machine_matches and import_proven and not apc_rows and len(rows) == 11,
            "direct_worker_reachable_named_getproc_apc_surface_rejected": all_machine_matches and import_proven and not apc_rows and len(rows) == 11,
            "indirect_resolver_calls_ruled_out": False,
            "hashed_or_generated_resolution_ruled_out": False,
            "manual_export_walk_ruled_out": False,
            "native_or_syscall_injection_ruled_out": False,
            "controller1_timing_exhaustive": False,
            "p1_3d_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This proof covers only the eleven already-pinned direct worker-reachable GetProcAddress callsites.",
            "Register reuse is admitted only where the exact machine seed loads the GetProcAddress IAT into EBX/ESI and the exact call window uses that register.",
            "No claim is made about hashed/generated names, manual PE export walking, indirect resolver callbacks, or native/syscall APC injection.",
        ],
        "next_step": "Continue the #1699 manual-export/native primitive inventory and join any positive candidate to exact Controller #1 thread identity before changing timing gates.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = analyze(args.exe)
    except ValueError as exc:
        parser.error(str(exc))
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
