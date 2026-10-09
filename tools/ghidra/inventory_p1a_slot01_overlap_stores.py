#!/usr/bin/env python3
"""Inventory direct PC-retail stores overlapping wheel-local bytes +0x538..+0x53f.

This scanner is deliberately wider than an exact `+0x538` search: a store may
start before the field and overlap it, or may write only the high dword at
`+0x53c`.  The output is a machine-instruction inventory only; receiver identity
is adjudicated by a separate evidence contract.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import re
import sqlite3
import subprocess
from pathlib import Path

EXE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
SQLITE_SHA256 = "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
FORMAT = "SHIFT.P1A.P13ASlot01OverlapStoreInventory/1"
TARGET_START = 0x538
TARGET_END = 0x540

WIDTHS = {
    "BYTE": 1,
    "WORD": 2,
    "DWORD": 4,
    "QWORD": 8,
    "TBYTE": 10,
    "XMMWORD": 16,
    "YMMWORD": 32,
    "ZMMWORD": 64,
}
WRITE_MNEMONICS = {
    "mov",
    "fst",
    "fstp",
    "fist",
    "fistp",
    "movss",
    "movsd",
    "movups",
    "movaps",
    "movdqa",
    "movdqu",
    "movq",
}

LINE_RE = re.compile(r"\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*(.*)$")
MEM_DEST_RE = re.compile(
    r"^(?P<mnem>\w+)\s+"
    r"(?P<size>BYTE|WORD|DWORD|QWORD|TBYTE|XMMWORD|YMMWORD|ZMMWORD)\s+PTR\s+"
    r"\[[^\]]*?(?P<sign>[+-])\s*0x(?P<disp>[0-9a-fA-F]+)\]",
    re.IGNORECASE,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_functions(db_path: Path) -> list[tuple[int, int, str]]:
    uri = f"file:{db_path.resolve()}?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True)
    try:
        rows = []
        for address, name, raw_json in connection.execute(
            "select address,name,raw_json from functions where address is not null"
        ):
            data = json.loads(raw_json)
            size = int(data.get("size", 0))
            if size <= 0:
                continue
            start = int(address, 16)
            rows.append((start, start + size, name))
        rows.sort()
        return rows
    finally:
        connection.close()


def inventory(exe_path: Path, db_path: Path, objdump: str = "objdump") -> dict:
    exe_hash = sha256(exe_path)
    db_hash = sha256(db_path)
    if exe_hash != EXE_SHA256:
        raise ValueError(f"unexpected SHIFT.exe sha256: {exe_hash}")
    if db_hash != SQLITE_SHA256:
        raise ValueError(f"unexpected shift_ghidra.sqlite sha256: {db_hash}")

    functions = load_functions(db_path)
    starts = [row[0] for row in functions]
    disassembly = subprocess.check_output(
        [objdump, "-Mintel", "-d", str(exe_path)],
        text=True,
        errors="replace",
    )

    stores = []
    for line in disassembly.splitlines():
        match = LINE_RE.match(line)
        if not match:
            continue
        address = int(match.group(1), 16)
        instruction = match.group(2).strip()
        operand = MEM_DEST_RE.match(instruction)
        if not operand:
            continue
        mnemonic = operand.group("mnem").lower()
        if mnemonic not in WRITE_MNEMONICS:
            continue
        width_name = operand.group("size").upper()
        width = WIDTHS[width_name]
        displacement = int(operand.group("disp"), 16)
        if operand.group("sign") == "-":
            displacement = -displacement
        write_start = displacement
        write_end = displacement + width
        if write_start >= TARGET_END or write_end <= TARGET_START:
            continue

        index = bisect.bisect_right(starts, address) - 1
        function_name = None
        function_address = None
        if index >= 0:
            start, end, name = functions[index]
            if address < end:
                function_name = name
                function_address = f"0x{start:08x}"

        stores.append(
            {
                "site": f"0x{address:08x}",
                "function": function_name,
                "function_address": function_address,
                "mnemonic": mnemonic,
                "width": width_name.lower(),
                "width_bytes": width,
                "literal_displacement": f"0x{displacement:x}",
                "write_range": [f"0x{write_start:x}", f"0x{write_end:x}"],
                "instruction": instruction,
            }
        )

    stores.sort(key=lambda row: int(row["site"], 16))
    by_function: dict[str, list[str]] = {}
    unowned = []
    for row in stores:
        if row["function"] is None:
            unowned.append(row["site"])
            continue
        by_function.setdefault(row["function"], []).append(row["site"])

    qword_or_wider = [row for row in stores if row["width_bytes"] >= 8]
    partial = [row for row in stores if row["width_bytes"] < 8]
    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "authority": {
            "retail_executable_sha256": exe_hash,
            "ghidra_sqlite_sha256": db_hash,
            "objdump_syntax": "intel",
        },
        "target_local_byte_range": ["0x538", "0x540"],
        "scanned_sized_function_count": len(functions),
        "overlapping_store_count": len(stores),
        "partial_store_count": len(partial),
        "qword_or_wider_store_count": len(qword_or_wider),
        "function_count": len(by_function),
        "unowned_instruction_count": len(unowned),
        "unowned_sites": unowned,
        "stores": stores,
        "sites_by_function": by_function,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path)
    parser.add_argument("sqlite", type=Path)
    parser.add_argument("--objdump", default="objdump")
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()
    try:
        payload = inventory(args.exe, args.sqlite, args.objdump)
    except ValueError as exc:
        parser.error(str(exc))
    rendered = json.dumps(payload, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
