#!/usr/bin/env python3
"""Scan PC retail SHIFT.exe for literal exact-carrier code pointers for P1.3A.

Semantic scope is deliberately narrow: raw little-endian 32-bit absolute VAs for
the 16 exact carrier entrypoints across the complete on-disk image. RVA byte
matches are retained as diagnostics only and never promoted to code-pointer
identity. Runtime-generated/copied/encoded/relocated pointers remain open.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

FORMAT = "SHIFT.P1A.P13AExactCarrierWholeImagePointerLiteralClosure/1"
UPSTREAM_FORMAT = "SHIFT.P1A.P13ASlot01StaticCallbackTargetComposition/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
RETAIL_SIZE = 8_801_792
IMAGE_BASE = 0x00400000

CARRIERS = [
    ("FUN_00758b50", 0x00758B50),
    ("FUN_00755950", 0x00755950),
    ("FUN_00770e80", 0x00770E80),
    ("FUN_00755a60", 0x00755A60),
    ("FUN_00752fc0", 0x00752FC0),
    ("FUN_00760b50", 0x00760B50),
    ("FUN_00763570", 0x00763570),
    ("FUN_00755f80", 0x00755F80),
    ("FUN_0076d100", 0x0076D100),
    ("FUN_00758810", 0x00758810),
    ("FUN_00769ef0", 0x00769EF0),
    ("FUN_007675f0", 0x007675F0),
    ("FUN_007682c0", 0x007682C0),
    ("FUN_00766510", 0x00766510),
    ("FUN_00758fc0", 0x00758FC0),
    ("FUN_00765c40", 0x00765C40),
]

EXPECTED_SECTIONS = [
    (".text", 0x00001000, 6_964_736),
    (".rdata", 0x006A6000, 896_000),
    (".data", 0x00781000, 243_200),
    (".tls", 0x008E9000, 512),
    (".rsrc", 0x008EA000, 290_304),
    (".secu", 0x00931000, 406_016),
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_pe(data: bytes) -> tuple[int, list[dict]]:
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
            "virtual_size": struct.unpack_from("<I", data, off + 8)[0],
            "rva": struct.unpack_from("<I", data, off + 12)[0],
            "raw_size": struct.unpack_from("<I", data, off + 16)[0],
            "raw_offset": struct.unpack_from("<I", data, off + 20)[0],
        })
    return image_base, sections


def file_offset_location(offset: int, image_base: int, sections: list[dict]) -> tuple[str | None, int | None]:
    for section in sections:
        start = section["raw_offset"]
        end = start + section["raw_size"]
        if start <= offset < end:
            va = image_base + section["rva"] + (offset - start)
            return section["name"], va
    return None, None


def find_all(data: bytes, value: int) -> list[int]:
    needle = struct.pack("<I", value)
    result = []
    start = 0
    while True:
        pos = data.find(needle, start)
        if pos < 0:
            return result
        result.append(pos)
        start = pos + 1


def scan_literals(data: bytes, image_base: int, sections: list[dict]) -> tuple[list[dict], list[dict]]:
    absolute_hits = []
    rva_diagnostics = []
    for function, address in CARRIERS:
        for offset in find_all(data, address):
            section, image_va = file_offset_location(offset, image_base, sections)
            absolute_hits.append({
                "function": function,
                "target": f"0x{address:08x}",
                "file_offset": f"0x{offset:08x}",
                "image_va": f"0x{image_va:08x}" if image_va is not None else None,
                "section": section,
                "file_offset_mod4": offset % 4,
            })
        rva = address - image_base
        for offset in find_all(data, rva):
            section, image_va = file_offset_location(offset, image_base, sections)
            rva_diagnostics.append({
                "function": function,
                "target": f"0x{address:08x}",
                "rva_value": f"0x{rva:08x}",
                "file_offset": f"0x{offset:08x}",
                "image_va": f"0x{image_va:08x}" if image_va is not None else None,
                "section": section,
                "file_offset_mod4": offset % 4,
            })
    return absolute_hits, rva_diagnostics


def analyze(executable: Path, upstream_path: Path) -> dict:
    upstream = json.loads(upstream_path.read_text(encoding="utf-8"))
    if upstream.get("format") != UPSTREAM_FORMAT or upstream.get("ready") is not True:
        raise ValueError("unexpected or incomplete static callback-target handoff")
    ua = upstream.get("adjudication", {})
    if ua.get("p13a_exact_carrier_vtable_target_subset_complete") is not True:
        raise ValueError("upstream vtable target subset incomplete")
    if ua.get("p13a_exact_carrier_static_table_literal_pointer_subset_complete") is not True:
        raise ValueError("upstream static-table pointer subset incomplete")
    if upstream.get("carrier_set", {}).get("count") != len(CARRIERS):
        raise ValueError("upstream carrier-count drift")

    data = executable.read_bytes()
    actual_sha = sha256_bytes(data)
    if actual_sha != RETAIL_SHA256:
        raise ValueError(f"unexpected SHIFT.exe SHA-256: {actual_sha}")
    if len(data) != RETAIL_SIZE:
        raise ValueError(f"unexpected SHIFT.exe size: {len(data)}")
    image_base, sections = parse_pe(data)
    if image_base != IMAGE_BASE:
        raise ValueError(f"unexpected image base: 0x{image_base:08x}")
    actual_sections = [(s["name"], s["rva"], s["raw_size"]) for s in sections]
    if actual_sections != EXPECTED_SECTIONS:
        raise ValueError(f"section layout drift: {actual_sections!r}")

    absolute_hits, rva_diagnostics = scan_literals(data, image_base, sections)
    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1A / P1.3A",
        "upstream_contract": UPSTREAM_FORMAT,
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": actual_sha,
            "retail_file_size": len(data),
            "image_base": f"0x{image_base:08x}",
            "whole_file_raw_bytes_adjudicate_literal_presence": True,
        },
        "carrier_set": {
            "count": len(CARRIERS),
            "rows": [{"name": name, "address": f"0x{address:08x}"} for name, address in CARRIERS],
        },
        "pe_sections": [
            {"name": s["name"], "rva": f"0x{s['rva']:08x}", "raw_size": s["raw_size"]}
            for s in sections
        ],
        "absolute_va_literal_scan": {
            "encoding": "little-endian 32-bit absolute VA",
            "searched_file_byte_count": len(data),
            "hit_count": len(absolute_hits),
            "hits": absolute_hits,
        },
        "rva_diagnostics": {
            "semantic_gate": False,
            "encoding": "little-endian 32-bit RVA byte sequence",
            "raw_match_count": len(rva_diagnostics),
            "aligned_file_offset_match_count": sum(1 for row in rva_diagnostics if row["file_offset_mod4"] == 0),
            "matches": rva_diagnostics,
            "interpretation": "RVA byte matches are navigation diagnostics only; numeric equality is not code-pointer identity.",
        },
        "adjudication": {
            "p13a_whole_image_exact_carrier_absolute_va_literal_subset_complete": True,
            "p13a_whole_image_exact_carrier_absolute_va_literal_hit_found": bool(absolute_hits),
            "p13a_whole_image_exact_carrier_absolute_va_literal_hit_count": len(absolute_hits),
            "runtime_callback_registration_ruled_out": False,
            "incoming_indirect_entry_ruled_out": False,
            "relocated_or_rva_encoded_carrier_pointers_ruled_out": False,
            "runtime_generated_or_copied_carrier_pointers_ruled_out": False,
            "runtime_generated_selected_wheel_pointer_stores_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "p13a_slot0_complete": False,
            "p13a_slot1_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only raw 32-bit absolute-VA literals equal to one of the 16 exact carrier entrypoints anywhere in the on-disk retail image.",
            "Direct rel32 calls are intentionally outside this pointer-literal class and are already covered by the carrier call-target composition.",
            "RVA byte-sequence matches are retained only as diagnostics; they are not treated as callback/function-pointer identity.",
            "Relocated, encoded, copied, reconstructed or runtime-generated pointers plus incoming indirect entry remain open."
        ],
        "next_step": (
            "Use whole-image machine references and runtime/dataflow evidence to bound relocated/RVA-encoded or runtime-generated carrier pointers, "
            "then join any positive callback registration to its eventual indirect consumer."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--upstream", type=Path, default=Path("evidence/p1a_p13a_slot01_static_callback_target_composition.json"))
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
