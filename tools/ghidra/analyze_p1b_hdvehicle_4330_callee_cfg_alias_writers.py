#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import deque
from pathlib import Path

SHA = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
FORMAT = "SHIFT.P1B.HDVehicle4330CalleeCFGAliasWriterProbe/1"
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


def exact_alias_mem_reg(op: str, aliases: dict[str, int]):
    mm = MEM.fullmatch(op)
    if not mm:
        return None
    expr = mm.group(1).replace(" ", "")
    return expr if expr in aliases else None


def next_index(rows, idx):
    return idx + 1 if idx + 1 < len(rows) else None


def branch_target(mn: str, ops: str):
    if mn == "jmp" or mn.startswith("j") or mn.startswith("loop"):
        p = split_ops(ops)
        return imm(p[0]) if p else None
    return None


def trace_callee_cfg(rows, start_idx: int, incoming: dict[str, int], limit_states: int = 256):
    index = {a: i for i, (a, _, _) in enumerate(rows)}
    q = deque([(start_idx, dict(incoming))])
    seen = set()
    writes = []
    state_count = 0
    nested_call_boundaries = 0
    unresolved_branch_targets = 0

    while q and state_count < limit_states:
        idx, aliases = q.popleft()
        key = (idx, tuple(sorted(aliases.items())))
        if key in seen:
            continue
        seen.add(key)
        state_count += 1
        address, mn, ops = rows[idx]
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

        if mn == "call":
            nested_call_boundaries += 1
            continue
        if mn in {"ret", "retn", "iret", "iretd", "int", "int3", "ud2"}:
            continue

        new_aliases = update_consts(mn, ops, aliases)
        bt = branch_target(mn, ops)
        if mn == "jmp":
            if bt in index:
                q.append((index[bt], new_aliases))
            else:
                unresolved_branch_targets += 1
            continue
        if mn.startswith("j") or mn.startswith("loop"):
            if bt in index:
                q.append((index[bt], dict(new_aliases)))
            elif bt is not None:
                unresolved_branch_targets += 1
            ni = next_index(rows, idx)
            if ni is not None:
                q.append((ni, new_aliases))
            continue
        ni = next_index(rows, idx)
        if ni is not None:
            q.append((ni, new_aliases))

    return {
        "visited_state_count": state_count,
        "state_limit_hit": bool(q),
        "nested_call_boundary_count": nested_call_boundaries,
        "unresolved_branch_target_count": unresolved_branch_targets,
        "exact_slot_writes": writes,
    }


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
                    "cfg_trace": None,
                }
                if target in index:
                    trace = trace_callee_cfg(rows, index[target], live)
                    entry["cfg_trace"] = trace
                    writer_hits.extend({"call_site": entry["call_site"], "call_target": entry["call_target"], **w} for w in trace["exact_slot_writes"])
                boundaries.append(entry)
            consts.clear()
            continue
        if mn in {"jmp", "ret", "retn", "iret", "iretd", "int", "int3", "ud2"} or mn.startswith("j") or mn.startswith("loop"):
            consts.clear()
            continue
        consts = update_consts(mn, ops, consts)

    traces = [b["cfg_trace"] for b in boundaries if b["cfg_trace"] is not None]
    return {
        "format": FORMAT,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "surface": {
            "direct_call_boundary_count": len(boundaries),
            "direct_call_boundaries": boundaries,
            "cfg_exact_slot_writer_count": len(writer_hits),
            "cfg_exact_slot_writers": writer_hits,
            "cfg_state_limit_hit_count": sum(1 for t in traces if t["state_limit_hit"]),
            "nested_call_boundary_count": sum(t["nested_call_boundary_count"] for t in traces),
            "unresolved_branch_target_count": sum(t["unresolved_branch_target_count"] for t in traces),
            "selected_slots": [f"0x{x:08x}" for x in sorted(SLOTS)],
        },
        "adjudication": {
            "direct_callee_register_alias_cfg_subset_scanned": True,
            "callee_cfg_alias_writer_provenance_complete": False,
            "nested_callee_alias_writer_provenance_complete": False,
            "interprocedural_alias_writer_provenance_complete": False,
            "runtime_or_alias_writer_provenance_complete": False,
            "memory_derived_indirect_call_target_identity_complete": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This follows exact register aliases across direct in-function branch/jump successors with a bounded exact-state worklist.",
            "Nested calls terminate a path; stack-memory aliases, indirect branch targets, heap/object replacement, arbitrary runtime mutation and generated/self-modifying code remain open.",
        ],
        "next_step": "Run on authoritative SHIFT.exe; classify recovered CFG exact-slot writers and only then trace nested-call or stack-memory alias classes that survive retail evidence.",
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
