#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330DirectWin32RuntimePatchingSurface/1"
EXPECTED_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
EXPECTED_SIZE = 8_801_792
EXPECTED_PROVIDER_COUNT = 7

PATCH_API_NAMES = (
    "VirtualProtect",
    "VirtualProtectEx",
    "WriteProcessMemory",
    "FlushInstructionCache",
    "VirtualAllocEx",
    "NtProtectVirtualMemory",
    "ZwProtectVirtualMemory",
)

EXECUTABLE_PAGE_PROTECTIONS = {0x10, 0x20, 0x40, 0x80}


class PE32:
    def __init__(self, data: bytes):
        self.data = data
        if data[:2] != b"MZ":
            raise ValueError("not MZ")
        self.pe = struct.unpack_from("<I", data, 0x3C)[0]
        if data[self.pe:self.pe + 4] != b"PE\0\0":
            raise ValueError("not PE")
        (
            self.machine,
            self.section_count,
            _timestamp,
            _ptrsym,
            _numsym,
            self.optional_size,
            _characteristics,
        ) = struct.unpack_from("<HHIIIHH", data, self.pe + 4)
        self.optional = self.pe + 24
        if struct.unpack_from("<H", data, self.optional)[0] != 0x10B:
            raise ValueError("not PE32")
        self.image_base = struct.unpack_from("<I", data, self.optional + 28)[0]
        self.size_of_headers = struct.unpack_from("<I", data, self.optional + 60)[0]
        self.directory_count = struct.unpack_from("<I", data, self.optional + 92)[0]
        self.directories = [
            struct.unpack_from("<II", data, self.optional + 96 + i * 8)
            for i in range(min(self.directory_count, 16))
        ]
        section_off = self.optional + self.optional_size
        self.sections = []
        for i in range(self.section_count):
            off = section_off + i * 40
            name = data[off:off + 8].split(b"\0", 1)[0].decode("ascii", "replace")
            virtual_size, virtual_address, raw_size, raw_ptr = struct.unpack_from("<IIII", data, off + 8)
            characteristics = struct.unpack_from("<I", data, off + 36)[0]
            self.sections.append(
                {
                    "name": name,
                    "virtual_address": virtual_address,
                    "virtual_size": virtual_size,
                    "raw_ptr": raw_ptr,
                    "raw_size": raw_size,
                    "characteristics": characteristics,
                }
            )

    def rva_to_offset(self, rva: int) -> int:
        if rva < self.size_of_headers:
            return rva
        for sec in self.sections:
            start = sec["virtual_address"]
            span = max(sec["virtual_size"], sec["raw_size"])
            if start <= rva < start + span:
                return sec["raw_ptr"] + (rva - start)
        raise ValueError(f"RVA outside mapped image: 0x{rva:08x}")

    def offset_to_va(self, off: int) -> tuple[int, str]:
        for sec in self.sections:
            if sec["raw_ptr"] <= off < sec["raw_ptr"] + sec["raw_size"]:
                va = self.image_base + sec["virtual_address"] + (off - sec["raw_ptr"])
                return va, sec["name"]
        raise ValueError(f"file offset outside sections: 0x{off:x}")

    def imports(self) -> list[dict]:
        if len(self.directories) < 2:
            return []
        import_rva, _import_size = self.directories[1]
        if not import_rva:
            return []
        desc = self.rva_to_offset(import_rva)
        out = []
        while True:
            oft, timestamp, forwarder, name_rva, first_thunk = struct.unpack_from("<IIIII", self.data, desc)
            if oft == timestamp == forwarder == name_rva == first_thunk == 0:
                break
            name_off = self.rva_to_offset(name_rva)
            dll_end = self.data.index(b"\0", name_off)
            dll = self.data[name_off:dll_end].decode("ascii", "replace")
            thunk_rva = oft or first_thunk
            thunk_off = self.rva_to_offset(thunk_rva)
            functions = []
            index = 0
            while True:
                value = struct.unpack_from("<I", self.data, thunk_off + index * 4)[0]
                if value == 0:
                    break
                if value & 0x80000000:
                    name = f"ordinal_{value & 0xffff}"
                else:
                    ibn = self.rva_to_offset(value)
                    end = self.data.index(b"\0", ibn + 2)
                    name = self.data[ibn + 2:end].decode("ascii", "replace")
                functions.append(
                    {
                        "name": name,
                        "iat_va": self.image_base + first_thunk + index * 4,
                    }
                )
                index += 1
            out.append({"dll": dll, "functions": functions})
            desc += 20
        return out


def parse_objdump(exe: Path) -> list[dict]:
    text = subprocess.check_output(
        ["objdump", "-d", "-Mintel", str(exe)],
        text=True,
        errors="replace",
    )
    rows = []
    pattern = re.compile(
        r"^\s*([0-9a-fA-F]+):\s+((?:[0-9a-fA-F]{2}\s+)+)\s*([a-zA-Z][a-zA-Z0-9.]*)\s*(.*)$"
    )
    for line in text.splitlines():
        match = pattern.match(line)
        if not match:
            continue
        rows.append(
            {
                "address": int(match.group(1), 16),
                "mnemonic": match.group(3).lower(),
                "operands": match.group(4).strip().lower(),
            }
        )
    return rows


def parse_push_immediate(operands: str) -> int | None:
    token = operands.split()[0] if operands else ""
    try:
        return int(token, 0)
    except ValueError:
        return None


