#!/usr/bin/env python3
import argparse, json
from pathlib import Path

FORMAT = "SHIFT.P1B.RenderManagerDerivedSubobjectClosure/1"


def load(path):
    return json.loads(Path(path).read_text())


def build(cross, plus4, plus780):
    transitions = cross["result"]["derived_subobject_transitions"]
    assert len(transitions) == 3
    assert plus4["adjudication"]["outer_plus_4_interface_surface_closed_negative_for_exact_root_reconstruction"] is True
    assert plus780["adjudication"]["derived_subobject_alias_surface_complete"] is True
    assert plus780["adjudication"]["outer_plus_0x780_alias_surface_closed_negative_for_exact_root_reconstruction"] is True
    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "upstream_contracts": [
            cross["format"], plus4["format"], plus780["format"]
        ],
        "derived_transitions": transitions,
        "classification": {
            "outer_plus_4": {
                "transition_count": 1,
                "secondary_vtable": plus4["secondary_vtable"]["vtable"],
                "reconstructs_exact_outer_root": False,
            },
            "outer_plus_0x780": {
                "transition_count": len(plus780["root_derived_entry_paths"]),
                "subobject_vtable": plus780["subobject_identity"]["vtable"],
                "reconstructs_exact_outer_root": False,
            },
        },
        "adjudication": {
            "derived_subobject_transition_count": 3,
            "derived_subobject_alias_surface_complete": True,
            "derived_subobject_can_reconstruct_exact_outer_root": False,
            "callee_created_or_external_exact_root_alias_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "next_step": "Close callee-created/external exact outer-root aliases and opaque helper/non-vtable setter paths before final manager+0x374 identity adjudication."
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cross")
    p.add_argument("plus4")
    p.add_argument("plus780")
    p.add_argument("--json-out", required=True)
    a = p.parse_args()
    out = build(load(a.cross), load(a.plus4), load(a.plus780))
    Path(a.json_out).write_text(json.dumps(out, indent=2) + "\n")

if __name__ == "__main__":
    main()
