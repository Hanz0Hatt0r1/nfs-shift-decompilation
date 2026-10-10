#!/usr/bin/env python3
"""Compose bounded static callback/indirect-target evidence for P1.3A.

Consumes the merged P1A 16-carrier composition plus P1D navigation exports for
CALLIND callers and static code-pointer tables. This closes only those finite
exported/static subsets. Runtime callback registration, incoming indirect entry,
computed/encoded pointers and runtime-generated/copied selected-wheel aliases
remain fail-closed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1A.P13ASlot01StaticCallbackTargetComposition/1"
CARRIER_FORMAT = "SHIFT.P1A.P13ASlot01CarrierSurfaceComposition/1"
INDIRECT_FORMAT = "SHIFT.P1D.Slot3ExactCarrierIndirectCallSurface/1"
STATIC_FORMAT = "SHIFT.P1D.Slot3ExactCarrierStaticPointerSurface/1"
INDEX_SHA256 = "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
VTABLES_SHA256 = "15ca935e5bdca1efe2e6b3cac8eb01d20b54c05c5abf829cdb5903b62e52a7ed"
STATIC_TABLES_SHA256 = "798c426ef160d82ea297a088a52e737a7715febc55be631e63afa02390fc5bc2"

EXPECTED_CARRIERS = [
    ("FUN_00758b50", "0x00758b50"),
    ("FUN_00755950", "0x00755950"),
    ("FUN_00770e80", "0x00770e80"),
    ("FUN_00755a60", "0x00755a60"),
    ("FUN_00752fc0", "0x00752fc0"),
    ("FUN_00760b50", "0x00760b50"),
    ("FUN_00763570", "0x00763570"),
    ("FUN_00755f80", "0x00755f80"),
    ("FUN_0076d100", "0x0076d100"),
    ("FUN_00758810", "0x00758810"),
    ("FUN_00769ef0", "0x00769ef0"),
    ("FUN_007675f0", "0x007675f0"),
    ("FUN_007682c0", "0x007682c0"),
    ("FUN_00766510", "0x00766510"),
    ("FUN_00758fc0", "0x00758fc0"),
    ("FUN_00765c40", "0x00765c40"),
]


def require_ready(data: dict, fmt: str, label: str) -> None:
    if data.get("format") != fmt:
        raise ValueError(f"unexpected {label} format: {data.get('format')!r}")
    if data.get("ready") is not True:
        raise ValueError(f"{label} evidence is not ready")


def carrier_rows(data: dict, key: str) -> list[tuple[str, str]]:
    rows = data.get("carrier_set", {}).get(key, [])
    return [(row.get("name"), row.get("address")) for row in rows]


def build(carrier: dict, indirect: dict, static: dict) -> dict:
    require_ready(carrier, CARRIER_FORMAT, "P1A carrier composition")
    require_ready(indirect, INDIRECT_FORMAT, "P1D exact-carrier CALLIND surface")
    require_ready(static, STATIC_FORMAT, "P1D exact-carrier static-pointer surface")

    if carrier.get("carrier_surface", {}).get("carrier_count") != 16:
        raise ValueError("P1A carrier-count drift")
    ca = carrier.get("adjudication", {})
    if ca.get("p13a_sixteen_carrier_call_target_surface_complete") is not True:
        raise ValueError("P1A carrier call-target prerequisite incomplete")
    if ca.get("p13a_sixteen_carrier_runtime_unknown_call_target_found") is not False:
        raise ValueError("P1A carrier surface gained runtime-unknown target")

    if indirect.get("authority", {}).get("ghidra_sqlite_sha256") != INDEX_SHA256:
        raise ValueError("CALLIND Ghidra SQLite SHA-256 drift")
    if indirect.get("carrier_set", {}).get("count") != 16:
        raise ValueError("CALLIND carrier-count drift")
    if carrier_rows(indirect, "functions") != EXPECTED_CARRIERS:
        raise ValueError("CALLIND exact-carrier set drift")
    ins = indirect.get("indirect_surface", {})
    if ins.get("whole_index_indirect_call_edge_count") != 19500:
        raise ValueError("whole-index CALLIND count drift")
    if ins.get("carrier_indirect_call_edge_count") != 0 or ins.get("carrier_indirect_call_edges") != []:
        raise ValueError("exact carrier gained Ghidra-recorded CALLIND caller edge")
    ia = indirect.get("adjudication", {})
    if ia.get("known_exact_carrier_indirect_call_edge_surface_complete") is not True:
        raise ValueError("exact-carrier CALLIND caller surface incomplete")
    if ia.get("known_exact_carrier_indirect_call_edge_surface_empty") is not True:
        raise ValueError("exact-carrier CALLIND caller surface no longer empty")

    auth = static.get("authority", {})
    if auth.get("vtables_sha256") != VTABLES_SHA256:
        raise ValueError("vtables export SHA-256 drift")
    if auth.get("static_tables_sha256") != STATIC_TABLES_SHA256:
        raise ValueError("static-tables export SHA-256 drift")
    if static.get("carrier_set", {}).get("count") != 16:
        raise ValueError("static-pointer carrier-count drift")
    if carrier_rows(static, "rows") != EXPECTED_CARRIERS:
        raise ValueError("static-pointer exact-carrier set drift")

    vt = static.get("vtable_surface", {})
    if vt.get("candidate_table_count") != 2533 or vt.get("slot_count") != 22416:
        raise ValueError("vtable candidate surface drift")
    if vt.get("exact_carrier_target_hit_count") != 0 or vt.get("hits") != []:
        raise ValueError("exact carrier found in exported vtable slot")

    st = static.get("static_table_surface", {})
    expected_static = {
        "record_count": 55066,
        "declared_length_total": 956464,
        "raw_hex_bytes_total": 684472,
        "pointer_encoding": "little-endian 32-bit absolute VA",
        "exact_carrier_pointer_hit_count": 0,
    }
    for key, value in expected_static.items():
        if st.get(key) != value:
            raise ValueError(f"static-table surface drift: {key}")
    if st.get("hits") != []:
        raise ValueError("exact carrier found in exported static table")
    sa = static.get("adjudication", {})
    if sa.get("exact_carrier_vtable_slot_target_subset_complete") is not True:
        raise ValueError("vtable target subset incomplete")
    if sa.get("exact_carrier_static_table_literal_pointer_subset_complete") is not True:
        raise ValueError("static-table pointer subset incomplete")
    if sa.get("static_exact_carrier_pointer_hit_found") is not False:
        raise ValueError("static exact-carrier pointer hit appeared")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1A / P1.3A",
        "upstream_contracts": [CARRIER_FORMAT, INDIRECT_FORMAT, STATIC_FORMAT],
        "authority": {
            "ghidra_sqlite_sha256": INDEX_SHA256,
            "vtables_sha256": VTABLES_SHA256,
            "static_tables_sha256": STATIC_TABLES_SHA256,
            "exports_are_navigation_crosscheck_only": True,
            "cross_lane_evidence_consumed_without_reowning": True,
        },
        "carrier_set": {
            "count": 16,
            "rows": [{"name": name, "address": address} for name, address in EXPECTED_CARRIERS],
        },
        "callind_caller_surface": {
            "whole_index_indirect_call_edge_count": 19500,
            "exact_carrier_caller_edge_count": 0,
            "exact_carrier_caller_edges": [],
        },
        "static_target_surface": {
            "vtable_candidate_count": 2533,
            "vtable_slot_count": 22416,
            "vtable_exact_carrier_target_hit_count": 0,
            "static_table_record_count": 55066,
            "static_table_declared_length_total": 956464,
            "static_table_raw_hex_bytes_total": 684472,
            "static_pointer_encoding": "little-endian 32-bit absolute VA",
            "static_table_exact_carrier_pointer_hit_count": 0,
        },
        "adjudication": {
            "p13a_exact_carrier_callind_caller_subset_complete": True,
            "p13a_exact_carrier_callind_caller_edge_found": False,
            "p13a_exact_carrier_vtable_target_subset_complete": True,
            "p13a_exact_carrier_static_table_literal_pointer_subset_complete": True,
            "p13a_exact_carrier_static_target_hit_found": False,
            "callbacks_registered_outside_carriers_ruled_out": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "global_indirect_dispatch_ruled_out": False,
            "runtime_generated_selected_wheel_pointer_stores_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "p13a_slot0_complete": False,
            "p13a_slot1_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "The CALLIND result closes only Ghidra-recorded indirect-call edges whose caller is one of the 16 exact carriers.",
            "The vtable/static-table result closes only the two finite exported static code-pointer inventories and is navigation/cross-check evidence, not semantic object identity.",
            "Zero static carrier targets does not exclude runtime callback registration, incoming computed indirect entry, copied/encoded code pointers, heap/global pointer stores outside exported records, or selected-wheel data-pointer aliases.",
            "No global callback/indirect-entry, stored-or-escaped-alias, slot0/slot1 or aggregate P1.3 gate is promoted."
        ],
        "next_step": (
            "Trace runtime callback registration/incoming indirect-entry joins and runtime-generated/copied selected-wheel data pointers; "
            "join any positive escape to its consumer before changing global alias gates."
        ),
    }


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--carrier", type=Path, default=Path("evidence/p1a_p13a_slot01_carrier_surface_composition.json"))
    parser.add_argument("--indirect", type=Path, default=Path("evidence/p1d_slot3_exact_carrier_indirect_call_surface.json"))
    parser.add_argument("--static", type=Path, default=Path("evidence/p1d_slot3_exact_carrier_static_pointer_surface.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = build(load(args.carrier), load(args.indirect), load(args.static))
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
