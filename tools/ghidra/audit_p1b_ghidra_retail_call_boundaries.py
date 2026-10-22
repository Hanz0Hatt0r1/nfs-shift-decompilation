#!/usr/bin/env python3
"""Cross-check Ghidra direct CALL starts against PC retail objdump boundaries."""
from __future__ import annotations

import argparse
import bisect
import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORMAT = "SHIFT.P1B.GhidraRetailDirectCallBoundaryAudit/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
INSN = re.compile(
    r"^\s*([0-9a-fA-F]+):\s+((?:[0-9a-fA-F]{2}\s+)+)\s*"
    r"([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$"
)
GHIDRA_RUNNER = ROOT / "tools/ghidra/run_p1b_manager374_helper_setter_ghidra_frontier.py"
RETAIL_PROBE = ROOT / "tools/ghidra/analyze_p1b_manager374_helper_returned_materialized_targets.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise ValueError(f"cannot load analyzer: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def raw_rows(executable: Path) -> list[tuple[int, int, str, str]]:
    proc = subprocess.run(
        ["objdump", "-d", "-Mintel", str(executable)],
        capture_output=True,
        text=True,
        check=True,
        errors="replace",
    )
    rows = []
    for line in proc.stdout.splitlines():
        match = INSN.match(line)
        if match:
            rows.append((
                int(match.group(1), 16),
                len(match.group(2).split()),
                match.group(3).lower(),
                re.sub(r"\s+", " ", match.group(4).strip()).replace(", ", ","),
            ))
    return rows


def audit_rows(ghidra_rows, retail_rows, parse_direct_target) -> dict:
    retail_starts = {address: (length, mnemonic, operands)
                     for address, length, mnemonic, operands in retail_rows}
    retail_addresses = [address for address, _length, _mnemonic, _operands in retail_rows]
    retail_direct_calls = {}
    for address, _length, mnemonic, operands in retail_rows:
        if mnemonic == "call":
            retail_direct_calls[address] = parse_direct_target(operands)

    confirmed = 0
    mismatches = []
    for address, raw_mnemonic, operands in ghidra_rows:
        mnemonic = raw_mnemonic.lower()
        if mnemonic != "call":
            continue
        target = parse_direct_target(operands)
        if target is None:
            continue
        if retail_direct_calls.get(address) == target:
            confirmed += 1
            continue

        index = bisect.bisect_right(retail_addresses, address) - 1
        covering = None
        if index >= 0:
            start, length, raw_mnemonic, raw_operands = retail_rows[index]
            if start < address < start + length:
                covering = (start, length, raw_mnemonic, raw_operands)
        if covering:
            start, length, raw_mnemonic, raw_operands = covering
            reason = "inside_retail_instruction"
            retail_instruction = {
                "address": f"0x{start:08x}",
                "length": length,
                "mnemonic": raw_mnemonic,
                "operands": raw_operands,
            }
        elif address in retail_starts:
            length, raw_mnemonic, raw_operands = retail_starts[address]
            reason = "retail_boundary_is_not_matching_direct_call"
            retail_instruction = {
                "address": f"0x{address:08x}",
                "length": length,
                "mnemonic": raw_mnemonic,
                "operands": raw_operands,
            }
        else:
            reason = "no_retail_objdump_instruction_at_callsite"
            retail_instruction = None

        mismatches.append({
            "callsite": f"0x{address:08x}",
            "ghidra_target": f"0x{target:08x}",
            "reason": reason,
            "retail_instruction": retail_instruction,
        })

    return {
        "ghidra_direct_call_count": confirmed + len(mismatches),
        "confirmed_retail_direct_call_count": confirmed,
        "ghidra_direct_call_boundary_mismatch_count": len(mismatches),
        "ghidra_direct_call_boundary_mismatches": mismatches,
    }


def run(executable: Path, instruction_stream: Path) -> dict:
    digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    if digest != RETAIL_SHA256:
        raise ValueError(f"unexpected executable SHA: {digest}")

    ghidra_runner = load_module(GHIDRA_RUNNER, "p1b_ghidra_frontier_runner")
    retail_probe = load_module(RETAIL_PROBE, "p1b_manager374_helper_return_probe")
    header, ghidra, stream_sha256 = ghidra_runner.read_stream(instruction_stream)
    retail = raw_rows(executable)
    surface = audit_rows(ghidra, retail, retail_probe.parse_direct_target)
    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": digest,
            "ghidra_executable_md5": header["executable_md5"].lower(),
            "canonical_instruction_stream_sha256": stream_sha256,
            "ghidra_instruction_count": len(ghidra),
            "retail_objdump_instruction_count": len(retail),
        },
        "surface": surface,
        "limits": [
            "This cross-check validates direct CALL instruction starts and targets only; it does not merge or replace either decoder stream.",
            "A mismatch identifies a Ghidra-only direct CALL boundary in this retail objdump listing; it does not by itself classify callees or global pointer provenance.",
            "External modules, runtime-generated code, and other decoder disagreements remain outside this bounded audit.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("instruction_stream", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = run(args.executable, args.instruction_stream)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
