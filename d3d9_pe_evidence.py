"""Minimal PE image resolver for evidence extraction from SHIFT.exe.

The resolver maps the virtual addresses recovered from Ghidra into file offsets,
without requiring third-party PE libraries. It deliberately distinguishes
file-backed bytes from uninitialized/loader-initialized memory.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any


FORMAT = "SHIFT.PEImageEvidence/1"

DOS_MAGIC = 0x5A4D
PE_SIGNATURE = b"PE\x00\x00"
PE32_MAGIC = 0x10B
PE32PLUS_MAGIC = 0x20B

TARGET_RANGES = {
    "type_code_table": (0x00B90088, 20 * 4),
    "size_table": (0x00B900D8, 17 * 4),
    "usage_table": (0x00B9011C, 9 * 4),
    "usage_index_table": (0x00B90140, 14 * 4),
    "channel_table": (0x00B90178, 22 * 4),
    "type_name_pointer_table": (0x00B901D0, 17 * 4),
}


@dataclass(frozen=True)
class PESection:
    name: str
    virtual_address: int
    virtual_size: int
    raw_pointer: int
    raw_size: int

    @property
    def mapped_size(self) -> int:
        return max(self.virtual_size, self.raw_size)


@dataclass(frozen=True)
class PEImage:
    data: bytes
    image_base: int
    machine: int
    optional_magic: int
    sections: tuple[PESection, ...]

    def section_for_va(self, address: int) -> PESection | None:
        rva = address - self.image_base
        if rva < 0:
            return None
        for section in self.sections:
            if section.virtual_address <= rva < section.virtual_address + section.mapped_size:
                return section
        return None

    def file_offset_for_va(self, address: int) -> int | None:
        section = self.section_for_va(address)
        if section is None:
            return None
        rva = address - self.image_base
        delta = rva - section.virtual_address
        if delta < 0 or delta >= section.raw_size:
            return None
        offset = section.raw_pointer + delta
        if offset < 0 or offset >= len(self.data):
            return None
        return offset

    def read_virtual(self, address: int, size: int) -> bytes | None:
        if size < 0:
            raise ValueError("size must be non-negative")
        parts: list[bytes] = []
        for index in range(size):
            offset = self.file_offset_for_va(address + index)
            if offset is None:
                return None
            parts.append(self.data[offset : offset + 1])
        return b"".join(parts)


class PEFormatError(ValueError):
    pass


def parse_pe(data: bytes, *, image_base_override: int | None = None) -> PEImage:
    if len(data) < 0x40:
        raise PEFormatError("PE image is truncated before DOS header")
    if struct.unpack_from("<H", data, 0)[0] != DOS_MAGIC:
        raise PEFormatError("missing MZ signature")

    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if pe_offset < 0 or pe_offset + 24 > len(data):
        raise PEFormatError("invalid e_lfanew")
    if data[pe_offset : pe_offset + 4] != PE_SIGNATURE:
        raise PEFormatError("missing PE signature")

    file_header = pe_offset + 4
    machine, section_count, _timestamp, _sym_ptr, _sym_count, optional_size, _characteristics = struct.unpack_from(
        "<HHIIIHH", data, file_header
    )

    optional = file_header + 20
    if optional + optional_size > len(data) or optional_size < 32:
        raise PEFormatError("truncated optional header")

    magic = struct.unpack_from("<H", data, optional)[0]
    if magic == PE32_MAGIC:
        if optional_size < 32:
            raise PEFormatError("truncated PE32 optional header")
        image_base = struct.unpack_from("<I", data, optional + 28)[0]
        pointer_size = 4
    elif magic == PE32PLUS_MAGIC:
        if optional_size < 32:
            raise PEFormatError("truncated PE32+ optional header")
        image_base = struct.unpack_from("<Q", data, optional + 24)[0]
        pointer_size = 8
    else:
        raise PEFormatError(f"unsupported optional header magic 0x{magic:04x}")

    if image_base_override is not None:
        image_base = image_base_override

    section_table = optional + optional_size
    sections: list[PESection] = []
    for index in range(section_count):
        offset = section_table + index * 40
        if offset + 40 > len(data):
            raise PEFormatError(f"truncated section header {index}")
        raw_name = data[offset : offset + 8]
        name = raw_name.split(b"\x00", 1)[0].decode("ascii", errors="replace")
        virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from(
            "<IIII", data, offset + 8
        )
        sections.append(
            PESection(
                name=name,
                virtual_address=virtual_address,
                virtual_size=virtual_size,
                raw_pointer=raw_pointer,
                raw_size=raw_size,
            )
        )

    return PEImage(
        data=data,
        image_base=image_base,
        machine=machine,
        optional_magic=magic,
        sections=tuple(sections),
    )


def _read_u32(image: PEImage, address: int) -> int | None:
    payload = image.read_virtual(address, 4)
    return None if payload is None else struct.unpack("<I", payload)[0]


def _read_cstring(image: PEImage, address: int, max_length: int = 256) -> str | None:
    payload = bytearray()
    for index in range(max_length):
        value = image.read_virtual(address + index, 1)
        if value is None:
            return None
        if value == b"\x00":
            break
        byte = value[0]
        if byte < 0x20 or byte > 0x7E:
            return None
        payload.append(byte)
    return payload.decode("ascii", errors="strict")


def analyze_d3d9_pe_image(
    data: bytes,
    *,
    image_base_override: int | None = None,
) -> dict[str, Any]:
    image = parse_pe(data, image_base_override=image_base_override)

    tables: dict[str, Any] = {}
    for name, (address, size) in TARGET_RANGES.items():
        raw = image.read_virtual(address, size)
        section = image.section_for_va(address)
        tables[name] = {
            "address": f"0x{address:08x}",
            "requested_bytes": size,
            "file_backed": raw is not None,
            "section": section.name if section else None,
            "file_offset": (
                None if raw is None else image.file_offset_for_va(address)
            ),
            "hex": None if raw is None else raw.hex(),
        }

    pointer_entries: list[dict[str, Any]] = []
    for ordinal in range(17):
        address = 0x00B901D0 + ordinal * 4
        pointer = _read_u32(image, address)
        entry: dict[str, Any] = {
            "ordinal": ordinal,
            "table_address": f"0x{address:08x}",
            "pointer": None if pointer is None else f"0x{pointer:08x}",
            "string": None,
            "status": "unavailable" if pointer is None else "unresolved",
        }
        if pointer is not None:
            string_value = _read_cstring(image, pointer)
            if string_value is not None:
                entry["string"] = string_value
                entry["status"] = "decoded"
        pointer_entries.append(entry)

    return {
        "format": FORMAT,
        "image": {
            "bytes": len(data),
            "image_base": f"0x{image.image_base:08x}",
            "machine": f"0x{image.machine:04x}",
            "optional_header_magic": f"0x{image.optional_magic:04x}",
            "pointer_size": 8 if image.optional_magic == PE32PLUS_MAGIC else 4,
            "section_count": len(image.sections),
        },
        "sections": [
            {
                "name": section.name,
                "virtual_address": f"0x{section.virtual_address:08x}",
                "virtual_size": section.virtual_size,
                "raw_pointer": section.raw_pointer,
                "raw_size": section.raw_size,
                "mapped_size": section.mapped_size,
            }
            for section in image.sections
        ],
        "tables": tables,
        "type_name_pointers": pointer_entries,
        "conclusions": {
            "file_backed_type_table": tables["type_code_table"]["file_backed"],
            "file_backed_type_name_pointer_table": tables["type_name_pointer_table"]["file_backed"],
            "meb_460_461_to_type_code": {
                "status": "not-proven",
                "detail": "a PE image can expose the declaration-table bytes, but this adapter does not assign MEB properties to type codes automatically",
            },
        },
    }


def analyze_d3d9_pe_image_file(
    path: str | Path,
    *,
    image_base_override: int | None = None,
) -> dict[str, Any]:
    source_path = Path(path)
    report = analyze_d3d9_pe_image(
        source_path.read_bytes(),
        image_base_override=image_base_override,
    )
    report["image"]["path"] = str(source_path)
    return report
