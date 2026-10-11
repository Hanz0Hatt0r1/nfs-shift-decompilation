#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330MemoryTargetWriterProvenanceProbe/1"
SHA = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
SLOTS = (0x00B83DC0, 0x00B83EC0)
CALL_SITES = (0x00553247, 0x005539AC)
I = re.compile(r"^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$")
ABS_MEM = re.compile(r"^(?:BYTE|WORD|DWORD|QWORD) PTR \[(0x[0-9a-fA-F]+)\]$")
MEM = re.compile(r"^(?:BYTE|WORD|DWORD|QWORD) PTR \[([^\]]+)\]$")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip()).replace(", ", ",")


def disassemble(exe: Path):
    p = subprocess.run(
        ["objdump", "-d", "-Mintel", str(exe)],
        text=True,
        capture_output=True,
        check=True,
        errors="replace",
    )
    rows = []
    for line in p.stdout.splitlines():
        m = I.match(line)
        if m:
            rows.append((int(m.group(1), 16), m.group(2).lower(), norm(m.group(3))))
    return rows


def split_ops(ops: str):
    return ops.split(",") if ops else []


def absolute_mem(op: str):
    m = ABS_MEM.fullmatch(op)
    return int(m.group(1), 16) if m else None


def refs_slot(ops: str, slot: int) -> bool:
    needle = f"0x{slot:x}"
    return needle in ops.lower()


def scan_rows(rows):
    rows = list(rows)
    by_addr = {a: i for i, (a, _, _) in enumerate(rows)}
    slot_refs = {slot: [] for slot in SLOTS}
    slot_writes = {slot: [] for slot in SLOTS}

    for a, mn, ops in rows:
        parts = split_ops(ops)
        for slot in SLOTS:
            if refs_slot(ops, slot):
                slot_refs[slot].append({"site": f"0x{a:08x}", "mnemonic": mn, "operands": ops})
            if parts and absolute_mem(parts[0]) == slot and mn not in {"cmp", "test"}:
                slot_writes[slot].append({
                    "site": f"0x{a:08x}",
                    "mnemonic": mn,
                    "destination": parts[0],
                    "source": parts[1] if len(parts) > 1 else None,
                })

    calls = []
    for call_site in CALL_SITES:
        idx = by_addr.get(call_site)
        if idx is None:
            calls.append({"call_site": f"0x{call_site:08x}", "present": False})
            continue
        a, mn, ops = rows[idx]
        window = rows[max(0, idx - 4): idx + 1]
        target_loads = []
        for wa, wmn, wops in window:
            p = split_ops(wops)
            if wmn == "mov" and len(p) == 2 and p[0] == "edx":
                mm = MEM.fullmatch(p[1])
                if mm and "+0x4" in mm.group(1).replace(" ", ""):
                    target_loads.append({"site": f"0x{wa:08x}", "source": p[1]})
        calls.append({
            "call_site": f"0x{a:08x}",
            "present": mn == "call",
            "call_operand": ops,
            "nearby_object_plus_4_target_loads": target_loads,
        })

    return {
        "format": FORMAT,
        "ready": True,
        "scope": {
            "object_pointer_slots": [f"0x{x:08x}" for x in SLOTS],
            "positive_call_sites": [f"0x{x:08x}" for x in CALL_SITES],
            "claims_exact_runtime_target_identity": False,
        },
        "slot_reference_counts": {f"0x{k:08x}": len(v) for k, v in slot_refs.items()},
        "slot_write_counts": {f"0x{k:08x}": len(v) for k, v in slot_writes.items()},
        "slot_references": {f"0x{k:08x}": v for k, v in slot_refs.items()},
        "slot_direct_absolute_writes": {f"0x{k:08x}": v for k, v in slot_writes.items()},
        "positive_call_site_shapes": calls,
        "adjudication": {
            "writer_provenance_probe_complete": True,
            "exact_runtime_target_identity_complete": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "next_step": "Run on authoritative SHIFT.exe, then trace every writer/alias feeding 0x00b83dc0 and 0x00b83ec0 and classify the [object+4] targets at 0x00553247 and 0x005539ac.",
    }


def analyze(exe: Path):
    sha = hashlib.sha256(exe.read_bytes()).hexdigest()
    if sha != SHA:
        raise ValueError(f"unexpected executable SHA: {sha}")
    result = scan_rows(disassemble(exe))
    result["authority"] = {"platform": "PC retail 1.02", "retail_executable_sha256": sha}
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("executable", type=Path)
    ap.add_argument("--output", type=Path)
    ns = ap.parse_args()
    text = json.dumps(analyze(ns.executable), indent=2, sort_keys=True) + "\n"
    if ns.output:
        ns.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
