#!/usr/bin/env python3
"""Bound canonical CALL-next/POP EIP capture for exact HDVehicle+0x4330 carriers."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330CanonicalEipCaptureSurface/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
EXPECTED_CANDIDATE = {"section": ".secu", "call": "0x00d31404", "pop": "0x00d31409", "pop_register": "ebp"}
WINDOW_VA = 0x00D31400
WINDOW_HEX = "9c505351e8000000005d81ed09040000b801000000b9100000008bdd870385c07409f39083c340e2f3ebea8beb648b1d0400000083eb048b03894504892b595b589dc3"
SECTION_RE = re.compile(r"^Disassembly of section ([^:]+):$")
INST_RE = re.compile(r"^\s*([0-9a-fA-F]+):\s+((?:[0-9a-fA-F]{2}\s+)+)\s*(.*)$")
POP_REGS = {0x58:"eax",0x59:"ecx",0x5a:"edx",0x5b:"ebx",0x5c:"esp",0x5d:"ebp",0x5e:"esi",0x5f:"edi"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_pe(data: bytes) -> dict:
    if data[:2] != b"MZ":
        raise ValueError("not an MZ executable")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe+4] != b"PE\0\0":
        raise ValueError("missing PE signature")
    coff = pe + 4
    nsec = struct.unpack_from("<H", data, coff + 2)[0]
    opt_size = struct.unpack_from("<H", data, coff + 16)[0]
    opt = coff + 20
    if struct.unpack_from("<H", data, opt)[0] != 0x10B:
        raise ValueError("expected PE32")
    base = struct.unpack_from("<I", data, opt + 28)[0]
    table = opt + opt_size
    sections = []
    for index in range(nsec):
        off = table + index * 40
        name = data[off:off+8].split(b"\0",1)[0].decode("ascii", errors="replace")
        virtual_size, rva, raw_size, raw_ptr = struct.unpack_from("<IIII", data, off + 8)
        characteristics = struct.unpack_from("<I", data, off + 36)[0]
        sections.append({
            "name": name,
            "va": base + rva,
            "rva": rva,
            "virtual_size": virtual_size,
            "raw_size": raw_size,
            "raw_ptr": raw_ptr,
            "executable": bool(characteristics & 0x20000000),
        })
    return {"image_base": base, "sections": sections}


def bytes_at_va(data: bytes, pe: dict, va: int, size: int) -> bytes:
    for section in pe["sections"]:
        start = section["va"]
        span = max(section["virtual_size"], section["raw_size"])
        if start <= va < start + span:
            offset = section["raw_ptr"] + (va - start)
            return data[offset:offset+size]
    raise ValueError(f"unmapped VA 0x{va:08x}")


def parse_objdump(text: str) -> tuple[set[str], list[dict]]:
    current_section = None
    sections = set()
    instructions = []
    for line in text.splitlines():
        sm = SECTION_RE.match(line.strip())
        if sm:
            current_section = sm.group(1)
            sections.add(current_section)
            continue
        im = INST_RE.match(line)
        if not im or current_section is None:
            continue
        instructions.append({
            "section": current_section,
            "address": int(im.group(1), 16),
            "bytes": bytes.fromhex(im.group(2)),
            "asm": im.group(3).strip(),
        })
    return sections, instructions


def find_call_next_pop(instructions: list[dict]) -> list[dict]:
    candidates = []
    for index in range(len(instructions)-1):
        call = instructions[index]
        pop = instructions[index+1]
        raw = call["bytes"]
        if len(raw) != 5 or raw[0] != 0xE8 or raw[1:] != b"\0\0\0\0":
            continue
        if call["section"] != pop["section"] or pop["address"] != call["address"] + 5:
            continue
        if len(pop["bytes"]) != 1 or pop["bytes"][0] not in POP_REGS:
            continue
        candidates.append({
            "section": call["section"],
            "call": f"0x{call['address']:08x}",
            "pop": f"0x{pop['address']:08x}",
            "pop_register": POP_REGS[pop["bytes"][0]],
        })
    return candidates


def analyze(exe: Path) -> dict:
    digest = sha256(exe)
    if digest != RETAIL_SHA256:
        raise ValueError(f"unexpected retail SHA-256: {digest}")
    data = exe.read_bytes()
    pe = parse_pe(data)
    executable_sections = sorted(section["name"] for section in pe["sections"] if section["executable"])
    if executable_sections != [".secu", ".text"]:
        raise ValueError(f"executable section drift: {executable_sections!r}")

    proc = subprocess.run(
        ["objdump", "-d", "-M", "intel", str(exe)],
        check=True, capture_output=True, text=True, errors="replace",
    )
    disassembled_sections, instructions = parse_objdump(proc.stdout)
    if not set(executable_sections).issubset(disassembled_sections):
        raise ValueError(f"objdump omitted executable sections: {disassembled_sections!r}")
    candidates = find_call_next_pop(instructions)
    if candidates != [EXPECTED_CANDIDATE]:
        raise ValueError(f"canonical EIP-capture candidate drift: {candidates!r}")

    expected_window = bytes.fromhex(WINDOW_HEX)
    if bytes_at_va(data, pe, WINDOW_VA, len(expected_window)) != expected_window:
        raise ValueError("0x00d31400 security helper window drift")
    secu = next(section for section in pe["sections"] if section["name"] == ".secu")
    derived_base = 0x00D31409 - 0x409
    if derived_base != secu["va"] or derived_base != 0x00D31000:
        raise ValueError(f"unexpected call/pop derived base: 0x{derived_base:08x}")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": digest,
            "retail_machine_bytes_adjudicate": True,
            "objdump_role": "instruction-boundary inventory",
            "executable_sections": executable_sections,
        },
        "upstream_contracts": [
            "SHIFT.P1B.HDVehicle4330WholeImageLiteralPointerSurface/1",
            "SHIFT.P1B.HDVehicle4330ExternalCallerFinalTranche/1",
        ],
        "canonical_call_next_pop_surface": {
            "candidate_count": 1,
            "candidates": [EXPECTED_CANDIDATE],
            "candidate_machine_window": "0x00d31400..0x00d31442",
            "derived_value": "0x00d31000",
            "derived_value_identity": ".secu section base",
            "post_capture_use": "16-slot lock/TLS bookkeeping rooted at .secu base; candidate returns at 0x00d31442",
            "exact_4330_carrier_pointer_derived": False,
        },
        "adjudication": {
            "canonical_call_next_pop_eip_capture_surface_complete": True,
            "canonical_call_next_pop_candidate_count": 1,
            "canonical_call_next_pop_can_derive_exact_carrier": False,
            "noncanonical_eip_capture_surface_complete": False,
            "runtime_computed_carrier_pointers_ruled_out": False,
            "runtime_copied_or_encoded_carrier_pointers_ruled_out": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "global_runtime_derived_4330_alias_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only the canonical direct CALL-next followed immediately by POP-GPR EIP-capture idiom on instruction boundaries.",
            "The sole candidate derives the .secu base and is unrelated to the exact carrier address domain.",
            "Other EIP acquisition idioms, transformed constants, runtime copies, and encoded pointers remain open."
        ],
        "next_step": "Bound noncanonical EIP acquisition, especially x87 F[N]STENV instruction-pointer extraction, then continue copied/transformed runtime callback pointers."
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = analyze(args.exe)
    except (ValueError, subprocess.CalledProcessError) as exc:
        parser.error(str(exc))
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
