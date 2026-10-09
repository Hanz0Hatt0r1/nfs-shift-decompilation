#!/usr/bin/env python3
"""Bound the #1699 native/manual APC primitive heuristic directly from retail PE.

The proof is deliberately based on the whole PE disassembly, not on a guessed
contiguous Ghidra function body.  Ghidra function bodies may contain disjoint
chunks, while the SQLite export stores only entry/size summary data.

This tool can close two exact sub-surfaces:
- the #1699 FS:[0x30] + PE export-offset manual-walk heuristic when no FS:[0x30]
  instruction exists anywhere in the disassembly;
- directly statically referenced SYSENTER/INT 0x2e instructions.

Indirect jumps, generated code, WOW64/native stubs, alternate PEB discovery and
Controller #1 target-thread identity remain fail-closed.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import re
import sqlite3
import subprocess
from collections import deque
from pathlib import Path

FORMAT = "SHIFT.P1D.Controller1NativePrimitivePEClosure/1"
EXPECTED_PE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
SUPPORTED_INDEX_FORMATS = {"SHIFT.GhidraSQLiteIndex/1", "SHIFT.GhidraSQLiteIndex/2"}
INSTRUCTION_RE = re.compile(r"^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*(.*)$")
INT2E_RE = re.compile(r"^int\s+0x2e\b", re.I)
PEB_FS30_RE = re.compile(r"fs:(?:0x30\b|\[[^\]]*0x30\b[^\]]*\])", re.I)
HEX_TOKEN_RE = re.compile(r"0x([0-9a-fA-F]+)")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_function_entries(db_path: Path) -> tuple[str, list[dict]]:
    db = sqlite3.connect(db_path)
    try:
        fmt_row = db.execute("SELECT value FROM metadata WHERE key='format'").fetchone()
        if fmt_row is None or fmt_row[0] not in SUPPORTED_INDEX_FORMATS:
            raise ValueError(f"unsupported SQLite format: {None if fmt_row is None else fmt_row[0]!r}")
        functions = []
        for address, name, raw_json in db.execute("SELECT address,name,raw_json FROM functions"):
            rec = json.loads(raw_json)
            if rec.get("external"):
                continue
            try:
                start = int(address, 16)
                size = int(rec.get("size") or 0)
            except (TypeError, ValueError):
                continue
            if size <= 0:
                continue
            functions.append({
                "start": start,
                "address": f"0x{start:08x}",
                "name": name or rec.get("name") or f"FUN_{start:08x}",
                "size_summary": size,
            })
        functions.sort(key=lambda row: row["start"])
        return fmt_row[0], functions
    finally:
        db.close()


def nearest_entries(address: int, functions: list[dict]) -> dict:
    starts = [row["start"] for row in functions]
    index = bisect.bisect_right(starts, address) - 1
    previous = functions[index] if index >= 0 else None
    next_row = functions[index + 1] if index + 1 < len(functions) else None
    entry = next((row for row in (previous, next_row) if row and row["start"] == address), None)
    return {
        "ghidra_function_entry": None if entry is None else {
            "address": entry["address"], "name": entry["name"]
        },
        "previous_function_entry": None if previous is None else {
            "address": previous["address"], "name": previous["name"]
        },
        "next_function_entry": None if next_row is None else {
            "address": next_row["address"], "name": next_row["name"]
        },
    }


def _run_objdump(executable: Path, objdump: str):
    proc = subprocess.Popen(
        [objdump, "-d", "-Mintel", str(executable)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
    )
    assert proc.stdout is not None
    return proc


def _finish_objdump(proc: subprocess.Popen) -> None:
    stderr = ""
    if proc.stderr is not None:
        stderr = proc.stderr.read()
    status = proc.wait()
    if status != 0:
        raise ValueError(f"objdump failed with status {status}: {stderr.strip()}")


def scan_primitives(executable: Path, objdump: str = "objdump") -> dict:
    fs_count = 0
    fs30_sites = []
    sysenter_sites = []
    int2e_sites = []
    previous = deque(maxlen=8)

    proc = _run_objdump(executable, objdump)
    for line in proc.stdout:
        match = INSTRUCTION_RE.match(line)
        if not match:
            continue
        address = int(match.group(1), 16)
        text = match.group(2).strip()
        lower = text.lower()
        site = {"address": f"0x{address:08x}", "text": text}
        if "fs:" in lower:
            fs_count += 1
            if PEB_FS30_RE.search(lower):
                fs30_sites.append(site)
        if lower.startswith("sysenter"):
            sysenter_sites.append({**site, "preceding_instructions": list(previous)})
        if INT2E_RE.search(lower):
            int2e_sites.append({**site, "preceding_instructions": list(previous)})
        previous.append(site)
    _finish_objdump(proc)
    return {
        "fs_segment_instruction_count": fs_count,
        "exact_fs30_count": len(fs30_sites),
        "exact_fs30_sites": fs30_sites,
        "raw_sysenter_count": len(sysenter_sites),
        "raw_sysenter_sites": sysenter_sites,
        "raw_int2e_count": len(int2e_sites),
        "raw_int2e_sites": int2e_sites,
    }


def scan_direct_flow_refs(executable: Path, targets: set[int], objdump: str = "objdump") -> dict[int, list[dict]]:
    refs = {target: [] for target in targets}
    if not targets:
        return refs
    proc = _run_objdump(executable, objdump)
    for line in proc.stdout:
        match = INSTRUCTION_RE.match(line)
        if not match:
            continue
        address = int(match.group(1), 16)
        text = match.group(2).strip()
        mnemonic = text.split(None, 1)[0].lower() if text else ""
        if not (mnemonic.startswith("j") or mnemonic.startswith("call") or mnemonic.startswith("loop")):
            continue
        for token in HEX_TOKEN_RE.findall(text):
            target = int(token, 16)
            if target in refs:
                refs[target].append({"address": f"0x{address:08x}", "text": text})
    _finish_objdump(proc)
    return refs


def absolute_pointer_count(executable: Path, address: int) -> int:
    needle = address.to_bytes(4, "little", signed=False)
    data = executable.read_bytes()
    count = 0
    start = 0
    while True:
        pos = data.find(needle, start)
        if pos < 0:
            return count
        count += 1
        start = pos + 1


def analyze(executable: Path, database: Path, objdump: str = "objdump") -> dict:
    pe_hash = sha256(executable)
    if pe_hash != EXPECTED_PE_SHA256:
        raise ValueError(f"unexpected retail PE SHA-256: {pe_hash}")
    index_format, functions = load_function_entries(database)
    primitive = scan_primitives(executable, objdump=objdump)
    native_targets = {
        int(row["address"], 16)
        for row in primitive["raw_sysenter_sites"] + primitive["raw_int2e_sites"]
    }
    direct_refs = scan_direct_flow_refs(executable, native_targets, objdump=objdump)

    native_sites = []
    for row in primitive["raw_sysenter_sites"] + primitive["raw_int2e_sites"]:
        address = int(row["address"], 16)
        native_sites.append({
            **row,
            **nearest_entries(address, functions),
            "direct_static_incoming_refs": direct_refs.get(address, []),
            "absolute_pointer_occurrence_count": absolute_pointer_count(executable, address),
        })

    exact_manual_empty = primitive["exact_fs30_count"] == 0
    direct_static_native_empty = all(
        not row["direct_static_incoming_refs"] and row["absolute_pointer_occurrence_count"] == 0
        for row in native_sites
    )
    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": pe_hash,
            "ghidra_sqlite_sha256": sha256(database),
            "ghidra_sqlite_format": index_format,
            "machine_disassembly_is_semantic_authority": True,
            "sqlite_function_entries_are_navigation_only": True,
            "sqlite_size_is_not_assumed_to_be_a_contiguous_function_body": True,
        },
        "surface": {
            "ghidra_function_entry_count": len(functions),
            "fs_access": {
                "raw_disassembly_count": primitive["fs_segment_instruction_count"],
                "exact_fs30_count": primitive["exact_fs30_count"],
                "exact_fs30_sites": primitive["exact_fs30_sites"],
            },
            "manual_export_walk": {
                "exact_fs30_plus_pe_export_offset_candidate_possible": not exact_manual_empty,
                "candidate_count": 0 if exact_manual_empty else None,
            },
            "direct_native": {
                "raw_sysenter_count": primitive["raw_sysenter_count"],
                "raw_int2e_count": primitive["raw_int2e_count"],
                "native_sites": native_sites,
            },
        },
        "adjudication": {
            "exact_fs30_plus_pe_export_offset_heuristic_ruled_out": exact_manual_empty,
            "direct_statically_addressed_sysenter_int2e_surface_ruled_out": direct_static_native_empty,
            "computed_or_indirect_entry_to_native_bytes_ruled_out": False,
            "alternative_peb_acquisition_ruled_out": False,
            "indirect_native_stub_or_function_pointer_ruled_out": False,
            "generated_or_wow64_transition_ruled_out": False,
            "manual_export_walking_ruled_out": False,
            "native_or_syscall_apc_injection_ruled_out": False,
            "controller1_thread_handle_join_complete": False,
            "controller1_timing_exhaustive": False,
            "p1_3d_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "Ghidra function size is a summary count, not assumed to describe a contiguous body; chunked bodies are possible.",
            "Zero exact FS:[0x30] instructions rules out only the exact #1699 PEB heuristic, not alternate PEB/module discovery or generated/decoded resolver logic.",
            "A raw SYSENTER/INT 0x2e site with no direct branch/call or absolute pointer reference can still be reached through computed/indirect control flow; such execution remains open.",
            "Indirect native stubs, imported ntdll calls, WOW64 transitions and generated code remain outside this narrow direct-static surface.",
            "No result changes Controller #1 target-thread identity or timing-exhaustiveness gates."
        ],
        "next_step": (
            "Adjudicate computed/indirect reachability to every raw native-transition byte site, then continue indirect/native-stub and Controller #1 target-thread-handle provenance."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("database", type=Path)
    parser.add_argument("--objdump", default="objdump")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = analyze(args.executable, args.database, objdump=args.objdump)
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
