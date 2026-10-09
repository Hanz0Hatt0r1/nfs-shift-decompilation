#!/usr/bin/env python3
"""Inventory shallow ordinary-MOV copy/init loops for P1.3A slot0/slot1.

This is a deliberately bounded machine-navigation scan. It follows direct calls
from the four recovered wheel/physics roots to depth four, disassembles only
sized functions in that frontier, and selects backward-branch loops containing
ordinary MOV copy/init stores whose non-stack destination address is advanced
inside the loop. Canonical MOVS/STOS string instructions and REP-prefixed forms
are outside this subset and are closed by separate contracts.
"""
from __future__ import annotations

import argparse
import bisect
import collections
import hashlib
import json
import re
import sqlite3
import subprocess
from pathlib import Path

FORMAT = "SHIFT.P1A.P13ASlot01OrdinaryMovLoopFrontier/1"
SUPPORTED_INDEXES = {"SHIFT.GhidraSQLiteIndex/1", "SHIFT.GhidraSQLiteIndex/2"}
DEFAULT_ROOTS = (
    "FUN_00758b50",
    "FUN_0076d100",
    "FUN_00763570",
    "FUN_00770e80",
)
REGS = {"eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp"}
WRITE_MNEMONICS = {"mov", "lea", "add", "sub", "inc", "dec", "xor", "and", "or", "shl", "shr", "sar", "imul"}
INSN_RE = re.compile(r"^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([^\s]+)\s*(.*)$")
TARGET_RE = re.compile(r"0x([0-9a-fA-F]+)")
REG_RE = re.compile(r"\b(?:eax|ebx|ecx|edx|esi|edi|ebp|esp)\b")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def split_ops(text: str) -> list[str]:
    return [part.strip() for part in text.split(",", 1)] if "," in text else [text.strip()]


def register_name(text: str) -> str | None:
    value = text.lower().strip()
    value = re.sub(r"^(?:byte|word|dword|qword) ptr\s+", "", value)
    return value if value in REGS else None


def memory_registers(text: str) -> set[str]:
    return set(REG_RE.findall(text.lower()))


def nonstack_memory(text: str) -> bool:
    lower = text.lower()
    return "[" in lower and "]" in lower and "ebp" not in lower and "esp" not in lower


def index_format(db: sqlite3.Connection) -> str:
    row = db.execute("SELECT value FROM metadata WHERE key='format'").fetchone()
    if row is None:
        raise ValueError("SQLite index has no metadata format")
    fmt = str(row[0])
    if fmt not in SUPPORTED_INDEXES:
        raise ValueError(f"unsupported SQLite index format: {fmt!r}")
    return fmt


def load_direct_graph(db: sqlite3.Connection, fmt: str) -> tuple[dict[str, list[str]], dict[tuple[str, str], list[str]]]:
    adjacency: dict[str, list[str]] = collections.defaultdict(list)
    sites: dict[tuple[str, str], list[str]] = collections.defaultdict(list)
    if fmt == "SHIFT.GhidraSQLiteIndex/1":
        rows = db.execute("SELECT raw_json FROM calls")
        for (raw_json,) in rows:
            rec = json.loads(raw_json)
            if rec.get("indirect"):
                continue
            src = str(rec.get("from_name") or rec.get("from_function") or "")
            dst = str(rec.get("to_name") or rec.get("to") or "")
            site = str(rec.get("instruction") or rec.get("callsite") or "")
            if src and dst:
                adjacency[src].append(dst)
                sites[(src, dst)].append(site)
        return adjacency, sites

    for caller, callee, callsite, kind, indirect in db.execute(
        "SELECT caller,callee,callsite,kind,indirect FROM calls"
    ):
        if indirect or str(kind).lower() == "indirect" or not caller or not callee:
            continue
        src, dst = str(caller), str(callee)
        adjacency[src].append(dst)
        sites[(src, dst)].append(str(callsite or ""))
    return adjacency, sites


def shallow_reachability(adjacency: dict[str, list[str]], roots=DEFAULT_ROOTS, max_depth: int = 4):
    minimum: dict[str, int] = {}
    best_path: dict[str, list[str]] = {}
    for root in roots:
        distance = {root: 0}
        parent: dict[str, str] = {}
        queue = collections.deque([root])
        while queue:
            node = queue.popleft()
            if distance[node] >= max_depth:
                continue
            for callee in adjacency.get(node, []):
                if callee in distance:
                    continue
                distance[callee] = distance[node] + 1
                parent[callee] = node
                queue.append(callee)
        for node, depth in distance.items():
            if depth >= minimum.get(node, 1 << 30):
                continue
            minimum[node] = depth
            path = [node]
            cur = node
            while cur != root:
                cur = parent[cur]
                path.append(cur)
            best_path[node] = list(reversed(path))
    return minimum, best_path


def sized_ranges(db: sqlite3.Connection, reachable: dict[str, int]):
    result = []
    for address, name, raw_json in db.execute("SELECT address,name,raw_json FROM functions"):
        if name not in reachable or not address:
            continue
        size = int(json.loads(raw_json).get("size") or 0)
        if size <= 0:
            continue
        start = int(str(address), 16)
        result.append((start, start + size, str(name), reachable[str(name)]))
    return sorted(result)


