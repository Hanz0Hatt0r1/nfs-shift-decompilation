#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

SHA = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
FORMAT = "SHIFT.P1B.HDVehicle4330CalleeRegisterWriterProbe/1"
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
    total = 0
    for raw in re.findall(r"[+-]?[^+-]+", expr.replace(" ", "")):
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
        mm = MEM.fullmatch(p[1])
        v = eval_expr(mm.group(1), c) if mm else None
        if v is None:
            c.pop(p[0], None)
        else:
            c[p[0]] = v
    elif mn in {"add", "sub"} and len(p) == 2 and p[0] in REGS:
        n = imm(p[1])
        if p[0] in c and n is not None:
            c[p[0]] = (c[p[0]] + (n if mn == "add" else -n)) & 0xFFFFFFFF
        else:
            c.pop(p[0], None)
    elif mn == "xor" and len(p) == 2 and p[0] == p[1] and p[0] in REGS:
        c[p[0]] = 0
    elif p and p[0] in REGS and mn not in {"cmp", "test", "push"}:
        c.pop(p[0], None)
    return c


def is_boundary(mn: str) -> bool:
    return mn in {"call", "jmp", "ret", "retn", "iret", "iretd", "int", "int3", "ud2"} or mn.startswith("j") or mn.startswith("loop")


def exact_alias_mem_reg(op: str, aliases: dict[str, int]):
    mm = MEM.fullmatch(op)
    if not mm:
        return None
    expr = mm.group(1).replace(" ", "")
    if expr in aliases:
        return expr
    if expr.startswith("+") and expr[1:] in aliases:
        return expr[1:]
    return None


def trace_callee(rows, start_idx: int, incoming: dict[str, int], limit: int = 64):
    aliases = dict(incoming)
    writes = []
    copied_aliases = []
    for address, mn, ops in rows[start_idx:start_idx + limit]:
        p = split_ops(ops)
        if p and mn not in {"cmp", "test"}:
            reg = exact_alias_mem_reg(p[0], aliases)
            if reg is not None:
                writes.append({
                    "site": f"0x{address:08x}",
                    "mnemonic": mn,
                    "destination": p[0],
                    "slot": f"0x{aliases[reg]:08x}",
                    "alias_register": reg,
                    "source": p[1] if len(p) > 1 else None,
                })
        if is_boundary(mn):
            break
        if mn == "mov" and len(p) == 2 and p[0] in REGS:
            dst, src = p
            if src in aliases:
                aliases[dst] = aliases[src]
                copied_aliases.append({"site": f"0x{address:08x}", "dst": dst, "src": src, "slot": f"0x{aliases[src]:08x}"})
            else:
                aliases.pop(dst, None)
        elif mn == "lea" and len(p) == 2 and p[0] in REGS:
            mm = MEM.fullmatch(p[1])
            expr = mm.group(1).replace(" ", "") if mm else ""
            if expr in aliases:
                aliases[p[0]] = aliases[expr]
                copied_aliases.append({"site": f"0x{address:08x}", "dst": p[0], "src": expr, "slot": f"0x{aliases[expr]:08x}"})
            else:
                aliases.pop(p[0], None)
        elif p and p[0] in REGS and mn not in {"cmp", "test", "push"}:
            aliases.pop(p[0], None)
    return writes, copied_aliases


def disassemble(exe: Path):
    p = subprocess.run(["objdump", "-d", "-Mintel", str(exe)], capture_output=True, text=True, check=True, errors="replace")
    rows = []
    for line in p.stdout.splitlines():
        m = I.match(line)
        if m:
            rows.append((int(m.group(1), 16), m.group(2).lower(), norm(m.group(3))))
    return rows


def scan_rows(rows):
    index = {address: i for i, (address, _, _) in enumerate(rows)}
    consts: dict[str, int] = {}
    boundaries = []
    writer_hits = []
    for address, mn, ops in rows:
        p = split_ops(ops)
        if mn == "call":
            live = {reg: value for reg, value in consts.items() if value in SLOTS}
            target = imm(p[0]) if p else None
            if live and target is not None:
                entry = {
                    "call_site": f"0x{address:08x}",
                    "call_target": f"0x{target:08x}",
                    "incoming_register_slots": {reg: f"0x{value:08x}" for reg, value in sorted(live.items())},
                    "callee_present_in_disassembly": target in index,
                    "first_span_writes": [],
                    "callee_alias_copies": [],
                }
                if target in index:
                    writes, copies = trace_callee(rows, index[target], live)
                    entry["first_span_writes"] = writes
                    entry["callee_alias_copies"] = copies
                    writer_hits.extend({"call_site": entry["call_site"], "call_target": entry["call_target"], **w} for w in writes)
                boundaries.append(entry)
            consts.clear()
            continue
        if is_boundary(mn):
            consts.clear()
            continue
        consts = update_consts(mn, ops, consts)
    return {
        "format": FORMAT,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "surface": {
            "direct_call_boundary_count": len(boundaries),
            "direct_call_boundaries": boundaries,
            "first_span_exact_slot_writer_count": len(writer_hits),
            "first_span_exact_slot_writers": writer_hits,
            "selected_slots": [f"0x{x:08x}" for x in sorted(SLOTS)],
        },
        "adjudication": {
            "direct_callee_register_alias_first_span_scanned": True,
            "callee_created_alias_writer_provenance_complete": False,
            "interprocedural_alias_writer_provenance_complete": False,
            "runtime_or_alias_writer_provenance_complete": False,
            "memory_derived_indirect_call_target_identity_complete": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This traces only direct call targets present in the disassembly and only the first straight-line callee span before a control-flow boundary.",
            "Nested calls, branch successors, stack-memory aliases, heap/object replacement, arbitrary runtime mutation and generated/self-modifying code remain open.",
        ],
        "next_step": "Run on authoritative SHIFT.exe; classify any recovered first-span exact-slot writers, then extend surviving callee aliases across branches/nested calls only where evidence requires it.",
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
