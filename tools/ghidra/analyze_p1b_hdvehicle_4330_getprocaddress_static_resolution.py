#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330GetProcAddressStaticResolutionSurface/1"
EXPECTED_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
EXPECTED_SIZE = 8_801_792
EXPECTED_PROVIDER_COUNT = 7
GETPROCADDRESS_IAT = 0x00AA62FC
GENERIC_WRAPPER = 0x0093DD2B
GENERIC_WRAPPER_GPA_CALL = 0x0093DD43

PATCH_API_NAMES = {
    "VirtualProtect",
    "VirtualProtectEx",
    "WriteProcessMemory",
    "FlushInstructionCache",
    "VirtualAllocEx",
    "NtProtectVirtualMemory",
    "ZwProtectVirtualMemory",
}

FORMATTED_WRAPPER_FORMATS = {
    "%sFMODGetCodecDescription%s",
    "%sFMODGetCodecDescriptionEx%s",
    "%sFMODGetDSPDescription%s",
    "%sFMODGetDSPDescriptionEx%s",
    "%sFMODGetOutputDescription%s",
    "%sFMODGetOutputDescriptionEx%s",
}


class PE32:
    def __init__(self, data: bytes):
        self.data = data
        self.pe = struct.unpack_from("<I", data, 0x3C)[0]
        if data[:2] != b"MZ" or data[self.pe:self.pe + 4] != b"PE\0\0":
            raise ValueError("not PE")
        self.optional_size = struct.unpack_from("<H", data, self.pe + 20)[0]
        self.optional = self.pe + 24
        if struct.unpack_from("<H", data, self.optional)[0] != 0x10B:
            raise ValueError("not PE32")
        self.image_base = struct.unpack_from("<I", data, self.optional + 28)[0]
        self.size_of_headers = struct.unpack_from("<I", data, self.optional + 60)[0]
        self.section_count = struct.unpack_from("<H", data, self.pe + 6)[0]
        section_off = self.optional + self.optional_size
        self.sections = []
        for i in range(self.section_count):
            off = section_off + i * 40
            name = data[off:off + 8].split(b"\0", 1)[0].decode("ascii", "replace")
            vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", data, off + 8)
            self.sections.append((name, vaddr, vsize, rawptr, rawsize))

    def rva_to_offset(self, rva: int) -> int:
        if rva < self.size_of_headers:
            return rva
        for _name, vaddr, vsize, rawptr, rawsize in self.sections:
            if vaddr <= rva < vaddr + max(vsize, rawsize):
                return rawptr + (rva - vaddr)
        raise ValueError(f"unmapped RVA 0x{rva:x}")

    def va_to_offset(self, va: int) -> int:
        return self.rva_to_offset(va - self.image_base)

    def cstring(self, va: int) -> str | None:
        try:
            off = self.va_to_offset(va)
        except ValueError:
            return None
        end = self.data.find(b"\0", off, off + 512)
        if end < 0:
            return None
        raw = self.data[off:end]
        try:
            text = raw.decode("ascii")
        except UnicodeDecodeError:
            return None
        if not text or any(ord(ch) < 32 or ord(ch) >= 127 for ch in text):
            return None
        return text


def parse_objdump(exe: Path) -> list[dict]:
    text = subprocess.check_output(
        ["objdump", "-d", "-Mintel", str(exe)],
        text=True,
        errors="replace",
    )
    pattern = re.compile(
        r"^\s*([0-9a-fA-F]+):\s+((?:[0-9a-fA-F]{2}\s+)+)\s*([a-zA-Z][a-zA-Z0-9.]*)\s*(.*)$"
    )
    rows = []
    for line in text.splitlines():
        match = pattern.match(line)
        if match:
            rows.append(
                {
                    "address": int(match.group(1), 16),
                    "mnemonic": match.group(3).lower(),
                    "operands": match.group(4).strip().lower(),
                }
            )
    return rows


