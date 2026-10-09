#!/usr/bin/env python3
"""Close shallow straight-line ordinary-MOV zero initialization for P1.3A."""
from __future__ import annotations

import argparse
import collections
import json
import sqlite3
from pathlib import Path

import analyze_p1a_slot01_unrolled_mov_copy_frontier as base

FORMAT = "SHIFT.P1A.P13ASlot01StraightZeroInitMachineClosure/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
INDEX_SHA256 = "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
EXPECTED_CANDIDATES = (
    "FUN_00887580", "FUN_00647a10", "FUN_0070fae0",
    "FUN_0087aa00", "FUN_00886e10", "FUN_0088f110",
)
SEMANTIC = {
    "FUN_00887580": ("fixed-singleton-constructor", "FUN_00887720 passes exact ECX=0x00c29640; ordinary zero stores remain fields of that singleton."),
    "FUN_00647a10": ("fixed-singleton-base-constructor", "On the only depth<=4 P1A path FUN_00887580 calls with unchanged singleton receiver 0x00c29640."),
    "FUN_0070fae0": ("physics-manager-singleton-constructor", "FUN_0070fe99 passes exact ECX=0x00c104e0; FUN_0070fae0 installs vptr 0x00b04524, the recovered Physics Manager singleton."),
    "FUN_0087aa00": ("hdvehicle-high-service-subobjects", "The bounded caller FUN_00a62780 is entered as HDVehicle+0x6730 and calls on only HDVehicle+0x6754 and HDVehicle+0x6814; the helper clears local +0/+0xc/+0x10/+0x14."),
    "FUN_00886e10": ("fixed-singleton-nested-subobject", "FUN_00887580 calls with ECX=0x00c29640+0x70c=0x00c29d4c; merged REP evidence independently pins this receiver."),
    "FUN_0088f110": ("fixed-singleton-nested-subobject", "FUN_00887580 calls with ECX=0x00c29640+0x558=0x00c29b98; its local zero stores remain inside that singleton subobject."),
}


def _in_loop(index: int, intervals) -> bool:
    return any(start <= index <= end for start, end in intervals)


def zero_hits(instructions):
    intervals = base.backward_intervals(instructions)
    zero_regs: set[str] = set()
    hits = []
    for index, (address, mnemonic, operands) in enumerate(instructions):
        parts = base.split_ops(operands)
        if mnemonic in {"xor", "sub"} and len(parts) == 2:
            left, right = base.reg(parts[0]), base.reg(parts[1])
            if left and left == right:
                zero_regs.add(left)
                continue
        if mnemonic == "mov" and len(parts) == 2:
            dst, src = parts
            dst_reg, src_reg = base.reg(dst), base.reg(src)
            is_zero = src.lower().strip() in {"0", "0x0"} or bool(src_reg and src_reg in zero_regs)
            info = base.mem_info(dst)
            if info and is_zero and not _in_loop(index, intervals):
                _width, dest_base, _offset, _expr = info
                if "ebp" not in dest_base and "esp" not in dest_base:
                    hits.append({"i": index, "site": f"0x{address:08x}", "destination": dst, "info": info, "source": src})
            if dst_reg:
                if is_zero:
                    zero_regs.add(dst_reg)
                else:
                    zero_regs.discard(dst_reg)
            continue
        if mnemonic.startswith("call"):
            zero_regs.difference_update({"eax", "ecx", "edx"})
            continue
        if parts and mnemonic in base.WRITE_MNEMONICS:
            target = base.reg(parts[0])
            if target:
                zero_regs.discard(target)
    return hits


def _coverage(hits) -> int:
    spans = []
    for hit in hits:
        width, _dest_base, offset, _expr = hit["info"]
        if width is None:
            return 0
        spans.append((offset, offset + width))
    spans.sort()
    start, end = spans[0]
    best = 0
    for next_start, next_end in spans[1:]:
        if next_start <= end:
            end = max(end, next_end)
        else:
            best = max(best, end - start)
            start, end = next_start, next_end
    return max(best, end - start)


