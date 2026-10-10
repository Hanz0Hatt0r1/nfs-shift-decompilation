#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330TextBaseDeltaTableSeedSurface/1"
EXPECTED_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
EXPECTED_SIZE = 8_801_792
IMAGE_BASE = 0x00400000
TEXT_RVA = 0x00001000
TEXT_BASE = IMAGE_BASE + TEXT_RVA
EXPECTED_PROVIDER_COUNT = 7
IMAGE_SCN_MEM_EXECUTE = 0x20000000

CARRIERS = {
    "FUN_00769520": 0x00769520,
    "FUN_0076b130": 0x0076B130,
    "FUN_0076df50": 0x0076DF50,
    "FUN_00768a4d": 0x00768A4D,
    "FUN_00756050": 0x00756050,
    "FUN_00772200": 0x00772200,
    "FUN_00772570": 0x00772570,
    "FUN_007c3b00": 0x007C3B00,
    "FUN_0076b280": 0x0076B280,
    "FUN_007618f0": 0x007618F0,
    "FUN_00769640": 0x00769640,
    "FUN_007567a0": 0x007567A0,
    "FUN_00756bb0": 0x00756BB0,
    "FUN_00771db0": 0x00771DB0,
    "FUN_00771e10": 0x00771E10,
}


def parse_sections(data: bytes) -> list[dict]:
    if data[:2] != b"MZ":
        raise ValueError("not an MZ image")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("not a PE image")
    section_count = struct.unpack_from("<H", data, pe + 6)[0]
    optional_size = struct.unpack_from("<H", data, pe + 20)[0]
    optional = pe + 24
    magic = struct.unpack_from("<H", data, optional)[0]
    if magic != 0x10B:
        raise ValueError("expected PE32 optional header")
    image_base = struct.unpack_from("<I", data, optional + 28)[0]
    if image_base != IMAGE_BASE:
        raise ValueError(f"image-base drift: 0x{image_base:08x}")
    section_table = optional + optional_size
    rows = []
    for i in range(section_count):
        off = section_table + i * 40
        name = data[off:off + 8].split(b"\0", 1)[0].decode("ascii", "replace")
        virtual_size, rva, raw_size, raw_offset = struct.unpack_from("<IIII", data, off + 8)
        characteristics = struct.unpack_from("<I", data, off + 36)[0]
        rows.append({
            "name": name,
            "rva": rva,
            "virtual_size": virtual_size,
            "raw_size": raw_size,
            "raw_offset": raw_offset,
            "characteristics": characteristics,
            "executable": bool(characteristics & IMAGE_SCN_MEM_EXECUTE),
        })
    return rows


def section_for_offset(sections: list[dict], file_offset: int) -> dict | None:
    for section in sections:
        lo = section["raw_offset"]
        hi = lo + section["raw_size"]
        if lo <= file_offset < hi:
            return section
    return None


def file_offset_to_va(section: dict, file_offset: int) -> int:
    return IMAGE_BASE + section["rva"] + (file_offset - section["raw_offset"])


def find_all(data: bytes, needle: bytes, start: int = 0, end: int | None = None) -> list[int]:
    if end is None:
        end = len(data)
    hits = []
    cursor = start
    while True:
        pos = data.find(needle, cursor, end)
        if pos < 0:
            return hits
        hits.append(pos)
        cursor = pos + 1


def classify_hit(data: bytes, sections: list[dict], name: str, carrier: int, delta: int, file_offset: int) -> dict:
    section = section_for_offset(sections, file_offset)
    row = {
        "carrier": name,
        "carrier_va": f"0x{carrier:08x}",
        "text_base_delta": f"0x{delta:08x}",
        "file_offset": f"0x{file_offset:08x}",
        "file_offset_mod4": file_offset % 4,
        "section": section["name"] if section else None,
        "section_executable": section["executable"] if section else None,
        "classification": "raw_dword_sequence",
    }
    if section is not None:
        row["sequence_va"] = f"0x{file_offset_to_va(section, file_offset):08x}"
    if section is not None and section["executable"] and file_offset > 0 and data[file_offset - 1] in (0xE8, 0xE9):
        opcode = data[file_offset - 1]
        disp = struct.unpack_from("<i", data, file_offset)[0]
        opcode_va = file_offset_to_va(section, file_offset - 1)
        target = (opcode_va + 5 + disp) & 0xFFFFFFFF
        row.update({
            "classification": "rel32_control_transfer_displacement",
            "control_transfer": "call" if opcode == 0xE8 else "jmp",
            "instruction_va": f"0x{opcode_va:08x}",
            "control_target_va": f"0x{target:08x}",
            "control_target_is_exact_p1b_carrier": target in set(CARRIERS.values()),
        })
    return row


