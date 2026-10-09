#!/usr/bin/env python3
"""Inventory PC-retail functions that contain both wheel-base +0x400 and stride +0xa80.

The scanner combines authoritative SHIFT.exe machine instructions with function
boundaries from the pinned Ghidra SQLite. It is a bounded candidate inventory,
not a selected-HDVehicle identity proof.
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
FORMAT = "SHIFT.P1A.P13ASlot01SameFunctionTopologyMachineInventory/1"
TARGET_SCALARS = ("0x400", "0xa80", "0x538", "0x938", "0x13b8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_functions(db_path: Path) -> list[tuple[int, int, str]]:
    connection = sqlite3.connect(db_path)
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


def exact_scalar(instruction: str, scalar: str) -> bool:
    pattern = r"(?<![0-9a-fA-F])" + re.escape(scalar) + r"(?![0-9a-fA-F])"
    return re.search(pattern, instruction, re.IGNORECASE) is not None


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

    uses: dict[tuple[int, int, str], dict[str, list[dict]]] = {}
    line_pattern = re.compile(
        r"\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*(.*)$"
    )
    for line in disassembly.splitlines():
        match = line_pattern.match(line)
        if not match:
            continue
        address = int(match.group(1), 16)
        instruction = match.group(2).strip()
        index = bisect.bisect_right(starts, address) - 1
        if index < 0:
            continue
        start, end, name = functions[index]
        if address >= end:
            continue
        hits = [scalar for scalar in TARGET_SCALARS if exact_scalar(instruction, scalar)]
        if not hits:
            continue
        record = uses.setdefault(
            (start, end, name), {scalar: [] for scalar in TARGET_SCALARS}
        )
        for scalar in hits:
            record[scalar].append(
                {
                    "address": f"0x{address:08x}",
                    "instruction": instruction,
                }
            )

    candidates = []
    for (start, end, name), hits in sorted(uses.items()):
        if not hits["0x400"] or not hits["0xa80"]:
            continue
        candidates.append(
            {
                "function_address": f"0x{start:08x}",
                "function_end": f"0x{end:08x}",
                "function_name": name,
                "hits": {key: value for key, value in hits.items() if value},
            }
        )

    return {
        "format": FORMAT,
        "version": 1,
        "authority": {
            "retail_executable_sha256": exe_hash,
            "ghidra_sqlite_sha256": db_hash,
        },
        "scanned_sized_function_count": len(functions),
        "required_same_function_scalars": ["0x400", "0xa80"],
        "context_scalars": ["0x538", "0x938", "0x13b8"],
        "candidate_count": len(candidates),
        "candidates": candidates,
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
