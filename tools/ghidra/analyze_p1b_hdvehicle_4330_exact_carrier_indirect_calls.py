#!/usr/bin/env python3
"""Bound Ghidra-recorded indirect calls inside exact HDVehicle+0x4330 carriers."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330ExactCarrierIndirectCallSurface/1"
SQLITE_SHA256 = "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
SUPPORTED = {"SHIFT.GhidraSQLiteIndex/1", "SHIFT.GhidraSQLiteIndex/2"}
CARRIERS = {
    "0x00769520": "FUN_00769520",
    "0x0076b130": "FUN_0076b130",
    "0x0076df50": "FUN_0076df50",
    "0x00768a4d": "FUN_00768a4d",
    "0x00756050": "FUN_00756050",
    "0x00772200": "FUN_00772200",
    "0x00772570": "FUN_00772570",
    "0x007c3b00": "FUN_007c3b00",
    "0x0076b280": "FUN_0076b280",
    "0x007618f0": "FUN_007618f0",
    "0x00769640": "FUN_00769640",
    "0x007567a0": "FUN_007567a0",
    "0x00756bb0": "FUN_00756bb0",
    "0x00771db0": "FUN_00771db0",
    "0x00771e10": "FUN_00771e10",
}
EXPECTED = {
    "0x00769520": (280, "9298d68af33d267227cbabe19e663b22a8ddb1720eee0e44cb7778a2b20bc9f3"),
    "0x0076b130": (321, "d74607c82ee610c9ade7a14d3813df774d5621f541c33d64542371f8e3793430"),
    "0x0076df50": (1548, "73a0d9d46d5d1bfd58068d2f72e91b77cf8c31cadb27745ba75b646901834dda"),
    "0x00768a4d": (1427, "b9fd2052029a1f80068d00c9cb5353a5180af538a38a01699677761a54438763"),
    "0x00756050": (97, "5557c675c3b699005eca89288611b4386e928b99b1e69fe4ccea7c815a053a01"),
    "0x00772200": (334, "79328aa9670d0845d454a0f7beb2cf4ab85c3cb988a83ad37bb56001f1596c3e"),
    "0x00772570": (128, "99268e9309b07eb265c80f557853493aad77c203f78dd06bc853d7d6e3b98b4b"),
    "0x007c3b00": (5739, "a8b5650ee33983f6bf4375a491846bb0d675a0274bb75ca99cbb97b1f88b0dce"),
    "0x0076b280": (7796, "9563b40c06bcc7442aabd3308eefa62e1b9f7d0bb9afe752ddf0dc068e0cd7f6"),
    "0x007618f0": (6706, "05ce71ce315b2d6bf40fb224235aaae46ee3db26da789f566e5d05b6953d5b4a"),
    "0x00769640": (1814, "c836df0dcd099dd8fe051c228e3e6df729a8db0efb55488b55576b6374df567d"),
    "0x007567a0": (794, "e630d4b294558d865a871ebd6b78f26699e29cf7cb578a018fdd2779e0209c87"),
    "0x00756bb0": (1844, "9aade43b3d3f6a4e95fe87c9aeea92428f8f2a231048b47566d337ca0ee08d43"),
    "0x00771db0": (87, "37a1584aa3c1f7136e8a1d9989220a0d9f3afafc36238f41284043f99bbaa63b"),
    "0x00771e10": (40, "b97c84382efab8b9931bf3daec9e1ecc440c84bd390182aa8277d973a825e591"),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def analyze(database: Path) -> dict:
    digest = sha256(database)
    if digest != SQLITE_SHA256:
        raise ValueError(f"unexpected SQLite SHA-256: {digest}")
    db = sqlite3.connect(database)
    try:
        row = db.execute("SELECT value FROM metadata WHERE key='format'").fetchone()
        fmt = None if row is None else row[0]
        if fmt not in SUPPORTED:
            raise ValueError(f"unsupported SQLite format: {fmt!r}")

        admitted = []
        for address, name in CARRIERS.items():
            row = db.execute("SELECT name,raw_json FROM functions WHERE lower(address)=?", (address,)).fetchone()
            if row is None:
                raise ValueError(f"missing carrier {address}")
            raw = json.loads(row[1])
            size, expected_digest = EXPECTED[address]
            if row[0] != name or int(raw.get("size") or -1) != size or raw.get("mnemonic_sha256") != expected_digest:
                raise ValueError(f"carrier identity drift: {address}")
            admitted.append({"address": address, "name": name, "size": size, "mnemonic_sha256": expected_digest})

        total_indirect = 0
        carrier_indirect = []
        for (raw_text,) in db.execute("SELECT raw_json FROM calls"):
            rec = json.loads(raw_text)
            if rec.get("indirect") is not True:
                continue
            total_indirect += 1
            source = str(rec.get("from_function") or "").lower()
            if source in CARRIERS:
                carrier_indirect.append({
                    "from_function": source,
                    "from_name": rec.get("from_name"),
                    "instruction": str(rec.get("instruction") or "").lower(),
                })
        if total_indirect <= 0:
            raise ValueError("SQLite no longer exposes indirect call edges")

        return {
            "format": FORMAT,
            "version": 1,
            "ready": True,
            "owner": "Process 1B / P1.3B",
            "authority": {
                "platform": "PC retail 1.02",
                "ghidra_sqlite_sha256": digest,
                "ghidra_sqlite_format": fmt,
                "sqlite_is_navigation_index": True,
            },
            "carrier_set": {
                "count": len(admitted),
                "functions": admitted,
                "semantic_identity_source": "merged exact HDVehicle+0x4330 materializer/consumer retail machine contracts",
            },
            "indirect_surface": {
                "whole_index_indirect_call_edge_count": total_indirect,
                "carrier_indirect_call_edge_count": len(carrier_indirect),
                "carrier_indirect_call_edges": carrier_indirect,
            },
            "adjudication": {
                "sqlite_indirect_call_edge_class_present": True,
                "known_exact_4330_carrier_indirect_call_edge_surface_complete": True,
                "known_exact_4330_carrier_indirect_call_edge_surface_empty": len(carrier_indirect) == 0,
                "indirect_entry_into_carriers_ruled_out": False,
                "callbacks_registered_outside_carriers_ruled_out": False,
                "runtime_generated_or_copied_function_pointers_ruled_out": False,
                "global_runtime_derived_4330_alias_surface_complete": False,
                "manager_374_join_to_hdvehicle_4330_complete": False,
                "last_literal_0x004b86cf_rejected": False,
                "p1_3_control_producer_complete": False,
                "external_provider_count": 7,
            },
            "limits": [
                "This closes only Ghidra-recorded CALLIND edges whose caller is one of the 15 already-proven exact HDVehicle+0x4330 carriers.",
                "Zero carrier CALLIND rows does not rule out indirect entry into a carrier, callbacks invoked elsewhere, stored/generated function pointers, or HDVehicle+0x4330 data aliases created outside the carrier set.",
                "SQLite records are navigation/cross-check evidence; merged retail machine contracts remain semantic authority for exact object identity.",
            ],
            "next_step": "Trace indirect entry into exact carriers plus runtime-generated/copied pointers and non-root-derived HDVehicle+0x4330 data aliases before changing the manager identity gate.",
        }
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = analyze(args.database)
    except ValueError as exc:
        parser.error(str(exc))
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
