#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / "evidence/hdvehicle_64e8_manager_374_getter_local_alias_surface.json"
PERSIST = ROOT / "evidence/hdvehicle_64e8_manager_374_getter_persistence_closure.json"
WRITERS = ROOT / "evidence/p1b_manager374_writer_coverage.json"
OUT = ROOT / "evidence/p1b_manager374_exact_root_alias_closure.json"


def load(path: Path):
    return json.loads(path.read_text())


def build():
    local = load(LOCAL)
    persist = load(PERSIST)
    writers = load(WRITERS)

    assert local["format"] == "SHIFT.HDVehicle64e8Manager374GetterLocalAliasSurface/1"
    assert persist["format"] == "SHIFT.HDVehicle64e8Manager374GetterPersistenceClosure/1"
    assert writers["format"] == "SHIFT.P1B.Manager374WriterCoverage/1"

    la = local["adjudication"]
    pa = persist["adjudication"]
    wa = writers["adjudication"]

    assert la["immediate_getter_stack_argument_surface_complete"] is True
    assert local["scope"]["immediate_push_eax_after_getter_count"] == 0
    assert pa["exact_getter_stack_persistence_surface_complete"] is True
    assert pa["exact_getter_object_or_global_persistence_surface_complete"] is True
    assert pa["exact_getter_object_or_global_store_count"] == 0
    assert pa["exact_getter_persistence_can_create_manager_plus_0x374_value"] is False
    assert wa["bounded_manager_374_writer_classes_complete"] is True

    return {
        "format": "SHIFT.P1B.Manager374ExactRootAliasClosure/1",
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B aggregate integration",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1",
            "machine_transfer_adjudicates": True,
        },
        "upstream_contracts": [
            local["format"],
            persist["format"],
            writers["format"],
        ],
        "surface": {
            "whole_image_direct_getter_callsite_count": persist["whole_image_direct_getter_callsite_count"],
            "exact_root_stack_save_count": persist["exact_root_persistence_partition"]["stack_save_count"],
            "exact_root_object_or_global_store_count": persist["exact_root_persistence_partition"]["object_or_global_store_count"],
            "immediate_push_eax_after_getter_count": local["scope"]["immediate_push_eax_after_getter_count"],
            "immediate_local_store_count": local["scope"]["immediate_local_store_count"],
            "exact_getter_stack_persistence_surface_complete": True,
            "exact_getter_object_or_global_persistence_surface_complete": True,
            "exact_getter_stack_argument_surface_complete": True,
            "exact_getter_persistence_can_create_manager_plus_0x374_value": False,
        },
        "adjudication": {
            "bounded_manager_374_writer_classes_complete": True,
            "escaped_storage_paths_complete": True,
            "stack_argument_alias_paths_complete": True,
            "exact_getter_root_alias_surface_complete": True,
            "exact_getter_root_alias_can_establish_manager_374_to_hdvehicle_4330_join": False,
            "non_immediate_manager_root_reconstruction_complete": False,
            "helper_or_non_vtable_indirect_setter_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes aliases derived from the exact FUN_00489ad0 return value through registers, stack locals, stack-argument forwarding, object fields, and absolute globals.",
            "No exact getter-root object/global store exists in the audited whole-image persistence surface, and no immediate push of getter EAX exists.",
            "Arithmetic/non-immediate reconstruction of the manager singleton root and helper/non-vtable indirect setters remain outside this contract.",
            "No identity is inferred from matching numeric offsets.",
        ],
        "next_step": "Close arithmetic/non-immediate manager-root reconstruction and helper/non-vtable indirect setter paths, then perform the final manager+0x374 -> HDVehicle+0x4330 identity join and 0x004b86cf / slot2 adjudication.",
    }


def main():
    payload = build()
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if "--check" in __import__("sys").argv:
        assert OUT.read_text() == text
    else:
        OUT.write_text(text)


if __name__ == "__main__":
    main()
