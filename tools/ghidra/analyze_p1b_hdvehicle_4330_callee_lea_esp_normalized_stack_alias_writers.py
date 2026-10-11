#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

SHA = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
FORMAT = "SHIFT.P1B.HDVehicle4330CalleeLEAESPNormalizedStackAliasWriterProbe/1"
SLOTS = {0x00B83DC0, 0x00B83EC0}
REGS = {"eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp"}
I = re.compile(r"^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$")
MEM = re.compile(r"^(?:(?:BYTE|WORD|DWORD|QWORD) PTR )?\[([^\]]+)\]$")
IMM = re.compile(r"^(?:0x([0-9a-fA-F]+)|([0-9]+))$")
STACK = re.compile(r"^(e(?:bp|sp))(?:([+-])0x([0-9a-f]+))?$", re.I)
LEA_ESP = re.compile(r"^\[esp(?:([+-])0x([0-9a-f]+))?\]$", re.I)


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


def parse_stack(op: str):
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
    return base.lower(), off


def logical_stack_key(op: str, esp_delta: int):
    parsed = parse_stack(op)
    if not parsed:
        return None
    base, off = parsed
    if base == "esp":
        off += esp_delta
    return f"{base}{off:+#x}"


def lea_esp_adjustment(ops: str):
    p = split_ops(ops)
    if len(p) != 2 or p[0] != "esp":
        return None
    m = LEA_ESP.fullmatch(p[1].replace(" ", ""))
    if not m:
        return None
    sign, n = m.groups()
    if n is None:
        return 0
    value = int(n, 16)
    return -value if sign == "-" else value


def scan_rows(rows):
    index = {a: i for i, (a, _, _) in enumerate(rows)}
    caller = {}
    boundaries = []
    writers = []
    lea_events = 0
    unsupported_esp_adjustments = 0
    for a, mn, ops in rows:
        p = split_ops(ops)
        if mn == "mov" and len(p) == 2 and p[0] in REGS:
            n = imm(p[1])
            if n is not None:
                caller[p[0]] = n & 0xffffffff
            elif p[1] in caller:
                caller[p[0]] = caller[p[1]]
            else:
                caller.pop(p[0], None)
        elif mn == "call":
            live = {r: v for r, v in caller.items() if v in SLOTS}
            target = direct_target(p[0]) if p else None
            if live and target in index:
                aliases = dict(live)
                stack_aliases = {}
                esp_delta = 0
                hits = []
                local_events = []
                local_unsupported = 0
                for ca, cmn, cops in rows[index[target]:index[target] + 128]:
                    cp = split_ops(cops)
                    if cmn in {"ret", "retn", "iret", "iretd", "int", "int3", "ud2", "call", "jmp"} or cmn.startswith("j") or cmn.startswith("loop"):
                        break
                    if cmn in {"sub", "add"} and len(cp) == 2 and cp[0] == "esp":
                        n = imm(cp[1])
                        if n is None:
                            unsupported_esp_adjustments += 1
                            local_unsupported += 1
                            break
                        esp_delta += n if cmn == "sub" else -n
                        local_events.append({"site": f"0x{ca:08x}", "kind": cmn, "amount": n, "esp_delta": esp_delta})
                        continue
                    if cmn == "lea" and len(cp) == 2 and cp[0] == "esp":
                        adj = lea_esp_adjustment(cops)
                        if adj is None:
                            unsupported_esp_adjustments += 1
                            local_unsupported += 1
                            break
                        esp_delta -= adj
                        lea_events += 1
                        local_events.append({"site": f"0x{ca:08x}", "kind": "lea", "amount": adj, "esp_delta": esp_delta})
                        continue
                    if cmn == "mov" and len(cp) == 2:
                        sk = logical_stack_key(cp[0], esp_delta)
                        if sk and cp[1] in aliases:
                            stack_aliases[sk] = aliases[cp[1]]
                        elif cp[0] in REGS:
                            src_sk = logical_stack_key(cp[1], esp_delta)
                            if src_sk in stack_aliases:
                                aliases[cp[0]] = stack_aliases[src_sk]
                            elif cp[1] in aliases:
                                aliases[cp[0]] = aliases[cp[1]]
                            else:
                                aliases.pop(cp[0], None)
                    if cp:
                        mm = MEM.fullmatch(cp[0])
                        if mm and mm.group(1).replace(" ", "") in aliases and cmn not in {"cmp", "test"}:
                            reg = mm.group(1).replace(" ", "")
                            hit = {"site": f"0x{ca:08x}", "slot": f"0x{aliases[reg]:08x}", "alias_register": reg, "destination": cp[0], "mnemonic": cmn}
                            hits.append(hit)
                            writers.append({"call_site": f"0x{a:08x}", "call_target": f"0x{target:08x}", **hit})
                boundaries.append({"call_site": f"0x{a:08x}", "call_target": f"0x{target:08x}", "normalization_events": local_events, "unsupported_esp_adjustment_count": local_unsupported, "stack_aliases": {k: f"0x{v:08x}" for k, v in sorted(stack_aliases.items())}, "exact_slot_writes": hits})
            caller.clear()
        elif mn in {"jmp", "ret", "retn", "iret", "iretd", "int", "int3", "ud2"} or mn.startswith("j") or mn.startswith("loop"):
            caller.clear()
    return {
        "format": FORMAT,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "surface": {
            "direct_call_boundary_count": len(boundaries),
            "direct_call_boundaries": boundaries,
            "lea_esp_normalization_event_count": lea_events,
            "unsupported_esp_adjustment_count": unsupported_esp_adjustments,
            "lea_esp_normalized_stack_alias_writer_count": len(writers),
            "lea_esp_normalized_stack_alias_writers": writers,
            "selected_slots": [f"0x{x:08x}" for x in sorted(SLOTS)],
        },
        "adjudication": {
            "callee_lea_esp_normalized_stack_alias_subset_scanned": True,
            "callee_stack_pointer_normalization_complete": False,
            "nested_callee_alias_writer_provenance_complete": False,
            "interprocedural_alias_writer_provenance_complete": False,
            "runtime_or_alias_writer_provenance_complete": False,
            "memory_derived_indirect_call_target_identity_complete": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "Covers immediate add/sub ESP and exact lea esp,[esp+/-imm] normalization in the first straight-line direct-callee span.",
            "Register-sized or masked ESP changes, CFG stack merges, nested calls, heap/runtime mutation and generated code remain open.",
        ],
        "next_step": "Run on authoritative SHIFT.exe; classify recovered LEA-normalized writers, then extend only surviving dynamic-stack or nested-call aliases."
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
