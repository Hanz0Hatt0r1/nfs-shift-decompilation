#!/usr/bin/env python3
"""Bound the #1699 native/manual APC primitive heuristic directly from retail PE.

This tool joins GNU objdump instruction text to the function intervals exported in
shift_ghidra.sqlite.  It is intentionally narrow: it can close the exact
FS:[0x30] + PE-export-offset heuristic and direct SYSENTER/INT 0x2e instructions
inside known retail functions.  It does not claim a universal no-APC theorem.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import re
import sqlite3
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

FORMAT = "SHIFT.P1D.Controller1NativePrimitivePEClosure/1"
EXPECTED_PE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
SUPPORTED_INDEX_FORMATS = {"SHIFT.GhidraSQLiteIndex/1", "SHIFT.GhidraSQLiteIndex/2"}
INSTRUCTION_RE = re.compile(r"^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*(.*)$")
HEX_3C_RE = re.compile(r"(?<![0-9a-f])0x3c(?![0-9a-f])", re.I)
HEX_78_RE = re.compile(r"(?<![0-9a-f])0x78(?![0-9a-f])", re.I)
INT2E_RE = re.compile(r"^int\s+0x2e\b", re.I)
# GNU objdump renders the x86 PEB load as fs:0x30 or fs:[...0x30...].
PEB_FS30_RE = re.compile(r"fs:(?:0x30\b|\[[^\]]*0x30\b[^\]]*\])", re.I)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_functions(db_path: Path) -> tuple[str, list[dict]]:
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
                "end": start + size,
                "name": name or rec.get("name") or f"FUN_{start:08x}",
                "address": f"0x{start:08x}",
                "size": size,
            })
        functions.sort(key=lambda row: row["start"])
        return fmt_row[0], functions
    finally:
        db.close()


def owner_for(address: int, functions: list[dict], starts: list[int]) -> dict | None:
    index = bisect.bisect_right(starts, address) - 1
    if index < 0:
        return None
    row = functions[index]
    return row if address < row["end"] else None


def nearest_function_bounds(address: int, functions: list[dict], starts: list[int]) -> dict:
    index = bisect.bisect_right(starts, address) - 1
    previous = functions[index] if index >= 0 else None
    next_row = functions[index + 1] if index + 1 < len(functions) else None
    return {
        "previous_function": None if previous is None else {
            "address": previous["address"],
            "name": previous["name"],
            "end": f"0x{previous['end']:08x}",
        },
        "next_function": None if next_row is None else {
            "address": next_row["address"],
            "name": next_row["name"],
        },
    }


def scan(executable: Path, functions: list[dict], objdump: str = "objdump") -> dict:
    starts = [row["start"] for row in functions]
    by_function: dict[str, dict[str, list[dict]]] = defaultdict(
        lambda: {"peb": [], "e_lfanew": [], "export_rva": [], "sysenter": [], "int2e": []}
    )
    fs_owner_count = 0
    fs_raw_count = 0
    fs_forms = Counter()
    raw_sysenter = []
    raw_int2e = []
    raw_peb = []

    proc = subprocess.Popen(
        [objdump, "-d", "-Mintel", str(executable)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        match = INSTRUCTION_RE.match(line)
        if not match:
            continue
        address = int(match.group(1), 16)
        text = match.group(2).strip()
        lower = text.lower()
        interesting = (
            "fs:" in lower or "sysenter" in lower or lower.startswith("int ")
            or "0x3c" in lower or "0x78" in lower
        )
        if not interesting:
            continue
        owner = owner_for(address, functions, starts)
        site = {"address": f"0x{address:08x}", "text": text}

        if "fs:" in lower:
            fs_raw_count += 1
            if owner is not None:
                fs_owner_count += 1
                operand = lower[lower.index("fs:"):]
                fs_forms[operand] += 1
            if PEB_FS30_RE.search(lower):
                raw_peb.append({**site, "function": None if owner is None else owner["address"]})
                if owner is not None:
                    by_function[owner["address"]]["peb"].append(site)

        if lower.startswith("sysenter"):
            raw_sysenter.append({**site, "function": None if owner is None else owner["address"]})
            if owner is not None:
                by_function[owner["address"]]["sysenter"].append(site)
        if INT2E_RE.search(lower):
            raw_int2e.append({**site, "function": None if owner is None else owner["address"]})
            if owner is not None:
                by_function[owner["address"]]["int2e"].append(site)

        if owner is not None and HEX_3C_RE.search(lower):
            by_function[owner["address"]]["e_lfanew"].append(site)
        if owner is not None and HEX_78_RE.search(lower):
            by_function[owner["address"]]["export_rva"].append(site)

    stderr = ""
    if proc.stderr is not None:
        stderr = proc.stderr.read()
    status = proc.wait()
    if status != 0:
        raise ValueError(f"objdump failed with status {status}: {stderr.strip()}")

    manual_candidates = []
    native_candidates = []
    for fn in sorted(by_function):
        group = by_function[fn]
        if group["peb"] and group["e_lfanew"] and group["export_rva"]:
            manual_candidates.append({
                "function": fn,
                "peb_sites": group["peb"],
                "e_lfanew_sites": group["e_lfanew"],
                "export_rva_sites": group["export_rva"],
            })
        if group["sysenter"] or group["int2e"]:
            native_candidates.append({
                "function": fn,
                "sysenter_sites": group["sysenter"],
                "int2e_sites": group["int2e"],
            })

    unowned_sysenter = []
    for row in raw_sysenter:
        if row["function"] is None:
            address = int(row["address"], 16)
            unowned_sysenter.append({**row, **nearest_function_bounds(address, functions, starts)})

    return {
        "function_count": len(functions),
        "fs_access": {
            "raw_disassembly_count": fs_raw_count,
            "owned_function_count": fs_owner_count,
            "exact_fs30_count": len(raw_peb),
            "owned_exact_fs30_count": sum(row["function"] is not None for row in raw_peb),
            "owned_operand_forms": dict(sorted(fs_forms.items())),
        },
        "manual_export_walk": {
            "candidate_function_count": len(manual_candidates),
            "candidate_functions": manual_candidates,
        },
        "direct_native": {
            "raw_sysenter_count": len(raw_sysenter),
            "owned_sysenter_count": sum(row["function"] is not None for row in raw_sysenter),
            "raw_int2e_count": len(raw_int2e),
            "owned_int2e_count": sum(row["function"] is not None for row in raw_int2e),
            "owned_candidate_function_count": len(native_candidates),
            "owned_candidate_functions": native_candidates,
            "unowned_sysenter_sites": unowned_sysenter,
        },
    }


def analyze(executable: Path, database: Path, objdump: str = "objdump") -> dict:
    pe_hash = sha256(executable)
    if pe_hash != EXPECTED_PE_SHA256:
        raise ValueError(f"unexpected retail PE SHA-256: {pe_hash}")
    index_format, functions = load_functions(database)
    result = scan(executable, functions, objdump=objdump)
    owned_native_empty = (
        result["direct_native"]["owned_sysenter_count"] == 0
        and result["direct_native"]["owned_int2e_count"] == 0
    )
    exact_manual_empty = result["manual_export_walk"]["candidate_function_count"] == 0
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
            "sqlite_function_intervals_are_ownership_navigation": True,
        },
        "surface": result,
        "adjudication": {
            "exact_fs30_plus_pe_export_offset_heuristic_has_candidates": not exact_manual_empty,
            "exact_fs30_plus_pe_export_offset_heuristic_ruled_out": exact_manual_empty,
            "defined_function_sysenter_int2e_surface_has_candidates": not owned_native_empty,
            "defined_function_sysenter_int2e_surface_ruled_out": owned_native_empty,
            "unowned_raw_sysenter_surface_ruled_out": False,
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
            "Zero exact FS:[0x30] heuristic candidates does not rule out alternate PEB/module discovery or generated/decoded resolver logic.",
            "Zero SYSENTER/INT 0x2e instructions inside indexed functions does not rule out indirect native stubs, imported ntdll calls, WOW64 transitions, generated code, or execution from bytes not owned by the current function index.",
            "A raw SYSENTER decode outside every indexed function is recorded but not promoted to executable APC semantics without a proven control-flow owner.",
            "No result changes Controller #1 target-thread identity or timing-exhaustiveness gates.",
        ],
        "next_step": (
            "Adjudicate every unowned direct-native byte site by exact control-flow ownership. Separately continue indirect/native-stub and target-thread-handle provenance; only proven API/service identity joined to Controller #1 may advance timing."
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
