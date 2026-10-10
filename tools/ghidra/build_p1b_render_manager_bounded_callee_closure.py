#!/usr/bin/env python3
import argparse, json
from pathlib import Path

FORMAT = "SHIFT.P1B.RenderManagerBoundedCalleeClosure/1"


def load(p):
    return json.loads(Path(p).read_text())


def build(direct, byaddr, copyret, derived):
    a = direct["adjudication"]
    assert a["bounded_receiver_transfer_direct_target_opaque_surface_complete"] is True
    assert a["remaining_bounded_direct_target_count"] == 0
    assert byaddr["adjudication"]["these_byaddress_local_paths_closed_negative"] is True
    assert copyret["adjudication"]["known_returned_root_consumer_surface_complete"] is True
    assert derived["adjudication"]["derived_subobject_alias_surface_complete"] is True
    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "upstream_contracts": [direct["format"], byaddr["format"], copyret["format"], derived["format"]],
        "bounded_direct_receiver_targets": {
            "total": a["bounded_direct_target_count"],
            "closed": a["cumulative_explicitly_closed_direct_target_count"],
            "remaining": a["remaining_bounded_direct_target_count"],
            "byaddress_local_helper_paths_closed": byaddr["adjudication"]["closed_path_count"],
        },
        "adjudication": {
            "bounded_direct_callee_alias_surface_complete": True,
            "bounded_direct_callee_can_export_or_recreate_exact_outer_root": False,
            "external_or_unknown_origin_alias_surface_complete": False,
            "memory_load_or_opaque_runtime_reconstruction_complete": False,
            "helper_non_vtable_indirect_setter_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "next_step": "Close external/unknown-origin exact outer-root aliases plus opaque memory/helper/non-vtable setter sources before final manager+0x374 identity adjudication."
    }


def main():
    p = argparse.ArgumentParser()
    for name in ("direct", "byaddr", "copyret", "derived"):
        p.add_argument(name)
    p.add_argument("--json-out", required=True)
    a = p.parse_args()
    out = build(load(a.direct), load(a.byaddr), load(a.copyret), load(a.derived))
    Path(a.json_out).write_text(json.dumps(out, indent=2) + "\n")

if __name__ == "__main__":
    main()
