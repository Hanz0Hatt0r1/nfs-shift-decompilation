#!/usr/bin/env python3
"""Extract SHIFT RTTI registrations and correlate them with retail PE vtables."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from collections import defaultdict
from pathlib import Path

FORMAT = "SHIFT-RTTI-REGISTRY/1"

_REGISTRATION_CALL = re.compile(
    r'FUN_00631740\(&(?P<local>local_[0-9a-fA-F]+),'
    r'(?P<name>"(?:[^"\\]|\\.)*"|&(?:DAT|PTR)_[0-9a-fA-F]+)\);'
)
_DESCRIPTOR_ASSIGN = re.compile(
    r'_?DAT_([0-9a-fA-F]{8})\s*=\s*&PTR_FUN_00aaa988\s*;'
)
_SYMBOL_ASSIGN = re.compile(
    r'_?DAT_([0-9a-fA-F]{8})\s*=\s*&'
    r'((?:_?DAT|PTR_[A-Z]+|PTR_PTR)_[0-9a-fA-F]+)\s*;'
)
_FUNCTION_HEADER = re.compile(r'\bvoid\s+(FUN_[0-9a-fA-F]+)\(void\)\s*\{')


def _symbol_address(symbol: str) -> int | None:
    match = re.search(r"_([0-9a-fA-F]{8})$", symbol)
    return int(match.group(1), 16) if match else None


def _registration_function(text: str, position: int) -> str | None:
    prefix = text[max(0, position - 1600):position]
    matches = list(_FUNCTION_HEADER.finditer(prefix))
    return matches[-1].group(1) if matches else None


def _pe_sections(data: bytes) -> tuple[int, dict[str, dict[str, int]]]:
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise ValueError("not a PE image")
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if pe_offset + 24 > len(data) or data[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise ValueError("invalid PE signature")

    section_count = struct.unpack_from("<H", data, pe_offset + 6)[0]
    optional_size = struct.unpack_from("<H", data, pe_offset + 20)[0]
    optional = pe_offset + 24
    if optional + optional_size > len(data):
        raise ValueError("truncated PE optional header")
    magic = struct.unpack_from("<H", data, optional)[0]
    if magic == 0x10B:
        image_base = struct.unpack_from("<I", data, optional + 28)[0]
    elif magic == 0x20B:
        image_base = struct.unpack_from("<Q", data, optional + 24)[0]
    else:
        raise ValueError(f"unsupported PE optional-header magic 0x{magic:04x}")

    table = optional + optional_size
    sections: dict[str, dict[str, int]] = {}
    for index in range(section_count):
        offset = table + index * 40
        if offset + 40 > len(data):
            raise ValueError("truncated PE section table")
        name = data[offset:offset + 8].split(b"\0", 1)[0].decode(
            "ascii", errors="replace"
        )
        virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from(
            "<IIII", data, offset + 8
        )
        sections[name] = {
            "virtual_address": virtual_address,
            "virtual_size": virtual_size,
            "raw_offset": raw_offset,
            "raw_size": raw_size,
        }
    return int(image_base), sections


def _section_bounds(data: bytes, section: dict[str, int]) -> tuple[int, int]:
    start = int(section["raw_offset"])
    end = min(len(data), start + int(section["raw_size"]))
    if start < 0 or start > end:
        raise ValueError("invalid PE section raw range")
    return start, end


def _va_to_offset(
    data: bytes,
    image_base: int,
    sections: dict[str, dict[str, int]],
    address: int,
) -> int | None:
    rva = address - image_base
    for section in sections.values():
        start = int(section["virtual_address"])
        span = max(int(section["virtual_size"]), int(section["raw_size"]))
        if not start <= rva < start + span:
            continue
        delta = rva - start
        if delta >= int(section["raw_size"]):
            return None
        offset = int(section["raw_offset"]) + delta
        return offset if 0 <= offset < len(data) else None
    return None


def _ascii_cstring(data: bytes, offset: int | None, limit: int = 256) -> str | None:
    if offset is None or not 0 <= offset < len(data):
        return None
    end = data.find(b"\0", offset, min(len(data), offset + limit))
    if end < 0 or end == offset:
        return None
    raw = data[offset:end]
    try:
        value = raw.decode("ascii")
    except UnicodeDecodeError:
        return None
    if not all(0x20 <= ord(ch) < 0x7F for ch in value):
        return None
    return value


def _pe_string(
    data: bytes,
    image_base: int,
    sections: dict[str, dict[str, int]],
    address: int,
) -> str | None:
    offset = _va_to_offset(data, image_base, sections, address)
    direct = _ascii_cstring(data, offset)
    if direct is not None:
        return direct
    if offset is None or offset + 4 > len(data):
        return None
    indirect_address = struct.unpack_from("<I", data, offset)[0]
    return _ascii_cstring(
        data,
        _va_to_offset(data, image_base, sections, indirect_address),
    )


def build_pe_rtti_index(data: bytes) -> dict:
    image_base, sections = _pe_sections(data)
    if ".text" not in sections or ".rdata" not in sections:
        raise ValueError("PE lacks .text or .rdata")

    text_section = sections[".text"]
    rdata_section = sections[".rdata"]
    text_start, text_end = _section_bounds(data, text_section)
    rdata_start, rdata_end = _section_bounds(data, rdata_section)
    text_va = image_base + int(text_section["virtual_address"])
    text_virtual_end = text_va + max(
        int(text_section["virtual_size"]), int(text_section["raw_size"])
    )
    rdata_va = image_base + int(rdata_section["virtual_address"])

    getters: dict[int, list[int]] = defaultdict(list)
    for offset in range(text_start, max(text_start, text_end - 5)):
        if data[offset] != 0xB8 or data[offset + 5] != 0xC3:
            continue
        descriptor = struct.unpack_from("<I", data, offset + 1)[0]
        getters[descriptor].append(text_va + (offset - text_start))

    rdata_refs: dict[int, list[int]] = defaultdict(list)
    for offset in range(rdata_start + 4, rdata_end - 3, 4):
        value = struct.unpack_from("<I", data, offset)[0]
        if text_va <= value < text_virtual_end:
            rdata_refs[value].append(offset)

    vtables: dict[int, list[int]] = {}
    for descriptor, addresses in getters.items():
        candidates: set[int] = set()
        for getter in addresses:
            for offset in rdata_refs.get(getter, ()):
                first_entry = struct.unpack_from("<I", data, offset - 4)[0]
                if text_va <= first_entry < text_virtual_end:
                    candidates.add(rdata_va + (offset - rdata_start) - 4)
        vtables[descriptor] = sorted(candidates)

    return {
        "image_base": image_base,
        "sections": sections,
        "getter_addresses": getters,
        "vtable_candidates": vtables,
    }


def extract_registry(source: Path, exe: Path | None = None) -> dict:
    source_data = source.read_bytes()
    text = source_data.decode("utf-8", errors="replace")
    exe_data = exe.read_bytes() if exe is not None else None
    pe = build_pe_rtti_index(exe_data) if exe_data is not None else None

    classes: list[dict] = []
    for match in _REGISTRATION_CALL.finditer(text):
        function_end = text.find("\n}", match.end())
        if function_end < 0:
            continue
        tail = text[match.end():function_end]
        descriptor_match = _DESCRIPTOR_ASSIGN.search(tail)
        if descriptor_match is None:
            continue

        descriptor = int(descriptor_match.group(1), 16)
        token = match.group("name")
        name: str | None = None
        name_source_symbol: str | None = None
        if token.startswith('"'):
            name = bytes(token[1:-1], "utf-8").decode("unicode_escape")
        else:
            name_source_symbol = token[1:]
            if exe_data is not None and pe is not None:
                address = _symbol_address(name_source_symbol)
                if address is not None:
                    name = _pe_string(
                        exe_data,
                        int(pe["image_base"]),
                        pe["sections"],
                        address,
                    )

        assignments: list[tuple[int, str]] = []
        for assignment in _SYMBOL_ASSIGN.finditer(tail):
            assignments.append((
                int(assignment.group(1), 16),
                assignment.group(2).lstrip("_"),
            ))

        parent_symbol = next(
            (rhs for lhs, rhs in assignments if lhs == descriptor + 8),
            None,
        )
        reflection_slot = next(
            (rhs for lhs, rhs in assignments if lhs == descriptor + 12),
            None,
        )
        reflection_metadata = None
        reflection_address = _symbol_address(reflection_slot or "")
        if reflection_slot and reflection_slot.startswith("PTR_PTR_") and reflection_address:
            candidate = f"DAT_{reflection_address + 4:08x}"
            if candidate in text:
                reflection_metadata = candidate

        row = {
            "name": name,
            "name_source_symbol": name_source_symbol,
            "registration_function": _registration_function(text, match.start()),
            "descriptor": descriptor,
            "descriptor_symbol": f"DAT_{descriptor:08x}",
            "parent_symbol": parent_symbol,
            "parent_descriptor": _symbol_address(parent_symbol or ""),
            "parent_class": None,
            "reflection_slot_symbol": reflection_slot,
            "reflection_metadata_symbol": reflection_metadata,
            "rtti_getter_addresses": [],
            "vtable_candidates": [],
            "unique_vtable": None,
        }
        if pe is not None:
            row["rtti_getter_addresses"] = list(
                pe["getter_addresses"].get(descriptor, ())
            )
            row["vtable_candidates"] = list(
                pe["vtable_candidates"].get(descriptor, ())
            )
            row["unique_vtable"] = (
                row["vtable_candidates"][0]
                if len(row["vtable_candidates"]) == 1
                else None
            )
        classes.append(row)

    by_descriptor = {row["descriptor"]: row for row in classes}
    for row in classes:
        parent = by_descriptor.get(row["parent_descriptor"])
        if parent is not None:
            row["parent_class"] = parent["name"]

    return {
        "format": FORMAT,
        "source": str(source),
        "source_sha256": hashlib.sha256(source_data).hexdigest(),
        "exe": str(exe) if exe is not None else None,
        "exe_sha256": (
            hashlib.sha256(exe_data).hexdigest() if exe_data is not None else None
        ),
        "class_count": len(classes),
        "resolved_name_count": sum(row["name"] is not None for row in classes),
        "resolved_parent_count": sum(
            row["parent_class"] is not None for row in classes
        ),
        "reflection_metadata_count": sum(
            row["reflection_metadata_symbol"] is not None for row in classes
        ),
        "rtti_getter_count": sum(
            bool(row["rtti_getter_addresses"]) for row in classes
        ),
        "vtable_candidate_count": sum(
            bool(row["vtable_candidates"]) for row in classes
        ),
        "unique_vtable_count": sum(
            row["unique_vtable"] is not None for row in classes
        ),
        "classes": classes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="recovered SHIFT.exe.c")
    parser.add_argument("--exe", type=Path, help="retail SHIFT.exe")
    parser.add_argument("--prefix", help="keep class names beginning with this prefix")
    parser.add_argument("--name", action="append", help="keep this exact class name")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = extract_registry(args.source, args.exe)
    selected = report["classes"]
    if args.prefix:
        selected = [
            row for row in selected
            if (row["name"] or "").startswith(args.prefix)
        ]
    if args.name:
        wanted = set(args.name)
        selected = [row for row in selected if row["name"] in wanted]

    rendered = dict(report)
    rendered["selected_class_count"] = len(selected)
    rendered["classes"] = selected
    payload = json.dumps(rendered, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