def zero_clusters(instructions):
    by_base = collections.defaultdict(list)
    for hit in zero_hits(instructions):
        by_base[hit["info"][1]].append(hit)
    result = []
    for dest_base, hits in by_base.items():
        chunk = []
        for hit in hits + [None]:
            if hit is not None and (not chunk or hit["i"] - chunk[-1]["i"] <= 16):
                chunk.append(hit)
                continue
            if len(chunk) >= 2 and _coverage(chunk) >= 8:
                result.append({
                    "destination_base": dest_base,
                    "max_contiguous_coverage_bytes": _coverage(chunk),
                    "stores": [{k: v for k, v in row.items() if k not in {"i", "info"}} for row in chunk],
                })
            chunk = [] if hit is None else [hit]
    return result


def analyze(database: Path, executable: Path, max_depth: int = 4) -> dict:
    exe_sha, index_sha = base.sha256_file(executable), base.sha256_file(database)
    if exe_sha != RETAIL_SHA256 or index_sha != INDEX_SHA256:
        raise ValueError(f"authority hash mismatch: exe={exe_sha} index={index_sha}")
    db = sqlite3.connect(database)
    try:
        fmt = base.index_format(db)
        adjacency, sites = base.direct_graph(db, fmt)
        reachable, paths = base.reachability(adjacency, max_depth)
        ranges = base.sized_ranges(db, reachable)
    finally:
        db.close()
    instructions = base.parse_instructions(base.disassemble(executable), ranges)
    candidates = []
    for start, _end, name, depth in ranges:
        clusters = zero_clusters(instructions.get(name, []))
        if not clusters:
            continue
        path = paths[name]
        candidates.append({
            "function": name, "address": f"0x{start:08x}", "min_direct_depth": depth,
            "shortest_path": path,
            "path_edges": [{"from": a, "to": b, "callsites": sorted(set(sites[(a, b)]))} for a, b in zip(path, path[1:])],
            "clusters": clusters,
        })
    candidates.sort(key=lambda row: (row["min_direct_depth"], row["address"], row["function"]))
    if {row["function"] for row in candidates} != set(EXPECTED_CANDIDATES):
        raise ValueError(f"candidate drift: {[row['function'] for row in candidates]}")
    semantic = [{"function": name, "rejected": True, "class": SEMANTIC[name][0], "evidence": SEMANTIC[name][1]} for name in EXPECTED_CANDIDATES]
    return {
        "format": FORMAT, "version": 1, "ready": True, "owner": "Process 1A / P1.3A",
        "scope": "slot0/slot1 shallow straight-line ordinary-MOV zero-init machine closure",
        "authority": {"platform": "PC retail 1.02", "retail_executable_sha256": exe_sha, "source_index_format": fmt, "source_index_sha256": index_sha, "machine_transfer_adjudicates": True, "callgraph_is_navigation_only": True},
        "roots": list(base.ROOTS), "max_direct_call_depth": max_depth,
        "reachable_sized_function_count": len(ranges), "candidate_count": len(candidates),
        "candidates": candidates, "candidate_adjudication": semantic,
        "adjudication": {
            "shallow_straight_zero_init_depth4_surface_complete": True,
            "shallow_straight_zero_init_candidate_count": len(candidates),
            "shallow_straight_zero_init_rejected_count": len(semantic),
            "selected_hdvehicle_target_writer_found": False,
            "sse_vector_copy_init_ruled_out": False,
            "deeper_direct_alias_paths_ruled_out": False,
            "indirect_or_callback_alias_paths_ruled_out": False,
            "slot0_selected_root_alias_callee_bulk_copy_complete": False,
            "slot1_selected_root_alias_callee_bulk_copy_complete": False,
            "p13a_slot0_complete": False, "p13a_slot1_complete": False,
            "p1_3_control_producer_complete": False, "external_provider_count": 7,
        },
        "limits": [
            "Closes only straight-line ordinary MOV zero initialization within direct depth <=4.",
            "Backward-branch loop stores are excluded because earlier loop contracts already close them.",
            "SSE/vector initialization, deeper direct paths, and indirect/callback carriers remain open.",
            "Reachability and numeric offset equality never establish selected-HDVehicle identity.",
        ],
        "next_step": "Inventory and adjudicate shallow SSE/vector copy-init sequences, then widen only concrete selected-HDVehicle-derived aliases to deeper direct or indirect/callback paths.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path); parser.add_argument("executable", type=Path)
    parser.add_argument("--max-depth", type=int, default=4); parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = analyze(args.database, args.executable, args.max_depth)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    args.output.write_text(text, encoding="utf-8") if args.output else print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
