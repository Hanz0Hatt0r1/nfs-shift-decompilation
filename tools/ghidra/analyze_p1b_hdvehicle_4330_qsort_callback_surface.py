#!/usr/bin/env python3
"""Bound CRT _qsort comparator callbacks for P1B exact HDVehicle+0x4330 carriers."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330QsortCallbackSurface/1"
SQLITE_SHA256 = "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
SUPPORTED = {"SHIFT.GhidraSQLiteIndex/1", "SHIFT.GhidraSQLiteIndex/2"}

EXACT_CARRIERS = {
    0x00769520, 0x0076B130, 0x0076DF50, 0x00768A4D, 0x00756050,
    0x00772200, 0x00772570, 0x007C3B00, 0x0076B280, 0x007618F0,
    0x00769640, 0x007567A0, 0x00756BB0, 0x00771DB0, 0x00771E10,
}

EXPECTED_QSORT_ROWS = {
    ("0x00432830", "0x00432949"),
    ("0x004bad20", "0x004baec3"),
    ("0x004bad20", "0x004baee1"),
    ("0x004bad20", "0x004baeff"),
    ("0x004e6ea0", "0x004e73c5"),
    ("0x004f2c10", "0x004f306b"),
    ("0x0051e770", "0x0051e7af"),
    ("0x005202f0", "0x00520340"),
    ("0x0053cc80", "0x0053cd4f"),
    ("0x00628010", "0x00628164"),
    ("0x007729d0", "0x00772e83"),
    ("0x007a9f60", "0x007a9fce"),
    ("0x0087d140", "0x0087d1f4"),
    ("0x009aee07", "0x009aeec0"),
    ("0x009b598b", "0x009b5a14"),
    ("0x00a0f2d0", "0x00a0f31b"),
}

COMPARATORS = {
    "FUN_00431dd0": 0x00431DD0,
    "FUN_004ba980": 0x004BA980,
    "FUN_004baa90": 0x004BAA90,
    "FUN_004bab80": 0x004BAB80,
    "FUN_004bac50": 0x004BAC50,
    "FUN_004e5d80": 0x004E5D80,
    "FUN_004efbd0": 0x004EFBD0,
    "FUN_0051ce10": 0x0051CE10,
    "FUN_0051ffd0": 0x0051FFD0,
    "FUN_0053c250": 0x0053C250,
    "FUN_00626140": 0x00626140,
    "FUN_00771320": 0x00771320,
    "FUN_007a7970": 0x007A7970,
    "FUN_0087a730": 0x0087A730,
    "LAB_009aede8": 0x009AEDE8,
    "LAB_009b597a": 0x009B597A,
    "LAB_009f7ac0": 0x009F7AC0,
}

REQUIRED_SOURCE_FRAGMENTS = [
    "_qsort(local_a4,_NumOfElements,8,FUN_00431dd0);",
    "_qsort(param_2,_NumOfElements,1,FUN_004baa90);",
    "_qsort(param_2,_NumOfElements,1,FUN_004bab80);",
    "case 0:\n    _PtFuncCompare = FUN_004ba980;",
    "case 3:\n    _PtFuncCompare = FUN_004bac50;",
    "_qsort(param_2,_NumOfElements,1,_PtFuncCompare);",
    "_qsort(local_1c,(size_t)param_3,4,FUN_004e5d80);",
    "_qsort(local_1c,*(int *)(param_1 + 0x8830) * 3,100,FUN_004efbd0);",
    "_qsort(local_88,uVar1,8,FUN_0051ce10);",
    "_qsort(*(void **)((int)this + 0x34),*(size_t *)((int)this + 0x2c),0x30,FUN_0051ffd0);",
    "_qsort(_Base,*(size_t *)(param_1 + 0x6c),4,FUN_0053c250);",
    "_qsort(*(void **)(param_1 + 0x418),local_c,4,FUN_00626140);",
    "_qsort(_Base,_NumOfElements,0x18,FUN_00771320);",
    "_qsort((void *)param_1[0x1d],param_1[1],8,FUN_007a7970);",
    "_qsort(*(void **)(param_1 + 0xc),*(size_t *)(param_1 + 0x18),8,FUN_0087a730);",
    "*(undefined1 **)(&stack0xffffffd8 + iVar32) = &LAB_009aede8;",
    "_qsort(local_124,_NumOfElements,4,(_PtFuncCompare *)&LAB_009b597a);",
    "_qsort(*(void **)(param_1 + 0x20),*(size_t *)(param_1 + 0x28),4,(_PtFuncCompare *)&LAB_009f7ac0)",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def analyze(database: Path, source: Path) -> dict:
    db_hash = sha256(database)
    src_hash = sha256(source)
    if db_hash != SQLITE_SHA256:
        raise ValueError(f"unexpected SQLite SHA-256: {db_hash}")
    if src_hash != SOURCE_SHA256:
        raise ValueError(f"unexpected source SHA-256: {src_hash}")

    db = sqlite3.connect(database)
    try:
        row = db.execute("SELECT value FROM metadata WHERE key='format'").fetchone()
        fmt = None if row is None else row[0]
        if fmt not in SUPPORTED:
            raise ValueError(f"unsupported SQLite format: {fmt!r}")
        got = set()
        for (raw_text,) in db.execute("SELECT raw_json FROM calls"):
            rec = json.loads(raw_text)
            if rec.get("indirect") is True or rec.get("to_name") != "_qsort":
                continue
            got.add((str(rec.get("from_function")).lower(), str(rec.get("instruction")).lower()))
    finally:
        db.close()

    if got != EXPECTED_QSORT_ROWS:
        raise ValueError(f"_qsort call surface drift: {sorted(got)!r}")

    text = source.read_text(encoding="utf-8", errors="strict")
    missing = [fragment for fragment in REQUIRED_SOURCE_FRAGMENTS if fragment not in text]
    if missing:
        raise ValueError(f"_qsort source fragment drift: {missing!r}")

    exact_hits = sorted(addr for addr in COMPARATORS.values() if addr in EXACT_CARRIERS)
    if exact_hits:
        raise ValueError(f"exact HDVehicle+0x4330 carrier used as qsort comparator: {exact_hits!r}")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "authority": {
            "platform": "PC retail 1.02",
            "ghidra_sqlite_sha256": db_hash,
            "shift_exe_c_sha256": src_hash,
            "sqlite_and_source_are_navigation_crosscheck": True,
        },
        "surface": {
            "direct_qsort_callsite_count": len(got),
            "possible_comparator_entrypoint_count": len(COMPARATORS),
            "possible_comparator_entrypoints": [
                {"name": name, "address": f"0x{addr:08x}"}
                for name, addr in sorted(COMPARATORS.items(), key=lambda item: item[1])
            ],
            "exact_4330_carrier_comparator_count": 0,
            "switch_resolved_dynamic_comparator_site": "0x004baeff",
            "switch_resolved_dynamic_choices": ["FUN_004ba980", "FUN_004bac50"],
            "stack_materialized_comparator_site": "0x009aeec0",
            "stack_materialized_comparator": "LAB_009aede8",
        },
        "adjudication": {
            "qsort_callback_surface_complete": True,
            "exact_4330_carrier_reachable_via_qsort": False,
            "runtime_callback_registration_ruled_out": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "global_runtime_derived_4330_alias_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only comparator callbacks reachable through the 16 direct CRT _qsort callsites in the pinned SQLite/source pair.",
            "The FUN_004bad20 dynamic comparator is finite because the local comparator variable is assigned only FUN_004ba980 or FUN_004bac50 on paths reaching the shared qsort call.",
            "Other application callback wrappers, CRT callback mechanisms, generic function-pointer stores/copies and computed indirect entry remain open.",
        ],
        "next_step": "Continue finite CRT/application callback mechanisms and generic runtime function-pointer stores/copies; keep global callback and manager identity gates fail-closed.",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("database", type=Path)
    p.add_argument("source", type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    try:
        result = analyze(args.database, args.source)
    except ValueError as exc:
        p.error(str(exc))
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
