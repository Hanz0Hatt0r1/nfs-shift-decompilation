#!/usr/bin/env python3
"""Extract SHA-locked named PE32 exports; optionally exact-join Ghidra function entries.

No PE dependency, no demangler dependency and NO automatic renaming.
Only original exact VA matches establish an exported function-entry anchor.

Examples:
 python3 tools/ghidra/export_shift_named_pe_symbols.py SHIFT.exe --output-dir /tmp/shift-export-anchors
 python3 tools/ghidra/export_shift_named_pe_symbols.py SHIFT.exe --output-dir /tmp/shift-export-anchors --inventory /path/to/shift.functions.tsv.gz
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import struct
from collections import Counter
from pathlib import Path

RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
GHIDRA_INVENTORY_SHA256 = "8b8b00d8493dba459edf186869ddf492dc26002af3b65d08b6988dc91a87fa24"
FIELDS = ("ordinal", "name", "rva", "va", "section", "kind", "forwarder")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def pe_exports(path: Path) -> tuple[list[dict], dict]:
    if digest(path) != RETAIL_SHA256:
        raise ValueError("SHIFT.exe SHA-256 does not match pinned PC retail 1.02")
    b = path.read_bytes()
    def u16(o): return struct.unpack_from("<H", b, o)[0]
    def u32(o): return struct.unpack_from("<I", b, o)[0]
    def string(o):
        end = b.find(b"\0", o)
        if end < 0:
            raise ValueError("unterminated string in PE export directory")
        return b[o:end].decode("ascii", "replace")
    if b[:2] != b"MZ":
        raise ValueError("bad MZ signature")
    pe = u32(0x3c)
    if b[pe:pe + 4] != b"PE\0\0":
        raise ValueError("bad PE signature")
    machine, count = struct.unpack_from("<HH", b, pe + 4)
    op_size = u16(pe + 20)
    op = pe + 24
    if machine != 0x14c or u16(op) != 0x10b:
        raise ValueError("expected 32-bit i386 PE")
    base = u32(op + 28)
    export_rva, export_size = struct.unpack_from("<II", b, op + 96)
    if not export_rva or not export_size:
        raise ValueError("PE has no export directory")
    sections = []
    for i in range(count):
        pos = op + op_size + i * 40
        name, virtual_size, rva, raw_size, offset = struct.unpack_from("<8sIIII", b, pos)
        sections.append((name.split(b"\0")[0].decode(), rva, max(virtual_size, raw_size), raw_size, offset))
    def section(rva):
        return next((s for s in sections if s[1] <= rva < s[1] + s[2]), None)
    def off(rva, size=1):
        s = section(rva)
        if s is None or rva + size > s[1] + s[3]:
            raise ValueError(f"RVA {rva:#x} not backed by on-disk PE section")
        result = s[4] + rva - s[1]
        if result + size > len(b):
            raise ValueError("truncated export table")
        return result

    p = off(export_rva, 40)
    (_, _, _, _, dll_rva, ordinal_base, n_eat, n_names,
     eat_rva, names_rva, ords_rva) = struct.unpack_from("<IIHHIIIIIII", b, p)
    if n_eat > 100000 or n_names > n_eat:
        raise ValueError("unreasonable export table size")
    eat = struct.unpack_from(f"<{n_eat}I", b, off(eat_rva, n_eat * 4))
    names = struct.unpack_from(f"<{n_names}I", b, off(names_rva, n_names * 4))
    ords = struct.unpack_from(f"<{n_names}H", b, off(ords_rva, n_names * 2))
    rows = []
    for name_rva, ordinal_index in zip(names, ords):
        if ordinal_index >= n_eat:
            raise ValueError("export ordinal index outside EAT")
        rva = eat[ordinal_index]
        forwarded = export_rva <= rva < export_rva + export_size
        s = section(rva)
        rows.append({
            "ordinal": ordinal_base + ordinal_index,
            "name": string(off(name_rva)),
            "rva": f"0x{rva:08x}",
            "va": "" if forwarded or not rva else f"0x{base + rva:08x}",
            "section": s[0] if s else "",
            "kind": "forwarder" if forwarded else "code_candidate" if s and s[0] in (".text", ".secu") else "noncode_or_unknown",
            "forwarder": string(off(rva)) if forwarded else "",
        })
    rows.sort(key=lambda r: r["ordinal"])
    if len(set(row["ordinal"] for row in rows)) != len(rows):
        raise ValueError("duplicate named export ordinals")
    meta = {
        "format": "SHIFT.PE32ExportAnchors/1",
        "authority": {"program": "SHIFT.exe", "executable_sha256": RETAIL_SHA256, "image_base": f"0x{base:08x}"},
        "pe_export_name": string(off(dll_rva)),
        "export_address_table_entries": n_eat,
        "named_export_count": len(rows),
        "unique_address_count": len({r["va"] for r in rows if r["va"]}),
        "counts_by_kind": dict(Counter(r["kind"] for r in rows)),
        "limits": [
            "Names are original MSVC-mangled names; signatures and class layouts are not recovered.",
            "A shared address may have multiple export names, including stub aliases.",
            "Exact Ghidra entry equality is the only asserted join; no fuzzy renaming is performed."
        ]
    }
    return rows, meta


def read_inventory(path: Path) -> dict[str, dict]:
    if digest(path) != GHIDRA_INVENTORY_SHA256:
        raise ValueError("Ghidra inventory SHA-256 differs from the frozen 41,538-function inventory")
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        if not reader.fieldnames or not {"entry", "address_count"}.issubset(reader.fieldnames):
            raise ValueError("Ghidra inventory must have entry and address_count columns")
        result = {}
        for record in reader:
            address = f"0x{int(record['entry'].removeprefix('0x'), 16):08x}"
            if address in result:
                raise ValueError("duplicate Ghidra entry " + address)
            result[address] = record
    if len(result) != 41538:
        raise ValueError(f"expected 41,538 functions; received {len(result)}")
    return result


def write_csv(path: Path, rows: list[dict], fields) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("executable", type=Path)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--inventory", type=Path, help="original pinned shift.functions.tsv.gz from local evidence cache")
    args = ap.parse_args()

    try:
        rows, summary = pe_exports(args.executable)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        write_csv(args.output_dir / "shift_named_exports.csv", rows, FIELDS)
        if args.inventory is not None:
            inventory = read_inventory(args.inventory)
            joined = []
            for row in rows:
                match = inventory.get(row["va"]) if row["va"] else None
                joined.append({
                    **row,
                    "status": "exact_entry_match" if match else "not_in_frozen_entry_inventory",
                    "ghidra_name": (match or {}).get("name", ""),
                    "ghidra_address_count": (match or {}).get("address_count", ""),
                })
            write_csv(args.output_dir / "shift_exports_ghidra_exact_join.csv", joined,
                      (*FIELDS, "status", "ghidra_name", "ghidra_address_count"))
            summary["ghidra_join"] = {
                "inventory_sha256": GHIDRA_INVENTORY_SHA256,
                "inventory_entries": len(inventory),
                "matched_export_names": sum(r["status"] == "exact_entry_match" for r in joined),
                "matched_unique_addresses": len({r["va"] for r in joined if r["status"] == "exact_entry_match"}),
                "unmatched_export_names": sum(r["status"] != "exact_entry_match" for r in joined),
            }
        (args.output_dir / "shift_named_exports_report.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except (OSError, ValueError, struct.error) as exc:
        ap.error(str(exc))
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
