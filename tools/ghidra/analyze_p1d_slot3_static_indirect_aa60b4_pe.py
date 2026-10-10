#!/usr/bin/env python3
"""Resolve FUN_00770e80 call [0x00aa60b4] through the PE import table.

The on-disk FirstThunk dword is an IMAGE_IMPORT_BY_NAME RVA, not a code VA.
At load time Windows resolves this IAT slot to KERNEL32!InterlockedExchange.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

FORMAT = "SHIFT.P1D.Slot3StaticIndirectAA60B4Closure/2"
SUPERSEDES = "SHIFT.P1D.Slot3StaticIndirectAA60B4Closure/1"
EXE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
SLOT_VA = 0x00AA60B4
SLOT_RVA = 0x006A60B4
CALLSITES = [0x00770EC4, 0x00770F41]
IMPORT_DLL = "KERNEL32.dll"
IMPORT_NAME = "InterlockedExchange"
IMPORT_HINT = 0x0229
IMPORT_NAME_RVA = 0x00778052
IMPORT_DESCRIPTOR_RVA = 0x007776BC
ORIGINAL_FIRST_THUNK_RVA = 0x00777938
FIRST_THUNK_RVA = 0x006A6088
IMPORT_INDEX = 11
CALL_ENCODING = bytes.fromhex("ff15b460aa00")
CALL1_WINDOW = (0x00770EBB, 0x00770ECA, "687df04bb024afe13a22da177fd986c83e4fe3f1edcc273a20cad5e8737a1ce3")
CALL2_WINDOW = (0x00770F0D, 0x00770F47, "48505813af30c6aebc2287761d0793038d771593a40cd594dc8c831eb7355273")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_pe32(data: bytes) -> dict:
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise ValueError("not a PE image")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("missing PE signature")
    section_count = struct.unpack_from("<H", data, pe + 6)[0]
    optional_size = struct.unpack_from("<H", data, pe + 20)[0]
    optional = pe + 24
    if struct.unpack_from("<H", data, optional)[0] != 0x10B:
        raise ValueError("expected PE32")
    image_base = struct.unpack_from("<I", data, optional + 28)[0]
    import_rva, import_size = struct.unpack_from("<II", data, optional + 104)
    table = optional + optional_size
    sections = []
    for i in range(section_count):
        off = table + i * 40
        sections.append({
            "name": data[off:off + 8].split(b"\0", 1)[0].decode("ascii", errors="replace"),
            "virtual_size": struct.unpack_from("<I", data, off + 8)[0],
            "rva": struct.unpack_from("<I", data, off + 12)[0],
            "raw_size": struct.unpack_from("<I", data, off + 16)[0],
            "raw_offset": struct.unpack_from("<I", data, off + 20)[0],
        })
    return {
        "image_base": image_base,
        "import_rva": import_rva,
        "import_size": import_size,
        "sections": sections,
    }


def rva_to_offset(pe: dict, rva: int, size: int = 1) -> int:
    for section in pe["sections"]:
        if section["rva"] <= rva and rva + size <= section["rva"] + section["raw_size"]:
            return section["raw_offset"] + (rva - section["rva"])
    raise ValueError(f"RVA 0x{rva:08x} is not file-backed")


def read_rva(data: bytes, pe: dict, rva: int, size: int) -> bytes:
    off = rva_to_offset(pe, rva, size)
    return data[off:off + size]


def read_va(data: bytes, pe: dict, va: int, size: int) -> bytes:
    return read_rva(data, pe, va - pe["image_base"], size)


def c_string(data: bytes, pe: dict, rva: int) -> str:
    off = rva_to_offset(pe, rva)
    end = data.index(b"\0", off)
    return data[off:end].decode("ascii", errors="strict")


def section_for_rva(pe: dict, rva: int) -> str:
    for section in pe["sections"]:
        if section["rva"] <= rva < section["rva"] + max(section["virtual_size"], section["raw_size"]):
            return section["name"]
    raise ValueError(f"RVA 0x{rva:08x} has no section")


def resolve_iat_slot(data: bytes, pe: dict, slot_rva: int) -> dict:
    descriptor_rva = pe["import_rva"]
    while True:
        raw = read_rva(data, pe, descriptor_rva, 20)
        oft, timestamp, forwarder, name_rva, first_thunk = struct.unpack("<IIIII", raw)
        if not any((oft, timestamp, forwarder, name_rva, first_thunk)):
            break
        dll = c_string(data, pe, name_rva)
        lookup = oft or first_thunk
        index = 0
        while True:
            entry = struct.unpack("<I", read_rva(data, pe, lookup + index * 4, 4))[0]
            if entry == 0:
                break
            current_slot = first_thunk + index * 4
            if current_slot == slot_rva:
                if entry & 0x80000000:
                    return {
                        "descriptor_rva": descriptor_rva,
                        "dll": dll,
                        "original_first_thunk_rva": oft,
                        "first_thunk_rva": first_thunk,
                        "index": index,
                        "ordinal": entry & 0xFFFF,
                    }
                hint = struct.unpack("<H", read_rva(data, pe, entry, 2))[0]
                name = c_string(data, pe, entry + 2)
                on_disk_iat = struct.unpack("<I", read_rva(data, pe, current_slot, 4))[0]
                return {
                    "descriptor_rva": descriptor_rva,
                    "dll": dll,
                    "original_first_thunk_rva": oft,
                    "first_thunk_rva": first_thunk,
                    "index": index,
                    "import_name_rva": entry,
                    "hint": hint,
                    "name": name,
                    "on_disk_first_thunk_value": on_disk_iat,
                }
            index += 1
        descriptor_rva += 20
    raise ValueError(f"IAT slot RVA 0x{slot_rva:08x} not found in import descriptors")


def verify_window(data: bytes, pe: dict, spec: tuple[int, int, str]) -> dict:
    start, stop, expected_hash = spec
    raw = read_va(data, pe, start, stop - start)
    actual_hash = hashlib.sha256(raw).hexdigest()
    if actual_hash != expected_hash:
        raise ValueError(f"caller window drift at 0x{start:08x}: {actual_hash}")
    return {"start": f"0x{start:08x}", "stop": f"0x{stop:08x}", "sha256": actual_hash, "bytes": raw.hex()}


def analyze(exe: Path) -> dict:
    data = exe.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXE_SHA256:
        raise ValueError(f"unexpected SHIFT.exe SHA-256: {digest}")
    pe = parse_pe32(data)
    if pe["image_base"] != 0x00400000:
        raise ValueError(f"unexpected image base: 0x{pe['image_base']:08x}")

    resolved = resolve_iat_slot(data, pe, SLOT_RVA)
    expected = {
        "descriptor_rva": IMPORT_DESCRIPTOR_RVA,
        "dll": IMPORT_DLL,
        "original_first_thunk_rva": ORIGINAL_FIRST_THUNK_RVA,
        "first_thunk_rva": FIRST_THUNK_RVA,
        "index": IMPORT_INDEX,
        "import_name_rva": IMPORT_NAME_RVA,
        "hint": IMPORT_HINT,
        "name": IMPORT_NAME,
        "on_disk_first_thunk_value": IMPORT_NAME_RVA,
    }
    if resolved != expected:
        raise ValueError(f"IAT import resolution drift: {resolved}")
    if section_for_rva(pe, SLOT_RVA) != ".rdata" or section_for_rva(pe, IMPORT_NAME_RVA) != ".rdata":
        raise ValueError("IAT/name section drift")

    callsites = []
    for site in CALLSITES:
        raw = read_va(data, pe, site, 6)
        if raw != CALL_ENCODING:
            raise ValueError(f"callsite drift at 0x{site:08x}: {raw.hex()}")
        callsites.append({"address": f"0x{site:08x}", "encoding": "ff 15 b4 60 aa 00"})

    call1 = verify_window(data, pe, CALL1_WINDOW)
    call2 = verify_window(data, pe, CALL2_WINDOW)
    if call1["bytes"] != "6a018d862040000050ff15b460aa00":
        raise ValueError("first InterlockedExchange argument setup drift")
    if not call2["bytes"].startswith("6a02") or "8d862040000050" not in call2["bytes"] or not call2["bytes"].endswith("ff15b460aa00"):
        raise ValueError("second InterlockedExchange argument setup drift")

    return {
        "format": FORMAT,
        "version": 2,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "supersedes": SUPERSEDES,
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": digest,
            "pe_import_table_adjudicates_indirect_target": True,
        },
        "iat": {
            "slot_va": "0x00aa60b4",
            "slot_rva": "0x006a60b4",
            "slot_section": ".rdata",
            "import_descriptor_rva": "0x007776bc",
            "dll": IMPORT_DLL,
            "original_first_thunk_rva": "0x00777938",
            "first_thunk_rva": "0x006a6088",
            "thunk_index": IMPORT_INDEX,
            "import_name_rva": "0x00778052",
            "import_hint": IMPORT_HINT,
            "import_name": IMPORT_NAME,
            "on_disk_first_thunk_value": "0x00778052",
            "on_disk_value_semantics": "IMAGE_IMPORT_BY_NAME RVA, not code VA",
            "runtime_slot_semantics": "loader-resolved KERNEL32!InterlockedExchange address",
        },
        "callsites": [
            {
                **callsites[0],
                "operation": "InterlockedExchange((LONG volatile*)(HDVehicle+0x4020), 1)",
                "target_argument": "HDVehicle+0x4020",
                "value_argument": 1,
            },
            {
                **callsites[1],
                "operation": "InterlockedExchange((LONG volatile*)(HDVehicle+0x4020), 2)",
                "target_argument": "HDVehicle+0x4020",
                "value_argument": 2,
            },
        ],
        "verified_caller_windows": [call1, call2],
        "adjudication": {
            "fun00770e80_aa60b4_import_indirect_subset_complete": True,
            "aa60b4_runtime_unknown_target": False,
            "aa60b4_runtime_import": "KERNEL32!InterlockedExchange",
            "aa60b4_on_disk_value_is_code_target": False,
            "aa60b4_selected_wheel_alias_found": False,
            "aa60b4_exact_hdvehicle_root_persistent_store_found": False,
            "aa60b4_scalar_state_target": "HDVehicle+0x4020",
            "other_indirect_entry_ruled_out": False,
            "callee_created_aliases_ruled_out": False,
            "runtime_generated_pointer_stores_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "slot3_writer_provenance_proven": False,
            "p1_3d_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only the two FUN_00770e80 calls through IAT slot 0x00aa60b4.",
            "The on-disk FirstThunk value 0x00778052 is an IMAGE_IMPORT_BY_NAME RVA and must not be executed as a code VA.",
            "Both bounded calls exchange scalar state at HDVehicle+0x4020; they do not materialize/store a selected wheel pointer.",
            "Other indirect calls, callbacks, reconstructed pointers and runtime-generated/copied aliases remain open."
        ],
        "next_step": "Continue with other indirect/callback entry surfaces and runtime-generated/copied selected-wheel pointer paths before changing global alias gates."
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("exe", type=Path)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    try:
        result = analyze(a.exe)
    except ValueError as exc:
        p.error(str(exc))
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if a.output:
        a.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
