#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

FORMAT = "SHIFT.Fun00766510EarlyResponseBranchOwnership/1"
PINNED_SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"

ANCHORS = {
    "clamp_setup": "*(undefined8 *)((int)this + 0x3b00) = *(undefined8 *)(param_2 + 0xcc8);",
    "table_source": "local_14 = (float *)(param_2 + 0xd20);",
    "table_dest": "pdStack_1c = (double *)((int)this + 0x3b30);",
    "table_stride": "local_14 = local_14 + 0x12;",
    "application_setup": "FUN_00753590(local_d8,&local_c0,(double *)((int)param_2 + 0xcd0));",
    "application_x": "*(undefined8 *)((int)this_01 + 0x3b08) = *puVar24;",
    "derived_3ae8_store": "*(double *)((int)this + 0x3ae8) =",
    "runtime_last_lane": "*(double *)((int)param_1 + 0x3ba8) =",
    "runtime_table_use": "FUN_007551e0((void *)((int)param_1 + 0x3b20),&local_60,local_200,local_1b8,&local_c0);",
    "runtime_application": "FUN_007aefb0((void *)(*(int *)((int)param_1 + 0x33a0) + 0xd4),(double *)((int)param_1 + 0x3b08),",
    "runtime_body_apply": "FUN_007baa70(*(void **)((int)param_1 + 0x33a0),&local_108,local_120);",
    "runtime_accum": "*(double *)((int)param_1 + 0x40a0) = *pdVar7 + *(double *)((int)param_1 + 0x40a0);",
}


def hits(lines: list[str], needle: str) -> list[int]:
    return [i for i, line in enumerate(lines, 1) if needle in line]


def one(lines: list[str], key: str) -> int:
    found = hits(lines, ANCHORS[key])
    if len(found) != 1:
        raise SystemExit(f"expected one {key} anchor, found {found}")
    return found[0]


def one_in_range(lines: list[str], key: str, start: int, end: int) -> int:
    found = [i for i in hits(lines, ANCHORS[key]) if start <= i <= end]
    if len(found) != 1:
        raise SystemExit(
            f"expected one {key} anchor in {start}..{end}, found {found}"
        )
    return found[0]


def analyze(path: Path) -> dict:
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != PINNED_SOURCE_SHA256:
        raise SystemExit(f"unexpected SHIFT.exe.c sha256: {sha}")
    lines = raw.decode("utf-8").splitlines()

    anchor_lines = {
        "clamp_setup": one(lines, "clamp_setup"),
        "table_source": one(lines, "table_source"),
        "table_dest": one(lines, "table_dest"),
        "table_stride": one_in_range(lines, "table_stride", 751619, 751640),
        "application_setup": one(lines, "application_setup"),
        "application_x": one(lines, "application_x"),
        "derived_3ae8_store": one(lines, "derived_3ae8_store"),
        "runtime_last_lane": one(lines, "runtime_last_lane"),
        "runtime_table_use": one(lines, "runtime_table_use"),
        "runtime_application": one(lines, "runtime_application"),
        "runtime_body_apply": one_in_range(lines, "runtime_body_apply", 759541, 759560),
        "runtime_accum": one_in_range(lines, "runtime_accum", 759541, 759560),
    }

    recompute_3ae8 = hits(lines, "FUN_00756b60(")
    if recompute_3ae8 != [751484, 751658, 752626, 752713, 761375]:
        raise SystemExit(f"unexpected FUN_00756b60 surface: {recompute_3ae8}")

    return {
        "format": FORMAT,
        "ready": True,
        "source": {
            "authority": "PC retail 1.02",
            "file": path.name,
            "sha256": sha,
            "retail_executable_sha256": "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1",
            "xbox_recomp_required": False,
        },
        "setup": {
            "function": "FUN_00756bb0 plus FUN_0076b280 application-vector setup",
            "clamp_3b00": {
                "source": "VehicleLoadData+0xcc8",
                "line": anchor_lines["clamp_setup"],
            },
            "table_3b20": {
                "count": 6,
                "entry_stride": "0x18 bytes",
                "source_record_stride": "0x48 bytes",
                "source_record_first_component": "VehicleLoadData+0xd08",
                "source_component_offsets_per_record": ["+0x00", "+0x14", "+0x28"],
                "source_cursor_anchor": "VehicleLoadData+0xd20",
                "source_line": anchor_lines["table_source"],
                "destination_line": anchor_lines["table_dest"],
                "stride_line": anchor_lines["table_stride"],
                "evaluator": "FUN_007a6be0 with explicit f32 spill before f64 storage",
            },
            "application_vector_3b08": {
                "source": "VehicleLoadData+0xcd0 transformed by FUN_00753590",
                "setup_call_line": anchor_lines["application_setup"],
                "store_start_line": anchor_lines["application_x"],
                "storage": "+0x3b08/+0x3b10/+0x3b18",
            },
        },
        "persistent_derived_state": {
            "HDVehicle+0x3ae8": {
                "writer": "FUN_00756b60",
                "formula": "+0x37b8 * s + +0x37b0",
                "selector_state": "+0x3c90",
                "writer_line": anchor_lines["derived_3ae8_store"],
                "writer_call_surface": recompute_3ae8[1:],
                "setup_constant": False,
            },
            "HDVehicle+0x3ba8": {
                "role": "sixth table entry Z lane overwritten immediately before FUN_007551e0",
                "formula": "+0x3af0 * 0.5 * (clamped_pair_sum) + +0x3ae8 + abs(pair_delta) * +0x3af8",
                "runtime_write_line": anchor_lines["runtime_last_lane"],
                "setup_constant": False,
            },
        },
        "runtime_branch": {
            "function": "FUN_00766510",
            "table_use_line": anchor_lines["runtime_table_use"],
            "application_transform_line": anchor_lines["runtime_application"],
            "body_apply_line": anchor_lines["runtime_body_apply"],
            "caller_accumulator_write_line": anchor_lines["runtime_accum"],
            "ordering": "clamp pair -> refresh +0x3ba8 -> table response +0x3b20 -> transform application vector +0x3b08 -> BODY apply -> caller accumulator",
        },
        "adjudication": {
            "early_response_branch_owner_closed": True,
            "table_setup_owner_closed": True,
            "application_vector_setup_owner_closed": True,
            "plus_3ba8_runtime_mutation_required": True,
            "plus_3ae8_persistent_refresh_required": True,
            "safe_to_model_whole_3b20_table_as_setup_constant": False,
            "contact_response_provider_removable_now": False,
        },
        "limits": [
            "The exact physical names of the branch/table are not promoted.",
            "This does not close the optional +0x3bc8/+0x3cxx branch or all later FUN_00766510 paths.",
            "This proof establishes ownership/order, not selected BMW numeric values for all setup records.",
        ],
        "next_owner": "Process 2 can consume this early-branch ownership; Process 1 continues with the optional +0x3bc8/+0x3cxx branch.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = analyze(args.source)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
