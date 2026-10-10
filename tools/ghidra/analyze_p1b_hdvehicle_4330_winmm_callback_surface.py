#!/usr/bin/env python3
"""Bound WinMM wave/timer callback registration for P1B exact HDVehicle+0x4330 carriers."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330WinMMCallbackSurface/1"
SQLITE_SHA256 = "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
SUPPORTED = {"SHIFT.GhidraSQLiteIndex/1", "SHIFT.GhidraSQLiteIndex/2"}

EXACT_CARRIERS = {
    0x00769520, 0x0076B130, 0x0076DF50, 0x00768A4D, 0x00756050,
    0x00772200, 0x00772570, 0x007C3B00, 0x0076B280, 0x007618F0,
    0x00769640, 0x007567A0, 0x00756BB0, 0x00771DB0, 0x00771E10,
}

EXPECTED = {
    "waveOutOpen": {
        ("0x006135a0", "0x006135ee"),
        ("0x00999129", "0x009991f6"),
        ("0x00999b73", "0x00999c69"),
    },
    "waveInOpen": {
        ("0x00613350", "0x0061339e"),
        ("0x009995ee", "0x00999714"),
    },
    "timeSetEvent": {
        ("0x009a8db7", "0x009a8e7d"),
    },
}

NONNULL_CALLBACKS = {
    "waveInOpen@0x00999714": 0x0099955B,
    "timeSetEvent@0x009a8e7d": 0x009A8D8F,
}

REQUIRED_SOURCE_FRAGMENTS = [
    "waveInOpen(&local_18,param_2,&local_14,0,0,0);",
    "waveOutOpen(&local_18,param_2,&local_14,0,0,0);",
    "waveOutOpen(&local_8,param_1,&local_30,0,0,0);",
    "waveOutOpen((LPHWAVEOUT)((int)this + 0x288),param_1,&local_2c,0,0,0);",
    "waveInOpen(phwi,*(UINT *)(param_3 + 0xc),&WStack_2c,0x99955b,param_1,0x30000);",
    "waveInOpen(phwi,*(UINT *)(iVar9 + 0xc),(LPCWAVEFORMATEX)(unaff_EBP + -0x28),0x99955b,\n                       param_1,0x30000);",
    "fptc = &fptc_009a8d8f;",
    "timeSetEvent((UINT)uVar5,uResolution,fptc,dwUser,fuEvent);",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _direct_rows(db: sqlite3.Connection, name: str) -> set[tuple[str, str]]:
    out = set()
    for (raw_text,) in db.execute("SELECT raw_json FROM calls"):
        rec = json.loads(raw_text)
        if rec.get("indirect") is True or rec.get("to_name") != name:
            continue
        out.add((str(rec.get("from_function")).lower(), str(rec.get("instruction")).lower()))
    return out


def analyze(database: Path, source: Path) -> dict:
    db_hash = sha256(database)
    src_hash = sha256(source)
    if db_hash != SQLITE_SHA256:
        raise ValueError(f"unexpected SQLite SHA-256: {db_hash}")
    if src_hash != SOURCE_SHA256:
        raise ValueError(f"unexpected source SHA-256: {src_hash}")

    db = sqlite3.connect(database)
    try:
        fmt_row = db.execute("SELECT value FROM metadata WHERE key='format'").fetchone()
        fmt = None if fmt_row is None else fmt_row[0]
        if fmt not in SUPPORTED:
            raise ValueError(f"unsupported SQLite format: {fmt!r}")
        got = {name: _direct_rows(db, name) for name in EXPECTED}
    finally:
        db.close()

    for name, expected in EXPECTED.items():
        if got[name] != expected:
            raise ValueError(f"{name} call surface drift: {sorted(got[name])!r}")

    text = source.read_text(encoding="utf-8", errors="strict")
    missing = [fragment for fragment in REQUIRED_SOURCE_FRAGMENTS if fragment not in text]
    if missing:
        raise ValueError(f"WinMM source fragment drift: {missing!r}")

    exact_hits = sorted(addr for addr in NONNULL_CALLBACKS.values() if addr in EXACT_CARRIERS)
    if exact_hits:
        raise ValueError(f"exact HDVehicle+0x4330 carrier registered via WinMM: {exact_hits!r}")

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
            "physical_callsite_count": sum(len(rows) for rows in got.values()),
            "waveoutopen_callsite_count": len(got["waveOutOpen"]),
            "waveinopen_callsite_count": len(got["waveInOpen"]),
            "timesetevent_callsite_count": len(got["timeSetEvent"]),
            "null_callback_callsite_count": 4,
            "nonnull_callback_callsite_count": 2,
            "nonnull_callback_entrypoint_count": len(set(NONNULL_CALLBACKS.values())),
            "nonnull_callbacks": [
                {"registration": name, "address": f"0x{addr:08x}"}
                for name, addr in sorted(NONNULL_CALLBACKS.items())
            ],
            "exact_4330_carrier_callback_count": 0,
            "source_rendered_duplicate_wavein_path": True,
            "machine_inventory_is_physical_callsite_authority": True,
        },
        "adjudication": {
            "winmm_callback_surface_complete": True,
            "exact_4330_carrier_reachable_via_winmm": False,
            "runtime_callback_registration_ruled_out": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "global_runtime_derived_4330_alias_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only waveOutOpen, waveInOpen and timeSetEvent callback registration in the pinned retail SQLite/source pair.",
            "Three waveOutOpen sites and the simple waveInOpen site use NULL callbacks; the FMOD waveIn callback is 0x0099955b and the timer callback is 0x009a8d8f.",
            "The Ghidra source renders the FMOD waveInOpen path twice, while the SQLite machine-call inventory pins one physical callsite at 0x00999714.",
            "Other callback APIs, application wrappers, CRT registration, generic function-pointer stores/copies and computed entry remain open.",
        ],
        "next_step": "Continue finite callback registrations and generic runtime function-pointer stores/copies before promoting global runtime-callback or indirect-entry gates.",
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
