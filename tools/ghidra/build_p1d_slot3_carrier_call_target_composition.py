#!/usr/bin/env python3
"""Compose the complete call-target surface of the 16 exact-root carriers.

The two non-immediate FUN_00770e80 calls are resolved by the corrected PE-import
contract as KERNEL32!InterlockedExchange, not as an on-disk code VA.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1D.Slot3CarrierCallTargetComposition/2"
SUPERSEDES = "SHIFT.P1D.Slot3CarrierCallTargetComposition/1"
DIRECT_FORMAT = "SHIFT.P1D.Slot3DirectCalleeBulkOpcodeClosure/1"
IMPORT_FORMAT = "SHIFT.P1D.Slot3StaticIndirectAA60B4Closure/2"
EXPECTED_DIRECT = 214
EXPECTED_IMPORT_INDIRECT = 2
EXPECTED_TOTAL = 216
EXPECTED_SITES = ["0x00770ec4", "0x00770f41"]
EXPECTED_IMPORT = "KERNEL32!InterlockedExchange"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build(direct_path: Path, import_path: Path) -> dict:
    direct, imported = load(direct_path), load(import_path)
    if direct.get("format") != DIRECT_FORMAT or imported.get("format") != IMPORT_FORMAT:
        raise ValueError("upstream format mismatch")
    if direct.get("ready") is not True or imported.get("ready") is not True:
        raise ValueError("upstream evidence is not ready")

    surface = direct["surface"]
    indirect_sites = [x["site"] for x in surface["indirect_callsites"]]
    resolved_sites = [x["address"] for x in imported["callsites"]]
    if surface["carrier_count"] != 16 or surface["direct_callsite_count"] != EXPECTED_DIRECT:
        raise ValueError("direct carrier call surface drift")
    if surface["indirect_callsite_count"] != EXPECTED_IMPORT_INDIRECT or indirect_sites != EXPECTED_SITES:
        raise ValueError("indirect carrier call surface drift")
    if resolved_sites != EXPECTED_SITES:
        raise ValueError("import resolution site drift")

    gates = imported["adjudication"]
    if gates.get("fun00770e80_aa60b4_import_indirect_subset_complete") is not True:
        raise ValueError("corrected import-indirect subset incomplete")
    if gates.get("aa60b4_runtime_unknown_target") is not False:
        raise ValueError("import-indirect target still unknown")
    if gates.get("aa60b4_runtime_import") != EXPECTED_IMPORT:
        raise ValueError("import target drift")
    if gates.get("aa60b4_on_disk_value_is_code_target") is not False:
        raise ValueError("on-disk import-name RVA regressed to code-target interpretation")

    iat = imported["iat"]
    if iat.get("slot_va") != "0x00aa60b4" or iat.get("import_name") != "InterlockedExchange":
        raise ValueError("IAT identity drift")
    if iat.get("on_disk_value_semantics") != "IMAGE_IMPORT_BY_NAME RVA, not code VA":
        raise ValueError("IAT on-disk semantics drift")

    resolved = []
    for row in imported["callsites"]:
        resolved.append({
            "site": row["address"],
            "slot": "0x00aa60b4",
            "resolution_kind": "PE import/IAT",
            "runtime_import": EXPECTED_IMPORT,
            "operation": row["operation"],
            "target_argument": row["target_argument"],
            "value_argument": row["value_argument"],
        })

    return {
        "format": FORMAT,
        "version": 2,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "supersedes": SUPERSEDES,
        "upstream_contracts": [DIRECT_FORMAT, IMPORT_FORMAT],
        "surface": {
            "carrier_count": 16,
            "total_machine_callsite_count": EXPECTED_TOTAL,
            "immediate_direct_callsite_count": EXPECTED_DIRECT,
            "call_through_memory_site_count": EXPECTED_IMPORT_INDIRECT,
            "runtime_unknown_call_target_count_within_16_carrier_bodies": 0,
            "resolved_call_through_memory_sites": resolved,
            "on_disk_import_name_rva_misclassified_as_code_target": False,
        },
        "adjudication": {
            "sixteen_carrier_machine_call_target_surface_complete": True,
            "sixteen_carrier_runtime_unknown_call_target_found": False,
            "sixteen_carrier_runtime_unknown_call_target_count": 0,
            "sixteen_carrier_import_resolved_callsite_count": 2,
            "sixteen_carrier_static_game_code_target_count_for_aa60b4": 0,
            "other_indirect_entry_ruled_out": False,
            "callbacks_registered_outside_carriers_ruled_out": False,
            "callee_created_aliases_ruled_out": False,
            "runtime_generated_pointer_stores_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "slot3_writer_provenance_proven": False,
            "p1_3d_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This composes only CALL instructions physically present in the 16 exact-root carrier bodies.",
            "The two call-through-memory sites are loader-resolved PE imports to KERNEL32!InterlockedExchange; the on-disk 0x00778052 value is an IMAGE_IMPORT_BY_NAME RVA, not game code.",
            "It does not rule out callbacks, indirect entry into carriers/callees, deeper callee indirection, runtime-generated/copied aliases, or reconstructed pointer aliases."
        ],
        "next_step": "Trace callback/indirect entry and reconstructed/runtime-generated pointer-store surfaces outside the 16 carrier bodies before changing global P1.3D gates."
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("direct", type=Path)
    p.add_argument("imported", type=Path)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    try:
        result = build(a.direct, a.imported)
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        p.error(str(exc))
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if a.output:
        a.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