def disassemble(executable: Path) -> str:
    proc = subprocess.run(
        ["objdump", "-d", "-M", "intel", str(executable)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return proc.stdout


def parse_reachable_instructions(text: str, ranges):
    starts = [row[0] for row in ranges]
    instructions: dict[str, list[tuple[int, str, str]]] = collections.defaultdict(list)
    for line in text.splitlines():
        match = INSN_RE.match(line)
        if not match:
            continue
        address = int(match.group(1), 16)
        idx = bisect.bisect_right(starts, address) - 1
        if idx < 0:
            continue
        start, end, name, _depth = ranges[idx]
        if start <= address < end:
            instructions[name].append((address, match.group(2).lower(), match.group(3).strip()))
    return instructions


def _loop_hits(body: list[tuple[int, str, str]]):
    mutated: set[str] = set()
    for _addr, mnemonic, operands in body:
        parts = split_ops(operands)
        if mnemonic in {"add", "sub", "inc", "dec", "lea"} and parts:
            reg = register_name(parts[0])
            if reg:
                mutated.add(reg)

    last_memory_load: dict[str, tuple[int, str]] = {}
    zero_registers: set[str] = set()
    hits = []
    for address, mnemonic, operands in body:
        parts = split_ops(operands)
        if mnemonic == "mov" and len(parts) == 2:
            dst, src = parts
            dst_reg, src_reg = register_name(dst), register_name(src)
            if nonstack_memory(dst) and (memory_registers(dst) & mutated):
                if src_reg and src_reg in last_memory_load:
                    load_addr, load_mem = last_memory_load[src_reg]
                    hits.append({
                        "kind": "memory-transfer",
                        "load_site": f"0x{load_addr:08x}",
                        "store_site": f"0x{address:08x}",
                        "source": load_mem,
                        "destination": dst,
                        "carrier_register": src_reg,
                    })
                elif src in {"0", "0x0"} or (src_reg and src_reg in zero_registers):
                    hits.append({
                        "kind": "zero-init",
                        "store_site": f"0x{address:08x}",
                        "source": src,
                        "destination": dst,
                    })

            if dst_reg:
                if "[" in src and "]" in src:
                    last_memory_load[dst_reg] = (address, src)
                else:
                    last_memory_load.pop(dst_reg, None)
                if src in {"0", "0x0"}:
                    zero_registers.add(dst_reg)
                else:
                    zero_registers.discard(dst_reg)
            continue

        if mnemonic == "xor" and len(parts) == 2 and parts[0].lower() == parts[1].lower():
            reg = register_name(parts[0])
            if reg:
                last_memory_load.pop(reg, None)
                zero_registers.add(reg)
            continue

        if parts and mnemonic in WRITE_MNEMONICS:
            reg = register_name(parts[0])
            if reg:
                last_memory_load.pop(reg, None)
                zero_registers.discard(reg)
    return hits


def candidate_loops(instructions: list[tuple[int, str, str]]):
    if not instructions:
        return []
    loops = []
    seen = set()
    for index, (address, mnemonic, operands) in enumerate(instructions):
        if not mnemonic.startswith("j"):
            continue
        target_match = TARGET_RE.search(operands)
        if not target_match:
            continue
        target = int(target_match.group(1), 16)
        if not (instructions[0][0] <= target < address):
            continue
        start_index = next((i for i, row in enumerate(instructions) if row[0] >= target), None)
        if start_index is None:
            continue
        key = (target, address)
        if key in seen:
            continue
        seen.add(key)
        body = instructions[start_index:index + 1]
        hits = _loop_hits(body)
        if hits:
            loops.append({
                "loop_start": f"0x{target:08x}",
                "backedge_site": f"0x{address:08x}",
                "hits": hits,
            })
    return loops


def analyze(database: Path, executable: Path, max_depth: int = 4) -> dict:
    if max_depth < 1:
        raise ValueError("max_depth must be >= 1")
    db = sqlite3.connect(database)
    try:
        fmt = index_format(db)
        adjacency, callsites = load_direct_graph(db, fmt)
        reachable, paths = shallow_reachability(adjacency, max_depth=max_depth)
        ranges = sized_ranges(db, reachable)
    finally:
        db.close()

    instructions = parse_reachable_instructions(disassemble(executable), ranges)
    candidates = []
    for start, _end, name, depth in ranges:
        loops = candidate_loops(instructions.get(name, []))
        if not loops:
            continue
        path = paths[name]
        edge_sites = []
        for src, dst in zip(path, path[1:]):
            edge_sites.append({"from": src, "to": dst, "callsites": sorted(set(callsites[(src, dst)]))})
        candidates.append({
            "function": name,
            "address": f"0x{start:08x}",
            "min_direct_depth": depth,
            "shortest_path": path,
            "path_edges": edge_sites,
            "loops": loops,
        })

    candidates.sort(key=lambda row: (row["min_direct_depth"], row["address"], row["function"]))
    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1A / P1.3A",
        "scope": "slot0/slot1 shallow ordinary MOV copy/init loop navigation frontier",
        "source_index_format": fmt,
        "source_index_sha256": sha256_file(database),
        "retail_executable_sha256": sha256_file(executable),
        "roots": list(DEFAULT_ROOTS),
        "max_direct_call_depth": max_depth,
        "reachable_unique_node_count": len(reachable),
        "reachable_sized_function_count": len(ranges),
        "candidate_function_count": len(candidates),
        "candidates": candidates,
        "adjudication": {
            "navigation_frontier_captured": True,
            "candidate_reachability_proves_selected_hdvehicle_alias": False,
            "ordinary_mov_loop_semantics_complete": False,
            "p13a_slot0_complete": False,
            "p13a_slot1_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = analyze(args.database, args.executable, args.max_depth)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
