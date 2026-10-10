#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATHS = {
    "frontier": ROOT / "evidence/p1b_manager374_runtime_root_frontier.json",
    "cfg": ROOT / "evidence/hdvehicle_64e8_render_manager_crossblock_exact_root_store_closure.json",
    "direct_returns": ROOT / "evidence/hdvehicle_64e8_render_manager_returned_root_direct_callers.json",
    "table_returns": ROOT / "evidence/hdvehicle_64e8_render_manager_table_return_closure.json",
}


def load(k):
    return json.loads(PATHS[k].read_text())


def build():
    frontier = load("frontier")
    cfg = load("cfg")
    direct = load("direct_returns")
    table = load("table_returns")

    assert frontier["ready"] is True
    assert cfg["adjudication"]["cross_block_exact_root_memory_store_surface_closed_negative"] is True
    assert direct["adjudication"]["direct_returned_root_caller_surface_complete"] is True
    assert direct["adjudication"]["direct_returned_root_caller_can_persist_or_dispatch_exact_root"] is False
    assert table["adjudication"]["returned_root_consumer_surface_complete"] is True
    assert table["adjudication"]["table_only_returned_root_can_persist_or_dispatch_exact_root"] is False

    return {
        "format": "SHIFT.P1B.RenderManagerCopyReturnClosure/1",
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B aggregate integration",
        "upstream_contracts": [
            frontier["format"], cfg["format"], direct["format"], table["format"]
        ],
        "machine_cfg": {
            "exact_global_seed_count": cfg["scope"]["exact_direct_load_seed_count"],
            "exact_root_memory_store_count": cfg["result"]["exact_root_memory_store_count"],
            "exact_root_push_count": cfg["result"]["exact_root_push_count"],
            "unmodelled_exact_alias_transfer_count": cfg["result"]["unmodelled_exact_alias_transfer_count"],
            "derived_subobject_transition_count": cfg["result"]["derived_subobject_transition_count"],
        },
        "returned_root": {
            "conditional_exact_eax_return_function_count": direct["machine_return_scan"]["conditional_exact_eax_return_function_count"],
            "direct_return_callsite_count": direct["direct_callers"]["callsite_count"],
            "direct_return_consumers_persist_or_dispatch_exact_root": False,
            "table_return_consumer_surface_complete": True,
            "table_return_consumers_persist_or_dispatch_exact_root": False,
        },
        "adjudication": {
            "direct_exact_global_postconstruction_copy_surface_complete": True,
            "direct_exact_global_postconstruction_copy_surface_closed_negative": True,
            "known_returned_root_consumer_surface_complete": True,
            "known_returned_root_can_persist_or_dispatch_exact_root": False,
            "derived_subobject_alias_surface_complete": False,
            "callee_created_or_external_exact_root_alias_surface_complete": False,
            "memory_load_or_opaque_runtime_reconstruction_complete": False,
            "helper_non_vtable_indirect_setter_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "remaining_frontier": {
            "derived_subobject_transitions": cfg["result"]["derived_subobject_transitions"],
            "callee_created_or_external_exact_root_aliases": True,
            "unknown_memory_or_opaque_helper_returns": True,
        },
        "limits": [
            "The closed copy surface starts from exact direct loads of DAT_00bc185c and follows exact register identity only within decoded intra-function CFG paths.",
            "The three LEA-derived subobjects remain distinct from the exact outer root and are not promoted back to it.",
            "Opaque callees, external initialization, unknown-memory loads, and helper-created aliases remain open.",
            "No identity is inferred from matching offsets."
        ],
        "next_step": "Adjudicate the three derived-subobject paths and opaque callee/external exact-root aliases; then revisit the final manager+0x374 identity join and 0x004b86cf.",
    }


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, sort_keys=True))
