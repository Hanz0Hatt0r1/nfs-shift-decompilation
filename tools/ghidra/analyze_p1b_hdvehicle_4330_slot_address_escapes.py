#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

SHA = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
FORMAT = "SHIFT.P1B.HDVehicle4330SlotAddressEscapeProbe/1"
SLOTS = {0x00B83DC0, 0x00B83EC0}
REGS = {"eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp"}
I = re.compile(r"^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$")
MEM = re.compile(r"^(?:(?:BYTE|WORD|DWORD|QWORD) PTR )?\[([^\]]+)\]$")
IMM = re.compile(r"^(?:0x([0-9a-fA-F]+)|([0-9]+))$")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip()).replace(", ", ",")


def imm(s: str):
    m = IMM.fullmatch(s)
    if not m:
        return None
    return int(m.group(1), 16) if m.group(1) else int(m.group(2))


def split_ops(ops: str):
    return ops.split(",") if ops else []


def eval_expr(expr: str, consts: dict[str, int]):
    expr = expr.replace(" ", "")
    total = 0
    for raw in re.findall(r"[+-]?[^+-]+", expr):
        sign = -1 if raw.startswith("-") else 1
        term = raw[1:] if raw[:1] in "+-" else raw
        if "*" in term:
            reg, scale = term.split("*", 1)
            n = imm(scale)
            if reg not in consts or n is None:
                return None
            total += sign * consts[reg] * n
        elif term in REGS:
            if term not in consts:
                return None
            total += sign * consts[term]
        else:
            n = imm(term)
            if n is None:
                return None
            total += sign * n
    return total & 0xFFFFFFFF


def update_consts(mn: str, ops: str, consts: dict[str, int]):
    p = split_ops(ops)
    c = dict(consts)
    if mn == "mov" and len(p) == 2 and p[0] in REGS:
        dst, src = p
        n = imm(src)
        if n is not None:
            c[dst] = n & 0xFFFFFFFF
        elif src in c:
            c[dst] = c[src]
        else:
            c.pop(dst, None)
    elif mn == "lea" and len(p) == 2 and p[0] in REGS:
        dst, src = p
        mm = MEM.fullmatch(src)
        v = eval_expr(mm.group(1), c) if mm else None
        if v is None:
            c.pop(dst, None)
        else:
            c[dst] = v
    elif mn in {"add", "sub"} and len(p) == 2 and p[0] in REGS:
        n = imm(p[1])
        if p[0] in c and n is not None:
            c[p[0]] = (c[p[0]] + (n if mn == "add" else -n)) & 0xFFFFFFFF
        else:
            c.pop(p[0], None)
    elif p and p[0] in REGS and mn not in {"cmp", "test", "push"}:
        c.pop(p[0], None)
    return c


def disassemble(exe: Path):
    p = subprocess.run(["objdump", "-d", "-Mintel", str(exe)], capture_output=True, text=True, check=True, errors="replace")
    rows = []
    for line in p.stdout.splitlines():
        m = I.match(line)
        if m:
            rows.append((int(m.group(1), 16), m.group(2).lower(), norm(m.group(3))))
    return rows


def scan_rows(rows):
    consts: dict[str, int] = {}
    pending_pushes = []
    escapes = []
    for a, mn, ops in rows:
        p = split_ops(ops)
        if mn == "push" and len(p) == 1:
            value = consts.get(p[0]) if p[0] in REGS else imm(p[0])
            if value in SLOTS:
                pending_pushes.append({"site": f"0x{a:08x}", "slot": f"0x{value:08x}", "source": p[0]})
        if mn == "call":
            target = p[0] if p else None
            if pending_pushes:
                escapes.append({"call_site": f"0x{a:08x}", "call_target": target, "slot_arguments": list(pending_pushes)})
            pending_pushes.clear()
            consts.clear()
            continue
        if mn in {"jmp", "ret", "retn", "iret", "iretd", "int", "int3", "ud2"} or mn.startswith("j") or mn.startswith("loop"):
            pending_pushes.clear()
            consts.clear()
            continue
        consts = update_consts(mn, ops, consts)
    return {
        "format": FORMAT,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "surface": {
            "slot_address_escape_count": len(escapes),
            "slot_address_escapes": escapes,
            "selected_slots": [f"0x{x:08x}" for x in sorted(SLOTS)],
        },
        "adjudication": {
            "slot_address_direct_callee_escape_subset_scanned": True,
            "interprocedural_alias_writer_provenance_complete": False,
            "runtime_or_alias_writer_provenance_complete": False,
            "memory_derived_indirect_call_target_identity_complete": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This covers only exact slot-address values pushed into direct callees within a bounded local constant-propagation span.",
            "Register arguments not materialized via push, stack aliases, callee-created aliases, heap replacement, runtime mutation and generated/self-modifying code remain open.",
        ],
        "next_step": "Run on authoritative SHIFT.exe, classify each callee receiving an exact selected-slot address, then expand to register-argument and callee-created alias writers.",
    }


def analyze(exe: Path):
    sha = hashlib.sha256(exe.read_bytes()).hexdigest()
    if sha != SHA:
        raise ValueError(f"unexpected executable SHA: {sha}")
    r = scan_rows(disassemble(exe))
    r["authority"] = {"platform": "PC retail 1.02", "retail_executable_sha256": sha}
    return r


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
