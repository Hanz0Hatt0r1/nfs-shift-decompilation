#!/usr/bin/env python3
"""Verify the standard PE base-relocation carrier-pointer path is absent.

This closes only Windows PE loader base relocations. Manual image-base addition,
encoded/reconstructed pointers, callback registration, runtime copies and other
computed pointer paths remain open.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

FORMAT = "SHIFT.P1A.P13APeBaseRelocationCarrierClosure/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
RETAIL_SIZE = 8_801_792
IMAGE_BASE = 0x00400000
EXPECTED_CHARACTERISTICS = 0x0103
IMAGE_FILE_RELOCS_STRIPPED = 0x0001
BASE_RELOCATION_DIRECTORY_INDEX = 5
EXPECTED_SECTIONS = [".text", ".rdata", ".data", ".tls", ".rsrc", ".secu"]


def analyze(path: Path) -> dict:
    data = path.read_bytes()
    actual_sha = hashlib.sha256(data).hexdigest()
    if actual_sha != RETAIL_SHA256:
        raise ValueError(f"unexpected SHIFT.exe SHA-256: {actual_sha}")
    if len(data) != RETAIL_SIZE:
        raise ValueError(f"unexpected SHIFT.exe size: {len(data)}")
    if data[:2] != b"MZ":
        raise ValueError("not an MZ image")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("missing PE signature")
    section_count = struct.unpack_from("<H", data, pe + 6)[0]
    optional_size = struct.unpack_from("<H", data, pe + 20)[0]
    characteristics = struct.unpack_from("<H", data, pe + 22)[0]
    if characteristics != EXPECTED_CHARACTERISTICS:
        raise ValueError(f"unexpected file characteristics: 0x{characteristics:04x}")
    opt = pe + 24
    if struct.unpack_from("<H", data, opt)[0] != 0x10B:
        raise ValueError("expected PE32")
    image_base = struct.unpack_from("<I", data, opt + 28)[0]
    if image_base != IMAGE_BASE:
        raise ValueError(f"unexpected image base: 0x{image_base:08x}")
    number_of_rva_and_sizes = struct.unpack_from("<I", data, opt + 92)[0]
    if number_of_rva_and_sizes <= BASE_RELOCATION_DIRECTORY_INDEX:
        raise ValueError("PE data directory table is too short")
    directory = opt + 96 + BASE_RELOCATION_DIRECTORY_INDEX * 8
    reloc_rva, reloc_size = struct.unpack_from("<II", data, directory)
    section_table = opt + optional_size
    sections = []
    for index in range(section_count):
        off = section_table + index * 40
        sections.append(data[off:off + 8].split(b"\0")[0].decode("ascii", "replace"))
    if sections != EXPECTED_SECTIONS:
        raise ValueError(f"section-name drift: {sections!r}")
    reloc_section_present = ".reloc" in sections
    relocs_stripped = bool(characteristics & IMAGE_FILE_RELOCS_STRIPPED)
    if not relocs_stripped:
        raise ValueError("IMAGE_FILE_RELOCS_STRIPPED is no longer set")
    if reloc_rva != 0 or reloc_size != 0:
        raise ValueError("base-relocation directory is no longer empty")
    if reloc_section_present:
        raise ValueError("unexpected .reloc section")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1A / P1.3A",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": actual_sha,
            "retail_file_size": len(data),
            "machine_format_adjudicates": True,
        },
        "pe": {
            "format": "PE32",
            "image_base": f"0x{image_base:08x}",
            "file_characteristics": f"0x{characteristics:04x}",
            "image_file_relocs_stripped": relocs_stripped,
            "number_of_rva_and_sizes": number_of_rva_and_sizes,
            "base_relocation_directory": {
                "index": BASE_RELOCATION_DIRECTORY_INDEX,
                "rva": f"0x{reloc_rva:08x}",
                "size": reloc_size,
            },
            "section_names": sections,
            "reloc_section_present": reloc_section_present,
        },
        "adjudication": {
            "p13a_standard_pe_base_relocation_subset_complete": True,
            "p13a_standard_pe_base_relocation_records_present": False,
            "p13a_pe_loader_base_relocation_carrier_pointer_path_ruled_out": True,
            "manual_imagebase_plus_rva_pointer_construction_ruled_out": False,
            "encoded_or_reconstructed_carrier_pointers_ruled_out": False,
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
            "This closes only IMAGE_DIRECTORY_ENTRY_BASERELOC / Windows loader base-relocation records in the authoritative on-disk PE.",
            "IMAGE_FILE_RELOCS_STRIPPED plus a zero RVA/size relocation directory and no .reloc section do not exclude manual image-base addition, encoded/reconstructed values, runtime registration or copied pointers.",
            "The result does not classify selected-wheel data-pointer persistence and does not promote slot0/slot1 or aggregate P1.3."
        ],
        "next_step": (
            "Trace manual image-base/RVA reconstruction, encoded/runtime-generated carrier code pointers and callback registration; "
            "continue selected-wheel data-pointer persistence independently."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = analyze(args.executable)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