def parse_immediate(text: str) -> int | None:
    token = text.strip().split(",")[-1].strip()
    try:
        return int(token, 0)
    except ValueError:
        return None


def destination_register(insn: dict) -> str | None:
    if insn["mnemonic"] not in {
        "mov", "lea", "xor", "add", "sub", "and", "or", "imul",
        "shl", "shr", "sar", "rol", "ror", "inc", "dec", "neg",
        "not", "pop", "movzx", "movsx",
    }:
        return None
    return insn["operands"].split(",", 1)[0].strip() if insn["operands"] else None


def immediate_proc_name_before_call(instructions: list[dict], call_index: int, pe: PE32) -> str | None:
    pushes = []
    for cursor in range(call_index - 1, max(-1, call_index - 14), -1):
        insn = instructions[cursor]
        if insn["mnemonic"] in {"call", "ret", "jmp"} or insn["mnemonic"].startswith("j"):
            break
        if insn["mnemonic"] == "push":
            pushes.append(insn)
            if len(pushes) >= 2:
                va = parse_immediate(pushes[1]["operands"])
                if va is not None:
                    return pe.cstring(va)
                break

    for cursor in range(call_index - 1, max(-1, call_index - 10), -1):
        insn = instructions[cursor]
        if insn["mnemonic"] == "mov" and insn["operands"].startswith("dword ptr [esp],"):
            va = parse_immediate(insn["operands"])
            if va is not None:
                return pe.cstring(va)
        if insn["mnemonic"] in {"ret", "jmp"}:
            break
    return None


def resolve_formatted_wrapper_name(
    instructions: list[dict],
    call_index: int,
    pe: PE32,
) -> str | None:
    for cursor in range(call_index - 1, max(-1, call_index - 24), -1):
        insn = instructions[cursor]
        if insn["mnemonic"] == "call" and insn["operands"] == "0x9031bd":
            pushes = []
            for inner in range(cursor - 1, max(-1, cursor - 10), -1):
                candidate = instructions[inner]
                if candidate["mnemonic"] == "push":
                    pushes.append(candidate)
                    if len(pushes) >= 2:
                        fmt_va = parse_immediate(pushes[1]["operands"])
                        if fmt_va is None:
                            return None
                        fmt = pe.cstring(fmt_va)
                        if fmt not in FORMATTED_WRAPPER_FORMATS:
                            return None
                        return fmt.replace("%s", "_", 1).replace("%s", "@0", 1)
                if candidate["mnemonic"] in {"call", "ret", "jmp"}:
                    break
            return None
    return None