def virtualalloc_call_rows(instructions: list[dict], iat_va: int) -> list[dict]:
    target = f"0x{iat_va:x}"
    rows = []
    boundaries = {"call", "ret", "retf", "iret", "int", "jmp"}
    for index, insn in enumerate(instructions):
        if insn["mnemonic"] != "call" or target not in insn["operands"]:
            continue
        pushes = []
        cursor = index - 1
        while cursor >= 0 and len(pushes) < 4 and index - cursor <= 32:
            prev = instructions[cursor]
            if prev["mnemonic"] in boundaries or prev["mnemonic"].startswith("j"):
                break
            if prev["mnemonic"] == "push":
                pushes.append(prev)
            cursor -= 1
        if len(pushes) != 4:
            protection = None
        else:
            protection = parse_push_immediate(pushes[3]["operands"])
        rows.append(
            {
                "callsite": f"0x{insn['address']:08x}",
                "fl_protect": None if protection is None else f"0x{protection:08x}",
                "fl_protect_value": protection,
            }
        )
    return rows


def analyze(exe: Path) -> dict:
    data = exe.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SHA256 or len(data) != EXPECTED_SIZE:
        raise ValueError("retail authority mismatch")

    pe = PE32(data)
    imports = pe.imports()
    imported = {
        fn["name"]: {"dll": entry["dll"], "iat_va": fn["iat_va"]}
        for entry in imports
        for fn in entry["functions"]
    }

    virtualalloc = imported.get("VirtualAlloc")
    if virtualalloc is None:
        raise ValueError("VirtualAlloc import disappeared")

    iat_bytes = struct.pack("<I", virtualalloc["iat_va"])
    iat_occurrences = []
    cursor = 0
    while True:
        off = data.find(iat_bytes, cursor)
        if off < 0:
            break
        va, section = pe.offset_to_va(off)
        iat_occurrences.append(
            {"file_offset": f"0x{off:08x}", "va": f"0x{va:08x}", "section": section}
        )
        cursor = off + 1

    instructions = parse_objdump(exe)
    calls = virtualalloc_call_rows(instructions, virtualalloc["iat_va"])
    executable_calls = [
        row for row in calls if row["fl_protect_value"] in EXECUTABLE_PAGE_PROTECTIONS
    ]
    unknown_calls = [row for row in calls if row["fl_protect_value"] is None]

    api_strings = {}
    for name in PATCH_API_NAMES:
        encoded = name.encode("ascii")
        offsets = []
        cursor = 0
        while True:
            off = data.find(encoded, cursor)
            if off < 0:
                break
            offsets.append(off)
            cursor = off + 1
        api_strings[name] = offsets

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": digest,
            "retail_file_size": len(data),
            "image_base": f"0x{pe.image_base:08x}",
            "retail_bytes_are_machine_authority": True,
        },
        "import_surface": {
            "import_descriptor_count": len(imports),
            "imported_function_count": sum(len(entry["functions"]) for entry in imports),
            "virtualalloc_imported": True,
            "virtualalloc_iat_va": f"0x{virtualalloc['iat_va']:08x}",
            "getprocaddress_imported": "GetProcAddress" in imported,
            "patch_api_import_presence": {
                name: name in imported for name in PATCH_API_NAMES
            },
            "patch_api_ascii_string_hit_counts": {
                name: len(offsets) for name, offsets in api_strings.items()
            },
        },
        "virtualalloc_surface": {
            "iat_address_whole_image_occurrence_count": len(iat_occurrences),
            "iat_address_occurrences": iat_occurrences,
            "direct_iat_callsite_count": len(calls),
            "callsites": [
                {
                    "callsite": row["callsite"],
                    "fl_protect": row["fl_protect"],
                    "executable_protection": row["fl_protect_value"] in EXECUTABLE_PAGE_PROTECTIONS
                    if row["fl_protect_value"] is not None
                    else None,
                }
                for row in calls
            ],
            "executable_protection_callsite_count": len(executable_calls),
            "unknown_protection_callsite_count": len(unknown_calls),
        },
        "adjudication": {
            "direct_standard_win32_runtime_patching_subset_complete": True,
            "direct_imported_code_page_protection_api_found": any(
                name in imported for name in PATCH_API_NAMES
            ),
            "direct_virtualalloc_executable_allocation_found": bool(executable_calls),
            "virtualalloc_static_reference_surface_complete": len(iat_occurrences) == len(calls),
            "runtime_patching_or_generated_code_ruled_out": False,
            "runtime_computed_carrier_pointers_ruled_out": False,
            "runtime_copied_or_encoded_carrier_pointers_ruled_out": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": EXPECTED_PROVIDER_COUNT,
        },
        "limits": [
            "This closes only direct retail-image references to imported Win32 code-page protection/write APIs and direct VirtualAlloc IAT calls.",
            "GetProcAddress is imported, so dynamically resolved APIs, externally supplied names/addresses, runtime patching by opaque helpers, JIT-style engines and copied/generated code pointers remain open.",
            "PAGE_READWRITE allocations are not treated as executable code pages.",
        ],
        "next_step": "Trace dynamic GetProcAddress consumers or runtime-populated function-pointer stores before promoting global runtime-generated/copied pointer gates.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("exe", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze(args.exe)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
