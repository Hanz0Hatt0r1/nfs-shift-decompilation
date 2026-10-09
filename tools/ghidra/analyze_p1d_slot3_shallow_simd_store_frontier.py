#!/usr/bin/env python3
"""Bound shallow explicit SIMD/SSE memory-store candidates for P1.3D slot3.

This is a navigation + machine-destination inventory. Direct callgraph reachability
never proves selected-HDVehicle identity. The semantic claim is limited to
explicit canonical SIMD move stores mapped into sized functions reachable from
four proven wheel/physics roots within the requested direct-call depth.
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

FORMAT = "SHIFT.P1D.P13DSlot3ShallowSIMDStoreFrontier/1"
SUPPORTED = {"SHIFT.GhidraSQLiteIndex/1", "SHIFT.GhidraSQLiteIndex/2"}
ROOTS = ("FUN_00758b50", "FUN_0076d100", "FUN_00763570", "FUN_00770e80")
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
SQLITE_SHA256 = "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"

INSN_RE = re.compile(r"^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([^\s]+)\s*(.*)$")
MEM_RE = re.compile(r"\[([^\]]+)\]", re.I)
SIMD_REG_RE = re.compile(r"\b(?:xmm\d+|mm\d+)\b", re.I)

# Canonical x86 MMX/SSE/SSE2 move-store mnemonics relevant to copy/zero-init.
STORE_MNEMONICS = {
    "movaps", "movups", "movapd", "movupd", "movdqa", "movdqu",
    "movss", "movsd", "movd", "movq", "movlps", "movhps", "movlpd", "movhpd",
    "movntps", "movntpd", "movntdq", "movntq",
}
IMPLICIT_STORE_MNEMONICS = {"maskmovq", "maskmovdqu"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def index_format(db: sqlite3.Connection) -> str:
    row = db.execute("select value from metadata where key='format'").fetchone()
    value = str(row[0]) if row else ""
    if value not in SUPPORTED:
        raise ValueError(f"unsupported/missing index format: {value!r}")
    return value


def callgraph(db: sqlite3.Connection, version: str):
    adj = collections.defaultdict(list)
    sites = collections.defaultdict(list)
    if version.endswith("/1"):
        for (raw,) in db.execute("select raw_json from calls"):
            row = json.loads(raw)
            if row.get("indirect"):
                continue
            caller = str(row.get("from_name") or row.get("from_function") or "")
            callee = str(row.get("to_name") or row.get("to") or "")
            site = str(row.get("instruction") or row.get("callsite") or "")
            if caller and callee:
                adj[caller].append(callee)
                sites[caller, callee].append(site)
    else:
        for caller, callee, site, kind, indirect in db.execute(
            "select caller,callee,callsite,kind,indirect from calls"
        ):
            if indirect or str(kind).lower() == "indirect" or not caller or not callee:
                continue
            caller, callee = str(caller), str(callee)
            adj[caller].append(callee)
            sites[caller, callee].append(str(site or ""))
    return adj, sites


def reachable(adj, max_depth: int):
    best: dict[str, int] = {}
    paths: dict[str, list[str]] = {}
    for root in ROOTS:
        dist = {root: 0}
        parent: dict[str, str] = {}
        queue = collections.deque([root])
        while queue:
            node = queue.popleft()
            if dist[node] >= max_depth:
                continue
            for callee in adj.get(node, []):
                if callee in dist:
                    continue
                dist[callee] = dist[node] + 1
                parent[callee] = node
                queue.append(callee)
        for node, depth in dist.items():
            if depth >= best.get(node, 1 << 30):
                continue
            best[node] = depth
            path = [node]
            cur = node
            while cur != root:
                cur = parent[cur]
                path.append(cur)
            paths[node] = path[::-1]
    return best, paths


def function_ranges(db: sqlite3.Connection, reach: dict[str, int]):
    out = []
    for address, name, raw in db.execute("select address,name,raw_json from functions"):
        if name not in reach or not address:
            continue
        size = int(json.loads(raw).get("size") or 0)
        if size <= 0:
            continue
        start = int(str(address), 16)
        out.append((start, start + size, str(name), reach[str(name)]))
    return sorted(out)


def split_operands(text: str) -> list[str]:
    return [part.strip().lower() for part in text.split(",")]


def destination_memory(operand: str) -> str | None:
    match = MEM_RE.search(operand.lower())
    return match.group(1).replace(" ", "") if match else None


def is_stack(expr: str) -> bool:
    return bool(re.search(r"(?:^|[+*\-])(esp|ebp)(?:$|[+*\-])", expr))


def parse_disassembly(executable: Path, ranges):
    starts = [row[0] for row in ranges]
    rows = collections.defaultdict(list)
    proc = subprocess.Popen(
        ["objdump", "-d", "-M", "intel", str(executable)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        match = INSN_RE.match(line)
        if not match:
            continue
        address = int(match.group(1), 16)
        idx = bisect.bisect_right(starts, address) - 1
        if idx < 0:
            continue
        start, end, name, _depth = ranges[idx]
        if start <= address < end:
            rows[name].append((address, match.group(2).lower(), match.group(3).strip().lower()))
    stderr = proc.stderr.read() if proc.stderr is not None else ""
    status = proc.wait()
    if status:
        raise RuntimeError(f"objdump failed ({status}): {stderr}")
    return rows


def analyze(database: Path, executable: Path, max_depth: int = 4) -> dict:
    if sha256(database) != SQLITE_SHA256:
        raise ValueError("unexpected Ghidra SQLite SHA-256")
    if sha256(executable) != RETAIL_SHA256:
        raise ValueError("unexpected retail executable SHA-256")

    db = sqlite3.connect(database)
    try:
        version = index_format(db)
        adj, sites = callgraph(db, version)
        reach, paths = reachable(adj, max_depth)
        ranges = function_ranges(db, reach)
    finally:
        db.close()

    instructions = parse_disassembly(executable, ranges)
    simd_instruction_count = 0
    simd_function_names = set()
    explicit_stores = []
    implicit_mask_stores = []

    for _start, _end, name, depth in ranges:
        for address, mnemonic, operands in instructions.get(name, []):
            if SIMD_REG_RE.search(operands):
                simd_instruction_count += 1
                simd_function_names.add(name)
            if mnemonic in IMPLICIT_STORE_MNEMONICS:
                implicit_mask_stores.append(
                    {"function": name, "site": f"0x{address:08x}", "mnemonic": mnemonic, "operands": operands}
                )
            if mnemonic not in STORE_MNEMONICS:
                continue
            parts = split_operands(operands)
            if len(parts) < 2 or not SIMD_REG_RE.search(parts[1]):
                continue
            destination = destination_memory(parts[0])
            if destination is None:
                continue
            explicit_stores.append(
                {
                    "function": name,
                    "depth": depth,
                    "path": paths[name],
                    "site": f"0x{address:08x}",
                    "mnemonic": mnemonic,
                    "destination": parts[0],
                    "destination_expression": destination,
                    "stack_destination": is_stack(destination),
                }
            )

    non_stack = [row for row in explicit_stores if not row["stack_destination"]]
    stack = [row for row in explicit_stores if row["stack_destination"]]
    store_functions = sorted({row["function"] for row in explicit_stores})
    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": RETAIL_SHA256,
            "ghidra_sqlite_sha256": SQLITE_SHA256,
            "direct_callgraph_is_navigation_only": True,
            "machine_destination_adjudicates": True,
        },
        "scan": {
            "roots": list(ROOTS),
            "max_direct_call_depth": max_depth,
            "reachable_unique_node_count": len(reach),
            "reachable_sized_function_count": len(ranges),
            "simd_instruction_count": simd_instruction_count,
            "simd_instruction_function_count": len(simd_function_names),
            "explicit_simd_store_count": len(explicit_stores),
            "explicit_simd_store_function_count": len(store_functions),
            "stack_explicit_simd_store_count": len(stack),
            "non_stack_explicit_simd_store_count": len(non_stack),
            "implicit_mask_store_count": len(implicit_mask_stores),
            "store_functions": store_functions,
        },
        "explicit_stores": explicit_stores,
        "implicit_mask_stores": implicit_mask_stores,
        "adjudication": {
            "shallow_mapped_canonical_simd_store_surface_complete": True,
            "all_explicit_simd_stores_are_stack_local": len(explicit_stores) > 0 and not non_stack,
            "shallow_non_stack_simd_store_candidate_count": len(non_stack),
            "selected_slot3_simd_writer_found": False,
            "deeper_direct_aliases_complete": False,
            "indirect_callback_aliases_complete": False,
            "slot3_writer_provenance_proven": False,
            "p1_3d_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only explicit canonical MMX/SSE/SSE2 move stores mapped into sized function ranges reachable within the direct depth bound.",
            "Ghidra function ranges and direct reachability are navigation evidence; the negative result rests on exact retail store destinations.",
            "Out-of-line chunks outside sized ranges, deeper direct paths, implicit/custom vector stores not in the enumerated class, and indirect/callback paths remain open.",
            "Stack-only SIMD activity cannot establish selected-HDVehicle slot3 identity."
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = analyze(args.database, args.executable, args.max_depth)
    except (ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