def analyze(exe: Path) -> dict:
    data = exe.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SHA256 or len(data) != EXPECTED_SIZE:
        raise ValueError("retail authority mismatch")
    pe = PE32(data)
    instructions = parse_objdump(exe)

    iat_bytes = struct.pack("<I", GETPROCADDRESS_IAT)
    raw_offsets = [match.start() for match in re.finditer(re.escape(iat_bytes), data)]

    refs = [
        (index, row)
        for index, row in enumerate(instructions)
        if f"0x{GETPROCADDRESS_IAT:x}" in row["operands"]
    ]
    direct_refs = [(index, row) for index, row in refs if row["mnemonic"] == "call"]
    load_refs = [(index, row) for index, row in refs if row["mnemonic"] == "mov"]
    if len(refs) != len(raw_offsets):
        raise ValueError("IAT reference classification drift")

    name_rows = []
    generic_wrapper_seen = False

    for index, row in direct_refs:
        if row["address"] == GENERIC_WRAPPER_GPA_CALL:
            generic_wrapper_seen = True
            continue
        name = immediate_proc_name_before_call(instructions, index, pe)
        if row["address"] == 0x00634046 and name is None:
            name = pe.cstring(0x00AEBE58)
        if name is None:
            raise ValueError(f"unresolved direct GetProcAddress name at 0x{row['address']:08x}")
        name_rows.append(
            {"source": "direct_iat_call", "callsite": f"0x{row['address']:08x}", "name": name}
        )

    loaded_call_count = 0
    for index, row in load_refs:
        register = row["operands"].split(",", 1)[0].strip()
        for cursor in range(index + 1, min(len(instructions), index + 1200)):
            current = instructions[cursor]
            if current["mnemonic"].startswith("ret"):
                break
            if current["mnemonic"] == "call" and current["operands"] == register:
                loaded_call_count += 1
                name = immediate_proc_name_before_call(instructions, cursor, pe)
                if name is None:
                    raise ValueError(
                        f"unresolved register-loaded GetProcAddress name at 0x{current['address']:08x}"
                    )
                name_rows.append(
                    {
                        "source": "register_loaded_iat",
                        "callsite": f"0x{current['address']:08x}",
                        "name": name,
                    }
                )
            if destination_register(current) == register:
                break

    wrapper_callers = [
        (index, row)
        for index, row in enumerate(instructions)
        if row["mnemonic"] == "call" and row["operands"] == f"0x{GENERIC_WRAPPER:x}"
    ]
    wrapper_names = []
    for index, row in wrapper_callers:
        name = immediate_proc_name_before_call(instructions, index, pe)
        if name is None:
            name = resolve_formatted_wrapper_name(instructions, index, pe)
        if name is None:
            raise ValueError(f"unresolved wrapper caller name at 0x{row['address']:08x}")
        wrapper_names.append(name)
        name_rows.append(
            {"source": "generic_wrapper_direct_caller", "callsite": f"0x{row['address']:08x}", "name": name}
        )

    unique_names = sorted({row["name"] for row in name_rows})
    patch_hits = sorted(set(unique_names) & PATCH_API_NAMES)

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": digest,
            "retail_file_size": len(data),
            "retail_bytes_are_machine_authority": True,
        },
        "getprocaddress_surface": {
            "iat_va": f"0x{GETPROCADDRESS_IAT:08x}",
            "whole_image_iat_dword_occurrence_count": len(raw_offsets),
            "classified_instruction_reference_count": len(refs),
            "direct_iat_call_reference_count": len(direct_refs),
            "iat_load_reference_count": len(load_refs),
            "register_loaded_callsite_count": loaded_call_count,
            "physical_getprocaddress_callsite_count": len(direct_refs) + loaded_call_count,
            "generic_wrapper": f"0x{GENERIC_WRAPPER:08x}",
            "generic_wrapper_getprocaddress_callsite": f"0x{GENERIC_WRAPPER_GPA_CALL:08x}",
            "generic_wrapper_direct_caller_count": len(wrapper_callers),
            "generic_wrapper_direct_caller_names": wrapper_names,
            "known_name_instance_count": len(name_rows),
            "known_unique_name_count": len(unique_names),
            "known_unique_names": unique_names,
            "known_patch_api_name_hits": patch_hits,
        },
        "adjudication": {
            "static_getprocaddress_iat_reference_surface_complete": True,
            "register_loaded_getprocaddress_call_surface_complete": True,
            "generic_wrapper_direct_caller_name_surface_complete": generic_wrapper_seen,
            "known_getprocaddress_patch_api_resolution_found": bool(patch_hits),
            "dynamic_getprocaddress_resolution_ruled_out": False,
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
            "This bounds all static references to the imported GetProcAddress IAT slot and direct callers of the one generic wrapper.",
            "Indirect/runtime-generated callers of the generic wrapper, dynamically constructed proc-name strings, externally supplied module/proc addresses and opaque helper resolution remain open.",
            "Absence of known patch API names does not globally rule out runtime patching or generated/copied code pointers.",
        ],
        "next_step": "Trace indirect entry/address-taking into the generic GetProcAddress wrapper or runtime-populated function-pointer stores before promoting global runtime patching/indirect-entry gates.",
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
