#!/usr/bin/env python3
"""Machine-adjudicate the two remaining exact-carrier RVA byte diagnostics.

The merged whole-image scan found exactly two raw matches for FUN_0076d100 RVA
0x0036d100, both in .rdata. This verifier proves that each match is an unaligned
cross-element byte sequence inside an exact 0x400-byte / 256-DWORD table which
retail code consumes as 4-byte ordered elements. It closes only those two raw
RVA diagnostics; relocated/generated/encoded code pointers remain open.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

FORMAT = "SHIFT.P1A.P13AExactCarrierRdataRvaDiagnosticClosure/1"
UPSTREAM_FORMAT = "SHIFT.P1A.P13AExactCarrierTextRvaLiteralClosure/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
TABLE_SHA256 = "85f4d25300d1437af965cebc94bf108d075b6dccff375290da83bc73aac2fb7e"
IMAGE_BASE = 0x00400000
TARGET_RVA = 0x0036D100
MATCH_BYTES = bytes.fromhex("00d13600")

TABLES = [
    {
        "name": "table_a",
        "start": 0x00AD42C8,
        "end": 0x00AD46C8,
        "diagnostic_va": 0x00AD443F,
        "range_setup": {
            0x0059CD29: "68c846ad00",
            0x0059CD2E: "68c842ad00",
        },
        "callsite": 0x0059CD43,
        "callee": 0x00597DB0,
        "callee_windows": {
            0x00597DB0: "8b5424088b4424042bd0c1fa02",
            0x00597DD0: "8bcad1f9393488730d83",
        },
        "consumer_proof": "FUN_00597db0 computes (end-start)>>2 and compares DWORD PTR [base+index*4]",
    },
    {
        "name": "table_b",
        "start": 0x00B66330,
        "end": 0x00B66730,
        "diagnostic_va": 0x00B664A7,
        "range_setup": {
            0x00A485E8: "ba3067b600",
            0x00A485ED: "b93063b600",
        },
        "callsite": 0x00A485F2,
        "callee": 0x00A485A0,
        "callee_windows": {
            0x00A485A0: "8bc12bd0c1fa02568bf285f67e24",
            0x00A485B5: "8bd6d1fa3b0c90720d83",
        },
        "consumer_proof": "FUN_00a485a0 computes (end-start)>>2 and compares DWORD PTR [base+index*4]",
    },
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_pe32(data: bytes):
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise ValueError("not a PE image")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("missing PE signature")
    count = struct.unpack_from("<H", data, pe + 6)[0]
    opt_size = struct.unpack_from("<H", data, pe + 20)[0]
    opt = pe + 24
    if struct.unpack_from("<H", data, opt)[0] != 0x10B:
        raise ValueError("expected PE32")
    image_base = struct.unpack_from("<I", data, opt + 28)[0]
    table = opt + opt_size
    sections = []
    for i in range(count):
        off = table + i * 40
        sections.append({
            "name": data[off:off + 8].split(b"\0")[0].decode("ascii", "replace"),
            "rva": struct.unpack_from("<I", data, off + 12)[0],
            "raw_size": struct.unpack_from("<I", data, off + 16)[0],
            "raw_offset": struct.unpack_from("<I", data, off + 20)[0],
        })
    return image_base, sections


def read_va(data: bytes, image_base: int, sections: list[dict], va: int, size: int) -> bytes:
    rva = va - image_base
    for section in sections:
        if section["rva"] <= rva and rva + size <= section["rva"] + section["raw_size"]:
            off = section["raw_offset"] + (rva - section["rva"])
            return data[off:off + size]
    raise ValueError(f"VA 0x{va:08x} is not file-backed")


def section_for_va(image_base: int, sections: list[dict], va: int) -> str | None:
    rva = va - image_base
    for section in sections:
        if section["rva"] <= rva < section["rva"] + section["raw_size"]:
            return section["name"]
    return None


def rel32_target(data: bytes, image_base: int, sections: list[dict], site: int) -> int:
    raw = read_va(data, image_base, sections, site, 5)
    if raw[0] != 0xE8:
        raise ValueError(f"0x{site:08x}: expected CALL rel32")
    rel = struct.unpack_from("<i", raw, 1)[0]
    return site + 5 + rel


def verify_window(data: bytes, image_base: int, sections: list[dict], va: int, expected_hex: str) -> None:
    expected = bytes.fromhex(expected_hex)
    actual = read_va(data, image_base, sections, va, len(expected))
    if actual != expected:
        raise ValueError(f"0x{va:08x}: expected {expected_hex}, got {actual.hex()}")


def analyze(executable: Path, upstream_path: Path) -> dict:
    upstream = json.loads(upstream_path.read_text(encoding="utf-8"))
    if upstream.get("format") != UPSTREAM_FORMAT or upstream.get("ready") is not True:
        raise ValueError("unexpected or incomplete .text RVA closure")
    non_text = upstream.get("non_text_unresolved_surface", {})
    if non_text.get("raw_match_count") != 2 or non_text.get("semantic_gate") is not False:
        raise ValueError("expected exactly two unresolved non-text RVA diagnostics")

    data = executable.read_bytes()
    actual_sha = sha256_bytes(data)
    if actual_sha != RETAIL_SHA256:
        raise ValueError(f"unexpected SHIFT.exe SHA-256: {actual_sha}")
    image_base, sections = parse_pe32(data)
    if image_base != IMAGE_BASE:
        raise ValueError(f"unexpected image base: 0x{image_base:08x}")

    expected_upstream = sorted((row["image_va"], row["rva_value"], row["section"]) for row in non_text["matches"])
    expected_rows = sorted([
        ("0x00ad443f", "0x0036d100", ".rdata"),
        ("0x00b664a7", "0x0036d100", ".rdata"),
    ])
    if expected_upstream != expected_rows:
        raise ValueError("unresolved upstream RVA diagnostic set drift")

    rows = []
    for spec in TABLES:
        start, end, diagnostic_va = spec["start"], spec["end"], spec["diagnostic_va"]
        if end - start != 0x400:
            raise ValueError("expected exact 0x400-byte table span")
        if section_for_va(image_base, sections, start) != ".rdata" or section_for_va(image_base, sections, diagnostic_va) != ".rdata":
            raise ValueError("expected table/diagnostic in .rdata")
        table = read_va(data, image_base, sections, start, 0x400)
        if sha256_bytes(table) != TABLE_SHA256:
            raise ValueError(f"{spec['name']}: table SHA-256 drift")
        values = list(struct.unpack("<256I", table))
        if any(values[i] > values[i + 1] for i in range(255)):
            raise ValueError(f"{spec['name']}: expected nondecreasing DWORD table")
        rel = diagnostic_va - start
        if rel != 0x177 or rel % 4 != 3:
            raise ValueError(f"{spec['name']}: diagnostic offset/alignment drift")
        if read_va(data, image_base, sections, diagnostic_va, 4) != MATCH_BYTES:
            raise ValueError(f"{spec['name']}: diagnostic bytes drift")
        previous_offset = rel - (rel % 4)
        next_offset = previous_offset + 4
        previous_value = struct.unpack_from("<I", table, previous_offset)[0]
        next_value = struct.unpack_from("<I", table, next_offset)[0]
        if previous_value != 0x000032B7 or next_value != 0x000036D1:
            raise ValueError(f"{spec['name']}: neighboring DWORD values drift")
        for va, expected_hex in spec["range_setup"].items():
            verify_window(data, image_base, sections, va, expected_hex)
        for va, expected_hex in spec["callee_windows"].items():
            verify_window(data, image_base, sections, va, expected_hex)
        target = rel32_target(data, image_base, sections, spec["callsite"])
        if target != spec["callee"]:
            raise ValueError(f"{spec['name']}: call target drift")
        rows.append({
            "name": spec["name"],
            "table_start": f"0x{start:08x}",
            "table_end": f"0x{end:08x}",
            "table_size": 0x400,
            "element_width": 4,
            "element_count": 256,
            "table_sha256": TABLE_SHA256,
            "nondecreasing_u32": True,
            "consumer": f"0x{spec['callee']:08x}",
            "consumer_proof": spec["consumer_proof"],
            "diagnostic_va": f"0x{diagnostic_va:08x}",
            "diagnostic_rva_bytes": MATCH_BYTES.hex(),
            "diagnostic_unaligned_u32_value": f"0x{TARGET_RVA:08x}",
            "diagnostic_offset_from_table_start": "0x177",
            "diagnostic_offset_mod_element_width": 3,
            "previous_aligned_element_offset": f"0x{previous_offset:03x}",
            "previous_aligned_element_value": f"0x{previous_value:08x}",
            "next_aligned_element_offset": f"0x{next_offset:03x}",
            "next_aligned_element_value": f"0x{next_value:08x}",
            "diagnostic_is_aligned_table_element": False,
            "classification": "cross-DWORD byte sequence inside machine-consumed 256-element u32 table",
        })

    if rows[0]["table_sha256"] != rows[1]["table_sha256"]:
        raise ValueError("expected duplicate DWORD-table contents")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1A / P1.3A",
        "upstream_contract": UPSTREAM_FORMAT,
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": actual_sha,
            "machine_transfer_adjudicates": True,
        },
        "target_diagnostic": {
            "carrier": "FUN_0076d100",
            "carrier_va": "0x0076d100",
            "carrier_rva": "0x0036d100",
            "raw_match_bytes": MATCH_BYTES.hex(),
        },
        "tables": rows,
        "verified_machine_windows": [
            {"site": f"0x{va:08x}", "bytes": hx}
            for spec in TABLES
            for group in (spec["range_setup"], spec["callee_windows"])
            for va, hx in group.items()
        ],
        "verified_calls": [
            {"site": f"0x{spec['callsite']:08x}", "target": f"0x{spec['callee']:08x}"}
            for spec in TABLES
        ],
        "adjudication": {
            "p13a_non_text_exact_carrier_rva_diagnostic_subset_complete": True,
            "p13a_non_text_exact_carrier_rva_diagnostic_count": 2,
            "p13a_non_text_exact_carrier_rva_diagnostic_pointer_element_found": False,
            "p13a_whole_image_raw_exact_carrier_rva_match_subset_complete": True,
            "p13a_whole_image_raw_exact_carrier_rva_semantic_pointer_hit_found": False,
            "relocated_or_rva_encoded_carrier_pointers_ruled_out": False,
            "runtime_callback_registration_ruled_out": False,
            "incoming_indirect_entry_ruled_out": False,
            "runtime_generated_or_copied_carrier_pointers_ruled_out": False,
            "runtime_generated_selected_wheel_pointer_stores_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "p13a_slot0_complete": False,
            "p13a_slot1_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only the two raw FUN_0076d100-RVA byte matches retained by the merged whole-image scan.",
            "Both matches are machine-proven cross-element byte sequences inside 256xDWORD tables; this does not rule out separately relocated, encoded, reconstructed, copied or runtime-generated carrier pointers.",
            "The table classification is structural (ordered u32 elements consumed by binary-search-style machine code); no higher-level table meaning is required or claimed.",
            "No global callback/indirect-entry, stored-or-escaped-alias, slot0/slot1 or aggregate P1.3 gate is promoted."
        ],
        "next_step": (
            "Remove raw exact-carrier absolute-VA/RVA literals from the callback seed frontier and trace relocation records, encoded/reconstructed/runtime-generated carrier pointers, "
            "plus selected-wheel data-pointer persistence."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--upstream", type=Path, default=Path("evidence/p1a_p13a_exact_carrier_text_rva_literal_closure.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = analyze(args.executable, args.upstream)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
