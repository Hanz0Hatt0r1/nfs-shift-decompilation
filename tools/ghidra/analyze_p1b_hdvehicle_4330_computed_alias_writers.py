#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

SHA = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
FORMAT = "SHIFT.P1B.HDVehicle4330ComputedAliasWriterProbe/1"
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
    used_reg = False
    for raw in re.findall(r"[+-]?[^+-]+", expr):
        sign = -1 if raw.startswith("-") else 1
        term = raw[1:] if raw[:1] in "+-" else raw
        if "*" in term:
            reg, scale = term.split("*", 1)
            n = imm(scale)
            if reg not in REGS or reg not in consts or n is None:
                return None
            total += sign * consts[reg] * n
            used_reg = True
        elif term in REGS:
            if term not in consts:
                return None
            total += sign * consts[term]
            used_reg = True
        else:
            n = imm(term)
            if n is None:
                return None
            total += sign * n
    return total & 0xFFFFFFFF, used_reg


def is_control(mn: str) -> bool:
    return mn in {"call", "jmp", "ret", "retn", "iret", "iretd", "int", "int3", "ud2"} or mn.startswith("j") or mn.startswith("loop")


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
        v = eval_expr(mm.group(1), c)[0] if mm and eval_expr(mm.group(1), c) is not None else None
        if v is None:
            c.pop(dst, None)
        else:
            c[dst] = v
    elif mn in {"add", "sub"} and len(p) == 2 and p[0] in REGS:
        dst, src = p
        n = imm(src)
        if dst in c and n is not None:
            c[dst] = (c[dst] + (n if mn == "add" else -n)) & 0xFFFFFFFF
        else:
            c.pop(dst, None)
    elif mn == "xor" and len(p) == 2 and p[0] == p[1] and p[0] in REGS:
        c[p[0]] = 0
    elif p and p[0] in REGS and mn not in {"cmp", "test", "push"}:
        c.pop(p[0], None)
    return c


def scan_rows(rows):
    consts: dict[str, int] = {}
    hits = []
    all_resolved_writes = []
    for a, mn, ops in rows:
        p = split_ops(ops)
        if p and mn not in {"cmp", "test"}:
            mm = MEM.fullmatch(p[0])
            if mm:
                ev = eval_expr(mm.group(1), consts)
                if ev is not None:
                    ea, used_reg = ev
                    item = {
                        "site": f"0x{a:08x}",
                        "mnemonic": mn,
                        "destination": p[0],
                        "resolved_address": f"0x{ea:08x}",
                        "source": p[1] if len(p) > 1 else None,
                        "register_derived": used_reg,
                    }
                    all_resolved_writes.append(item)
                    if ea in SLOTS and used_reg:
                        hits.append(item)
        if is_control(mn):
            consts.clear()
        else:
            consts = update_consts(mn, ops, consts)
    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "scope": {
            "slots": [f"0x{x:08x}" for x in sorted(SLOTS)],
            "subset": "same-basic-block register-constant-derived memory destinations",
            "control_flow_policy": "clear constant state at calls, jumps, branches, returns, traps",
        },
        "surface": {
            "computed_alias_writer_count": len(hits),
            "computed_alias_writers": hits,
            "resolved_memory_write_count": len(all_resolved_writes),
        },
        "adjudication": {
            "computed_same_block_alias_writer_subset_scanned": True,
            "runtime_or_alias_writer_provenance_complete": False,
            "memory_derived_indirect_call_target_identity_complete": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This probe resolves only register-constant-derived stores inside a single linear control-flow span.",
            "Value-derived aliases, interprocedural aliases, heap/object replacement, runtime mutation and self-modifying/generated code remain open.",
        ],
        "next_step": "Run on authoritative SHIFT.exe, classify each computed alias writer into 0x00b83dc0/0x00b83ec0, then expand to value-derived and interprocedural alias writers.",
    }


def disassemble(exe: Path):
    p = subprocess.run(["objdump", "-d", "-Mintel", str(exe)], text=True, capture_output=True, check=True, errors="replace")
    rows = []
    for line in p.stdout.splitlines():
        m = I.match(line)
        if m:
            rows.append((int(m.group(1), 16), m.group(2).lower(), norm(m.group(3))))
    return rows


def analyze(exe: Path):
    sha = hashlib.sha256(exe.read_bytes()).hexdigest()
    if sha != SHA:
        raise ValueError(f"unexpected executable SHA: {sha}")
    out = scan_rows(disassemble(exe))
    out["authority"] = {"platform": "PC retail 1.02", "retail_executable_sha256": sha}
    return out


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
