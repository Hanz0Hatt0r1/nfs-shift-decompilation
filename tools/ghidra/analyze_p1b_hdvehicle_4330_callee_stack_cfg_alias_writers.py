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
FORMAT = "SHIFT.P1B.HDVehicle4330CalleeStackCFGAliasWriterProbe/1"
SLOTS = {0x00B83DC0, 0x00B83EC0}
REGS = {"eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp"}
I = re.compile(r"^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$")
MEM = re.compile(r"^(?:(?:BYTE|WORD|DWORD|QWORD) PTR )?\[([^\]]+)\]$")
IMM = re.compile(r"^(?:0x([0-9a-fA-F]+)|([0-9]+))$")
STACK = re.compile(r"^(e(?:bp|sp))(?:([+-])0x([0-9a-f]+))?$", re.I)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip()).replace(", ", ",")


def split_ops(s: str):
    return s.split(",") if s else []


def imm(s: str):
    m = IMM.fullmatch(s)
    if not m:
        return None
    return int(m.group(1), 16) if m.group(1) else int(m.group(2))


def direct_target(op: str):
    tok = op.split()[0] if op else ""
    if tok.startswith("0x"):
        return int(tok, 16)
    if re.fullmatch(r"[0-9a-fA-F]+", tok):
        return int(tok, 16)
    return None


def stack_key(op: str):
    m = MEM.fullmatch(op)
    if not m:
        return None
    e = m.group(1).replace(" ", "")
    sm = STACK.fullmatch(e)
    if not sm:
        return None
    base, sign, n = sm.groups()
    off = int(n, 16) if n else 0
    if sign == "-":
        off = -off
    return f"{base.lower()}{off:+#x}"


def alias_mem_reg(op: str, aliases: dict[str, int]):
    m = MEM.fullmatch(op)
    if not m:
        return None
    e = m.group(1).replace(" ", "")
    return e if e in aliases else None


def branch_target(mn: str, ops: str):
    if mn == "jmp" or mn.startswith("j") or mn.startswith("loop"):
        p = split_ops(ops)
        return direct_target(p[0]) if p else None
    return None


def trace_cfg(rows, start_idx: int, incoming: dict[str, int], limit_states: int = 512):
    index = {a: i for i, (a, _, _) in enumerate(rows)}
    q = deque([(start_idx, dict(incoming), {})])
    seen = set()
    writes = []
    nested_calls = 0
    unresolved_targets = 0
    states = 0

    while q and states < limit_states:
        idx, aliases, stack_aliases = q.popleft()
        key = (idx, tuple(sorted(aliases.items())), tuple(sorted(stack_aliases.items())))
        if key in seen:
            continue
        seen.add(key)
        states += 1
        a, mn, ops = rows[idx]
        p = split_ops(ops)

        if p and mn not in {"cmp", "test"}:
            reg = alias_mem_reg(p[0], aliases)
            if reg is not None:
                writes.append({
                    "site": f"0x{a:08x}",
                    "mnemonic": mn,
                    "destination": p[0],
                    "slot": f"0x{aliases[reg]:08x}",
                    "alias_register": reg,
                })

        new_aliases = dict(aliases)
        new_stack = dict(stack_aliases)
        if mn == "mov" and len(p) == 2:
            dst, src = p
            dst_sk = stack_key(dst)
            if dst_sk:
                if src in new_aliases:
                    new_stack[dst_sk] = new_aliases[src]
                else:
                    new_stack.pop(dst_sk, None)
            elif dst in REGS:
                src_sk = stack_key(src)
                if src_sk in new_stack:
                    new_aliases[dst] = new_stack[src_sk]
                elif src in new_aliases:
                    new_aliases[dst] = new_aliases[src]
                else:
                    new_aliases.pop(dst, None)
        elif p and p[0] in REGS and mn not in {"cmp", "test", "push"}:
            new_aliases.pop(p[0], None)

        if mn == "call":
            nested_calls += 1
            continue
        if mn in {"ret", "retn", "iret", "iretd", "int", "int3", "ud2"}:
            continue

        bt = branch_target(mn, ops)
        if mn == "jmp":
            if bt in index:
                q.append((index[bt], new_aliases, new_stack))
            else:
                unresolved_targets += 1
            continue
        if mn.startswith("j") or mn.startswith("loop"):
            if bt in index:
                q.append((index[bt], dict(new_aliases), dict(new_stack)))
            elif bt is not None:
                unresolved_targets += 1
            if idx + 1 < len(rows):
                q.append((idx + 1, new_aliases, new_stack))
            continue
        if idx + 1 < len(rows):
            q.append((idx + 1, new_aliases, new_stack))

    return {
        "visited_state_count": states,
        "state_limit_hit": bool(q),
        "nested_call_boundary_count": nested_calls,
        "unresolved_branch_target_count": unresolved_targets,
        "exact_slot_writes": writes,
    }


