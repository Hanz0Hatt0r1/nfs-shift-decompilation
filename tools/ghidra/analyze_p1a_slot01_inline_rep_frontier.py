#!/usr/bin/env python3
"""Bound shallow inline REP MOVS/STOS paths for P1.3A slot0/slot1.

The Ghidra SQLite callgraph is navigation evidence. The retail PE image is the
machine authority. This tool finds REP MOVS/STOS instructions, maps them to
Ghidra function ranges, and records shortest direct-call paths from the four
P1.3A wheel/physics roots. It does not infer HDVehicle identity from reachability
or numeric offsets.
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

FORMAT = "SHIFT.P1A.P13ASlot01InlineRepFrontier/1"
SUPPORTED_INDEXES = {"SHIFT.GhidraSQLiteIndex/1", "SHIFT.GhidraSQLiteIndex/2"}
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
INDEX_SHA256 = "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
DEFAULT_ROOTS = (
    "FUN_00758b50",
    "FUN_0076d100",
    "FUN_00763570",
    "FUN_00770e80",
)

EXPECTED_BYTES = {
    0x0076425F: "33c0",
    0x00764261: "e91574d1ff",
    0x0047B67B: "b954000000",
    0x0047B681: "e9e08b2e00",
    0x00764266: "8dbde0fcffff",
    0x0076426C: "f3ab",
    0x006343A9: "bf309bbf00",
    0x006343C4: "f3a5",
    0x006343CB: "f3a4",
    0x00634415: "befcbeae00",
    0x0063441A: "f3a5",
    0x0063442F: "bee0beae00",
    0x00634434: "f3a5",
    0x007B79A2: "b908000000",
    0x007B79A7: "8db550ffffff",
    0x007B79AD: "8dbd80feffff",
    0x007B79B3: "f3a5",
    0x00887733: "b94096c200",
    0x00887738: "e843feffff",
    0x0088774A: "b84096c200",
    0x00887590: "c706900ab200",
    0x0088766F: "8dbea0030000",
    0x00887675: "b96e000000",
    0x0088767A: "f3ab",
    0x008875FE: "8d8e0c070000",
    0x00887604: "e807f8ffff",
    0x00886E61: "8bf8",
    0x00886E63: "f3a5",
    0x00887118: "8db814020000",
    0x0088711E: "b907000000",
    0x00887129: "f3a5",
    0x0062DF40: "e8fb620000",
    0x007B82F4: "e847f5ffff",
}
EXPECTED_REL32_TARGETS = {
    0x00764261: 0x0047B67B,
    0x0047B681: 0x00764266,
    0x0062DF40: 0x00634240,
    0x007B82F4: 0x007B7840,
    0x00887738: 0x00887580,
    0x00887604: 0x00886E10,
}

REP_RE = re.compile(r"^\s*([0-9a-fA-F]+):\s+.*\brep(?:z|nz)?\s+(movs|stos)\b", re.I)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def index_format(db: sqlite3.Connection) -> str:
    row = db.execute("SELECT value FROM metadata WHERE key='format'").fetchone()
    if row is None:
        raise ValueError("SQLite index has no metadata format")
    fmt = str(row[0])
    if fmt not in SUPPORTED_INDEXES:
        raise ValueError(f"unsupported SQLite index format: {fmt!r}")
    return fmt


def load_function_ranges(db: sqlite3.Connection) -> list[tuple[int, int, str]]:
    ranges: list[tuple[int, int, str]] = []
    for address, name, raw_json in db.execute("SELECT address,name,raw_json FROM functions"):
        try:
            start = int(str(address), 16)
            size = int(json.loads(raw_json).get("size") or 0)
        except (ValueError, TypeError, json.JSONDecodeError):
            continue
        if start > 0 and size > 0 and name:
            ranges.append((start, start + size, str(name)))
    ranges.sort()
    return ranges


def load_direct_edges(db: sqlite3.Connection, fmt: str) -> dict[str, list[tuple[str, str]]]:
    graph: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
    if fmt == "SHIFT.GhidraSQLiteIndex/1":
        for (raw_json,) in db.execute("SELECT raw_json FROM calls"):
            rec = json.loads(raw_json)
            if rec.get("indirect"):
                continue
            src = str(rec.get("from_name") or rec.get("from_function") or "")
            dst = str(rec.get("to_name") or rec.get("to") or "")
            site = str(rec.get("instruction") or rec.get("callsite") or "")
            if src and dst:
                graph[src].append((dst, site))
        return graph

    for caller, callee, callsite, kind, indirect in db.execute(
        "SELECT caller,callee,callsite,kind,indirect FROM calls"
    ):
        if indirect or str(kind).lower() == "indirect":
            continue
        if caller and callee:
            graph[str(caller)].append((str(callee), str(callsite or "")))
    return graph


def parse_rep_sites(text: str) -> list[dict]:
    sites = []
    for line in text.splitlines():
        match = REP_RE.search(line)
        if not match:
            continue
        sites.append({
            "address_int": int(match.group(1), 16),
            "address": f"0x{int(match.group(1), 16):08x}",
            "kind": match.group(2).lower(),
            "text": line.strip(),
        })
    return sites


def map_sites_to_functions(sites: list[dict], ranges: list[tuple[int, int, str]]) -> list[dict]:
    starts = [start for start, _, _ in ranges]
    mapped = []
    for site in sites:
        address = site["address_int"]
        i = bisect.bisect_right(starts, address) - 1
        item = dict(site)
        item.pop("address_int", None)
        item["function"] = None
        if i >= 0:
            start, end, name = ranges[i]
            if start <= address < end:
                item["function"] = name
        mapped.append(item)
    return mapped


def bfs(graph: dict[str, list[tuple[str, str]]], root: str, max_depth: int):
    distance = {root: 0}
    parent: dict[str, str] = {}
    parent_site: dict[str, str] = {}
    queue = collections.deque([root])
    while queue:
        node = queue.popleft()
        if distance[node] >= max_depth:
            continue
        for callee, site in graph.get(node, []):
            if callee in distance:
                continue
            distance[callee] = distance[node] + 1
            parent[callee] = node
            parent_site[callee] = site
            queue.append(callee)
    return distance, parent, parent_site


def path_to(root: str, node: str, distance, parent, parent_site) -> dict:
    nodes = [node]
    callsites = []
    cur = node
    while cur != root:
        callsites.append(parent_site[cur])
        cur = parent[cur]
        nodes.append(cur)
    nodes.reverse()
    callsites.reverse()
    return {"depth": distance[node], "nodes": nodes, "callsites": callsites}


def _pe_layout(data: bytes):
    import struct
    if data[:2] != b"MZ":
        raise ValueError("retail executable is not an MZ image")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe+4] != b"PE\0\0":
        raise ValueError("retail executable has no PE signature")
    coff = pe + 4
    sections = struct.unpack_from("<H", data, coff + 2)[0]
    optional_size = struct.unpack_from("<H", data, coff + 16)[0]
    optional = coff + 20
    magic = struct.unpack_from("<H", data, optional)[0]
    if magic != 0x10B:
        raise ValueError(f"expected PE32 optional header, got {magic:#x}")
    image_base = struct.unpack_from("<I", data, optional + 28)[0]
    table = optional + optional_size
    mapped = []
    for index in range(sections):
        off = table + index * 40
        virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from("<IIII", data, off + 8)
        mapped.append((virtual_address, max(virtual_size, raw_size), raw_pointer))
    return image_base, mapped


def _va_bytes(data: bytes, va: int, size: int) -> bytes:
    image_base, sections = _pe_layout(data)
    rva = va - image_base
    for section_rva, span, raw_pointer in sections:
        if section_rva <= rva < section_rva + span:
            offset = raw_pointer + (rva - section_rva)
            return data[offset:offset + size]
    raise ValueError(f"VA {va:#x} is not mapped by any PE section")


def verify_machine_anchors(executable: Path) -> dict:
    data = executable.read_bytes()
    verified = []
    for va, expected_hex in EXPECTED_BYTES.items():
        expected = bytes.fromhex(expected_hex)
        actual = _va_bytes(data, va, len(expected))
        if actual != expected:
            raise ValueError(f"machine anchor mismatch at {va:#x}: {actual.hex()} != {expected_hex}")
        verified.append({"address": f"0x{va:08x}", "bytes": expected_hex})
    rel32 = []
    for va, target in EXPECTED_REL32_TARGETS.items():
        raw = _va_bytes(data, va, 5)
        if raw[0] not in (0xE8, 0xE9):
            raise ValueError(f"expected rel32 call/jump at {va:#x}")
        disp = int.from_bytes(raw[1:5], "little", signed=True)
        actual_target = va + 5 + disp
        if actual_target != target:
            raise ValueError(f"rel32 target mismatch at {va:#x}: {actual_target:#x} != {target:#x}")
        rel32.append({"site": f"0x{va:08x}", "target": f"0x{target:08x}"})
    return {"byte_windows": verified, "rel32_transfers": rel32}


def analyze(executable: Path, database: Path, *, max_depth: int = 4, objdump: str = "objdump") -> dict:
    if max_depth < 1:
        raise ValueError("max_depth must be >= 1")
    exe_hash = sha256(executable)
    db_hash = sha256(database)
    if exe_hash != RETAIL_SHA256:
        raise ValueError(f"unexpected retail executable SHA-256: {exe_hash}")
    if db_hash != INDEX_SHA256:
        raise ValueError(f"unexpected SQLite index SHA-256: {db_hash}")

    db = sqlite3.connect(database)
    try:
        fmt = index_format(db)
        ranges = load_function_ranges(db)
        graph = load_direct_edges(db, fmt)
    finally:
        db.close()

    machine_anchors = verify_machine_anchors(executable)

    proc = subprocess.run(
        [objdump, "-d", "-M", "intel", str(executable)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    mapped = map_sites_to_functions(parse_rep_sites(proc.stdout), ranges)
    mapped_function_sites = [site for site in mapped if site["function"]]
    by_function: dict[str, list[dict]] = collections.defaultdict(list)
    for site in mapped_function_sites:
        by_function[site["function"]].append(site)

    root_results = []
    candidate_paths: dict[str, list[dict]] = collections.defaultdict(list)
    for root in DEFAULT_ROOTS:
        distance, parent, parent_site = bfs(graph, root, max_depth)
        hits = []
        for function in sorted(by_function):
            if function not in distance:
                continue
            path = path_to(root, function, distance, parent, parent_site)
            hit = {
                "function": function,
                "path": path,
                "rep_sites": by_function[function],
            }
            hits.append(hit)
            candidate_paths[function].append({"root": root, **path})
        hits.sort(key=lambda h: (h["path"]["depth"], h["function"]))
        root_results.append({
            "root": root,
            "max_depth": max_depth,
            "rep_function_hit_count": len(hits),
            "rep_function_hits": hits,
        })

    candidates = []
    for function, paths in candidate_paths.items():
        candidates.append({
            "function": function,
            "minimum_depth": min(p["depth"] for p in paths),
            "reachable_from": sorted(paths, key=lambda p: (p["depth"], p["root"])),
            "rep_sites": by_function[function],
            "candidate_only": True,
        })
    candidates.sort(key=lambda c: (c["minimum_depth"], c["function"]))

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1A / P1.3A",
        "scope": "shallow direct-call inline REP MOVS/STOS frontier for slot0/slot1 alias/bulk-copy closure",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": exe_hash,
            "source_index_format": fmt,
            "source_index_sha256": db_hash,
            "machine_transfer_adjudicates": True,
            "callgraph_is_navigation_only": True,
        },
        "roots": list(DEFAULT_ROOTS),
        "max_direct_call_depth": max_depth,
        "whole_image_rep_site_count": len(mapped),
        "mapped_rep_site_count": len(mapped_function_sites),
        "mapped_rep_function_count": len(by_function),
        "distinct_shallow_candidate_count": len(candidates),
        "verified_machine_anchors": machine_anchors,
        "root_results": root_results,
        "shallow_candidates": candidates,
        "adjudication": {
            "navigation_frontier_captured": True,
            "reachability_or_rep_opcode_proves_selected_hdvehicle_identity": False,
            "shallow_inline_rep_candidates_semantically_rejected": False,
            "slot0_selected_root_alias_callee_bulk_copy_complete": False,
            "slot1_selected_root_alias_callee_bulk_copy_complete": False,
            "p13a_slot0_complete": False,
            "p13a_slot1_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "next_step": (
            "Adjudicate every shallow candidate by exact machine destination and receiver provenance. "
            "Only then may the bounded inline REP subset close; deeper paths, non-REP custom copies, "
            "and indirect dispatch remain separate fail-closed frontiers."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("database", type=Path)
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--objdump", default="objdump")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = analyze(args.executable, args.database, max_depth=args.max_depth, objdump=args.objdump)
    except (ValueError, subprocess.CalledProcessError) as exc:
        parser.error(str(exc))
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
