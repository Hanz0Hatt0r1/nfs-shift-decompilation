#!/usr/bin/env python3
"""Close the first deeper-direct P1.3A HDVehicle-root tranche.

The upstream shallow work proves FUN_0076f030 receives the selected HDVehicle root.
This verifier does not broaden the call graph indiscriminately. It proves that the
only direct callees of FUN_0076f030 not already reachable within depth <=4 are four
bounded depth-5 functions, then adjudicates their exact retail destination domains.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sqlite3
import struct
from pathlib import Path

FORMAT = "SHIFT.P1A.P13ASlot01DeeperHDVehicleRootTranche/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
INDEX_SHA256 = "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
SUPPORTED_INDEXES = {"SHIFT.GhidraSQLiteIndex/1", "SHIFT.GhidraSQLiteIndex/2"}
ROOTS = ("FUN_00758b50", "FUN_0076d100", "FUN_00763570", "FUN_00770e80")
SOURCE = "FUN_0076f030"
EXPECTED_DIRECT_CALLEES = [
    ("0x0076f468", "FUN_007534b0"),
    ("0x0076f499", "FUN_0076eb60"),
    ("0x0076f4a1", "FUN_0076ea70"),
    ("0x0076f51a", "FUN_0090328a"),
    ("0x0076f523", "FUN_00901310"),
    ("0x0076f550", "FUN_0075bdc0"),
]
EXPECTED_NEW_DEPTH5 = ["FUN_007534b0", "FUN_0076ea70", "FUN_00901310", "FUN_0075bdc0"]
EXPECTED_BYTES = {
    0x0076F03A: "8bf1",
    0x0076F464: "8bce",
    0x0076F468: "e84340feff",
    0x0076F49E: "8bce",
    0x0076F4A1: "e8caf5ffff",
    0x0076F523: "e8e81d1900",
    0x0076F54E: "8bce",
    0x0076F550: "e86bc8feff",
    0x007534B2: "dc91583e0000",
    0x007534C4: "dc9948020000",
    0x007534D1: "80b9d23c000000",
    0x007534DA: "80b9a03d000000",
    0x0076EA7D: "8bf1",
    0x0076EA91: "c686d23c000001",
    0x0076EA98: "e8f313faff",
    0x0076EA9D: "8bb888020000",
    0x0076EAA9: "8d55fc",
    0x0076EAAE: "e8ddbef9ff",
    0x0076EAC1: "c6420503",
    0x0076EAC5: "c6420404",
    0x0076EAE0: "894208",
    0x0076EAF7: "894a0c",
    0x0076EAFF: "894210",
    0x0076EB21: "dd86003d0000",
    0x0076EB51: "dd9ea83d0000",
    0x00901322: "dd1c24",
    0x00901325: "f20f2c0424",
    0x0075BDC6: "80b9d23c000000",
    0x0075BDDB: "dc9948020000",
    0x0075BE05: "dd5df0",
    0x0075BE14: "dd5df8",
    0x0075BE2A: "dd55f8",
    0x0075BE2F: "dd55f0",
}
EXPECTED_CALL_TARGETS = {
    0x0076F468: 0x007534B0,
    0x0076F4A1: 0x0076EA70,
    0x0076F523: 0x00901310,
    0x0076F550: 0x0075BDC0,
    0x0076EA98: 0x0070FE90,
    0x0076EAAE: 0x0070A990,
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_pe32(data: bytes):
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise ValueError("not a PE image")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("missing PE signature")
    count = struct.unpack_from("<H", data, pe + 6)[0]
    opt_size = struct.unpack_from("<H", data, pe + 20)[0]
    opt = pe + 24
    if struct.unpack_from("<H", data, opt)[0] != 0x10B:
        raise ValueError("expected PE32")
    image_base = struct.unpack_from("<I", data, opt + 28)[0]
    table = opt + opt_size
    sections = []
    for i in range(count):
        off = table + i * 40
        sections.append((
            struct.unpack_from("<I", data, off + 12)[0],
            struct.unpack_from("<I", data, off + 16)[0],
            struct.unpack_from("<I", data, off + 20)[0],
        ))
    return image_base, sections


def read_va(data: bytes, va: int, size: int) -> bytes:
    base, sections = parse_pe32(data)
    rva = va - base
    for section_rva, raw_size, raw_offset in sections:
        if section_rva <= rva and rva + size <= section_rva + raw_size:
            off = raw_offset + (rva - section_rva)
            return data[off:off + size]
    raise ValueError(f"VA 0x{va:08x} is not file-backed")


def rel32_target(data: bytes, site: int) -> int:
    raw = read_va(data, site, 5)
    if raw[0] != 0xE8:
        raise ValueError(f"0x{site:08x}: expected CALL rel32")
    return site + 5 + struct.unpack_from("<i", raw, 1)[0]


def load_callgraph(database: Path):
    db = sqlite3.connect(database)
    try:
        row = db.execute("SELECT value FROM metadata WHERE key='format'").fetchone()
        fmt = str(row[0]) if row else ""
        if fmt not in SUPPORTED_INDEXES:
            raise ValueError(f"unsupported/missing index format: {fmt!r}")
        adjacency: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
        if fmt.endswith("/1"):
            for (raw,) in db.execute("SELECT raw_json FROM calls"):
                rec = json.loads(raw)
                if rec.get("indirect"):
                    continue
                src = str(rec.get("from_name") or rec.get("from_function") or "")
                dst = str(rec.get("to_name") or rec.get("to") or "")
                site = str(rec.get("instruction") or rec.get("callsite") or "")
                if src and dst:
                    adjacency[src].append((dst, site))
        else:
            for caller, callee, site, kind, indirect in db.execute(
                "SELECT caller,callee,callsite,kind,indirect FROM calls"
            ):
                if indirect or str(kind).lower() == "indirect" or not caller or not callee:
                    continue
                adjacency[str(caller)].append((str(callee), str(site or "")))
        return fmt, adjacency
    finally:
        db.close()


def distances(adjacency, max_depth=5):
    distance: dict[str, int] = {}
    queue = collections.deque()
    for root in ROOTS:
        distance[root] = 0
        queue.append(root)
    while queue:
        node = queue.popleft()
        if distance[node] >= max_depth:
            continue
        for callee, _site in adjacency.get(node, []):
            if callee not in distance:
                distance[callee] = distance[node] + 1
                queue.append(callee)
    return distance


def analyze(executable: Path, database: Path) -> dict:
    exe_hash = sha256(executable)
    db_hash = sha256(database)
    if exe_hash != RETAIL_SHA256:
        raise ValueError(f"unexpected retail SHA-256: {exe_hash}")
    if db_hash != INDEX_SHA256:
        raise ValueError(f"unexpected SQLite SHA-256: {db_hash}")

    fmt, adjacency = load_callgraph(database)
    distance = distances(adjacency)
    direct = sorted(
        ((site.lower(), callee) for callee, site in adjacency.get(SOURCE, [])),
        key=lambda row: int(row[0], 16),
    )
    if direct != EXPECTED_DIRECT_CALLEES:
        raise ValueError(f"{SOURCE} direct-callee surface drifted: {direct!r}")
    if distance.get(SOURCE) != 4:
        raise ValueError(f"{SOURCE} expected at min direct depth 4, got {distance.get(SOURCE)!r}")
    novel = [callee for _site, callee in direct if distance.get(callee) == 5]
    if novel != EXPECTED_NEW_DEPTH5:
        raise ValueError(f"depth-5 tranche drifted: {novel!r}")

    data = executable.read_bytes()
    byte_rows = []
    for site, expected_hex in sorted(EXPECTED_BYTES.items()):
        expected = bytes.fromhex(expected_hex)
        actual = read_va(data, site, len(expected))
        if actual != expected:
            raise ValueError(
                f"0x{site:08x}: bytes mismatch: expected {expected_hex}, got {actual.hex()}"
            )
        byte_rows.append({"site": f"0x{site:08x}", "bytes": expected_hex})

    call_rows = []
    for site, expected_target in sorted(EXPECTED_CALL_TARGETS.items()):
        target = rel32_target(data, site)
        if target != expected_target:
            raise ValueError(
                f"0x{site:08x}: target mismatch: expected 0x{expected_target:08x}, got 0x{target:08x}"
            )
        call_rows.append({"site": f"0x{site:08x}", "target": f"0x{target:08x}"})

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
            "machine_transfer_adjudicates": True,
            "callgraph_is_navigation_only": True,
        },
        "source": {
            "function": SOURCE,
            "min_direct_depth": 4,
            "receiver": "selected HDVehicle root",
            "receiver_proof_upstream": "SHIFT.P1A.P13ASlot01X87ReuseTrancheClosure/1",
            "direct_callee_count": len(direct),
            "direct_callees": [
                {"callsite": site, "function": callee, "min_direct_depth": distance.get(callee)}
                for site, callee in direct
            ],
            "novel_depth5_callees": novel,
        },
        "verified_byte_windows": byte_rows,
        "verified_calls": call_rows,
        "candidate_adjudication": [
            {
                "function": "FUN_007534b0",
                "rejected": True,
                "class": "hdvehicle-root-read-only-predicate",
                "evidence": [
                    "0x0076f464 restores ECX=ESI immediately before 0x0076f468; ESI is the HDVehicle root captured at 0x0076f03a.",
                    "The complete 0x35-byte callee reads only HDVehicle+0x3e58/+0x248 and bytes +0x3cd2/+0x3da0, returns AL, and contains no memory store."
                ],
            },
            {
                "function": "FUN_0076ea70",
                "rejected": True,
                "class": "hdvehicle-root-high-offset-state-plus-service-record",
                "evidence": [
                    "0x0076f49e restores ECX=ESI before 0x0076f4a1; FUN_0076ea70 captures that HDVehicle root in ESI at 0x0076ea7d.",
                    "Direct HDVehicle writes are byte +0x3cd2 at 0x0076ea91 and qword +0x3da8 at 0x0076eb51, both disjoint from +0x938/+0x13b8.",
                    "The remaining writes use EDX returned through FUN_0070a990 on the separate service object loaded from FUN_0070fe90()+0x288; they target service-record +0x4/+0x5/+0x8/+0xc/+0x10."
                ],
            },
            {
                "function": "FUN_00901310",
                "rejected": True,
                "class": "x87-to-int-runtime-helper",
                "evidence": [
                    "0x0076f523 calls the helper without forwarding ECX as an object receiver.",
                    "The helper spills only the incoming x87 value to [ESP] and converts that stack qword with CVTTSD2SI; it has no non-stack destination."
                ],
            },
            {
                "function": "FUN_0075bdc0",
                "rejected": True,
                "class": "hdvehicle-root-read-only-scalar-helper",
                "evidence": [
                    "0x0076f54e restores ECX=ESI before 0x0076f550, so FUN_0075bdc0 receives the exact HDVehicle root.",
                    "The callee reads HDVehicle+0x3cd2 and +0x248; every FST/FSTP destination is EBP-relative stack local. It contains no receiver-relative store."
                ],
            },
        ],
        "adjudication": {
            "deeper_hdvehicle_root_tranche_source_complete": True,
            "novel_depth5_candidate_count": 4,
            "novel_depth5_rejected_count": 4,
            "selected_slot0_slot1_writer_found": False,
            "all_deeper_direct_aliases_ruled_out": False,
            "indirect_callback_aliases_ruled_out": False,
            "p13a_slot0_complete": False,
            "p13a_slot1_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only the novel depth-5 direct callees under the exact HDVehicle-root function FUN_0076f030.",
            "FUN_0076eb60 and FUN_0090328a are direct callees of FUN_0076f030 but already have min direct depth <=4 and therefore remain part of the merged shallow surface rather than this tranche.",
            "No claim is made about unrelated depth-5 functions, deeper descendants, or indirect/callback carriers."
        ],
        "next_step": "Enumerate the next exact HDVehicle/wheel receiver carriers at the shallow boundary and close only their novel deeper direct callees; do not scan unrelated depth-5 nodes wholesale."
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
