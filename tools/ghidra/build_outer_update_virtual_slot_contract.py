#!/usr/bin/env python3
"""Prove the short dispatch table containing FUN_0079b2d0.

The saved Ghidra export misses this table because the exporter historically
required three consecutive function pointers. The retail PE contains only two
consecutive code pointers at PTR_FUN_00b0b744. Recovered source independently
shows constructor/teardown vptr stores to that address.

This tool cross-checks PE bytes, Ghidra globals/static data/functions/callgraph,
and the pinned SHIFT.exe.c snapshot. It proves table membership and the +0x340
embedded-subobject lifecycle without assigning a final class name or resolving a
specific virtual callsite.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.OuterUpdateVirtualSlotStatic/1"
SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
IMAGE_BASE = 0x00400000

TABLE_VA = 0x00B0B744
SLOT0 = 0x0079BEE0
SLOT1 = 0x0079B2D0
SLOT0_ADDR = "0x0079bee0"
SLOT1_ADDR = "0x0079b2d0"
EXPECTED_TABLE_CODE_REFS = (0x0079B1F4, 0x0079C205)
TEARDOWN = "0x0079b1d0"
CONSTRUCTOR = "0x0079c1c0"
ENCLOSING_CONSTRUCTOR = "0x0072ed20"
ENCLOSING_TEARDOWN = "0x0072f1b0"
UPSTREAM_BATCH = "0x00713050"
OUTER_UPDATE = "0x00770e80"

SOURCE_NAMES = {
    SLOT0_ADDR: "FUN_0079bee0",
    SLOT1_ADDR: "FUN_0079b2d0",
    TEARDOWN: "FUN_0079b1d0",
    CONSTRUCTOR: "FUN_0079c1c0",
    ENCLOSING_CONSTRUCTOR: "FUN_0072ed20",
    ENCLOSING_TEARDOWN: "FUN_0072f1b0",
    UPSTREAM_BATCH: "FUN_00713050",
}


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            yield row


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _extract_function(source: str, name: str) -> dict[str, Any]:
    pattern = re.compile(
        rf"(?m)^(?:{re.escape(name)}|[^\s\n][^\n]*\b{re.escape(name)})\s*\("
    )
    matches = list(pattern.finditer(source))
    if len(matches) != 1:
        raise ValueError(
            f"{name}: expected exactly one function definition; found {len(matches)}"
        )
    start = matches[0].start()
    brace = source.find("{", matches[0].end())
    if brace < 0:
        raise ValueError(f"{name}: opening brace not found")
    depth = 0
    end = None
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                end = index + 1
                break
    if end is None:
        raise ValueError(f"{name}: closing brace not found")
    body = source[start:end]
    return {
        "name": name,
        "body": body,
        "compact": _compact(body),
        "line": source.count("\n", 0, start) + 1,
    }


def _require(function: str, compact_body: str, fragment: str) -> None:
    if _compact(fragment) not in compact_body:
        raise ValueError(f"{function}: required source fragment missing: {fragment}")


def _load_pe_sections(data: bytes) -> tuple[int, list[dict[str, Any]]]:
    if len(data) < 0x40:
        raise ValueError("PE too small")
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if pe_offset + 24 > len(data) or data[pe_offset : pe_offset + 4] != b"PE\0\0":
        raise ValueError("invalid PE signature")
    coff = pe_offset + 4
    _, section_count, _, _, _, optional_size, _ = struct.unpack_from(
        "<HHIIIHH", data, coff
    )
    optional = coff + 20
    if optional + optional_size > len(data):
        raise ValueError("truncated PE optional header")
    magic = struct.unpack_from("<H", data, optional)[0]
    if magic != 0x10B:
        raise ValueError(f"expected PE32 optional header, got 0x{magic:04x}")
    image_base = struct.unpack_from("<I", data, optional + 28)[0]
    section_table = optional + optional_size
    sections = []
    for index in range(section_count):
        off = section_table + index * 40
        if off + 40 > len(data):
            raise ValueError("truncated PE section table")
        name = data[off : off + 8].split(b"\0", 1)[0].decode(
            "ascii", errors="replace"
        )
        virtual_size, rva, raw_size, raw_pointer = struct.unpack_from(
            "<IIII", data, off + 8
        )
        characteristics = struct.unpack_from("<I", data, off + 36)[0]
        sections.append(
            {
                "name": name,
                "rva": rva,
                "virtual_size": virtual_size,
                "raw_pointer": raw_pointer,
                "raw_size": raw_size,
                "execute": bool(characteristics & 0x20000000),
            }
        )
    return image_base, sections


def _section_for_va(
    image_base: int, sections: list[dict[str, Any]], va: int
) -> dict[str, Any] | None:
    rva = va - image_base
    for section in sections:
        span = max(section["virtual_size"], section["raw_size"])
        if section["rva"] <= rva < section["rva"] + span:
            return section
    return None


def _va_to_file(image_base: int, sections: list[dict[str, Any]], va: int) -> int:
    section = _section_for_va(image_base, sections, va)
    if section is None:
        raise ValueError(f"VA 0x{va:08x} is not mapped by a PE section")
    delta = (va - image_base) - section["rva"]
    if delta >= section["raw_size"]:
        raise ValueError(f"VA 0x{va:08x} is not backed by raw PE bytes")
    return section["raw_pointer"] + delta


def _file_to_va(
    image_base: int, sections: list[dict[str, Any]], offset: int
) -> tuple[int, dict[str, Any]]:
    for section in sections:
        if section["raw_pointer"] <= offset < section["raw_pointer"] + section["raw_size"]:
            va = image_base + section["rva"] + (offset - section["raw_pointer"])
            return va, section
    raise ValueError(f"file offset 0x{offset:x} is not inside a raw PE section")


def _u32_occurrences(data: bytes, value: int) -> list[int]:
    needle = struct.pack("<I", value)
    out: list[int] = []
    cursor = 0
    while True:
        offset = data.find(needle, cursor)
        if offset < 0:
            return out
        out.append(offset)
        cursor = offset + 1


def _edge(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "from_function": row.get("from_function"),
        "instruction": row.get("instruction"),
        "to": row.get("to"),
        "to_name": row.get("to_name"),
        "indirect": row.get("indirect"),
    }


def build_outer_update_virtual_slot_contract(
    source_path: Path,
    exe_path: Path,
    ghidra_root: Path,
    *,
    expected_source_sha256: str = SOURCE_SHA256,
    expected_pe_md5: str = PE_MD5,
) -> dict[str, Any]:
    source_bytes = source_path.read_bytes()
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    if source_hash != expected_source_sha256:
        raise ValueError(
            "unexpected SHIFT.exe.c SHA-256: "
            f"expected {expected_source_sha256}, got {source_hash}"
        )
    source = source_bytes.decode("utf-8", errors="strict")

    pe = exe_path.read_bytes()
    pe_md5 = hashlib.md5(pe).hexdigest()
    if pe_md5 != expected_pe_md5:
        raise ValueError(
            f"unexpected SHIFT.exe MD5: expected {expected_pe_md5}, got {pe_md5}"
        )
    image_base, sections = _load_pe_sections(pe)
    if image_base != IMAGE_BASE:
        raise ValueError(f"unexpected PE image base: 0x{image_base:08x}")

    required = (
        "binary.json",
        "functions.jsonl",
        "callgraph.jsonl",
        "globals.jsonl",
        "static_tables.jsonl",
        "vtables.json",
        "constructors.jsonl",
    )
    missing = [name for name in required if not (ghidra_root / name).is_file()]
    if missing:
        raise FileNotFoundError("missing required Ghidra files: " + ", ".join(missing))

    binary = json.loads((ghidra_root / "binary.json").read_text(encoding="utf-8"))
    if binary.get("executable_md5") != expected_pe_md5:
        raise ValueError("Ghidra binary identity does not match retail PE")

    functions = {
        row["address"]: row
        for row in read_jsonl(ghidra_root / "functions.jsonl")
        if isinstance(row.get("address"), str)
    }
    required_functions = set(SOURCE_NAMES) | {OUTER_UPDATE}
    absent = sorted(required_functions - set(functions))
    if absent:
        raise ValueError(
            "required function(s) absent from Ghidra export: " + ", ".join(absent)
        )

    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_jsonl(ghidra_root / "callgraph.jsonl"):
        if row.get("indirect") is not False:
            continue
        src = row.get("from_function")
        dst = row.get("to")
        if isinstance(src, str) and isinstance(dst, str):
            outgoing[src].append(row)
            incoming[dst].append(row)

    def require_direct(src: str, dst: str) -> dict[str, Any]:
        rows = [row for row in outgoing.get(src, []) if row.get("to") == dst]
        if len(rows) != 1:
            raise ValueError(
                f"{src}: expected exactly one direct call to {dst}; found {len(rows)}"
            )
        return rows[0]

    slot0_teardown = require_direct(SLOT0_ADDR, TEARDOWN)
    slot1_outer = require_direct(SLOT1_ADDR, OUTER_UPDATE)
    enclosing_construct = require_direct(ENCLOSING_CONSTRUCTOR, CONSTRUCTOR)
    enclosing_teardown = require_direct(ENCLOSING_TEARDOWN, TEARDOWN)
    if incoming.get(SLOT1_ADDR, []):
        raise ValueError(f"{SLOT1_ADDR}: expected no direct incoming Ghidra call")

    globals_rows = [
        row
        for row in read_jsonl(ghidra_root / "globals.jsonl")
        if row.get("address") == "0x00b0b744"
    ]
    if len(globals_rows) != 1:
        raise ValueError("expected exactly one Ghidra global at 0x00b0b744")
    table_global = globals_rows[0]
    if (
        table_global.get("name") != "PTR_FUN_00b0b744"
        or table_global.get("reference_count") != 2
    ):
        raise ValueError("Ghidra table global metadata changed")

    static_rows = [
        row
        for row in read_jsonl(ghidra_root / "static_tables.jsonl")
        if row.get("address") == "0x00b0b744"
    ]
    if (
        len(static_rows) != 1
        or static_rows[0].get("raw_hex", "").lower() != "e0be7900"
    ):
        raise ValueError("Ghidra static-table head at 0x00b0b744 changed")

    vtable_payload = json.loads(
        (ghidra_root / "vtables.json").read_text(encoding="utf-8")
    )
    if (
        vtable_payload.get("format") != "SHIFT.GhidraVtableCandidates/1"
        or vtable_payload.get("status") != "heuristic-candidates"
    ):
        raise ValueError("unsupported Ghidra vtable candidate export")
    heuristic_table = next(
        (
            row
            for row in vtable_payload.get("vtables", [])
            if row.get("address") == "0x00b0b744"
        ),
        None,
    )
    constructor_rows = [
        row
        for row in read_jsonl(ghidra_root / "constructors.jsonl")
        if row.get("vtable") == "0x00b0b744"
    ]

    table_section = _section_for_va(image_base, sections, TABLE_VA)
    if (
        table_section is None
        or table_section["name"] != ".rdata"
        or table_section["execute"]
    ):
        raise ValueError("dispatch table is not in non-executable .rdata")
    table_off = _va_to_file(image_base, sections, TABLE_VA)
    if table_off + 12 > len(pe):
        raise ValueError("truncated dispatch table bytes")
    raw_entries = struct.unpack_from("<III", pe, table_off)
    if raw_entries[:2] != (SLOT0, SLOT1):
        raise ValueError(
            "short dispatch table slots changed: "
            + ", ".join(f"0x{value:08x}" for value in raw_entries[:2])
        )
    for index, target in enumerate(raw_entries[:2]):
        target_section = _section_for_va(image_base, sections, target)
        if target_section is None or not target_section["execute"]:
            raise ValueError(
                f"table slot {index} target is not executable: 0x{target:08x}"
            )
    third_section = _section_for_va(image_base, sections, raw_entries[2])
    if third_section is not None and third_section["execute"]:
        raise ValueError(
            "dispatch table no longer terminates after two executable slots"
        )

    table_refs = []
    for offset in _u32_occurrences(pe, TABLE_VA):
        va, section = _file_to_va(image_base, sections, offset)
        table_refs.append(
            {
                "file_offset": f"0x{offset:x}",
                "va": f"0x{va:08x}",
                "section": section["name"],
                "execute": section["execute"],
            }
        )
    actual_ref_vas = tuple(sorted(int(row["va"], 16) for row in table_refs))
    if actual_ref_vas != tuple(sorted(EXPECTED_TABLE_CODE_REFS)):
        raise ValueError(
            "absolute table reference set changed: expected "
            f"{[hex(x) for x in EXPECTED_TABLE_CODE_REFS]}, "
            f"got {[hex(x) for x in actual_ref_vas]}"
        )
    if not all(row["execute"] for row in table_refs):
        raise ValueError("dispatch-table absolute reference found outside executable code")

    if _u32_occurrences(pe, SLOT0) != [table_off]:
        raise ValueError("slot-0 function pointer occurrence set changed")
    if _u32_occurrences(pe, SLOT1) != [table_off + 4]:
        raise ValueError("slot-1 function pointer occurrence set changed")

    extracted = {
        address: _extract_function(source, name)
        for address, name in SOURCE_NAMES.items()
    }
    teardown = extracted[TEARDOWN]
    constructor = extracted[CONSTRUCTOR]
    slot0 = extracted[SLOT0_ADDR]
    slot1 = extracted[SLOT1_ADDR]
    enclosing_ctor = extracted[ENCLOSING_CONSTRUCTOR]
    enclosing_dtor = extracted[ENCLOSING_TEARDOWN]
    batch = extracted[UPSTREAM_BATCH]

    for row in (teardown, constructor):
        _require(
            row["name"], row["compact"], "*param_1 = &PTR_FUN_00b0b744;"
        )
    _require(slot0["name"], slot0["compact"], "FUN_0079b1d0(this);")
    _require(
        slot1["name"], slot1["compact"], "FUN_00770e80(&DAT_00c13700"
    )
    _require(
        enclosing_ctor["name"],
        enclosing_ctor["compact"],
        "FUN_0079c1c0(param_1 + 0xd0);",
    )
    _require(
        enclosing_dtor["name"],
        enclosing_dtor["compact"],
        "FUN_0079b1d0((undefined4 *)(param_1 + 0x340));",
    )
    _require(
        batch["name"],
        batch["compact"],
        "FUN_00794a30((void *)(*piVar1 + 0x340)",
    )

    return {
        "format": FORMAT,
        "source": {
            "sha256": source_hash,
            "function_lines": {
                address: row["line"] for address, row in extracted.items()
            },
        },
        "pe": {
            "md5": pe_md5,
            "image_base": f"0x{image_base:08x}",
            "table_file_offset": f"0x{table_off:x}",
            "table_section": table_section["name"],
            "absolute_table_references": table_refs,
        },
        "dispatch_table": {
            "address": "0x00b0b744",
            "ghidra_symbol": table_global.get("name"),
            "ghidra_reference_count": table_global.get("reference_count"),
            "contiguous_executable_slot_count": 2,
            "slots": [
                {
                    "index": 0,
                    "target": SLOT0_ADDR,
                    "name": functions[SLOT0_ADDR].get("name"),
                    "source_role": "teardown-wrapper-calling-FUN_0079b1d0",
                },
                {
                    "index": 1,
                    "target": SLOT1_ADDR,
                    "name": functions[SLOT1_ADDR].get("name"),
                    "source_role": "outer-update-caller-variant",
                },
            ],
            "terminator_dword": f"0x{raw_entries[2]:08x}",
            "present_in_legacy_heuristic_vtable_export": heuristic_table is not None,
            "legacy_constructor_rows_for_table": constructor_rows,
        },
        "lifecycle": {
            "constructor": {
                "function": CONSTRUCTOR,
                "source_line": constructor["line"],
                "vptr_store": "object +0x0 <- 0x00b0b744",
            },
            "teardown": {
                "function": TEARDOWN,
                "source_line": teardown["line"],
                "vptr_store": "object +0x0 <- 0x00b0b744",
            },
            "slot0_wrapper": {
                "function": SLOT0_ADDR,
                "source_line": slot0["line"],
                "direct_call": _edge(slot0_teardown),
            },
        },
        "embedded_subobject": {
            "byte_offset": "0x340",
            "constructor_owner": {
                "function": ENCLOSING_CONSTRUCTOR,
                "source_line": enclosing_ctor["line"],
                "direct_call": _edge(enclosing_construct),
                "source_expression": "param_1 + 0xd0 dwords",
            },
            "teardown_owner": {
                "function": ENCLOSING_TEARDOWN,
                "source_line": enclosing_dtor["line"],
                "direct_call": _edge(enclosing_teardown),
                "source_expression": "param_1 + 0x340 bytes",
            },
            "upstream_batch_matching_offset": {
                "function": UPSTREAM_BATCH,
                "source_line": batch["line"],
                "source_expression": "*record + 0x340 passed to FUN_00794a30",
            },
        },
        "virtual_outer_update_slot": {
            "table": "0x00b0b744",
            "slot_index": 1,
            "target": SLOT1_ADDR,
            "source_line": slot1["line"],
            "direct_outer_update_call": _edge(slot1_outer),
            "direct_incoming_call_count": len(incoming.get(SLOT1_ADDR, [])),
        },
        "scope": {
            "two_slot_object_dispatch_table_proven": True,
            "slot1_membership_proven": True,
            "constructor_and_teardown_vptr_store_proven": True,
            "embedded_subobject_offset_proven": True,
            "specific_virtual_callsite_resolved": False,
            "final_class_name_proven": False,
            "FUN_00794a30_same_dynamic_type_proven": False,
            "rendered_frame_schedule_proven": False,
            "automatic_function_renaming_performed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("exe", type=Path)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = build_outer_update_virtual_slot_contract(
        args.source, args.exe, args.ghidra_export
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print("table: 0x00b0b744 (2 executable slots)")
    print("slot 1: 0x0079b2d0")
    print("embedded subobject offset: 0x340")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
