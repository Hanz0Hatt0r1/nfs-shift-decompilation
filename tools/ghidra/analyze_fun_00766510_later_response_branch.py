#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

FORMAT = "SHIFT.Fun00766510LaterResponseBranchOwnership/1"
PINNED_SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"

ANCHORS = {
    "curve_setup": "FUN_00752f10((void *)((int)this + 0x3a08)",
    "table_source": "local_14 = (float *)(param_2 + 0xa68);",
    "table_dest": "pdStack_1c = (double *)((int)this + 0x3a50);",
    "table_stride": "local_14 = local_14 + 0x12;",
    "coeff_3770": "FUN_007a6be0((float *)(param_2 + 0x9f4));",
    "coeff_3778": "FUN_007a6be0((float *)(param_2 + 0xa08));",
    "coeff_3780": "FUN_007a6be0((float *)(param_2 + 0xa1c));",
    "coeff_3788": "FUN_007a6be0((float *)(param_2 + 0x9b8));",
    "coeff_3790": "FUN_007a6be0((float *)(param_2 + 0x9cc));",
    "coeff_3798": "FUN_007a6be0((float *)(param_2 + 0x9e0));",
    "baseline_3cb8": "*(undefined8 *)((int)this + 0x3cb8) = *(undefined8 *)((int)this + 0x3770);",
    "baseline_3cc0": "*(undefined8 *)((int)this + 0x3cc0) = *(undefined8 *)((int)this + 0x3788);",
    "initial_refresh": "FUN_00756b10(this,(double)*(int *)(param_1 + 0x16ec)",
    "application_setup": "FUN_00753590(local_d8,&local_c0,(double *)((int)param_2 + 0xc18));",
    "application_store": "*(undefined8 *)((int)this_01 + 0x3a28) = *puVar24;",
    "writer_selector": "*(double *)((int)this + 0x3cb0) = param_1;",
    "writer_3a00": "*(double *)((int)this + 0x3a00) =",
    "writer_3ac8": "*(double *)((int)this + 0x3ac8) =",
    "runtime_application": "(double *)((int)param_1 + 0x3a28),",
    "runtime_curve": "FUN_00755340((double *)((int)param_1 + 0x3a08),local_60,local_50);",
    "runtime_scale": "fVar9 = fVar9 * (float10)*(double *)((int)param_1 + 0x3a00);",
    "runtime_last_y": "*(double *)((int)param_1 + 0x3ac0) = (double)fVar9;",
    "runtime_table": "FUN_007551e0((void *)((int)param_1 + 0x3a40),&local_60,local_200,local_1b8,&local_78);",
    "runtime_body": "FUN_007baa70(*(void **)((int)param_1 + 0x33a0),&local_108,local_120);",
    "runtime_cross": "pdVar7 = (double *)FUN_00753650(local_1a0,&local_108,local_120);",
    "runtime_accum": "*(double *)((int)param_1 + 0x40a0) = *(double *)((int)param_1 + 0x40a0) + *pdVar7;",
    "diagnostic_gate": "if (local_11 != '\\0') {",
    "diagnostic_store": "*(double *)((int)param_1 + 0x42d8) = local_20;",
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
        raise SystemExit(f"expected one {key} in {start}..{end}, found {found}")
    return found[0]


def analyze(path: Path) -> dict:
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != PINNED_SOURCE_SHA256:
        raise SystemExit(f"unexpected SHIFT.exe.c sha256: {sha}")
    lines = raw.decode("utf-8").splitlines()

    setup = {key: one(lines, key) for key in (
        "curve_setup", "table_source", "table_dest", "coeff_3770", "coeff_3778",
        "coeff_3780", "coeff_3788", "coeff_3790", "coeff_3798", "baseline_3cb8",
        "baseline_3cc0", "initial_refresh", "application_setup", "application_store",
    )}
    setup["table_stride"] = one_in_range(lines, "table_stride", 751573, 751591)

    writer = {key: one(lines, key) for key in (
        "writer_selector", "writer_3a00", "writer_3ac8",
    )}
    refresh_surface = hits(lines, "FUN_00756b10(")
    if refresh_surface != [751469, 751615, 752661, 752742, 761382]:
        raise SystemExit(f"unexpected FUN_00756b10 surface: {refresh_surface}")

    runtime = {
        "application": one(lines, "runtime_application"),
        "curve": one(lines, "runtime_curve"),
        "scale": one(lines, "runtime_scale"),
        "last_y": one(lines, "runtime_last_y"),
        "table": one(lines, "runtime_table"),
        "body": one_in_range(lines, "runtime_body", 759711, 759734),
        "cross": one_in_range(lines, "runtime_cross", 759711, 759734),
        "accum": one(lines, "runtime_accum"),
        "diagnostic_gate": one_in_range(lines, "diagnostic_gate", 759738, 759752),
        "diagnostic_store": one(lines, "diagnostic_store"),
    }

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
        "setup_owned": {
            "curve_3a08": "FUN_00752f10 from VehicleLoadData+0xa38/+0xa40/+0xa48",
            "table_3a40": {
                "count": 6,
                "entry_stride": "0x18 bytes",
                "source_record_stride": "0x48 bytes",
                "source_record_first_component": "VehicleLoadData+0xa50",
                "source_component_offsets_per_record": ["+0x00", "+0x14", "+0x28"],
                "source_cursor_anchor": "VehicleLoadData+0xa68",
                "storage": "+0x3a40..+0x3ac8",
                "runtime_overwritten_lanes": ["+0x3ac0", "+0x3ac8"],
                "evaluator": "FUN_007a6be0 with explicit f32 spill before f64 storage",
            },
            "application_vector_3a28": {
                "source": "VehicleLoadData+0xc18 transformed by FUN_00753590",
                "storage": "+0x3a28/+0x3a30/+0x3a38",
            },
            "coefficient_initial_sources": {
                "+0x3770": "evaluated VehicleLoadData+0x9f4",
                "+0x3778": "evaluated VehicleLoadData+0xa08",
                "+0x3780": "evaluated VehicleLoadData+0xa1c",
                "+0x3788": "evaluated VehicleLoadData+0x9b8",
                "+0x3790": "evaluated VehicleLoadData+0x9cc",
                "+0x3798": "evaluated VehicleLoadData+0x9e0",
            },
            "anchor_lines": setup,
        },
        "persistent_derived_state": {
            "HDVehicle+0x3a00": {
                "writer": "FUN_00756b10",
                "formula": "+0x3780*s^2 + +0x3778*s + +0x3770",
                "selector_state": "+0x3cb0",
                "writer_line": writer["writer_3a00"],
                "writer_call_surface": refresh_surface[1:],
                "setup_constant": False,
            },
            "HDVehicle+0x3ac8": {
                "writer": "FUN_00756b10",
                "formula": "+0x3798*s^2 + +0x3790*s + +0x3788",
                "selector_state": "+0x3cb0",
                "writer_line": writer["writer_3ac8"],
                "writer_call_surface": refresh_surface[1:],
                "setup_constant": False,
            },
            "mutable_coefficient_bases": {
                "+0x3770": {
                    "baseline": "+0x3cb8",
                    "mutation": "FUN_00758000",
                    "clamp_reset": "FUN_00758280 and reset path",
                },
                "+0x3788": {
                    "baseline": "+0x3cc0",
                    "mutation": "FUN_00758000",
                    "clamp_reset": "FUN_00758280 and reset path",
                },
            },
            "HDVehicle+0x3ac0": {
                "role": "sixth table entry second lane overwritten immediately before FUN_007551e0",
                "source": "current FUN_00755340(+0x3a08) result multiplied by persistent +0x3a00",
                "runtime_write_line": runtime["last_y"],
                "setup_constant": False,
            },
        },
        "runtime_branch": {
            "function": "FUN_00766510",
            "application_transform_line": runtime["application"],
            "curve_line": runtime["curve"],
            "scale_line": runtime["scale"],
            "last_entry_y_refresh_line": runtime["last_y"],
            "table_use_line": runtime["table"],
            "body_apply_line": runtime["body"],
            "cross_product_line": runtime["cross"],
            "caller_accumulator_line": runtime["accum"],
            "diagnostic_gate_line": runtime["diagnostic_gate"],
            "diagnostic_write_line": runtime["diagnostic_store"],
            "ordering": "transform +0x3a28 application -> derive relative vector -> +0x3a08 curve * persistent +0x3a00 -> overwrite +0x3ac0 -> +0x3a40 table response -> transform table output -> BODY apply -> FUN_00753650 -> caller accumulator -> optional +0x42d8..+0x42f0 diagnostics",
        },
        "adjudication": {
            "later_response_branch_owner_closed": True,
            "curve_and_application_setup_owner_closed": True,
            "table_setup_owner_closed": True,
            "plus_3a00_persistent_refresh_required": True,
            "plus_3ac0_runtime_mutation_required": True,
            "plus_3ac8_persistent_refresh_required": True,
            "safe_to_model_whole_3a40_table_as_setup_constant": False,
            "contact_response_provider_removable_now": False,
        },
        "limits": [
            "No physical semantic names are promoted for this response block.",
            "This contract does not close FUN_00713630 upstream runtime-global/value ownership or the final cumulative response/tail write audit.",
            "Selected BMW numeric values are not synthesized.",
        ],
        "next_owner": "Process 2 can consume this later-branch ownership; Process 1 continues residual P1.1a/P1.1c proof before contact_response removal.",
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
