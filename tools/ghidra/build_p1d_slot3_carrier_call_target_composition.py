#!/usr/bin/env python3
"""Compose the complete call-target surface of the 16 exact-root carriers."""
from __future__ import annotations
import argparse, json
from pathlib import Path

FORMAT = "SHIFT.P1D.Slot3CarrierCallTargetComposition/1"
DIRECT_FORMAT = "SHIFT.P1D.Slot3DirectCalleeBulkOpcodeClosure/1"
STATIC_FORMAT = "SHIFT.P1D.Slot3StaticIndirectAA60B4Closure/1"
EXPECTED_DIRECT = 214
EXPECTED_STATIC_INDIRECT = 2
EXPECTED_TOTAL = 216
EXPECTED_SITES = ["0x00770ec4", "0x00770f41"]

def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def build(direct_path: Path, static_path: Path) -> dict:
    direct, static = load(direct_path), load(static_path)
    if direct.get("format") != DIRECT_FORMAT or static.get("format") != STATIC_FORMAT:
        raise ValueError("upstream format mismatch")
    surface = direct["surface"]
    sites = [x["site"] for x in surface["indirect_callsites"]]
    resolved_sites = [x["address"] for x in static["callsites"]]
    if surface["carrier_count"] != 16 or surface["direct_callsite_count"] != EXPECTED_DIRECT:
        raise ValueError("direct carrier call surface drift")
    if surface["indirect_callsite_count"] != EXPECTED_STATIC_INDIRECT or sites != EXPECTED_SITES:
        raise ValueError("indirect carrier call surface drift")
    if resolved_sites != EXPECTED_SITES:
        raise ValueError("static resolution site drift")
    if not static["adjudication"]["fun00770e80_aa60b4_static_indirect_subset_complete"]:
        raise ValueError("static indirect subset incomplete")
    if static["adjudication"]["aa60b4_runtime_unknown_target"]:
        raise ValueError("static indirect target still unknown")
    return {
        "format": FORMAT, "version": 1, "ready": True, "owner": "Process 1D / P1.3D",
        "upstream_contracts": [DIRECT_FORMAT, STATIC_FORMAT],
        "surface": {
            "carrier_count": 16,
            "total_machine_callsite_count": EXPECTED_TOTAL,
            "immediate_direct_callsite_count": EXPECTED_DIRECT,
            "call_through_memory_site_count": EXPECTED_STATIC_INDIRECT,
            "runtime_unknown_call_target_count_within_16_carrier_bodies": 0,
            "resolved_call_through_memory_sites": [
                {"site": site, "slot": "0x00aa60b4", "static_image_target": "0x00778052"}
                for site in EXPECTED_SITES
            ],
        },
        "adjudication": {
            "sixteen_carrier_machine_call_target_surface_complete": True,
            "sixteen_carrier_runtime_unknown_call_target_found": False,
            "sixteen_carrier_runtime_unknown_call_target_count": 0,
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
            "It does not rule out callbacks, indirect entry into carriers/callees, deeper callee indirection, runtime code patching, or reconstructed pointer aliases.",
            "The two call-through-memory sites are classified from the pinned retail image slot; this is not a global immutability claim."
        ],
        "next_step": "Trace callback/indirect entry and reconstructed pointer-store surfaces outside the 16 carrier bodies before changing global P1.3D gates."
    }

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("direct", type=Path); p.add_argument("static", type=Path); p.add_argument("--output", type=Path)
    a=p.parse_args()
    try: result=build(a.direct,a.static)
    except (ValueError,KeyError,json.JSONDecodeError) as e: p.error(str(e))
    text=json.dumps(result,indent=2,sort_keys=True)+"\n"
    if a.output: a.output.write_text(text,encoding="utf-8")
    else: print(text,end="")
    return 0
if __name__=="__main__": raise SystemExit(main())
