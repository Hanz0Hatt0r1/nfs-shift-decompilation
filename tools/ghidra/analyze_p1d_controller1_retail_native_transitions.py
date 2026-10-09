#!/usr/bin/env python3
"""Bound retail x86 native-transition instructions outside function-scoped Ghidra scans.

This tool verifies the authoritative PC retail 1.02 PE hash, disassembles the
`.text` section with GNU objdump, extracts instruction-aligned SYSENTER and
`INT 0x2e` sites, joins them to sized functions from the Ghidra SQLite index,
and counts direct static call/jump references to each transition site.

The result is navigation evidence only. A native-transition instruction does not
identify a Windows service, APC semantics, or Controller #1 target-thread
identity. Indirect entry remains open unless proven separately.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
from pathlib import Path

FORMAT = "SHIFT.P1D.Controller1RetailNativeTransitionSurface/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
SQLITE_FORMATS = {"SHIFT.GhidraSQLiteIndex/1", "SHIFT.GhidraSQLiteIndex/2"}
INS_RE = re.compile(r"^\s*([0-9a-fA-F]+):\s+((?:[0-9a-fA-F]{2}\s+)+)\s*(.*?)\s*$")
TARGET_RE = re.compile(r"\b(?:call|j[a-z]+)\s+(?:0x)?([0-9a-fA-F]+)\b", re.I)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_index_format(db: sqlite3.Connection) -> str:
    row = db.execute("SELECT value FROM metadata WHERE key='format'").fetchone()
    if row is None:
        raise ValueError("SQLite index has no metadata format")
    fmt = str(row[0])
    if fmt not in SQLITE_FORMATS:
        raise ValueError(f"unsupported SQLite index format: {fmt!r}")
    return fmt


def load_functions(db_path: Path) -> tuple[str, list[dict]]:
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    try:
        fmt = read_index_format(db)
        functions = []
        for row in db.execute("SELECT address,name,raw_json FROM functions"):
            address = str(row["address"] or "")
            if not address.startswith("0x"):
                continue
            rec = json.loads(row["raw_json"])
            size = int(rec.get("size", 0) or 0)
            if size <= 0:
                continue
            start = int(address, 16)
            functions.append({
                "start": start,
                "end": start + size,
                "address": f"0x{start:08x}",
                "name": str(row["name"] or rec.get("name") or ""),
                "size": size,
            })
        functions.sort(key=lambda item: item["start"])
        return fmt, functions
    finally:
        db.close()


def containing_function(functions: list[dict], address: int) -> dict | None:
    # 41k functions is small enough for deterministic linear lookup over the few
    # transition candidates. Avoid adding an interval-tree dependency.
    for fn in functions:
        if fn["start"] <= address < fn["end"]:
            return fn
    return None


def run_objdump(exe: Path, objdump: str | None = None) -> str:
    tool = objdump or shutil.which("objdump")
    if not tool:
        raise ValueError("GNU objdump is required but was not found in PATH")
    try:
        proc = subprocess.run(
            [tool, "-Mintel", "-d", str(exe)],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise ValueError(f"objdump failed with status {exc.returncode}: {exc.stderr}") from exc
    return proc.stdout


def parse_instructions(text: str) -> list[dict]:
    rows = []
    for raw in text.splitlines():
        match = INS_RE.match(raw)
        if not match:
            continue
        address = int(match.group(1), 16)
        byte_tokens = match.group(2).split()
        asm = match.group(3).strip()
        if not asm:
            continue
        mnemonic = asm.split(None, 1)[0].lower()
        rows.append({
            "address_int": address,
            "address": f"0x{address:08x}",
            "bytes": "".join(token.lower() for token in byte_tokens),
            "asm": asm,
            "mnemonic": mnemonic,
        })
    return rows


def is_native_transition(ins: dict) -> bool:
    if ins["mnemonic"] == "sysenter":
        return True
    if ins["mnemonic"] != "int":
        return False
    operand = ins["asm"][len("int"):].strip().lower()
    return operand in {"0x2e", "2e", "2eh"}


def direct_static_refs(instructions: list[dict], target: int) -> list[dict]:
    refs = []
    for ins in instructions:
        match = TARGET_RE.search(ins["asm"])
        if not match:
            continue
        if int(match.group(1), 16) != target:
            continue
        refs.append({"address": ins["address"], "asm": ins["asm"]})
    return refs


def analyze(exe: Path, db_path: Path, objdump: str | None = None) -> dict:
    digest = sha256(exe)
    if digest != RETAIL_SHA256:
        raise ValueError(f"unexpected retail PE sha256: {digest}")

    index_format, functions = load_functions(db_path)
    text = run_objdump(exe, objdump=objdump)
    instructions = parse_instructions(text)
    transitions = []
    for ins in instructions:
        if not is_native_transition(ins):
            continue
        fn = containing_function(functions, ins["address_int"])
        refs = direct_static_refs(instructions, ins["address_int"])
        transitions.append({
            "address": ins["address"],
            "mnemonic": ins["mnemonic"],
            "bytes": ins["bytes"],
            "asm": ins["asm"],
            "containing_function": None if fn is None else {
                "address": fn["address"],
                "name": fn["name"],
                "size": fn["size"],
            },
            "outside_sized_ghidra_function": fn is None,
            "direct_static_reference_count": len(refs),
            "direct_static_references": refs,
        })

    sysenter = [row for row in transitions if row["mnemonic"] == "sysenter"]
    int2e = [row for row in transitions if row["mnemonic"] == "int"]
    orphan = [row for row in transitions if row["outside_sized_ghidra_function"]]

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "scope": "Controller #1 direct native-transition timing frontier",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": digest,
            "sqlite_format": index_format,
            "whole_pe_instruction_disassembly": "GNU objdump -Mintel -d",
            "machine_code_is_semantic_authority": True,
        },
        "inventory": {
            "instruction_count": len(instructions),
            "instruction_aligned_native_transition_count": len(transitions),
            "sysenter_count": len(sysenter),
            "int2e_count": len(int2e),
            "outside_sized_ghidra_function_count": len(orphan),
            "transitions": transitions,
        },
        "adjudication": {
            "whole_pe_sysenter_int2e_instruction_surface_bounded": True,
            "function_scoped_ghidra_exporter_covers_all_native_transitions": not orphan,
            "direct_static_entry_to_native_transition_present": any(
                row["direct_static_reference_count"] for row in transitions
            ),
            "indirect_entry_to_native_transition_ruled_out": False,
            "native_service_identity_proven": False,
            "controller1_target_thread_join_complete": False,
            "native_or_syscall_apc_injection_ruled_out": False,
            "controller1_timing_exhaustive": False,
            "p1_3d_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "A SYSENTER/INT 0x2e instruction does not identify a Windows service number or APC semantics.",
            "Zero direct static call/jump references does not rule out indirect entry, computed control flow, callbacks, generated code, or external transfer.",
            "Function containment is taken from sized Ghidra function records; an orphan instruction may still be intentionally executable code.",
            "No timing gate changes without exact service/API identity and Controller #1 target-thread provenance.",
        ],
        "next_step": (
            "Adjudicate the orphan native-transition candidate by recovering all pointer/data references and any computed entry path; if reachable, recover the exact service setup and join its target thread to Controller #1. Separately continue manual PEB/export-walk adjudication."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path)
    parser.add_argument("database", type=Path)
    parser.add_argument("--objdump")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = analyze(args.exe, args.database, objdump=args.objdump)
    except ValueError as exc:
        parser.error(str(exc))
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