def analyze_bytes(data: bytes) -> dict:
    sections = parse_sections(data)
    text = next((row for row in sections if row["name"] == ".text"), None)
    if text is None or text["rva"] != TEXT_RVA or not text["executable"]:
        raise ValueError("authoritative .text geometry drift")

    carrier_rows = []
    raw_hits = []
    nonexec_hits = []
    for name, carrier in CARRIERS.items():
        delta = (carrier - TEXT_BASE) & 0xFFFFFFFF
        needle = struct.pack("<I", delta)
        carrier_hits = find_all(data, needle)
        carrier_rows.append({
            "name": name,
            "address": f"0x{carrier:08x}",
            "text_base_delta": f"0x{delta:08x}",
            "raw_hit_count": len(carrier_hits),
        })
        for file_offset in carrier_hits:
            hit = classify_hit(data, sections, name, carrier, delta, file_offset)
            raw_hits.append(hit)
            if hit["section_executable"] is False:
                nonexec_hits.append(hit)

    rel32_diagnostics = [h for h in raw_hits if h["classification"] == "rel32_control_transfer_displacement"]
    unclassified_executable = [
        h for h in raw_hits
        if h["section_executable"] is True and h["classification"] != "rel32_control_transfer_displacement"
    ]

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": hashlib.sha256(data).hexdigest(),
            "retail_file_size": len(data),
            "preferred_image_base": f"0x{IMAGE_BASE:08x}",
            "text_rva": f"0x{TEXT_RVA:08x}",
            "text_base_va": f"0x{TEXT_BASE:08x}",
            "retail_bytes_are_machine_authority": True,
        },
        "carrier_set": {
            "count": len(CARRIERS),
            "rows": carrier_rows,
        },
        "section_inventory": [
            {
                "name": s["name"],
                "rva": f"0x{s['rva']:08x}",
                "raw_offset": f"0x{s['raw_offset']:08x}",
                "raw_size": s["raw_size"],
                "executable": s["executable"],
            }
            for s in sections
        ],
        "scan": {
            "raw_exact_text_base_delta_hit_count": len(raw_hits),
            "non_executable_section_exact_text_base_delta_hit_count": len(nonexec_hits),
            "rel32_control_transfer_diagnostic_count": len(rel32_diagnostics),
            "unclassified_executable_diagnostic_count": len(unclassified_executable),
            "raw_hits": raw_hits,
        },
        "adjudication": {
            "image_backed_text_base_delta_table_seed_subset_complete": True,
            "image_backed_text_base_delta_table_seed_found": bool(nonexec_hits),
            "all_raw_text_base_delta_diagnostics_classified": len(raw_hits) == len(rel32_diagnostics),
            "memory_table_derived_carrier_pointers_ruled_out": False,
            "computed_or_encoded_code_pointers_ruled_out": False,
            "runtime_computed_carrier_pointers_ruled_out": False,
            "runtime_copied_or_encoded_carrier_pointers_ruled_out": False,
            "generic_function_pointer_stores_copies_ruled_out": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "global_runtime_derived_4330_alias_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": EXPECTED_PROVIDER_COUNT,
        },
        "limits": [
            "This closes only direct image-backed data-table entries equal to carrier_va - .text_base.",
            "Executable-section raw matches are retained as diagnostics and are rejected only when exact machine bytes prove they are rel32 control-transfer displacements.",
            "Other section bases, transformed/delta chains, runtime-populated tables, cross-block arithmetic, runtime patching, opaque helper returns and copied pointers remain open."
        ],
        "next_step": "Bound other transformed table bases or cross-block memory-derived reconstruction, then classify any positive runtime pointer store/copy sinks."
    }


def analyze(path: Path) -> dict:
    data = path.read_bytes()
    if len(data) != EXPECTED_SIZE:
        raise ValueError(f"retail size drift: {len(data)}")
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError(f"retail SHA-256 drift: {digest}")
    result = analyze_bytes(data)
    if result["scan"]["non_executable_section_exact_text_base_delta_hit_count"] != 0:
        raise ValueError("new non-executable .text-base delta seed appeared")
    if result["scan"]["unclassified_executable_diagnostic_count"] != 0:
        raise ValueError("unclassified executable .text-base delta diagnostic appeared")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("retail", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze(args.retail)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
