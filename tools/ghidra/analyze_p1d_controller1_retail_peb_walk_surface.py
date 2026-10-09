#!/usr/bin/env python3
"""Bound the standard x86 FS:[0x30] PEB export-walk surface in retail SHIFT.

This is a narrow negative proof for the classic user-mode resolver shape that
starts by reading the x86 PEB from FS:[0x30]. It does not rule out module bases
obtained from imports, loader APIs, globals, callbacks, generated code, or other
TEB/PEB derivations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

FORMAT = "SHIFT.P1D.Controller1RetailPebWalkSurface/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
INS_RE = re.compile(r"^\s*([0-9a-fA-F]+):\s+((?:[0-9a-fA-F]{2}\s+)+)\s*(.*?)\s*$")
FS_RE = re.compile(r"\bfs\s*:", re.I)
FS30_RE = re.compile(
    r"\bfs\s*:\s*(?:\[[^\]]*?(?:0x)?0*30(?:h)?[^\]]*\]|(?:0x)?0*30(?:h)?\b)",
    re.I,
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_objdump(exe: Path, objdump: str | None = None) -> str:
    tool = objdump or shutil.which("objdump")
    if not tool:
        raise ValueError("GNU objdump is required but was not found in PATH")
    try:
        return subprocess.run(
            [tool, "-Mintel", "-d", str(exe)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except subprocess.CalledProcessError as exc:
        raise ValueError(f"objdump failed with status {exc.returncode}: {exc.stderr}") from exc


def parse_instructions(text: str) -> list[dict]:
    rows = []
    for raw in text.splitlines():
        match = INS_RE.match(raw)
        if not match:
            continue
        asm = match.group(3).strip()
        if not asm:
            continue
        address = int(match.group(1), 16)
        rows.append({
            "address": f"0x{address:08x}",
            "bytes": "".join(match.group(2).split()).lower(),
            "asm": asm,
        })
    return rows


def fs30_access(ins: dict) -> bool:
    return bool(FS30_RE.search(str(ins.get("asm", ""))))


def analyze(exe: Path, objdump: str | None = None) -> dict:
    digest = sha256(exe)
    if digest != RETAIL_SHA256:
        raise ValueError(f"unexpected retail PE sha256: {digest}")

    instructions = parse_instructions(run_objdump(exe, objdump=objdump))
    fs_rows = [row for row in instructions if FS_RE.search(row["asm"])]
    fs30_rows = [row for row in fs_rows if fs30_access(row)]

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "scope": "Controller #1 standard x86 PEB/manual-export-walk frontier",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": digest,
            "whole_pe_instruction_disassembly": "GNU objdump -Mintel -d",
            "machine_code_is_semantic_authority": True,
        },
        "inventory": {
            "instruction_count": len(instructions),
            "fs_segment_instruction_count": len(fs_rows),
            "fs30_peb_access_count": len(fs30_rows),
            "fs30_peb_accesses": fs30_rows,
        },
        "adjudication": {
            "whole_pe_fs30_surface_bounded": True,
            "standard_fs30_peb_entry_present": bool(fs30_rows),
            "standard_fs30_peb_export_walk_ruled_out": not fs30_rows,
            "all_manual_export_resolution_ruled_out": False,
            "loader_api_or_import_derived_module_base_ruled_out": False,
            "generated_or_runtime_code_ruled_out": False,
            "hashed_or_generated_resolution_ruled_out": False,
            "native_or_syscall_apc_injection_ruled_out": False,
            "controller1_timing_exhaustive": False,
            "p1_3d_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only the classic direct FS:[0x30] PEB entry shape over the static retail instruction stream.",
            "A module base can still come from GetModuleHandle/LoadLibrary, imports, globals, caller arguments, alternate TEB derivation, generated code, or another resolver.",
            "Absence of FS:[0x30] does not prove absence of manual PE export parsing after a module base is acquired by another route.",
            "Controller #1 timing remains fail-closed until all remaining indirect/native mechanisms and target-thread identity are adjudicated.",
        ],
        "next_step": (
            "Bound manual export parsing fed by non-PEB module-base sources and continue the orphan SYSENTER 0x004209c8 indirect-entry/service-identity frontier."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path)
    parser.add_argument("--objdump")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = analyze(args.exe, objdump=args.objdump)
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
