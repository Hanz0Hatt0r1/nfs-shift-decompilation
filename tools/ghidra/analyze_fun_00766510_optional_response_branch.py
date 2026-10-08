#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

FORMAT = "SHIFT.Fun00766510OptionalResponseBranchOwnership/1"
PINNED_SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"

ANCHORS = {
    "gate_setup": "*(undefined1 *)((int)this + 0x3bc8) = *(undefined1 *)(param_2 + 0xf10);",
    "mutable_3bd0_setup": "*(double *)((int)this + 0x3bd0) = (double)fVar1;",
    "setup_3bd8": "*(double *)((int)this + 0x3bd8) = (double)(float)fVar4;",
    "setup_3be0": "*(double *)((int)this + 0x3be0) = (double)(float)fVar4;",
    "setup_3be8": "*(undefined8 *)((int)this + 0x3be8) = *(undefined8 *)(param_2 + 0xf80);",
    "setup_3bf0": "*(undefined8 *)((int)this + 0x3bf0) = *(undefined8 *)(param_2 + 0xf90);",
    "setup_3bf8": "*(undefined8 *)((int)this + 0x3bf8) = *(undefined8 *)(param_2 + 0xf60);",
    "setup_3c00": "*(undefined8 *)((int)this + 0x3c00) = *(undefined8 *)(param_2 + 0xf68);",
    "setup_3c08": "*(undefined8 *)((int)this + 0x3c08) = *(undefined8 *)(param_2 + 0xf70);",
    "setup_3c10": "*(undefined8 *)((int)this + 0x3c10) = *(undefined8 *)(param_2 + 0xf88);",
    "setup_3c30": "*(undefined8 *)((int)this + 0x3c30) = *(undefined8 *)(param_2 + 0xf98);",
    "setup_3c38": "*(double *)((int)this + 0x3c38) = 1.0 - *(double *)(param_2 + 4000);",
    "curve_setup": "FUN_00752f10((void *)((int)this + 0x3c40),*(undefined8 *)(param_2 + 0xfa8),",
    "application_setup": "FUN_00753590(local_d8,&local_c0,(double *)((int)param_2 + 0xfc0));",
    "application_store": "*(undefined8 *)((int)this_01 + 0x3c60) = *puVar24;",
    "runtime_gate": "if ((*(char *)((int)param_1 + 0x3bc8) != '\\0') && (local_50 < 0.0)) {",
    "runtime_curve": "fVar9 = FUN_00755340((double *)((int)param_1 + 0x3c40),local_60,local_50);",
    "runtime_scalar_apply": "FUN_007af040((void *)(*(int *)((int)param_1 + 0x33a0) + 0xd4),",
    "runtime_application": "(double *)((int)param_1 + 0x3c60),&local_108);",
    "runtime_body_apply": "FUN_007baa70(*(void **)((int)param_1 + 0x33a0),&local_108,local_120);",
    "runtime_accum": "*(double *)((int)param_1 + 0x40a0) = *pdVar7 + *(double *)((int)param_1 + 0x40a0);",
    "diagnostic_store": "*(double *)((int)param_1 + 0x4298) = local_20;",
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
        "gate_setup", "mutable_3bd0_setup", "setup_3bd8", "setup_3be0",
        "setup_3be8", "setup_3bf0", "setup_3bf8", "setup_3c08", "setup_3c10",
        "setup_3c38", "curve_setup", "application_setup", "application_store",
    )}
    setup["setup_3c00"] = one_in_range(lines, "setup_3c00", 751660, 751696)
    setup["setup_3c30"] = one_in_range(lines, "setup_3c30", 751660, 751696)

    runtime = {
        "runtime_gate": one(lines, "runtime_gate"),
        "runtime_curve": one(lines, "runtime_curve"),
        "runtime_scalar_apply": one_in_range(lines, "runtime_scalar_apply", 759577, 759623),
        "runtime_application": one(lines, "runtime_application"),
        "runtime_body_apply": one_in_range(lines, "runtime_body_apply", 759577, 759623),
        "runtime_accum": one_in_range(lines, "runtime_accum", 759577, 759623),
        "diagnostic_store": one(lines, "diagnostic_store"),
    }

    clamp_mutators = hits(lines, "FUN_00753620((void *)((int)param_1 + 0x3bd0),")
    if clamp_mutators != [752714, 761376]:
        raise SystemExit(f"unexpected +0x3bd0 clamp/reset surface: {clamp_mutators}")
    mutable_3bd0 = {
        "FUN_00757fa0_increment": hits(lines, "this_00 = (double *)((int)this + 0x3bd0);")[0],
        "FUN_00758170_clamp": clamp_mutators[0],
        "FUN_00769d60_reset_clamp": clamp_mutators[1],
        "FUN_0076ed60_state_load": hits(
            lines,
            "*(undefined8 *)((int)this + 0x3bd0) = *(undefined8 *)(param_1 + 0x28);",
        )[0],
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
            "gate_3bc8": {"source": "VehicleLoadData+0xf10", "line": setup["gate_setup"]},
            "coefficients": {
                "+0x3bd8": "evaluated VehicleLoadData+0xf28",
                "+0x3be0": "evaluated VehicleLoadData+0xf3c",
                "+0x3be8": "VehicleLoadData+0xf80",
                "+0x3bf0": "VehicleLoadData+0xf90",
                "+0x3bf8": "VehicleLoadData+0xf60",
                "+0x3c00": "VehicleLoadData+0xf68",
                "+0x3c08": "VehicleLoadData+0xf70",
                "+0x3c10": "VehicleLoadData+0xf88",
                "+0x3c30": "VehicleLoadData+0xf98",
            },
            "derived_shape": {
                "+0x3c18": "VehicleLoadData+0xf78, clamped to zero when <= 0",
                "+0x3c20/+0x3c28": "derived from +0x3c18 then scaled by VehicleLoadData+0xfa0",
                "+0x3c38": "1 - VehicleLoadData+0xfa0",
            },
            "curve_3c40": "FUN_00752f10 from VehicleLoadData+0xfa8/+0xfb0/+0xfb8",
            "application_vector_3c60": "FUN_00753590 from VehicleLoadData+0xfc0 into +0x3c60/+0x3c68/+0x3c70",
            "anchor_lines": setup,
        },
        "persistent_mutable": {
            "HDVehicle+0x3bd0": {
                "initial_source": "evaluated VehicleLoadData+0xf14",
                "initial_line": setup["mutable_3bd0_setup"],
                "mutation_surface": mutable_3bd0,
                "setup_constant": False,
            }
        },
        "runtime_branch": {
            "gate": "+0x3bc8 != 0 and local_50 < 0",
            "gate_line": runtime["runtime_gate"],
            "curve_line": runtime["runtime_curve"],
            "negative_result_required_for_body_apply": True,
            "scalar_apply_line": runtime["runtime_scalar_apply"],
            "application_vector_line": runtime["runtime_application"],
            "body_apply_line": runtime["runtime_body_apply"],
            "caller_accumulator_line": runtime["runtime_accum"],
            "diagnostic_write_line": runtime["diagnostic_store"],
            "ordering": "gate -> coefficient polynomial/clamps -> +0x3c40 curve -> negative-only BODY scalar/vector apply -> caller accumulator -> optional diagnostics",
        },
        "adjudication": {
            "optional_branch_owner_closed": True,
            "gate_and_static_coefficients_setup_owned": True,
            "application_vector_setup_owned": True,
            "plus_3bd0_requires_persistent_mutation_model": True,
            "safe_to_freeze_whole_optional_block_as_setup_config": False,
            "contact_response_provider_removable_now": False,
        },
        "limits": [
            "No physical semantic names are assigned to the optional branch.",
            "This contract does not yet prove all diagnostics/state outside this branch or every remaining FUN_00766510 tail operation.",
            "Selected BMW numeric values are not synthesized.",
        ],
        "next_owner": "Process 2 can consume the optional branch ownership; Process 1 continues residual FUN_00766510 state/diagnostic write audit before callback removal.",
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
