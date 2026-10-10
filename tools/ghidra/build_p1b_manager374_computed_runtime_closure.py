#!/usr/bin/env python3
import json
from pathlib import Path

FORMAT = "SHIFT.P1B.Manager374ComputedRuntimeClosure/1"
EXPECTED = {
    "blocker": "SHIFT.P1B.Manager374IdentityBlocker/1",
    "returned": "SHIFT.HDVehicle64e8Manager374ReturnedPointer529020Closure/1",
    "source_only": "SHIFT.HDVehicle64e8Manager374SourceOnlyForwardingBatch/1",
    "p13a_5292": "SHIFT.HDVehicle64e8Manager374P13A005292dbReceiverRejection/1",
    "p13a_5f4f": "SHIFT.HDVehicle64e8Manager374P13A005f4ffaReceiverRejection/1",
    "p13b_5f6e": "SHIFT.HDVehicle64e8Manager374P13B005f6edaReceiverRejection/1",
    "p13b_70f6": "SHIFT.HDVehicle64e8Manager374P13B0070f62dVptrRejection/1",
    "p13d": "SHIFT.P1D.P13D.B04524ComputedReceiverRejections/1",
}

PATHS = {
    "blocker": Path("evidence/p1b_manager374_identity_blocker.json"),
    "returned": Path("evidence/hdvehicle_64e8_manager_374_returned_pointer_529020_closure.json"),
    "source_only": Path("evidence/hdvehicle_64e8_manager_374_source_only_forwarding_batch.json"),
    "p13a_5292": Path("evidence/hdvehicle_64e8_manager_374_p13a_005292db_receiver_rejection.json"),
    "p13a_5f4f": Path("evidence/hdvehicle_64e8_manager_374_p13a_005f4ffa_receiver_rejection.json"),
    "p13b_5f6e": Path("evidence/hdvehicle_64e8_manager_374_p13b_005f6eda_receiver_rejection.json"),
    "p13b_70f6": Path("evidence/hdvehicle_64e8_manager_374_p13b_0070f62d_vptr_rejection.json"),
    "p13d": Path("evidence/p1d_p1_3d_b04524_computed_rejections.json"),
}

SIX_SITES = [
    "0x005292db", "0x005f4ffa", "0x005f6eda",
    "0x0070f62d", "0x0070fb45", "0x0070fdeb",
]


def load(path):
    return json.loads(path.read_text())


def build(inputs):
    for name, expected in EXPECTED.items():
        data = inputs[name]
        assert data.get("format") == expected, (name, data.get("format"))
        assert data.get("ready") is True

    blocker = inputs["blocker"]
    returned = inputs["returned"]
    source = inputs["source_only"]
    a5292 = inputs["p13a_5292"]
    a5f4f = inputs["p13a_5f4f"]
    b5f6e = inputs["p13b_5f6e"]
    b70f6 = inputs["p13b_70f6"]
    d = inputs["p13d"]

    assert blocker["surface"]["remaining_computed_runtime_path_count"] == 18
    assert returned["adjudication"]["returned_computed_pointer_consumer_surface_complete"] is True
    assert returned["adjudication"]["remaining_computed_runtime_path_count"] == 17
    assert source["closed_site_count"] == 11
    assert source["adjudication"]["remaining_callee_forwarding_path_count"] == 6
    assert source["remaining_forwarding_sites"] == SIX_SITES

    assert a5292["adjudication"]["p13a_computed_forwarding_sites_complete"] is True
    assert a5f4f["adjudication"]["p13a_site_0x005f4ffa_complete"] is True
    assert b5f6e["adjudication"]["p13b_computed_forwarding_sites_complete"] is True
    assert b70f6["adjudication"]["p13b_site_0x0070f62d_complete"] is True
    assert d["adjudication"]["assigned_sites_complete"] is True
    assert d["adjudication"]["rejected_site_count"] == 2

    closed_receiver_sites = [
        a5292["target_site"]["address"],
        a5f4f["target_site"]["address"],
        b5f6e["target_site"]["address"],
        b70f6["site"]["address"],
    ] + [x["site"] for x in d["sites"]]
    assert sorted(closed_receiver_sites) == sorted(SIX_SITES)

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B aggregate integration",
        "upstream_contracts": list(EXPECTED.values()),
        "surface": {
            "original_computed_runtime_path_count": 18,
            "direct_write_through_candidate_count": 1,
            "direct_write_through_rejected_count": 1,
            "returned_pointer_path_count": 1,
            "returned_pointer_paths_closed_read_only": 1,
            "callee_forwarding_path_count": 17,
            "source_only_forwarding_path_count": 11,
            "source_only_forwarding_paths_closed": 11,
            "receiver_or_destination_forwarding_path_count": 6,
            "receiver_or_destination_forwarding_paths_closed": 6,
            "receiver_or_destination_sites": SIX_SITES,
            "remaining_computed_runtime_path_count": 0,
        },
        "adjudication": {
            "computed_runtime_paths_complete": True,
            "computed_address_manager_374_writer_surface_complete": True,
            "computed_runtime_path_can_establish_manager_374_to_hdvehicle_4330_join": False,
            "escaped_storage_paths_complete": False,
            "stack_argument_alias_paths_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes the finite computed +0x374 use partition only: direct write-through, returned pointer, source-only forwarding, and six destination/receiver forwarding sites.",
            "Stored manager-root escapes, stack-argument aliases, unrelated reconstructed manager roots, and other non-computed identity paths remain outside this contract.",
            "Completing computed paths does not by itself prove manager+0x374 equals or cannot equal fixed HDVehicle+0x4330 globally.",
        ],
        "next_step": "Close escaped-storage and stack-argument manager-root alias paths, then perform the final manager+0x374 -> HDVehicle+0x4330 identity join and 0x004b86cf adjudication.",
    }


def main():
    inputs = {name: load(path) for name, path in PATHS.items()}
    print(json.dumps(build(inputs), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
