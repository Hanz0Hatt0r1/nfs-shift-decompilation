from __future__ import annotations

import json
from pathlib import Path

FORMAT = "SHIFT.P1B.Manager374IdentityBlocker/1"
DIRECT_FORMAT = "SHIFT.HDVehicle64e8Manager374ExactRootDirectCalleeSurface/1"
DSP_FORMAT = "SHIFT.HDVehicle64e8Manager374DirectWriteDspRejection/1"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build(direct: dict, dsp: dict) -> dict:
    assert direct["format"] == DIRECT_FORMAT and direct["ready"] is True
    assert dsp["format"] == DSP_FORMAT and dsp["ready"] is True

    da = direct["adjudication"]
    xa = dsp["adjudication"]
    assert da["direct_callee_count"] == 9
    assert da["direct_callees_writing_manager_374_count"] == 1
    assert da["only_direct_nonzero_writer"] == "FUN_00d60660"
    assert da["only_direct_nonzero_writer_can_equal_fixed_hdvehicle_plus_0x4330"] is False
    assert xa["direct_write_through_computed_candidate_complete"] is True
    assert xa["direct_write_through_computed_candidate_rejected"] is True
    assert xa["remaining_computed_runtime_path_count"] == 18
    assert xa["returned_pointer_escape_complete"] is False
    assert xa["callee_forwarding_surface_complete"] is False

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "upstream_contracts": [DIRECT_FORMAT, DSP_FORMAT],
        "surface": {
            "exact_root_direct_callee_count": 9,
            "exact_root_direct_manager_374_writer_count": 1,
            "only_direct_nonzero_writer": "FUN_00d60660",
            "only_direct_nonzero_writer_value_domain": "allocator-owned manager+0x2a0 selected entry",
            "direct_surface_places_hdvehicle_plus_0x4330_into_manager_374": False,
            "computed_direct_write_candidate_count": 1,
            "computed_direct_write_candidate_rejected_count": 1,
            "remaining_computed_runtime_path_count": 18,
            "remaining_returned_pointer_escape_path_count": 1,
            "remaining_callee_forwarding_path_count": 17,
        },
        "adjudication": {
            "manager_374_direct_writer_surface_composed": True,
            "known_direct_writers_join_to_hdvehicle_4330": False,
            "computed_runtime_paths_complete": False,
            "escaped_storage_paths_complete": False,
            "stack_argument_alias_paths_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This contract composes only the exact-root direct-callee writer surface and the unique direct computed +0x374 write-through rejection.",
            "The remaining 18 computed runtime paths are not adjudicated here: one returned-pointer escape plus seventeen callee-forwarding paths.",
            "No identity is inferred from matching numeric offsets.",
        ],
        "next_step": "Adjudicate the one returned-pointer escape and seventeen callee-forwarding computed runtime paths, then revisit manager+0x374 -> HDVehicle+0x4330 and 0x004b86cf.",
    }


def main() -> None:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("direct", type=Path)
    p.add_argument("dsp", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    a.output.write_text(json.dumps(build(load(a.direct), load(a.dsp)), indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