def scan_rows(rows):
    index = {a: i for i, (a, _, _) in enumerate(rows)}
    caller_consts = {}
    boundaries = []
    writers = []
    for a, mn, ops in rows:
        p = split_ops(ops)
        if mn == "mov" and len(p) == 2 and p[0] in REGS:
            n = imm(p[1])
            if n is not None:
                caller_consts[p[0]] = n & 0xffffffff
            elif p[1] in caller_consts:
                caller_consts[p[0]] = caller_consts[p[1]]
            else:
                caller_consts.pop(p[0], None)
        elif mn == "call":
            live = {r: v for r, v in caller_consts.items() if v in SLOTS}
            target = direct_target(p[0]) if p else None
            if live and target in index:
                trace = trace_cfg(rows, index[target], live)
                entry = {
                    "call_site": f"0x{a:08x}",
                    "call_target": f"0x{target:08x}",
                    "incoming_register_slots": {r: f"0x{v:08x}" for r, v in sorted(live.items())},
                    "cfg_trace": trace,
                }
                boundaries.append(entry)
                writers.extend({"call_site": entry["call_site"], "call_target": entry["call_target"], **w} for w in trace["exact_slot_writes"])
            caller_consts.clear()
        elif mn in {"jmp", "ret", "retn", "iret", "iretd", "int", "int3", "ud2"} or mn.startswith("j") or mn.startswith("loop"):
            caller_consts.clear()

    traces = [b["cfg_trace"] for b in boundaries]
    return {
        "format": FORMAT,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "surface": {
            "direct_call_boundary_count": len(boundaries),
            "direct_call_boundaries": boundaries,
            "stack_cfg_exact_slot_writer_count": len(writers),
            "stack_cfg_exact_slot_writers": writers,
            "state_limit_hit_count": sum(1 for t in traces if t["state_limit_hit"]),
            "nested_call_boundary_count": sum(t["nested_call_boundary_count"] for t in traces),
            "unresolved_branch_target_count": sum(t["unresolved_branch_target_count"] for t in traces),
            "selected_slots": [f"0x{x:08x}" for x in sorted(SLOTS)],
        },
        "adjudication": {
            "callee_stack_cfg_alias_subset_scanned": True,
            "callee_stack_alias_writer_provenance_complete": False,
            "nested_callee_alias_writer_provenance_complete": False,
            "interprocedural_alias_writer_provenance_complete": False,
            "runtime_or_alias_writer_provenance_complete": False,
            "memory_derived_indirect_call_target_identity_complete": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This follows exact EBP/ESP stack-slot aliases across direct conditional/unconditional CFG successors with a bounded exact-state worklist.",
            "Nested calls terminate a path; stack-pointer normalization, indirect branches, heap/object replacement, runtime mutation and generated/self-modifying code remain open.",
        ],
        "next_step": "Run on authoritative SHIFT.exe; classify recovered stack-CFG writers, then trace nested-call or stack-pointer-normalized aliases only if retail evidence survives."
    }


def disassemble(exe: Path):
    p = subprocess.run(["objdump", "-d", "-Mintel", str(exe)], capture_output=True, text=True, check=True, errors="replace")
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
