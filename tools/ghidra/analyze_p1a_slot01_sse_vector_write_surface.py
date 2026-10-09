#!/usr/bin/env python3
"""Bound the shallow P1.3A SSE/MMX vector write surface.

The scan follows direct calls from the four recovered wheel/physics roots to depth
four. It records direct XMM/MM -> memory stores and vector -> GPR extraction
values that subsequently escape through an ordinary non-stack memory store before
a clobber or call. This is a bounded machine-write surface, not an object-identity
claim for deeper or indirect paths.
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

FORMAT = "SHIFT.P1A.P13ASlot01SSEVectorWriteClosure/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
INDEX_SHA256 = "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
SUPPORTED_INDEXES = {"SHIFT.GhidraSQLiteIndex/1", "SHIFT.GhidraSQLiteIndex/2"}
ROOTS = ("FUN_00758b50", "FUN_0076d100", "FUN_00763570", "FUN_00770e80")
MAX_DEPTH = 4

VECTOR_STORE_MNEMONICS = {
    "movaps", "movups", "movapd", "movupd", "movdqa", "movdqu",
    "movq", "movss", "movsd", "movlpd", "movhpd", "movlps", "movhps",
    "movd", "movntps", "movntpd", "movntdq", "movntq",
}
VECTOR_TO_GPR_MNEMONICS = {"movd", "pextrw", "pmovmskb", "movmskpd", "movmskps"}
GPRS = {"eax", "ebx", "ecx", "edx", "esi", "edi"}
VECTOR_RE = re.compile(r"\b(?:xmm\d+|mm\d+)\b", re.I)
LINE_RE = re.compile(r"^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([^\s]+)\s*(.*)$")
STACK_RE = re.compile(r"\b(?:esp|ebp|rsp|rbp)\b", re.I)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def split_operands(text: str) -> list[str]:
    return [p.strip().lower() for p in text.split(",", 1)] if "," in text else [text.strip().lower()]


def is_stack_memory(operand: str) -> bool:
    return "[" in operand and bool(STACK_RE.search(operand))


def direct_vector_store(mnemonic: str, operands: str) -> tuple[bool, bool]:
    """Return (is_vector_store, is_stack_destination)."""
    m = mnemonic.lower()
    parts = split_operands(operands)
    if m not in VECTOR_STORE_MNEMONICS or len(parts) != 2:
        return False, False
    dst, src = parts
    if "[" not in dst or not VECTOR_RE.search(src):
        return False, False
    return True, is_stack_memory(dst)


def _written_gpr(mnemonic: str, operands: str) -> str | None:
    parts = split_operands(operands)
    if not parts:
        return None
    dst = parts[0]
    return dst if dst in GPRS else None


def vector_to_gpr_source(mnemonic: str, operands: str) -> str | None:
    parts = split_operands(operands)
    if mnemonic.lower() not in VECTOR_TO_GPR_MNEMONICS or len(parts) < 2:
        return None
    dst = parts[0]
    if dst in GPRS and VECTOR_RE.search(parts[1]):
        return dst
    return None


def escaped_vector_gpr_stores(instructions: list[tuple[int, str, str]]) -> list[dict]:
    """Conservatively track extracted vector bits until clobber/call."""
    tainted: set[str] = set()
    out: list[dict] = []
    for address, mnemonic, operands in instructions:
        m = mnemonic.lower()
        parts = split_operands(operands)
        if m.startswith("call") or m.startswith("ret"):
            tainted.clear()
            continue
        if m == "mov" and len(parts) == 2 and "[" in parts[0] and parts[1] in tainted:
            if not is_stack_memory(parts[0]):
                out.append({
                    "site": f"0x{address:08x}",
                    "instruction": f"{m} {operands}",
                    "carrier": parts[1],
                    "destination": parts[0],
                })
        written = _written_gpr(m, operands)
        if written:
            source = vector_to_gpr_source(m, operands)
            if source:
                tainted.add(written)
            else:
                tainted.discard(written)
    return out


def load_index(db_path: Path):
    db = sqlite3.connect(db_path)
    row = db.execute("SELECT value FROM metadata WHERE key='format'").fetchone()
    if not row or str(row[0]) not in SUPPORTED_INDEXES:
        db.close()
        raise ValueError("unsupported or missing SQLite index format")
    fmt = str(row[0])
    adjacency: dict[str, list[str]] = collections.defaultdict(list)
    if fmt == "SHIFT.GhidraSQLiteIndex/1":
        for (raw,) in db.execute("SELECT raw_json FROM calls"):
            rec = json.loads(raw)
            if rec.get("indirect"):
                continue
            src = str(rec.get("from_name") or rec.get("from_function") or "")
            dst = str(rec.get("to_name") or rec.get("to") or "")
            if src and dst:
                adjacency[src].append(dst)
    else:
        for caller, callee, kind, indirect in db.execute("SELECT caller,callee,kind,indirect FROM calls"):
            if indirect or str(kind).lower() == "indirect":
                continue
            if caller and callee:
                adjacency[str(caller)].append(str(callee))

    sizes: dict[str, tuple[int, int]] = {}
    for address, name, raw in db.execute("SELECT address,name,raw_json FROM functions"):
        rec = json.loads(raw)
        size = int(rec.get("size") or 0)
        if name and size > 0:
            start = int(str(address), 16)
            sizes[str(name)] = (start, start + size)
    db.close()
    return fmt, adjacency, sizes


def reachable(adjacency: dict[str, list[str]]) -> dict[str, int]:
    distance: dict[str, int] = {}
    queue = collections.deque()
    for root in ROOTS:
        distance[root] = 0
        queue.append(root)
    while queue:
        node = queue.popleft()
        if distance[node] >= MAX_DEPTH:
            continue
        for callee in adjacency.get(node, []):
            if callee not in distance:
                distance[callee] = distance[node] + 1
                queue.append(callee)
    return distance


def disassemble_reachable(executable: Path, ranges: list[tuple[int, int, str]]) -> dict[str, list[tuple[int, str, str]]]:
    text = subprocess.run(
        ["objdump", "-d", "-M", "intel", str(executable)],
        check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout
    ranges = sorted(ranges)
    starts = [r[0] for r in ranges]
    result: dict[str, list[tuple[int, str, str]]] = collections.defaultdict(list)
    for line in text.splitlines():
        match = LINE_RE.match(line)
        if not match:
            continue
        address = int(match.group(1), 16)
        i = bisect.bisect_right(starts, address) - 1
        if i < 0:
            continue
        start, end, name = ranges[i]
        if address < end:
            result[name].append((address, match.group(2).lower(), match.group(3).strip().lower()))
    return result


def analyze(executable: Path, database: Path) -> dict:
    exe_hash = sha256(executable)
    db_hash = sha256(database)
    if exe_hash != RETAIL_SHA256:
        raise ValueError(f"unexpected retail SHA-256: {exe_hash}")
    if db_hash != INDEX_SHA256:
        raise ValueError(f"unexpected SQLite SHA-256: {db_hash}")

    fmt, adjacency, sizes = load_index(database)
    distance = reachable(adjacency)
    ranges = [(sizes[name][0], sizes[name][1], name) for name in distance if name in sizes]
    instructions = disassemble_reachable(executable, ranges)

    direct_rows = []
    escape_rows = []
    for name in sorted(instructions, key=lambda n: (distance.get(n, 999), n)):
        for address, mnemonic, operands in instructions[name]:
            is_store, is_stack = direct_vector_store(mnemonic, operands)
            if is_store:
                direct_rows.append({
                    "depth": distance[name],
                    "function": name,
                    "site": f"0x{address:08x}",
                    "instruction": f"{mnemonic} {operands}",
                    "destination_class": "stack" if is_stack else "non-stack",
                })
        for row in escaped_vector_gpr_stores(instructions[name]):
            row.update({"depth": distance[name], "function": name})
            escape_rows.append(row)

    direct_rows.sort(key=lambda r: int(r["site"], 16))
    escape_rows.sort(key=lambda r: int(r["site"], 16))
    stack_count = sum(r["destination_class"] == "stack" for r in direct_rows)
    nonstack_count = len(direct_rows) - stack_count
    functions = sorted({r["function"] for r in direct_rows})

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1A / P1.3A",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": exe_hash,
            "ghidra_sqlite_sha256": db_hash,
            "source_index_format": fmt,
            "machine_write_surface_adjudicates": True,
        },
        "scan": {
            "roots": list(ROOTS),
            "max_direct_call_depth": MAX_DEPTH,
            "reachable_unique_node_count": len(distance),
            "reachable_sized_function_count": len(ranges),
            "direct_vector_memory_store_count": len(direct_rows),
            "direct_stack_vector_memory_store_count": stack_count,
            "direct_nonstack_vector_memory_store_count": nonstack_count,
            "direct_vector_store_function_count": len(functions),
            "vector_to_gpr_nonstack_escape_count": len(escape_rows),
        },
        "direct_vector_stores": direct_rows,
        "vector_to_gpr_nonstack_escapes": escape_rows,
        "adjudication": {
            "shallow_sse_vector_write_depth4_surface_complete": True,
            "shallow_sse_vector_selected_hdvehicle_writer_found": False,
            "sse_vector_copy_init_complete": True,
            "deeper_direct_aliases_ruled_out": False,
            "indirect_callback_aliases_ruled_out": False,
            "p13a_slot0_complete": False,
            "p13a_slot1_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only explicit XMM/MM memory writes and vector-to-GPR ordinary-store escapes within four direct-call edges of the four P1.3A roots.",
            "Deeper direct paths and indirect/callback aliases remain outside this bounded surface.",
            "Callgraph reachability never establishes selected-HDVehicle identity by itself."
        ],
        "next_step": "Trace deeper direct aliases only from exact selected-HDVehicle-derived destinations, then bound indirect/callback alias carriers before promoting slot0/slot1 or aggregate P1.3 gates."
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("database", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = analyze(args.executable, args.database)
    except ValueError as exc:
        parser.error(str(exc))
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
